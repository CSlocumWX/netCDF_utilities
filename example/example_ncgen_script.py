"""
Example program on how to generate a NetCDF file via Python

This script contains an example of how to write data to a
NetCDF file. This tool can be used to generate NetCDF3 or
NetCDF4 with either fixed or unlimited dimensions.

This example uses the json files in this directory to
configure the NetCDF metadata. This can be used to generate
a CF compliant NetCDF file.

References
----------
.. [1] Whitaker, J.: netCDF4 API documentation.
       http://unidata.github.io/netcdf4-python/
.. [2] CF Conventions and Metadata. http://cfconventions.org/
"""
from __future__ import division, print_function, absolute_import
import numpy as np
from netCDF_utilities import ncgen

# Print ncgen docstring
print(ncgen.__doc__)

# Create some random data
lats = np.linspace(-90, 90)
lons = np.linspace(0, 359)
time = np.array([123456, 123457], dtype=np.int32)
random_data = np.random.random((time.size, lats.size, lons.size)) * 75.

# set a value to the max and min
random_data[0, 0, 0] = 0.
random_data[0, 0, 1] = 75.

#####################################################################
# First example: We have all our data and just want a NetCDF file
data = {'lat': lats,
        'lon': lons,
        'time': time,
        'pwat': random_data}
# Set  the example configuration file
nc_config = "./example_nc_config.toml"
# Call ncgen
ncgen('all_data_ex.nc', data, nc_config, clobber=True)

####################################################################
# Second example: We don't have all our data or we will append in time
data = {'lat': lats,
        'lon': lons}

nc_config = "./example_nc_config_timeUnlimited.toml"
# ncgen returns an instance of the NetCDF file and we will use a 'with' statement
with ncgen('unlimited_time_ex.nc', data, nc_config, return_instance=True, clobber=True) as nc_fid:
    # To write to the unlimited dimensions, use a procedure like
    # the one provided below.
    for count in range(time.size):
        # increase the time dimension by one by writing a new time
        nc_fid.variables['time'][count] = time[count]
        # write data corresponding to that time
        nc_fid.variables['pwat'][count, :, :] = random_data[count, :, :]


####################################################################
# Third example: Groups
data = {'groups': {'blah': {}}}
data['groups']['blah'].update({'lat': lats,
        'lon': lons,
        'time': time,
        'pwat': random_data})

nc_config = "./example_groups_nc_config.toml"
ncgen('groups.nc', data, nc_config, clobber=True)

#####################################################################
# First example: We have all our data and just want a NetCDF file
data = {'lat': lats,
        'lon': lons,
        'time': time,
        'pwat': random_data}
# Set  the example configuration file
nc_config = "./example_nc_config_packed.toml"
# Call ncgen
ncgen('packed_ex.nc', data, nc_config, clobber=True)
