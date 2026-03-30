"""
Globally rigging package. It will contain utility code for daily usage.
Main reason is to establish a global rigging standart for all pso facilities.
And make cooperation easier for all facilites.
"""

# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Import built-in modules
import os

# Import third-party modules
from future import standard_library
import pixo_paths
from pkg_resources import DistributionNotFound
from pkg_resources import get_distribution

standard_library.install_aliases()

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # Package is not installed
    __version__ = "0.0.0-pxodev.1"
