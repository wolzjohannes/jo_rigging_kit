"""Collect all lod sets from the scene.
Creates for each LOD set an lod_rig instance with a custom pxoContext.
These will be used later in the extract rig LOD extractor

Notes:
    Used at the end of CollectRig plugin.
    Requires the CollectRig plugin as it references context data `extractionPath`
    which gets collected by the CollectRig plugin.

"""

# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Import built-in modules
import os
import copy

# Import third-party modules
from maya_scene_io.paths import get_temp_path
from maya_scene_io.references import collect_used_refs
from future import standard_library
from pixo_pyblish import register
from pyblish import api as pyblish_api
import pymel.core as pmc

# Import local modules
from pxo_rigging_kit.maya_utils import lod_utils
from pxo_rigging_kit import core

standard_library.install_aliases()


class CollectRigLodSets(pyblish_api.ContextPlugin):
    """Discover and collect all LOD object set data in the scene.
    And creates a instance and pxoContext for each found LOD object set"""

    offset = 0.48
    order = pyblish_api.CollectorOrder + offset
    label = "Collect Rig LOD Sets"
    families = ["rig"]
    hosts = ["maya"]
    targets = ["local"]
    extraction_hook_set = "pxo_rigging_kit_lod_extraction_hook"
    lod_extraction_hooks_settings_name = "lod_extraction_hooks_settings"

    def process(self, context):
        """Collect Rig LOD Sets and register them in pyblish.

        Args:
            context (pyblish.api.context): Context object that contains information
                                           about the current context to process on.

        Raises:
            Exception: If no lod object sets exist.

        """
        try:
            lod_data_dict = lod_utils.get_lod_data_dict()
        except:
            self.log.info("No rig LOD object sets found in the scene. Rig seems not to be a LOD rig.")
            return
        anim_controller_interface = self.get_data(context, "AnimControllerInterface")

        anim_controller_interface_attributes = self.get_data(context,"AnimControllerInterfaceAttributes")

        version_stream_field = self.get_data(context,"versionStreamFields")
        # We need the path to the master rig extarction because the LOD extraction
        # plugin will always open this file for the extarction process.
        rig_file = self.get_data(context,"extractionPath")
        master_instance = context[0]
        for lod, lod_dict in (sorted(lod_data_dict["lods"].items())):
            lod = str(lod)
            if not any(lod_dict.values()):
                self.log.info("No lod data specified in LOD_{} object set.".format(lod))
                return
            lowest_lod = lod_dict["lowest_lod"]
            highest_lod = lod_dict["highest_lod"]
            lod_name = lod_dict["lod_name"]
            lod_master = lod_dict["lod_master"]
            if highest_lod:
                lod_name = "high"
            if lowest_lod:
                lod_name = "proxy"
            if lod_master:
                lod_name = "master"
            sg_usage = f"rig-lod-{lod}-{lod_name}"
            instance = context.create_instance("LOD_{}".format(lod), family="lod_rig")
            instance.data["master_instance"] = master_instance
            instance.data["label"] = "LOD_{}".format(lod)
            instance.data["lod_number"] = lod
            instance.data["create_shotgun_version"] = False
            instance.data["pluginSource"] = self.__class__.__name__
            instance.data["versionStreamFields"] = copy.copy(version_stream_field)
            instance.data["versionStreamFields"]["variant"] = "rig{0}".format(lod)
            instance.data["versionStreamFields"]["usage"] = sg_usage
            instance.data["rig_file"] = rig_file
            instance.data["extractionPath"] = os.path.join(get_temp_path(".mb"), "tmpLod{}Rig.mb".format(lod))
            instance.data["AnimControllerInterface"] = anim_controller_interface
            instance.data["AnimControllerInterfaceAttributes"] = anim_controller_interface_attributes
            instance.data["pxoContext"] = self.get_rig_lod_context(context, lod)
            # To find the references used by a lod, we must expand the nested object
            # sets, which is why there's a cmds.set inside of itself here.
            lod_nodes = pmc.listRelatives(
                pmc.sets(pmc.sets(lod_data_dict["lod_sets"][int(lod)], query=True), query=True),
                allDescendents=True
            )
            # The 3D built CollectRefs runs before this plugin, so we have to imitate it here
            # to assist tracking of upstreams during extraction.
            instance.data["usedRefs"] = {
                ref.fileName(resolvedName=True, includePath=False, includeCopyNumber=False)
                for ref in collect_used_refs(lod_nodes)
            }
            instance.data["rootName"] = master_instance.data.get("root").longName()
        self.get_lod_extraction_hooks(context)

    def get_data(self, context, name):
        """
        Looking for existing instance of 'name' in context.data

        Args:
            context: The context for the current processing instance.
            name: name of the targeted data

        Returns:
            data: targeted data found in context

        """

        data = None
        for instance in context:
            if instance.data.get(name, None):
                data = instance.data.get(name, None)
        return data

    def get_rig_lod_context(self, context, lod_number):
        """Get rig context for given rig lod number.

        This context uses the same environment as our current environment.

        Args:
            context (pyblish.plugin.Context): The Context object to update.
            lod_number(str): The rig lod number.

        Returns:
            pixo_context.Context: A generated rig lod context.

        """
        lod_rig_context = context.data["pxoContext"].clone()
        # # Must ignore 'WPS125 Found builtin shadowing: type' as this is how pixo_context
        # # names the attribute and we need to set it here.
        lod_rig_context.task.type = "rig"  # noqa: WPS125
        lod_rig_context.task.partname = lod_number
        # We comment out lod_rig_context.task.sgid so we are not generating a task for this output.
        # Because there is no need to generate it for an LOD rig because it is just an output from the master rig task.
        # And will not  be
        # lod_rig_context.task.sgid = get_rig_lod_sgid(lod_number)
        # Still need to set the task.name although we have already updated the type and
        # part name. Otherwise, the str represenation of the context would still refer
        # to the current task's context.
        lod_rig_context.task.name = lod_number# noqa: WPS125

        return lod_rig_context

    def get_lod_extraction_hooks(self, context):
        """Collects the configured extraction hooks."""
        try:
            configured_plugins = register.get_configured_plugin_names(
                self.extraction_hook_set
            )
        except KeyError:
            self.log.debug(
                'The set "{0}" is not set up.'.format(self.extraction_hook_set)
            )
            return
        try:
            settings = core.get_config(self.lod_extraction_hooks_settings_name)
        except ValueError:
            settings = {}
            self.log.debug(
                'No settings found in "{0}"'.format(
                    self.lod_extraction_hooks_settings_name
                )
            )
        hook_config = {
            "plugins": register.get_plugins(configured_plugins),
            "settings": settings,
        }
        context.data["rig_lod_extraction_hooks"] = hook_config
