"""
Custom script to prepare the spine component for quadruped rigs.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import third-party modules
from future import standard_library

# Import built-in modules
from itertools import chain
import logging

# Import third-party modules
import pymel.core as pmc
import mgear.shifter.custom_step as cstp

# Import local modules
from pxo_rigging_kit.maya_utils import attributes_utils
from pxo_rigging_kit.maya_utils.rigging import rig_utils
from pxo_rigging_kit.maya_utils import dag_utils
from pxo_rigging_kit.maya_utils.mgear import mgear_build_utils

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

    SPINE_COMPONENT = "spine_"
    ROOT_COMPONENT = "root_"
    SPINE_IK_ORIENT_DIC = {
        "up_axes": "y",
        "aim_axes": "z",
        "aim_ref_pos": (0, 10, 0),
        "up_ref_pos": (0, 0, -10),
    }

    def __init__(self):
        self.name = "pxo_quadruped_spine_setup"
        self.acting_step_dict = None

    def run(self, stepDict):
        self.acting_step_dict = stepDict["mgearRun"]
        spine_comp_keys = mgear_build_utils.get_nonhost_components(
            self.acting_step_dict, self.SPINE_COMPONENT
        )
        root_comp_keys = mgear_build_utils.get_nonhost_components(
            self.acting_step_dict, self.ROOT_COMPONENT, include_capitalization=False
        )
        root_ctrl = list(
            chain.from_iterable(
                [
                    mgear_build_utils.get_component_ctrls(
                        self.acting_step_dict, comp_key
                    )
                    for comp_key in root_comp_keys
                ]
            )
        )
        if len(root_ctrl) > 1:
            raise ValueError(f"More then one root ctrl exist: {root_ctrl}")

        for spine_comp_key in spine_comp_keys:
            spine_controls = mgear_build_utils.get_component_ctrls(
                self.acting_step_dict, spine_comp_key
            )
            self.change_spine_orientation(spine_controls, root_ctrl[0])

    def change_spine_orientation(self, spine_controls, root_ctrl):
        """
        Change the ctrl of the spine component to a world space orientation

        Args:
            spine_controls(list): The spine controller objects.
            root_ctrl(pmc.PyNode): The rig root ctrl.

        """
        spine_ik_controls = [
            node for node in spine_controls if "_ik" in node.name()
        ]
        spine_tan_control = [
            node for node in spine_controls if "_tan_" in node.name()
        ][0]
        spine_tang_controls = []
        for x in range(100):
            for node in spine_controls:
                if "_tan{}".format(x) in node.name():
                    spine_tang_controls.append(node)
        temp_trs = []
        for spine_con in spine_ik_controls:
            spine_childs = spine_con.getChildren(typ="transform")
            if spine_childs:
                for child in spine_childs:
                    spine_child_trs = rig_utils.create_transfrom_on_position(
                        child
                    )
                    spine_child_trs.addChild(child)
                    temp_trs.append(spine_child_trs)
                    pmc.parent(spine_child_trs, w=True)
            new_trs = rig_utils.exchange_connections_to_new_trs(
                spine_con, ["controller", "objectSet", "dagPose"]
            )
            rig_utils.switch_mgear_control_orientation(
                spine_con, **self.SPINE_IK_ORIENT_DIC
            )
            npo = dag_utils.create_buffer_groups([spine_con])[0]
            npo.rename(npo.name().replace("_npo", "_1_npo"))
            spine_con.addChild(new_trs)
            if spine_childs:
                for child_ in spine_childs:
                    new_trs.addChild(child_)
            if temp_trs:
                for node in temp_trs:
                    if pmc.objExists(node):
                        pmc.delete(node)
        if spine_tan_control:
            attributes_utils.unlock_attributes(
                spine_tan_control, ["rx", "ry", "rz"]
            )
            rig_utils.switch_mgear_control_orientation(
                spine_tan_control, **self.SPINE_IK_ORIENT_DIC
            )
            tan_npo = dag_utils.create_buffer_groups([spine_tan_control])[0]
            tan_npo.rename(tan_npo.name().replace("_npo", "_1_npo"))
            attributes_utils.lock_and_hide_attributes(
                spine_tan_control, attributes=["rx", "ry", "rz"]
            )
        if spine_tang_controls:
            for spine_tang in spine_tang_controls:
                tange_trs = rig_utils.exchange_connections_to_new_trs(
                    spine_tang, ["controller", "objectSet", "dagPose"]
                )
                tange_off_nd = spine_tang.getParent()
                attributes_utils.unlock_attributes(
                    tange_off_nd, ["tx", "ty", "tz", "rx", "ry", "rz"]
                )
                rig_utils.switch_mgear_control_orientation(
                    tange_off_nd, **self.SPINE_IK_ORIENT_DIC
                )
                tange_off_nd.translate.disconnect()
                mult_db_nd = pmc.createNode("multDoubleLinear")
                spine_tan_control.translateY.connect(mult_db_nd.input1)
                mult_db_nd.input2.set(-1)
                mult_db_nd.output.connect(tange_off_nd.translateZ)
                spine_tan_control.translateZ.connect(tange_off_nd.translateY)
                spine_tan_control.translateX.connect(tange_off_nd.translateX)
                attributes_utils.lock_and_hide_attributes(tange_off_nd)
                spine_tang.addChild(tange_trs)
                pmc.matchTransform(
                    spine_ik_controls[0],
                    root_ctrl,
                    pos=False,
                    rot=False,
                    scl=False,
                    piv=True,
                )
