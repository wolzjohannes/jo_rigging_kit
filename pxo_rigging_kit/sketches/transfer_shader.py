import os

import pymel.core as pmc

# Import local modules
from pxo_rigging_kit.maya_utils import attributes_utils
from pxo_rigging_kit.maya_utils import decorators
from pxo_rigging_kit.maya_utils import paths_utils
from pxo_rigging_kit.maya_utils import scene_utils
import pixo_paths
from maya_scene_io.paths import get_temp_path
from maya_scene_io import export_scene

#######################################################
# GLOBALS
#######################################################

DECORATORS = decorators.Decorators()
PUBLISH_OPTIONS = {
    "force": True,
    "type": "mayaBinary",
    "shader": True,
    "channels": True,
    "constraints": False,
    "expressions": False,
}

#######################################################
# FUNCTIONS
#######################################################

def transfer_src_shd_to_trgt(source, target_nd):
    """
    Will transfer exsiting shader tree to target geo.
    Source objects is the first selected one. All others are the targets.
    If a uvChosser setup is included it will make the corresponding connections.
    But we always assume that the uvSet[1] is the oneUdim set in every object.
    """
    source_shape = source.getShape()
    shading_engine = [node for node in source_shape.connections() if "initialShadingGroup" not in node.nodeName()]
    try:
        shading_engine = shading_engine[0]
    except:
        raise Exception(f"No shading engine found for {source_shape}")
    target_shape = target_nd.getShape()
    pmc.select(target_nd)
    pmc.hyperShade(assign=shading_engine)
    uv_chosser_nodes = shading_engine.listHistory(type="uvChooser")
    for uv_ch_nd in uv_chosser_nodes:
        index = attributes_utils.get_next_free_array_index(uv_ch_nd.uvSets.name(), 0)
        target_shape.uvSet[1].uvSetName.connect(uv_ch_nd.attr(f"uvSets[{index}]"))

@DECORATORS.undo
def transfer_src_shd_to_mutliple_trgt():
    """
    Will transfer exsiting shader tree to multiple object by selection.
    """
    selection = pmc.selected()
    source_nd = selection[0]
    target_nodes = selection[1:]
    for target_nd in target_nodes:
        transfer_src_shd_to_trgt(source_nd, target_nd)

@DECORATORS.undo    
def transfer_shd_by_node_name(source_nodes, target_namespace="", replace_tuples_list=None):
    """
    Will transfer the shaders for given source nodes objects to others by name.

    Args:
        source_nodes(list): The given source nodes with the source shaders.
        target_namespace(str): The namespaces for the target object names.
                               That means if your target objects has a namespace you need to add this here with a ":".
                               For example like this "dra_02:".
                               Default is an empty string as no namespace.
        replace_tuples_list(list): The list filled with tuples. You can use that if your target objects has additional
                                   words in the names.
                                   For example, we use this for the "_proxy_" and "_render_" meshes.
                                   Examples: [("_proxy_", "_render_")]
    """
    for src_nd in source_nodes:
        target_nd =f"{target_namespace}{src_nd.name(long=None)}"
        if replace_tuples_list:
            for replace_tpl in replace_tuples_list:
                target_nd = target_nd.replace(replace_tpl[0], replace_tpl[1])
        target_nd = pmc.PyNode(target_nd)
        transfer_src_shd_to_trgt(src_nd, target_nd)
        
def publish():
    """
    Will create a simple publish for the texture delivery into the rigs.
    Will create a _publish folder into the asset_previs directory.
    """
    asset_task_root = paths_utils.get_root_path(pmc.sceneName(), "asset_task")
    publish_folder = pixo_paths.normalize(os.path.join(asset_task_root, "_publish"))
    if not os.path.exists(publish_folder):
        os.mkdir(publish_folder)
    publish_path = os.path.join(publish_folder, os.path.basename(pmc.sceneName()).split(".")[0])
    pmc.saveFile(force=True, type="mayaAscii")
    temp_path = get_temp_path(".mb")
    temp_file = pixo_paths.normalize(
        os.path.join(temp_path, "NO_WORKFILE.mb")
    )
    pmc.renameFile("NO_WORKFILE")
    pmc.exportAll(temp_file)
    scene_utils.import_references()
    pmc.delete(pmc.PyNode("delete_on_publish").members())
    scene_utils.delete_unkown_plugins()
    scene_utils.delete_unkown_nodes()
    pmc.select(pmc.ls(assemblies=True))
    export_scene.export_type(publish_path, "mb", None, PUBLISH_OPTIONS, {})
    pmc.informBox("Simple SHD publisher", f"Published succesfully to:\n {publish_path}")

#Uncomment these and use it if you need to transfer shaders from one selected object to another selected object
# transfer_src_shd_to_mutliple_trgt()

# Uncomment these and use it if you need to tarnsfer shader from objects to the other objects by name.
# transfer_shd_by_node_name(pmc.selected(), "", [("tes_01", "tes_02"),("_proxy_", "_render_")])

# Uncomment these and use it to publish your scene
publish()
