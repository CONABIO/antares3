import os
import gc
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
        nc_filename = os.path.join(path, 'landsat_belize_001_%d_%d_%s.nc' % (tile[0][0], tile[0][1], center_dt))
        # Load Landsat sr
        if os.path.isfile(nc_filename):
            logger.warning('%s already exists. Returning filename for database indexing', nc_filename)
            return nc_filename
        # Get crs from first tile of tile list
        #crs = tile[1][0].geobox.crs
        sr_0 = xr.merge([GridWorkflow.load(x, dask_chunks={'latitude': 1860, 'longitude': 1860, 'time': 1})
                         for x in tile[1]])
        sr_0.attrs['geobox'] = tile[1][0].geobox
        # Mask clouds, shadow, water, ice,... and drop qa layer
        clear = masking.make_mask(sr_0.pixel_qa, cloud=False, cloud_shadow=False,
                                  snow=False)
        sr_1 = sr_0.where(clear)
        sr_1 = sr_1.drop('pixel_qa')
        sr_1 = sr_1.apply(func=to_float, keep_attrs=True)
        # Compute vegetation indices
        sr_1['ndvi'] = ((sr_1.nir - sr_1.red) / (sr_1.nir + sr_1.red)) * 10000
        sr_1['ndvi'].attrs['nodata'] = -9999
        sr_1['ndmi'] = ((sr_1.nir - sr_1.swir1) / (sr_1.nir + sr_1.swir1)) * 10000
        sr_1['ndmi'].attrs['nodata'] = -9999
        # Run temporal reductions and rename DataArrays
        sr_mean = sr_1.mean('time', keep_attrs=True, skipna=True)
        sr_mean.rename({'blue': 'blue_mean',
                        'green': 'green_mean',
                        'red': 'red_mean',
                        'nir': 'nir_mean',
                        'swir1': 'swir1_mean',
                        'swir2': 'swir2_mean',
                        'ndmi': 'ndmi_mean',
                        'ndvi': 'ndvi_mean'}, inplace=True)
        # Compute min/max/std only for vegetation indices
        ndvi_max = sr_1.ndvi.max('time', keep_attrs=True, skipna=True)
        ndvi_max = ndvi_max.rename('ndvi_max')
        ndvi_max.attrs['nodata'] = -9999
        ndvi_min = sr_1.ndvi.min('time', keep_attrs=True, skipna=True)
        ndvi_min = ndvi_min.rename('ndvi_min')
        ndvi_min.attrs['nodata'] = -9999
        # ndmi
        ndmi_max = sr_1.ndmi.max('time', keep_attrs=True, skipna=True)
        ndmi_max = ndmi_max.rename('ndmi_max')
        ndmi_max.attrs['nodata'] = -9999
        ndmi_min = sr_1.ndmi.min('time', keep_attrs=True, skipna=True)
        ndmi_min = ndmi_min.rename('ndmi_min')
        ndmi_min.attrs['nodata'] = -9999
        # Load terrain metrics using same spatial parameters than sr
        dc = datacube.Datacube(app = 'landsat_belize_%s' % randomword(5))
        terrain = dc.load(product='srtm_cgiar_belize', like=sr_0,
                          time=(datetime(1970, 1, 1), datetime(2018, 1, 1)),
                         dask_chunks={'latitude': 1860, 'longitude': 1860, 'time': 1})
        dc.close()
        # Merge dataarrays
        combined = xr.merge([sr_mean.apply(to_int),
                             to_int(ndvi_max),
                             to_int(ndvi_min),
                             to_int(ndmi_max),
                             to_int(ndmi_min),
                             terrain])
        combined.attrs['crs'] = crs
        combined = combined.compute()
        write_dataset_to_netcdf(combined, nc_filename)
        # Explicitely deallocate objects and run garbage collector
        sr_0=sr_1=sr_mean=clear=ndvi_max=ndvi_min=ndmi_max=ndmi_min=terrain=combined=None
        gc.collect()
        return nc_filename
    except Exception as e:
        logger.warning('Tile (%d, %d) not processed. %s' % (tile[0][0], tile[0][1], e))
        return None


