"""
Custom step to localize skincluster influences.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import third-party modules
from future import standard_library
import mgear.shifter.custom_step as cstp

standard_library.install_aliases()

# Import built-in modules
from importlib import reload
import logging

# Import local modules

from pxo_rigging_kit.maya_utils.deformers.utilities import skincluster_layering
reload(skincluster_layering)

from importlib import reload

reload(localize_skin_influences_setup)
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
        self.name = "pxo_localize_skin_influences_setup"

    def run(self, stepDict):
        skincluster_layering.load_and_execute_localize_data()
