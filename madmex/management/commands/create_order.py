'''
Created on Dec 19, 2017

@author: agutierrez
'''

import json
import logging
import re

from django.contrib.gis.geos.polygon import Polygon

from madmex.management.base import AntaresBaseCommand
from madmex.models import Country, Footprint
from madmex.util.remote import UsgsApi, EspaApi


logger = logging.getLogger(__name__)

OLI_TIRS_REGEX = '^lc08_{1}\\w{4}_{1}[0-9]{6}_{1}[0-9]{8}_{1}[0-9]{8}_{1}[0-9]{2}_{1}\\w{2}$'

def point_from_object(coords):
    return (coords.get('longitude'), coords.get('latitude'))

class Command(AntaresBaseCommand):
    '''
    classdocs
    '''
    def add_arguments(self, parser):
        '''
        Just queries for the name to greet.
        '''
        parser.add_argument('--shape', nargs='+', help='The name of the shape to use in the database.')

    def handle(self, **options):
        '''This method takes a given shape names and queries the usgs api for available scenes.
        
        Using
        '''
        
        usgs_client = UsgsApi()
        
        usgs_client.login()
        
        
        espa_client = EspaApi()
        
        for shape in options['shape']:
            logger.info(shape)
            country = Country.objects.get(name=shape)
            extent = country.the_geom.extent
            
            collection_usgs = 'LANDSAT_8_C1'
            collection_espa = 'olitirs8_collection'
            
            data = usgs_client.search(extent, collection_usgs, start_date='1986-03-01', end_date='1986-03-31').get('data')
            

            products = ['sr', 'pixel_qa']
            
            interest = []
            
            if data:
                results= data.get('results')
                if results:
                    for scene in results:
                        
                        coords = tuple(point_from_object(scene.get(coord)) for coord in ['lowerLeftCoordinate', 'upperLeftCoordinate', 'upperRightCoordinate', 'lowerRightCoordinate', 'lowerLeftCoordinate'])
                        scene_extent = Polygon(coords)
                        entity_id = scene.get('displayId')
                        # we use the same regular expression that espa uses to filter the names that are valid; otherwise, the order throws an error
                        if scene_extent.intersects(country.the_geom) and re.match(OLI_TIRS_REGEX, entity_id.lower()):
                            in_region = 1
                            interest.append(entity_id)
                            f = Footprint(name=entity_id, the_geom=scene_extent, in_region=in_region)
                            f.save()
            print(json.dumps(interest, indent=4))
            data = espa_client.order(collection_espa, interest, products)
            if data.get('status') == 'ordered':
                logger.info('The order was posted with id: %s' % data.get('orderid'))
            else:          
                logger.info(json.dumps(data, indent=4))