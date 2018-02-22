'''
Created on Jan 31, 2018

@author: agutierrez
'''
from importlib import import_module
import logging

import numpy

logger = logging.getLogger(__name__)

def calculate_zonal_statistics(array, labels, index, statistics):
    '''
    Receives an array with labels and indexes for those labels. It calculates the zonal
    statistics for those labels. Statistics are the target functions to be applied, it should
    cointain strings from the set: ('mean', 'maximum', 'median', 'minimum', 'standard_deviation',
    'variance','sum')
    
    Args:
        array (numpy.array): Array to which statitstics will be applied
        labels (numpy.array): Labels for the statistics of interest
        index (numpy.array): Positions in which the statistics can be found
        statistics (string array): Functions to be applied

    Return:
        zonal_statistics (numpy.array): The calculated statistics
    
    '''
    results = []
    module = import_module('scipy.ndimage.measurements')
    for statistic in statistics:
        function = getattr(module, statistic)
        stat = function(array, labels=labels, index=index)
        results.append(stat)
    zonal_statistics = numpy.asarray(results).transpose()  
    return zonal_statistics