#!/usr/bin/env python

"""
Author: palmoreck
Date: 2019-02-26
Purpose: Write result of a classification to a raster file on disk
"""
import os
import json
import logging
import gc
import numpy as np

from dask.distributed import Client
from fiona.crs import to_string
import rasterio
from rasterio.warp import transform_geom
from rasterio.crs import CRS as CRS_rio
from rasterio.merge import merge
from rasterio import features

from madmex.management.base import AntaresBaseCommand
from madmex.models import Country, Region, PredictClassification
from madmex.util.db import classification_to_cmap
from madmex.settings import TEMP_DIR
from madmex.wrappers import write_predict_result_to_raster

logger = logging.getLogger(__name__)


class Command(AntaresBaseCommand):
    help = """
Write result of classification to a raster file (only supports GeoTiff for now)

--------------
Example usage:
--------------
# Query classification performed for the state of Jalisco and write it to  GeoTiff
antares db_to_raster --region Jalisco --name s2_001_jalisco_2017_bis_rf_1 --filename Jalisco_sentinel_2017.tif --resolution 20 --scheduler scheduler.json
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
        parser.add_argument('-sc', '--scheduler',
                            type=str,
                            default=None,
                            help='Path to file with scheduler information (usually called scheduler.json)')

    def handle(self, *args, **options):
        name = options['name']
        region = options['region']
        filename = options['filename']
        resolution = options['resolution']
        scheduler_file = options['scheduler']

        # Query country or region contour
        try:
            region = Country.objects.get(name=region).the_geom
        except Country.DoesNotExist:
            region = Region.objects.get(name=region).the_geom

        region_geojson = region.geojson
        geometry_region = json.loads(region_geojson)


        path_destiny = os.path.join(TEMP_DIR, 'db_to_raster_results')
        if not os.path.exists(path_destiny):
            os.makedirs(path_destiny)

        qs_ids = PredictClassification.objects.filter(predict_object__the_geom__intersects=region).filter(name=name).distinct('predict_object_id')
        list_ids = [x.predict_object_id for x in qs_ids]

        client = Client(scheduler_file=scheduler_file)
        client.restart()
        c = client.map(write_predict_result_to_raster,
                       list_ids,
                       **{'predict_name': name,
                          'resolution': resolution,
                          'path_destiny': path_destiny})
        result = client.gather(c)
        logger.info('Merging results')

        src_files_to_mosaic = [rasterio.open(f) for f in result]
        # Retrieve metadata of one file for later use
        meta = src_files_to_mosaic[0].meta.copy()

        mosaic, out_trans = merge(src_files_to_mosaic)
        meta.update(width=mosaic.shape[2],
                    height=mosaic.shape[1],
                    transform=out_trans,
                    compress='lzw')

        # Reproject geometry of the region
        geometry_region_proj = transform_geom(CRS_rio.from_epsg(4326),
                                              CRS_rio.from_proj4(to_string(meta['crs'])),
                                              geometry_region)

        # rasterize region using mosaic as template
        logger.info('Masking mosaic')
        mask_array = features.rasterize(shapes=[(geometry_region_proj, 1)],
                                        out_shape=(mosaic.shape[1],mosaic.shape[2]),
                                        fill=0,
                                        transform=meta['transform'],
                                        dtype=rasterio.uint8)

        # Apply mask to mosaic
        mosaic[:,mask_array==0] = 0

        # Write results to file
        logger.info('Writing mosaig to filename')
        filename_mosaic = os.path.expanduser(os.path.join("~/", filename))
        with rasterio.open(filename_mosaic, "w", **meta) as dst:
            dst.write(mosaic)
            try:
                cmap = classification_to_cmap(name)
                dst.write_colormap(1,cmap)
            except Exception as e:
                logger.info('Didn\'t find a colormap or couldn\'t write it: %s' % e)
                pass

        #close & clean:
        logger.info('Deleting temporary results')
        for i in range(0,len(result)):
            src_files_to_mosaic[i].close()
            os.remove(result[i])
