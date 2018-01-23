'''
Created on Jan 22, 2018

@author: agutierrez
'''

from rest_framework import serializers
from madmex.models import Object


class ObjectSerializer(serializers.HyperlinkedModelSerializer):
    tags = serializers.StringRelatedField(many=True)
    regions = serializers.StringRelatedField(many=True)
    class Meta:
        model = Object
        fields = ('added', 'id', 'regions', 'tags', 'the_geom')
        