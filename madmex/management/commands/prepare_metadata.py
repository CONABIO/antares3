#!/usr/bin/env python

"""
Author: Loic Dutrieux
Date: 2017-12-11
Purpose: Prepare metadata file for a list of scenes or tiles belonging to any of the
    datasets suported
"""
from importlib import import_module
import os
import logging
from glob import glob

from dask.distributed import Client, LocalCluster

from madmex.management.base import AntaresBaseCommand
from madmex.util import s3


logger = logging.getLogger(__name__)

class Command(AntaresBaseCommand):
    help = """
Command line to generate metadata file required for indexation of a dataset in the datacube database.
Supported datasets (passed in the --dataset_name argument) are landsat_espa and srtm_cgiar.

The command allows to generate one metadata file for multiple scenes or tiles.

Datasets details:
    - landsat_espa corresponds to landsat surface reflectance data ordered via the espa platform. Every scene
        must be unzipped so that it corresponds to a folder with at least the individual surface reflectance bands,
        the pixel_qa band and the .xml metadata file.

    - srtm_cgiar corresponds to the 90m gap filled version of the srtm DEM prepared by CGIAR. It is distributed in 5 degrees
        tile (can be downloaded manually from e.g. http://dwtkns.com/srtm/). A mosaic as well as derived terrain metrics has to
        be prepared prior to running this command, and the 3 geotiff named srtm_mosaic.tif, slope_mosaic.tif and aspect_mosaic.tif
        must be present in the target directory (--path argument). The preparation can be achieved by running the following bash commands
        in the directory where the unpacked srtm tiles are stored:
            file_list=$(ls *zip|sed -n 's/\(.*\).zip/\/vsizip\/\\1.zip\/\\1.tif/g;p'|tr -s '\\n' ' ')
            gdal_merge.py -o srtm_mosaic.tif $file_list
            gdaldem slope srtm_mosaic.tif slope_mosaic.tif -s 111120
            gdaldem aspect srtm_mosaic.tif aspect_mosaic.tif

        Note that the target directory (--path) must not contain subdirectories

    - country_mask is a dataset to identify pixels inside vs outside of a country. See the antares make_country_mask for
        more informations about how to generate this dataset

--------------
Example usage:
--------------
# Landsat espa
antares prepare_metadata --path /path/to/dir/containing/scenes --dataset_name landsat_espa --outfile metadata_landsat.yaml

# srtm_cgiar
antares prepare_metadata --path /path/to/dir/containing/srtm_terrain_metrics --dataset_name srtm_cgiar --outfile metadata_srtm.yaml

# Sentinel2 L2A 20m
antares prepare_metadata --path /path/to/dir/containing/granules --dataset_name s2_l2a_20m --outfile metadata_sentinel.yaml

# Country mask
antares prepare_metadata --path /path/to/dir/with/tiles --dataset_name country_mask --outfile metadata_country_mask.yaml

# Generate metadata for a single Landsat path row of landsat 8 data stored on s3
antares prepare_metadata --path dir/inside/bucket --bucket conabio-s3-oregon --dataset_name landsat_espa --outfile metadata_landsat_bucket.yaml --pattern .*LC08039037.* --multi 20
"""
    def add_arguments(self, parser):
        parser.add_argument('-p', '--path',
                            type=str,
                            required=True,
                            help='Directory containing the scenes or tiles for which metadata have to be generated')
        parser.add_argument('-d', '--dataset_name',
                            type=str,
                            required=True,
                            help='Name of the dataset to ingest. Supported datasets are landsat_espa')
        parser.add_argument('-o', '--outfile',
                            type=str,
                            required=True,
                            help='Name of the file to which metadata will be written. Typically of type .yaml')
        parser.add_argument('-b', '--bucket',
                            type=str,
                            default=None,
                            help='Optional name of a s3 bucket containing the data to index')
        parser.add_argument('-pattern', '--pattern',
                            type=str,
                            default=None,
                            help='Optional regex like pattern to use in the initial query. Only supported for s3 queries')
        parser.add_argument('-multi', '--multi',
                            type=int,
                            default=1,
                            help='The optional amount of worker to use for generating metadata information in parallel')

    def handle(self, *args, **options):
        path = options['path']
        bucket = options['bucket']
        pattern = options['pattern']
        multi = options['multi']
        if bucket is None:
            subdir_list = glob(os.path.join(path, '*'))
            # If the directory does not contain subdirectories it means that it's a single target directory
            if not any([os.path.isdir(x) for x in subdir_list]):
                subdir_list = [path]
        else:
            subdir_list = s3.list_folders(bucket=bucket, path=path, pattern=pattern)
            if not subdir_list:
                subdir_list = [path]
        try:
            ingest = import_module('madmex.ingestion.%s' % options['dataset_name'])
        except ImportError as e:
            raise ValueError('Invalid dataset_name argument')

        # Function to pass to map with error catcher
        def generate_meta_str(x, bucket):
            try:
                return ingest.metadata_convert(x, bucket=bucket)
            except Exception as e:
                logger.warn('No metadata generated for %s, reason: %s' % (x, e))
                return None

        # Set up local cluster and distribute iterator between processes
        cluster = LocalCluster(n_workers=multi, threads_per_worker=1)
        client = Client(cluster)
        C = client.map(generate_meta_str,
                       subdir_list,
                       **{'bucket': bucket})
        metadata_list = client.gather(C)
        # Clean up None elements from list
        metadata_list = [x for x in metadata_list if x is not None]

        # Write metadata_list to a single file
        with open(options['outfile'], 'w') as dst:
            for metadata in metadata_list:
                dst.write(metadata)
                dst.write('\n---\n')


