import random
import string

import yaml

def randomword(length):
    """Generate a random string of desired length
    """
    return ''.join(random.choice(string.ascii_lowercase) for i in range(length))


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

def parser_extra_args(x):
    """Helper to parse extra args passed to argparse

    nargs= must be set to '*' in add_argument

    Args:
        x (list): A list of strings. Each string must be a key=value pair

    Return:
        dict: Kwargs style dictionary

    Example:
        a = ['arg0=12', 'arg1=madmex']
    """
    def to_bool(s):
        if s.lower() == 'true':
            return True
        elif s.lower() == 'false':
            return False
        else:
            raise ValueError('Cannot be coerced to boolean')

    def change_type(s):
        try:
            r = to_bool(s)
            return r
        except ValueError as e:
            pass

        try:
            r = int(s)
            return r
        except ValueError as e:
            pass

        try:
            r = float(s)
            return r
        except ValueError as e:
            pass

        return s

    d0 = dict(item.split('=') for item in x)
    d1 = {k: change_type(v) for k, v in d0.items()}
    return d1
