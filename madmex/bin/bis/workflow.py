"""
Chain together main segmentation function with post processing.

Published by Berkeley Environmental Technology International, LLC
Copyright (c) 2012 James Scarborough - All rights reserved
"""
import os
from . import segment, vectorize, stats, train #,classify
from . import tools

def workflow(imagename, do_vectorize=True, do_stats=True, do_train=True,
             do_classify=True, **kwargs):
    """A wrapper worflow performing segmentation and all post processing.
    
    You may include segmentation parameters as usual and they will be passed.
    
    >>> files = workflow('test/ag.bmp', t=20)
    >>> files #doctest:+NORMALIZE_WHITESPACE
    ['test/ag.bmp_20_05_05.tif', 'test/ag.bmp_20_05_05.tif.shp',
     'test/ag.bmp_20_05_05.tif.dbf', 'test/ag.bmp_20_05_05.tif.shx',
     'test/ag.bmp_20_05_05.tif_stats.csv', 'test/ag.bmp_20_05_05.tif_train.csv']
    >>> all(map(os.path.exists, files))
    True
    >>> ',class,' in open('test/ag.bmp_20_05_05.tif_stats.csv').read()
    True
    >>> for f in files: os.remove(f)
    """
    regionimages = segment.segment(imagename, **kwargs)
    postfiles = []
    for regionimage in regionimages:
        if do_vectorize or do_stats or do_train:
            vectorfiles = [regionimage + ex for ex in ('.shp', '.dbf', '.shx')]
            vectorize.vectorize(regionimage, vectorfiles[0])
            postfiles += vectorfiles
        
        if do_stats:
            statsfile = regionimage + '_stats.csv'
            stats.stats(imagename, regionimage, vectorfiles[0], statsfile)
            postfiles += [statsfile]
        
        if do_train:
            "Needs user supplied groundtruth shapefile with 'class' field."
            trainfile = regionimage + '_train.csv'
            train.train(vectorfiles[0], imagename + '_train.shp', trainfile,
                        field='class')
            postfiles += [trainfile]
        
        if do_stats and do_train:
            "For classification, add single 'class' col from training to stats."
            tools.csvadd(statsfile, 'id', trainfile, 'class', outname=statsfile)

        if do_classify: ##############
            "Call WEKA wrapper, To do"
            pass
        
    return regionimages + postfiles


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
        tools.commandline(workflow, "For HELP run: workflow.py --help",
                          function2=segment.segment)
