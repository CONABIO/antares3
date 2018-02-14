import os
import uuid
from datetime import datetime

import yaml
from datacube.index._datasets import ProductResource, MetadataTypeResource, DatasetResource
from datacube.index.postgres._connections import PostgresDb
from datacube.model import Dataset
from pyproj import Proj
import netCDF4 as nc
from affine import Affine
from osgeo import osr

from madmex.util import randomword

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
    db = PostgresDb.from_config()
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

    It's added to 2 tables:
      - dataset: with all the metadata
      - dataset_location

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
    db = PostgresDb.from_config()
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
        aff = Affine.from_gdal(*src['crs'].GeoTransform)
        res = aff[0]
        xmin = min(src['x']) - res / 2
        xmax = max(src['x']) + res / 2
        ymin = min(src['y']) - res / 2
        ymax = max(src['y']) + res / 2
        crs_wkt = src['crs'].crs_wkt
        # var list
        var_list = src.get_variables_by_attributes(grid_mapping='crs')
        var_list = [x.name for x in var_list]
    # Convert projected corner coordinates to longlat
    p = Proj(wkt_to_proj4(crs_wkt))
    long_min, lat_min = p(xmin, ymin, inverse=True)
    long_max, lat_max = p(xmax, ymax, inverse=True)
    out = {
        'id': str(uuid.uuid5(uuid.NAMESPACE_URL, file)),
        'creation_dt': creation_dt,
        'product_type': description['metadata']['product_type'],
        'platform': description['metadata']['platform'],
        'instrument': description['metadata']['instrument'],
        'format': description['metadata']['format'],
        'extent': {
            'coord': {
                'll': {'lat': lat_min, 'lon': long_min},
                'lr': {'lat': lat_min, 'lon': long_max},
                'ul': {'lat': lat_max, 'lon': long_min},
                'ur': {'lat': lat_max, 'lon': long_max}
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
