'''
Created on Jan 17, 2018

@author: agutierrez
'''
import unittest

class TestModel(unittest.TestCase):


    def testTestingIngestion(self):
        import shapely
        import fiona
        import pyproj
        # This test is just a stub. A database created specifically for testing purposes
        # must be created. It should be accessible from travis. Maybe Amazon? it shouldn't
        # very large.
        self.assertTrue(True)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()