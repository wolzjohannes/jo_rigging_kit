"""
Custom script to prepare the wing feather setup. You will need the start and end locators
as guides in the scene. And you will need a proxy and proxy iland mesh in the guides as well.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import third-party modules
from future import standard_library

standard_library.install_aliases()

# Import built-in modules
import logging

# Import third-party modules
import mgear.shifter.custom_step as cstp
import pymel.core as pmc
import maya.internal.nodes.proximitywrap.node_interface as ifc
# Import local modules
from pxo_rigging_kit.maya_utils import dag_utils

from pxo_rigging_kit.maya_utils import exceptions
from pxo_rigging_kit.maya_utils.mgear import mgear_build_utils
from pxo_rigging_kit.maya_utils.post_and_pre_build import feather_setup
from pxo_rigging_kit.maya_utils.post_and_pre_build.feather_setup import \
    FEATHERS_PROXY_ILAND_MESH
from pxo_rigging_kit.maya_utils.post_and_pre_build.feather_setup import \
    FEATHERS_PROXY_LOCAL_MESH
from pxo_rigging_kit.maya_utils.post_and_pre_build.feather_setup import \
    FEATHERS_PROXY_MESH
from pxo_rigging_kit.maya_utils.post_and_pre_build.feather_setup import \
    FEATHERS_START_SET_NAME

##########################################################
# GLOBALS
##########################################################

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)

data = feather_setup.gather_feather_data()

TAIL_PROXY_MESH = data["TAIL_PROXY"]
FEATHER_ATTACH_GEO_DIC = data["FEATHER_ATTACH_GEO_DIC"]
SCALE_CTRL = "global_0_ctrl"
##########################################################
# FUNCTIONS
##########################################################

class CustomShifterStep(cstp.customShifterMainStep):
    COMPONENT = "wingFeather"
    AIM_COMPONENT = "wingFeatherEnd"
    HOST_COMPONENT = "Host"
    ARM_COMPONENT = "arm"
    TAIL_COMPONENT = "tail"

    def __init__(self):
        self.name = "pxo_bird_feather_setup"
        self.acting_step_dict = None
        self.wing_sections_names = ["primary", "secondary", "tail"]
        self.setup_nd_name = "setup"
        self.bnd_root_name = "C_bnd_root_0_0_jnt"

    def run(self, stepDict):
        self.acting_step_dict = stepDict["mgearRun"]

        # First we collect all need guide objects in the scene.
        # If one of them not existing we will fail.
        # So we make sure that the build gets what it needs to.
        wing_feather_component_keys = mgear_build_utils.get_nonhost_components(
            self.acting_step_dict,
            self.COMPONENT,
            self.HOST_COMPONENT,
            self.AIM_COMPONENT,
        )
        wing_feather_end_component_keys = (
            mgear_build_utils.get_nonhost_components(
                self.acting_step_dict, self.AIM_COMPONENT, self.HOST_COMPONENT
            )
        )
        host_component_keys = mgear_build_utils.get_host_component(
            self.acting_step_dict, self.ARM_COMPONENT, self.HOST_COMPONENT
        )
        tail_host_component_keys = mgear_build_utils.get_host_component(
            self.acting_step_dict, self.TAIL_COMPONENT, self.HOST_COMPONENT
        )
        if tail_host_component_keys:
            host_component_keys.extend(tail_host_component_keys)

        if not wing_feather_component_keys:
            raise exceptions.MayaNodeNotFound(
                f"No {self.COMPONENT} rig components found in the scene."
            )
        if not wing_feather_end_component_keys:
            raise exceptions.MayaNodeNotFound(
                f"No {self.AIM_COMPONENT} rig components found in the scene."
            )

        if not host_component_keys:
            raise exceptions.MayaNodeNotFound(
                f"No {self.ARM_COMPONENT}{self.HOST_COMPONENT} host rig components found in the scene."
            )

        controlers_set = mgear_build_utils.get_controlers_set(stepDict)
        deformers_set = mgear_build_utils.get_deformers_set(stepDict)
        top_set = mgear_build_utils.get_top_set(stepDict)
        feather_start_set_members = pmc.PyNode(
            FEATHERS_START_SET_NAME
        ).members()
        feathers_proxy_mesh = pmc.PyNode(FEATHERS_PROXY_MESH)
        feathers_proxy_iland_mesh = pmc.PyNode(FEATHERS_PROXY_ILAND_MESH)
        feathers_local_mesh = pmc.PyNode(FEATHERS_PROXY_LOCAL_MESH)

        setup_grp = pmc.PyNode(self.setup_nd_name)
        bnd_root_jnt = pmc.PyNode(self.bnd_root_name)
        if not feather_start_set_members:
            raise exceptions.MayaObjectSetError(
                "The object set {} has no members".format(
                    FEATHERS_START_SET_NAME
                )
            )
        # Here we start with actual running the build.
        feathers_start_locs = feather_setup.sort_start_locs_by_side(
            feather_start_set_members
        )

        dupl_feather_proxy_mesh = feathers_proxy_mesh.duplicate()[0]
        dupl_feathers_proxy_iland_mesh = feathers_proxy_iland_mesh.duplicate()[
            0
        ]

        # A duplicate so tail doesn't grab influence from wing when proximityWrapped
        if pmc.objExists(TAIL_PROXY_MESH):
            tail_local_mesh = pmc.PyNode(TAIL_PROXY_MESH)
            dupl_tail_proxy_mesh = tail_local_mesh.duplicate()[0]

        dag_utils.delete_hidden_shapes(dupl_feather_proxy_mesh)
        dag_utils.delete_hidden_shapes(dupl_feathers_proxy_iland_mesh)
        pmc.parent(
            [dupl_feathers_proxy_iland_mesh, dupl_feather_proxy_mesh], None
        )
        component_controls = [
            mgear_build_utils.get_component_ctrls(self.acting_step_dict, comp)[
                0
            ]
            for comp in wing_feather_component_keys
        ]
        aim_controls = [
            mgear_build_utils.get_component_ctrls(self.acting_step_dict, comp)[
                0
            ]
            for comp in wing_feather_end_component_keys
        ]
        arm_host_controls = [
            mgear_build_utils.get_component_ctrls(self.acting_step_dict, comp)[
                0
            ]
            for comp in host_component_keys
        ]
        l_aim_controls = [
            node for node in aim_controls if "_L_" in node.nodeName()
        ]
        r_aim_controls = [
            node for node in aim_controls if "_R_" in node.nodeName()
        ]
        pin_aim_controls = l_aim_controls[1:-1] + r_aim_controls[1:-1]
        system_root_childs = []
        feather_setup.aim_the_wingFeathers_comps(
            component_controls, aim_controls
        )
        end_ctrl_pin_nodes = feather_setup.pin_feather_edge_ctrl_setup(
            dupl_feathers_proxy_iland_mesh, pin_aim_controls
        )

        (
            aim_drv_jnts,
            aim_drv_jnts_buffer_grps,
        ) = feather_setup.create_aim_drv_joints(feathers_start_locs)

        scale_ctrl = pmc.PyNode(SCALE_CTRL)
        for ctrl in pin_aim_controls:
            root_node = dag_utils.get_root_node_from_child_node(ctrl, feather_setup.RIG_COMPONENT_ROOT_SUFFIX)
            scale_ctrl.scale >> root_node.scale

        seg_pkg_list = feather_setup.create_jnt_segments(aim_drv_jnts)

        for jnt_list in seg_pkg_list:
            for jnt in jnt_list[1]:
                print(jnt)
                pmc.connectAttr(scale_ctrl.scale, pmc.PyNode(jnt).scale)

        (
            drv_locs,
            twist_trs_list,
            ik_handle_list,
        ) = feather_setup.create_ik_spline_setup(
            seg_pkg_list, dupl_feather_proxy_mesh
        )
        controls_pkg = feather_setup.create_tweak_control_setup(
            seg_pkg_list, controlers_set=controlers_set
        )
        feather_setup.create_bnd_joints(
            controls_pkg,
            bnd_root_jnt,
            pxo_deformers_set=deformers_set,
            pxo_root_set=top_set,
        )
        txt_def_list = feather_setup.create_wind_effect(
            feathers_local_mesh, dupl_feather_proxy_mesh, arm_host_controls
        )
        # This section is to redundant needs improvement

        for host_key in host_component_keys:
            control = mgear_build_utils.get_component_ctrls(
                self.acting_step_dict, host_key
            )[0]
            side = mgear_build_utils.get_component_side(
                self.acting_step_dict, host_key
            )

            for wing_section in self.wing_sections_names:

                separator_ = True
                matching_tuple = self.get_matching_ctls_from_pkg(controls_pkg, side, wing_section)

                if not matching_tuple:
                    continue

                self.setup_fake_component(matching_tuple, side, stepDict, wing_section)

                self.setup_attr_control(control, ik_handle_list, matching_tuple, separator_, side, wing_section)

        system_root_childs.extend(aim_drv_jnts_buffer_grps)
        system_root_childs.extend(end_ctrl_pin_nodes)
        system_root_childs.extend(drv_locs)
        system_root_childs.extend(twist_trs_list)
        system_root_childs.extend(txt_def_list)
        system_root_childs.append(dupl_feathers_proxy_iland_mesh)
        system_root_childs.append(dupl_feather_proxy_mesh)

        if pmc.objExists(TAIL_PROXY_MESH):
            system_root_childs.append(dupl_tail_proxy_mesh)
            pmc.hide(dupl_tail_proxy_mesh)

        feather_setup.generate_system_root_node(system_root_childs, setup_grp)
        feather_setup.hide_driver(
            [
                dupl_feathers_proxy_iland_mesh,
                dupl_feather_proxy_mesh,
                txt_def_list[0]
            ]
            + twist_trs_list
            + drv_locs
        )

        feather_setup.attach_body_feathers(FEATHER_ATTACH_GEO_DIC)

        _LOGGER.info("Wing feather setup build successfully.")

    def setup_attr_control(self, control, ik_handle_list, matching_tuple, separator_, side, wing_section, negate_right_side = True):
        negate = False
        if negate_right_side:
            negate = side == "R"

        feather_setup.create_curl_setup(
            matching_tuple,
            control,
            "{}_curl".format(wing_section),
            wing_section,
            "Z",
            separator_,
            negate
        )
        separator_ = False
        for type_ in ["roll", "twist"]:
            matching_ik_list = self.get_matching_ik_list(ik_handle_list, side, wing_section)

            if not matching_ik_list:
                raise ValueError("Unable to find matching ik handles starting with '{}' of '{}' wing section"
                                 .format(side, wing_section))

            feather_setup.create_roll_twist_setup(
                type_,
                matching_ik_list,
                control,
                "{}_{}".format(wing_section, type_),
                wing_section,
                separator_,
                negate
            )

    def setup_fake_component(self, matching_tuple, side, stepDict, wing_section):
        stepDict["mgearRun"].components[wing_section + "_" + side] = mgear_build_utils.MgearFakeComponentClass()
        all_ctls = []
        for obj_list in matching_tuple:
            for obj in obj_list:
                all_ctls.append(obj)
        stepDict["mgearRun"].components[wing_section + "_" + side].groups["controllers"] = all_ctls
        stepDict["mgearRun"].components[wing_section + "_" + side].side = side
        stepDict["mgearRun"].components[wing_section + "_" + side].name = "feather_{}".format(wing_section)

    def get_matching_ik_list(self, ik_handle_list, side, wing_section):
        matching_ik_list = []
        for ik_handle in ik_handle_list:
            if wing_section in str(ik_handle) and side == str(ik_handle)[0]:
                matching_ik_list.append(ik_handle)
        return matching_ik_list

    def get_matching_ctls_from_pkg(self, controls_pkg, side, wing_section):
        matching_tuple = []
        for obj_tuple in controls_pkg:
            if wing_section in obj_tuple[0].name() and (side + "_") in obj_tuple[0].name():
                matching_tuple.append(obj_tuple)
        return matching_tuple


