import logging
import os

import rasterio

from madmex.lcc.bitemporal.imadmaf import IMAD,MAF
from madmex.management.base import AntaresBaseCommand
from madmex.settings import TEMP_DIR


logger = logging.getLogger(__name__)


class Command(AntaresBaseCommand):

   def add_arguments(self, parser):
       parser.add_argument('--a',
                           type=str,
                           default=None,
                           help='Image A')

       parser.add_argument('--b',
                           type=str,
                           default=None,
                           help=('Image B'))

   def handle(self, *args, **options):
       image_a = options['a']
       image_b = options['b']
       
       with rasterio.open(image_a) as src:
           X = src.read()
           profile = src.profile
       with rasterio.open(image_b) as src:
           Y = src.read()
           
       imad = IMAD(max_iterations=25, min_delta=0.02)
       
       
       M, U, V, chi_squared = imad.fit_transform(X, Y)
       
       print(U.shape)
       final_path = os.path.join(TEMP_DIR,'imad.tif')
       

       
       with rasterio.open(final_path, 'w', **profile) as dst:
           print(profile)
           dst.write(M.astype(rasterio.float32))
           
       final_path = os.path.join(TEMP_DIR,'U.tif')
       
       with rasterio.open(final_path, 'w', **profile) as dst:
           print(profile)
           dst.write(U.astype(rasterio.float32))
       final_path = os.path.join(TEMP_DIR,'V.tif')
       
       with rasterio.open(final_path, 'w', **profile) as dst:
           print(profile)
           dst.write(V.astype(rasterio.float32))

       maf = MAF(no_data=0, shift=(1,1))

       maf.fit(M)

       maf_output = maf.transform(M)
       
       final_path = os.path.join(TEMP_DIR,'maf.tif')

       with rasterio.open(final_path, 'w', **profile) as dst:

        dst.write(maf_output.astype(rasterio.float32))