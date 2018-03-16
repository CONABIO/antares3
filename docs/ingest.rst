**************
Ingesting data
**************

Landsat 8 example
=================

These instructions assume you already have LAndsat 8 surface reflectance data downloaded from espa. Each individual scene should correspond to a folder in which there is at least:
- Surface reflectance bands
- A pixel_qa band
- A xml metadata file
  
.. code-block:: bash

    datacube -v product add ~/.config/madmex/indexing/landsat_8_espa_scenes.yaml
    antares prepare_metadata -p ~/data/landsat_8_espa -d landsat_espa -o ~/ls8_espa.yaml
    datacube -v dataset add ~/ls8_espa.yaml
    datacube ingest -c ~/.config/madmex/ingestion/ls8_espa_mexico.yaml --executor multiproc 3

