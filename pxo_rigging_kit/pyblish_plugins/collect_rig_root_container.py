"""Collect the rig root container."""

# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Import third-party modules
from future import standard_library
from pyblish import api as pyblish_api

# Import local modules
from pxo_rigging_kit.maya_utils import exceptions
from pxo_rigging_kit.maya_utils.rigging import rig_utils

standard_library.install_aliases()


class CollectRigRootContainer(pyblish_api.InstancePlugin):
    """Discover and collect rig root container."""

    offset = 0.46
    order = pyblish_api.CollectorOrder + offset
    label = "Collect Rig Root Container"
    families = ["rig"]
    hosts = ["maya"]
    targets = ["local"]

    def process(self, instance):
        """Discover and collect the rig root container node.

        Args:
            instance (pyblish.api.Instance): Instance object passed down from Pyblish.

        Raises:
            Exception: If the meta node can not be collected.

        """
        rig_root_container = rig_utils.get_rig_containers()[0]
        if not rig_root_container:
            raise exceptions.MayaNodeNotFound("No rig root container.")
        instance.data["rig_root_container"] = rig_root_container
        self.log.info("Rig root container collected.")
