**********************
Command line interface
**********************

All command line interface start with the prefix ``antares``. Simply running ``antares`` in a terminal will give a list of all available commands. Detailed help of each command line can then be accessed by running ``antares command_line --help``. An example of help pages, returned by the ``--help`` flag is given at the bottom of this page.


Command list
============

System administration
---------------------


==================   ===================================================================
Command              Short description
==================   ===================================================================
antares init         Perform initial system setup (database, configuration files)
==================   ===================================================================


Data preparation
----------------


==============================   ===================================================================
Command                          Short description
==============================   ===================================================================
antares rasterize_vector_file    Generate a tiled raster product from any vector file
antares make_country_mask        Generate a tiled raster binary mask for any country
antares prepare_metadata         Generate metadata for a given dataset prior to datacube indexing
==============================   ===================================================================


Data download
-------------


=======================   ===================================================================
Command                   Short description
=======================   ===================================================================
antares create_order      Place a Landsat surface reflectance pre-processing order to espa
antares download_order    Download a previously placed espa processing order 
=======================   ===================================================================


Ingestion
---------


==============================   ===================================================================
Command                          Short description
==============================   ===================================================================
antares ingest_catalog           Ingest Landsat data catalog into the database
antares ingest_footprints        Ingest shapefile of Landsat scenes footprints into the database
antares ingest_training          Ingest training data into the database
antares ingest_validation        Ingest validation data into the database
==============================   ===================================================================



Export
------

==============================   ===================================================================
Command                          Short description
==============================   ===================================================================
antares db_to_vector             Export the result of a classification to a vector file
antares db_to_raster             Export the result of a classification to a raster file
antares generate_style           Export the information of a given scheme to a QGIS style file
==============================   ===================================================================



Processing
----------


==============================   ===================================================================
Command                          Short description
==============================   ===================================================================
antares apply_recipe             Generate a new datacube product from a defined recipe
antares segment                  Run segmentation and write the output to the database
antares model_fit                Train a model given a training set and a datacube product
antares model_predict            Predict land cover pixel based given a trained model
antares model_predict_object     Predict land cover for a set of segmentation polygons
antares detect_change            Run change detection and classification between two products
==============================   ===================================================================




Validation
----------


==============================   ===================================================================
Command                          Short description
==============================   ===================================================================
antares validate                 Validate a classification using an ingested set of validation data
==============================   ===================================================================


Inventory, parameters retrieval
-------------------------------


==============================   ===========================================================================================
Command                          Short description
==============================   ===========================================================================================
antares list                     List models, training sets, classifications, segmentation, ... present in the database
antares bi_change_params         Retrieve list of change detection algorithm implemented and their parameters
antares model_params             Retrieve list of models implemented and their parameters
antares segment_params           Retrieve list of segmentation agorithms implemented and their parameters
==============================   ===========================================================================================




Help page example
=================

Running ``antares model_fit --help`` returns:


.. program-output:: antares model_fit --help