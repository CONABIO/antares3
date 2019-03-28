from madmex.segmentation import BaseSegmentation
from skimage.segmentation import slic



class Segmentation(BaseSegmentation):
    """Antares implementation of scikit-image's SLIC segmentation algorithm
    """
    def __init__(self, array, affine, crs, n_segments=10000, compactness=10.0):
        """SLIC superpixel segmentation

        See http://scikit-image.org/docs/dev/api/skimage.segmentation.html#skimage.segmentation.slic
        for more details

        Args:
            n_segments (int): The (approximate) number of labels in the segmented output image.
            compactness (float): Balances color proximity and space proximity

        Example:
            >>> from madmex.segmentation.slic import Segmentation
            >>> from madmex.models import SegmentationInformation

            >>> Seg = Segmentation.from_geoarray(geoarray, n_segments=100000, compactness=0.1)
            >>> Seg.segment()
            >>> Seg.polygonize()

            >>> meta = SegmentationInformation(algorithm='bis', datasource='sentinel2',
            >>>                                parameters="{'compactness': 12}",
            >>>                                datasource_year='2018')
            >>> meta.save()
            >>> Seg.to_db()
        """
        super().__init__(array=array, affine=affine, crs=crs)
        self.algorithm = 'slic'
        self.n_segments = n_segments
        self.compactness = compactness

    def segment(self):
        arr = slic(self.array, compactness = self.compactness,
                   n_segments=self.n_segments, multichannel = True)
        self.segments_array = arr
