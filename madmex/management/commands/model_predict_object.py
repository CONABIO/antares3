#!/usr/bin/env python

"""
Author: Loic Dutrieux
Date: 2018-03-28
Purpose: Perform object based classification
"""
import os
import logging

from dask.distributed import Client, LocalCluster

from madmex.management.base import AntaresBaseCommand

from madmex.wrappers import gwf_query, predict_object

logger = logging.getLogger(__name__)

class Command(AntaresBaseCommand):
    help = """
Command line for performing object based classification

The following steps must have been performed prior to running this command line.
- Generate an intermediary product by apply a recipe to ingested collections (see apply_recipe command line)
- Train a model (see model_fit command line)
- Perform a segmentation (see segment command line)

--------------
Example usage:
--------------
# Predict land cover over the state of Jalisco using a previously trained model
antares model_predict_object -p landsat_madmex_001_jalisco_2017_2 -m rf_madmex_001_2017_Jalisco_0 -s landsat_slic_test_2017 -r Jalisco -name rf_madmex_001_2017_Jalisco_0
"""
    def add_arguments(self, parser):
        parser.add_argument('-p', '--product',
                            type=str,
                            required=True,
                            help='Name of the datacube to use for prediction')
        parser.add_argument('-m', '--model',
                            type=str,
                            required=True,
                            help='Name under which the trained model is referenced in the database')
        parser.add_argument('-s', '--segmentation',
                            type=str,
                            required=True,
                            help='Name under which the segmentation is referenced in the database')
        parser.add_argument('-n', '--name',
                            type=str,
                            required=True,
                            help='Name under which the classification results should be registered in the database')
        parser.add_argument('-lat', '--lat',
                            type=float,
                            nargs=2,
                            default=None,
                            help='minimum and maximum latitude of the bounding box over which the segmentation should be applied')
        parser.add_argument('-long', '--long',
                            type=float,
                            nargs=2,
                            default=None,
                            help='minimum and maximum longitude of the bounding box over which the segmentation should be applied')
        parser.add_argument('-r', '--region',
                            type=str,
                            default=None,
                            help=('Name of the region over which the segmentation should be applied. The geometry of the region should be present '
                                  'in the madmex-region or the madmex-country table of the database (Overrides lat and long when present) '
                                  'Use ISO country code for country name'))
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
        parser.add_argument('-sc', '--scheduler',
                            type=str,
                            default=None,
                            help='Path to file with scheduler information (usually called scheduler.json)')

    def handle(self, *args, **options):
        # Unpack variables
        name = options['name']
        model = options['model']
        segmentation = options['segmentation']
        spatial_aggregation = options['spatial_aggregation']
        categorical_variables = options['categorical_variables']
        scheduler_file = options['scheduler']

        # datacube query
        gwf_kwargs = { k: options[k] for k in ['product', 'lat', 'long', 'region']}
        iterable = gwf_query(**gwf_kwargs)

        # Start cluster and run 
        client = Client(scheduler_file=scheduler_file)
        client.restart()
        C = client.map(predict_object,
                       iterable,
                       pure=False,
                       **{'model_name': model,
                          'segmentation_name': segmentation,
                          'categorical_variables': categorical_variables,
                          'aggregation': spatial_aggregation,
                          'name': name,
                          })
        result = client.gather(C)

        print('Successfully ran prediction on %d tiles' % sum(result))
        print('%d tiles failed' % result.count(False))
