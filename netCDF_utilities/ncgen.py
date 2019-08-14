"""
Generates a NetCDF file

Attributes
----------
_standard_global_attr : list
    List of the CF complaint NetCDF standard global attributes
"""
from __future__ import division, print_function, absolute_import
import netCDF4
import datetime
import numpy as np
import os
import warnings

_standard_global_attr = ['title', 'institution', 'source', 'history',
                         'references', 'comments', 'Conventions']
_NC4_OPTIONS = ['zlib', 'complevel', 'shuffle', 'least_significant_digit']
_NOT_ATTRS = ['size', 'dtype', 'dat', 'dim', 'var'] + _NC4_OPTIONS

def _create_var(nc_fid, name, dtype, dimensions=None, attributes=None):
    if dimensions is None:
        dimensions = ()
    if attributes is None:
        attributes = {}
    else:
        attributes = {key:value for key, value in attributes.items() if key in _NC4_OPTIONS}
    return nc_fid.createVariable(name, dtype, dimensions, **attributes)


def ncgen(filename, data, nc_config, nc_format='NETCDF4',
        return_instance=False, clobber=False):
    """
    generates a NetCDF file based on a given data and configuration file

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
    """
    if os.path.exists(filename):
        if clobber:
            os.remove(filename)
        else:
            raise IOError("NetCDF file already exists: %s" % filename)
    if nc_format not in netCDF4._netCDF4._format_dict:
        raise ValueError(nc_format + " not a valid netCDF4 module format")
    if not isinstance(nc_config, dict):
        from collections import OrderedDict
        ext = os.path.basename(nc_config).split('.')[-1]
        if ext == 'json':
            import json
            nc_config = json.load(open(nc_config, 'r'), object_pairs_hook=OrderedDict)
        elif ext == 'toml':
            import toml
            nc_config = toml.load(open(nc_config, 'r'), _dict=OrderedDict)
        else:
            raise IOError("The following file extension for the configuration file is not supported: " + ext)
    nc_fid = netCDF4.Dataset(filename, mode='w', clobber=clobber,
                             format=nc_format)
    nc_attrs = nc_config['global_attributes']
    for global_attr in nc_attrs:
        if global_attr not in _standard_global_attr:
            warnings.warn("%s not in list of standard global attributes" % global_attr)
        setattr(nc_fid, global_attr, nc_attrs[global_attr])
    history = ''
    if 'history' in nc_attrs:
        history += nc_attrs['history'] 
    nc_fid.history = " Generated %s" % datetime.datetime.utcnow()
    if 'groups' in nc_config:
        for groupname in nc_config['groups']:
            group = nc_fid.createGroup(groupname)
            _add_to_group(group, data['groups'][groupname], nc_config['groups'][groupname], nc_format)
    else:
        _add_to_group(nc_fid, data, nc_config, nc_format)
    nc_fid.close()
    if return_instance:
        nc_fid = netCDF4.Dataset(filename, mode='a')
        return nc_fid


def _add_to_group(group, data, config, nc_format):
    def _add_attribute(obj, attribute, attribute_value, dtype):
        if any([isinstance(attribute_value, current_type) for current_type in [float, int, np.float, np.int]]):
            attribute_value =  np.dtype(dtype).type(attribute_value)
        elif any([isinstance(attribute_value, current_type) for current_type in [np.ndarray, list, tuple]]):
            attribute_value = np.array(attribute_value, dtype=dtype)
        obj.setncattr(attribute, attribute_value)

    if 'attributes' in config:
        attrs = config['attributes']
        for attr in attrs:
            group.setncattr(attr, attrs[attr])
    nc_dims = config['dimensions']
    for dim in nc_dims:
        ncattrs = list(nc_dims[dim].keys())
        if 'size' in ncattrs:
            group.createDimension(dim, nc_dims[dim]['size'])
        elif 'dat' in ncattrs:
            group.createDimension(dim, data[nc_dims[dim]['dat']].size)
        else:
            group.createDimension(dim, None)
        var_create = True
        if 'var' in ncattrs:
            var_create = nc_dims[dim]['var']
        if var_create:
            dtype = np.dtype(nc_dims[dim]['dtype'])
            nc_dim = _create_var(group, name=dim, dtype=np.dtype(nc_dims[dim]['dtype']), dimensions=(dim), attributes=nc_dims[dim])
            for ncattr in ncattrs:
                if ncattr not in _NOT_ATTRS:
                    _add_attribute(nc_dim, ncattr,  nc_dims[dim][ncattr], dtype)
                elif ncattr == 'dat':
                    group.variables[dim][:] = data[nc_dims[dim]['dat']]
    nc_vars = config['variables']
    for var in nc_vars:
        if nc_vars[var]['dtype'] == 'str':
            if nc_format != 'NETCDF4':
                dtype = 'c'
            else:
                dtype = np.str
        else:
            dtype = np.dtype(nc_vars[var]['dtype'])
        has_dim = 'dim' in nc_vars[var]
        if has_dim:
            dimensions = nc_vars[var]['dim']
            assert all(dim in nc_dims for dim in dimensions), \
                "One of the dimensions for %s does not exist" % var
            nc_var = _create_var(group, name=var, dtype=dtype, dimensions=(dimensions), attributes=nc_vars[var])
        else:
            if dtype == 'c':
                size = len(data[var])
                name = "strdim%02d" % size
                if name not in nc_fid.variables:
                    group.createDimension(name, size)
                nc_var = _create_var(group, name=var, dtype=dtype, dimensions=(name,), attributes=nc_vars[var])
            else:
                nc_var = _create_var(group, name=var, dtype=dtype, attributes=nc_vars[var])
        for ncattr in list(nc_vars[var].keys()):
            if ncattr not in _NOT_ATTRS:
                attr_value = nc_vars[var][ncattr]
                _add_attribute(nc_var, ncattr, attr_value, dtype)
        if var in data:
            if dtype == 'c':
                data_entry = netCDF4.stringtoarr(data[var], len(data[var]))
                for count, char in enumerate(data[var]):
                    group.variables[var][count] = data_entry[count]
            else:
                data_entry = data[var]
                if has_dim:
                    group.variables[var][:] = data_entry.astype(dtype)
                else:
                    group.variables[var][0] = data_entry
