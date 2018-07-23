#!/usr/bin/env python

"""
Author: Loic Dutrieux
Date: 2018-07-23
Purpose: Generates a raster mask for a given country
"""
import json
from madmex.management.base import AntaresBaseCommand
from madmex.models import Country
from django.db import connection
import rasterio
from rasterio import features
from madmex.util import s3


def postgis_box_parser(box):
    pattern = re.compile(r'BOX\((\d+\.*\d*) (\d+\.*\d*),(\d+\.*\d*) (\d+\.*\d*)\)')
    m = pattern.search(box)
    return [float(x) for x in m.groups()]


def grid_gen():
    """Takes extent, tile size and resolution and returns a generator of (shape, transform) tuples
    """

class Command(AntaresBaseCommand):
    help = """
Generate a tiled raster mask for a given country

--------------
Example usage:
--------------
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
        resolution = options['resolution']
        tile_size = options['tile_size']
        bucket = options['bucket']
        path = options['path']

        if bucket is not None:
            path = s3.build_rasterio_path(bucket, path)

        query_0 = 'SELECT st_extent(the_geom) FROM public.madmex_country WHERE name = %s'
        query_1 = 'SELECT st_asgeojson(the_geom, 6) FROM public.madmex_country WHERE name = %s'
        with connection.cursor() as c:
            c.execute(query_0, [country.upper()])
            bbox = c.fetchone()
            c.execute(query_1, [country.upper()])
            geom = c.fetchall()

        xmin, ymin, xmax, ymax = postgis_box_parser(bbox[0])
        geom = json.loads(geom)
