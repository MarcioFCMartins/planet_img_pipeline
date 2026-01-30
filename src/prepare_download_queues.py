import os
import requests

from argparse import ArgumentParser
from OrderCreator import OrderCreator
from dotenv import load_dotenv


def main():
    # Create HTML session with proper Planets key 
    # Get your key in your Planet account page and place it in .env
    load_dotenv()
    API_KEY = os.getenv("PLANET_KEY")
    planet_session = requests.Session()
    planet_session.auth = (API_KEY, "")

    # Load file locations from command line arguments
    parser = ArgumentParser()
    parser.add_argument("-q", "--queries", help="CSV file with desired queries")
    parser.add_argument("-o", "--queue", help="Download queue to manage existing queries")
    parser.add_argument("-r", "--report", help="folder to output reports to")
    args = parser.parse_args()

    # Load the previous image queries and setup settings for new requests
    available_data_selector = OrderCreator(
        args.queue,
        planet_session=planet_session
    )

    # Load new requests from CSV file
    available_data_selector.query_available_data(args.queries)

    print("\nStarting data optimization")
    available_data_selector.optimize_available_data(min_coverage=0.90)
    print("\nCreating asset download queue.")
    available_data_selector.create_download_queue()

    available_data_selector.generate_report(3, args.report)
    print("\nDownload queue has been created successfully.")

# If running script, run application
if __name__ == "__main__":
    main()
