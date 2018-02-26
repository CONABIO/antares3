'''
Created on Jan 17, 2018

@author: agutierrez
'''
import os

from sklearn.ensemble.forest import RandomForestClassifier
from sklearn.externals import joblib

from madmex.modeling import BaseModel


class Model(BaseModel):
    '''
    classdocs
    '''

    def __init__(self):
        '''
        '''
        self.model = RandomForestClassifier(n_estimators=150,n_jobs=8)
        self.model_name = 'rf'

    def fit(self, X, y):
        self.model.fit(X,y)

    def predict(self, X):
        '''
        Simply passes down the prediction from the underlying model.
        '''
        return self.model.predict(X)

    def score(self, X, y):
        '''
        Test the model given a dataset and a target vector.

        This method applies the model that this object represents to the given dataset using
        the response variable y. It is a measure of the accuracy of the trained model. Usually
        the orginal dataset should be splitted in training and testing subsets to cross validate
        the model.
        '''
        return self.model.score(X,y)
