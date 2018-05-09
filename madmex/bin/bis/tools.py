"""
Support functions for BIS.
"""
import os
import multiprocessing
import sys, getopt, inspect
import csv
import imp, inspect

def map(function, args_list, processes=None):
    """Multiprocessing map function allowing different params to one function.
    
    Number of processes defaults to cpu_count(), ie number of cores on system.
    
    >>> map(_f, [(1, 1), (2, 2)]) # Test function _f below: return x+y
    [2, 4]
    """
    pool = multiprocessing.Pool(processes=processes)
    jobs = [pool.apply_async(function, args) for args in args_list]
    pool.close()
    pool.join()
    return [job.get() for job in jobs]

def _f(x, y):
    "Test function for map_, separate so it can be pickled"
    return x + y

def csvwrite(filename, table, key_field):
    r"""Save dict-of-dicts to CSV with column headings, id field, and all rows.
    
    >>> table = {1: {'b': 'b1', 'a': 'a1'}, 2: {'a': 'a2', 'b': 'b2'}}
    >>> csvwrite('csvtest.csv', table, key_field='id')
    >>> open('csvtest.csv').read()
    'id,a,b\n1,a1,b1\n2,a2,b2\n'
    >>> os.remove('csvtest.csv')
    """
    for key, row in table.items():
        row[key_field] = key
    order = list(table.values())[0].keys()
    order.sort()
    order.remove(key_field); order.insert(0, key_field)
    c = csv.DictWriter(open(filename, 'w'), order, lineterminator='\n')
    c.writerow(dict(list(zip(order, order))))
    c.writerows(iter(table.values()))

def csvadd(left_file, key_field, right_file, add_field, outname):
    r"""Add the new field/column into the target file, joining by the key field.
    
    >>> open('test/csv1.csv').read(); open('test/csv2.csv').read()
    'id,f1a,f1b\n0,1a,1b\n1,1c,1d\n'
    'id,f2a,f2b\n1,2c,2d\n0,2a,2b\n'
    >>> csvadd('test/csv1.csv', 'id', 'test/csv2.csv', 'f2a', 'csv3.csv')
    >>> open('csv3.csv').read()
    'id,f1a,f1b,f2a\n1,1c,1d,2c\n0,1a,1b,2a\n'
    >>> os.remove('csv3.csv')
    """
    csv1 = csv.DictReader(open(left_file))
    csv2 = csv.DictReader(open(right_file))
    table1 = dict([(row[key_field], row) for row in csv1])
    table2 = dict([(row[key_field], row) for row in csv2])
    for key, row in table1.items():
        row[add_field] = table2[key][add_field]
    csvwrite(outname, table1, key_field)

##def csvmerge(filename1, filename2, outname, key_field):
##    r"""Join filename2 onto filename1 based on 'id' and save with new order.
##    
##    >>> open('test/csv1.csv').read(); open('test/csv2.csv').read()
##    'id,f1a,f1b\n0,1a,1b\n1,1c,1d\n'
##    'id,f2a,f2b\n1,2c,2d\n0,2a,2b\n'
##    >>> csvmerge('test/csv1.csv', 'test/csv2.csv', 'csv3.csv', 'id')
##    >>> open('csv3.csv').read()
##    'id,f1a,f1b,f2a,f2b\n1,1c,1d,2c,2d\n0,1a,1b,2a,2b\n'
##    >>> os.remove('csv3.csv')
##    """
##    csv1 = csv.DictReader(open(filename1))
##    csv2 = csv.DictReader(open(filename2))
##    table1 = dict([(row[key_field], row) for row in csv1])
##    table2 = dict([(row[key_field], row) for row in csv2])
##    for key, row in table1.iteritems():
##        row.update(table2[key])
##    csvwrite(outname, table1, key_field)

def thisdir(filename):
    r"""Return the absolute directory name of the filename.
    
    >>> thisdir('/root/dir/file.txt') #doctest:+SKIP
    'C:\\root\\dir/'
    >>> thisdir(__file__) #doctest:+SKIP
    'C:\\jscar\\beti\\SALES\\SoftwarePlan\\astro\\support\\mex\\bis/'
    """
    return os.path.dirname(os.path.abspath(filename)) + '/'

def readfunctions(filename):
    """Import the functions from the python file to a dictionary of name: func
    
    >>> import numpy as np
    >>> m = imp.load_source('mod', 'test/stattest.py')
    >>> m.max(np.array([0, 1]))
    1
    >>> functions = readfunctions('test/stattest.py')
    >>> functions # doctest:+ELLIPSIS
    {'max': <function max at 0x...>}
    >>> functions['max'](np.array([0, 1]))
    1
    >>> os.remove('test/stattest.pyc')
    """
    name = os.path.splitext(os.path.basename(filename))[0]
    mod = imp.load_source(name, filename)
    members = [m for m in inspect.getmembers(mod, inspect.isfunction) if
               not m[0].startswith('_')]
    return dict(members)

def eval_(string):
    """Parse command line args to pass to a Python function.
    
    >>> [eval_(s) for s in ['ag.bmp', '10', 'False', 'None', '10.0']]
    ['ag.bmp', 10, False, None, 10.0]
    """
    try: return eval(string)
    except: return string

def commandline(function, error_text="", argv=None, function2=None):
    """Parse and pass command line args to wrap a Python function.
    
    >>> from segment import segment
    >>> import os
    >>> commandline(segment)
    Traceback (most recent call last):
    ...
    SystemExit: segment() takes at least 1 argument (0 given)
    >>> commandline(segment, argv=['segment.py', 'test/ag.bmp', '-t', '[6,11]',
    ...                            '--tile', 'True'])
    >>> os.remove('test/ag.bmp_6_05_05.tif')
    >>> os.remove('test/ag.bmp_11_05_05.tif')
    >>> commandline(segment, argv=['segment.py', 'test/ag.bmp', '--NOT'])
    ...   # This will look different to the screen at runtime.
    Traceback (most recent call last):
    ...
    SystemExit: option --NOT not recognized
    """
    if argv is None:
        argv = sys.argv
    if '--help' in argv:
        help(function)
    else:
        inspected = inspect.getargspec(function)[0]
        args_def = ':'.join([i for i in inspected if len(i) == 1]) + ':'
        opts_def = [i + '=' for i in inspected if len(i) > 1]
        if function2:
            "Accomodate passing **kwargs from workflow to segment"
            inspected2 = inspect.getargspec(function2)[0]
            args_def += ':'.join([i for i in inspected2 if len(i) == 1]) + ':'
            opts_def += [i + '=' for i in inspected2 if len(i) > 1]
        try:
            opts, args = getopt.gnu_getopt(argv[1:], args_def, opts_def)
        except Exception as e:
            print('\n', error_text, '\n')
            exit(e)
        args = [eval_(a) for a in args]
        opts = [(key.lstrip('-'), eval_(value)) for key, value in opts]
        try:
            function(*args, **dict(opts))
        except Exception as e:
            print('\n', error_text, '\n')
            exit(e)


if __name__ == '__main__':
    "Run Python standard module doctest which executes the >>> lines."
    import doctest
    doctest.testmod()
