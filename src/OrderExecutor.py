import json
import os
import pathlib
import time
import requests


class OrderExecutor:
    """
    Uses Planet's orders API to clip and download imagery based on a download queue.
    https://github.com/planetlabs/notebooks/blob/master/jupyter-notebooks/orders/tools_and_toolchains.ipynb
    https://github.com/planetlabs/notebooks/blob/master/jupyter-notebooks/orders/ordering_and_delivery.ipynb
    """

    def __init__(self, download_queue, planet_session):
        with open(download_queue, "r", encoding="utf-8") as file:
            self.queue = json.load(file)
        self.queue_path = download_queue
        self.session = planet_session
        self.orders, self.orders_area = self._read_orders()
        self.monthly_quotas = self._available_quota()

    def place_orders(self):
        ORDERS_URL = "https://api.planet.com/compute/ops/orders/v2"
        headers = {"content-type": "application/json"}

        for order in self.orders:
            # Check if order was already placed
            order_queue = self.queue[order["name"]]
            if order_queue["ordered"]:
                print(f'Order {order["name"]} was already submitted. Skipping')
                continue

            # Place new orders. Retries placement with exponential back off
            tries = 0
            sleep = 1
            while tries < 30:
                tries += 1
                try:
                    response = self.session.post(
                        ORDERS_URL, data=json.dumps(order), headers=headers
                    )
                    break
                except Exception:
                    print(
                        f"Error in placing order. Retrying in {sleep ** 2 * 10} seconds",
                        end="\r",
                    )
                    time.sleep(sleep**2 * 10)
                    sleep += 1
                    continue

            # If order placement was valid, wait for server to say if it's successful
            # e.g. you could place a valid order, but be over your monthly quota, which will be a failed query
            if response.ok:
                order_id = response.json()["id"]
                order_name = response.json()["name"]
                order_url = ORDERS_URL + "/" + order_id
                print(
                    f'Order for query {order["name"]} has been placed. Waiting until order is finalized.'
                )
                final_response = self._wait_for_final_state(order_url)

                if final_response["state"] == "success":
                    print(f'Order {final_response["name"]} was a success.')
                    # Update download queue when order is placed
                    self.queue[order_name]["ordered"] = True
                    self.queue[order_name]["id"] = order_id
                    with open(self.queue_path, "w", encoding="utf-8") as file:
                        json.dump(self.queue, file, indent=4)

                elif final_response["state"] == "failed":
                    # If order failed due to lack of quota, stop placing more orders
                    if (final_response["last_message"] == "Quota check failed - Over quota "):
                        print("Your monthly quota was exhausted. Stopping order placement.")
                        break
                    else:
                        print(f'Order {final_response["name"]} failed due to:\n{final_response["last_message"]}')
            # If order placement failed, print error and try next order
            else:
                print(f'Order {order["name"]} returned an unexpected result:')
                try:
                    print(str(response.status_code) + ": " + str(response.json()))
                except Exception:
                    print("Could not retrieve error message")

                continue

    def download_orders(self, download_path, overwrite=False):
        ORDERS_URL = "https://api.planet.com/compute/ops/orders/v2"

        for order_name in self.queue:
            order = self.queue[order_name]
            if order["ordered"] and not order["downloaded"]:
                print(f"\033[1;33m Downloading order {order_name} \033[0m")
                order_url = ORDERS_URL + "/" + order["id"]
                response = self._wait_for_delivery(order_url)
                results = response["_links"]["results"]
                results_urls = [r["location"] for r in results]
                # Retrieve the path to store each item in
                results_names = [r["name"] for r in results]
                # Replace the query ID in the file path with our user-based query name
                results_names = [f'{order_name}/{pathlib.Path(*pathlib.Path(result).parts[1:])}' for result in results_names]

                for url, name in zip(results_urls, results_names):
                    file_path = pathlib.Path(os.path.join(download_path, name))

                    if overwrite or not file_path.exists():
                        print(f"Downloading {name}")
                        r = requests.get(url, allow_redirects=True)
                        file_path.parent.mkdir(parents=True, exist_ok=True)
                        open(file_path, "wb").write(r.content)
                    else:
                        print(f"{name} already exists. Download skipped")

                # Update download queue when order is downloaded
                order["downloaded"] = True
                with open(self.queue_path, "w", encoding="utf-8") as file:
                    json.dump(self.queue, file, indent=4)

    def check_order_status(self):
        colors = {
            "downloaded": "\033[32m",
            "submitted": "\033[34m",
            "to be processed": "\033[33m",
            "end color": "\033[0m",
        }

        for order_name in self.queue:
            order = self.queue[order_name]

            if order["downloaded"]:
                print(colors["downloaded"] + order_name + colors["end color"])
            elif order["ordered"]:
                print(colors["submitted"] + order_name + colors["end color"])
            else:
                print(colors["to be processed"] + order_name + colors["end color"])

    def _wait_for_delivery(self, order_url):
        tries = 0
        sleep = 1
        while tries < 30:
            tries += 1
            try:
                response = self.session.get(order_url).json()
            except Exception:
                # If the query fails, re-try
                print(
                    f"Error in checking delivery status. Retrying in {sleep ** 2 * 10} seconds"
                )
                time.sleep(sleep**2 * 10)
                sleep += 1
                continue

            message = response["last_message"]
            if message == "Manifest delivery completed":
                return response

            # If the order is not in a final state yet, wait and re-try
            print(f"Order not ready yet, trying again {sleep ** 2 * 10} seconds.")
            time.sleep(sleep**2 * 10)
            sleep += 1

    def _wait_for_final_state(self, order_url):
        tries = 0
        sleep = 1
        while True:
            tries += 1
            try:
                response = self.session.get(order_url).json()
            except Exception:
                # If the query fails, re-try
                print(
                    f"Error in checking order status. Retrying in {sleep ** 2 * 10} seconds",
                    end="\r",
                )
                time.sleep(sleep**2 * 10)
                sleep += 1
                continue

            state = response["state"]
            end_states = ["success", "failed", "partial"]
            if state in end_states:
                return response
            # If the order is not in a final state yet, wait and re-try
            print(f"Order not ready, trying again in 60 seconds.")
            time.sleep(60)

    def _read_orders(self):
        orders = []
        areas = []

        for query_id in self.queue:
            query = self.queue[query_id]
            query_items = query["items"]
            query_roi = query["roi"]
            query_area = query["area"]
            # We want the optimally selected items, 4band and surface reflectance
            query_products = [
                {
                    "item_ids": query_items,
                    "item_type": "PSScene",
                    "product_bundle": "analytic_8b_sr_udm2",
                }
            ]
            # Clip to given ROI and create a composite from all images
            clip = {"clip": {"aoi": query_roi}}

            # Build final request
            order_request = {
                "name": query_id,
                "products": query_products,
                "tools": [clip],
            }

            areas.append(query_area)
            orders.append(order_request)

        return orders, areas

    def _available_quota(self):
        quotas = self.session.get(
            "https://api.planet.com/auth/v1/experimental/public/my/subscriptions"
        ).json()
        try:
            remaining = quotas[0]["quota_sqkm"] - quotas[0]["quota_used"]
        except Exception:
            print(
                "\033[1;33m You can not access your quota, make sure you have an active account. \033[0m"
            )
            print(f'Message: {quotas.get("message")}')
            remaining = 0

        return remaining
