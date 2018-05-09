'''
Created on Jan 22, 2018

@author: agutierrez
'''

from rest_framework import serializers

from madmex.models import Footprint, TrainClassification, \
    PredictClassification, Tag


class ObjectSerializer(serializers.ModelSerializer):

    class Meta:
        model = TrainClassification
        fields = ('pk', 'interpret_tag', 'train_object')
        depth = 1
        
class FootprintSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Footprint
        fields = ('name', 'the_geom', 'sensor')
        
class TagSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Tag
        fields = '__all__'

class PredictSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = PredictClassification
        fields = ('id', 'tag_id', 'predict_object', 'name')
        depth = 1
        