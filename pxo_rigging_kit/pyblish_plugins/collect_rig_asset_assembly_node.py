"""Collect the rig asset assembly node.
This node inherits all the mdl asset data with existing in the rig."""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import third-party modules
from future import standard_library

standard_library.install_aliases()
# Import third-party modules
from pyblish import api as pyblish_api

# Import local modules
from pxo_rigging_kit.maya_utils import assembly_utils
from pxo_rigging_kit.maya_utils import exceptions


class CollectRigAssetAssemblyNode(pyblish_api.InstancePlugin):
    """Discover and collect all LOD object set data in the scene."""

    offset = 0.49
    order = pyblish_api.CollectorOrder + offset
    label = "Collect Rig Asset Assembly Node"
    families = ["rig"]
    hosts = ["maya"]
    targets = ["local"]

    def process(self, instance):
        """Discover and collect the rig asset assembly node.

        Args:
            context (pyblish.api.Instance): Instance object passed down from Pyblish.

        Raises:
            Exception: If no asset assembly.

        """
        asset_assembly_nodes = assembly_utils.get_asset_assembly_nodes_from_scene()
        instance.data["rig_asset_assembly_nd"] = asset_assembly_nodes
        if not instance:
            exceptions.MayaNodeNotFound("Rig asset assembly not existing in the scene")
        self.log.info("Rig asset assembly node collected.")
