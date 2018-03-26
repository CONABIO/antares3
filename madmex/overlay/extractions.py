'''
Created on Jan 31, 2018

@author: agutierrez
'''
from importlib import import_module
import logging
from collections import OrderedDict

import numpy as np
import xarray as xr

from madmex.overlay.conversions import rasterize_xarray

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


def zonal_stats_xarray(dataset, fc, field, aggregation='mean'):
    """Perform extraction and grouping using xarray groupby method

    Args:
        dataset (xarray.Dataset): The Dataset from which the data have to be extracted
            Each dataarray should not have more than two dimensions
        fc (list): Feature collection to use for extraction
        field (str): Feature collection property to use for assigning labels
        aggregation (str): Spatial aggregation function to use (mean (default),
            median, std, min, max)

    Return:
        list: A list of [0] predictors array, and [2] target values [X, y]
    """
    # Rasterize feature collection
    arr = rasterize_xarray(fc, dataset)
    # Convert arr to a dataArray
    xr_arr = xr.DataArray(arr, dims=['x', 'y'], name='features_id')
    # Combine the Dataset with the DataArray
    combined = xr.merge([xr_arr, dataset])
    # Perform groupby aggregation
    if aggregation == 'mean':
        groups_xr = combined.groupby('features_id').mean()
    elif aggregation == 'median':
        groups_xr = combined.groupby('features_id').median()
    elif aggregation == 'std':
        groups_xr = combined.groupby('features_id').std()
    elif aggregation == 'min':
        groups_xr = combined.groupby('features_id').min()
    elif aggregation == 'max':
        groups_xr = combined.groupby('features_id').max()
    else:
        raise ValueError('Unsuported aggregation function')
    # Extract predictors and target values arrays
    X = groups_xr.to_array().values.transpose()
    ids = list(groups_xr.features_id.values.astype('uint32') - 1)
    y = [fc[x]['properties'][field] for x in ids]
    return [X, y]

def zonal_stats_pandas(dataset, fc, field, aggregation='mean',
                       categorical_variables=None):
    """Perform extraction and grouping using xarray groupby method

    Data are first coerced to pandas dataframe and pandas' groupby method is used
    to perform spatial aggregation

    Args:
        dataset (xarray.Dataset): The Dataset from which the data have to be extracted
            Each dataarray should not have more than two dimensions
        fc (list): Feature collection to use for extraction
        field (str): Feature collection property to use for assigning labels
        aggregation (str): Spatial aggregation function to use (mean (default),
            median, std, min, max)
        categorical_variable (list): A list of strings corresponding to the names
            of the categorical_variables

    Return:
        list: A list of [0] predictors array, and [2] target values [X, y]
    """
    # Build spatial aggregation mapping
    var_list = list(dataset.data_vars)
    agg_list = [(k, aggregation) if k not in categorical_variables else (k, 'first') for k in var_list]
    agg_ordered_dict = OrderedDict(agg_list)
    # Rasterize feature collection
    arr = rasterize_xarray(fc, dataset)
    # Convert arr to a dataArray
    xr_arr = xr.DataArray(arr, dims=['x', 'y'], name='features_id')
    # Combine the Dataset with the DataArray
    combined = xr.merge([xr_arr, dataset])
    # Coerce to pandas dataframe
    df = combined.to_dataframe().groupby('features_id').agg(agg_ordered_dict)
    X = df.values
    ids = list(df.index.values.astype('uint32') - 1)
    y = [fc[x]['properties'][field] for x in ids]
    return [X, y]
