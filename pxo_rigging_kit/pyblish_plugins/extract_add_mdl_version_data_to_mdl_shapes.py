"""
Store the asset version number on the mdl shape nodes.

Requires:
    instance.data["rig_asset_assembly_nd"]

"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import built-in modules
from builtins import int

# Import third-party modules
from future import standard_library

standard_library.install_aliases()
# Import third-party modules
from pyblish import api as pyblish_api

# Import local modules
from pxo_rigging_kit import constants
from pxo_rigging_kit.maya_utils import \
    exceptions  # We import this module to register the pymel virtual classes for our custom nodes.
from pxo_rigging_kit.maya_utils import pymel_utils


class ExtractAddMdlVersionDataToMdlShapes(pyblish_api.InstancePlugin):
    """Store the asset version number on the mdl shape nodes."""

    label = "Add mdl version data to mdl shape nodes"
    offset = 0.298
    order = pyblish_api.ExtractorOrder + offset
    families = ["rig"]
    hosts = ["maya"]
    targets = ["local"]
    optional = True
    active = True
    mdl_version_str = "mdl_version"

    def process(self, instance):
        """Store the asset version number on the mdl shape nodes.

        Args:
            context (pyblish.plugin.Context): Context object that contains information
                about the current context to process on.

        """
        try:
            # Try to get the asset assembly node form the instance data.
            # Will fail if list is empty.
            asset_assembly_nd = instance.data["rig_asset_assembly_nd"][0]
        except:
            raise exceptions.MayaNodeNotFound("Rig Asset Assembly node is missing.")
        asset_assembly_data_list = asset_assembly_nd.get_assembly_data()
        for asset_data_dict in asset_assembly_data_list:
            mdl_version = int(asset_data_dict["version"])
            components_dict = asset_data_dict["components"]
            components_keys = list(components_dict.keys())
            for key in components_keys:
                items = list(components_dict[key].items())
                geo_transforms = list(set(items[0][1]))
                shape_nodes = []
                for node in geo_transforms:
                    shape_nd = node.getShape(noIntermediate=True)
                    if shape_nd:
                        shape_nodes.append(shape_nd)
                    else:
                        raise exceptions.MayaNodeNotFound(
                            "{} has no shape nodes".format(node)
                        )
                [
                    node.addAttr(
                        "{}_{}".format(
                            constants.MAYA_ARNOLD_ATTR_PREFIX,
                            self.mdl_version_str,
                        ),
                        type="long",
                        keyable=True,
                    )
                    for node in shape_nodes
                    if not node.hasAttr(
                        "{}_{}".format(
                            constants.MAYA_ARNOLD_ATTR_PREFIX,
                            self.mdl_version_str,
                        )
                    )
                ]
                [
                    node_.attr(
                        "{}_{}".format(
                            constants.MAYA_ARNOLD_ATTR_PREFIX,
                            self.mdl_version_str,
                        )
                    ).set(mdl_version)
                    for node_ in shape_nodes
                ]
        self.log.info("Adding mdl version to model shapes nodes successfully.")
