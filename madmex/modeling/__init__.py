'''
Created on Nov 24, 2016

@author: agutierrez
'''

import abc
import logging
import dill

import numpy
from sklearn import metrics
from sklearn.preprocessing import OneHotEncoder

import os
from madmex.models import Model
from madmex.settings import SERIALIZED_OBJECTS_DIR
from madmex.util import randomword

LOGGER = logging.getLogger(__name__)

class BaseModel(abc.ABC):
    '''
    This class works as a wrapper to have a single interface to several
    models and machine learning packages. This will hide the complexity
    of the different ways in which the algorithms are used. This is inteded
    to be used with the xarray package.
    '''
    def __init__(self, categorical_features=None):
        '''
        Constructor

        Args:
            categorical_features (list): Indices of categorical variables
        '''
        self.categorical_features = categorical_features

    def fit(self, X, y):
        '''
        This method will train the classifier with given data.
        '''
        NotImplementedError('Children of BaseModel need to implement their own fit method')

    def predict(self, X):
        '''
        When the model is created, this method lets the user predict on unseen data.
        '''
        NotImplementedError('Children of BaseModel need to implement their own predict method')

    def predict_confidence(self, X):
        '''
        For every unseen observation, get the highest probability
        '''
        NotImplementedError('Children of BaseModel need to implement their own predict_confidence method')

    def hot_encode_training(self, X):
        """Apply one hot encoding to one or several predictors determined by the list
        of indices of the hot_encode attribute

        In case no encoding is required (self.categorical_features is None),
        simply returns the input array

        Args:
            X (array): The array of predictors

        Return:
            array: The array of predictors with specified variables encoded
        """
        if self.categorical_features is not None:
            enc = OneHotEncoder(categorical_features=self.categorical_features,
                                sparse=False)
            self.enc = enc.fit(X)
            X = enc.transform(X)
        return X

    def hot_encode_predict(self, X):
        """Hot Encode data on which prediction is to be performed
        """
        if self.categorical_features is not None:
            X = self.enc.transform(X)
        return X


    def save(self, filepath):
        '''
        Write entire object to file
        '''
        with open(filepath, 'wb') as dst:
            dill.dump(self, dst)

    @staticmethod
    def load(filepath):
        '''
        Read object from file
        '''
        with open(filepath, 'rb') as src:
            obj = dill.load(src)
        return obj

    @classmethod
    def from_db(cls, name):
        """Instantiate an object from a children class of BaseModel reading it from the database

        Args:
            name (str): Name under which the trained model is referenced in the database

        Return:
            The object previously saved under the name 'name'
        """
        inst = cls()
        model_row = Model.objects.get(name=name)
        filepath = model_row.path
        return inst.load(filepath)

    def to_db(self, name, recipe=None, training_set=None):
        """Write the instance of the class to the datbase

        In reality the object is written to file after being serialized and a reference
        to that file is written to the database.

        Args:
            name (str): Name/unique identifier to give to the model
            recipe (str): Name of the recipe used to fit the model (more like name of
                the product)
            training_set (str): Name of the training set used to fit the model
        """
        # Save to file
        filename = '%s_%s.pkl' % (name, randomword(5))
        filepath = os.path.join(SERIALIZED_OBJECTS_DIR, filename)
        self.save(filepath)
        # Create database entry
        m = Model(name=name, path=filepath, training_set=training_set,
                   recipe=recipe)
        m.save()

    def score(self, filepath):
        '''
        Lets the user load a previously trained model to predict with it.
        '''
        raise NotImplementedError('subclasses of BaseModel must provide a score() method')

    def create_report(self, expected, predicted, filepath='report.txt'):
        '''
        Creates a report in the given filepath, it includes the confusion
        matrix, and information about the score. It contrasts expected and
        predicted outcomes.
        '''
        with open(filepath,'w') as report:
            report.write('Classification report for classifier:\n%s\n' % metrics.classification_report(expected, predicted))
            report.write('Confusion matrix:\n%s\n' % metrics.confusion_matrix(expected, predicted, labels=numpy.unique(expected)))
