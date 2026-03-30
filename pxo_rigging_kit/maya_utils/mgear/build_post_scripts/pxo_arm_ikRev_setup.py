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

# Import third-party modules
import pymel.core as pmc
from future import standard_library

# Import built-in modules
import logging

# Import third-party modules
import mgear.shifter.custom_step as cstp

# Import local modules
from pxo_rigging_kit.maya_utils.mgear import mgear_build_utils
from pxo_rigging_kit.maya_utils.rigging import rig_utils
from pxo_rigging_kit.maya_utils import maya_conversion_utils

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

    COMPONENT = "armIkRev"
    THUMB_PALM_COMPONENT = "thumbPalm"
    HAND_PALM_COMPONENT = "handPalm"
    ARM_COMPONENT = "arm"

    def __init__(self):
        self.name = "pxo_arm_ikRev_setup"
        self.acting_step_dict = None

    def run(self, stepDict):
        self.acting_step_dict = stepDict["mgearRun"]
        # Getting the arm ikRev component
        arm_ikRev_comp_keys = mgear_build_utils.get_nonhost_components(
            self.acting_step_dict,
            self.COMPONENT,
        )
        # Getting all arm objects we need
        arm_comp_keys = mgear_build_utils.get_nonhost_components(
            self.acting_step_dict, self.ARM_COMPONENT, exclude_component_name=self.COMPONENT
        )
        arm_controls = []
        arm_roots = []
        arm_host = []
        for arm_comp_key in arm_comp_keys:
            arm_controls.extend(
                mgear_build_utils.get_component_ctrls(
                    self.acting_step_dict, arm_comp_key
                )
            )
            arm_roots.append(
                mgear_build_utils.get_component_root(
                    self.acting_step_dict, arm_comp_key
                )
            )
            arm_host.append(
                mgear_build_utils.get_host_from_component(
                    self.acting_step_dict, arm_comp_key
                )
            )
        # Getting the hand palm objects
        hand_palm_root = []
        hand_palm_keys = mgear_build_utils.get_nonhost_components(
            self.acting_step_dict, self.HAND_PALM_COMPONENT
        )
        for hand_palm_key in hand_palm_keys:
            hand_palm_root.append(
                mgear_build_utils.get_component_root(
                    self.acting_step_dict, hand_palm_key
                )
            )
        # Getting the thumb palm objects
        thumb_palm_root = []
        thumb_palm_keys = mgear_build_utils.get_nonhost_components(
            self.acting_step_dict, self.THUMB_PALM_COMPONENT
        )
        for thumb_palm_key in thumb_palm_keys:
            thumb_palm_root.append(
                mgear_build_utils.get_component_root(
                    self.acting_step_dict, thumb_palm_key
                )
            )
        # Create the setup
        for comp_key in arm_ikRev_comp_keys:
            control = mgear_build_utils.get_component_ctrls(
                self.acting_step_dict, comp_key
            )[0]
            root = mgear_build_utils.get_component_root(
                self.acting_step_dict, comp_key
            )
            side = mgear_build_utils.get_component_side(
                self.acting_step_dict, comp_key
            )
            name = mgear_build_utils.get_component_name(
                self.acting_step_dict, comp_key
            )


            control = maya_conversion_utils.pymaya_to_pymel(control)
            root = maya_conversion_utils.pymaya_to_pymel(root)
            arm_host = maya_conversion_utils.pymaya_to_pymel(arm_host)

            self.create_ik_arm_reverse_setup(
                control,
                root,
                side,
                name,
                hand_palm_root,
                thumb_palm_root,
                arm_controls,
                arm_roots,
                arm_host,
            )

    def create_ik_arm_reverse_setup(
        self,
        ik_rev_control,
        ik_rev_root,
        ik_rev_side,
        ik_rev_name,
        hand_palm_root_list,
        thumb_palm_root_list,
        arm_control_list,
        arm_root_list,
        arm_host_list,
    ):
        """
        Create a reverse ik control. So you have a control which behaves like a
        foot roll on the arms.

        Args:
            ik_rev_control(pmc.PyNode()): The Ik reverse control.
            ik_rev_root(pmc.PyNode()): The Ik reverse control root.
            ik_rev_side(str): The component side.
            ik_rev_name(str): The component name.
            hand_palm_root_list(list): The hand palm component roots.
            thumb_palm_root_list(list): The thumb palm component roots
            arm_control_list(list): The arm controls.
            arm_root_list(list): The arm root groups.
            arm_host_list(list): The arm host controls.

        """
        arm_root = [
            node
            for node in arm_root_list
            if "_{}".format(ik_rev_side) in node.name()
        ][0]
        arm_ik_ctrl = [
            node_
            for node_ in arm_control_list
            if "_{}".format(ik_rev_side) in node_.name()
            and "_ik_" in node_.name()
        ][0]
        print("="*10)
        print(arm_host_list)
        arm_host = [
            host
            for host in arm_host_list
            if "_{}".format(ik_rev_side) in host.name()
        ][0]
        arm_ik_ctrl = maya_conversion_utils.pymaya_to_pymel(arm_ik_ctrl)
        ikCtl_ref_nd = [
            nd
            for nd in arm_ik_ctrl.getChildren(typ="transform")
            if "_ikCtl_ref" in nd.name()
        ][0]
        arm_root = maya_conversion_utils.pymaya_to_pymel(arm_root)
        eff_loc_nd = [
            loc
            for loc in arm_root.getChildren(typ="transform")
            if "_eff_loc" in loc.name()
        ][0]
        palm_root_list = [
            root_nd
            for root_nd in list(hand_palm_root_list + thumb_palm_root_list)
            if "_{}0".format(ik_rev_side) in root_nd.name()
        ]
        eff_loc_nd_trs = rig_utils.create_transfrom_on_position(eff_loc_nd)
        ikCtl_ref_nd_trs = rig_utils.create_transfrom_on_position(
            eff_loc_nd, "arm_{}0_ik_ref_match_trs".format(ik_rev_side)
        )
        arm_root.addChild(eff_loc_nd_trs)
        arm_ik_ctrl.addChild(ikCtl_ref_nd_trs)
        arm_ik_ctrl.addChild(ik_rev_root)
        p_con = pmc.parentConstraint(
            ikCtl_ref_nd_trs, eff_loc_nd, eff_loc_nd_trs, mo=True
        )
        for axe in "XYZ":
            eff_loc_nd.attr("scale{}".format(axe)).connect(
                eff_loc_nd_trs.attr("scale{}".format(axe))
            )
        p_con_weight_alias_list = p_con.getWeightAliasList()
        reverse_nd = pmc.createNode("reverse")
        arm_host.arm_blend.connect(p_con_weight_alias_list[0])
        arm_host.arm_blend.connect(reverse_nd.inputX)
        reverse_nd.outputX.connect(p_con_weight_alias_list[1])
        ik_rev_control.addChild(ikCtl_ref_nd)
        [eff_loc_nd_trs.addChild(palm_nd) for palm_nd in palm_root_list]
        arm_host.arm_blend.connect(ik_rev_root.visibility)
        _LOGGER.info(
            "Ik reverse setup created for {}_{}".format(
                ik_rev_name, ik_rev_side
            )
        )
