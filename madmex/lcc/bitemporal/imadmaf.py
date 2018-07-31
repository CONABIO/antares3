'''
Created on Jun 25, 2018

@author: agutierrez
'''
import logging

import numpy

from madmex.lcc.bitemporal import BaseBiChange
from madmex.lcc.transform.irmad import Transform as IRMAD
from madmex.lcc.transform.kapur import Transform as Kapur
from madmex.lcc.transform.maf import Transform as MAF


logger = logging.getLogger(__name__)

class BiChange(BaseBiChange):
    """Antares implementation of iMAD-MAF change detection algorithm
    """
    def __init__(self, array, affine, crs, max_iterations=25, min_delta=0.01,
                 lmbda=0.0, shift=(1, 1), threshold='kapur', **kwargs):
        """iMAD-MAF based bitemporal change detection

        Process to detect land cover change using the iteratively reweighted
        Multivariate Alteration Detection algorithm and then postprocesing
        the output using the Maximum Autocorrelation Factor.

        Args:
            max_iterations (int): Max number of iteration of the irmad process
            min_delta (float): Threshold to stop the iteration process
            lmbda (float): Value to perform regularization on the eigenvalue
                problem when the condition number is too high
            shift (tuple): Quantity to shift the matrix to calculate the
                spatial autocorrelation
            threshold (str): One of the automatic thresholding method exposed in
                ``madmex.lcc.bitemporal.BaseBiChange.threshold_change``
            **kwargs: Additional arguments to pass to the thresolding method

        Example:
			>>> from madmex.lcc.bitemporal.imadmaf import BiChange
            >>> import numpy as np
            >>> from affine import Affine

            >>> # Build random data
            >>> arr0 = np.random.randint(1,2000,30000).reshape((3, 100, 100))
            >>> arr1 = np.random.randint(1,2000,30000).reshape((3, 100, 100))

            >>> # Instantiate classes
            >>> Change_0 = BiChange(arr0, Affine.identity(), '+proj=longlat')
            >>> Change_1 = BiChange(arr1, Affine.identity(), '+proj=longlat')

            >>> # Compute distance
            >>> Change_0.run(Change_1)
            >>> print(Change_0.change_array)
            >>> print(np.sum(Change_0.change_array))

            >>> Change_0.filter_mmu(1.2)
            >>> print(np.sum(Change_0.change_array))


        """
        super().__init__(array=array, affine=affine, crs=crs)
        self.max_iterations = max_iterations
        self.min_delta = min_delta
        self.lmbda = lmbda
        self.shift = shift
        self.threshold = threshold
        self.kwargs = kwargs


    def _run(self, arr0, arr1):
        M = IRMAD(arr0, arr1, self.max_iterations, self.min_delta, self.lmbda).transform()
        M = MAF(M, self.shift).transform()
        M = self.threshold_change(M, method=self.threshold, **self.kwargs).astype(numpy.uint8)
        return M

