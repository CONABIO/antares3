"""
Library of vector functions that will be run during stats computation.

Each function will be called per polygon.
Each function as named here will be a column heading in stats csv file.
See caching functions at the top of this module.

data = {'geometry': g, 'area': a, 'perimeter': p, 'bperim': b}

Published by Berkeley Environmental Technology International, LLC
Copyright (c) 2012 James Scarborough - All rights reserved
"""
import math
from osgeo import ogr

def _area(geometry):
    """Compute the area of the polygon.
    
    >>> g = ogr.CreateGeometryFromWkt('POLYGON ((0 0,1 0,1 1,0 1,0 0))')
    >>> _area(g)
    1.0
    """
    return geometry.Area()

def _perimeter(geometry):#### with holes?
    """Compute the perimeter of the polygon.
    
    >>> g = ogr.CreateGeometryFromWkt('POLYGON ((0 0,1 0,1 1,0 1,0 0))')
    >>> _perimeter(g)
    4.0
    """
    return ogr.ForceToMultiLineString(geometry).Length()

def _bperim(geometry):
    """Return perimeter of bounding box/envelope of the polygon.
    
    >>> _bperim(ogr.CreateGeometryFromWkt('POLYGON ((0 0,1 0,1 1,0 1,0 0))'))
    4.0
    >>> _bperim(ogr.CreateGeometryFromWkt(
    ...   'POLYGON ((0 0,3 0,3 3,0 3,0 0), (1 1,2 1,2 2,1 2,1 1))')) # hole
    12.0
    >>> _bperim(ogr.CreateGeometryFromWkt(
    ...   'POLYGON ((0 0,3 0,3 3,2 3,2 2, 1 2,1 3,0 3,0 0))')) # notched
    12.0
    """
    minx, maxx, miny, maxy = geometry.GetEnvelope()
    return 2 * (maxx - minx + maxy - miny)

def _cache(function):
    """Compute area and perimeter with OGR and cache for other functions.
    
    >>> _cache(None) #doctest:+ELLIPSIS
    <function decorator at 0x...>
    
    >>> g = ogr.CreateGeometryFromWkt('POLYGON ((0 0,1 0,1 1,0 1,0 0))')
    >>> data = {'geometry': g, 'area': None}
    >>> area(data)
    1.0
    >>> data #doctest:+ELLIPSIS
    {'geometry': <osgeo.ogr.Geometry; ...>, 'perimeter': 4.0, 'bperim': 4.0, 'area': 1.0}
    >>> area(data)
    1.0
    """
    todo = [('area', _area), ('perimeter', _perimeter), ('bperim', _bperim)]
    def decorator(data):
        for lookup, f in todo:
            if data.get(lookup, None) is None:
                data[lookup] = f(data['geometry'])
        return function(data)
    return decorator  


def _tests():
    """Provide doctests and user code here.
    
    Module doctest won't run tests in decorated functions.
    
    >>> g = ogr.CreateGeometryFromWkt('POLYGON ((0 0,1 0,1 1,0 1,0 0))')
    >>> data = {'geometry': g}
    >>> area(data)
    1.0
    >>> data #doctest:+ELLIPSIS +NORMALIZE_WHITESPACE
    {'geometry': <osgeo.ogr.Geometry; ...>, 'perimeter': 4.0, 'bperim': 4.0,
     'area': 1.0}
    >>> perimeter(data)
    4.0
    >>> bperim(data)
    4.0
    
    >>> compact(data)
    4.0
    >>> smooth(data)
    1.0
    >>> para(data)
    4.0
    
    >>> shape({'area': math.pi, 'perimeter': 2*math.pi, 'bperim': 0}) # circle
    1.0
    >>> shape({'area': 1, 'perimeter': 4, 'bperim': 0}) # square
    0.78539816339744828
    
    >>> math.log(math.e) # Confirm math.log() is natural log
    1.0
    >>> frac({'area': 4, 'perimeter': 8, 'bperim': 0}) # square
    1.0
    >>> frac({'area': 9, 'perimeter': 12, 'bperim': 0}) # square
    1.0
    >>> frac({'area': 4, 'perimeter': 10, 'bperim': 0}) # wiggly perimeter
    1.3219280948873624
    >>> frac({'area': math.pi, 'perimeter': 2 * math.pi, 'bperim': 0}) # circle
    0.78897687720343956
    >>> frac({'area': 1, 'perimeter': 4, 'bperim': 0}) # no crash on 1.0 area
    1.0
    >>> frac({'area': 0.1, 'perimeter': 0.4, 'bperim': 0}) # floor at 1.0
    1.0
    >>> frac({'area': 0.962890625, 'perimeter': 4.551999999, 'bperim': 0})
    1.0
    """

@_cache
def area(data):
    "Return the area of the polygon."
    return data['area']

@_cache
def perimeter(data):
    "Return the perimeter of the polygon."
    return data['perimeter']

@_cache
def bperim(data):
    "Return perimeter of bounding box/envelope of the polygon."
    return data['bperim']

@_cache
def para(data):
    "Return the perimeter-area ratio of the polygon."
    return data['perimeter'] / data['area']

@_cache
def compact(data):
    """Calculate compactness metric per BIS segmentation parameter.
    
    But perimeters here not normalized to raster perim, different from algo.
    """
    return data['area'] * data['bperim'] / math.sqrt(data['area'])

@_cache
def smooth(data):
    """Calculate smoothness metric per BIS segmentation parameter.
    """
    return data['area'] * data['bperim'] / data['perimeter']

@_cache
def shape(data):
    """Calculate 'circularity ratio' metric for a polygon.
    
    http://en.wikipedia.org/wiki/Compactness_measure_of_a_shape
    Different from FRAGSTATS SHAPE P8 which is raster/square based. 
    """
    return 4 * math.pi * data['area'] / math.pow(data['perimeter'], 2)

@_cache
def frac(data):
    """Calculate fractal dimension index (FRAGSTATS P9).
    
    frac = 2 * ln(perim) / ln(area)
    Adjust perimeter (0.25) to correct for raster bias, per FRAGSTATS doc.
    Return 1.0 if perimeter or area parameter < 1.0, rather than ZeroDivision
    or bogus value less than 1.0.
    """
    area, perimeter = data['area'], data['perimeter'] * 0.25
    if area <= 1 or perimeter < 1:
        return 1.0
    else:
        return 2 * math.log(perimeter) / math.log(area)


if __name__ == '__main__':
    "Run Python standard module doctest which executes the >>> lines."
    import doctest
    doctest.testmod()
