'''
Created on Nov 24, 2016

@author: agutierrez
'''

import os
import abc
import logging

import dill
import numpy as np
from sklearn import metrics
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import IsolationForest
from sklearn.utils import shuffle

from madmex.models import Model
from madmex.settings import SERIALIZED_OBJECTS_DIR
from madmex.util import randomword
from madmex.util.numpy import groupby

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

        
    def grid_search_cv_fit(self, X, y, cv, parameter_values):
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
        See https://stackoverflow.com/questions/53802618/dummy-encoding-using-columtransformer
            https://datascience.stackexchange.com/questions/41113/deprecationwarning-the-categorical-features-keyword-is-deprecated-in-version
        for ColumnTransformer usage 
        """
        if self.categorical_features is not None:
            ct = ColumnTransformer(
                 [('one_hot_encoder', OneHotEncoder(), self.categorical_features)],
                 remainder='passthrough')
            self.enc = ct.fit(X)
            X = ct.transform(X)
        return X


    def hot_encode_predict(self, X):
        """Hot Encode data on which prediction is to be performed
        """
        if self.categorical_features is not None:
            X = self.enc.transform(X)
        return X


    @staticmethod
    def remove_outliers(X, y, n_estimators=101, max_samples='auto', contamination=0.25,
                        bootstrap=True, n_jobs=-1, **kwargs):
        """Performs outliers detection and removal using Isolation Forest anomaly score

        Args:
            X (np.ndarray): Array of independent variables of shape (n,m)
            y (np.ndarray): Array of dependent variable of shape (n,)
            contamination (float): The amount of contamination of the data set,
                i.e. the proportion of outliers in the data set. Used when
                fitting to define the threshold on the decision function.
            max_sample (float): Proportion of observations to draw from X to fit
                each estimator
            **kwargs: Arguments passed to ``sklearn.ensemble.IsolationForest``

        Example:
            >>> from sklearn.datasets import make_classification
            >>> from madmex.modeling import BaseModel
            >>> X, y = make_classification(n_samples=10000, n_features=10,
            >>>                            n_classes=5, n_informative=6)
            >>> X_clean, y_clean = BaseModel.remove_outliers(X, y)
            >>> print('Input shape:', X.shape, 'Output shape:', X_clean.shape)

        Return:
            tuple: Tuple of filtered X and y arrays (X, y)
        """
        # Split X
        grouped = groupby(X, y)
        X_list = []
        y_list = []
        for g in grouped:
            isolation_forest = IsolationForest(n_estimators=n_estimators,
                                               max_samples=max_samples,
                                               contamination=contamination,
                                               bootstrap=bootstrap,
                                               n_jobs=n_jobs,
                                               **kwargs)
            isolation_forest.fit(g[1])
            is_inlier = isolation_forest.predict(g[1])
            is_inlier = np.where(is_inlier == 1, True, False)
            X_out = g[1][is_inlier,:]
            X_list.append(X_out)
            y_out = np.empty_like(X_out[:,0], dtype=np.int16)
            y_out[:] = g[0]
            y_list.append(y_out)
        # Concatenate returned arrays
        Xc = np.concatenate(X_list)
        yc = np.concatenate(y_list)
        X, y = shuffle(Xc,yc,random_state=658432434)
        return (X, y)


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

