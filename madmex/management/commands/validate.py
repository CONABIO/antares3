#!/usr/bin/env python

"""
Author: palmoreck
Date: 2019-03-07
Purpose: Compute validation metrics on an existing object based classification
"""
from madmex.management.base import AntaresBaseCommand
import logging

from madmex.validation import validate, prepare_validation
from madmex.validation import query_validation_intersect, pprint_val_dict
from madmex.util.db import get_validation_scheme_name
from madmex.models import ValidationResults
from dask.distributed import Client
from madmex.util.spatial import geometry_transform
from pprint import pprint
from madmex.models import Country, Region, PredictClassification

logger = logging.getLogger(__name__)

class Command(AntaresBaseCommand):
    help = """
Compute validation metrics over an existing object based classification and optionally
log it the database.

Both the classification and the validation data must be present in the database
See the antares ingest_validation for instruction on how to ingest a validation dataset

--------------
Example usage:
--------------
# Validate map, and log the result to the database
antares validate --classification chihuahua_nalcm_2015 --validation bits_interpret --region Chihuahua --log -sc scheduler.json
"""
    def add_arguments(self, parser):
        parser.add_argument('-c', '--classification',
                            type=str,
                            required=True,
                            help='Name of the classification to validate')
        parser.add_argument('-val', '--validation',
                            type=str,
                            required=True,
                            help='Name of the validation dataset to use to perform the validation')
        parser.add_argument('-r', '--region',
                            type=str,
                            default=None,
                            help=('Optional name of a region to use for spatially constraining the validation. '
                                  'If left empty validation is ran over the full extent of the validation dataset. '
                                  'The geometry of the region should be present in the madmex-region or the madmex-country table of the database. '
                                  'Use ISO country code for country name'))
        parser.add_argument('--log',
                            action='store_true',
                            help='Write the validation metrics to the database when specified.')
        parser.add_argument('--comment',
                            type=str,
                            default=None,
                            help='Optional quotted comment to be added to the database')
        parser.add_argument('-sc', '--scheduler',
                            type=str,
                            default=None,
                            help='Path to file with scheduler information (usually called scheduler.json)')

    def handle(self, *args, **options):
        # Unpack variables
        classification = options['classification']
        validation = options['validation']
        region = options['region']
        log = options['log']
        comment = options['comment']
        scheduler_file = options['scheduler']

        # Get the scheme name
        scheme = get_validation_scheme_name(validation)
        # Query country or region contour
        try:
            region = Country.objects.get(name=region).the_geom
        except Country.DoesNotExist:
            region = Region.objects.get(name=region).the_geom
        
        region_geojson = region.geojson
        geometry_region = json.loads(region_geojson)
        
        # Query the data
        
        qs_ids = PredictClassification.objects.filter(name=classification).distinct('predict_object_id')
        list_ids = [x.predict_object_id for x in qs_ids]
        
        
        client = Client(scheduler_file=scheduler_file)
        client.restart()
        c = client.map(fun,list_ids,**{'validation_set': validation,
                                       'test_set': classification,
                                       'geometry_region': geometry_region})
        result = client.gather(c)
        fc_valid = [x[0][index] for x in result for index in range(0,len(x[0]))]
        fc_test = [x[1][index] for x in result for index in range(0,len(x[1]))]

        report = """
                      Validation Report
Region: %s
Classification identifier: %s
Validation dataset identifier: %s
Number of validation polygons: %d
Number of intersecting classification polygons: %d

"""

        print(report % (region, classification, validation,
                        len(fc_valid), len(fc_test)))

        # Prepare validation vectors
        y_true, y_pred, sample_weight = prepare_validation(fc_valid, fc_test)
        # Run the validation
        acc_dict = validate(y_true=y_true, y_pred=y_pred, sample_weight=sample_weight,
                            scheme=scheme)
        pprint_val_dict(acc_dict)

        # Optionally log the results to the db
        if log:
            logger.info('Writing validation results to the database')
            ValidationResults.objects.create(classification=classification,
                                             validation=validation,
                                             region=region,
                                             scheme=scheme,
                                             n_val=len(fc_valid),
                                             n_pred=len(fc_test),
                                             overall_acc=acc_dict['overall_accuracy'],
                                             report=acc_dict,
                                             comment=comment)

