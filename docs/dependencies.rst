************
Dependencies
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

