"""
Custom step to build the dragon frontFlap system
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import built-in modules
import logging

# Import third-party modules
from future import standard_library
import mgear.shifter.custom_step as cstp
import pymel.core as pmc

# Import local modules
from pxo_rigging_kit.maya_utils.mgear.mgear_build_utils import BetterRibbon2

standard_library.install_aliases()

##########################################################
# GLOBALS
##########################################################

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)

##########################################################
# FUNCTIONS
##########################################################

class CustomShifterStep(cstp.customShifterMainStep):

    FRONT_FLAP_COMP = "frontFlap"
    FRONT_FLAP_ROOT = "frontFlap_*0_root"
    FRONT_FLAP_STR = "frontFlap_*_0_ik*_default_ctrl"
    GLOB_CTRL = "global_0_default_ctrl"

    def __init__(self):
        self.name = "pxo_front_flap_setup"
        self.acting_step_dict = None
        self.setup = "setup"

    def run(self, stepDict):
        for side in ["L", "R"]:
            setup_grp = pmc.PyNode(self.setup)
            guide_driver_mesh = pmc.PyNode(f"guide_frontFlap_driver_{side}_0_geo")
            driver_mesh = guide_driver_mesh.duplicate(guide_driver_mesh, n=f"frontFlap_driver_{side}_0_geo")[0]
            my_ribbon = BetterRibbon2(fk_ik_component=f"{self.FRONT_FLAP_COMP}_{side}0",
                                      surface_association="mesh", driver_mesh=driver_mesh,
                                      auto_skin_curve=True,
                                      rebuild_curve=10)
            my_ribbon.build()
            pmc.parent(driver_mesh, setup_grp)
            driver_mesh.visibility.set(0)
        for node in pmc.ls(self.FRONT_FLAP_STR):
            cns_grp = node.getParent()
            for axe in ["X", "Y", "Z"]:
                scale_attr = cns_grp.attr(f"scale{axe}")
                scale_attr.unlock()
                pmc.PyNode(f"{self.GLOB_CTRL}.{f'scale{axe}'}").connect(scale_attr)
        for root in pmc.ls(self.FRONT_FLAP_ROOT):
            root.inheritsTransform.set(0)