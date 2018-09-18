import json
from affine import Affine
from rasterio.features import rasterize
import numpy as np

from madmex.util.spatial import feature_transform

def rasterize_xarray(fc, dataset):
    """Rasterize a feature collection using an xarray dataset as target

    Feature collection and xarray dataset must already be in the same CRS

    Args:
        fc (list): Collection of valid (see geojson.org) features
        dataset (xarray.Dataset): A Dataset generated using Datacube.load() or
            GridWorkflow.load(). Must have an affine attribute

    Return:
        numpy.array: An array with 0 as background value. Pixels overlapping
        with features geometries are assigned the value of the geometry ID (calculated on
        the fly based on feature order).
    """
    # Extract geometries from features
    geom_list = [x['geometry'] for x in fc]
    # Prepare iterable to be passed to rasterio rasterize
    iterable = zip(geom_list, range(1, len(geom_list) + 1))
    # Use Affine from the affine library to be safe
    aff = Affine(*list(dataset.affine)[0:6])
    # Rasterize
    dimensions_dataset = list(dataset.coords)
    list_dimensions = [x for x in dimensions_dataset if x != 'time']
    lambda_function = lambda l_netcdf,l_test: l_netcdf[0] if l_netcdf[0] in l_test else l_netcdf[1]
    xdim = lambda_function(list_dimensions,['x','longitude'])
    ydim = lambda_function(list_dimensions,['y','latitude'])
    fc_raster = rasterize(iterable, transform=aff,
                          out_shape=(dataset.sizes[ydim], dataset.sizes[xdim]),
                          dtype='float64', fill=np.nan)
    return fc_raster


def train_object_to_feature(x, crs=None):
    """Convert a Django object, part of a QuerySet, to a geojson like feature

    The feature contains a single ``property`` called ``class`` that corresponds to
    the unique id of the ``madmex_tag`` table.
    The feature is optionally reprojected to a different CRS

    Args:
        x (django QuerySet): QuerySet returned by sending a query to the database
        crs (int or str): CRS (WKT, proj4 or SRID code). See django gis transform for
            more information

    Return:
        list: A feature collection
    """
    attr = {'class': x.interpret_tag.id}
    if crs is None:
        geometry = json.loads(x.train_object.the_geom.geojson)
    else:
        geometry = json.loads(x.train_object.the_geom.transform(crs, clone=True).geojson)
    feature = {
        "type": "Feature",
        "geometry": geometry,
        "properties": attr
    }
    return feature


def predict_object_to_feature(x, crs=None):
    """Convert a PredictObject to a feature

    This function is often meant to be called in a list comprehension whose iterator
    is a django QuerySet.
    The feature has a single attribute corresponding to the database object id

    Args:
        x (PredictObject): Object extracted from the database
        crs (str): proj4 string to reproject to. Can be extrated from a geoarray using
            ``geoarray.crs._crs.ExportToProj4()``. Default to None in which case no
            reprojection is performed. Data in the database must be stored in 4326 crs

    Return:
        dict: A geojson like feature
    """
    geometry = json.loads(x.the_geom.geojson)
    feature = {'type': 'feature',
               'geometry': geometry,
               'properties': {'id': x.id}}
    if crs is not None:
        feature = feature_transform(feature, crs)
    return feature
