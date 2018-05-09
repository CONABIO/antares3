"""
Compute goodness metrics and train segments after segmentation.

Published by Berkeley Environmental Technology International, LLC
Copyright (c) 2012 James Scarborough - All rights reserved

For the GDAL/OGR copyright notice and license please see:
  http://svn.osgeo.org/gdal/trunk/gdal/LICENSE.TXT
"""
import os.path
from osgeo import ogr
from osgeo.ogr import CreateGeometryFromWkt as _wkt
from . import tools

P = tools.thisdir(__file__)

def train(vectorfile, truthfile, outfile=None, functions=P+'train_metrics.py',
          field='class', precision=3):
    r"""Compare each segment to the relevant groundtruth polygon, save as CSV.
    
    >>> train('test/output.tif.shp', 'test/ag.bmp_train.shp',
    ...       'output_train.csv') #doctest:+ELLIPSIS
    {...327: {'id': 327,... 'class': 'white',... 'dmetric': 1.002}...}
    >>> open('output_train.csv').read() #doctest:+ELLIPSIS
    'id,class,dmetric,overseg,underseg\n0...327,white,1.002,...'
    >>> import os
    >>> os.remove('output_train.csv')
    """
    rsource, tsource = ogr.Open(vectorfile), ogr.Open(truthfile)
    regions = [(f['id'], f.geometry().Clone()) for f in rsource[0]]
    truths = [(f[field], f.geometry().Clone()) for f in tsource[0]]
    funcs = tools.readfunctions(functions)
    table = metrics(regions, truths, functions=funcs, precision=precision)
    if outfile:
        tools.csvwrite(outfile, table, key_field='id')
    return table

def metrics(regions, truths, functions, field='class', precision=3):
    """Compare each segment to the relevant groundtruth poly, compute metrics.
    
    >>> import train_metrics as tm
    >>> functions = {'Relevant': tm.Relevant, 'underseg': tm.underseg}
    >>> rs = [(0, _wkt('POLYGON ((0 0,1 0,1 1,0 1,0 0))'))]
    >>> ts = [(1, _wkt('POLYGON ((0 0,1 0,1 1,0 1,0 0))'))]
    >>> metrics(rs, ts, functions=functions)
    {0: {'underseg': 0.0, 'class': 1}}
    """
    Relevant = functions.pop('Relevant')
    table = {}
    for i, region in regions:
        row = dict.fromkeys(list(functions.keys()) + [field], None)
        for t, truth in truths:
            if Relevant(region, truth):
                "Only apply metrics to first relevant truth shape encountered."
                for name, function in functions.items():
                    row[name] = round(function(region, truth), precision)
                row[field] = t
                break
        table[i] = row
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
        tools.commandline(train, "For HELP run: train.py --help")
