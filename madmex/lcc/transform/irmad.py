'''
Created on Jul 6, 2018

@author: agutierrez
'''
import logging

import numpy
from scipy import stats

from madmex.lcc.transform import BitransformBase
from madmex.lcc.transform.mad import Transform as MAD


logger = logging.getLogger(__name__)

class Transform(BitransformBase):
    '''
    This class implements The iteratively Multivariate Alteration Detection (MAD)
    transformation of two images. 
    
    '''

    def __init__(self, max_iterations=50, min_delta=0.001, lmbda=0.0):
        '''
        Constructor
        '''
        self.max_iterations = max_iterations
        self.threshold = min_delta
        self.lmbda = lmbda
        
    def transform(self, X, Y):
        i = 0
        delta = 1.0
        old_rho = numpy.ones((self.X.shape[0]))
        weights = numpy.ones((self.X.shape[1],self.X.shape[2]))
        while i < self.max_iterations and delta > self.threshold:
            logger.info('Iteration #%s' % i)
            logger.info('delta: %s' % delta)
            M, sigma_squared, rho = MAD(lmbda=self.lmbda).fit_transform(self.X, self.Y, weights)
            chi_square = numpy.tensordot(1 / sigma_squared, numpy.multiply(M, M), axes=1)
            weights = 1 - stats.chi2.cdf(chi_square, self.bands)
            delta = max(abs(rho - old_rho))
            old_rho = rho
            i = i + 1
        return M