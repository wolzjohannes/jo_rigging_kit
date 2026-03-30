from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from . import base
from . import utils
from . import modules
from . import systems
from . import shows
import pymel.core as pmc

# Import built-in modules
import logging

#######################################################
# GLOBALS
#######################################################

logging.basicConfig(level=logging)
_LOGGER = logging.getLogger(__name__ + ".py")
MESSAGE = ("This rig lib is legacy. The dragon eye lid system is the only reason for existence."
                  "So pls do not use it except of the eyelid module for the HOD dragons.")

#######################################################
# FUNCTIONS
#######################################################

def print_legacy_warning():
    _LOGGER.warning(MESSAGE)
    pmc.warning(MESSAGE)

print_legacy_warning()

