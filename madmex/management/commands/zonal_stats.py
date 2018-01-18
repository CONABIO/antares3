'''
Created on Jan 16, 2018

@author: rmartinez
'''

import numpy
import logging
import xarray
import rasterio
import fiona
import json
import pprint

from osgeo import ogr, osr, gdal
from scipy import stats
from madmex.management.base import AntaresBaseCommand


logger = logging.getLogger(__name__)

def rasterio_to_xarray(fname):
    '''
        Converts the given file to an xarray.DataArray object.

        Arguments:
         - fname: the filename of the rasterio-compatible file to read
        
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


def get_raster_georeference_from_xarray(ordered_dict):
    '''
        Given an OrderedDict collection from xarray, returns georeference info.
    '''
    xOrigin     = list(ordered_dict.values())[0][0] 
    yOrigin     = list(ordered_dict.values())[0][3] 
    pixelWidth  = list(ordered_dict.values())[0][1] 
    pixelHeight = list(ordered_dict.values())[0][5]

    return xOrigin, yOrigin, pixelWidth, pixelHeight

def zonal_stats_by_feat(feat, input_zone_polygon, input_value_raster):
    '''
    '''
    #logger.info('Converting the given raster file to an xarray.DataArray object')
    #xarr = rasterio_to_xarray(rasterg)

    #logger.info('Extracting georeference data from xarray raster')
    #xO, yO, pW, pH = get_raster_georeference_from_xarray(xarr.attrs)

    raster = gdal.Open(input_value_raster)
    shp = ogr.Open(input_zone_polygon)
    lyr = shp.GetLayer() 

    transform = raster.GetGeoTransform()
    xOrigin = transform[0]
    yOrigin = transform[3]
    pixelWidth = transform[1]
    pixelHeight = transform[5]

    #logger.info('Reprojecting vector file to same as raster')
    sourceSR = lyr.GetSpatialRef()
    targetSR = osr.SpatialReference()
    targetSR.ImportFromWkt(raster.GetProjectionRef())
    coordTrans = osr.CoordinateTransformation(sourceSR,targetSR)
    geom = feat.GetGeometryRef()
    geom.Transform(coordTrans)


    # Get extent of feat
    geom = feat.GetGeometryRef()
    if (geom.GetGeometryName() == 'MULTIPOLYGON'):
        count = 0
        pointsX = []; pointsY = []
        for polygon in geom:
            geomInner = geom.GetGeometryRef(count)
            ring = geomInner.GetGeometryRef(0)
            numpoints = ring.GetPointCount()
            for p in range(numpoints):
                lon, lat, z = ring.GetPoint(p)
                pointsX.append(lon)
                pointsY.append(lat)
            count += 1
    elif (geom.GetGeometryName() == 'POLYGON'):
        ring = geom.GetGeometryRef(0)
        numpoints = ring.GetPointCount()
        pointsX = []; pointsY = []
        for p in range(numpoints):
            lon, lat, z = ring.GetPoint(p)
            pointsX.append(lon)
            pointsY.append(lat)
    else:
        logger.ERROR('ERROR: Geometry needs to be either Polygon or Multipolygon')

    xmin = min(pointsX)
    xmax = max(pointsX)
    ymin = min(pointsY)
    ymax = max(pointsY)
    
    # Specify offset and rows and columns to read
    xoff = int((xmin - xOrigin)/pixelWidth)
    yoff = int((yOrigin - ymax)/pixelWidth)
    xcount = int((xmax - xmin)/pixelWidth)+1
    ycount = int((ymax - ymin)/pixelWidth)+1
    
    # Create memory target raster
    target_ds = gdal.GetDriverByName('MEM').Create('', xcount, ycount, 1, gdal.GDT_Byte)
    target_ds.SetGeoTransform((
        xmin, pixelWidth, 0,
        ymax, 0, pixelHeight,
    ))

    # Create for target raster the same projection as for the value raster
    raster_srs = osr.SpatialReference()
    raster_srs.ImportFromWkt(raster.GetProjectionRef())
    target_ds.SetProjection(raster_srs.ExportToWkt())

    # Rasterize zone polygon to raster
    gdal.RasterizeLayer(target_ds, [1], lyr, burn_values=[1])

    # Read raster as arrays
    banddataraster = raster.GetRasterBand(1)
    dataraster = banddataraster.ReadAsArray(xoff, yoff, xcount, ycount).astype(numpy.float)

    bandmask = target_ds.GetRasterBand(1)
    datamask = bandmask.ReadAsArray(0, 0, xcount, ycount).astype(numpy.float)

    # Mask zone of raster
    zoneraster = numpy.ma.masked_array(dataraster,  numpy.logical_not(datamask))

    # Calculate statistics of zonal raster
    sDict = {}
    sDict['mean'] = numpy.mean(zoneraster)
    sDict['median'] = numpy.ma.median(zoneraster)
    sDict['std'] = numpy.std(zoneraster)
    sDict['var'] = numpy.var(zoneraster)
    sDict['max'] = numpy.max(zoneraster)
    sDict['min'] = numpy.min(zoneraster)

    return sDict


def loop_zonal_stats(input_zone_polygon, input_value_raster):

    shp = ogr.Open(input_zone_polygon)
    lyr = shp.GetLayer()
    featList = range(lyr.GetFeatureCount())
    statDict = {}

    for i in range(lyr.GetFeatureCount()):
        feature = lyr.GetFeature(i)
        f = feature.ExportToJson()
        pprint.pprint(json.loads(f)['properties'])
        meanValue = zonal_stats_by_feat(feature, input_zone_polygon, input_value_raster)
        statDict[i] = meanValue
        pprint.pprint(statDict[i])
        print('-'*30)
    
    return statDict

def run(shape, raster):
    return loop_zonal_stats(shape, raster)


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
        run(shape, raster)

