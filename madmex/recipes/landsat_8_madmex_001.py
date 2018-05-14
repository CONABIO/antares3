import os
import datacube
from datacube.storage.storage import write_dataset_to_netcdf
from datacube.storage import masking
from datacube.api import GridWorkflow
import xarray as xr
import numpy as np
import dask

from madmex.util.xarray import to_float, to_int

from datetime import datetime

from madmex.util import randomword
import logging
logger = logging.getLogger(__name__)

dask.set_options(get=dask.get)

def run(tile, center_dt, path):
    """Basic datapreparation recipe 001

    Combines temporal statistics of surface reflectance and ndvi with terrain
    metrics

    Args:
        tile (tuple): Tuple of (tile indices, Tile object). Tile object can be
            loaded as xarray.Dataset using gwf.load()
        center_dt (datetime): Date to be used in making the filename
        path (str): Directory where files generated are to be written

    Return:
        str: The filename of the netcdf file created
    """
    try:
        center_dt = center_dt.strftime("%Y-%m-%d")
        nc_filename = os.path.join(path, 'madmex_001_%d_%d_%s.nc' % (tile[0][0], tile[0][1], center_dt))
        # Load Landsat sr
        if os.path.isfile(nc_filename):
            raise ValueError('%s already exist' % nc_filename)
        sr_0 = GridWorkflow.load(tile[1], dask_chunks={'x': 1667, 'y': 1667})
        # Load terrain metrics using same spatial parameters than sr
        dc = datacube.Datacube(app = 'landsat_madmex_001_%s' % randomword(5))
        terrain = dc.load(product='srtm_cgiar_mexico', like=sr_0,
                          time=(datetime(1970, 1, 1), datetime(2018, 1, 1)),
                          dask_chunks={'x': 1667, 'y': 1667})
        dc.close()
        # Mask clouds, shadow, water, ice,... and drop qa layer
        clear = masking.make_mask(sr_0.pixel_qa, cloud=False, cloud_shadow=False,
                                    snow=False)
        sr_1 = sr_0.where(clear)
        sr_2 = sr_1.drop('pixel_qa')
        # Convert Landsat data to float (nodata values are converted to np.Nan)
        sr_3 = sr_2.apply(func=to_float, keep_attrs=True)
        # Compute ndvi
        sr_3['ndvi'] = ((sr_3.nir - sr_3.red) / (sr_3.nir + sr_3.red)) * 10000
        sr_3['ndvi'].attrs['nodata'] = -9999
        # Run temporal reductions and rename DataArrays
        sr_mean = sr_3.mean('time', keep_attrs=True, skipna=True)
        sr_mean.rename({'blue': 'blue_mean',
                        'green': 'green_mean',
                        'red': 'red_mean',
                        'nir': 'nir_mean',
                        'swir1': 'swir1_mean',
                        'swir2': 'swir2_mean',
                        'ndvi': 'ndvi_mean'}, inplace=True)
        sr_min = sr_3.min('time', keep_attrs=True, skipna=True)
        sr_min.rename({'blue': 'blue_min',
                        'green': 'green_min',
                        'red': 'red_min',
                        'nir': 'nir_min',
                        'swir1': 'swir1_min',
                        'swir2': 'swir2_min',
                        'ndvi': 'ndvi_min'}, inplace=True)
        sr_max = sr_3.max('time', keep_attrs=True, skipna=True)
        sr_max.rename({'blue': 'blue_max',
                        'green': 'green_max',
                        'red': 'red_max',
                        'nir': 'nir_max',
                        'swir1': 'swir1_max',
                        'swir2': 'swir2_max',
                        'ndvi': 'ndvi_max'}, inplace=True)
        sr_std = sr_3.std('time', keep_attrs=True, skipna=True)
        sr_std.rename({'blue': 'blue_std',
                        'green': 'green_std',
                        'red': 'red_std',
                        'nir': 'nir_std',
                        'swir1': 'swir1_std',
                        'swir2': 'swir2_std',
                        'ndvi': 'ndvi_std'}, inplace=True)
        # Merge dataarrays
        combined = xr.merge([sr_mean.apply(to_int),
                             sr_min.apply(to_int),
                             sr_max.apply(to_int),
                             sr_std.apply(to_int), terrain])
        combined.attrs['crs'] = sr_0.attrs['crs']
        write_dataset_to_netcdf(combined, nc_filename)
        return nc_filename
    except Exception as e:
        logger.warning('Tile (%d, %d) not processed. %s' % (tile[0][0], tile[0][1], e))
        return None


