'''
2018 07 10
@author: jequihua
'''
import logging

import numpy as np

from sklearn.covariance import EllipticEnvelope
from madmex.lcc.transform import TransformBase

class Transform(TransformBase):
    '''Antares implementation of elliptic envelop thresholding transformation

    This class implements the elliptic envelope method to threshold a difference
    image (like that prodced by the iMAD-MAF transform) to produce a change/no-change
    classes partition.
    It uses an elliptic envelope, this method will detect point in the dataset
    that do not behave as expected under a Gaussian distribution.
    '''

    def __init__(self, X, bands_subset=[0,1], outliers_fraction=0.05,
                 assume_centered=True, support_fraction=None, no_data=None):
        '''Instantiate class

        Args:
            bands_subset (list): Which bands to consider.
            outlier_fraction (float): The proportion of outliers in the data set.
            assume_centered (bool): If True it will not center the data.
            support_fraction (float): The proportion of points to be included in
                the support of the raw MCD estimate.
            no_data (int): Value to be used as no data.
        '''
        super().__init__(X)
        self.bands_subset = np.array(bands_subset)
        self.outliers_fraction = outliers_fraction
        self.assume_centered = assume_centered
        self.support_fraction = support_fraction
        self.no_data = no_data


    def transform(self):
        """Filters outliers from a Gaussian distributed dataset.

        Return:
            np.ndarray: 2 dimensional matrix with ones in the pixels that are outliers,
                and zeros othewise.
        """
        n_used_bands = len(self.bands_subset)
        image_bands_flattened = np.zeros((self.cols * self.rows, n_used_bands))

        for k in range(n_used_bands):
            image_bands_flattened[:, k] = np.ravel(self.X[self.bands_subset[k].astype(int), :, :])

        if self.no_data is not None:
            data_mask = image_bands_flattened[0, :] != self.no_data
            self.image_bands_flattened = image_bands_flattened[:, data_mask]

        # specify and fit model
        model_specification = EllipticEnvelope(contamination=self.outliers_fraction,
                                               assume_centered=self.assume_centered,
                                               support_fraction=self.support_fraction)
        model_specification.fit(image_bands_flattened)
        # tag outliers
        change_classification = model_specification.predict(image_bands_flattened) * 1

        if self.no_data is not None:
            change_classification_full = np.zeros((self.cols * self.rows))
            change_classification = change_classification_full[data_mask]
            change_classification[change_classification==0] = self.no_data

        # resize to original image shape
        change_classification = np.resize(change_classification,
                                          (self.rows, self.cols))
        # set correct change labels
        change_classification[change_classification==1] = 0
        change_classification[change_classification==-1] = 1

        return change_classification.astype(np.uint8)
