"""
BIS API: Berkeley Image Seg for Python, streamlined API for automated workflows.

Published by Berkeley Environmental Technology International, LLC
Copyright (c) 2012 James Scarborough - All rights reserved
This is not open source software, just inexpensive

Dependencies: GDAL, numpy
Code style: Python PEP8 -- http://www.python.org/dev/peps/pep-0008/
Unit tests: Run file from command line with --test to execute all >>> lines
Licensing: cregionmerge C-extension requires license.txt to be in this folder
Support and suggestions: support@BerkEnviro.com, +1-877-322-4670 (California)

This module allows execution and passing options from the command line

Revisions:
20120822 Integrate classify.py Weka command line wrapper
20120814 workflow.py wrapper demonstrating segmentation and post processing
20120808 Stats and Training modules, with pluggable stats/metrics functions
20120803 Vectorization to polygons module utilizing gdal.Polygonize
20120731 Fill/fix first pixel in nodata output with neighbor's label
20120728 NoData to region #0 option revived, plus survival through tiling
20120630 Deployment on PiCloud, dispatch and files layer above this package
20120619 Fix tiling bug of wrong combine order and non-sequential label ids
20120523 Add multiple threshold capability using generator function layer
20120521 Add command line parser/wrapper for main segment function
20120510 Essential functionality refactored from BIS 1.0rc8
"""
import os
import numpy as np
from . import image_gdal as image
from . import tools
try:
    from . import cregionmerge
except ImportError as e:
    print("Cannot import module")
    print("ERROR: %s" % e)

def segment(imagefile, t=10, s=0.5, c=0.5, tile=False, xt=5, rows=1000, mp=True,
            nodata=None):
    """Open image and send array to segment, save regions as int image file.
    
    't' is threshold integer or ordered list to kick out multiple thresholds.
    's' and 'c' are floats between 0 and 1.
    'tile' to True to process large image in chunks.
    'xt' is the tile threshold, raise to put more merging in the tile phase.
    'rows' is the size of the tiles (strips). If RAM problems, decrease this.
    'mp' uses Python multiprocessing module to dispatch tiles to cores.
    'nodata' is None for off or a masking integer, zero is OK to mask 0.
      Each band of a pixel must have the value to be recognized as nodata.
    
    Threshold controls size, a larger threshold maps bigger objects.
    Experiment with Shape and Compactness (0-1) to adjust boundary uniformity.
    
    Use this tool to automate different parameter runs to find the best combo.
    Thresholds with the same Shape and Compactness will geometrically nest.
    Give list of thresholds to kick out multiple scales from one run.
    
    Turn on tiling to split image to multiple cores then combine.
    Increase xt and decrease rows to put more work in more jobs.
    But not too much that you get seamlines in your final regions.
    
    This function and its arguments can be called from the command line:
    % python segment.py test/11-band.tif -t [20,50] --tile True --xt 10
    
    >>> segment('test/ag.bmp', t=5)
    ['test/ag.bmp_5_05_05.tif']
    >>> image.read('test/ag.bmp_5_05_05.tif')[-1, 0, 0]
    0
    >>> image.compare(image.read('test/truth_float.tif'),
    ...               image.read('test/ag.bmp_5_05_05.tif'))
    True
    >>> os.remove('test/ag.bmp_5_05_05.tif')
    >>> segment('test/11-band.tif', t=5) # GeoTiff with 11-bands
    ['test/11-band.tif_5_05_05.tif']
    >>> os.remove('test/11-band.tif_5_05_05.tif')
    >>> segment('test/11-band.tif', t=5, tile=True) # GeoTiff with 11-bands
    Traceback (most recent call last):
    ...
    ValueError: First t must be larger than tiling threshold xt
    >>> segment('test/ag.bmp', t=[5, 10])
    ['test/ag.bmp_5_05_05.tif', 'test/ag.bmp_10_05_05.tif']
    >>> os.remove('test/ag.bmp_5_05_05.tif')
    >>> os.remove('test/ag.bmp_10_05_05.tif')
    """
    if not isinstance(t, list):
        t = [t]
    array = image.read(imagefile)
    generator = segment_gen(array, t, s, c, tile, xt, rows, mp, nodata)
    outfiles = []
    for regions, ti in zip(generator, t):
        outfile = name(imagefile, ti, s, c)
        image.save(regions, outfile, georef=imagefile, compress='DEFLATE')
        outfiles.append(outfile)
    return outfiles

def segment_gen(array, t=[10], s=0.5, c=0.5, tile=False, xt=5, rows=1000,
                       mp=True, nodata=None):
    """Segment 3D array one threshold at a time and generate the region grids.
    
    Send an array to this function for raw capability to generate array output.
    
    >>> gen = segment_gen(image.read('test/ag.bmp'), t=[5, 10])
    >>> gen #doctest:+ELLIPSIS
    <generator object segment_gen at 0x...>
    >>> [array[0,-1] for array in gen]
    [1331, 336]
    """
    if tile:
        if not t[0] > xt:
            raise ValueError("First t must be larger than tiling threshold xt")
        merger = segmentor_tiles(array, s, c, xt, rows, mp, nodata)
    else:
        merger = segmentor(array, s, c, nodata=nodata)
    height, width, nbands = array.shape
    for ti in t:
        regions = np.zeros((height, width), dtype=np.int32)
        merger.merge(ti, regions)
        if nodata is not None:
            nodata_fix(regions, rows)
        yield regions

def segmentor(array, s=0.5, c=0.5, istile=False, xt=5, nodata=None):
    """Setup segmentation object, if a tile then generate initial run to xt.
    
    >>> segmentor([[[1, 1, 1]]]) #doctest:+ELLIPSIS
    <cregionmerge.cmerger object at 0x...>
    >>> g = segment_gen(np.array([[[1, 1, 1]]])) # Uses this function
    >>> list(g)[0]
    array([[0]])
    >>> segmentor([[[1, 1, 1]]], istile=True) #doctest:+ELLIPSIS
    {...'j': array([0]), ...}
    """
    array = np.asarray(array)
    height, width, nbands = array.shape
    size = height * width
    nd, ndv = nodata_(nodata)
    merger = cregionmerge.cmerger(array, size, width, height, nbands, s, c,
                                  nodata=nd, nd_val=ndv)
    if istile:
        merger.merge(xt, np.zeros((height, width), dtype=np.int32))
        return freeze(merger)
    else:
        return merger

def segmentor_tiles(array, s=0.5, c=0.5, xt=5, rows=1000, mp=True,
                    nodata=None):
    """Split image by rows, segment the tiles, then combine to new object.
    
    >>> segmentor_tiles(np.array([[[1, 1, 1]], [[2, 2, 2]]]), rows=1, mp=False)
    ...   #doctest:+ELLIPSIS
    <cregionmerge.cmerger object at 0x...>
    >>> g = segment_gen(np.array([[[1, 1, 1]], [[2, 2, 2]]]), tile=True, rows=1,
    ...                 mp=False)  # Uses this function
    >>> list(g)[0] #doctest:+NORMALIZE_WHITESPACE
    array([[0], [0]])
    >>> untiled = image.read(segment('test/ag.bmp')[0])
    >>> tiled = image.read(segment('test/ag.bmp', tile=True)[0])
    >>> image.compare(untiled, tiled) # tiled didn't actually get split
    True
    >>> tiled = image.read(segment('test/ag.bmp', tile=True, rows=70)[0])
    >>> image.compare(untiled, tiled) # does get split, and not exactly same
    False
    >>> tiled.max()+1, untiled.max()+1 # ...but close, similar num of segments.
    (335, 338)
    >>> os.remove('test/ag.bmp_10_05_05.tif')
    """
    tiles = split(array, rows)
    if mp:
        freezes = tools.map(segmentor,
                           [(a, s, c, True, xt, nodata) for a in tiles])
    else:
        freezes = [segmentor(a, s, c, True, xt, nodata) for a in tiles]
    tot_regions = sum([freeze['j'].max() + 1 for freeze in freezes])
    height, width, nbands = array.shape
    nd, ndv = nodata_(nodata)
    big = cregionmerge.cmerger(None, tot_regions, width, height, nbands, s, c,
                               no_load=True, nodata=nd, nd_val=ndv)
    combine(big, freezes, width, xt, nd=nd)
    return big

def split(array, rows=1000):
    """Return list of views into mama array given how many rows per tile.
    
    Expects pixel interleaved. Pass np.split exact rows to split on.
    
    >>> array = np.array([[[1], [2]], [[3], [4]], [[5], [6]]]) # 3 rows
    >>> rows = 1
    >>> np.arange(len(array))[::rows][1:] # Will split at 0, 1, and 2
    array([1, 2])
    >>> split(array, rows) #doctest:+NORMALIZE_WHITESPACE
    [array([[[1], [2]]]), array([[[3], [4]]]), array([[[5], [6]]])]
    >>> split(array, 2) #doctest:+NORMALIZE_WHITESPACE
    [array([[[1], [2]], [[3], [4]]]), array([[[5], [6]]])]
    >>> image.compare(array, np.concatenate(split(array, 2))) # Cat is opposite
    True
    >>> split(array) #If no splitting happening #doctest:+NORMALIZE_WHITESPACE
    [array([[[1], [2]], [[3], [4]], [[5], [6]]])]
    """
    if len(array) <= rows:
        return [array]
    else:
        return np.split(array, np.arange(len(array))[::rows][1:])

def freeze(merger):
    """Return the (proprietary) innards of the merger state.
    
    >>> a = np.array([[[1, 1, 1]]])
    >>> height, width, nbands = a.shape
    >>> merger = cregionmerge.cmerger(a, height*width, width, height, nbands,
    ...                               0.5, 0.5)
    >>> regions = np.zeros((height, width), dtype=np.int32)
    >>> merger.merge(5, regions)
    1
    >>> freeze(merger) #doctest:+ELLIPSIS
    {'a': array([1, 1, 1]), ...'j': array([0]), 'l': array([0]), ...}
    """
    return merger.freeze2()

def combine(cmerger, freezes, width, threshold, nd=False):
    """Load states from frozen tiles into big cmerger object.
    """
    pix_offset = row_offset = reg_offset = 0
    freezes.reverse()
    for freeze in freezes:
        size = len(freeze['j'])
        n = cmerger.combine2(freeze, size, pix_offset, row_offset, reg_offset,
                             nodata=nd)
        pix_offset += size
        row_offset += size / width
        reg_offset += n
    cmerger.combine_init(threshold)

def name(filename, threshold=5, shaperate=0.5, compactnessrate=0.5,
         ext='tif', sep='_'):
    """Compose an output filename signifying the segmentation parameters.
    
    >>> name('filename.inp')
    'filename.inp_5_05_05.tif'
    >>> name('./test.inp', 100, 0.75, 1.0, ext='jpg') # Path and floats
    './test.inp_100_075_10.jpg'
    >>> name('/wherethefileis/filename.inp') # Puts output where input is
    '/wherethefileis/filename.inp_5_05_05.tif'
    """
    params = sep.join([str(x).replace('.', '')
                       for x in (threshold, shaperate, compactnessrate)])
    return filename + sep + params + '.' + ext

def nodata_(nodata):
    """Expand nodata variable from None or an int to tuple of bool and the int.
    
    >>> nodata_(None)
    (False, 0)
    >>> nodata_(-9999)
    (True, -9999)
    >>> nodata_(0) # Thus can pass zero for the value
    (True, 0)
    """
    return (nodata is not None, nodata or 0)

def nodata_fix(regions, rows):
    """Fill the first-pixel-per-tile holes left by nodata processing.
    
    Just grab region label immediately east. Process in-place, nothing returned.
    
    >>> np.array([0, 1, 2, 3])[::2] # Skipping slice
    array([0, 2])
    >>> regions = np.array([[5, 6, 0], [3, 4, 0], [0, 2, 0], [0, 1, 0]])
    >>> rows = 3
    >>> np.arange(len(regions))[::rows] - 1 # The end index of each former tile
    array([-1,  2])
    >>> nodata_fix(regions, rows)
    >>> regions #doctest:+NORMALIZE_WHITESPACE
    array([[5, 6, 0], [3, 4, 0], [2, 2, 0], [1, 1, 0]])
    
    >>> im = image.read('test/ag.bmp').astype(int)
    >>> im[-1,0:5] # Last row, first 5 pixels
    array([[126,  54,  57],
           [130,  58,  61],
           [135,  60,  64],
           [129,  54,  58],
           [142,  63,  68]])
    >>> im[:,2:4,:] = -9999 # Burn a vertical band of nodata
    >>> im[-1,0:5]
    array([[  126,    54,    57],
           [  130,    58,    61],
           [-9999, -9999, -9999],
           [-9999, -9999, -9999],
           [  142,    63,    68]])
    >>> g = segment_gen(im, mp=True, nodata=-9999, tile=True, rows=50)
    >>> regions = list(g)[0]
    >>> regions[-3:-1,0:5] # Bottom of image, pixel zero is not val zero
    array([[1, 1, 0, 0, 2],
           [1, 1, 0, 0, 2]])
    >>> regions[50-1:50+2,0:5] # OK at tile edge also
    array([[205, 205,   0,   0, 208],
           [205, 205,   0,   0, 208],
           [205, 205,   0,   0, 208]])
    """
    indices = np.arange(len(regions))[::rows] - 1
    regions[indices,0] = regions[indices,1]


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
        tools.commandline(segment, "For HELP run: segment.py --help")
