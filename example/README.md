# NetCDF utilities example

The `example_ncgen_script.py` shows how to use a configuration file
(e.g., `example_nc_config.toml`) to combine metadata with data to
generate a netCDF file.

## Sections in the configuration file

### Global attributes
This is the metadata for the file. Typically, `source`, `Conventions`,
`institution`, and a `title` are added so that folks have some general
information about the data.

### Dimensions
These are the data dimensions. You'll need/want a `long_name`,
`standard_name`, and `units` in the file. These are all part of
the NetCDF file convention. For NetCDF utilities, you'll need
to provide the data type `dtype` and `dat` and/or `size` to
provide the rest of the information needed for creating
the dimensions.

### Variables
This is where your data lives. Again, `long_name`,
`standard_name`, and `units` are needed. Also, you'll need to
provide the dimensions that the variable depends on in a list.


### Example toml file

```toml
[global_attributes]  # add your global attributes to this section of the file
    source = "some_script.py"
    title = "Example toml file"

[dimensions]  # NetCDF variable dimensions

    [dimensions.time]
        long_name = "time"
        standard_name = "time"
        calendar = "standard"
        units = "hours since 1970-01-01"
        dtype = "int32"
        dat = "time"

[variables]  # Variable section of the netCDF file

    [variables.pwat]
        long_name = "temperature"
        standard_name = "temperature"
        units = "K"
        dtype = "float32"
        dim = [ "time", ]
```
