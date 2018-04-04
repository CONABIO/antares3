************
Cluster mode
************


Local
=====

Coming soon


Cloud
=====


Amazon Web Services
-------------------


Sun Grid Engine
^^^^^^^^^^^^^^^

1. Create AMI of AWS from bash cript.

Select an instance with AMI ``Ubuntu 16.04 LTS``

The following bash script can be used in **User data** configuration of an instance to:

\* Install AWS cli.

\* Install package ``amazon-ssm-agent.deb`` to use RunCommand service of EC2. 

.. note:: 
 
  RunCommand service is not a mandatory installation neither for antares3, Open Datacube nor SGE, we use it for it's simplicity to execute commands on all of the instances, see more at `RunCommand`_. You can use instead `clusterssh`_  or other tool for cluster management.

.. _clusterssh: https://github.com/duncs/clusterssh

.. _RunCommand: https://docs.aws.amazon.com/systems-manager/latest/userguide/execute-remote-commands.html

\* Tag your instance with **Key** ``Name`` and **Value** ``$name_instance``.

\* Install dependencies for SGE, antares3 and Open Datacube.

.. note:: 

	Modify variables ``region`` and ``name_instance`` with your own configuration.

.. code-block:: bash

	#!/bin/bash
	##Bash script to create AMI of AWS for master and nodes:
	##variables:
	region=us-west-2
	name_instance=conabio-dask-sge
	##Install awscli
	apt-get update
	apt-get install -y awscli
	##Tag instance
	INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
	PUBLIC_IP_LOCAL=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)
	PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
	aws ec2 create-tags --resources $INSTANCE_ID --tag Key=Name,Value=$name_instance-$PUBLIC_IP --region=$region
	##Dependencies for sge, antares3 and datacube
	apt-get install -y nfs-common openssh-server openjdk-8-jre xsltproc apache2 git htop postgresql \
	python-software-properties \
	libssl-dev \
	libffi-dev \
	python3-dev \
	python-pip \
	python3-pip \
	python-setuptools \
	python3-setuptools 
	service ssh start
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
	##Install python virtualenv
	pip install --upgrade pip
	pip install virtualenv virtualenvwrapper
	pip3 install virtualenv virtualenvwrapper
	##Install spatial libraries
	add-apt-repository -y ppa:ubuntugis/ubuntugis-unstable && apt-get -qq update
	apt-get install -y \
	    netcdf-bin \
	    libnetcdf-dev \
	    ncview \
	    libproj-dev \
	    libgeos-dev \
	    gdal-bin \
	    libgdal-dev
	##Install dask distributed
	pip install dask distributed --upgrade
	pip3 install dask distributed --upgrade
	pip install bokeh
	pip3 install bokeh
	##Install missing package for datacube:
	pip3 install --upgrade python-dateutil
	##Create shared volume
	mkdir /LUSTRE_compartido
	##Create directories for antares3 and locale settings for open datacube
	mkdir -p /home/ubuntu/.virtualenvs
	mkdir -p /home/ubuntu/git && mkdir -p /home/ubuntu/sandbox
	echo 'source /usr/local/bin/virtualenvwrapper.sh' >> /home/ubuntu/.bash_aliases
	echo "alias python=python3" >> /home/ubuntu/.bash_aliases
	echo "export LC_ALL=C.UTF-8" >> /home/ubuntu/.profile
	echo "export LANG=C.UTF-8" >> /home/ubuntu/.profile
	##Set variable mount_point
	echo "export mount_point=/LUSTRE_compartido" >> /home/ubuntu/.profile


2. Configure an Autoscaling group of AWS.

Once created the AMI of step 1, we use the following bash script to configure an autoscaling group tagged with **Key**: ``Type`` and **Value**: ``Node-dask-sge``. See `Tagging Autoscaling groups and Instances`_ 

.. _Tagging Autoscaling groups and Instances: https://docs.aws.amazon.com/autoscaling/ec2/userguide/autoscaling-tagging.html

.. attention:: 

	Open Datacube supports NETCDF CF and S3 drivers for storage (see `Open DataCube Ingestion Config`_). Different dependencies are required for different drivers. Choose one of the drivers supported by OpendataCube according to your application and select appropiate bash script to configure the autoscaling group. 

.. _Open DataCube Ingestion Config: https://datacube-core.readthedocs.io/en/latest/ops/ingest.html#ingestion-config

\* NETCDF CF driver of Open Datacube

.. note:: 

	Modify variables ``region`` and ``name_instance`` with your own configuration.

.. code-block:: bash

	#!/bin/bash
	region=us-west-2
	name_instance=conabio-dask-sge-node
	#To tag instances of type node
	INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
	PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
	aws ec2 create-tags --resources $INSTANCE_ID --tag Key=Name,Value=$name_instance-$PUBLIC_IP --region=$region
	cd /home/ubuntu/git && git clone https://github.com/CONABIO/antares3.git && cd antares3 && git checkout -b develop origin/develop
	/bin/bash -c "alias python=python3 && pip3 install numpy && pip3 install cloudpickle && pip3 install GDAL==$(gdal-config --version) --global-option=build_ext --global-option='-I/usr/include/gdal' && pip3 install rasterio==1.0a12 && pip3 install scipy && pip3 install git+https://github.com/CONABIO/datacube-core.git@release-1.5 && cd /home/ubuntu/git/antares3 && pip3 install -e ."

\* S3 driver of Open Datacube
  
.. note:: 

	Modify variables ``region`` and ``name_instance`` with your own configuration.

   
.. code-block:: bash

	#!/bin/bash
	region=us-west-2
	name_instance=conabio-dask-sge-node
	#To tag instances of type node
	INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
	PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
	aws ec2 create-tags --resources $INSTANCE_ID --tag Key=Name,Value=$name_instance-$PUBLIC_IP --region=$region
	cd /home/ubuntu/git && git clone https://github.com/CONABIO/antares3.git && cd antares3 && git checkout -b develop origin/develop
	/bin/bash -c "alias python=python3 && pip3 install numpy && pip3 install cloudpickle && pip3 install GDAL==$(gdal-config --version) --global-option=build_ext --global-option='-I/usr/include/gdal' && pip3 install rasterio==1.0a12 && pip3 install scipy && pip3 install boto3 && pip3 install SharedArray && pip3 install pathos && pip3 install zstandard && pip3 install git+https://github.com/CONABIO/datacube-core.git@develop && cd /home/ubuntu/git/antares3 && pip3 install -e ."




MPI
^^^

Coming Soon


.. code-block:: bash

    echo "hello world"


another line

`url <https://www.gob.mx/conabio>`_


