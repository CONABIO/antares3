****************
Downloading data
****************


``Antares`` allows automated data download from various sources like SciHub, Usgs or Espa.

See for instance the ``create_order`` and ``download_order`` command lines that allow a user to order on demand surface reflectance preprocessing of Landsat data and retrieve the data once its been processed by the espa system.

Create order
============

This command needs a span of time of interest and a polygon in the database for the spatial query. Additionally one can specify the amount of cloud cover to be present in the images as parameter.

.. code-block:: bash

    antares create_order --shape 'VNM' \
                         --start-date '2017-01-01' \
                         --end-date '2017-12-31' \
                         --landsat 8 \
                         --max-cloud-cover 10

Uppon success, this command will submit a petition to the USGS portal for them to preprocess and make the order available. This command will use the credentials in the antares configuration file. When the order is ready for download, an email will be received from the USGS portal and the other command can then be used.
