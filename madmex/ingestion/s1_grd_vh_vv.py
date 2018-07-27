from glob import glob
import os
import uuid

import rasterio
from pyproj import Proj
from jinja2 import Environment, PackageLoader

from madmex.util import s3


def metadata_convert(path, bucket=None):
    """Prepare metadata prior to datacube indexing

    Given a directory containing ...

    Args:
        path (str): Path of the directory containing ... 
        bucket (str or None): Name of the s3 bucket containing the data. If ``None``
            (default), data are considered to be on a mounted filesystem

    Examples:

    Returns:
        str: The content of the metadata for later writing to file.
    """
    if bucket is not None:
        path = s3.build_rasterio_path(bucket, path)
    pol_vh = os.path.join(path, 'corrected_VH_filtered.tif')
    pol_vv = os.path.join(path, 'corrected_VH_filtered.tif')
    # Check that these files exist
    with rasterio.open(pol_vh) as src:
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
        'pol_vh': pol_vh,
        'pol_vv': pol_vv,
    }
    # Load template
    env = Environment(loader=PackageLoader('madmex', 'templates'))
    template = env.get_template('s1_grd_vh_vv.yaml')
    out = template.render(**meta_out)
    return out
