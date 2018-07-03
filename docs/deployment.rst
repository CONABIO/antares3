**********
Deployment
**********

Single machine
==============

Installation
------------

Activate a ``python3`` virtual environmemt and run:

.. code-block:: bash

    # Install antares and all its dependencies (square brackets need to be escaped in zsh)
    pip install git+https://github.com/CONABIO/antares3.git#egg=antares3[all]


Setup
-----

Initial setup of both ``datacube`` (used as backend for antares) and ``antares`` itself requires a few one time actions.



Configuration files
^^^^^^^^^^^^^^^^^^^

Both ``datacube`` and ``antares`` require configuration files to operate. In both cases these configuration files must be placed at the root of the user's home directory (``~/``).


Open DataCube
"""""""""""""


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
----


Open DataCube
^^^^^^^^^^^^^

.. code-block:: bash

    createdb datacube
    datacube -v system init

Check that datacube is properly setup by running

.. code-block:: bash

    datacube system check


Antares3
^^^^^^^^

Antares setup consists of enabling the postgis extension for the database, setting up the database schemas, ingesting country borders in a table and deploy the configuration files specific to each dataset.

.. code-block:: bash
	
    # Replace yourdatabase by the name of the database
    psql -d yourdatabase -c "CREATE EXTENSION postgis;"
    antares init -c mex

This will create a ``madmex`` directory under ``~/.config/`` where ingestion files for all different suported dataset will be stored.


Cluster
=======

Local
-----


Cloud
------

Amazon Web Services and Sun Grid Engine
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**0. Prerequisites**

\* Configure `Amazon Virtual Private Cloud`_ on AWS with properly `VPCs and Subnets`_ configured according to your application.


\* Configure `Security Groups for Your VPC`_  with ports 6444 TCP and 6445 UDP for communication within instances via SGE and port 80 for web SGE, port 2043 for `Amazon Elastic File System`_ service on AWS and port 22 to ssh to instances from your machine.


\* Configure `Amazon Elastic File System`_ service on AWS (shared volume via Network File System -NFS-).

\* Create a bucket on S3 (see `Amazon S3`_) if using driver S3 of Open DataCube (see `Open DataCube Ingestion Config`_). `Boto3 Documentation`_ and AWS suggests as a best practice using `IAM Roles for Amazon EC2`_ to access this bucket. See `Best Practices for Configuring Credentials`_.

\* **(Not mandatory but useful)** Configure an `Elastic IP Addresses`_  on AWS. Master node will have this elastic ip.


\* AWS provide a managed relational database service `Amazon Relational Database Service (RDS)`_ with several database instance types and a `PostgreSQL`_  database engine.


    \* Configure `Amazon Relational Database Service (RDS)`_  with `PostgreSQL`_  version 9.5 + with properly `Amazon RDS Security Groups`_ and subnet group for the RDS configured (see `Tutorial Create an Amazon VPC for Use with an Amazon RDS DB Instance`_).


    \* Configure `Postgis`_ extension to `PostgreSQL`_  for storing and managing spatial information in the instance of `Amazon Relational Database Service (RDS)`_ you created.

    .. note:: 

        AWS gives you necessary steps to setup Postgis extension in `Working with PostGis`_ documentation.


    We use the following bash script to setup `Postgis`_ extension in database instance:

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

        createdb -h <db_host> -U <db_user> <database_name>

























It's assumed that a Cluster is already configured and variable ``mount_point`` is set to path of shared volume. See `Installation-Cloud Deployment`_ .

Open DataCube
^^^^^^^^^^^^^

Log in to an instance of `Auto Scaling Groups`_ configured in `Dependencies-Cloud Deployment`_ in step 2, create on the ``$mount_point/.datacube.conf`` file the datacube configuration file and execute:

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

    antares init -c mex
 
Use `RunCommand`_ service of AWS to execute following bash script in all instances with **Key** ``Type``, **Value** ``Node-dask-sge`` configured in `Dependencies-Cloud Deployment`_ in step 2, or use a tool for cluster management like `clusterssh`_ . 



.. code-block:: bash

    #!/bin/bash
    source /home/ubuntu/.profile
    su ubuntu -c "/home/ubuntu/.local/bin/antares init"

This will create a ``madmex`` directory under ``/home/ubuntu/.config/`` where ingestion files for all different suported dataset will be stored.





.. Install references:

.. _Create an AMI from an Amazon EC2 Instace: https://docs.aws.amazon.com/toolkit-for-visual-studio/latest/user-guide/tkv-create-ami-from-instance.html

.. _Auto Scaling Groups: https://docs.aws.amazon.com/autoscaling/ec2/userguide/AutoScalingGroup.html

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

.. _clusterssh: https://github.com/duncs/clusterssh

.. _RunCommand: https://docs.aws.amazon.com/systems-manager/latest/userguide/execute-remote-commands.html

.. _Open DataCube Ingestion Config: https://datacube-core.readthedocs.io/en/latest/ops/ingest.html#ingestion-config

.. _Security Groups for Your VPC: https://docs.aws.amazon.com/AmazonVPC/latest/UserGuide/VPC_SecurityGroups.html

.. _VPCs and Subnets: https://docs.aws.amazon.com/AmazonVPC/latest/UserGuide/VPC_Subnets.html

.. _Amazon Virtual Private Cloud: https://aws.amazon.com/vpc/

.. _Elastic IP Addresses: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/elastic-ip-addresses-eip.html



.. Last references:

.. _Auto Scaling Groups: https://docs.aws.amazon.com/autoscaling/ec2/userguide/AutoScalingGroup.html


.. _this question in StackOverFlow: https://stackoverflow.com/questions/46981873/permission-denied-to-set-session-authorization-on-amazon-postgres-rds


.. _Open DataCube Ingestion Config: https://datacube-core.readthedocs.io/en/latest/ops/ingest.html#ingestion-config
.. _clusterssh: https://github.com/duncs/clusterssh

.. _RunCommand: https://docs.aws.amazon.com/systems-manager/latest/userguide/execute-remote-commands.html


