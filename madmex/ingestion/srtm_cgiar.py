from glob import glob
import os
import uuid

import rasterio
from pyproj import Proj
from jinja2 import Environment, PackageLoader

from madmex.util import s3

def metadata_convert(path, bucket=None):
    """Prepare metadata prior to datacube indexing

    Given a directory containing srtm derived terrain metrics (elevation, aspect, slope)
    prepares a metadata string with the appropriate formating for indexing in the datacube

    Args:
        path (str): Path of the directory containing the 3 terrain metrics calculated from srtm.
        bucket (str or None): Name of the s3 bucket containing the data. If ``None``
            (default), data are considered to be on a mounted filesystem

    Examples:
        >>> from madmex.ingestion.srtm_cgiar import metadata_convert
        >>> path = '/path/to/srtm/dir'
        >>> yaml_str = metadata_convert(path)

        >>> with open('/path/to/metadata_out.yaml', 'w') as dst:
        >>>     dst.write(yaml_str)

    Returns:
        str: The content of the metadata for later writing to file.
    """
    if bucket is not None:
        file_list = s3.list_files(bucket, path,
                                  r'.*(srtm_mosaic|slope_mosaic|aspect_mosaic)\.tif$')
        if len(file_list) == 3:
            check_exist = [True]
        else:
            check_exist = [False]
        path = s3.build_rasterio_path(bucket, path)
    elevation = os.path.join(path, 'srtm_mosaic.tif')
    slope = os.path.join(path, 'slope_mosaic.tif')
    aspect = os.path.join(path, 'aspect_mosaic.tif')
    # Check that these files exist
    if bucket is None:
        check_exist = [os.path.isfile(x) for x in [elevation, slope, aspect]]
    if not all(check_exist):
        raise ValueError('Target directory must at least contain the 3 following files (srtm_mosaic.tif, slope_mosaic.tif, aspect_mosaic.tif)')
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
        'elevation': elevation,
        'slope': slope,
        'aspect': aspect,
    }
    # Load template
    env = Environment(loader=PackageLoader('madmex', 'templates'))
    template = env.get_template('srtm_cgiar.yaml')
    out = template.render(**meta_out)
    return out
