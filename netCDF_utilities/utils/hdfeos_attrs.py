"""
Script to process StructMetadata.0 from a HDFEOS file
and return a Python dictionary
"""
import re
from collections import OrderedDict
import numpy as np

__author__ = "Christopher Slocum"
__copyright__ = "Copyright 2018, Christopher Slocum"
__license__ = "BSD 3-Clause"
__email__ = "Christopher.Slocum@colostate.edu"


def insert_or_append(dictionary, key, value):
    """
    Insert a value in dict at key if one does not exist
    Otherwise, convert value to list and append

    Parameters
    ----------
    dictionary : dict
        dictionary to insert or append to
    key : str
        the dictionary key
    value
        the value to be added to the dictionary
    """
    if key in dictionary:
        if not isinstance(dictionary[key], list):
            dictionary[key] = [dictionary[key]]
        if value is not None:
            dictionary[key].append(value)
    else:
        dictionary[key] = value


def ttree_to_dict(ttree, level=0):
    """
    tabular tree to dictionary

    Parameters
    ----------
    ttree : list of dictionaries
        tabular tree
    level : int, optional
        used in recursion
    """
    result = OrderedDict()
    for i in range(len(ttree)):
        current = ttree[i]
        try:
            next_level = ttree[i+1]['level']
        except:
            next_level = -1
        # Edge cases
        if current['level'] > level:
            continue
        if current['level'] < level:
            return result
        # Recursion
        if next_level == level:
            insert_or_append(result, current['key'], current['value'])
        elif next_level > level:
            rr = ttree_to_dict(ttree[i+1:], level=next_level)
            insert_or_append(result, current['key'], rr)
        else:
            insert_or_append(result, current['key'], current['value'])
            return result
    return result


def hdfeos_attrs(ncid):
    """
    Get and process StructMetadata.0 string
    from a HDFEOS file read by netCDF4-python

    Parameters
    ----------
    ncid : object
        an instance of the netCDF4 Dataset class

    Returns
    -------
    attrs : dict
        a dictionary of the global attributes
    """
    attrs = []
    for line in getattr(ncid, 'StructMetadata.0').split('\n'):
        if line and "END" not in line:
            level = line.count("\t")
            item = line.strip("\t").split("=")
            key = item[0]
            if len(item) == 2:
                attr = re.sub('[()\"\s+]', '', item[1])
                if ',' in attr:
                    attr = attr.split(',')
                try:
                    attr = np.float_(attr).tolist()
                except ValueError:
                    pass
                if "GROUP" in key or "OBJECT" in key:
                    pair = (attr, None)
                else:
                    pair = (key, attr)
            else:
                pair = (key, None)
            attrs.append({"key": pair[0], "value": pair[1], "level": level})
    return ttree_to_dict(attrs)
