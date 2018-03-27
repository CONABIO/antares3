import os
import unittest
from pprint import pprint

import fiona
import xarray as xr
import numpy as np
from madmex.overlay.extractions import zonal_stats_pandas

path = os.path.dirname(__file__)
test_shp = os.path.join(path, 'data/test_lc_class.shp')
test_nc = os.path.join(path, 'data/test_data.nc')

dataset = xr.open_dataset(test_nc)
with fiona.open(test_shp) as src:
    fc = [x for x in src]


class TestExtract(unittest.TestCase):
    def test_extract_groupby(self):
        X, y = zonal_stats_pandas(dataset, fc, field='class', aggregation='mean',
                                  categorical_variables='cover')
        expected_X = np.array([[4., 22., 1],
                              [23., 3., 2]], dtype='float32')
        self.assertListEqual(y, ['water', 'forest'])
        np.testing.assert_allclose(X, expected_X)

