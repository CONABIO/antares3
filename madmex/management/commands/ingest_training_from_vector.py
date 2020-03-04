#!/usr/bin/env python

"""
Author: Loic Dutrieux
Date: 2018-08-30
Purpose: Ingest a vector file containing training data into the antares database
"""

import logging
import json
import os

from django.contrib.gis.geos.geometry import GEOSGeometry
import fiona
from fiona.crs import to_string
from pyproj import Proj

from madmex.management.base import AntaresBaseCommand
from madmex.models import TrainObject, Tag, TrainClassification, TrainClassificationLabeledByApp
from madmex.util.spatial import feature_transform
from madmex.util.spatial import get_geom_bbox, geometry_transform
from shapely.geometry import shape, mapping, Point, Polygon


logger = logging.getLogger(__name__)

class Command(AntaresBaseCommand):
    help = """
Ingest a vector file containing training data into the antares database

--------------
Example usage:
--------------
antares ingest_training_from_vector /path/to/file.shp --scheme madmex --year 2015 --name train_mexico --field code
antares ingest_training_from_vector /path/to/file.shp --scheme automatic --year 2020 --name agricultura --field preds --app
antares ingest_training_from_vector /path/to/file.shp --scheme automatic --year 2020 --name agricultura --field preds --app --train_interpreted --scheme_interpreted agricultura_conabio --field_interpreted class --dc_tile 40_-31
    """
    def add_arguments(self, parser):
        parser.add_argument('input_file',
                            type=str,
                            help='Path of vector file to ingest')
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
        parser.add_argument('--app',
                            action='store_true',
                            help='Ingest to table TrainClassificationLabeledByApp?')
        parser.add_argument('-train_interpreted', '--train_interpreted',
                            action='store_true',
                            help='Does trainining set has some labels?')
        parser.add_argument('-scheme_interpreted', '--scheme_interpreted',
                            type=str,
                            help='Name of the classification scheme to which the data belong. Use it if train_interpreted flag is set')
        parser.add_argument('-field_interpreted', '--field_interpreted',
                            type=str,
                            help='Name of the vector file field containing the numeric codes of the class of interest. Use it if train_interpreted flag is set')
        parser.add_argument('-dc_tile', '--dc_tile',
                            type=str,
                            help='Coordinates of dc tile to be registered in madmex_trainingsetandodctilesforapp table')
    def handle(self, **options):
        input_file = options['input_file']
        year = options['year']
        scheme = options['scheme']
        field = options['field']
        name = options['name']
        app = options['app']
        train_interpreted = options['train_interpreted']
        scheme_interpreted = options['scheme_interpreted']
        field_interpreted = options['field_interpreted']
        dc_tile = options['dc_tile']
        # Create ValidClassification objects list
        # Push it to database

        # Read file and Optionally reproject the features to longlat
        with fiona.open(input_file) as src:
            p = Proj(src.crs)
            if p.crs.is_geographic: # Here we assume that geographic coordinates are automatically 4326 (not quite true)
                fc = list(src)
            else:
                crs_str = to_string(src.crs)
                fc = [feature_transform(x, crs_out='+proj=longlat', crs_in=crs_str)
                      for x in src]

        # Write features to ValidObject table
        def train_obj_builder(x):
            """Build individual ValidObjects
            """
            geom = GEOSGeometry(json.dumps(x['geometry']))
            obj = TrainObject(the_geom=geom,
                              filename=os.path.basename(input_file),
                              creation_year=year)
            return obj

        obj_list = [train_obj_builder(x) for x in fc]
        batch_size = int(len(obj_list)/10)
        TrainObject.objects.bulk_create(obj_list, batch_size=batch_size)

        # Get list of unique tags
        unique_numeric_codes = list(set([x['properties'][field] for x in fc]))

        # Update Tag table using get or create
        def make_tag_tuple(x):
            obj, _ = Tag.objects.get_or_create(numeric_code=x, scheme=scheme)
            return (x, obj)

        tag_dict = dict([make_tag_tuple(x) for x in unique_numeric_codes])

        # Build validClassification object list (valid_tag, valid_object, valid_set)
        def train_class_obj_builder(x):
            """x is a tuple (ValidObject, feature)"""
            tag = tag_dict[x[1]['properties'][field]]
            obj = TrainClassification(predict_tag=tag,
                                      interpret_tag=tag,
                                      train_object=x[0],
                                      training_set=name)
            return obj
        def get_geometry_extent_of_features(fc_input):
            bbox_list = (get_geom_bbox(x['geometry']) for x in fc_input)
            xmin_list, ymin_list, xmax_list, ymax_list = zip(*bbox_list)
            xmin = min(xmin_list)
            ymax  = max(ymax_list)
            xmax = max(xmax_list)
            ymin = min(ymin_list)
            bbox = (xmin, ymin, xmax, ymax)
            p1 = Point(xmin, ymax)
            p2 = Point(xmax, ymax)
            p3 = Point(xmax, ymin)
            p4 = Point(xmin, ymin)
            p1 = shape(mapping(p1))
            p2 = shape(mapping(p2))
            p3 = shape(mapping(p3))
            p4 = shape(mapping(p4))
            np1 = (p1.coords.xy[0][0], p1.coords.xy[1][0])
            np2 = (p2.coords.xy[0][0], p2.coords.xy[1][0])
            np3 = (p3.coords.xy[0][0], p3.coords.xy[1][0])
            np4 = (p4.coords.xy[0][0], p4.coords.xy[1][0])
            bb_polygon = Polygon([np1, np2, np3, np4])
            return GEOSGeometry(json.dumps(mapping(bb_polygon)))
        def catalog_training_set_and_odc_tiles_for_app_builder(fc_input):
            from madmex.models import CatalogTrainingSetForApp, TrainingSetAndODCTilesForApp
            tset_for_app = CatalogTrainingSetForApp.objects.get_or_create(name=name)[0]
            geom = get_geometry_extent_of_features(fc_input)
            tset_and_odc_tiles = TrainingSetAndODCTilesForApp.objects.get_or_create(training_set=tset_for_app,
                                                                                    the_geom = geom,
                                                                                    odc_tile=dc_tile)[0]

            return (tset_for_app, tset_and_odc_tiles)


        def train_class_labeled_by_app_obj_builder(x, training_set_for_app, training_set_and_odc_tiles):
            """x is a tuple (ValidObject, feature)"""
            from madmex.models import Users, Institutions
            user_dummy = Users()
            institution_dummy = Institutions()
            if train_interpreted and field_interpreted is not None and scheme_interpreted is not None and dc_tile is not None:
                if Tag.objects.filter(scheme=scheme_interpreted).first() is not None:
                    try:
                        tag_interpreted = Tag.objects.get(pk=x[1]['properties'][field_interpreted], scheme=scheme_interpreted)
                    except:
                        tag_interpreted = Tag()
                else:
                    logger.info('Couldnt find scheme_interpreted, you need to first run antares register_tag, even so will continue ingestion process')
                    tag_interpreted = Tag()
            else:
                tag_interpreted = Tag()
            tag = tag_dict[x[1]['properties'][field]]
            obj = TrainClassificationLabeledByApp(train_object=x[0],
                                                  training_set=training_set_for_app,
                                                  user=user_dummy,
                                                  institution=institution_dummy,
                                                  interpret_tag=tag_interpreted,
                                                  automatic_label_tag=tag,
                                                  odc_tile=training_set_and_odc_tiles)
            return obj
        if app:
            training_set_for_app, training_set_and_odc_tiles = catalog_training_set_and_odc_tiles_for_app_builder(fc)
            train_class_obj_list = [train_class_labeled_by_app_obj_builder(x,training_set_for_app, training_set_and_odc_tiles) for x in zip(obj_list, fc)]
            TrainClassificationLabeledByApp.objects.bulk_create(train_class_obj_list, batch_size=batch_size)
        else:
            train_class_obj_list = [train_class_obj_builder(x) for x in zip(obj_list, fc)]
            TrainClassification.objects.bulk_create(train_class_obj_list, batch_size=batch_size)
