#!/usr/bin/env python

"""
Author: Loic Dutrieux
Date: 2018-04-03
Purpose: Retrieve and display parameters of an implemented model
"""
from importlib import import_module


from madmex.management.base import AntaresBaseCommand

from madmex.util import pprint_args
import madmex.modeling.supervised as modeling
import pkgutil
import inspect

class Command(AntaresBaseCommand):
    help = """
Helper command line to retrieve and display available models and their parameters

    - Run the command line without arguments to retrieve the list of implemented models
    - Run the command with the name of an implemented model to retrieve the parameter of that given model

--------------
Example usage:
--------------
# Get the list of implemented models
antares model_params

# Get the list of available parameters for the rf model
antares model_params rf
"""
    def add_arguments(self, parser):
        parser.add_argument('model',
                            type=str,
                            nargs='?',
                            default=None,
                            help='Name of the model from which parameters should be retrieved')

    def handle(self, *args, **options):
        model = options['model']

        # No model argument provided. Print a list of implemented models
        if model is None:
            print('{:<10}{:<75}'.format('Model', 'description'))
            print('{:<10}{:<75}'.format('--------', '---------------'))
            for _, modname, _ in pkgutil.iter_modules(modeling.__path__):
                module = import_module('madmex.modeling.supervised.%s' % modname)
                # Get first line of docstring
                ds = inspect.getdoc(module.Model).split('\n')[0]
                row = '{:<10}{:<75}'.format(modname, ds)
                print(row)

        else:
            # Load model class
            try:
                module = import_module('madmex.modeling.supervised.%s' % model)
                Model = module.Model
            except ImportError as e:
                raise ValueError('Invalid model argument')

            pprint_args(Model, ['categorical_features'])
