import os
import datacube
from datacube.drivers.netcdf import write_dataset_to_netcdf
from datacube.api import GridWorkflow
import xarray as xr
import numpy as np

import gc
from madmex.util.xarray import to_float, to_int

from datetime import datetime

from madmex.util import randomword
import logging
logger = logging.getLogger(__name__)


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
        nc_filename = os.path.join(path, 's2_10m_scl_crops_%d_%d_%s.nc' % (tile[0][0], tile[0][1], center_dt))
        # Load Landsat sr
        if os.path.isfile(nc_filename):
            logger.warning('%s already exists. Returning filename for database indexing', nc_filename)
            return nc_filename
        sr_0 = xr.merge([GridWorkflow.load(x, dask_chunks={'x': 600, 'y': 600}) for x in tile[1]])
        sr_0.attrs['geobox'] = tile[1][0].geobox
        sr_0 = sr_0.apply(func=to_float, keep_attrs=True)
        # Keep clear pixels (2: Dark features, 4: Vegetation, 5: Not vegetated,
        # 6: Water, 7: Unclassified, 8: Cloud medium probability, 11: Snow/Ice)
        sr_1 = sr_0.where(sr_0.pixel_qa.isin([2,4,5,6,7,8,11]))
        #drop pixel_qa
        sr_1 = sr_1.drop(['pixel_qa'])
        # Compute ndvi
        sr_1['ndvi'] = ((sr_1.nir - sr_1.red) / (sr_1.nir + sr_1.red)) * 10000
        sr_1['ndvi'].attrs['nodata'] = 0
        # Run temporal reductions and rename DataArrays
        sr_mean = sr_1.mean('time', keep_attrs=True, skipna=True)
        sr_mean = sr_mean.rename({'red': 'red_mean',
                        'green': 'green_mean',
                        'blue': 'blue_mean',
                        'nir': 'nir_mean',
                        'ndvi': 'ndvi_mean'})

        # Compute min/max/std only for vegetation indices
        ndvi_max = sr_1.ndvi.max('time', keep_attrs=True, skipna=True)
        ndvi_max = ndvi_max.rename('ndvi_max')
        ndvi_max.attrs['nodata'] = 0
        ndvi_min = sr_1.ndvi.min('time', keep_attrs=True, skipna=True)
        ndvi_min = ndvi_min.rename('ndvi_min')
        ndvi_min.attrs['nodata'] = 0
        indexes = sr_1['ndvi'].argmax(axis=0).compute()
        begin_date = str(sr_1['ndvi']['time'][0].values).split('-')[0] + '-01-01'
        begin = datetime.strptime(begin_date, '%Y-%m-%d').timestamp()*1e-4 - 100
        ndvi_argmax = xr.DataArray(sr_1['ndvi']['time'][indexes].values.astype(datetime)*1e-13 - begin, 
                                   coords=ndvi_max.coords, dims=ndvi_max.dims)
        ndvi_argmax = ndvi_argmax.rename('ndvi_argmax')
        ndvi_argmax.attrs['nodata'] = 0

        combined = xr.merge([sr_mean.apply(to_int),
                             to_int(ndvi_max),
                             to_int(ndvi_min),
                             to_int(ndvi_argmax)])
        combined.attrs['crs'] = crs

        combined = combined.compute(scheduler='threads')
        write_dataset_to_netcdf(combined, nc_filename)
        # Explicitely deallocate objects and run garbage collector
        sr_0=sr_1=sr_mean=ndvi_max=ndvi_min=indexes=ndvi_argmax=combined=None
        gc.collect()
        return nc_filename
    except Exception as e:
        logger.warning('Tile (%d, %d) not processed. %s' % (tile[0][0], tile[0][1], e))
        return None
