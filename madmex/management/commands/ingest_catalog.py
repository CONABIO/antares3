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
    help = """
This command ingest metadata from the calalogs found in https://landsat.usgs.gov/download-entire-collection-metadata.
The metadata can be used to perform availability analysis over the entire landsat collection without the need
of performing additional queries to the USGS. This command is prepared to process the catalogs for
Landsat 4-5, Landsat 7 and Landsat 8.

--------------
Example usage:
--------------
antares ingest_catalog --file <path-to-file>/LANDSAT_8_C1.csv
    """
    
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
                                        cloud_cover=float(row[headers.index('cloudCoverFull')]),
                                        cloud_cover_land=float(row[headers.index('CLOUD_COVER_LAND')]),
                                        min_lat=float(row[headers.index('lowerRightCornerLatitude')]),
                                        min_lon=float(row[headers.index('upperLeftCornerLongitude')]),
                                        max_lat=float(row[headers.index('upperLeftCornerLatitude')]),
                                        max_lon=float(row[headers.index('lowerRightCornerLongitude')])))
        Scene.objects.bulk_create(scenes)

        