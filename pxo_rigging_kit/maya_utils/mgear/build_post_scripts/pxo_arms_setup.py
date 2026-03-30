"""
Custom script to prepare the arm_2jnt_freeTangents_01 component to our needs.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import built-in modules
from importlib import reload

# Import third-party modules
from future import standard_library

# Import built-in modules
import logging

# Import third-party modules
import mgear.shifter.custom_step as cstp
import pymel.core as pmc

# Import local modules
from pxo_rigging_kit.maya_utils import dag_utils
from pxo_rigging_kit.maya_utils.mgear import guide_utils
from pxo_rigging_kit.maya_utils.mgear import mgear_build_utils
from pxo_rigging_kit.maya_utils.rigging import curves_utils
from pxo_rigging_kit.maya_utils.rigging import rig_utils
from pxo_rigging_kit.maya_utils import maya_conversion_utils

standard_library.install_aliases()
reload(curves_utils)

#######################################################
# GLOBALS
#######################################################

logging.basicConfig(level=logging)
_LOGGER = logging.getLogger(__name__ + ".py")

#######################################################
# CLASSES
#######################################################


class CustomShifterStep(cstp.customShifterMainStep):

    COMPONENT = "arm"
    EXCLUDE_COMPS = "armIkRev"
    TWIST_BUFFER_CTRL_SUFFIX = "controlBuffer"
    Z_TWIST_INDEX_LIST = [0, 1, 2, 4, 5, 6]

    def __init__(self):
        self.name = "pxo_arms_setup"
        self.acting_step_dict = None

    def run(self, stepDict):
        self.acting_step_dict = stepDict["mgearRun"]
        ctrl_naming_rule = guide_utils.get_ctrl_naming_rule()
        controller_set = mgear_build_utils.get_controlers_set(
            stepDict
        )
        arm_comp_keys = mgear_build_utils.get_nonhost_components(
            self.acting_step_dict, self.COMPONENT, exclude_component_name=self.EXCLUDE_COMPS
        )
        for comp_key in arm_comp_keys:
            component_root = mgear_build_utils.get_component_root(
                self.acting_step_dict, comp_key
            )
            controls = mgear_build_utils.get_component_ctrls(
                self.acting_step_dict, comp_key
            )
            side = mgear_build_utils.get_component_side(
                self.acting_step_dict, comp_key
            )
            index = mgear_build_utils.get_component_index(
                self.acting_step_dict, comp_key
            )
            self.neutralize_arm_ik(controls, side)
            self.add_arm_twist_control(
                component_root, side, index, controller_set, ctrl_naming_rule, stepDict
            )

    def neutralize_arm_ik(self, comp_controls, comp_side):
        """
        Method will add a npo node over the arm ik to get it neutral.
        And set it to worldspace orientation.

        Args:
            comp_controls(list): All arm component controls
            comp_side(side): The component side

        """
        arm_ik_control = [
            node for node in comp_controls if "_ik_" in node.name()
        ][0]
        arm_ik_cns_control = [
            node for node in comp_controls if "_ikcns_" in node.name()
        ]

        npo_trs = dag_utils.create_buffer_groups(arm_ik_cns_control)[0]
        parent_nd = npo_trs.getParent()
        control_children = arm_ik_control.getChildren(typ="transform")
        for child in control_children:
            pmc.parent(child, w=True)
        pmc.parent(npo_trs, None)
        npo_trs.rotate.set(0, 0, 0)
        pmc.parent(npo_trs, parent_nd)
        for child_ in control_children:
            arm_ik_control.addChild(child_)
        _LOGGER.info("Add {} arm ik NPO succeeded.".format(comp_side))

    def add_arm_twist_control(
        self, component_root, side, index, controllers_set, ctrl_naming_rule, stepDict
    ):
        """
        Method which adds arm twist controls.

        Args:
            component_root(pmc.PyNode): The component root node.
            side(str): The component side.
            index(int): The component index.
            controllers_set(pmc.PyNode): The controllers set.
            ctrl_naming_rule(str): The ctrl naming convention rule.
            stepDict(dict): The mgear build step dict.

        """
        controllers_set = maya_conversion_utils.pymaya_to_pymel(controllers_set)
        color_index = 18
        if side == "R":
            color_index = 20
        valid_locs = list()
        z_twist_controls_list = list()
        mgear_fake_class_list = []
        for div_index in self.Z_TWIST_INDEX_LIST:
            valid_locs.extend(
                [
                    node
                    for node in component_root.getChildren(
                        ad=True, type="transform"
                    )
                    if node.name(long=None)
                    == "arm_{}{}_div{}_loc".format(side, index, div_index)
                ]
            )
        for div_index, div_loc in enumerate(valid_locs):
            div_loc = maya_conversion_utils.pymaya_to_pymel(div_loc) #mgear pymaya to pymel - 2025
            matrix_con = div_loc.worldMatrix[0].connections(p=True)
            control_name = (
                ctrl_naming_rule.replace("{component}", "arm")
                .replace("{side}", side)
                .replace("{index}", str(index))
                .replace("{description}", f"twist{div_index}")
                .replace("{extension}", "ctrl")
            )
            comp_dic_name = "{}_{}{}".format(
                    "arm",
                    side,
                    index,
                )
            z_twist_instance = curves_utils.SquareControl()
            z_twist_instance.create_curve(
                name=control_name,
                scale=(10.0, 10.0, 10.0),
                match=div_loc,
                lock_scale=["sx", "sy", "sz"],
                lock_translate=["tx", "ty", "tz"],
                lock_visibility=True,
                color_index=color_index
            )
            z_twist_instance.buffer_grp.setParent(div_loc)
            if matrix_con:
                source = f"{z_twist_instance.control.name()}.worldMatrix[0]"
                dest = matrix_con[0].name() if hasattr(matrix_con[0], 'name') else matrix_con[0]
                pmc.connectAttr(source, dest, force=True)

            z_twist_controls_list.append(z_twist_instance.control)
            mgear_fake_class_list.append((z_twist_instance.control, comp_dic_name))
        # Search about buffer curves and apply the shape on the actual control curve
        for ctrl_ in z_twist_controls_list:
            buffer_ctrl_name = f"{str(ctrl_.name(long=None))}_{self.TWIST_BUFFER_CTRL_SUFFIX}"
            buffer_ctrl = pmc.ls(buffer_ctrl_name)
            if not buffer_ctrl:
                _LOGGER.info(f"{buffer_ctrl_name} not existing. Will skip.")
                continue
            dag_utils.swap_curve_shapes(buffer_ctrl[-1], ctrl_)
        # create arm_twist fix
        valid_twist_ctrls = list()
        for i in range(3):
            search_pattern = "_twist{}_".format(i)
            for ctrl in z_twist_controls_list:
                if search_pattern in ctrl.name(long=None):
                    valid_twist_ctrls.append(ctrl)
        valid_twist_ctrls[1].addAttr(
            "auto_twist_fix", type="float", max=1.0, min=0.0, keyable=True
        )
        div_loc = valid_twist_ctrls[1].getParent(generations=2)
        aim_trs_parent = valid_twist_ctrls[2].getParent(generations=2)
        aim_trs = rig_utils.create_transfrom_on_position(
            valid_twist_ctrls[1], "{}_aim_trs".format(valid_twist_ctrls[1])
        )
        aim_trs.setParent(valid_twist_ctrls[1])
        aim_trs.translateY.set(-20)
        aim_trs.setParent(aim_trs_parent)
        aim_con = pmc.aimConstraint(
            aim_trs,
            valid_twist_ctrls[1].getParent(),
            aim=(0, -1, 0),
            u=(0, 0, 1),
            wut="object",
            wuo=div_loc,
            skip=["y", "z"],
        )
        mult_angle_0 = pmc.createNode("math_MultiplyAngle")
        mult_angle_1 = pmc.createNode("math_MultiplyAngle")
        valid_twist_ctrls[1].auto_twist_fix.connect(mult_angle_0.input2)
        mult_angle_0.output.connect(mult_angle_1.input1)
        mult_angle_1.input2.set(0.125)
        controllers_set.addMembers(z_twist_controls_list)
        aim_con.constraintRotateX.connect(mult_angle_0.input1)
        mult_angle_0.output.connect(
            valid_twist_ctrls[1].getParent().rotateX, force=True
        )
        mult_angle_1.output.connect(valid_twist_ctrls[0].getParent().rotateX)

        # We pass the new builded controls into the stepDict as MgearFakeClass
        # So that our visibility post script can catch it up.
        for ctrl, comp_dic_name in mgear_fake_class_list:
            if stepDict["mgearRun"].components.get(comp_dic_name):
                all_controls = (
                    stepDict["mgearRun"]
                    .components[comp_dic_name]
                    .groups.get("controllers")
                    + [ctrl]
                )
                stepDict["mgearRun"].components[comp_dic_name].groups[
                    "controllers"
                ] = all_controls
            else:
                mgear_fake_comp_class = mgear_build_utils.MgearFakeComponentClass(
                )
                mgear_fake_comp_class.set_name("arm")
                mgear_fake_comp_class.set_side(side)
                mgear_fake_comp_class.set_index(
                    index
                )
                mgear_fake_comp_class.set_controls_list([ctrl])
                stepDict["mgearRun"].components[
                    comp_dic_name
                ] = mgear_fake_comp_class

        #2025 addition
        for ctrl in z_twist_controls_list:
            node = pmc.PyNode(ctrl) if isinstance(ctrl, str) else ctrl

            node.rotateX.unlock()
            node.rotateY.unlock()
            node.rotateZ.unlock()