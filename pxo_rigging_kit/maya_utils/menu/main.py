# Author:     Johannes Wolz / Lead Rigging TD

"""
Utility code for maya menu integration.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Import built-in modules
from builtins import str
from importlib import reload

# Import python standart import
import logging
import pprint
import site
import os
import pathlib

# Import third-party modules
from future import standard_library
import pymel.core as pmc

# Import local modules
from pxo_rigging_kit import constants
from pxo_rigging_kit.maya_utils import assembly_utils
from pxo_rigging_kit.maya_utils import dag_utils
from pxo_rigging_kit.maya_utils import exceptions
from pxo_rigging_kit.maya_utils import lod_utils
from pxo_rigging_kit.maya_utils import mesh_utils
from pxo_rigging_kit.maya_utils import paths_utils
from pxo_rigging_kit.maya_utils import pymel_utils
from pxo_rigging_kit.maya_utils.deformers import blendshape_utils

from pxo_rigging_kit.maya_utils.deformers.utilities import skincluster_layering
from pxo_rigging_kit.maya_utils.deformers.utilities import skincluster_precision_mode
from pxo_rigging_kit.maya_utils.deformers.utilities.commandline_shortcuts import skincluster_import_newest, \
    skincluster_import_selected, skincluster_transfer_selected, skincluster_prune_selected

from pxo_rigging_kit.maya_utils.guis import blendshape_utils_gui
from pxo_rigging_kit.maya_utils.guis import hik_save_char_description_gui
from pxo_rigging_kit.maya_utils.guis import hik_save_tpose_ik_fk_match_data_gui
from pxo_rigging_kit.maya_utils.guis import rig_meta_data_gui

from pxo_rigging_kit.maya_utils.guis import guides_manager_gui
from pxo_rigging_kit.maya_utils.guis import guide_transfer_gui


from pxo_rigging_kit.maya_utils.guis.tool_skinio_gui import show_skinio_window

from pxo_rigging_kit.maya_utils.mgear import guide_utils
from pxo_rigging_kit.maya_utils.rigging import mocap_utils
from pxo_rigging_kit.maya_utils.rigging import rig_utils
from pxo_rigging_kit.maya_utils.rigging.mocap_utils import (
    HIK_TARGET_RIG_CHAR_DESC_NAME,
)

from pxo_rigging_kit.maya_utils.guis import tool_controller_gui
from pxo_rigging_kit.maya_utils.guis import tool_renamer_gui

reload(guides_manager_gui)
reload(blendshape_utils)
reload(blendshape_utils_gui)

standard_library.install_aliases()

##########################################################
# GLOBALS
##########################################################

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.INFO)


##########################################################
# FUNCTIONS
##########################################################
def window_controller_gui():
    from pxo_rigging_kit.maya_utils.guis import tool_controller_gui
    import importlib
    importlib.reload(tool_controller_gui)

    tool_controller_gui.show()


def window_renamer_gui():
    from pxo_rigging_kit.maya_utils.guis import tool_renamer_gui
    import importlib
    importlib.reload(tool_renamer_gui)

    tool_renamer_gui.show()


def window_script_browser():
    """
    Show window for save blendshape setups.
    """
    from pxo_rigging_kit.maya_utils.guis import script_browser
    import importlib
    importlib.reload(script_browser)

    script_browser.show_maya_script_browser(True)


def window_save_bshp_setup():
    """
    Show window for save blendshape setups.
    """
    main_window = blendshape_utils_gui.MainWindow()
    main_window.show()


def import_bshp_data():
    """
    Import blendshape target deltas.
    """
    start_dir = paths_utils.get_project_paths(pmc.sceneName())
    file_path = pmc.fileDialog2(
        bbo=1, spe=True, dir=start_dir, cap="Path", fm=2
    )
    if not file_path:
        return
    target_shape = None
    confirm_dialog = pmc.confirmDialog(
        title="Import bshp target deltas",
        message="Pls choose import target."
                "\nThis import will not validate or transfer mesh data."
                "\nBe sure the vertex data is the same like in the export.",
        messageAlign="left",
        button=["Selection", "Stored mesh shape", "Cancel"],
        defaultButton="Stored mesh shape",
        cancelButton="Abort",
        dismissString="Abort",
        icon="question",
    )
    if confirm_dialog == "Abort" or confirm_dialog == "Cancel":
        return
    if confirm_dialog == "Selection":
        try:
            target_shape = pmc.ls(sl=True)[0].getShape(noIntermediate=True)
        except:
            raise exceptions.MayaSelectionError(
                "No mesh geo selected or geo has no mesh shape"
            )
    blendshape_utils.import_blendshape_data(str(file_path[0]), target_shape)


def import_bshp_setup(pack=False):
    """
    Import blendshapes setup command for the maya menu.

    Args:
        pack(bool): import blendshape setup pack.

    """
    start_dir = paths_utils.get_project_paths(pmc.sceneName())
    file_path = pmc.fileDialog2(
        bbo=1, spe=True, dir=start_dir, cap="Path", fm=2
    )
    if file_path:
        file_path = str(file_path[0])
        if pack:
            blendshape_utils.import_blendshape_setup_pack(
                file_path, info_box=True
            )
        else:
            blendshape_utils.import_blendshape_setup(file_path, info_box=True)


def import_latest_bshp_setup():
    """
    Import command for the maya menu.
    Import latest blendshape setup pack found in the PXO_BSHP dir
     in the project data dir.
    """
    data_dir = paths_utils.get_project_paths(pmc.sceneName())
    blendshape_utils.import_from_PXO_BSHP_directory(data_dir, info_box=True)


def transfer_bshp_setup(disconnect_source_blendshape_ports=False):
    """
    Transfer command for the maya menu.
    Will transfer blendshape setup from selected source to target.

    Args:
        disconnect_source_blendshape_ports(bool): Enable if you want to
                                                  disconnect the weight
                                                  ports of the source
                                                  blendshape node.
    """
    selection = pmc.selected()
    source = selection[0]
    target = selection[1]
    blendshape_utils.transfer_blendshape_setup(
        source, target, True, disconnect_source_blendshape_ports, True
    )


def window_skin_cluster_setup():
    """
    Show window for skin cluster setups.
    """

    show_skinio_window()


def import_skin_cluster_setup():
    """
    Import skin cluster setup command for the maya menu.

    """
    skincluster_import_selected()


def prune_selected_skin_clusters():
    """
    Import skin cluster setup command for the maya menu.

    """
    skincluster_prune_selected()


def import_latest_skin_cluster_setup():
    """
    Import command for the maya menu.
    Import latest skin cluster pack found in the [constants.PXO_FILEPATH_SKIN] dir in the project data dir.
    """
    skincluster_import_newest()


def compare_meshes():
    """
    Compare mesh command for the maya menu.
    Compare meshes in vertex count, poly count,
    vertex IDS and world positions of each vertice.
    """
    selection = pmc.selected()
    source_mesh = selection[0].getShape().name()
    target_mesh = selection[1].getShape().name()
    result = mesh_utils.check_mesh_data(
        source_mesh, target_mesh, True, True, True, True
    )
    _LOGGER.info(pprint.pformat(result))


def create_mdl_asset_hierarchy_template(pxo_asset_node=True):
    """
    Create mdl hierarchy structure as template.

    Args:
        pxo_asset_node(bool): Enable new pxoAsset node. Default is True

    """
    assembly_utils.create_mdl_asset_hierarchy(
        pmc.sceneName(), pxo_asset_node=pxo_asset_node
    )


def import_latest_sg_hand_off_model_publish(reference=False):
    """
    Import latest model publish which hand off flagged in shotgrid.
    """
    asset_list = [
        {
            "category": None,
            "asset_name": None,
            "lod": "",
            "version_number": False,
        }
    ]
    assembly_utils.assemble_scene(
        pmc.sceneName(), asset_list, reference=reference
    )


def show_rig_meta_data_gui(root_nd):
    """
    Show the rig meta data from given rig root nd.

    Args:
        root_nd(str, pmc.PyNode): The rig root node.

    """
    if not isinstance(root_nd, pmc.PyNode):
        root_nd = pmc.PyNode(root_nd)

    root_uuid = pymel_utils.process_pxo_uuid(
        [
            constants.PXO_UUID_DICT["root"],
            constants.PXO_UUID_DICT["rig"],
            constants.PXO_UUID_DICT["container"],
        ]
    )
    if pymel_utils.get_pxo_uuid(root_nd) != root_uuid:
        raise exceptions.PxoPymelNodeClassError(
            "Selected node is no PxoContainerRigRootNode."
        )

    asset_name = root_nd.get_meta_asset_name()

    asset_assembly_nd = root_nd.get_meta_asset_assembly_node()

    meta_data = root_nd.get_data_bunch_from_bunch_ref_attr()[
        "pxo_rig_meta_data"
    ]

    asset_assembly_data = None

    if asset_assembly_nd:
        asset_assembly_data = asset_assembly_nd.get_assembly_data()

    rig_meta_data_gui.show(
        [
            {
                "asset_name": asset_name,
                "meta_data": meta_data,
                "asset_assembly_data": asset_assembly_data,
            }
        ]
    )


def rig_root_container_rmb_cmd():
    """
    Helper function for the asset context menu in maya.
    This is needed for the melWrapper.
    """
    return ("Show Rig Meta Data", "show_rig_meta_data_gui")


def show_rig_meta_data_from_scene():
    """
    Show rig meta data from all rig root nodes in the scene.
    """
    meta_data_list = []
    root_nodes = rig_utils.get_rig_containers()
    if not root_nodes:
        raise exceptions.MayaNodeNotFound("No rig root nodes found.")
    for root_nd in root_nodes:
        asset_name = root_nd.get_meta_asset_name()
        asset_assembly_nd = root_nd.get_meta_asset_assembly_node()
        meta_data = root_nd.get_data_bunch_from_bunch_ref_attr()[
            "pxo_rig_meta_data"
        ]
        asset_assembly_data = None
        if asset_assembly_nd:
            asset_assembly_data = asset_assembly_nd.get_assembly_data()
        meta_data_list.append(
            {
                "asset_name": asset_name,
                "meta_data": meta_data,
                "asset_assembly_data": asset_assembly_data,
            }
        )
    rig_meta_data_gui.show(meta_data_list)


def test_LOD_extraction(new_scene_with_lods=False, reference_lods=False):
    """
    Test the rig lod publish in current workscene.
    Will save current scene before testing.
    """
    rig_utils.extract_rig_lods(new_scene_with_lods, reference_lods)


def create_lod_sets():
    """
    Create the lod object set nodes.
    """

    lod_utils.create()


def kill_lod_sets():
    """
    Create the lod object set nodes.
    """

    lod_utils.kill()


def import_lod_sets():
    """
    Import the lod object set nodes.
    """

    lod_utils.load()


def export_lod_sets():
    """
    Export the lod object set nodes.
    """

    lod_utils.save()


def create_rig_meta_node():
    """
    Create the rig meta node.
    """

    selection = pmc.ls(sl=True)

    if selection:
        selection = selection[0]

    rig_utils.create_rig_meta_node(selection)


def hik_add_hik_rig_description_to_selected(type="character"):
    """
    Add the hik description to selected rig.

    Args:
        type(str): Description type.
                   Valid are ["character", "source"]

    """
    selection = pmc.ls(sl=True)

    if not selection:
        raise RuntimeError("You have to select the root node.")

    selection = selection[0]
    if not any(
            [
                dag_utils.is_root_node(selection),
                dag_utils.is_root_node(selection, "joint"),
            ]
    ):
        raise RuntimeError("Selection is no root node.")

    namespace = selection.namespace()
    data = [selection]
    data.extend(selection.getChildren(ad=True))

    if type == "character":
        mocap_utils.hik_add_target_rig_description(
            HIK_TARGET_RIG_CHAR_DESC_NAME, data, namespace=namespace
        )
    else:
        mocap_utils.hik_add_mocap_data_description(data, namespace=namespace)


def hik_import_target_rig(file_path=None):
    """
    Import target rig and add the corresponding hik description.
    Will open a maya fileDialog for directory browsing.
    Will validate the rig with hik description.
    Will validate the rig Tpose. If it is not valid will ask you
    if you want to set it.
    """
    project_path = paths_utils.get_root_path(pmc.sceneName(), "project")
    import_path = pmc.fileDialog2(
        cap="Import HIK character rig",
        fm=1,
        ds=2,
        dir=project_path,
        okc="Import",
    )
    if import_path:
        mocap_utils.hik_import_target_rig(
            HIK_TARGET_RIG_CHAR_DESC_NAME,
            import_path[0],
        )


def hik_import_mocap_data_and_connect():
    """
    Will import the mocap data.
    Will open a maya fileDialog for directory browsing.
    Add the corresponding hik description and connect it with target rig.
    Will validate the mocap data with the hik description.
    """

    project_path = paths_utils.get_root_path(pmc.sceneName(), "project")
    zero_out_joints_rotate = pmc.confirmBox(
        "Set MoCap to T-Pose",
        "Do you want to zero out rotate values of the MoCap rig?",
    )
    snap_mocap_hip_to_target_hip = pmc.confirmBox(
        "Snap MoCap rig root to target root",
        "Do you want to snap the MoCap rig root to target rig root?",
    )
    import_path = pmc.fileDialog2(
        cap="Import MoCap data", fm=1, ds=2, dir=project_path, okc="Import"
    )

    if not import_path:
        return

    mocap_utils.hik_import_and_connect_mocap(
        HIK_TARGET_RIG_CHAR_DESC_NAME,
        import_path[0],
        zero_out_joint_rotates=zero_out_joints_rotate,
        snap_mocap_hip_to_target_hip=snap_mocap_hip_to_target_hip,
    )


def hik_import_target_rig_and_connect_mocap():
    """
    Import target rig and add the corresponding hik description.
    Will open a maya fileDialog for directory browsing.
    Will validate the rig with hik description.
    If you are using the mgear captainAverage rig
    it will ask you if you want to se it to Tpose.
    Will import the mocap data.
    Will open a maya fileDialog for directory browsing.
    Add the corresponding hik description and connect it with target rig.
    Will validate the mocap data with the hik description.
    """
    hik_import_target_rig()
    hik_import_mocap_data_and_connect()

    bake = pmc.confirmBox(
        "Bake to target rig", "Do you want to bake result to target rig?"
    )
    if not bake:
        return

    hik_bake_mocap_to_target_rig()


def hik_save_hik_description():
    """
    Save the target_rig and mocap_rig hik description
    as json file on project or scene level.
    """
    main_window = hik_save_char_description_gui.MainWindow()
    main_window.show()


def hik_bake_mocap_to_target_rig():
    """
    Bake the mocap data to target rig.
    Will ask if you want to clean scene from all HIK notes.
    Will ask for ik to fk matching of the target rig.
    """
    clean_scene = pmc.confirmBox(
        "Clean Scene", "Do want to clean the scene after bake?"
    )
    ik_fk_match = pmc.confirmBox(
        "IK FK Match", "Do want to match ik to the fk controls?"
    )
    mocap_utils.hik_bake_mocap_to_target_rig(clean_scene=clean_scene)
    if not ik_fk_match:
        return

    mocap_utils.hik_mgear_bake_fk_to_ik()


def hik_set_rig_tpose(limb_type="arm"):
    """
    Set the hik target rig to Tpose.

    Args:
        limb_type(str): The limb type.
                        Valid values are ["arm", "leg"].
                        Default is "arm"
    """
    mocap_utils.hik_set_tpose(limb_type=limb_type)


def hik_save_tpose_and_ik_fk_match_data():
    """
    Open the save_Tpose_and_ik_fk_match_data gui.
    """
    window_ = hik_save_tpose_ik_fk_match_data_gui.MainWindow()
    window_.show()


def create_rig_container_hierarchy(advanced=False):
    """
    Create the rig container hierarchy based on the asset in the scene.

    Args:
        advanced(bool): Will take non dag container
                        instead of the normal container.
                        A non dag container has no transform.
                        But it can zip all kind of maya nodes.
    """
    rig_utils.create_rig_root_hierarchy(advanced)


def close_open_rig_container_hierarchy():
    """
    Close or open the rig container hierarchy.
    """
    selection = pmc.ls(sl=True)

    if not selection:
        exceptions.MayaSelectionError(
            "You have to select the rig root container."
        )

    rig_root_containers = rig_utils.get_rig_containers()

    selection = selection[0]

    if selection not in rig_root_containers:
        raise exceptions.MayaSelectionError(
            "Your selection is not a valid PxoRootRigContainer"
        )

    sub_containers = selection.getSubcontainers()

    current_black_box_value = all(
        node.blackBox.get() for node in sub_containers
    )

    if not current_black_box_value:
        current_black_box_value = True
    else:
        current_black_box_value = False

    rig_utils.close_open_rig_root_nd(selection, current_black_box_value)


def create_asset_assembly_node():
    """
    Create asset assembly node in the scene.
    """
    assembly_utils.create_asset_assembly_node_from_scene()


def _check_selection_about_rig_containers():
    """
    Will check if rig container in selection or not.
    """
    selection = pmc.ls(sl=True)

    if len(selection) <= 1:
        exceptions.MayaSelectionError(
            "You have to select a bunch of objects."
            "The last object of the selection has"
            " to be the container node."
        )
    container = selection[-1]
    rig_containers = (
            rig_utils.get_rig_containers() + rig_utils.get_rig_containers("sub")
    )
    if container not in rig_containers:
        raise exceptions.MayaSelectionError(
            "Your selection has not a valid PxoRigContainer"
        )
    return container, selection[0:-1]


def add_nodes_to_selected_rig_container():
    """
    Add selected nodes to an rig container.
    The last object in your selection
    """
    selection = _check_selection_about_rig_containers()
    selection[0].add_nodes(selection[1])


def publish_selected_nodes_in_rig_container():
    """
    Publish selected nodes in given container node.
    """
    selection = _check_selection_about_rig_containers()
    selection[0].publish_nodes(selection[1])


def transfer_skinclusters():
    """
    Creates a tag on selection for skin cluster save mode.
    """
    skincluster_transfer_selected()


def add_tags_for_skin_cluster_precision_mode_master():
    """
    Creates a tag on selection for skin cluster save mode.
    """
    skincluster_precision_mode.set_world_precision_sys_root_ctrl()


def remove_tags_for_skin_cluster_precision_mode_master():
    """
    Removes all tags in scene referencing skin cluster save mode.
    """
    skincluster_precision_mode.remove_precision_mode_tagged_nodes()


def apply_skin_cluster_precision_mode():
    """
    Applies the Skin Cluster Save Mode.
    """
    skincluster_precision_mode.correct_rig_world_precision_issue()


def revert_skin_cluster_precision_mode_behaviour():
    """
    Reverts the Skin Cluster Save Mode without removing the setup.
    """
    skincluster_precision_mode.revert_rig_world_precision_issue(remove_tagging=False)


def remove_skin_cluster_precision_mode_system():
    """
    Reverts the Skin Cluster Save Mode and removes the setup.
    """
    skincluster_precision_mode.revert_rig_world_precision_issue(remove_tagging=True)


def save_skin_cluster_precision_mode_system():
    """
    Saves the Skin Cluster Save Mode setup.
    """
    skincluster_precision_mode.save()


def load_skin_cluster_precision_mode_system():
    """
    Loads the Skin Cluster Save Mode setup.
    """
    skincluster_precision_mode.load()


def hide_non_dag_history():
    """
    Hides the non dag history for all non dag objects in the scene.
    """
    rig_utils.hide_non_dag_history()


def show_non_dag_history():
    """
    Reveals the non dag history for all non dag objects in the scene.
    """
    rig_utils.show_non_dag_history()


def publish_rig_guides(safe_mode=True):
    """
    Publish the current rig guides in the scene.

    Args:
        safe_mode(bool): Save and rename the current file before execute the publishing steps.
                         This will prevent a corruption of the source scene.

    """
    guide_utils.publish_guides(safe_mode)


def import_latest_rig_guides():
    """
    Imports the latest rig guides for current asset.
    """
    guide_utils.load_latest_guides()


def create_skin_layers_from_selection():
    """
    Creates skinlayer meshes and sets from selection
    """
    skincluster_layering.create_skin_merge_sets_from_selection()


def create_skincluster_stack():
    """
    Create the actual skin cluster stack based on the existing skinlyer data in the scene.
    """
    skincluster_layering.create_skincluster_stacks()


def save_skinlayer_data():
    """
    Save the skinlayer data of existing
    """
    skincluster_layering.save_skinlayer_data()


def load_skinlayer_data():
    """
    Load the skinlayer data for current asset.
    """
    skincluster_layering.load_skinlayer_data()



def show_guides_template_manager():
    """
    Open up the guides template manager.
    """
    guides_manager_gui.show()


def show_guides_transfer():
    """
    Open the transfer guides ui
    """
    guide_transfer_gui.show()


def create_simple_rigs():
    """
    Creates simple rigs based on the selected mdl root nodes.
    """
    selection = pmc.ls(sl=True)
    for node in selection:
        rig_utils.create_simple_pxoAsset_rig([node])


def create_container_simple_rig():
    """
    Creates a rig for multiple selected proxy Reference nodes.
    """
    selection = pmc.ls(sl=True)
    rig_utils.create_simple_pxoAsset_rig(selection)


def show_controller_tool():
    tool_controller_gui.show()


def show_renamer_tool():
    tool_renamer_gui.show()
