'''
Created on Jan 16, 2018

@author: rmartinez
'''

from madmex.management.base import AntaresBaseCommand

import logging


logger = logging.getLogger(__name__)

class Command(AntaresBaseCommand):
    help = '''
Command that calculates statistics on values of a raster within the zones of a vector dataset. 

--------------
Example usage:
--------------

Not implemented yet.
# 
''' 
    def add_arguments(self, parser):
        '''
        Requires a raster file and a vector shapefile.
        '''
        parser.add_argument('--raster', nargs=1, help='Path to raster data.')
        parser.add_argument('--shapefile', nargs=1, help='Path to shapefile data.')

    def handle(self, **options):
        '''

        '''
        raster = options['raster'][0]
        shape  = options['shapefile'][0]
        logger.info('Raster file : %s ' % raster)
        logger.info('Shapefile : %s' % shape)
            
            