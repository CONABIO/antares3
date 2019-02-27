#!/usr/bin/env python

"""
Author: palmoreck
Date: 2019-02-26
Purpose: Write result of a classification to a raster file on disk
"""
from madmex.management.base import AntaresBaseCommand

from madmex.models import Country, Region, PredictClassification
from madmex.util.db import classification_to_cmap
import fiona
import json
import logging
import gc
import rasterio
from rasterio.merge import merge
from dask.distributed import Client
import os
from os.path import expanduser
from madmex.settings import TEMP_DIR

logger = logging.getLogger(__name__)


class Command(AntaresBaseCommand):
    help = """
Write result of classification to a raster file (only supports GeoTiff for now)

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
        parser.add_argument('-sc', '--scheduler',
                            type=str,
                            default=None,
                            help='Path to file with scheduler information (usually called scheduler.json)')

    def handle(self, *args, **options):
        name = options['name']
        region = options['region']
        filename = options['filename']
        resolution = options['resolution']
        # Proj4 string needs to be quoted in query
        proj4 = options['proj4']
        scheduler_file = options['scheduler']

        # Query country or region contour
        try:
            region = Country.objects.get(name=region).the_geom
        except Country.DoesNotExist:
            region = Region.objects.get(name=region).the_geom
        
        region_geojson = region.geojson
        geometry = json.loads(region_geojson)
        
        path_destiny = os.path.join(TEMP_DIR, 'db_to_raster_results')
        if not os.path.exists(path_destiny):
            os.makedirs(path_destiny)

        qs_ids = PredictClassification.objects.filter(name=predict_name).distinct('predict_object_id')
        list_ids = [x.predict_object_id for x in qs_ids]
        
        client = Client(scheduler_file=scheduler_file)
        client.restart()
        c = client.map(fun,list_ids,**{'predict_name': name,
                                       'geometry': geometry,
                                       'resolution': resolution,
                                       'path_destiny': path_destiny,
                                       'proj4': proj4})
        result = client.gather(c) 
        logger.info('Merging results')
        
        src_files_to_mosaic=[]
        for file in result:
            src = rasterio.open(file)
            src_files_to_mosaic.append(src)
        
        mosaic, out_trans = merge(src_files_to_mosaic)
        meta = {'driver': 'GTiff',
                'width': mosaic.shape[2],
                'height': mosaic.shape[1],
                'count': 1,
                'dtype': mosaic.dtype,
                'crs': proj4,
                'transform': out_trans,
                'compress': 'lzw',
                'nodata': 0}
        
        filename_mosaic = expanduser("~") + filename

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
        with rasterio.open(filename_mosaic, 'w', **meta) as dst:
            dst.write(mosaic)
            try:
                cmap = classification_to_cmap(name)
                dst.write_colormap(1,cmap)
            except Exception as e:
                logger.info('Didn\'t find a colormap or couldn\'t write it: %s' % e)
                pass
        
        #close & clean:
        for i in range(0,len(result)):
            src_files_to_mosaic[i].close()
            os.remove(result[i])
