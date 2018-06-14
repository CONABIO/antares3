import json

from shapely.geometry import shape
from sklearn.metrics import precision_score as user_acc
from sklearn.metrics import recall_score as prod_acc
from sklearn.metrics import accuracy_score, confusion_matrix
from django.db import connection

from madmex.models import Country, Region
from madmex.util.db import get_label_encoding

def prepare_validation(fc_valid, fc_test, valid_field=None, test_field=None):
    """Generate area weighted confusion matrix

    Generate the various vectors required to produce area weighted validation metrics
    (y_true, y_pred, weight, labels). Weight is simply the area of intersection between
    each pair of intersecting polygons from the test and validation features collections
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
        >>> prepare_validation(fc_validation, fc_test, 'value', 'value')

    Returns:
        Tupple: Array of 3 lists (y_true, y_pred, weight)
    """
    if valid_field is not None and test_field is not None:
        # Build list of (geometry, value) tuples for both feature collections
        geom_list_valid = [(shape(x['geometry']), x['properties'][valid_field]) for x in fc_valid]
        geom_list_test = [(shape(x['geometry']), x['properties'][test_field]) for x in fc_test]
    else:
        geom_list_valid = [(shape(x[0]), x[1]) for x in fc_valid]
        geom_list_test = [(shape(x[0]), x[1]) for x in fc_test]
    results = []
    for v in geom_list_valid:
        for t in geom_list_test:
            if v[0].intersects(t[0]):
                # The area used for weighting is multiplied by 1000000 to approximate hectares (more friendly conf matrix)
                results.append((v[1], t[1], v[0].intersection(t[0]).area * 1000000))
    y_true, y_pred, weight = zip(*results)
    return (y_true, y_pred, weight)


def validate(y_true, y_pred, sample_weight=None, scheme=None):
    """Compute user's and producer's accuracy for each class and overall accuracy

    Args:
        y_true (list, array): 1D array-like list of truth labels
        y_pred (list, array): 1D array-like list of estimated targets
        sample_weight (list, array): See sklearn.metrics
        scheme (str): Name of the classification scheme

    Return:
        dict: A dictionary organizing the accuracy information
    """
    labels = list(set(y_true + y_pred))
    pa = prod_acc(y_true=y_true, y_pred=y_pred, average=None,
                  labels=labels, sample_weight=sample_weight)
    ua = user_acc(y_true=y_true, y_pred=y_pred, average=None,
                  labels=labels, sample_weight=sample_weight)
    cm = confusion_matrix(y_true=y_true, y_pred=y_pred,
                          labels=labels, sample_weight=sample_weight)
    acc_dict = {}
    acc_dict['users_accuracy'] = dict(zip(labels, ua))
    acc_dict['producers_accuracy'] = dict(zip(labels, pa))
    acc_dict['confusion_matrix'] = cm.tolist()
    acc_dict['overall_accuracy'] = accuracy_score(y_true=y_true, y_pred=y_pred,
                                                  sample_weight=sample_weight)
    acc_dict['numeric_labels'] = labels
    if scheme is not None:
        acc_dict['label_encoding'] = get_label_encoding(scheme, inverse=True)
    return acc_dict


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


def pprint_val_dict(d):
    """Prints the dictionary returned by madmex.validation.validate as a nicely formated table

    Args:
        d (dict): The dictionary returned by madmex.validation.validate()

    Return:
        This function is used for its side effect of print a dictionary as a table
    """
    print('{:<15} {:<20} {:<20} {:<50}'.format('Numeric code','User\'s Accuracy','Producer\'s Accuracy','Class Name'))
    for code in d['users_accuracy'].keys():
        print("{:<15} {:<20.2f} {:<20.2f} {:<50}".format(code,
                                                         d['users_accuracy'][code],
                                                         d['producers_accuracy'][code],
                                                         d['label_encoding'][code]))
    print('-----')
    print('Overall Accuracy: %.2f' % d['overall_accuracy'])
    print('\n------')
    print('Confusion matrix')
    row_format = '{:<6}' + ' {:<10.0f}'*len(d['numeric_labels'])
    print(row_format.format('   ', *d['numeric_labels']))
    for i, row in enumerate(d['confusion_matrix']):
        print(row_format(d['numeric_labels'][i], *row))



def db_log():
    """Log the results of a validation to the database

    Args:

    """
    pass
