#!/usr/bin/env python

"""
Author: Loic Dutrieux
Date: 2018-03-01
Purpose: Run pixel based prediction using a model previously trained with model_fit
"""
import os
import logging

from dask.distributed import Client, LocalCluster
import numpy as np

from madmex.management.base import AntaresBaseCommand

from madmex.wrappers import predict_pixel_tile, gwf_query

logger = logging.getLogger(__name__)

class Command(AntaresBaseCommand):
    help = """
Run pixel based prediction using a previously trained model stored in the database, and write the outputs to geotiff.
One raster file per tile covered by the selected spatial extent is produced.

--------------
Example usage:
--------------
# Predict using a random forest model trained against chips jalisco for product rf_int_landsat_madmex_001_jalisco_2017_jalisco_chips
antares model_predict --region Jalisco -p landsat_madmex_001_jalisco_2017_2 -id rf_int_landsat_madmex_001_jalisco_2017_jalisco_chips -dir /home/madmex_user/datacube_ingest/lc_jalisco/
"""
    def add_arguments(self, parser):
        parser.add_argument('-p', '--product',
                            type=str,
                            required=True,
                            help=('Name of the datacube product on which prediction should be ran. '
                                  'Must have the same variables than the product on which the model was trained.'))
        parser.add_argument('-lat', '--lat',
                            type=float,
                            nargs=2,
                            default=None,
                            help='minimum and maximum latitude of the bounding box over which data will be predicted')
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
        parser.add_argument('-id', '--model_id',
                            type=str,
                            required=True,
                            help='Unique model identifier under which the model is registered in the database. Note that this model must have been trained against a numeric variable')
        parser.add_argument('-dir', '--out_dir',
                            type=str,
                            required=True,
                            help='Directory where output files should be written')

    def handle(self, *args, **options):
        # Unpack variables
        model_id = options['model_id']
        out_dir = options['out_dir']

        # Create output dir if does not exist
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        # datacube query
        gwf_kwargs = { k: options[k] for k in ['product', 'lat', 'long', 'region']}
        iterable = gwf_query(**gwf_kwargs)

        # Start cluster and run 
        client = Client()
        client.restart()
        C = client.map(predict_pixel_tile,
                       iterable, **{'model_id': model_id,
                                    'outdir': out_dir})
        filename_list = client.gather(C)
        print(filename_list)

