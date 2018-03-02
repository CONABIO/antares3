#!/usr/bin/env python

"""
Author: Loic Dutrieux
Date: 2018-03-01
Purpose: Run pixel based prediction using a model previously trained with model_fit
"""
import os
import logging

from dask.distributed import Client, LocalCluster
from datacube.api import GridWorkflow
import datacube
import numpy as np

from madmex.management.base import AntaresBaseCommand

from madmex.wrappers import predict_pixel_tile

logger = logging.getLogger(__name__)

class Command(AntaresBaseCommand):
    help = """
Run pixel based prediction using a previously trained model stored in the database, and write the outputs to geotiff.
One raster file per tile covered by the selected spatial extent is produced.

--------------
Example usage:
--------------
# Predict using a random forest model trained against chips jalisco for product rf_int_landsat_madmex_001_jalisco_2017_jalisco_chips
python madmex.py model_predict -lat 19 23 -long -106 -101 -p landsat_madmex_001_jalisco_2017_2 -id rf_int_landsat_madmex_001_jalisco_2017_jalisco_chips -type rf -dir /home/madmex_user/datacube_ingest/lc_jalisco/
"""
    def add_arguments(self, parser):
        parser.add_argument('-p', '--product',
                            type=str,
                            required=True,
                            help=('Name of the datacube product on which prediction should be ran.'
                                  'Must have the same variables than the product on which the model was trained.'))
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
        parser.add_argument('-id', '--model_id',
                            type=str,
                            required=True,
                            help='Unique model identifier under which the model is registered in the database. Note that this model must have been trained against a numeric variable')
        parser.add_argument('-type', '--model_type',
                            type=str,
                            required=True,
                            help='Type of model that was previously trained (e.g.: rf). TODO: Redundant, find a way around that')
        parser.add_argument('-dir', '--out_dir',
                            type=str,
                            required=True,
                            help='Directory where output files should be written')

    def handle(self, *args, **options):
        # Unpack variables
        product = options['product']
        model_id = options['model_id']
        model_type = options['model_type']
        lat = tuple(options['lat'])
        long = tuple(options['long'])
        out_dir = options['out_dir']

        # Create output dir if does not exist
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        # GridWorkflow object
        dc = datacube.Datacube()
        gwf = GridWorkflow(dc.index, product=product)
        tile_dict = gwf.list_cells(product=product, x=long, y=lat)
        # Iterable (dictionary view (analog to list of tuples))
        iterable = tile_dict.items()

        # Start cluster and run 
        client = Client()
        C = client.map(predict_pixel_tile,
                       iterable, **{'gwf': gwf,
                                    'model_id': model_id,
                                    'model': model_type,
                                    'outdir': out_dir})
        filename_list = client.gather(C)
        print(filename_list)

