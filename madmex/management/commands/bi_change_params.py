#!/usr/bin/env python

"""
Author: Loic Dutrieux
Date: 2018-06-30
Purpose: Retrieve and display parameters of an implemented bi-temporal change
    detection method
"""
from importlib import import_module

from madmex.management.base import AntaresBaseCommand

from madmex.util import pprint_args
import madmex.lcc.bitemporal as bitemporal
import pkgutil
import inspect

class Command(AntaresBaseCommand):
    help = """
Helper command line to retrieve and display available bi-temporal change methods and their parameters

    - Run the command line without arguments to retrieve the list of implemented methods
    - Run the command with the name of an implemented method/algorithm to retrieve the
      parameter of that given method

--------------
Example usage:
--------------
# Get the list of implemented methods
antares bi_change_params

# Get the list of available parameters for the distance change method
antares bi_change_params distance
"""
    def add_arguments(self, parser):
        parser.add_argument('method',
                            type=str,
                            nargs='?',
                            default=None,
                            help='Name of the change detection method from which parameters should be retrieved')

    def handle(self, *args, **options):
        method = options['method']

        # No method argument provided. Print a list of implemented methods
        if method is None:
            print('{:<10}{:<75}'.format('Method', 'description'))
            print('{:<10}{:<75}'.format('--------', '---------------'))
            for _, modname, _ in pkgutil.iter_modules(bitemporal.__path__):
                module = import_module('madmex.lcc.bitemporal.%s' % modname)
                # Get first line of docstring
                ds = inspect.getdoc(module.BiChange).split('\n')[0]
                row = '{:<10}{:<75}'.format(modname, ds)
                print(row)

        else:
            # Load method class
            try:
                module = import_module('madmex.lcc.bitemporal.%s' % method)
                BiChange = module.BiChange
            except ImportError as e:
                raise ValueError('Invalid method argument')

            pprint_args(BiChange, ['affine', 'crs'])
