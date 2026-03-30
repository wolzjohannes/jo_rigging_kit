"""Validate remove Shapes Plugin."""

# Import third-party modules
from maya_pyblish_plugins import maya_ui
from pixo_pyblish.constants import CleanerOrder
from pyblish.api import ContextPlugin

# Import local modules
from pxo_rigging_kit.maya_utils.scene_utils import delete_shapes_plugin_data


class CollectRemoveShapesPlugin(ContextPlugin):
    """Remove SHAPES plugin info cleaner."""

    offset = .2
    order = CleanerOrder + offset

    label = "Remove SHAPES Attributes and Nodes"

    families = ["rig"]
    hosts = ["maya"]
    optional = True

    def process(self, context):
        """Remove SHAPES plugin data from the scene.

        Args:
            context (pyblish.plugin.Context): The global context.

        """
        with maya_ui.refresh_suspended():
            delete_shapes_plugin_data()

            self.log.info(
                    "SHAPES plugin data was deleted from blendShape nodes."
            )


