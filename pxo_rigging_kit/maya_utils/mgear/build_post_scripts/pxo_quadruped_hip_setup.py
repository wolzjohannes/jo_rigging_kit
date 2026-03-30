"""
Custom script to prepare the quadruped hips to our needs.
"""
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
from pxo_rigging_kit.maya_utils import attributes_utils
from pxo_rigging_kit.maya_utils import dag_utils
from pxo_rigging_kit.maya_utils.mgear import mgear_build_utils
from pxo_rigging_kit.maya_utils.rigging import rig_utils

#######################################################
# GLOBALS
#######################################################

logging.basicConfig(level=logging)
_LOGGER = logging.getLogger(__name__ + ".py")
standard_library.install_aliases()

#######################################################
# CLASSES
#######################################################


class CustomShifterStep(cstp.customShifterMainStep):

    HIP_COMPONENT = "hip"
    HIP_IK_ORIENT_DIC = {
        "up_axes": "y",
        "aim_axes": "z",
        "aim_ref_pos": (-10, 0, 0),
        "up_ref_pos": (0, -10, 0),
    }

    def __init__(self):
        self.name = "pxo_hip_setup.py"
        self.acting_step_dict = None

    def run(self, stepDict):
        """Run Method.

        Args:
            stepDict(dict): Containing the objects from the previous
            custom step.

        Example:
            stepDict["mgearRun"].global_ctl gets back the global_ctl
            from shifter rig from post step

        """
        self.acting_step_dict = stepDict["mgearRun"]
        # First find the components
        hip_component_keys = mgear_build_utils.get_nonhost_components(
            self.acting_step_dict, self.HIP_COMPONENT
        )
        # Get the component.
        for hip_comp_key in hip_component_keys:
            hip_comp_side = mgear_build_utils.get_component_side(
                self.acting_step_dict, hip_comp_key
            )
            hip_component_controls = mgear_build_utils.get_component_ctrls(
                self.acting_step_dict, hip_comp_key
            )[0]
            if hip_comp_side == "C":
                self.change_hip_orientation(hip_component_controls)
                attributes_utils.lock_and_hide_attributes(
                    hip_component_controls,
                    attributes=["tx", "ty", "tz", "sx", "sy", "sz", "v"],
                )

    def change_hip_orientation(self, hip_controller):
        """
        Change the hip orientation.

        Args:
            hip_controller(pmc.PyNode()): The hip controller objects.

        """
        new_trs = rig_utils.exchange_connections_to_new_trs(
            hip_controller, ["controller", "objectSet", "dagPose"]
        )
        rig_utils.switch_mgear_control_orientation(
            hip_controller, **self.HIP_IK_ORIENT_DIC
        )
        npo = dag_utils.create_buffer_groups([hip_controller])[0]
        hip_controller.addChild(new_trs)
        _LOGGER.info("Hip orientation change successful")
