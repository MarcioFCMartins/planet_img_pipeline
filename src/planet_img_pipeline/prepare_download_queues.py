import os
import requests
from AssetSelector import AssetSelector
from dotenv import load_dotenv


# Main application
def main():
    load_dotenv()
    API_KEY = os.getenv("API_KEY")

    planet_session = requests.Session()
    planet_session.auth = (API_KEY, "")

    query_processor = AssetSelector("./outputs/download_queue.json", layers=3, planet_session=planet_session)

    query_processor.query_available_data("./inputs/south-portugal-queries-seasonal.csv")

    print("\nStarting data optimization")
    query_processor.optimize_available_data(min_coverage=0.95)

    print("\nCreating asset download queue.")
    query_processor.create_download_queue()

    query_processor.generate_report(3, "./outputs/reports/")
    print("\nDownload queue has been created successfully.")

# If running script, run application
if __name__ == "__main__":
    main()
