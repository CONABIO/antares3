'''
Created on 2018 07 13 

@author: Julián Equihua

'''
import numpy as np

from sklearn.ensemble import IsolationForest

from madmex.lcc.transform import VectransformBase

class Transform(VectransformBase):
    '''
    Given a matrix of independent variables (columns) and a vector of labels, 
    this class computes an outlier análisis based on Isolation Forests. 

    X should be a matrix containing observations of interest * independent variables. 

    Y should be an array of values representing class labels in a classificaitno task.

    Returns a boolean array which allows to discard rows which correspond to outliers.

    '''

    def __init__(self, outlier_fraction=[0.2], max_samples=0.632, n_estimators=100, n_jobs=-1):
        '''
        Constructor
        '''
        self.outlier_fraction = np.array(outlier_fraction)
        self.max_samples = max_samples
        self.n_estimators = n_estimators
        self.n_jobs = n_jobs

    def transform(self, X, Y):
        
        '''
        Estimate a measure of outlierness for each observation per class in the labels
        vector using Isolation Forests. Given an assumed proportion of outliers per class,
        returns a boolean array which allows to discard these observations.

        outlier_fraction can be a list of outlier_fractions per class, it should be 
        ordered in ascending order based on the class labels.

        '''

        # initialize output array
        output_array = np.zeros((self.rows),dtype=np.int8)

        unique_classes = np.unique(self.Y)

        if len(self.outlier_fraction)==1:
            self.outlier_fraction = np.repeat(self.outlier_fraction,len(unique_classes))

        i=0

        for class_label in unique_classes:

            class_idx = self.Y == class_label

            X_subset = self.X[0,class_idx,:]

            # specify and fit model
            model_specification = IsolationForest(
                                   contamination=self.outlier_fraction[i],
                                   max_samples=self.max_samples,
                                   n_estimators=self.n_estimators,
                                   n_jobs = self.n_jobs)

            model_specification.fit(X_subset)

            # tag outliers
            outliers = model_specification.predict(\
                                                 X_subset)*1

            output_array[class_idx]=outliers

            i += 1

        return output_array==1
