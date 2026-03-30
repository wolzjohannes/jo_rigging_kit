"""
Custom script to prepare the quadruped tail to our needs.
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
from importlib import reload

# Import third-party modules
import mgear.shifter.custom_step as cstp

# Import local modules
from pxo_rigging_kit.maya_utils.post_and_pre_build import chain_interpolation_setup
from pxo_rigging_kit.maya_utils.mgear import mgear_build_utils

reload(chain_interpolation_setup)

#######################################################
# GLOBALS
#######################################################

logging.basicConfig(level=logging)
_LOGGER = logging.getLogger(__name__ + ".py")
standard_library.install_aliases()


#######################################################
# CLASSES
#######################################################


class CustomShifterStep(chain_interpolation_setup.InterpolationSetup, cstp.customShifterMainStep):

    COMPONENT = "tail_"
    JNT_NUM = 30

    def __init__(self):
        super(CustomShifterStep, self).__init__()
        self.name = "pxo_tail_chain_interpolation_setup"
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
        tail_component_keys = mgear_build_utils.get_nonhost_components(self.acting_step_dict, self.COMPONENT)
        for tail_comp_key in tail_component_keys:
            self.deformer_set = mgear_build_utils.get_deformers_set(stepDict)
            self.tail_joint_list = mgear_build_utils.get_component_jnts(self.acting_step_dict, tail_comp_key)
            self.component_name = mgear_build_utils.get_component_name(self.acting_step_dict, tail_comp_key)
            self.create()
