'''
Created on Jan 22, 2018

@author: agutierrez
'''
import json

from django.contrib.gis.geos.geometry import GEOSGeometry
from django.contrib.gis.geos.polygon import Polygon
from django.http.response import JsonResponse
from rest_framework import viewsets
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import RetrieveModelMixin
import xarray

from madmex.models import TrainObject, Footprint
from madmex.orm.queries import get_datacube_objects, get_datacube_chunks
from madmex.rest.serializers import ObjectSerializer, FootprintSerializer


class ObjectViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """

    def retrieve(self, request, *args, **kwargs):
        return RetrieveModelMixin.retrieve(self, request, *args, **kwargs)


    def get_queryset(self):
        
        
        wkt = self.request.query_params.get('polygon', None)
        
        print(wkt)
        
        queryset = GenericAPIView.get_queryset(self)
        
        if wkt is not None:
            
            polygon = GEOSGeometry(wkt)
            queryset = queryset.filter(the_geom__intersects=polygon)

        return queryset

    #pagination_class = None       
    queryset = TrainObject.objects.all()
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