#!/usr/bin/env python

"""
Author: Loic Dutrieux
Date: 2018-05-31
Purpose: Query the result of a classification and write the results to a raster
    file on disk
"""
from madmex.management.base import AntaresBaseCommand

from madmex.models import Country, Region, PredictClassification
from madmex.util.spatial import geometry_transform, get_geom_bbox
from madmex.util import chunk
from madmex.util.db import classification_to_cmap
from django.db import connection

import fiona
from fiona.crs import from_string
import json
import logging
import gc
import re

import numpy as np
from affine import Affine
import rasterio
from rasterio.features import rasterize

logger = logging.getLogger(__name__)


class Command(AntaresBaseCommand):
    help = """
Query the result of a classification and write it to a raster file (only supports GeoTiff for now)

--------------
Example usage:
--------------
# Query classification performed for the state of Jalisco and write it to  GeoTiff
antares db_to_raster --region Jalisco --name s2_001_jalisco_2017_bis_rf_1 --filename Jalisco_sentinel_2017.tif --resolution 20 --proj4 '+proj=lcc +lat_1=17.5 +lat_2=29.5 +lat_0=12 +lon_0=-102 +x_0=2500000 +y_0=0 +a=6378137 +b=6378136.027241431 +units=m +no_defs'
"""
    def add_arguments(self, parser):
        parser.add_argument('-n', '--name',
                            type=str,
                            default=None,
                            help='Name of the classification to export to file')
        parser.add_argument('-region', '--region',
                            type=str,
                            default=None,
                            help=('Name of the region over which the recipe should be applied. The geometry of the region should be present '
                                  'in the madmex-region or the madmex-country table of the database (Overrides lat and long when present) '
                                  'Use ISO country code for country name'))
        parser.add_argument('-f', '--filename',
                            type=str,
                            default=None,
                            help='Name of the output filename')
        parser.add_argument('-res', '--resolution',
                            type=float,
                            required=True,
                            help='Resolution of the output raster in crs units. (See the --proj4 argument to define a projection, otherwise will be in longlat and resolution has to be specified in degrees)')
        parser.add_argument('-p', '--proj4',
                            type=str,
                            default=None,
                            help='Optional proj4 string defining the output projection')


    def handle(self, *args, **options):
        name = options['name']
        region = options['region']
        filename = options['filename']
        resolution = options['resolution']
        # Proj4 string needs to be quoted in query
        proj4 = options['proj4']

        # Query 0: Create the temp table
        q_0_proj = """
CREATE TEMP TABLE predict_proj AS
SELECT
    st_transform(public.madmex_predictobject.the_geom, %s) AS geom_proj,
    public.madmex_tag.numeric_code AS tag
FROM
    public.madmex_predictclassification
INNER JOIN
    public.madmex_predictobject ON public.madmex_predictclassification.predict_object_id = public.madmex_predictobject.id AND st_intersects(public.madmex_predictobject.the_geom, ST_GeometryFromText(%s, 4326)) AND public.madmex_predictclassification.name = %s
INNER JOIN
    public.madmex_tag ON public.madmex_predictclassification.tag_id = public.madmex_tag.id;
        """

        q_0_longlat = """
CREATE TEMP TABLE predict_proj AS
SELECT
    public.madmex_predictobject.the_geom AS geom_proj,
    public.madmex_tag.numeric_code AS tag
FROM
    public.madmex_predictclassification
INNER JOIN
    public.madmex_predictobject ON public.madmex_predictclassification.predict_object_id = public.madmex_predictobject.id AND st_intersects(public.madmex_predictobject.the_geom, ST_GeometryFromText(%s, 4326)) AND public.madmex_predictclassification.name = %s
INNER JOIN
    public.madmex_tag ON public.madmex_predictclassification.tag_id = public.madmex_tag.id;
        """

        # Query 1: Get bbox
        q_1 = """
SELECT
    st_extent(geom_proj)
FROM
    predict_proj;
        """

        # Query 2: Get the whole queryset/table
        q_2 = """
SELECT st_asgeojson(geom_proj, 5), tag FROM predict_proj;
        """

        # Define function to convert query set object to feature
        def to_feature(x):
            """Not really a feature; more like a geometry/value tuple
            """
            geometry = json.loads(x[0])
            return (geometry, x[1])

        def postgis_box_parser(box):
            pattern = re.compile(r'BOX\((\d+\.*\d*) (\d+\.*\d*),(\d+\.*\d*) (\d+\.*\d*)\)')
            m = pattern.search(box)
            return [float(x) for x in m.groups()]

        # Query country or region contour
        try:
            region = Country.objects.get(name=region).the_geom
        except Country.DoesNotExist:
            region = Region.objects.get(name=region).the_geom

        # Query objects
        logger.info('Querying the database for intersecting records')
        with connection.cursor() as c:
            if proj4 is not None:
                c.execute(q_0_proj, [proj4, region.wkt, name])
            else:
                c.execute(q_0_longlat, [region.wkt, name])
            c.execute(q_1)
            bbox = c.fetchone()
            c.execute(q_2)
            qs = c.fetchall()

        xmin, ymin, xmax, ymax = postgis_box_parser(bbox[0])

        # Define output raster shape
        nrows = int(((ymax - ymin) // resolution) + 1)
        ncols = int(((xmax - xmin) // resolution) + 1)
        shape = (nrows, ncols)
        logger.info('Allocating array of shape (%d, %d)' % (nrows, ncols))
        arr = np.zeros((nrows, ncols), dtype=np.uint8)
        aff = Affine(resolution, 0, xmin, 0, -resolution, ymax)

        # Define affine transform
        logger.info('Rasterizing feature collection')
        for qs_sub in chunk(qs, 100000):
            # Convert query set to feature collection 
            fc = [to_feature(x) for x in qs_sub]
            rasterize(shapes=fc, transform=aff, dtype=np.uint8, out=arr)
            fc = None
            gc.collect()

        if proj4 is None:
            proj4 = "+proj=longlat"

        # Write array to file
        meta = {'driver': 'GTiff',
                'width': shape[1],
                'height': shape[0],
                'count': 1,
                'dtype': arr.dtype,
                'crs': proj4,
                'transform': aff,
                'compress': 'lzw',
                'nodata': 0}

        logger.info('Writing rasterized feature collection to file')
        with rasterio.open(filename, 'w', **meta) as dst:
            dst.write(arr, 1)
            try:
                cmap = classification_to_cmap(name)
                dst.write_colormap(1, cmap)
            except Exception as e:
                logger.info('Didn\'t find a colormap or couldn\'t write it: %s' % e)
                pass

