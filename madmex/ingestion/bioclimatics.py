from glob import glob
import os
import uuid

import rasterio
from pyproj import Proj
from jinja2 import Environment, PackageLoader

def metadata_convert(path):
    """Prepare metadata prior to datacube indexing

    Given a directory containing bioclimatics raster information prepares  
    a metadata string with the appropriate formating for indexing in the datacube

    Args:
        path (str): Path of the directory containing temperature and precipitation measurements.

    Examples:
        >>> from madmex.ingestion.bioclimatics import metadata_convert
        >>> path = '/path/to/bioclim/dir'
        >>> yaml_str = metadata_convert(path)

        >>> with open('/path/to/metadata_out.yaml', 'w') as dst:
        >>>     dst.write(yaml_str)

    Returns:
        str: The content of the metadata for later writing to file.
    """
    tmax = os.path.join(path, 'tmax.tif')
    tmean = os.path.join(path, 'tmean.tif')
    tmin = os.path.join(path, 'tmin.tif')
    # Check that these files exist
    check_exist = [os.path.isfile(x) for x in [tmax, tmean, tmin]]
    if not all(check_exist):
        raise ValueError('Target directory must at least contain the 3 following files (tmax.tif, tmean.tif, tmin.tif)')
    with rasterio.open(elevation) as src:
        crs = src.crs
        bounds = src.bounds
    meta_out = {
        'id': uuid.uuid5(uuid.NAMESPACE_URL, path),
        'll_lat': bounds.bottom,
        'lr_lat': bounds.bottom,
        'ul_lat': bounds.top,
        'ur_lat': bounds.top,
        'll_lon': bounds.left,
        'lr_lon': bounds.right,
        'ul_lon': bounds.left,
        'ur_lon': bounds.right,
        'crs': crs.wkt,
        'tmax': tmax,
        'tmean': tmean,
        'tmin': tmin,
    }
    # Load template
    env = Environment(loader=PackageLoader('madmex', 'templates'))
    template = env.get_template('bioclimatics.yaml')
    out = template.render(**meta_out)
    return out
