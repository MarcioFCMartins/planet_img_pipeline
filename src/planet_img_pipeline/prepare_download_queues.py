import os
import requests

from AssetSelector import AssetSelector
from dotenv import load_dotenv


# Main application
def main():
    # Create HTML session with proper Planets key 
    # Get your key in your Planet account page and place it in .env
    load_dotenv()
    API_KEY = os.getenv("API_KEY")
    planet_session = requests.Session()
    planet_session.auth = (API_KEY, "")

    # Load the previous image queries and setup settings for new requests
    query_processor = AssetSelector(
        "./outputs/download_queue.json",
        planet_session=planet_session
    )

    # Load new requests from CSV file
    query_processor.query_available_data("./inputs/image-queries.csv")

    print("\nStarting data optimization")
    query_processor.optimize_available_data(min_coverage=0.95)

    print("\nCreating asset download queue.")
    query_processor.create_download_queue()

    query_processor.generate_report(3, "./outputs/reports/")
    print("\nDownload queue has been created successfully.")

# If running script, run application
if __name__ == "__main__":
    main()
