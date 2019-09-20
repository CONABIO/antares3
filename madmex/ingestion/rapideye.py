import os
from glob import glob
import re
import uuid
import xml.etree.ElementTree as ET

from rasterio.crs import CRS
from pyproj import Proj
from jinja2 import Environment, PackageLoader

def metadata_convert(path, bucket=None):
    """Prepare metatdata prior to datacube indexing

    Given a directory containing Rapideye image and a xml file,
    prepares a metadata string with the appropriate formating.

    Args:
        path (str): Path of the directory containing the Rapideye image
            and the Rapideye metadata file.
        bucket (str or None): Name of the s3 bucket containing the data. If ``None``
            (default), data are considered to be on a mounted filesystem

    Examples:
        >>> from madmex.ingestion.rapideye import metadata_convert
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
    pattern = re.compile(r'.*[0-9]{4}-[0-9]{2}-[0-9]{2}.*_RE(2|4|5)_3A.*_metadata\.xml')
    # Check that path is a dir and contains appropriate files
    if not os.path.isdir(path):
        raise ValueError('Argument path= is not a directory')
    xml_file_list = glob(os.path.join(path, '*.xml'))
    # Filter list of xml files with regex (there could be more than one in case 
    # some bands have been opend in qgis for example)

    xml_file_list = [x for x in xml_file_list if pattern.search(x)]
    if len(xml_file_list) != 1:
        raise ValueError('Could not identify a unique xml metadata file')
    xml_file = xml_file_list[0]
    # Start parsing xml
    root = ET.parse(xml_file).getroot()
    # Some namespaces that will help parsing metadata
    ns = 'http://www.opengis.net/gml'
    ns2 = 'http://schemas.rapideye.de/products/productMetadataGeocorrected'
    ns3 = 'http://earth.esa.int/eop'
    dt = root.find('ns:metaDataProperty/ns2:EarthObservationMetaData/ns3:downlinkedTo/ns3:DownlinkInformation/ns3:acquisitionDate',
                   namespaces={'ns': ns, 'ns2': ns2, 'ns3': ns3}).text
    #removing minutes, seconds, ...
    dt = dt[:19]
    product_type = root.find('ns:metaDataProperty/ns2:EarthObservationMetaData/ns3:productType',
                             namespaces = {'ns':ns, 'ns2':ns2,'ns3':ns3}).text
    instrument = root.find('ns:using/ns3:EarthObservationEquipment/ns3:instrument/ns3:Instrument/ns3:shortName',
                           namespaces={'ns': ns, 'ns3': ns3}).text
    format_image = root.find('ns:metaDataProperty/ns2:EarthObservationMetaData/ns3:processing/ns3:ProcessingInformation/ns3:nativeProductFormat',
                             namespaces={'ns': ns, 'ns2':ns2,'ns3':ns3}).text
    satellite = root.find('ns:using/ns3:EarthObservationEquipment/ns3:platform/ns3:Platform/ns3:serialIdentifier',
                          namespaces={'ns': ns, 'ns3':ns3}).text
    ul_lat = float(root.find('ns:target/ns2:Footprint/ns2:geographicLocation/ns2:topLeft/ns2:latitude',
                             namespaces={'ns': ns, 'ns2': ns2}).text)
    ul_lon = float(root.find('ns:target/ns2:Footprint/ns2:geographicLocation/ns2:topLeft/ns2:longitude',
                             namespaces={'ns': ns, 'ns2': ns2}).text)
    ur_lat = float(root.find('ns:target/ns2:Footprint/ns2:geographicLocation/ns2:topRight/ns2:latitude',
                             namespaces={'ns': ns, 'ns2': ns2}).text)
    ur_lon = float(root.find('ns:target/ns2:Footprint/ns2:geographicLocation/ns2:topRight/ns2:longitude',
                             namespaces={'ns': ns, 'ns2': ns2}).text)
    lr_lat = float(root.find('ns:target/ns2:Footprint/ns2:geographicLocation/ns2:bottomRight/ns2:latitude',
                             namespaces={'ns': ns, 'ns2': ns2}).text)
    lr_lon = float(root.find('ns:target/ns2:Footprint/ns2:geographicLocation/ns2:bottomRight/ns2:longitude',
                             namespaces={'ns': ns, 'ns2': ns2}).text)
    ll_lat = float(root.find('ns:target/ns2:Footprint/ns2:geographicLocation/ns2:bottomLeft/ns2:latitude',
                             namespaces={'ns': ns, 'ns2': ns2}).text)
    ll_lon = float(root.find('ns:target/ns2:Footprint/ns2:geographicLocation/ns2:bottomLeft/ns2:longitude',
                             namespaces={'ns': ns, 'ns2': ns2}).text)
    utm_zone = root.find('ns:resultOf/ns2:EarthObservationResult/ns3:product/ns2:ProductInformation/ns2:spatialReferenceSystem/ns2:projectionZone',
                         namespaces={'ns':ns,'ns2':ns2, 'ns3':ns3}).text
    crs = CRS({'proj': 'utm',
               'zone': utm_zone})
    p = Proj(crs)
    ulx,uly = p(ul_lon,ul_lat)
    lrx,lry = p(lr_lon,lr_lat)
    product = os.path.join(path, root.find('ns:resultOf/ns2:EarthObservationResult/ns3:product/ns2:ProductInformation/ns3:fileName',
                                           namespaces={'ns':ns, 'ns2':ns2, 'ns3':ns3}).text)
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
        'blue': {'path': product, 'layer': 1}
        }
    # Load template
    env = Environment(loader=PackageLoader('madmex', 'templates'))
    template = env.get_template('rapideye.yaml')
    out = template.render(**meta_out)
    return out
