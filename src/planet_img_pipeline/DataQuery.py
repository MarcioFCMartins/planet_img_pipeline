import time
from TideInterpolator import TideInterpolator


class DataQuery:
    def __init__(self, planet_filter, min_tide, max_tide, port, planet_session):
        self.filter = planet_filter.filter
        self.session = planet_session
        try:
            self.max_tide = float(max_tide)
        except ValueError:
            self.max_tide = None

        try:
            self.min_tide = float(min_tide)
        except ValueError:
            self.min_tide = None

        self.port = port
        self.items = self.__concat_items()

    def query_stats(self, interval):
        stats_filter = {
            "interval": interval,
            "filter": self.filter.filter
        }

        image_stats = self.session.post(
            "https://api.planet.com/data/v1/stats",
            json=stats_filter
        )

        print(image_stats)

        return image_stats.json()

    def __concat_items(self):
        """
        Go through all available pages returned by the query and combine them in a single object. Called at init
        """

        tries = 0
        sleep = 1
        # Submit query 
        while tries < 30:
            tries += 1
            try:
                first_response_page = self.session.post(
                    'https://api.planet.com/data/v1/quick-search?_sort=acquired asc&_page_size=50',
                    json=self.filter
                )
            except Exception:
                # If the query fails, re-try
                print(f'Error in checking delivery status. Retrying in {sleep ** 2 * 10} seconds')
                time.sleep(sleep ** 2 * 10)
                sleep += 1
                continue

        current_page = first_response_page.json()
        last_page = False
        items = []

        if not first_response_page.ok:
            print("There was an error with this query, please check your inputs.")
            return None

        if not current_page["features"]:
            print("No features found for this query.")
            return None

        while not last_page:
            items.extend(current_page["features"])
            next_page_link = current_page["_links"]["_next"]

            if next_page_link is None:
                last_page = True
            else:
                current_page = self.session.get(next_page_link).json()

        if self.max_tide:
            items_filtered = []
            tide_interpolator = TideInterpolator()
            print("Acquiring tide height at time of image captures. This might take a while.")
            for i, item in enumerate(items):
                tidal_height = tide_interpolator.interpolate_tide(date_time=item["properties"]["acquired"], port=self.port)

                if tidal_height >= self.min_tide and tidal_height <= self.max_tide :
                    print(f"Asset {i + 1} of {len(items)} is within tidal range.", end = "\r")
                    item["properties"]["tidal_height"] = tidal_height
                    items_filtered.append(item)
        else:
            print("No tidal height filtering.")
            items_filtered = items

        return items_filtered
