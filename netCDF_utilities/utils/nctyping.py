"""The custom typing hints used."""
# Standard library imports
from typing import Union

# Third party imports
import netCDF4
import numpy as np
from typing_extensions import TypeAlias

Number = Union[int, float, np.integer, np.floating]
NCtDsetGrp: TypeAlias = Union[netCDF4._netCDF4.Dataset, netCDF4._netCDF4.Group]
NCtVar: TypeAlias = netCDF4._netCDF4.Variable
