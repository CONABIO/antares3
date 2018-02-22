'''
Created on Jan 17, 2018

@author: agutierrez
'''
import os
import unittest

from sklearn_xarray.data import load_digits_dataarray
from sklearn_xarray.target import Target

from madmex.modeling.supervised import rf
from madmex.settings import TEMP_DIR


class TestModel(unittest.TestCase):


    def testModelRandomForest(self):
        X = load_digits_dataarray()
        y = Target(coord='digit')(X)
        model_path = TEMP_DIR
        my_model = rf.Model()
        my_model.fit(X,y) 
        my_model.save(model_path)
        model_file = os.path.join(model_path,'%s.pkl' % my_model.model_name)
        self.assertTrue(os.path.isfile(model_file))
        os.remove(model_file)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()