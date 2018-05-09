'''
Created on Dec 13, 2017

@author: agutierrez
'''
import os
import shutil
import unittest
from datetime import datetime
import datetime as dt

from madmex import util
import madmex.util.xarray as xutils
from madmex.settings import TEMP_DIR
from madmex.util.local import aware_make_dir
from madmex.util import parser_extra_args

import numpy as np
import xarray as xr


class TestUtil(unittest.TestCase):

    def test_basename(self):
        filename = '/fake/file/path/to/file.txt'
        self.assertEqual(util.local.basename(filename), 'file.txt')
        self.assertEqual(util.local.basename(filename, True), 'file.txt')
        self.assertEqual(util.local.basename(filename, False), 'file')
        self.assertEqual(util.local.basename(filename), 'file.txt')
        self.assertEqual(util.local.basename(filename, suffix=True), 'file.txt')
        self.assertEqual(util.local.basename(filename, suffix=False), 'file')

    def test_aware_make_dir(self):
        name = os.path.join(TEMP_DIR, 'this_is_a_test')
        aware_make_dir(name)
        self.assertTrue(os.path.exists(name))
        shutil.rmtree(name)
        self.assertFalse(os.path.exists(name))

    def test_filter_files_from_folder(self):
        directory = os.path.join(TEMP_DIR, 'this_is_a_test')
        aware_make_dir(directory)
        files = ['file1.txt', 'file2.txt', 'image1.csv']
        for f in files:
            with open(os.path.join(directory, f), 'w') as temp_file:
                temp_file.write('some text')
        print(util.local.filter_files_from_folder(directory, r'.*\.txt'))
        self.assertEqual(len(util.local.filter_files_from_folder(directory, r'.*\.txt')), 2)
        self.assertEqual(len(util.local.filter_files_from_folder(directory, r'.*\.csv')), 1)
        self.assertEqual(util.local.filter_files_from_folder(directory, r'.*\.csv')[0], 'image1.csv')
        shutil.rmtree(directory)

    def test_xutils(self):
        # Build test data
        arr = np.array([1,2,-9999], dtype=np.int16)
        arr_float = np.array([1,2,-9999], dtype=np.float)
        date_list = [datetime(2018, 1, 1) + dt.timedelta(delta) for delta in range(3)]
        xarr = xr.DataArray(arr, dims=['time'], coords={'time': date_list},
                                                attrs={'nodata': -9999})
        xarr_float = xr.DataArray(arr_float, dims=['time'], coords={'time': date_list},
                                  attrs={'nodata': -9999})
        xset_in_int = xr.Dataset({'blue': xarr, 'green': xarr, 'red': xarr})
        xset_in_float = xr.Dataset({'blue': xarr_float, 'green': xarr_float,
                                    'red': xarr_float})
        # Round trip int to float (with nodata replaced by nan) and back to int
        xset_out_float_0 = xset_in_int.apply(func=xutils.to_float, keep_attrs=True)
        xset_out_float_1 = xset_in_float.apply(func=xutils.to_float, keep_attrs=True)
        xset_out_int = xset_out_float_0.apply(xutils.to_int, keep_attrs=True)
        self.assertIsNone(xr.testing.assert_equal(xset_in_int, xset_out_int))
        self.assertIsNone(xr.testing.assert_allclose(xset_out_float_0, xset_out_float_1))

    def test_parse_extra_args(self):
        extra_args = ['arg0=madmex', 'arg1=True', 'arg2=False', 'arg3=12',
                      'arg4=12.3']
        transformed_args = {'arg0': 'madmex', 'arg1': True, 'arg2': False,
                            'arg3': 12, 'arg4': 12.3}
        self.assertEqual(parser_extra_args(extra_args), transformed_args)
if __name__ == '__main__':
    unittest.main()
