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
_NOT_ATTRS = ['size', 'dtype', 'dat', 'dim'] + _NC4_OPTIONS

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
    nc_config : dict
        Dictionary with configuration options for globel attributes,
        dimensions, and variables
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
    nc_attr = nc_config['global_attributes']
    nc_dims = nc_config['dimensions']
    nc_vars = nc_config['variables']
    nc_fid = netCDF4.Dataset(filename, mode='w', clobber=clobber,
                             format=nc_format)
    for global_attr in nc_attr:
        if global_attr not in _standard_global_attr:
            warnings.warn("%s not in list of standard global attributes" %
                          global_attr)
        setattr(nc_fid, global_attr, nc_attr[global_attr])
    nc_fid.history = "Generated %s" % datetime.datetime.utcnow()
    for dim in nc_dims:
        ncattrs = list(nc_dims[dim].keys())
        if 'size' in ncattrs:
            nc_fid.createDimension(dim, nc_dims[dim]['size'])
        else:
            nc_fid.createDimension(dim, data[nc_dims[dim]['dat']].size)
        nc_dim = _create_var(nc_fid, name=dim, dtype=np.dtype(nc_dims[dim]['dtype']), dimensions=(dim), attributes=nc_dims[dim])
        for ncattr in ncattrs:
            if ncattr not in _NOT_ATTRS:
                nc_dim.setncattr(ncattr, nc_dims[dim][ncattr])
            elif ncattr == 'dat':
                nc_fid.variables[dim][:] = data[nc_dims[dim]['dat']]
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
            nc_var = _create_var(nc_fid, name=var, dtype=dtype, dimensions=(dimensions), attributes=nc_vars[var])
        else:
            if dtype == 'c':
                size = len(data[var])
                name = "strdim%02d" % size
                if name not in nc_fid.variables:
                    nc_fid.createDimension(name, size)
                nc_var = _create_var(nc_fid, name=var, dtype=dtype, dimensions=(name,), attributes=nc_vars[var])
            else:
                nc_var = _create_var(nc_fid, name=var, dtype=dtype, attributes=nc_vars[var])
        for ncattr in list(nc_vars[var].keys()):
            if ncattr not in _NOT_ATTRS:
                nc_var.setncattr(ncattr, nc_vars[var][ncattr])
        if var in data:
            if dtype == 'c':
                data_entry = netCDF4.stringtoarr(data[var], len(data[var]))
                for count, char in enumerate(data[var]):
                    nc_fid.variables[var][count] = data_entry[count]
            else:
                data_entry = data[var]
                if has_dim:
                    nc_fid.variables[var][:] = data_entry
                else:
                    nc_fid.variables[var][0] = data_entry
    nc_fid.close()
    if return_instance:
        nc_fid = netCDF4.Dataset(filename, mode='a')
        return nc_fid
