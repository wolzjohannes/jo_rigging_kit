# Import build-in modules
import os
import logging

# Import third-party modules
from future import standard_library
import pymel.core as pmc
import maya_scene_io
from maya_scene_io.paths import get_temp_path
from pixo_paths import normalize

# Import local modules
from pxo_rigging_kit.maya_utils import paths_utils
from pxo_rigging_kit.maya_utils import pymel_utils
from pxo_rigging_kit.maya_utils import scene_utils
from pxo_rigging_kit.maya_utils import attributes_utils
from pxo_rigging_kit.maya_utils import decorators

#######################################################
# GLOBALS
#######################################################

MODEL_ASSET_SUB_CONTAINER_NAME = (
    pymel_utils.PxoContainerRigBaseNode.MODEL_ASSET_SUB_CONTAINER_NAME
)
RIG_SUB_CONTAINER_NAME = (
    pymel_utils.PxoContainerRigBaseNode.RIG_SUB_CONTAINER_NAME
)
JNT_ORG_GRP_NAME = "jnt_org"
DECORATORS = decorators.Decorators()
standard_library.install_aliases()
_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)

#######################################################
# FUNCTIONS
#######################################################


def get_rig_assets():
    """
    Will get the rig assets form the scene

    Returns:
        List: All found rig assets.

    """
    result = []
    pxo_asset_nodes = [
        node
        for node in pmc.ls(type="pxoAsset")
        if node.pxo_asset_type.get() is 2
    ]
    for node in pxo_asset_nodes:
        root_nd = node.getParent()
        if root_nd:
            if root_nd.nodeType() == "proxyReferenceAsset":
                result.append(root_nd)
            else:
                result.append(node)
        else:
            result.append(node)
    return result


def _get_asset_name(root_nd: pmc.PyNode):
    """
    Get the asset name for root node.

    Args:
        root_nd(pmc.PyNode()): The rig root node.

    Returns:
        String: The asset name.

    """
    if root_nd.nodeType() == "proxyReferenceAsset":
        root_nd = root_nd.getChildren()[0]
    return root_nd.pxo_asset_name.get()


def get_export_nodes(root_node: pmc.PyNode):
    """
    Get all needed export nodes.

    Args:
        root_nd(pmc.PyNode()): The rig root node.

    Returns:
        List: List of strings.

    """
    container_node = root_node.getChildren(type="dagContainer")
    if root_node.nodeType() == "proxyReferenceAsset":
        pxo_asset_node = root_node.getChildren()[0]
        container_node = pxo_asset_node.getChildren()
    container_node = container_node[0]
    model_con = container_node.attr(MODEL_ASSET_SUB_CONTAINER_NAME).get()
    rig_con = container_node.attr(RIG_SUB_CONTAINER_NAME).get()
    model_root_nodes = model_con.getChildren()
    jnt_org_grp = [
        node
        for node in rig_con.getChildren()[0].getChildren()
        if JNT_ORG_GRP_NAME in node.name(long=None)
    ][0]
    return [str(node.name()) for node in model_root_nodes + [jnt_org_grp]]


def export_fbx(
    scene_name: str,
    time_range: list,
    export_nodes: list,
    export_path: str = None,
    asset_name: str = "",
):
    """
    Export the exported_nodes as fbx.

    Args:
        scene_name(str): The sceneName.
        time_range(list): List of integer for min and max range.
        export_nodes(list): Names of the exported nodes.
        export_path(str): The export path with the name of the result file.
                          If None will be exported to the shot_task "cache" folder.
                          With the name o fthe current file.
                          Default is None.
        asset_name(str): The asset name for the export paths.
                         Will just be used if the export_path flag is not used.

    """
    if not export_path:
        path = paths_utils.get_project_paths(scene_name, "shot_task", "cache")
        path = os.path.join(path, "fbx")
        if not os.path.exists(path):
            os.mkdir(path)
        file_name = os.path.basename(scene_name).split(".")[0]
        file_name = f"{file_name}{asset_name.upper()}"
        export_path = normalize(os.path.join(path, file_name))
    options = {
        "FBXExportBakeComplexAnimation": True,
        "FBXExportBakeComplexStart": time_range[0],
        "FBXExportBakeComplexEnd": time_range[1],
        "FBXExportConstraints": False,
        "FBXExportInputConnections": False,
        "FBXExportShapes": True,
        "FBXExportSkeletonDefinitions": True,
        "FBXExportSkins": True,
        "FBXExportInAscii": True,
    }
    maya_scene_io.export_fbx(export_path, export_nodes, options)
    _LOGGER.info(f"Asset exported to: {os.path.split(export_path)[0]}")


def _create_no_worfile():
    """
    Swap the current file into a NON WORKFILE.
    """
    temp_path = get_temp_path(".mb")
    temp_file = normalize(os.path.join(temp_path, "NO_WORKFILE.mb"))
    pmc.renameFile("NO_WORKFILE")
    pmc.exportAll(temp_file)


def _serial_fbx_export(
    current_scene_name: str, rig_root_nodes: list, time_range: list
):
    """
    Will export ich asset in serial as fbx format.

    Args:
        current_scene_name(str): The current scene name.
        rig_root_nodes(list): List of pmc.PyNodes()
        time_range(list): List of integers for min and max.

    """
    for rig_root_nd in rig_root_nodes:
        export_nodes = get_export_nodes(rig_root_nd)
        asset_name = _get_asset_name(rig_root_nd)
        fbx_grp = pmc.createNode("transform", n=f"{asset_name}_fbx_grp")
        pmc.parent(export_nodes, fbx_grp)
        for node in fbx_grp.getChildren(ad=True, type="joint"):
            attributes_utils.unlock_attributes(node)
        for node in fbx_grp.getChildren():
            node.visibility.disconnect()
            node.visibility.set(1)
            node.overrideEnabled.set(0)
        export_fbx(
            current_scene_name,
            time_range,
            [fbx_grp.name()],
            asset_name=asset_name,
        )


# DECORATORS.refresh_suspended()
# DECORATORS.dg_evaluation()
def execute_fbx_export(rig_root_nodes, time_range, safety_save=True):
    """
    Will execute the fbx export process.

    Args:
        rig_root_nodes(list): List of pmc.PyNodes()
        time_range(list): List of integers for min and max.
        safety_save(bool): Will enable/disable the saving of the current working file.
                           Default is True

    """
    if not rig_root_nodes:
        raise ValueError("No rig root nodes nodes given.")
    current_scene_name = pmc.sceneName()
    if safety_save:
        pmc.saveFile(force=True, type="mayaAscii")
    _create_no_worfile()
    scene_utils.import_references()
    _serial_fbx_export(current_scene_name, rig_root_nodes, time_range)
