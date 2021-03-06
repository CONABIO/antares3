import os
from glob import glob
import re
import uuid
import xml.etree.ElementTree as ET

from rasterio.crs import CRS
from pyproj import Proj
from jinja2 import Environment, PackageLoader

from madmex.util import s3

def metadata_convert(path, bucket=None):
    """Prepare metatdata prior to datacube indexing

    Given a directory containing sentinel2 surface reflectance bands processed
    with sen2cor, prepares a metadata string with the appropriate formating.

    Args:
        path (str): Path of the directory containing data and metadata with SAFE
            structure. Output of sen2cor processor
        bucket (str or None): Name of the s3 bucket containing the data. If ``None``
            (default), data are considered to be on a mounted filesystem

    Examples:
        >>> from madmex.ingestion.sentinel2_sr_20m import metadata_convert
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
    def get_namespace(element):
        m = re.match('\{(.*)\}', element.tag)
        return m.group(1) if m else ''
    # List all files in directory
    if bucket is None:
        all_files = glob(os.path.join(path, '**'), recursive=True)
    else:
        all_files = s3.list_files(bucket, path)
    # Check that path is a dir and contains appropriate files
    if len(all_files) <= 1:
        raise ValueError('Argument path= is not a directory, or doesn\'t contain any files')
    mtl_pattern = re.compile(r'.*GRANULE.*MTD_TL\.xml$')
    mtl_file = [x for x in all_files if mtl_pattern.search(x)][0]
    # Extract metadata from filename
    # satellite = os.path.basename(path)[:3]
    satellite = 'sentinel2' # using generic name for both satellite to avoid mismatch with product description
    instrument = 'MSI'
    # Start parsing xml
    if bucket is None:
        root = ET.parse(mtl_file).getroot()
    else:
        xml_str = s3.read_file(bucket, mtl_file)
        root = ET.fromstring(xml_str)
    n1 = get_namespace(root)
    date_str = root.find('n1:General_Info/SENSING_TIME',
                         namespaces={'n1': n1}).text
    dt = date_str[:-5]
    # Scene corners in projected coordinates
    nrow = int(root.find('n1:Geometric_Info/Tile_Geocoding/Size[@resolution="20"]/NROWS',
                     namespaces={'n1': n1}).text)
    ncol = int(root.find('n1:Geometric_Info/Tile_Geocoding/Size[@resolution="20"]/NCOLS',
                     namespaces={'n1': n1}).text)
    ulx = float(root.find('n1:Geometric_Info/Tile_Geocoding/Geoposition[@resolution="20"]/ULX',
                     namespaces={'n1': n1}).text)
    uly = float(root.find('n1:Geometric_Info/Tile_Geocoding/Geoposition[@resolution="20"]/ULY',
                     namespaces={'n1': n1}).text)
    lrx = ulx + ncol * 20
    lry = uly - nrow * 20
    # Get coorner coordinates in long lat by transforming from projected values 
    crs = root.find('n1:Geometric_Info/Tile_Geocoding/HORIZONTAL_CS_CODE',
                               namespaces={'n1': n1}).text
    crs_wkt = CRS(init=crs).wkt
    p = Proj(init=crs)
    ul_lon, ul_lat = p(ulx, uly, inverse=True)
    lr_lon, lr_lat = p(lrx, lry, inverse=True)
    ll_lon, ll_lat = p(ulx, lry, inverse=True)
    ur_lon, ur_lat = p(lrx, uly, inverse=True)
    # FUnction to get band path from its suffix
    def get_band(suffix):
        pattern = re.compile(r'.*GRANULE/.*/IMG_DATA/R20m/.*%s_20m\.jp2$' % suffix)
        band = [x for x in all_files if pattern.search(x)][0]
        if bucket is not None:
            band = s3.build_rasterio_path(bucket, band)
        return band
    # Prepare metadata fields
    meta_out = {
        'id': uuid.uuid5(uuid.NAMESPACE_URL, path),
        'dt': dt,
        'll_lat': ll_lat,
        'lr_lat': lr_lat,
        'ul_lat': ul_lat,
        'ur_lat': ur_lat,
        'll_lon': ll_lon,
        'lr_lon': lr_lon,
        'ul_lon': ul_lon,
        'ur_lon': ur_lon,
        'll_x': ulx,
        'lr_x': lrx,
        'ul_x': ulx,
        'ur_x': lrx,
        'll_y': lry,
        'lr_y': lry,
        'ul_y': uly,
        'ur_y': uly,
        'crs': crs_wkt,
        'blue': get_band('B02'),
        'green': get_band('B03'),
        'red': get_band('B04'),
        're1': get_band('B05'),
        're2': get_band('B06'),
        're3': get_band('B07'),
        'nir': get_band('B8A'),
        'swir1': get_band('B11'),
        'swir2': get_band('B12'),
        'qual': get_band('SCL'),
        'instrument': instrument,
        'platform': satellite,
    }
    # Load template
    env = Environment(loader=PackageLoader('madmex', 'templates'))
    template = env.get_template('s2_l2a_20m.yaml')
    out = template.render(**meta_out)
    return out
