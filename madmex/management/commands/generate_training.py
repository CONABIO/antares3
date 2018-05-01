'''
Created on Apr 27, 2018

@author: agutierrez
'''

import logging

from django.contrib.gis.geos.geometry import GEOSGeometry
import fiona
import pyproj
import rasterio
from rasterio.features import shapes
from shapely.ftools import partial
from shapely.geometry.geo import shape, mapping
from shapely.ops import transform
import shapely.wkt

from madmex.management.base import AntaresBaseCommand
from madmex.models import Country, TrainObject, Tag, TrainClassification
from madmex.util.local import basename


logger = logging.getLogger(__name__)

def extract_water_training_data(filename, country_shape):
    base = basename(filename)
    with rasterio.open(filename) as src:
        water = src.read(1)
    
        water[water < 90] = 255
        water[water <= 100] = 1
        mask = water == 1
        i = 0
        
        
        object_list = []
        
        
        
        is_same_proj = src.crs['init'].lower() == 'EPSG:4326'.lower()
        
        if is_same_proj:
            print('Same projection.')
        else:
            print('Other projection.')
            project = partial(
                pyproj.transform,
                pyproj.Proj(src.crs),
                pyproj.Proj(init='EPSG:4326'))
        
        for s in shapes(water, mask=mask, transform=src.transform):
            my_object = shape(s[0])
            
            if(my_object.intersects(country_shape)):
                i = i + 1
                
                intersected_object = my_object.intersection(country_shape)
                #logger.debug('%s shapes processed.', i)
                if not is_same_proj:
                    intersected_object = transform(project, intersected_object)
                object_list.append(TrainObject(the_geom = GEOSGeometry(intersected_object.wkt),
                                    filename=base,
                                    creation_year=2018))
                
        logger.info('Total for %s: %s', base, i)
                
        TrainObject.objects.bulk_create(object_list)
        
        water_tag_id = Tag.objects.get(value='agua').id
        train_classification_objects = []
        for obj in object_list:
            train_classification_objects.append(TrainClassification(train_object=obj,
                                                       predict_tag_id=water_tag_id,
                                                       interpret_tag_id=water_tag_id,
                                                       training_set='Global_Surface_Water'.lower()))
        TrainClassification.objects.bulk_create(train_classification_objects)


class Command(AntaresBaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--input', nargs='*', help='The name of the raster to process.')

    def handle(self, *args, **options):
        input_raster = options['input']
        
        
        
        mexico = Country.objects.get(name='MEX').the_geom
        my_mexico = shapely.wkt.loads(mexico.wkt)
        logger.debug('Simplifying country shape.')
        my_mexico = my_mexico.simplify(0.01, preserve_topology=False)
        
        for raster in input_raster:
            extract_water_training_data(raster, my_mexico)