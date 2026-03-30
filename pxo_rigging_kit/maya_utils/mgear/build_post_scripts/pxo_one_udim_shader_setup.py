"""
Custom script for one udim shader creation.
Requieres:
- pxo_asset_assembly_NTW (maya network node)
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

# Import local modules
from pxo_rigging_kit.maya_utils.shader_utils import \
    apply_udim_shader_from_asset_assembly
from pxo_rigging_kit.maya_utils.shader_utils import clear

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
        self.name = "pxo_one_udim_shader_setup"

    def run(self, stepDict=None):
        clear()
        apply_udim_shader_from_asset_assembly()



"""
from pxo_rigging_kit.maya_utils.shader_utils import (
    apply_udim_shader_from_asset_assembly,
    clear,
)
clear()
apply_udim_shader_from_asset_assembly()


"""