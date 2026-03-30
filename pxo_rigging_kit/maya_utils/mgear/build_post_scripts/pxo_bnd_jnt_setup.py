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
import pymel.core as pmc
# Import local modules
from pxo_rigging_kit.maya_utils import assembly_utils
from pxo_rigging_kit.maya_utils.rigging.rig_utils import get_object_size
from pxo_rigging_kit.maya_utils.maya_conversion_utils import pymaya_to_pymel as pconv


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
    """Custom Step description
    """
    def __init__(self):
        self.name = "pxo_bnd_jnt_setup"
        self.offset_mult_value = 0.025
        self.bnd_color_index = 17
        self.jnt_org = "jnt_org"

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
        asset_assembly_nd = (
            assembly_utils.get_asset_assembly_nodes_from_scene()[0]
        )
        assembly_data_list = asset_assembly_nd.get_assembly_data()
        scale_factors = [get_object_size(data_dict["asset_root"]) for data_dict in assembly_data_list]
        scale_factor = (sum(scale_factors)/len(scale_factors))*self.offset_mult_value

        rig = stepDict["mgearRun"].model
        deformers_set = rig.rigGroups.inputs()[3]
        self.finish_bnd_joints(deformers_set, scale_factor)

    def finish_bnd_joints(self, deformers_set, scale_factor):
        """
        Method to finish all the bnd joints in the rig.

        Args:
            deformers_set(pmc.PyNode()): The bind joint selection set.
            scale_factor(int): The scale factor from the root guide group.

        """
        for jnt in deformers_set.members():
            jnt = pmc.PyNode(jnt)
            jnt.radius.set(scale_factor)
            try:
                jnt.overrideEnabled.set(1)
            except:
                pass
            try:
                jnt.overrideColor.set(self.bnd_color_index)
            except:
                pass
