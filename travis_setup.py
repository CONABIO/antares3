#!/usr/bin/env python

import os

### 1 - datacube database requires a configuration file
dc_conf = ['[datacube]',
           'db_database: datacube',
           'db_hostname: localhost',
           'db_username: postgres',
           'db_password: postgres']

with open(os.path.expanduser('~/.datacube.conf'), 'w') as dst:
    for line in dc_conf:
        dst.write('%s\n' % line)

with open(os.path.expanduser('~/.antares'), 'w') as dst:
    dst.write('DEBUG=False')
