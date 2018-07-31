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
    '''Antares implementation of the IR-MAD transformation

    IR-MAD corresponds to Iterative Reweighted Multivariate Alteration Detection (MAD),
    it is applied over two matching arrays

    It implements the method of performing several MAD transformations and re-weighting
    the importance of the pixels at each consecutive run. Given that we expect the pixels
    in the MAD transform to behave like a normal distribution, we can detect anomalies using
    a chi-distribution with n degrees of freedom, with n equal to the number of classes. We
    use the likelihood of seeing a change value to re-weight each pixel and then run the
    MAD transform again until any end criteria is met.
    '''
    def __init__(self, X, Y, max_iterations=50, min_delta=0.001, lmbda=0.0):
        '''Instantiate class to run MAD transformation on two arrays

        Args:
            max_iterations (int): The maximum number of times that the process will
                run the MAD transform.
            min_delta (float): After each successive iteration of the MAD transform,
                the distance between the eigenvalues is measured. Min_delta is used
                to stop the iterations when the value of the difference is lower than
                this threshold.
            lmbda (float): Value used by the MAD transform to perform regularization
                when the condition number of the matrix in the generalized eigenvalue
                problem is too big.
        '''
        super().__init__(X, Y)
        self.max_iterations = max_iterations
        self.threshold = min_delta
        self.lmbda = lmbda


    def transform(self):
        """Implements iterative Multivariate Alteration Detection.

        Return:
            np.ndarray: Transformed array
        """
        i = 0
        delta = 1.0
        old_rho = numpy.ones((self.X.shape[0]))
        weights = numpy.ones((self.X.shape[1],self.X.shape[2]))
        while i < self.max_iterations and delta > self.threshold:
            logger.info('Iteration #%s' % i)
            logger.info('delta: %s' % delta)
            M, sigma_squared, rho = MAD(self.X, self.Y, lmbda=self.lmbda, weights=weights).transform()
            chi_square = numpy.tensordot(1 / sigma_squared, numpy.multiply(M, M), axes=1)
            weights = 1 - stats.chi2.cdf(chi_square, self.bands)
            delta = max(abs(rho - old_rho))
            old_rho = rho
            i = i + 1
        return M
