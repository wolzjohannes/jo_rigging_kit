"""
Pre script for buffer curve modifications.
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
from importlib import reload

# Import third-party modules
import mgear.shifter.custom_step as cstp
import pymel.core as pmc

# Import local modules
from pxo_rigging_kit.maya_utils.mgear import guide_utils
from pxo_rigging_kit.maya_utils import exceptions
from pxo_rigging_kit.maya_utils import attributes_utils

standard_library.install_aliases()
reload(guide_utils)

#######################################################
# GLOBALS
#######################################################

logging.basicConfig(level=logging)
_LOGGER = logging.getLogger(__name__ + ".py")

#######################################################
# CLASSES
#######################################################

class CustomShifterStep(cstp.customShifterMainStep):

    CONTROLLERS_ORG_M_ATTR = guide_utils.GUIDES_BUFFER_CRV_GRP_ROOT_ND_NAME
    ANIM_CURVE_COLOR_MIRROR_DIC = {0: 0, 18: 20, 6: 13, 11: 21}

    def __init__(self):
        self.name = "pxo_control_buffer_setup"

    def run(self, stepDict):
        """Run Method.

        Args:

            stepDict(dict): Containing the objects from the previous
            custom step.

        """
        guide_root_nd = guide_utils.get_guide_root_nd_from_selection()
        controllers_org = guide_utils.get_buffer_root_grp_from_guide(
            guide_root_nd
        )
        if not controllers_org:
            raise exceptions.MayaNodeNotFound(f"No root node of the control buffer curves found under the {guide_root_nd}")
        controllers_org = controllers_org[0]
        print(controllers_org)
        self.prep_buffer_curves(controllers_org)
        self.secure_controllers_org(guide_root_nd, controllers_org, stepDict)

    def prep_buffer_curves(self, controllers_org):
        """
        Prep the buffer curves for post scripts.

        Args:
            controllers_org(pmc.Pynode()): The buffer curve root group node.

        """

        # Get all buffer curves
        source_buffer_curves = [
            node for node in controllers_org.getChildren() if node.getShape()
        ]
        for node in source_buffer_curves:
            if "_L_" in node.name():
                r_name = node.name().replace("_L_", "_R_")
                if not pmc.objExists(r_name):
                    r_buffer_curve = pmc.duplicate(node, n="temp_buffer_curve")[
                        0
                    ]
                    attributes_utils.lock_and_hide_attributes(r_buffer_curve, False, False)
                    mirror_grp = pmc.createNode("transform")
                    pmc.parent(r_buffer_curve, mirror_grp)
                    mirror_grp.scale.set(-1, 1, -1)
                    pmc.parent(r_buffer_curve, controllers_org)
                    pmc.delete(mirror_grp)
                    pmc.makeIdentity(
                        r_buffer_curve, t=False, r=False, s=True, a=True
                    )
                    current_color_index_trs = r_buffer_curve.overrideColor.get()
                    r_color_trs = self.ANIM_CURVE_COLOR_MIRROR_DIC.get(current_color_index_trs, current_color_index_trs)
                    r_buffer_curve.overrideColor.set(r_color_trs)
                    r_buffer_curve.rename(r_name)
                    for r_shape in r_buffer_curve.getShapes():
                        current_color_index = r_shape.overrideColor.get()
                        r_color = self.ANIM_CURVE_COLOR_MIRROR_DIC.get(current_color_index, current_color_index)
                        r_shape.overrideColor.set(r_color)

        _LOGGER.info("Prep anim curves succeed.")

    def secure_controllers_org(self, guide_root_nd, controllers_org, stepDict):
        """
        This method will duplicate the buffer groups of mgear for safety purposes.
        And pass it to the mgear build stepDict for further use.

        Args:
            controllers_org(pmc.PyNode): The original controllers org group.
            stepDict(dict): THe mgear build stepdict.

        """
        controllers_org_dup = pmc.duplicate(
            controllers_org, n=f"{self.CONTROLLERS_ORG_M_ATTR}_tmp"
        )[0]
        for node in controllers_org_dup.getChildren():
            tmp_name = f"{node.name(long=None)}_tmp"
            node.rename(tmp_name)
        pmc.parent(controllers_org_dup, None)
        stepDict["controllers_org_tmp"] = controllers_org_dup
        pmc.select(guide_root_nd)
