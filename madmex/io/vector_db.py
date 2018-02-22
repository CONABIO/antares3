from . import AntaresDb

from django.contrib.gis.geos import Polygon

@classmethod
def from_geobox(cls, geobox):
    """classmethod to monkey patch django Polygon

    Args:
        geobox (datacube.GeoBox): A GeoBox (ususally an attribute of a Dataset when loaded
            from the datacube)
    """
    left, bottom, right, top = geobox.geographic_extent.boundingbox
    return cls.from_bbox((left, bottom, right, top))

Polygon.from_geobox = from_geobox

class VectorDb(AntaresDb):
    """docstring for VectorDb"""
    def load_from_dataset(self, table, dataset):
        pass

    def load_from_extent(self, table, extent):
        pass

    def load_from_sql(self, sql):
        pass

    def write_fc(self, fc):
        """Write a feature collection to the database
        """
        pass
