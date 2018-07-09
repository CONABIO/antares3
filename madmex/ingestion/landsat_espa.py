import os
from glob import glob
import re
import uuid
import xml.etree.ElementTree as ET

import rasterio
from pyproj import Proj
from jinja2 import Environment, PackageLoader

try:
    import boto3
except ImportError:
    _has_boto3 = False
else:
    _has_boto3 = True

LANDSAT_BANDS = {'TM': {'blue': 'sr_band1',
                        'green': 'sr_band2',
                        'red': 'sr_band3',
                        'nir': 'sr_band4',
                        'swir1': 'sr_band5',
                        'swir2': 'sr_band7'},
                 'OLI_TIRS': {'blue': 'sr_band2',
                              'green': 'sr_band3',
                              'red': 'sr_band4',
                              'nir': 'sr_band5',
                              'swir1': 'sr_band6',
                              'swir2': 'sr_band7'}}
LANDSAT_BANDS['ETM'] = LANDSAT_BANDS['TM']

def metadata_convert(path, bucket=None):
    """Prepare metatdata prior to datacube indexing

    Given a directory containing landsat surface reflectance bands and a MLT.txt
    file, prepares a metadata string with the appropriate formating.

    Args:
        path (str): Path of the directory containing the surface reflectance bands
            and the Landsat metadata file.
        bucket (str or None): Name of the s3 bucket containing the data. If ``None``
            (default), data are considered to be on a mounted filesystem

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
    pattern = re.compile(r'[A-Z0-9]{4}_[A-Z0-9]{4}_\d{6}_\d{8}_\d{8}_01_(T1|T2|RT)\.xml')
    if bucket is None:
        # Check that path is a dir and contains appropriate files
        if not os.path.isdir(path):
            raise ValueError('Argument path= is not a directory')
        mtl_file_list = glob(os.path.join(path, '*.xml'))
        # Filter list of xml files with regex (there could be more than one in case
        # some bands have been opend in qgis for example)
        mtl_file_list = [x for x in mtl_file_list if pattern.search(x)]
        print(mtl_file_list)
        if len(mtl_file_list) != 1:
            raise ValueError('Could not identify a unique xml metadata file')
        mtl_file = mtl_file_list[0]
        # Start parsing xml
        root = ET.parse(mtl_file).getroot()
    else:
        if not _has_boto3:
            raise ImportError('boto3 is required for working with s3 buckets')
        # OPen bucket connection
        s3 = boto3.resource('s3')
        my_bucket = s3.Bucket(bucket)
        # Retrieve all the files from the directory
        file_list = [x.key for x in my_bucket.objects.filter(Prefix=path)]
        # Filter using regex pattern
        mtl_file_list = [x for x in file_list if pattern.search(x)]
        print(mtl_file_list)
        if len(mtl_file_list) != 1:
            raise ValueError('Could not identify a unique xml metadata file')
        mtl_file = mtl_file_list[0]
        # REad xml as string
        obj = s3.Object(bucket, mtl_file)
        xml_str = obj.get()["Body"].read()
        # generate element tree root
        root = ET.fromstring(xml_str)

    ns = 'http://espa.cr.usgs.gov/v2'
    # Build datetime from date and time
    date_str = root.find('ns:global_metadata/ns:acquisition_date',
                         namespaces={'ns': ns}).text
    time_str = root.find('ns:global_metadata/ns:scene_center_time',
                         namespaces={'ns': ns}).text
    dt = '%sT%s' % (date_str, time_str[:8])
    # satellite sensor metadata
    instrument = root.find('ns:global_metadata/ns:instrument',
                           namespaces={'ns': ns}).text
    satellite = root.find('ns:global_metadata/ns:satellite',
                          namespaces={'ns': ns}).text
    # Scene corners in projected coordinates
    ulx = float(root.find('ns:global_metadata/ns:projection_information/ns:corner_point[@location="UL"]',
                          namespaces={'ns': ns}).attrib['x'])
    uly = float(root.find('ns:global_metadata/ns:projection_information/ns:corner_point[@location="UL"]',
                          namespaces={'ns': ns}).attrib['y'])
    lrx = float(root.find('ns:global_metadata/ns:projection_information/ns:corner_point[@location="LR"]',
                          namespaces={'ns': ns}).attrib['x'])
    lry = float(root.find('ns:global_metadata/ns:projection_information/ns:corner_point[@location="LR"]',
                          namespaces={'ns': ns}).attrib['y'])
    # Retrieve crs from first band
    if bucket is None:
        bands = glob(os.path.join(path, '*_sr_band2.tif'))
        with rasterio.open(bands[0]) as src:
            crs = src.crs
    else:
        b2_pattern = re.compile(r'.*_sr_band2.tif$')
        bands = [x for x in file_list if b2_pattern.search(x)]
        band2 = os.path.join('s3://', bucket, bands[0])
        print(band2)
        with rasterio.open(band2) as src:
            crs = src.crs
        path = os.path.join('s3://', bucket, path)

    # Get coorner coordinates in long lat by transforming from projected values 
    p = Proj(crs)
    ul_lon, ul_lat = p(ulx, uly, inverse=True)
    lr_lon, lr_lat = p(lrx, lry, inverse=True)
    ll_lon, ll_lat = p(ulx, lry, inverse=True)
    ur_lon, ur_lat = p(lrx, uly, inverse=True)
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
        'crs': crs.wkt,
        'blue': os.path.join(path, root.find('ns:bands/ns:band[@name="%s"]/ns:file_name' %
                                             LANDSAT_BANDS[instrument]['blue'],
                                             namespaces={'ns': 'http://espa.cr.usgs.gov/v2'}).text),
        'green': os.path.join(path, root.find('ns:bands/ns:band[@name="%s"]/ns:file_name' %
                                              LANDSAT_BANDS[instrument]['green'],
                                              namespaces={'ns': 'http://espa.cr.usgs.gov/v2'}).text),
        'red': os.path.join(path, root.find('ns:bands/ns:band[@name="%s"]/ns:file_name' %
                                              LANDSAT_BANDS[instrument]['red'],
                                              namespaces={'ns': 'http://espa.cr.usgs.gov/v2'}).text),
        'nir': os.path.join(path, root.find('ns:bands/ns:band[@name="%s"]/ns:file_name' %
                                              LANDSAT_BANDS[instrument]['nir'],
                                              namespaces={'ns': 'http://espa.cr.usgs.gov/v2'}).text),
        'swir1': os.path.join(path, root.find('ns:bands/ns:band[@name="%s"]/ns:file_name' %
                                              LANDSAT_BANDS[instrument]['swir1'],
                                              namespaces={'ns': 'http://espa.cr.usgs.gov/v2'}).text),
        'swir2': os.path.join(path, root.find('ns:bands/ns:band[@name="%s"]/ns:file_name' %
                                              LANDSAT_BANDS[instrument]['swir2'],
                                              namespaces={'ns': 'http://espa.cr.usgs.gov/v2'}).text),
        'qual': os.path.join(path, root.find('ns:bands/ns:band[@name="pixel_qa"]/ns:file_name',
                                              namespaces={'ns': 'http://espa.cr.usgs.gov/v2'}).text),
        'instrument': instrument,
        'platform': satellite,

    }
    # Load template
    env = Environment(loader=PackageLoader('madmex', 'templates'))
    template = env.get_template('landsat_espa.yaml')
    out = template.render(**meta_out)
    return out
