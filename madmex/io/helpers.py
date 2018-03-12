'''
Created on Mar 7, 2018

@author: agutierrez
'''
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "madmex.settings")
import django
django.setup()
from madmex.models import Tag


def get_label_encoding(scheme, inverse=False):
    """Get label --> Numeric code correspondance for a given classification scheme as a dictionary

    Args:
        scheme (str): Classification scheme
        inverse (bool): Use numerics codes as keys and labels as values if True.
            Defaults to False (labels as keys and codes as values)

    Return:
        dict: A dictionary of encoding mapping

    Example:
        >>> from madmex.io.helpers import get_label_encoding
        >>> from pprint import pprint

        >>> d = get_label_encoding('madmex')
        >>> pprint(d)
        >>> d_inv = get_label_encoding('madmex', inverse=True)
        >>> pprint(d_inv)
    """
    query_set = Tag.objects.filter(scheme=scheme)
    if not inverse:
        out = {row.value:row.numeric_code for row in query_set}
    else:
        out = {row.numeric_code:row.value for row in query_set}
    return out
