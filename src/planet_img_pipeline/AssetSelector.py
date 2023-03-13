import csv
import json
import math
from io import BytesIO
import PIL
import time
import pyproj
import pathlib
import os
import hashlib

from TideInterpolator import TideInterpolator
from DataQuery import DataQuery
from MosaicOptimizer import MosaicOptimizer
from pathlib import Path
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas
from shapely.geometry import shape
from shapely.ops import transform

class PlanetFilter:
    def __init__(self, roi, min_date, max_date, max_cloud_cover):
        with open(roi) as f:
            self.roi = json.load(f)
        self.min_date = f"{min_date}T00:00:00.000Z"
        self.max_date = f"{max_date}T00:00:00.000Z"
        self.max_cloud_cover = float(max_cloud_cover)
        self.filter = None
        
    def build_filter(self):
        date_range_filter = {
          "type": "DateRangeFilter",
          "field_name": "acquired",
          "config": {
            "gte": self.min_date,
            "lte": self.max_date
            }
        }
        
        roi_filter = {
            "type": "GeometryFilter",
            "field_name": "geometry",
            "config": self.roi
        }
        
        cloud_filter = {
            "type": "RangeFilter",
            "field_name": "cloud_cover",
            "config": {
                "lte": self.max_cloud_cover
            }
        }

        asset_filter = {
            "type": "AssetFilter",
            "config": ["ortho_analytic_8b_sr"]
        }

        image_filter = {
            "type": "AndFilter",
            "config": [date_range_filter, roi_filter, cloud_filter, asset_filter]
        }
            
        self.filter = image_filter


class AssetSelector:
    def __init__(self, download_queue_path, layers, planet_session):
        self.planet_session = planet_session
        self.available_data = []
        self.query_names = []
        self.query_hashes = []
        self.queries = []
        self.download_queue_path = download_queue_path
        self.layers = layers
        # If a download queue already exists, load it
        if os.path.isfile(download_queue_path):
            with open(download_queue_path, "r", encoding="utf-8") as file:
                self.download_queue = json.load(file)
        else:
            self.download_queue = {}

    def query_available_data(self, file_path):
        row_count = sum(1 for row in open(file_path)) - 1
        with open(file_path) as file:
            filter_csv = csv.reader(file, delimiter=",")
            next(filter_csv, None)  # Skip header

            for i, row in enumerate(filter_csv):
                planet_filter = PlanetFilter(row[0], row[1], row[2], row[3])
                planet_filter.build_filter()

                query_hash = str(self.layers) + row[3] + row[4] + json.dumps(planet_filter.filter)
                query_hash = hashlib.md5(query_hash.encode("utf-8")).hexdigest()

                query_name = f'{Path(row[0]).stem}_{row[1].replace("-", "")}_{row[2].replace("-", "")}'
                print(f'\nQuerying DATA API: {filter_csv.line_num - 1} of {row_count}')
                query_result = DataQuery(planet_filter, row[5], row[6], self.planet_session)

                if query_result.items:
                    self.query_names.append(query_name)
                    self.query_hashes.append(query_hash)
                    self.available_data.append(query_result)

                # Sleep to respect rate limit of 10 requests per second
                time.sleep(0.1)

    def optimize_available_data(self, min_coverage):
        optimal_tiles = []
        geometries = []
        query_number = len(self.available_data)
        queued_hashes = [query["hash"] for query in self.download_queue.values()]

        for i, query in enumerate(self.available_data):
            # If this query is already in the download queue, skip to next one
            query_hash = self.query_hashes[i]
            if query_hash in queued_hashes:
                optimal_tiles.append(None)
                print(f'Query {self.query_names[i]} is already in queue. Skipping.')
                continue

            optimizer = MosaicOptimizer(query)
            query_result = optimizer.select_tiles(self.layers, min_coverage)
            optimal_tiles.append(query_result)
            geometries.append(optimizer.items)

            print(f'Optimizing selected assets: {i + 1} of {query_number}')

        self.queries = optimal_tiles

    def create_download_queue(self):
        for i, query in enumerate(self.queries):
            # Skip queries that were already in queue
            if query is None:
                continue

            query_name = self.query_names[i]
            query_hash = self.query_hashes[i]
            query_roi = self.available_data[i].filter.roi
            query_area = self.__project_vectors(shape(query_roi).buffer(0))
            query_area = query_area.area
            query_queue = {
                "roi": query_roi,
                "hash": query_hash,
                "items": [],
                "ordered": False,
                "downloaded": False,
                "area": query_area
            }
            for j, mosaic in enumerate(query):
                for k, item_index in enumerate(mosaic[0]):
                    current_item = self.available_data[i].items[item_index]
                    query_queue["items"].append(current_item["id"])

            self.download_queue[query_name] = query_queue

        with open(self.download_queue_path, "w", encoding="utf-8") as file:
            json.dump(self.download_queue, file, indent=4)

    def generate_report(self, grid_cell_number, destination_folder):
        for i, query in enumerate(self.queries):
            # Skip queries that were already in queue
            if query is None:
                continue

            report_name = f'{self.query_names[i]}.pdf'
            PAGE_SIZE = 1200
            grid_size = math.floor((PAGE_SIZE - 200) / grid_cell_number)
            report_path = pathlib.Path(os.path.join(destination_folder, report_name))
            canvas = Canvas(str(report_path), pagesize=(PAGE_SIZE, PAGE_SIZE))
            canvas.translate(0, PAGE_SIZE)
            # count how many thumbnails were drawn to decide when to change pages
            drawn_thumbnails = 0
            cells_per_page = grid_cell_number * grid_cell_number
            page = 0
            image_size = grid_size - 50
            col = 0
            row = 0

            # Store which items must be included in the report for this query
            query_items = []
            # And the total bandwith used / wasted by the query
            query_stats = {
                "query_area": 0,
                "wasted_area": 0
            }

            for mosaic in query:
                query_items.extend(mosaic[0])
                mosaic_stats = mosaic[1]
                query_stats["query_area"] = query_stats["query_area"] + mosaic_stats["mosaic_area"]
                query_stats["wasted_area"] = query_stats["wasted_area"] + mosaic_stats["wasted_area"]

            # Start by adding the stats of that query to the page
            canvas.drawString(500, -100, f'used bandwidth:{round(query_stats["query_area"])} km2')
            canvas.drawString(500, -120, f'wasted bandwidth:{round(query_stats["wasted_area"])} km2')

            for j, item_index in enumerate(query_items):
                item = self.available_data[i].items[item_index]
                # Get coordinates in the page for corresponding cell
                x = col * grid_size
                y = row * grid_size + 200  # Leave top of page empty for mosaic stats

                # Recommendations from requests author on reading image from a request
                # https://2.python-requests.org/en/latest/user/quickstart/#binary-response-content
                thumbnail = self.planet_session.get(item["_links"]["thumbnail"], stream=True)
                thumbnail = PIL.Image.open(BytesIO(thumbnail.content))
                time.sleep(0.1)

                acquired = str(item["properties"]["acquired"])
                cloud_cover = str(item["properties"]["cloud_cover"])
                stage = str(item["properties"]["publishing_stage"])
                item_id = str(item["id"])
                tide = str(item["properties"]["tidal_height"]) if "tidal_height" in item["properties"] else "NA"

                canvas.drawImage(ImageReader(thumbnail), x, - y - image_size, width=image_size,
                                 height=image_size)
                canvas.drawString(x, - y - image_size - 15, f'{item_id} : {acquired}')
                canvas.drawString(x, - y - image_size - 30, f'cloud cover:{cloud_cover}  tide:{tide}')
                canvas.drawString(x, - y - image_size - 45, stage)

                drawn_thumbnails += 1

                # If page is full, start new page and skip increments to col and row indices
                if drawn_thumbnails == cells_per_page:
                    canvas.showPage()
                    canvas.translate(0, PAGE_SIZE)
                    drawn_thumbnails = 0
                    page += 1
                    row = 0
                    col = 0
                    continue

                # Update row and column indices
                col += 1
                if col >= grid_cell_number:
                    col = 0
                    row = row + 1

            print(f'Report saved to {report_path}')
            canvas.save()

    @staticmethod
    def __project_vectors(vector):
        wgs84 = pyproj.CRS("EPSG:4326")
        pttm06 = pyproj.CRS("EPSG:3763")
        transformation = pyproj.Transformer.from_crs(wgs84, pttm06, always_xy=True).transform
        return transform(transformation, vector)


