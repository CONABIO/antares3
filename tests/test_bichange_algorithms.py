import unittest
import pkgutil

import numpy as np
from affine import Affine
import madmex.lcc.bitemporal as bitemp

# Load all models in a list
algo_list = []
for importer, modname, ispakg in pkgutil.iter_modules(bitemp.__path__):
    m = importer.find_module(modname).load_module(modname)
    algo_list.append(m.BiChange)

# Test data
arr0_3D = np.random.randint(1,2000,30000).reshape((3, 100, 100))
arr1_3D = np.random.randint(1,2000,30000).reshape((3, 100, 100))
arr0_2D = np.random.randint(1,2000,10000).reshape((100, 100))
arr1_2D = np.random.randint(1,2000,10000).reshape((100, 100))
identity = Affine.identity()
proj_0 = '+proj=longlat'

class TestBiChange(unittest.TestCase):

    def test_change_batch_3D(self):
        for Algorithm in algo_list:
            Change_0 = Algorithm(arr0_3D, identity, proj_0)
            Change_1 = Algorithm(arr1_3D, identity, proj_0)
            Change_0.run(Change_1)
            self.assertEqual(Change_0.change_array.shape, (100, 100))
            self.assertEqual(Change_0.change_array.dtype, np.uint8)

    def test_change_batch_2D(self):
        for Algorithm in algo_list:
            Change_0 = Algorithm(arr0_2D, identity, proj_0)
            Change_1 = Algorithm(arr1_2D, identity, proj_0)
            Change_0.run(Change_1)
            self.assertEqual(Change_0.change_array.shape, (100, 100))
            self.assertEqual(Change_0.change_array.dtype, np.uint8)


if __name__ == "__main__":
    unittest.main()
