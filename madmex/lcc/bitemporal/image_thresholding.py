'''
Created on Jun 25, 2018

@author: agutierrez
'''
import logging

import  math

import numpy

from scipy import linalg, stats

from sklearn.covariance import EllipticEnvelope

from madmex.lcc.bitemporal import BaseBiChange


logger = logging.getLogger(__name__)

class threshold_outliers(object):
    '''
    This class implements an outlier detectino method to threshold a difference image (like that prodced by the iMAD-MAF transform)
    to produce a change/no-change classes partition
    
    '''
    def __init__(self, bands_subset=numpy.array([0,1]), outliers_fraction=0.05,assume_centered=False):
        
        self.bands_subset = bands_subset
        
        self.outliers_fraction = outliers_fraction

        self.assume_centered=assume_centered
    
    def fit(self, X):
        
        self.X = X

        self.bands, self.rows, self.columns = self.X.shape
                
    
    def transform(self, X):

        n_used_bands = len(self.bands_subset)

        image_bands_flattened = numpy.zeros((n_used_bands , self.columns * self.rows))
        
        for k in range(n_used_bands):
            image_bands_flattened[k, :] = numpy.ravel(self.X[self.bands_subset[k].astype(int), :, :])

        NO_DATA = 0
        
        data_mask = image_bands_flattened[0, :] == NO_DATA

        self.image_bands_flattened = image_bands_flattened[:, data_mask]
        
        data_mask_sum = numpy.sum(data_mask)
        
        logger.info('Fitting outlier model.')  
 
        flag = True

        change_classification = None

        print(change_classification)

        try:

            # specify and fit model
            outliers_model_specification = EllipticEnvelope(contamination=self.outliers_fraction,assume_centered=self.assume_centered,support_fraction=0.3)

            fitted_outliers_model = outliers_model_specification.fit(image_bands_flattened)

            # tag outliers
            change_classification = outliers_model_specification.predict(image_bands_flattened)*1

        except Exception as error:
            flag = False
            logger.error('Outlier model fitting failed with error: %s', str(repr(error))) 

        output_flat = numpy.zeros((self.columns * self.rows))
        output_flat[data_mask] = change_classification
        
        # resize to original image shape
        output_flat = numpy.resize(output_flat,(self.rows, self.columns))
        
        return output_flat

    def fit_transform(self, X):
        self.fit(X)
        return self.transform(X)