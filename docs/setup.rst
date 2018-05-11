********************
Setup/first time use
********************


Initial setup of both ``datacube`` (used as backend for antares) and ``antares`` itself requires a few one time actions.



Configuration Files
===================

Both ``datacube`` and ``antares`` require configuration files to operate. In both cases these configuration files must be placed at the root of the user's home directory (``~/``).

Open DataCube
-------------

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
--------

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


Local
======

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



Cloud deployment
================

This section uses configuration files at the top of this page.

Amazon Web Services
-------------------

It's assumed that a Cluster is already configured and variable ``mount_point`` is set to path of shared volume. See `Installation-Cloud Deployment`_ .

Open DataCube
^^^^^^^^^^^^^

Log in to an instance of `Auto Scaling Groups`_ configured in `Dependencies-Cloud Deployment`_ in step 2, create on that instance the configuration file for ``datacube`` and execute:

.. attention:: 

	Open Datacube supports NETCDF CF and S3 drivers for storage (see `Open DataCube Ingestion Config`_). Different software dependencies are required for different drivers and different ``datacube system init`` command.


\* NETCDF CF

.. code-block:: bash

    datacube -v system init --no-init-users 


\* S3 

.. code-block:: bash

    datacube -v system init -s3 --no-init-users 


.. note:: 

	The ``--no-init-users`` flag is necessary for both drivers so we don't have errors related to permissions. See `this question in StackOverFlow`_ .



For both drivers you can execute the following to check that Open DataCube is properly setup:

.. code-block:: bash

    datacube system check


.. note:: 

	For S3 driver additionally you can check the following tables are created in your database: 

	.. code-block:: psql

		\dt agdc.*

		s3_dataset
		s3_dataset_chunk
		s3_dataset_mapping



Antares3
^^^^^^^^

Antares setup consists of setting up the database schemas, ingesting country borders in a table and deploy the configuration files specific to each dataset.

Log in to master node, copy paste in ``$mount_point/.antares`` the configuration file for ``antares`` and execute:

.. code-block:: bash

    ln -sf $mount_point/.antares /home/ubuntu/.antares
    antares init -c mex
 
Use `RunCommand`_ service of AWS to execute following bash script in all instances with **Key** ``Type``, **Value** ``Node-dask-sge`` configured in `Dependencies-Cloud Deployment`_ in step 2, or use a tool for cluster management like `clusterssh`_ . 



.. code-block:: bash

    #!/bin/bash
    source /home/ubuntu/.profile
    ln -sf $mount_point/.antares /home/ubuntu/.antares
    su ubuntu -c "antares init"

This will create a ``madmex`` directory under ``/home/ubuntu/.config/`` where ingestion files for all different suported dataset will be stored.



.. _Auto Scaling Groups: https://docs.aws.amazon.com/autoscaling/ec2/userguide/AutoScalingGroup.html


.. _this question in StackOverFlow: https://stackoverflow.com/questions/46981873/permission-denied-to-set-session-authorization-on-amazon-postgres-rds


.. _Open DataCube Ingestion Config: https://datacube-core.readthedocs.io/en/latest/ops/ingest.html#ingestion-config
.. _clusterssh: https://github.com/duncs/clusterssh

.. _RunCommand: https://docs.aws.amazon.com/systems-manager/latest/userguide/execute-remote-commands.html


