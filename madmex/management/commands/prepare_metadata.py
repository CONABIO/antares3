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

from madmex.management.base import AntaresBaseCommand


logger = logging.getLogger(__name__)

class Command(AntaresBaseCommand):
    help = """
Command line to generate metadata file required for indexation of a dataset in the datacube database.
Supported datasets (passed in the --dataset_name argument) are landsat_espa.

The command allows to generate one metadata file for multiple scenes or tiles.

Datasets details:
    - landsat_espa corresponds to landsat surface reflectance data ordered via the espa platform. Every scene
        must be unzipped so that it corresponds to a folder with at least the individual surface reflectance bands,
        the pixel_qa band and the .xml metadata file.

--------------
Example usage:
--------------
python madmex.py prepare_metadata.py --path /path/to/dir/containing/scenes --dataset_name landsat_espa --outfile metadata_landsat.yaml
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

    def handle(self, *args, **options):
        scene_list = glob(os.path.join(options['path'], '*'))
        try:
            ingest = import_module('madmex.ingestion.%s' % options['dataset_name'])
        except ImportError as e:
            raise ValueError('Invalid dataset_name argument')
        metadata_list = []
        # iterate over each element contained in path, for loop needed for error catching
        for scene in scene_list:
            try:
                metadata_list.append(ingest.metadata_convert(scene))
            except Exception as e:
                logger.warn('No metadata generated for %s, reason: %s' % (scene, e))
        # Write metadata_list to a single file
        with open(options['outfile'], 'w') as dst:
            for metadata in metadata_list:
                dst.write(metadata)
                dst.write('\n---\n')


