'''
Created on Jan 16, 2018

@author: rmartinez
'''

import numpy
import ogr
import osr
import gdal
import logging
import xarray
import rasterio

from madmex.management.base import AntaresBaseCommand


logger = logging.getLogger(__name__)

def rasterio_to_xarray(fname):
    '''Converts the given file to an xarray.DataArray object.

    Arguments:
     - `fname`: the filename of the rasterio-compatible file to read
    
    Returns:
        An xarray.DataArray object containing the data from the given file,
        along with the relevant geographic metadata.
    
    Notes:
    
    This produces an xarray.DataArray object with two dimensions: x and y.
    The co-ordinates for these dimensions are set based on the geographic
    reference defined in the original file.
    '''
    
    with rasterio.open(fname) as src:
        data = src.read(1)

        # Set values to nan wherever they are equal to the nodata
        # value defined in the input file
        data = numpy.where(data == src.nodata, numpy.nan, data)

        # Get coords
        nx, ny = src.width, src.height
        x0, y0 = src.bounds.left, src.bounds.top
        dx, dy = src.res[0], -src.res[1]

        coords = {'y': numpy.arange(start=y0, stop=(y0 + ny * dy), step=dy),
                  'x': numpy.arange(start=x0, stop=(x0 + nx * dx), step=dx)}

        dims = ('y', 'x')
        attrs = {}

        try:
            aff = src.affine
            attrs['affine'] = aff.to_gdal()
        except AttributeError:
            pass

        try:
            c = src.crs
            attrs['crs'] = c.to_string()
        except AttributeError:
            pass

    return xarray.DataArray(data, dims=dims, coords=coords, attrs=attrs)

def read_shapefile(input_zone_polygon):
    '''
        Given a raster path, it opens it and returns the dataset.
    '''

    shp = ogr.Open(input_zone_polygon)
    lyr = shp.GetLayer()
    return lyr

def get_raster_georeference_from_xarray(ordered_dict):
    '''

    '''
    xOrigin     = list(ordered_dict.values())[0][0] 
    yOrigin     = list(ordered_dict.values())[0][3] 
    pixelWidth  = list(ordered_dict.values())[0][1] 
    pixelHeight = list(ordered_dict.values())[0][5]

    return xOrigin, yOrigin, pixelWidth, pixelHeight

class Command(AntaresBaseCommand):
    help = '''
Computes zonal statistics for every feature in a vector datasource across in a raster datasource.

--------------
Example usage:
--------------

python madmex.py zonal_stats --raster /path/to/raster/data.tif --shapefile /path/to/raster/vector.shp
# 
''' 
    def add_arguments(self, parser):
        '''
        Requires a raster file and a vector shapefile.
        '''
        parser.add_argument('--raster', nargs=1, help='Path to raster data.')
        parser.add_argument('--shapefile', nargs=1, help='Path to shapefile data.')

    def handle(self, **options):
        '''
        
        '''
        raster = options['raster'][0]
        shape  = options['shapefile'][0]        
        logger.info('Raster file : %s ' % raster)
        logger.info('Shapefile : %s' % shape)
        logger.info('Converting the given raster file to an xarray.DataArray object')
        xarr = rasterio_to_xarray(raster)

        xO, yO, pW, pH = get_raster_georeference_from_xarray(xarr.attrs)

        logger.info('Reading shapefile')
        vector_data = read_shapefile(shape)

        

