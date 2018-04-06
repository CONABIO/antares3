**************
Setup Database
**************


Local
=====

Coming soon


Cloud
=====

Amazon Web Services
-------------------

AWS provide a managed relational database service `Amazon Relational Database Service (RDS)`_ with several database instance types and a `PostgreSQL`_  database engine.



**0. Prerequisites**

\* Configure `Amazon Relational Database Service (RDS)`_  with `PostgreSQL`_  version 9.5 + with properly `Amazon RDS Security Groups`_ and subnet group for the RDS configured (see `Tutorial Create an Amazon VPC for Use with an Amazon RDS DB Instance`_)


\* Open Datacube supports NETCDF CF and S3 drivers for storage (see `Open DataCube Ingestion Config`_). Different software dependencies are required for different drivers. Choose one of the drivers supported by Open DataCube according to your application. For NETCDF CF we use `Amazon Elastic File System`_ and for S3 driver we use `Amazon S3`_ . 

.. note:: 

	If S3 driver for storage of Open DataCube is selected, you need to create a bucket on S3. `Boto3 Documentation`_ and AWS suggests as a best practice using `IAM Roles for Amazon EC2`_ to access this bucket. See `Best Practices for Configuring Credentials`_.


\* Configure `Postgis`_ extension to `PostgreSQL`_  for storing and managing spatial information in the instance of `Amazon Relational Database Service (RDS)`_ you created.

.. note:: 

	AWS gives you necessary steps to setup Postgis extension in `Working with PostGis`_ documentation.


We use the following bash script to setup `Postgis`_ extension:

.. code-block:: bash

	#!/bin/bash
	##First argument its the name of database created on RDS, following arguments are self explanatory
	db=$1
	db_user=$2
	db_host=$3
	psql -h $db_host -U $db_user --dbname=$db --command "create extension postgis;"
	psql -h $db_host -U $db_user --dbname=$db --command "create extension fuzzystrmatch;"
	psql -h $db_host -U $db_user --dbname=$db --command "create extension postgis_tiger_geocoder;"
	psql -h $db_host -U $db_user --dbname=$db --command "create extension postgis_topology;"
	psql -h $db_host -U $db_user --dbname=$db --command "alter schema tiger owner to rds_superuser;"
	psql -h $db_host -U $db_user --dbname=$db --command "alter schema tiger_data owner to rds_superuser;"
	psql -h $db_host -U $db_user --dbname=$db --command "alter schema topology owner to rds_superuser;"
	psql -h $db_host -U $db_user --dbname=$db --command "CREATE FUNCTION exec(text) returns text language plpgsql volatile AS \$f\$ BEGIN EXECUTE \$1; RETURN \$1; END; \$f\$;"
	psql -h $db_host -U $db_user --dbname=$db --command "SELECT exec('ALTER TABLE ' || quote_ident(s.nspname) || '.' || quote_ident(s.relname) || ' OWNER TO rds_superuser;') FROM (SELECT nspname, relname FROM pg_class c JOIN pg_namespace n ON (c.relnamespace = n.oid) WHERE nspname in ('tiger','topology') AND relkind IN ('r','S','v') ORDER BY relkind = 'S') s;"

Make sure a file ``.pgpass`` is in ``/home/ubuntu`` path so you are not prompted with the password for every command. The contents of this file are:

::

<db_host>:<port>:<name of database>:<name of database user>:<database password>

and permissions of this ``.pgpass`` are:

.. code-block:: bash

    chmod 0600 /home/ubuntu/.pgpass


\* **(Not mandatory but useful)** You can either work with the database configured in RDS or create a new one with:

.. code-block:: bash

    createdb -h <db_host> -U <madmex_user> <database_name>


1. Configuration Files
^^^^^^^^^^^^^^^^^^^^^^

Both ``datacube`` and ``antares`` require configuration files to operate. In both cases these configuration files must be placed at the root of the user's home directory (``/home/ubuntu``).

DataCube
""""""""

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
""""""""

The configuration file used by antares contain various fields related to data location, password and database details, and must be named ``.antares``. Place it at the root of the user's home directory (``/home/ubuntu``). Depending on the ``antares`` functionalities you are planning to use, some field may be left empty. For instance ``SCIHUB_USER`` and ``SCIHUB_PASSWORD`` are not required if you are not planning to query or download sentinel data.

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



2. Antares3 and Open DataCube init
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Open DataCube
"""""""""""""

Open Datacube supports NETCDF CF and S3 drivers for storage (see `Open DataCube Ingestion Config`_). Different software dependencies are required for different drivers and different ``datacube system init`` command:

Execute:

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

	For S3 driver you can check that the following tables are created in your database: 

	.. code-block:: psql

		\dt agdc.*

		s3_dataset
		s3_dataset_chunk
		s3_dataset_mapping


Antares3
""""""""


Antares setup consists of setting up the database schemas, ingesting country borders in a table and deploy the configuration files specific to each dataset.

.. code-block:: bash
	
    antares init -c mex

This will create a ``madmex`` directory under ``/home/ubuntu/.config/`` where ingestion files for all different suported dataset will be stored.




.. _this question in StackOverFlow: https://stackoverflow.com/questions/46981873/permission-denied-to-set-session-authorization-on-amazon-postgres-rds

.. _Working with PostGis: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Appendix.PostgreSQL.CommonDBATasks.html#Appendix.PostgreSQL.CommonDBATasks.PostGIS

.. _Postgis: https://postgis.net/ 
	
.. _Boto3 Documentation: http://boto3.readthedocs.io/en/latest/index.html 
	
.. _PostgreSQL: https://www.postgresql.org/

.. _Amazon Relational Database Service (RDS): https://aws.amazon.com/rds/

.. _Tutorial Create an Amazon VPC for Use with an Amazon RDS DB Instance: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_Tutorials.WebServerDB.CreateVPC.html

.. _Amazon RDS Security Groups: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Overview.RDSSecurityGroups.html

.. _IAM Roles for Amazon EC2: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html
	
.. _Best Practices for Configuring Credentials: http://boto3.readthedocs.io/en/latest/guide/configuration.html#best-practices-for-configuring-credentials

.. _Amazon S3: https://aws.amazon.com/s3/

.. _Amazon Elastic File System: https://aws.amazon.com/efs/ 

.. _Open DataCube Ingestion Config: https://datacube-core.readthedocs.io/en/latest/ops/ingest.html#ingestion-config

