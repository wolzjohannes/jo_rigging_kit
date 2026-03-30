"""
Close the rig container and publish all anim controls in the container.
Insert imported mdl reference.

Requires:
    instance.data["rig_root_container"]

"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Import third-party modules
from future import standard_library
from pyblish import api as pyblish_api

# Import local modules
from pxo_rigging_kit.maya_utils.rigging import rig_utils

standard_library.install_aliases()


class ExtractCloseRigContainer(pyblish_api.InstancePlugin):
    """Extract rig version to container root node meta data."""

    label = "Close the rig container root node"
    offset = 0.299
    order = pyblish_api.ExtractorOrder + offset
    families = ["rig"]
    hosts = ["maya"]
    targets = ["local"]
    optional = True
    active = True

    def process(self, instance):
        """Extract the current state of the current work file.

        Args:
            context (pyblish.plugin.Context): Context object that contains information
                about the current context to process on.

        """
        rig_root_container = instance.data["rig_root_container"]
        rig_utils.finish_rig_root_nd(rig_root_container)
