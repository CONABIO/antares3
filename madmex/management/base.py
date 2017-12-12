'''
Created on Dec 7, 2017

@author: agutierrez
'''

import logging
import time
from argparse import RawTextHelpFormatter

from django.core.management.base import BaseCommand


logger = logging.getLogger(__name__)


class AntaresBaseCommand(BaseCommand):
    '''
    This class just pretends to be a decorator from django base command to provide feedback
    on how much time does a commandt takes to finish.
    '''
    def create_parser(self, *args, **kwargs):
        """Allow line breaks in command help string
        """
        parser = super(AntaresBaseCommand, self).create_parser(*args, **kwargs)
        parser.formatter_class = RawTextHelpFormatter
        return parser

    def execute(self, *args, **options):
        '''
        Just wrapping a timer around regular execution.
        '''
        logger.debug('Command line arguments: %s' % options)
        start_time = time.time()
        output = BaseCommand.execute(self, *args, **options)
        logger.debug('Command execution is done in %s seconds.' % (time.time() - start_time))
        return output
