#!/usr/bin/env python

"""
Author: Loic Dutrieux
Date: 2018-06-08
Purpose: Compute validation metrics on an existing object based classification
"""
from madmex.management.base import AntaresBaseCommand
import logging

from madmex.validation import validate, prepare_validation
from madmex.validation import query_validation_intersect, pprint_val_dict
from madmex.util.db import get_validation_scheme_name

from pprint import pprint

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
antares validate --classification chihuahua_nalcm_2015 --validation bits_interpret --region Chihuahua --log
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

    def handle(self, *args, **options):
        # Unpack variables
        classification = options['classification']
        validation = options['validation']
        region = options['region']
        log = options['log']

        # Get the scheme name
        scheme = get_validation_scheme_name(validation)

        # Query the data
        fc_valid, fc_test = query_validation_intersect(validation_set=validation,
                                                       test_set=classification,
                                                       region=region)
        report = """
                      Validation Report
Region: %s
Classification identifier: %s
Validation dataset identifier: %s
Number of validation polygons: %d
Number of intersecting classification polygons: %d """

        print(report % (region, classification, validation,
                        len(fc_valid), len(fc_test)))

        # Prepare validation vectors
        y_true, y_pred, sample_weight = prepare_validation(fc_valid, fc_test)
        # Run the validation
        acc_dict = validate(y_true=y_true, y_pred=y_pred, sample_weight=sample_weight,
                            scheme=scheme)
        ppprint_val_dict(acc_dict)

        # Optionally log the results to the db
        if log:
            logger.info('Logging the results of a validation hasn\'t been implemented yet')

