import rasterio
import numpy as np
import os
import json
import hashlib
from datetime import datetime
import gc
import datacube
from datacube.api import GridWorkflow
from datacube.utils.geometry import Geometry, CRS
from importlib import import_module
from madmex.util.xarray import to_float
from madmex.util import chunk
from madmex.io.vector_db import VectorDb, load_segmentation_from_dataset
from madmex.overlay.extractions import zonal_stats_xarray
from madmex.modeling import BaseModel
from madmex.settings import TEMP_DIR
from madmex.models import Region, Country, Model, PredictClassification, PredictObject
from datacube.model import GridSpec
from operator import itemgetter
from shapely.geometry import mapping, shape
from madmex.util.spatial import geometry_transform, feature_transform
import fiona
from fiona.crs import from_string
import sys
from madmex.loggerwriter import LoggerWriter
import logging
from django.contrib.gis.geos import Polygon
from affine import Affine
from rasterio.features import rasterize

logging.basicConfig(format="%(asctime)s - %(name)s - %(module)s %(funcName)s: %(message)s")
logger = logging.getLogger(__name__)

stdl = LoggerWriter(logger.debug)
sys.stdout = stdl
stdl = LoggerWriter(logger.error)
sys.stderr = stdl
"""
The wrapper module gathers functions that are typically called by
command lines
"""

def predict_pixel_tile(tile, model_id, outdir=None):
    """Run a model in prediction mode and generates a raster file written to disk

    Meant to be called within a dask.distributed.Cluster.map() over a list of tiles
    returned by GridWorkflow.list_cells
    Called in model_predict command line

    Args:
        tile: Datacube tile as returned by GridWorkflow.list_cells()
        model_id (str): Database identifier of trained model to use. The model
            must have been trained against a numeric dependent variable.
            (See --encode flag in model_fit command line)
        outdir (str): Directory where output data should be written. Only makes sense
            when generating unregistered geotiffs. The directory must already exist,
            it is therefore a good idea to generate it in the command line function
            before sending the tasks

    Return:
        str: The function is used for its side effect of generating a predicted
        array and writting it to a raster file (GeoTiff or NetCDF). OPtionally the file is registered as a storage unit in the datacube database.
    """
    # TODO: How to handle data type. When ran in classification mode int16 would always
    # be fine, but this function could potentially also be ran in regression mode
    try:
        # Load model class corresponding to the right model
        trained_model = BaseModel.from_db(model_id)
        try:
            # Avoid opening several threads in each process
            trained_model.model.n_jobs = 1
        except Exception as e:
            pass
        # Generate filename
        filename = os.path.join(outdir, 'prediction_%s_%d_%d.tif' % (model_id, tile[0][0], tile[0][1]))
        # Load tile
        xr_dataset = GridWorkflow.load(tile[1])
        # Convert it to float?
        # xr_dataset = xr_dataset.apply(func=to_float, keep_attrs=True)
        # Transform file to nd array
        arr_3d = xr_dataset.to_array().squeeze().values
        arr_3d = np.moveaxis(arr_3d, 0, 2)
        shape_2d = (arr_3d.shape[0] * arr_3d.shape[1], arr_3d.shape[2])
        arr_2d = arr_3d.reshape(shape_2d)
        # predict
        predicted_array = trained_model.predict(arr_2d)
        # Reshape back to 2D
        predicted_array = predicted_array.reshape((arr_3d.shape[0], arr_3d.shape[1]))
        # Write array to geotiff
        rasterio_meta = {'width': predicted_array.shape[1],
                         'height': predicted_array.shape[0],
                         'affine': xr_dataset.affine,
                         'crs': xr_dataset.crs.crs_str,
                         'count': 1,
                         'dtype': 'int16',
                         'compress': 'lzw',
                         'driver': 'GTiff'}
        with rasterio.open(filename, 'w', **rasterio_meta) as dst:
            dst.write(predicted_array.astype('int16'), 1)
        # Coerce back to xarray with all spatial parameters properly set
        # xr_out = xr_dataset.drop(xr_dataset.data_vars)
        # Build output filename
        # xr_out['predicted'] = (('y', 'x'), predicted_array)
        # Write to filename
        # write_geotiff(filename=filename, dataset=xr_out)
        # Register to database
        return filename
    except Exception as e:
        print(e)
        return None


def extract_tile_db(tile, sp, training_set, sample):
    """Function to extract data under training geometries for a given tile

    Meant to be called within a dask.distributed.Cluster.map() over a list of tiles
    returned by GridWorkflow.list_cells
    Called in model_fit command line

    Args:
        tile: Datacube tile as returned by GridWorkflow.list_cells()
        sp: Spatial aggregation function
        training_set (str): Training data identifier (training_set field)
        sample (float): Proportion of training data to sample from the complete set

    Returns:
        A list of predictors and target values arrays
    """
    try:
        # Load tile as Dataset
        xr_dataset = GridWorkflow.load(tile[1])
        # Query the training geometries fitting into the extent of xr_dataset
        db = VectorDb()
        fc = db.load_training_from_dataset(xr_dataset,
                                           training_set=training_set,
                                           sample=sample)
        # fc is a feature collection with one property (class)
        # Overlay geometries and xr_dataset and perform extraction combined with spatial aggregation
        extract = zonal_stats_xarray(xr_dataset, fc, field='class', aggregation=sp)
        fc = None
        gc.collect()
        # Return the extracted array (or a list of two arrays?)
        return extract
    except Exception as e:
        print(e)
        return [None, None]


def gwf_query(product, lat=None, long=None, region=None, begin=None, end=None,
              view=True, resolution=None, tilesize=None, origin=None, proj4=None):
    """Run a spatial query on a datacube product using either coordinates or a region name

    Wrapper function to call at the begining of nearly all spatial processing command lines

    Args:
        product (str): Name of an ingested datacube product. The product to query
        lat (tuple): OPtional. For coordinate based spatial query. Tuple of min and max
            latitudes in decimal degreees.
        long (tuple): OPtional. For coordinate based spatial query. Tuple of min and max
            longitudes in decimal degreees.
        region (str): Optional name of a region or country whose geometry is present in the database
            region  or country table. Overrides lat and long when present (not None).
            Countries must be queried using ISO code (e.g.: 'MEX' for Mexico)
        begin (str): Date string in the form '%Y-%m-%d'. For temporally bounded queries
        end (str): Date string in the form '%Y-%m-%d'. For temporally bounded queries
        view (bool): Returns a view instead of the dictionary returned by ``GridWorkflow.list_cells``.
            Useful when the output is be used directly as an iterable (e.g. in ``distributed.map``)
            Default to True
        resolution (tuple): Optional. For creating a GridSpec regular spatial grid for ``GridWorkflow`` initialization.
        tilesize (tuple): Optional. For creating a GridSpec regular spatial grid for ``GridWorkflow`` initialization.
        origin (tuple): Optional. For creating a GridSpec regular spatial grid for ``GridWorkflow`` initialization.
        proj4 (str): Optional. For creating a GridSpec regular spatial grid for ``GridWorkflow`` initialization.

    Returns:
        dict or view: Dictionary (view) of Tile index, Tile key value pair

    Example:

        >>> from madmex.wrappers import gwf_query

        >>> # Using region name, time unbounded
        >>> tiles_list = gwf_query(product='ls8_espa_mexico', region='Jalisco')
        >>> # Using region name, time windowed
        >>> tiles_list = gwf_query(product='ls8_espa_mexico', region='Jalisco',
        ...                        begin = '2017-01-01', end='2017-03-31')
        >>> # Using lat long box, time windowed
        >>> tiles_list = gwf_query(product='ls8_espa_mexico', lat=[19, 22], long=[-104, -102],
        ...                        begin = '2017-01-01', end='2017-03-31')
        >>> tiles_list = gwf_query(resolution= (-10, 10), origin = (2426720, 977160), tilesize = (100020,100020)
        ...                        proj4 = '+proj=lcc +lat_1=17.5 +lat_2=29.5 +lat_0=12 +lon_0=-102 +x_0=2500000 +y_0=0 +a=6378137 +b=6378136.027241431 +units=m +no_defs')
    """
    query_params = {'product': product}
    if region is not None:
       # Query database and build a datacube.utils.Geometry(geopolygon)
       try:
           query_set = Country.objects.get(name=region)
       except Country.DoesNotExist:
           query_set = Region.objects.get(name=region)
       region_json = json.loads(query_set.the_geom.geojson)
       crs = CRS('EPSG:%d' % query_set.the_geom.srid)
       geom = Geometry(region_json, crs)
       query_params.update(geopolygon=geom)
    elif lat is not None and long is not None:
        query_params.update(x=long, y=lat)
    else:
        raise ValueError('Either a region name or a lat and long must be provided')

    if begin is not None and end is not None:
        begin = datetime.strptime(begin, "%Y-%m-%d")
        end = datetime.strptime(end, "%Y-%m-%d")
        query_params.update(time=(begin, end))

    # GridWorkflow object
    dc = datacube.Datacube()
    if resolution is not None and tilesize is not None and origin is not None and proj4 is not None:
        crs = CRS(proj4)
        gs = GridSpec(crs=crs, tile_size = tilesize, resolution = resolution, origin = origin)
        gwf = GridWorkflow(dc.index, grid_spec = gs)
    else:
        gwf = GridWorkflow(dc.index, product=product)
    tile_dict = gwf.list_cells(**query_params)
    # Iterable (dictionary view (analog to list of tuples))
    if view:
        tile_dict = tile_dict.items()
    return tile_dict

def segment(tile, algorithm, segmentation_meta,
            band_list, extra_args):
    """Run a segmentation algorithm on tile

    Meant to be called within a dask.distributed.Cluster.map() over a list of tiles
    returned by GridWorkflow.list_cells
    Called in segment command line

    Args:
        tile: Datacube tile as returned by GridWorkflow.list_cells()
        algorithm (str): Name of the segmentation algorithm to apply
        segmentation_meta (madmex.models.SegmentationInformation.object): Django object
            relating to every segmentation object generated by this run
        band_list (list): Optional subset of bands of the product to use for running the segmentation.
        extra_args (dict): dictionary of additional arguments
    """
    # Load segment class
    try:
        module = import_module('madmex.segmentation.%s' % algorithm)
        Segmentation = module.Segmentation
    except ImportError as e:
        raise ValueError('Invalid model argument')

    try:
        # Load tile
        geoarray = GridWorkflow.load(tile[1], measurements=band_list)
        dataset_name = segmentation_meta.datasource + '_%d_%d_' % (tile[0][0], tile[0][1]) + segmentation_meta.datasource_year
        hash = hashlib.md5(dataset_name.encode('utf-8')).hexdigest()[0:6]
        name_file = hash + '_' + dataset_name
        path = os.path.join(TEMP_DIR, 'segmentation_results')
        if not os.path.exists(path):
            os.makedirs(path)
        seg = Segmentation.from_geoarray(geoarray, **extra_args)
        seg.segment()
        # Try deallocating input array
        seg.polygonize(crs_out=None)
        seg.to_filesystem(path,name_file)
        seg.to_db(name_file, segmentation_meta)
        seg.to_bucket(path, name_file)
        seg.array = None
        geoarray = None
        gc.collect()
        return True
    except Exception as e:
        print(e)
        return False

def predict_object(tile, model_name, segmentation_name,
                   categorical_variables, aggregation, name):
    """Run a trained classifier in prediction mode on all objects intersection with a tile

    Args:
        tile: Datacube tile as returned by GridWorkflow.list_cells()
        model_name (str): Name under which the trained model is referenced in the
            database
        segmentation_name (str): Name of the segmentation to use
        categorical_variables (list): List of strings corresponding to categorical
            features.
        aggregation (str): Spatial aggregation method to use
    """
    try:
        # Load geoarray and feature collection
        geoarray = GridWorkflow.load(tile[1])
        poly = Polygon.from_ewkt(geoarray.geobox.extent.wkt)
        query_set = PredictObject.objects.filter(the_geom__contained=poly,
                                                 segmentation_information__name=segmentation_name)
        seg_id = query_set[0].id
        path = query_set[0].path
        with fiona.open(path) as src:
            X, y = zonal_stats_xarray(dataset = geoarray, fc=src, field='id',
                                          categorical_variables=categorical_variables,
                                          aggregation=aggregation)
            # Deallocate geoarray and feature collection
            geoarray = None
            fc = None
            gc.collect()
            # Load model
            PredModel = BaseModel.from_db(model_name)
            model_id = Model.objects.get(name=model_name).id
            try:
                # Avoid opening several threads in each process
                PredModel.model.n_jobs = 1
            except Exception as e:
                pass
            # Run prediction
            y_pred = PredModel.predict(X)
            y_conf = PredModel.predict_confidence(X)
            # Deallocate arrays of extracted values and model
            X = None
            PredModel = None
            gc.collect()
            # Build list of PredictClassification objects
            def predict_object_builder(i, pred, conf):
                return PredictClassification(model_id=model_id, predict_object_id=seg_id,
                                             tag_id=pred, name=name, confidence=conf, features_id=i)
            # Write labels to database combining chunking and bulk_create
            for sub_zip in chunk(zip(y, y_pred, y_conf), 10000):
                obj_list = [predict_object_builder(i,pred,conf) for i, pred, conf in sub_zip]
                PredictClassification.objects.bulk_create(obj_list)
                obj_list = None
            gc.collect()
            y = None
            y_pred = None
            y_conf = None
            gc.collect()
            return True
    except Exception as e:
        print('Prediction failed because: %s' % e)
        logger.exception('Pred failed because: %s' % e)
        return False

def write_predict_result_to_vector(id, predict_name, geometry, path_destiny,
                                   driver='ESRI Shapefile', layer=None, proj4=None):
    """Retrieve classification results in db: label and confidence per polygon. Add this information to
    to segmentation file via fiona's functionality and write result to path_destiny (by this time only writes to 
    file system are supported)
    
    This function uses dask.distributed.Cluster.map() over a list of id's of segmentation files already registered
    in db PredictObject table related to name of prediction file and generated by arguments passed in command line.
    Works by datacube tile.
    
    Args:
        id (int): id of segmentation file registered in PredictObject table.
        predict_name (str): Name of predict file registered in PredictObject table.
        geometry (geom): Geometry of a region in a geojson-format
        pat_destiny (str): Path that will hold results. Only writes to file system are supported now.
        driver (str): OGR driver to use for writting the data to file. Defaults to ESRI Shapefile
        layer (str): Name of the layer (only for drivers that support multi-layer files)
        proj4 (str): Optional. crs projection in string format.
    
    """
    seg = PredictObject.objects.filter(id=id)
    path = seg[0].path
    if proj4 is not None:
        geometry_proj = geometry_transform(geometry,proj4)
    else:
        geometry_proj = geometry_transform(geometry, '+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
    shape_region=shape(geometry_proj)
    geom_dc_tile = shape_region.intersection(shape(json.loads(seg[0].the_geom.geojson)))
    segmentation_name_classified = os.path.basename(path).split('.')[0] + '_classified'
    with fiona.open(path) as src:
        if proj4 is not None:
            fc = (feature_transform(x, crs_out=proj4, crs_in=proj4) for x in src)
            crs = from_string(proj4)
        else:
            fc = (feature_transform(x,
                                    crs_out='+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs') for x in src)
            crs = from_string('+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
            
        pred_objects_sorted = PredictClassification.objects.filter(name=predict_name,
                                                                   predict_object_id=id).prefetch_related('tag').order_by('features_id')
        fc_pred=[(x['properties']['id'], x['geometry']) for x in fc]
        fc = None
        fc_pred_sorted = sorted(fc_pred, key=itemgetter(0))
        fc_pred = [(x[0][1], x[1].tag.numeric_code,
                    x[1].tag.value,
                    x[1].confidence) for x in zip(fc_pred_sorted, pred_objects_sorted)]
        fc_pred_sorted = None
        pred_objects_sorted = None
        fc_schema = {'geometry': 'Polygon',
                     'properties': {'code': 'int',
                                    'class':'str',
                                    'confidence': 'float'}}
        filename = path_destiny + '/' + segmentation_name_classified + '.shp'
        with fiona.open(filename, 'w',
                        encoding='utf-8',
                        driver=driver,
                        layer=layer,
                        crs=crs,
                        schema=fc_schema) as dst:
            [dst.write({'geometry': mapping(shape(feat[0]).intersection(geom_dc_tile)),
                        'properties':{'code': feat[1],
                                      'class': feat[2],
                                      'confidence': feat[3]}}) for feat in fc_pred if shape(feat[0]).intersects(geom_dc_tile)]
        fc_pred = None     
    return filename


def write_predict_result_to_raster(id, predict_name, geometry, resolution,
                                   path_destiny, proj4=None):
    """Retrieve classification results in db: label per polygon. Add this information to
    to segmentation file via fiona's functionality and write result to path_destiny (by this time only writes to 
    file system are supported)
    
    This function uses dask.distributed.Cluster.map() over a list of id's of segmentation files already registered
    in db PredictObject table related to name of prediction file and generated by arguments passed in command line.
    Works by datacube tile.
    
    Args:
        id (int): id of segmentation file registered in PredictObject table.
        predict_name (str): Name of predict file registered in PredictObject table.
        geometry (geom): Geometry of a region in a geojson-format
        resolution (int): Resolution of the output raster in crs units. (See the proj4 argument to define a projection, otherwise will be in longlat and resolution has to be specified in degrees)
        pat_destiny (str): Path that will hold results. Only writes to file system are supported now.
        proj4 (str): Optional. crs projection in string format.
    
    """
    seg = PredictObject.objects.filter(id=id)
    path = seg[0].path
    if proj4 is not None:
        geometry_proj = geometry_transform(geometry,proj4)
    else:
        geometry_proj = geometry_transform(geometry, '+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
    shape_region=shape(geometry_proj)
    geom_dc_tile = shape_region.intersection(shape(json.loads(seg[0].the_geom.geojson)))
    segmentation_name_classified = os.path.basename(path).split('.')[0] + '_classified'
    with fiona.open(path) as src:
        if proj4 is not None:
            fc = (feature_transform(x, crs_out=proj4, crs_in=proj4) for x in src)
            crs = from_string(proj4)
        else:
            fc = (feature_transform(x,
                                    crs_out='+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs') for x in src)
            crs = from_string('+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
            
        pred_objects_sorted = PredictClassification.objects.filter(name=predict_name, predict_object_id=id).prefetch_related('tag').order_by('features_id')
        fc_pred=[(x['properties']['id'], x['geometry']) for x in fc]
        fc = None
        fc_pred_sorted = sorted(fc_pred, key=itemgetter(0))
        fc_pred = [(x[0][1],
                    x[1].tag.numeric_code) for x in zip(fc_pred_sorted, pred_objects_sorted)]
        fc_pred_sorted = None
        pred_objects_sorted = None
        #rasterize
        bbox = seg[0].the_geom
        xmin, ymin, xmax, ymax = bbox.extent
        nrows = int(((ymax - ymin) // resolution) + 1)
        ncols = int(((xmax - xmin) // resolution) + 1)
        shape_dim = (nrows, ncols)
        arr = np.zeros((nrows, ncols), dtype=np.uint8)
        aff = Affine(resolution, 0, xmin, 0, -resolution, ymax)
        fc_pred_intersection = [(mapping(shape(feat[0]).intersection(geom_dc_tile)),
                                 feat[1]) for feat in fc_pred if shape(feat[0]).intersects(geom_dc_tile)]
        rasterize(shapes=fc_pred_intersection, transform=aff, dtype=np.uint8, out=arr)
        meta = {'driver': 'GTiff',
                'width': shape_dim[1],
                'height': shape_dim[0],
                'count': 1,
                'dtype': arr.dtype,
                'crs': proj4,
                'transform': aff,
                'compress': 'lzw',
                'nodata': 0}
        filename = path_destiny + '/' + segmentation_name_classified + '.tif'
        with rasterio.open(filename, 'w', **meta) as dst:
            dst.write(arr, 1)
    return filename


def detect_and_classify_change(tiles, algorithm, change_meta, band_list, mmu,
                               lc_pre, lc_post, extra_args,
                               filter_labels=True):
    """Run a change detection algorithm between two tiles, classify the results and write to the database

    Meant to be called within a dask.distributed.Cluster.map() over a list of
    (tile_index, [tile0, tile1]) tupples generated by two calls to gwf_query
    Called in detect_change command line

    Args:
        tiles (tuple): Tuple of (tile_index, [tile0, tile1]). Tiles are Datacube
            tiles as returned by GridWorkflow.list_cells()
        algorithm (str): Name of the change detection algorithm to use
        change_meta (madmex.models.ChangeInformation): Django object containing change
            objects meta information. Resulting from a call to ``get_or_create``
        band_list (list): Optional subset of bands of the product to use for running
            the change detection
        mmu (float or None): Minimum mapping unit in the unit of the tile crs
            (e.g.: squared meters, squared degrees, ...) to apply for filtering
            small change objects
        lc_pre (str): Name of the anterior land cover map to use for change
            classification
        lc_post (str): Name of the post land cover map to use for change
            classification
        extra_args (dict): dictionary of additional arguments
        filter_labels (bool): Whether to apply a filter to remove objects with same
            pre and post label. Defaults to True, in which case objects with same
            label are discarded
    """
    # Load change detection class
    try:
        module = import_module('madmex.lcc.bitemporal.%s' % algorithm)
        BiChange = module.BiChange
    except ImportError as e:
        raise ValueError('Invalid algorithm argument')

    try:
        # Load geoarrays
        geoarray_pre = GridWorkflow.load(tiles[1][0], measurements=band_list)
        BiChange_pre = BiChange.from_geoarray(geoarray_pre, **extra_args)
        geoarray_post = GridWorkflow.load(tiles[1][1], measurements=band_list)
        BiChange_post = BiChange.from_geoarray(geoarray_post)
        # Run change detection
        BiChange_pre.run(BiChange_post)
        # Apply mmu filter
        if mmu is not None:
            BiChange_pre.filter_mmu(mmu)
        # Exit function if there are no changes left
        if BiChange_pre.change_array.sum() == 0:
            return True
        # Load pre and post land cover map as feature collections
        fc_pre = BiChange_pre.read_land_cover(lc_pre)
        fc_post = BiChange_pre.read_land_cover(lc_post)
        # Generate feature collection of labelled change objects
        fc_change = BiChange_pre.label_change(fc_pre, fc_post)
        # Optionally filter objects with same pre and post label
        if filter_labels:
            fc_change = BiChange.filter_no_change(fc_change)
        # Write that feature collection to the database
        BiChange_pre.to_db(fc=fc_change, meta=change_meta, pre_name=lc_pre,
                       post_name=lc_post)
        # Deallocate large objects and run gc.collect
        geoarray_pre = None
        geoarray_post = None
        BiChange_pre = None
        BiChange_post = None
        fc_pre = None
        fc_post = None
        fc_change = None
        gc.collect()
        return True
    except Exception as e:
        print('Change detection failed because: %s' % e)
        return False

