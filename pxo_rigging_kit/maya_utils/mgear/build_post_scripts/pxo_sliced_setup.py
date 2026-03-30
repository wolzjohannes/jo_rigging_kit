"""
Custom step to constrain the sliced geo of the dragons.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import third-party modules
from future import standard_library
import mgear.shifter.custom_step as cstp
import pymel.core as pmc

# Import built-in modules
import logging
from importlib import reload
# Import local modules
from pxo_rigging_kit.maya_utils.rigging import rig_utils
reload(rig_utils)
##########################################################
# GLOBALS
##########################################################

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)
standard_library.install_aliases()

##########################################################
# FUNCTIONS
##########################################################


class CustomShifterStep(cstp.customShifterMainStep):
    def __init__(self):
        self.name = "pxo_sliced_setup"
        self.acting_step_dict = None
        self.sliced_root_node_name = "*:*sliced*grp"
        self.shape_parent_nd_attr_name = "mtoa_constant_parent_nd"
        self.parent_nd_attr_name = "parent_nd"

    def run(self, stepDict):
        self.connect_sliced_meshes()

    def connect_sliced_meshes(self):
        """
        Connect the sliced meshes.
        """
        pmc.select(clear=True)
        sliced_geo_root_nd = pmc.ls(self.sliced_root_node_name)
        if not sliced_geo_root_nd:
            raise LookupError(
                "No sliced root node found with name patter {}.".format(
                    self.sliced_root_node_name
                )
            )
        sliced_geos = sliced_geo_root_nd[0].getChildren()
        pivot_trs = pmc.createNode("transform")
        for node in sliced_geos:
            pmc.matchTransform(
                node, pivot_trs, pos=False, rot=False, scl=False, piv=True
            )
            shape_nd = node.getShape()
            if node.hasAttr(self.parent_nd_attr_name):
                parent_nd_name = node.attr(self.parent_nd_attr_name).get()
            elif shape_nd.hasAttr(self.shape_parent_nd_attr_name):
                parent_nd_name = shape_nd.attr(self.shape_parent_nd_attr_name).get()
            else:
                _LOGGER.info(f"No parent_nd attribute existing either on the transform or shape node")
                continue

            try:
                jnt = pmc.PyNode(parent_nd_name)
            except pmc.general.MayaNodeError:
                _LOGGER.info(f"{parent_nd_name} not existing will skip.")
                continue

            rig_utils.pxo_constraining(masters=jnt,
                                       slaves=node,
                                       maintainOffset=True,
                                       name=None,
                                       skipRotate=None,
                                       skipTranslate=None,
                                       skipScale=None,
                                       native=False,
                                       space_switch=False,
                                       host=None,
                                       use_parent_offset_mtx=True
                                       )
        pmc.delete(pivot_trs)
        _LOGGER.info("Sliced geos constraining successfully.")
