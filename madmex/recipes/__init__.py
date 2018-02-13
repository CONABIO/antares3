import os
from .madmex_001 import run as madmex_001
from .ndvi_mean import run as ndvi_mean

RECIPES = {
    'madmex_001': {
        'product': 'ls8_espa_mexico',
        'fun': madmex_001,
        'config_file': os.path.expanduser('~/.config/madmex/indexing/madmex_001.yaml'),
    },
    'ndvi_mean': {
        'product': 'ls8_espa_mexico',
        'fun': ndvi_mean,
        'config_file': os.path.expanduser('~/.config/madmex/indexing/ndvi_mean.yaml'),
    },
}
