from glob import glob
from datetime import datetime

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
        file_list = [os.path.basename(x) for x in
                     s3.list_files(bucket, path, r'.*filtered\.tif$')]
        path = s3.build_rasterio_path(bucket, path)
    else:
        file_list = [os.path.basename(x) for x in
                     glob(os.path.join(path, '*filtered.tif'))]
    pol_vh = [x for x in file_list if '_VH_' in x][0]
    pol_vv = [x for x in file_list if '_VV_' in x][0]
    pol_vh = os.path.join(path, pol_vh)
    pol_vv = os.path.join(path, pol_vv)

    fname = os.path.basename(pol_vh).split("_")[0]
    if 'T' in fname:
        date_str = fname.replace('T','')
    else:
        date_str = fname
    dt = datetime.strptime(date_str,'%Y%m%d%H%M%S')
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
       'dt': dt.strftime('%Y-%m-%dT%H:%M:%S'), # 2018-01-22T17:56:29
       'crs': crs.wkt,
       'pol_vh': pol_vh,
       'pol_vv': pol_vv,
    }
    # Load template
    env = Environment(loader=PackageLoader('madmex', 'templates'))
    template = env.get_template('s1_grd_vh_vv.yaml')
    out = template.render(**meta_out)
    return out
