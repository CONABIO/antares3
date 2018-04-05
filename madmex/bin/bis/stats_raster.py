"""
Library of raster functions that will be run during stats computation.

Each function will be called per region per band.
A 1D numpy array will sent as the sole argument.
Each function as named here will be a column heading in stats csv file.

Published by Berkeley Environmental Technology International, LLC
Copyright (c) 2012 James Scarborough - All rights reserved
"""
import numpy as np

def max(array):
    """Return max value of the array.
    
    >>> max([1, 2])
    2
    """
    return np.max(array)

def min(array):
    """Return min value of the array.
    
    >>> min([1, 2])
    1
    """
    return np.min(array)

def mean(array):
    """Return the mean of the array.
    
    >>> mean([1, 2])
    1.5
    """
    return np.mean(array)

def std(array):
    """Return the standard deviation of the array.
    
    >>> std([1, 2])
    0.5
    """
    return np.std(array)


if __name__ == '__main__':
    "Run Python standard module doctest which executes the >>> lines."
    import doctest
    doctest.testmod()
