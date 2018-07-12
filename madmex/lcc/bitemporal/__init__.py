"""Bitemporal change detection module"""

import abc
import json

from rasterio import features
from rasterio.crs import CRS as rasterioCRS
from shapely import geometry
from affine import Affine
import numpy as np
from datacube.utils.geometry import CRS, GeoBox
from django.contrib.gis.geos import Polygon
from django.contrib.gis.geos.geometry import GEOSGeometry

from madmex.io.vector_db import from_geobox
from madmex.util.spatial import geometry_transform
from madmex.models import PredictClassification, ChangeObject, ChangeClassification
from madmex.lcc.transform.elliptic import Transform as Elliptic
from madmex.lcc.transform.kapur import Transform as Kapur

# Monkeypatch Django Polygon class to instantiate it using a datacube style geobox
Polygon.from_geobox = from_geobox


class BaseBiChange(metaclass=abc.ABCMeta):
    """
    Parent class implementing generic methods related to change detection results
    handling.
    """
    def __init__(self, array, affine, crs):
        """Parent class to run bi-temporal change detection

        Args:
            array (numpy.array): A 3 dimensional numpy array. Dimention order should
                be (bands, y, x)
            affine (affine.Affine): Affine transform
            crs (str): Proj4 string corresponding to the array's CRS
        """
        self.array = array
        self.affine = affine
        self.crs = crs
        self.change_array = None
        self.algorithm = None


    @classmethod
    def from_geoarray(cls, geoarray, **kwargs):
        """Instantiate class from a geoarray (xarray read with datacube.load)

        Args:
            geoarray (xarray.Dataset): a Dataset with crs and affine attribute. Typically
                coming from a call to Datacube.load or GridWorkflow.load
            **kwargs: Additional arguments. Allow children class to set algorithm specific
                parameters during instantiation
        """
        array = geoarray.squeeze().to_array().values
        affine = Affine(*list(geoarray.affine)[0:6])
        crs = geoarray.crs._crs.ExportToProj4()
        return cls(array=array, affine=affine, crs=crs, **kwargs)


    @property
    def geobox(self):
        """Object geobox

        Returns:
            datacube.utils.geometry.GeoBox
        """
        return GeoBox(width=self.array.shape[2], height=self.array.shape[1],
                      affine=self.affine, crs=CRS(self.crs))


    @abc.abstractmethod
    def _run(self, arr0, arr1):
        """Takes two nd arrays and returns a binary array of change/no change

        When 3D arrays are used, order should be (bands, y, x)

        The only method that needs to be included in children classes. May use
        additional variables taken from children attributes passed during instantiation

        Does not write to any of the class attributes but returns a 2D array,
        uint8 datatype and with zeros and ones only
        """
        pass


    def run(self, other):
        """Run change detection using algorithm defined in _run

        Args:
            other (madmex.lcc.bitemporal.BaseBiChange): Instance of a class inheriting
                from madmex.lcc.bitemporal.BaseBiChange. The data agains which to detect
                changes
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

    @staticmethod
    def threshold_change(diff_image, method, **kwargs):
        """Applies a thresholding method to a continuous difference image

        Takes aan array of difference images and thresholds them to produce discrete
        change/no-change image masks

        Args:
            diff_image (ndarray): a 2D or 3D numpy array consisting
            of difference image bands.

        Returns:
            change_mask (ndarray): a 2D numpy array
            consisting of change (=1) /no-change image masks (=0)
        """
        if method=="Kapur":
            model_spec = Kapur(diff_image, **kwargs)
            change_mask = model_spec.fit_transform(diff_image)
        elif method=="Elliptic":
            model_spec = Elliptic(diff_image, **kwargs)
            change_mask = model_spec.fit_transform(diff_image)

        return change_mask.astype(np.int8)


    def filter_mmu(self, min_area):
        """Filter clumps of pixels smaller than min_area

        Args:
            min_area (float): Minimum size of objects to keep, in the crs of the
                input array.
        """
        # Vectorize (generator of (featue, value) tuples)
        fc = features.shapes(self.change_array,
                             mask=self.change_array,
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
        """Label change array

        Args:
            fc_0 (list): Iterable of (geometry, value) pairs. Corresponds to the
                land cover map anterior to change
            fc_1 (list): Iterable of (geometry, value) pairs. Corresponds to the
                land cover map posterior to change

        Returns:
            list: A list of change geometries with before and after label in the
            form of a tuple (geometry, label_0, label_1)
         """
        # Obtain before and after categorical arrays by rasterizing feature collection and masking
        arr_0 = features.rasterize(shapes=fc_0,
                                   out_shape=self.change_array.shape,
                                   fill=0,
                                   transform=self.affine,
                                   dtype=np.uint8)
        arr_0[self.change_array == 0 ] = 0
        arr_1 = features.rasterize(shapes=fc_1,
                                   out_shape=self.change_array.shape,
                                   fill=0,
                                   transform=self.affine,
                                   dtype=np.uint8)
        arr_1[self.change_array == 0 ] = 0
        # Combine both array
        arr_combined = np.add((arr_0.astype(np.uint16) << 8), arr_1)
        # Vectorize combined array
        fc_change = features.shapes(arr_combined, mask=self.change_array,
                                    transform=self.affine)
        # Generate feature collection with before and after label
        # (generates a list of tuples (feature, label0, label1))
        fc_label = [(x[0], *divmod(x[1], 256)) for x in fc_change]
        return fc_label


    @staticmethod
    def filter_no_change(fc):
        """Filter labeled change polygons that have the same before and after label

        Takes the feature collection output by ``label_change``, filter out elements
        that have the same before and after label, and returns the resulting feature
        collection

        Args:
            fc (list): List of geometries with before and after label in the form
            of a tuple (geometry, label_0, label_1)

        Returns:
            list: A list of change geometries with before and after label in the
            form of a tuple (geometry, label_0, label_1)
        """
        return [x for x in fc if x[1] != x[2]]


    def to_db(self, fc, meta, pre_name, post_name):
        """Write feature collection returned by label_change to the antares3 database

        The geometries of fc are assumed to be in the crs specified in the instance
        attribute ``crs``

        Args:
            fc (list): List of tuples (geometry, tag_id_pre, tag_id_post)
            meta (madmex.models.ChangeInformation): Django model object containing
                change objects meta informations. Often resulting from a call to
                ``get_or_create()``
            pre_name (str): Name of the classification used for assigning anterior
                labels
            post_name (str): Name of the classification used for assigning posterior
                labels

        Returns:
            Function used for its side effect of writing a feature collection to
            the database
        """
        def change_obj_builder(geom, meta, crs_in):
            geom_ll = geometry_transform(geom, '+proj=longlat', crs_in)
            the_geom = GEOSGeometry(json.dumps(geom_ll)).buffer(0)
            return ChangeObject(the_geom, meta)
        # Build list of ChangeObjects
        obj_list = [change_obj_builder(x[0], meta, self.crs) for x in fc]
        # Write ChangeObjects with bulk_create
        ChangeObject.objects.bulk_create(obj_list)
        # Build list of ChangeClassification 
        class_list = [ChangeClassification(pre_name=pre_name,
                                           post_name=post_name,
                                           change_object=x[0],
                                           pre_tag_id=x[1][1],
                                           post_tag_id=x[1][2])
                      for x in zip(obj_list, fc)]
        # Write it with bulk_create
        ChangeClassification.objects.bulk_create(class_list)


    def read_land_cover(self, name):
        """Read the specified land cover map covering the extent of the instance array

        Args:
            name (str): Database classification identifier (see madmex_predictclassification
                table)

        Return:
            list: A list of (geometry, tag_id) tupples in the crs of the instance.
            The list can be passed directly to the label_change method
        """
        poly = Polygon.from_geobox(self.geobox)
        query_set = PredictClassification.objects.filter(predict_object__the_geom__contained=poly,
                                                         name=name).prefetch_related('predict_object', 'tag')
        def to_feature(x, crs):
            geometry = json.loads(x.the_geom.geojson)
            feature = (geometry_transform(geometry, crs), x.tag)
            return feature
        return [to_feature(x, self.crs) for x in query_set]


    def __eq__(self, other):
        """Compare crs, affine and shape between two instance of the class
        """
        crs_0 = rasterioCRS.from_string(self.crs)
        crs_1 = rasterioCRS.from_string(other.crs)
        return (self.affine.almost_equals(other.affine)
                and crs_0 == crs_1
                and self.array.shape == other.array.shape)

