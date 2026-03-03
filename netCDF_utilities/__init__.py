"""Utility to provide ncdump and ncgen."""
# Local folder imports
from .ncgen import ncgen
from .ncdump import ncdump

__all__ = ["ncgen", 'ncdump']
__version__ = "1.6"
