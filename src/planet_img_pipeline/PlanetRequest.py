import json

class PlanetRequest:
    def __init__(self, roi, min_date, max_date, max_cloud_cover):
        with open(roi) as f:
            self.roi = json.load(f)
        self.min_date = f"{min_date}T00:00:00.000Z"
        self.max_date = f"{max_date}T00:00:00.000Z"
        self.max_cloud_cover = float(max_cloud_cover)
        self.filter = None
        
    def build_request(self):
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
