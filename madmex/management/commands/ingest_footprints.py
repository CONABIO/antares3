
'''
Created on Jan 19, 2018

@author: agutierrez
'''

from functools import partial
import logging

from django.contrib.gis.geos.geometry import GEOSGeometry
from django.db.utils import IntegrityError
import fiona
import pyproj
from shapely.geometry.geo import shape
from shapely.ops import transform

from madmex.management.base import AntaresBaseCommand
from madmex.models import Footprint, Country


logger = logging.getLogger(__name__)

class Command(AntaresBaseCommand):
    
    def add_arguments(self, parser):
        '''
        Adds arguments for this command.
        '''
        parser.add_argument('--shape', nargs=1, help='The name of the shape to ingest.')
        parser.add_argument('--sensor', nargs=1, help='The name of the sensor for these footprints.')
        parser.add_argument('--country', nargs=1, help='Country to filter the footprints.')
        parser.add_argument('--column', nargs=1, help='Column of interest in shapefile.')
    
    def handle(self, **options):
        
        shape_file = options['shape'][0]
        sensor = options['sensor'][0]
        country = options['country'][0]
        column = options['column'][0]
        
        country_object = Country.objects.get(name=country)
        

        with fiona.open(shape_file) as source:
            print(source.crs)
            for feat in source:
                s1 = shape(feat['geometry'])
                
                if source.crs['init'] !=  'epsg:4326':
                    project = partial(
                        pyproj.transform,
                        pyproj.Proj(source.crs),
                        pyproj.Proj(init='EPSG:4326'))
                    s2 = transform(project, s1)
                else:
                    s2 = s1
                geom = GEOSGeometry(s2.wkt)
                
                if country_object.the_geom.intersects(geom):
                    name = '%03d%03d' % (feat['properties']['PATH'], feat['properties']['ROW'])
                    if name:
                        try:
                            o = Footprint(the_geom = geom, sensor=sensor, name=name)
                            o.save()
                        except IntegrityError:
                            logger.error('Name %s already exists.' % name)
                