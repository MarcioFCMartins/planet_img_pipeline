import os
import requests
from dotenv import load_dotenv
from OrderManager import OrderManager


def main():
    load_dotenv()
    API_KEY = os.getenv("API_KEY")

    planet_session = requests.Session()
    planet_session.auth = (API_KEY, "")

    order_manager = OrderManager("./outputs/download_queue.json", planet_session)

    #order_manager.place_orders()

    order_manager.download_orders("/mnt/10274c4b-4f18-41e0-a518-ff86b71a055f/planet_labs_imagery")


# If running script, run application
if __name__ == "__main__":
    main()
