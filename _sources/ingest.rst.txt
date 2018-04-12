**************
Ingesting data
**************

Running large scale workflows requires that the data be ingested in the datacube. Ingested collections are reprojected to a common grid whose characteristics is defined by the user (coordinate reference system, resolution, tiling). The example below consists of ingesting a Surface reflectance Landsat 8 data downloaded from the espa platform.

Landsat 8 example
=================

Local
-----

These instructions assume you already have LAndsat 8 surface reflectance data downloaded from espa. Each individual scene should correspond to a folder in which there is at least:
- Surface reflectance bands
- A pixel_qa band
- A xml metadata file
  
.. code-block:: bash

    datacube -v product add ~/.config/madmex/indexing/landsat_8_espa_scenes.yaml
    antares prepare_metadata -p ~/data/landsat_8_espa -d landsat_espa -o ~/ls8_espa.yaml
    datacube -v dataset add ~/ls8_espa.yaml
    datacube ingest -c ~/.config/madmex/ingestion/ls8_espa_mexico.yaml --executor multiproc 3


Cloud deployment
----------------


.. attention:: 

	Open Datacube supports NETCDF CF and S3 drivers for storage (see `Open DataCube Ingestion Config`_). Different software dependencies are required for different drivers and different ``datacube ingest`` command.



Example in S3
^^^^^^^^^^^^^

It's assumed you have created a bucket in S3.

.. code-block:: bash

    
	datacube -v product add /home/ubuntu/.config/madmex/indexing/landsat_8_espa_scenes.yaml

	#right now is not dynamic, so copy and modify container entry of ls8_espa_mexico_s3.yaml with name of bucket. Next line is to copy already file created

	#cp /shared_volume/datacube/madmex_conf_files/ingestion/ls8_espa_mexico_s3.yaml /home/ubuntu/.config/madmex/ingestion/

	mkdir /home/ubuntudatacube

	antares prepare_metadata -p $mount_point/data/staging/landsat_8_data_downloaded/2017/Jalisco/ -d landsat_espa -o /home/ubuntu/datacube/ls8_espa.yaml

	datacube -v dataset add /home/ubuntu/datacube/ls8_espa.yaml

	datacube --driver s3 -v ingest -c /home/ubuntu/.config/madmex/ingestion/ls8_espa_mexico_s3.yaml --executor multiproc 2


























.. _Open DataCube Ingestion Config: https://datacube-core.readthedocs.io/en/latest/ops/ingest.html#ingestion-config
