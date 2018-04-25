'''
Created on Jan 22, 2018

@author: agutierrez
'''
import json
import math
import os

from django.contrib.gis.geos.geometry import GEOSGeometry
from django.contrib.gis.geos.polygon import Polygon
from django.http.response import JsonResponse
from django.template.response import TemplateResponse
from rest_framework import viewsets
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import RetrieveModelMixin
import xarray

from madmex.models import TrainObject, Footprint, TrainClassification, \
    PredictClassification, Tag
from madmex.orm.queries import get_datacube_objects, get_datacube_chunks
from madmex.rest.serializers import ObjectSerializer, FootprintSerializer, \
    PredictSerializer, TagSerializer
from madmex.settings import TEMP_DIR
from madmex.wrappers import predict_object


class ObjectViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """

    def get_queryset(self):    
        wkt = self.request.query_params.get('polygon', None)
        queryset = GenericAPIView.get_queryset(self)
        if wkt is not None:
            polygon = GEOSGeometry(wkt)
            queryset = queryset.filter(train_object__the_geom__intersects=polygon)
        return queryset

    queryset = TrainClassification.objects.all()
    serializer_class = ObjectSerializer

class FootprintViewSet(viewsets.ModelViewSet):
    
    def get_queryset(self):
        """
        Optionally restricts the returned purchases to a given user,
        by filtering against a `username` query parameter in the URL.
        """
        queryset = Footprint.objects.all()
        sensor = self.request.query_params['sensor']
        if sensor is not None:
            queryset = queryset.filter(sensor=sensor)
        return queryset
    
    
    queryset = Footprint.objects.all()
    serializer_class = FootprintSerializer

class PredictViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows the client to query for the predict objects.
    """
    def get_queryset(self):    
        wkt = self.request.query_params.get('polygon', None)
        if wkt is not None:
            polygon = GEOSGeometry(wkt)
            queryset = PredictClassification.objects.filter(predict_object__the_geom__intersects=polygon,
                                                            predict_object__segmentation_information_id=26,
                                                            name='s2_001_jalisco_2017_bis_rf_0')
        else:
            queryset = PredictClassification.objects.all()
        return queryset
    queryset = PredictClassification.objects.all()
    serializer_class = PredictSerializer

def datacube_landsat_tiles(request):
    count = 0
    datacube_landsat_tiles = []
    flag = True
    for s in get_datacube_objects('ls8_espa_mexico_uncompressed'):
        
        if flag:
            print(json.dumps(s, indent=4))
            flag = False
        
        
        chunk = {}
        chunk['id'] = count
        ll = s[0].get('extent').get('coord').get('ll')
        lr = s[0].get('extent').get('coord').get('lr')
        ul = s[0].get('extent').get('coord').get('ul')
        ur = s[0].get('extent').get('coord').get('ur')    
        polygon_wkt = 'SRID=4326;POLYGON ((%s %s, %s %s, %s %s, %s %s, %s %s))' % (ul.get('lon'), ul.get('lat'), ur.get('lon'), ur.get('lat'), lr.get('lon'), lr.get('lat'), ll.get('lon'), ll.get('lat'), ul.get('lon'), ul.get('lat'))
        chunk['the_geom'] = polygon_wkt
        datacube_landsat_tiles.append(chunk)
        count = count + 1
    response = {}
    response['count'] = len(datacube_landsat_tiles)
    response['results'] = datacube_landsat_tiles
    return JsonResponse(response)


def datacube_chunks(request):
    count = 0
    datacube_landsat_tiles = []
    flag = True
    base = '/LUSTRE/MADMEX/tasks/2018_tasks/datacube_madmex/datacube_directories_mapping_docker_2'
    for s in get_datacube_chunks('ls8_espa_mexico_uncompressed'):
        name = '%s%s' % (base, s[0][19:])
        polygon_wkt = 'SRID=4326;%s' %xarray.open_dataset(name).attrs['geospatial_bounds']
        chunk = {}
        chunk['id'] = count
        chunk['the_geom'] = polygon_wkt
        datacube_landsat_tiles.append(chunk)
        count = count + 1
        print(count)
    response = {}
    response['count'] = len(datacube_landsat_tiles)
    response['results'] = datacube_landsat_tiles
    return JsonResponse(response)


def tile_ul(x, y, z):
    n = 2.0 ** z
    lon_deg = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat_deg = math.degrees(lat_rad)
    return  lon_deg,lat_deg

def get_tile(z,x,y):
    xmin,ymin = tile_ul(x, y, z)
    xmax,ymax = tile_ul(x + 1, y + 1, z)
    
    tile = None
    
    tilefolder = "{}/{}/{}".format(TEMP_DIR,z,x)
    tilepath = "{}/{}.pbf".format(tilefolder,y)
    
    
    print(xmin, ymin)
    print(xmax,ymax)
    
    return tile


def training_objects(request, z, x, y):

    print(dir(request))

    print(z,x,y)
    tile = get_tile(z, x, y)
    
    response = {'Hello':'World'}

    
    return JsonResponse(response)

def map(request):
    tags_list = TagSerializer(Tag.objects.all(), many=True).data
    tags = json.dumps(tags_list)
    return TemplateResponse(request, 'map.html', {'tags':tags})

