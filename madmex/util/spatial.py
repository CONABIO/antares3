from pyproj import Proj, transform

import copy


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
    crs_in = Proj(crs_in)
    crs_out = Proj(crs_out)
    feature_out = copy.deepcopy(feature)
    new_coords = []
    for ring in feature['geometry']['coordinates']:
        x2, y2 = transform(crs_in, crs_out, *zip(*ring))
        new_coords.append(list(zip(x2, y2)))
    feature_out['geometry']['coordinates'] = new_coords
    return feature_out


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
    geom_out = copy.deepcopy(geometry)
    new_coords = []
    for ring in geometry['coordinates']:
        x2, y2 = transform(crs_in, crs_out, *zip(*ring))
        new_coords.append(list(zip(x2, y2)))
    geom_out['coordinates'] = new_coords
    return geom_out


def get_geom_ul(geometry):
    """Given a geojson like geometry, returns its top left coordinates

    Copied from https://gis.stackexchange.com/a/90554/17409

    Args:
        geometry (dict): The geometry part of a geojson like feature

    Return:
        tuple: top left corner coordinates in (x, y) or (long, lat) order
    """
    def explode(geom):
        for e in coords:
            if isinstance(e, (float, int, long)):
                yield coords
                break
            else:
                for f in explode(e):
                    yield f

    x, y = zip(*list(explode(geometry['coordinates'])))
    return (min(x), max(y))










