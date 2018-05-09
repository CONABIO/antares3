import random
import string
import inspect
from itertools import chain, islice

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


def chunk(iterable, size=10000):
    """Splits an iterable into chunks

    Args:
        x (list): A list or generator
        chunk_size (int): The chunking size

    Return:
        A chunks generator
    """
    iterator = iter(iterable)
    for first in iterator:
        yield chain([first], islice(iterator, size - 1))


def pprint_args(fun, exclude=None):
    """Retrieves the arguments and default parameters of a function and prints a formated table

    Args:
        fun: A function or method
        exclude (list): List of string. Arguments to exclude from the report

    Example:
        >>> from madmex.util import pprint_args
        >>> from madmex.modeling.supervised.lgb import Model

        >>> pprint_args(Model, exclude=['categorical_features'])

    """
    def get_default(s, x):
        if s.parameters[x].default is s.parameters[x].empty:
            return '-'
        else:
            return str(s.parameters[x].default)
    s = inspect.signature(fun)
    params = list(s.parameters)
    if exclude is not None:
        if not isinstance(exclude, list):
            exclude = [exclude]
        for item in exclude:
            try:
                params.remove(item)
            except Exception as e:
                pass
    table = [(x, get_default(s, x)) for x in params]
    row_format = '{:>25} | {:<25}'
    print(row_format.format('Argument', 'Default value'))
    print(row_format.format('==================', '=============='))
    for row in table:
        print(row_format.format(*row))


