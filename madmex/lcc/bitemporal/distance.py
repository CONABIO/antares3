from madmex.lcc.bitemporal import BaseBiChange
import numpy as np


def _hist_match_band(source, template):
    """
    Adjust the pixel values of a source 2D array such that its histogram
    matches that of a target array

    From `stackoverflow answer <https://stackoverflow.com/a/33047048/2270789>`_

    Args:
        source (np.ndarray): Source 2D array to transform
        template (np.ndarray): Template 2D array to use for histogram matching

    Returns:
        np.ndarray: The transformed output array
    """

    oldshape = source.shape
    source = source.ravel()
    template = template.ravel()

    # get the set of unique pixel values and their corresponding indices and
    # counts
    s_values, bin_idx, s_counts = np.unique(source, return_inverse=True,
                                            return_counts=True)
    t_values, t_counts = np.unique(template, return_counts=True)

    # take the cumsum of the counts and normalize by the number of pixels to
    # get the empirical cumulative distribution functions for the source and
    # template images (maps pixel value --> quantile)
    s_quantiles = np.cumsum(s_counts).astype(np.float64)
    s_quantiles /= s_quantiles[-1]
    t_quantiles = np.cumsum(t_counts).astype(np.float64)
    t_quantiles /= t_quantiles[-1]

    # interpolate linearly to find the pixel values in the template image
    # that correspond most closely to the quantiles in the source image
    interp_t_values = np.interp(s_quantiles, t_quantiles, t_values)

    return interp_t_values[bin_idx].reshape(oldshape)


class BiChange(BaseBiChange):
    """Antares implementation of a simple distance based bi-temporal change detection algorithm
    """
    def __init__(self, array, affine, crs, norm='hist', threshold='kapur',
                 **kwargs):
        """Euclidean distance based change detection

        Optionally performs histogram matching to normalize input arrays, compute
        euclidean distance and determines change using the distance threshold

        Args:
            norm (str): Normalization method to use in order to match source and
                destination arrays (one of ``'hist'`` or ``None``)
            threshold (float or str): If numeric, distance value above which a
                change is considered a change. If str, one of the automatic thresholding
                method exposed in ``madmex.lcc.bitemporal.BaseBiChange.threshold_change``
                static method
            **kwargs: Additional arguments to pass to the thresolding method

        Example:
			>>> from madmex.lcc.bitemporal.distance import BiChange
            >>> import numpy as np
            >>> from affine import Affine

            >>> # Build random data
            >>> arr0 = np.random.randint(1,2000,30000).reshape((3, 100, 100))
            >>> arr1 = np.random.randint(1,2000,30000).reshape((3, 100, 100))

            >>> # Instantiate classes
            >>> Change_0 = BiChange(arr0, Affine.identity(), '+proj=longlat', threshold=150)
            >>> Change_1 = BiChange(arr1, Affine.identity(), '+proj=longlat')

            >>> # Compute distance
            >>> Change_0.run(Change_1)
            >>> print(Change_0.change_array)
            >>> print(np.sum(Change_0.change_array))

            >>> Change_0.filter_mmu(1.2)
            >>> print(np.sum(Change_0.change_array))
        """
        super().__init__(array=array, affine=affine, crs=crs)
        self.algorithm = 'distance'
        self.norm = norm
        self.threshold = threshold
        self.kwargs = kwargs


    def _run(self, arr0, arr1):
        # Normalize arr0 to arr1
        if self.norm == 'hist':
            if arr0.ndim == 2:
                arr0_t = _hist_match_band(arr0, arr1)
            elif arr0.ndim == 3:
                # Iterate over each band
                arr0_t = np.empty(arr0.shape)
                for i, band in enumerate(arr0):
                    arr0_t[i] = _hist_match_band(band, arr1[i])
            else:
                raise ValueError('Improper number of dimensions')
        elif self.norm is None:
            arr0_t = arr0
        else:
            raise ValueError('Invalid normalization method selected')
        # Compute distance between both ndarrays
        if arr0.ndim == 2:
            dist = np.absolute(arr0_t - arr1)
        else: # 3
            dist = np.linalg.norm(arr0_t - arr1, axis=0)
        # Apply threshold and generate binary array
        if isinstance(self.threshold, (float, int)):
            out_arr = np.where(dist > self.threshold, 1, 0).astype(np.uint8)
        else:
            if self.threshold == 'kapur':
                self.kwargs.update(symmetrical=False)
            out_arr = self.threshold_change(dist, self.threshold, **self.kwargs)
        return out_arr


