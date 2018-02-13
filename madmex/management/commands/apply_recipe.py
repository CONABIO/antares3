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
from datacube.index.postgres._connections import PostgresDb
from datacube.index._api import Index
from datacube.api import GridWorkflow

from madmex.management.base import AntaresBaseCommand

from madmex.indexing import add_product, add_dataset, metadict_from_netcdf
from madmex.util import yaml_to_dict, mid_date
from madmex.recipes import RECIPES


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

    def handle(self, *args, **options):
        try:
            recipe_meta = RECIPES[options['recipe']]
        except KeyError:
            raise ValueError('Selected recipe does not exist')
        product = recipe_meta['product']
        fun = recipe_meta['fun']
        print(fun)
        yaml_file = recipe_meta['config_file']
        # TODO: Make this path more dynamic. MAybe with a variable defined in .env
        path = os.path.expanduser(os.path.join('~/datacube_ingest/recipes/', options['recipe']))
        if not os.path.exists(path):
            os.makedirs(path)
        # Apply the recipe
        lat = tuple(options['lat'])
        long = tuple(options['long'])
        begin = datetime.strptime(options['begin'], '%Y-%m-%d')
        end = datetime.strptime(options['end'], '%Y-%m-%d')
        time = (begin, end)
        # Prepare data for product indexing
        product_description = yaml_to_dict(yaml_file)
        center_dt = mid_date(begin, end)
        # metadict = metadict_from_netcdf(file=filename, description=product_description,
                                        # center_dt=center_dt, from_dt=begin,
                                        # to_dt=end, algorithm=options['recipe'])
        # Add product
        # pr, dt = add_product(product_description, options['name'])
        # Add dataset
        # add_dataset(pr=pr, dt=dt, metadict=metadict)



        # GridWorkflow object
        db = PostgresDb.from_config()
        i = Index(db)
        gwf = GridWorkflow(i, product=product)
        tile_dict = gwf.list_cells(product=product, time=(begin, end),
                                   x=long, y=lat)
        # Iterable (dictionary view (analog to list of tuples))
        iterable = tile_dict.items()
        print(product)

        # Start cluster and run 
        # cluster = LocalCluster(n_workers=n_workers,
                               # threads_per_worker=threads)
        client = Client()
        C = client.map(fun, iterable, **{'gwf': gwf, 'center_dt': center_dt})
        nc_list = client.gather(C)
        print(nc_list)

        # TODO: Index every element of nc_list (might need exception handling for the None)


