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
    help = """
This command helps in the ingestion process of new training data. The schema
consideres two classification tags, interpret and predict. Interpret is considered
the main tag. If there is no predict tag, value will be left blank.

--------------
Example usage:
--------------
antares ingest_training --shape /LUSTRE/MADMEX/mapa_referencia_2015/final/aguascalientes/1349025_finalcut.shp 
                        --interpret interpreta 
                        --predict predicted 
                        --scheme madmex 
                        --year 2015 
                        --dataset aguascalientes_example
    """
    
    def add_arguments(self, parser):
        '''
        Adds arguments for this command.
        '''
        parser.add_argument('--shape',
                            type=str,
                            help='The name of the shape to ingest.')
        parser.add_argument('--interpret',
                            type=str,
                            help='The field in the shape used as interpreted tag.')
        parser.add_argument('--predict',
                            type=str,
                            default=None,
                            help='The field in the shape used as predict tag.')
        parser.add_argument('--dataset',
                            type=str,
                            help='Identifier for the rows ingested through this workflow.')
        parser.add_argument('--year',
                            help='The creation year for this objects.')
        parser.add_argument('--scheme',
                            type=str,
                            help='Classification scheme.')
        parser.add_argument('--filter',
                            type=int,
                            default=None,
                            help='Number to filter the shapes.')
    
    def handle(self, **options):
        
        shape_file = options['shape']
        interpret = options['interpret']
        predict = options['predict']
        dataset = options['dataset']
        year = options['year']
        scheme = options['scheme']
        filter = options['filter']
        
        filename = basename(shape_file, False)
        
        if filter is not None and filter <= 1:
            filter = None

        with fiona.open(shape_file) as source:
            project = partial(
                pyproj.transform,
                pyproj.Proj(source.crs),
                pyproj.Proj(init='EPSG:4326'))
            if filter == None:
                object_list = [(TrainObject(the_geom = GEOSGeometry(transform(project, shape(feat['geometry'])).wkt),
                                        filename=filename,
                                        creation_year=year), feat['properties']) for feat in source]
            else:
                object_list = [(TrainObject(the_geom = GEOSGeometry(transform(project, shape(feat['geometry'])).wkt),
                                        filename=filename,
                                        creation_year=year), feat['properties']) for ind, feat in enumerate(source) if ind % filter == 0]
        TrainObject.objects.bulk_create(list(map(lambda x: x[0], object_list)))

        
        train_classification_objects = []
        
        tag_map = {}

        for tup in object_list:
            o = tup[0]
            p = tup[1]
            
            value = p[interpret]
            interpret_tag = tag_map.get(value)                
            if not interpret_tag:                    
                interpret_tag, created = Tag.objects.get_or_create(
                    numeric_code=value,
                    scheme=scheme
                )
                tag_map[value] = interpret_tag
                if created:
                    logger.info('New tag created with values: numeric_code=%s, scheme=%s' % (value, scheme))
            
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
        