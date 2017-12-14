'''
Created on Dec 13, 2017

@author: agutierrez
'''
import base64
import json
import logging
import sys

import requests

from madmex.settings import USGS_USER, USGS_PASSWORD


logger = logging.getLogger(__name__)

espa_version = 'v1'
usgs_version = 'stable'

class UsgsApi():
    def __init__(self):
        '''
        This is the constructor, it creates an object that holds
        credentials to usgs portal. 
        '''
        if USGS_USER != None and USGS_PASSWORD != None:
            self.username = USGS_USER
            self.password = USGS_PASSWORD
            self.host = 'https://earthexplorer.usgs.gov/inventory/json/v/%s' % usgs_version
            self.api_key = None
        else:
            logger.error('Please add the usgs credentials to the .env file.')
            sys.exit(-1)

    def _consume_api_requests(self, endpoint, payload=None):
        '''
        This method hides the complexity of making a request to usgs,
        depending on whether data parameter is given or not, it makes
        a GET or a POST request. It requires an endpoint to query the
        api if an invalid request is given, then the aip will answer
        with a 404 error message.
        '''
        url = self.host + endpoint
        logger.info(url)
        if not payload:
            response = requests.get(url)
        else: # a POST request
            response = requests.post(url, data=payload)
        data = response.json()
        return data
    
    def login(self):
        data = {'username': USGS_USER,
                'password': USGS_PASSWORD}
        payload = {'jsonRequest': json.dumps(data)}
        endpoint = '/login'
        response = self._consume_api_requests(endpoint, payload)
        if not len(response['error']):
            self.api_key = response['data']
            logger.debug('Succesfully logged in to earth explorer usgs api.')
        else:
            return False
        return True
    
    
    def logout(self):
        if self.api_key:
            payload = {'apiKey': self.api_key}
            endpoint = '/logout?jsonRequest=%s' % json.dumps(payload)
            response = self._consume_api_requests(endpoint)
            if response['data']:
                logger.debug('Succesfully logged out of earth explorer usgs api.')

    def search(self, extent):
        #(xmin, ymin, xmax, ymax)
        #(min_longitude, min_latitude, max_longitude, max_latitude)
        #"lowerLeft": {"latitude": 75,"longitude": -135},"upperRight": {"latitude": 90,"longitude": -120 }
        
        payload = {
                'datasetName': 'LANDSAT_8',
                    'spatialFilter': {
                        'filterType': 'mbr',
                        'lowerLeft': {
                            'latitude': extent[1],
                            'longitude': extent[0]
                        },
                        'upperRight': {
                            'latitude': extent[3],
                            'longitude': extent[2] 
                        }
                    },
                    'temporalFilter': {
                        'dateField': 'search_date',
                        'startDate': '2006-01-01',
                        'endDate': '2007-12-01'
                    },
                    'additionalCriteria': {
                        'filterType': 'and', 
                        'childFilters': [
                            {'filterType':'between','fieldId':10036,'firstValue':'22','secondValue':'24'},
                            {'filterType':'between','fieldId':10038,'firstValue':'38','secondValue':'40'}
                        ]
                    },
                'maxResults': 10,
                'startingNumber': 1,
                'sortOrder': 'ASC',
                'apiKey': self.api_key
            }
        
        endpoint = '/search?jsonRequest=%s' % json.dumps(payload)
        response = self._consume_api_requests(endpoint)
        return response