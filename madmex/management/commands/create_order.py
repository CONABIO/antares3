'''
Created on Dec 19, 2017

@author: agutierrez
'''

import json
import logging
import re

from django.contrib.gis.geos.polygon import Polygon

from madmex.management.base import AntaresBaseCommand
from madmex.models import Country, Footprint, Region, Order
from madmex.util.remote import UsgsApi, EspaApi


logger = logging.getLogger(__name__)

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
        parser.add_argument('--shape', nargs=1, help='The name of the shape to use in the database.')
        parser.add_argument('--start-date', nargs=1, help='Date to start the query, inclusive.')
        parser.add_argument('--end-date', nargs=1, help='Date to end the query, inclusive.')
        parser.add_argument('--landsat', nargs=1, help='Landsat mission.')

    def handle(self, **options):
        '''This method takes a given shape names and queries the usgs api for available scenes.
        
        Using two api clients for the usgs and espa we query for a given shape and create an order
        to download the landsat scenes for a specific temporal window.
        '''
        usgs_client = UsgsApi()
        usgs_client.login()

        start_date = options['start_date'][0]
        end_date = options['end_date'][0]
        landsat = int(options['landsat'][0])
        shape_name = options['shape'][0]

        espa_client = EspaApi()

        logger.info(shape_name)
        try:
            shape_object = Country.objects.get(name=shape_name)
            logger.info('Country %s was loaded.' % shape_name)
        except:
            try:
                shape_object = Region.objects.get(name=shape_name)
                logger.info('Region %s was loaded.' % shape_name)
            except:
                shape_object = None

        if shape_object:
            extent = shape_object.the_geom.extent

            if landsat == 8:
                collection_usgs = 'LANDSAT_8_C1'
                collection_espa = 'olitirs8_collection'
                collection_regex = '^lc08_{1}\\w{4}_{1}[0-9]{6}_{1}[0-9]{8}_{1}[0-9]{8}_{1}[0-9]{2}_{1}\\w{2}$'
            elif landsat == 7:
                collection_usgs = 'LANDSAT_ETM_C1'
                collection_espa = 'etm7_collection'
                collection_regex = '^le07_{1}\\w{4}_{1}[0-9]{6}_{1}[0-9]{8}_{1}[0-9]{8}_{1}[0-9]{2}_{1}\\w{2}$'
            elif landsat == 5:
                collection_usgs = 'LANDSAT_TM_C1'
                collection_espa = 'tm5_collection'
                collection_regex = '^lt05_{1}\\w{4}_{1}[0-9]{6}_{1}[0-9]{8}_{1}[0-9]{8}_{1}[0-9]{2}_{1}\\w{2}$'

            data = usgs_client.search(extent, collection_usgs, start_date=start_date, end_date=end_date).get('data')

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
                        if scene_extent.intersects(shape_object.the_geom) and re.match(collection_regex, entity_id.lower()):
                            interest.append(entity_id)
                            footprint = Footprint(name=entity_id, the_geom=scene_extent)
                            footprint.save()
            print(json.dumps(interest, indent=4))
            data = espa_client.order(collection_espa, interest, products)
            if data.get('status') == 'ordered':
                logger.info('The order was posted with id: %s' % data.get('orderid'))
                order = Order(user=espa_client.username, order_id=data.get('orderid'), downloaded=False)
                order.save()
            else:
                logger.info(json.dumps(data, indent=4))
        else:
            logger.info('No shape with the name %s was found in the database.' % shape_name)
