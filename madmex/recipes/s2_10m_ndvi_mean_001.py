import os
import datacube
from datacube.storage.storage import write_dataset_to_netcdf
from datacube.api import GridWorkflow
import xarray as xr
import numpy as np
import dask
import gc
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
        crs = tile[1][0].geobox.crs
        center_dt = center_dt.strftime("%Y-%m-%d")
        nc_filename = os.path.join(path, 's2_10m_ndvi_mean_001_%d_%d_%s.nc' % (tile[0][0], tile[0][1], center_dt))
        # Load Landsat sr
        if os.path.isfile(nc_filename):
            logger.warning('%s already exists. Returning filename for database indexing', nc_filename)
            return nc_filename
        sr_0 = xr.merge([GridWorkflow.load(x, dask_chunks={'x': 2000, 'y': 2000, 'time': 35},
					   measurements=['red','nir']) for x in tile[1]])
        sr_0.attrs['geobox'] = tile[1][0].geobox
        sr_0 = sr_0.apply(func=to_float, keep_attrs=True)
	#datacube
	dc = datacube.Datacube(app = 's2_10m_001_%s' % randomword(5))
        # Keep clear pixels (2: Dark features, 4: Vegetation, 5: Not vegetated,
        # 6: Water, 7: Unclassified, 8: Cloud medium probability, 11: Snow/Ice)
        s2_20m_scl = dc.load(product='s2_l2a_20m_mexico', 
			     like = sr_0,
			     measurements = ['pixel_qa'],
			    dask_chunks = {'x': 2000, 'y': 2000, 'time':35})
        sr_1 = sr_0.where(s2_20m_scl.pixel_qa.isin([2,4,5,6,7,8,11]))
        # Compute ndvi
        sr_1['ndvi'] = ((sr_1.nir - sr_1.red) / (sr_1.nir + sr_1.red)) * 10000
        sr_1['ndvi'].attrs['nodata'] = 0
        # Run temporal reductions and rename DataArrays
        sr_mean = sr_1.mean('time', keep_attrs=True, skipna=True)
        sr_mean.rename({'ndvi': 'ndvi_mean'}, inplace=True)
        sr_mean = sr_mean.apply(to_int)
        sr_mean.attrs['crs'] = crs
        sr_mean = sr_mean.compute()
        write_dataset_to_netcdf(sr_mean, nc_filename)
        # Explicitely deallocate objects and run garbage collector
        sr_0=sr_1=sr_mean=s2_20m_scl=None
        gc.collect()
        return nc_filename
    except Exception as e:
        logger.warning('Tile (%d, %d) not processed. %s' % (tile[0][0], tile[0][1], e))
        return None
