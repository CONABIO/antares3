'''
Created on Dec 12, 2017

@author: agutierrez
'''

from glob import glob
import logging
import os
import shutil

from django.core.management import call_command

from madmex.management.base import AntaresBaseCommand
from madmex.models import ingest_countries_from_shape, ingest_states_from_shape
from madmex.settings import TEMP_DIR, BIS_LICENSE
from madmex.util.local import aware_download, extract_zip, aware_make_dir, \
    filter_files_from_folder
from madmex.util import fill_and_copy
from madmex.settings import INGESTION_PATH
import pkg_resources as pr


logger = logging.getLogger(__name__)

class Command(AntaresBaseCommand):
    help = '''
Command line to setup the antares system directly following a fresh installation or update an existing setup.
Standard setup consists in:
    - Creating tables required by antares in the specified database. Can be disabled
    using the --no-create-tables flag.
    - Downloading and ingesting in the database countriy and regions administrative boundaries
    of the selected countries. --countries argurment can be left empty in which case no countries are ingested
    - Writing configuration files (used for data indexing and ingestion) to a standard system
    location (~/.config/madmex). Can be disabled using the --no-conf-setup flag
    - Setting or updating BIS licence setup (must be set as a variable in ~/.antares configuration file)

--------------
Example usage:
--------------
# Basic setup with ingestion of mexico and guatemala administrative boundaries
antares init -c mex gtm
'''
    def add_arguments(self, parser):
        parser.add_argument('-c', '--countries',
                            nargs='*',
                            default=None,
                            help='List of country iso codes to ingest')

        parser.add_argument('--no-create-tables', dest='create_tables',
                            action='store_false',
                            help='Disable creation of antares database tables')

        parser.add_argument('--no-conf-setup', dest='conf_setup',
                            action='store_false',
                            help='Disable setup/overwriting of ingestion and indexing configuration files')

    def handle(self, *args, **options):
        # unpack arguments
        countries = options['countries']
        create_tables = options['create_tables']
        conf_setup = options['conf_setup']

        # Create antares tables
        if create_tables:
            call_command('makemigrations', interactive=False)
            call_command('migrate', interactive=False)
        # Ingest geometries of selected countries in database
        if countries is not None:
            for country in countries:
                url = 'http://data.biogeo.ucdavis.edu/data/gadm2.8/shp/%s_adm_shp.zip' % country.upper()
                filepath = aware_download(url, TEMP_DIR)
                unzipdir = extract_zip(filepath, TEMP_DIR)
                country_file = glob(os.path.join(unzipdir, '*adm0.shp'))[0]
                logger.info('This %s shape file will be ingested.' % country_file)
                mapping = {
                    'name' : 'ISO',
                    'the_geom' : 'MULTIPOLYGON'
                }
                ingest_countries_from_shape(country_file, mapping)
                # Ingest first level of adm boundaries (e.g.: regions, states)
                filtered = glob(os.path.join(unzipdir, '*adm1.shp'))
                # First adm level may not exist for small countries/islands
                if len(filtered) > 0:
                    regions_file = filtered[0]
                    logger.info('This %s shape file will be ingested.' % regions_file)
                    mapping = {
                        'country': {'name': 'ISO'},
                        'name' : 'NAME_1',
                        'the_geom' : 'MULTIPOLYGON'
                    }
                    ingest_states_from_shape(regions_file, mapping)

        # Move config files from package to standard system location
        if conf_setup:
            system_config_dir = os.path.expanduser('~/.config/madmex')
            if not os.path.exists(system_config_dir):
                os.makedirs(system_config_dir)
            # INdexing conf files destination
            system_index_dir = os.path.join(system_config_dir, 'indexing')
            if not os.path.exists(system_index_dir):
                os.makedirs(system_index_dir)
            # Ingestion conf files destination
            system_ingest_dir = os.path.join(system_config_dir, 'ingestion')
            if not os.path.exists(system_ingest_dir):
                os.makedirs(system_ingest_dir)
            # Origin root
            conf_dir = pr.resource_filename('madmex', 'conf')
            indexing_origin_dir = os.path.join(conf_dir, 'indexing')
            ingestion_origin_dir = os.path.join(conf_dir, 'ingestion')
            # Copy indexing conf files
            for f in glob(os.path.join(indexing_origin_dir, '*.yaml')):
                shutil.copy2(f, system_index_dir)
            # Template and copy ingestion files
            for f in glob(os.path.join(ingestion_origin_dir, '*.yaml')):
                fill_and_copy(template=f, out_dir=system_ingest_dir,
                              ingestion_path=INGESTION_PATH)

        # Setup bis license
        bis_module = pr.resource_filename('madmex', 'bin/bis')
        license_file = os.path.join(bis_module, 'license.txt')
        with open(license_file, 'w') as dst:
            dst.write(BIS_LICENSE)



