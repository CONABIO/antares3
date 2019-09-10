'''
Created on Dec 19, 2017

@author: agutierrez
'''

import json
import logging
import re

from django.contrib.gis.geos.polygon import Polygon

from madmex.api.remote import UsgsApi, EspaApi
from madmex.management.base import AntaresBaseCommand
from madmex.models import Country, Footprint, Region, Order


logger = logging.getLogger(__name__)

def point_from_object(coords):
    return (coords.get('longitude'), coords.get('latitude'))

def int_or_str(value):
    try:
        return int(value)
    except:
        return value
    
class Command(AntaresBaseCommand):
    help = '''
Command that places an order into the ESPA system matching the given criteria. ESPA
will take some time to process the order and it will send confirmation e-mails both when
the order is placed, and when the order is ready. Once the order is ready, the download_order
command must be used to download the scenes.

--------------
Example usage:
--------------
# Downloads the Landsat 8 scenes that intersect the state of Jalisco and where taken during 2017.
antares create_order --region 'Jalisco'  --start-date '2017-01-01' --end-date '2017-12-31' --landsat 8

# It is posible to search by Landsat tile, under the rule 'path0row'. For instance:
antares create_order --region 22049  --start-date '2001-01-01' --end-date '2002-12-31' --landsat 5 --max-cloud-cover 30

# Show only the Landsat 5 scenes that intersect the state of Jalisco and where taken during 2005.
antares create_order --region 'Jalisco'  --start-date '2005-01-01' --end-date '2005-12-31' --landsat 5 --no-order
'''
    def add_arguments(self, parser):
        '''
        Just queries for the name to greet.
        '''
        parser.add_argument('--region', type=int_or_str, help='The name of the region to use in the database.')
        parser.add_argument('--start-date', help='Date to start the query, inclusive.')
        parser.add_argument('--end-date', help='Date to end the query, inclusive.')
        parser.add_argument('--landsat',
                            type=int,
                            help='Landsat mission.')
        parser.add_argument('--max-cloud-cover',
                            type=int,
                            default=100,
                            help='Maximum amount of cloud cover.')
        parser.add_argument('--no-order',
                            dest='order',
                            action='store_false',
                            help='Show only the scenes found.')
        parser.set_defaults(order=True)

    def handle(self, **options):
        '''This method takes a given region names and queries the usgs api for available scenes.

        Using two api clients for the usgs and espa we query for a given region and create an order
        to download the landsat scenes for a specific temporal window.
        '''
        usgs_client = UsgsApi()
        usgs_client.login()

        start_date = options['start_date']
        end_date = options['end_date']
        landsat = options['landsat']
        region = options['region']
        cloud_cover = options['max_cloud_cover']
        order = options['order']

        espa_client = EspaApi()

        logger.info(region)
        
        region = int_or_str(region)
        if isinstance(region, int):
            region_object = Footprint.objects.get(name=region)
            logger.info('Footprint %s was loaded.' % region)
        elif isinstance(region, str):
            try:
                region_object = Country.objects.get(name=region)
                logger.info('Country %s was loaded.' % region)
            except:
                try:
                    region_object = Region.objects.get(name=region)
                    logger.info('Region %s was loaded.' % region)
                except:
                    region_object = None

        if region_object:
            extent = region_object.the_geom.extent

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

            data = usgs_client.search(extent, collection_usgs, start_date=start_date, end_date=end_date, max_cloud_cover=cloud_cover).get('data')

            products = ['sr', 'pixel_qa']
            interest = []
            if data:
                results= data.get('results')
                if results:
                    for scene in results:
                        coords = tuple(point_from_object(scene.get(coord)) for coord in ['lowerLeftCoordinate', 'upperLeftCoordinate', 'upperRightCoordinate', 'lowerRightCoordinate', 'lowerLeftCoordinate'])
                        scene_extent = Polygon(coords)
                        entity_id = scene.get('displayId')                        
                        if isinstance(region, int):
                            if str(region) in entity_id:
                                interest.append(entity_id)
                        elif scene_extent.intersects(region_object.the_geom):                        
                            interest.append(entity_id)                            
            if order == True:
                data = espa_client.order(collection_espa, interest, products)
                if data.get('status') == 'ordered':
                    logger.info('The order was posted with id: %s' % data.get('orderid'))
                    order = Order(user=espa_client.username, order_id=data.get('orderid'), downloaded=False)
                    order.save()
                else:
                    logger.info(json.dumps(data, indent=4))
            else:
                logger.info("%s scenes found in %s" %(len(interest), region))
                logger.info(json.dumps(interest, indent=4))
                logger.info("Delete '--no-order' to make the request to USGS.")
        else:
            logger.info('No region with the name %s was found in the database.' % region)
