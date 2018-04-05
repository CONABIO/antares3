"""
Compute region statistics after segmentation.

Published by Berkeley Environmental Technology International, LLC
Copyright (c) 2012 James Scarborough - All rights reserved

For the GDAL/OGR copyright notice and license please see:
  http://svn.osgeo.org/gdal/trunk/gdal/LICENSE.TXT
"""
import os
import numpy as np
from osgeo import ogr
from .image_gdal import read
from . import vectorize
from . import tools

P = tools.thisdir(__file__)

def stats(imagefile, regionfile, vectorfile, outfile=None,
          vfunctions=P+'stats_vector.py', rfunctions=P+'stats_raster.py'):
    r"""Read in data and function files and compute all stats.
    
    Use this on segmentation output data: original image name, the output
    segments image name, and a filename to save stats as a CSV.
    
    >>> stats('test/ag.bmp', 'test/output.tif', 'test/output.tif.shp',
    ...   'statstest.csv',
    ...   vfunctions={'area': lambda d: d['geometry'].Area()},
    ...   rfunctions={'max': lambda a: a.max()}) #doctest:+ELLIPSIS
    {0: {'b2_max': 74, 'b0_max': 152, 'id': 0, 'b1_max': 74, ...}...
    >>> open('statstest.csv').read() #doctest:+ELLIPSIS
    'id,area,b0_max,b1_max,b2_max\n0,15200.0,152,74,74\n1...'
    >>> stats('test/ag.bmp', 'test/output.tif', 'test/output.tif.shp',
    ...       'statstest.csv') #doctest:+ELLIPSIS
    {0: {'compact': 93699.092845128442,... 'id': 0, 'b2_min': 36,...}...}
    >>> os.remove('statstest.csv')
    """
    if isinstance(vfunctions, str):
        vfunctions = tools.readfunctions(vfunctions)
    if isinstance(rfunctions, str):
        rfunctions = tools.readfunctions(rfunctions)
    source = ogr.Open(vectorfile)
    shapes, regions = list(zip(*[(f.geometry().Clone(), f['id']) for f in source[0]]))
    vtable = vstats(shapes, regions, functions=vfunctions)
    rtable = rstats(read(imagefile), read(regionfile), functions=rfunctions)
    for r in vtable:
        vtable[r].update(rtable[r])
    if outfile:
        tools.csvwrite(outfile, vtable, key_field='id')
    return vtable

def vstats(shapes, regions, functions={}):
    """Compute vector stats given a list of polgons and their ids.
    
    Functions are passed a dictionary so core computations can be cached.
    See stats_vector module for decorator function and logic.
    
    >>> s = ogr.CreateGeometryFromWkt('POLYGON ((0 0,1 0,1 1,0 1,0 0))')
    >>> vstats([s], [0], functions={'area': lambda d: d['geometry'].Area(),
    ...                             'perimeter': lambda x: 4})
    {0: {'perimeter': 4, 'area': 1.0}}
    """
    table = {}
    for region, shape in zip(regions, shapes):
        row = {}
        data = {'geometry': shape}
        for name, function in list(functions.items()):
            row[name] = function(data)
        table[region] = row
    return table

def rstats(image, regions, functions={}):
    """Compute raster statistics across each band for each image object.
    
    >>> np.array([[0, 1]]).flatten()
    array([0, 1])
    >>> a = np.array([[[10,11]], [[20,21]]])
    >>> a.reshape((2, -1))
    array([[10, 11],
           [20, 21]])
    >>> a.reshape((2, -1)).T
    array([[10, 20],
           [11, 21]])
    
    >>> functions = {'max': lambda a: a.max(), 'min': lambda a: a.min()}
    >>> rstats(np.array([[[10], [20], [21]]]), np.array([[0, 1, 1]]),
    ...       functions=functions)
    {0: {'b0_max': 10, 'b0_min': 10}, 1: {'b0_max': 21, 'b0_min': 20}}
    
    >>> rstats(np.array([[[10,11], [20,21]]]), np.array([[0, 0]]),
    ...       functions=functions)
    {0: {'b1_min': 11, 'b0_max': 20, 'b0_min': 10, 'b1_max': 21}}
    """
    table = {}
    nbands = image.shape[-1]
    regions_flat, pixels_flat = regions.flat, image.reshape((-1, nbands))
    for region in range(regions.max() + 1):
        row = {}
        masked = np.compress(regions_flat == region, pixels_flat, axis=0)
        for b in range(nbands):
            band = masked.T[b]
            for name, function in list(functions.items()):
                row['b%s_%s' % (b, name)] = function(band)
        table[region] = row
    return table


if __name__ == '__main__':
    """Run Python standard module doctest which executes the >>> lines.
    
    If there are no errors, then nothing is printed. (No news is good news.)
    If there is an error in a unit test, the traceback will print.
    
    If no test keyword, feed command line flags to Python function.
    """
    import sys
    if '--test' in sys.argv:
        import doctest
        doctest.testmod()
    else:
        tools.commandline(stats, "For HELP run: stats.py --help")
