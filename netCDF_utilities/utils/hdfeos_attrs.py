"""Script to process StructMetadata.0 from a HDFEOS file."""
# Standard library imports
import re
import contextlib
from collections import OrderedDict
from typing import Any

# Third party imports
import numpy as np

# Local folder imports
from .nctyping import NCtDsetGrp

__author__ = "Christopher Slocum"
__copyright__ = "Copyright 2018, Christopher Slocum"
__license__ = "BSD 3-Clause"
__email__ = "Christopher.Slocum@colostate.edu"


def insert_or_append(dictionary: dict, key: str, value: Any) -> None:
    """
    Insert or append key value pair.

    Insert a value in dict at key if one does not exist
    Otherwise, convert value to list and append.

    Parameters
    ----------
    dictionary : dict
        Dictionary to insert or append to.
    key : str
        The dictionary key.
    value
        The value to be added to the dictionary.
    """
    if key in dictionary:
        if not isinstance(dictionary[key], list):
            dictionary[key] = [dictionary[key]]
        if value is not None:
            dictionary[key].append(value)
    else:
        dictionary[key] = value


def ttree_to_dict(ttree: list[dict], level: int=0) -> dict:
    """
    Return tabular tree to dictionary.

    Parameters
    ----------
    ttree : list of dictionaries
        The tabular tree.
    level : int, default=0
        The level value used in recursion.

    Returns
    -------
    dict
        The dictionary from tabular tree.
    """
    result = OrderedDict()
    for i in range(len(ttree)):
        current = ttree[i]
        try:
            next_level = ttree[i+1]["level"]
        except:
            next_level = -1
        # Edge cases
        if current["level"] > level:
            continue
        if current["level"] < level:
            return result
        # Recursion
        if next_level == level:
            insert_or_append(result, current["key"], current["value"])
        elif next_level > level:
            rr = ttree_to_dict(ttree[i+1:], level=next_level)
            insert_or_append(result, current["key"], rr)
        else:
            insert_or_append(result, current["key"], current["value"])
            return result
    return result


def hdfeos_attrs(ncid: NCtDsetGrp) -> dict:
    """
    Get StructMetadata.0 string.

    This function reads the StructMetadata.0 string
    from a HDFEOS file read by netCDF4-python.

    Parameters
    ----------
    ncid : object
        An instance of the netCDF4 Dataset class.

    Returns
    -------
    dict
        A dictionary of the global attributes.
    """
    attrs = []
    for line in getattr(ncid, "StructMetadata.0").split("\n"):
        if line and "END" not in line:
            level = line.count("\t")
            item = line.strip("\t").split("=")
            key = item[0]
            if len(item) == 2:
                attr = re.sub(r"""[()"\s+]""", "", item[1])
                if "," in attr:
                    attr = attr.split(",")
                with contextlib.suppress(ValueError):
                    attr = np.float32(attr).tolist()
                if "GROUP" in key or "OBJECT" in key:
                    pair = (attr, None)
                else:
                    pair = (key, attr)
            else:
                pair = (key, None)
            attrs.append({"key": pair[0], "value": pair[1], "level": level})
    return ttree_to_dict(attrs)
