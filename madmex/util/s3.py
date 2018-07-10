import os
try:
    import boto3
except ImportError:
    _has_boto3 = False
else:
    _has_boto3 = True


def list_folders(bucket, path):
    """List 'sub-folders' of a s3 bucket 'folder'

    Args:
        bucket (str): Name of an existing s3 bucket
        path (str): Path of the folder to containing the sub-folders to be listed

    Returns:
        list: List of subfolder names
    """
    if not _has_boto3:
        raise ImportError('boto3 is required for working with s3 buckets')
    # Add trailing slash to path if not already there and remove leading slash
    path = os.path.join(path.strip('/'), '')
    # Connect to bucket
    client = boto3.client('s3')
    paginator = client.get_paginator('list_objects')
    params = {'Bucket': bucket, 'Prefix': path, 'Delimiter': '/'}
    page_iterator = paginator.paginate(**params)
    out_list = []
    for page in page_iterator:
        out_list.append([x.get('Prefix') for x in page.get('CommonPrefixes')])
    return [item for sublist in out_list for item in sublist]
