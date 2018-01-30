#!/usr/bin/env python

"""
Author: Loic Dutrieux
Date: 2018-01-30
Purpose: Apply a recipe to generate an intermediary dataset indexed in the datacube
"""
from importlib import import_module
import os
import logging
from datetime import datetime

import dask
import dask.multiprocessing
dask.set_options(get=dask.multiprocessing.get)

from madmex.management.base import AntaresBaseCommand

from madmex.indexing import add_product, add_dataset, metadict_from_netcdf
from madmex.util import yaml_to_dict, mid_date


logger = logging.getLogger(__name__)

class Command(AntaresBaseCommand):
    help = """

--------------
Example usage:
--------------
# Apply madmex_001 recipe (The datacube must contain the ls8_espa_mexico and srtm_cgiar_mexico products)
python madmex.py apply_recipe -recipe madmex_001 -b 2016-01-01 -e 2016-12-31 -lat 19 23 -long -106 -101 --name madmex_001_jalisco_2016
"""
    def add_arguments(self, parser):
        # Recipe is a positional argument
        parser.add_argument('-recipe', '--recipe',
                            type=str,
                            required=True,
                            help='Name of the recipe to apply to the dataset. The recipe must exist in madmex.recipes and the required products must be available in the datacube deployment.')
        parser.add_argument('-b', '--begin',
                            type=str,
                            required=True,
                            help='Begin date used for temporal reduction')
        parser.add_argument('-e', '--end',
                            type=str,
                            required=True,
                            help='End date used for temporal reduction')
        parser.add_argument('-lat', '--lat',
                            type=float,
                            nargs=2,
                            required=True,
                            help='minimum and maximum latitude of the bounding box over which the recipe should be applied')
        parser.add_argument('-long', '--long',
                            type=float,
                            nargs=2,
                            required=True,
                            help='minimum and maximum longitude of the bounding box over which the recipe should be applied')
        parser.add_argument('-name', '--name',
                            type=str,
                            required=True,
                            help='Name under which the product should be referenced in the datacube')
        parser.add_argument('-chunk', '--chunk_size',
                            type=int,
                            required=False,
                            help='Dask chunk size (in x and y dimensions) to use for distributed processing')
        parser.set_defaults(chunk_size=2000)

    def handle(self, *args, **options):
        # TODO: Make this path more dynamic. MAybe with a variable defined in .env
        path = os.path.expanduser('~/datacube_ingest/recipes/')
        if not os.path.exists(path):
            os.makedirs(path)
        filename = os.path.join(path, '%s.nc' % options['name'])
        # Import recipe
        try:
            mod = import_module('madmex.recipes.%s' % options['recipe'])
        except ImportError as e:
            raise ValueError('Selected recipe does not exist')
        # Apply the recipe
        lat = tuple(options['lat'])
        long = tuple(options['long'])
        begin = datetime.strptime(options['begin'], '%Y-%m-%d')
        end = datetime.strptime(options['end'], '%Y-%m-%d')
        time = (begin, end)
        dask_chunks = {'x': options['chunk_size'],
                       'y': options['chunk_size']}
        mod.run(x=long, y=lat, time=time, dask_chunks=dask_chunks,
                nc_filename=filename)
        # Prepare data for product indexing
        yaml_file = os.path.expanduser(os.path.join('~/.config/madmex/indexing',
                                                    '%s.yaml' % options['recipe']))
        product_description = yaml_to_dict(yaml_file)
        center_dt = mid_date(begin, end)
        metadict = metadict_from_netcdf(file=filename, description=product_description,
                                        center_dt=center_dt, from_dt=begin,
                                        to_dt=end, algorithm=options['recipe'])
        # Add product
        pr, dt = add_product(product_description, options['name'])
        # Add dataset
        add_dataset(pr=pr, dt=dt, metadict=metadict)


