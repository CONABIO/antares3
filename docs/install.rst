************
Installation
************

System libraries
================

The system requires gdal, postgres, postgis and libnetcdf. The instructions below refer to a deployment on Ubuntu or Ubuntu derivatives.
  
.. code-block:: bash

    sudo add-apt-repository ppa:ubuntugis/ubuntugis-unstable
    sudo apt-get update
    # Datacube system dependencies (gdal and netcdf)
    sudo apt-get install libhdf5-serial-dev libnetcdf-dev libgdal1-dev
    # Postgres
    sudo apt-get install postgresql postgresql-contrib postgis
    # Python3
    sudo apt-get install python3 python3-dev python3-pip python3-virtualenv
    # Other
    sudo pip install virtualenvwrapper
    # Source virtualenvwrapper installation directory in your .bashrc


Python package
==============

Activate a ``python3`` virtual environmemt and run:

.. code-block:: bash

    pip install numpy
    pip install GDAL==$(gdal-config --version) --global-option=build_ext --global-option="-I/usr/include/gdal"
    pip install rasterio==1.0a12
    # Install antares and all its dependencies (square brackets need to be escaped in zsh)
    pip install git+https://github.com/CONABIO/antares3.git#egg=antares3[all]



Configuration files
===================

Both ``datacube`` and ``antares`` require configuration files to operate. In both cases these configuration files must be placed at the root of the user's home directory (``~/``).

Datacube
--------

In the case of datacube, the configuration file must be named ``.datacube.conf`` and contains database connection specifications. See `datacube doc <http://datacube-core.readthedocs.io/en/stable/ops/db_setup.html#create-configuration-file>`_ for more details.

::

    [datacube]
    db_database: datacube

    # A blank host will use a local socket. Specify a hostname (such as localhost) to use TCP.
    db_hostname:

    # Credentials are optional: you might have other Postgres authentication configured.
    # The default username otherwise is the current user id.
    # db_username: 
    # db_password:

antares
-------

The configuration file used by antares contain various fields related to data location, password and database details, and must be named ``.antares``. Place it at the root of the user's home directory. Depending on the ``antares`` functionalities you are planning to use, some field may be left empty. For instance ``SCIHUB_USER`` and ``SCIHUB_PASSWORD`` are not required if you are not planning to query or download sentinel data.

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
    SERIALIZED_OBJECTS_DIR=

