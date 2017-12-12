'''
Created on Dec 12, 2017

@author: agutierrez
'''

from django.contrib.gis.db import models


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

def ingest_from_shape(path, table):
    print(__name__)