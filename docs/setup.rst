********************
Setup/first time use
********************

Initial setup of both ``datacube`` (used as backend for antares) and ``antares`` itself requires a few one time actions.

Datacube
========

.. code-block:: bash

    createdb datacube
    datacube -v system init

Check that datacube is properly setup by running

.. code-block:: bash

    datacube system check


Antares
=======

Antares setup consists of enabling the postgis extension for the database, setting up the database schemas, ingesting country borders in a table and deploy the configuration files specific to each dataset.

.. code-block:: bash
	
    # Replace yourdatabase by the name of the database
    psql -d yourdatabase -c "CREATE EXTENSION postgis;"
    antares init -c mex

This will create a ``madmex`` directory under ``~/.config/`` where ingestion files for all different suported dataset will be stored.
