#!/usr/bin/env python

"""
Author: Loic Dutrieux
Date: 2018-04-03
Purpose: Retrieve and display parameters of an implemented segmentation algorithm
"""
from importlib import import_module


from madmex.management.base import AntaresBaseCommand

from madmex.util import pprint_args
import madmex.segmentation as seg_module
import pkgutil
import inspect

class Command(AntaresBaseCommand):
    help = """
Helper command line to retrieve and display available models and their parameters

    - Run the command line without arguments to retrieve the list of implemented segmentation algorithms
    - Run the command with the name of an algorithm to retrieve the exposed parameter of that algorithm

--------------
Example usage:
--------------
# Get the list of implemented segmentation algorithms
antares segment_params

# Get the list of available parameters for the slic segmentation algorithm
antares segment_params slic
"""
    def add_arguments(self, parser):
        parser.add_argument('segmentation',
                            type=str,
                            nargs='?',
                            default=None,
                            help='Name of the segmentation algorithm from which parameters should be retrieved')

    def handle(self, *args, **options):
        segmentation = options['segmentation']

        # No model argument provided. Print a list of implemented models
        if segmentation is None:
            print('{:<10}{:<75}'.format('Algorithm', 'description'))
            print('{:<10}{:<75}'.format('--------', '---------------'))
            for _, algo_name, _ in pkgutil.iter_modules(seg_module.__path__):
                module = import_module('madmex.segmentation.%s' % algo_name)
                # Get first line of docstring
                ds = inspect.getdoc(module.Segmentation).split('\n')[0]
                row = '{:<10}{:<75}'.format(algo_name, ds)
                print(row)

        else:
            # Load model class
            try:
                module = import_module('madmex.segmentation.%s' % segmentation)
                Segmentation = module.Segmentation
            except ImportError as e:
                raise ValueError('Invalid segmentation argument')

            pprint_args(Segmentation, ['array', 'affine', 'crs'])
