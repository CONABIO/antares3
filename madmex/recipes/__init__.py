import os
from .landsat_madmex_001 import run as landsat_madmex_001
from .landsat_madmex_002 import run as landsat_madmex_002
from .landsat_colombia_001 import run as landsat_colombia_001
from .landsat_belize_001 import run as landsat_belize_001
from .landsat_guyana_001 import run as landsat_guyana_001
from .landsat_ndvi_mean import run as landsat_ndvi_mean
from .s2_20m_001 import run as s2_20m_001
from .s2_10m_ndvi_mean_001 import run as s2_10m_ndvi_mean_001
from .s2_10m_scl_ndvi_mean_001 import run as s2_10m_scl_ndvi_mean_001
from .s1-2_10m_001 import run as s1-2_10m_001

"""
Adding recipes:
    - Write the recipe function. The function should accept 3 arguments
    (tile, center_dt, path). tile is a tuple as returned by gwd.list_cells(),
    center_dt is a datetime, and path is a string. The function
    should write to a netcdf file and return the path (str) of the file created.
    - Write a product configuration file and place it in madmex/conf/indexing
    - Add an entry to the RECIPES dictionary below (product is the datacube product to
    query in the command line (apply_recipe), and that will be passed to the function
    through the tile= argument)
    - Add a meaningful example to the docstring of the apply_recipe command line
"""

RECIPES = {
    'landsat_madmex_001': {
        'product': ['ls8_espa_mexico', 'ls5_espa_mexico'],
        'fun': landsat_madmex_001,
        'config_file': os.path.expanduser('~/.config/madmex/indexing/landsat_madmex_001.yaml'),
    },
    'landsat_madmex_002': {
        'product': ['ls8_espa_mexico'],
        'fun': landsat_madmex_002,
        'config_file': os.path.expanduser('~/.config/madmex/indexing/landsat_madmex_002.yaml'),
    },
    'landsat_colombia_001': {
        'product': ['ls8_espa_colombia', 'ls7_espa_colombia', 'ls5_espa_colombia'],
        'fun': landsat_colombia_001,
        'config_file': os.path.expanduser('~/.config/madmex/indexing/landsat_colombia_001.yaml'),
    },
    'landsat_belize_001': {
        'product': ['ls8_espa_belize'],
        'fun': landsat_belize_001,
        'config_file': os.path.expanduser('~/.config/madmex/indexing/landsat_belize_001.yaml'),
    },
    'landsat_guyana_001': {
        'product': ['ls8_espa_guyana'],
        'fun': landsat_guyana_001,
        'config_file': os.path.expanduser('~/.config/madmex/indexing/landsat_guyana_001.yaml'),
    },
    'landsat_ndvi_mean': {
        'product': ['ls8_espa_mexico'],
        'fun': landsat_ndvi_mean,
        'config_file': os.path.expanduser('~/.config/madmex/indexing/landsat_ndvi_mean.yaml'),
    },
    's2_20m_001': {
        'product': ['s2_l2a_20m_mexico'],
        'fun': s2_20m_001,
        'config_file': os.path.expanduser('~/.config/madmex/indexing/s2_20m_001.yaml'),
    },
    's2_20m_s3_001': {
        'product': ['s2_l2a_20m_s3_mexico'],
        'fun': s2_20m_001,
        'config_file': os.path.expanduser('~/.config/madmex/indexing/s2_20m_s3_001.yaml'),
    },
    's2_10m_ndvi_mean_001': {
        'product': ['s2_l2a_10m_mexico'],
        'fun': s2_10m_ndvi_mean_001,
        'config_file': os.path.expanduser('~/.config/madmex/indexing/s2_10m_ndvi_mean_001.yaml'),
    },
    's2_10m_scl_ndvi_mean_001': {
        'product': ['s2_l2a_10m_scl_s3_mexico'],
        'fun': s2_10m_scl_ndvi_mean_001,
        'config_file': os.path.expanduser('~/.config/madmex/indexing/s2_10m_ndvi_mean_001.yaml'),
    },
    's1-2_10m_001': {
        'product': ['s2_l2a_20m_s3_mexico', 's1_snappy_vh_vv_mexico'],
        'fun': s1-2_10m_001,
        'config_file': os.path.expanduser('~/.config/madmex/indexing/s1-2_10m_001.yaml'),
    }
}
