*************
Setup cluster
*************


Local
=====

Coming soon


Cloud
=====


Amazon Web Services
-------------------


Sun Grid Engine
^^^^^^^^^^^^^^^

*0. Prerequisites*

\* Configure `Amazon Virtual Private Cloud`_ on AWS with properly `VPCs and Subnets`_ configured according to your application.

.. _VPCs and Subnets: https://docs.aws.amazon.com/AmazonVPC/latest/UserGuide/VPC_Subnets.html

.. _Amazon Virtual Private Cloud: https://aws.amazon.com/vpc/

\* Configure `Security Groups for Your VPC`_  with ports 6444 TCP and 6445 UDP for communication within instances via SGE and port 80 for web SGE, port 2043 for `Amazon Elastic File System`_ service on AWS and port 22 to ssh to instances from your machine.

.. _Security Groups for Your VPC: https://docs.aws.amazon.com/AmazonVPC/latest/UserGuide/VPC_SecurityGroups.html

\* Configure `Amazon Elastic File System`_ service on AWS (shared volume via Network File System -NFS-).


\* (Not mandatory but useful) Configure an `Elastic IP Addresses`_  on AWS. Master node will have this elastic ip.


1. Create AMI of AWS from bash cript.

Select an instance with AMI ``Ubuntu 16.04 LTS``

The following bash script can be used in **User data** configuration of an instance to:

\* Install AWS cli.

\* Install package ``amazon-ssm-agent.deb`` to use `RunCommand`_ service of EC2. 

.. note:: 
 
  RunCommand service is not a mandatory installation for antares3, Open Datacube nor SGE, we use it for it's simplicity to execute commands on all of the instances (see  `RunCommand`_). You can use instead `clusterssh`_  or other tool for cluster management.

.. _clusterssh: https://github.com/duncs/clusterssh

.. _RunCommand: https://docs.aws.amazon.com/systems-manager/latest/userguide/execute-remote-commands.html

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
	##Dependencies for sge, antares3 and open datacube
	apt-get install -y nfs-common openssh-server openjdk-8-jre xsltproc apache2 git htop postgresql \
	python-software-properties \
	libssl-dev \
	libffi-dev \
	python3-dev \
	python3-pip \
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
	pip3 install dask distributed --upgrade
	pip3 install bokeh
	##Install missing package for open datacube:
	pip3 install --upgrade python-dateutil
	##Create shared volume
	mkdir $shared_volume
	##Create directories for antares3 and locale settings for open datacube
	mkdir -p /home/ubuntu/.virtualenvs
	mkdir -p /home/ubuntu/git && mkdir -p /home/ubuntu/sandbox
	echo 'source /usr/local/bin/virtualenvwrapper.sh' >> /home/ubuntu/.bash_aliases
	echo "alias python=python3" >> /home/ubuntu/.bash_aliases
	echo "export LC_ALL=C.UTF-8" >> /home/ubuntu/.profile
	echo "export LANG=C.UTF-8" >> /home/ubuntu/.profile
	##Set variable mount_point
	echo "export mount_point=$shared_volume" >> /home/ubuntu/.profile


2. Configure an Autoscaling group of AWS using AMI of previous step.

Once created the AMI of step 1, use the following bash script to configure instances from an autoscaling group of AWS with AMI created in first step.

.. attention:: 

	Open Datacube supports NETCDF CF and S3 drivers for storage (see `Open DataCube Ingestion Config`_). Different dependencies are required for different drivers. Choose one of the drivers supported by OpendataCube according to your application and select appropiate bash script to configure the autoscaling group. 

.. _Open DataCube Ingestion Config: https://datacube-core.readthedocs.io/en/latest/ops/ingest.html#ingestion-config

\* NETCDF CF driver of Open Datacube

.. note:: 

	Modify variables ``region``, ``name_instance`` and ``type_value`` with your own configuration.

.. code-block:: bash

	#!/bin/bash
	region=<region>
	name_instance=conabio-dask-sge-node
	type_value=Node-dask-sge
	##Tag instances of type node
	INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
	PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
	aws ec2 create-tags --resources $INSTANCE_ID --tag Key=Name,Value=$name_instance-$PUBLIC_IP --region=$region
	aws ec2 create-tags --resources $INSTANCE_ID --tag Key=Type,Value=$type_value --region=$region
	cd /home/ubuntu/git && git clone https://github.com/CONABIO/antares3.git && cd antares3 && git checkout -b develop origin/develop
	##Install open datacube and antares3
	/bin/bash -c "alias python=python3 && pip3 install numpy && pip3 install cloudpickle && pip3 install GDAL==$(gdal-config --version) --global-option=build_ext --global-option='-I/usr/include/gdal' && pip3 install rasterio==1.0a12 && pip3 install scipy && pip3 install git+https://github.com/CONABIO/datacube-core.git@release-1.5 && cd /home/ubuntu/git/antares3 && pip3 install -e ."

\* S3 driver of Open Datacube
  
.. note:: 

	Modify variables ``region``, ``name_instance`` and ``type_value`` with your own configuration.

   
.. code-block:: bash

	#!/bin/bash
	region=<region>
	name_instance=conabio-dask-sge-node
	type_value=Node-dask-sge
	##Tag instances of type node
	INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
	PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
	aws ec2 create-tags --resources $INSTANCE_ID --tag Key=Name,Value=$name_instance-$PUBLIC_IP --region=$region
	aws ec2 create-tags --resources $INSTANCE_ID --tag Key=Type,Value=$type_value --region=$region
	cd /home/ubuntu/git && git clone https://github.com/CONABIO/antares3.git && cd antares3 && git checkout -b develop origin/develop
	##Install open datacube and antares3
	/bin/bash -c "alias python=python3 && pip3 install numpy && pip3 install cloudpickle && pip3 install GDAL==$(gdal-config --version) --global-option=build_ext --global-option='-I/usr/include/gdal' && pip3 install rasterio==1.0a12 && pip3 install scipy && pip3 install boto3 && pip3 install SharedArray && pip3 install pathos && pip3 install zstandard && pip3 install git+https://github.com/CONABIO/datacube-core.git@develop && cd /home/ubuntu/git/antares3 && pip3 install -e ."


3. `RunCommand`_ on an instance (doesn't matter which one).

Run the following bash script using `RunCommand`_ or login to an instance to run it. The instance where  the bash script is executed will be the **master node** of our cluster.
 
We use an elastic IP provided by AWS for the node that will be the **master node**, so change variable ``eip`` according to your ``Allocation ID`` (see `Elastic IP Addresses`_ ).
 
 .. _Elastic IP Addresses: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/elastic-ip-addresses-eip.html

We also use Elastic File System of AWS (shared file storage, see `Amazon Elastic File System`_), which multiple Amazon EC2 instances running in multiple Availability Zones (AZs) within the same region can access it. Change variable ``efs_dns`` according to your ``DNS name``.
 
 .. _Amazon Elastic File System: https://aws.amazon.com/efs/ 

.. note:: 

	Modify variables ``region``, ``name_instance``, ``efs_dns``, ``queue_name`` and ``slots`` with your own configuration. Variable ``type_value`` has the value configured in step **2. Configure an Autoscaling group of AWS**. Elastic IP and EFS are not mandatory. You can use a NFS server instead  of EFS, for example.

.. code-block:: bash

	#!/bin/bash
	##variables
	eip=<Allocation ID of Elastic IP>
	region=<region>
	name_instance=conabio-dask-sge-master
	efs_dns=<DNS name of EFS>
	type_value=Node-dask-sge
	source /home/ubuntu/.profile
	##Name of the queue that will be used by dask-scheduler and dask-workers
	queue_name=dask-queue.q
	##We use one slot for every instance
	slots=1
	##Mount EFS according to variable mount_point defined on bash script of step 1
	mount -t nfs4 -o nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2 $efs_dns:/ $mount_point
	##Tag instance
	INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
	PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
	PUBLIC_IP_LOCAL=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)
	aws ec2 associate-address --instance-id $INSTANCE_ID --allocation-id $eip --region $region
	aws ec2 create-tags --resources $INSTANCE_ID --tag Key=Name,Value=$name_instance-$PUBLIC_IP --region=$region
	##commands for SGE
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

   

4. `RunCommand`_ on nodes with **Key** Type and **Value** Node-dask-sge.
 
Use `RunCommand`_ service of AWS to execute following bash script in all instances with **Key** ``Type``, **Value** ``Node-dask-sge`` configured in step **2. Configure an Autoscaling group of AWS**, or use a tool for cluster management like `clusterssh`_ . 


Modify variables ``region``, ``efs_dns`` with your own configuration.

.. code-block:: bash

	#!/bin/bash
	source /home/ubuntu/.profile
	efs_dns=<DNS name of EFS>
	region=<region>
	mount -t nfs4 -o nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2 $efs_dns:/ $mount_point
	master_dns=$(cat $mount_point/ip_master.txt)
	##Ip for sun grid engine master
	echo $master_dns > /var/lib/gridengine/default/common/act_qmaster
	/etc/init.d/gridengine-exec restart


5. Run SGE commands to init cluster.
   
Login to master node and execute:

.. code-block:: bash

	# Start dask-scheduler on master node. The file scheduler.json will be created on $mount_point (shared_volume) of EFS
	qsub -b y -l h=$HOSTNAME dask-scheduler --scheduler-file $mount_point/scheduler.json

If your group of autoscaling has 3 nodes, then execute:

.. code-block:: bash

	# Start 2 dask-worker processes in an array job pointing to the same file
	qsub -b y -t 1-2 dask-worker --scheduler-file $mount_point/scheduler.json

You can view the web SGE on the page:

**<public DNS of master>/qstat/qstat.cgi**

and the state of your cluster with `bokeh`_  at:

.. _bokeh: https://bokeh.pydata.org/en/latest/

**<public DNS of master>:8787**

or

**<public DNS of worker>:8789** 

6. Run an example.
   
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
	-285
	total
	<Future: status: finished, type: int, key: sum-ccdc2c162ed26e26fc2dc2f47e0aa479>
	client.gather(A)
	[0, 1, 4, 9, 16, 25, 36, 49, 64, 81]


7. Stop cluster.

On master or node execute:

.. code-block:: bash

	qdel 1 2



MPI
^^^

Coming Soon




