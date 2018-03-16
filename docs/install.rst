************
Installation
************

System libraries
================

- Postgres + postgis
- GDAL
- python3
- git
- virtualenv

Python package
==============

Activate a ``python3`` virtual environmemt and run:

.. code-block:: bash

    pip install numpy
    pip install GDAL==$(gdal-config --version) --global-option=build_ext --global-option="-I/usr/include/gdal"
    pip install rasterio==1.0a12
    # Install antares and all its dependencies (square brackets need to be escaped in zsh)
    pip install git+https://github.com/CONABIO/antares3.git[all]



Configuration files
===================

Datacube
--------

See datacube documentation

antares
-------

::

    SECRET_KEY=
    DEBUG=True
    DJANGO_LOG_LEVEL=DEBUG
    DATABASE_NAME=
    DATABASE_USER=
    DATABASE_PASSWORD=
    DATABASE_HOST=
    DATABASE_PORT=
    SERIALIZED_OBJECTS_DIR=
    USGS_USER=
    USGS_PASSWORD=
    SCIHUB_USER=
    SCIHUB_PASSWORD=
    TEMP_DIR=
    INGESTION_PATH=

