'''
Created on Jan 16, 2018

@author: rmartinez
'''

import logging

import numpy
import xarray

from madmex.data.munge import stats
from madmex.management.base import AntaresBaseCommand


logger = logging.getLogger(__name__)

class Command(AntaresBaseCommand):
    help = '''
Computes zonal statistics for every feature in a mask datasource across the xarray datasource.
The mask is a numpy.ndarray like:

            [[ 1.  1.  0.  0.  0.]
             [ 1.  1.  0.  0.  0.]
             [ 0.  0.  2.  2.  2.]
             [ 0.  0.  2.  2.  2.]
             [ 0.  0.  2.  2.  2.]]

Where 1, 2, .. etc represents features to analyze for zonal stats. 
This mask is applied to the xarray that represents satellite data, bio-climatics information, digital elevations models, etc. 
The xarray can privide many of this information at the same time, for that reason the shape of the xarray 
can be like  

            (3, 5, 5)  for ('z', 'y', 'x') 

Where 'z' represents the information described above. Sometimes, 'z' represents 'time' over a serie of time
over the same place. 
The zonal stats get information over every 'z' level according with the mask over the xarray.
For now, 5 distinct statistics are applied:
    
            mean, max, median, min and standard-deviation

Args:
        xarray (numpy.ndarray): Xarray from datacube database
        mask (xarray.DataArray): Numpy array 

Returns:
        statistics (xarray.DataArray): An xarray with the statistics computed.


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
        parser.add_argument('--mask', nargs=1, help='numpy.ndarray with 1 in the 1st feature, 2 for the 2nd one and so on')

    def handle(self, **options):
        '''
        
        '''
        xarr = options['xarray'][0]
        mask  = options['mask'][0]
        
        logger.info('Getting indexes from mask')
        index = numpy.unique(mask)


        for i in range(xarr.shape[0]):
            logger.info('Processing time', i)
            z = xarr.isel(time=int(i))            
            logger.info('Computing statistics over layer ', i)
            st = stats(z, mask, index)
            stat_xr = xarray.DataArray(st)
            print(stat_xr)
