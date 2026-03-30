# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import third-party modules
from future import standard_library

# Import built-in modules
import logging

# Import third-party modules
import mgear.shifter.custom_step as cstp

# Import local modules
from pxo_rigging_kit.maya_utils.mgear import mgear_build_utils
from pxo_rigging_kit.maya_utils.rigging import rig_utils

standard_library.install_aliases()

#######################################################
# GLOBALS
#######################################################

logging.basicConfig(level=logging)
_LOGGER = logging.getLogger(__name__ + ".py")

#######################################################
# CLASSES
#######################################################


class CustomShifterStep(cstp.customShifterMainStep):
    """Custom Step description"""

    HOSTS_COMPONENT = "Host"

    def __init__(self):
        self.name = "pxo_finish_hosts_setup"
        self.acting_step_dict = None

    def run(self, stepDict):
        """Run method.

            i.e:  self.mgear_run.global_ctl
                gets the global_ctl from shifter rig build base

            i.e:  self.component("control_C0").ctl
                gets the ctl from shifter component called control_C0

            i.e:  self.custom_step("otherCustomStepName").ctlMesh
                gets the ctlMesh from a previous custom step called
                "otherCustomStepName"

        Returns:
            None: None
        """
        self.acting_step_dict = stepDict["mgearRun"]
        host_components = {
            mgear_build_utils.get_host_from_component(
                self.acting_step_dict, comp_key
            )
            for comp_key in self.acting_step_dict.components.keys()
        }
        for host_ctrl in host_components:
            if host_ctrl:
                rig_utils.reformat_mgear_seperator_enums(host_ctrl)