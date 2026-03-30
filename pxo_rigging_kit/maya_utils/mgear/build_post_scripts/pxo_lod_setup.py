"""
Custom step to import lod set data.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import built-in modules
import logging

# Import third-party modules
from future import standard_library
import mgear.shifter.custom_step as cstp
import pymel.core as pmc

# Import local modules
from pxo_rigging_kit.maya_utils.lod_utils import load

standard_library.install_aliases()

##########################################################
# GLOBALS
##########################################################

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)

##########################################################
# FUNCTIONS
##########################################################


class CustomShifterStep(cstp.customShifterMainStep):

    def __init__(self):
        self.name = "pxo_lod_setup"
        self.acting_step_dict = None

    def run(self, stepDict):
        pmc.select(clear=True)
        load()