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

from madmex.management.base import AntaresBaseCommand

from madmex.indexing import add_product_from_yaml, add_dataset, metadict_from_netcdf
from madmex.util import yaml_to_dict, mid_date
from madmex.recipes import RECIPES

logger = logging.getLogger(__name__)

class Command(AntaresBaseCommand):
    help = """

--------------
Example usage:
--------------
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

    def handle(self, *args, **options):
        # Unpack variables
        product = options['product']
        model = options['model']
        training = options['name']
        sp = options['spatial_aggregation']
        lat = tuple(options['lat'])
        long = tuple(options['long'])

        # Load model class
        try:
            module = import_module('madmex.model.supervised.%s' % model)
            from module import Model
        except ImportError as e:
            raise ValueError('Invalid model argument')

        # Fitting function to iterate over 'iterable'
        # Must take 
        def fun(tile, gwf, training, sp):
            """FUnction to extract data under trining geometries for a given tile

            Meant to be called within a dask.distributed.Cluster.map() over a list of tiles
            returned by GridWorkflow.list_cells

            Args:
                tile: Datacube tile as returned by GridWorkflow.list_cells()
                gwf: GridWorkflow object
                training: Identifier to locate the training data in the database
                sp: Spatial aggregation function

            Returns:
                A numpy array (or is it two?)
            """
            # Load tile as Dataset
            xr_dataset = gwf.load(tile[1])
            # Query the training geometries fitting into the extent of xr_dataset
            # Overlay geometries and xr_dataset and perform extraction combined with spatial aggregation
            # Return the extracted array (or a list of two arrays?)

        # GridWorkflow object
        dc = datacube.Datacube()
        gwf = GridWorkflow(dc.index, product=product)
        tile_dict = gwf.list_cells(product=product, x=long, y=lat)
        # Iterable (dictionary view (analog to list of tuples))
        iterable = tile_dict.items()

        # Start cluster and run 
        client = Client()
        C = client.map(fun, iterable, **{'gwf': gwf,
                                         'training': training,
                                         'sp': sp})
        arr_list = client.gather(C)

        # Merge the list of arrays into a single array
        X, y = np.concatenate(...)
        # Instantiate Model class
        m = Model()
        # Fit the model
        m.fit(X, y)
        # Write the fitted model to the database

