#!/usr/bin/env python

"""
Author: Loic Dutrieux
Date: 2018-08-30
Purpose: Ingest a subset of training data randomly sampled from a raster into the antares database
"""

import logging
import json
import os
import numpy as np
import random

from django.contrib.gis.geos.geometry import GEOSGeometry
import rasterio
import rasterio.features
from rasterio.windows import Window
import itertools
from shapely.geometry import mapping, shape
from fiona.crs import to_string
from pyproj import Proj

from madmex.management.base import AntaresBaseCommand
from madmex.models import TrainObject, Tag, TrainClassification
from madmex.util.spatial import geometry_transform

logger = logging.getLogger(__name__)

class Command(AntaresBaseCommand):
    help = """
Ingest a subset of training data randomly sampled from a raster into the antares database
--------------
Example usage:
--------------
antares ingest_training_from_raster_chunk /path/to/file.tif --fraction 0.0001 --classes 31 --chunk_size 20000 --scheme madmex --year 2015 --name train_mexico --field code
    """
    def add_arguments(self, parser):
        parser.add_argument('input_file',
                            type=str,
                            help='Path of vector file to ingest')
        parser.add_argument('-frac', '--fraction',
                            type=float,
                            help='fraction of data to ingest.')
        parser.add_argument('-cl', '--classes',
                            type=int,
                            help='Number of classes')
        parser.add_argument('-chunk', '--chunk_size',
                            type=int,
                            help='Number of pixels in chunk')
        parser.add_argument('-scheme', '--scheme',
                            type=str,
                            help='Name of the classification scheme to which the data belong')
        parser.add_argument('-field', '--field',
                            type=str,
                            help='Name of the vector file field containing the numeric codes of the class of interest')
        parser.add_argument('-name', '--name',
                            type=str,
                            help='Name/identifier under which the training set should be registered in the database')
        parser.add_argument('-year', '--year',
                            type=str,
                            help='Data interpretation year',
                            required=False,
                            default=-1)
    def handle(self, **options):
        input_file = options['input_file']
        year = options['year']
        frac = options['fraction']
        classes = options['classes']
        chunk_size = options['chunk_size']
        scheme = options['scheme']
        field = options['field']
        name = options['name']
        
        def add_samples(frac, arr, train_arr):
            mask = np.zeros(train_arr.size, dtype=np.uint8)
            for indx in np.where(arr)[0]:
                tmp = np.zeros(train_arr.shape, dtype=np.uint8)
                tmp[train_arr == indx+1] = 1
                ind = np.where(tmp.reshape(-1) == 1)[0]
                num = int(np.ceil(ind.size*frac))  # 0.7/3600
                samples = np.array(random.sample(list(ind),num))
                mask[samples] = 1
            mask = mask.reshape(train_arr.shape)
            return mask

        def chunk_dim(length, chunk_size):
            begins = range(0, length, chunk_size)
            n_complete, remain = divmod(length, chunk_size)
            intervals = list(itertools.repeat(chunk_size, n_complete)) + [remain]
            return zip(begins, intervals)

        def window_generator(dataset, chunk_size):
            """Generator of (window index, window)"""
            for i, col in enumerate(chunk_dim(dataset.width, chunk_size)):
                for j, row in enumerate(chunk_dim(dataset.height, chunk_size)):
                    yield ((j, i), Window(col[0], row[0], col[1], row[1]))

        # Write features to ValidObject table
        def train_obj_builder(x):
            """Build individual ValidObjects
            """
            geom = GEOSGeometry(json.dumps(x['geometry']))
            obj = TrainObject(the_geom=geom,
                              filename=os.path.basename(input_file),
                              creation_year=year)
            return obj

        # Update Tag table using get or create
        def make_tag_tuple(x):
            obj, _ = Tag.objects.get_or_create(numeric_code=x, scheme=scheme)
            return (x, obj)

        # Build validClassification object list (valid_tag, valid_object, valid_set)
        def train_class_obj_builder(x):
            """x is a tuple (ValidObject, feature)"""
            tag = tag_dict[x[1]['properties'][field]]
            obj = TrainClassification(predict_tag=tag,
                                      interpret_tag=tag,
                                      train_object=x[0],
                                      training_set=name)
            return obj

        # Create ValidClassification objects list
        # Push it to database
        
        # Read file and Optionally reproject the features to longlat
        with rasterio.open(input_file) as src:
            for win in window_generator(src, chunk_size):
                try:
                    train_arr = src.read(1, window=win[1])
                    aff = rasterio.windows.transform(win[1], src.transform)
                    #crs_str = to_string(src.crs)

                    # Build mask for shapes
                    mask = np.zeros(train_arr.shape, dtype=np.uint8)
                    # Count total number of pixels per class
                    pxpcl = np.array([train_arr[train_arr == cl].size for cl in range(1,classes+1)])

                    # Generate number of samples per class
                    smplpxpcl = np.array([int(np.ceil(train_arr[train_arr == cl].size*frac)) for cl in range(1,classes+1)])

                    # Generate mask of samples
                    smplcl = np.logical_and(pxpcl > 0, smplpxpcl > 0)
                    if any(smplcl):
                        mask[add_samples(frac, smplcl, train_arr) == 1] = 1

                    # Build the feature collection
                    p = Proj(src.crs)
                    if p.is_latlong(): # Here we assume that geographic coordinates are automatically 4326 (not quite true)
                        fc = [{'type': 'feature',
                           'geometry': mapping(shape(x[0])),
                           'properties': {'class': int(x[1])}} for x in rasterio.features.shapes(train_arr,mask,connectivity=4,transform=aff)]
                    else:
                        crs_str = to_string(src.crs)
                        fc = [{'type': 'feature',
                           'geometry': geometry_transform(x[0], crs_out='+proj=longlat', crs_in=crs_str),
                           'properties': {'class': int(x[1])}} for x in rasterio.features.shapes(train_arr,mask,connectivity=4,transform=aff)]
                 
                    if len(fc) < 1:
                        raise ValueError("No features")

                    obj_list = [train_obj_builder(x) for x in fc]
                    TrainObject.objects.bulk_create(obj_list)

                    # Get list of unique tags
                    unique_numeric_codes = list(set([x['properties'][field] for x in fc]))

                    tag_dict = dict([make_tag_tuple(x) for x in unique_numeric_codes])

                    train_class_obj_list = [train_class_obj_builder(x) for x in zip(obj_list, fc)]

                    TrainClassification.objects.bulk_create(train_class_obj_list)
                except:
                    pass
