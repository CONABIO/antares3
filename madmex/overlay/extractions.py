'''
Created on Jan 31, 2018

@author: agutierrez
'''
from importlib import import_module
import logging

import numpy as np
import xarray as xr

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
    zonal_statistics = np.asarray(results).transpose()
    return zonal_statistics


def zonal_stats_xarray(arr, dataset, aggregation='mean'):
    """Perform extraction and grouping using xarray groupby method

    Args:
        arr (numpy.array): Array as returned by madmex.overlay.transform.rasterize_xarray
            Of float type and with non overlayed pixels set to np.nan
        dataset (xarray.Dataset): The Dataset from which the data have to be extracted
            Each dataarray should not have more than two dimensions
        aggregation (str): Spatial aggregation function to use (mean (default), median, std)

    Return:
        Don't know yet
    """
    # Convert arr to a dataArray
    xr_arr = xr.DataArray(arr, dims=['x', 'y'], name='features_id')
    # Combine the Dataset with the DataArray
    combined = xr.merge([xr_arr, dataset])
    if aggregation == 'mean':
        groups_xr = combined.groupby('features_id').mean()
    elif aggregation == 'median':
        groups_xr = combined.groupby('features_id').median()
    elif aggregation == 'std':
        groups_xr = combined.groupby('features_id').std()
    else:
        raise ValueError('Unsuported aggregation function')
    return groups_xr
