#!/usr/bin/env python

"""
Author: Loic Dutrieux
Date: 2018-07-26
Purpose: Rasterizes a vector file
"""
import json
from math import ceil, floor
import itertools
import re
import os

from madmex.management.base import AntaresBaseCommand
from madmex.models import Country
from madmex.util.spatial import get_geom_bbox, feature_transform
from django.db import connection
import rasterio
from rasterio import features
from affine import Affine
import numpy as np
import dask.array as da
from madmex.util import s3
import fiona
from fiona.crs import to_string

def postgis_box_parser(box):
    pattern = re.compile(r'BOX\((-?\d+\.*\d*) (-?\d+\.*\d*),(-?\d+\.*\d*) (-?\d+\.*\d*)\)')
    m = pattern.search(box)
    return [float(x) for x in m.groups()]


def grid_gen(extent, res, size, prefix):
    """Tile generator

    Takes extent, tile size and resolution and returns a generator of
    (shape, transform, filename) tuples

    Args:
        extent (list): List or tuple of extent coordinates in the form
            (xmin, ymin, xmax, ymax)
        res (float): Resolution of the grid to chunk
        size (int): Tile size in number of pixels (nrows == ncols)

    yields:
        tuple: Tuple of (shape, affine, filename)
    """
    nrow_full = ceil((extent[3] - extent[1]) / res)
    ncol_full = ceil((extent[2] - extent[0]) / res)
    ul_lat_iter = np.arange(extent[3], extent[1], -(res * size))
    ul_lon_iter = np.arange(extent[0], extent[2], (res * size))
    nrow_iter, ncol_iter = da.zeros((nrow_full, ncol_full), chunks=(size, size)).chunks
    for i, (row_tup, col_tup) in enumerate(itertools.product(zip(ul_lat_iter, nrow_iter),
                                                             zip(ul_lon_iter, ncol_iter))):
        aff = Affine(res, 0, col_tup[0], 0, -res, row_tup[0])
        size = (row_tup[1], col_tup[1])
        yield (size, aff, '%s_%d.tif' % (prefix, i))


class Command(AntaresBaseCommand):
    help = """
Rasterize a vector file to a desired resolution, projection, tiling scheme and extent

Note the the output rasters (usually several because since tiling is performed) are of type uint8. The
values to rasterize must therefore be of that type too.

--------------
Example usage:
--------------
# Generate a raster of mexican states
wget http://data.biogeo.ucdavis.edu/data/gadm2.8/shp/MEX_adm_shp.zip
unzip -j MEX_adm_shp.zip MEX_adm1* -d .
antares rasterize_vector_file MEX_adm1.shp -res 0.01 -tile 2000 --path /LUSTRE/MADMEX/tasks/2018_tasks/sandbox/ --prefix mex_states_raster --field ID_1

# Reprojecting to a custom crs
antares rasterize_vector_file MEX_adm1.shp -res 1000 -tile 2000 --path /LUSTRE/MADMEX/tasks/2018_tasks/sandbox/ --prefix mex_states_raster_laea --field ID_1 --proj '+proj=laea +lat_0=20 +lon_0=-100'


# Using the ingested geometry of mexico as rasterizing extent
antares rasterize_vector_file MEX_adm1.shp -res 1000 -tile 2000 --path /LUSTRE/MADMEX/tasks/2018_tasks/sandbox/ --prefix mex_states_raster_laea_mex_extent --field ID_1 --proj '+proj=laea +lat_0=20 +lon_0=-100' --country mex
"""
    def add_arguments(self, parser):
        parser.add_argument('input_file',
                            type=str,
                            help='Path of vector file to vectorize. Must be readable by one of fiona\'s suported drivers')
        parser.add_argument('-proj', '--proj',
                            type=str,
                            default=None,
                            help=('Optional proj4 string to set output crs. When left empty the crs of the input vector '
                                  'file is used'))
        parser.add_argument('-country', '--country',
                            type=str,
                            default=None,
                            help=('Optional iso code of a country whose coutour geometry has been ingested in the antares database '
                                  'When specified, the extented of the country is used to set rasterization boundaries'))
        parser.add_argument('-res', '--resolution',
                            type=float,
                            required=True,
                            help=('Resolution in the crs of the input file or in the --proj crs is specified'))
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
        parser.add_argument('-field', '--field',
                            type=str,
                            default=None,
                            help=('Field/property of the vector file to rasterize. When not specified, a binary rasterization '
                                  'is performed (features=1, no-feature=0)'))
        parser.add_argument('-prefix', '--prefix',
                            type=str,
                            required=True,
                            help='The prefix to use for naming the produced files')


    def handle(self, *args, **options):
        input_file = options['input_file']
        country = options['country']
        resolution = options['resolution']
        tile_size = options['tile_size']
        bucket = options['bucket']
        path = options['path']
        proj = options['proj']
        field = options['field']
        prefix = options['prefix']

        # Read the vector file
        with fiona.open(input_file) as src:
            crs = to_string(src.crs)
            fc = list(src)

        # Optionally reproject the feature collection to a specified CRS
        if proj is not None:
            fc = [feature_transform(x, crs_out=proj, crs_in=crs) for x in fc]
            crs = proj

        # Build the iterator using the field specified as argument (can be none, in which case binary rasterization is performed)
        if field is not None:
            shapes_iterator = [(x['geometry'], x['properties'][field]) for x in fc]
        else:
            shapes_iterator = [(x['geometry'], 1) for x in fc]

        # Either retrieve extent from file or from an ingested country geometry
        if country is None:
            bbox_list = (get_geom_bbox(x['geometry']) for x in fc)
            xmin_list, ymin_list, xmax_list, ymax_list = zip(*bbox_list)
            xmin = min(xmin_list)
            ymax  = max(ymax_list)
            xmax = max(xmax_list)
            ymin = min(ymin_list)
            extent = (xmin, ymin, xmax, ymax)
        else:
            query = 'SELECT st_extent(st_transform(the_geom, %s)) FROM public.madmex_country WHERE name = %s;'
            with connection.cursor() as c:
                c.execute(query, [crs, country.upper()])
                bbox = c.fetchone()
            extent = postgis_box_parser(bbox[0])

        # Generate the tiles and write them either to filesystem or to s3 bucket
        grid_generator = grid_gen(extent, resolution, tile_size, prefix)
        # Generate the rasters
        for shape, aff, filename in grid_generator:
            arr = features.rasterize(shapes_iterator, out_shape=shape, transform=aff,
                                     dtype=np.uint8)
            meta = {'driver': 'GTiff',
                    'height': shape[0],
                    'width': shape[1],
                    'count': 1,
                    'transform': aff,
                    'dtype': rasterio.uint8,
                    'crs': crs,
                    'compress': 'lzw'}
            fp = os.path.join(path, filename)
            if bucket is not None:
                s3.write_raster(bucket, fp, arr, **meta)
            else:
                with rasterio.open(fp, 'w', **meta) as dst:
                    dst.write(arr, 1)
