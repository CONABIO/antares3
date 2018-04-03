#!/usr/bin/env python

"""
Author: Loic Dutrieux
Date: 2018-04-03
Purpose: Retrieve and display parameters of an implemented model
"""
from importlib import import_module


from madmex.management.base import AntaresBaseCommand

from madmex.util import pprint_args

class Command(AntaresBaseCommand):
    help = """
Helper command line to retrieve and display the parameters of an implemented model

--------------
Example usage:
--------------
# Random forest example
antares model_params rf
"""
    def add_arguments(self, parser):
        parser.add_argument('model',
                            type=str,
                            help='Name of the model from which parameters should be retrieved')

    def handle(self, *args, **options):
        model = options['model']

        # Load model class
        try:
            module = import_module('madmex.modeling.supervised.%s' % model)
            Model = module.Model
        except ImportError as e:
            raise ValueError('Invalid model argument')

        pprint_args(Model, ['categorical_features'])
