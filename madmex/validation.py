import json

from shapely.geometry import shape
from sklearn.metrics import confusion_matrix
from django.db import connection

from madmex.models import Country, Region

def validate(fc_valid, fc_test, valid_field=None, test_field=None):
    """Generate area weighted confusion matrix

    Generate an area weighted confusion matrix given 2 feature collections of
    polygon or multipolygon geometries
    Both feature collections must be in the same CRS. Note that an equal area CRS
    should be preferred for this type of operations.

    Args:
        fc_valid (list): The feature collection containing validation polygons
            Can also be a list of (geometry, value) tupples in case any of valid_field
            and test_fields are specified
        fc_test (list): The feature collection containing test polygons
            Can also be a list of (geometry, value) tupples in case any of valid_field
            and test_fields are specified
        valid_field (str): Name of the field containing the validation values.
            Defaults to None in which case fc_valid and fc_test are assumed to be
            lists of (geometry, value) tupples.
        test_field (str): Name of the field containing the test values
            Defaults to None in which case fc_valid and fc_test are assumed to be
            lists of (geometry, value) tupples.

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
    if valid_field is not None and test_field is not None:
        # Build list of (geometry, value) tuples for both feature collections
        geom_list_valid = [(shape(x['geometry']), x['properties'][valid_field]) for x in fc_valid]
        geom_list_test = [(shape(x['geometry']), x['properties'][test_field]) for x in fc_test]
    else:
        geom_list_valid = [(shape(x[0]), x[1]) for x in fc_valid]
        geom_list_test = [(shape(x[0]), x[1]) for x in fc_test]
    unique_labels = list(set([x[1] for x in fc_valid] + [x[1] for x in fc_test]))
    results = []
    for v in geom_list_valid:
        for t in geom_list_test:
            if v[0].intersects(t[0]):
                # The area used for weighting is multiplied by 1000000 to approximate hectares (more friendly conf matrix)
                results.append((v[1], t[1], v[0].intersection(t[0]).area * 1000000))
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
        tuple: A tuple (fc_valid, fc_test) of two list of (geometry, value) tupples
    """
    # Create temp table with validation geometries filtered by name and optionally by region (geom, value)
    # Get that table converting to geojson on the fly
    # Query the PredictClassification data that intersect with the validation data (st_asgeojson(the_geom), value)
    q0_sp_filter = """
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

    q0 = """
CREATE TEMP TABLE validation AS
SELECT
    public.madmex_validobject.the_geom AS geom,
    public.madmex_tag.numeric_code AS tag
FROM
    public.madmex_validclassification AS vc
INNER JOIN
    public.madmex_validobject ON vc.valid_object_id = public.madmex_validobject.id
    AND
    vc.valid_set = %s
INNER JOIN
    public.madmex_tag ON vc.valid_tag_id = public.madmex_tag.id;
    """

    q1 = """
SELECT
    st_asgeojson(geom, 6),
    tag
FROM
    validation;
    """

    q2 = """
SELECT
    st_asgeojson(public.madmex_predictobject.the_geom, 6),
    public.madmex_tag.numeric_code
FROM
    public.madmex_predictclassification AS cl
INNER JOIN
    public.madmex_predictobject ON cl.predict_object_id = public.madmex_predictobject.id
INNER JOIN
    validation ON st_intersects(validation.geom, public.madmex_predictobject.the_geom)
INNER JOIN
    public.madmex_tag ON cl.tag_id = public.madmex_tag.id
WHERE
    cl.name = %s;
    """
    if region is not None:
        # Query country or region contour
        try:
            region = Country.objects.get(name=region).the_geom
        except Country.DoesNotExist:
            region = Region.objects.get(name=region).the_geom

    with connection.cursor() as c:
        if region is None:
            c.execute(q0, [validation_set])
        else:
            c.execute(q0_sp_filter, [region.wkt, validation_set])
        c.execute(q1)
        val_qs = c.fetchall()
        c.execute(q2, [test_set])
        pred_qs = c.fetchall()

    val_fc = [(json.loads(x[0]), x[1]) for x in val_qs]
    pred_fc = [(json.loads(x[0]), x[1]) for x in pred_qs]
    return (val_fc, pred_fc)



def db_log():
    """Log the results of a validation to the database

    Args:

    """
    pass
