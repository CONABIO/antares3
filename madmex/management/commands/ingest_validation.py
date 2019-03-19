#!/usr/bin/env python

"""
Author: Loic Dutrieux
Date: 2018-06-06
Purpose: Ingest a vector file containing validation data into the antares database
"""

import logging
import json
import os

from django.contrib.gis.geos.geometry import GEOSGeometry
import fiona
from fiona.crs import to_string
from pyproj import Proj

from madmex.management.base import AntaresBaseCommand
from madmex.models import ValidObject, Tag, ValidClassification
from madmex.util.spatial import feature_transform

logger = logging.getLogger(__name__)

class Command(AntaresBaseCommand):
    help = """
Ingest a vector file containing validation data into the antares database

--------------
Example usage:
--------------
antares ingest_validation /path/to/file.shp --scheme madmex --year 2015 --name random_validation --field code
    """
    def add_arguments(self, parser):
        parser.add_argument('input_file',
                            type=str,
                            help='Path of vector file to ingest')
        parser.add_argument('-scheme', '--scheme',
                            type=str,
                            help='Name of the classification scheme to which the data belong. Ideally, that scheme already exists in the database')
        parser.add_argument('-field', '--field',
                            type=str,
                            help='Name of the vector file field containing the numeric codes of the class of interest')
        parser.add_argument('-name', '--name',
                            type=str,
                            help='Name/identifier under which the validation set should be registered in the database')
        parser.add_argument('-year', '--year',
                            type=int,
                            help='Data interpretation year',
                            required=False,
                            default=-1)
    def handle(self, **options):
        input_file = options['input_file']
        year = options['year']
        scheme = options['scheme']
        field = options['field']
        name = options['name']
        # Create ValidClassification objects list
        # Push it to database

        # Read file and Optionally reproject the features to longlat
        with fiona.open(input_file) as src:
            p = Proj(src.crs)
            if p.is_latlong(): # Here we assume that geographic coordinates are automatically 4326 (not quite true)
                fc = list(src)
            else:
                crs_str = to_string(src.crs)
                fc = [feature_transform(x, crs_out='+proj=longlat', crs_in=crs_str)
                      for x in src]

        # Write features to ValidObject table
        def valid_obj_builder(x):
            """Build individual ValidObjects
            """
            geom = GEOSGeometry(json.dumps(x['geometry'])).buffer(0)
            obj = ValidObject(filename=os.path.basename(input_file),
                              the_geom=geom)
            return obj

        obj_list = [valid_obj_builder(x) for x in fc]
        valid_obj_list = [obj for obj in obj_list if obj.the_geom.is_valid]
        if len(valid_obj_list) < len(obj_list)*0.9:
            raise Error('Too many invalid geometries')
        ValidObject.objects.bulk_create(obj_list)

        # Get list of unique tags
        unique_numeric_codes = list(set([x['properties'][field] for x in fc]))

        # Update Tag table using get or create
        def make_tag_tuple(x):
            obj, _ = Tag.objects.get_or_create(numeric_code=x, scheme=scheme)
            return (x, obj)

        tag_dict = dict([make_tag_tuple(x) for x in unique_numeric_codes])

        # Build validClassification object list (valid_tag, valid_object, valid_set)
        def valid_class_obj_builder(x):
            """x is a tuple (ValidObject, feature)"""
            tag = tag_dict[x[1]['properties'][field]]
            obj = ValidClassification(valid_tag=tag, valid_object=x[0],
                                      valid_set=name, interpretation_year=year)
            return obj

        valid_class_obj_list = [valid_class_obj_builder(x) for x in zip(obj_list, fc)]

        ValidClassification.objects.bulk_create(valid_class_obj_list)
