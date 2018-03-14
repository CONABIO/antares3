"""madmex"""
import os

import django


__version__ = "0.0.2"

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "madmex.settings")

django.setup()
