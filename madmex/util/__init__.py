import random
import string
import inspect
from itertools import chain, islice
import os

import yaml
import jinja2

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
    delta = (date1 - date0) / 2
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


def fill_and_copy(template, out_dir, **kwargs):
    """Retrieves a template, fills it with jinja2 and writes it with the same basename to a target directory

    Args:
        template (str): Path to template file
        out_dir (str): Path of directory to which the filled template should be written
        **kwargs: template variables

    Returns:
        This function is used for its side effect of filling a template and writing it to a chosen destination.
    """
    out_file = os.path.join(out_dir, os.path.basename(template))
    # Load template as regular file
    with open(template) as src:
        template = jinja2.Template(src.read())
    # Fill template
    out = template.render(**kwargs)
    # Write to file
    with open(out_file, 'w') as dst:
        dst.write(out)


def join_dicts(*args, join='inner'):
    """Join dictionaries by combining elements with similar keys into lists

    Args:
        *args: The dictionaries to join
        join (str): Type of join. Either inner (default) or full

    Return:
        dict: The dictionary with combined keys

    Examples:
        >>> d1 = {1: 2, 3: 4}
        >>> d2 = {1: 6, 3: 7, 5: 6}
        >>> d3 = {1: 4, 3: 1, 9: 12, 5: 3}
        >>> join_dicts(d1, d2, d3)
        >>> join_dicts(d1, d2, d3, join='full')
    """
    # Get list of lists of keys
    key_list = [list(d.keys()) for d in args]
    if join == 'inner':
        key_iter = set(key_list[0]).intersection(*key_list)
        return {k:[d[k] for d in args] for k in key_iter}
    elif join == 'full':
        key_iter = set([j for i in args for j in i])
        return {k:[d.get(k) for d in args if d.get(k) is not None]
                for k in key_iter}
    else:
        raise ValueError('Unknown join type')
