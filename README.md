NetCDF utilities
================

What are my NetCDF utilities?
-----------------------------

Simply put, my utilities are snippets of code I constantly reused
in my Python workflow to read and write NetCDF files. I posted
the files here so others could use them. Hopefully, others find
them useful.

With updates to the underlying NetCDF C libraries, HDFEOS files
can be read by netCDF4-python. However, the attribute information
is contained in a string called 'StructMetadata.0'. To get the
attribute information, `netCDF_utilities.ncdump` checks the file
and returns global attributes with the metadata tree. The netCDF4
Dataset object instance is not updated to include these
attributes.

Installation
------------

`python setup.py install`

Usage
-----

### ncdump
`netCDF_utilities.ncdump` returns lists containing the dimensions,
variables, and their attribute information. The information is
similar to that of the Unidata ncdump binary utility. If `verb=True`,
the information will be printed to the screen. For an example, see
http://schubert.atmos.colostate.edu/~cslocum/netcdf_example.html

### ncgen
`netCDF_utilities.ncgen` takes a data dictionary and a attribute
configuration dictionary to generate a NetCDF3 or NetCDF4 file
using the Unidata NetCDF4 API [1]. The attribute information can
be stored in a JSON file or as a Python dict/OrderedDict. Dimensions
can also be unlimited. At the moment, groups are not supported.
See `./test/` for examples.

References
----------
.. [1] NetCDF4 API documentation.
       http://unidata.github.io/netcdf4-python/

.. [2] CF Conventions and Metadata. http://cfconventions.org/

License information
-------------------

See the file ``LICENSE.txt`` for information on the history of this
software, terms & conditions for usage, and a DISCLAIMER OF ALL
WARRANTIES.
