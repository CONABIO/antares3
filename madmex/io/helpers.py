'''
Created on Mar 7, 2018

@author: agutierrez
'''
from madmex.models import TrainTag


def tag_dictionary(dataset):
    '''This method creates a dictionary to map the tags in the database with their
    corresponding id into a python dict.
    '''
    dictionary = {}
    for o in TrainTag.objects.filter(key=dataset):
        dictionary[o.id] = o.value
    return dictionary