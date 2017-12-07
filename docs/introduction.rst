Introduction
------------

The system has the following characteristics

- Flexibility
    - Capability to use various types of training datasets (vector, raster, etc)
    - Spatially decoupled model training and prediction (keep a library of trained model that can be used to predict land cover for any area given the availability of predictors)
- Scalability
    - Should be able to run on any system including a local machine, an institutional cluster, or an AWS cluster of n instances
    - Should be able to run on user defined subsets of the total study area (e.g. Run for a single Mexican state with a state specific classification scheme)
- Reproducibility
- User friendliness
    - Coherent interface with limited amount of entry points
    - Clear installation and usage instruction
- Efficiency (computing time and memory usage should be optimized)
- Modularity (it should be "easy" to extend and add (or remove) functionalities to the system)
    - Every step after data ingestion should be completely sensor independent
- Measurability
    - Rapidly and objectively assess accuracy of different classification or segmentation approaches