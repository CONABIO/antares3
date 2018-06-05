from madmex.models import Tag, PredictClassification

def classification_to_cmap(x):
    """Generate a colormap (cmap) object for a given classification

    Colors are read from the database. The cmap can later be written to the metadata
    of a GeoTiff file using the write_colormap rasterio method
    0 is always considered no value and is therefore assigned no full transparency

    Args:
        x (str): Name of an existing classification, registered in the madmex_predictclassification
            table

    Returns:
        dict: A color map object {value0: [R, G, B, Alpha], ...}
    """
    def hex_to_rgba(hex_code):
        return tuple(int(hex_code[i:i+2], 16) for i in (1, 3 ,5)) + (255,)
    first = PredictClassification.objects.filter(name=x).first()
    scheme = first.tag.scheme
    qs_tag = Tag.objects.filter(scheme=scheme)
    hex_dict = dict([(i.numeric_code, i.color) for i in qs_tag])
    rgb_dict = {k:hex_to_rgba(v) for k,v in hex_dict.items()}
    rgb_dict[0] = (0,0,0,0)
    return rgb_dict

