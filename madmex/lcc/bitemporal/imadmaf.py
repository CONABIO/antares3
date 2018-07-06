'''
Created on Jun 25, 2018

@author: agutierrez
'''
import logging

from madmex.lcc.bitemporal import BaseBiChange
from madmex.lcc.bitemporal.thresholding import Elliptic
from madmex.lcc.transform.irmad import Transform as IRMAD
from madmex.lcc.transform.maf import Transform as MAF

logger = logging.getLogger(__name__)

class BiChange(BaseBiChange):
    '''
    Process to detect land cover change using the iteratively reweighted
    Multivariate Alteration Detection algorithm and then postprocesing
    the output using the Maximum Autocorrelation Factor.
    '''

    def __init__(self,  array, affine, crs, max_iterations=25, min_delta=0.01, lmbda=0.0, shift=(1, 1)):
        '''
        Constructor
        '''
        super.__init__(array=array, affine=affine, crs=crs)
        self.max_iterations = max_iterations
        self.min_delta = min_delta
        self.lmda = lmbda
        self.shift = shift
    def _run(self, arr0, arr1):
        M = IRMAD(self.max_iterations, self.min_delta, self.lmbda).fit_transform(arr0, arr1)
        M = MAF(self.shift).fit_transform(M)
        return Elliptic().fit_transform(M)
        