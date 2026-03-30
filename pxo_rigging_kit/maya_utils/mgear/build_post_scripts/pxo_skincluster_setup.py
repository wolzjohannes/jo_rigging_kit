"""
Custom step to import existing skinning data.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
from future import standard_library

# Import third-party modules
import mgear.shifter.custom_step as cstp # noqa: import error

from pxo_rigging_kit.maya_utils.deformers.utilities.commandline_shortcuts import skincluster_import
from pxo_rigging_kit.maya_utils.deformers.utilities.supply import get_external_skinclusters

##########################################################
# GLOBALS
##########################################################

standard_library.install_aliases()

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)

##########################################################
# FUNCTIONS
##########################################################


class CustomShifterStep(cstp.customShifterMainStep):

    def __init__(self):
        self.name = "pxo_skinning_setup"
        self.acting_step_dict = None

    def run(self, stepDict):
        # Here we import the latest skinning pack for the whole asset with our own skin I/O

        exported_skinclusters = get_external_skinclusters()

        skincluster_import(exported_skinclusters)
