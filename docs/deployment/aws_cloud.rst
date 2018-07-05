*******************
Amazon Web Services
*******************

Prerequisites
=============

\* Configure `Amazon Virtual Private Cloud`_ on AWS with properly `VPCs and Subnets`_ configured according to your application.


\* Configure `Security Groups for Your VPC`_  with ports 6444 TCP and 6445 UDP for communication within instances via SGE and port 80 for web SGE, port 2043 for Amazon Elastic File System service on AWS and port 22 to ssh to instances from your machine.


\* Configure `Amazon Elastic File System`_ service on AWS (shared volume via Network File System -NFS-).

\* Create a bucket on S3 (see `Amazon S3`_) if using driver S3 of Open DataCube (see `Open DataCube Ingestion Config`_). `Boto3 Documentation`_ and AWS suggests as a best practice using `IAM Roles for Amazon EC2`_ to access this bucket. See `Best Practices for Configuring Credentials`_.

\* **(Not mandatory but useful)** Configure an `Elastic IP Addresses`_  on AWS. Master node will have this elastic ip.


\* AWS provide a managed relational database service `Amazon Relational Database Service (RDS)`_ with several database instance types and a `PostgreSQL`_  database engine.


    \* Configure RDS with PostgreSQL  version 9.5 + with properly `Amazon RDS Security Groups`_ and subnet group for the RDS configured (see `Tutorial Create an Amazon VPC for Use with an Amazon RDS DB Instance`_).


    \* Configure `Postgis`_ extension to PostgreSQL  for storing and managing spatial information in the instance of RDS you created.

    .. note:: 

        AWS gives you necessary steps to setup Postgis extension in `Working with PostGis`_ documentation.


    We use the following bash script to setup Postgis extension in database instance:

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
        
        chmod 0600 ~/.pgpass


    \* **(Not mandatory but useful)** You can either work with the database configured in RDS or create a new one with:

    .. code-block:: bash

        createdb -h <db_host> -U <db_user> <database_name>




Sun Grid Engine and Dask
========================


1. Create AMI of AWS from bash script.
--------------------------------------


Launch an instance with AMI ``Ubuntu 16.04 LTS``.

The following bash script can be used in **User data** configuration of the instance to:

\* Install AWS cli.

\* Install package ``amazon-ssm-agent.deb`` to use RunCommand service of EC2. 

.. note:: 
 
  RunCommand service is not a mandatory installation for antares3, Open Datacube nor SGE, we use it for it's simplicity to execute commands on all of the instances (see  `RunCommand`_). You can use instead `clusterssh`_  or other tool for cluster management.


\* Tag your instance with **Key** ``Name`` and **Value** ``$name_instance``.

\* Install dependencies for SGE, antares3 and Open Datacube.

.. note:: 

    Modify variables ``region``, ``name_instance``, ``shared_volume`` and ``user`` with your own configuration.

.. code-block:: bash

    #!/bin/bash
    ##Bash script to create AMI of AWS for master and nodes:
    ##variables:
    region=<region>
    name_instance=conabio-dask-sge
    shared_volume=/shared_volume
    user=ubuntu
    ##System update
    apt-get update
    ##Install awscli
    apt-get install -y python3-pip && pip3 install --upgrade pip==9.0.3
    pip3 install awscli --upgrade
    ##Tag instance
    INSTANCE_ID=$(curl -s http://instance-data/latest/meta-data/instance-id)
    PUBLIC_IP_LOCAL=$(curl -s http://instance-data/latest/meta-data/local-ipv4)
    PUBLIC_IP=$(curl -s http://instance-data/latest/meta-data/public-ipv4)
    aws ec2 create-tags --resources $INSTANCE_ID --tag Key=Name,Value=$name_instance-$PUBLIC_IP --region=$region
    ##Set locales for OpenDataCube
    echo "export LC_ALL=C.UTF-8" >> /home/$user/.profile
    echo "export LANG=C.UTF-8" >> /home/$user/.profile
    ##Set variable mount_point
    echo "export mount_point=$shared_volume" >> /home/$user/.profile
    ##Dependencies for sge, antares3 and open datacube
    apt-get install -y nfs-common openssh-server openjdk-8-jre xsltproc apache2 git htop postgresql-client \
    python-software-properties \
    libssl-dev \
    libffi-dev \
    python3-dev \
    python3-setuptools
    ##For RunCommand service of EC2
    wget https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/debian_amd64/amazon-ssm-agent.deb
    dpkg -i amazon-ssm-agent.deb
    systemctl enable amazon-ssm-agent
    ##For web SGE
    echo "<VirtualHost *:80>
        ServerAdmin webmaster@localhost
        DocumentRoot /var/www/
        ErrorLog ${APACHE_LOG_DIR}/error.log
        # Possible values include: debug, info, notice, warn, error, crit,
        # alert, emerg.
        LogLevel warn
        CustomLog ${APACHE_LOG_DIR}/access.log combined
        <Directory /var/www/qstat>
                Options +ExecCGI
                AddHandler cgi-script .cgi
                   DirectoryIndex qstat.cgi
        </Directory>
    </VirtualHost>
    # vim: syntax=apache ts=4 sw=4 sts=4 sr noet" > /etc/apache2/sites-available/000-default.conf
    git clone https://github.com/styv/webqstat.git /var/www/qstat
    sed -i '/tools/s/./#./' /var/www/qstat/config.sh
    a2enmod cgid
    service apache2 start
    ##Install gridengine non interactively
    export DEBIAN_FRONTEND=noninteractive
    apt-get install -q -y gridengine-client gridengine-exec gridengine-master
    /etc/init.d/gridengine-master restart
    service apache2 restart
    ##Install spatial libraries
    add-apt-repository -y ppa:ubuntugis/ubuntugis-unstable && apt-get -qq update
    apt-get install -y \
        netcdf-bin \
        libnetcdf-dev \
        libproj-dev \
        libgeos-dev \
        gdal-bin \
        libgdal-dev
    ##Install dask distributed
    pip3 install dask distributed --upgrade
    pip3 install bokeh
    ##Install missing package for open datacube:
    pip3 install --upgrade python-dateutil
    ##Create shared volume
    mkdir $shared_volume
    ##Locale settings for open datacube
    echo "alias python=python3" >> /home/$user/.bash_aliases
    #dependencies for antares3 & datacube
    pip3 install numpy && pip3 install cloudpickle && pip3 install GDAL==$(gdal-config --version) --global-option=build_ext --global-option='-I/usr/include/gdal' && pip3 install rasterio==1.0a12 --no-binary rasterio && pip3 install scipy
    pip3 install sklearn
    pip3 install lightgbm
    pip3 install fiona --no-binary fiona
    pip3 install django
    #datacube:
    pip3 install git+https://github.com/opendatacube/datacube-core.git@develop#egg=datacube[s3]


Once launching of the instance was successful, log in and execute next commands:


.. note::


    We use Elastic File System of AWS (shared file storage, see `Amazon Elastic File System`_), which multiple Amazon EC2 instances running in multiple Availability Zones (AZs) within the same region can access it. Change variable ``efs_dns`` according to your ``DNS name``.

.. code-block:: bash

    efs_dns=<DNS name of EFS service>
    ##Mount shared volume
    sudo mount -t nfs4 -o nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2 $efs_dns:/ $mount_point
    


Then open an editor an copy-paste next bash script in ``$mount_point/create-dask-sge-queue.sh`` file.


.. code-block:: bash

    #!/bin/bash
    #First parameter is name of queue on SGE
    #Second parameter is number of slots that queue of SGE will have
    #Third parameter is user 
    source /home/$user/.profile
    queue_name=$1
    slots=$2
    type_value=$type_value
    region=$region
    qconf -am $user
    ##queue of SGE, this needs to be executed for registering nodes:
    echo -e "group_name @allhosts\nhostlist NONE" > $mount_point/host_group_sge.txt
    qconf -Ahgrp $mount_point/host_group_sge.txt
    echo -e "qname                 $queue_name\nhostlist              NONE\nseq_no                0\nload_thresholds       np_load_avg=1.75\nsuspend_thresholds    NONE\nnsuspend              1\nsuspend_interval      00:05:00\npriority              0\nmin_cpu_interval      00:05:00\nprocessors            UNDEFINED\nqtype                 BATCH INTERACTIVE\nckpt_list             NONE\npe_list               make\nrerun                 FALSE\nslots                 1\ntmpdir                /tmp\nshell                 /bin/csh\nprolog                NONE\nepilog                NONE\nshell_start_mode      posix_compliant\nstarter_method        NONE\nsuspend_method        NONE\nresume_method         NONE\nterminate_method      NONE\nnotify                00:00:60\nowner_list            NONE\nuser_lists            NONE\nxuser_lists           NONE\nsubordinate_list      NONE\ncomplex_values        NONE\nprojects              NONE\nxprojects             NONE\ncalendar              NONE\ninitial_state         default\ns_rt                  INFINITY\nh_rt                  INFINITY\ns_cpu                 INFINITY\nh_cpu                 INFINITY\ns_fsize               INFINITY\nh_fsize               INFINITY\ns_data                INFINITY\nh_data                INFINITY\ns_stack               INFINITY\nh_stack               INFINITY\ns_core                INFINITY\nh_core                INFINITY\ns_rss                 INFINITY\nh_rss                 INFINITY\ns_vmem                INFINITY\nh_vmem                INFINITY" > $mount_point/queue_name_sge.txt
    qconf -Aq $mount_point/queue_name_sge.txt
    qconf -aattr queue hostlist @allhosts $queue_name
    qconf -aattr queue slots $slots $queue_name
    qconf -aattr hostgroup hostlist $HOSTNAME @allhosts
    ##Get IP's of instances using awscli
    aws ec2 describe-instances --region=$region --filter Name=tag:Type,Values=$type_value --query 'Reservations[].Instances[].PrivateDnsName' |grep compute| cut -d'"' -f2 > $mount_point/nodes.txt
    /bin/sh -c 'for ip in $(cat $mount_point/nodes.txt);do qconf -as $ip;done'
    /bin/sh -c 'for ip in $(cat $mount_point/nodes.txt);do echo "hostname $ip \nload_scaling NONE\ncomplex_values NONE\nuser_lists NONE \nxuser_lists NONE\nprojects NONE\nxprojects NONE\nusage_scaling NONE\nreport_variables NONE " > $mount_point/ips_nodes_format_sge.txt; qconf -Ae $mount_point/ips_nodes_format_sge.txt ; qconf -aattr hostgroup hostlist $ip @allhosts ;done'
    ##echo IP of node master
    echo $(hostname).$region.compute.internal > $mount_point/ip_master.txt


Once bash script was created unmount the shared volume and terminate instance:

.. code-block:: bash

    sudo umount $mount_point


You can use this instance to create AMI of AWS `Create an AMI from an Amazon EC2 Instace`_.

2. Configure an Autoscaling group of AWS using AMI
--------------------------------------------------

Once created an AMI of AWS from previous step, use the following bash script to configure instances using `Auto Scaling Groups`_ service of AWS.


.. note:: 

    Modify variables ``region``, ``name_instance``, ``type_value`` and ``user`` with your own configuration. Here instances are tagged with **Key** ``Type`` and **Value** ``Node-dask-sge`` so we can use `RunCommand`_ service of AWS to execute bash scripts (for example) on instances with this tag.

.. code-block:: bash

    #!/bin/bash
    region=<region>
    name_instance=conabio-dask-sge-node
    type_value=Node-dask-sge
    user=ubuntu
    ##Tag instances of type node
    INSTANCE_ID=$(curl -s http://instance-data/latest/meta-data/instance-id)
    PUBLIC_IP=$(curl -s http://instance-data/latest/meta-data/public-ipv4)
    aws ec2 create-tags --resources $INSTANCE_ID --tag Key=Name,Value=$name_instance-$PUBLIC_IP --region=$region
    ##Next line is useful so RunCommand can execute bash scripts (for example) on instances with Key=Type, Value=$type_value
    aws ec2 create-tags --resources $INSTANCE_ID --tag Key=Type,Value=$type_value --region=$region
    echo "export region=$region" >> /home/$user/.profile
    echo "export type_value=$type_value" >> /home/$user/.profile
    ##Uncomment next two lines if you want to install Antares3 on your AutoScalingGroup
    #su $user -c "pip3 install --user git+https://github.com/CONABIO/antares3.git@develop"
    #echo "export PATH=$PATH:/home/$user/.local/bin/" >> ~/.profile



**Example using** `RunCommand`_ **service of AWS with Tag Name and Tag Value**

.. image:: https://dl.dropboxusercontent.com/s/kubf3ibnuv5axx4/aws_runcommand_sphix_docu.png?dl=0
    :width: 600

3. Init Cluster
---------------

**Example with one master and two nodes. Install Open DataCube and Antares3 in all nodes.**

Using instances of `Auto Scaling Groups`_ configured in step 2 we have to configure SGE queue on master node and register nodes on this queue.


3.1 Assign Elastic IP to master node and create Sun Grid Engine queue
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


Run the following bash script using `RunCommand`_ or login to an instance from your autoscaling group to run it (doesn't matter which one). The instance where  the bash script is executed will be the **master node** of our cluster.
 
We use an elastic IP provided by AWS for the node that will be the **master node**, so change variable ``eip`` according to your ``Allocation ID`` (see `Elastic IP Addresses`_).
 

We also use Elastic File System of AWS (shared file storage, see `Amazon Elastic File System`_), which multiple Amazon EC2 instances running in multiple Availability Zones (AZs) within the same region can access it. Change variable ``efs_dns`` according to your ``DNS name``.
 

.. note:: 

    Modify variables ``user``, ``eip``, ``name_instance``, ``efs_dns``, ``queue_name`` and ``slots`` with your own configuration.  Elastic IP and EFS are not mandatory. You can use a NFS server instead  of EFS, for example. In this example the instances have two cores each of them.

.. code-block:: bash

    #!/bin/bash
    ##variables
    user=ubuntu
    source /home/$user/.profile
    eip=<Allocation ID of Elastic IP>
    name_instance=conabio-dask-sge-master
    efs_dns=<DNS name of EFS>
    ##Name of the queue that will be used by dask-scheduler and dask-workers
    queue_name=dask-queue.q
    ##Change number of slots to use for every instance, in this example the instances have 2 slots each of them
    slots=2
    region=$region
    type_value=$type_value
    ##Mount shared volume
    mount -t nfs4 -o nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2 $efs_dns:/ $mount_point
    mkdir -p $mount_point/datacube/datacube_ingest
    ##Tag instance
    INSTANCE_ID=$(curl -s http://instance-data/latest/meta-data/instance-id)
    PUBLIC_IP=$(curl -s http://instance-data/latest/meta-data/public-ipv4)
    ##Assining elastic IP where this bash script is executed
    aws ec2 associate-address --instance-id $INSTANCE_ID --allocation-id $eip --region $region
    ##Tag instance where this bash script is executed
    aws ec2 create-tags --resources $INSTANCE_ID --tag Key=Name,Value=$name_instance-$PUBLIC_IP --region=$region
    ##Execute bash script create-dask-sge-queue already created on Dependencies-Cloud Deployment
    bash $mount_point/create-dask-sge-queue.sh $queue_name $slots

3.2 Restart gridengine-exec on nodes and install Open DataCube and Antares3
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


Use `RunCommand`_ service of AWS to execute following bash script in all instances with **Key** ``Type``, **Value** ``Node-dask-sge`` already configured in step 2, or use a tool for cluster management like `clusterssh`_ . (You can also have the line that install OpenDataCube and Antares3 on the bash script configured in step 2 in instances of AutoScalingGroup)


.. code-block:: bash

    #!/bin/bash
    user=ubuntu
    source /home/$user/.profile
    efs_dns=<DNS name of EFS>
    mount -t nfs4 -o nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2 $efs_dns:/ $mount_point
    ##Ip for sun grid engine master
    master_dns=$(cat $mount_point/ip_master.txt)
    echo $master_dns > /var/lib/gridengine/default/common/act_qmaster
    /etc/init.d/gridengine-exec restart
    ##Install antares3
    su $user -c "pip3 install --user git+https://github.com/CONABIO/antares3.git@develop"
    echo "export PATH=$PATH:/home/$user/.local/bin/" >> ~/.profile
    ##Create symbolic link to configuration files for antares3
    ln -sf $mount_point/.antares /home/$user/.antares
    ##Create symbolic link to configuration files for datacube in all instances
    ln -sf $mount_point/.datacube.conf /home/$user/.datacube.conf
    ##Uncomment next line if you want to init antares (previously installed)
    #su $user -c "/home/$user/.local/bin/antares init"

3.3 Run SGE commands to init cluster
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


Login to master node and execute:

.. code-block:: bash

    # Start dask-scheduler on master node. The file scheduler.json will be created on $mount_point (shared_volume) of EFS
    qsub -b y -l h=$HOSTNAME dask-scheduler --scheduler-file $mount_point/scheduler.json

The master node has two cores, one is used for dask-scheduler, the other core can be used as a dask-worker:

.. code-block:: bash

    qsub -b y -l h=$HOSTNAME dask-worker --nthreads 1 --scheduler-file $mount_point/scheduler.json

If your group of autoscaling has 3 nodes, then execute:

.. code-block:: bash

    # Start 6 (=3 nodes x 2 cores each node) dask-worker processes in an array job pointing to the same file
    qsub -b y -t 1-6 dask-worker --nthreads 1 --scheduler-file $mount_point/scheduler.json

You can view the web SGE on the page:

**<public DNS of master>/qstat/qstat.cgi**

.. image:: https://dl.dropboxusercontent.com/s/vr2hj5m26q90std/sge_1_sphinx_docu.png?dl=0
    :width: 400


**<public DNS of master>/qstat/queue.cgi**


.. image:: https://dl.dropboxusercontent.com/s/4wfmbodapxx62ql/sge_2_sphinx_docu.png?dl=0
    :width: 400

**<public DNS of master>/qstat/qstat.cgi**

.. image:: https://dl.dropboxusercontent.com/s/l45t46e1lg9lolt/sge_3_sphinx_docu.png?dl=0
    :width: 600

and the state of your cluster with `bokeh`_  at:


**<public DNS of master>:8787**

.. image:: https://dl.dropboxusercontent.com/s/ujmxapvn1m3t8lf/bokeh_1_sphinx_docu.png?dl=0
    :width: 400

**<public DNS of master>:8787/workers**

.. image:: https://dl.dropboxusercontent.com/s/1q6z4z10o5tv27f/bokeh_1_workers_sphinx_docu.png?dl=0
    :width: 600

or

**<public DNS of worker>:8789** 

.. image:: https://dl.dropboxusercontent.com/s/rnapd51c565huij/bokeh_2_sphinx_docu.png?dl=0
    :width: 400

Run an example
^^^^^^^^^^^^^^

   
On master or node execute:

.. code-block:: python3

    from dask.distributed import Client
    import os
    client = Client(scheduler_file=os.environ['mount_point']+'/scheduler.json')

    def square(x):
        return x ** 2

    def neg(x):
        return -x

    A = client.map(square, range(10))
    B = client.map(neg, A)
    total = client.submit(sum, B)
    total.result()
    -285
    total
    <Future: status: finished, type: int, key: sum-ccdc2c162ed26e26fc2dc2f47e0aa479>
    client.gather(A)
    [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]


from **<public DNS of master>:8787/graph** we have:

.. image:: https://dl.dropboxusercontent.com/s/kcge4zzk48m1xr3/bokeh_3_graph_sphinx_docu.png?dl=0
    :width: 600



.. note::

    To stop cluster on master or node execute:

    .. code-block:: bash

        qdel 1 2


4. Init
-------


In step 1 it was configured variable ``mount_point`` which is a path to a shared volume.

Open DataCube
^^^^^^^^^^^^^


Log in to an instance of `Auto Scaling Groups`_ configured in step 2 and create in ``$mount_point/.datacube.conf`` the datacube configuration file:


::

    [user]
    default_environment: <datacube or s3aio_env, first for netcdf and second for s3>
    
    [datacube]
    db_hostname: <database_host>
    db_database: <database_name>
    db_username: <database_user>
    db_password: <database_password>
    
    execution_engine.use_s3: <True or False>
    
    [s3aio_env]
    db_hostname: <database_host>
    db_database: <database_name>
    db_username: <database_user>
    db_password: <database_password>
    index_driver: <default or s3aio_index>, first for netcdf and second for s3>
    
    execution_engine.use_s3: <True or False>



and execute:

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
~~~~~~~~

Antares setup consists of setting up the database schemas, ingesting country borders in a table and deploy the configuration files specific to each dataset.

Log in to master node and create in ``$mount_point/.antares`` the configuration file for ``antares``:


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




and execute:

.. code-block:: bash

    antares init -c mex
 
Use `RunCommand`_ service of AWS to execute following bash script in all instances with **Key** ``Type``, **Value** ``Node-dask-sge`` configured in step 2, or use a tool for cluster management like `clusterssh`_ . Modify variable ``user`` according to your user.



.. code-block:: bash

    #!/bin/bash
    user=ubuntu
    source /home/$user/.profile
    su $user -c "antares init"

This will create a ``madmex`` directory under ``~/.config/`` where ingestion files for all different suported dataset will be stored.


Kubernetes and Dask
===================


Kubernetes is an open-source system for automating deployment, scaling, and management of containerized applications (see `Kubernetes`_ and `Kubernetes github page`_ ). There are a lot of ways to deploy a Kubernetes cluster, for instance see `Picking the right solution`_.


Cluster creation
----------------

The nex steps follow `kops`_ and `kops - Kubernetes Operations`_ guides:

1) Configure a domain and a subdomain with their respective hosted zones. For the following description `Route 53`_ service of AWS was used to create the domain ``conabio-route53.net`` and subdomain ``antares3.conabio-route53.net``. Also a **gossip based Kubernetes cluster** can be used instead (see for example this `issue`_ and this `entry of blog`_).

2) Install **same versions** of kops and kubectl. We use a ``t2.micro`` instance with AMI ``Ubuntu 16.04 LTS`` to install this tools with the next bash script:
 

.. code-block:: bash

	#!/bin/bash
	##variables:
	region=<region>
	name_instance=conabio-kubernetes
	shared_volume=/shared_volume
	user=ubuntu
	##System update
	apt-get update
	##Install awscli
	apt-get install -y python3-pip && pip3 install --upgrade pip==9.0.3
	pip3 install awscli --upgrade
	##Tag instance
	INSTANCE_ID=$(curl -s http://instance-data/latest/meta-data/instance-id)
	PUBLIC_IP=$(curl -s http://instance-data/latest/meta-data/public-ipv4)
	aws ec2 create-tags --resources $INSTANCE_ID --tag Key=Name,Value=$name_instance-$PUBLIC_IP --region=$region
	##Assing elastic IP where this bash script is executed
	aws ec2 associate-address --instance-id $INSTANCE_ID --allocation-id $eip --region $region
	##Set variables for completion of bash commands
	echo "export LC_ALL=C.UTF-8" >> /home/$user/.profile
	echo "export LANG=C.UTF-8" >> /home/$user/.profile
	##Set variable mount_point
	echo "export mount_point=$shared_volume" >> /home/$user/.profile
	##Useful software for common operations
	apt-get install -y nfs-common jq git htop
	##For RunCommand service of EC2
	wget https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/debian_amd64/amazon-ssm-agent.deb
	dpkg -i amazon-ssm-agent.deb
	systemctl enable amazon-ssm-agent
	##Create shared volume
	mkdir $shared_volume
	##install docker for ubuntu:
	curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
	add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
	apt-get update
	apt-cache policy docker-ce
	apt-get install -y docker-ce 
	service docker start
	##install kops version 1.9.0:
	wget -O kops https://github.com/kubernetes/kops/releases/download/1.9.0/kops-linux-amd64
	chmod +x ./kops
	sudo mv ./kops /usr/local/bin/
	##install kubernetes command line tool v1.9: kubectl
	wget -O kubectl https://storage.googleapis.com/kubernetes-release/release/v1.9.0/bin/linux/amd64/kubectl
	chmod +x ./kubectl
	sudo mv ./kubectl /usr/local/bin/kubectl
	##enable completion for kubectl:
	echo "source <(kubectl completion bash)" >> /home/$user/.bashrc


You can check kops and kubectl versions with:

.. code-block:: bash

	$kops version

	$kubectl version


3) Use next **Dockerfile** to build docker image for antares3:
   
.. code-block:: bash


	FROM ubuntu:xenial
	USER root

	#see: https://github.com/Yelp/dumb-init/ for next line:
	RUN apt-get update && apt-get install -y wget curl && wget -O /usr/local/bin/dumb-init https://github.com/Yelp/dumb-init/releases/download/v$	(curl -s https://api.github.com/repos/Yelp/dumb-init/releases/latest| grep tag_name|sed -n 's/  ".*v\(.*\)",/\1/p')/dumb-init_$(curl -s 	https://api.github.com/repos/Yelp/dumb-init/releases/latest| grep tag_name|sed -n 's/  ".*v\(.*\)",/\1/p')_amd64 && chmod +x /usr/local/bin/	dumb-init
	
	#base dependencies
	RUN apt-get update && apt-get install -y \
		openssh-server \
		openssl \
		sudo \
		nano \
		software-properties-common \
		python-software-properties \
		git \
		vim \
		vim-gtk \
		htop \
		build-essential \
		libssl-dev \
		libffi-dev \
		cmake \
		python3-dev \
		python3-pip \
		python3-setuptools \
		ca-certificates \
		postgresql-client \
	    libudunits2-dev  && pip3 install --upgrade pip==9.0.3
	
	#Install spatial libraries
	RUN add-apt-repository -y ppa:ubuntugis/ubuntugis-unstable && apt-get -qq update
	RUN apt-get install -y \
		netcdf-bin \
		libnetcdf-dev \
		ncview \
		libproj-dev \
		libgeos-dev \
		gdal-bin \
		libgdal-dev
	
	#Create user: madmex_user
	RUN groupadd madmex_user
	RUN useradd madmex_user -g madmex_user -m -s /bin/bash
	RUN echo "madmex_user ALL=(ALL:ALL) NOPASSWD:ALL" | (EDITOR="tee -a" visudo)
	RUN echo "madmex_user:madmex_user" | chpasswd
	
	##Install dask distributed
	RUN pip3 install dask distributed --upgrade && pip3 install bokeh
	##Install missing package for open datacube:
	RUN pip3 install --upgrade python-dateutil
	
	#Dependencies for antares3 & datacube
	RUN pip3 install numpy && pip3 install GDAL==$(gdal-config --version) --global-option=build_ext --global-option='-I/usr/include/gdal' && 	pip3 install rasterio==1.0b1 --no-binary rasterio  
	RUN pip3 install scipy cloudpickle sklearn lightgbm fiona django --no-binary fiona
	RUN pip3 install --no-cache --no-binary :all: psycopg2
	RUN pip3 install futures pathlib setuptools==20.4
	
	#datacube:
	RUN apt-get clean && apt-get update && apt-get install -y locales
	RUN locale-gen en_US.UTF-8
	ENV LANG en_US.UTF-8
	ENV LC_ALL en_US.UTF-8
	RUN pip3 install git+https://github.com/opendatacube/datacube-core.git@develop#egg=datacube[s3]
	
	#Upgrade awscli and tools for s3:
	RUN pip3 install boto3 botocore awscli --upgrade
	
	#antares3:
	USER madmex_user
	RUN pip3 install --user git+https://github.com/CONABIO/antares3.git@develop
	
	##Set locales for OpenDataCube
	RUN echo "export LC_ALL=C.UTF-8" >> ~/.profile
	RUN echo "export LANG=C.UTF-8" >> ~/.profile
	#Set variables
	ARG mount_point=$mount_point
	RUN echo "export mount_point=$mount_point" >> ~/.profile
	#Use python3
	RUN echo "alias python=python3" >> ~/.bash_aliases
	#Antares3:
	RUN echo "export PATH=$PATH:/home/madmex_user/.local/bin/" >> ~/.profile
	#Config files for datacube and antares
	RUN ln -sf $mount_point/.antares ~/.antares
	RUN ln -sf $mount_point/.datacube.conf ~/.datacube.conf
	
	#Final settings
	WORKDIR /home/madmex_user/
	VOLUME ["/shared_volume"]
	ENTRYPOINT ["/usr/local/bin/dumb-init", "--"]

   
Build docker image with:

.. code-block:: bash

	DOCKER_REPOSITORY=<name of your docker hub repository>
	DOCKER_IMAGE_NAME=antares3-k8s-cluster-dependencies
	DOCKER_IMAGE_VERSION=latest
	sudo docker build --build-arg mount_point=$mount_point -t $DOCKER_REPOSITORY/$DOCKER_IMAGE_NAME:$DOCKER_IMAGE_VERSION . 
	sudo docker login
	sudo docker push $DOCKER_REPOSITORY/$DOCKER_IMAGE_NAME:$DOCKER_IMAGE_VERSION
	sudo docker rmi $DOCKER_REPOSITORY/$DOCKER_IMAGE_NAME:$DOCKER_IMAGE_VERSION

4) Set next bash variables:
 
.. code-block:: bash

	#Your domain name that is hosted in AWS Route 53
	#Use: export DOMAIN_NAME="antares3.k8s.local" #for a gossip based cluster
	export DOMAIN_NAME="antares3.conabio-route53.net"
	
	# Friendly name to use as an alias for your cluster
	export CLUSTER_ALIAS="testing-k8s-deployment"
	
	# Leave as-is: Full DNS name of you cluster
	export CLUSTER_FULL_NAME="${CLUSTER_ALIAS}.${DOMAIN_NAME}"
	
	# AWS availability zone where the cluster will be created
	export CLUSTER_AWS_AZ="us-west-2a,us-west-2b,us-west-2c"
	
	# Leave as-is: AWS Route 53 hosted zone ID for your domain (don't set if gossip based cluster)
	export DOMAIN_NAME_ZONE_ID=$(aws route53 list-hosted-zones \
	       | jq -r '.HostedZones[] | select(.Name=="'${DOMAIN_NAME}'.") | .Id' \
	       | sed 's/\/hostedzone\///')
	
	export KUBERNETES_VERSION="1.9.0"
	
	export KOPS_STATE_STORE="s3://${CLUSTER_FULL_NAME}-state"

	export EDITOR=nano

	
5) Create AWS S3 bucket to hold information for Kubernetes cluster:

.. note:: 

	The instance needs the policy **AmazonS3FullAccess** attach to a role created by you to have permissions to execute next command.
	
.. code-block:: bash

    $aws s3api create-bucket --bucket ${CLUSTER_FULL_NAME}-state


6) Create group and user kops and generate access keys for user kops:


.. note:: 
	
	The instance needs the policy **IAMFullAccess** attach to a role created by you to have permissions to execute next command.

Create group and permissions of it:

.. code-block:: bash

	$aws iam create-group --group-name kops
	$aws iam attach-group-policy --policy-arn arn:aws:iam::aws:policy/AmazonEC2FullAccess --group-name kops
	$aws iam attach-group-policy --policy-arn arn:aws:iam::aws:policy/AmazonRoute53FullAccess --group-name kops
	$aws iam attach-group-policy --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess --group-name kops
	$aws iam attach-group-policy --policy-arn arn:aws:iam::aws:policy/IAMFullAccess --group-name kops
	$aws iam attach-group-policy --policy-arn arn:aws:iam::aws:policy/AmazonVPCFullAccess --group-name kops
	$aws iam attach-group-policy --policy-arn arn:aws:iam::aws:policy/AmazonElasticFileSystemFullAccess --group-name kops


Create user kops and add it to already created group kops:

.. code-block:: bash

	$aws iam create-user --user-name kops
	$aws iam add-user-to-group --user-name kops --group-name kops


Create access keys for user kops:


.. code-block:: bash

	$aws iam create-access-key --user-name kops


This will generate an **AccessKeyId** and **SecretAccessKey** that must be kept in a safe place. Use them to configure awscli and set next variables:

.. code-block:: bash

	$aws configure 
		AWS Access Key ID [None]: xxxx
		AWS Secret Access Key [None]: xxxxxxx
		Default region name [None]: <leave it empty>
		Default output format [None]: <leave it empty>
	$export AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id)
	$export AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key)


7) Create a Key Pair with AWS console and a Public Key. See `Amazon EC2 Key Pairs`_ sections: **Creating a Key Pair Using Amazon EC2** and **Creating a Key Pair Using Amazon EC2**. Save the Public Key in ``/home/ubuntu/.ssh/id_rsa.pub``.


8) Deploy Kubernetes Cluster. An example is:


.. code-block:: bash

	$kops create cluster \
	--name=${CLUSTER_FULL_NAME} \
	--zones=${CLUSTER_AWS_AZ} \
	--master-size="t2.medium" \
	--node-size="t2.medium" \
	--node-count="3" \
	--dns-zone=${DOMAIN_NAME} \
	--ssh-public-key="/home/ubuntu/.ssh/id_rsa.pub" \
	--kubernetes-version=${KUBERNETES_VERSION} --yes

.. note::

	You can delete cluster with: ``$kops delete cluster ${CLUSTER_FULL_NAME} --yes`` (without ``yes`` flag is used to just see what changes are going to be applied) and don't forget to delete S3 bucket: ``$aws s3api delete-bucket --bucket ${CLUSTER_FULL_NAME}-state`` after cluster deletion.


.. note:: 

	You can turn on/off cluster editing screen that appears with command: 
	``$kops edit ig nodes --name $CLUSTER_FULL_NAME``, setting 3/0 number of instances (3 is an example) and then ``$kops update cluster $CLUSTER_FULL_NAME`` and  ``$kops update cluster $CLUSTER_FULL_NAME --yes``. 
	For master you can use: ``$kops edit ig master-us-west-2a --name $CLUSTER_FULL_NAME`` set 1/0 number of instances and then ``$kops update cluster $CLUSTER_FULL_NAME`` and ``$kops update cluster $CLUSTER_FULL_NAME --yes`` commands (you can check your instance type of master with: ``$kops get instancegroups``).



Deployment for Elastic File System
----------------------------------


In order to share some files (for example ``.antares`` and ``.datacube.conf``) between all containers an ``efs-provisioner`` is used. See `efs-provisioner`_. 


Retrieve id's of subnets and security groups created by kops:

.. code-block:: bash
	
	region=<region>
	
	subnets_kops=$(aws ec2 describe-subnets --filters "Name=tag:KubernetesCluster,Values=$CLUSTER_FULL_NAME" --region $region|jq -r 	'.Subnets[].SubnetId'|tr -s '\n' ' ')
	
	subnets_kops1=$(echo $subnets_kops|cut -d' ' -f1)
	subnets_kops2=$(echo $subnets_kops|cut -d' ' -f2)
	subnets_kops3=$(echo $subnets_kops|cut -d' ' -f3)
	
	sgroups_kops=$(aws ec2 describe-security-groups --filters "Name=tag:KubernetesCluster,Values=$CLUSTER_FULL_NAME" --region $region|jq -r 	'.SecurityGroups[].GroupId'|tr -s '\n' ' ')
	
	sgroups_master=$(aws ec2 describe-security-groups --filters "Name=tag:Name,Values=masters.$CLUSTER_FULL_NAME" --region $region|jq -r 	'.SecurityGroups[].GroupId'|tr -s '\n' ' ')
	
	sgroups_nodes=$(aws ec2 describe-security-groups --filters "Name=tag:Name,Values=nodes.$CLUSTER_FULL_NAME" --region $region|jq -r '.SecurityGroups[].GroupId'|tr -s '\n' ' ')


Use next commands to create EFS and give access to docker containers to EFS via mount targets and security groups 	(here it's assumed that three subnets were created by ``kops create cluster`` command):




.. code-block:: bash

	region=<region>

	#create EFS:
	aws efs create-file-system --performance-mode maxIO --creation-token <some random integer number> --region $region
	

Set DNS and id of EFS: (last command sould output this values)

.. code-block:: bash
	
	region=<region>

	efs_dns=<DNS of EFS>
	efs_id=<id of EFS>
	
	#create mount targets for three subnets: 
	aws efs create-mount-target --file-system-id $efs_id --subnet-id $subnets_kops1 --security-groups $sgroups_kops --region $region
	aws efs create-mount-target --file-system-id $efs_id --subnet-id $subnets_kops2 --security-groups $sgroups_kops --region $region
	aws efs create-mount-target --file-system-id $efs_id --subnet-id $subnets_kops3 --security-groups $sgroups_kops --region $region
	
	#You have to poll the status of mount targets until status LifeCycleState = “available”:
	
	#aws efs describe-mount-targets --file-system-id $efs_id --region $region
	
	#Create inbound rules for NFS on the security groups:
	
	aws ec2 authorize-security-group-ingress --group-id $sgroups_master --protocol tcp --port 2049 --source-group $sgroups_master --region 	$region
	aws ec2 authorize-security-group-ingress --group-id $sgroups_nodes --protocol tcp --port 2049 --source-group $sgroups_nodes --region $region


Deployment for EFS
^^^^^^^^^^^^^^^^^^

In the next ``.yaml`` put **EFS id**, **region**, **AccessKeyId** and **SecretAccessKey** generated for user kops:



.. code-block:: bash

	---
	apiVersion: v1
	kind: ConfigMap
	metadata:
	  name: efs-provisioner
	data:
	  file.system.id: <efs id>
	  aws.region: <region>
	  provisioner.name: aws-efs
	---
	kind: ClusterRole
	apiVersion: rbac.authorization.k8s.io/v1
	metadata:
	  name: efs-provisioner-runner
	rules:
	  - apiGroups: [""]
	    resources: ["persistentvolumes"]
	    verbs: ["get", "list", "watch", "create", "delete"]
	  - apiGroups: [""]
	    resources: ["persistentvolumeclaims"]
	    verbs: ["get", "list", "watch", "update"]
	  - apiGroups: ["storage.k8s.io"]
	    resources: ["storageclasses"]
	    verbs: ["get", "list", "watch"]
	  - apiGroups: [""]
	    resources: ["events"]
	    verbs: ["list", "watch", "create", "update", "patch"]
	---
	kind: ClusterRoleBinding
	apiVersion: rbac.authorization.k8s.io/v1
	metadata:
	  name: run-efs-provisioner
	subjects:
	  - kind: ServiceAccount
	    name: efs-provisioner
	    namespace: default
	roleRef:
	  kind: ClusterRole
	  name: efs-provisioner-runner
	  apiGroup: rbac.authorization.k8s.io
	---
	apiVersion: v1
	kind: ServiceAccount
	metadata:
	  name: efs-provisioner
	---
	kind: Deployment
	apiVersion: extensions/v1beta1
	metadata:
	  name: efs-provisioner
	spec:
	  replicas: 1
	  strategy:
	    type: Recreate
	  template:
	    metadata:
	      labels:
	        app: efs-provisioner
	    spec:
	      serviceAccount: efs-provisioner
	      containers:
	        - name: efs-provisioner
	          image: quay.io/external_storage/efs-provisioner:latest
	          env:
	            - name: FILE_SYSTEM_ID
	              valueFrom:
	                configMapKeyRef:
	                  name: efs-provisioner
	                  key: file.system.id
	            - name: AWS_REGION
	              valueFrom:
	                configMapKeyRef:
	                  name: efs-provisioner
	                  key: aws.region
	            - name: PROVISIONER_NAME
	              valueFrom:
	                configMapKeyRef:
	                  name: efs-provisioner
	                  key: provisioner.name
	            - name: AWS_ACCESS_KEY_ID
	              value: <AccessKeyId of user kops>
	            - name: AWS_SECRET_ACCESS_KEY
	              value: <SecretAccessKey of user kops>
	          volumeMounts:
	            - name: pv-volume
	              mountPath: /persistentvolumes
	      volumes:
	        - name: pv-volume
	          nfs:
	            server: <efs id>.efs.us-west-2.amazonaws.com
	            path: /
	---
	kind: StorageClass
	apiVersion: storage.k8s.io/v1beta1
	metadata:
	  name: aws-efs
	provisioner: aws-efs
	---
	kind: PersistentVolumeClaim
	apiVersion: v1
	metadata:
	  name: efs
	  annotations:
	    volume.beta.kubernetes.io/storage-class: "aws-efs"
	spec:
	  accessModes:
	    - ReadWriteMany
	  resources:
	    requests:
	      storage: 1Mi
	---

Execute next commands to create deployment:

.. code-block:: bash

    $kubectl create -f efs-provisioner.yaml


.. note:: 

	PersistentVolumes can have various reclaim policies, including “Retain”, “Recycle”, and “Delete”.For dynamically provisioned 	PersistentVolumes, the default reclaim policy is “Delete”. This means that a dynamically provisioned volume is automatically deleted when a user deletes the corresponding PersistentVolumeClaim. This automatic behavior might be inappropriate if the volume contains precious data. In that case, it is more appropriate to use the “Retain” policy. With the “Retain” policy, if a user deletes a PersistentVolumeClaim, the 	corresponding PersistentVolume is not be deleted. Instead, it is moved to the Released phase, where all of its data can be manually recovered. See: `Why change reclaim policy of a PersistentVolume`_ 
	
	.. _Why change reclaim policy of a PersistentVolume: https://kubernetes.io/docs/tasks/administer-cluster/change-pv-reclaim-policy/


To change reclaim policy:

.. code-block:: bash

	#retrieve persistent volume:

	pv_id=$(kubectl get pv|grep pvc | cut -d' ' -f1)

	kubectl patch pv $pv_id -p '{"spec":{"persistentVolumeReclaimPolicy":"Retain"}}


In order to be able to turn on/off cluster without deleting deployment of efs, next command is useful:

.. code-block:: bash

    kubectl scale deployments/efs-provisioner --replicas=0 #use replicas=1 when turn on cluster


Deployments for dask scheduler and worker
-----------------------------------------

.. Kubernetes references:

.. _efs-provisioner: https://github.com/kubernetes-incubator/external-storage/tree/master/aws/efs

.. _Amazon EC2 Key Pairs: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-key-pairs.html

.. _Kubernetes github page: https://github.com/kubernetes/kubernetes

.. _Kubernetes: https://kubernetes.io/

.. _Picking the right solution: https://kubernetes.io/docs/setup/pick-right-solution/

.. _kops - Kubernetes Operations: https://github.com/kubernetes/kops

.. _kops: https://kubernetes.io/docs/setup/custom-cloud/kops/

.. _Route 53: https://aws.amazon.com/route53/?nc1=h_ls

.. _entry of blog: http://blog.arungupta.me/gossip-kubernetes-aws-kops/

.. _issue: https://github.com/kubernetes/kops/issues/2858  

.. Dependencies references:

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


.. Install references

.. _Auto Scaling Groups: https://docs.aws.amazon.com/autoscaling/ec2/userguide/AutoScalingGroup.html

.. _bokeh: https://bokeh.pydata.org/en/latest/

.. _clusterssh: https://github.com/duncs/clusterssh

.. _RunCommand: https://docs.aws.amazon.com/systems-manager/latest/userguide/execute-remote-commands.html

.. _Open DataCube Ingestion Config: https://datacube-core.readthedocs.io/en/latest/ops/ingest.html#ingestion-config

.. _Amazon Elastic File System: https://aws.amazon.com/efs/ 

.. _Elastic IP Addresses: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/elastic-ip-addresses-eip.html





.. Last references:

.. _Auto Scaling Groups: https://docs.aws.amazon.com/autoscaling/ec2/userguide/AutoScalingGroup.html


.. _this question in StackOverFlow: https://stackoverflow.com/questions/46981873/permission-denied-to-set-session-authorization-on-amazon-postgres-rds


.. _Open DataCube Ingestion Config: https://datacube-core.readthedocs.io/en/latest/ops/ingest.html#ingestion-config
.. _clusterssh: https://github.com/duncs/clusterssh

.. _RunCommand: https://docs.aws.amazon.com/systems-manager/latest/userguide/execute-remote-commands.html


