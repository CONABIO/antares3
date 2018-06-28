'''
Created on Jun 25, 2018

@author: agutierrez
'''
import logging
import  math

import numpy
from scipy import linalg, stats

from madmex.lcc.bitemporal import BaseBiChange


logger = logging.getLogger(__name__)

class IMAD(object):
    '''
    This class implements The iteratively Multivariate Alteration Detection (MAD)
    transformation of two images. Taking the difference between the canonical variates
    from a canonical correlation analysis we obtain the MAD components. The canonical
    correlated variates are ordered 
    
    '''
    def __init__(self, max_iterations=25, min_delta=0.02):
        self.max_iterations = max_iterations
        self.min_delta = min_delta
    
    def fit(self, X, Y):
        self.X = X
        self.Y = Y
        if len(self.X.shape) == 2:
            self.bands = 1
            self.rows, self.columns = self.X.shape
            self.X = X[numpy.newaxis,:]
            self.Y = Y[numpy.newaxis,:]
        elif len(self.X.shape) == 3:
            self.bands, self.rows, self.columns = self.X.shape
        else:
            logger.error('An image of 3 or 2 dimensions is expected.')
                
    
    def transform(self, X, Y):
        image_bands_flattened = numpy.zeros((2 * self.bands, self.columns * self.rows))
        for k in range(self.bands):
            image_bands_flattened[k, :] = numpy.ravel(self.X[k, :, :])
            image_bands_flattened[self.bands + k, :] = numpy.ravel(self.Y[k, :, :])
        NO_DATA = 0
        no_data_X = image_bands_flattened[0, :] == NO_DATA
        no_data_Y = image_bands_flattened[self.bands, :] == NO_DATA
        data_mask = (no_data_X | no_data_Y) == False
        self.image_bands_flattened = image_bands_flattened[:, data_mask]
        data_mask_sum = numpy.sum(data_mask)
        self.weights = numpy.ones(int(data_mask_sum)) # we start with weights defined as ones.
        self.outcorrlist = []
        i = 0
        logger.info('Starting iMAD iterations.')  
        old_rho = numpy.zeros(self.bands)
        delta = 1.0
        flag = True
        while (delta > self.min_delta) and (i < self.max_iterations) and flag:
            try:
                logger.info('iMAD iteration: %d', i)
                weighted_sum = numpy.sum(self.weights)
                means = numpy.average(self.image_bands_flattened, axis=1, weights=self.weights)
                dmc = self.image_bands_flattened - means[:, numpy.newaxis]
                dmc = numpy.multiply(dmc, numpy.sqrt(self.weights))
                sigma = numpy.dot(dmc, dmc.T) / weighted_sum
                s11 = sigma[0:self.bands, 0:self.bands]
                s22 = sigma[self.bands:, self.bands:]
                s12 = sigma[0:self.bands, self.bands:]
                s21 = sigma[self.bands:, 0:self.bands]
                aux_1 = linalg.solve(s22, s21)
                lamda_a, a = linalg.eig(numpy.dot(s12, aux_1), s11)
                aux_2 = linalg.solve(s11, s12)
                lamda_b, b = linalg.eig(numpy.dot(s21, aux_2), s22)
                # sort a
                sorted_indexes = numpy.argsort(lamda_a)
                a = a[:, sorted_indexes]
                # sort b        
                sorted_indexes = numpy.argsort(lamda_b)
                b = b[:, sorted_indexes]          
                # canonical correlations        
                rho = numpy.sqrt(numpy.real(lamda_b[sorted_indexes])) 
                self.delta = numpy.sum(numpy.abs(rho - old_rho))
                if(not math.isnan(self.delta)):
                    self.outcorrlist.append(rho)
                    # normalize dispersions  
                    tmp1 = numpy.dot(numpy.dot(a.T, s11), a)
                    tmp2 = 1. / numpy.sqrt(numpy.diag(tmp1))
                    tmp3 = numpy.tile(tmp2, (self.bands, 1))
                    a = numpy.multiply(a, tmp3)
                    b = numpy.mat(b)
                    tmp1 = numpy.dot(numpy.dot(b.T, s22), b)
                    tmp2 = 1. / numpy.sqrt(numpy.diag(tmp1))
                    tmp3 = numpy.tile(tmp2, (self.bands, 1))
                    b = numpy.multiply(b, tmp3)
                    # assure positive correlation
                    tmp = numpy.diag(numpy.dot(numpy.dot(a.T, s12), b))
                    b = numpy.dot(b, numpy.diag(tmp / numpy.abs(tmp)))
                    # canonical and MAD variates
                    U = numpy.dot(a.T, (self.image_bands_flattened[0:self.bands, :] - means[0:self.bands, numpy.newaxis]))    
                    V = numpy.dot(b.T, (self.image_bands_flattened[self.bands:, :] - means[self.bands:, numpy.newaxis]))          
                    M_flat = U - V  # TODO: is this operation stable?
                    # new weights        
                    var_mad = numpy.tile(numpy.mat(2 * (1 - rho)).T, (1, data_mask_sum))    
                    chi_squared = numpy.sum(numpy.multiply(M_flat, M_flat) / var_mad, 0)
                    self.weights = numpy.squeeze(1 - numpy.array(stats.chi2._cdf(chi_squared, self.bands))) 
                    old_rho = rho
                    logger.info('Processing of iteration %d finished [%f] ...', i, numpy.max(self.delta))
                    i = i + 1
                else:
                    flag = False
                    logger.warning('Some error happened.')
            except Exception as error:
                flag = False
                logger.error('iMAD transform failed with error: %s', str(repr(error))) 
                logger.error('Processing in iteration %d produced error. Taking last MAD of iteration %d' % (i, i - 1))
        output_flat = numpy.zeros((self.bands, self.columns * self.rows))
        output_flat[0:self.bands, data_mask] = M_flat
        M = numpy.zeros((self.bands, self.rows, self.columns))
        for b in range(self.bands):
            M[b, :, :] = (numpy.resize(output_flat[self.bands - (b + 1), :], (self.rows, self.columns)))
        
        
        U_flat = numpy.zeros((self.bands, self.columns * self.rows))
        U_flat[0:self.bands, data_mask] = U
        U_final = numpy.zeros((self.bands, self.rows, self.columns))
        for b in range(self.bands):
            U_final[b, :, :] = (numpy.resize(U_flat[b, :], (self.rows, self.columns)))
            
        V_flat = numpy.zeros((self.bands, self.columns * self.rows))
        V_flat[0:self.bands, data_mask] = V
        V_final = numpy.zeros((self.bands, self.rows, self.columns))
        for b in range(self.bands):
            V_final[b, :, :] = (numpy.resize(V_flat[b, :], (self.rows, self.columns)))
        
        
        
        return M, U_final, V_final, chi_squared

    def fit_transform(self, X, Y):
        self.fit(X, Y)
        return self.transform(X, Y)
    
def spatial_covariance(X, h):
    X_shifted = numpy.roll(numpy.roll(X, h[1], axis=1), h[0], axis=2)
    X_shifted_transpose = numpy.transpose(X_shifted, axes=[0,2,1])
    product = numpy.matmul(X_shifted, X_shifted_transpose)
    bands = product.shape[0]
    pixels = product.shape[1] * product.shape[2]
    bands_by_row = numpy.matmul(X_shifted, X_shifted_transpose).reshape((bands, pixels))
    C = numpy.cov(bands_by_row)
    return C
    
class MAF(object):
    
    def __init__(self, shift=(1, 1), no_data=0):
        self.no_data = no_data
        self.h = numpy.array(shift)
    def fit(self, X):
        self.X = X
        if len(self.X.shape) == 2:
            self.bands = 1
            self.rows, self.columns = self.X.shape
            self.X = X[numpy.newaxis,:]
        elif len(self.X.shape) == 3:
            self.bands, self.rows, self.columns = self.X.shape
        else:
            logger.error('An image of 3 or 2 dimensions is expected.')
    def transform(self, X):
        sigma = spatial_covariance(X, numpy.array((0,0)))
        gamma = 2 * sigma - spatial_covariance(X, self.h) - spatial_covariance(X, -self.h)       
        lower = numpy.linalg.cholesky(sigma)
        lower_inverse = numpy.linalg.inv(lower)
        eig_problem = numpy.matmul(numpy.matmul(lower_inverse, gamma), lower_inverse.T)
        eig_values, eig_vectors = numpy.linalg.eig(eig_problem)
        sort_index = eig_values.argsort()
        vector = eig_vectors[sort_index]
        M = numpy.tensordot(vector, X, axes=1)
        return M
    
    def fit_transform(self, X):
        self.fit(X)
        return self.transform(X)
    
class MAD(object):
    
    def __init__(self):
        pass
    
    def fit(self, X, Y):
        self.X = X
        self.Y = Y
        if len(self.X.shape) == 2:
            self.bands = 1
            self.rows, self.cols = self.X.shape
            self.X = X[numpy.newaxis,:]
            self.Y = Y[numpy.newaxis,:]
        elif len(self.X.shape) == 3:
            self.bands, self.rows, self.cols = self.X.shape
        else:
            logger.error('An image of 3 or 2 dimensions is expected.')
                
    def transform(self, X, Y):

        g_11_product = numpy.matmul(X, numpy.transpose(X, axes=[0,2,1]))
        g_22_product = numpy.matmul(Y, numpy.transpose(Y, axes=[0,2,1]))
        g_12_product = numpy.matmul(X, numpy.transpose(Y, axes=[0,2,1]))

        bands_11 = g_11_product.shape[0]
        pixels_11 = g_11_product.shape[1] * g_11_product.shape[2]
        
        bands_22 = g_22_product.shape[0]
        pixels_22 = g_22_product.shape[1] * g_22_product.shape[2]

        bands_12 = g_12_product.shape[0]
        pixels_12 = g_12_product.shape[1] * g_12_product.shape[2]

        sigma_11 = numpy.cov(g_11_product.reshape(bands_11, pixels_11))
        sigma_22 = numpy.cov(g_22_product.reshape(bands_22, pixels_22))
        sigma_12 = numpy.cov(g_12_product.reshape(bands_12, pixels_12))

        lower_11 = numpy.linalg.cholesky(sigma_11)
        lower_22 = numpy.linalg.cholesky(sigma_22)
        lower_12 = numpy.linalg.cholesky(sigma_12)

        lower_11_inverse = numpy.linalg.inv(lower_11)
        lower_22_inverse = numpy.linalg.inv(lower_22)
        
        sigma_11_inverse = numpy.linalg.inv(sigma_11)
        sigma_22_inverse = numpy.linalg.inv(sigma_22)
        
        
        eig_problem_1 = numpy.matmul(lower_11_inverse, 
                                     numpy.matmul(sigma_12, 
                                                  numpy.matmul(sigma_22_inverse, 
                                                               numpy.matmul(sigma_12.T, lower_11_inverse.T)))) 
        
        eig_problem_2 = numpy.matmul(lower_22_inverse, 
                                     numpy.matmul(sigma_12.T, 
                                                  numpy.matmul(sigma_22_inverse, 
                                                               numpy.matmul(sigma_12, lower_22_inverse.T)))) 
        
        
        eig_values_1, eig_vectors_1 = numpy.linalg.eig(eig_problem_1)
        eig_values_2, eig_vectors_2 = numpy.linalg.eig(eig_problem_2)
        
        sort_index_1 = numpy.flip(eig_values_1.argsort(), 0)
        sort_index_2 = numpy.flip(eig_values_2.argsort(), 0)
        
        vector_u = eig_vectors_1[sort_index_1]
        vector_v = eig_vectors_2[sort_index_2]
        
        U = numpy.tensordot(vector_u, X, axes=1)
        V = numpy.tensordot(vector_v, Y, axes=1)
        
        M = U - V
        
        return M
        
    def fit_transform(self, X, Y):
        self.fit(X, Y)
        return self.transform(X, Y)


class BiChange(BaseBiChange):
    '''
    Process to detect land cover change using the iteratively reweighted
    Multivariate Alteration Detection algorithm and then postprocesing
    the output using the Maximum Autocorrelation Factor.
    '''


    def __init__(self,  array, affine, crs, max_iterations=25, min_delta=0.02):
        '''
        Constructor
        '''
        super.__init__(array=array, affine=affine, crs=crs)
        self.max_iterations = max_iterations
        self.min_delta = min_delta
    def _run(self, arr0, arr1):
        imad = IMAD(self.max_iterations, self.min_delta)
        pass
        #maf = MAF(imad)
        #return get_mask(maf)
        