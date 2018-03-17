'''
Created on Jan 22, 2018

@author: agutierrez
'''

from rest_framework import serializers

from madmex.models import TrainObject, Footprint


class ObjectSerializer(serializers.HyperlinkedModelSerializer):
    training_tags = serializers.SlugRelatedField(many=True, read_only=True, slug_field='value')
    
    regions = serializers.StringRelatedField(many=True)
    ones = serializers.SerializerMethodField('get_one')
    
    def get_one(self, foo):
        return 1
    class Meta:
        model = TrainObject
        fields = ('added', 'id', 'regions', 'training_tags', 'the_geom', 'ones')
        
class FootprintSerializer(serializers.ModelSerializer):
    

    class Meta:
        model = Footprint
        fields = ('name', 'the_geom', 'sensor')

        