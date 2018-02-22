import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "madmex.settings")
import django

class AntaresDb(object):
    """docstring for AntaresDb"""
    def __init__(self):
        django.setup()

    def query_sql(self, sql):
        pass

    def close(self):
        pass
