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

def get_landsat_catalog(mission):
    
    query = ("SELECT f.name AS path_row, extract(year from s.acquisition_date) AS year, count(f.the_geom) AS number_of_scenes " 
            "FROM madmex_scene AS s, madmex_footprint AS f " 
            "WHERE f.id = s.footprint_id AND s.cloud_cover < 20 AND s.landsat_product_id like '%s' " 
            "GROUP BY f.name, extract(year from s.acquisition_date) " 
            "ORDER BY path_row, year")

    mission_name = 'LE07%'

    if int(mission) == 7:
        mission_name = 'LE07%'  
    elif int(mission) == 8: 
        mission_name = 'LC08%'
    elif int(mission) == 5: 
        mission_name = 'LT05%'
    elif int(mission) == 4:
        mission_name = 'LT04%'

    print(mission_name)
    print(query % mission_name)

    with connection.cursor() as cursor:
        cursor.execute(query % mission_name)
        result = cursor.fetchall()
    return result
    