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
from operator import itemgetter

from dask.distributed import Client, LocalCluster

from madmex.management.base import AntaresBaseCommand

from madmex.indexing import add_product_from_yaml, add_dataset, metadict_from_netcdf
from madmex.util import yaml_to_dict, mid_date, parser_extra_args
from madmex.recipes import RECIPES
from madmex.wrappers import gwf_query
from madmex.settings import INGESTION_PATH
from madmex.util import join_dicts

logger = logging.getLogger(__name__)

class Command(AntaresBaseCommand):
    help = """
Apply an existing 'recipe' to an ingested collection or a list of ingested collections in the datacube.
A new ingested collection is created every time this command line is ran. The same recipe cannot be ran twice over the same
area.

Data are processed in parallel using dask distributed

Available recipes are:
    - landsat_ndvi_mean: Simple ndvi temporal mean
    - landsat_madmex_004: Temporal metrics (mean) of Landsat bands and nd ndmi, ndvi (min,max) combined with terrain metrics (elevation, slope and aspect)
    - s2_20m_001: Temporal metrics (mean) of Sentinel2 20m bands and ndmi, ndvi (min,max) combined with terrain metrics (elevation, slope and aspect)
    - s2_20m_resampled_10m_001: Temporal metrics (mean) of Sentinel2 20m bands resampled to 10m resolution using GridSpec functionality of datacube (same description of s2_20m_001 recipe).
    - s2_10m_scl_ndvi_mean_001: Ndvi of Sentinel2 10m resolution bands
    - s1_2_10m_001: Temporal metrics (mean) of Sentinel2 bands. Right now the recipe is using 2015 data for Sentinel1 bands. For Sentinel2 also nd ndmi, ndvi (min,max) combined with terrain metrics (elevation, slope and aspect) are calculated.


See docstring in madmex/recipes/__init__.py for instructions on how to add new recipes to the system

--------------
Example usage:
--------------
# Apply landsat_madmex_004 recipe (The datacube must contain the ls8_espa_mexico and srtm_cgiar_mexico products)
antares apply_recipe -recipe landsat_madmex_004 -b 2016-01-01 -e 2016-12-31 -lat 19 23 -long -106 -101 --name landsat_madmex_004_jalisco_2016

# Apply landsat_ndvi_mean recipe (The datacube must contain the ls8_espa_mexico)
antares apply_recipe -recipe landsat_ndvi_mean -b 2017-01-01 -e 2017-12-31 --region Jalisco --name landsat_ndvi_jalisco_2017

# Apply landsat_madmex_004 recipe (The datacube must contain the ls8_espa_mexico)
antares apply_recipe -recipe landsat_madmex_004 -b 2017-01-01 -e 2017-12-31 --region Jalisco --name landsat_madmex_004_jalisco_2017

# Apply landsat_madmex_004 recipe with histogram match (The datacube must contain the ls8_espa_mexico)
antares apply_recipe 

# Apply sentinel 20m 001 recipe (The datacube must contain the s2_20m_mexico dataset)
antares apply_recipe -recipe s2_20m_001 -b 2017-01-01 -e 2017-12-31 -region Jalisco --name s2_001_jalisco_2017_0

# Apply sentinel 20m 001 recipe using an user defined GridSpec regular grid (The datacube must contain the s2_20m_mexico dataset, extra arguments help to define GridSpec regular spatial grid)
antares apply_recipe -recipe s2_20m_resampled_10m_001 -b 2017-01-01 -e 2017-12-31 -region Jalisco --name s2_001_jalisco_2017_10_resampled --resolution -10 10 --tilesize 100020 100020 --origin 2426720 977160 --proj4 '+proj=lcc +lat_1=17.5 +lat_2=29.5 +lat_0=12 +lon_0=-102 +x_0=2500000 +y_0=0 +a=6378137 +b=6378136.027241431 +units=m +no_defs'

#Apply sentinel 10m_scl 001 recipe (ndvi)
antares apply_recipe -recipe s2_10m_scl_ndvi_mean_001 -b 2017-01-01 -e 2017-12-31 -region Jalisco --name s2_001_jalisco_2017_10

#Apply s1_2_10m_001 recipe (combination with S2, S1 and terrain)
antares apply_recipe -recipe s1_2_10m_001 -b 2017-01-01 -e 2017-12-31 -region Jalisco --name s1_2_001_jalisco_2017

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
        parser.add_argument('-recipe_reference', '--recipe_reference',
                            type=str,
                            default=None,
                            help='Recipe reference for histogram matching')
        parser.add_argument('--begin_reference',
                            type=str,
                            default=None,
                            help='Begin date for recipe reference in histogram matching')
        parser.add_argument('--end_reference',
                            type=str,
                            default=None,
                            help='End date used for recipe reference in histogram matching')
        parser.add_argument('-name', '--name',
                            type=str,
                            required=True,
                            help='Name under which the product should be referenced in the datacube')
        parser.add_argument('-sc', '--scheduler',
                            type=str,
                            default=None,
                            help='Path to file with scheduler information (usually called scheduler.json)')
        parser.add_argument('-res', '--resolution',
                            type=float,
                            nargs=2,
                            default=None,
                            help='(Y, X) size of each data point in  GridSpec regular spatial grid, in CRS units. Y will usually be negative.')
        parser.add_argument('-tilesize', '--tilesize',
                            type=float,
                            nargs=2,
                            default=None,
                            help='(Y, X) size of each tile, in CRS units')
        parser.add_argument('-origin', '--origin',
                            type=float,
                            nargs=2,
                            default=None,
                            help='(Y, X) coordinates of a corner of the (0,0) tile in CRS units to use in GridSpec regular spatial grid. default is (0.0, 0.0)')
        parser.add_argument('-proj4', '--proj4',
                            type=str,
                            default=None,
                            help='Coordinate System used to define the grid of GridSpec regular spatial grid')

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
        algorithm = options['recipe']
        time = (begin, end)
        center_dt = mid_date(begin, end)
        scheduler_file = options['scheduler']
        recipe_reference = options['recipe_reference']
        begin_reference = options['begin_reference']
        end_reference = options['end_reference']
        # database query
        gwf_kwargs = { k: options[k] for k in ['lat', 'long', 'region', 'begin', 'end', 'resolution', 'tilesize', 'origin', 'proj4']}

        if not isinstance(product, list):
            raise TypeError('Product (defined in madmex.recipes.RECIPES) must be a list')
        dict_list = []
        for prod in product:
            gwf_kwargs.update(product = prod)
            try:
                dict_list.append(gwf_query(**gwf_kwargs, view=False))
            # Exception is in case one of the product hasn't been registered in the datacube
            except Exception as e:
                pass
        iterable = join_dicts(*dict_list, join='full').items()
        # Start cluster and run
        client = Client(scheduler_file=scheduler_file)
        client.restart()
        if recipe_reference is not None and begin_reference is not None and end_reference is not None:
            dict_list_reference = []
            gwf_kwargs_reference = { k: options[k] for k in ['lat', 'long', 'region', 'resolution', 'tilesize', 'origin', 'proj4']}
            gwf_kwargs_reference.update(product = recipe_reference, begin=begin_reference, end=end_reference)
            try:
                dict_list_reference.append(gwf_query(**gwf_kwargs_reference, view=False))
            # Exception is in case one of the product hasn't been registered in the datacube
            except Exception as e:
                pass
            print(gwf_query(**gwf_kwargs_reference, view=False))
            print(join_dicts(*dict_list_reference, join='full').items())
            list_iterable_reference = list(join_dicts(*dict_list_reference, join='full').items())
            list_iterable = list(iterable)
            if len(list_iterable) == len(list_iterable_reference):
                list_iterable_sorted = sorted(list_iterable, key=itemgetter(0))
                list_iterable_reference_sorted = sorted(list_iterable_reference, key=itemgetter(0))
                list_iterable = None
                list_iterable_reference = None
                list_union = [(s,t) for (s,t) in zip(list_iterable_sorted, list_iterable_reference_sorted)]
                C = client.map(fun, list_union,
                               pure=False,
                               **{'center_dt': center_dt,
                                  'path': path,
                                  'histogram_match': True})
            else:
                logger.info('Can not perform histogram match, source and reference lists have different lengths')
                C = None
        else:
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
        def add_dataset_to_db(tup):
            try:
                print("Adding %s to datacube database" % tup[0])
                add_dataset(pr=pr, dt=dt, metadict=tup[1], file=tup[0])
                return True
            except:
                return False
        args = {'description': product_description,
                'center_dt': center_dt,
                'from_dt': begin,
                'to_dt': end,
                'algorithm': algorithm}
        
        client.restart()
        logger.info('Extracting metadata from netcdf files')
        C = client.map(metadict_from_netcdf, nc_list, **args)
        r = client.gather(C)
        
        l_r = [add_dataset_to_db(x) for x in r]
        if False in l_r:
            logger.info('A nc file (or more) failed to written to datacube database')
        else:
            logger.info('Processing done, %d tiles added to datacube database' % n_tiles)
            
        
