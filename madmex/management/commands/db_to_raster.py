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

import fiona
from fiona.crs import from_string
import json
import logging
import gc

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
        proj4 = options['proj4']

        # Query 0: Create the temp table
        """
CREATE TEMP TABLE predict_proj AS
SELECT
    st_transform(public.madmex_predictobject.the_geom, '+proj=lcc +lat_1=17.5 +lat_2=29.5 +lat_0=12 +lon_0=-102 +x_0=2500000 +y_0=0 +a=6378137 +b=6378136.027241431 +units=m +no_defs') AS geom_proj,
    public.madmex_tag.numeric_code
FROM
    public.madmex_predictclassification
INNER JOIN
    public.madmex_predictobject ON public.madmex_predictclassification.predict_object_id = public.madmex_predictobject.id AND st_intersects(public.madmex_predictobject.the_geom, ST_GeometryFromText('POLYGON ((-106.90521240234375 29.185737173254434, -106.962890625 29.12577252480808, -106.89697265625 29.07057414581467, -106.787109375 29.099376992628493, -106.820068359375 29.185737173254434, -106.85302734374999 29.19053283229458, -106.90521240234375 29.185737173254434))', 4326))
INNER JOIN
    public.madmex_tag ON public.madmex_predictclassification.tag_id = public.madmex_tag.id;
        """

        # Query 1: Get bbox
        """
SELECT
    st_extent(geom_proj)
FROM
    predict_proj;
        """

        # Query 2: Get the whole queryset/table
        """
SELECT geom_proj, tag FROM predict_proj;
        """
        # Define function to convert query set object to feature
        def to_feature(x):
            """Not really a feature; more like a geometry/value tuple
            """
            geometry = json.loads(x.predict_object.the_geom.geojson)
            return (geometry, x.tag.numeric_code)

        def to_proj_feature(x, crs):
            """Not really a feature; more like a geometry/value tuple
            """
            geometry = json.loads(x.predict_object.the_geom.geojson)
            geometry = geometry_transform(geometry, proj4)
            return (geometry, x.tag.numeric_code)

        # Query country or region contour
        try:
            region = Country.objects.get(name=region).the_geom
        except Country.DoesNotExist:
            region = Region.objects.get(name=region).the_geom

        # Query objects
        logger.info('Querying the database for intersecting records')
        qs = PredictClassification.objects.filter(name=name)
        qs = qs.filter(predict_object__the_geom__intersects=region).iterator(chunk_size=20000)

        # Convert query set to feature collection 
        logger.info('Generating feature collection')
        if proj4 is None:
            fc = [to_feature(x) for x in qs]
            crs = '+proj=longlat'
        else:
            fc = [to_proj_feature(x, proj4) for x in qs]
            crs = proj4
        qs = None
        gc.collect()

        # Find top left corner coordinate
        logger.info('Looking for top left coordinates')
        ul_coord_list = (get_geom_bbox(x[0]) for x in fc)
        xmin_list, ymin_list, xmax_list, ymax_list = zip(*ul_coord_list)
        ul_x = min(xmin_list)
        ul_y = max(ymax_list)
        lr_x = max(xmax_list)
        lr_y = min(ymin_list)

        # Define output raster shape
        nrows = int(((ul_y - lr_y) // resolution) + 1)
        ncols = int(((lr_x - ul_x) // resolution) + 1)
        shape = (nrows, ncols)

        # Define affine transform
        logger.info('Rasterizing feature collection')
        aff = Affine(resolution, 0, ul_x, 0, -resolution, ul_y)
        arr = rasterize(shapes=fc, out_shape=shape, transform=aff, dtype=np.uint8)

        # Write array to file
        meta = {'driver': 'GTiff',
                'width': shape[1],
                'height': shape[0],
                'count': 1,
                'dtype': arr.dtype,
                'crs': crs,
                'transform': aff,
                'compress': 'lzw',
                'nodata': 0}

        logger.info('Writing rasterized feature collection to file')
        with rasterio.open(filename, 'w', **meta) as dst:
            dst.write(arr, 1)

# Add colormaps
# 1 Read from tags table (via external function)
# 2 Convert hex color codes to rgb + transparency https://stackoverflow.com/questions/29643352/converting-hex-to-rgb-value-in-python
# 3 Add other tags (0, etc)
# Write to file with rasterio.dst.write_colormap
