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

from dask.distributed import Client, LocalCluster

from madmex.management.base import AntaresBaseCommand

from madmex.indexing import add_product_from_yaml, add_dataset, metadict_from_netcdf
from madmex.util import yaml_to_dict, mid_date
from madmex.recipes import RECIPES
from madmex.wrappers import gwf_query
from madmex.settings import INGESTION_PATH

logger = logging.getLogger(__name__)

class Command(AntaresBaseCommand):
    help = """
Apply an existing 'recipe' to an ingested collection or a list of ingested collections in the datacube.
A new ingested collection is created every time this command line is ran. The same recipe cannot be ran twice over the same
area.

Data are processed in parallel using dask distributed

Available recipes are:
    - landsat_8_madmex_001: Temporal metrics (min, max, mean, std) of Landsat bands and ndvi combined with terrain metrics (elevation, slope and aspect)
    - landsat_8_ndvi_mean: Simple ndvi temporal mean

See docstring in madmex/recipes/__init__.py for instructions on how to add new recipes to the system

--------------
Example usage:
--------------
# Apply landsat_8_madmex_001 recipe (The datacube must contain the ls8_espa_mexico and srtm_cgiar_mexico products)
antares apply_recipe -recipe landsat_8_madmex_001 -b 2016-01-01 -e 2016-12-31 -lat 19 23 -long -106 -101 --name landsat_8_madmex_001_jalisco_2016

# Apply landsat_8_ndvi_mean recipe (The datacube must contain the ls8_espa_mexico)
antares apply_recipe -recipe landsat_8_ndvi_mean -b 2017-01-01 -e 2017-12-31 --region Jalisco --name landsat_ndvi_jalisco_2017

# Apply landsat_8_madmex_002 recipe (The datacube must contain the ls8_espa_mexico)
antares apply_recipe -recipe landsat_8_madmex_002 -b 2017-01-01 -e 2017-12-31 --region Jalisco --name landsat_8_madmex_002_jalisco_2017

# Apply sentinel 20m 001 recipe (The datacube must contain the s2_20m_mexico dataset)
antares apply_recipe -recipe s2_20m_001 -b 2017-01-01 -e 2017-12-31 -region Jalisco --name s2_001_jalisco_2017_0
"""
    def add_arguments(self, parser):
        # Recipe is a positional argument
        parser.add_argument('-recipe', '--recipe',
                            type=str,
                            required=True,
                            help='Name of the recipe to apply to the dataset. The recipe must exist in madmex.recipes and the required products must be available in the datacube deployment.')
        parser.add_argument('-b', '--begin',
                            type=str,
                            default=None,
                            help='Begin date used for temporal reduction')
        parser.add_argument('-e', '--end',
                            type=str,
                            default=None,
                            help='End date used for temporal reduction')
        parser.add_argument('-lat', '--lat',
                            type=float,
                            nargs=2,
                            default=None,
                            help='minimum and maximum latitude of the bounding box over which the recipe should be applied')
        parser.add_argument('-long', '--long',
                            type=float,
                            nargs=2,
                            default=None,
                            help='minimum and maximum longitude of the bounding box over which the recipe should be applied')
        parser.add_argument('-region', '--region',
                            type=str,
                            default=None,
                            help=('Name of the region over which the recipe should be applied. The geometry of the region should be present '
                                  'in the madmex-region or the madmex-country table of the database (Overrides lat and long when present) '
                                  'Use ISO country code for country name'))
        parser.add_argument('-name', '--name',
                            type=str,
                            required=True,
                            help='Name under which the product should be referenced in the datacube')
        parser.add_argument('-sc', '--scheduler',
                            type=str,
                            default=None,
                            help='Path to file with scheduler information (usually called scheduler.json)')

    def handle(self, *args, **options):
        path = os.path.join(INGESTION_PATH, 'recipes', options['name'])
        if not os.path.exists(path):
            os.makedirs(path)
        # Prepare a few variables
        try:
            recipe_meta = RECIPES[options['recipe']]
        except KeyError:
            raise ValueError('Selected recipe does not exist')
        product = recipe_meta['product']
        fun = recipe_meta['fun']
        yaml_file = recipe_meta['config_file']
        begin = datetime.strptime(options['begin'], '%Y-%m-%d')
        end = datetime.strptime(options['end'], '%Y-%m-%d')
        time = (begin, end)
        center_dt = mid_date(begin, end)
        scheduler_file = options['scheduler']

        # database query
        gwf_kwargs = { k: options[k] for k in ['lat', 'long', 'region', 'begin', 'end']}
        gwf_kwargs.update(product=product)
        iterable = gwf_query(**gwf_kwargs)

        # Start cluster and run 
        client = Client(scheduler_file=scheduler_file)
        client.restart()
        C = client.map(fun, iterable,
                       pure=False,
                       **{'center_dt': center_dt,
                          'path': path})
        nc_list = client.gather(C)
        n_tiles = len([x for x in nc_list if x is not None])
        logger.info('Processing done, %d tiles written to disk' % n_tiles)

        # Add product
        product_description = yaml_to_dict(yaml_file)
        pr, dt = add_product_from_yaml(yaml_file, options['name'])
        # Function to run on the list of filenames returned by Client.map()
        def index_nc_file(nc):
            """Helper function with tons of variables taken from the local environment
            """
            try:
                print("Adding %s to datacube database" % nc)
                metadict = metadict_from_netcdf(file=nc, description=product_description,
                                                center_dt=center_dt, from_dt=begin,
                                                to_dt=end, algorithm=options['recipe'])
                add_dataset(pr=pr, dt=dt, metadict=metadict, file=nc)
            except Exception as e:
                pass

        [index_nc_file(x) for x in nc_list]


