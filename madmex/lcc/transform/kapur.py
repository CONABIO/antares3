'''
2018 07 10
@author: jequihua
'''
import logging

from scipy import stats

from madmex.lcc.transform import TransformBase
import numpy as np


def optimal_bins(data_vector, method="shimazaki-shinomoto", bins=1000):

    '''Computes optimal number of bins to produce a histogram

    Args:
        data_vector (np.ndarray): 1D array over which to compute number of bins
        method (str): Method to use to determine optimal bins. One of sturges,
            scott, freedman-diaconis, shimazaki-shinomoto. Set to None, or random
            string to manually set the number of bins
        bins (int): User defined number of bins for when none of the available
            method is selected

    Return:
        int: The optimal bin number
    '''

    if method == "sturges":
        # number of bins
        number_of_bins=np.ceil(np.log2(len(data_vector))+1)

    elif method == "scott":
        # number of bins
        number_of_bins=3.59*np.std(data_vector)*np.power(len(data_vector),
                                                               (-1.0)/(3.0))

    elif method == "freedman-diaconis":
        # sorted image data
        data_vector = np.sort(data_vector)
        # generate a histogram using Freedman-Diaconis bin size
        upperQuartile = stats.scoreatpercentile(data_vector,.75)
        lowerQuartile = stats.scoreatpercentile(data_vector,.25)
        #   Interquartile range
        IQR = upperQuartile - lowerQuartile
        bin_length = 2*IQR*np.power(len(data_vector),(-1.0)/(3.0))
        data_range = max(data_vector)-min(data_vector)
        #   number of bins
        number_of_bins = np.int(np.ceil(data_range/bin_length))

    elif method == "shimazaki-shinomoto":
        # propose an optimal bin size for a histogram
        # using the Shimazaki-Shinomoto method
        x_max = max(data_vector)
        x_min = min(data_vector)
        N_MIN = 100   # minimum number of bins 
        N_MAX = 3000  # maximum number of bins 
        N = np.arange(N_MIN, N_MAX,10) # #of Bins
        D = (x_max - x_min) / N    # bin size vector
        C = np.zeros(shape=(np.size(D), 1))

        # computation of the cost function
        for i in range(np.size(N)):
            ki = np.histogram(data_vector, bins=N[i])
            ki = ki[0]
            k = np.mean(ki) # mean of event count
            v = np.var(ki)  # variance of event count
            C[i] = (2 * k - v) / (D[i]**2) # the cost function

        # optimal bin size selection
        idx  = np.argmin(C)
        number_of_bins = N[idx]

    else:
        number_of_bins = bins

    return number_of_bins


def _clip_histogram_tails(X, clip_hist_tails=3):
    """Clip tails of a distribution.

    Destroys observations in an array that are a certain amount
    of standard deviations away from the mean.
    
    Return:
        np.ndarray: A copy of the array without the tails.
    """
    X = X[(X > (np.mean(X) - clip_hist_tails * np.std(X))) & \
                        (X < (np.mean(X) + clip_hist_tails * np.std(X)))]
    return X 


def _maximum_entropy_cut(histo, bin_edges, argmax=True):
    '''
    given a histogram and its corresponding bin edges, calculates the bin
    at which a cut produces maximum entropy
    '''
    # bin with maximum frecuency
    if argmax:
        maxindex = np.argmax(histo)
        # take only positive parts
        histo = histo[maxindex:]
        bin_edges = bin_edges[(maxindex + 1):]
    else:
        # take only parts after median (middle)
        middle = int(np.floor(np.median(range(len(histo)))))
        histo = histo[middle:]
        bin_edges = bin_edges[(middle + 1):]
    # drop any zero bins
    keep = histo != 0
    histo = histo[keep]
    bin_edges = bin_edges[keep]
    # check for corner cases
    if np.product(histo)==1:
        return 2 ** histo[0]
    # standardize histogram to obtain probabilities
    probabilities = histo.astype(np.float) / np.float(np.sum(histo))
    # initialize vector to fill with calculated entropies
    entropies = np.zeros(len(probabilities))
    for i in range(len(probabilities) - 2):
        white_class = probabilities[0:(i + 1)]
        white_class_sum = np.sum(white_class)
        white_class = -1 * np.sum(np.multiply(white_class / white_class_sum,
                                            np.log(white_class / white_class_sum)))
        black_class = probabilities[(i + 2):len(probabilities)]
        black_class_sum = np.sum(black_class)
        black_class = -1 * np.sum(np.multiply(black_class / black_class_sum,
                                            np.log(black_class / black_class_sum)))
        entropies[i] = white_class + black_class
    idx_maximum_entropy = np.argmax(entropies)
    threshold = bin_edges[np.int(idx_maximum_entropy)]
    return threshold


class Transform(TransformBase):
    '''Antares implementation of Kapur, Sahoo and Wong entropy based array thresholding
    '''
    def __init__(self, X, band=0, histogram=None, n_bins=1000, symmetrical=True,
                 argmax=True, clip_hist_tails=3, no_data=None):
        '''Instantiate Kapur transform class

        Args:
            band (int): Band to which the algorithm is applied.
            histogram (str or int): Either one of the automatic methods to determine
                optimal number of bins of a distribution (one of sturges, scott,
                freedman-diaconis, shimazaki-shinomoto), or None
            n_bins (int): Ignored if histogram is not ``None``. Number of bins
            symetrical (bool): Is the distribution symetrical. Assumes there must
                be a lower and a higher threshold. ``False`` should be used for
                array of absolute values, in which case there should only be one
                higher threshold
            argmax (bool): Determines is the histogram bin with maximum frequency
                should be ignored.
            clip_hist_tails (int): Determines if observations further away than
            a certain amount of standard deviations from the mean should be 
            ignored.
            no_data (int): Value to be used as no data. 
        '''
        super().__init__(X)
        self.band=band
        self.argmax = argmax
        self.histogram = histogram
        self.n_bins = n_bins
        self.symmetrical = symmetrical
        self.clip_hist_tails = clip_hist_tails
        self.no_data = no_data


    def _transform(self):
        """ 
            Using the Kapurs method for image binarization, this method will detect
            points in the dataset that do are considered background and foreground.
        
        Return:
            np.ndarray: 2 dimensional matrix with ones in the pixels that are outliers,
                and zeros otherwise.

        """
        change_classification = np.zeros((self.cols * self.rows), dtype=np.uint8)
        positive_threshold = None
        negative_threshold = None
        X = np.ravel(self.X[int(self.band), :, :])
        X_copy = X
        if self.no_data is not None:
            # handle no data values
            idx_keep = X != self.no_data
            X = X[idx_keep]
        # sorted image
        X = np.sort(X)
        if self.clip_hist_tails is not None:
            X = _clip_histogram_tails(X, self.clip_hist_tails)
        # decide on optimal number of bins for histogram
        bins = optimal_bins(X, method=self.histogram, bins=self.n_bins)
        # generate histogram based on this number of bins
        histo, bin_edges = np.histogram(X, bins)
        ### positive side
        positive_threshold = _maximum_entropy_cut(histo,
                                                  bin_edges,
                                                  argmax=self.argmax)
        if self.symmetrical:
            ### negative side
            # flip vectors
            histo = histo[::-1]
            bin_edges = bin_edges[::-1]
            negative_threshold = _maximum_entropy_cut(histo,
                                                      bin_edges,
                                                      argmax=self.argmax)
            if self.no_data is not None:
                idx_keep_neg = idx_keep and (X_copy < negative_threshold)
                change_classification[idx_keep_neg] = 1
            else:
                change_classification[X_copy < negative_threshold] = 1
        if self.no_data is not None:
            idx_keep_neg = idx_keep and (X_copy > positive_threshold)
            change_classification[idx_keep_neg] = 1
            change_classification[np.invert(idx_keep)] = self.no_data
        else:
            change_classification[X_copy > positive_threshold] = 1
        # resize to original image shape
        change_classification = np.resize(change_classification, (self.rows, self.cols))
        return change_classification
