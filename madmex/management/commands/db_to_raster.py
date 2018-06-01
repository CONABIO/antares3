#!/usr/bin/env python

"""
Author: Loic Dutrieux
Date: 2018-05-31
Purpose: Query the result of a classification and write the results to a raster
    file on disk
"""
from madmex.management.base import AntaresBaseCommand

from madmex.models import Country, Region, PredictClassification
from madmex.util.spatial import geometry_transform, get_geom_ul

import fiona
from fiona.crs import from_string
import json
import logging
import gc

logger = logging.getLogger(__name__)


class Command(AntaresBaseCommand):
    help = """
Query the result of a classification and write it to a raster file

--------------
Example usage:
--------------
# Query classification performed for the state of Jalisco and write it to  GeoTiff
antares db_to_vector --region Jalisco --name s2_001_jalisco_2017_bis_rf_1 --filename Jalisco_s2.shp
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
        # parser.add_argument('-d', '--driver',
                            # type=str,
                            # default='ESRI Shapefile',
                            # help='OGR driver to use for writting the data to file. Defaults to ESRI Shapefile')
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
        # driver = options['driver']
        proj4 = options['proj4']

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
        qs = qs.filter(predict_object__the_geom__intersects=region).prefetch_related('predict_object', 'tag')

        # Convert query set to feature collection 
        logger.info('Generating feature collection')
        if proj4 is None:
            fc = [to_feature(x) for x in qs]
        else:
            fc = [to_proj_feature(x) for x in qs]
        qs = None
        gc.collect()

        # Find top left corner coordinate
        ul_coord_list = (get_geom_ul(x[0]) for x in fc)
        ulx_list, uly_list = zip(*ul_coord_list)
        ul_x = min(ulx_list)
        ul_y = max(uly_list)




