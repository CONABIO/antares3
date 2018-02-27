'''
Created on Jan 17, 2018

@author: agutierrez
'''
import os
import unittest

from madmex.modeling.supervised import rf
from madmex.settings import TEMP_DIR
from madmex.util import randomword
from sklearn.datasets import make_classification


class TestModel(unittest.TestCase):


    def testModelRandomForest(self):
        X, y = make_classification(n_samples=10000, n_features=10,
                                   n_classes=5, n_informative=5)
        filename = os.path.join(TEMP_DIR, '%s.pkl' % randomword(5))
        my_model = rf.Model()
        my_model.fit(X,y)
        my_model.save(filename)
        self.assertTrue(os.path.isfile(filename))
        os.remove(filename)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
