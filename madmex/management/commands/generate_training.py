'''
Created on Apr 27, 2018

@author: agutierrez
'''

import logging

import fiona
import rasterio
from rasterio.features import shapes
from shapely.geometry.geo import shape, mapping
import shapely.wkt

from madmex.management.base import AntaresBaseCommand
from madmex.models import Country


logger = logging.getLogger(__name__)

class Command(AntaresBaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--input', nargs=1, help='The name of the raster to process.')
        parser.add_argument('--output', nargs=1, help='The name of the shape to output.')

    def handle(self, *args, **options):
        input_raster = options['input'][0]
        output = options['output'][0]

        mexico = Country.objects.get(name='MEX').the_geom


        with rasterio.open(input_raster) as src:
            water = src.read(1)
        
            water[water < 50] = 255
            water[water <= 100] = 1
            mask = water == 1
            results = []
            i = 0
            my_mexico = shapely.wkt.loads(mexico.wkt)
            logger.debug('Simplifying country shape.')
            my_mexico = my_mexico.simplify(0.01, preserve_topology=False)
            for s in shapes(water, mask=mask, transform=src.transform):
                my_object = shape(s[0])
                
                if(my_object.intersects(my_mexico)):
                    i = i + 1
                    results.append({'properties': {'raster_val': 29}, 'geometry': mapping(my_object.intersection(my_mexico))})
                    logger.debug('%s shapes processed.', i)
            with fiona.open(output,
                            'w',
                            driver='ESRI Shapefile',
                            crs=src.crs,
                            schema={'properties': [('raster_val', 'int')],
                        'geometry': 'Polygon'}) as dst:
                dst.writerecords(tuple(results))
