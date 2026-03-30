"""
Custom script to prepare the clavicle component to our needs.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import built-in modules
from builtins import dict
from pprint import pprint

from pymel import core as pmc
# Import third-party modules
from future import standard_library

# Import built-in modules
import logging

# Import third-party modules
import mgear.shifter.custom_step as cstp

from pxo_rigging_kit.maya_utils.EWAW_rs import node
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

    COMPONENT = "clavicle"
    CHEST_COMPONENT = "chest"

    def __init__(self):
        self.name = "pxo_clavicle_setup"
        self.acting_step_dict = None

    def run(self, stepDict):
        self.acting_step_dict = stepDict["mgearRun"]

        clav_comp_keys = mgear_build_utils.get_nonhost_components(
            self.acting_step_dict, self.COMPONENT
        )

        chest_comp_keys = mgear_build_utils.get_nonhost_components(
            self.acting_step_dict, self.CHEST_COMPONENT
        )

        controls = [
            mgear_build_utils.get_component_ctrls(
                self.acting_step_dict, comp_key
            )
            for comp_key in clav_comp_keys
        ]

        clav_joints = [
            mgear_build_utils.get_component_jnts(
                self.acting_step_dict, comp_key
            )
            for comp_key in clav_comp_keys
        ]

        chest_joints = [
            mgear_build_utils.get_component_jnts(
                self.acting_step_dict, comp_key
            )
            for comp_key in chest_comp_keys
        ]

        for ctrl_list in controls:
            for ctrl in ctrl_list:
                clavicle_end_space_tweak(ctrl)

        _LOGGER.error(f"clav_joints: {clav_joints}")
        _LOGGER.error(f"chest_joints: {chest_joints}")

        for clav_list in clav_joints:
            for clav_joint in clav_list:
                if "End" in clav_joint.name():
                    static_rotation_clavicle_joint(clav_joint, pmc.PyNode("C_bnd_chest_0_0_jnt"))


def clavicle_end_space_tweak(clavicle_control):
    """
    Will make the space switch only working for orientation.

    Args:
        clavicle_control(pmc.PyNode()): The clavicle control.

    """
    cns = clavicle_control.getParent()

    for axe in "XYZ":
        attribute = cns.attr(f"translate{axe}")
        attribute.unlock()

        if attribute.isConnected():
            attribute.disconnect()


def static_rotation_clavicle_joint(clavicle_joint, chest_joint):
    """
    Will make the space switch only working for orientation.

    Args:
        clavcile_control(pmc.PyNode()): The clavicle control.

    """
    clavicle_joint_decomposed_name = clavicle_joint.split("_")
    clavicle_joint_decomposed_name[2] = "clavicleVolume"

    new_name = "_".join(clavicle_joint_decomposed_name)

    jnt = node.createNode("joint",
                          n=new_name,
                          as_type="pymel",
                          tag="supportJoint")
    jnt.setParent(chest_joint)

    pmc.matchTransform(jnt, clavicle_joint)

    rig_utils.pxo_constraining(
        clavicle_joint,
        jnt,
        maintainOffset=False,
        name=None,
        skipRotate=True,
        skipTranslate=False,
        skipScale=True,
        constraint_tag=None,
        use_parent_offset_mtx=False,
    )

    rig_utils.pxo_constraining(
        chest_joint,
        jnt,
        maintainOffset=True,
        name=None,
        skipRotate=False,
        skipTranslate=True,
        skipScale=False,
        constraint_tag=None,
        use_parent_offset_mtx=False,
    )