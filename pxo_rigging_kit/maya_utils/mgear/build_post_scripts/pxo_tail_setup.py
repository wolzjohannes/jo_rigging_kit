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

# Import third-party modules
import mgear.shifter.custom_step as cstp
import pymel.core as pmc

# Import local modules
from pxo_rigging_kit.maya_utils import attributes_utils
from pxo_rigging_kit.maya_utils import dag_utils
from pxo_rigging_kit.maya_utils.mgear import mgear_build_utils
from pxo_rigging_kit.maya_utils.mgear.build_post_scripts import pxo_neck_setup
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


class CustomShifterStep(pxo_neck_setup.CustomShifterStep, cstp.customShifterMainStep):

    TAIL_COMPONENT = "tail_"
    REFORMAT_SPACES_ENUM_DIC = {
        "root": "root",
        "neck": "neck",
        "spine": "chest",
        "local": "global",
    }
    TAIL_IK_ORIENT_DIC = {
        "up_axes": "y",
        "aim_axes": "z",
        "aim_ref_pos": (-50, 0, 0),
        "up_ref_pos": (0, -100, 0),
    }

    TAIL_SPACES_DIC = [
        ("global", "local_C_0_*_ctrl"),
        ("root", "root_C_0_*_ctrl"),
    ]

    TAIL_ROOT_IK_REF_ENUM_ATTR_DIC = {
        "longName": "tail_rootref",
        "niceName": "tail_root_ori_ref",
    }

    TAIL_IK_REF_ENUM_ATTR_DIC = {
        "longName": "tail_iksref",
        "niceName": "tail_iks_ref",
    }
    TAIL_LOCAL_SPACE_EN_NAME = "Auto"

    pxo_neck_setup.CustomShifterStep.SPLINE_IK_SECTION_FOLLOW_ATTR["longName"] = "tail_sub_cons_follow"
    pxo_neck_setup.CustomShifterStep.SPLINE_IK_SECTION_FOLLOW_ATTR["niceName"] = "tail_sub_cons_follow"

    def __init__(self):
        self.name = "pxo_tail_setup"
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
        tail_component_keys = mgear_build_utils.get_nonhost_components(
            self.acting_step_dict, self.TAIL_COMPONENT
        )
        for tail_comp_key in tail_component_keys:
            tail_host_control = mgear_build_utils.get_host_from_component(
                self.acting_step_dict, tail_comp_key
            )
            tail_controls = mgear_build_utils.get_component_ctrls(
                self.acting_step_dict, tail_comp_key
            )
            tail_component_root = mgear_build_utils.get_component_root(
                self.acting_step_dict, tail_comp_key
            )
            self.change_tail_ik_orientation(tail_controls)
            self.add_tail_spaces(
                tail_component_root, tail_controls, tail_host_control
            )
            # Comment the neck tail follow system
            # self.tweak_all_spline_sections(tail_controls, tail_host_control)

    def change_tail_ik_orientation(self, tail_controls):
        """
        Change the tail ik orientation.

        Args:
            tail_controls(list): The tail controller objects.

        """
        tail_ik_controllers = [
            node for node in tail_controls if "_ik" in node.name()
        ]
        for tail_ik_nd in tail_ik_controllers:
            new_trs = rig_utils.exchange_connections_to_new_trs(
                tail_ik_nd, ["controller", "objectSet", "dagPose"]
            )
            rig_utils.switch_mgear_control_orientation(
                tail_ik_nd, **self.TAIL_IK_ORIENT_DIC
            )
            npo = dag_utils.create_buffer_groups([tail_ik_nd])[0]
            tail_ik_nd.addChild(new_trs)
        _LOGGER.info("Tail ik orientation change successful")

    def add_tail_spaces(
        self, tail_component_root, tail_controls, tail_host_control
    ):
        """
        Add new tail spaces to the tail ik controls.

        Args:
            tail_component_root(pmc.PyNode()): The tail component root node.
            Inherits the whole tail component setup.
            tail_controls(list): List of all tail ik controls.
            tail_host_control(pmc.PyNode()): The host controls of the component.

        """
        target_tpl_list = [
            (data_tpl[0], pmc.ls(data_tpl[1])[0])
            for data_tpl in self.TAIL_SPACES_DIC
            if pmc.ls(data_tpl[1])
        ]
        tail_ik_controllers = [
            node for node in tail_controls if "_ik" in node.name()
        ][1:]
        attributes_utils.add_enum_attribute(
            tail_host_control,
            self.TAIL_ROOT_IK_REF_ENUM_ATTR_DIC.get("longName"),
            [self.TAIL_LOCAL_SPACE_EN_NAME] + [obj[0] for obj in target_tpl_list],
            nice_name=self.TAIL_ROOT_IK_REF_ENUM_ATTR_DIC.get("niceName"),
            keyable=True
        )
        attributes_utils.add_enum_attribute(
            tail_host_control,
            self.TAIL_IK_REF_ENUM_ATTR_DIC.get("longName"),
            [self.TAIL_LOCAL_SPACE_EN_NAME] + [obj[0] for obj in target_tpl_list],
            nice_name=self.TAIL_IK_REF_ENUM_ATTR_DIC.get("niceName"),
            keyable=True
        )
        p_con_0 = pmc.parentConstraint(
            [obj[1] for obj in target_tpl_list], tail_component_root, mo=True
        )
        for axe in "XYZ":
            p_con_0.attr("constraintTranslate{}".format(axe)).disconnect()
        cond_nd_0 = pmc.createNode("condition")
        cond_nd_1 = pmc.createNode("condition")
        cond_nd_0.secondTerm.set(1)
        cond_nd_1.secondTerm.set(2)
        for col in "RGB":
            cond_nd_0.attr("colorIfTrue{}".format(col)).set(1)
            cond_nd_1.attr("colorIfTrue{}".format(col)).set(1)
            cond_nd_0.attr("colorIfFalse{}".format(col)).set(0)
            cond_nd_1.attr("colorIfFalse{}".format(col)).set(0)
        tail_host_control.attr(
            self.TAIL_ROOT_IK_REF_ENUM_ATTR_DIC.get("longName")
        ).connect(cond_nd_0.firstTerm)
        tail_host_control.attr(
            self.TAIL_ROOT_IK_REF_ENUM_ATTR_DIC.get("longName")
        ).connect(cond_nd_1.firstTerm)
        pcon_target_list = p_con_0.getWeightAliasList()
        cond_nd_0.outColorR.connect(pcon_target_list[0])
        cond_nd_1.outColorR.connect(pcon_target_list[1])
        for ik_control in tail_ik_controllers:
            npo = dag_utils.create_buffer_groups([ik_control], "space_npo")[0]
            p_con_1 = pmc.parentConstraint(
                [obj[1] for obj in target_tpl_list], npo, mo=True
            )
            cond_nd_2 = pmc.createNode("condition")
            cond_nd_3 = pmc.createNode("condition")
            cond_nd_2.secondTerm.set(1)
            cond_nd_3.secondTerm.set(2)
            for col_ in "RGB":
                cond_nd_2.attr("colorIfTrue{}".format(col_)).set(1)
                cond_nd_3.attr("colorIfTrue{}".format(col_)).set(1)
                cond_nd_2.attr("colorIfFalse{}".format(col_)).set(0)
                cond_nd_3.attr("colorIfFalse{}".format(col_)).set(0)
            tail_host_control.attr(
                self.TAIL_IK_REF_ENUM_ATTR_DIC.get("longName")
            ).connect(cond_nd_2.firstTerm)
            tail_host_control.attr(
                self.TAIL_IK_REF_ENUM_ATTR_DIC.get("longName")
            ).connect(cond_nd_3.firstTerm)
            pcon_target_list = p_con_1.getWeightAliasList()
            cond_nd_2.outColorR.connect(pcon_target_list[0])
            cond_nd_3.outColorR.connect(pcon_target_list[1])
