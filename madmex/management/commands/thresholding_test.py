import logging
import os

import rasterio

import numpy

from madmex.lcc.bitemporal.imadmaf import IMAD
from madmex.lcc.bitemporal.imagethresholding import Elliptic,Kapur
from madmex.management.base import AntaresBaseCommand
from madmex.settings import TEMP_DIR


logger = logging.getLogger(__name__)


class Command(AntaresBaseCommand):

   def add_arguments(self, parser):
       parser.add_argument('--a',
                           type=str,
                           default=None,
                           help='Image')

   
   def handle(self, *args, **options):
       image_a = options['a']

       with rasterio.open(image_a) as src:
           X = src.read()
           profile = src.profile
           
       thresholded = Kapur(bands_subset=numpy.array([0,1,2]))
       
       
       thresholded = thresholded.fit_transform(X)

       print(thresholded.shape)

       final_path = '/home/jequihua/Documents/cd_tests/imad_thresholded_kapur.tif'
       
       profile["count"]=1
       
       with rasterio.open(final_path, 'w', **profile) as dst:
           print(profile)
           dst.write_band(1,thresholded.astype(rasterio.float32))
