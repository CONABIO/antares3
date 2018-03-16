********************
Setup/first time use
********************

Initial setup of both ``datacube`` (used as backend for antares) and ``antares`` itself requires a few one time actions.

Datacube
========

.. code-block:: bash

    createdb datacube
    datacube -v system init

Check that datacube is properly setup by running

.. code-block:: bash

    datacube system check


Antares
=======

.. code-block:: bash

    antares conf_setup

This will create a ``madmex`` directory under ``~/.config/`` where ingestion files for all different suported dataset will be stored.