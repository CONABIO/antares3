""" MEthods for image thresholding """

import logging
import  math

import numpy as np
from sklearn.covariance import EllipticEnvelope


logger = logging.getLogger(__name__)

class Elliptic(object):
    '''
    This class implements the elliptic envelope method to threshold a difference
    image (like that prodced by the iMAD-MAF transform) to produce a change/no-change
    classes partition

    '''
    def __init__(self, bands_subset=np.array([0,1]), outliers_fraction=0.05,
        assume_centered=True, support_fraction=None, auto_optimize=True, no_data=None):

        self.bands_subset = bands_subset
        self.outliers_fraction = outliers_fraction
        self.assume_centered = assume_centered
        self.support_fraction = support_fraction
        self.auto_optimize = auto_optimize
        self.no_data = no_data

    def fit(self, X):

        self.X = X

        if len(self.X.shape) == 2:

            self.bands = 1
            self.rows, self.columns = self.X.shape
            self.X = X[np.newaxis,:]

        elif len(self.X.shape) == 3:
            self.bands, self.rows, self.columns = self.X.shape

        else:
            logger.error('An image of 3 or 2 dimensions is expected.')

    def transform(self, X):

        n_used_bands = len(self.bands_subset)
        image_bands_flattened = np.zeros((self.columns * self.rows,n_used_bands))

        for k in range(n_used_bands):

            image_bands_flattened[:, k] = np.ravel(self.X[\
                                         self.bands_subset[k].astype(int), :, :])

        if self.no_data is not None:

            data_mask = image_bands_flattened[0, :] != self.no_data
            self.image_bands_flattened = image_bands_flattened[:, data_mask]

        logger.info('Fitting elliptic model.')

        flag = True
        change_classification = None

        try:

            # specify and fit model
            model_specification = EllipticEnvelope(
                contamination=self.outliers_fraction,
                assume_centered=self.assume_centered,
                support_fraction=self.support_fraction)

            model_specification.fit(image_bands_flattened)

            # tag outliers
            change_classification = model_specification.predict(\
                                                     image_bands_flattened)*1

        except Exception as error:
            flag = False
            logger.error('Elliptic model fitting failed with error:/ %s',
                                                             str(repr(error)))

        if self.no_data is not None:

            change_classification_full = np.zeros((self.columns * self.rows))
            change_classification = change_classification_full[data_mask]

        # resize to original image shape
        change_classification = np.resize(change_classification,
                                                   (self.rows, self.columns))

        return change_classification.astype(np.int8)

    def fit_transform(self, X):
        self.fit(X)
        return self.transform(X)

def optimal_bins(data_vector, method="shimazaki-shinomoto", bins=100):

    '''
    Computes optimal number of bins to produce a histogram

    Methods: sturges, scott, freedman-diaconis, shimazaki-shinomoto

    '''

    if (method=="sturges"):

        # number of bins
        number_of_bins=np.ceil(np.log2(len(data_vector))+1)

    elif (method=="scott"):

        # number of bins
        number_of_bins=3.59*np.std(data_vector)*np.power(len(data_vector),
                                                               (-1.0)/(3.0))

    elif (method=="freedman-diaconis"):
        print(method)

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

    elif (method=="shimazaki-shinomoto"):
        print(method)
        # propose an optimal bin size for a histogram
        # using the Shimazaki-Shinomoto method
        x_max = max(data_vector)
        x_min = min(data_vector)
        N_MIN = 100   # Minimum number of bins (integer)
        N_MAX = 3000  # Maximum number of bins (integer)
        N = np.arange(N_MIN, N_MAX,10) # #of Bins
        D = (x_max - x_min) / N    #Bin size vector
        C = np.zeros(shape=(np.size(D), 1))

        # computation of the cost function
        for i in xrange(np.size(N)):
            ki = np.histogram(data_vector, bins=N[i])
            ki = ki[0]
            k = np.mean(ki) #Mean of event count
            v = np.var(ki)  #Variance of event count
            C[i] = (2 * k - v) / (D[i]**2) #The cost Function

        # optimal bin size selection
        idx  = np.argmin(C)
        number_of_bins = N[idx]

    else:
        print("using custom number of bins")
        number_of_bins = bins

    return number_of_bins

def clip_histogram_tails(X, clip_hist_tails=3):
    '''
    destroys observations in an array that are a certain amount
    of standard deviations away from  the mean

    '''
    X = X[(X>(np.mean(X)-clip_hist_tails*np.std(X))) & \
                        (X<(np.mean(X)+clip_hist_tails*np.std(X)))]

    return(X)

def maximum_entropy_cut(histo, bin_edges, argmax=True):
    '''
    given a histogram and its corresponding bin edges, calculates the bin
    at which a cut produces maximum entropy

    '''
    # bin with maximum frecuency
    if argmax:
        maxindex = np.argmax(histo)

        # take only positive parts
        histo = histo[maxindex:]
        bin_edges = bin_edges[(maxindex+1):]

    else:
        # take only parts after median (middle)
        middle = int(np.floor(np.median(range(len(histo)))))
        histo = histo[middle:]
        bin_edges = bin_edges[(middle+1):]

    # drop any zero bins
    keep = histo != 0
    histo = histo[keep]
    bin_edges = bin_edges[keep]

    # check for corner cases
    if np.product(histo)==1:
        return 2**histo[0]

    # Standarize histogram to obtain probabilities
    probabilities = histo.astype(np.float)/np.float(np.sum(histo))

    # initialize vector to fill with calculated entropies
    entropies = np.zeros(len(probabilities))

    for i in range(len(probabilities)-2):

        white_class = probabilities[0:(i+1)]
        white_class_sum = np.sum(white_class)
        white_class = -1*np.sum(np.multiply(white_class/white_class_sum,
                                            np.log(white_class/white_class_sum)))

        black_class = probabilities[(i+2):len(probabilities)]
        black_class_sum = np.sum(black_class)
        black_class = -1*np.sum(np.multiply(black_class/black_class_sum,
                                            np.log(black_class/black_class_sum)))

        entropies[i] = white_class + black_class

    idx_maximum_entropy = np.argmax(entropies)
    threshold = bin_edges[np.int(idx_maximum_entropy)]

    return threshold

class Kapur(object):
    '''
    This class implements the apur, Sahoo, & Wong method of entropy based
    thresholding of difference images (like those prodced by the iMAD-MAF transform).

    '''
    def __init__(self,bands_subset=np.array([0]), histogram=1000, symmetrical=True,
                                    argmax=True, clip_hist_tails=3, no_data=None):

        self.bands_subset = bands_subset
        self.argmax = argmax
        self.histogram = histogram
        self.symmetrical = symmetrical
        self.clip_hist_tails = clip_hist_tails
        self.no_data = no_data

    def fit(self, X):

        self.X = X

        if len(self.X.shape) == 2:

            self.bands = 1
            self.rows, self.columns = self.X.shape
            self.X = X[np.newaxis,:]

        elif len(self.X.shape) == 3:
            self.bands, self.rows, self.columns = self.X.shape

        else:
            logger.error('An image of 3 or 2 dimensions is expected.')

    def transform(self, X):

        n_used_bands = len(self.bands_subset)

        change_classification = np.ones((n_used_bands,self.columns * self.rows),
                                         dtype=np.int8)

        flag = True
        positive_threshold = None
        negative_threshold = None

        try:

            for k in range(n_used_bands):

                X = np.ravel(self.X[self.bands_subset[k].astype(int), :, :])
                X_copy = X

                if self.no_data is not None:
                    # handle no data values
                    idx_keep = X != self.no_data
                    X = X[idx_keep]

                # sorted image
                X = np.sort(X)

                if self.clip_hist_tails is not None:
                    X = clip_histogram_tails(X,self.clip_hist_tails)

                # decide on optimal number of bins for histogram
                bins = optimal_bins(X,method=self.histogram)

                # generate histogram based on this number of bins
                histo, bin_edges = np.histogram(X,bins)

                ### positive side
                positive_threshold = maximum_entropy_cut(histo,bin_edges,
                                                        argmax=self.argmax)

                if self.symmetrical:

                    ### negative side

                    # flip vectors
                    histo = histo[::-1]
                    bin_edges = bin_edges[::-1]

                    negative_threshold = maximum_entropy_cut(histo,bin_edges,
                                                            argmax=self.argmax)

                    if self.no_data is not None:
                        idx_keep_neg = idx_keep and (X_copy<negative_threshold)
                        change_classification[k,idx_keep_neg]=-1

                    else:
                        change_classification[k,X_copy<negative_threshold]=-1

                if self.no_data is not None:
                    idx_keep_neg = idx_keep and (X_copy>positive_threshold)
                    change_classification[k,idx_keep_neg]=-1
                    change_classification[k,np.invert(keep)]=self.no_data

                else:
                    change_classification[k,X_copy>positive_threshold]=-1

        except Exception as error:
            flag = False
            logger.error('Kapur thresholding failed with error: %s', str(repr(error)))

        # resize to original image shape
        change_classification = np.resize(change_classification,(self.rows, self.columns))

        return change_classification.astype(np.int8)

    def fit_transform(self, X):
        self.fit(X)
        return self.transform(X)
