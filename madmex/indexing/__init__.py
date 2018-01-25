import os

import yaml
from datacube.index._datasets import ProductResource, MetadataTypeResource, DatasetResource
from datacube.index.postgres._connections import PostgresDb
from datacube.model import Dataset

from ../util import randomword

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


def add_dataset(pr, dt, metadict):
    """Add a dataset to the datacube

    Args:
        pr (ProductResource): A ProductResource object, contained in the return of
            ``add_product``
        dt (DatasetType): A DatasetType object, contained in the return of ``add_product``
        metadict (dict): Dictionary containing dataset metadata, generally generated
            by ``metadict_from_netcdf``

    Return:
        No return, the function is used for its side effect of adding a dataset to the datacube
    """
    db = PostgresDb.from_config()
    dataset_resource = DatasetResource(db, pr)
    dataset = Dataset(dt, metadict)
    dataset_resource.add(dataset)


def metadict_from_netcdf(file, description):
    """Get metadata dictionary for netcdf dataset written using ``write_dataset_to_netcdf``

    Args:
        file (str): Netcdf file previously written using the ``write_dataset_to_netcdf``
            function.
        description (dict): corresponding product description

    Return:
        dict: A dictionary containing dataset metadata
    """
    raise NotImplementedError()
    out = {
        'id':,
        'creation_dt':,
        'product_type':,
        'platform': {
            'code':
        },
        'instrument': {
            'name':
        },
        'format': {
            'name': 'NetCDF'
        },
        'extent': {
            'coord': {
                'll': {'lat':, 'lon':},
                'lr': {'lat':, 'lon':},
                'ul': {'lat':, 'lon':},
                'ur': {'lat':, 'lon':}
            }
        },
        'from_dt':,
        'center_dt':,
        'to_dt':,
        'grid_spatial': {
            'projection': {
                'geo_ref_points': {
                    'll': {'y':, 'x':},
                    'lr': {'y':, 'x':},
                    'ul': {'y':, 'x':},
                    'ur': {'y':, 'x':}
                },
                'spatial_reference':,
            },
        },
        'image': {
            'bands': {
            },
        },
        'lineage': {
            'algorithm':,
        },
    }
