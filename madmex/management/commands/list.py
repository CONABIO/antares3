#!/usr/bin/env python

"""
Author: Loic Dutrieux
Date: 2018-04-09
Purpose: Retrieve and display list of models, segmentations and training sets
    saved in the database
"""
from madmex.management.base import AntaresBaseCommand
from madmex.models import Model, SegmentationInformation, TrainClassification
from madmex.models import PredictClassification, ChangeInformation

class Command(AntaresBaseCommand):
    help = """
Helper command line to inspect models, segmentations, classifications
change detection and training sets present in the database

--------------
Example usage:
--------------
# Get the list of trained models
antares list models

# Get the list of training sets available
antares list training_sets

# Get the list of previously ran segmentations
antares list segmentations

# Get the list of generated object based classifications
antares list classifications

# Get the list of bi-temporal change detection results
antares list bi_change
"""
    def add_arguments(self, parser):
        parser.add_argument('key',
                            type=str,
                            default=None,
                            help='Field to inspect (one of models, training_sets, or segmentations)')

    def handle(self, *args, **options):
        key = options['key']

        if key == 'models':
            fields = ['name', 'training_set', 'recipe']
            qs = Model.objects.values_list(*fields).distinct()
        elif key == 'training_sets':
            fields = ['training_set']
            qs = TrainClassification.objects.values_list(*fields).distinct()
        elif key == 'segmentations':
            fields = ['name', 'algorithm']
            qs = SegmentationInformation.objects.values_list(*fields).distinct()
        elif key == 'bi_change':
            fields = ['year_pre', 'year_post', 'algorithm']
            qs = ChangeInformation.objects.values_list(*fields).distinct()
        elif key == 'classifications':
            fields = ['name']
            qs = PredictClassification.objects.values_list(*fields).distinct()
        else:
            print('Unknown command argument')
            return
        row_length = len(fields)
        row_template = '{:<50}' * row_length
        print(row_template.format(*fields))
        print(row_template.format(*['---------------------'] * row_length))
        for row in qs:
            print(row_template.format(*row))
