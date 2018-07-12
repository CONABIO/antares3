import logging
import sys

import numpy


logger = logging.getLogger(__name__)

class TransformBase(object):
    def __init__(self):
        pass

    def fit(self, X):
        '''Sets everything in place for the transformation process. Fails in case
        the image does not have at least 2 or more than 3 dimensions.

        Args:
            X (numpy.array): A 2 or 3 dimensional numpy array. Dimension order should
                be (bands, y, x)
        '''
        if len(X.shape) == 2:
            self.bands = 1
            self.rows, self.cols = X.shape
            self.X = X[numpy.newaxis,:]
        elif len(X.shape) == 3:
            self.X = X
            self.bands, self.rows, self.cols = X.shape
        else:
            logger.error('First parameter should be an image of 3 or 2 dimensions.')

    def transform(self, X):
        '''Depending on the implementation, this method will transform the input into an array of
        interest.
        '''
        raise NotImplementedError('Subclasses of TransformBase must provide a transform() method.')

    def fit_transform(self, X):
        '''
        Helper method to call fit and transform methods.
        '''
        self.fit(X)
        return self.transform(X)


class BitransformBase(TransformBase):
    def __init__(self):
        TransformBase.__init__(self)

    def fit(self, X, Y):
        '''Sets everything in place for the two image transformation process. Fails in case
        the images do not have the same shapes.

        Args:
            X (numpy.array): A 2 or 3 dimensional numpy array. Dimension order should
                be (bands, y, x)
            Y (numpy.array): A 3 dimensional numpy array. Dimension order should
                be (bands, y, x)
        '''
        if not X.shape == Y.shape:
            logger.error('The shapes of both images are expected to be the same.')
            sys.exit(0)
        else:
            super().fit(X)
            if len(Y.shape) == 2:
                self.Y = Y[numpy.newaxis,:]
            elif len(Y.shape) == 3:
                self.Y = Y
            else:
                logger.error('Second parameter should be an image of 3 or 2 dimensions.')

    def transform(self, X, Y):
        raise NotImplementedError('Subclasses of TransformBase must provide a transform() method.')

    def fit_transform(self, X, Y):
        '''
        Helper method to call fit and transform methods.
        '''
        self.fit(X, Y)
        return self.transform(X, Y)
