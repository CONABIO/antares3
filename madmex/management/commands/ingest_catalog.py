'''
Created on Jan 19, 2018

@author: agutierrez
'''

import csv
import logging

from madmex.management.base import AntaresBaseCommand
from madmex.models import Footprint, Scene


logger = logging.getLogger(__name__)

class Command(AntaresBaseCommand):
    
    def add_arguments(self, parser):
        '''
        Adds arguments for this command.
        '''
        parser.add_argument('--file', nargs=1, help='The name of the file to ingest.')
    
    def handle(self, **options):
        
        catalog_file = options['file'][0]
        
        footprints = Footprint.objects.filter(sensor='landsat')
        path_row = {}
        for footprint in footprints:
            path_row[footprint.name] = footprint.id
        scenes = []
        with open(catalog_file, 'rt') as f:
            reader = csv.reader(f)
            headers = next(reader)
            for row in reader:
                name = '%03d%03d' % (int(row[headers.index('path')]), int(row[headers.index('row')]))
                if path_row.get(name, None) and row[headers.index('dayOrNight')].lower() == 'day':
                    scenes.append(Scene(footprint_id=path_row[name],
                                        scene_id=row[headers.index('sceneID')],
                                        landsat_product_id=row[headers.index('LANDSAT_PRODUCT_ID')],
                                        acquisition_date=row[headers.index('acquisitionDate')],
                                        image_quality=int(row[headers.index('imageQuality1')]),
                                        cloud_cover=float(row[headers.index('cloudCoverFull')]),
                                        min_lat=float(row[headers.index('lowerRightCornerLatitude')]),
                                        min_lon=float(row[headers.index('upperLeftCornerLongitude')]),
                                        max_lat=float(row[headers.index('upperLeftCornerLatitude')]),
                                        max_lon=float(row[headers.index('lowerRightCornerLongitude')])))
        Scene.objects.bulk_create(scenes)

        