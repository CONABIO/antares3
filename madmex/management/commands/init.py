'''
Created on Dec 12, 2017

@author: agutierrez
'''

import logging

from madmex.management.base import AntaresBaseCommand
from madmex.models import ingest_countries_from_shape
from madmex.settings import TEMP_DIR
from madmex.util import aware_download


logger = logging.getLogger(__name__)

class Command(AntaresBaseCommand):
    '''
    classdocs
    '''
    def add_arguments(self, parser):
        '''
        Just queries for the name to greet.
        '''
        parser.add_argument('--path', nargs=1, help='The path to the shape to be ingested.')

    def handle(self, **options):
        '''
        We retrieve the names given in the command line input and greet
        each one of them.
        '''
        path = 'http://thematicmapping.org/downloads/TM_WORLD_BORDERS-0.3.zip'
        
        aware_download(path, TEMP_DIR)
        logger.debug('The path to the shape is %s to be ingested.' % path)
        #ingest_countries_from_shape(path)

