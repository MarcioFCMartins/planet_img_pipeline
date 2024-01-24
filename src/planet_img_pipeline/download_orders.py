import os
import requests
from dotenv import load_dotenv
from OrderManager import OrderManager


def main():
    # Load planet API key
    load_dotenv()
    API_KEY = os.getenv("API_KEY")
    # Authenthicate session
    planet_session = requests.Session()
    planet_session.auth = (API_KEY, "")

    # Create order manager
    order_manager = OrderManager("./outputs/download_queue.json", planet_session)
    
    # If there is available quota, place new orders
    if order_manager._available_quota() > 0:
        order_manager.place_orders()

    # Download any placed orders that have not yet been downloaded
    order_manager.download_orders("/mnt/10274c4b-4f18-41e0-a518-ff86b71a055f/planet_labs_imagery")


# If running script, run application
if __name__ == "__main__":
    main()
