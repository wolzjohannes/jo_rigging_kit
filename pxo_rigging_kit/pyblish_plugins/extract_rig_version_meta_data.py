"""Extract version to node.

Requires:
    context.data["version_number"]
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
from pxo_rigging_kit.maya_utils import \
    pymel_utils  # Needs to be imported to register the pxo nodes in pymel

standard_library.install_aliases()


class ExtractRigVersionMetaData(pyblish_api.InstancePlugin):
    """Extract rig version to container root node meta data."""

    label = "Add Rig Version Meta Data to rig container"
    offset = 0.29
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
        version_number = instance.context.data.get("version_number")
        rig_root_container.set_meta_rig_publish_version(version_number)
        self.log.info("Rig version meta data added.")
