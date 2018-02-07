'''
Created on Jan 22, 2018

@author: agutierrez
'''

from rest_framework import serializers
from madmex.models import Object


class ObjectSerializer(serializers.HyperlinkedModelSerializer):
    tags = serializers.SlugRelatedField(many=True, read_only=True, slug_field='value')
    regions = serializers.StringRelatedField(many=True)
    ones = serializers.SerializerMethodField('get_one')
    
    def get_one(self, foo):
        return 1
    class Meta:
        model = Object
        fields = ('added', 'id', 'regions', 'tags', 'the_geom', 'ones')
        