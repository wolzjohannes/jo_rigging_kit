"""Extract rig lod from master rig.

Requires:
    instance.data["rig_file"]
    instance.data["lod_number"]
    instance.context.data["extractionData"]
    instance.data["AnimControllerInterfaceAttributes"]
    families = ["lod_rig"]

Notes:
    This has to be placed after the ExtractRigMB plugin.
    Because we want all pre pyblish plugins happen before.
    And we open the extracted rig as base for the extraction process.
    We do it this way instead of working with the undoChunk because the undoChunk is very
    unstable with complicated assets. And produced a lot of fatal errors in the pubslish process.
    The function rig_utils.extract_rig_lods() is a mirrored logic from this
    plugin so we can test build the LODs in our work scenes before publish
    to know if everything is alright.

"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Import built-in modules
import os
import tempfile

# Import third-party modules
from future import standard_library
from maya_pyblish_plugins import rig_utils as maya_pyblish_rig_utils
from maya_pyblish_plugins import maya_skin
from maya_pyblish_plugins import maya_ui
from pyblish import api as pyblish_api
from pixo_pyblish import plugin_instances
from pixo_pyblish.plugins.integrate_file import assemble_publish_path
from pixo_pyblish.plugins.integrate_file import VERSION_NUMBER
from pixo_pyblish.plugins.integrate_file import PUBLISH_PATH
import pymel.core as pmc

# Import local modules
from pxo_rigging_kit.maya_utils import lod_utils
from pxo_rigging_kit.maya_utils.rigging import rig_utils

standard_library.install_aliases()


class ExtractRigLods(pyblish_api.InstancePlugin):
    """Extract rig LODs from current master rig."""

    label = "Extract Rig LODs"
    offset = 0.39
    order = pyblish_api.ExtractorOrder + offset
    families = ["lod_rig"]
    hosts = ["maya"]
    targets = ["local"]
    optional = True
    active = True

    def process(self, instance):
        """Extract the rig lod from given rig instance.

        Args:
            context (pyblish.plugin.Instance): Instance object passed down from Pyblish.

        """
        master_rig_instance = instance.data["master_instance"]
        upstream_field = master_rig_instance.data["versionStreamFields"].get("upstream", [])
        rig_file = instance.data["rig_file"]
        pmc.openFile(rig_file, force=True)
        no_workfile_path = os.path.join(tempfile.gettempdir(), "NO_WORKFILE.ma")
        maya_ui.rename_workfile(no_workfile_path)
        lod = instance.data["lod_number"]
        tempfile_path = instance.data["extractionPath"]
        # Here we get the lod data again because the data can change a lot during all pyblish plugins from before.
        lod_set_data = lod_utils.get_lod_data_dict(True, True)
        # fall out if no lod data exist for given lod number.
        if not any(lod_set_data["lods"][lod].values()):
            self.log.info(
                "No LOD data exist for {}. Will skip.".format(instance.name)
            )
            return
        anim_control_interface_attributes_dict = instance.data[
            "AnimControllerInterfaceAttributes"
        ]
        rig_utils.extract_single_rig_lod(
            lod,
            lod_set_data,
            tempfile_path,
            anim_control_interface_attributes_dict,
        )
        plugin_instances.ensure_extraction_data(instance)
        ext = ".mb"
        extraction_data_dict = {
            "extractionPath": tempfile_path,
            "ext": ext,
            "plugin": self.__class__.__name__,
            "publishedFileType": 459,  # 459 = Proxy Rig
            "upstream": instance.data.get("usedRefs", [])
        }
        publish_path = assemble_publish_path(
            extraction_data_dict,
            instance.data.get("versionStreamFields") or {},
            instance.context.data.get(VERSION_NUMBER),
            "rig",
            lod,
        )
        extraction_data_dict[PUBLISH_PATH] = publish_path
        instance.data["extractionData"].append(extraction_data_dict)
        master_rig_instance.data["versionStreamFields"]["upstream"] = upstream_field + [publish_path]
        self.log.info(
            "Rig LOD_{0} extracted to: {1}.".format(lod, tempfile_path)
        )
        # self.execute_hooks(instance)

    def execute_hooks(self, instance):
        """Execute the configured hooks.

        Args:
            instance(pyblish.api.Instance).
        """
        hook_plugins = instance.context.data.get(
            "rig_lod_extraction_hooks", {}).get("plugins", []
                                                )
        if not hook_plugins:
            return
        self.log.info(
            "Running lod extraction hooks for {0}.".format(instance.data["lod_number"])
        )
        settings = instance.context.data["rig_lod_extraction_hooks"].get("settings", {})
        # It is not ideal but since the extractor will re-open the maya file for every
        # instance the pymel nodes will not exist anymore. To ensure a correct
        # collection for the hooks we need to collect pymel-nodes here.
        instance.data["root"] = pmc.PyNode(instance.data["rootName"])
        # ToDo: In the future we should use the rig_asset_assembly_nd here and in CollectRig from maya_pyblish_plugins.
        #   That would give rigging more control and would unify the collection.
        maya_pyblish_rig_utils.collect_rig_container_content(instance)
        instance.data["meshes"] = self.get_mdl_nodes(instance)
        instance.data["joints"] = maya_skin.bind_joints(instance.data["meshes"])
        for plugin in hook_plugins:
            plugin_settings = settings.get(plugin.__name__, {})
            filters = plugin_settings.get("lod_filters", [])
            self.log.info("Processing hook plugin: {0}.".format(plugin.__name__))
            if filters and int(instance.data["lod_number"]) not in filters:
                return
            if plugin_settings.get("run_as_hook"):
                self.log.debug("Running plugin as hook.")
                plugin_instance = plugin(run_as_hook=True)
                plugin_instance.process(instance)
            else:
                self.log.debug("Running plugin regular.")
                plugin_instance = plugin()
                plugin_instance.process(instance)

    def get_mdl_nodes(self, instance):
        """Get all descendants nodes under provided model roots.

        Args:
            instance (pyblish.plugin.Instance): The current instance

        Returns:
            `list`: List of descendants under root nodes.

        """
        all_descendants = []
        root = instance.data["root"]
        model_assets = [
            pxo_asset
            for pxo_asset in root.getChildren(allDescendents=True, type="pxoAsset")
            if pxo_asset.pxo_asset_type.get(asString=True) == "model"
        ]
        for pxoAsset in model_assets:
            mdl_root_descendants = pxoAsset.listRelatives(ad=True, ni=True)
            if not mdl_root_descendants:
                self.log.warning(
                    "{0} has no descendants, nothing to publish".format(pxoAsset.nodeName())
                )
                continue
            all_descendants.extend(mdl_root_descendants)
        return all_descendants
