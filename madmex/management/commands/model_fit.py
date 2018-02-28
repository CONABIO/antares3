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
from datacube.api import GridWorkflow
import datacube
import numpy as np
from sklearn import preprocessing

from madmex.management.base import AntaresBaseCommand

from madmex.indexing import add_product_from_yaml, add_dataset, metadict_from_netcdf
from madmex.util import yaml_to_dict, mid_date, parser_extra_args
from madmex.recipes import RECIPES
from madmex.io.vector_db import VectorDb
from madmex.overlay.extractions import zonal_stats_xarray

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
python madmex.py model_fit -model rf -p landsat_madmex_001_jalisco_2017 -f level_2 -t chips_jalisco -lat 19 23 -long -106 -101 --name rf_landsat_madmex_001_jalisco_2017 -sp mean

# With extra args passed to the random forest object constructor
python madmex.py model_fit -model rf -p landsat_madmex_001_jalisco_2017_2 -f level_2 -t jalisco_chips -lat 19 23 -long -106 -101 --name rf_landsat_madmex_001_jalisco_2017_jalisco_chips -sp mean -extra n_estimators=60 n_jobs=15
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
        parser.add_argument('-f', '--field',
                            type=str,
                            required=True,
                            help='Feature collection property to use for assigning labels')
        parser.add_argument('-lat', '--lat',
                            type=float,
                            nargs=2,
                            required=True,
                            help='minimum and maximum latitude of the bounding box over which the model should be trained')
        parser.add_argument('-long', '--long',
                            type=float,
                            nargs=2,
                            required=True,
                            help='minimum and maximum longitude of the bounding box over which the model should be trained')
        parser.add_argument('-name', '--name',
                            type=str,
                            required=True,
                            help='Name under which the produced model should be referenced in the database')
        parser.add_argument('-sp', '--spatial_aggregation',
                            type=str,
                            required=False,
                            default='mean',
                            help='Function to use for spatially aggregating the pixels over the training geometries')
        parser.add_argument('--encode',
                            action='store_true',
                            help=('Perform numeric encoding of the dependent variable. This is useful when using a character field for later'
                                 'running a pixel based prediction'))
        parser.add_argument('-extra', '--extra_kwargs',
                            type=str,
                            nargs='*',
                            help='''
Additional named arguments passed to the selected model class constructor. These arguments have
to be passed in the form of key=value pairs. e.g.: model_fit ... -extra arg1=12 arg2=median''')

    def handle(self, *args, **options):
        # Unpack variables
        product = options['product']
        model = options['model']
        name = options['name']
        training = options['training']
        field = options['field']
        sp = options['spatial_aggregation']
        lat = tuple(options['lat'])
        long = tuple(options['long'])
        kwargs = parser_extra_args(options['extra_kwargs'])
        encode = options['encode']

        # Load model class
        try:
            module = import_module('madmex.modeling.supervised.%s' % model)
            Model = module.Model
        except ImportError as e:
            raise ValueError('Invalid model argument')

        # Fitting function to iterate over 'iterable'
        # Must take 
        def fun(tile, gwf, field, sp, training_set):
            """FUnction to extract data under trining geometries for a given tile

            Meant to be called within a dask.distributed.Cluster.map() over a list of tiles
            returned by GridWorkflow.list_cells

            Args:
                tile: Datacube tile as returned by GridWorkflow.list_cells()
                gwf: GridWorkflow object
                field (str): Feature collection property to use for assigning labels
                sp: Spatial aggregation function
                training_set (str): Training data identifier (training_set field)

            Returns:
                A list of predictors and target values arrays
            """
            try:
                # Load tile as Dataset
                xr_dataset = gwf.load(tile[1])
                # Query the training geometries fitting into the extent of xr_dataset
                db = VectorDb()
                fc = db.load_training_from_dataset(xr_dataset,
                                                   training_set=training_set)
                # Overlay geometries and xr_dataset and perform extraction combined with spatial aggregation
                extract = zonal_stats_xarray(xr_dataset, fc, field, sp)
                # Return the extracted array (or a list of two arrays?)
                return extract
            except Exception as e:
                return [None, None]

        # GridWorkflow object
        dc = datacube.Datacube()
        gwf = GridWorkflow(dc.index, product=product)
        tile_dict = gwf.list_cells(product=product, x=long, y=lat)
        # Iterable (dictionary view (analog to list of tuples))
        iterable = tile_dict.items()

        # Start cluster and run 
        client = Client()
        C = client.map(fun, iterable, **{'gwf': gwf,
                                         'field': field,
                                         'sp': sp,
                                         'training_set': training})
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

        # Convert str labels to integers
        if encode:
            le = preprocessing.LabelEncoder()
            y = le.fit_transform(y)

        print("Fitting %s model for %d observations" % (model, y.shape[0]))

        # Fit model
        mod = Model(**kwargs)
        mod.fit(X, y)
        # Write the fitted model to the database
        mod.to_db(name=name, recipe=product, training_set=training)

