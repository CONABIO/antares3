'''
Created on Jan 16, 2018

@author: rmartinez
'''

import numpy
import logging
import xarray

from scipy import ndimage
from madmex.management.base import AntaresBaseCommand


logger = logging.getLogger(__name__)

def stats(t):
    '''
        Receives a 'z' level from the xarray, then applies the mask and get statistics
        over every distinct feature (index) in the mask.
    '''
    looger.info('Applying mask to xarray')
    results = []

    mean    = ndimage.mean(t.values.tolist(), labels=labels, index=index)
    maximum = ndimage.maximum(t.values.tolist(), labels=labels, index=index)
    median  = ndimage.median(t.values.tolist(), labels=labels, index=index)
    minimum = ndimage.minimum(t.values.tolist(), labels=labels, index=index)
    std     = ndimage.standard_deviation(t.values.tolist(), labels=labels, index=index)
    var     = ndimage.variance(t.values.tolist(), labels=labels, index=index)

    results.append(mean)
    results.append(maximum)
    results.append(median)
    results.append(minimum)
    results.append(std)
    results.append(var)
    
    return results

class Command(AntaresBaseCommand):
    help = '''
Computes zonal statistics for every feature in a mask datasource across an xarray datasource.
The mask is a numpy.ndarray like:

            [[ 1.  1.  0.  0.  0.]
             [ 1.  1.  0.  0.  0.]
             [ 0.  0.  2.  2.  2.]
             [ 0.  0.  2.  2.  2.]
             [ 0.  0.  2.  2.  2.]]

Where 1, 2, .. etc represents features to analyze for zonal stats. 
This mask is apllyed to a xarray that represents satellite, bio-climatics, digital elevations models, etc. 
The xarray can privide many of this information at the same time, for that reason the shape of the xarray 
can be like  

            (5, 5, 3)  for ('x', 'y', 'z') 

Where 'z' represents the informations written before. Sometimes, 'z' represents time over a serie of time
over the same place. 
The zonal stats get information over every 'z' level according the mask over the xarray.
For now, 6 distinct statistics are applied:
    
            mean, max, median, min, standard deviation and variance

Args:
        xarray (numpy.ndarray object ): Xarray from datacube data base
        mask (xarray.DataArray object): Numpy array 

Returns:
        bool: The return value. True for success, False otherwise.


--------------
Example usage:
--------------

python madmex.py zonal_stats --xarray <xarray_from_data_cube> --mask <numpy.ndarray>
# 
''' 
    def add_arguments(self, parser):
        '''
            Requires a raster file and a vector shapefile.
        '''
        parser.add_argument('--xarray', nargs=1, help='xarray from datacube data base.')
        parser.add_argument('--mask', nargs=1, help='numpy.ndarray with 1 in the 1st feature, 2 in de second and so on')

    def handle(self, **options):
        '''
        
        '''
        xarr = options['xarray'][0]
        mask  = options['mask'][0]


        for i in range(xarr.shape[2]):
            looger.info('Processing time', i)
            z = xarr.isel(time=int(i))
            looger.info('Getting indexes from mask')
            index = numpy.unique(mask)
            looger.info('Computing statistics over layer ', i)
            st = stats(z)
            stat_xr = xarray.DataArray(st)
            
        

