#!/usr/bin/env python

"""
Author: Loic Dutrieux
Date: 2017-12-13
Purpose: Write static configuration files written in the library to a standard
    system location
"""
import os
import pkg_resources as pr
from shutil import copytree

from madmex.management.base import AntaresBaseCommand

class Command(AntaresBaseCommand):
    help = """
Command line to write configuration files (used for data indexing and ingestion into the datacube)
to a standard system location (~/.config/madmex) or a user defined location

--------------
Example usage:
--------------
# Write configuration files to standard location
python madmex.py conf_setup

# Write config files to user defined location
python madmex.py conf_setup --dir /home/user/madmex_conf_files
"""
    def add_arguments(self, parser):
        parser.add_argument('-d', '--dir',
                            type=str,
                            required=False,
                            help='Optional directory where configuration files will be written, the directory will be created if if doesn\'t exist')
        parser.set_defaults(dir=None)

    def handle(self, *args, **options):
        if options['dir'] is not None:
            dir_out = options['dir']
        else:
            dir_out = os.path.expanduser('~/.config/madmex')
        if not os.path.exists(dir_out):
            os.makedirs(dir_out)
        conf_sub_dirs = pr.resource_listdir('madmex', '../conf')
        [copytree(x, dir_out) for x in conf_sub_dirs]

# TODO build string with pr.resource_string


