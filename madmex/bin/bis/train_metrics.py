"""
Library of goodnes metrics that will be run during training.

Each function will be called with one segment and one ground truth polygon.
Each function as named here will be a column heading in stats csv file.
Helper functions start with underbar and are not ready by train.py

Published by Berkeley Environmental Technology International, LLC
Copyright (c) 2012 James Scarborough - All rights reserved

For the GDAL/OGR copyright notice and license please see:
  http://svn.osgeo.org/gdal/trunk/gdal/LICENSE.TXT
"""
from osgeo import ogr
from osgeo.ogr import CreateGeometryFromWkt as _wkt

def Relevant(region, truth, threshold=0.5):
    """Compute if this region and truth shapes are relevant to each other.
    
    Imported explicitly and used by train module.
    
    Cite: Clinton 2010, pg 290
    
    >>> Relevant(_wkt('POLYGON ((0 0,1 0,1 1,0 1,0 0))'),
    ...          _wkt('POLYGON ((0 0,1 0,1 1,0 1,0 0))'))
    True
    >>> Relevant(_wkt('POLYGON ((10 10,11 10,11 11,10 11,10 10))'),
    ...          _wkt('POLYGON ((0 0,1 0,1 1,0 1,0 0))'))
    False
    """
    intersection = _intersect(region, truth)
    if _not(intersection):
        "Triage"
        return False
    return (_centerin(truth, region) or
            _centerin(region, truth) or
            _area(intersection) / _area(region) > threshold or
            _area(intersection) / _area(truth) > threshold)

def _not(geometry):
    """Boolean test if the geometry is null/empty.
    
    >>> g = _intersect(_wkt('POLYGON ((10 10,11 10,11 11,10 11,10 10))'),
    ...                _wkt('POLYGON ((0 0,1 0,1 1,0 1,0 0))'))
    >>> g.ExportToWkt(), g.Area(), g.IsEmpty() # No intersection
    ('GEOMETRYCOLLECTION EMPTY', 0.0, True)
    >>> _not(g)
    True
    """
    return geometry.IsEmpty()

def _area(geometry):
    """Return the area of the shape.
    
    >>> _area(_wkt('POLYGON ((0 0,1 0,1 1,0 1,0 0))'))
    1.0
    """
    return geometry.Area()

def _intersect(geometry1, geometry2):
    """Return the spatial intersection of two shapes.
    
    >>> g = _intersect(_wkt('POLYGON ((0 0,1 0,1 1,0 1,0 0))'),
    ...                _wkt('POLYGON ((0 0,1 0,1 1,0 1,0 0))'))
    >>> g.ExportToWkt()
    'POLYGON ((1 0,0 0,0 1,1 1,1 0))'
    >>> g = _intersect(_wkt('POLYGON ((10 10,11 10,11 11,10 11,10 10))'),
    ...                _wkt('POLYGON ((0 0,1 0,1 1,0 1,0 0))'))
    >>> g.IsEmpty() # No intersection
    True
    """
    return geometry1.Intersection(geometry2)

def _centerin(inner, outer):
    """True if the center of inner is inside the border of outer.
    
    >>> _centerin(_wkt('POLYGON ((0 0,1 0,1 1,0 1,0 0))'),
    ...           _wkt('POLYGON ((0 0,1 0,1 1,0 1,0 0))'))
    True
    >>> _centerin(_wkt('POLYGON ((10 10,11 10,11 11,10 11,10 10))'),
    ...           _wkt('POLYGON ((0 0,1 0,1 1,0 1,0 0))'))
    False
    """
    return inner.Centroid().Within(outer)

def underseg(region, truth):
    """Compute how much the region is an undersegmentation of the truth shape.
    
    Cite: Clinton 2010, pg 291 (corrected)
    
    >>> underseg(_wkt('POLYGON ((0 0,1 0,1 1,0 1,0 0))'),
    ...          _wkt('POLYGON ((0 0,1 0,1 1,0 1,0 0))'))
    0.0
    >>> underseg(_wkt('POLYGON ((0 0,1 0,1 1,0 1,0 0))'),
    ...          _wkt('POLYGON ((0.5 0.5,1.5 0.5,1.5 1.5,0.5 1.5,0.5 0.5))'))
    0.75
    """
    return 1 - _area(_intersect(region, truth)) / _area(region)

def overseg(region, truth):
    """Compute how much the region is an oversegmentation of the truth shape.
    
    Cite: Clinton 2010, pg 291
    
    >>> overseg(_wkt('POLYGON ((0 0,1 0,1 1,0 1,0 0))'),
    ...         _wkt('POLYGON ((0 0,1 0,1 1,0 1,0 0))'))
    0.0
    >>> overseg(_wkt('POLYGON ((0 0,1 0,1 1,0 1,0 0))'),
    ...         _wkt('POLYGON ((0.5 0.5,1.5 0.5,1.5 1.5,0.5 1.5,0.5 0.5))'))
    0.75
    """
    return 1 - _area(_intersect(region, truth)) / _area(truth)

def dmetric(region, truth):
    """Compute as 'distance' from perfect under and over segmetation.
    
    Cite: Clinton 2010, pg 291
    
    >>> dmetric(_wkt('POLYGON ((0 0,1 0,1 1,0 1,0 0))'),
    ...         _wkt('POLYGON ((0 0,1 0,1 1,0 1,0 0))'))
    0.0
    """
    return (overseg(region, truth) ** 2 + underseg(region, truth) ** 2) ** 0.5


if __name__ == '__main__':
    "Run Python standard module doctest which executes the >>> lines."
    import doctest
    doctest.testmod()
