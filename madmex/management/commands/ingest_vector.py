'''
Created on May 22, 2019
@author: palmoreck
'''

import logging
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

from madmex.management.base import AntaresBaseCommand
from madmex.models import Region, Country
from madmex.util.spatial import feature_transform


logger = logging.getLogger(__name__)

class Command(AntaresBaseCommand):
    help = """
Ingest vector data to tables Country and Region in antares database.
--------------
Example usage:
--------------
antares ingest_vector --file <path-to-file>/my_shapefile.shp --layer-name layer --field field
antares ingest_vector --file <path-to-file>/my_shapefile.shp --layer-name layer --field ''
    """

    def add_arguments(self, parser):
        '''
        Adds arguments for this command.
        '''
        parser.add_argument('-f', '--file',
                            type=str,
                            help='Path of vector file to ingest.')
        parser.add_argument('-l', '--layer-name',
                            type=str,
                            help='Name of layer of vector file')
        parser.add_argument('--field',
                            type=str,
                            help='Name of the vector file field containing the names of the polygons, if file doesnt has this field then name_of_file_<id> is created where <id> is an integer from 0 to number of polygons',
                            required='False')

    def handle(self, **options):
        input_file = options['file']
        field = options['field']
        layer_name = options['layer_name']
        with fiona.open(input_file,
                        encoding='utf-8') as src:
            fc = list(src)
            src_crs = src.crs
            to_string_crs = to_string(src_crs)
            proj_crs = Proj(src.crs)
            if not proj_crs.crs.is_geographic:
                fc_proj = [feature_transform(x,
                                            "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs",
                                            to_string_crs) for x in fc]
            else:
                fc_proj = fc

            shape_list = [shape(feat['geometry']) for feat in fc_proj]
            country_shape = cascaded_union(shape_list)
            country, _ = Country.objects.get_or_create(the_geom=GEOSGeometry(country_shape.wkt),
                                                       name=layer_name)
            for k in range(0,len(fc_proj)):
                shapefile = shape_list[k]
                geom = GEOSGeometry(shapefile.wkt,4326)

                if not field: #needs to generate name for every entry
                    name = layer_name + '_%s'
                    name_feature = name % fc_proj[k]['id']
                else:
                    name_feature = fc_proj[k]['properties'][field].replace(" ", "_")
                    name_feature_normalized = unicodedata.normalize('NFKD', name_feature).encode('ASCII', 'ignore').decode('utf-8')
                    name_feature = layer_name + '_' + name_feature_normalized
                _ = Region.objects.get_or_create(name=name_feature,
                                                 the_geom=geom,
                                                 country=country)

