'''
Created on Jan 9, 2018

@author: agutierrez
'''
import logging

from madmex.management.base import AntaresBaseCommand
from madmex.models import Order
from madmex.settings import TEMP_DIR
from madmex.util.local import aware_download
from madmex.util.remote import EspaApi


logger = logging.getLogger(__name__)

class Command(AntaresBaseCommand):
    '''
    classdocs
    '''

    def add_arguments(self, parser):
        '''
        Just queries for the name to greet.
        '''

    def handle(self, **options):
        logger.info('Hello world!')
        
        client = EspaApi()
        
        for order in Order.objects.filter(downloaded=False):
            
            #logger.info(order.order_id)
            
            payload = client.get_list_order(order.order_id)
            
            for image in payload[order.order_id]:
                logger.info('Download %s' % image['product_dload_url'])
                aware_download(image['product_dload_url'], TEMP_DIR)
            
            order.downloaded = True
            order.save()