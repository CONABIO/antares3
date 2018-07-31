import functools
from math import ceil, floor
import itertools
import re

from pyproj import Proj, transform
from shapely import ops
from shapely.geometry import shape, mapping
from affine import Affine
import dask.array as da
import numpy as np


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


def grid_gen(extent, res, size, prefix):
    """Tile generator

    Takes extent, tile size and resolution and returns a generator of
    (shape, transform, filename) tuples

    Args:
        extent (list): List or tuple of extent coordinates in the form
            (xmin, ymin, xmax, ymax)
        res (float): Resolution of the grid to chunk
        size (int): Tile size in number of pixels (nrows == ncols)
        prefix (str): Common prefix to all filenames generated

    yields:
        tuple: Tuple of (shape, affine, filename)
    """
    nrow_full = ceil((extent[3] - extent[1]) / res)
    ncol_full = ceil((extent[2] - extent[0]) / res)
    ul_lat_iter = np.arange(extent[3], extent[1], -(res * size))
    ul_lon_iter = np.arange(extent[0], extent[2], (res * size))
    nrow_iter, ncol_iter = da.zeros((nrow_full, ncol_full), chunks=(size, size)).chunks
    for i, (row_tup, col_tup) in enumerate(itertools.product(zip(ul_lat_iter, nrow_iter),
                                                             zip(ul_lon_iter, ncol_iter))):
        aff = Affine(res, 0, col_tup[0], 0, -res, row_tup[0])
        size = (row_tup[1], col_tup[1])
        yield (size, aff, '%s_%d.tif' % (prefix, i))



