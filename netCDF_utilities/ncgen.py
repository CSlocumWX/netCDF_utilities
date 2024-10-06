"""
Generates a NetCDF file.

Attributes
----------
_STANDARD_GLOBAL_ATTR : list
    List of the CF complaint NetCDF standard global attributes
"""
# Standard library
from __future__ import division, print_function, absolute_import
import os
import json
import warnings
import datetime
from collections import OrderedDict
from typing import Optional, Union
from numbers import Number
# community packages
import toml
import numpy as np
import numpy.typing as npt
import netCDF4

# Climate and Forecast Convention global attributes
_STANDARD_GLOBAL_ATTR = [
    'title', 'institution', 'source', 'history', 'references', 'comments',
    'Conventions'
]
# Attribute Convention for Data Discovery (ACDD) attributes
_ACDD_GLOBAL_ATTR = [
    'summary', 'id', 'naming_authority', 'source', 'processing_level',
    'acknowledgment', 'license', 'standard_name_vocabulary', 'date_created',
    'creator_name', 'creator_email', 'creator_url', 'project', 'publisher_name',
    'publisher_email', 'publisher_url', 'geospatial_bounds',
    'geospatial_bounds_crs', 'geospatial_bounds_vertical_crs',
    'geospatial_lat_min', 'geospatial_lat_max', 'geospatial_lon_min',
    'geospatial_lon_max', 'geospatial_vertical_min', 'geospatial_vertical_max',
    'geospatial_vertical_positive', 'time_coverage_start', 'time_coverage_end',
    'time_coverage_duration', 'time_coverage_resolution', 'creator_type',
    'creator_institution', 'publisher_type', 'publisher_institution', 'program',
    'contributor_name', 'contributor_role', 'geospatial_lat_units',
    'geospatial_lat_resolution', 'geospatial_lon_units',
    'geospatial_lon_resolution', 'geospatial_vertical_units',
    'geospatial_vertical_resolution', 'date_modified', 'date_issued',
    'date_metadata_modified', 'product_version', 'keywords_vocabulary',
    'platform', 'platform_vocabulary', 'instrument', 'instrument_vocabulary',
    'cdm_data_type', 'metadata_link', 'keywords', 'keyword_vocabulary',
    'contributor_url', 'contributor_type', 'contributor_institution',
    'contributor_email'
]

_NC4_OPTIONS = [
    'zlib',
    'complevel',
    'shuffle',
    'least_significant_digit',
    'fill_value',
    'compression',
    'szip_coding',
    'szip_pixels_per_block',
    'blosc_shuffle',
    'fletcher32',
    'contiguous',
    'chunksizes',
    'endian',
    'significant_digits',
    'quantize_mode',
    'chunk_cache',
]
_NOT_ATTRS = ['size', 'dtype', 'dat', 'dim', 'var'] + _NC4_OPTIONS
_PACK_ATTRS = [
    "add_offset", "scale_factor", "least_significant_digit", "actual_range"
]

# Tuples of types
_SCALAR_TYPES = (float, int, np.float32, np.float64, np.int16, np.int32,
                 np.int64)
_ARRAY_TYPES = (np.ndarray, np.ma.core.MaskedArray, list, tuple)
_STR_TYPES = (str, np.str_, np.character)

# Attribute dtype for packing-related attributes
# default unpacked attribute dtype
_ATTR_UNPACK_DTYPE = np.float32


def _pack_unpack(unpacked_value: npt.ArrayLike, scale_factor: Number,
                 add_offset: Number) -> np.ndarray:
    """
    Packs and unpacks input to ensure consistency.

    Parameters
    ----------
    unpacked_value : array-like
        The unpacked data (e.g., actual_range)
    scale_factor : float
        The value to scale with during packing
    add_offset : float
        The offset value for packing

    Returns
    -------
    new_unpacked_value : array-like
        The value that has been packed and unpacked
    """
    # To avoid introducing a bias into the unpacked values due to truncation
    # when packing, round to the nearest integer rather than just truncating
    # towards zero using NumPy's rint function
    packed_value = np.rint(
        (np.asarray(unpacked_value) - add_offset) / scale_factor)
    # The unpacked data set to the default unpacked data type
    new_unpacked_value = (packed_value * scale_factor +
                          add_offset).astype(_ATTR_UNPACK_DTYPE)
    return new_unpacked_value


def _create_var(nc_fid: netCDF4.Dataset,
                varname: str,
                datatype: str,
                dimensions: Optional[npt.ArrayLike] = None,
                attributes: Optional[npt.ArrayLike] = None) -> netCDF4.Variable:
    """
    Create a new variable.

    Parameters
    ----------
    nc_fid : netCDF4.Dataset
        Dataset instance
    varname : str
        Variable name
    datatype : str
        Variable date type
    dimensions : array-like, optional
        Variable dimensions (must already exist)
    attributes : array-like, optional
        Variable attributes including fill_value and compression

    Returns
    -------
    var : netCDF4.Variable
        Instance of the Variable class
    """
    if dimensions is None:
        dimensions = ()
    if attributes is None:
        attributes = {}
    else:
        attributes = {
            key: value
            for key, value in attributes.items() if key in _NC4_OPTIONS
        }
    variable = nc_fid.createVariable(varname, datatype, dimensions,
                                     **attributes)
    return variable


def _add_to_group(group: netCDF4.Group, data: dict, config: dict,
                  nc_format: str) -> None:
    """
    Add to a group.

    In a netCDF4.Dataset, add to a group.

    Parameters
    ----------
    group : netCDF4.Group
        The existing group instance
    data : dict
        The data to be added to the group
    config : dict
        configuration information for group
    nc_format : str
        the NetCDF format
    """
    def _add_attribute(obj, attribute, attribute_value, dtype):
        """
        Add attribute.

        Parameters
        ----------
        obj : netCDF class instance
            The class/level to add attribute
        attribute : str
            the attribute name (key)
        attribute_value : object
            any valid data type for an attribute
        dtype : type
            the data type for the attribute_value
        """
        if attribute in _PACK_ATTRS:
            tmp_dtype = _ATTR_UNPACK_DTYPE
        else:
            tmp_dtype = dtype
        if isinstance(attribute_value, _SCALAR_TYPES):
            attribute_value = np.dtype(tmp_dtype).type(attribute_value)
        elif isinstance(attribute_value, _ARRAY_TYPES):
            attribute_value = np.ma.array(attribute_value, dtype=tmp_dtype)
        obj.setncattr(attribute, attribute_value)

    # add group level attributes
    if 'attributes' in config:
        attrs = config['attributes']
        for attr in attrs:
            group.setncattr(attr, attrs[attr])
    # Process dimensions
    nc_dims = config['dimensions']
    for dimname in nc_dims:
        ncattrs = list(nc_dims[dimname].keys())
        if 'size' in ncattrs:
            # use the size from the configuration file
            size = nc_dims[dimname]['size']
        elif 'dat' in ncattrs and isinstance(data[nc_dims[dimname]['dat']],
                                             _ARRAY_TYPES):
            # use the array for the size
            size = np.ma.array(data[nc_dims[dimname]['dat']]).size
        elif 'dat' in ncattrs and isinstance(data[nc_dims[dimname]['dat']],
                                             _SCALAR_TYPES):
            # scalar assumes the data value is the size
            size = data[nc_dims[dimname]['dat']]
        else:
            # Set size to None for unlimited dimension
            size = None
        # Create dimension
        group.createDimension(dimname, size=size)
        # Create a variable if the dimname is a variable
        var_create = True
        if 'var' in ncattrs:
            var_create = nc_dims[dimname]['var']
        if var_create:
            dtype = np.dtype(nc_dims[dimname]['dtype'])
            nc_dim = _create_var(group,
                                 varname=dimname,
                                 datatype=np.dtype(nc_dims[dimname]['dtype']),
                                 dimensions=(dimname),
                                 attributes=nc_dims[dimname])
            for ncattr in ncattrs:
                if ncattr not in _NOT_ATTRS:
                    _add_attribute(nc_dim, ncattr, nc_dims[dimname][ncattr],
                                   dtype)
                elif ncattr == 'dat':
                    group.variables[dimname][:] = data[nc_dims[dimname]['dat']]
    # Add non-dimension variables
    nc_vars = config['variables']
    for varname in nc_vars:
        # get data type if defined for variable
        if nc_vars[varname]['dtype'] == 'str':
            # Handle string vs char
            if nc_format != 'NETCDF4':
                dtype = 'c'
            else:
                dtype = np.str_
        else:
            # make user dtype a numpy.dtype
            dtype = np.dtype(nc_vars[varname]['dtype'])
        # get fill value if defined for variable
        fill_value = None
        for key in nc_vars[varname]:
            if key in ['fill_value', '_FillValue']:
                fill_value = nc_vars[varname][key]
                break
        # get the dimensions for the variable
        has_dim = 'dim' in nc_vars[varname]
        if has_dim:
            dimensions = nc_vars[varname]['dim']
            assert all(dimname in nc_dims for dimname in dimensions), \
                "One of the dimensions for %s does not exist" % varname
            dimensions = (dimensions)
        else:
            if dtype == 'c':
                size = len(data[varname])
                dimname = "strdim%02d" % size
                if dimname not in nc_vars:
                    group.createDimension(dimname, size)
                dimensions = (dimname, )
            else:
                dimensions = None
        nc_var = _create_var(group,
                             varname=varname,
                             datatype=dtype,
                             dimensions=dimensions,
                             attributes=nc_vars[varname])
        # add the attributes to the variable
        for ncattr in list(nc_vars[varname].keys()):
            if ncattr not in _NOT_ATTRS:
                attr_value = nc_vars[varname][ncattr]
                if ncattr == 'actual_range':
                    try:
                        scale_factor = nc_vars[varname]['scale_factor']
                        add_offset = nc_vars[varname]['add_offset']
                    except KeyError:
                        msg = "scale_factor and add_offset are not defined" + \
                              f" for {varname}."
                        warnings.warn(msg)
                    else:
                        attr_value = _pack_unpack(attr_value,
                                                  scale_factor=scale_factor,
                                                  add_offset=add_offset)
                _add_attribute(nc_var, ncattr, attr_value, dtype)
        # get the data if it exists
        if varname in data:
            if dtype == 'c':
                data_entry = netCDF4.stringtoarr(data[varname],
                                                 len(data[varname]))
                for count, char in enumerate(data_entry):
                    group.variables[varname][count] = char
            else:
                data_entry = data[varname]
                if has_dim:
                    if any(dtype is current_type
                           for current_type in _STR_TYPES):
                        data_entry = np.array(data_entry.data)
                    else:
                        data_entry = np.ma.array(data_entry)
                        if fill_value is not None:
                            data_entry = data_entry.filled(fill_value)
                    group.variables[varname][:] = data_entry
                else:
                    group.variables[varname][0] = data_entry


def ncgen(filename: str,
          data: dict,
          nc_config: Union[str, dict],
          nc_format: str = 'NETCDF4',
          return_instance: bool = False,
          clobber: bool = False) -> Union[None, netCDF4.Dataset]:
    """
    Generate a NetCDF file.

    Using input, given data, and configuration file create a new NetCDF file.

    Parameters
    ----------
    filename : str
        string containing the filename and path
    data : dict
        Python dictionary containing appropriate data
    nc_config : dict or file path
        Configuration options for globel attributes,
        dimensions, and variables
        Either as a dict or toml/json file
    nc_format : str (default='NETCDF4')
        See netCDF4 documentation for options
    return_instance : Boolean
        If you plan to append, get the instance of the NetCDF object
    clobber : Boolean
        netCDF4 can't open or delete bad NetCDF files. As a safeguard,
        the files must be manually removed

    Returns
    -------
    nc_fid : netCDF4.Dataset or None
        Dataset instance if return_instance = True
    """
    if os.path.exists(filename):
        if clobber:
            os.remove(filename)
        else:
            raise IOError("NetCDF file already exists: %s" % filename)
    if nc_format not in netCDF4._netCDF4._format_dict:
        raise ValueError(nc_format + " not a valid netCDF4 module format")
    if not isinstance(nc_config, dict):
        ext = os.path.basename(nc_config).split('.')[-1]
        if ext == 'json':
            with open(nc_config, mode='r', encoding='utf-8') as fid:
                nc_config = json.load(fid, object_pairs_hook=OrderedDict)
        elif ext == 'toml':
            with open(nc_config, mode='r', encoding='utf-8') as fid:
                nc_config = toml.load(fid, _dict=OrderedDict)
        else:
            raise IOError(
                "The following file extension for the configuration file is not supported: "
                + ext)
    with netCDF4.Dataset(filename, mode='w', clobber=clobber,
                         format=nc_format) as nc_fid:
        nc_attrs = nc_config['global_attributes']
        for global_attr in nc_attrs:
            if global_attr not in _STANDARD_GLOBAL_ATTR + _ACDD_GLOBAL_ATTR:
                warnings.warn(
                    "%s not in list of standard global attributes or ACDD" %
                    global_attr)
            setattr(nc_fid, global_attr, nc_attrs[global_attr])
        if hasattr(nc_fid, "date_created"):
            date_created = nc_fid.date_created
        else:
            date_created = "%sZ" % datetime.datetime.utcnow().isoformat(
                sep='T', timespec='milliseconds')
            nc_fid.date_created = date_created
        if not hasattr(nc_fid, "date_modified"):
            nc_fid.date_modified = date_created
        history = 'Created ' + date_created
        if 'history' in nc_attrs:
            history += ' ' + nc_attrs['history']
        nc_fid.history = history

        if 'global_attributes' in data:
            for attr in data['global_attributes']:
                setattr(nc_fid, attr, data['global_attributes'][attr])
        if 'groups' in nc_config:
            for groupname in nc_config['groups']:
                group = nc_fid.createGroup(groupname)
                _add_to_group(group, data['groups'][groupname],
                              nc_config['groups'][groupname], nc_format)
        else:
            _add_to_group(nc_fid, data, nc_config, nc_format)
    if return_instance:
        nc_fid = netCDF4.Dataset(filename, mode='a')
        return nc_fid
