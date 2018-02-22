import json

def rasterize_xarray(fc, dataset):
    """
    """
    pass


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
