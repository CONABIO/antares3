#!/usr/bin/env python

"""
Author: Loic Dutrieux
Date: 2017-12-13
Purpose: Write static configuration files written in the library to a standard
    system location
"""
import os
import pkg_resources as pr
from distutils.dir_util import copy_tree

from madmex.management.base import AntaresBaseCommand

class Command(AntaresBaseCommand):
    help = """
Command line to write configuration files (used for data indexing and ingestion into the datacube)
to a standard system location (~/.config/madmex) or a user defined location

--------------
Example usage:
--------------
# Write configuration files to standard location
antares conf_setup

# Write config files to user defined location
antares conf_setup --dir /home/user/madmex_conf_files
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
        conf_dir = pr.resource_filename('madmex', 'conf')
        copy_tree(conf_dir, dir_out)
