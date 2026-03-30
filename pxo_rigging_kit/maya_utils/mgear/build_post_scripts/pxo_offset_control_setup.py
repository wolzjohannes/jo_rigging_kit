# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import pprint

# Import third-party modules
from future import standard_library

# Import built-in modules
import logging

# Import third-party modules
import pymel.core as pmc
import mgear.shifter.custom_step as cstp

# Import local modules
from pxo_rigging_kit.maya_utils import attributes_utils
from pxo_rigging_kit.maya_utils.mgear import mgear_build_utils
from pxo_rigging_kit.maya_utils import dag_utils

standard_library.install_aliases()

#######################################################
# GLOBALS
#######################################################

logging.basicConfig(level=logging)
_LOGGER = logging.getLogger(__name__ + ".py")
OFFSET_CTRL_ATTR_NAME = "offset_ctrl"

#######################################################
# CLASSES
#######################################################


class CustomShifterStep(cstp.customShifterMainStep):
    """Custom Step description
    """
    HOST_COMPONENT = "Host"

    def __init__(self):
        self.name = "pxo_offset_control_setup"
        self.acting_step_dict = None

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
        self.acting_step_dict = stepDict["mgearRun"]
        non_host_components = mgear_build_utils.get_all_components(self.acting_step_dict, self.HOST_COMPONENT)
        for comp_key in non_host_components:
            controls = mgear_build_utils.get_component_ctrls(self.acting_step_dict, comp_key)
            for ctrl in controls:
                create_offset_control(ctrl)

def create_offset_control(ctrl_nd):
    """
    Creates a offset ctrl for given ctrl node and puts it on top of the ctrl_nd.

    Args:
        ctrl_nd(pmc.PyNode): The control node.

    """
    ctrl_nd_name = ctrl_nd.name(long=None)
    ctrl_nd_split = ctrl_nd_name.split('_')
    offset_ctrl = pmc.duplicate(ctrl_nd, n=f"{'_'.join(ctrl_nd_split[0:-1])}_offset_{ctrl_nd_split[-1]}")[0]
    dag_utils.create_buffer_groups([offset_ctrl])
    shapes = offset_ctrl.getShapes(noIntermediate=True)
    killable_childs = [node for node in offset_ctrl.getChildren() if node not in shapes]
    pmc.delete(killable_childs)
    attributes_utils.lock_and_hide_attributes(offset_ctrl, False, False, ["sx", "sy", "sz"])
    offset_ctrl.scale.set(1.25, 1.25, 1.25)
    pmc.makeIdentity(offset_ctrl, apply=True, translate=False, rotate=False, scale=True)
    attributes_utils.lock_and_hide_attributes(offset_ctrl, True, True, ["sx", "sy", "sz"])
    ctrl_nd.addAttr(OFFSET_CTRL_ATTR_NAME, type="bool", keyable=True, dv=0)
    for shape in shapes:
        ctrl_nd.attr(OFFSET_CTRL_ATTR_NAME).connect(shape.visibility)
    locked_attributes = []
    for axe in ["X", "Y", "Z"]:
        for channel in ["translate", "rotate"]:
            attr = ctrl_nd.attr(f"{channel}{axe}")
            if attr.isLocked():
                locked_attributes.append(attr)
    if locked_attributes:
        for attr_ in locked_attributes:
            attr_.unlock()
    ctrl_nd.setParent(offset_ctrl)
    for attr__ in locked_attributes:
            attr__.lock()
