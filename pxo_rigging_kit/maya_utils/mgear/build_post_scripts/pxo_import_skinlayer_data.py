# Author: Johannes Woz / Head of Rigging

"""
Post script module to set up the skinlayer setup.
Requieres:
- pre script pxo_skinlayer_data_import_setup.py.
- existing skinning data on the layer meshes.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import built-in modules
import logging

# Import third-party modules
# external libraries
from future import standard_library
import mgear.shifter.custom_step as cstp
# Maya modules
import pymel.core as pmc

# Import local modules
# internal libraries
from pxo_rigging_kit.maya_utils.deformers.utilities import skincluster_layering

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

    def __init__(self):
        self.name = "pxo_import_skinlayer_data"
        self.delete_on_publish = "delete_on_publish"

    def run(self, stepDict):
        """Run Method.

        Args:

            stepDict(dict): Containing the objects from the previous
            custom step.

        Example:
            stepDict["mgearRun"].global_ctl gets back the global_ctl
            from shifter rig from post step

        """
        layer_meshes = skin_layering.load_skinlayer_data()
        delete_on_publish_set = pmc.PyNode(self.delete_on_publish)
        delete_on_publish_set.addMembers(layer_meshes)
