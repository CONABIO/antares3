'''
Created on Dec 13, 2017

@author: agutierrez
'''
import os
import shutil
import unittest

from madmex import util
from madmex.settings import TEMP_DIR
from madmex.util.local import aware_make_dir


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

if __name__ == '__main__':
    unittest.main()