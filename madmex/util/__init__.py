import random

import yaml

def randomword(length):
    """Generate a random string of desired length
    """
    return ''.join(random.choice(string.lowercase) for i in range(length))


def yaml_to_dict(filename):
    """Load the content of a yaml file as a python dictionary

    Args:
        filename (str): Path of the yaml file

    Return:
        dict: Python dictionary
    """
    with open(filename, 'r') as src:
        out = yaml.load(src)
    return out


def mid_date(date0, date1):
    """FInd the mid point between two dates

    Args:
        date0 (datetime.datetime): Anterior date
        date1 (datetime.datetime): Posterior date

    Return:
        datetime.datetime: The mid date
    """
    delta = (date0 - date1) / 2
    return date0 + delta

