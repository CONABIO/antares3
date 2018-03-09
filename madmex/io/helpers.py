'''
Created on Mar 7, 2018

@author: agutierrez
'''
from madmex.models import Tag


def tag_dictionary(scheme):
    '''This method creates a dictionary to map the tags in the database with their
    corresponding id into a python dict.
    '''
    dictionary = {}
    for o in Tag.objects.filter(scheme=scheme):
        dictionary[o.id] = o.value
    return dictionary