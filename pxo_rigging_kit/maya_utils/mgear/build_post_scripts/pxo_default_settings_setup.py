"""
Post script to apply all save dafualt values
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
from pxo_rigging_kit.maya_utils.rigging import default_settings

standard_library.install_aliases()

#######################################################
# GLOBALS
#######################################################

logging.basicConfig(level=logging)
_LOGGER = logging.getLogger(__name__ + ".py")

#######################################################
# CLASSES
#######################################################


class CustomShifterStep(
    cstp.customShifterMainStep
):
    def __init__(self):
        self.name = "pxo_default_settings_setup"

    def run(self, stepDict):
        """Run Method.

        Args:

            stepDict(dict): Containing the objects from the previous
            custom step.

        Example:
            stepDict["mgearRun"].global_ctl gets back the global_ctl
            from shifter rig from post step

        """
        try:
            default_settings.import_and_apply_visibility_default_values()
        except Exception as e:
            print(e, "Will skip.")
        try:
            default_settings.import_and_apply_controls_default_values()
        except Exception as e:
            print(e, "Will skip.")