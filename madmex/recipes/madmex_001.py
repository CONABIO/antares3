import datacube
from datacube.storage.storage import write_dataset_to_netcdf
from datacube.storage import masking
import xarray as xr
import numpy as np

def run(x, y, time, dask_chunks, nc_filename):
    """Basic datapreparation recipe 001

    Combines temporal statistics of surface reflectance and ndvi with terrain
    metrics

    Args:
        x (tuple): Tuple of longitude limits passed to dc.load
        y (tuple): Tuple of latitude limits passed to dc.load
        time (tuple): Tuple of date limits passed to dc.load
        dask_chunks (dict): Dask chunking parameters, see dc.load documentation
            for more details
        nc_filename (str): Full path of the netcdf file to write results to
    """
    dc = datacube.Datacube(app = 'recipe_madmex_001')
    # Load Landsat sr
    sr = dc.load(product='ls8_espa_mexico', x=x, y=y, time=time,
                 group_by='solar_day', dask_chunks=dask_chunks)
    # Compute ndvi
    sr['ndvi'] = (sr.nir - sr.red) / (sr.nir + sr.red)
    # Load terrain metrics using same spatial parameters than sr
    terrain = dc.load(product='srtm_cgiar_mexico', like=sr, time=(datetime(1970, 1, 1), datetime(2018, 1, 1)),
                      dask_chunks=dask_chunks)
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


