import unittest
import numpy as np
from madmex.util.spatial import feature_transform

# Example polygon feature with a hole


class TestSpatialUtils(unittest.TestCase):

    def test_feature_transform(self):
        feature_polygon = {'geometry': {'coordinates': [[[5.02, 45.319],
                                                         [5.201, 45.217],
                                                         [5.134, 45.074],
                                                         [5.494, 45.071],
                                                         [5.464, 44.793],
                                                         [5.825, 44.7],
                                                         [5.641, 44.651],
                                                         [5.597, 44.543],
                                                         [5.664, 44.501],
                                                         [5.418, 44.424],
                                                         [5.631, 44.331],
                                                         [5.678, 44.146],
                                                         [5.454, 44.119],
                                                         [5.15, 44.235],
                                                         [5.166, 44.314],
                                                         [4.825, 44.228],
                                                         [4.65, 44.329],
                                                         [4.886, 44.936],
                                                         [4.8, 45.298],
                                                         [5.02, 45.319]],
                                                        [[4.97, 44.429],
                                                         [4.889, 44.304],
                                                         [5.07, 44.376],
                                                         [4.97, 44.429]]],
                                        'type': 'Polygon'},
                           'properties': {'name': 'atlantis'},
                           'type': 'Feature'}
        crs_proj = "+proj=lcc +lat_1=17.5 +lat_2=29.5 +lat_0=12 +lon_0=-102 +x_0=2500000 +y_0=0 +a=6378137 +b=6378136.027241431 +units=m +no_defs"
        crs_geo = "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs"
        # Perform round trip transformation 
        feature_proj = feature_transform(feature_polygon, crs_proj, crs_geo)
        feature_geo = feature_transform(feature_proj, crs_geo, crs_proj)
        # Compare polygon
        np.testing.assert_almost_equal(feature_polygon['geometry']['coordinates'][0],
                                       feature_geo['geometry']['coordinates'][0])
        # Compare hole
        np.testing.assert_almost_equal(feature_polygon['geometry']['coordinates'][1],
                                       feature_geo['geometry']['coordinates'][1])

if __name__ == '__main__':
    unittest.main()
