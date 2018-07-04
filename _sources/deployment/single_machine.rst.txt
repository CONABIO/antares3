

**************
Single machine
**************


Installation
============


Activate a ``python3`` virtual environmemt and run:

.. code-block:: bash

    # Install antares and all its dependencies (square brackets need to be escaped in zsh)
    pip install git+https://github.com/CONABIO/antares3.git#egg=antares3[all]

Setup
=====


Initial setup of both ``datacube`` (used as backend for antares) and ``antares`` itself requires a few one time actions.


Configuration files
-------------------


Both ``datacube`` and ``antares`` require configuration files to operate. In both cases these configuration files must be placed at the root of the user's home directory (``~/``).

Open DataCube
^^^^^^^^^^^^^


In the case of datacube, the configuration file must be named ``.datacube.conf`` and contains database connection specifications. See `datacube doc <http://datacube-core.readthedocs.io/en/stable/ops/db_setup.html#create-configuration-file>`_ for more details.

::

    [datacube]
    db_database: <database_name>

    # A blank host will use a local socket. Specify a hostname (such as localhost) to use TCP.
    db_hostname: <database_host>

    # Credentials are optional: you might have other Postgres authentication configured.
    # The default username otherwise is the current user id.
    db_username: <database_user>
    db_password: <database_password>

Antares3
^^^^^^^^


The configuration file used by antares contain various fields related to data location, password and database details, and must be named ``.antares``. Place it at the root of the user's home directory (``~/``). Depending on the ``antares`` functionalities you are planning to use, some field may be left empty. For instance ``SCIHUB_USER`` and ``SCIHUB_PASSWORD`` are not required if you are not planning to query or download sentinel data.

::

    SECRET_KEY=
    DEBUG=True
    DJANGO_LOG_LEVEL=DEBUG
    DATABASE_NAME=
    DATABASE_USER=
    DATABASE_PASSWORD=
    DATABASE_HOST=
    DATABASE_PORT=
    ALLOWED_HOSTS=
    SERIALIZED_OBJECTS_DIR=
    USGS_USER=
    USGS_PASSWORD=
    SCIHUB_USER=
    SCIHUB_PASSWORD=
    TEMP_DIR=
    INGESTION_PATH=
    BIS_LICENSE=

Init
====


Open DataCube
-------------


.. code-block:: bash

    createdb datacube
    datacube -v system init

Check that datacube is properly setup by running

.. code-block:: bash

    datacube system check


Antares3
--------

Antares setup consists of enabling the postgis extension for the database, setting up the database schemas, ingesting country borders in a table and deploy the configuration files specific to each dataset.

.. code-block:: bash
	
    # Replace yourdatabase by the name of the database
    psql -d yourdatabase -c "CREATE EXTENSION postgis;"
    antares init -c mex

This will create a ``madmex`` directory under ``~/.config/`` where ingestion files for all different suported dataset will be stored.

