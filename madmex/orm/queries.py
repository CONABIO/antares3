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

def get_datacube_objects(dataset_name):
    
    query = "select d.metadata from agdc.dataset as d, agdc.dataset_type as m where d.dataset_type_ref=m.id and m.name='%s';" % dataset_name
    
    with connection.cursor() as cursor:
        cursor.execute(query)
        result = cursor.fetchall()
    return result

def get_datacube_chunks(dataset_name):
    
    query = "select l.uri_body from agdc.dataset as d, agdc.dataset_type as m, agdc.dataset_location as l where d.dataset_type_ref=m.id and l.dataset_ref=d.id and m.name='%s';" % dataset_name
    
    with connection.cursor() as cursor:
        cursor.execute(query)
        result = cursor.fetchall()
    return result


    