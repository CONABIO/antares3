'''
Created on Jan 23, 2018

@author: agutierrez
'''
from _functools import reduce
import datetime
import json
import math

from django.db import connection
import pytz

from madmex.models import Country, Footprint


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
             "WHERE f.id = s.footprint_id AND s.cloud_cover_land < 20 AND s.landsat_product_id like '%s' " 
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

def calculate_quality_by_year_tile_cloud_cover(scene_name, cloud_cover_land, year, mission=8):
    query = ("SELECT cloud_cover_land, acquisition_date "
             "FROM madmex_scene AS s, madmex_footprint AS f "
             "WHERE f.id = s.footprint_id "
             "AND s.cloud_cover < %s "
             "AND s.landsat_product_id like '%s' "
             "AND extract(year from s.acquisition_date) = %s "
             "AND name='%s'")

    mission_name = None

    if mission == 7:
        mission_name = 'LE07%'  
    elif mission == 8: 
        mission_name = 'LC08%'
    elif mission == 5: 
        mission_name = 'LT05%'
    elif mission == 4:
        mission_name = 'LT04%'
        
    def helper_landsat_7(row):
        utc=pytz.UTC
        FAILURE = datetime.datetime(2003, 5, 31).replace(tzinfo=utc)
        if row[1] < FAILURE:
            return math.log(row[0] / 100.0 + 0.000001)
        else:
            cloud_cover = row[0] / 100.0
            scan_line_error = .5 # This value is conservative, the proportion according to Wikipedia is .22
            return math.log(scan_line_error + cloud_cover - cloud_cover * scan_line_error + 0.000001)
            
            
    with connection.cursor() as cursor:
        cursor.execute(query % (cloud_cover_land, mission_name, year, scene_name))
        result = cursor.fetchall()
    if mission == 7:
        cloud_covers = map(helper_landsat_7, result)
    else:
        cloud_covers = map(lambda x: math.log(x[0] / 100.0 + 0.000001), result)
    #print(list(cloud_covers))
    return sum(cloud_covers)

def calculate_quality(cloud_cover, country_name='MEX'):
    
    country_geom = Country.objects.get(name=country_name).the_geom
    path_row_list = list(map(lambda x: x.name, Footprint.objects.filter(the_geom__intersects=country_geom, sensor='landsat')))
    mission_list = [5, 7, 8]
    
    data = {}
    for path_row in path_row_list:
        path_row_info = {}
        max_score = 0
        for year in range(1995, 2018):
            probs = []
            for mission in mission_list:
                probs.append(calculate_quality_by_year_tile_cloud_cover(path_row, cloud_cover, year, mission))
            score = round(math.pow(math.e, sum(probs)), 2)
            if max_score < score:
                max_score = score 
            path_row_info[year] = score
        path_row_info['max'] = max_score
        data[path_row] = path_row_info
        
    print(json.dumps(data, indent=4))
    
    
    