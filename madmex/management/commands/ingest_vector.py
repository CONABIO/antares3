'''
Created on May 22, 2019
@author: palmoreck
'''

import json
from pprint import pprint
import sys
import unicodedata

import fiona
from shapely.geometry import shape, mapping
from shapely.ops import cascaded_union
from django.contrib.gis.geos import GEOSGeometry
from fiona.crs import to_string, from_epsg
from fiona.transform import transform_geom
from pyproj import Proj

from madmex.models import Region, Country
from madmex.util.spatial import feature_transform


logger = logging.getLogger(__name__)

class Command(AntaresBaseCommand):
    help = """
Ingest vector data to tables Country and Region in antares database.
--------------
Example usage:
--------------
antares ingest_vector --file <path-to-file>/my_shapefile.shp --column_name
    """
    
    def add_arguments(self, parser):
        '''
        Adds arguments for this command.
        '''
        parser.add_argument('--file', nargs=1, help='Name of the file to ingest.')
    
    def handle(self, **options):
        
