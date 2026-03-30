"""
mgear post script for animation controls modifications.

Requieres:
    -mgear pre script:
        - pxo_control_buffer_setup.py
            - stepDict["controllers_org_tmp"]
"""

# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import built-in modules
import logging
from importlib import reload

# Import third-party modules
from future import standard_library
from mgear.rigbits import mirror_controls
from mgear.shifter import guide_manager
import mgear.shifter.custom_step as cstp
import pymel.core as pmc

# Import local modules
from pxo_rigging_kit.maya_utils.rigging import rig_utils
from pxo_rigging_kit.maya_utils.mgear import guide_utils
from pxo_rigging_kit.maya_utils.mgear import mgear_build_utils
from pxo_rigging_kit.maya_utils import dag_utils

reload(dag_utils)

standard_library.install_aliases()

#######################################################
# GLOBALS
#######################################################

logging.basicConfig(level=logging)
_LOGGER = logging.getLogger(__name__ + ".py")
CONTROLLERS_ORG_M_ATTR = guide_utils.GUIDES_BUFFER_CRV_GRP_ROOT_ND_NAME

#######################################################
# CLASSES
#######################################################


class CustomShifterStep(
    cstp.customShifterMainStep, mirror_controls.MirrorController
):
    """Custom Step description"""

    R_SIDE_STR = "R"
    L_SIDE_STR = "L"
    MIRROR_COMPONENT_EXCEPTION_LIST = ["ui_slider_01","force_skip"]

    def __init__(self):
        self.name = "pxo_control_curves_setup"

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
        # Get the controllers_org duplicate from before the build.
        controllers_org_tmp = stepDict.get("controllers_org_tmp", None)
        if not controllers_org_tmp:
            controllers_org_tmp = pmc.PyNode(f"{CONTROLLERS_ORG_M_ATTR}_temp")

        controllers_set = mgear_build_utils.get_controlers_set(stepDict)

        controllers_set = pmc.PyNode(controllers_set.name())#mgear 2025
        rig_utils.add_pxo_anim_tags(controllers_set.members())

        # THis could be obselete with the newest mgear version
        # self._reformat_anim_control_names(
        #     [("_control_", "_")], controllers_set.members()
        # )

        # exchange controllers org group with the secured temp version.
        self._preserve_ctrl_buffer_data(controllers_org_tmp)

        # mirror the ctrl shapes from left to right for safety.
        #self._mirror_left_to_right(controllers_set.members())

        # extract all control curves for safety as buffer controls to the controllers_org grp
        # self._extract_ctrls_to_buffer_curves(controllers_set)

    def _preserve_ctrl_buffer_data(self, controllers_org_tmp):
        """
        Will exchange the controllers_org group with a duplicate from before the build.
        Sometimes this curves are coruppted during the build.

        Args:
            controllers_org_tmp(pmc.PyNode): The controller_org group from before the build.

        """
        controllers_org = guide_utils.get_buffer_root_grp_from_scene()
        controllers_org_parent = controllers_org.getParent()
        controllers_org_name = str(controllers_org.name(long=None))
        pmc.delete(controllers_org)
        controllers_org_tmp.setParent(controllers_org_parent)
        controllers_org_tmp.rename(controllers_org_name)
        for node in controllers_org_tmp.getChildren():
            restored_name = node.name(long=None).replace("_tmp", "")
            node.rename(restored_name)

    def _extract_ctrls_to_buffer_curves(self, controllers_set):
        """
        Extract the rig controller shapes as bufferc curves.

        Args:
            controllers_set(pmc.PyNode): The controllers object set.

        """
        current_selection = pmc.selected()
        pmc.select(controllers_set)
        guide_manager.extract_controls()
        pmc.select(current_selection)

    def _reformat_anim_control_names(self, search_pattern_list, anim_controls):
        """
        Reformat anim control names by given search pattern.

        Args:
            search_pattern_list(list): The seach pattern for exchanging.
            anim_controls(list): The anim rig controls.

        """
        for ctrl in anim_controls:
            new_name = ctrl.name(long=False)
            for pattern_tuple in search_pattern_list:
                new_name = new_name.replace(pattern_tuple[0], pattern_tuple[1])
            ctrl.rename(new_name)

    def _mirror_left_to_right(self, controls):
        r_controls = [
            node
            for node in controls
            if node.getMatrix(worldSpace=True).translate[0] < 0.0
            and f"_{self.R_SIDE_STR}_" in node.name(long=None)
        ]
        l_controls = [
            pmc.PyNode(node.replace(f"_{self.R_SIDE_STR}_", f"_{self.L_SIDE_STR}_"))
            for node in r_controls
            if node.overrideDisplayType.get() == 0
            and node.getShape().overrideDisplayType.get() == 0
            and True is pmc.objExists(node.replace(f"_{self.R_SIDE_STR}_", f"_{self.L_SIDE_STR}_"))
        ]
        pairs = [
            [source, pmc.PyNode(source.name(long=None).replace(f"_{self.L_SIDE_STR}_", f"_{self.R_SIDE_STR}_"))]
            for source in l_controls
        ]
        for source_crv, target_crv in pairs:
            if not pmc.objExists(target_crv + ".compRoot"):
                continue
            target_crv_root_nd = target_crv.compRoot.get()
            comp_type = target_crv_root_nd.componentType.get()
            if comp_type in self.MIRROR_COMPONENT_EXCEPTION_LIST:
                continue
            dag_utils.swap_curve_shapes(source_crv, target_crv, mirror=True, reel_swap=False)