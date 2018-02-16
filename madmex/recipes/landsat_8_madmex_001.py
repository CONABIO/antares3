import os
import datacube
from datacube.storage.storage import write_dataset_to_netcdf
from datacube.storage import masking
import xarray as xr
import numpy as np
import dask

from datetime import datetime

from madmex.util import randomword
import logging
logger = logging.getLogger(__name__)

dask.set_options(get=dask.get)

def run(tile, gwf, center_dt):
    """Basic datapreparation recipe 001

    Combines temporal statistics of surface reflectance and ndvi with terrain
    metrics

    Args:
        tile (tuple): Tuple of (tile indices, Tile object). Tile object can be
            loaded as xarray.Dataset using gwf.load()
        gwf (GridWorkflow): GridWorkflow object instantiated with the corresponding
            product
        center_dt (datetime): Date to be used in making the filename

    Return:
        str: The filename of the netcdf file created
    """
    try:
        dc = datacube.Datacube(app = 'landsat_madmex_001_%s' % randomword(5))
        center_dt = center_dt.strftime("%Y-%m-%d")
        # TODO: Need a more dynamic way to handle this filename (e.g.: global variable for the path up to datacube_ingest)
        nc_filename = os.path.expanduser('~/datacube_ingest/recipes/landsat_8_madmex_001/madmex_001_%d_%d_%s.nc' % (tile[0][0], tile[0][1], center_dt))
        # Load Landsat sr
        if os.path.isfile(nc_filename):
            raise ValueError('%s already exist' % nc_filename)
        sr = gwf.load(tile[1], dask_chunks={'x': 1667, 'y': 1667})
        # Load terrain metrics using same spatial parameters than sr
        terrain = dc.load(product='srtm_cgiar_mexico', like=sr,
                          time=(datetime(1970, 1, 1), datetime(2018, 1, 1)),
                          dask_chunks={'x': 1667, 'y': 1667})
        # Compute ndvi
        sr['ndvi'] = (sr.nir - sr.red) / (sr.nir + sr.red)
        # Mask clouds, shadow, water, ice,... and drop qa layer
        invalid = masking.make_mask(sr.pixel_qa, cloud=True, cloud_shadow=True,
                                    snow=True, fill=True)
        sr_clear = sr.where(~invalid)
        sr_clear2 = sr_clear.drop('pixel_qa')
        # Run temporal reductions and rename DataArrays
        sr_mean = sr_clear2.mean('time', keep_attrs=True, skipna=True).astype('int16')
        sr_mean.rename({'blue': 'blue_mean',
                        'green': 'green_mean',
                        'red': 'red_mean',
                        'nir': 'nir_mean',
                        'swir1': 'swir1_mean',
                        'swir2': 'swir2_mean',
                        'ndvi': 'ndvi_mean'}, inplace=True)
        sr_min = sr_clear2.min('time', keep_attrs=True, skipna=True).astype('int16')
        sr_min.rename({'blue': 'blue_min',
                        'green': 'green_min',
                        'red': 'red_min',
                        'nir': 'nir_min',
                        'swir1': 'swir1_min',
                        'swir2': 'swir2_min',
                        'ndvi': 'ndvi_min'}, inplace=True)
        sr_max = sr_clear2.max('time', keep_attrs=True, skipna=True).astype('int16')
        sr_max.rename({'blue': 'blue_max',
                        'green': 'green_max',
                        'red': 'red_max',
                        'nir': 'nir_max',
                        'swir1': 'swir1_max',
                        'swir2': 'swir2_max',
                        'ndvi': 'ndvi_max'}, inplace=True)
        sr_std = sr_clear2.std('time', keep_attrs=True, skipna=True).astype('int16')
        sr_std.rename({'blue': 'blue_std',
                        'green': 'green_std',
                        'red': 'red_std',
                        'nir': 'nir_std',
                        'swir1': 'swir1_std',
                        'swir2': 'swir2_std',
                        'ndvi': 'ndvi_std'}, inplace=True)
        # Merge dataarrays
        combined = xr.merge([sr_mean, sr_min, sr_max, sr_std, terrain])
        combined.attrs['crs'] = sr.attrs['crs']
        write_dataset_to_netcdf(combined, nc_filename)
        return nc_filename
    except Exception as e:
        logger.info('Tile (%d, %d) not processed. %s' % (tile[0][0], tile[0][1], e))
        return None


