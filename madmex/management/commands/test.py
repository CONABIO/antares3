'''
Created on Jan 17, 2018

@author: agutierrez
'''

import logging
import os


from madmex.management.base import AntaresBaseCommand
from madmex.model.supervised import rf
from madmex.settings import TEMP_DIR


logger = logging.getLogger(__name__)

class Command(AntaresBaseCommand):
    def handle(self, **options):
        print('hello world')
        
        from sklearn_xarray.data import load_digits_dataarray
        from sklearn_xarray import Target
        X = load_digits_dataarray()
        y = Target(coord='digit')(X)
        model_path = TEMP_DIR
        print(model_path)
        my_model = rf.Model()
        my_model.fit(X,y)
        print('Model has been persisted.') 
        my_model.save(model_path)
        del(my_model)
        my_model = rf.Model()
        my_model.load(model_path)
        print('Model has been loaded.')
        print('Model score.')
        print(my_model.score(X,y))
        
        
        
        
        