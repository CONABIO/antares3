import re


def postgis_box_parser(box):
    """Parses the output of st_bbox into an in-memory bounding box

    Args:
        box (str): serialized postGIS bounding box

    Returns:
        list: list of four coordinates corresponding to [xmin, ymin, xmax, ymax]

    Example:
        >>> from madmex.util import parsers
        >>> print(parsers.postgis_box_parser('BOX(778783.5625 2951741.25,794875.8125 2970042.75)'))
    """
    pattern = re.compile(r'BOX\((-?\d+\.*\d*) (-?\d+\.*\d*),(-?\d+\.*\d*) (-?\d+\.*\d*)\)')
    m = pattern.search(box)
    return [float(x) for x in m.groups()]
