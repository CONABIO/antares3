from shapely.geometry import shape
from sklearn.metrics import confusion_matrix

from madmex.models import Country, Region

def validate(fc_valid, fc_test, valid_field, test_field):
    """Generate area weighted confusion matrix

    Generate an area weighted confusion matrix given 2 feature collections of
    polygon or multipolygon geometries
    Both feature collections must be in the same CRS. Note that an equal area CRS
    should be preferred for this type of operations.

    Args:
        fc_valid (list): The feature collection containing validation polygons
        fc_test (list): The feature collection containing test polygons
        valid_field (str): Name of the field containing the validation values
        test_field (str): Name of the field containing the test values

    Example:
        >>> import os, json
        >>> from madmex.validation import validate

        >>> with open(os.path.userexpand('~/git/antares3/tests/data/validation.geojson')) as src:
        >>>     fc = json.load(src)['features']

        >>> fc_test = [x for x in fc if x['properties']['set'] == 'test']
        >>> fc_validation = [x for x in fc if x['properties']['set'] == 'validation']
        >>> validate(fc_validation, fc_test, 'value', 'value')

    Returns:
        Tupple: Array of labels and confusion matrix
    """
    pass
    # Build list of (geometry, value) tuples for both feature collections
    geom_list_valid = [(shape(x['geometry']), x['properties'][valid_field]) for x in fc_valid]
    geom_list_test = [(shape(x['geometry']), x['properties'][test_field]) for x in fc_test]
    unique_labels = list(set([x[1] for x in geom_list_valid] + [x[1] for x in geom_list_test]))
    results = []
    for v in geom_list_valid:
        for t in geom_list_test:
            if v[0].intersects(t[0]):
                results.append((v[1], t[1], v[0].intersection(t[0]).area))
    y_true, y_pred, weight = zip(*results)
    mat = confusion_matrix(y_true=y_true, y_pred=y_pred, sample_weight=weight,
                           labels=unique_labels)
    return (unique_labels, mat)

def pprint_conf(matrix, scheme):
    pass


def query_validation_intersect(validation_set, test_set, region=None):
    """Query intersecting records from the validation and the predictClassification database table

    validation_set and test_set must exist in the ValidClassification and PredictClassification
    respectively

    Args:
        validation_set (str): Name/unique identifier of the validation set to use
        test_set (str): Name/unique identifier of the data to validate. Must be present
            in the PredictClassification table of the database
        region (str): Optional region withing which to query the data. Specified as
            iso country code (Country table) or region name (Region table)

    Return:
        tuple: A tuple of two feature collections corresponding to the validation
        dataset and the spatially intersecting records of the test dataset (fc_valid, fc_test)
        For both feature collections, attribute values are written to the ```value``
        property
    """
    # Create temp table with validation geometries filtered by name and optionally by region (geom, value)
    # Get that table converting to geojson on the fly
    # Query the PredictClassification data that intersect with the validation data (st_asgeojson(the_geom), value)
    q_0 = """
CREATE TEMP TABLE validation AS
SELECT
    public.madmex_validobject.the_geom AS geom,
    public.madmex_tag.numeric_code AS tag
FROM
    public.madmex_validclassification
INNER JOIN
    public.madmex_validobject ON public.madmex_validclassification.valid_object_id = public.madmex_validobject.id
    AND
    st_intersects(public.madmex_validobject.the_geom, st_geometryFromText(%s, 4326))
    AND
    public.madmex_validclassification.valid_set = %s
INNER JOIN
    public.madmex_tag ON public.madmex_validclassification.valid_tag_id = public.madmex_tag.id;
    """
    if region is not None:
        # Query country or region contour
        try:
            region = Country.objects.get(name=region).the_geom
        except Country.DoesNotExist:
            region = Region.objects.get(name=region).the_geom

def db_log():
    """Log the results of a validation to the database

    Args:

    """
    pass
