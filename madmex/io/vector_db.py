from . import AntaresDb
from madmex.overlay.conversions import querySet_to_fc

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
    """Query, read and write geometries between python's memory and the database"""
    def load_training_from_dataset(self, dataset):
        """Retieves training data from the database based on intersection with an xr Dataset

        Args:
            dataset (xarray.Dataset): Typical Dataset object generated using one of
                the datacube load method (GridWorkflow or Datacube clases)

        Return:
            list: A feature collection in the CRS in which it is stored in the database
        """
        from madmex.models import TrainObject
        geobox = dataset.geobox
        poly = Polygon.from_geobox(geobox)
        query_set = TrainObject.objects.filter(the_geom__contained=poly)
        fc = [querySet_to_fc(x) for x in query_set]
        return fc

    def load_from_extent(self, table, extent):
        pass

    def load_from_sql(self, sql):
        pass

    def write_fc(self, fc):
        """Write a feature collection to the database
        """
        pass
