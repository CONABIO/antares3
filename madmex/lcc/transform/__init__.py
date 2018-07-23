import logging
import sys
import abc

import numpy


logger = logging.getLogger(__name__)


class TransformBase(metaclass=abc.ABCMeta):
    '''Metaclass to support single array transform.
    '''
    def __init__(self, X):
        '''Instantiate class to perform of a single 2D or 3D array.

        Args:
            X (numpy.ndarray): A 2 or 3 dimensional numpy array. Dimension order should
                be (bands, y, x)
        '''
        if X.ndim == 2:
            self.bands = 1
            self.rows, self.cols = X.shape
            self.X = X[numpy.newaxis,:]
        elif X.ndim == 3:
            self.X = X
            self.bands, self.rows, self.cols = X.shape
        else:
            raise ValueError('Input array must have 2 or 3 dimensions')


    @abc.abstractmethod
    def transform(self):
        '''Run transformation defined by children instance

        Depending on the implementation, this method will transform the input into an array of
        interest.

        Return:
            np.ndarray: Transformed array (2D)
        '''
        raise NotImplementedError(
            'Subclasses of TransformBase must provide a preprocessing() method.'
            )


class BitransformBase(metaclass=abc.ABCMeta):
    '''Metaclasss to support two array transform
    '''
    def __init__(self, X, Y):
        '''Instantiate class to perform array transformation against one another

        Args:
            X (numpy.ndarray): A 2 or 3 dimensional numpy array. Dimension order should
                be (bands, y, x)
            Y (numpy.ndarray): A 3 dimensional numpy array. Dimension order should
                be (bands, y, x)
        '''
        if X.shape != Y.shape:
            raise ValueError('Input arrays must have the same shape')
        if X.ndim == 2:
            self.bands = 1
            self.rows, self.cols = X.shape
            self.X = X[numpy.newaxis,:]
            self.Y = Y[numpy.newaxis,:]
        elif X.ndim == 3:
            self.X = X
            self.Y = Y
            self.bands, self.rows, self.cols = X.shape
        else:
            raise ValueError('Input arrays must be of 2 or 3 dimensions')


    @abc.abstractmethod
    def transform(self):
        '''Run transformation defined by children instance

        Depending on the implementation, this method will transform the input into an array of
        interest.

        Return:
            np.ndarray: Transformed array
        '''
        raise NotImplementedError(
            'Subclasses of TransformBase must provide a transform() method.'
            )
