#!/usr/bin/env python

"""
Author: Loic Dutrieux
Date: 2018-07-05
Purpose: Run change detection on a pair of tiles, classify the result and write
     the feature collection to the database
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
Command line for running a change detection algorithm over a given extent and write the resulting
change polygons to the database

TODO: Add more details about the process:
    - Detect 'spectral' changes
    - Filter clumps with a size rule
    - Assign before/after labels using existing classifications
    - Discard objects with same before and after label
    - Write to the database
--------------
Example usage:
--------------
# Run simple euclidean distance based change detection
antares detect_change --prod_pre landsat_jalisco_2015 \
        --prod_post landsat_jalisco_2018 \
        --lc_pre jalisco_2015 \
        --lc_post jalisco_2018 \
        --algorithm distance \
        --name jalisco_2015_2018 \
        --bands ndvi_mean ndmi_mean \
        --mmu 5000 \
        --region Jalisco

"""
    def add_arguments(self, parser):
        parser.add_argument('-a', '--algorithm',
                            type=str,
                            required=True,
                            help=('Name of the change detection algorithm to use. The list of implemented segmentation algorithms '
                                  'can be retrieved using the antares bi_change_params command line'))
        parser.add_argument('-b', '--bands',
                            type=str,
                            default=None,
                            nargs='*',
                            help='Optional subset of bands of the product to use to detect changes. All bands are used if left empty')
        parser.add_argument('-n', '--name',
                            type=str,
                            required=True,
                            help='Name under which the change detction results should be registered in the database')
        parser.add_argument('-p_pre', '--product_pre',
                            type=str,
                            required=True,
                            help='Name of the anterior datacube product to use')
        parser.add_argument('-p_post', '--product_post',
                            type=str,
                            required=True,
                            help='Name of the posterior datacube product to use')
        parser.add_argument('-lc_pre', '--lc_pre',
                            type=str,
                            required=True,
                            help='Name of the anterior land cover map to use')
        parser.add_argument('-lc_post', '--lc_post',
                            type=str,
                            required=True,
                            help='Name of the posterior land cover map to use')
        parser.add_argument('-lat', '--lat',
                            type=float,
                            nargs=2,
                            default=None,
                            help='minimum and maximum latitude of the bounding box over which changes have to be detected')
        parser.add_argument('-long', '--long',
                            type=float,
                            nargs=2,
                            default=None,
                            help='minimum and maximum longitude of the bounding box over which changes have to be detected')
        parser.add_argument('-r', '--region',
                            type=str,
                            default=None,
                            help=('Name of the region over which changes should be detected. The geometry of the region should be present '
                                  'in the madmex-region or the madmex-country table of the database (Overrides lat and long when present) '
                                  'Use ISO country code for country name'))
        parser.add_argument('--no-label-filter', dest='filter_label',
                            action='store_false',
                            help='Do not discard change polygon with the same pre and post label')
        parser.add_argument('-mmu', '--mmu',
                            default=None,
                            type=float,
                            help=('Optional minimum size of clusters of contiguous change pixels, in the unit of the products crs. '
                                 'Can be left empty in which case all pixels detected as change are kept.'))
        parser.add_argument('-extra', '--extra_kwargs',
                            type=str,
                            default='',
                            nargs='*',
                            help='''
Additional named arguments passed to the selected BiChange class constructor. These arguments have
to be passed in the form of key=value pairs. e.g.: antares detect_change ... -extra arg1=12 arg2=0.2
The list of parameters corresponding to every implemented change detection algorithm can be retrieved
using the antares bi_change_params command line''')
        parser.add_argument('-sc', '--scheduler',
                            type=str,
                            default=None,
                            help='Path to file with scheduler information (usually called scheduler.json)')

    def handle(self, *args, **options):
        # Unpack variables
        algorithm = options['algorithm']
        extra_args = parser_extra_args(options['extra_kwargs'])
        bands = options['bands']
        name = options['name']
        scheduler_file = options['scheduler']

        # Build segmentation meta object
        meta, _ = ChangeInformation.objects.get_or_create(
        )

        # Build gwf_kwargs, send a query for both products, combine the dict and generate iterable
        gwf_kwargs = { k: options[k] for k in ['lat', 'long', 'region']}
        pre_dict = gwf_query(product_pre, view=False, **gwf_kwargs)
        post_dict = gwf_query(product_post, view=False, **gwf_kwargs)
        iterable = join_dicts(pre_dict, post_dict).items()

        # Start cluster and run 
        client = Client(scheduler_file=scheduler_file)
        client.restart()
        C = client.map(segment,
                       iterable,
                       pure=False,
                       **{'algorithm': algorithm})
        result = client.gather(C)

        print('Successfully ran change detection on %d tiles' % sum(result))
        print('%d tiles failed' % result.count(False))
