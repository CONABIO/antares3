import os
import datacube
from datacube.storage.storage import write_dataset_to_netcdf
from datacube.storage import masking
import xarray as xr
import numpy as np

from datetime import datetime

def run(tile, gwf, center_dt):
    """Basic datapreparation recipe 001

    Computes mean NDVI for a landsat collection over a given time frame

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
        center_dt = center_dt.strftime("%Y-%m-%d")
        # TODO: Need a more dynamic way to handle this filename (e.g.: global variable for the path up to datacube_ingest)
        nc_filename = os.path.expanduser('~/datacube_ingest/recipes/ndvi_mean/ndvi_mean_%d_%d_%s.nc' % (tile[0][0], tile[0][1], center_dt))
        # TODO: Is it a good idea to check if file already exist and skip processing if it does?
        # Load Landsat sr
        sr = gwf.load(tile[1], dask_chunks={'x': 1667, 'y': 1667})
        # Compute ndvi
        sr['ndvi'] = (sr.nir - sr.red) / (sr.nir + sr.red) * 10000
        ndvi = sr.drop(['pixel_qa', 'blue', 'red', 'green', 'nir', 'swir1', 'swir2'])
        # Run temporal reductions and rename DataArrays
        ndvi_mean = ndvi.mean('time', keep_attrs=True).astype('int16')
        ndvi_mean.attrs['crs'] = sr.attrs['crs']
        write_dataset_to_netcdf(ndvi_mean, nc_filename)
        return nc_filename
    except Exception as e:
        print(e)
        return None


