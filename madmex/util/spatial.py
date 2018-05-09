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
