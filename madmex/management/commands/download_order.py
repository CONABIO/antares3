'''
Created on Jan 9, 2018

@author: agutierrez
'''
import logging

from madmex.api.remote import EspaApi
from madmex.management.base import AntaresBaseCommand
from madmex.models import Order
from madmex.settings import TEMP_DIR
from madmex.util.local import aware_download


logger = logging.getLogger(__name__)

class Command(AntaresBaseCommand):
    help = '''
Command line option to download scenes using the ESPA api. An order must be placed in
advanced using the create_order command. When an order is placed, ESPA will take some
time to process the order. When it is ready an email confirmation is sent. This command
looks into the database for orders that had not been downloaded yet. It then parses the
contents of the order.

--------------
Example usage:
--------------
# Downloads the orders found in the database that have not been downloaded yet.
python madmex.py download_order
'''
    def handle(self, **options):
        client = EspaApi()
        for order in Order.objects.filter(downloaded=False):
            logger.info(order.order_id)
            payload = client.get_list_order(order.order_id)
            for image in payload[order.order_id]:
                logger.info('Download %s' % image['product_dload_url'])
                aware_download(image['product_dload_url'], TEMP_DIR)
            order.downloaded = True
            order.save()