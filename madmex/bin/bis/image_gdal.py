"""
Read and write image files to Numpy arrays using the GDAL library.

Published by Berkeley Environmental Technology International, LLC
Copyright (c) 2012 James Scarborough - All rights reserved

For the GDAL/OGR copyright notice and license please see:
  http://svn.osgeo.org/gdal/trunk/gdal/LICENSE.TXT
"""
import os
import numpy as np
from osgeo import gdal_array, gdal, ogr

def read(filename, pixel=True):
    """Use GDAL to open a band-interleaved image as a numpy array.
    
    Force 3D array for 1-band images as segment assumes 3D array shape.
    Doctests using == because 64-bit gives Long (with "L") and 32-bit gives Int
    
    >>> truth = read('test/truth_float.tif')
    >>> truth.shape == (127, 212, 1)
    True
    >>> truth[-1, 0, 0]
    0.0
    >>> orig = read('test/ag.bmp', pixel=False)
    >>> orig.shape == (3, 127, 212) # Note: band interleaved
    True
    >>> orig[:, -1, 0]
    array([126,  54,  57], dtype=uint8)
    >>> read('test/ag.bmp').shape == (127, 212, 3)
    ...   # Default is pixel-interleaved
    True
    """
    array = gdal_array.LoadFile(filename)
    if len(array.shape) == 2:
        array = np.asarray([array])
    if pixel:
        array = roll(array, 'left')
    return array

def save(array, filename, dtype=None, georef=None, compress=None, pixel=True):
    """Export a numpy array as a band-interleaved GDAL image.
    
    georef clones transform, projection, and GCPs from source image filename.
    Compression with DEFLATE better than LZW, need to use predictor for ints.
    
    >>> a1 = read('test/truth_float.tif')
    >>> save(a1, 'copy.tif')
    >>> a2 = read('copy.tif')
    >>> compare(a1, a2)
    True
    >>> os.remove('copy.tif')
    >>> row = [[255, 0, 0, 128]] * 10 # 4-band, 10-cols, pixel interleaved
    >>> a = np.array([row, row, row], dtype=np.uint8) # 3-rows
    >>> save(a, 'bands.tif', dtype=np.uint8)
    >>> read('bands.tif')[0, 0] # Read a pixel, from pixel interleaved
    array([255,   0,   0, 128], dtype=uint8)
    >>> os.remove('bands.tif')
    
    >>> gdal.Open('test/ag.bmp').GetGeoTransform()
    (95.0, 10.0, 0.0, 105.0, 0.0, -10.0)
    >>> save(read('test/ag.bmp'), 'copy.tif', georef='test/ag.bmp')
    >>> gdal.Open('copy.tif').GetGeoTransform()
    (95.0, 10.0, 0.0, 105.0, 0.0, -10.0)
    
    >>> os.path.getsize('copy.tif') # Uncompressed by default
    81114L
    >>> save(read('test/ag.bmp'), 'copy.tif', georef='test/ag.bmp',
    ...      compress='DEFLATE')
    >>> os.path.getsize('copy.tif')
    48109L
    >>> os.remove('copy.tif')
    """
    if dtype:
        array = array.astype(dtype)
    if pixel and len(array.shape) > 2:
        array = roll(array, 'right')
    if compress is None:
        options = []
    else:
        "Optimized for int image compression"
        options = ['COMPRESS=%s' % compress, 'PREDICTOR=2']
    driver = gdal.GetDriverByName('GTiff')
    driver.CreateCopy(filename, gdal_array.OpenArray(array, georef),
                      options=options)

def roll(array, direction):
    """Reorder axes to/from pixel-interleaved (BIS) and band-interleaved (GDAL).
    
    Per numpy doc: Transpose returns a 'view' with axes transposed.
    
    >>> pix = np.zeros((127, 212, 3))
    >>> band = roll(pix, 'right')
    >>> band.shape == (3, 127, 212)
    True
    >>> roll(band, 'left').shape == (127, 212, 3)
    True
    """
    if direction == 'right':
        "Pixel->Band: (0, 1, 2) rolls to (2, 0, 1)"
        return array.transpose(2, 0, 1)
    elif direction == 'left':
        "Band->Pixel: (0, 1, 2) rolls to (1, 2, 0)"
        return array.transpose(1, 2, 0)

def compare(array1, array2):
    """Are two arrays identical?  Can pass array or image filename.
    
    >>> compare([[0, 1]], [[0, 1]])
    True
    >>> compare([[0, 1]], [[0, 2]])
    False
    """
    if isinstance(array1, str):
        array1, array2 = read(array1), read(array2)
    return np.array_equal(array1, array2)

gdal.PushErrorHandler('CPLQuietErrorHandler')
def isdataset(filename):
    """Return True if the filename can be opened by GDAL.
    
    Needs to have GDAL_DATA set properly for some formats
    Also relies on finding .hdr files for some formats (ENVI)
    Don't print to stderr: gdal.PushErrorHandler('CPLQuietErrorHandler')
    
    >>> isdataset('test/ag.bmp')
    True
    >>> isdataset('test/ag.bpw')
    False
    """
    return gdal.Open(filename) is not None


if __name__ == '__main__':
    "Run Python standard module doctest which executes the >>> lines."
    import doctest
    doctest.testmod()
