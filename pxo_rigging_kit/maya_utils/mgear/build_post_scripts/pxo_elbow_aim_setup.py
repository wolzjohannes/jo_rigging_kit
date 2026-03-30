"""
Custom script to prepare the wingElbow component to our needs.
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
from itertools import chain
from importlib import reload

# Import third-party modules
import mgear.shifter.custom_step as cstp
import pymel.core as pmc

# Import local modules
from pxo_rigging_kit.maya_utils import dag_utils
from pxo_rigging_kit.maya_utils.mgear import mgear_build_utils
from pxo_rigging_kit.maya_utils.rigging import curves_utils
from pxo_rigging_kit.maya_utils.rigging import rig_utils
from pxo_rigging_kit.maya_utils import attributes_utils

from pxo_rigging_kit.maya_utils.maya_conversion_utils import pymaya_to_pymel as pconv



reload(rig_utils)
reload(curves_utils)
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

    ELBOW_COMPONENT = "wingElbow"
    WING_AIM_COMPONENT = "wingAim"
    BODY_ROOT_COMP = "root_"
    ELBOW_AIM_START_END_COMP = "elbowAimCurve"
    ARM_COMP = "arm"
    SETUP_GRP_NAME = "setup"

    def __init__(self):
        self.name = "pxo_elbow_aim_setup"
        self.acting_step_dict = None

    def run(self, stepDict):
        self.acting_step_dict = stepDict["mgearRun"]
        elbow_aim_component_keys = mgear_build_utils.get_nonhost_components(
            self.acting_step_dict, self.ELBOW_COMPONENT
        )
        elbow_aim_curve_component_keys = (
            mgear_build_utils.get_nonhost_components(
                self.acting_step_dict, self.ELBOW_AIM_START_END_COMP
            )
        )
        wing_aim_component_keys = mgear_build_utils.get_nonhost_components(
            self.acting_step_dict, self.WING_AIM_COMPONENT
        )
        body_root_component_keys = mgear_build_utils.get_nonhost_components(
            self.acting_step_dict, self.BODY_ROOT_COMP
        )
        arm_host_component_keys = mgear_build_utils.get_host_component(
            self.acting_step_dict, self.ARM_COMP
        )
        body_root_control = [
            mgear_build_utils.get_component_ctrls(
                self.acting_step_dict, comp_key
            )[0]
            for comp_key in body_root_component_keys
        ][0]
        wing_aim_controls = [
            (
                mgear_build_utils.get_component_side(
                    self.acting_step_dict, comp_key
                ),
                mgear_build_utils.get_component_ctrls(
                    self.acting_step_dict, comp_key
                )[0],
            )
            for comp_key in wing_aim_component_keys
        ]
        wing_aim_components = [
            (
                mgear_build_utils.get_component_side(
                    self.acting_step_dict, comp_key
                ),
                mgear_build_utils.get_component_root(
                    self.acting_step_dict, comp_key
                ),
            )
            for comp_key in wing_aim_component_keys
        ]
        elbow_aim_curve_controls = [
            (
                mgear_build_utils.get_component_side(
                    self.acting_step_dict, comp_key
                ),
                mgear_build_utils.get_component_ctrls(
                    self.acting_step_dict, comp_key
                ),
            )
            for comp_key in elbow_aim_curve_component_keys
        ]
        arm_host_controls = [
            (
                mgear_build_utils.get_component_side(
                    self.acting_step_dict, comp_key
                ),
                mgear_build_utils.get_component_ctrls(
                    self.acting_step_dict, comp_key
                )[0],
            )
            for comp_key in arm_host_component_keys
        ]
        for elbow_aim_comp_key in elbow_aim_component_keys:
            controls = mgear_build_utils.get_component_ctrls(
                self.acting_step_dict, elbow_aim_comp_key
            )
            side = mgear_build_utils.get_component_side(
                self.acting_step_dict, elbow_aim_comp_key
            )
            root = mgear_build_utils.get_component_root(
                self.acting_step_dict, elbow_aim_comp_key
            )
            wing_aim_control = [
                obj_tpl[1]
                for obj_tpl in wing_aim_controls
                if side == obj_tpl[0]
            ][0]
            wing_aim_component_root = [
                obj_tpl[1]
                for obj_tpl in wing_aim_components
                if side == obj_tpl[0]
            ][0]
            arm_host = [
                obj_tpl[1]
                for obj_tpl in arm_host_controls
                if side == obj_tpl[0]
            ][0]
            elbow_aim_curve_ends = list(
                chain.from_iterable(
                    [
                        obj_tpl[1]
                        for obj_tpl in elbow_aim_curve_controls
                        if side == obj_tpl[0]
                    ]
                )
            )
            self.add_elbow_aim_system(
                controls,
                arm_host,
                side,
                root,
                wing_aim_control,
                wing_aim_component_root,
                body_root_control,
                elbow_aim_curve_ends,
            )

    def add_elbow_aim_system(
        self,
        elbow_controls,
        arm_host,
        side,
        component_root,
        wing_aim_control,
        wing_aim_component_root,
        body_root_ctrl,
        elbow_aim_curve_ends,
    ):
        """
        Adds a elbow aim system to the rigs to support the wings better.

        Args:
            elbow_controls(list): The elbow controls.
            arm_host(pmc.PyNode()): The arm host control.
            side(str): Component side.
            component_root(pmc.PyNode()): Component root node.
            wing_aim_control(pmc.PyNode()): The wing aim control.
            wing_aim_component_root(pmc.PyNode()): The wing aim comp root.
            elbow_aim_curve_ends: .
            body_root_ctrl: .

        """

        (
            elbow_controls,
            arm_host,
            side,
            component_root,
            wing_aim_control,
            wing_aim_component_root,
            body_root_ctrl,
            elbow_aim_curve_ends,
        ) = pconv(
            elbow_controls,
            arm_host,
            side,
            component_root,
            wing_aim_control,
            wing_aim_component_root,
            body_root_ctrl,
            elbow_aim_curve_ends,
        )

        up_vec_trs = pmc.createNode(
            "transform", n="{}_elbow_aim_upvec_trs".format(side)
        )
        new_pos = component_root.getMatrix(worldSpace=True).translate
        new_pos = [new_pos[0], new_pos[1] + 10.0, new_pos[2]]
        up_vec_trs.translate.set(new_pos)
        up_vec_trs.setParent(component_root)
        name = "wingElbow_{}_0_aim".format(side)
        system_root_grp = pmc.createNode("transform", n="{}_grp".format(name))
        elbow_end_ctrl = elbow_controls[-1]
        elbow_start_ctrl = elbow_controls[0]
        on_crv_param = None
        curve_dict = curves_utils.create_nurbs_curve(
            elbow_aim_curve_ends, name="{}_crv".format(name), visibility=0
        )
        for loc, curve_end in zip(
            curve_dict.get("locators"), elbow_aim_curve_ends
        ):
            curve_end.addChild(loc)
            loc.visibility.set(0)
        aim_loc = rig_utils.locator_on_curve_to_closest_point_of_target(
            elbow_end_ctrl,
            curve_dict.get("curve"),
            param_on_crv=on_crv_param,
        )
        aim_loc.getShape().visibility.set(0)
        aim_loc.addChild(wing_aim_component_root)
        pmc.parentConstraint(
            body_root_ctrl, aim_loc, mo=True, st=["x", "y", "z"]
        )
        wing_aim_component_root.translate.set(0, 0, 0)
        elbow_start_ctrl_npo = elbow_start_ctrl.getParent()
        for axe in "XYZ":
            elbow_start_ctrl_npo.attr("rotate{}".format(axe)).unlock()
        aim_value = (1, 0, 0)
        up_vector = (0, -1, 0)
        if side == "R":
            aim_value = (-1, 0, 0)
            up_vector = (0, 1, 0)
        aim_con = pmc.aimConstraint(
            wing_aim_control,
            elbow_start_ctrl_npo,
            aim=aim_value,
            upVector=up_vector,
            worldUpType="object",
            worldUpObject=up_vec_trs,
            mo=True,
        )
        aim_con_weight = aim_con.getWeightAliasList()
        attributes_utils.add_pxo_separator_attr(arm_host, "wingElbow_aim")
        arm_host.addAttr(
            "wingElbow_middle_aim", type="float", keyable=True, min=0.0, max=1.0
        )
        arm_host.wingElbow_middle_aim.connect(aim_con_weight[0])
        arm_host.wingElbow_middle_aim.connect(system_root_grp.visibility)
        wing_aim_control_twist_trs = rig_utils.create_transfrom_on_position(
            wing_aim_control, name="{}_twist_trs".format(aim_loc.name())
        )
        (
            elbow_start_ctrl_buffer_trs,
            wing_aim_control_twist_trs_buffer_grp,
        ) = dag_utils.create_buffer_groups(
            [elbow_start_ctrl, wing_aim_control_twist_trs]
        )
        elbow_start_ctrl_npo.addChild(wing_aim_control_twist_trs_buffer_grp)
        wing_aim_control_twist_trs_buffer_grp.translate.set(0, 0, 0)
        wing_aim_control.rotateZ.connect(wing_aim_control_twist_trs.rotateZ)
        wing_aim_control_twist_trs.addChild(elbow_start_ctrl_buffer_trs)
        pmc.parent([curve_dict.get("curve"), aim_loc], system_root_grp)
        system_root_grp.setParent(pmc.PyNode(self.SETUP_GRP_NAME))
        _LOGGER.info("{}_wingAim setup created.".format(side))
