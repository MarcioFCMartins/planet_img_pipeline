import pyproj
from shapely.geometry import shape, GeometryCollection
from shapely.ops import transform


class MosaicOptimizer:
    """
    This class provides methods to select which tiles are optimal to cover the ROI and preview that
     tile selection would look like.
    """
    def __init__(self, data_query):
        self.roi = self.__project_vectors(shape(data_query.filter.roi).buffer(0))
        # Project all vector data to EPSG 3763 to allow calculating areas in square kilometers
        # https://medium.com/@pramukta/recipe-importing-geojson-into-shapely-da1edf79f41d
        if data_query.items:
            self.items = self.__project_vectors(GeometryCollection(
                [shape(item["geometry"]).buffer(0) for item in data_query.items]
            ))
        else:
            self.items = None
        self.query = data_query.items
        self.session = data_query.session

    @staticmethod
    def __project_vectors(vector):
        wgs84 = pyproj.CRS("EPSG:4326")
        pttm06 = pyproj.CRS("EPSG:3763")
        transformation = pyproj.Transformer.from_crs(wgs84, pttm06, always_xy=True).transform
        return transform(transformation, vector)

    def select_tiles(self, n_layers, min_coverage):
        if not self.items:
            return None

        mosaics = []
        # Estimate the intersection area between each of the query items and the ROI
        # https://stackoverflow.com/questions/50372135/calculate-overlap-between-polygon-and-shapefile-in-python-3-6
        intersection_area = []
        for i, item in enumerate(self.items):
            current_intersect = self.roi.intersection(item.convex_hull)
            intersection_area.append(current_intersect.area / 1000000)

        # Select the nth items with highest ROI cover to start the mosaic, where n = number of layers
        starter_indices = sorted(range(len(intersection_area)), key=lambda i: intersection_area[i])[-int(n_layers):]
        mosaics.extend(starter_indices)
        # Keep track of which items were already used in this query
        included_items = mosaics.copy()
        mosaics = [[[index], None] for index in mosaics]
        for i in range(len(mosaics)):
            starter_index = mosaics[i][0][0]
            starter_item = self.items[starter_index]
            missing_region = self.roi.difference(starter_item)
            covered_region = starter_item
            missing_fraction = missing_region.area / self.roi.area

            # Find tiles with highest coverage until the minimum coverage value is reached - maximum of 10 images
            loops = 0
            while missing_fraction > (1 - min_coverage) and loops <= 10:
                # https://stackoverflow.com/questions/50372135/calculate-overlap-between-polygon-and-shapefile-in-python-3-6
                intersection_area = []
                wasted_area = []
                for j, item in enumerate(self.items):
                    if j in included_items:
                        intersection_area.append(0)
                        wasted_area.append(item.area)
                        continue

                    # Penalize
                    cloud_cover_penalty = 1 - (self.query[j]["properties"]["cloud_cover"] / 0.1)
                    cloud_cover_penalty = 1 if cloud_cover_penalty > 1 else cloud_cover_penalty
                    cloud_cover_penalty = 0 if cloud_cover_penalty > 0 else cloud_cover_penalty
                    # Area of missing region covered by item
                    current_intersect = missing_region.intersection(item.convex_hull).area * cloud_cover_penalty
                    # Area already covered by item and outside of roi
                    current_waste = covered_region.intersection(item.convex_hull).area + item.convex_hull.difference(self.roi).area

                    intersection_area.append(current_intersect / 1000000)
                    wasted_area.append(current_waste / 1000000)

                new_tile_index = intersection_area.index(max(intersection_area))
                loops += 1
                # If we are out of tiles, and are starting to re-use them, go to next mosaic
                if new_tile_index in included_items:
                    continue

                mosaics[i][0].append(new_tile_index)
                included_items.append(new_tile_index)
                missing_region = missing_region.difference(self.items[new_tile_index])
                missing_fraction = missing_region.area / self.roi.area
                covered_region = covered_region.union(self.items[new_tile_index])

            # Returns the area of the mosaic,
            mosaics[i][1] = {
                "mosaic_area": covered_region.area / 1000000,
                "wasted_area": covered_region.difference(self.roi).area / 1000000,
                "missing_fraction": missing_fraction}


        return mosaics
