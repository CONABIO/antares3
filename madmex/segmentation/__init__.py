"""Spatial segmentation module"""

import abc
import json
import gc
import os

from affine import Affine
import numpy as np
import fiona
import boto3
from rasterio import features
from shapely.geometry import shape, mapping
from django.contrib.gis.geos.geometry import GEOSGeometry
from datacube.utils.geometry import CRS, GeoBox

from madmex.settings import TEMP_DIR
from madmex.util.spatial import feature_transform
from madmex.models import PredictObject
from madmex.util import chunk, s3


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

    def polygonize(self):
        """Transform the raster result of a segmentation to a feature collection

        Return:
            list: The feature collection resulting from the segmentation
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
                "geometry": mapping(shape(feature[0]).buffer(0)),
                "properties": {
                    "id": feature[1]
                }
            }
            return fc_out
        return [to_feature(x) for x in geom_collection]

    def to_shapefile(self, filename, fc=None, bucket=None):
        """Write the result of the segmentation to a ESRI Shapefile file

        Args:
            filename (str): File name (use full path when writing to filesystem)
                and basename when writing to s3 bucket
            fc (dict): Feature collection with one property who's name must be
                id. Typically the return of the ``polygonize()`` method.
                Can be ``None``, in which case, it is generated on the fly
            bucket (string): Optional name of s3 bucket to write the shapefile

        Return:
            str: The function is used for its side effect of writing a feature
            collection to file, however, it also returns the path to the written file
        """
        if fc is None:
            fc = self.polygonize()
        crs = from_string(self.crs)
        schema = {'geometry': 'Polygon',
                  'properties': {'id': 'int'}}
        if bucket is None:
            with fiona.open(filename, 'w',
                            driver='ESRI Shapefile',
                            schema=schema,
                            crs=crs) as dst:
                for feature in fc:
                    dst.write(feature)
        else:
            filename = s3.write_shapefile(bucket=bucket, fc=fc, schema=schema,
                                          crs=crs)
        return filename

    def save(self, filename, fc=None, bucket=None):
        """Write the result of a segmentation to disk or an S3 bucket if specified

        Also references the file path and extent in the antares database

        Args:
            filename (str): Output file name (must end with shp)
            fc (dict): Feature collection with one property who's name must be
                id. Typically the return of the ``polygonize()`` method.
                Can be ``None``, in which case, it is generated on the fly
            bucket (str): Optional name of an S3 bucket where to write the file 

        Returns:
            str: Used for its side effect of writting a file to filesystem or S3
            and indexing it in the database. Also returns the filename
        """
        geom = GEOSGeometry(self.geobox.extent.wkt)
        # TODO: Generate segmentation_information object
        shp_path = self.to_shapefile(filename=filename, fc=fc, bucket=bucket)
        PredictObject.objects.get_or_create(path=shp_path,
                                            the_geom=geom,
                                            segmentation_information=meta_object)
        return filename

