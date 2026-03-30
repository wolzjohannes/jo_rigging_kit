"""Extract rig lod from master rig.

Requires:
    instance.data["lod_number"]
    instance.context.data["extractionData"]
    instance.data["AnimControllerInterfaceAttributes"]
    families = ["lod_rig"]

Notes:
    This has to be placed after the ExtractRigMB plugin.
    Because we want all pre pyblish plugins happen before.
    So all LODs are the same.
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

# Import third-party modules
from future import standard_library
from maya_scene_io.paths import get_temp_path
from pixo_pyblish import plugin_instances
from pixo_pyblish.plugins.integrate_file import PUBLISH_PATH
from pixo_pyblish.plugins.integrate_file import VERSION_NUMBER
from pixo_pyblish.plugins.integrate_file import assemble_publish_path
from pyblish import api as pyblish_api
import pymel.core as pmc

# Import local modules
from pxo_rigging_kit.maya_utils import dag_utils
from pxo_rigging_kit.maya_utils import lod_utils
from pxo_rigging_kit.maya_utils.rigging import rig_utils

try:
    # Import built-in modules
    from importlib import reload
except:
    pass
reload(rig_utils)

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
            context (pyblish.plugin.Context): Context object that contains information
                about the current context to process on.

        """
        lod = instance.data["lod_number"]
        # Here we get the lod data again because the data can change a lot during all pyblish plugins from before.
        lod_set_data = lod_utils.get_lod_data_dict(True, True)
        # fall out if no lod data exist for given lod number.
        if not any(lod_set_data["lods"][lod].values()):
            self.log.info(
                "No LOD data exist for {}. Will skip.".format(instance.name)
            )
            return
        tempfile_path = os.path.join(
            get_temp_path(".mb"), "tmpLod{}Rig.mb".format(lod)
        )
        anim_control_interface_attributes_dict = instance.data[
            "AnimControllerInterfaceAttributes"
        ]
        with pmc.UndoChunk():
            rig_utils.extract_single_rig_lod(
                lod,
                lod_set_data,
                tempfile_path,
                anim_control_interface_attributes_dict,
            )
        pmc.undo()
        ext = ".mb"
        extraction_data_dict = {
            "extractionPath": tempfile_path,
            "ext": ext,
            "plugin": self.__class__.__name__,
            "publishedFileType": 308,  # 308 = Rig
            "subname": instance.data["versionStreamFields"]["variant"],
        }
        plugin_instances.ensure_extraction_data(instance)
        publish_path = assemble_publish_path(
            extraction_data_dict,
            instance.data.get("versionStreamFields") or {},
            instance.context.data.get(VERSION_NUMBER),
            "rig",
            lod,
        )
        extraction_data_dict[PUBLISH_PATH] = publish_path
        instance.data["extractionData"].append(extraction_data_dict)
        self.log.info(
            "Rig LOD_{0} extracted to: {1}.".format(lod, tempfile_path)
        )