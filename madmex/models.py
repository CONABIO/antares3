'''
Created on Dec 12, 2017

@author: agutierrez
'''

from importlib import import_module

from django.contrib.gis.db import models
from django.contrib.gis.utils.layermapping import LayerMapping


class Country(models.Model):
    '''This table stores the geometries for the countries.
    '''
    name = models.CharField(max_length=100, unique=True)
    the_geom = models.MultiPolygonField()
    added = models.DateField(auto_now_add=True)

class Region(models.Model):
    '''This model represents a region that can be related to a Country. 
    '''
    name = models.CharField(max_length=100, unique=True)
    the_geom = models.MultiPolygonField()
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='country', default=None)
    added = models.DateField(auto_now_add=True)

class Footprint(models.Model):
    '''This model represents a footprint. 
    '''
    name = models.CharField(max_length=50, unique=True)
    the_geom = models.PolygonField()
    added = models.DateField(auto_now_add=True)
    
class Order(models.Model):
    '''This model holds the information of usgs orders. 
    '''
    user = models.CharField(max_length=50, default=None)
    order_id = models.CharField(max_length=100, unique=True)
    downloaded = models.BooleanField()
    added = models.DateField(auto_now_add=True)

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