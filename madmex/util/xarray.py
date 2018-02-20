import xarray as xr
from xarray import DataArray
import numpy as np

def to_float(x):
    """TAkes a DataArray, converts data flagged as nodata to Nan and return corresponding array in float

    Meant to be used with Dataset.apply() to apply to all the DataArrays of a Dataset

    Args:
        x (xarray.DataArray): Input DataArray. Must have a nodata flag written to
            x.attrs['nodata']

    Return:
        xarray.DataArray: The corresponding DataArray cast to float and with nodata
        converted to Nan

    Example:
        >>> import xarray as xr
        >>> import numpy as np
        >>> from datetime import datetime
        >>> import datetime as dt
        >>> from xarray.testing import assert_identical

        >>> # Build test data
        >>> arr = np.array([1,2,-9999], dtype=np.int16)
        >>> date_list = [datetime(2018, 1, 1) + dt.timedelta(delta) for delta in range(3)]
        >>> xarr = xr.DataArray(arr, dims=['time'], coords={'time': date_list},
        >>>                     attrs={'nodata': -9999})
        >>> xset = xr.Dataset({'blue': xarr, 'green': xarr, 'red': xarr})
        >>> print(xset)

        >>> # Round trip int to float (with nodata replaced by nan) to int
        >>> xset_float = xset.apply(func=to_float, keep_attrs=True)
        >>> print(xset_float)
        >>> xset_int = xset_float.apply(to_int)
        >>> print(xset_int)
        >>> assert_identical(xset, xset_int)
    """
    x_float = x.where(x != x.attrs['nodata'])
    return x_float

def to_int(x):
    """TAkes a DataArray in float and converts it to int, converting Nan to nodata flags

    Meant to be used with Dataset.apply() to apply to all the DataArrays of a Dataset

    Args:
        x (xarray.DataArray): Input DataArray. Must have a nodata flag written to
            x.attrs['nodata']

    Return:
        xarray.DataArray: The corresponding DataArray cast to int16 and with Nan converted
        to nodata value

    Example:
        >>> import xarray as xr
        >>> import numpy as np
        >>> from datetime import datetime
        >>> import datetime as dt
        >>> from xarray.testing import assert_identical

        >>> # Build test data
        >>> arr = np.array([1,2,-9999], dtype=np.int16)
        >>> date_list = [datetime(2018, 1, 1) + dt.timedelta(delta) for delta in range(3)]
        >>> xarr = xr.DataArray(arr, dims=['time'], coords={'time': date_list},
        >>>                     attrs={'nodata': -9999})
        >>> xset = xr.Dataset({'blue': xarr, 'green': xarr, 'red': xarr})
        >>> print(xset)

        >>> # Round trip int to float (with nodata replaced by nan) to int
        >>> xset_float = xset.apply(func=to_float, keep_attrs=True)
        >>> print(xset_float)
        >>> xset_int = xset_float.apply(to_int)
        >>> print(xset_int)
        >>> assert_identical(xset, xset_int)
    """
    x_int = x.where(DataArray.notnull(x), x.attrs['nodata'])
    return x_int.astype('int16')

