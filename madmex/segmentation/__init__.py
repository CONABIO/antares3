"""Spatial segmentation module"""

import abc
import json
import gc
from affine import Affine
import numpy as np
from rasterio import features
from django.contrib.gis.geos.geometry import GEOSGeometry
from datacube.utils.geometry import CRS, GeoBox

from madmex.util.spatial import feature_transform
from madmex.models import PredictObject
from madmex.util import chunk


class BaseSegmentation(metaclass=abc.ABCMeta):
    """
    Parent class implementing generic methods related to running spatial segmentation
    algorithms on raster data, converting input and output data and interacting with the
    database.
    """
    def __init__(self, array, affine, crs):
        """Parent class to run spatial segmentation

        Args:
            array (numpy.array): A 3 dimensional numpy array. Dimention order should
                be (x, y, bands)
            affine (affine.Affine): Affine transform
            crs (str): Proj4 string corresponding to the array's CRS
        """
        self.array = array
        self.affine = affine
        self.crs = crs
        self.fc = None
        self.segments_array = None
        self.algorithm = None

    @classmethod
    def from_geoarray(cls, geoarray, **kwargs):
        """Instantiate class from a geoarray (xarray read with datacube.load)

        Args:
            geoarray (xarray.Dataset): a Dataset with crs and affine attribute. Typically
                coming from a call to Datacube.load or GridWorkflow.load
            **kwargs: Additional arguments. Allow children class to set algorithm specific
                parameters during instantiation
        """
        array = geoarray.squeeze().to_array().values
        array = np.moveaxis(array, 0, 2)
        affine = Affine(*list(geoarray.affine)[0:6])
        crs = geoarray.crs._crs.ExportToProj4()
        return cls(array=array, affine=affine, crs=crs, **kwargs)

    @abc.abstractmethod
    def segment(self):
        """Run segmentation
        """
        pass

    @property
    def geobox(self):
        """Object geobox

        Returns:
            datacube.utils.geometry.GeoBox
        """
        return GeoBox(width=self.array.shape[1], height=self.array.shape[0],
                      affine=self.affine, crs=CRS(self.crs))

    def polygonize(self, crs_out="+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs"):
        """Transform the raster result of a segmentation to a feature collection

        Args:
            crs_out (proj4): The coordinate reference system of the feature collection
                produced. Defaults to longlat, can be None if no reprojection is needed
        """
        if self.segments_array is None:
            raise ValueError("self.segments_array is None, you must run segment before this method")
        # Use rasterio.features.shapes to generate a geometries collection from the
        # segmented raster
        geom_collection = features.shapes(self.segments_array.astype(np.uint16),
                                          transform=self.affine)
        # Make it a valid featurecollection
        def to_feature(feature):
            """Tranforms the results of rasterio.feature.shape to a feature"""
            fc_out = {
                "type": "Feature",
                "geometry": {
                    "type": feature[0]['type'],
                    "coordinates": feature[0]['coordinates']
                },
                "properties": {
                    "id": feature[1]
                }
            }
            return fc_out
        fc_out = (to_feature(x) for x in geom_collection)
        if crs_out is not None:
            fc_out = (feature_transform(x, crs_out=crs_out, crs_in=self.crs) for x in fc_out)
        self.fc = fc_out


    def to_db(self, out_file, meta_object):
        """Write the result of a segmentation to the database

        Args:
            meta_object (madmex.models.SegmentationInformation.object): The python mapping
                of a django object containing segmentation metadata information
            out_file (str): Absolute path for segmentation result file in s3

        Example:
            >>> from madmex.models import SegmentationInformation
            >>> from madmex.segmentation.bis import Segmentation

            >>> Seg = Segmentation.from_geoarray(geoarray, compactness=12)
            >>> Seg.segment()
            >>> Seg.polygonize()

            >>> meta = SegmentationInformation(algorithm='bis', datasource='sentinel2',
            >>>                                parameters="{'compactness': 12}",
            >>>                                datasource_year='2018')
            >>> meta.save()
            >>> out_file = 's3://my-segmentation-bucket/shapefile'

            >>> Seg.to_db(out_file, meta)
        """
        if self.fc is None:
            raise ValueError('fc (feature collection) attribute is empty, you must first run the polygonize method')

        geom = GEOSGeometry(self.geobox.extent.wkt)
        filename = out_file + '.shp'
        obj = PredictObject(path=out_file, the_geom=geom, segmentation_information=meta_object)
        PredictObject.objects.bulk_create(obj)
        gc.collect()
    def to_bucket(self, out_file):
        return True
        



