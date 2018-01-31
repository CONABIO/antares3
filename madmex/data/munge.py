'''
Created on Jan 31, 2018

@author: agutierrez
'''
import logging

from scipy import ndimage


logger = logging.getLogger(__name__)

def stats(t, labels, index):
    '''
        Receives a 'z' level from the xarray, then applies the mask and get statistics
        over every distinct feature (index) in the mask.
    '''
    logger.info('Applying mask to xarray')
    results = []

    mean = ndimage.mean(t.values.tolist(), labels=labels, index=index)
    maximum = ndimage.maximum(t.values.tolist(), labels=labels, index=index)
    median = ndimage.median(t.values.tolist(), labels=labels, index=index)
    minimum = ndimage.minimum(t.values.tolist(), labels=labels, index=index)
    std = ndimage.standard_deviation(t.values.tolist(), labels=labels, index=index)

    results.append(mean)
    results.append(maximum)
    results.append(median)
    results.append(minimum)
    results.append(std)

    return results