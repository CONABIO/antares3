import json

from sklearn.metrics import precision_score as user_acc
from sklearn.metrics import recall_score as prod_acc
from sklearn.metrics import accuracy_score, confusion_matrix
from django.db import connection
from madmex.models import PredictObject, ValidClassification, PredictClassification
from madmex.models import Country, Region
from madmex.util.db import get_label_encoding
from django.contrib.gis.geos.geometry import GEOSGeometry
from shapely.geometry import shape, mapping
from operator import itemgetter
from madmex.util.spatial import geometry_transform
import fiona
from fiona.crs import to_string
from madmex.overlay.conversions import valid_object_to_feature

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


def query_validation_intersect(id_dc_tile, validation_set, test_set, geometry_region=None):
    """Query intersecting records from the validation and the predictClassification database table
    validation_set and test_set must exist in the ValidClassification and PredictClassification
    respectively
    This function uses dask.distributed.Cluster.map() over a list of id's of segmentation files already registered
    in db PredictObject table related to name of prediction file and generated by arguments passed in command line.
    Works by datacube tile.

    Args:
        id_dc_tile (int): id of segmentation file registered in PredictObject table.
        validation_set (str): Name/unique identifier of the validation set to use
        test_set (str): Name/unique identifier of the data to validate. Must be present
            in the PredictClassification table of the database
        geometry_region (geom): Optional geometry of a region in a geojson-format

    Return:
        tuple: A tuple (fc_valid, fc_test) of two list of (geometry, value) tupples
    """
    seg = PredictObject.objects.filter(id=id_dc_tile)
    s3_path = seg[0].path
    poly = seg[0].the_geom
    #next lines to reproyect extent registered in DB 
    #TODO: register geometry of extent of each shapefile of segments of dc tile in lat long
    poly_geojson = poly.geojson
    geometry = json.loads(poly_geojson)
    proj4_out = '+proj=longlat'
    with fiona.open(s3_path) as src:
        crs = to_string(src.crs)
        geometry_proj = geometry_transform(geometry,proj4_out,crs_in=crs)
        poly_proj = GEOSGeometry(json.dumps(geometry_proj))
        qs_dc_tile = ValidClassification.objects.filter(valid_object__the_geom__contained=poly_proj,
                                                   valid_set=validation_set).prefetch_related('valid_object', 'valid_tag') 
    
        fc_qs = [valid_object_to_feature(x) for x in qs_dc_tile]
        if geometry_region is not None:
            shape_region=shape(geometry_region)
            fc_qs_in_region = [{'geometry': mapping(shape_region.intersection(shape(x['geometry']))),
                                'class': x['properties']['class']} for x in fc_qs if shape_region.intersects(shape(x['geometry']))]
            fc_qs = fc_qs_in_region
            fc_qs_in_region = None 
        fc_qs_proj = [feature_transform(x, crs_out=crs) for x in fc_qs]
        fc_qs = None
        fc_qs_proj = [(x['geometry'],x['class']) for x in fc_qs_proj]
        #create fc with (geometry, tag) values
        pred_objects_sorted = PredictClassification.objects.filter(name=test_set,
                                                                   predict_object_id=id_dc_tile).prefetch_related('tag').order_by('features_id')
        fc_pred=[(x['properties']['id'], x['geometry']) for x in src]
        fc_pred_sorted = sorted(fc_pred, key=itemgetter(0))
        fc_pred = [(x[0][1], x[1].tag.numeric_code) for x in zip(fc_pred_sorted, pred_objects_sorted)]
        fc_pred_sorted = None
        pred_objects_sorted = None
        #intersect with fc of validation set
        fc_pred_intersect_validset = [(x[0],x[1]) for x in fc_pred for y in fc_qs_proj if shape(x[0]).intersects(shape(y[0]))]
        fc_pred = None   
    return [fc_qs_proj, fc_pred_intersect_validset]


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
    print('\n-----')
    print('Confusion matrix')
    print('-----')
    head_format = '{:<6}|' + ' {:<7}'*len(d['numeric_labels'])
    row_format = '{:<6}|' + ' {:<7.2f}'*len(d['numeric_labels'])
    print(head_format.format('   ', *d['numeric_labels']))
    print(head_format.format('   ', *['-------'] * len(d['numeric_labels'])))
    for i, row in enumerate(d['confusion_matrix']):
        print(row_format.format(d['numeric_labels'][i], *row))



def db_log():
    """Log the results of a validation to the database

    Args:

    """
    pass
