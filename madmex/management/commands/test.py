'''
Created on Jan 17, 2018

@author: agutierrez
'''
from _collections import OrderedDict
import datetime
import json
import os
import re

from sentinelsat.sentinel import geojson_to_wkt, read_geojson, SentinelAPI

from madmex.management.base import AntaresBaseCommand
from madmex.models import Region, Footprint
from madmex.settings import SCIHUB_USER, SCIHUB_PASSWORD
from madmex.util.local import basename


def to_aws_format(tile, date_object):
    
    pattern = re.compile(r'([0-9]{1,2})([A-Z])([A-Z]{2})')
    match = pattern.match(tile)
    utm_code = match.group(1)
    latitude_band = match.group(2)
    square = match.group(3)
    year = date_object.year
    month = date_object.month
    day = date_object.day
    
    path = 's3://sentinel-s2-l1c/tiles/%s/%s/%s/%s/%s/%s/0/' % (utm_code, latitude_band, square, year, month, day)
    
    return path

class Command(AntaresBaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('-d', '--dest',
                            type=str,
                            required=True,
                            help='Directory containing the scenes or tiles for which metadata have to be generated')
        parser.add_argument('-r', '--region',
                            type=str,
                            required=True,
                            help='Directory containing the scenes or tiles for which metadata have to be generated')
    def handle(self, **options):
        destination = options['dest']
        region = options['region']
        print(destination)
        print(region)
        
        
        
        
        
        api = SentinelAPI(SCIHUB_USER, SCIHUB_PASSWORD)
        
        
        
        region = Region.objects.get(name=region)
        
        tiles = [f.name for f in Footprint.objects.filter(the_geom__intersects=region.the_geom, sensor='sentinel')]
        
        print(tiles)
        
        footprint = region.the_geom.convex_hull.wkt
        
        # Will query filtering using the convex hull but then we will filter the retrieved tiles using the polygon
        
        ##footprint = geojson_to_wkt(read_geojson('/Users/agutierrez/Documents/baja.geojson'))
        products = api.query(footprint,date=('20180101','NOW'),platformname='Sentinel-2')
    
        print(type(products))

        downloaded = []
        final = []
        
        for file in os.listdir('/Users/agutierrez/Development/antares3'):
            if file.endswith('.zip'):
                downloaded.append(basename(file, False))
        
        
        print(len(downloaded))
        
        for key, value in products.items():
            
            #
            
            if value['tileid'] in tiles:
                final.append(to_aws_format(value['tileid'], value['datatakesensingstart']))
        
        print(len(final))
        for f in final:
            print(f)
        #api.download_all(final)
        
        #print(json.dumps(value,indent=4))
        
        #for product in products:
            
        #   