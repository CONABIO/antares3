#!/usr/bin/env python

"""
Author: Loic Dutrieux
Date: 2018-02-20
Purpose: Fit a statistical model to a datacube product
"""
from importlib import import_module
import os
import logging
from datetime import datetime

from dask.distributed import Client, LocalCluster
import numpy as np

from madmex.management.base import AntaresBaseCommand

from madmex.indexing import add_product_from_yaml, add_dataset, metadict_from_netcdf
from madmex.util import yaml_to_dict, mid_date, parser_extra_args
from madmex.recipes import RECIPES
from madmex.wrappers import extract_tile_db, gwf_query
from madmex.util.datacube import var_to_ind

logger = logging.getLogger(__name__)

class Command(AntaresBaseCommand):
    help = """
Command line for training a statistical model over a given extent using:
    - A training set of geometries with attributes stored in the database
    - A datacube product
    - One of the models implemented in madmex.modeling

The steps of the process are for each tile of the datacube product to:
    - Load the data as an xarray Dataset
    - Query and load the corresponding training geometries from the database
    - Perform data extraction and spatial aggregation for the geometries overlay
All extracted data are then concatenated and used to train a statistical model. The model is then
saved to the database

--------------
Example usage:
--------------
# Extract data for an area covering more or less Jalisco and fit a random forest model to the extracted data
antares model_fit -model rf -p landsat_madmex_001_jalisco_2017 -t chips_jalisco -lat 19 23 -long -106 -101 --name rf_landsat_madmex_001_jalisco_2017 -sp mean

# With extra args passed to the random forest object constructor, use region name instead of lat long bounding box
antares model_fit -model rf -p landsat_madmex_001_jalisco_2017_2 -t jalisco_chips --region Jalisco --name rf_landsat_madmex_001_jalisco_2017_jalisco_chips -sp mean -extra n_estimators=60 n_jobs=15
"""
    def add_arguments(self, parser):
        parser.add_argument('-model', '--model',
                            type=str,
                            required=True,
                            help='Name of the model to apply to the dataset')
        parser.add_argument('-p', '--product',
                            type=str,
                            required=True,
                            help='Name of the datacube product to use for model fitting')
        parser.add_argument('-t', '--training',
                            type=str,
                            required=True,
                            help='Training data database identifier')
        parser.add_argument('-lat', '--lat',
                            type=float,
                            nargs=2,
                            default=None,
                            help='minimum and maximum latitude of the bounding box over which the model should be trained')
        parser.add_argument('-long', '--long',
                            type=float,
                            nargs=2,
                            default=None,
                            help='minimum and maximum longitude of the bounding box over which the model should be trained')
        parser.add_argument('-region', '--region',
                            type=str,
                            default=None,
                            help=('Name of the region over which the recipe should be applied. The geometry of the region should be present '
                                  'in the madmex-region or the madmex-country table of the database (Overrides lat and long when present) '
                                  'Use ISO country code for country name'))
        parser.add_argument('-sample', '--sample',
                            type=float,
                            default=0.2,
                            help='Proportion of the training data to use. Must be float between 0 and 1. A random sampling of the training objects is performed (defaults to 0.2).')
        parser.add_argument('-name', '--name',
                            type=str,
                            required=True,
                            help='Name under which the produced model should be referenced in the database')
        parser.add_argument('-sp', '--spatial_aggregation',
                            type=str,
                            required=False,
                            default='mean',
                            help='Function to use for spatially aggregating the pixels over the training geometries (defaults to mean)')
        parser.add_argument('-categorical_variables', '--categorical_variables',
                            type=str,
                            nargs='*',
                            default=None,
                            help='List of categorical variables to be encoded using One Hot Encoding before model fit')
        parser.add_argument('-extra', '--extra_kwargs',
                            type=str,
                            nargs='*',
                            help='''
Additional named arguments passed to the selected model class constructor. These arguments have
to be passed in the form of key=value pairs. e.g.: model_fit ... -extra arg1=12 arg2=median
To consult the exposed arguments for each model, use the "model_params" command line''')

    def handle(self, *args, **options):
        # Unpack variables
        product = options['product']
        model = options['model']
        name = options['name']
        training = options['training']
        sp = options['spatial_aggregation']
        kwargs = parser_extra_args(options['extra_kwargs'])
        categorical_variables = options['categorical_variables']
        sample = options['sample']

        # Prepare encoding of categorical variables if any specified
        if categorical_variables is not None:
            kwargs.update(categorical_features=var_to_ind(categorical_variables))

        # Load model class
        try:
            module = import_module('madmex.modeling.supervised.%s' % model)
            Model = module.Model
        except ImportError as e:
            raise ValueError('Invalid model argument')

        # datacube query
        gwf_kwargs = { k: options[k] for k in ['product', 'lat', 'long', 'region']}
        gwf, iterable = gwf_query(**gwf_kwargs)

        # Start cluster and run 
        client = Client()
        C = client.map(extract_tile_db,
                       iterable, **{'gwf': gwf,
                                    'sp': sp,
                                    'training_set': training,
                                    'sample': sample})
        arr_list = client.gather(C)

        print('Completed extraction of training data from %d tiles' % len(arr_list))

        # Zip list of predictors, target into two lists
        X_list, y_list = zip(*arr_list)

        # Filter Nones
        X_list = [x for x in X_list if x is not None]
        y_list = [x for x in y_list if x is not None]

        # Concatenate the lists
        X = np.concatenate(X_list)
        y = np.concatenate(y_list)

        print("Fitting %s model for %d observations" % (model, y.shape[0]))

        # Fit model
        mod = Model(**kwargs)
        mod.fit(X, y)
        # Write the fitted model to the database
        mod.to_db(name=name, recipe=product, training_set=training)

