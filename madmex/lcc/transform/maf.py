'''
Created on Jul 6, 2018

@author: agutierrez
'''
import numpy

from madmex.lcc.transform import TransformBase


def spatial_covariance(X, h):
    '''
    This method computes the spatial covariance for an image. This is, the covariance of an
    image with itself, but shifted by an amount specified with h.
    '''
    X_mean = numpy.average(X, axis=(1,2))
    X_shifted = numpy.roll(numpy.roll(X, h[1], axis=1), h[0], axis=2)
    bands = X.shape[0]
    pixels = X.shape[1] * X.shape[2]
    X_centered = (X - X_mean[:,numpy.newaxis,numpy.newaxis]).reshape(bands, pixels)
    X_shifted_centered = (X_shifted - X_mean[:,numpy.newaxis,numpy.newaxis]).reshape(bands, pixels)
    C = numpy.matmul(X_centered, X_shifted_centered.T) / (pixels - 1)
    return C

class Transform(TransformBase):
    '''
    This transform maximizes the autocorrelation for the image. The bands are
    order by autocorrelation with the first band having the maximum autocorrelation
    and subjected to be uncorrelated with the other bands.
    '''

    def __init__(self, shift=(1, 1)):
        '''
        Constructor
        '''
        self.h = numpy.array(shift)
    def transform(self, X):
        sigma = spatial_covariance(self.X, numpy.array((0,0)))
        gamma = 2 * sigma - spatial_covariance(self.X, self.h) - spatial_covariance(self.X, -self.h)       
        lower = numpy.linalg.cholesky(sigma)
        lower_inverse = numpy.linalg.inv(lower)
        eig_problem = numpy.matmul(numpy.matmul(lower_inverse, gamma), lower_inverse.T)
        eig_values, eig_vectors = numpy.linalg.eig(eig_problem)
        sort_index = eig_values.argsort()
        vector = eig_vectors[:, sort_index]
        M = numpy.matmul(vector.T, self.X.reshape(self.bands, self.rows * self.cols))
        return M.reshape(self.bands, self.rows, self.cols)
