"""Bitemporal change detection module"""

import abc

from rasterio import features
from rasterio.crs import CRS
from shapely import geometry
from affine import Affine
import numpy as np


class BaseBiChange(metaclass=abc.ABCMeta):
    """
    Parent class imlementing generic methods related to change detection results
    handling.
    """
    def __init__(self, array, affine, crs):
        self.array = array
        self.affine = affine
        self.crs = crs
        self.change_array = None
        self.labelled_array = None
        self.algorithm = None


    @classmethod
    def from_geoarray(cls, geoarray, **kwargs):
        pass


    @abc.abstractmethod
    def _run(self, arr0, arr1):
        """Takes two nd arrays and returns a binary array of change/no change

        The only method that needs to be included in children classes. May use
        additional variables taken from children attributes passed during instantiation

        Does not write to any of the class attributes but returns a 2D array,
        unint8 datatype and with zeros and ones only
        """
        pass


    def run(self, other):
        """Run change detection using algorithm defined in _run
        """
        if self != other:
            raise AssertionError('Object equality check failed')
        change_array = self._run(arr0=self.array, arr1=other.array)
        # Check array shape and datatype
        if change_array.dtype != np.uint8:
            raise ValueError('Children _run method must return an array of uint8 datatype')
        if len(change_array.shape) != 2:
            raise ValueError('Children _run method must return a 2D np.array')
        self.change_array = change_array



    def filter_mmu(self, min_area):
        """Filter clumps of pixels smaller than min_area

        Args:
            min_area (float): Minimum size of objects to keep, in the crs of the
                input array.
        """
        # Vectorize (generator of (featue, value) tuples)
        fc = features.shapes(self.array,
                             mask=self.array,
                             transform=self.affine)
        # Filter by area
        fc_sub = [x[0] for x in fc if geometry.shape(x[0]).area >= min_area]
        # Rasterize
        out_arr = features.rasterize(shapes=fc_sub,
                                     out_shape=self.change_array.shape,
                                     fill=0,
                                     transform=self.affine,
                                     default_value=1,
                                     dtype=np.uint8)
        self.change_array = out_arr


    def label_change(self, fc_0, fc_1):
        pass


    def __eq__(self, other):
        """Compare crs, affine and shape between two instance of the class
        """
        # Compare affine
        if not self.affine.almost_equals(other.affine):
            return False
        # Compare crs
        crs_0 = CRS.from_string(self.crs)
        crs_1 = CRS.from_string(other.crs)
        if crs_0 != crs_1:
            return False
        # compare shape of arrays
        if self.array.shape != other.array.shape:
            return False
        return True

