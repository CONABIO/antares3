'''
Created on Jan 17, 2018

@author: agutierrez
'''

import json
import logging
import os

from django.contrib.gis.geos.geometry import GEOSGeometry
from django.contrib.gis.geos.polygon import Polygon
from fiona import transform
import geojson
import numpy
import rasterio
from rasterio.features import rasterize
import scipy.ndimage
from shapely.geometry.geo import shape
import xarray

from madmex.management.base import AntaresBaseCommand
from madmex.model.supervised import rf
from madmex.models import Object
from madmex.orm.queries import example_query
from madmex.settings import TEMP_DIR


logger = logging.getLogger(__name__)

class Command(AntaresBaseCommand):
    def handle(self, **options):
        print('hello world')
        '''
        from sklearn_xarray.data import load_digits_dataarray
        from sklearn_xarray import Target
        X = load_digits_dataarray()
        y = Target(coord='digit')(X)
        model_path = TEMP_DIR
        print(model_path)
        my_model = rf.Model()
        my_model.fit(X,y)
        print('Model has been persisted.') 
        my_model.save(model_path)
        del(my_model)
        my_model = rf.Model()
        my_model.load(model_path)
        print('Model has been loaded.')
        print('Model score.')
        print(my_model.score(X,y))
        '''
        
        
        
        xr_array = xarray.open_dataset('/LUSTRE/MADMEX/datacube_ingest/LS8_espa/mexico/LS8_espa_12_-16_20171221172432088372.nc')
        
        
        print(xr_array)
        

        
        plygn_wkt = xr_array.attrs['geospatial_bounds']
        
        
        GEOSGeometry(plygn_wkt)
        
        shapes = [(json.loads(obj.the_geom.geojson), p + 2) for p, obj in enumerate(Object.objects.filter(the_geom__intersects=GEOSGeometry(plygn_wkt)))]
        
        print('the number if objects is: %s' % len(shapes))
        
        #my_str = json.loads(shapes[0].geojson)
        
        #my_shape = shape(my_str)
        
        #print(my_str)
        
        
        
        
        
        
        ulx = xr_array.attrs['geospatial_lon_min']
        
        uly = xr_array.attrs['geospatial_lat_max']
        
        brx = xr_array.attrs['geospatial_lon_max']
        
        bry = xr_array.attrs['geospatial_lat_min']
        
        
        
        from affine import Affine
        
        size = 3334
        
        shifted_affine = Affine((brx - ulx) / size, 0, ulx, 0, (bry-uly) / size, uly)
        
        
        print(shifted_affine)
        mask = rasterize(shapes, out_shape=(size,size), transform = shifted_affine)
        
        test_file_name = os.path.join(TEMP_DIR, 'new.tif')
        
        print(test_file_name)

        with rasterio.open(test_file_name, 'w', driver='GTiff', height=mask.shape[0],
                   width=mask.shape[1], count=1, dtype=mask.dtype,
                   crs='+proj=latlong', transform=shifted_affine) as dst:
            dst.write(mask, 1)
        print(mask.shape)
        
        
        print(scipy.ndimage.measurements.mean(xr_array.green.values.reshape(size,size), mask, numpy.unique(mask)))
        print(scipy.ndimage.measurements.minimum(xr_array.green.values.reshape(size,size), mask, numpy.unique(mask)))
        print(scipy.ndimage.measurements.maximum(xr_array.green.values.reshape(size,size), mask, numpy.unique(mask)))
        print(scipy.ndimage.measurements.sum(xr_array.green.values.reshape(size,size), mask, numpy.unique(mask)))
        print(scipy.ndimage.measurements.standard_deviation(xr_array.green.values.reshape(size,size), mask, numpy.unique(mask)))
        print(scipy.ndimage.measurements.variance(xr_array.green.values.reshape(size,size), mask, numpy.unique(mask)))
        print(scipy.ndimage.measurements.median(xr_array.green.values.reshape(size,size), mask, numpy.unique(mask)))
        
        xr_array
        
        #print(numpy.unique(result, return_counts=True))
        
        
        
        import math
        Polygon()
        for obj in Object.objects.all()[:10] :
            print(obj.the_geom.transform(3785, clone=True))
        
        '''
        for obj in Object.objects.filter(the_geom__intersects=GEOSGeometry(plygn_wkt)):
            print(obj)
        '''
        
        
        '''
        for row in example_query():
            print(row)
        '''
        
        