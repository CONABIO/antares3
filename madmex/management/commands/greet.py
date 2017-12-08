'''
Created on Dec 7, 2017

@author: agutierrez
'''

import logging

from madmex.management.base import AntaresBaseCommand


logger = logging.getLogger(__name__)

class Command(AntaresBaseCommand):
    '''
    classdocs
    '''
    def add_arguments(self, parser):
        '''
        Just queries for the name to greet.
        '''
        parser.add_argument('--names', nargs='+', help='Name to greet.')

    def handle(self, **options):
        '''
        We retrieve the names given in the command line input and greet
        each one of them.
        '''
        for name in options['names']:
            logger.info('Hello %s from madmex antares3 jojojo!' % name)

