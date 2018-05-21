'''
Created on Jan 31, 2018

@author: agutierrez
'''
from importlib import import_module
import logging
from collections import OrderedDict

import numpy as np
import xarray as xr
import dask

from madmex.overlay.conversions import rasterize_xarray
from madmex.util import chunk

logger = logging.getLogger(__name__)
dask.set_options(get=dask.get)

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


def zonal_stats_xarray(dataset, fc, field, aggregation='mean',
                       categorical_variables=None):
    """Perform extraction and grouping using pandas' groupby method

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
    if categorical_variables is None:
        categorical_variables = []
    agg_list = [(k, aggregation) if k not in categorical_variables else (k, 'first') for k in var_list]
    agg_ordered_dict = OrderedDict(agg_list)
    # Divide extraction in chunks to avoid blowing memory
    X_list = []
    y_list = []
    for fc_sub in chunk(fc, 10000):
        fc_sub = list(fc_sub)
        # Rasterize feature collection
        arr = rasterize_xarray(fc_sub, dataset)
        # Convert arr to a dataArray
        xr_arr = xr.DataArray(arr, dims=['y', 'x'], name='features_id')
        # Combine the Dataset with the DataArray
        combined = xr.merge([xr_arr, dataset])
        combined = combined.chunk({'x': 1000, 'y': 1000})
        # Get rid of everything that is np.nan in features_id variable
        # 1: flatten, 2: delete nans
        combined = combined.stack(z=('x', 'y')).reset_index('z').drop(['x', 'y'])
        combined = combined.where(np.isfinite(combined['features_id']), drop=True)
        combined = combined.compute()
        # Coerce to pandas dataframe
        df = combined.to_dataframe()
        combined = None
        df = df.groupby('features_id').agg(agg_ordered_dict)
        X_list.append(df.values)
        # TODO: Use numpy.array instead of list here to reduce memory footprint (see np.vectorize)
        ids = list(df.index.values.astype('uint32') - 1)
        y_list.append(np.array([fc_sub[x]['properties'][field] for x in ids]))
    # Deallocate array
    dataset = None
    y = np.concatenate(y_list)
    X = np.concatenate(X_list, axis=0)
    return [X, y]
