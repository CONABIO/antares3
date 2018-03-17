'''
Created on Jan 17, 2018

@author: agutierrez
'''

import datetime
import logging
import os
from os.path import isfile, join
from posix import listdir
import re
from xml.dom.minidom import parse

import numpy
import rasterio
from madmex.management.base import AntaresBaseCommand
from madmex.util.local import basename


logger = logging.getLogger(__name__)



def get_text(nodelist):
    '''
    This helper method extracts text from a node object in a xml tree.
    '''
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return ''.join(rc)

def get_metadata(tree, tag):
    '''
    Gets and parses the text inside a node.
    '''
    elements = tree.getElementsByTagName(tag)
    text = get_text(elements[0].childNodes)
    return text

def get_float_metadata(tree, tag):
    '''
    Gets and parses the text inside a a node with a particular tag into a float.
    '''
    return float(get_metadata(tree, tag))

def calculate_distance_sun_earth(datestr):
    '''
    Calculates distance between sun and earth in astronomical unints for a given
    date. Date needs to be a string using format YYYY-MM-DD or datetime object
    from metadata.
    '''
    import ephem
    sun = ephem.Sun()
    if isinstance(datestr, str):
        sun.compute(datetime.datetime.strptime(datestr, '%Y-%m-%d').date())
    elif isinstance(datestr, datetime.datetime ):
        sun.compute(datestr)
    sun_distance = sun.earth_distance  # needs to be between 0.9832898912 AU and 1.0167103335 AU
    return sun_distance

def calculate_rad_rapideye(data, radiometricScaleFactor=0.009999999776482582, radiometricOffsetValue=0.0):
    '''
    Convert digital number into radiance according to rapideye documentation. Returns 
    sensor radiance of that pixel in watts per steradian per square meter.
    '''
    rad = data * radiometricScaleFactor + radiometricOffsetValue
    rad[rad == radiometricOffsetValue] = 0
    return rad

def calculate_toa_rapideye(rad, sun_distance, sun_elevation):
    '''
    Calculates top of atmosphere from radiance according to RE documentation
    needs sun-earth distance and sun elevation.
    '''
    print('sun_elevation: %s' % sun_elevation)
    BANDS = 5
    solar_zenith = 90 - sun_elevation
    EAI = [1997.8, 1863.5, 1560.4, 1395.0, 1124.4]  # Exo-Atmospheric Irradiance in 
    toa = rad
    for i in range(BANDS):
        toa[i, :, :] = rad[i, :, :] * (numpy.pi * (sun_distance * sun_distance)) / (EAI[i] * numpy.cos(numpy.pi * solar_zenith / 180)) 
    return toa

class Command(AntaresBaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('-p', '--path',
                            type=str,
                            required=True,
                            help='Directory containing the scenes or tiles for which metadata have to be generated')
        parser.add_argument('-d', '--dest',
                            type=str,
                            required=True,
                            help='Directory containing the scenes or tiles for which metadata have to be generated')
    def handle(self, **options):
        
        directory = options['path']
        destination = options['dest']
        
        
        tif_file_regex = re.compile(".*[0-9]{6}.tif$")
        metadata_file_regex = re.compile(".*[0-9]{6}_metadata.xml$")
        for f in listdir(directory):
            if isfile(join(directory, f)): 
                if metadata_file_regex.match(f):
                    metadata = join(directory, f)
                if tif_file_regex.match(f):
                    image_path = join(directory, f)
                    
                    
                    
        print(metadata)
        print(directory)
        metadata_xml = parse(metadata)
        solar_zenith = get_float_metadata(metadata_xml, 'opt:illuminationElevationAngle')
        # We parse the aquisition date into a format that can be later used to calculate distance to the sun.
        aquisition_date = datetime.datetime.strptime(get_metadata(metadata_xml, 'eop:acquisitionDate'), "%Y-%m-%dT%H:%M:%S.%fZ")
        solar_azimuth =  get_float_metadata(metadata_xml, 'opt:illuminationAzimuthAngle')
        sun_earth_distance = calculate_distance_sun_earth(aquisition_date)
        print(sun_earth_distance)
        print(aquisition_date)
        print(solar_zenith)
        print(solar_azimuth)
        
        with rasterio.open(image_path) as src:
            data = src.read()
            profile = src.profile
            count = src.count
        radiance = calculate_rad_rapideye(data)
        top_of_atmosphere_data = calculate_toa_rapideye(radiance, sun_earth_distance, solar_zenith) * 10000
        
        print(numpy.min(top_of_atmosphere_data))
        print(numpy.max(top_of_atmosphere_data))
        
        profile.update(compress='lzw')
        
        print(basename(image_path,False))
        
        final_path = os.path.join(destination,'%s-toa.tif' % basename(image_path,False))
        
        print(final_path)
        
        with rasterio.open(final_path, 'w', **profile) as dst:
            dst.write(top_of_atmosphere_data.astype(rasterio.uint16))
        
        
        