"""
Custom step to import existing blendshape data into the rig.
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
from pxo_rigging_kit.maya_utils.menu.main import import_latest_bshp_setup
from pxo_rigging_kit.maya_utils.rigging import rig_utils

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
    def __init__(self):
        self.name = "pxo_blendshape_setup"
        self.acting_step_dict = None

    def run(self, stepDict):
        # Here we import the latest blendshape pack we can find of the asset.
        import_latest_bshp_setup()
        # We get all SHAPES weightDriver nodes and pin the position to the parent node.
        constraint_weight_driver_positions()

def constraint_weight_driver_positions(weight_driver_nodes=None):
    """
    Constraints position of all weightdriver with the driver locator parent.

    Args:
        weight_driver_nodes(list): List of weightdrivers if None will take all found in the scene.
                                   Default is None.

    Returns: None if failed. True if successfully.

    """
    if not weight_driver_nodes:
        weight_driver_nodes = pmc.ls(type="weightDriver")
    if weight_driver_nodes:
        for wg_driver in weight_driver_nodes:
            driver_loc = wg_driver.driverMatrix.connections()
            if driver_loc:
                wg_driver_trs = wg_driver.getTransform()
                driver_loc = driver_loc[0]
                driver_nd = driver_loc.getParent()

                rig_utils.create_worldspace_matrix_constraint(
                    wg_driver_trs,
                    driver_nd,
                    channels=["translateX", "translateY", "translateZ"],
                    force=True,
                )
            else:
                continue
        _LOGGER.info(
            "All weightdriver transform channels connected to driver nodes."
        )
        return True