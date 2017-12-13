'''
Created on Dec 12, 2017

@author: agutierrez
'''
import logging
import os
import sys
import zipfile

import requests


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

def extract_zip(filepath, directory):
    '''Extracts zip file to the given directory.

    This function extracts the contents of a zip file to a given directory.
    
    Args:
        url: The path to the zip file to be uncompressed.
        directory: The directory in which the file should be unzipped.
    ''' 
    target_directory = os.path.join(directory, basename(filepath, False))
    if os.path.exists(target_directory):
        logger.debug('The directory %s already exists.' % target_directory)
    else:
        aware_make_dir(target_directory)
        with zipfile.ZipFile(filepath, 'r') as zip_handle:
            logger.debug('Unzipping %s.' % target_directory)
            zip_handle.extractall(target_directory)
    return target_directory


def aware_make_dir(directory):
    '''Helper function to create a directory if it does not exists.

    The function checks first if the directory exists before it attemps to create it.

    Args:
        directory: The directory to be created.
    '''
    if not os.path.exists(directory):
        os.makedirs(directory)

def basename(filename, suffix=True):
    '''Get base name of a file with or without its suffix.
     
     Returns the base name of a file path. Depending on the arguments this can be
     done with or without the suffix. In case no suffix argument is given, the default would
     be to return the base name with the suffix.
     
    Args:
        filename: The path to the file.
        suffix: True to return the base with suffix; False otherwise.

    Returns:
        The base name.
    '''
    if suffix:
        name = os.path.basename(filename)
    else:
        name = os.path.splitext(os.path.basename(filename))[0]
    return name
