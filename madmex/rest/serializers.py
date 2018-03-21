'''
Created on Jan 22, 2018

@author: agutierrez
'''

from rest_framework import serializers

from madmex.models import TrainObject, Footprint, TrainClassification


class ObjectSerializer(serializers.ModelSerializer):

    class Meta:
        
        model = TrainClassification
        fields = ('pk', 'interpret_tag', 'train_object')
        depth = 1
        
class FootprintSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Footprint
        fields = ('name', 'the_geom', 'sensor')

        