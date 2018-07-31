#!/usr/bin/env python

"""
Author: Loic Dutrieux
Date: 2018-07-23
Purpose: Generates a raster mask for a given country
"""
import json
from math import ceil, floor
import itertools
import os

from madmex.management.base import AntaresBaseCommand
from madmex.models import Country
from django.db import connection
import rasterio
from rasterio import features
from affine import Affine
import numpy as np
import dask.array as da
from madmex.util import s3, parsers
from madmex.util.spatial import grid_gen


class Command(AntaresBaseCommand):
    help = """
Generate a tiled raster mask for a given country

Retrieve the country geometry from the antares database and rasterize it and write it to
files following the tiling scheme defined by the -tile argument.
Can also write directly to a s3 bucket

--------------
Example usage:
--------------
# Generate a land mask for mexico, 50m resolution with 5000*5000 pixels tiles
antares make_country_mask --country mex -res 100 -tile 5000 --path /LUSTRE/MADMEX/tasks/2018_tasks/sandbox/

# Same but writing the output directly to an s3 bucket
antares make_country_mask --country mex -res 100 -tile 5000 --path sandbox --bucket conabio-s3-oregon
"""
    def add_arguments(self, parser):
        parser.add_argument('-country', '--country',
                            type=str,
                            required=True,
                            help='Iso code of a country whose coutour geometry has been ingested in the antares database')
        parser.add_argument('-res', '--resolution',
                            type=float,
                            required=True,
                            help=('Resolution in meters of the generated mask. Note that it is internally transformed to degrees using the '
                                  'approximation 1 degree = 110 km'))
        parser.add_argument('-tile', '--tile_size',
                            type=int,
                            required=True,
                            help='Size of generated square tiles in pixels')
        parser.add_argument('-b', '--bucket',
                            type=str,
                            default=None,
                            help='Optional name of an s3 bucket to write the generated tiles')
        parser.add_argument('-p', '--path',
                            type=str,
                            required=True,
                            help='Path where the tiles should be written. Either in a filesystem of within the specified bucket')


    def handle(self, *args, **options):
        country = options['country']
        resolution = options['resolution'] / 110000
        tile_size = options['tile_size']
        bucket = options['bucket']
        path = options['path']

        # Retrieve data from database (country extent and POLYGON)
        query_0 = 'SELECT st_extent(the_geom) FROM public.madmex_country WHERE name = %s;'
        query_1 = 'SELECT st_asgeojson(the_geom, 6) FROM public.madmex_country WHERE name = %s;'
        with connection.cursor() as c:
            c.execute(query_0, [country.upper()])
            bbox = c.fetchone()
            c.execute(query_1, [country.upper()])
            geom = c.fetchone()
        extent = parsers.postgis_box_parser(bbox[0])
        geom = json.loads(geom[0])

        # Generate the binary rasters (1 for inside country, 0 for outside)
        grid_generator = grid_gen(extent, resolution, tile_size,
                                  prefix='land_mask_tile')
        for shape, aff, filename in grid_generator:
            arr = features.rasterize([(geom, 1)], out_shape=shape, transform=aff,
                                     dtype=np.uint8)
            meta = {'driver': 'GTiff',
                    'height': shape[0],
                    'width': shape[1],
                    'count': 1,
                    'transform': aff,
                    'dtype': rasterio.uint8,
                    'crs': '+proj=longlat',
                    'compress': 'lzw'}
            fp = os.path.join(path, filename)
            if bucket is not None:
                s3.write_raster(bucket, fp, arr, **meta)
            else:
                with rasterio.open(fp, 'w', **meta) as dst:
                    dst.write(arr, 1)
