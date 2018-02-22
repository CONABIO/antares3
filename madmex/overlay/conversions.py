import json
from affine import Affine
from rasterio.features import rasterize

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
    fc_raster = rasterize(iterable, transform=aff,
                          out_shape=(dataset.sizes['y'], dataset.sizes['x']))
    return fc_raster

def rasterize_numpy(fc, arr, transform, crs):
    """
    """
    pass


def vectorize_numpy(x, transform):
    """Trans
    """
    pass

def querySet_to_fc(x, crs=None):
    """Convert a QuerySet as returned by sending a spatial query to the database and
    converts it to a feature collection

    Args:
        x (django QuerySet): QuerySet returned by sending a query to the database
        crs (int or str): CRS (WKT, proj4 or SRID code). See django gis transform for
            more information

    Return:
        list: A feature collection
    """
    attr = x.training_tags.values_list()
    # TODO: I have no idea why attr is made of tupples of 3 or what the first element
    # of each tuple correspond to (loic)
    attr = [a[1:3] for a in attr]
    if crs is None:
        geometry = json.loads(x.the_geom.geojson)
    else:
        geometry = json.loads(x.the_geom.transform(crs, clone=True).geojson)
    feature = {
        "type": "Feature",
        "geometry": geometry,
        "properties": dict(attr)
    }
    return feature
