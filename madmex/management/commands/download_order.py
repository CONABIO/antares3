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
antares download_order --order_ids xxx@xxx-04302019-111111-111 xxx@xxx-04302019-111111-112 xxx@xxx-04302019-111111-113
'''
    def add_arguments(self, parser):
        parser.add_argument('-order_ids', '--order_ids',
                            type=str,
                            nargs='*',
                            default=None,
                            help='List of order ids to be downloaded')
        
    def handle(self, *args, **options):
        order_ids = options['order_ids']
        client = EspaApi()

        def dl_order(qs):
            for order in qs:
                logger.info(order.order_id)
                payload = client.get_list_order(order.order_id)
                for image in payload[order.order_id]:
                    if image['product_dload_url']:
                        logger.info('Download %s' % image['product_dload_url'])
                        aware_download(image['product_dload_url'], TEMP_DIR)
                    else:
                        logger.info('Skipping bad file')
                order.downloaded = True
                order.save()

        if order_ids == None:
            qs = Order.objects.filter(downloaded=False)
            dl_order(qs) 
        else:
            for order_id in order_ids:
                qs = Order.objects.filter(downloaded=False, order_id=order_id)
                dl_order(qs) 

