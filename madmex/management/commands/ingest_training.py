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
from madmex.models import Region, Tag, Object


logger = logging.getLogger(__name__)

class Command(AntaresBaseCommand):
    
    def add_arguments(self, parser):
        '''
        Adds arguments for this command.
        '''
        parser.add_argument('--shape', nargs=1, help='The name of the shape to ingest.')
        parser.add_argument('--properties', nargs='*', help='The name of the shape to ingest.')
    
    def handle(self, **options):
        
        shape_file = options['shape'][0]
        properties = options['properties']
        
        print(properties)


        with fiona.open(shape_file) as source:
            for feat in source:
                s1 = shape(feat['geometry'])
                project = partial(
                    pyproj.transform,
                    pyproj.Proj(source.crs),
                    pyproj.Proj(init='EPSG:4326'))
                s2 = transform(project, s1)
                geom = GEOSGeometry(s2.wkt)

 
                
                o = Object(the_geom = geom)
                o.save()
                for region in Region.objects.filter(the_geom__intersects=geom):
                    o.regions.add(region)
                
                for prop in properties:
                    key = prop
                    value = feat['properties'][prop].lower()
                    try:
                        tag = Tag.objects.get(key=key,value=value)
                    except Tag.DoesNotExist:
                        tag = Tag(key=key,value=value)
                        tag.save()
                    o.tags.add(tag)
                o.save()
                