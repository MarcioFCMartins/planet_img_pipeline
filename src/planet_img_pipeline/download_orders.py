import os
import requests
from argparse import ArgumentParser
from dotenv import load_dotenv
from OrderManager import OrderManager



def main():
    # Load planet API key
    load_dotenv()
    API_KEY = os.getenv("PLANET_KEY")
    # Authenticate session
    planet_session = requests.Session()
    planet_session.auth = (API_KEY, "")

    # Load file locations from command line arguments
    parser = ArgumentParser()
    parser.add_argument("-q", "--queue", help="Download queue file location")
    parser.add_argument("-s", "--storage", help="Folder to store imagery")
    args = parser.parse_args()

    # Create order manager
    order_manager = OrderManager(args.queue, planet_session)
    
    # If there is available quota, place new orders
    if order_manager._available_quota() > 0:
        order_manager.place_orders()

    # Download any placed orders that have not yet been downloaded
    order_manager.download_orders(args.storage)


# If running script, run application
if __name__ == "__main__":
    main()
