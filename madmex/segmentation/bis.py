from madmex.segmentation import BaseSegmentation
from madmex.bin.bis import segment_gen



class Segmentation(BaseSegmentation):
    """Antares implementation of Berkeley Image segmentation algorithm
    """
    def __init__(self, array, affine, crs, t=7, s=0.3, c=0.8):
        """BIS segmentation algorithm

        Args:
            t (int): threshold. Threshold controls size, a larger threshold maps bigger objects
            s (float): Shape
            c (float): Compactness

        Example:
            >>> from madmex.segmentation.bis import Segmentation
            >>> from madmex.models import SegmentationInformation

            >>> Seg = Segmentation.from_geoarray(geoarray, t=7, s=0.3, c=0.8)
            >>> Seg.segment()
            >>> Seg.polygonize()

            >>> meta = SegmentationInformation(algorithm='bis', datasource='sentinel2',
            >>>                                parameters="{'t': 7, 's': 0.3, 'c': 0.8}",
            >>>                                datasource_year='2018')
            >>> meta.save()
            >>> Seg.to_db()
        """
        super().__init__(array=array, affine=affine, crs=crs)
        self.algorithm = 'bis'
        self.t = t
        self.s = s
        self.c = c

    def segment(self):
        arr_gen = segment_gen(self.array, t=[self.t], s=self.s, c=self.c,
                              tile=False, nodata=None)
        arr = next(arr_gen)
        self.segments_array = arr
