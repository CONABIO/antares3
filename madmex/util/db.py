from madmex.models import Tag, PredictClassification, ValidClassification

def classification_to_cmap(x, region):
    """Generate a colormap (cmap) object for a given classification

    Colors are read from the database. The cmap can later be written to the metadata
    of a GeoTiff file using the write_colormap rasterio method
    0 is always considered no value and is therefore assigned no full transparency

    Args:
        x (str): Name of an existing classification, registered in the madmex_predictclassification
            table
        region (geom): geometry of region to avoid blowing DB memory in query

    Returns:
        dict: A color map object {value0: [R, G, B, Alpha], ...}
    """
    def hex_to_rgba(hex_code):
        return tuple(int(hex_code[i:i+2], 16) for i in (1, 3 ,5)) + (255,)
    first = PredictClassification.objects.filter(predict_object__the_geom__intersects=region).filter(name=x).first()
    scheme = first.tag.scheme
    qs_tag = Tag.objects.filter(scheme=scheme)
    hex_dict = dict([(i.numeric_code, i.color) for i in qs_tag])
    rgb_dict = {k:hex_to_rgba(v) for k,v in hex_dict.items()}
    rgb_dict[0] = (0,0,0,0)
    return rgb_dict



def get_label_encoding(scheme, inverse=False):
    """Get label --> Numeric code correspondance for a given classification scheme as a dictionary

    Args:
        scheme (str): Classification scheme
        inverse (bool): Use numerics codes as keys and labels as values if True.
            Defaults to False (labels as keys and codes as values)

    Return:
        dict: A dictionary of encoding mapping

    Example:
        >>> from madmex.io.helpers import get_label_encoding
        >>> from pprint import pprint

        >>> d = get_label_encoding('madmex')
        >>> pprint(d)
        >>> d_inv = get_label_encoding('madmex', inverse=True)
        >>> pprint(d_inv)
    """
    query_set = Tag.objects.filter(scheme=scheme)
    if not inverse:
        out = {row.value:row.numeric_code for row in query_set}
    else:
        out = {row.numeric_code:row.value for row in query_set}
    return out


def get_validation_scheme_name(name):
    """Given the name/identifier of an ingested validation dataset, returns its scheme name

    Args:
        name (str): Name, identifier of the classification, as it appears in the
            ValidClassification table

    Example:
        >>> from madmex.util.db import get_validation_scheme_name

        >>> get_validation_scheme_name('bis_interpret')

    Return:
        str: The name of the scheme used by that validation dataset
    """
    valid_obj = ValidClassification.objects.filter(valid_set=name).first()
    scheme = valid_obj.valid_tag.scheme
    return scheme
