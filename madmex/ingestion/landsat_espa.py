import os
from glob import glob
import uuid

import rasterio
from jinja2 import Environment, PackageLoader


def metadata_convert(path):
    """Prepare metatdata prior to datacube indexing

    Given a directory containing landsat surface reflectance bands and a MLT.txt
    file, prepares a metadata string with the appropriate formating.

    Args:
        path (str): Path of the directory containing the surface reflectance bands
            and the Landsat metadata file.

    Examples:
        >>> from madmex.ingestion.landsat_espa import metadata_convert
        >>> from glob import glob

        >>> scene_list = glob('/path/to/scenes/*')
        >>> yaml_list = [metadata_convert(x) for x in scene_list]

        >>> with open('/path/to/metadata_out.yaml', 'w') as dst:
        >>>     for yaml in yaml_list:
        >>>         dst.write(yaml)
        >>>         dst.write('\n---\n')

    Returns:
        str: The content of the metadata for later writing to file.
    """
    # Check that path is a dir and contains appropriate files
    if not os.path.isdir(path):
        raise ValueError('Argument path= is not a directory')
    mtl_file_list = glob(os.path.join(path, '*MTL.txt'))
    if len(mtl_file_list) != 1:
        raise ValueError('Target directory must contain a unique MTL text file')
    mtl_file = mtl_file_list[0]
    meta_dict = {}
    with open(mtl_file) as f:
        for line in f:
            try:
                (key, val) = line.split(' = ')
                (key, val) = (key.lstrip(), val.strip('\n').strip('"'))
                meta_dict[key] = val
            except Exception:
                pass
    # Retrieve crs from first band
    bands = glob(os.path.join(path, '*B1.TIF'))
    with rasterio.open(bands[0]) as src:
        epsg = src.crs['init']
    # Prepare metadata fields
    meta_out = {
        'id': uuid.uuid5(uuid.NAMESPACE_URL, path),
        'dt': meta_dict['SCENE_CENTER_TIME'],
        'll_lat': meta_dict['CORNER_LL_LAT_PRODUCT'],
        'lr_lat': meta_dict['CORNER_LR_LAT_PRODUCT'],
        'ul_lat': meta_dict['CORNER_UL_LAT_PRODUCT'],
        'ur_lat': meta_dict['CORNER_UR_LAT_PRODUCT'],
        'll_lon': meta_dict['CORNER_LL_LON_PRODUCT'],
        'lr_lon': meta_dict['CORNER_LR_LON_PRODUCT'],
        'ul_lon': meta_dict['CORNER_UL_LON_PRODUCT'],
        'ur_lon': meta_dict['CORNER_UR_LON_PRODUCT'],
        'll_x': meta_dict['CORNER_LL_PROJECTION_X_PRODUCT'],
        'lr_x': meta_dict['CORNER_LR_PROJECTION_X_PRODUCT'],
        'ul_x': meta_dict['CORNER_UL_PROJECTION_X_PRODUCT'],
        'ur_x': meta_dict['CORNER_UR_PROJECTION_X_PRODUCT'],
        'll_y': meta_dict['CORNER_LL_PROJECTION_Y_PRODUCT'],
        'lr_y': meta_dict['CORNER_LR_PROJECTION_Y_PRODUCT'],
        'ul_y': meta_dict['CORNER_UL_PROJECTION_Y_PRODUCT'],
        'ur_y': meta_dict['CORNER_UR_PROJECTION_Y_PRODUCT'],
        'epsg_code': epsg,
        # TODO: FIle names have to be assigned dynamically, otherwise will
        # only work for Landsat 8
        'blue': meta_dict['FILE_NAME_BAND_2'],
        'green': meta_dict['FILE_NAME_BAND_3'],
        'red': meta_dict['FILE_NAME_BAND_4'],
        'nir': meta_dict['FILE_NAME_BAND_5'],
        'swir1': meta_dict['FILE_NAME_BAND_6'],
        'swir2': meta_dict['FILE_NAME_BAND_7'],
        'instrument': meta_dict['SENSOR_ID'],
        'platform': meta_dict['SPACECRAFT_ID'],

    }
    # Load template
    env = Environment(loader=PackageLoader('madmex', 'templates'))
    template = env.get_template('landsat_espa.yaml')
    out = template.render(**meta_out)
    return out
