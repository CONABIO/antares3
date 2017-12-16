'''
Created on Dec 13, 2017

@author: agutierrez
'''
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
        '''Method to hide the http call from the user.
        
        This method hides the complexity of making a request to usgs,
        depending on whether data parameter is given or not, it makes
        a GET or a POST request. It requires an endpoint to query the
        api if an invalid request is given, then the aip will answer
        with a 404 error message.
        
        Args:
            endpoint: The endpoint to be consumed.
            payload: Data to be included in the request, if None, a GET method is used if present a POST method is used.
        
        Returns:
            A dictionary representing the json response.
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
        '''Function to log into the USGS query service.

        The USGS api requires a key to return data. In order to get the key, valid
        user name and password must be provided to the login endpoint. This key is ephimeral
        and will be valid only for one hour.

        Returns:
            True if the login was successful; False otherwise.
        '''
        data = {'username': USGS_USER,
                'password': USGS_PASSWORD}
        payload = {'jsonRequest': json.dumps(data)}
        endpoint = '/login'
        response = self._consume_api_requests(endpoint, payload)
        if not len(response['error']):
            self.api_key = response['data']
            logger.debug('Successfully logged in to earth explorer USGS api.')
        else:
            return False
        return True
    
    def search(self, extent, collection, node='EE', start_date=None, end_date=None, starting_number=1, max_results=50000):
        '''Queries the USGS api for images in a given extent.

        This service requires to be logged into USGS. It is limited to an extent of interest which
        must be a square and it is not suited for more complex polygons. It paginates automatically
        so in order to pull a big set, the query can be split. This behaviour can be controlled by using
        the max results and starting number attributes. Temporal queries are available by
        providing a time window. Several collections are available, as of the moment of writing this, only
        collection 1 items are available, so the query must be suffixed with that information, for example:
        LANDSAT_8_C1 would be a valid collection. Details on the api can be found in https://earthexplorer.usgs.gov/inventory

        Args:
            extent: The extent of the query in a tuple such as (min_lon, min_lat, max_lon, max_lat)
            collection: A string that represents the collection of interest for example LANDSAT_8_C1
            node: A service provider, can be one of: "CWIC", "EE", "HDDS", "LPVS"
            start_date: The start date for the temporal window in a format yyyy-mm-dd.
            end_date: The end date for the temporal window in a format yyyy-mm-dd.
            starting_number: An int representing where the query should start.
            max_results: The maximum number of scenes that the request will return.

        Returns:
            The response from the service.
        '''
        #(-118.404167, 14.550547, -86.701401, 32.718456)
        if self.api_key:
            data = {'apiKey': self.api_key,
                    'node': node,
                    'datasetName': collection,
                    'lowerLeft': {
                                    'latitude': extent[1],
                                    'longitude': extent[0]
                            },
                    'upperRight': {
                                    'latitude': extent[3],
                                    'longitude': extent[2]
                            }
                    }
            if start_date:
                data['startDate'] = start_date

            if end_date:
                data['endDate'] = end_date

            if max_results:
                data['maxResults'] = max_results

            if starting_number:
                data['startingNumber'] = starting_number

            payload= {'jsonRequest': json.dumps(data)}
            print(json.dumps(payload, indent=4))
            endpoint = '/search'
            response = self._consume_api_requests(endpoint, payload)
            print (response)
        else:
            logger.debug('The client is not logged in, or the key has expired.')
            response = {'error':'Must log into the USGS service in order to use this function.'}
        return response

    def logout(self):
        '''Function to log out the USGS query service.

        When the instance of this class is not useful anymore, this method must be called
        to invalidate the key.

        Returns:
            True if the login was successful; False otherwise.
        '''
        if self.api_key:
            payload = {'apiKey': self.api_key}
            endpoint = '/logout?jsonRequest=%s' % json.dumps(payload)
            response = self._consume_api_requests(endpoint)
            if response['data']:
                logger.debug('Successfully logged out of earth explorer usgs api.')
            else:
                logger.debug('The key was no longer valid.')
            self.api_key = None
        else:
            logger.debug('You need to log in first in order to log out!.')


class EspaApi():
    def __init__(self):
        '''
        This is the constructor, it creates an object that holds
        credentials to usgs portal. 
        '''
        if USGS_USER != None and USGS_PASSWORD != None:
            self.username = USGS_USER
            self.password = USGS_PASSWORD
            self.host = 'https://espa.cr.usgs.gov'
        else:
            logger.error('Please add the usgs credentials to the .env file.')
            sys.exit(-1)

    def _consume_api_requests(self, endpoint, data=None):
        '''
        This method hides the complexity of making a request to usgs,
        depending on whether data parameter is given or not, it makes
        a GET or a POST request. It requires an endpoint to query the
        api if an invalid request is given, then the aip will answer
        with a 404 error message.
        '''
        url = self.host + '/api' + endpoint
        logger.info(url)
        if not data:
            response = requests.get(url, auth=(USGS_USER,USGS_PASSWORD))
        else: # a POST request
            response = requests.post(url, data = data, auth=(USGS_USER,USGS_PASSWORD))
        data = response.json()
        return data

    def get_functions(self):
        '''Obtains the functions available in the api.
        
        Will query the api for the valid functions that it exposes.
        
        Returns:
            The dictionary representation of the api response.
        '''
        return self._consume_api_requests('/%s' % espa_version)

    def get_projections(self):
        '''Returns the available projections that the api supports.
        
        Just queries the api to obtain the available projections.
        
        Returns:
            A dictionary with the projections.
        '''
        return self._consume_api_requests('/%s/projections' % espa_version)

    def get_available_products(self, scene_id):
        '''Returns the available products that the api offers.
        
        Given a scene id, this method returns the available products
        that can be requested in an order.
        
        Returns:
            A dictionary with the available products.
        '''
        return self._consume_api_requests('/%s/available-products/%s' % (espa_version, scene_id))
    
    def get_formats(self):
        '''
        Returns the available formats in which the data can be requested.
        '''
        return self._consume_api_requests('/%s/formats' % espa_version)
    
    def order(self, collection, inputs, products):
        '''
        This is the only method implementing a post request. Data about which
        scenes are requested and which products are needed is required on 
        this method calling. More complex querying is supported, we are keeping
        this simple for now.
        '''
        request_json = {'format':'gtiff',
                        'note':'testing',
                        collection:{
                                'inputs':inputs,
                                'products':products
                            }
                        } 
        payload = json.dumps(request_json).encode('utf8')
        print payload
        return self._consume_api_requests('/%s/order' % espa_version, payload)
    
    def get_list_orders(self):
        '''
        This methos returns the status of the orders that have been posted.
        '''
        return self._consume_api_requests('/%s/list-orders' % espa_version)

    def get_resampling_methods(self):
        '''
        Returns the resampling methods available when the products are
        requested in a different resolution that the standard one. Default
        value will be nearest neighbors.
        '''
        return self._consume_api_requests('/%s/resampling-methods' % espa_version)

    def get_user_info(self):
        '''
        Returns information about the user that the credentials that this
        object holds.
        '''
        return self._consume_api_requests('/%s/user' % espa_version)

    def get_list_order(self, order_id):
        '''
        Returns the status of the given order.
        '''
        url = '/%s/item-status/%s' % (espa_version, order_id)
        return self._consume_api_requests(url)