'''
Created on Dec 12, 2017

@author: agutierrez
'''
import logging
import os
import sys

from pip._vendor import requests


logger = logging.getLogger(__name__)

def aware_download(url, directory):
    '''Download function that only executes when the file has not been downloaded.

    The function checks first if the file is present in the given directory, only
    if it is not, it will try to download it. The function returns the path to
    the file in its new location.
    
    Args:
        url: The url to the file to be downloaded.
        directory: The directory in which the file should be downloaded.

    Returns:
        The path to the file.
    '''
    aware_make_dir(directory)
    
    filename = url.split('/')[-1]
    filepath = os.path.join(directory, filename)

    
    if not os.path.isfile(filepath):
        with open(filepath, "wb") as file_handle:
            print('Downloading %s' % filepath)
            response = requests.get(url, stream=True)
            total_length = response.headers.get('content-length')
    
            if total_length is None:
                file_handle.write(response.content)
            else:
                dl = 0
                total_length = int(total_length)
                for data in response.iter_content(chunk_size=4096):
                    dl += len(data)
                    file_handle.write(data)
                    done = int(50 * dl / total_length)
                    sys.stdout.write("\r[%s%s]" % ('=' * done, ' ' * (50-done)) )    
                    sys.stdout.flush()
    else:
        logger.info('File already exists: %s' % filepath)

    return filepath
    
def aware_make_dir(directory):
    '''Helper function to create a directory if it does not exists.

    The function checks first if the directory exists before it attemps to create it.
    
    Args:
        directory: The directory to be created.
    '''    
    if not os.path.exists(directory):
        os.makedirs(directory)