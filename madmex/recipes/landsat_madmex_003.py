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
        # Get crs from first tile of tile list
        crs = tile[1][0].geobox.crs
        center_dt = center_dt.strftime("%Y-%m-%d")
        nc_filename = os.path.join(path, 'madmex_003_%d_%d_%s.nc' % (tile[0][0], tile[0][1], center_dt))

        print(crs)
        print(center_dt)
        print(nc_filename)

    except Exception as e:
        logger.warning('Tile (%d, %d) not processed. %s' % (tile[0][0], tile[0][1], e))
        return None
