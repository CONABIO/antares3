import os
from .landsat_8_madmex_001 import run as landsat_8_madmex_001
from .landsat_8_ndvi_mean import run as landsat_8_ndvi_mean

"""
Adding recipes:
    - Write the recipe function. The function should accept 4 arguments
    (tile, gwf, center_dt, path). tile is a tuple as returned by gwd.list_cells(),
    gwf is a GridWorkflow instance, center_dt is a datetime, and path is a string. The function
    should write to a netcdf file and return the path (str) of the file created.
    - Write a product configuration file and place it in madmex/conf/indexing
    - Add an entry to the RECIPES dictionary below (product is the datacube product to
    query in the command line (apply_recipe), and that will be passed to the function
    through the tile= argument)
    - Add a meaningful example to the docstring of the apply_recipe command line
"""

RECIPES = {
    'landsat_8_madmex_001': {
        'product': 'ls8_espa_mexico',
        'fun': landsat_8_madmex_001,
        'config_file': os.path.expanduser('~/.config/madmex/indexing/landsat_8_madmex_001.yaml'),
    },
    'landsat_8_ndvi_mean': {
        'product': 'ls8_espa_mexico',
        'fun': landsat_8_ndvi_mean,
        'config_file': os.path.expanduser('~/.config/madmex/indexing/landsat_8_ndvi_mean.yaml'),
    },
}
