'''
Created on Apr 27, 2018

@author: agutierrez
'''

import logging
import os
from xml.dom.minidom import parse

from django.contrib.gis.geos.geometry import GEOSGeometry
import fiona
from jinja2.environment import Environment
from jinja2.loaders import PackageLoader
import pyproj
import rasterio
from rasterio.features import shapes
from shapely.ftools import partial
from shapely.geometry.geo import shape, mapping
from shapely.ops import transform
import shapely.wkt

from madmex.management.base import AntaresBaseCommand
from madmex.models import Country, TrainObject, Tag, TrainClassification
from madmex.settings import BASE_DIR
from madmex.util.local import basename


logger = logging.getLogger(__name__)

class Command(AntaresBaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--scheme', nargs=1, help='The name of the raster to process.')

    def handle(self, *args, **options):
        scheme = options['scheme'][0]
        
        queryset = Tag.objects.filter(scheme=scheme)
        
        
        if queryset.count() > 0:
            logger.info('Scheme exists.')
            template_directory = os.path.join(BASE_DIR, 'madmex/templates')
            template = os.path.join(template_directory,'vector_style_template.qml')
            xml_tree = parse(template)
            
            print(dir(xml_tree))
        else:
            logger.info('Scheme does not exists.')