'''
Created on Jul 6, 2018

@author: agutierrez
'''
import numpy

from madmex.lcc.transform import BitransformBase


class Transform(BitransformBase):
    '''Antares implementation of the MAD transformation of two array

    This class computes the MAD components. These are useful in the study of phenomena
    changes between raster images taken in different times.
    Taking the difference between the canonical variates from a canonical correlation
    analysis we obtain the MAD components. The canonical correlated variates are ordered
    by similarity instead of wavelength. This difference will capture the changes
    between the images. The bands of the MAD components capture different nature of
    changes.
    '''
    def __init__(self, X, Y, lmbda=0.0, weights=None):
        '''Instantiate MAD transformation class

        Args:
            lmbda (float): A value to perform regularization during the transform, this
                is helpful when the condition number of the matrix involved in the
                eigenvalue problem is too large. 
            weights (np.ndarray): An array with same dimensions as X and Y, represents
                the importance of each pixel. This argument is useful when we calculate 
                the iterative re-weighted MAD transform, in any other case, this value 
                should be a matrix filled with ones.
        '''
        super().__init__(X, Y)
        self.lmbda = lmbda
        self.weights = weights



    def _transform(self):
        '''This method optimizes the proces of computing the MAD components. Instead of
        stacking the two matrices together and performing a matrix multiplication of the
        stack, we take advantage of the nature of the problem and just compute the parts of
        the matrix that we need. This process is described in the book: Image Analysis  Classification
        and Change Detection in Remote Sensing.
        '''
        weights = self.weights
        if weights is None:
            weights = numpy.ones((self.rows, self.cols))
        W = weights * numpy.ones(self.X.shape)
        X_mean = numpy.average(self.X, weights=W, axis=(1,2))
        Y_mean = numpy.average(self.Y, weights=W, axis=(1,2))
        X_centered = (self.X - X_mean[:,numpy.newaxis,numpy.newaxis])
        Y_centered = (self.Y - Y_mean[:,numpy.newaxis,numpy.newaxis])

        X_weigthed = X_centered * weights
        Y_weigthed = Y_centered * weights
        X_pixel_band = X_centered.reshape(self.bands, self.rows * self.cols)
        Y_pixel_band = Y_centered.reshape(self.bands, self.rows * self.cols)

        X_pixel_band_weigthed = X_weigthed.reshape(self.bands, self.rows * self.cols)
        Y_pixel_band_weigthed = Y_weigthed.reshape(self.bands, self.rows * self.cols)

        sigma_11 = numpy.matmul(X_pixel_band_weigthed, X_pixel_band.T) / (numpy.sum(weights) - 1)
        sigma_11 = (1-self.lmbda) * sigma_11 + self.lmbda * numpy.eye(self.bands)
        sigma_22 = numpy.matmul(Y_pixel_band_weigthed, Y_pixel_band.T) / (numpy.sum(weights) - 1)
        sigma_22 = (1-self.lmbda) * sigma_22 + self.lmbda * numpy.eye(self.bands)
        sigma_12 = numpy.matmul(X_pixel_band_weigthed, Y_pixel_band.T) / (numpy.sum(weights) - 1)
        lower_11 = numpy.linalg.cholesky(sigma_11)
        lower_22 = numpy.linalg.cholesky(sigma_22)
        lower_11_inverse = numpy.round(numpy.linalg.inv(lower_11), decimals=10)
        lower_22_inverse = numpy.round(numpy.linalg.inv(lower_22), decimals=10)
        sigma_11_inverse = numpy.linalg.inv(sigma_11)
        sigma_22_inverse = numpy.linalg.inv(sigma_22)

        eig_problem_1 = numpy.matmul(lower_11_inverse,
                                     numpy.matmul(sigma_12,
                                                  numpy.matmul(sigma_22_inverse,
                                                               numpy.matmul(sigma_12.T, lower_11_inverse.T))))
        eig_problem_1 = (eig_problem_1 + eig_problem_1.T) * 0.5
        eig_problem_2 = numpy.matmul(lower_22_inverse,
                                     numpy.matmul(sigma_12.T,
                                                  numpy.matmul(sigma_11_inverse,
                                                               numpy.matmul(sigma_12, lower_22_inverse.T))))
        eig_problem_2 = (eig_problem_2 + eig_problem_2.T) * 0.5
        eig_values_1, eig_vectors_1 = numpy.linalg.eig(eig_problem_1)
        eig_values_2, eig_vectors_2 = numpy.linalg.eig(eig_problem_2)

        eig_vectors_transformed_1 = numpy.matmul(lower_11_inverse.T, eig_vectors_1)
        eig_vectors_transformed_2 = numpy.matmul(lower_22_inverse.T, eig_vectors_2)

        sort_index_1 = numpy.flip(eig_values_1.argsort(), 0)
        sort_index_2 = numpy.flip(eig_values_2.argsort(), 0)

        vector_u = eig_vectors_transformed_1[:, sort_index_1]
        vector_v = eig_vectors_transformed_2[:, sort_index_2]

        mu = numpy.sqrt(eig_values_2[sort_index_2])
        norm_a_squared = numpy.diag(numpy.matmul(vector_u.T, vector_u))
        norm_b_squared = numpy.diag(numpy.matmul(vector_v.T, vector_v))

        variance_u = numpy.diag(1/numpy.sqrt(numpy.diag(sigma_11)))
        s = numpy.sum(numpy.matmul(variance_u, numpy.matmul(sigma_11, vector_u)),axis=0)
        vector_u = numpy.matmul(vector_u, numpy.diag(s / numpy.abs(s)))

        signs_vector = numpy.diag(numpy.dot(numpy.dot(vector_u.T, sigma_12), vector_v))
        signs = numpy.diag(signs_vector / numpy.abs(signs_vector))
        vector_v = numpy.matmul(vector_v, signs)

        U = numpy.matmul(vector_u.T, X_pixel_band)
        V = numpy.matmul(vector_v.T, Y_pixel_band)
        M = U - V
        sigma_squared = (2 - self.lmbda * (norm_a_squared + norm_b_squared)) / (1 - self.lmbda) - 2 * mu
        rho = mu * (1 - self.lmbda) / numpy.sqrt((1 - self.lmbda * norm_a_squared) * (1 - self.lmbda * norm_b_squared))
        return M.reshape(self.bands, self.rows, self.cols), sigma_squared, rho
