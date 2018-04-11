************
Installation
************

Activate a ``python3`` virtual environmemt and run:

.. code-block:: bash

    # Install antares and all its dependencies (square brackets need to be escaped in zsh)
    pip install git+https://github.com/CONABIO/antares3.git#egg=antares3[all]


Cloud Deployment
================

Amazon Web Services
-------------------

Sun Grid Engine
^^^^^^^^^^^^^^^


Init Cluster, example with one master and two nodes. Install Open DataCube and Antares3 in all nodes.
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""" 

Using instances of `Auto Scaling Groups`_ configured in `Dependencies-Cloud Deployment`_ in step 2 we have to configure SGE queue on master node and register nodes on this queue.
   
**Asing Elastic IP to master node and create Sun Grid Engine queue**
   
Run the following bash script using `RunCommand`_ or login to an instance from your autoscaling group to run it (doesn't matter which one). The instance where  the bash script is executed will be the **master node** of our cluster.
 
We use an elastic IP provided by AWS for the node that will be the **master node**, so change variable ``eip`` according to your ``Allocation ID`` (see `Elastic IP Addresses`_).
 

We also use Elastic File System of AWS (shared file storage, see `Amazon Elastic File System`_), which multiple Amazon EC2 instances running in multiple Availability Zones (AZs) within the same region can access it. Change variable ``efs_dns`` according to your ``DNS name``.
 

.. note:: 

    Modify variables ``eip``, ``name_instance``, ``efs_dns``, ``queue_name`` and ``slots`` with your own configuration.  Elastic IP and EFS are not mandatory. You can use a NFS server instead  of EFS, for example.

.. code-block:: bash

    #!/bin/bash
    ##variables
    source /home/ubuntu/.profile
    eip=<Allocation ID of Elastic IP>
    name_instance=conabio-dask-sge-master
    efs_dns=<DNS name of EFS>
    ##Name of the queue that will be used by dask-scheduler and dask-workers
    queue_name=dask-queue.q
    ##We use one slot for every instance
    slots=1
    region=$region
    type_value=$type_value
    ##Mount shared volume
    mount -t nfs4 -o nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2 $efs_dns:/ $mount_point
    ##Tag instance
    INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
    PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
    ##Assing elastic IP where this bash script is executed
    aws ec2 associate-address --instance-id $INSTANCE_ID --allocation-id $eip --region $region
    ##Tag instance where this bash script is executed
    aws ec2 create-tags --resources $INSTANCE_ID --tag Key=Name,Value=$name_instance-$PUBLIC_IP --region=$region
    ##Execute bash script create-dask-sge-queue already created on Dependencies-Cloud Deployment
    bash $mount_point/create-dask-sge-queue.sh $queue_name $slots

   
**Restart gridengine-exec on nodes and install OpenDataCube and Antares3**
 

Use `RunCommand`_ service of AWS to execute following bash script in all instances with **Key** ``Type``, **Value** ``Node-dask-sge`` already configured in `Dependencies-Cloud Deployment`_ in step 2, or use a tool for cluster management like `clusterssh`_ . (You can also have the line that install OpenDataCube and Antares3 on the bash script configured in `Dependencies-Cloud Deployment`_ in step 2 in instances of AutoScalingGroup)


.. code-block:: bash

    #!/bin/bash
    source /home/ubuntu/.profile
    efs_dns=<DNS name of EFS>
    mount -t nfs4 -o nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2 $efs_dns:/ $mount_point
    ##Ip for sun grid engine master
    master_dns=$(cat $mount_point/ip_master.txt)
    echo $master_dns > /var/lib/gridengine/default/common/act_qmaster
    /etc/init.d/gridengine-exec restart
    ##Install open datacube and antares3
    /bin/bash -c "alias python=python3 && pip3 install git+https://github.com/CONABIO/datacube-core.git@develop && cd /home/ubuntu/git/antares3 && pip3 install -e ."


**Run SGE commands to init cluster.**
   
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


**<public DNS of master>:8787**

or

**<public DNS of worker>:8789** 

**Run an example.**
   
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


.. note::

    To stop cluster on master or node execute:

    .. code-block:: bash

        qdel 1 2



MPI
"""

Coming Soon


.. _Auto Scaling Groups: https://docs.aws.amazon.com/autoscaling/ec2/userguide/AutoScalingGroup.html

.. _bokeh: https://bokeh.pydata.org/en/latest/

.. _clusterssh: https://github.com/duncs/clusterssh

.. _RunCommand: https://docs.aws.amazon.com/systems-manager/latest/userguide/execute-remote-commands.html

.. _Open DataCube Ingestion Config: https://datacube-core.readthedocs.io/en/latest/ops/ingest.html#ingestion-config

.. _Amazon Elastic File System: https://aws.amazon.com/efs/ 

.. _Elastic IP Addresses: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/elastic-ip-addresses-eip.html


