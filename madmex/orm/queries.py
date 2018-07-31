'''
Created on Jan 23, 2018

@author: agutierrez
'''
from _functools import reduce
import datetime
import json
import math
from os.path import os

from django.db import connection
import numpy
import pytz

from madmex.models import Country, Footprint
from madmex.settings import TEMP_DIR

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
    return sum(cloud_covers), len(cloud_covers)

def calculate_good_surface(scene_name, cloud_cover_land, year, mission=8):
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
            return 1 - row[0] / 100.0
        else:
            cloud_cover = row[0] / 100.0
            scan_line_error = .5 # This value is conservative, the proportion according to Wikipedia is .22
            return scan_line_error * (1 - cloud_cover)
        
    with connection.cursor() as cursor:
        cursor.execute(query % (cloud_cover_land, mission_name, year, scene_name))
        result = cursor.fetchall()
    if mission == 7:
        cloud_covers = map(helper_landsat_7, result)
    else:
        cloud_covers = map(lambda x: 1 - x[0] / 100.0, result)
    return sum(cloud_covers)

def calculate_quality(cloud_cover, country_name='MEX'):
    country_geom = Country.objects.get(name=country_name).the_geom
    path_row_list = list(map(lambda x: x.name, Footprint.objects.filter(the_geom__intersects=country_geom, sensor='landsat')))
    mission_list = [5, 7, 8]
    data = {}
    for path_row in path_row_list:
        path_row_info = {}
        min_score = 100000
        for year in range(1990, 2018):
            scores = []
            for mission in mission_list:
                log_prob_bad_pixel, num_images = calculate_quality_by_year_tile_cloud_cover(path_row, cloud_cover, year, mission)
                prob_bad_pixel = math.pow(math.e, log_prob_bad_pixel)
                prob_complete_info = 1 - prob_bad_pixel
                scores.append(prob_complete_info * num_images)
            score = round(sum(scores), 2)
            if min_score > score:
                min_score = score 
            path_row_info[year] = score
        path_row_info['max'] = min_score
        data[path_row] = path_row_info
    return data

def calculate_area_sum(cloud_cover, country_name='MEX'):
    country_geom = Country.objects.get(name=country_name).the_geom
    path_row_list = list(map(lambda x: x.name, Footprint.objects.filter(the_geom__intersects=country_geom, sensor='landsat')))
    mission_list = [5, 7, 8]
    data = {}
    for path_row in path_row_list:
        path_row_info = {}
        min_score = 100000
        for year in range(1990, 2018):
            probs = []
            for mission in mission_list:
                probs.append(calculate_good_surface(path_row, cloud_cover, year, mission))
            score = round(sum(probs), 2)
            if min_score > score:
                min_score = score 
            path_row_info[year] = score
        path_row_info['max'] = min_score
        data[path_row] = path_row_info
    return data

def data_to_heatmap(data):
    codes = []
    years = []
    matrix = []
    filled = False
    for code, scores in data.items():
        codes.append(code)
        score_array = []
        for year, score in scores.items():
            if not filled:
                years.append(year)
            score_array.append(score)
        filled = True
        matrix.append(score_array)
    final_data = numpy.array(matrix)
    numpy.savetxt(os.path.join(TEMP_DIR, 'final_data.csv'), final_data, delimiter=',')
