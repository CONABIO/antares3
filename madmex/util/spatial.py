from pyproj import Proj, transform

import copy


def feature_transform(feature, crs_in, crs_out):
    """Reproject a feature

    A feature is a dictionary representation of a geojson geometry + attributes

    Args:
        feature (dict): A feature that must contain at least the geometry key
        crs_in (str): proj4 string of the input feature
        crs_out (str): coordinate reference system to project to. In proj4 string
            format

    Return:
        dict: A feature
    """
    crs_in = Proj(crs_in)
    crs_out = Proj(crs_out)
    feature_out = copy.deepcopy(feature)
    new_coords = []
    for ring in feature['geometry']['coordinates']:
        x2, y2 = transform(p_in, p_out, *zip(*ring))
        new_coords.append(zip(x2, y2))
    feature_out['geometry']['coordinates'] = new_coords
    return feature_out
