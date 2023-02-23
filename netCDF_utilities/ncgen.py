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

_standard_global_attr = [
    'title', 'institution', 'source', 'history', 'references', 'comments',
    'Conventions'
]
_acdd_global_attr = [
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
    'zlib', 'complevel', 'shuffle', 'least_significant_digit', 'fill_value'
]
_NOT_ATTRS = ['size', 'dtype', 'dat', 'dim', 'var'] + _NC4_OPTIONS
_SCALAR_TYPES = [float, int, np.float, np.int]
_ARRAY_TYPES = [np.ndarray, np.ma.core.MaskedArray, list, tuple]
_STR_TYPES = [str, np.str, np.character, np.unicode]


def _create_var(nc_fid, name, dtype, dimensions=None, attributes=None):
    if dimensions is None:
        dimensions = ()
    if attributes is None:
        attributes = {}
    else:
        attributes = {
            key: value
            for key, value in attributes.items() if key in _NC4_OPTIONS
        }
    var = nc_fid.createVariable(name, dtype, dimensions, **attributes)
    return var


def ncgen(filename,
          data,
          nc_config,
          nc_format='NETCDF4',
          return_instance=False,
          clobber=False):
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
            nc_config = json.load(open(nc_config, 'r'),
                                  object_pairs_hook=OrderedDict)
        elif ext == 'toml':
            import toml
            nc_config = toml.load(open(nc_config, 'r'), _dict=OrderedDict)
        else:
            raise IOError(
                "The following file extension for the configuration file is not supported: "
                + ext)
    nc_fid = netCDF4.Dataset(filename,
                             mode='w',
                             clobber=clobber,
                             format=nc_format)
    nc_attrs = nc_config['global_attributes']
    for global_attr in nc_attrs:
        if global_attr not in _standard_global_attr + _acdd_global_attr:
            warnings.warn(
                "%s not in list of standard global attributes or ACDD" %
                global_attr)
        setattr(nc_fid, global_attr, nc_attrs[global_attr])
    date_created = "%sZ" % datetime.datetime.utcnow().isoformat(
        sep='T', timespec='milliseconds')
    history = 'Created ' + date_created
    if 'history' in nc_attrs:
        history += ' ' + nc_attrs['history']
    nc_fid.history = history
    nc_fid.date_created = date_created
    nc_fid.date_modified = date_created

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
    nc_fid.close()
    if return_instance:
        nc_fid = netCDF4.Dataset(filename, mode='a')
        return nc_fid


def _add_to_group(group, data, config, nc_format):
    def _add_attribute(obj, attribute, attribute_value, dtype):
        if attribute not in [
                "add_offset", "scale_factor", "least_significant_digit",
                "actual_range"
        ]:
            if any([
                    isinstance(attribute_value, current_type)
                    for current_type in _SCALAR_TYPES
            ]):
                attribute_value = np.dtype(dtype).type(attribute_value)
            elif any([
                    isinstance(attribute_value, current_type)
                    for current_type in _ARRAY_TYPES
            ]):
                attribute_value = np.ma.array(attribute_value, dtype=dtype)
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
        elif 'dat' in ncattrs and any([
                isinstance(data[nc_dims[dim]['dat']], current_type)
                for current_type in _ARRAY_TYPES
        ]):
            group.createDimension(dim,
                                  np.ma.array(data[nc_dims[dim]['dat']]).size)
        elif 'dat' in ncattrs and any([
                isinstance(data[nc_dims[dim]['dat']], current_type)
                for current_type in _SCALAR_TYPES
        ]):
            group.createDimension(dim, data[nc_dims[dim]['dat']])
        else:
            group.createDimension(dim, None)
        var_create = True
        if 'var' in ncattrs:
            var_create = nc_dims[dim]['var']
        if var_create:
            dtype = np.dtype(nc_dims[dim]['dtype'])
            nc_dim = _create_var(group,
                                 name=dim,
                                 dtype=np.dtype(nc_dims[dim]['dtype']),
                                 dimensions=(dim),
                                 attributes=nc_dims[dim])
            for ncattr in ncattrs:
                if ncattr not in _NOT_ATTRS:
                    _add_attribute(nc_dim, ncattr, nc_dims[dim][ncattr], dtype)
                elif ncattr == 'dat':
                    group.variables[dim][:] = data[nc_dims[dim]['dat']]
    nc_vars = config['variables']
    for var in nc_vars:
        # get data type if defined for variable
        if nc_vars[var]['dtype'] == 'str':
            if nc_format != 'NETCDF4':
                dtype = 'c'
            else:
                dtype = np.str
        else:
            dtype = np.dtype(nc_vars[var]['dtype'])
        # get fill value if defined for variable
        fill_value = None
        for key in nc_vars[var]:
            if key in ['fill_value', '_FillValue']:
                fill_value = nc_vars[var][key]
                break
        # get the dimensions for the variable
        has_dim = 'dim' in nc_vars[var]
        if has_dim:
            dimensions = nc_vars[var]['dim']
            assert all(dim in nc_dims for dim in dimensions), \
                "One of the dimensions for %s does not exist" % var
            nc_var = _create_var(group,
                                 name=var,
                                 dtype=dtype,
                                 dimensions=(dimensions),
                                 attributes=nc_vars[var])
        else:
            if dtype == 'c':
                size = len(data[var])
                name = "strdim%02d" % size
                if name not in nc_vars:
                    group.createDimension(name, size)
                nc_var = _create_var(group,
                                     name=var,
                                     dtype=dtype,
                                     dimensions=(name, ),
                                     attributes=nc_vars[var])
            else:
                nc_var = _create_var(group,
                                     name=var,
                                     dtype=dtype,
                                     attributes=nc_vars[var])
        # add the attributes to the variable
        for ncattr in list(nc_vars[var].keys()):
            if ncattr not in _NOT_ATTRS:
                attr_value = nc_vars[var][ncattr]
                _add_attribute(nc_var, ncattr, attr_value, dtype)
        # get the data if it exists
        if var in data:
            if dtype == 'c':
                data_entry = netCDF4.stringtoarr(data[var], len(data[var]))
                for count, char in enumerate(data[var]):
                    group.variables[var][count] = data_entry[count]
            else:
                data_entry = data[var]
                if has_dim:
                    if any(
                        [dtype is current_type for current_type in _STR_TYPES]):
                        group.variables[var][:] = np.array(data_entry.data)
                    else:
                        data_entry = np.ma.array(data_entry)
                        if fill_value is not None:
                            data_entry = data_entry.filled(fill_value)
                        group.variables[var][:] = data_entry
                else:
                    group.variables[var][0] = data_entry
