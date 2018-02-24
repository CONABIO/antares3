'''
Created on Jan 17, 2018

@author: agutierrez
'''
from _collections import OrderedDict
import json
import os

from sentinelsat.sentinel import geojson_to_wkt, read_geojson, SentinelAPI

from madmex.management.base import AntaresBaseCommand
from madmex.models import Region
from madmex.settings import SCIHUB_USER, SCIHUB_PASSWORD
from madmex.util.local import basename


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
        footprint = region.convex_hull()
        
        # Will query filtering using the convex hull but then we will filter the retrieved tiles using the polygon
        
        ##footprint = geojson_to_wkt(read_geojson('/Users/agutierrez/Documents/baja.geojson'))
        products = api.query(footprint,date=('20180101','NOW'),platformname='Sentinel-2')
        
        
        print(type(products))
        
        #api.download_all(products)
        
        downloaded = []
        final = OrderedDict()
        
        for file in os.listdir('/Users/agutierrez/Development/antares3'):
            if file.endswith('.zip'):
                downloaded.append(basename(file, False))
        
        
        print(len(downloaded))
        
        for key, value in products.items():
            print(value)
            if value['title'] not in downloaded:
                final[key] = value
        
        print(len(final))
        #api.download_all(final)
        
        #print(json.dumps(value,indent=4))
        
        #for product in products:
            
        #   