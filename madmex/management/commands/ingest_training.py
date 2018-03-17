'''
Created on Jan 19, 2018

@author: agutierrez
'''

from functools import partial
import logging

from django.contrib.gis.geos.geometry import GEOSGeometry
import fiona
import pyproj
from shapely.geometry.geo import shape
from shapely.ops import transform

from madmex.management.base import AntaresBaseCommand
from madmex.models import TrainObject, Tag, TrainClassification
from madmex.util.local import basename


logger = logging.getLogger(__name__)

class Command(AntaresBaseCommand):
    
    def add_arguments(self, parser):
        '''
        Adds arguments for this command.
        '''
        parser.add_argument('--shape', nargs=1, help='The name of the shape to ingest.')
        parser.add_argument('--interpret', nargs='?', default=None, help='The name of the shape to ingest.')
        parser.add_argument('--predict', nargs=1, help='The name of the shape to ingest.')
        parser.add_argument('--dataset', nargs=1, help='The name of the shape to ingest.')
        parser.add_argument('--year', nargs=1, help='The creation year for this objects.')
        parser.add_argument('--scheme', nargs=1, help='Classification scheme.')
    
    def handle(self, **options):
        
        shape_file = options['shape'][0]
        interpret = options['interpret']
        predict = options['predict'][0]
        dataset = options['dataset'][0]
        year = options['year'][0]
        scheme = options['scheme'][0]
        
        filename = basename(shape_file, False)

        with fiona.open(shape_file) as source:
            project = partial(
                pyproj.transform,
                pyproj.Proj(source.crs),
                pyproj.Proj(init='EPSG:4326'))
            object_list = [(TrainObject(the_geom = GEOSGeometry(transform(project, shape(feat['geometry'])).wkt),
                                        filename=filename,
                                        creation_year=year), feat['properties']) for feat in source]

        TrainObject.objects.bulk_create(list(map(lambda x: x[0], object_list)))

        
        train_classification_objects = []
        
        tag_map = {}

        for tup in object_list:
            o = tup[0]
            p = tup[1]
            
            value = p[interpret]
            interpret_tag = tag_map.get(value)                
            if not interpret_tag:
                try:
                    interpret_tag = Tag.objects.get(numeric_code=value, scheme=scheme)
                except Tag.DoesNotExist:
                    interpret_tag = Tag.objects.get(numeric_code=value, scheme=scheme)
                    interpret_tag.save()
                tag_map[value] = interpret_tag
            
            predict_tag = None
            if predict is not None:
                value = p[predict]
                predict_tag = tag_map.get(value)
                if not predict_tag:
                    try:
                        predict_tag = Tag.objects.get(numeric_code=value, scheme=scheme)
                    except Tag.DoesNotExist:
                        predict_tag = Tag.objects.get(numeric_code=value, scheme=scheme)
                        predict_tag.save()
                    tag_map[value] = predict_tag
            
            train_classification_objects.append(TrainClassification(train_object=o,
                                                           predict_tag=predict_tag,
                                                           interpret_tag=interpret_tag,
                                                           training_set=dataset))
        TrainClassification.objects.bulk_create(train_classification_objects)
        