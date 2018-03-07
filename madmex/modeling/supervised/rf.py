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

    def __init__(self, categorical_features=None, n_estimators=50, n_jobs=-1):
        '''
        Example:
            >>> from madmex.modeling.supervised.rf import Model
            >>> rf = Model()
            >>> # Write model to db
            >>> rf.to_db(name='test_model', recipe='mexmad', training_set='no')
            >>> # Read model from db
            >>> rf2 = Model.from_db('test_model')
        '''
        super().__init__(categorical_features=categorical_features)
        self.model = RandomForestClassifier(n_estimators=n_estimators,
                                            n_jobs=-1)
        self.model_name = 'rf'

    def fit(self, X, y):
        X = self.hot_encode(X)
        self.model.fit(X,y)

    def predict(self, X):
        '''
        Simply passes down the prediction from the underlying model.
        '''
        X = self.hot_encode(X)
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
