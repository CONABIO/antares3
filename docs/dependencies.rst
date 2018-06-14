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



Cloud deployment
================

Amazon Web Services
-------------------


Setting Cluster
^^^^^^^^^^^^^^^

Sun Grid Engine
"""""""""""""""

**0. Prerequisites**

\* Configure `Amazon Virtual Private Cloud`_ on AWS with properly `VPCs and Subnets`_ configured according to your application.


\* Configure `Security Groups for Your VPC`_  with ports 6444 TCP and 6445 UDP for communication within instances via SGE and port 80 for web SGE, port 2043 for `Amazon Elastic File System`_ service on AWS and port 22 to ssh to instances from your machine.


\* Configure `Amazon Elastic File System`_ service on AWS (shared volume via Network File System -NFS-).


\* **(Not mandatory but useful)** Configure an `Elastic IP Addresses`_  on AWS. Master node will have this elastic ip.


1. Create AMI of AWS from bash script.

Launch an instance with AMI ``Ubuntu 16.04 LTS``.

The following bash script can be used in **User data** configuration of the instance to:

\* Install AWS cli.

\* Install package ``amazon-ssm-agent.deb`` to use `RunCommand`_ service of EC2. 

.. note:: 
 
  RunCommand service is not a mandatory installation for antares3, Open Datacube nor SGE, we use it for it's simplicity to execute commands on all of the instances (see  `RunCommand`_). You can use instead `clusterssh`_  or other tool for cluster management.


\* Tag your instance with **Key** ``Name`` and **Value** ``$name_instance``.

\* Install dependencies for SGE, antares3 and Open Datacube.

.. note:: 

    Modify variables ``region``, ``name_instance``, ``shared_volume`` with your own configuration.

.. code-block:: bash

    #!/bin/bash
    ##Bash script to create AMI of AWS for master and nodes:
    ##variables:
    region=<region>
    name_instance=conabio-dask-sge
    shared_volume=/shared_volume
    ##Install awscli
    apt-get update
    apt-get install -y awscli
    ##Tag instance
    INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
    PUBLIC_IP_LOCAL=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)
    PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
    aws ec2 create-tags --resources $INSTANCE_ID --tag Key=Name,Value=$name_instance-$PUBLIC_IP --region=$region
    ##Set locales for OpenDataCube
    echo "export LC_ALL=C.UTF-8" >> /home/ubuntu/.profile
    echo "export LANG=C.UTF-8" >> /home/ubuntu/.profile
    ##Set variable mount_point
    echo "export mount_point=$shared_volume" >> /home/ubuntu/.profile
    ##Dependencies for sge, antares3 and open datacube
    apt-get install -y nfs-common openssh-server openjdk-8-jre xsltproc apache2 git htop postgresql-client \
    python-software-properties \
    libssl-dev \
    libffi-dev \
    python3-dev \
    python3-pip \
    python3-setuptools
    pip3 install --upgrade pip==9.0.3
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
    ##Create directories for antares3 and locale settings for open datacube
    mkdir -p /home/ubuntu/git && mkdir -p /home/ubuntu/sandbox
    echo "alias python=python3" >> /home/ubuntu/.bash_aliases
    #dependencies for antares3 & datacube
    pip3 install numpy && pip3 install cloudpickle && pip3 install GDAL==$(gdal-config --version) --global-option=build_ext --global-option='-I/usr/include/gdal' && pip3 install rasterio==1.0a12 --no-binary rasterio && pip3 install scipy
    pip3 install sklearn
    pip3 install lightgbm
    pip3 install fiona --no-binary fiona
    pip3 install django
    #datacube:
    pip3 install datacube==1.6rc1


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
    source /home/ubuntu/.profile
    queue_name=$1
    slots=$2
    type_value=$type_value
    region=$region
    qconf -am ubuntu
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


Once bash script was created unmount the shared volume:

.. code-block:: bash

    sudo umount $mount_point


You can use this instance to create AMI of AWS `Create an AMI from an Amazon EC2 Instace`_ 


2. Configure an Autoscaling group of AWS using AMI
  

Once created an AMI of AWS from previous step, use the following bash script to configure instances using `Auto Scaling Groups`_ service of AWS.


.. attention:: 

    Open Datacube supports NETCDF CF and S3 drivers for storage (see `Open DataCube Ingestion Config`_). Different software dependencies are required for different drivers. Choose one of the drivers supported by Open DataCube according to your application and select appropiate bash script to configure the autoscaling group. 


\* NETCDF CF driver of Open Datacube

.. note:: 

    Modify variables ``region``, ``name_instance`` and ``type_value`` with your own configuration. Here instances are tagged with **Key** ``Type`` and **Value** ``Node-dask-sge`` so we can use `RunCommand`_ service of AWS to execute bash scripts (for example) on instances with this tag.

.. code-block:: bash

    #!/bin/bash
    region=<region>
    name_instance=conabio-dask-sge-node
    type_value=Node-dask-sge
    ##Tag instances of type node
    INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
    PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
    aws ec2 create-tags --resources $INSTANCE_ID --tag Key=Name,Value=$name_instance-$PUBLIC_IP --region=$region
    ##Next line is useful so RunCommand can execute bash scripts (for example) on instances with Key=Type, Value=$type_value
    aws ec2 create-tags --resources $INSTANCE_ID --tag Key=Type,Value=$type_value --region=$region
    echo "export region=$region" >> /home/ubuntu/.profile
    echo "export type_value=$type_value" >> /home/ubuntu/.profile
    ##Uncomment next line if you want to install Antares3 on your AutoScalingGroup
    #su ubuntu -c "pip3 install --user git+https://github.com/CONABIO/antares3.git@develop"


\* S3 driver of Open Datacube
  
.. note:: 

    Modify variables ``region``, ``name_instance`` and ``type_value`` with your own configuration. Here instances are tagged with **Key** ``Type`` and **Value** ``Node-dask-sge`` so we can use `RunCommand`_ service of AWS to execute bash scripts (for example) on instances with this tag.


   
.. code-block:: bash

    #!/bin/bash
    region=<region>
    name_instance=conabio-dask-sge-node
    type_value=Node-dask-sge
    ##Tag instances of type node
    INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
    PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
    aws ec2 create-tags --resources $INSTANCE_ID --tag Key=Name,Value=$name_instance-$PUBLIC_IP --region=$region
    ##Next line is useful so RunCommand can execute bash scripts (for example) on instances with Key=Type, Value=$type_value
    aws ec2 create-tags --resources $INSTANCE_ID --tag Key=Type,Value=$type_value --region=$region
    echo "export region=$region" >> /home/ubuntu/.profile
    echo "export type_value=$type_value" >> /home/ubuntu/.profile
    /bin/bash -c "alias python=python3 && pip3 install boto3 && pip3 install SharedArray && pip3 install pathos && pip3 install zstandard"
    ##Uncomment next line if you want to install Antares3 on your AutoScalingGroup
    #su ubuntu -c "pip3 install --user git+https://github.com/CONABIO/antares3.git@develop"  


**Example using** `RunCommand`_ **service of AWS with Tag Name and Tag Value**

.. image:: https://dl.dropboxusercontent.com/s/kubf3ibnuv5axx4/aws_runcommand_sphix_docu.png?dl=0
    :width: 600


Setting DataBase
^^^^^^^^^^^^^^^^

AWS provide a managed relational database service `Amazon Relational Database Service (RDS)`_ with several database instance types and a `PostgreSQL`_  database engine.


**0. Prerequisites**

\* Configure `Amazon Relational Database Service (RDS)`_  with `PostgreSQL`_  version 9.5 + with properly `Amazon RDS Security Groups`_ and subnet group for the RDS configured (see `Tutorial Create an Amazon VPC for Use with an Amazon RDS DB Instance`_)


\* Open Datacube supports NETCDF CF and S3 drivers for storage (see `Open DataCube Ingestion Config`_). Different software dependencies are required for different drivers. Choose one of the drivers supported by Open DataCube according to your application. For NETCDF CF we use `Amazon Elastic File System`_ and for S3 driver we use `Amazon S3`_ . 

.. note:: 

	If S3 driver for storage of Open DataCube is selected, you need to create a bucket on S3. `Boto3 Documentation`_ and AWS suggests as a best practice using `IAM Roles for Amazon EC2`_ to access this bucket. See `Best Practices for Configuring Credentials`_.


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



