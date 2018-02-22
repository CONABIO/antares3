'''
Created on Jan 17, 2018

@author: agutierrez
'''
import os

from sklearn.ensemble.forest import RandomForestClassifier
from sklearn.externals import joblib
from sklearn_xarray.common.wrappers import wrap

from madmex.modeling import BaseModel


class Model(BaseModel):
    '''
    classdocs
    '''

    def __init__(self):
        '''The sklearn is wrapped using the decorator provided by the sklearn_xarray
        framework.
        TODO:Need to change the way in which the parameters are given, right now
        parameters are fixed.
        '''
        self.model = wrap(RandomForestClassifier(n_estimators=150,n_jobs=8))
        self.model_name = 'rf'

    def fit(self, X, y):
        self.model.fit(X,y)

    def predict(self, X):
        '''
        Simply passes down the prediction from the underlying model.
        '''
        return self.model.predict(X)

    def save(self, filepath):
        '''
        Persists the trained model to a file.
        
        The model is saved into a file using pickle format.
        TODO:Ingest the model into the database for later reference and use.
        '''
        joblib.dump(self.model, os.path.join(filepath,'%s.pkl' % self.model_name)) 

    def load(self, filepath):
        '''
        Loads an already train model from a file to perform predictions.
        
        The model is loaded from a file written by this same interface. Look into the save
        method of this object.
        TODO:The model should be accessible from the database.
        '''
        self.model = joblib.load(os.path.join(filepath,'%s.pkl' % self.model_name))

    def score(self, X, y):
        '''
        Test the model given a dataset and a target vector.
        
        This method applies the model that this object represents to the given dataset using
        the response variable y. It is a measure of the accuracy of the trained model. Usually
        the orginal dataset should be splitted in training and testing subsets to cross validate
        the model.
        '''
        return self.model.score(X,y)
