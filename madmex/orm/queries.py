'''
Created on Jan 23, 2018

@author: agutierrez
'''
from django.db import connection


def example_query():
    with connection.cursor() as cursor:
        cursor.execute('SELECT o.the_geom FROM madmex_object AS o LIMIT 10')
        result = cursor.fetchall()
    return result