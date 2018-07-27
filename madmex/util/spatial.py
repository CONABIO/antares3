import functools

from pyproj import Proj, transform
from shapely import ops
from shapely.geometry import shape, mapping


def geometry_transform(geometry, crs_out,
                       crs_in="+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs"):
    """Reproject a geometry

    Args:
        geometry (dict): The geometry part of a geojson like feature
        crs_out (str): coordinate reference system to project to. In proj4 string
            format
        crs_in (str): proj4 string of the input feature. Can be omited in which case
            it defaults to 4326

    Return:
        dict: A geometry
    """
    crs_in = Proj(crs_in)
    crs_out = Proj(crs_out)
    project = functools.partial(transform, crs_in, crs_out)
    geom_in_s = shape(geometry)
    geom_out_s = ops.transform(project, geom_in_s)
    return mapping(geom_out_s)


def feature_transform(feature, crs_out,
                      crs_in="+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs"):
    """Reproject a feature

    A feature is a dictionary representation of a geojson geometry + attributes

    Args:
        feature (dict): A feature that must contain at least the geometry key
        crs_out (str): coordinate reference system to project to. In proj4 string
            format
        crs_in (str): proj4 string of the input feature. Can be omited in which case
            it defaults to 4326

    Return:
        dict: A feature
    """
    geom_proj = geometry_transform(feature['geometry'],
                                   crs_out=crs_out,
                                   crs_in=crs_in)
    feature['geometry'] = geom_proj
    return feature


def get_geom_bbox(geometry):
    """Given a geojson like geometry, returns its bounding box as a tuple of coordinates

    Copied from https://gis.stackexchange.com/a/90554/17409

    Args:
        geometry (dict): The geometry part of a geojson like feature

    Return:
        tuple: bounding box coordinates in (xmin, ymin, xmax, ymax) order
    """
    def explode(coords):
        for e in coords:
            if isinstance(e, (float, int)):
                yield coords
                break
            else:
                for f in explode(e):
                    yield f

    x, y = zip(*list(explode(geometry['coordinates'])))
    return (min(x), min(y), max(x), max(y))










