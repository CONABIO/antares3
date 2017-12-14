'''
Created on Dec 12, 2017

@author: agutierrez
'''

import logging
import os

from madmex.management.base import AntaresBaseCommand
from madmex.models import ingest_countries_from_shape
from madmex.settings import TEMP_DIR
from madmex.util import aware_download, extract_zip, aware_make_dir, \
    filter_files_from_folder


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
        url = 'http://thematicmapping.org/downloads/TM_WORLD_BORDERS-0.3.zip'
        filepath = aware_download(url, TEMP_DIR)
        unzipdir = extract_zip(filepath, TEMP_DIR)
        os.listdir(unzipdir)
        shape_name = filter_files_from_folder(unzipdir, regex=r'.*.shp')[0]
        shape_file = os.path.join(unzipdir, shape_name)
        logger.info('This %s shape file will be ingested.' % shape_file)
        ingest_countries_from_shape(shape_file)