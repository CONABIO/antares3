'''
Created on Jan 22, 2018

@author: agutierrez
'''
from rest_framework import viewsets

from madmex.models import Object
from madmex.rest.serializers import ObjectSerializer


class ObjectViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = Object.objects.all()
    serializer_class = ObjectSerializer
        