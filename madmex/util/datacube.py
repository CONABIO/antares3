import datacube

def var_to_ind(variables, product):
    """Helper to get a list of index from a list of variables names

    Useful for telling the modeling module which are the categorical variables
    that should be encoded using One Hot Encoding

    Args:
        names (list): List of strings corresponding to existing variable names in the
            product
        product (str): Name of an existing datacube product

    Return:
        list: LIst of integer corresponding to dataset positions

    Example:
        >>> from madmex.util.datacube import var_to_ind

        >>> ind = var_to_ind(['blue', 'red', 'swir2'], 'ls8_espa_mexico')
        >>> print(ind)
    """
    dc = datacube.Datacube()
    prod = dc.index.products.get_by_name(name=product)
    measurements = list(prod.measurements)
    indices = [measurements.index(x) for x in variables]
    return indices
