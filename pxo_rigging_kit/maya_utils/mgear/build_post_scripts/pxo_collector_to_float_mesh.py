# mgear / pixo float meshes setup
# www.pixomondo.com
# Date: 10 / 10 / 2023
# Artist: Christof Puehringer / Rigging TD

"""
Custom script to prepare the arms to our needs.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import built-in modules
from importlib import reload
import logging

# Import third-party modules
# external libraries
from future import standard_library
import mgear.shifter.custom_step as cstp

# import maya modules
import pymel.core as pmc

# Import local modules
# internal libraries
from pxo_rigging_kit.maya_utils.mgear import mgear_build_utils
from pxo_rigging_kit.maya_utils.rigging import mesh_islands
reload(mesh_islands)
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

    COLLECTORS = "Collect"
    SETUP_GRP_NAME = "setup"
    SIZE_ATTR_NAME = "island_size"

    def __init__(self):
        self.name = "pxo_islands_setup"
        self.pxo_rigging_kit_old = None

    def run(self, stepDict):
        """Run Method.

        Args:

            stepDict(dict): Containing the objects from the previous
            custom step.

        Example:
            stepDict["mgearRun"].global_ctl gets back the global_ctl
            from shifter rig from post step

        """
        dimension = 2.5

        setup_grp = pmc.PyNode(self.SETUP_GRP_NAME)

        acting_step_dict = stepDict["mgearRun"]

        collector_roots = mgear_build_utils.get_nonhost_components(
            acting_step_dict,
            self.COLLECTORS,
        )

        if not collector_roots:
            return False

        for collector_root in collector_roots:

            collector_root_name = mgear_build_utils.get_component_name(
                acting_step_dict, collector_root
            )
            collector_root_ctl = mgear_build_utils.get_component_ctrls(
                acting_step_dict, collector_root
            )[0]
            subroots = get_subroots(collector_root_ctl)

            roots_node = pmc.ls(collector_root + "_root")

            for node in roots_node:
                if node.hasAttr("isGearGuide"):
                    if not node.hasAttr(self.SIZE_ATTR_NAME):
                        pmc.addAttr(
                            node,
                            longName=self.SIZE_ATTR_NAME,
                            attributeType="double",
                            defaultValue=2.5,
                            keyable=False,
                        )
                    else:
                        dimension = node.getAttr(self.SIZE_ATTR_NAME)
            build_islands_on_roots(
                collector_root_name, setup_grp, subroots, dimension
            )

            kill_collector_shapes(collector_root_ctl)


def build_islands_on_roots(root_node, setup_node, subroot_nodes, dimension=2.5):

    island_mesh, uv_pin_node = mesh_islands.build_combined_pin_mesh(
        subroot_nodes,
        rotate=True,
        pin_node_split_amount=100,
        ribbon_node_split_amount=100,
        desired_count=100,
        system_name=root_node,
        radius=dimension,
    )

    setup_node.addChild(island_mesh[0])
    island_mesh[0].visibility.set(0)


def get_subroots(root_node):
    return root_node.getChildren(type="transform")


def kill_collector_shapes(collector_control):
    collector_shapes = collector_control.getShapes()
    pmc.delete(collector_shapes)


def remove_numbering(acting_step_dict, subrooot):
    subroot_ctrl = mgear_build_utils.get_component_ctrls(
        acting_step_dict, subrooot
    )[0]
    subroot_ctrl_name = str(subroot_ctrl.shortName())
    subroot_ctrl.rename(subroot_ctrl_name.replace("_0_", "_"))
