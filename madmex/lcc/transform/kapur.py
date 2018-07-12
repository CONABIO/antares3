'''
2018 07 10
@author: jequihua
'''
import logging
import  math

from scipy import stats

from madmex.lcc.transform import TransformBase
import numpy as np


logger = logging.getLogger(__name__)

def optimal_bins(data_vector, method="shimazaki-shinomoto", bins=1000):

    '''
    Computes optimal number of bins to produce a histogram

    Methods: sturges, scott, freedman-diaconis, shimazaki-shinomoto, custom n bins

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
        N_MIN = 100   # minimum number of bins 
        N_MAX = 3000  # maximum number of bins 
        N = np.arange(N_MIN, N_MAX,10) # #of Bins
        D = (x_max - x_min) / N    #Bin size vector
        C = np.zeros(shape=(np.size(D), 1))

        # computation of the cost function
        for i in range(np.size(N)):
            ki = np.histogram(data_vector, bins=N[i])
            ki = ki[0]
            k = np.mean(ki) # mean of event count
            v = np.var(ki)  # variance of event count
            C[i] = (2 * k - v) / (D[i]**2) # the cost Function

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
    of standard deviations away from the mean

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

class Transform(TransformBase):
    '''
    This class implements the Kapur, Sahoo, & Wong method of entropy based
    thresholding of difference images (like those prodced by the iMAD-MAF transform).
    '''

    def __init__(self, band=0, histogram=1000, symmetrical=True,
                 argmax=True, clip_hist_tails=3, no_data=None):
        '''
        Constructor
        '''
        self.band=band
        self.argmax = argmax
        self.histogram = histogram
        self.symmetrical = symmetrical
        self.clip_hist_tails = clip_hist_tails
        self.no_data = no_data

    def transform(self, X):
        change_classification = np.zeros((self.cols * self.rows),
                                         dtype=np.int8)
        positive_threshold = None
        negative_threshold = None

        try:
            X = np.ravel(self.X[int(self.band),:,:])
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
            
            logger.debug('Positive threshold: %s' % positive_threshold)

            if self.symmetrical:

                ### negative side

                # flip vectors
                histo = histo[::-1]
                bin_edges = bin_edges[::-1]

                negative_threshold = maximum_entropy_cut(histo,bin_edges,
                                                        argmax=self.argmax)

                if self.no_data is not None:
                    idx_keep_neg = idx_keep and (X_copy<negative_threshold)
                    change_classification[idx_keep_neg] = 1

                else:
                    change_classification[X_copy<negative_threshold] = 1

            if self.no_data is not None:
                idx_keep_neg = idx_keep and (X_copy>positive_threshold)
                change_classification[idx_keep_neg]=1
                change_classification[np.invert(idx_keep)]=self.no_data

            else:
                change_classification[X_copy>positive_threshold] = 1

        except Exception as error:
            logger.error('Kapur thresholding failed with error: %s', str(repr(error)))

        logger.debug(np.unique(change_classification, return_counts=True))
        
        # resize to original image shape
        change_classification = np.resize(change_classification, (self.rows, self.cols))

        return change_classification.astype(np.int8)