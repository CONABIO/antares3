#!/usr/bin/env python

"""
Author: Loic Dutrieux
Date: 2018-05-07
Purpose: Query the result of a classification and write the results to a vector
    file on disk
"""
from madmex.management.base import AntaresBaseCommand

from madmex.models import Country, Region, PredictClassification
from madmex.util.spatial import feature_transform

import fiona
from fiona.crs import from_string
import json
import logging

logger = logging.getLogger(__name__)

def write_to_file(fc, filename, layer, driver, crs):
    # Define output file schema
    schema = {'geometry': 'Polygon',
              'properties': {'class':'str',
                             'code':'int'}}

    # Write to file
    logger.info('Writing feature collection to file')
    crs = from_string(crs)
    with fiona.open(filename, 'w',
                    encoding='utf-8',
                    schema=schema,
                    driver=driver,
                    layer=layer,
                    crs=crs) as dst:
        write = dst.write
        [write(feature) for feature in fc]

class Command(AntaresBaseCommand):
    help = """
Query the result of a classification and write the results to a vector file on disk

--------------
Example usage:
--------------
# Query classification performed for the state of Jalisco and write it to ESRI Shapfile
antares db_to_vector --region Jalisco --name s2_001_jalisco_2017_bis_rf_1 --filename Jalisco_s2.shp

# Query classification performed for the state of Jalisco and write it to Geopackage
antares db_to_vector --region Jalisco --name s2_001_jalisco_2017_bis_rf_1 --filename madmex_mexico.shp --layer Jalisco --driver GPKG

# With reprojection
antares db_to_vector --region Jalisco --name s2_001_jalisco_2017_bis_rf_1 --filename Jalisco_s2.shp --proj4 '+proj=lcc +lat_1=17.5 +lat_2=29.5 +lat_0=12 +lon_0=-102 +x_0=2500000 +y_0=0 +a=6378137 +b=6378136.027241431 +units=m +no_defs'
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
                            help='Name of the output filename. Can be an existing file if --layer is specified and the driver used support multiple layers')
        parser.add_argument('-l', '--layer',
                            type=str,
                            default=None,
                            help='Name of the layer (only for drivers that support multi-layer files)')
        parser.add_argument('-d', '--driver',
                            type=str,
                            default='ESRI Shapefile',
                            help='OGR driver to use for writting the data to file. Defaults to ESRI Shapefile')
        parser.add_argument('-p', '--proj4',
                            type=str,
                            default=None,
                            help='Optional proj4 string defining the output projection')


    def handle(self, *args, **options):
        name = options['name']
        region = options['region']
        filename = options['filename']
        layer = options['layer']
        driver = options['driver']
        proj4 = options['proj4']

        # Define function to convert query set object to feature
        def to_fc(x):
            geometry = json.loads(x.predict_object.the_geom.geojson)
            feature = {'type': 'feature',
                       'geometry': geometry,
                       'properties': {'class': x.tag.value, 'code': x.tag.numeric_code}}
            return feature

        # Query country or region contour
        try:
            region = Country.objects.get(name=region).the_geom
        except Country.DoesNotExist:
            region = Region.objects.get(name=region).the_geom

        # Query objects
        logger.info('Querying the database for intersecting records')
        qs = PredictClassification.objects.filter(name=name)
        qs = qs.filter(predict_object__the_geom__intersects=region).prefetch_related('predict_object', 'tag')

        # Convert query set to feature collection generator
        logger.info('Generating feature collection')
        fc = (to_fc(x) for x in qs)
        crs = '+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs'
        if proj4 is not None:
            fc = (feature_transform(x, crs_out=proj4) for x in fc)
            crs = proj4

        write_to_file(fc, filename, layer=layer, driver=driver, crs=crs)



