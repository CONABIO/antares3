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

Select an instance with AMI ``Ubuntu 16.04 LTS``

The following bash script can be used in **User data** configuration of an instance to:

	* Install AWS cli and package to use RunCommand service of EC2 (RunCommand service is not a mandatory installation neither for antares3, Sun Grid Engine nor datacube).
	* Tag your instance with name defined in ``name_instance``.
	* Install dependencies for Sun Grid Engine, antares3 and datacube.


(modify with your appropiate region of AWS on variable ``region`` and tagging for your instance at ``name_instance`` variable):

.. code-block:: bash

	#!/bin/bash
	#To create AMI of AWS for master and nodes:
	#variables:
	region=us-west-2
	name_instance=conabio-dask-sge
	#awscli
	apt-get update
	apt-get install -y awscli
	#tag instance
	INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
	PUBLIC_IP_LOCAL=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)
	PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
	aws ec2 create-tags --resources $INSTANCE_ID --tag Key=Name,Value=$name_instance-$PUBLIC_IP --region=$region
	#dependencies for sge, antares3 and datacube
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
	#for RunCommand service of EC2
	wget https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/debian_amd64/amazon-ssm-agent.deb
	dpkg -i amazon-ssm-agent.deb
	systemctl enable amazon-ssm-agent
	#for web sge 
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
	#install gridengine non interactively
	export DEBIAN_FRONTEND=noninteractive
	apt-get install -q -y gridengine-client gridengine-exec gridengine-master
	/etc/init.d/gridengine-master restart
	service apache2 restart
	#python virtualenv
	pip install --upgrade pip
	pip install virtualenv virtualenvwrapper
	pip3 install virtualenv virtualenvwrapper
	# Install spatial libraries
	add-apt-repository -y ppa:ubuntugis/ubuntugis-unstable && apt-get -qq update
	apt-get install -y \
	    netcdf-bin \
	    libnetcdf-dev \
	    ncview \
	    libproj-dev \
	    libgeos-dev \
	    gdal-bin \
	    libgdal-dev
	#dask distributed
	pip install dask distributed --upgrade
	pip3 install dask distributed --upgrade
	pip install bokeh
	pip3 install bokeh
	#missing package for datacube:
	pip3 install python-dateutil
	#Shared volume
	mkdir /LUSTRE_compartido
	#directories for antares3 and locale settings for datacube
	mkdir -p /home/ubuntu/.virtualenvs
	mkdir -p /home/ubuntu/git && mkdir -p /home/ubuntu/sandbox
	echo 'source /usr/local/bin/virtualenvwrapper.sh' >> /home/ubuntu/.bash_aliases
	echo "alias python=python3" >> /home/ubuntu/.bash_aliases
	echo "export LC_ALL=C.UTF-8" >> /home/ubuntu/.profile
	echo "export LANG=C.UTF-8" >> /home/ubuntu/.profile
	#setting variable mount_point
	echo "export mount_point=/LUSTRE_compartido" >> /home/ubuntu/.profile



MPI
^^^

Coming Soon


.. code-block:: bash

    echo "hello world"


another line

`url <https://www.gob.mx/conabio>`_


