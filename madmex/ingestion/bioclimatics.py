from glob import glob
import os
import uuid

import rasterio
from pyproj import Proj
from jinja2 import Environment, PackageLoader

from madmex.util import s3

def metadata_convert(path, bucket=None):
    """Prepare metadata prior to datacube indexing

    Given a directory containing bioclimatics raster information prepares
    a metadata string with the appropriate formating for indexing in the datacube

    Args:
        path (str): Path of the directory containing temperature and
            precipitation measurements.
        bucket (str or None): Name of the s3 bucket containing the data. If ``None``
            (default), data are considered to be on a mounted filesystem

    Examples:
        >>> from madmex.ingestion.bioclimatics import metadata_convert
        >>> path = '/path/to/bioclim/dir'
        >>> yaml_str = metadata_convert(path)

        >>> with open('/path/to/metadata_out.yaml', 'w') as dst:
        >>>     dst.write(yaml_str)

    Returns:
        str: The content of the metadata for later writing to file.
    """
    if bucket is not None:
        path = s3.build_rasterio_path(bucket, path)
    tmax_jan = os.path.join(path, 'tmax_1.tif')
    tmean_jan = os.path.join(path, 'tmean_1.tif')
    tmin_jan = os.path.join(path, 'tmin_1.tif')

    tmax_feb = os.path.join(path, 'tmax_2.tif')
    tmean_feb = os.path.join(path, 'tmean_2.tif')
    tmin_feb = os.path.join(path, 'tmin_2.tif')

    tmax_mar = os.path.join(path, 'tmax_3.tif')
    tmean_mar = os.path.join(path, 'tmean_3.tif')
    tmin_mar = os.path.join(path, 'tmin_3.tif')

    tmax_apr = os.path.join(path, 'tmax_4.tif')
    tmean_apr = os.path.join(path, 'tmean_4.tif')
    tmin_apr = os.path.join(path, 'tmin_4.tif')

    tmax_may = os.path.join(path, 'tmax_5.tif')
    tmean_may = os.path.join(path, 'tmean_5.tif')
    tmin_may = os.path.join(path, 'tmin_5.tif')

    tmax_jun = os.path.join(path, 'tmax_6.tif')
    tmean_jun = os.path.join(path, 'tmean_6.tif')
    tmin_jun = os.path.join(path, 'tmin_6.tif')

    tmax_jul = os.path.join(path, 'tmax_7.tif')
    tmean_jul = os.path.join(path, 'tmean_7.tif')
    tmin_jul = os.path.join(path, 'tmin_7.tif')

    tmax_aug = os.path.join(path, 'tmax_8.tif')
    tmean_aug = os.path.join(path, 'tmean_8.tif')
    tmin_aug = os.path.join(path, 'tmin_8.tif')

    tmax_sep = os.path.join(path, 'tmax_9.tif')
    tmean_sep = os.path.join(path, 'tmean_9.tif')
    tmin_sep = os.path.join(path, 'tmin_9.tif')

    tmax_oct = os.path.join(path, 'tmax_10.tif')
    tmean_oct = os.path.join(path, 'tmean_10.tif')
    tmin_oct = os.path.join(path, 'tmin_10.tif')

    tmax_nov = os.path.join(path, 'tmax_11.tif')
    tmean_nov = os.path.join(path, 'tmean_11.tif')
    tmin_nov = os.path.join(path, 'tmin_11.tif')

    tmax_dec = os.path.join(path, 'tmax_12.tif')
    tmean_dec = os.path.join(path, 'tmean_12.tif')
    tmin_dec = os.path.join(path, 'tmin_12.tif')

    # Check that these files exist
    #check_exist = [os.path.isfile(x) for x in [tmax_jan, tmean_jan, tmin_jan]]
    #if not all(check_exist):
    #    raise ValueError('Target directory must at least contain the 3 following files (tmax_1.tif, tmean_1.tif, tmin_1.tif)')

    with rasterio.open(tmax_jan) as src:
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
        'tmax_jan': tmax_jan,
        'tmean_jan': tmean_jan,
        'tmin_jan': tmin_jan,
        'tmax_feb': tmax_feb,
        'tmean_feb': tmean_feb,
        'tmin_feb': tmin_feb,
        'tmax_mar': tmax_mar,
        'tmean_mar': tmean_mar,
        'tmin_mar': tmin_mar,
        'tmax_apr': tmax_apr,
        'tmean_apr': tmean_apr,
        'tmin_apr': tmin_apr,
        'tmax_may': tmax_may,
        'tmean_may': tmean_may,
        'tmin_may': tmin_may,
        'tmax_jun': tmax_jun,
        'tmean_jun': tmean_jun,
        'tmin_jun': tmin_jun,
        'tmax_jul': tmax_jul,
        'tmean_jul': tmean_jul,
        'tmin_jul': tmin_jul,
        'tmax_aug': tmax_aug,
        'tmean_aug': tmean_aug,
        'tmin_aug': tmin_aug,
        'tmax_sep': tmax_sep,
        'tmean_sep': tmean_sep,
        'tmin_sep': tmin_sep,
        'tmax_oct': tmax_oct,
        'tmean_oct': tmean_oct,
        'tmin_oct': tmin_oct,
        'tmax_nov': tmax_nov,
        'tmean_nov': tmean_nov,
        'tmin_nov': tmin_nov,
        'tmax_dec': tmax_dec,
        'tmean_dec': tmean_dec,
        'tmin_dec': tmin_dec,
    }
    # Load template
    env = Environment(loader=PackageLoader('madmex', 'templates'))
    template = env.get_template('bioclimatics.yaml')
    out = template.render(**meta_out)
    return out
