#!/usr/bin/env python

"""
Author: palmoreck
Date: 2019-02-025
Purpose: Write result of classification + segmentation to a vector
    file on disk
"""
from madmex.management.base import AntaresBaseCommand

from madmex.models import Country, Region, PredictClassification
from dask.distributed import Client
import json
import logging
import fiona
from madmex.settings import TEMP_DIR
from os.path import expanduser
from madmex.wrappers import write_predict_result_to_vector
import os 
from madmex.util.spatial import geometry_transform

logger = logging.getLogger(__name__)




class Command(AntaresBaseCommand):
    help = """
Write results of classification + segmentation to a vector file on disk

--------------
Example usage:
--------------
# Query classification performed for the state of Jalisco and write it to ESRI Shapfile
antares db_to_vector --region Jalisco --name s2_001_jalisco_2017_bis_rf_1 --filename Jalisco_s2.shp

# Query classification performed for the state of Jalisco and write it to Geopackage
antares db_to_vector --region Jalisco --name s2_001_jalisco_2017_bis_rf_1 --filename madmex_mexico.shp --layer Jalisco --driver GPKG

# With reprojection
antares db_to_vector --region Jalisco --name s2_001_jalisco_2017_bis_rf_1 --filename Jalisco_s2.shp --proj4 '+proj=lcc +lat_1=17.5 +lat_2=29.5 +lat_0=12 +lon_0=-102 +x_0=2500000 +y_0=0 +a=6378137 +b=6378136.027241431 +units=m +no_defs' -sc scheduler.json
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
        parser.add_argument('-sc', '--scheduler',
                            type=str,
                            default=None,
                            help='Path to file with scheduler information (usually called scheduler.json)')

    def handle(self, *args, **options):
        predict_name = options['name']
        region = options['region']
        filename = options['filename']
        layer = options['layer']
        driver = options['driver']
        proj4 = options['proj4']
        scheduler_file = options['scheduler']
        # Query country or region contour
        try:
            region = Country.objects.get(name=region).the_geom
        except Country.DoesNotExist:
            region = Region.objects.get(name=region).the_geom

        region_geojson = region.geojson
        geometry = json.loads(region_geojson)
        
        if proj4 is not None:
            geometry_proj = geometry_transform(geometry,proj4)
        else:
            geometry_proj = geometry_transform(geometry, '+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')

        path_destiny = os.path.join(TEMP_DIR, 'db_to_vector_results')
        if not os.path.exists(path_destiny):
            os.makedirs(path_destiny)

        qs_ids = PredictClassification.objects.filter(name=predict_name).distinct('predict_object_id')
        list_ids = [x.predict_object_id for x in qs_ids]
        
        client = Client(scheduler_file=scheduler_file)
        client.restart()
        c = client.map(write_predict_result_to_vector,list_ids,**{'predict_name': predict_name,
                                       'geometry': geometry_proj,
                                       'path_destiny': path_destiny,
                                       'driver': driver,
                                       'layer': layer,
                                       'proj4': proj4})
        result = client.gather(c)        
        logger.info('Merging results')
        meta = fiona.open(result[0]).meta
        
        filename_merge = expanduser("~") + '/' + filename
        
        with fiona.open(filename_merge, 'w', **meta) as dst:
            [[dst.write(features) for features in fiona.open(x)] for x in result]
        for file in result:
            path_basename = file.split('.shp')[0]
            os.remove(file)
            os.remove(path_basename + '.shx')
            os.remove(path_basename + '.cpg')
            os.remove(path_basename + '.dbf')
            os.remove(path_basename + '.prj')
