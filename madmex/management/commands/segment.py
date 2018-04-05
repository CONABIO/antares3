#!/usr/bin/env python

"""
Author: Loic Dutrieux
Date: 2018-03-22
Purpose: Run segmentation on a datacube product and write the output to the database
"""
from importlib import import_module
import os
import logging
import json

from dask.distributed import Client, LocalCluster

from madmex.management.base import AntaresBaseCommand

from madmex.util import parser_extra_args
from madmex.wrappers import gwf_query, segment
from madmex.models import SegmentationInformation

logger = logging.getLogger(__name__)

class Command(AntaresBaseCommand):
    help = """
Command line for running segmentation over a given extent using

--------------
Example usage:
--------------
# Run BIS segmentation
antares segment --algorithm slic -n landsat_slic_test_2017 -p landsat_madmex_001_jalisco_2017_2 -r Jalisco -b green_mean red_mean ndvi_mean nir_mean swir1_mean swir2_mean --datasource landsat8 --year 2017 -extra compactness=0.01 n_segments=300000
"""
    def add_arguments(self, parser):
        parser.add_argument('-a', '--algorithm',
                            type=str,
                            required=True,
                            help=('Name of the segmentation algorithm to use. The list of implemented segmentation algorithms '
                                  'can be retrieved using the antares segmentation_params command line'))
        parser.add_argument('-b', '--bands',
                            type=str,
                            default=None,
                            nargs='*',
                            help='Optional subset of bands of the product to use for running the segmentation. All bands are used if left empty')
        parser.add_argument('-n', '--name',
                            type=str,
                            required=True,
                            help='Name under which the segmentation results should be registered in the database')
        parser.add_argument('-d', '--datasource',
                            type=str,
                            default='',
                            help='Name of the datasource used for the segmentation (e.g. landsat, sentinel, ...)')
        parser.add_argument('-y', '--year',
                            type=str,
                            default='',
                            help='Year of the input data. Can be a string like January_2017')
        parser.add_argument('-p', '--product',
                            type=str,
                            required=True,
                            help='Name of the datacube product to use')
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
        parser.add_argument('-extra', '--extra_kwargs',
                            type=str,
                            default='',
                            nargs='*',
                            help='''
Additional named arguments passed to the selected segmentation class constructor. These arguments have
to be passed in the form of key=value pairs. e.g.: antares segment ... -extra arg1=12 arg2=0.2
The list of parameters corresponding to every implemented segmentation algorithm can be retrieved
using the antares segment_params command line''')

    def handle(self, *args, **options):
        # Unpack variables
        product = options['product']
        algorithm = options['algorithm']
        extra_args = parser_extra_args(options['extra_kwargs'])
        bands = options['bands']
        datasource = options['datasource']
        year = options['year']
        name = options['name']

        # Build segmentation meta object
        meta, _ = SegmentationInformation.objects.get_or_create(
            algorithm=algorithm, datasource=datasource,
            parameters=json.dumps(extra_args),
            datasource_year=year,
            name=name,
        )

        # datacube query
        gwf_kwargs = { k: options[k] for k in ['product', 'lat', 'long', 'region']}
        gwf, iterable = gwf_query(**gwf_kwargs)

        # Start cluster and run 
        client = Client()
        C = client.map(segment,
                       iterable, **{'gwf': gwf,
                                    'algorithm': algorithm,
                                    'segmentation_meta': meta,
                                    'band_list': bands,
                                    'extra_args': extra_args})
        result = client.gather(C)

        print('Successfully ran segmentation on %d tiles' % sum(result))
        print('%d tiles failed' % result.count(False))
