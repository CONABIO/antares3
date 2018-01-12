'''
Created on Jan 9, 2018

@author: agutierrez
'''

from django.contrib.gis import admin
from .models import Footprint


admin.site.register(Footprint, admin.GeoModelAdmin)
