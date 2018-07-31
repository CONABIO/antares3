import numpy as np

def groupby(X, y):
    """Split a 2D array along the zero dimension using an array of groups

    Args:
        X (np.ndarray): 2D array of independent variables. Must be of shape (n,m)
        y (np.ndarray): Array of classes/groups (dependent variable of a classification)
            Must be of shape (n)

    Return:
        zip: Generator of (group, np.ndarray) tupples. The second element correspond
        to the split X array
    """
    sidy = y.argsort(kind='mergesort')
    y_sorted = y[sidy]
    X_sorted = X[sidy,:]
    X_out = np.split(X_sorted, np.flatnonzero(y_sorted[1:] != y_sorted[:-1])+1 )
    return zip(np.unique(y), X_out)
