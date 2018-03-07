'''
Created on Dec 12, 2017

@author: agutierrez
'''

from django.contrib.gis.db import models
from django.contrib.gis.utils.layermapping import LayerMapping


class Country(models.Model):
    '''This table stores the geometries for the countries.
    '''
    name = models.CharField(max_length=100, unique=True)
    the_geom = models.MultiPolygonField()
    added = models.DateTimeField(auto_now_add=True)

class Region(models.Model):
    '''This model represents a region that can be related to a Country. 
    '''
    name = models.CharField(max_length=100, unique=True)
    the_geom = models.MultiPolygonField()
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='country', default=None)
    added = models.DateTimeField(auto_now_add=True)

class Footprint(models.Model):
    '''This model represents a footprint. 
    '''
    name = models.CharField(max_length=50, unique=True)
    the_geom = models.PolygonField()
    sensor = models.CharField(max_length=50, default='')
    added = models.DateTimeField(auto_now_add=True)

class Order(models.Model):
    '''This model holds the information of usgs orders. 
    '''
    user = models.CharField(max_length=50, default=None)
    order_id = models.CharField(max_length=100, unique=True)
    downloaded = models.BooleanField()
    added = models.DateTimeField(auto_now_add=True)

class Model(models.Model):
    '''A database entry that handles the models that we train.
    '''
    name = models.CharField(max_length=100, unique=True)
    path = models.CharField(max_length=300, unique=True)
    training_set = models.CharField(max_length=100)
    recipe = models.CharField(max_length=100, default=None)
    added = models.DateTimeField(auto_now_add=True)

class TrainTag(models.Model):
    '''To keep a deeper control over the tags that we can handle. 
    '''
    key = models.CharField(max_length=50, default=None)
    value = models.CharField(max_length=150, default=None)

    def __unicode__(self):
        return self.value
    
class PredictTag(models.Model):
    '''To keep a the tags assigned to an object by a specific model. 
    '''
    key = models.CharField(max_length=50, default=None)
    value = models.CharField(max_length=150, default=None)
    model = models.ForeignKey(Model, on_delete=models.CASCADE, related_name='model', default=None)

class TrainObject(models.Model):
    '''This table holds objects that will be used for training. They must be related to
    regions and each object should have an assigned tag which is the ground truth for
    it.
    '''
    models.GeometryField
    the_geom = models.GeometryField()
    added = models.DateTimeField(auto_now_add=True)
    regions = models.ManyToManyField(Region)
    training_tags = models.ManyToManyField(TrainTag)
    training_set = models.CharField(max_length=100, default='')

class PredictObject(models.Model):
    '''This table holds objects that will be used for training. They must be related to
    regions and each object should have an assigned tag which is the ground truth for
    it.
    '''
    the_geom = models.GeometryField()
    added = models.DateTimeField(auto_now_add=True)
    regions = models.ManyToManyField(Region)
    prediction_tags = models.ManyToManyField(PredictTag, default=None)
    training_set = models.CharField(max_length=100, default='')

def ingest_countries_from_shape(path, mapping):
    '''Ingestion function for countries to database.

    This function should be executed only once when the system is configured:

    Args:
        path (str): The path to the shape file.

    '''
    layer_mapping = LayerMapping(
        Country, path, mapping,
        transform=False, encoding='UTF-8 ',
    )
    layer_mapping.save()
    
def ingest_states_from_shape(path, mapping):
    '''Ingestion function for countries to database.

    This function should be executed only once when the system is configured:

    Args:
        path (str): The path to the shape file.

    '''
    layer_mapping = LayerMapping(
        Region, path, mapping,
        transform=False, encoding='UTF-8 ',
    )
    layer_mapping.save()
