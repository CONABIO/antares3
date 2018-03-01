from importlib import import_module
from madmex.util.xarray import to_float
from madmex.io.vector_db import VectorDb
from madmex.overlay.extractions import zonal_stats_xarray

"""
The wrapper module gathers functions that are typically called by
command lines
"""

def predict_pixel_tile(tile, gwf, model_id, model):
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
        model (str): Type of model (must be a model implemented in madmex.modeling)
        #TODO: The argument above is redundant, find a way to avoid repeating model type

    Return:
        str: The function is used for its side effect of generating a predicted
        array and writting it to a raster file (GeoTiff or NetCDF). OPtionally the file is registered as a storage unit in the datacube database.
    """
    # Load model class corresponding to the right model
    try:
        module = import_module('madmex.modeling.supervised.%s' % model)
        Model = module.Model
        trained_model = Model.from_db(model_id)
    except ImportError as e:
        raise ValueError('Invalid model argument')
    # Load tile
    xr_dataset = gwf.load(tile[1])
    # Convert it to float?
    xr_dataset_float = xr_dataset.apply(func=to_float, keep_attrs=True)
    # Transform file to nd array
    arr_3d = xr_dataset_float.to_array().values
    2d_shape = (arr_3d.shape[0], arr_3d.shape[1] * arr_3d.shape[2])
    arr_2d = arr_3d.reshape(2d_shape)
    # predict
    predicted_array = trained_model.predict(arr_2d)
    # Reshape back to 2D
    predicted_array = predicted_array.reshape((arr_3d.shape[1], arr_3d.shape[2]))
    # Coerce back to xarray with all spatial parameters properly set
    # Build output filename
    # Write to filename
    # Register to database






def extract_tile_db(tile, gwf, field, sp, training_set):
    """FUnction to extract data under training geometries for a given tile

    Meant to be called within a dask.distributed.Cluster.map() over a list of tiles
    returned by GridWorkflow.list_cells
    Called in model_fit command line

    Args:
        tile: Datacube tile as returned by GridWorkflow.list_cells()
        gwf: GridWorkflow object
        field (str): Feature collection property to use for assigning labels
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
        # Overlay geometries and xr_dataset and perform extraction combined with spatial aggregation
        extract = zonal_stats_xarray(xr_dataset, fc, field, sp)
        # Return the extracted array (or a list of two arrays?)
        return extract
    except Exception as e:
        return [None, None]
