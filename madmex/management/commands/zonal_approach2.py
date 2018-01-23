'''
Created on Jan 16, 2018

@author: rmartinez
'''

import logging
import xarray
import rasterio
import fiona
import os
import ogr
import osr

from madmex.management.base import AntaresBaseCommand


logger = logging.getLogger(__name__)


def wkt_to_vector(wkt, shp_file):
    '''
    This code converts wkt data format to shapefile format.
    '''

    string = str(wkt.the_geom)
    srid = string.split(';')[0]
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(int(srid.split('=')[1]))
    wkt_poly = string.split(';')[1]

    poly_geometry = ogr.CreateGeometryFromWkt(wkt_poly)
    driver = ogr.GetDriverByName('ESRI Shapefile')
    layer_name = 'shapefile_layer'

    if os.path.exists(shp_file):
        driver.DeleteDataSource(shp_file)

    shp_datasource = driver.CreateDataSource(shp_file)
    shp_layer = shp_datasource.CreateLayer(layer_name, srs, ogr.wkbPolygon)
    feature = ogr.Feature(shp_layer.GetLayerDefn())
    feature.SetGeometry(poly_geometry)
    shp_layer.CreateFeature(feature)

def xarray_to_rasterio(xa, output_filename):
    '''
    Converts the given xarray.DataArray object to a raster output file
    using rasterio.
    Arguments:
     - `xa`: The xarray.DataArray to convert
     - `output_filename`: the filename to store the output GeoTIFF file in
    
    Notes:
    Converts the given xarray.DataArray to a GeoTIFF output file using rasterio.
    This function only supports 2D or 3D DataArrays, and GeoTIFF output.
    The input DataArray must have attributes (stored as xa.attrs) specifying
    geographic metadata, or the output will have _no_ geographic information.
    If the DataArray uses dask as the storage backend then this function will
    force a load of the raw data.
    '''
    # Forcibly compute the data, to ensure that all of the metadata is
    # the same as the actual data (ie. dtypes are the same etc)
    
    xa = xa.load()

    if len(xa.shape) == 2:
        count = 1
        height = xa.shape[0]
        width = xa.shape[1]
        band_indicies = 1
    else:
        count = xa.shape[0]
        height = xa.shape[1]
        width = xa.shape[2]
        band_indicies = np.arange(count) + 1

    processed_attrs = {}

    try:
        val = xa.attrs['affine']
        processed_attrs['affine'] = rasterio.Affine.from_gdal(*val)
    except KeyError:
        pass

    try:
        val = xa.attrs['crs']
        processed_attrs['crs'] = rasterio.crs.CRS.from_string(val)
    except KeyError:
        pass

    with rasterio.open(output_filename, 'w',
                       driver='GTiff',
                       height=height, width=width,
                       dtype=str(xa.dtype), count=count,
                       **processed_attrs) as dst:
        dst.write(xa.values, band_indicies)



class Command(AntaresBaseCommand):
    help = '''
            Compute zonal statistics ...



           '''
    def add_arguments(self, parser):
        '''
        '''
        parser.add_argument('--xarray', nargs=1, help='An xarray.DataArray object')
        parser.add_argument('--geom', nargs=1, help='Object with geometry attribute fron DB')
        
        
    def handle(self, **options):
        '''
        
        '''
        xarr = options['xarray'][0]
        geom  = options['geom'][0]

        shape_file = 'shapefile.shp'
        raster_file = 'raster.tif'

        wkt_to_vector(geom, shape_file)
        xarray_to_rasterio(xarr, raster_file)
        

                
