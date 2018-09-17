import os
import uuid
from datetime import datetime

import yaml
from datacube.index._datasets import DatasetResource
from datacube.index._products import ProductResource
from datacube.index._metadata_types import MetadataTypeResource
from datacube.drivers.postgres._connections import PostgresDb
from datacube.model import Dataset
from pyproj import Proj
import netCDF4 as nc
from affine import Affine
from osgeo import osr

from madmex.util import randomword
from configparser import ConfigParser

conf = ConfigParser()
conf.read(os.path.expanduser('~/.datacube.conf'))
CONFIG = conf['datacube']

def add_product(description, name):
    """Add a new product to the database given a product description dictionary

    Intended use is for indexing intermediary results resulting from applying a
    'recipe' to one or several ingested dataset. Product description files corresponding
    to each recipe should be placed in ``madmex/conf/indexing``. See also add_product_from_recipe
    and add_product_from_yaml

    Args:
        description (dict): A dictionary containing the product description. See
            datacube 'product definition' documentation for more details. The dictionary
            should not contain the name key since it has to be specified in an argument to
            this function.
        name (str): Product name

    Returns:
        list: List of 2, containing a ProductResource object and a DatasetType object
    """
    # Append name to dictionary
    description.update(name=name)
    # Add to database
    db = PostgresDb.from_config(CONFIG)
    meta_resource = MetadataTypeResource(db)
    product_resource = ProductResource(db, meta_resource)
    dataset_type = product_resource.add_document(description)
    return [product_resource, dataset_type]


def add_product_from_yaml(description, name):
    """Wrapper to add a product directly from a yaml file

    yaml files corresponding to recipes are normally placed in ``/madmex/conf/indexing``
    and exported to ``~/.config/madmex/indexing`` by running the ``conf_setup`` command.

    Args:
        description (str): Path to yaml file containing the product description.
            Must not include the 'name' property
        name (str): Product name

    Returns:
        list: List of 2, containing a ProductResource object and a DatasetType object
    """
    with open(description, 'r') as src:
        description_dict = yaml.load(src)
    return add_product(description_dict, name)


def add_product_from_recipe(recipe, name=None):
    """Wrapper to add a product from a recipe name

    yaml product description file corresponding to the recipe must be present in
    the ``~/.config/madmex/indexing`` directory.

    Args:
        recipe (str): Name of the recipe
        name (str): Product name, optional. Default to None in which case a random
            product name is generated.

    Returns:
        list: List of 2, containing a ProductResource object and a DatasetType object
    """
    description = os.path.expanduser(os.path.join('~/.config/madmex/indexing',
                                                  '%s.yaml' % recipe))
    if name is None:
        name = '%s_%s' % (recipe, randomword(5))
    return add_product_from_yaml(description, name)


def add_dataset(pr, dt, metadict, file):
    """Add a dataset to the datacube database

    It's added to 3 tables:
      - dataset: with all the metadata
      - dataset_location
      - dataset_type

    Args:
        pr (ProductResource): A ProductResource object, contained in the return of
            ``add_product``
        dt (DatasetType): A DatasetType object, contained in the return of ``add_product``
        metadict (dict): Dictionary containing dataset metadata, generally generated
            by ``metadict_from_netcdf``
        file (str): Path of the file to add to the index

    Return:
        No return, the function is used for its side effect of adding a dataset to the datacube
    """
    db = PostgresDb.from_config(CONFIG)
    dataset_resource = DatasetResource(db, pr)
    dataset = Dataset(dt, metadict, sources={})
    dataset_resource.add(dataset)
    uid = metadict['id']
    dataset_resource.add_location(uid, file)


def wkt_to_proj4(wkt):
    """Utility to convert CRS WKT to CRS in proj4 format

    Uses the gdal python bindings. This function can be deleted if a recent version
    of rasterio is present (1), in which case ``rasterio.crs.CRS`` ``from_wkt``
    method should be prefered.

    Args:
        wkt (str): CRS string in Well Known Text format

    Return:
        str: Corresponding proj4 string
    """
    srs = osr.SpatialReference()
    srs.ImportFromWkt(wkt)
    return srs.ExportToProj4()


def metadict_from_netcdf(file, description, center_dt, from_dt=None,
                         to_dt=None, algorithm=None):
    """Get metadata dictionary for netcdf dataset written using ``write_dataset_to_netcdf``

    Args:
        file (str): Netcdf file previously written using the ``write_dataset_to_netcdf``
            function.
        description (dict): corresponding product description
        center_dt (datetime.datetime): Central date of the dataset
        from_dt (datetime.datetime): Optional begin date of the dataset
        to_dt (datetime.datetime): Optional end date of the dataset
        algorithm (str): Option description/identifier of the algorithm/recipe used to
            produce that dataset

    Return:
        dict: A dictionary containing dataset metadata

    Example:
        >>> from madmex.indexing import metadict_from_netcdf
        >>> import yaml
        >>> from pprint import pprint
        >>> from datetime import datetime

        >>> nc_file = '/path/to/nc_file.nc'
        >>> with open('~/.config/madmex/indexing/corresponding_config_file.yaml') src:
        >>>     description = yaml.load(src)

        >>> metadict = metadict_from_netcdf(nc_file, description, center_dt=datetime(2015, 7, 1))
        >>> pprint(metadict)

    """
    if from_dt is None:
        from_dt = center_dt
    if to_dt is None:
        to_dt = center_dt
    with nc.Dataset(file) as src:
        creation_dt = src.date_created
        list_dimensions = [x for x in src.dimensions.keys() if x != 'time']
        lambda_function = lambda l_netcdf,l_test: l_netcdf[0] if l_netcdf[0] in l_test else l_netcdf[1]
        xdim = lambda_function(list_dimensions,['x','longitude'])
        ydim = lambda_function(list_dimensions,['y','latitude'])
        aff = Affine.from_gdal(*src['crs'].GeoTransform)
        res = aff[0]
        xmin = min(src[xdim]) - res / 2
        xmax = max(src[xdim]) + res / 2
        ymin = min(src[ydim]) - res / 2
        ymax = max(src[ydim]) + res / 2
        crs_wkt = src['crs'].crs_wkt
        # var list
        var_list = src.get_variables_by_attributes(grid_mapping='crs')
        var_list = [x.name for x in var_list]
    #Convert projected corner coordinates to longlat
    p = Proj(wkt_to_proj4(crs_wkt))
    p2 = Proj(init="EPSG:4326")
    s1 = osr.SpatialReference()
    s1.ImportFromProj4(p.srs)
    s2 = osr.SpatialReference()
    s2.ImportFromProj4(p2.srs)
    if not s1.IsSame(s2):
        ul_long, ul_lat = p(xmin, ymax, inverse=True) # inverse=True to transform x,y to long, lat
        ur_long, ur_lat = p(xmax, ymax, inverse=True)
        lr_long, lr_lat = p(xmax, ymin, inverse=True)
        ll_long, ll_lat = p(xmin, ymin, inverse=True)
    else:
        ul_long, ul_lat = xmin, ymax
        ur_long, ur_lat = xmax, ymax
        lr_long, lr_lat = xmax, ymin
        ll_long, ll_lat = xmin, ymin
    out = {
        'id': str(uuid.uuid5(uuid.NAMESPACE_URL, file)),
        'creation_dt': creation_dt,
        'product_type': description['metadata']['product_type'],
        'platform': description['metadata']['platform'],
        'instrument': description['metadata']['instrument'],
        'format': description['metadata']['format'],
        'extent': {
            'coord': {
                'll': {'lat': ll_lat, 'lon': ll_long},
                'lr': {'lat': lr_lat, 'lon': lr_long},
                'ul': {'lat': ul_lat, 'lon': ul_long},
                'ur': {'lat': ur_lat, 'lon': ur_long},
            },
            'from_dt': from_dt.strftime('%Y-%m-%d'),
            'center_dt': center_dt.strftime('%Y-%m-%d'),
            'to_dt': to_dt.strftime('%Y-%m-%d'),
        },
        'grid_spatial': {
            'projection': {
                'geo_ref_points': {
                    'll': {'y': ymin, 'x': xmin},
                    'lr': {'y': ymin, 'x': xmax},
                    'ul': {'y': ymax, 'x': xmin},
                    'ur': {'y': ymax, 'x': xmax}
                },
                'spatial_reference': crs_wkt,
            },
        },
        'image': {
            'bands': {band:{'path': file, 'layer': band} for band in var_list},
        },
        'lineage': {
            'algorithm': algorithm,
            'source_datasets': {},
        },
    }
    return out
