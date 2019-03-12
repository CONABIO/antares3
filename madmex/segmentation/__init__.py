"""Spatial segmentation module"""

import abc
import json
import gc
import fiona
from affine import Affine
import numpy as np
import os
import boto3
from rasterio import features
from django.contrib.gis.geos.geometry import GEOSGeometry
from datacube.utils.geometry import CRS, GeoBox
from madmex.settings import SEGMENTATION_BUCKET
from madmex.util.spatial import feature_transform, geometry_transform
from madmex.models import PredictObject
from madmex.util import chunk
from shapely.geometry import shape, mapping

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
        for feature in fc_out:
            feature['geometry'] = mapping(shape(feature['geometry']).buffer(0))
        if crs_out is not None:
            fc_out = (feature_transform(x, crs_out=crs_out, crs_in=self.crs) for x in fc_out)
        self.fc = fc_out


    def to_db(self, name_file, meta_object):
        """Write the result of a segmentation to the database

        Args:
            name_file (str): file name for segmentation result in s3
            meta_object (madmex.models.SegmentationInformation.object): The python mapping
                of a django object containing segmentation metadata information
            

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
            >>> name_file = 'shapefile'

            >>> Seg.to_db(name_file, meta)
        """
        if self.fc is None:
            raise ValueError('fc (feature collection) attribute is empty, you must first run the polygonize method')

        geom = GEOSGeometry(json.dumps(self.geobox.geographic_extent.json))
        SEGMENTATION_BUCKET = os.getenv('SEGMENTATION_BUCKET', '')
        filename = name_file + '.shp'
        file_path_in_s3 = 's3://' + SEGMENTATION_BUCKET + '/' + filename
        PredictObject.objects.get_or_create(path=file_path_in_s3, the_geom=geom, segmentation_information=meta_object)
        gc.collect()
    def to_filesystem(self, path, name_file):
        """Write result of a segmentation to filesystem in directory
        Args:
            path (str): absolute path that will have results of segmentation
            name_file (str): file name for segmentation result in s3
        Example:
            >>> from madmex.models import SegmentationInformation
            >>> from madmex.segmentation.bis import Segmentation
            >>> Seg = Segmentation.from_geoarray(geoarray, compactness=12)
            >>> Seg.segment()
            >>> Seg.polygonize() 
            >>> path = '/my_shared_volume/'
            >>> name_file = 'my_segmentation_result'
            >>> Seg.to_filesystem(path, name_file)
        
        """
        schema = {'geometry': 'Polygon',
                  'properties': [('id', 'int')]}
        with fiona.open(path, 'w', layer = name_file,
                        schema=schema,
                        driver='ESRI Shapefile',
                        crs=self.crs) as dst:
            for feature in self.fc:
                dst.write(feature)
        
    def to_bucket(self, path, name_file):
        """Write result of a segmentation to bucket in s3
        Args:
            path (str): absolute path that will have results of segmentation in bucket. In .antares 
                is specified the bucket in s3 for segmentation results                  
            name_file (str): file name for segmentation result in s3
        Example:
            >>> from madmex.models import SegmentationInformation
            >>> from madmex.segmentation.bis import Segmentation
            >>> Seg = Segmentation.from_geoarray(geoarray, compactness=12)
            >>> Seg.segment()
            >>> Seg.polygonize() 
            >>> path = '/my_shared_volume/'
            >>> name_file = 'my_segmentation_result'
            >>> Seg.to_filesystem(path, name_file)
            >>> Seg.to_bucket(path,name_file)
        
        """
        try:
            os.environ['SEGMENTATION_BUCKET']
        except KeyError: 
            print ('Please set the environment variable SEGMENTATION_BUCKET')
            raise KeyError ('Environ variable not set')

        SEGMENTATION_BUCKET = os.getenv('SEGMENTATION_BUCKET', '')
        s3 = boto3.client('s3')
        filename = name_file + '.shp'
        filepath = path + '/' + filename
        s3.upload_file(filepath, SEGMENTATION_BUCKET, filename)
        os.remove(filepath)
        filename = name_file + '.shx'
        filepath = path + '/' + filename
        s3.upload_file(filepath, SEGMENTATION_BUCKET, filename)
        os.remove(filepath)
        filename = name_file + '.cpg'
        filepath = path + '/' + filename
        s3.upload_file(filepath, SEGMENTATION_BUCKET, filename)
        os.remove(filepath)
        filename = name_file + '.dbf'
        filepath = path + '/' + filename
        s3.upload_file(filepath, SEGMENTATION_BUCKET, filename)
        os.remove(filepath)
        filename = name_file + '.prj'
        filepath = path + '/' + filename
        s3.upload_file(filepath, SEGMENTATION_BUCKET, filename)
        os.remove(filepath)
        



