import os
import datacube
from datacube.storage.storage import write_dataset_to_netcdf
from datacube.storage import masking
import xarray as xr
import numpy as np

from datetime import datetime

def run(tile, gwf, center_dt, dc):
    """Basic datapreparation recipe 001

    Combines temporal statistics of surface reflectance and ndvi with terrain
    metrics

    Args:
        tile (tuple): Tuple of (tile indices, Tile object). Tile object can be
            loaded as xarray.Dataset using gwf.load()
        gwf (GridWorkflow): GridWorkflow object instantiated with the corresponding
            product
        center_dt (datetime): Date to be used in making the filename
        dc (datacube.Datacube): Datacube object, useful for recipes that perform merging
            of several products

    Return:
        str: The filename of the netcdf file created
    """
    try:
        center_dt = center_dt.strftime("%Y-%m-%d")
        # TODO: Need a more dynamic way to handle this filename (e.g.: global variable for the path up to datacube_ingest)
        nc_filename = os.path.expanduser('~/datacube_ingest/recipes/madmex_001/madmex_001_%d_%d_%s.nc' % (tile[0][0], tile[0][1], center_dt))
        # TODO: Is it a good idea to check if file already exist and skip processing if it does?
        # Load Landsat sr
        sr = gwf.load(tile[1])
        # Compute ndvi
        sr['ndvi'] = (sr.nir - sr.red) / (sr.nir + sr.red)
        # Load terrain metrics using same spatial parameters than sr
        terrain = dc.load(product='srtm_cgiar_mexico', like=sr,
                          time=(datetime(1970, 1, 1), datetime(2018, 1, 1)))
        # Mask clouds, shadow, water, ice,... and drop qa layer
        # TODO: Don't we want to keep water?
        clear = masking.make_mask(sr.pixel_qa, clear=True)
        sr_clear = sr.where(clear)
        sr_clear2 = sr_clear.drop('pixel_qa')
        # Run temporal reductions and rename DataArrays
        sr_mean = sr_clear2.mean('time', keep_attrs=True, dtype=np.int16)
        sr_mean.rename({'blue': 'blue_mean',
                        'green': 'green_mean',
                        'red': 'red_mean',
                        'nir': 'nir_mean',
                        'swir1': 'swir1_mean',
                        'swir2': 'swir2_mean',
                        'ndvi': 'ndvi_mean'}, inplace=True)
        sr_min = sr_clear2.min('time', keep_attrs=True, dtype=np.int16)
        sr_min.rename({'blue': 'blue_min',
                        'green': 'green_min',
                        'red': 'red_min',
                        'nir': 'nir_min',
                        'swir1': 'swir1_min',
                        'swir2': 'swir2_min',
                        'ndvi': 'ndvi_min'}, inplace=True)
        sr_max = sr_clear2.max('time', keep_attrs=True, dtype=np.int16)
        sr_max.rename({'blue': 'blue_max',
                        'green': 'green_max',
                        'red': 'red_max',
                        'nir': 'nir_max',
                        'swir1': 'swir1_max',
                        'swir2': 'swir2_max',
                        'ndvi': 'ndvi_max'}, inplace=True)
        sr_std = sr_clear2.std('time', keep_attrs=True, dtype=np.int16)
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
        print(e)
        return None


