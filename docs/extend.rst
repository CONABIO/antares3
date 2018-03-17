********************
Extending the system
********************


Adding a new product or dataset
===============================

- Write a metadata parsing function on the model of `landsat_espa <https://github.com/CONABIO/antares3/blob/master/madmex/ingestion/landsat_espa.py>`_ or `srtm <https://github.com/CONABIO/antares3/blob/master/madmex/ingestion/srtm_cgiar.py>`_.
- Write a product description file and add it to ``madmex/conf/indexing``.
- Write an ingestion file and add it to ``madmex/conf/ingestion``.
- Document it in the ``prepare_metadata`` command line


Developping a recipe
====================

- Write the recipe function. The function should accept 4 arguments (``tile``, ``gwf``, ``center_dt``, ``path``). ``tile`` is a tuple as returned by ``gwd.list_cells()``, ``gwf`` is a ``GridWorkflow`` instance, ``center_dt`` is a ``datetime``, and ``path`` is a string. The function should write to a netcdf file and return the path (str) of the file created.
- Write a product configuration file and place it in ``madmex/conf/indexing``
- Add an entry to the ``RECIPES`` dictionary in ``madmex.recipes.__init__.py`` (product is the datacube product to query in the command line (``apply_recipe``), and that will be passed to the function through the ``tile`` argument)
- Add a meaningful example to the docstring of the ``apply_recipe`` command line.


Adding a new predictive model
=============================

Write a class named ``Model`` in a file named after the model you are implementing under ``madmex.modeling.supervised``. The new class must inherit from ``madmex.modeling.BaseModel``.


Adding a new segmentation algorithm
===================================

Coming soon