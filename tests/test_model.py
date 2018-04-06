'''
Created on Jan 17, 2018

@author: agutierrez
'''
import os
import unittest
import pkgutil

from madmex.settings import TEMP_DIR
from madmex.util import randomword
from sklearn.datasets import make_classification
import numpy as np

import madmex.modeling.supervised as modeling

# Load all models in a list
model_list = []
for importer, modname, ispakg in pkgutil.iter_modules(modeling.__path__):
    m = importer.find_module(modname).load_module(modname)
    model_list.append(m.Model)

def init_and_fit(mod, X, y, **kwargs):
    m = mod(**kwargs)
    m.fit(X,y)
    return m

X, y = make_classification(n_samples=10000, n_features=10,
                           n_classes=5, n_informative=6)
# The categorical feature
X[:,1] = np.random.randint(1, 10, (10000))


class TestModel(unittest.TestCase):

    def test_models_batch(self):
        fitted_models_simple = [init_and_fit(x, X, y) for x in model_list]
        fitted_models_encode = [init_and_fit(x, X, y, **{'categorical_features': [1]})
                                for x in model_list]
        for model in fitted_models_simple:
            filename = os.path.join(TEMP_DIR, '%s.pkl' % randomword(5))
            model.save(filename)
            self.assertTrue(os.path.isfile(filename))
            pred = model.predict([[1,2,3,4,5,6,7,8,9,10],
                                  [10,9,8,7,6,5,4,3,2,1]])
            conf = model.predict_confidence([[1,2,3,4,5,6,7,8,9,10],
                                             [10,9,8,7,6,5,4,3,2,1]])
            self.assertTrue(len(pred) == 2)
            self.assertTrue(len(conf) == 2)
        for model in fitted_models_encode:
            pred = model.predict([[1,2,3,4,5,6,7,8,9,10],
                                  [10,9,8,7,6,5,4,3,2,1]])
            conf = model.predict_confidence([[1,2,3,4,5,6,7,8,9,10],
                                             [10,9,8,7,6,5,4,3,2,1]])
            self.assertTrue(len(pred) == 2)
            self.assertTrue(len(conf) == 2)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
