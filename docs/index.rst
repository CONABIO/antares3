*******
Antares
*******

*A python library for scalable satellite image analysis, from data dowload to production of national scale maps.*

``Antares`` is the name of the `CONABIO <https://www.gob.mx/conabio>`_ geopsatial engine. The project started under the name `MAD-Mex <http://madmex.conabio.gob.mx/>`_ (Monitoring Activity Data for the Mexican REDD+ program) a few years ago. Back then the objective was to produce national land cover and land cover change information for Mexico (some of the products produced by MAD-Mex can be visualized via the CONABIO `geoportal <http://www.conabio.gob.mx/informacion/gis/>`_ ). MAD-Mex has now evolved into antares, a scalable system that aims to be more generic and flexible geoprocessing engine.

``Antares`` heavily relies and uses `open data cube <https://github.com/opendatacube/datacube-core>`_. Other key libraries that make this system possible are `xarray <http://xarray.pydata.org/en/stable/>`_, `dask <https://dask.pydata.org/en/latest/>`_ and `distributed <http://distributed.readthedocs.io/en/latest/>`_.
 



.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: User guide

   dependencies
   install
   setup
   cli
   download
   ingest


.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Developer guide

   extend
   api

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Examples

   example_s2_land_cover
   example_api


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`