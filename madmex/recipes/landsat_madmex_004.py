import os
import gc
import datacube
import xarray as xr
import numpy as np
import logging

from datacube.drivers.netcdf import write_dataset_to_netcdf
from datacube.storage import masking
from datacube.api import GridWorkflow

from madmex.util.xarray import to_float, to_int
from datetime import datetime
from madmex.util import randomword

logger = logging.getLogger(__name__)


def run(tile, center_dt, path, histogram_match=False):
    """Basic data preparation recipe 004

    Combines temporal statistics of surface reflectance and ndvi with terrain
    metrics. Optional perform histogram matching with recipe product of reference

    Args:
        tile (tuple or list of tuples): Tuple of (tile indices, Tile object). Tile object can be
            loaded as xarray.Dataset using gwf.load(). If histogram_match is True then must be a list of tuples wich in first position has a source Tile and in second position has a reference Tile
        center_dt (datetime): Date to be used in making the filename
        path (str): Directory where files generated are to be written
        histogram_match (bool): Wether to perform histogram match
    Return:
        str: The filename of the netcdf file created
    """
    try:

        if histogram_match:
            tile_reference = tile[1]
            tile = tile[0]
        # Get crs from first tile of tile list
        crs = tile[1][0].geobox.crs
        center_dt = center_dt.strftime("%Y-%m-%d")
        nc_filename = os.path.join(path, 'madmex_004_%d_%d_%s.nc' % (tile[0][0], tile[0][1], center_dt))
        # Load Landsat sr
        if os.path.isfile(nc_filename):
            logger.warning('%s already exists. Returning filename for database indexing', nc_filename)
            return nc_filename
        sr_0 = xr.auto_combine([GridWorkflow.load(x, dask_chunks={'x': 1200, 'y': 1200})
                         for x in tile[1]], concat_dim='time')
        sr_0.attrs['geobox'] = tile[1][0].geobox
        sr_0.attrs['crs'] = crs
        # Mask clouds, shadow, water, ice,... and drop qa layer
        clear = masking.make_mask(sr_0.pixel_qa, cloud=False, cloud_shadow=False,
                                  snow=False)
        sr_1 = sr_0.where(clear)
        sr_1 = sr_1.drop('pixel_qa')
        sr_1 = sr_1.apply(func=to_float, keep_attrs=True)
        # Check wheter or not to perform histogram matching:
        if tile_reference:
            def histogram_matching(source2D, r_values, r_quantiles):
                orig_shape = source2D.shape
                s_values, s_idx, s_counts = np.unique(source2D, return_inverse=True, return_counts=True)
                s_quantiles = np.cumsum(s_counts).astype(np.float64) / source2D.size
                interp_r_values = np.interp(s_quantiles, r_quantiles, r_values)
                target = interp_r_values[s_idx].reshape(orig_shape)
                return target
            def wrapper_histogram_match(source2D, reference2D, band, n_times):
                s_band = source2D[band]
                r_values, r_counts = np.unique(reference2D, return_counts=True)
                r_quantiles = np.cumsum(r_counts).astype(np.float64) / reference2D.size
                target_DA = xr.concat([xr.DataArray(histogram_matching(s_band.isel(time=k).values,
                                                                                   r_values,
                                                                                   r_quantiles),
                                                    dims=['y','x'],
                                                    coords= {'y': s_band.coords['y'],
                                                             'x': s_band.coords['x'],
                                                             'time': s_band.coords['time'][k]},
                                                    attrs=s_band.attrs) for k in range(0,n_times)],dim='time')
                return target_DA

            sr_reference = xr.auto_combine([GridWorkflow.load(x,
                                                             dask_chunks={'x': 1200, 'y': 1200},
                                                             measurements=['blue_mean',
                                                                           'green_mean',
                                                                           'red_mean',
                                                                           'nir_mean',
                                                                           'swir1_mean',
                                                                           'swir2_mean']) for x in tile_reference[1]],
                                                             concat_dim='time')
            xr_ds = xr.Dataset({}, attrs = sr_1.attrs)
            band_list_source = list(sr_1.data_vars)
            for k in range(0, len(band_list_source)):
                band = band_list_source[k]
                xr_ds[band] = wrapper_histogram_match(sr_1,
                                                      sr_reference[band + '_mean'].values,
                                                      band,
                                                      sr_1.dims['time'])
            sr_1.update(xr_ds.chunk({'x': 1200, 'y': 1200}))
            xr_ds = None
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
        dc = datacube.Datacube(app = 'landsat_madmex_002_%s' % randomword(5))
        terrain = dc.load(product='srtm_cgiar_mexico', like=sr_0,
                          time=(datetime(1970, 1, 1), datetime(2018, 1, 1)),
                          dask_chunks={'x': 1200, 'y': 1200})
        dc.close()
        # Merge dataarrays
        combined = xr.merge([sr_mean.apply(to_int),
                             to_int(ndvi_max),
                             to_int(ndvi_min),
                             to_int(ndmi_max),
                             to_int(ndmi_min),
                             terrain])
        combined.attrs['crs'] = crs
        combined = combined.compute(scheduler='threads')
        write_dataset_to_netcdf(combined, nc_filename)
        # Explicitely deallocate objects and run garbage collector
        sr_0=sr_1=sr_mean=clear=ndvi_max=ndvi_min=ndmi_max=ndmi_min=terrain=combined=None
        gc.collect()
        return nc_filename
    except Exception as e:
        logger.warning('Tile (%d, %d) not processed. %s' % (tile[0][0], tile[0][1], e))
        return None
