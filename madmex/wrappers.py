import rasterio
import numpy as np
import os
import json
from datetime import datetime
import datacube
from datacube.api import GridWorkflow
from datacube.utils.geometry import Geometry, CRS
from importlib import import_module
from madmex.util.xarray import to_float
from madmex.io.vector_db import VectorDb
from madmex.overlay.extractions import zonal_stats_xarray
from madmex.modeling import BaseModel

# Django stuff
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "madmex.settings")
import django
django.setup()
from madmex.models import Region, Country

"""
The wrapper module gathers functions that are typically called by
command lines
"""

def predict_pixel_tile(tile, gwf, model_id, outdir=None):
    """Run a model in prediction mode and generates a raster file written to disk

    Meant to be called within a dask.distributed.Cluster.map() over a list of tiles
    returned by GridWorkflow.list_cells
    Called in model_predict command line

    Args:
        tile: Datacube tile as returned by GridWorkflow.list_cells()
        gwf: GridWorkflow object
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
        xr_dataset = gwf.load(tile[1])
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


def extract_tile_db(tile, gwf, sp, training_set):
    """FUnction to extract data under training geometries for a given tile

    Meant to be called within a dask.distributed.Cluster.map() over a list of tiles
    returned by GridWorkflow.list_cells
    Called in model_fit command line

    Args:
        tile: Datacube tile as returned by GridWorkflow.list_cells()
        gwf: GridWorkflow object
        sp: Spatial aggregation function
        training_set (str): Training data identifier (training_set field)

    Returns:
        A list of predictors and target values arrays
    """
    try:
        # Load tile as Dataset
        xr_dataset = gwf.load(tile[1])
        # Query the training geometries fitting into the extent of xr_dataset
        db = VectorDb()
        fc = db.load_training_from_dataset(xr_dataset,
                                           training_set=training_set)
        # fc is a feature collection with one property (class)
        # Overlay geometries and xr_dataset and perform extraction combined with spatial aggregation
        extract = zonal_stats_xarray(xr_dataset, fc, field='class', aggregation=sp)
        # Return the extracted array (or a list of two arrays?)
        return extract
    except Exception as e:
        return [None, None]


def gwf_query(product, lat=None, long=None, region=None, begin=None, end=None):
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

    Returns:
        List: List of [0] GridWorkflow object and [1] dictionary view of Tile index, Tile
        key value pair

    Example:

        >>> from madmex.wrappers import gwf_query

        >>> # Using region name, time unbounded
        >>> gwf, tiles_list = gwf_query(product='ls8_espa_mexico', region='Jalisco')
        >>> # Using region name, time windowed
        >>> gwf, tiles_list = gwf_query(product='ls8_espa_mexico', region='Jalisco',
        ...                             begin = '2017-01-01', end='2017-03-31')
        >>> # Using lat long box, time windowed
        >>> gwf, tiles_list = gwf_query(product='ls8_espa_mexico', lat=[19, 22], long=[-104, -102],
        ...                             begin = '2017-01-01', end='2017-03-31')
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
    gwf = GridWorkflow(dc.index, product=product)
    tile_dict = gwf.list_cells(**query_params)
    # Iterable (dictionary view (analog to list of tuples))
    tiles_view = tile_dict.items()
    return [gwf, tiles_view]
