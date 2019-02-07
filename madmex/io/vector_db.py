from . import AntaresDb
from madmex.overlay.conversions import train_object_to_feature, predict_object_to_feature
from madmex.models import TrainClassification, PredictObject
from math import floor

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

# TODO: Get rid of this class
class VectorDb(AntaresDb):
    """Query, read and write geometries between python's memory and the database"""
    def load_training_from_dataset(self, dataset, training_set, sample=0.2):
        """Retieves training data from the database based on intersection with an xr Dataset

        Args:
            dataset (xarray.Dataset): Typical Dataset object generated using one of
                the datacube load method (GridWorkflow or Datacube clases)
            training_set (str): Name of the training set identifier to select the right
                training data
            sample (float): Float between 0 and 1. Proportion of intersection geometry to sample.
                Performs random sampling of the geometries

        Return:
            list: A feature collection reprojected to the CRS of the xarray Dataset
        """
        geobox = dataset.geobox
        crs = str(dataset.crs)
        poly = Polygon.from_geobox(geobox)
        query_set = TrainClassification.objects.filter(train_object__the_geom__contained=poly,
                                                       training_set=training_set).prefetch_related('train_object', 'interpret_tag')
        if  0 < sample < 1:
            nsample = floor(query_set.count() * sample)
            query_set = query_set.order_by('?')[:nsample]

        fc = (train_object_to_feature(x, crs) for x in query_set)
        return fc

def load_segmentation_from_dataset(geoarray, segmentation_name):
    """Retrieve a path in s3 segmentation intersecting with a geoarray

    Args:
        geoarray (xarray.Dataset): Typical Dataset object generated using one of
            the datacube load method (GridWorkflow or Datacube clases)
        segmentation_name (str): Unique segmentation identifier

    Return:
        location of segmentation in s3 (str)
    """
    poly = Polygon.from_ewkt(geoarray.geobox.extent.wkt)
    query_set = PredictObject.objects.filter(the_geom__intersects=poly,
                                         segmentation_information__name=segmentation_name)
    
    return query_set[0].path

