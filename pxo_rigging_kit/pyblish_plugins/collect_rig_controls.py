"""Collect rig anim interface plugin in the anim pyblish publishing.

Requires:
    - CollectAnim

"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import third-party modules
from future import standard_library

standard_library.install_aliases()
# Import built-in modules
from builtins import str

# Import third-party modules
from maya_tagging import TAG_EXPORT_ANIMATION
from maya_tagging import tagging_utils
from pyblish.api import CollectorOrder
from pyblish.api import InstancePlugin

# Import local modules
from pxo_rigging_kit.constants import PXO_CONTROLS_SET_NAME


def _node_has_a_anim_tag(node):
    """Returns a boolean indicating if the given node is tagged as layout.

    Args:
        node (pm.PyNode): Node to check

    Returns:
        bool: True if the given node is tagged as layout, False if not.

    """
    if tagging_utils.get_tag(node, TAG_EXPORT_ANIMATION):
        return True
    return False


class CollectRigsControlInterface(InstancePlugin):
    """Collect Rigs Control Interface plugin."""

    offset = 0.01
    order = CollectorOrder + offset
    families = ["anim"]
    hosts = ["maya"]
    label = "Collect Rigs control Interface"

    def process(self, instance):
        """
        Collect all anim controls for each anim instance and
        stored in the instance.data with the "anim_controls" key.

        Args:
            instance (pyblish.plugin.instance): instance object.

        """
        excluded_nodes = instance.context.data.get("excludedNodes", [])
        reference = instance.data["root"].referenceFile().refNode
        instance.data["anim_controls"] = self._get_anim_controls(
            reference, excluded_nodes
        )

    def _get_anim_controls(self, reference, excluded_nodes):
        """
        Get the anim controls for each anim instance based on his referenced nodes.
        First it will try to find a object set node with the
        PXO_CONTROLS_SET_NAME and his members.
        If can not find the object set it will try to find all nodes with
        export animation tag.

        Args:
            reference(pmc.PyNode): The instance reference.
            excluded_nodes(list). All nodes which are excluded from publishing.

        Return:
            None if reference has no nodes.
            None if rig root node is an excluded node.
            None if no objectset or no tagged anim controls exist.
            List if successfully.

        """
        if not reference.nodes():
            return
        root = reference.nodes()[0]
        if root in excluded_nodes:
            return

        controllers_set = [
            node
            for node in reference.nodes()
            if node.type() == "objectSet"
            and node.name(stripNamespace=True) == PXO_CONTROLS_SET_NAME
        ]
        if controllers_set:
            return controllers_set[0].members()
        return [node for node in reference.nodes() if _node_has_a_anim_tag(node)]
