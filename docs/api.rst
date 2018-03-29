.. currentmodule:: madmex

*************
API reference
*************

Api
===

Interact with various remote sensing data query and download APIs

.. autosummary::
   :toctree: generated

   api.remote.UsgsApi
   api.remote.EspaApi
   api.remote.ScihubApi



Indexing
========

Register datasets to the datacube database.

.. autosummary::
   :toctree: generated

   indexing.add_product
   indexing.add_product_from_yaml
   indexing.add_product_from_recipe
   indexing.add_dataset
   indexing.wkt_to_proj4
   indexing.metadict_from_netcdf


Ingestion
=========

Generate metadata to prepare indexing/ingestion of datasets

.. autosummary::
   :toctree: generated

   ingestion.bioclimatics.metadata_convert
   ingestion.landsat_espa.metadata_convert
   ingestion.srtm_cgiar.metadata_convert



I/O
===

Read and write data

.. autosummary::
   :toctree: generated

   io.helpers.get_label_encoding
   io.vector_db.from_geobox
   io.vector_db.VectorDb
   io.vector_db.VectorDb.load_training_from_dataset
   io.vector_db.load_segmentation_from_dataset


Modeling
========

Interface to various statistical models running on numpy arrays

Base class
----------

.. autosummary::
   :toctree: generated

   modeling.BaseModel
   modeling.BaseModel.fit
   modeling.BaseModel.predict
   modeling.BaseModel.load
   modeling.BaseModel.save
   modeling.BaseModel.from_db
   modeling.BaseModel.to_db
   modeling.BaseModel.hot_encode_training
   modeling.BaseModel.hot_encode_predict
   modeling.BaseModel.score
   modeling.BaseModel.create_report

Implemented models
------------------

.. autosummary::
   :toctree: generated

   modeling.supervised.rf.Model


Overlay
=======

Overlay operations: conversions (vector to raster to vector) and extractions

.. autosummary::
   :toctree: generated

   overlay.conversions.rasterize_xarray
   overlay.conversions.train_object_to_feature
   overlay.conversions.predict_object_to_feature
   overlay.extractions.calculate_zonal_statistics
   overlay.extractions.zonal_stats_xarray


Segmentation
============

Interface to various segmentation algorithms operating on numpy arrays and xarray ```Dataset``s

Base class
----------

.. autosummary::
   :toctree: generated

   segmentation.BaseSegmentation
   segmentation.BaseSegmentation.from_geoarray
   segmentation.BaseSegmentation.segment
   segmentation.BaseSegmentation.polygonize
   segmentation.BaseSegmentation.to_db

Implemented algorithms
----------------------

.. autosummary::
   :toctree: generated

   segmentation.slic.Segmentation


Wrappers
========

Wrapper functions to be called in scripts and command lines

.. autosummary::
   :toctree: generated

   wrappers.predict_pixel_tile
   wrappers.extract_tile_db
   wrappers.gwf_query
   wrappers.segment
   wrappers.predict_object



Utils
=====

Various utils

.. autosummary::
   :toctree: generated

   util.randomword
   util.yaml_to_dict
   util.mid_date
   util.parser_extra_args
   util.chunk
   util.datacube.var_to_ind
   util.local.aware_download
   util.local.extract_zip
   util.local.aware_make_dir
   util.local.basename
   util.local.filter_files_from_folder
   util.xarray.to_float
   util.xarray.to_int
   util.spatial.feature_transform
