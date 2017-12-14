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
    name = models.CharField(max_length=50)
    the_geom = models.MultiPolygonField()

class Region(models.Model):
    '''This model represents a region that can be related to a Country. 
    '''
    name = models.CharField(max_length=50)
    the_geom = models.MultiPolygonField()
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='country', default=None)

class Footprint(models.Model):
    '''This model represents a footprint. 
    '''
    name = models.CharField(max_length=50)
    the_geom = models.PolygonField()

def ingest_countries_from_shape(path):
    '''Ingestion function for countries to database.

    This function should be executed only once when the system is configured:

    Args:
        path (str): The path to the shape file.

    '''
    mapping = {
        'name' : 'NAME',
        'the_geom' : 'MULTIPOLYGON'
    }
    layer_mapping = LayerMapping(
        Country, path, mapping,
        transform=False, encoding='UTF-8 ',
    )
    layer_mapping.save()