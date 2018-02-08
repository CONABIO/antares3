'''
Created on Jan 22, 2018

@author: agutierrez
'''
from django.contrib.gis.geos.geometry import GEOSGeometry
from django.contrib.gis.geos.polygon import Polygon
from rest_framework import viewsets
from rest_framework.generics import GenericAPIView

from madmex.models import TrainObject
from madmex.rest.serializers import ObjectSerializer


class ObjectViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """

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
        