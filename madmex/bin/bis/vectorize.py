"""
Vectorize an image segmentation output to a polygon shapefile.

Published by Berkeley Environmental Technology International, LLC
Copyright (c) 2012 James Scarborough - All rights reserved

For the GDAL/OGR copyright notice and license please see:
  http://svn.osgeo.org/gdal/trunk/gdal/LICENSE.TXT
"""
import os
import tempfile
from osgeo import gdal, ogr
from . import image_gdal as image
from . import tools

def vectorize(imagefile, vectorfile, band=1, driver='ESRI Shapefile',
              field=('id', ogr.OFTInteger)):
    """Vectorize single band image of region lables to shapefile of polygons.
    
    Notes: Overwrite shapefile, pix value/region ID saved to ID field,
    projection transfered automatically, unless no projection which we fix.
    
    >>> vectorize('test/11-band.tif', 'test.shp') # Copies projection itself
    27676
    >>> image.read('test/11-band.tif')[0, 0] # Upper left pixel, 11 bands
    array([48, 19, 16, 34, 37, 15, 15, 55, 40, 30, 12], dtype=int16)
    >>> shapefile = ogr.Open('test.shp')
    >>> upper_left = shapefile[0][0] # First feature is upper left
    >>> upper_left.items() # First pixel first band was value 48
    {'id': 48}
    >>> gdal.Open('test/11-band.tif').GetGeoTransform() # Upper-left corner
    (399255.0, 30.0, 0.0, 2605275.0, 0.0, -30.0)
    >>> coords = eval(upper_left.geometry().ExportToJson())['coordinates'][0]
    >>> coords #doctest:+NORMALIZE_WHITESPACE
    [[399255.0, 2605275.0], [399285.0, 2605275.0], [399285.0, 2605245.0],
     [399255.0, 2605245.0], [399255.0, 2605275.0]]
    >>> [(x - 399255, y - 2605275) for (x, y) in coords] # De-offset to check
    [(0.0, 0.0), (30.0, 0.0), (30.0, -30.0), (0.0, -30.0), (0.0, 0.0)]
    >>> del shapefile # Note top left polygon extends east and south
    >>> all(map(os.path.exists, ['test.shp', 'test.shx', 'test.dbf']))
    True
    
    >>> import shutil
    >>> shutil.copy('test/truth_float.tif', 'raster.tif') # Has null projection
    >>> image.read('raster.tif').max() + 1
    1332.0
    >>> vectorize('raster.tif', 'test.shp')
    1332
    >>> image.read('test/truth_float.tif')[0, 0] # Upper left pixel, 11 bands
    array([ 1323.], dtype=float32)
    >>> shapefile = ogr.Open('test.shp')
    >>> last = shapefile[0].GetFeatureCount()
    >>> upper_left = shapefile[0][0] # Feature zero is upper left
    >>> upper_left.items()
    {'id': 1323}
    >>> upper_left.geometry().ExportToWkt() # Note nudging, then east and south
    'POLYGON ((-0.5 0.5,8.5 0.5,8.5 -0.5,-0.5 -0.5,-0.5 0.5))'
    >>> gdal.Open('raster.tif').GetGeoTransform() # Back to null
    (0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
    
    >>> del shapefile
    >>> for f in ['test.shp', 'test.shx', 'test.dbf']: os.remove(f)
    >>> os.remove('raster.tif')
    """
    image = gdal.Open(imagefile)
    altered, null = False, (0, 1, 0, 0, 0, 1)
    if image.GetGeoTransform() == null:
        """Default/null transform will result in upside-down shapefile.
        These parameters make it overlay in ArcMap 10, nudge left and up.
        AV3, FWTools, others(?) will display differently!"""
        image = gdal.Open(imagefile, True)
        image.SetGeoTransform((-0.5, 1, 0, 0.5, 0, -1))
        altered = True
    driver = ogr.GetDriverByName(driver)
    if os.path.exists(vectorfile):
        driver.DeleteDataSource(vectorfile)
    vectorsource = driver.CreateDataSource(vectorfile)
    layer = vectorsource.CreateLayer('polygon', None, ogr.wkbPolygon)
    layer.CreateField(ogr.FieldDefn(*field))
    gdal.Polygonize(image.GetRasterBand(band), maskBand=None, outLayer=layer,
                    iPixValField=0, options=[], callback=None,
                    callback_data=None)
    if altered:
        image.SetGeoTransform(null)
    return layer.GetFeatureCount()


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
        tools.commandline(vectorize, "For HELP run: vectorize.py --help")
