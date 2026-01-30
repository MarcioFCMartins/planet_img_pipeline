import time
import json
import hashlib
from TideInterpolator import TideInterpolator

class PlanetFilter:
    def __init__(self, roi, min_date, max_date, max_cloud_cover, asset_type):
        self.roi = self.__load_roi(roi)
        self.min_date = f"{min_date}T00:00:01.000Z"
        self.max_date = f"{max_date}T23:59:59.000Z"
        self.max_cloud_cover = float(max_cloud_cover)
        self.asset_type = asset_type
        self.filter = None

    def build_filter(self):
        date_range_filter = {
            "type": "DateRangeFilter",
            "field_name": "acquired",
            "config": {"gte": self.min_date, "lte": self.max_date},
        }

        roi_filter = {
            "type": "GeometryFilter",
            "field_name": "geometry",
            "config": self.roi,
        }

        cloud_filter = {
            "type": "RangeFilter",
            "field_name": "cloud_cover",
            "config": {"lte": self.max_cloud_cover},
        }

        asset_filter = {"type": "AssetFilter", "config": [self.asset_type]}

        combined_filter = {
            "type": "AndFilter",
            "config": [date_range_filter, roi_filter, cloud_filter, asset_filter],
        }

        planet_filter = {"item_types": ["PSScene"], "filter": combined_filter}

        self.filter = planet_filter

    @staticmethod
    def __load_roi(roi):
        with open(roi) as f:
            roi_json = json.load(f)

        try:
            # If ROI geojson was formatted as an individual polygon, do nothing else
            if roi_json["type"] == "Polygon" or roi_json["type"] == "MultiPolygon":
                pass
            # If a collection of features was passed, select the first polygon
            elif roi_json["type"] == "FeatureCollection":
                # Extract only polygons from the collection
                roi_polygons = [
                    feature["geometry"]
                    for feature in roi_json["features"]
                    if feature["geometry"]["type"] == "Polygon" or feature["geometry"]["type"]  == "MultiPolygon"
                ]

                if len(roi_polygons) > 1:
                    print(f"ROI {roi} has more than one polygon. Only using the first one")

                roi_json = roi_polygons[0]
        except:
            print(f"Error in loading ROI {roi}")
            roi_json = None

        return roi_json

class AvailableDataQuery:
    def __init__(
        self,
        planet_filter,
        planet_session,
        min_tide,
        max_tide,
        port,
        layers,
        clip,
        query_name,
    ):
        self.filter = planet_filter
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
        self.layers = layers
        self.clip = clip
        self.name = query_name
        self.hash = self.__hashname()
        self.items = self.__concat_items()

    def query_stats(self, interval):
        stats_filter = {"interval": interval, "filter": self.filter.filter}

        image_stats = self.session.post(
            "https://api.planet.com/data/v1/stats", json=stats_filter
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
                    "https://api.planet.com/data/v1/quick-search?_sort=acquired asc&_page_size=50",
                    json=self.filter.filter,
                )
            except Exception:
                # If the query fails, re-try
                print(
                    f"Error in checking delivery status. Retrying in {sleep ** 2 * 10} seconds"
                )
                time.sleep(sleep**2 * 10)
                sleep += 1
                continue

        current_page = first_response_page.json()
        last_page = False
        items = []

        if not first_response_page.ok:
            print("There was an error with this query, please check your inputs.")
            print(first_response_page.json())
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

        if (self.max_tide is not None) & (self.min_tide is not None):
            items_filtered = []
            tide_interpolator = TideInterpolator()
            print(
                "Acquiring tide height at time of image captures. This might take a while."
            )
            for i, item in enumerate(items):
                tidal_height = tide_interpolator.interpolate_tide(
                    date_time=item["properties"]["acquired"], port=self.port
                )

                if tidal_height >= self.min_tide and tidal_height <= self.max_tide:
                    print(
                        f"Asset {i + 1} of {len(items)} is within tidal range.",
                        end="\r",
                    )
                    item["properties"]["tidal_height"] = tidal_height
                    items_filtered.append(item)
        else:
            print("No tidal height filtering.")
            items_filtered = items

        # If no items match the filters, return None
        if len(items_filtered) == 0:
            items_filtered = None

        return items_filtered

    def __hashname(self):
        query_str = str(
            str(self.layers)
            + str(self.min_tide)
            + str(self.max_tide)
            + json.dumps(self.filter.filter)
        )
        query_hash = hashlib.md5(query_str.encode("utf-8")).hexdigest()

        return query_hash
