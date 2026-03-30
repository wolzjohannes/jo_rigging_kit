# Author:     Johannes Wolz / Lead Rigging TD

"""
Utils code for rigging.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library

# Import built-in modules
from builtins import int
from builtins import range
from builtins import round
from builtins import str
from builtins import object
from typing import Optional, Union

from past.utils import old_div
from statistics import mean
import logging
import json
import os
import pprint
from itertools import chain
from itertools import zip_longest
from collections import namedtuple
import re
from importlib import reload
from pprint import pprint

# Import third-party modules
import maya.cmds as cmds
from maya_scene_io import export_scene
from maya_scene_io.paths import get_temp_path

from mgear.core import anim_utils
import pymel.core as pmc
from pymel.core import mel
import pymel.core.datatypes as dt
from maya_proxy_node import asset_node
from maya_proxy_node import types
from maya_proxy_node import interaction
from maya_tagging import tagging_utils
from maya.internal.nodes.proximitywrap.node_interface import NodeInterface
from maya_tagging.constants import TAG_EXPORT_ANIMATION
from mgear.shifter import guide_manager
from mgear.rigbits import rbf_io
from mgear.rigbits import rbf_node
from mgear.rigbits.rbf_manager2 import rbf_manager_ui

# Import local modules
from pxo_rigging_kit import constants
from pxo_rigging_kit.maya_utils import attributes_utils
from pxo_rigging_kit.maya_utils import decorators
from pxo_rigging_kit.maya_utils import exceptions
from pxo_rigging_kit.maya_utils import lod_utils
from pxo_rigging_kit.maya_utils import openmaya_utils
from pxo_rigging_kit.maya_utils import paths_utils
from pxo_rigging_kit.maya_utils import pymel_utils
from pxo_rigging_kit.maya_utils import scene_utils
# from pxo_rigging_kit.maya_utils.dag_utils import get_deform_shape
# from pxo_rigging_kit.maya_utils.dag_utils  create_buffer_groups
from pxo_rigging_kit.maya_utils import dag_utils


from pxo_rigging_kit.maya_utils.EWAW_rs import matrix_maths, node
from pxo_rigging_kit.maya_utils.mgear import guide_utils
from pxo_rigging_kit.maya_utils import assembly_utils
from pxo_rigging_kit.maya_utils.rigging import curves_utils
from pxo_rigging_kit import string_utils



##########################################################
# GLOBALS
##########################################################


standard_library.install_aliases()

_LOGGER = logging.getLogger(f"{__name__}.py")
_LOGGER.setLevel(logging.INFO)

DECORATORS = decorators.Decorators()
DECORATORS.debug = True
DECORATORS.logger = _LOGGER

RIG_ROOT_SUB_CONTAINERS = ("MGEAR", "MODEL_ASSETS", "XTRA", "NO_TRANSFORM")

##########################################################
# FUNCTIONS
##########################################################


# This function is established for backwards compatibility
# for the old LOD workflow.
# The new rig root node will exchange that.
def create_rig_meta_node(rig_root_nd=None):
    """
    Create the rig meta node.

    Args:
        rig_root_nd(pmc.PyNode): The rig root node.
                                 Will connect meta nd and root nd via
                                 message attribute.

    Return:
        pmc.PyNode(): Rig meta node.

    """
    rig_meta_nd = pymel_utils.PxoRigMetaNode(name=constants.RIG_META_ND_NAME)
    if rig_root_nd:
        if not rig_root_nd.hasAttr(constants.RIG_META_ND_NAME):
            rig_root_nd.addAttr(constants.RIG_META_ND_NAME, typ="message")
        rig_meta_nd.set_rig_root_nd(rig_root_nd)
        rig_meta_nd.message.connect(
            rig_root_nd.attr(constants.RIG_META_ND_NAME)
        )
    return rig_meta_nd


def extract_single_rig_lod(
    lod,
    lod_set_data_dict,
    extract_path,
    rig_anim_interface_dict,
):
    """
    Extract given rig lod.

    Args:
        lod(str): The rig lod index.
        lod_set_data_dict(dict): The lod set data dict.
                                 Which specifies how the lod
                                 should look like.
        extract_path(str): The path for extraction.
        rig_anim_interface_dict(dict): This dict contains the anim
                                       controller and it animateable attributes.
                                       This is needed for the anim
                                       controls validation.

    Returns:
        String: The extract path.

    """
    _LOGGER.info("Processing LOD_{} extraction.".format(lod))
    lod_set_nodes = lod_set_data_dict.get("lod_sets", [])
    lod_sub_set_nodes = lod_set_data_dict.get("sub_sets", [])
    rig_root_container = get_rig_containers()
    if not rig_root_container:
        raise exceptions.MayaNodeNotFound("Rig root container not found.")
    rig_root_container = rig_root_container[0]
    rig_setup_sub_container = [
        node
        for node in rig_root_container.getSubcontainers()
        if node.name(long=None) == rig_root_container.RIG_SUB_CONTAINER_NAME
    ][0]
    set_data_dict = lod_set_data_dict["lods"][lod]
    set_rig_lod_meta_data(rig_root_container, lod, set_data_dict)
    rig_comp_roots = set_data_dict.get("roots", [])
    geos = set_data_dict.get("geo", [])
    dag = set_data_dict.get("dag", [])
    non_dag = set_data_dict.get("non_dag", [])
    visibility = set_data_dict.get("visibility", [])
    if rig_comp_roots:
        rig_comp_roots = [
            "*{}".format(node_name) for node_name in rig_comp_roots
        ]
        rig_comp_roots = pmc.ls(rig_comp_roots)
        rig_comp_roots = [node_name for node_name in rig_comp_roots]
        reduce_grp = reduce_rig_components(rig_comp_roots)
        reduce_grp.visibility.set(0)
        rig_setup_sub_container.add_nodes([reduce_grp])
    if visibility:
        visibility = ["*{}".format(node_str) for node_str in visibility]
        visibility = pmc.ls(visibility)
        visibility = [dag_utils.show_node(node) for node in visibility]
    delete_list = [
        node_name
        for node_name in geos
        + dag
        + non_dag
        + lod_set_nodes
        + lod_sub_set_nodes
        if pmc.objExists(node_name)
    ]
    pmc.delete(delete_list)
    pmc.mel.eval("MLdeleteUnused;")
    rig_anim_interface = get_anim_control_interface()
    missing_attributes = validate_anim_controller_interface(
        rig_anim_interface_dict, rig_anim_interface
    )
    if missing_attributes:
        pmc.select(list(missing_attributes.keys()))
    export_rig(extract_path)
    _LOGGER.info("Extracted rig LOD_{} to: {}".format(lod, extract_path))
    return extract_path


def _import_geo_references(lod_set_data_dict):
    """
    Import geo references stored in the lod set data.

    Args:
        lod_set_data_dict(dict): The lod set data dict.
                                 Which specifies how the lod
                                 should look like.
    """
    geos_list = []
    for lod in sorted(lod_set_data_dict["lods"].keys()):
        set_data_dict = lod_set_data_dict["lods"][lod]
        geos = set_data_dict.get("geo")
        geos_list.extend(geos)
    scene_utils.import_references(geos_list)


def extract_rig_lods(
    reference_lods=False, check_lods_only=False, save_before_start=True
):
    """
    Extract the rig lods to the temp folder.
    This function should be used for testing your current LOD set setup.

    Args:
        reference_lods(bool): Will reference the extracted
                              rig lods to your curent scene.
        check_lods_only(bool): Will import the extracted rig
                               lods into a new scene.
        save_before_start(bool): Save the current file before process starts.

    """
    extracted_paths = []
    current_file = pmc.sceneName()
    if save_before_start:
        pmc.saveFile(force=True, type="mayaAscii")
    pmc.renameFile("NO_WORKFILE")
    temp_path = get_temp_path(".mb")
    temp_file = os.path.join(temp_path, "NO_WORKFILE.mb")
    lod_set_data = lod_utils.get_lod_data_dict(True, True)
    scene_utils.import_references()
    rig_root_container = get_rig_containers()
    if not rig_root_container:
        raise exceptions.MayaNodeNotFound("Rig root container not found.")
    rig_root_container = rig_root_container[0]
    finish_rig_root_nd(rig_root_container)
    export_rig(temp_file)
    for lod in lod_set_data["lods"].keys():
        pmc.openFile(temp_file, force=True)
        extract_path = os.path.join(temp_path, "tmpLod{}Rig.mb".format(lod))
        lod_set_data_ = lod_utils.get_lod_data_dict(True, True)
        rig_anim_control_interface = get_anim_control_interface()
        rig_anim_interface_attributes_dict = get_anim_interface_attributes(
            rig_anim_control_interface
        )
        extract_path = extract_single_rig_lod(
            str(lod),
            lod_set_data_,
            extract_path,
            rig_anim_interface_attributes_dict,
        )
        extracted_paths.append(extract_path)
    extracted_lods = len(extracted_paths)
    if reference_lods:
        pmc.openFile(current_file, force=True)
        for x in range(extracted_lods):
            pmc.createReference(
                extracted_paths[x],
                rnn=True,
                ns=f"lod_{(extracted_lods - 1) - x}",
            )
    elif check_lods_only:
        pmc.newFile(force=True, type="mayaAscii")
        pmc.renameFile("NO_WORKFILE.ma")
        for x in range(extracted_lods):
            pmc.importFile(
                extracted_paths[x], ns="lod_{}".format((extracted_lods - 1) - x)
            )
    else:
        pmc.openFile(current_file, force=True)
    _LOGGER.info("LOD extraction successfully.")


def export_rig(path):
    """
    Export the collected rig.

    Args:
        path (string): Path for the export.

    """
    options = {
        "force": True,
        "type": "mayaBinary",
        "shader": True,
        "channels": True,
        "constraints": True,
        "expressions": True,
    }
    export_scene.export_type(path, "mb", None, options, {})


def get_anim_control_interface(as_strings=False, namespace=""):
    """
    Get all rig anim controller from scene.
    Will search about a controllers set in first place.
    If not found will take all tagged controls.

    Args:
        as_strings(bool): Gives back all controls as strings.
                          Default is False.
        namespace(str, optional): Will try to find controllers_set with
                                  given namespace.
                                  Valid value pattern is "nmsp_01:"
                                  Default is an empty string.

    Return:
        List: All found controls.
        LookupError if no controller_set or tagged objects found.

    """
    if namespace:
        set_name = str("".join([namespace, constants.PXO_CONTROLS_SET_NAME]))
    else:
        set_name = constants.PXO_CONTROLS_SET_NAME

    try:
        all_controls = pmc.PyNode(set_name).members()

    except:
        all_controls = [
            node.getTransform()
            for node in pmc.ls(type="nurbsCurve")
            if node.getTransform().hasAttr(constants.PXO_ANIMATION_CTRL_TAG)
            and node.getTransform().attr(constants.PXO_ANIMATION_CTRL_TAG).get()
            is True
            and node.getTransform().namespace() == namespace
        ]
    if not all_controls:
        raise LookupError(
            "No controllers_set found or not unique."
            " Or no controllers with activated export animation tag found."
            " Or given namespace not correct."
        )
    if as_strings:
        all_controls = [str(node_.name()) for node_ in all_controls]
    return list(set(all_controls))


def get_additional_container_publishes(as_strings=False, namespace=""):
    """
    Get all objects that are in the additional publish set or are tagged as such.
    Will search about a controllers set in first place.
    If not found will take all tagged controls.

    Args:
        as_strings(bool): Gives back all controls as strings.
                          Default is False.

        namespace(str, optional): Will try to find controllers_set with
                                  given namespace.
                                  Valid value pattern is "nmsp_01:"
                                  Default is an empty string.

    Return:
        List: All found objects that are part of the additional publish set.
        LookupError if no controller_set or tagged objects found.

    """
    if namespace:
        set_name = str("".join([namespace, constants.PXO_ADD_SET_NAME]))
    else:
        set_name = constants.PXO_ADD_SET_NAME

    try:
        all_additional_publish_set_items = pmc.PyNode(set_name).members(
            flatten=True
        )

    except:
        all_additional_publish_set_items = [
            pynode.getTransform()
            for pynode in pmc.ls(type=("light", "aiMeshLight"))
            if pynode.getTransform().hasAttr(constants.PXO_ANIMATION_LGT_TAG)
            and pynode.getTransform().attr(constants.PXO_ANIMATION_LGT_TAG).get()
            is True
            and pynode.getTransform().namespace() == namespace
        ]
    if not all_additional_publish_set_items:
        _LOGGER.error(
            f"No {constants.PXO_ADD_SET_NAME} found or not unique."
            " Or no controllers with activated export animation tag found."
            " Or given namespace not correct."
        )
        return
    if as_strings:
        all_additional_publish_set_items = [
            str(node.name()) for node in all_additional_publish_set_items
        ]

    return list(set(all_additional_publish_set_items))


def get_interface_attributes(controller):
    """
    Find all attributes of the given controller that are relevant for animation.
    Attributes relevant for animation are visible in Mayas channel box. They are
    unlocked and they can either be keyable or settable.

    Args:
        controller(obj:`pm.PyNode`): Rig controller.

    Returns:
        :obj:`list` of :obj:`pm.PyNode`: List of attributes.

    """
    channel_box_attributes = set()
    interface_attributes = []
    # Find all keyable attribute from the channel box
    # (This does also return locked attributes, as they can still have keys attached).
    # controller = pmc.PyNode(controller.name())
    channel_box_attributes.update(controller.listAttr(keyable=True))
    # # Find all settable attribute from the channel box
    # # (`listAttr(channelBox=True)` does not return the keyable attributes).
    channel_box_attributes.update(controller.listAttr(channelBox=True))
    for attr in channel_box_attributes:
        if not attr.isLocked():
            interface_attributes.append(str(attr.name(includeNode=False)))
    return interface_attributes


def get_bind_joints():
    """
    Get the rig bind joints.

    Return:
        List: Empty if no bind joints exist.
              List of pmc.PyNode().
    """
    deformers_set = pmc.PyNode(constants.PXO_DEFORMERS_SET_NAME)
    return deformers_set.members()


def get_rig_containers(typ="root"):
    """
    Get the rig root container from the scene.

    Args:
        typ(str): Container type. valid values are ["root", "sub"].
                  Default is "root".

    Return:
        Empty list if fail.
        List:
            pmc.PyNode()

    """
    custom_pxo_nodes = pymel_utils.get_custom_pxo_nodes_from_scene(
        ["container", "dagContainer"]
    )
    root_uuid = pymel_utils.process_pxo_uuid(
        [
            constants.PXO_UUID_DICT[typ],
            constants.PXO_UUID_DICT["rig"],
            constants.PXO_UUID_DICT["container"],
        ]
    )
    return [
        node
        for node in custom_pxo_nodes
        if pymel_utils.get_pxo_uuid(node) == root_uuid
    ]


def nodes_to_names_dict(controllers):
    """Convert the contents of a controller dictionary from pyNodes to strings.

    Args:
        controllers (obj:`dict` of :obj:`pm.PyNode`): Dictionary of controller nodes as
            keys and lists of attribute nodes as values.

    Returns:
        :obj:`dict` of :obj:`string`: Dictionary of controller names as keys and
        lists of attribute names as values.

    """
    controller_names_dict = {}
    for control in list(controllers.keys()):
        attr_names = []
        for attr in controllers[control]:
            attr_names.append(attr.attrName(longName=True))

            controller_names_dict[control.nodeName()] = attr_names
    return controller_names_dict


def compare_controllers_dict(source, other):
    """
    Compare two dictionaries of controller attributes.

    Args:
        source (obj:`dict`): Source dictionary.
        other (obj:`dict`): Goal dictionary.

    Returns:
        obj:`dict`: Controller attributes of source missing in goal.
        Empty dictionary if no attributes are missing.

    """
    source_keys = list(source.keys())
    other_keys = list(other.keys())
    diff_source = list(set(source_keys) - set(other_keys))
    diff_other = list(set(other_keys) - set(source_keys))
    if diff_source:
        raise exceptions.AnimControllerInterfaceError(
            "This controllers are missing in target anim interface:\n{}".format(
                pprint.pformat({key: source.get(key) for key in diff_source})
            )
        )
    if diff_other:
        raise exceptions.AnimControllerInterfaceError(
            "This controllers are missing in source anim interface:\n{}".format(
                pprint.pformat({key: other.get(key) for key in diff_other})
            )
        )
    missing_attributes = {
        control: [compare_attributes(source.get(control), other.get(control))]
        for control in source_keys
        if compare_attributes(source.get(control), other.get(control))
    }
    return missing_attributes


def compare_attributes(source, other):
    """Compare two lists of controller attributes.

    Limitations:
        Currently we can only compare the bare existence of the attribute.
        We do not have information about the attributes data type, limits, etc.

    Args:
        source (obj:`list`): Source list.
        other(obj:`list`): Goal list.

    Returns:
        obj:`list`: Missmatched controllers.

    """
    missing_attr = []
    for attribute in source:
        if attribute not in other:
            missing_attr.append(attribute)
    return missing_attr


def validate_anim_controller_interface(source_controller_dict, controller_list):
    """
    Get difference between controllers in a dictionary and in the current scene.
    This function will also log some useful output for the rigging artist.

    Args:
        source_controller_dict(obj:`dict`): Dict of controller names as keys
                                            and lists of attributes as values.
        controller_list(obj:`list` of :obj:`pm.PyNode`): List of
                                                         controllers in
                                                         the scene.

    Returns:
        obj:`tuple` of :obj:`dict`: Tuple of excessive and missing controller
            dictionaries.

    """
    interface_attributes_dict = get_anim_interface_attributes(controller_list)
    missing_attributes = compare_controllers_dict(
        source_controller_dict, interface_attributes_dict
    )
    if missing_attributes:
        for e in exceptions.AnimControllerInterfaceError(
            "This attributes are different compared to the"
            " source rig anim interface: \n {}".format(
                pprint.pformat(missing_attributes)
            )
        ):
            _LOGGER.info(e)
    return missing_attributes


@DECORATORS.refresh_suspended()
@DECORATORS.undo
def mgear_match_ik_fk_in_range(
    blend_attr,
    host_ctrl_name,
    fk_list,
    ik_ctrl_name,
    upv_ctrl_name,
    namespace=None,
    start_frame=None,
    end_frame=None,
    bake_steps=None,
    to_anim_layer=True,
    switch_to="ik",
):
    """
    Match the ik to the fk animation of an mgear rig in given frame range.

    Args:
        blend_attr(str): The ik/fk blend attribute.
        host_ctrl_name(str): The host control name.
        fk_list(list): List the fk control names.
        ik_ctrl_name(str): The ik control name.
        upv_ctrl_name(str): The pole vector control name.
        namespace(str): The rig namespace.
                        Default is None.
        start_frame(int): The start frame.
                          If none will take current playback settings.
                          Default is None.
        end_frame(int): The end frame.
                        If none will take current playback settings.
                        Default is None.
        bake_steps(int): Defines in which distance the baked keyframes are made.
                         If None will bake on ones.
                         Default is None.
        to_anim_layer(bool): Create a anim layer for the bakes keyframes.
                          Default is None.
        switch_to(str): Defines if you want to bake to "ik" or vise versa.
                        Valid values are ["ik", "fk"].
                        Default is "ik".

    """
    anim_layer = None
    if not start_frame:
        start_frame = int(pmc.playbackOptions(q=True, minTime=True))
    if not end_frame:
        end_frame = int(pmc.playbackOptions(q=True, maxTime=True))
    if not bake_steps:
        bake_steps = 1
    switch_value = 0
    reswitch_value = 1
    if switch_to == "ik":
        switch_value = 0
        reswitch_value = 1
    nmsp = ""
    if namespace:
        nmsp = f"{namespace}:"
    ik_ctrl_nd = pmc.PyNode(nmsp + ik_ctrl_name)
    ik_ctrl_upv_nd = pmc.PyNode(nmsp + upv_ctrl_name)
    if to_anim_layer:
        try:
            anim_layer = pmc.PyNode("mgear_ik_fk_match")
        except:
            anim_layer = pmc.animLayer("mgear_ik_fk_match")
        anim_layer.addMember(ik_ctrl_nd)
        anim_layer.addMember(ik_ctrl_upv_nd)
    count = start_frame
    while count < end_frame:
        pmc.currentTime(count)
        pmc.PyNode(nmsp + host_ctrl_name).attr(blend_attr).set(switch_value)
        anim_utils.ikFkMatch_with_namespace(
            nmsp,
            blend_attr,
            host_ctrl_name,
            fk_list,
            ik_ctrl_name,
            upv_ctrl_name,
            key=False,
        )
        pmc.PyNode(nmsp + host_ctrl_name).attr(blend_attr).set(reswitch_value)
        for ctrl in [ik_ctrl_nd, ik_ctrl_upv_nd]:
            for channel in ["translate", "rotate"]:
                for axe in ["X", "Y", "Z"]:
                    if to_anim_layer:
                        anim_layer.setAttribute(ctrl.attr(channel + axe))
                        pmc.setKeyframe(
                            ctrl.attr(channel + axe),
                            t=count,
                            animLayer="mgear_ik_fk_match",
                        )
                    else:
                        pmc.setKeyframe(
                            ctrl.attr(channel + axe),
                            t=count,
                        )
        count += bake_steps
    pmc.PyNode(nmsp + host_ctrl_name).attr(blend_attr).set(1)


def switch_mgear_control_orientation(
    control,
    aim_nd=None,
    up_axes="y",
    aim_axes="z",
    aim_ref_pos=(10, 0, 0),
    up_ref_pos=(0, -10, 0),
):
    """Switch a rig control to given orientation, temporarily unlocking rotate."""
    # axis tuples (compact)
    aim_tuple = {"x":(1,0,0),"y":(0,1,0),"z":(0,0,1),"-x":(-1,0,0),"-y":(0,-1,0),"-z":(0,0,-1)}.get(aim_axes,(0,0,-1))
    up_tuple  = {"x":(1,0,0),"y":(0,1,0),"z":(0,0,1),"-x":(-1,0,0),"-y":(0,-1,0),"-z":(0,0,-1)}.get(up_axes,(0,0,-1))

    # remember & unlock rotate locks
    r_attrs = [control.rx, control.ry, control.rz]
    was_locked = [a.isLocked() for a in r_attrs]
    for a in r_attrs:
        if a.isLocked():
            a.set(lock=False)

    aim_ref_nd = up_ref_nd = aim_ref_nd_npo = up_ref_nd_npo = aim_con = None
    try:
        # get plain 16-float world matrices via cmds (avoids pymaya Matrix coercion)
        src = aim_nd or control
        src_name = src.name() if hasattr(src, "name") else str(src)
        ctrl_name = control.name() if hasattr(control, "name") else str(control)

        aim_mtx = cmds.xform(src_name, q=True, ws=True, m=True)
        up_mtx  = cmds.xform(ctrl_name, q=True, ws=True, m=True)

        short = control.nodeName()
        aim_ref_nd = pmc.createNode("transform", n=f"{short}_aim_ref_trs")
        up_ref_nd  = pmc.createNode("transform", n=f"{short}_up_ref_trs")

        # apply matrices with cmds (plain lists)
        cmds.xform(aim_ref_nd.name(), ws=True, m=aim_mtx)
        cmds.xform(up_ref_nd.name(),  ws=True, m=up_mtx)

        # buffer groups after placing
        aim_ref_nd_npo = dag_utils.create_buffer_groups([aim_ref_nd])[0]
        up_ref_nd_npo = dag_utils.create_buffer_groups([up_ref_nd])[0]

        aim_ref_nd.translate.set(aim_ref_pos)
        up_ref_nd.translate.set(up_ref_pos)

        # constraint to bake orientation, then delete
        aim_con = pmc.aimConstraint(
            aim_ref_nd,
            control,
            aim=aim_tuple,
            u=up_tuple,
            wut="object",
            wuo=up_ref_nd,
        )
    finally:
        # cleanup temp nodes / constraint
        to_del = [n for n in (aim_ref_nd_npo, up_ref_nd_npo, aim_con) if n and pmc.objExists(n)]
        if to_del:
            pmc.delete(to_del)
        # restore original locks
        for a, lock_back in zip(r_attrs, was_locked):
            if lock_back:
                a.set(lock=True)

    return control


def exchange_connections_to_new_trs(node, exception_node_type=None):
    """
    Exchange all node connection to a new created trs node.

    Args:
        node(pmc.PyNode()): The node to exchange.
        exception_node_type(List): Node to skip the exchange.

    Example:
        >>> self.exchange_connections_to_new_trs(pmc.PyNode(
            "your_node"), ["dagPose", "ObjectSet"])

    Return:
        pmc.PyNode(): The new created trs node.

    """
    if exception_node_type is None:
        exception_node_type = list()

    trs_nd = pmc.createNode("transform", n="{}_trs".format(node.name()))
    trs_nd.setMatrix(node.getMatrix(worldSpace=True), worldSpace=True)
    parent_nd = node.getParent()
    parent_nd.addChild(trs_nd)
    plug_nd_list = []
    current_nd_types = []
    for plug in node.connections(s=False, d=True, c=True, p=True):
        data = {}
        target_node = pmc.PyNode(plug[1].split(".")[0])
        data["target_nd"] = target_node
        data["target_nd_type"] = target_node.type()
        data["target_plug"] = plug[1]
        data["source_plug"] = plug[0].split(".")[1]
        current_nd_types.append(target_node.type())
        plug_nd_list.append(data)
    current_nd_types = list(set(current_nd_types))
    valid_nd_types = list(set(current_nd_types) - set(exception_node_type))
    for type_ in valid_nd_types:
        for dic in plug_nd_list:
            if dic.get("target_nd_type") == type_:
                trs_nd.attr(dic.get("source_plug")).connect(
                    dic.get("target_plug"), force=True
                )
    return trs_nd


def is_almost_equal(
    value, equal_val, tolerance_float, decimal=4, check_negative=True
):
    """
    Check if a value is almost equal to another value in a given tolerance.

    Args:
        value(float): The source value.
        equal_val(float): The value you want to cSompare with.
        tolerance_float(float): This value adds to the equal_val.
                                This defines the valid tolerance area.
        decimal(int): The decimal rounding value.
                      Default is 4.
        check_negative(bool): Add negative tolerance to the comparison.
                             Default is True.

    Return:
        True or False.

    """
    value = round(value, decimal)
    tolerance_float = round((equal_val + tolerance_float), decimal)
    negative_tolerance_float = tolerance_float * -1

    if check_negative:
        if negative_tolerance_float <= value <= tolerance_float:
            return True
    else:
        if value < tolerance_float:
            return True
    return False


def get_dot_product(obj_0, obj_1, axis):
    """
    Get dot product from transform objects in given axis.

    Args:
        obj_0(pmc.PyNode()): Transform object.
        obj_1(pmc.PyNode()): Transform object.
        axis(str): The axis for the calculation.
                   Valid are ["z", "y"]

    Return:
        Float: Dot product value between 0 and 1.

    """
    vec_0 = dt.Vector(obj_0.getMatrix(worldSpace=True).translate)
    vec_1 = dt.Vector(obj_1.getMatrix(worldSpace=True).translate)
    disctance_ = vec_0.distanceTo(vec_1)
    sub_vec = vec_1.__sub__(vec_0)
    if axis == "z":
        vec_2 = dt.Vector(0, disctance_, 0)
    else:
        vec_2 = dt.Vector(0, 0, disctance_)
    return vec_2.normal().dot(sub_vec.normal())


def get_angle(obj_0, obj_1, axis="z"):
    """
    Get the angle between two transform objects.

    Args:
        obj_0(pmc.PyNode()): Transform object.
        obj_1(pmc.PyNode()): Transform object.
        axis(str): The axis for the calculation.
                   Valid are ["z", "y"]

    Return:
        Float: The angel as degree.

    """
    vec_0 = dt.VectorN(obj_0.getMatrix(worldSpace=True).translate)
    vec_1 = dt.VectorN(obj_1.getMatrix(worldSpace=True).translate)
    distance_ = vec_0.distanceTo(vec_1)
    a_end = dt.Vector(0, distance_, 0)
    c_end = dt.Vector(0, 0, distance_)
    b_end = vec_1.__sub__(vec_0)
    angle_obj = dt.Angle(90.0)
    if axis == "z":
        return angle_obj.asDegrees() - dt.degrees(a_end.angle(b_end))
    else:
        return dt.degrees(b_end.angle(c_end)) - angle_obj.asDegrees()


def get_distance(obj_0, obj_1):
    """
    Get the distance of two objects.

    Args:
        obj_0(pmc.PyNode()): Transform object.
        obj_1(pmc.PyNode()): Transform object.

    Return:
        Float: Distance value.

    """
    vec_0 = dt.VectorN(obj_0.getMatrix(worldSpace=True).translate)
    vec_1 = dt.VectorN(obj_1.getMatrix(worldSpace=True).translate)
    return vec_0.distanceTo(vec_1)


def get_anim_interface_attributes(controller_list):
    """
    Get all animateable attributes from given list.

    Args:
        controller_list(list): The animation controls.

    """
    interface_attributes_scene_dict = {}
    for control in controller_list:
        interface_attributes_scene_dict[
            str(control.name())
        ] = get_interface_attributes(control)
    return interface_attributes_scene_dict


def get_connected_anim_controls(
        rig_controls: list,
        as_PyNodes: bool = True,
        channels: Optional[list] = None,
):
    """
    Get all connected controls back from given rig controls list.

    Args:
        rig_controls(list): Given rig controls.
        as_PyNodes(bool): Gives controls back as pmc.PyNodes().
                          If False as OpenMaya_MObjects.
                          Default is True

        channels(list): Channels to check for as strings.
                        Default is:
                        ["translateX", "translateY", "translateZ",
                        "rotateX", "rotateY", "rotateZ",
                        "scaleX", "scaleY", "scaleZ"]

    Return:
        List: All found nodes as string or pmc.PyNode().
        None if no controls are connected.

    """
    if not channels:
        channels = (
            "translateX",
            "translateY",
            "translateZ",
            "rotateX",
            "rotateY",
            "rotateZ",
            "scaleX",
            "scaleY",
            "scaleZ",
        )

    connected_controls = set()
    sel = om2.MSelectionList()

    tuple(sel.add(list_item) for list_item in rig_controls)

    iter_ = om2.MItSelectionList(sel, om2.MFn.kTransform)
    transform_pointer = om2.MFnTransform()

    while not iter_.isDone():
        m_object = iter_.getDependNode()
        transform_pointer.setObject(m_object)

        for channel in channels:
            plug = transform_pointer.findPlug(channel, 0)

            if all((plug.isConnected, plug.isKeyable)):

                connected_controls.add(transform_pointer.name())
                next(iter_)

        next(iter_)

    if connected_controls:
        if as_PyNodes:
            return [pmc.PyNode(node) for node in connected_controls]

    return connected_controls


def set_rig_lod_meta_data(rig_root_nd, lod, lod_dict):
    """
    Set rig lod meta data. For given lod index.

    Args:
        rig_root_nd(pmc.PyNode): The rig root node.
        lod(str): The lod index.
        lod_dict(dict): The lod dict with all needed lod data for given lod.
                        Example: {'dag': [str, str], 'geo': [str, str],
                                  'non_dag': [str, str], 'roots': [str, str],
                                  'lod_name': 'proxy', 'lowest_lod': True, 'highest_lod': False}

    """
    rig_root_nd.set_meta_lod_index(int(lod))  # noqa: because this will be a pynode
    rig_root_nd.set_meta_lod_name(lod_dict[constants.LOD_NAME_META_ATTR])  # noqa: because this will be a pynode
    rig_root_nd.set_meta_lowest_lod(lod_dict[constants.LOD_LOWEST_META_ATTR])  # noqa: because this will be a pynode
    rig_root_nd.set_meta_highest_lod(lod_dict[constants.LOD_HIGHEST_META_ATTR])  # noqa: because this will be a pynode
    rig_root_nd.set_meta_lod_master(lod_dict[constants.LOD_MASTER])  # noqa: because this will be a pynode
    rig_root_nd.set_meta_lod_rig(True)  # noqa: because this will be a pynode


def create_rig_root_hierarchy(
    advanced: bool = False,
        asset_name: Optional[str] = None,
        version_number: Optional[int] = None,
        get_guide_data: bool =True,
):
    """
    Create the rig root hierarchy.
    This will use the rig root container node.

    Args:
        advanced(bool): Will take non dag container
                        instead of the normal container.
                        A non dag container has no transform.
                        But it can zip all kind of maya nodes.

    """
    scene_name = pmc.sceneName()
    guide_version = 0
    if get_guide_data:
        guide_meta_data = guide_utils.get_guide_meta_data()
        guide_version = guide_meta_data.get(constants.GUIDE_VERSION_ATTR_NAME)
    if not version_number:
        version_number = 1
    else:
        version_number = paths_utils.get_version_number_from_basename(
            os.path.basename(scene_name)
        )
    asset_assembly_uuid = pymel_utils.process_pxo_uuid(
        [
            constants.PXO_UUID_DICT["meta"],
            constants.PXO_UUID_DICT["rig"],
            constants.PXO_UUID_DICT["asset_assembly"],
        ]
    )
    if not asset_name:
        asset_name = paths_utils.get_asset_infos(pmc.sceneName(),
                                                 info_type="asset_name"
                                                 )

    root_name = f"{asset_name}_rig"

    if advanced:
        rig_root_nd = pymel_utils.PxoContainerRigRootNode(name=root_name)
    else:
        rig_root_nd = pymel_utils.PxoDagContainerRigRootNode(name=root_name)

    rig_root_nd.rmbCommand.set("rig_root_container_rmb_cmd")
    rig_root_nd.set_meta_data()
    rig_root_nd.set_sub_containers()
    rig_root_nd.set_meta_asset_name(asset_name)
    rig_root_nd.set_meta_rig_wip_path(scene_name)
    rig_root_nd.set_meta_rig_wip_version(version_number)
    rig_root_nd.set_meta_guide_version(guide_version)
    custom_pxo_nodes = pymel_utils.get_custom_pxo_nodes_from_scene()

    asset_assembly_node = [
        node
        for node in custom_pxo_nodes
        if pymel_utils.get_pxo_uuid(node) == asset_assembly_uuid
    ]

    if asset_assembly_node:
        rig_root_nd.set_meta_asset_assembly_node(asset_assembly_node[0])
    return rig_root_nd


def finish_rig_root_nd(
    root_nd, add_rig_setup=True, add_mdl_asset=True, asset_assembly_nd=None
):
    """
    Set the rig container to black box mode and insert the mdl asset
    and the rig setup grp.

    Args:
        root_nd(pmc.PyNode()): The rig root container node.
        add_rig_setup(bool): Insert the rig setup grp and
                             publish all included control curves.
                             So it is available for animation.
                             Default is True.
        add_mdl_asset(bool): Insert the mdl asset.
                             If the mdl asset is a reference then it
                             will import it.
                             Because you can not insert a reference
                             into an container node.
                             Default is True.
        asset_assembly_nd(pmc.PyNode()): The rig asset assembly node.
                                         This is optional.
                                         If none given will try to finde the
                                         asset assembly node in the scene.
    """
    sub_containers = root_nd.getSubcontainers()

    try:
        model_container = [
            node_
            for node_ in sub_containers
            if node_.name(long=None) == root_nd.MODEL_ASSET_SUB_CONTAINER_NAME
        ][0]

    except:
        raise exceptions.MayaNodeNotFound(
            "No PxoContainerRigSub node found for the model asset"
        )

    try:
        rig_container = [
            node_
            for node_ in sub_containers
            if node_.name(long=None) == root_nd.RIG_SUB_CONTAINER_NAME
        ][0]

    except:
        raise exceptions.MayaNodeNotFound(
            "No PxoContainerRigSub node found for the rig setup"
        )
    if add_rig_setup:
        rig_setup_root_nd = [pmc.PyNode(constants.RIG_SETUP_ROOT_NAME)]
        anim_controls = get_anim_control_interface()
        bind_joints = get_bind_joints()
        additional_publishable_items = get_additional_container_publishes()

        if rig_setup_root_nd not in rig_container.getNodeList():
            rig_container.add_nodes(rig_setup_root_nd)
            rig_container.publish_nodes(anim_controls)
            rig_container.publish_nodes(bind_joints)
            if additional_publishable_items:
                rig_container.publish_nodes(additional_publishable_items)

    if add_mdl_asset:
        model_asset_root_nodes = model_container.getChildren()
        mdl_asset_components = []
        if not asset_assembly_nd:
            asset_assembly_nd = root_nd.get_meta_asset_assembly_node()

        if asset_assembly_nd:
            asset_assembly_data = asset_assembly_nd.get_assembly_data()
            if not model_asset_root_nodes:
                model_asset_root_nodes = [
                    dag_utils.get_root_node_from_child_node(
                        data_dict.get(
                            constants.PXO_ASSET_ASSEMBLY_NODE_ASSET_ROOT_NODE
                        )
                    )
                    for data_dict in asset_assembly_data
                ]
            else:
                pmc.parent(model_asset_root_nodes, None)
            for asset_data_dict in asset_assembly_data:
                components_dict = asset_data_dict["components"]
                components_keys = list(components_dict.keys())
                for key in components_keys:
                    items = list(components_dict[key].items())
                    mdl_asset_components.extend(items[0][1])

            mdl_reference_list = [
                data_dict.get(
                    constants.PXO_ASSET_ASSEMBLY_NODE_ASSET_PUBLISH_PATH
                )
                for data_dict in asset_assembly_data
            ]

        if not model_asset_root_nodes:
            raise exceptions.MayaNodeNotFound(
                "No mdl asset root node found or"
                " asset assembly node not existing."
            )
        scene_utils.import_references()
        model_container.add_nodes(list(set(model_asset_root_nodes)))
        model_container.publish_nodes(list(set(mdl_asset_components)))
    close_open_rig_root_nd(root_nd, True)
    _LOGGER.info("Container: {0} finished.".format(root_nd))


def close_open_rig_root_nd(root_nd, value):
    """
    Open and close the rig root container.

    Args:
        root_nd(pmc.PyNode()): The rig root container node.
        value(bool): True --> Close, False --> Open.
    """
    sub_containers = root_nd.getSubcontainers()
    [container.set_black_box_mode(value) for container in sub_containers]


def create_worldspace_matrix_constraint(
    node,
    target_node,
    channels=[
        "translateX",
        "translateY",
        "translateZ",
        "rotateX",
        "rotateY",
        "rotateZ",
        "scaleX",
        "scaleY",
        "scaleZ",
    ],
    connect_output=True,
    force=False,
):
    """
    Create a basic worldspace matrix constraint node tree. Without an offset.

    Args:
        node(pmc.PyNode, str): The node to be constraint.
        target_node(pmc.PyNode, str): The target node to be constraint to.
        channels(list): List filled with strings.
                        Thats the channels the contraint and the node
                        are connected.
                        Default is :
                        [
                        "translateX",
                        "translateY",
                        "translateZ",
                        "rotateX",
                        "rotateY",
                        "rotateZ",
                        "scaleX",
                        "scaleY",
                        "scaleZ",
                        ]
        connect_output(bool): Connect the node with the constraint or not.
                              Default is True.
        force(bool): Will cut of all current connections of the given channels
                     and connect them with the constraint outputs.
                     Default is False.

    Return:
          Tuple: The created mult matrix and decompose matrix node.

    """
    if not isinstance(node, pmc.PyNode):
        node = pmc.PyNode(node)
    if not isinstance(target_node, pmc.PyNode):
        target_node = pmc.PyNode(target_node)
    mult_matrix = pmc.createNode("multMatrix")
    decompose_matrix = pmc.createNode("decomposeMatrix")
    target_node.worldMatrix[0].connect(mult_matrix.matrixIn[0])
    node.parentInverseMatrix[0].connect(mult_matrix.matrixIn[1])
    mult_matrix.matrixSum.connect(decompose_matrix.inputMatrix)
    if connect_output:
        for channel in channels:
            decompose_matrix.attr(
                "output{}{}".format(channel[0].upper(), channel[1:])
            ).connect(node.attr(channel), force=force)
    return mult_matrix, decompose_matrix


def locators_on_cv(shape, connect=False, locatorScale=(1, 1, 1), steps=None):
    """
    Created locators on each CV  of an curve or in given steps.

    Args:
        shape(pmc.PyNode): The curve shape.
        connect(bool): Connect each cv with created locator.
                       Default is False.
        locatorScale(tuple): The locator scale.
        steps(int): Specify if just locator of given steps are created.
                    If None will created a locator for each CV.

    Returns:
        List: The created locators.

    """
    result = []
    for nm, ps in enumerate(shape.getCVs()):
        loc = pmc.spaceLocator()
        result.append(loc)
        loc.translate.set(ps)
        loc.getShape().localScale.set(locatorScale)
        if connect:
            loc.getShape().worldPosition[0].connect(shape.controlPoints[nm])
    if steps:
        temp = range(len(result))
        temp = temp[0::steps]
        while len(temp) > 1:
            for x in range(temp[0] + 1, temp[1]):
                pmc.delete(result[x])
            temp.remove(temp[0])
    return result


def distribute_locators_on_curve(curve, num_locators, return_position=False):
    """
    Distribute a given number of locator on a curve

    Args:
        curve: the curve
        num_locators: the number of locator
        return_position: if true instead of creating locator will return an array on point in world space

    Returns:

    """
    if num_locators < 1:
        _LOGGER.warning("Number of locators must be at least 1")
        return

    curve_length = curve.length()
    interval = curve_length / (num_locators - 1)

    locators = []
    positions = []
    for i in range(num_locators):
        param = curve.findParamFromLength(interval * i)
        point = curve.getPointAtParam(param, space="world")
        positions.append(point)
        if not return_position:
            locator = pmc.spaceLocator()
            pmc.move(locator, point, worldSpace=True)
            locators.append(locator)
    if return_position:
        return positions
    else:
        return locators


def create_curve_from_transforms(
    selection, degree=1, locators=True, name="curve"
):
    """
    Create a curve based on selected transforms.
    By default it will have locators to control the curve points.

    Args:
            selection(list): Selected transforms.
            degree(int): The curve type. By Default is it "linear"
            locators(bool): Enable control lacotors.
            name(str): The curve name.

    Returns:
            Tuple: (The created curve, list of locators or none)
    """
    knotes = [node.getMatrix(worldSpace=True).translate for node in selection]
    curve = pmc.curve(d=degree, p=knotes, n=name)
    locs = []
    if locators:
        locs = locators_on_cv(curve.getShape(), connect=True)
        for count, node in enumerate(locs):
            node.rename("{}_{}_LOC".format(name, str(count)))
    return curve, locs


def clear_non_dag_history():
    """
    Sets the history display of all the non-dag nodes to false.
    """
    # get all nodes in scene that are not part of the dag
    non_dags = [
        str(node)
        for node in cmds.ls()
        if not cmds.objectType(node, isa="dagNode")
    ]

    # set those nodes to not interesting for history
    [
        cmds.setAttr("{0}.isHistoricallyInteresting".format(non_dag), False)
        for non_dag in non_dags
    ]


def set_constraints_to_shortest():
    """
    Sets all the constraints that have interpolation options in the scene to shortest.
    """

    registered_constraint_types = [
        str(node_type_str)
        for node_type_str in cmds.nodeType(
            "constraint", derived=True, isTypeName=True
        )
    ]

    in_scene_constraints = chain.from_iterable(
        [
            cmds.ls(type=node_type_str)
            for node_type_str in registered_constraint_types
        ]
    )

    in_scene_constraint_names = [
        str(node_name_str) for node_name_str in in_scene_constraints
    ]

    # set constraints to template
    [
        cmds.setAttr("{0}.template".format(node_name_str), True)
        for node_name_str in in_scene_constraint_names
    ]
    # set constraints to invisible
    [
        cmds.setAttr("{0}.visibility".format(node_name_str), False)
        for node_name_str in in_scene_constraint_names
    ]

    # get all constraints with interp Type attr
    in_scene_constraints_with_attr = [
        node_name_str
        for node_name_str in in_scene_constraint_names
        if cmds.attributeQuery("interpType", node=node_name_str, exists=True)
    ]
    # set interp Type attr to shortest
    [
        cmds.setAttr("{0}.interpType".format(node_name_str), 2)
        for node_name_str in in_scene_constraints_with_attr
    ]


def get_anim_control_objects(
    selection, meta_tag_string=constants.RIG_SYS_CONTROL_TAG
):
    """
    Get all anin control objects from given selection list.
    It will search about the objects based on a meta tag name.

    Args:
        selection(list): The controls objects root node.
        meta_tag_string(str): The meta tag string name to search for.
                              Default is constants.constants.RIG_SYS_CONTROL_TAG.

    Returns:
        List: All found control objects. None if no exists.

    """
    all_children = list(
        chain.from_iterable(
            [
                x.getChildren(ad=True, shapes=False)
                for x in selection
                if pmc.objExists(x)
            ]
        )
    )
    all_controls = list(
        set([node for node in all_children if node.hasAttr(meta_tag_string)])
    )
    all_controls.sort()
    return all_controls


def reduce_rig_components(
    lod_roots,
    group_name="mgear_rig_reduced",
    group_suffix="grp",
    clean_reducing=False,
):
    """
    Reduce the rig component. So we will have a new rig version with just the
    components we need for an LOD.

    Args:
        lod_roots(List): The component roots. List of pmc.PyNode()
        group_name(str): The rig reduce group name.
        group_suffix(str): The rig reduce grp suffix.
        clean_reducing(bool): Will delete unused nodes in the scene.
                              This is not undoable.

    Returns:
        pmc.PyNode(): The newly created reducing group.

    """
    lod_group_name = "_".join([group_name, "0", group_suffix])
    try:
        reduce_root_node = pmc.PyNode(lod_group_name)
    except:
        reduce_root_node = pmc.createNode("transform", n=lod_group_name)
        reduce_root_node.inheritsTransform.set(False, lock=True)
    controls = get_anim_control_objects(lod_roots)
    buffers = dag_utils.create_buffer_groups(controls)
    pmc.parent(buffers, reduce_root_node, absolute=True)
    children = list(
        chain.from_iterable([x.getChildren(ad=True) for x in controls])
    )
    temp = [node for node in children if node.nodeType() != "nurbsCurve"]
    pmc.delete(lod_roots + temp)
    out_connections = list(
        chain.from_iterable(
            [ctrl.connections(s=False, d=True, p=True) for ctrl in controls]
        )
    )
    for connection in out_connections:
        if "dagSetMembers" not in connection.name(includeNode=False):
            connection.unlock()
            connection.disconnect()
    if clean_reducing:
        _LOGGER.warning("Clean reducing is not undoable.")
        mel.eval("MLdeleteUnused;")
    return reduce_root_node


def create_aim_matrix(
    input_obj,
    target_mtx,
    up_mtx,
    initial_state_mtx,
    parent_ws_inverse_mtx=False,
    aim_vec=(1.0, 0.0, 0.0),
    up_vec=(0.0, 1.0, 0.0),
):
    """
    Create a aim matrix setup as alternative to an aim constraint.
    This setup evals faster then a aim constraint.

    Args:
        input_obj(pmc.PyNode): The obj to orient.
        target_mtx(pmc.dt.Matrix): The target matrix.
        up_mtx(pmc.dt.Matrix): The up matrix.
        initial_state_mtx(pmc.dt.Matrix): The initial matrix. Thats the rest pose.
        parent_ws_inverse_mtx(pmc.dt.Matrix):
        aim_vec(tuple): The aim vec. Default is (1.0, 0.0, 0.0)
        up_vec(tuple): The up vec. Default is (0.0, 1.0, 0.0)

    """
    aim_mtx_nt = pmc.createNode("aimMatrix")
    target_mtx.connect(aim_mtx_nt.primaryTargetMatrix)
    up_mtx.connect(aim_mtx_nt.secondaryTargetMatrix)
    initial_state_mtx.connect(aim_mtx_nt.inputMatrix)
    aim_mtx_nt.primaryInputAxis.set(aim_vec)
    aim_mtx_nt.secondaryInputAxis.set(up_vec)
    aim_mtx_nt.secondaryMode.set(1)
    output_plug = aim_mtx_nt.outputMatrix
    if isinstance(parent_ws_inverse_mtx, pmc.Attribute):
        mult_mtx_nd = pmc.createNode("multMatrix")
        output_plug.connect(mult_mtx_nd.matrixIn[1])
        parent_ws_inverse_mtx.connect(mult_mtx_nd.matrixIn[2])
        output_plug = mult_mtx_nd.matrixSum
    pick_matrix_nd = pmc.createNode("pickMatrix")
    output_plug.connect(pick_matrix_nd.inputMatrix)
    pick_matrix_nd.useScale.set(0)
    pick_matrix_nd.useTranslate.set(0)
    pick_matrix_nd.useShear.set(0)
    pick_matrix_nd.outputMatrix.connect(input_obj.offsetParentMatrix)


def create_uv_pin_setup(
    mesh_trs,
    target_nd_list,
    pin_directly=False,
    use_out_translate=False,
    keep_in_hierarchy=False,
):
    """
    Create the uv pin setup as alternative to an classic follicle set up.
    This evals faster then a follicle.

    Args:
        mesh_trs(pmc.PyNode): The mesh to pin on. This will needs layouted UVs.
        target_nd_list(List): The nodes you want to pin.
        pin_directly(bool): Connect directly into parentOffsetMatrix port or use a buffer grp.
                            Default is False.
        use_out_translate(bool): Use the vector translation instead of the matrix.
                                 Be aware that this gives no rotation and scale.
                                 Default is False
        keep_in_hierarchy:

    Returns:
        List: The buffer groups if used. If pinned directly this is None.
    """
    result = []
    from pxo_rigging_kit.maya_utils.EWAW_rs import node

    mesh_shape = mesh_trs.getShape()
    mesh_deformed_shape = mesh_trs.getShape(noIntermediate=True)

    uv_pin_nd = node.createNode("uvPin", as_type="pymel")

    mesh_deformed_shape.worldMesh[0].connect(uv_pin_nd.deformedGeometry)
    mesh_shape.worldMesh[0].connect(uv_pin_nd.originalGeometry)

    for index, node in enumerate(target_nd_list, 1):

        point = node.getMatrix(worldSpace=True).translate
        u_value, v_value = mesh_shape.getUVAtPoint(point, "world")

        uv_pin_nd.coordinate[index].coordinateU.set(u_value, lock=True)
        uv_pin_nd.coordinate[index].coordinateV.set(v_value, lock=True)

        output_port = uv_pin_nd.outputMatrix[index]
        input_port = "offsetParentMatrix"

        if use_out_translate:
            output_port = uv_pin_nd.outputTranslate[index]
            input_port = "translate"

        if not pin_directly:
            if keep_in_hierarchy:
                pin_trs_name = f"{node.nodeName()}_pin_TRS"

                # this settings allow the structure to stay in the hierachy without losing the position
                pin_trs = pmc.group(
                    node, n=pin_trs_name
                )
                result.append(pin_trs)

                hold_matrix_nd = pmc.createNode(
                    "holdMatrix", n=f"{pin_trs_name}_staticOffset_HMX"
                )

                mult_matrix_offset_nd = pmc.createNode(
                    "multMatrix", n=f"{pin_trs_name}_offset_MMX"
                )

                mult_matrix_position_nd = pmc.createNode(
                    "multMatrix", n=f"{pin_trs_name}_position_MMX"
                )

                parent = pin_trs.getParent()

                inverse_pos = output_port.get().inverse()
                world_parent_pos = parent.getMatrix(worldSpace=True)
                static_offset_mtx = world_parent_pos * inverse_pos

                output_port.connect(mult_matrix_position_nd.matrixIn[0])

                parent.worldInverseMatrix[0].connect(
                    mult_matrix_position_nd.matrixIn[1]
                )

                hold_matrix_nd.inMatrix.set(static_offset_mtx)

                # just getting the offset matrix, then reusing the mult_matrix_offset_nd
                hold_matrix_nd.outMatrix.connect(
                    mult_matrix_offset_nd.matrixIn[0]
                )
                mult_matrix_position_nd.matrixSum.connect(
                    mult_matrix_offset_nd.matrixIn[1]
                )
                mult_matrix_offset_nd.matrixSum.connect(
                    pin_trs.offsetParentMatrix
                )

            else:
                pin_trs = pmc.createNode(
                    "transform", n=f"{node.nodeName()}_pin_TRS"
                )

                result.append(pin_trs)
                output_port.connect(pin_trs.attr(input_port))
                node.setParent(pin_trs)

        else:
            output_port.connect(node.attr(input_port))

            if not use_out_translate:
                node.translate.set(0.0, 0.0, 0.0)
                node.rotate.set(0.0, 0.0, 0.0)
                node.scale.set(1.0, 1.0, 1.0)

    return result


def create_follicle_setup(mesh_trs, transform_list):
    """
    Create a follicle setup.

    Args:
        mesh_trs(pmc.PyNode): The mesh to pin on. This will needs layouted UVs.
        transform_list(list): The nodes you want to pin.

    Returns:
        List: Created follicles.

    """
    result = [create_follicle(mesh_trs, trs) for trs in transform_list]


def create_follicle(mesh, transform, parent_transform=True):
    """
    Create a follicle on the world position of given transform.

    Args:
        mesh(pmc.PyNode): The mesh to pin on. This will needs layouted UVs.
        transform(pmc.PyNode): The transform.
        parent_transform(bool): Parent the given transfrom under the created follicle.

    Returns:
        pmc.PyNode: Created follicle.

    """
    mesh_shape = mesh.getShapes(noIntermediate=True)[0]
    point = transform.getMatrix(worldSpace=True).translate
    u_value, v_value = mesh_shape.getUVAtPoint(point, "world")
    follicle_shape = pmc.createNode("follicle")
    follicle_transform = follicle_shape.getParent()
    follicle_transform.rename("{}_fol".format(transform.name()))
    mesh_shape.worldMesh[0].connect(follicle_shape.inputMesh)
    follicle_shape.outTranslate.connect(follicle_transform.translate)
    follicle_shape.outRotate.connect(follicle_transform.rotate)
    follicle_shape.parameterU.set(u_value)
    follicle_shape.parameterV.set(v_value)
    if parent_transform:
        follicle_transform.addChild(transform)
    return follicle_transform


def create_transfrom_on_position(target_obj, name=None):
    """
    Create a transform on the position of given object.

    Args:
        target_obj(pmc.PyNode): The target object for the position
        name(str): The tarnsform name.
                   If None will take name of the target object and add _pos_trs as suffix

    Returns:
        pmc.PyNode(): The created transform.

    """
    if not name:
        name = "{}_pos_trs".format(target_obj.nodeName())
    trs = pmc.createNode("transform", n=name)
    pmc.matchTransform(trs, target_obj)
    return trs


def create_transform_on_nurbs_surface(
    nurbs_surface,
    v_param=0.500,
    u_param=0.500,
    loc_name=None,
    decompose_name=None,
    reuse_uv_pin=False,
):
    """
    Add a locator to a nurbs surface! This works like a follicle.

    Args:
        nurbs_surface(pmc.PyNode()): The nurbsSurface geo.
        v_param(float): The position in v.
                        Default is 0.500.
        u_param(float): The position in u.
                        Default is 0.500
        loc_name(str): The locators name.
                       Default is None.
       decompose_name(str): The locators name.
                       Default is None.

    Returns:
        NamedTuple: ("locator", "point_on_surface", "four_by_four_matrix", "decompose_matrix")

    """
    loc = None
    decompose_mtx = None
    connection_names = list()

    nurbs_shape = nurbs_surface.getShape()

    free_index = 0
    if reuse_uv_pin:
        up_pin_node = nurbs_shape.worldSpace[0].connections(
            s=False, d=True, type="uvPin"
        )
        if not up_pin_node:
            up_pin_node = pmc.createNode("uvPin")
            nurbs_shape.worldSpace[0].connect(up_pin_node.deformedGeometry)
        else:
            up_pin_node = up_pin_node[0]
            for x in range(1000):
                if not up_pin_node.outputMatrix[x].isConnected():
                    free_index = x
                    break
    else:
        up_pin_node = pmc.createNode("uvPin")
        nurbs_shape.worldSpace[0].connect(up_pin_node.deformedGeometry)

    up_pin_node.coordinate[free_index].coordinateV.set(v_param)
    up_pin_node.coordinate[free_index].coordinateU.set(u_param)

    if decompose_name:
        decompose_mtx = pmc.createNode("decomposeMatrix", n=decompose_name)
        up_pin_node.outputMatrix[free_index].connect(decompose_mtx.inputMatrix)
        connections = (
            ("outputTranslate", "translate"),
            ("outputRotate", "rotate"),
            ("outputScale", "scale"),
        )

        for connection in connections:
            for axe in "XYZ":
                connection_names.append(
                    (f"{connection[0]}{axe}", f"{connection[1]}{axe}")
                )

    if loc_name:
        loc = pmc.createNode("locator").getTransform()
        loc.rename(loc_name)

    if loc_name and not decompose_name:
        up_pin_node.outputMatrix[free_index].connect(loc.offsetParentMatrix)

    elif decompose_name and loc_name:
        for con_name in connection_names:
            decompose_mtx.attr(f"{con_name[0]}").connect(
                loc.attr(f"{con_name[1]}")
            )

    result = namedtuple(
        "result",
        [
            "world_matrix_attr",
            "locator",
            "decompose_matrix",
            "decompose_matrix_connections",
        ],
    )
    return result(
        up_pin_node.outputMatrix[free_index],
        loc,
        decompose_mtx,
        connection_names,
    )


def reset_transform(trs):
    """
    Reset all channel of given transform.

    Args:
        trs(pmc.PyNode): The transform to reset

    """
    trs.translate.set(0.0, 0.0, 0.0)
    trs.rotate.set(0.0, 0.0, 0.0)
    trs.scale.set(1.0, 1.0, 1.0)


def reset_joint(jnt: pmc.PyNode) -> None:
    """
    Reset all channel of given joint.

    Args:
        jnt(pmc.PyNode): The transform to reset

    """
    jnt.jointOrient.set(0.0, 0.0, 0.0)
    reset_transform(jnt)


def compare_world_positions(source_node, target_node, raise_error=False):
    """
    Compare the wold position of to nodes. If they are on the same potion or not.

    Args:
        source_node(pmc.PyNode): The source node.
        target_node(pmc.PyNode): The target node.
        raise_error(bool): Raise error message or not.
                           Default is False.

    Returns:
        ValueError if positions are not equal and raise_error flag is True.
        False if positions are not equal and raise_error flag is False.
        True if positions are equal.

    """
    if source_node.getMatrix(worldSpace=True) != target_node.getMatrix(
        worldSpace=True
    ):
        if raise_error:
            raise ValueError("World positions not equal")
        else:
            return False
    return True


@DECORATORS.requires_plugins(["proxy_reference.py"])
def build_rig_pxo_reference_node(rig_lods, node_name, namespace):
    """Setup a proxy node with rig LODs.

    Args:
        rig_lods(list of dict): List of dicts with path and name attribute
        node_name (str): Name of the container node.
        namespace (str): Namespace for the container node.

    """
    return pmc.ProxyRefAssetFromJsonString(  # noqa: this will be created on fly
        name=node_name,
        ns=namespace,
        input=json.dumps(rig_lods),
        defaultProxy=rig_lods[0]["name"],  # Initially use the lowest LOD
    )


def create_rig_pxo_reference_from_sgid(published_file_id):
    """Create pxoReference node as rig container in anim from SGID of the rig version."""

    # Call SG to get published files paths
    published_files = paths_utils.get_rig_published_files(published_file_id)
    if not published_files:
        _LOGGER.info(
            "No published files could be loaded for ID {}".format(
                published_file_id
            )
        )
        return
    rig_lods = []
    for published_file in published_files:
        rig_lods.append(
            {
                "name": published_file["sg_usage"].split("-")[-1],
                "filepath": os.environ["PXO_PROJECTS_ROOT"]
                + published_file["path_cache"],
                "type": types.MB,
            }
        )

    node_name = published_files[0]["entity"]["name"]
    namespace = published_files[0]["sg_namespace"]
    if not namespace:
        namespace = f"{node_name.split('_')[-1][0:3]}_01"

    # Call build container
    build_rig_pxo_reference_node(rig_lods, node_name, namespace)

    return


@DECORATORS.requires_plugins(["maya-math-nodes"])
def pxo_constraining(
    masters,
    slaves,
    maintainOffset=False,
    name=None,
    skipRotate=None,
    skipTranslate=None,
    skipScale=True,
    native=False,
    space_switch=False,
    host=None,
    constraint_tag=None,
    use_parent_offset_mtx=False,
    weight_list=None,
    quaterion_rotation_slerp=True,
):

    """
    This function creates the baseline for constraints, right now it just does parentconstraints and has a switch
    this switch changes the maya native constraints to matrix constraints.

    Args:
        masters(list, pymel.core.PyNode): The master nodes as pmc.PyNode.
        slaves(list, pymel.core.PyNode): The slave nodes as pmc.PyNode.
        maintainOffset(bool): Maintain the slaves offsets.
                              Default is False.
        name(str, None): Constraint name. If None will take master name.
                   Default is None.
        skipRotate(bool, None): Skip rotate. If None will use rotation.
                          Default is None
        skipTranslate(bool, None): Skip translate. If None will use translation.
                             Default is None
        skipScale(bool, None): Skip scale. If None will use scale.
                         Default is None.
        native(bool): If True will create constraint instead of matrices.
        space_switch(bool): Will create a space switch setup.
        host(pmc.PyNode, None): The host controls for the space switch attribute.
                          Requieres the space_switch arg as True.

        constraint_tag(str/bool): Attribute added to the constraint to get its identity in the scene.

        use_parent_offset_mtx(bool): Determines if the Constraint will make use of the offset parent matrix or decompose.

    Returns:
        List: The constraint setup nodes.

    """
    #   sort out slaves and masters
    if not masters and slaves:
        raise ValueError("there was no given input for masters and slaves")

    if not isinstance(masters, list):
        masters = [masters]

    if not isinstance(slaves, list):
        slaves = [slaves]

    master_nodes = [pmc.PyNode(x) if isinstance(x, str) else x for x in masters]
    slave_nodes = [pmc.PyNode(x) if isinstance(x, str) else x for x in slaves]

    #   sort out weight interpolation
    weight_interpolation = 1.0 / len(master_nodes)

    #   sort out skipping behaviour
    skip_rotate = skip_transformation_component(skipRotate)
    skip_translate = skip_transformation_component(skipTranslate)
    skip_scale = skip_transformation_component(skipScale)

    consts = list()

    #   the basic maya constraint behaviour
    if native:
        for nde in slave_nodes:
            #   sort out naming
            constraint_nodes = create_native_constraints(
                maintainOffset,
                master_nodes,
                name,
                nde,
                skip_rotate,
                skip_scale,
                skip_translate,
                weight_interpolation,
            )

            consts.extend(constraint_nodes)

        [fix_constraint_attrs(con) for con in consts]

        return consts

    #   the maya node based setup
    else:
        return_dict = {}

        for nde in slave_nodes:
            host_attr_name = str(nde.name())
            host_attr_nice_name = "Ik Ref"

            #   get the world matrix of the slave node
            slave_world_pos = nde.getMatrix(worldSpace=True)

            #   get the parent of the slave
            parent_node = nde.getParent()

            #   before we go into the master node connections, check if we need a blend node
            blending_node = None

            nde_name = str(nde.shortName())

            if not constraint_tag:
                constraint_tag = nde_name

            if len(master_nodes) > 1:
                if not space_switch:

                    blending_node = create_constraint_subnode(
                        "wtAddMatrix", "bMtx", nde_name, constraint_tag
                    )
                    consts = blending_node
                    normalize_array_node = pmc.createNode("math_NormalizeArray")
                    normalize_array_node.isHistoricallyInteresting.set(0)

                else:
                    if host:
                        master_nodes_names = [x.name() for x in master_nodes]
                        master_nodes_enum = ":".join(master_nodes_names)
                        host.addAttr(
                            host_attr_name,
                            niceName=host_attr_nice_name,
                            at="enum",
                            enumName=master_nodes_enum,
                            k=False,
                        )
                        host.attr(host_attr_name).set(cb=True)
                        host.attr(host_attr_name).set(len(master_nodes) - 1)

                    matrix_chooser = create_constraint_subnode(
                        "choice", "cho", nde_name, constraint_tag
                    )

                    blending_node = matrix_chooser

            for iteration, mst in enumerate(master_nodes):
                matrix_out_attr = mst.worldMatrix[0]

                #   checks if there is an offset to maintain
                if maintainOffset:

                    #   calculates the offset amount
                    master_world_inv = mst.getMatrix(worldSpace=True).inverse()
                    offset_from_master = slave_world_pos * master_world_inv

                    #   applies the offset
                    master_offset_mmtx = create_constraint_subnode(
                        "math_MultiplyMatrix",
                        "masterOffset_mMtx",
                        nde_name,
                        constraint_tag,
                    )
                    master_offset_mmtx.isHistoricallyInteresting.set(0)
                    master_offset_mmtx.input1.set(offset_from_master, lock=True)

                    #   connects the master to its own offset
                    mst.worldMatrix[0].connect(master_offset_mmtx.input2)
                    matrix_out_attr = master_offset_mmtx.output

                #   adds offset for parent nodes
                parent_offset_mmtx = None
                if parent_node:
                    parent_offset_mmtx = create_constraint_subnode(
                        "math_MultiplyMatrix",
                        "parentOffset_mMtx",
                        nde_name,
                        constraint_tag,
                    )

                    matrix_out_attr.connect(parent_offset_mmtx.input1)
                    parent_node.worldInverseMatrix[0].connect(
                        parent_offset_mmtx.input2
                    )

                    matrix_out_attr = parent_offset_mmtx.output

                #   checks if there are multiple master nodes and connects them
                if blending_node:
                    if not space_switch:

                        mtx_attr = "wtMatrix[{0}].matrixIn".format(
                            str(iteration)
                        )
                        mtx_wgt = "wtMatrix[{0}].weightIn".format(
                            str(iteration)
                        )
                        blending_node.addAttr(
                            masters[iteration],
                            at=float,
                            min=0,
                            dv=weight_list[iteration]
                            if weight_list
                            else weight_interpolation,
                        )
                        blending_node.attr(masters[iteration]).setKeyable(True)
                        blending_node.attr(masters[iteration]).connect(
                            normalize_array_node.attr(f"input[{iteration}]")
                        )

                        normalize_array_node.attr(
                            f"output[{iteration}]"
                        ).connect(blending_node.attr(mtx_wgt))
                        matrix_out_attr.connect(blending_node.attr(mtx_attr))
                        matrix_out_attr = blending_node.matrixSum

                    else:

                        mtx_attr = "input[{0}]".format(str(iteration))
                        mtx_wgt = "selector"

                        if not host:
                            blending_node.attr(mtx_wgt).set(
                                len(master_nodes) - 1
                            )

                        matrix_out_attr.connect(blending_node.attr(mtx_attr))
                        matrix_out_attr = blending_node.output

            #   last output of the calculation, basically from here it should always stay the same
            if host and space_switch:
                host.attr(host_attr_name).connect(
                    blending_node.attr("selector")
                )

            if not use_parent_offset_mtx:
                decompose_matrix = create_constraint_subnode(
                    "decomposeMatrix", "dMtx", nde_name, constraint_tag
                )
                decompose_matrix.isHistoricallyInteresting.set(0)
                matrix_out_attr.connect(decompose_matrix.inputMatrix)

                #   finishing up the connections
                #   connect the maths to the slave based on exclusion lists

                connect_constraint_component(
                    "translate", decompose_matrix, nde, skip_translate
                )

                connect_constraint_component(
                    "rotate", decompose_matrix, nde, skip_rotate
                )

                connect_constraint_component(
                    "scale", decompose_matrix, nde, skip_scale
                )
            else:
                pick_matrix = create_constraint_subnode(
                    "pickMatrix", "pMtx", nde_name, constraint_tag
                )
                matrix_out_attr.connect(pick_matrix.inputMatrix, f=True)
                pick_matrix.outputMatrix.connect(nde.offsetParentMatrix, f=True)

                pick_matrix.useTranslate.set(not bool(skipTranslate), l=True)
                pick_matrix.useRotate.set(not bool(skipRotate), l=True)
                pick_matrix.useScale.set(not bool(skipScale), l=True)
                pick_matrix.useShear.set(not bool(skipScale), l=True)

                try:
                    nde.setTranslation((0, 0, 0))
                except pmc.MayaAttributeError:
                    pass

                try:
                    nde.setRotation((0, 0, 0))
                except pmc.MayaAttributeError:
                    pass

                try:
                    nde.setScale((1, 1, 1))
                except pmc.MayaAttributeError:
                    pass

        # todo add named tuple / dict

        return consts


def pxo_constraining2(
    masters,
    slaves,
    maintainOffset=False,
    skipRotate=False,
    skipTranslate=False,
    skipScale=True,
    constraint_tag=None,
    use_parent_offset_mtx=False,
    weight_list=None,
    quaterion_rotation_slerp=True,
):
    """
    This function creates the baseline for constraints, right now it just does parentconstraints and has a switch
    this switch changes the maya native constraints to matrix constraints.

    Args:
        masters(list): The master nodes as pmc.PyNode.
        slaves(list): The slave nodes as pmc.PyNode.
        maintainOffset(bool): Maintain the slaves offsets.
                              Default is False.
        skipRotate(bool, None): Skip rotate. If None will use rotation.
                          Default is None
        skipTranslate(bool, None): Skip translate. If None will use translation.
                             Default is None
        skipScale(bool, None): Skip scale. If None will use scale.
                         Default is None.

        constraint_tag(str/bool): Attribute added to the constraint to get its identity in the scene.

        use_parent_offset_mtx(bool): Determines if the Constraint will make use of the offset parent matrix or decompose.

    Returns:
        List: The constraint setup nodes.

    """
    #   sort out slaves and masters
    if not masters or not slaves:
        raise ValueError("Masters and slaves must be provided.")

    master_nodes = convert_to_pynode_list(masters)
    slave_nodes = convert_to_pynode_list(slaves)

    weight_interpolation = 1.0 / len(masters)

    consts = []

    for slave in slave_nodes:
        constraint_tag = constraint_tag or str(slave.shortName())
        slave_world_pos = slave.getMatrix(worldSpace=True)
        parent_node = slave.getParent()

        blending_node = None

        if len(masters) > 1:
            blending_node = pmc.createNode(
                "wtAddMatrix", name=f"{slave.name()}_bMtx_{constraint_tag}"
            )
            normalize_array_node = pmc.createNode("math_NormalizeArray")
            normalize_array_node.isHistoricallyInteresting.set(0)
            consts.append(blending_node)

        for i, mst in enumerate(master_nodes):
            matrix_out_attr = mst.worldMatrix[0]

            if maintainOffset:
                offset_from_master = (
                    slave_world_pos * mst.getMatrix(worldSpace=True).inverse()
                )
                master_offset_mmtx = pmc.createNode(
                    "math_MultiplyMatrix",
                    name=f"{slave.name()}_masterOffset_mMtx_{constraint_tag}",
                )
                master_offset_mmtx.isHistoricallyInteresting.set(0)
                master_offset_mmtx.input1.set(offset_from_master, lock=True)
                mst.worldMatrix[0].connect(master_offset_mmtx.input2)
                matrix_out_attr = master_offset_mmtx.output

                if quaterion_rotation_slerp:
                    pass

            if parent_node:
                parent_offset_mmtx = pmc.createNode(
                    "math_MultiplyMatrix",
                    name=f"{slave.name()}_parentOffset_mMtx_{constraint_tag}",
                )
                matrix_out_attr.connect(parent_offset_mmtx.input1)
                parent_node.worldInverseMatrix[0].connect(
                    parent_offset_mmtx.input2
                )
                matrix_out_attr = parent_offset_mmtx.output

            if blending_node:
                blending_node.addAttr(
                    masters[i],
                    at=float,
                    min=0,
                    dv=weight_list[i] if weight_list else weight_interpolation,
                )
                blending_node.attr(masters[i]).setKeyable(True)
                blending_node.attr(masters[i]).connect(
                    normalize_array_node.attr(f"input[{i}]")
                )
                normalize_array_node.attr(f"output[{i}]").connect(
                    blending_node.attr(f"wtMatrix[{i}].weightIn")
                )
                matrix_out_attr.connect(
                    blending_node.attr(f"wtMatrix[{i}].matrixIn")
                )
                matrix_out_attr = blending_node.matrixSum

        if use_parent_offset_mtx:
            pick_matrix = pmc.createNode(
                "pickMatrix", name=f"{slave.name()}_pMtx_{constraint_tag}"
            )
            matrix_out_attr.connect(pick_matrix.inputMatrix)
            pick_matrix.outputMatrix.connect(slave.offsetParentMatrix)
            pick_matrix.useTranslate.set(not skipTranslate, l=True)
            pick_matrix.useRotate.set(not skipRotate, l=True)
            pick_matrix.useScale.set(not skipScale, l=True)
            pick_matrix.useShear.set(not skipScale, l=True)
            slave.setTranslation((0, 0, 0), worldSpace=True)
            slave.setRotation((0, 0, 0), worldSpace=True)
            slave.setScale((1, 1, 1))
        else:
            decompose_matrix = pmc.createNode(
                "decomposeMatrix", name=f"{slave.name()}_dMtx_{constraint_tag}"
            )
            decompose_matrix.isHistoricallyInteresting.set(0)
            matrix_out_attr.connect(decompose_matrix.inputMatrix)

            if not skipTranslate:
                decompose_matrix.outputTranslate.connect(slave.translate)
            if not skipRotate:
                decompose_matrix.outputRotate.connect(slave.rotate)
            if not skipScale:
                decompose_matrix.outputScale.connect(slave.scale)

    return consts


def convert_to_pynode_list(nodes):
    """
    Ensure the input is a list and convert any string elements to pmc.PyNode objects.

    Args:
        nodes (str, pmc.PyNode, or list): A single node as a string or pmc.PyNode, or a list of nodes.

    Returns:
        list: A list of pmc.PyNode objects.
    """
    if not isinstance(nodes, list):
        nodes = [nodes]

    converted_nodes = []
    for node in nodes:
        if isinstance(node, str):
            converted_nodes.append(pmc.PyNode(node))
        else:
            converted_nodes.append(node)

    return converted_nodes


def create_native_constraints(
    maintain_offset,
    master_nodes,
    constraint_name,
    slave_node,
    skip_rotate,
    skip_scale,
    skip_translate,
    weight_interpolation,
):
    """
    Wrapper to create maya native parent and scale constraints for the pxo_constraining method.

    Args:
        maintain_offset(bool): Check if Offset will be maintained.
        master_nodes(list): List of PyNodes that are the masters of the constraint.
        constraint_name(str): Name of the Constraint that will be created.
        slave_node(pymel.core.PyNode): PyNode that is the slave of the constraint.
        skip_rotate(list): List of axis that will be skipped.
        skip_scale(list): List of axis that will be skipped.
        skip_translate(list): List of axis that will be skipped.
        weight_interpolation(float): VALUE TO BE IMPLEMENTED FURTHER

    Returns:
        List(consts): List of created constraint nodes.

    """

    consts = list()
    node_name = str(slave_node.shortName())

    if not constraint_name:
        master_part = master_nodes[0].shortName()
        slave_part = node_name
        constraint_name = "{0}TO{1}_prc".format(master_part, slave_part)

    parent_constraint = pmc.parentConstraint(
        master_nodes,
        slave_node,
        name=constraint_name,
        skipTranslate=skip_translate,
        skipRotate=skip_rotate,
        weight=weight_interpolation,
        maintainOffset=maintain_offset,
    )

    add_metadata_to_constraint_nodes(
        constraint_name, parent_constraint, node_name
    )
    consts.append(parent_constraint)

    if not skip_scale:
        scale_constraint = pmc.scaleConstraint(
            master_nodes,
            slave_node,
            name=constraint_name.replace("prc", "scc"),
            weight=weight_interpolation,
            skip=skip_scale,
            maintainOffset=maintain_offset,
        )

        add_metadata_to_constraint_nodes(
            constraint_name, parent_constraint, node_name
        )
        consts.append(scale_constraint)

    return consts


def create_constraint_subnode(nodetype, node_suffix, node_name, constraint_tag):
    """
    Wrapper to build nodes with added metadata for constraint tracking in scene.

    Args:
        nodetype(str): String of the nodetype that will be created.
        node_suffix(str): String of the suffix.
        node_name(str): String of the node name.
        constraint_tag(str): String of the tag that will be assigned

    Returns:
        pymel.core.PyNode(created_node): The created PyNode

    """

    if not constraint_tag:
        constraint_tag = node_name

    created_node = pmc.createNode(
        nodetype, n="{0}_{1}".format(node_name, node_suffix)
    )
    add_metadata_to_constraint_nodes(constraint_tag, created_node, node_name)

    return created_node


def add_metadata_to_constraint_nodes(constraint_tag, created_node, node_name):
    """
    Adds the constraint metadata to created node.

    Args:
        constraint_tag(str): Name of the constraint for scene search purposes.
        created_node(pymel.core.PyNode): Node to be tagged.
        node_name(str): Name of the node.

    """
    # add tag as a constraint
    created_node.addAttr(constants.PXO_CONSTRAINT_TAG, at="bool")

    # name of the constrained object
    created_node.addAttr(constants.PXO_CONSTRAINT_OBJECT_NAME, dt="string")
    created_node.attr(constants.PXO_CONSTRAINT_OBJECT_NAME).set(
        "{0}_constraint".format(node_name), type="string"
    )

    # name of the operation the nodes are part of
    created_node.addAttr(constants.PXO_CONSTRAINT_GROUPED, dt="string")
    created_node.attr(constants.PXO_CONSTRAINT_GROUPED).set(
        "{0}".format(constraint_tag), type="string"
    )


def fix_constraint_attrs(const):
    """
    Sets the default settings for constraints.

    Args:
        const(pymel.core.PyNode): Constraint node for which the attrs will be set.

    """
    if const.hasAttr("interpType"):
        const.interpType.set(2)

    if const.hasAttr("template"):
        const.template.set(1)

    if const.hasAttr("visibility"):
        const.visibility.set(0)


def connect_constraint_component(
    component_name, decompose_matrix, node, skip_transformation
):
    """
    Connects the Decompose Matrix with the specified Transformation.

    Args:
        component_name(str): Transformation component (translate / rotate / scale).
        decompose_matrix(pymel.core.PyNode): Decompose Matrix Node.
        node(pymel.core.PyNode): Node that will get the input.
        skip_transformation(list): List of attributes that will be skipped in the connection.

    """

    translate_axis = list({"x", "y", "z"} - set(skip_transformation))
    for axe in translate_axis:
        axe_c = axe.capitalize()
        node_attr = node.attr("{0}{1}".format(component_name, axe_c))
        if node_attr.isLocked():
            try:
                node_attr.set(lock=False)
            except:
                _LOGGER.warning(
                    f"{str(node_attr.name())} unable to unlock maybe it == from a referenced file."
                )
                pass
        decompose_matrix.attr(
            "output{0}{1}".format(component_name.capitalize(), axe_c)
        ).connect(node.attr("{0}{1}".format(component_name, axe_c)), force=True)


def skip_transformation_component(skip_transformation):
    """
    Converts the skipTransformation Value into the formatted Value for the constraint.

    Args:
        skip_transformation(list, bool): Inputs to build the skip list.

    Returns:
        List(skip_transformation): List of attrs to be skipped.
    """
    if skip_transformation is True:
        skip_transformation = ["x", "y", "z"]

    if not skip_transformation:
        skip_transformation = []

    return skip_transformation


def get_deformers_for_shape(mesh):
    """
    Get the deformers from an object's history that only
    effect that particular mesh, and not inputs from other
    meshes (IE, meshes driving blendshapes).

    Args:
        mesh(pmc.PyNode): The mesh node with deformer inputs.

    Returns:
        exception.MayaNodeNotFound: If no deform shape found or new deformer creation with component tags in use.
        List: Filled with pmc.PyNode() for each found deformer.

    """
    result = []
    shape_sets = []
    geometry_filters = pmc.ls(pmc.listHistory(mesh), type="geometryFilter")
    shape = dag_utils.get_deform_shape(mesh)

    if shape is not None:
        shape_sets = pmc.ls(pmc.listConnections(str(shape)), type="objectSet")
    else:
        exceptions.MayaNodeNotFound(f"No deform shape found for {mesh}")

    if not shape_sets:
        exceptions.MayaNodeNotFound(
            "No deformer object set found. Maybe new deformer"
            " creation with component tags in use."
        )

    for deformer in geometry_filters:

        def_set = pmc.ls(pmc.listConnections(deformer), type="objectSet")

        if def_set:
            def_set = def_set[0]

        if def_set in shape_sets:
            result.append(deformer)

    print(geometry_filters)
    return result


def locator_on_curve_to_closest_point_of_target(
    target, curve, name=None, param_on_crv=None
):
    """
    Will create a locator node on a curve to the closest point
    of an given target node.

    Args:
        target(pmc.PyNode()): The target node to calculate the closest point.
        curve(pmc.PyNode()): The curve to add the transform on.
        name(str): The locators name. If none will take
                   the curve name and add "_loc" as suffix.
        param_on_crv(float, optional): The param value to place the
                                       locator on the curve.

    Return:
        pmc.PyNode(): Locator on the curve.

    """
    if not name:
        name = "{}_loc".format(curve.name())
    curve_shape = curve.getShape()
    if not param_on_crv:
        nearest_po_crv = pmc.createNode("nearestPointOnCurve")
        curve_shape.worldSpace[0].connect(nearest_po_crv.inputCurve)
        decomp_nd = pmc.createNode("decomposeMatrix")
        target.worldMatrix[0].connect(decomp_nd.inputMatrix)
        decomp_nd.outputTranslate.connect(nearest_po_crv.inPosition)
        param_on_crv = nearest_po_crv.result.parameter.get()
        pmc.delete([nearest_po_crv, decomp_nd])
    mo_nd = pmc.createNode("motionPath")
    loc = pmc.createNode("locator")
    loc_trs = loc.getTransform()
    loc_trs.rename(name)
    curve_shape.worldSpace[0].connect(mo_nd.geometryPath)
    mo_nd.uValue.set(param_on_crv)
    for axe in "XYZ":
        mo_nd.attr("allCoordinates.{}Coordinate".format(axe.lower())).connect(
            loc.getTransform().attr("translate{}".format(axe))
        )
    return loc_trs


def closest_point_on_poly_constraint(
    master_mesh,
    slave_ctrl,
    aim_object=None,
    rotation_mode="normal",
    aimV=(0, 0, 1),
    wupVct=(0, 1, 0),
    UpType="object",
):
    """
    Creates a closest point on mesh constrain master_mesh and a slave_ctrl, it creates a trsf group on top fo the ctrl

    Args:
        master_mesh(pmc.PyNode): the master mesh for the constraint
        slave_ctrl(pmc.PyNode): the proper control, _ctl
        for the argument of the constraint look maya documentation:
            aim_object(str)
            rotation_mode(str)
            aimV
            wupVct,
            UpType

    Returns:
        the trsf group were the constraint is applied and the constraint if created

    """
    slave_ctrl_parent = slave_ctrl.getParent()
    constrained_group = pmc.group(
        em=True, name=slave_ctrl.name().replace("_ctrl", "_clspnt_trs")
    )
    offs_Grp = pmc.group(
        slave_ctrl, name=slave_ctrl.name().replace("_ctrl", "_off")
    )
    pmc.matchTransform(constrained_group, slave_ctrl)
    pmc.parent(constrained_group, slave_ctrl_parent)

    cpom_node = pmc.createNode("closestPointOnMesh")
    obj_decompose_node = pmc.createNode("decomposeMatrix")
    compose_matrix_node = pmc.createNode("composeMatrix")
    mult_matrix_node = pmc.createNode("multMatrix")

    # Connections using .connect()
    master_mesh.outMesh.connect(cpom_node.inMesh)
    master_mesh.worldMatrix[0].connect(cpom_node.inputMatrix)

    slave_ctrl_parent.worldMatrix[0].connect(obj_decompose_node.inputMatrix)
    obj_decompose_node.outputTranslate.connect(cpom_node.inPosition)

    cpom_node.result.position.connect(compose_matrix_node.inputTranslate)

    compose_matrix_node.outputMatrix.connect(mult_matrix_node.matrixIn[0])
    slave_ctrl_parent.worldInverseMatrix[0].connect(
        mult_matrix_node.matrixIn[1]
    )

    mult_matrix_node.matrixSum.connect(constrained_group.offsetParentMatrix)
    if rotation_mode == "normal":
        constr = pmc.normalConstraint(
            master_mesh,
            constrained_group,
            aimVector=aimV,
            worldUpType=UpType,
            upVector=wupVct,
            worldUpObject=aim_object,
        )
    elif rotation_mode == "orient":
        constr = pmc.orientConstraint(aim_object, constrained_group, mo=True)

    offs_Grp.setParent(constrained_group)
    return constrained_group, constr


def blend_2_spaces(
    node0,
    node1,
    control,
    host=None,
    attr_name="blend",
    host_attr_name="main_blend",
    default_value=1.0,
):
    """
    Create a basic worldspace matrix constraint node tree. Without an offset and create a blend attribute to blend
    between the 2

    Args:
        node0(pmc.PyNode, str): The node that will have value 0.
        node1(pmc.PyNode, str): the node that will have value 1.
        control(pmc.PyNode, str): The target node to be constraint to.
        host(pmc.PyNode, str): The node that will have the attribute, if none control is used
        attr_name(str): The name for the blend attribute.
                        Default is "blend".
        host_attr_name(str): The blend attribute on the host control.
                             Default is "main_blend"
        default_value(float): The blend attribute default value.
                              Default is 1.

    Return:
          Tuple: The created mult matrix and decompose matrix node.

    """
    if not isinstance(node1, pmc.PyNode):
        node1 = pmc.PyNode(node1)
    if not isinstance(node0, pmc.PyNode):
        node0 = pmc.PyNode(node0)
    if not isinstance(control, pmc.PyNode):
        control = pmc.PyNode(control)

    blend_matrix = pmc.createNode("blendMatrix")
    mult_matrix = pmc.createNode("multMatrix")

    node0.worldMatrix[0].connect(blend_matrix.inputMatrix)
    node1.worldMatrix[0].connect(blend_matrix.target[0].targetMatrix)

    blend_matrix.outputMatrix.connect(mult_matrix.matrixIn[0])

    if not control.hasAttr(attr_name):
        control.addAttr(
            attr_name,
            at="float",
            dv=default_value,
            min=0,
            max=1,
            k=True,
        )
        control.attr(attr_name).set(cb=True)
    if host:
        if not isinstance(host, pmc.PyNode):
            host = pmc.PyNode(host)
        if not host.hasAttr(host_attr_name):
            host.addAttr(
                host_attr_name, at="float", dv=default_value, min=0, max=1, k=True
            )
            host.attr(host_attr_name).set(cb=True)

        multiply = pmc.createNode("math_Multiply")

        host.attr(host_attr_name).connect(multiply.input1)
        control.attr(attr_name).connect(multiply.input2)
        multiply.output.connect(blend_matrix.target[0].weight)
    else:
        control.attr(attr_name).connect(blend_matrix.target[0].weight)

    parent = control.getParent()
    parent.worldInverseMatrix[0].connect(mult_matrix.matrixIn[1])
    mult_matrix.matrixSum.connect(control.offsetParentMatrix)
    return mult_matrix


def hide_non_dag_history():
    """
    Hides the non dag history for all non dag objects in the scene.

    """
    non_dags = [
        str(node)
        for node in cmds.ls()
        if not cmds.objectType(node, isa="dagNode")
    ]

    [
        cmds.setAttr("{0}.isHistoricallyInteresting".format(non_dag), False)
        for non_dag in non_dags
    ]


def show_non_dag_history():
    """
    Reveals the non dag history for all non dag objects in the scene.

    """

    non_dags = [
        str(node)
        for node in cmds.ls()
        if not cmds.objectType(node, isa="dagNode")
    ]

    [
        cmds.setAttr("{0}.isHistoricallyInteresting".format(non_dag), True)
        for non_dag in non_dags
    ]


def get_object_size(object_node):
    """
    Get the object size from object bounding box.

    Args:
        object_node(pmc.PyNode): The object we want the size from.

    Returns:
        Tuple: The size in all three dimensions.

    """
    box_min_x = abs(float(object_node.getAttr("boundingBoxMinX")))
    box_max_x = float(object_node.getAttr("boundingBoxMaxX"))
    box_x = box_max_x + box_min_x

    box_min_y = abs(float(object_node.getAttr("boundingBoxMinY")))
    box_max_y = float(object_node.getAttr("boundingBoxMaxY"))
    box_y = box_max_y + box_min_y

    box_min_z = abs(float(object_node.getAttr("boundingBoxMinZ")))
    box_max_z = float(object_node.getAttr("boundingBoxMaxZ"))
    box_z = box_max_z + box_min_z

    return (box_x + box_y + box_z) / 3.0


def get_object_size2(obj_nd):
    """
    Get object size from object bounding box with the bounding box width, depth and height.
    Inlcudes invisible objects as well.

    Args:
        obj_nd(pmc.PyNode()): The object which we want the objec size from.

    Returns:
        Float: The object size.
    """
    bounding_box = obj_nd.getBoundingBox(True)
    return (
        float(bounding_box.height())
        + float(bounding_box.width())
        + float(bounding_box.depth())
    ) / 3.0


def get_exact_world_object_size(object_nodes):
    """
    Will calculate a exact world bounding box which includes all given nodes.

    Args:
        object_nodes(list): The object we want to include.

    Returns:
        Tuple(object_size, (scale_x, scale_y, scale_z))
    """
    for node in object_nodes:
        if get_object_size2(node) < 0.0 or get_object_size2(node) == 0.0:
            return 0.0, (0.0, 0.0, 0.0)
    bbox = [float(val) for val in pmc.exactWorldBoundingBox(object_nodes)]
    box_x = abs(bbox[0]) + bbox[3]
    box_y = abs(bbox[1]) + bbox[4]
    box_z = abs(bbox[2]) + bbox[5]
    return (box_x + box_y + box_z) / 3, (box_x, box_y, box_z)


def get_object_center(node):
    """
    Get object center point from bounding box of given node.

    Args:
        node(pmc.PyNode): The node which we want the center pivot of.

    Returns:
        Point(): The center point.

    """
    return node.getBoundingBox(True, space="world").center()


def get_avg_object_center(nodes):
    """
    Get the average object center of given nodes.

    Args:
        nodes(list): The objects we want the average center from.

    Returns:
        dt.Position: The average center position.
    """
    object_centers = [get_object_center(node) for node in nodes]
    return (
        mean([pos[0] for pos in object_centers]),
        mean([pos[1] for pos in object_centers]),
        mean([pos[2] for pos in object_centers]),
    )


def create_distance_lerp(system_root, system_tip):
    """
    Create a distance lerp setup from two objects.

    Args:
        system_root(pmc.PyNode): The start object.
        system_tip(pmc.PyNode): The end object.

    Returns:
        Tuple:
                (Attribute(distance_remap_clamp_nde.inputMin),
                 Attribute(distance_remap_clamp_nde.inputMax),
                 Attribute(distance_remap_clamp_nde.outValue))
    """
    system_root_vec = pmc.datatypes.Vector(
        system_root.getTranslation(space="world")
    )
    system_tip_vec = pmc.datatypes.Vector(
        system_tip.getTranslation(space="world")
    )
    starting_distance = system_root_vec.distanceTo(system_tip_vec)

    distance_between_nde = pmc.createNode("math_DistanceTransforms")
    distance_remap_clamp_nde = pmc.createNode("remapValue")

    system_root.worldMatrix.connect(distance_between_nde.input1)
    system_tip.worldMatrix.connect(distance_between_nde.input2)

    distance_between_nde.output.connect(distance_remap_clamp_nde.inputValue)
    distance_remap_clamp_nde.inputMax.set(starting_distance)

    return (
        distance_remap_clamp_nde.inputMin,
        distance_remap_clamp_nde.inputMax,
        distance_remap_clamp_nde.outValue,
    )


def create_angular_lerp(
    system_root, system_tip, effected_attr, effected_host_attr
):

    """
    Creates a angular lerp system for given two objects.

    Args:
        system_root(pmc.PyNode): The start object.
        system_tip(pmc.PyNode): The end object.
        effected_attr(pmc.Attribute): The effected lerp attribute.
        effected_host_attr(pmc.Attribute): The control attribute on given host control.

    Returns:
        pmc.PyNode: The math_LerpAngle node.

    """
    input_min_attr, input_max_attr, output_attr = create_distance_lerp(
        system_root, system_tip
    )
    input_min_attr, input_max_attr, output_attr = create_distance_lerp(
        system_root, system_tip
    )

    angle_lerp = pmc.createNode("math_LerpAngle")
    output_attr.connect(angle_lerp.alpha)
    effected_host_attr.connect(angle_lerp.input1)
    angle_lerp.output.connect(effected_attr)

    return angle_lerp


def add_soft_mod(
    geo_list, controller, falloff_radius=2, connect_falloff_center=False
):
    """
    Adds a softMod deformer to the specified geometry with a controller.
    The deformer's falloff radius is managed by an attribute on the controller.

    Args:
        geo_list(list): List of geometries to which the softMod deformer will be applied.
        controller(pmc.nt.Transform): The controller object that will manage the softMod deformer.
        falloff_radius(float, optional): The default falloff radius for the softMod deformer.
                                          Defaults to 2.
        connect_falloff_center(bool): Connect the falloff center of the soft mod to the controllers parent.
                                      Default is False

    Returns:
        Tuple: A tuple containing the softMod deformer node and its handle.
    """
    if not controller.hasAttr("falloffRadius"):
        controller.addAttr(
            "falloffRadius", at="double", min=0, dv=falloff_radius
        )
        controller.falloffRadius.setKeyable(True)

    controller_position = pmc.xform(controller, q=True, ws=True, t=True)
    soft_mod_name = controller.replace("control_default_ctrl", "softMod")
    soft_mod, soft_mod_handle = pmc.softMod(
        geo_list,
        fc=controller_position,
        fr=controller.falloffRadius.get(),
        falloffAroundSelection=False,
        n=soft_mod_name,
        rel=True,
    )
    grp_name = controller.replace("control_default_ctrl", "softModGRP")
    grp = pmc.group(soft_mod_handle, n=grp_name)
    pmc.parent(grp, controller.getParent())
    pmc.parentConstraint(controller, soft_mod_handle, mo=True)
    if connect_falloff_center:
        dcmp_matrix = pmc.createNode("decomposeMatrix")
        controller.getParent().worldMatrix[0].connect(dcmp_matrix.inputMatrix)
        dcmp_matrix.outputTranslate.connect(soft_mod.falloffCenter)
    controller.falloffRadius.connect(soft_mod.falloffRadius)
    grp.visibility.set(0)

    return soft_mod, soft_mod_handle


def create_primitive_falloff(
    name="primitiveFalloff",
    start=0.0,
    end=1.0,
    use_original_geometry=True,
    shape="plane",
    scale=50.0,
):
    """
    Creates a primitive falloff node.

    Args:
        name(str): Name of the falloff.
        start(float): Clipping plane start value.
        end(float): Clipping plane end value.
        use_original_geometry(bool): Use original geometry as driver.
        shape(str): The falloff shape.
                    Valid is ["sphere", "plane"]
                    Default is "plane".
        scale(float): The scale value.
                      Default is 50.0

    Returns:
        pmc.PyNode: The fall off node.

    """
    falloff_node = pmc.createNode("primitiveFalloff", name=name)

    falloff_node.start.set(start)
    falloff_node.end.set(end)
    falloff_node.useOriginalGeometry.set(use_original_geometry)
    falloff_node.primitive.set(1 if shape == "plane" else 0)
    falloff_node.scaleX.set(scale)
    falloff_node.scaleY.set(scale)
    falloff_node.scaleZ.set(scale)

    return falloff_node


def set_driven_key(data_dict):
    """
    Set driven keyframes based on a dictionary mapping attributes to their values.

    Parameters:
    data_dict (dict): A dictionary where the first key-value pair is the master attribute and its values,
                      and the remaining pairs are the target attributes with their corresponding values.

    Raises:
    ValueError: If the lengths of the lists in the dictionary values are not the same.
    """
    # Check if all lists in the values have the same length
    value_lengths = [len(values) for values in data_dict.values()]
    if len(set(value_lengths)) > 1:
        raise ValueError(
            "All lists in the dictionary values must have the same length."
        )

    # Decompose the data
    master_attr = pmc.PyNode(list(data_dict.keys())[0])
    target_attr_list = list(data_dict.keys())[1:]

    master_values = list(data_dict.values())[0]

    # Set driven keyframes
    for i, master_val in enumerate(master_values):
        for target_attr in target_attr_list:
            pmc.setDrivenKeyframe(
                target_attr,
                value=data_dict[target_attr][i],
                currentDriver=master_attr,
                driverValue=master_val,
            )


def create_wrap_deformer(
    influence,
    surface,
    weight_threshold=1.0,
    max_distance=1.0,
    exclusive_bind=True,
    auto_weight_threshold=True,
    falloff_mode=0,
):
    """
    Create wrap deformer.

    Args:
        influence(pmc.PyNode()): The influnce object.
        surface(pmc.PyNode()): The surface object to deform.
        weight_threshold(float): The weighted threshold.
        max_distance(float): The max distance.
        exclusive_bind(bool): Enable/Disable exclusiveBind.
        auto_weight_threshold(bool): Enable/Disable autoWeightThreshold.
        falloff_mode(int): Valid values are [0: Volume, 1: Surface]

    Return:
        pmc.PyNode(): The created wrap deformer.

    """
    influence_shape = influence.getShape(noIntermediate=True).name()
    influence = influence.name()
    surface = surface.name()
    # create wrap deformer
    max_distance = max_distance
    exclusive_bind = exclusive_bind
    auto_weight_threshold = auto_weight_threshold
    falloff_mode = falloff_mode
    wrap_data = cmds.deformer(surface, type="wrap")
    wrap_node = wrap_data[0]

    # set attributes on wrap node
    cmds.setAttr("{0}.weightThreshold".format(wrap_node), weight_threshold)
    cmds.setAttr("{0}.maxDistance".format(wrap_node), max_distance)
    cmds.setAttr("{0}.exclusiveBind".format(wrap_node), exclusive_bind)
    cmds.setAttr(
        "{0}.autoWeightThreshold".format(wrap_node), auto_weight_threshold
    )
    cmds.setAttr("{0}.falloffMode".format(wrap_node), falloff_mode)

    # connect geometry to wrap node
    cmds.connectAttr(
        "{0}.worldMatrix[0]".format(surface), "{0}.geomMatrix".format(wrap_node)
    )

    # add influence
    base = pmc.duplicate(influence, name="{0}Base".format(influence))[0]
    dag_utils.delete_hidden_shapes(base)
    base.visibility.set(0)
    base_shape = str(base.getShape().name())

    # create dropoff attr if it doesn't exist
    if not cmds.attributeQuery("dropoff", n=influence, exists=True):
        cmds.addAttr(
            influence, sn="dr", ln="dropoff", dv=4.0, min=0.0, max=20.0
        )
        cmds.setAttr("{0}.dr".format(influence), k=True)

    # if type mesh
    if cmds.nodeType(influence_shape) == "mesh":
        # create smoothness attr if it doesn't exist
        if not cmds.attributeQuery("smoothness", n=influence, exists=True):
            cmds.addAttr(influence, sn="smt", ln="smoothness", dv=0.0, min=0.0)
            cmds.setAttr("{0}.smt".format(influence), k=True)
        # create the inflType attr if it doesn't exist
        if not cmds.attributeQuery("inflType", n=influence, exists=True):
            cmds.addAttr(
                influence,
                at="short",
                sn="ift",
                ln="inflType",
                dv=2,
                min=1,
                max=2,
            )
        cmds.connectAttr(
            "{0}.worldMesh".format(influence_shape),
            "{0}.driverPoints[0]".format(wrap_node),
        )
        cmds.connectAttr(
            "{0}.worldMesh".format(base_shape),
            "{0}.basePoints[0]".format(wrap_node),
        )
        cmds.connectAttr(
            "{0}.inflType".format(influence),
            "{0}.inflType[0]".format(wrap_node),
        )
        cmds.connectAttr(
            "{0}.smoothness".format(influence),
            "{0}.smoothness[0]".format(wrap_node),
        )
    # if type nurbsCurve or nurbsSurface
    if (
        cmds.nodeType(influence_shape) == "nurbsCurve"
        or cmds.nodeType(influence_shape) == "nurbsSurface"
    ):
        # create the wrapSamples attr if it doesn't exist
        if not cmds.attributeQuery("wrapSamples", n=influence, exists=True):
            cmds.addAttr(
                influence,
                at="short",
                sn="wsm",
                ln="wrapSamples",
                dv=10,
                min=1,
            )

            cmds.setAttr("{0}.wsm".format(influence), k=True)
        cmds.connectAttr(
            "{0}.ws".format(influence_shape),
            "{0}.driverPoints[0]".format(wrap_node),
        )
        cmds.connectAttr(
            "{0}.ws".format(base_shape), "{0}.basePoints[0]".format(wrap_node)
        )
        cmds.connectAttr(
            "{0}.wsm".format(influence), "{0}.nurbsSamples[0]".format(wrap_node)
        )
    cmds.connectAttr(
        "{0}.dropoff".format(influence), "{0}.dropoff[0]".format(wrap_node)
    )

    return wrap_node, base


def add_pxo_anim_tags(
    anim_controls,
):
    """
    Add alll needed PXO animation tags to the animation controls.

    Args:
        anim_controls(list): The animation controls.

    """
    # Tag all curve with the pxm anim control tag.
    for anim_curve in anim_controls:
        tagging_utils.create_tag(anim_curve, TAG_EXPORT_ANIMATION)
        tagging_utils.set_tag(anim_curve, TAG_EXPORT_ANIMATION, True)
        if not anim_curve.hasAttr(constants.RIG_SYS_CONTROL_TAG):
            anim_curve.addAttr(
                constants.RIG_SYS_CONTROL_TAG, type="bool", keyable=False
            )


def reformat_mgear_seperator_enums(host_nd):
    """
    Will change the mgear separator enum to PXO design.

    Args:
        host_nd(pmc.PyNode()): The mgear host control.

    """
    sep_attributes = [
        attr_
        for attr_ in host_nd.listAttr(ud=True)
        if attr_.type() == "enum"
        and "__________" in pmc.addAttr(attr_, query=True, niceName=True)
    ]
    if sep_attributes:
        for sep_attr in sep_attributes:
            enum_dict = sep_attr.getEnums()
            pmc.addAttr(
                sep_attr,
                edit=True,
                niceName=enum_dict.key(0),
                enumName="########",
            )
            sep_attr.lock()


def reformat_mgear_spaces_enums(host_nd):
    """
    Method will change the mgear enum attributes to PXO design.

    Args:
        host_nd(pmc.PyNode()): The mgear host control.

    """
    ikref_attributes = [
        attr_
        for attr_ in host_nd.listAttr(ud=True)
        if attr_.type() == "enum" and constants.IK_REF_ENUM_STR in attr_.name()
    ]
    for ikref_enum in ikref_attributes:
        enum_dict = ikref_enum.getEnums()
        new_enums = ":".join(
            [enum_dict[x].split("_")[0] for x in range(len(enum_dict))]
        )
        pmc.addAttr(ikref_enum, edit=True, enumName=new_enums)


def create_rig_pxoAsset_node(asset_name, network_node=True):
    """
    Creates a pxoAsset rig root node.

    Args:
        asset_name(str): The asset name
        network_node(bool): Creates the pxoAsset network node.
                            Default is True

    Returns:
            pmc.PyNode: The newly created pxoAsset node.
    """
    asset_data = {
        "asset_name": asset_name,
        "asset_type": "rig",
        "usage": "render",
        "asset_sub_type": "default",
        "component": "default",
        "variant": "default",
    }
    asset_name = asset_node.get_default_asset_name(asset_data)
    return asset_node.create_pxo_asset(
        asset_data,
        asset_name,
        network_node,
    )


def _reload_pxo_ref_node(mdl_nodes):
    """
    Will reload the proxy reference asset node as gpu cache.

    Args:
        mdl_nodes(list): List of mdl top nodes.

    Returns:
        Will fail if proxyReferenceAsse nodes are not children of the selected mdl top nodes.
    """
    for mdl_node in mdl_nodes:
        proxy_ref_nd = mdl_node.getChildren(type="proxyReferenceAsset")[0]
        pmc.select(proxy_ref_nd)
        interaction.switch_selected("gpu")


def _import_and_build_rig_template_simple_rig(
    mdl_nodes, obj_size, pxo_asset=False
):
    """
    Import and build rig template for the simple rig approach.

    Args:
        mdl_nodes(list): The mdl root nodes.
        obj_size(float): The obj size.
        pxo_asset(bool): Mdl data assembled by a pxoAsset node.
                         If false we assume that the data is assembled by a proxyReferenceAsset (gpu cache) node.

    Returns:
        Tuple: (guide_root_node, asset_assembly_node)
    """
    assembly_node = None
    guide_template = "Proxy Rig"
    if pxo_asset:
        # If we are using the pxo asset node we need the asset assembly node for our pos scripts.
        assembly_node = assembly_utils.__create_asset_assembly_node(mdl_nodes)
        guide_template = "Base"  # Our standart base template with our standart custom scripts.

    guide_root_nd = (
        guide_utils.import_guide_template_with_custom_steps_from_repo(
            guide_template,
            override_custom_steps="Yes",
            override_confirm_box=False,
        )
    )

    guide_global_root = guide_root_nd.getChildren()[-1]

    # We reset all transformation values of the guides
    for node_ in [
        shape.getTransform()
        for shape in guide_global_root.getChildren(ad=True, shapes=True)
    ]:
        reset_transform(node_)

    # We find the local and gloabl roots and set the ctrl sizes
    local_root = [
        node.getTransform()
        for node in guide_global_root.getChildren(ad=True, shapes=True)
        if "local" in node.name(long=None)
    ][0]
    local_root.ctlSize.set(obj_size * 10.0)
    local_root.icon.set("null")
    global_root = [
        node.getTransform()
        for node in guide_global_root.getChildren(ad=True, shapes=True)
        if "global" in node.name(long=None)
    ][0]
    global_root.ctlSize.set(obj_size)

    # And we tweak the body root and place it in the middle of the mdl.
    avg_object_center_mtx = pmc.datatypes.TransformationMatrix()
    avg_object_center_mtx.setTranslation(
        get_avg_object_center(mdl_nodes), "world"
    )
    body_root = [
        node.getTransform()
        for node in guide_global_root.getChildren(ad=True, shapes=True)
        if "body" in node.name(long=None)
    ][0]
    body_root.joint.set(True)
    body_root.setMatrix(avg_object_center_mtx, worldSpace=True)

    vis_root = [
        node.getTransform()
        for node in guide_global_root.getChildren(ad=True, shapes=True)
        if "visibility" in node.name(long=None)
    ][0]

    # We set the vis ctrl the worldspace pos of the bounding box edge.
    pmc.xform(vis_root, t=(0.0, obj_size, 0.0), ws=True)
    if not pxo_asset:
        pmc.delete(vis_root)

    # We delete all buffer curves of the template
    pmc.delete(
        guide_utils.get_buffer_root_grp_from_guide(guide_root_nd)[
            0
        ].getChildren()
    )

    # Actually rig building
    pmc.select(guide_root_nd)
    guide_manager.build_from_selection()

    return guide_root_nd, assembly_node


def _generate_bounding_box_buffer_curve(
    mdl_nodes,
    bbox_buffer_curve_name,
    object_scale,
    buffer_crv_message_attr,
):
    """
    Generate a bounding box control curve for the simple rig.

    Args:
        mdl_nodes(list): Mdl nodes which the control should include.
        bbox_buffer_curve_name(str): Control name.
        object_scale(tuple): Control scale values.
        buffer_crv_message_attr(str): The buffer curve message attr name.

    Returns:
        pmc.PyNode(): The control curve.
    """
    avg_obj_center_mtx = pmc.datatypes.TransformationMatrix()
    avg_obj_center_mtx.setTranslation(get_avg_object_center(mdl_nodes), "world")
    box_ctrl = curves_utils.BoxControl()
    box_ctrl.create_curve(
        name=bbox_buffer_curve_name,
        scale=object_scale,
        buffer_grp=False,
        match=avg_obj_center_mtx,
    )
    box_ctrl.control.addAttr(buffer_crv_message_attr, type="message")
    mdl_nodes[0].message.connect(box_ctrl.control.attr(buffer_crv_message_attr))
    return box_ctrl.control


def create_simple_pxoAsset_rig(
    mdl_nodes,
    pxo_asset=False,
    asset_name_attr="asset_name",
    namespace_attr="namespace",
    generate_cache_attr_name="generate_pub_cache",
    default_control_size=1000.0,
    informBox=True,
):
    """
    Creates a very simple prop rig. This creation can happen in a rig, anim or layout task.

    Args:
        mdl_nodes(list): List of mdl root nodes.
        pxo_asset(bool): Mdl data assembled by a pxoAsset node.
                         If false we assume that the data is assembled by a proxyReferenceAsset (gpu cache) node.
        asset_name_attr(str): Name of the asset name metadata attribute from the mdl top node.
        namespace_attr(str): Name of the namespace metadata attribute from the mdl top node.
        generate_cache_attr_name(str): Name of the generate cache attr which enables cahcing in
                                       anim or layout task if is keyframed.
        default_control_size(float): The default control size which will be taken if the calcualtion of the
                                     bounding box fails. Default is 1000.0
        informBox(bool): Enable/Disable the info box if BBox is not accessable.
                         Default value is True
    """
    b_box_buffer_curve = None
    # Get asset data
    asset_name = mdl_nodes[0].attr(asset_name_attr).get()
    bbox_buffer_curve_name = f"{asset_name}_boundingBox_C_001_buffer_crv"
    bbox_buffer_curve_message_attr = "simple_rig_buf_crv"
    buffer_curves = pmc.ls(
        bbox_buffer_curve_name.replace(asset_name, "*"), type="transform"
    )
    # We have to pre calculate the proy node first to get the correct bounding box and therefore the correct object size.
    if not pxo_asset:
        _reload_pxo_ref_node(mdl_nodes)
    obj_size, object_scale = get_exact_world_object_size(mdl_nodes)
    if obj_size < 1.0:
        try:
            b_box_buffer_curve = [
                node
                for node in buffer_curves
                if node.attr(bbox_buffer_curve_message_attr).get() in mdl_nodes
                and node.hasAttr(bbox_buffer_curve_message_attr)
            ][0]
            obj_size, object_scale = get_exact_world_object_size(
                [b_box_buffer_curve]
            )
        except:
            message = (
                f"Bounding box for {mdl_nodes} is not accessable."
                f" Sometimes this happens with gpu caches. "
                f"For this we leave a buffer curve in the scene. "
                f"Pls adjust this curve as you wish and run the build again."
            )
            if informBox:
                pmc.informBox("Simple Rig logger", message)
            pmc.warning(message)
            return _generate_bounding_box_buffer_curve(
                mdl_nodes,
                bbox_buffer_curve_name,
                (
                    default_control_size,
                    default_control_size,
                    default_control_size,
                ),
                bbox_buffer_curve_message_attr,
            )

    if not b_box_buffer_curve:
        b_box_buffer_curve = _generate_bounding_box_buffer_curve(
            mdl_nodes,
            bbox_buffer_curve_name,
            object_scale,
            bbox_buffer_curve_message_attr,
        )

    if len(mdl_nodes) > 1:
        asset_name = f"{asset_name}{''.join([str(mdl_node.attr(asset_name_attr).get()).split('_')[-1].capitalize() for mdl_node in mdl_nodes[1:]])}"
    namespace = mdl_nodes[0].attr(namespace_attr).get()
    pxo_asset_node = create_rig_pxoAsset_node(asset_name)

    # We try to find out which obj in the hierarchy are not coming from a reference
    mdl_obj_without_reference = []
    for node_ in mdl_nodes:
        for child in node_.getChildren(ad=True, type="transform"):
            if not child.parentNamespace():
                mdl_obj_without_reference.append(child)

    guide_root_nd, assembly_node = _import_and_build_rig_template_simple_rig(
        mdl_nodes, obj_size, pxo_asset
    )

    rig_root_grp = pmc.PyNode(constants.RIG_SETUP_ROOT_NAME)
    rig_root_set = pmc.PyNode(constants.PXO_ROOT_SET_NAME)
    body_jnt = [
        jnt
        for jnt in pmc.PyNode(constants.PXO_DEFORMERS_SET_NAME).members()
        if "body" in jnt.name()
    ]
    body_ctrl = [
        node
        for node in pmc.PyNode(constants.PXO_CONTROLS_SET_NAME).members()
        if "body" in node.name()
    ][0]
    for mdl_node in mdl_nodes:
        pxo_constraining(body_jnt, mdl_node, True)

    dag_utils.swap_curve_shapes(
        b_box_buffer_curve, body_ctrl
    )  # We need to swap the box control shape because there is mgear bug.
    rig_root_nd = pymel_utils.PxoDagContainerRigRootNode(
        name=f"{asset_name}_rig"
    )
    rig_root_nd.set_sub_containers()
    if assembly_node:
        rig_root_nd.set_meta_data()
        rig_root_nd.set_meta_asset_assembly_node(assembly_node)
    rig_container = [
        node
        for node in rig_root_nd.getSubcontainers()
        if node.name(long=None) == rig_root_nd.RIG_SUB_CONTAINER_NAME
    ][0]
    model_container = [
        node
        for node in rig_root_nd.getSubcontainers()
        if node.name(long=None) == rig_root_nd.MODEL_ASSET_SUB_CONTAINER_NAME
    ][0]

    # Specific thing exclusive for the pxoAsset node
    if not pxo_asset:
        # We generate the visbility attributes if we not using the pxoAsset node.
        rig_vis_class = RigVisibilitySetup()
        rig_vis_class.geo_attributes_data = []
        rig_vis_class.ctrl_attributes_data = []
        rig_vis_class.overall_rig_attributes_data = [
            {
                "connect_to": [rig_root_grp.jnt_vis],
                "separator": "mgear_controls",
                "longName": "mgear_jnt_vis",
                "type": "bool",
                "keyable": True,
                "defaultValue": 0,
            },
            {
                "connect_to": [rig_root_grp.ctl_vis],
                "separator": "mgear_controls",
                "longName": "ctrl_vis",
                "type": "bool",
                "keyable": True,
                "defaultValue": 1,
            },
            {
                "connect_to": [rig_root_grp.ctl_vis_on_playback],
                "separator": "mgear_controls",
                "longName": "ctl_vis_on_playback",
                "type": "bool",
                "keyable": True,
                "defaultValue": 0,
            },
            {
                "separator": "mgear_controls",
                "longName": generate_cache_attr_name,
                "type": "bool",
                "keyable": True,
                "defaultValue": 1,
            },
        ]
        for data_dict in rig_vis_class.basic_attributes_data:
            if data_dict["longName"] == rig_vis_class.RESOLUTION_ATTR_NAME:
                data_dict["defaultValue"] = 3
        rig_vis_class.creation(body_ctrl, mdl_nodes[0].getChildren())
        for mdl_node in mdl_nodes:
            mdl_node.overrideEnabled.set(1)
            body_ctrl.attr(rig_vis_class.MDL_DISPL_TYPE).connect(
                mdl_node.overrideDisplayType, force=True
            )
        pmc.setKeyframe(body_ctrl, at=generate_cache_attr_name, t=[1001, 1002])

    # Add the rig container node.
    rig_container.add_nodes(rig_root_grp)
    model_container.add_nodes(mdl_nodes)
    pxo_asset_node.addChild(rig_root_nd)

    # Everything needs to be in a unique namespace
    scene_utils.add_objects_to_namespace(
        mdl_obj_without_reference
        + [pxo_asset_node, rig_root_grp, rig_root_set, rig_root_nd]
        + mdl_nodes
        + rig_root_grp.getChildren(ad=True)
        + rig_root_set.members()
        + rig_root_nd.getSubcontainers(),
        scene_utils.get_unique_namespace(namespace),
    )
    if assembly_node:
        assembly_node.unlock()
        scene_utils.add_objects_to_namespace([assembly_node], namespace)
        assembly_node.lock()
    pmc.delete(guide_root_nd, b_box_buffer_curve)


def create_sine_setup(
    target_nodes_list,
    sine_setup_attributes_dict_list,
    name="Test",
    index=0,
    target_input_axe="Y",
    input_nd=None,
    parent_nd=None,
):
    """
    Create a sin curve setup on given node list.

    Args:
        target_nodes_list(List): The target nodes.
        sine_setup_attributes_dict_list(List): The setup attributes dict list.
        name(str): Name for the new input node.
        index(index): The setup index.
        target_input_axe(str): The input axes of the target nodes.
        Valid is ["X", "Y", "Z", "-X", "-Y", "-Z"].
        input_nd(pmc.PyNode()): The input node which holds the
                                keyable attributes.
                                If None will create new one.
        parent_nd(pmc.PyNode()): Parent node for the new created input node.
                                 Only works if input_nd flag is None.
    Return:
        pmc.PyNode(): The input node with keyable attributes.

    """
    name = "{}_{}_input_trs".format(name, index)
    axes = target_input_axe.replace("-", "")
    if not input_nd:
        input_nd = pmc.createNode("transform", n=name)
        for axe in "XYZ":
            for channel in ["translate", "rotate", "scale"]:
                input_nd.attr("{}{}".format(channel, axe)).set(
                    keyable=False, channelBox=False, lock=True
                )
        input_nd.visibility.set(keyable=False, channelBox=False, lock=True)
        if parent_nd:
            parent_nd.addChild(input_nd)
    for attr_ in sine_setup_attributes_dict_list:
        attributes_utils.add_attribute_to_node_by_dict(input_nd, **attr_)
    math_sine_nd = pmc.createNode("math_SinAngle")
    negate_nd = pmc.createNode("multDoubleLinear")
    amplitude_nd = pmc.createNode("multDoubleLinear")
    time_offset_nd = pmc.createNode("math_AddAngle")
    speed_nd = pmc.createNode("math_MultiplyAngle")
    clamp_at_zero_nd = pmc.createNode("remapValue")
    clamp_at_zero_nd_rev_nd = pmc.createNode("reverse")
    negative_slope_rev_nd = pmc.createNode("reverse")
    input_nd.progress.connect(time_offset_nd.input1)
    input_nd.time_offset.connect(time_offset_nd.input2)
    time_offset_nd.output.connect(speed_nd.input1)
    input_nd.speed.connect(speed_nd.input2)
    speed_nd.output.connect(math_sine_nd.input)
    math_sine_nd.output.connect(clamp_at_zero_nd.inputValue)
    input_nd.clamp_at_zero.connect(clamp_at_zero_nd_rev_nd.inputX)
    clamp_at_zero_nd_rev_nd.outputX.connect(clamp_at_zero_nd.outputMax)
    clamp_at_zero_nd.inputMin.set(-1)
    clamp_at_zero_nd.inputMax.set(1)
    clamp_at_zero_nd.outputMin.set(-1)
    input_nd.strength.connect(amplitude_nd.input1)
    clamp_at_zero_nd.outValue.connect(amplitude_nd.input2)
    amplitude_nd.output.connect(negate_nd.input1)
    negate_nd.input2.set(-1)
    input_nd.negative_slope.connect(negative_slope_rev_nd.inputX)
    negative_slope_mult_nodes = []
    blend_nodes = []
    mult_value = 1.0 / len(target_nodes_list)
    for x in range(len(target_nodes_list) - 1):
        mult_nd = pmc.createNode("multDoubleLinear")
        blend_nd = pmc.createNode("blendTwoAttr")
        negative_slope_rev_nd.outputX.connect(blend_nd.attributesBlender)
        mult_nd.input1.set(mult_value * (x + 1))
        negative_slope_mult_nodes.append(mult_nd)
        blend_nodes.append(blend_nd)
    for index, (mult_nd_, blend_nd_) in enumerate(
        zip(negative_slope_mult_nodes, blend_nodes)
    ):
        input_nd_attr = amplitude_nd.output
        if index % 2:
            input_nd_attr = negate_nd.output
        input_nd_attr.connect(mult_nd_.input2)
        mult_nd_.output.connect(blend_nd_.input[0])
        input_nd_attr.connect(blend_nd_.input[1])
        if "-" in target_input_axe:
            negate_axe_nd = pmc.createNode("multDoubleLinear")
            blend_nd_.output.connect(negate_axe_nd.input1)
            negate_axe_nd.input2.set(-1)
            negate_axe_nd.output.connect(
                target_nodes_list[index].attr("translate{}".format(axes))
            )
        else:
            blend_nd_.output.connect(
                target_nodes_list[index].attr("translate{}".format(axes))
            )
    if "-" in target_input_axe:
        negate_axe_nd = pmc.createNode("multDoubleLinear")
        amplitude_nd.output.connect(negate_axe_nd.input1)
        negate_axe_nd.input2.set(-1)
        negate_axe_nd.output.connect(
            target_nodes_list[-1].attr("translate{}".format(axes))
        )
    else:
        amplitude_nd.output.connect(
            target_nodes_list[-1].attr("translate{}".format(axes))
        )
    return input_nd


def duplicate_linear_ribbon_guide(
    selection, increase_index=0, increase_count=0
):
    for ribbon_sys in selection:
        old_guide_instance = LinearRibbon(ribbon_sys)
        meta_data = old_guide_instance.prep_meta_data_dict()
        comp_count = meta_data.get("comp_count_")
        comp_side = meta_data.get("comp_side_")
        comp_index = meta_data.get("comp_index_")
        search_pattern = "_{}_{}_{}_".format(comp_side, comp_index, comp_count)
        replace_pattern = "_{}_{}_{}_".format(
            comp_side, comp_index + increase_index, comp_count + increase_count
        )
        new_membrane_setup = pmc.duplicate(ribbon_sys, un=True)[0]
        new_membrane_setup_nodes = new_membrane_setup.getChildren(
            ad=True, type="transform"
        )
        new_membrane_setup.rename(
            new_membrane_setup.name()
            .replace(search_pattern, replace_pattern)
            .replace("_grp1", "_grp")
        )
        for node in new_membrane_setup_nodes:
            new_name = node.name().replace(search_pattern, replace_pattern)
            node.rename(new_name)
        new_guide_instance = LinearRibbon(new_membrane_setup)
        new_guide_instance.root_ctrl.comp_index_.set(
            comp_index + increase_index
        )
        new_guide_instance.root_ctrl.comp_count_.set(
            comp_count + increase_count
        )
        pmc.select(new_guide_instance.root_ctrl)


def build_dragons_wingMembrane_system(
    name="wingMembrane",
    build_from_selection=False,
    setup_root_grp_name="wingMembranes_C_0_grp",
    setup_jnt_root_grp_name="jnt_org",
    squatch_axes="Z",
    main_membrane_up_axes="X",
    main_membrane_aim_axes="Y",
):
    root_grp = None
    jnt_root = None

    with pmc.UndoChunk():
        wingMembranes_guide_root_nodes = pmc.ls(f"guide_{name}_*_root_grp")

        if build_from_selection:
            wingMembranes_guide_root_nodes = pmc.ls(sl=True)

        if setup_root_grp_name:
            try:
                root_grp = pmc.PyNode(setup_root_grp_name)
            except pmc.MayaNodeError:
                root_grp = pmc.createNode("transform", n=setup_root_grp_name)

        if setup_jnt_root_grp_name:
            try:
                jnt_root = pmc.PyNode(setup_jnt_root_grp_name)
            except pmc.MayaNodeError:
                jnt_root = pmc.createNode(
                    "transform", n=setup_jnt_root_grp_name
                )
        if wingMembranes_guide_root_nodes:
            for node in wingMembranes_guide_root_nodes:
                wingMembraneInstance = LinearRibbon(node)
                wingMembraneInstance.set_main_membrane_clamp_value(100.0)
                rig = wingMembraneInstance.build_rig(
                    root_grp,
                    jnt_root,
                    squatch_axes,
                    main_membrane_up_axes,
                    main_membrane_aim_axes,
                )
                rigInstance = LinearRibbon(rig)
                meta_data = rigInstance.prep_meta_data_dict()
                main_membrane_ctrl = meta_data.get("main_membrane_ctrls")[0]
                for value, attr_ in zip(
                    (-0.5, 0.5, -1, 1),
                    (
                        "down_stream_nd_rot_angle_0",
                        "up_stream_nd_rot_angle_0",
                        "down_stream_nd_rot_angle_1",
                        "up_stream_nd_rot_angle_1",
                    ),
                ):
                    main_membrane_ctrl.attr(attr_).set(value)
        else:
            raise StopIteration(
                "No guides root nodes found with the name: guide_${name}_*_root_grp"
            )


def get_basename(node):
    """
    Remove path from a node name

    Args:
        node: A maya name with or without path or a pymel PyNode

    Returns:
        str: The name with path removed.

    """
    node = str(node)
    return node.rsplit('|')[-1]


def multiply_matrix(matrix1, matrix2):
    """
    matrix1 and matrix2 are just the list of numbers of a 4x4 matrix.
        This can be had with cmds.getAttr("transform.worldMatrix" or something)
    """
    mat1 = om2.MMatrix(matrix1)
    mat2 = om2.MMatrix(matrix2)

    return mat1 * mat2


def build_matrix(x_axis=(1.0, 0.0, 0.0),
                 y_axis=(0.0, 1.0, 0.0),
                 z_axis=(0.0, 0.0, 1.0),
                 origin=(0.0, 0.0, 0.0),
                 scale=(1.0, 1.0, 1.0)):
    """
    This is useful when editing a matrix to have axis point a different direction.
    Constructs a 4x4 transformation matrix from basis vectors and an origin.

    Parameters:
        x_axis (tuple of float): Direction of the local X axis (default: (1.0, 0.0, 0.0)).
        y_axis (tuple of float): Direction of the local Y axis (default: (0.0, 1.0, 0.0)).
        z_axis (tuple of float): Direction of the local Z axis (default: (0.0, 0.0, 1.0)).
        origin (tuple of float): Position of the local origin in world space (default: (0.0, 0.0, 0.0)).
        scale  (tuple of float): Scale the axis vectors to apply scale to the matrix (default: (1.0,1.0,1.0)).

    Returns:
        list of float: A 16 number list.
    """

    x = [x_axis[i] * scale[0] for i in range(3)]
    y = [y_axis[i] * scale[1] for i in range(3)]
    z = [z_axis[i] * scale[2] for i in range(3)]

    t = origin

    # Construct row-major 4x4 matrix
    matrix = [
        x[0], x[1], x[2], t[0],
        y[0], y[1], y[2], t[1],
        z[0], z[1], z[2], t[2],
        0.0,  0.0,  0.0, 1.0
    ]

    return matrix


def constrain_matrix(transform_source, transform_target, translate = True, rotate = True, scale = True):
    out_attr = f'{transform_target}.offsetParentMatrix'

    nice_name = transform_target.split('|')[-1]
    mult_matrix = cmds.createNode('multMatrix', n=f'multMatrix_{nice_name}')

    inverse_matrix = cmds.getAttr(f'{transform_target}.inverseMatrix')
    parent = cmds.listRelatives(transform_target, p=True)
    target_matrix = cmds.getAttr(f'{transform_target}.worldMatrix')
    source_inverse_matrix = cmds.getAttr(f'{transform_source}.worldInverseMatrix')

    offset_matrix = multiply_matrix(inverse_matrix, target_matrix)
    offset_matrix = multiply_matrix(offset_matrix, source_inverse_matrix)

    cmds.setAttr(f'{mult_matrix}.matrixIn[0]', offset_matrix, type='matrix')

    cmds.connectAttr(f'{transform_source}.worldMatrix', f'{mult_matrix}.matrixIn[1]')

    if parent:
        cmds.connectAttr(f'{parent[0]}.worldInverseMatrix', f'{mult_matrix}.matrixIn[2]')

    pick_matrix = cmds.createNode('pickMatrix', n=f'pickMatrix_{nice_name}')

    cmds.connectAttr(f'{mult_matrix}.matrixSum', f'{pick_matrix}.inputMatrix')
    if not translate:
        cmds.setAttr(f'{pick_matrix}.useTranslate', False)
    if not rotate:
        cmds.setAttr(f'{pick_matrix}.useRotate', False)
    if not scale:
        cmds.setAttr(f'{pick_matrix}.useScale', False)

    cmds.connectAttr(f'{pick_matrix}.outputMatrix', out_attr)

    return mult_matrix


def get_unique_name(name_string):
    while cmds.objExists(name_string):
        name_string = string_utils.increment_last_number(name_string)

    return name_string


##########################################################
# CLASSES
##########################################################


class RigVisibilitySetup(object):
    """
    Managing class for visibility switching of controls and other objects in a rig.
    If you use it out of the box it will create predefined placeholder attributes.
    For custom results you would need to inherit this class in new class and override
    the vars in the init.

    Example:
        >>> import pymel.core as pmc
        >>> from pxo_rigging_kit.maya_utils.rigging import rig_utils
        >>> class TestOverride(rig_utils.RigVisibilitySetup):
        >>>     def __init__(self):
        >>>         super(TestOverride, self).__init__()
        >>>         # We override this var so we get our own custom overall rig attributes.
        >>>         self.overall_rig_attributes_data = [
        >>>             {
        >>>                 "separator": "mgear_controls",
        >>>                 "longName": "mgear_jnt_vis",
        >>>                 "type": "bool",
        >>>                 "keyable": True,
        >>>                 "defaultValue": 0,
        >>>             },
        >>>             {
        >>>                 "separator": "mgear_controls",
        >>>                 "longName": "ctrl_vis",
        >>>                 "type": "bool",
        >>>                 "keyable": True,
        >>>                 "defaultValue": 1,
        >>>             },
        >>>             {
        >>>                 "separator": "mgear_controls",
        >>>                 "longName": "ctl_vis_on_playback",
        >>>                 "type": "bool",
        >>>                 "keyable": True,
        >>>                 "defaultValue": 0,
        >>>             }
        >>>             ]
        >>> vis_setup_inst = TestOverride()
        >>> test_trs = pmc.createNode("transform")
        >>> vis_setup_inst.creation(test_trs)
    """

    RESOLUTION_ATTR_NAME = "resolution"
    GEO_VIS_SEP_ATTR_NAME = "geo_vis"
    PXO_MDL_RESOLUTION_GRP_NAMES = constants.PXO_MDL_RESOLUTION_GRP_NAMES
    CUSTOM_SEP_ATTR_NAME_PLACE_HOLDER = "custom_attrs"
    MDL_DISPL_TYPE = "model_display_type"

    def __init__(self):
        """
        Inherits important class vars which are used in the creation method.
        """
        # All vars can be overriden for Asset specific needs
        # This var defines the basic generic rig attributes.
        # Normally there is no need for an override.
        # Because these attributes are needed in further processes.
        # But you can enhance the list.
        self.basic_attributes_data = [
            {
                "longName": self.MDL_DISPL_TYPE,
                "type": "enum",
                "en": ["normal", "template", "reference"],
                "keyable": False,
                "defaultValue": 2,
            },
            {
                "longName": "texture_display",
                "type": "enum",
                "en": ["off", "on"],
                "keyable": False,
                "defaultValue": 0,
            },
            {
                "longName": "texture_variations",
                "type": "enum",
                "en": ["var_0", "var_1"],
                "keyable": False,
                "defaultValue": 0,
            },
            {
                "longName": "bump_map_display",
                "type": "enum",
                "en": ["off", "on"],
                "keyable": False,
                "defaultValue": 0,
            },
            {
                "longName": self.RESOLUTION_ATTR_NAME,
                "type": "enum",
                "en": self.PXO_MDL_RESOLUTION_GRP_NAMES,
                "keyable": False,
                "defaultValue": 0,
            },
        ]
        # This var defines overall generic rig attributes.
        # For example a switch for bind joints or all controls at once.
        # Be aware that the "separator" key in the attributes dict defines the belonging of the attributes.
        # This means each attribute with the same "separator" lives under the same separator attribute in the channelbox
        # A override is recommended.
        self.overall_rig_attributes_data = [
            {
                "separator": self.CUSTOM_SEP_ATTR_NAME_PLACE_HOLDER,
                "longName": "custom_attr_01",
                "type": "bool",
                "keyable": True,
                "defaultValue": 0,
            },
            {
                "separator": self.CUSTOM_SEP_ATTR_NAME_PLACE_HOLDER,
                "longName": "custom_attr_02",
                "type": "bool",
                "keyable": True,
                "defaultValue": 0,
            },
        ]
        # This var defines all geo switcher attributes.
        # Be aware that the "separator" key in the attributes dict defines the belonging of the attributes.
        # This means each attribute with the same "separator" lives under the same separator attribute in the channelbox
        # A override is recommended.
        self.geo_attributes_data = [
            {
                "longName": "geo_attr_01",
                "type": "bool",
                "keyable": True,
                "defaultValue": 0,
            },
            {
                "longName": "geo_attr_02",
                "type": "bool",
                "keyable": True,
                "defaultValue": 0,
            },
        ]
        # This var defines the ctrl visibility switches.
        # Be aware that the "separator" key in the attributes dict defines the belonging of the attributes.
        # This means each attribute with the same "separator" lives under the same separator attribute in the channelbox
        self.ctrl_attributes_data = [
            {
                "separator": "control_01_vis",
                "longName": "CTRL_attr_01",
                "type": "bool",
                "keyable": True,
                "defaultValue": 0,
            },
            {
                "separator": "control_02_vis",
                "longName": "CTRL_attr_02",
                "type": "bool",
                "keyable": True,
                "defaultValue": 0,
            },
            {
                "separator": "control_03_vis",
                "longName": "CTRL_attr_03",
                "type": "bool",
                "keyable": True,
                "defaultValue": 0,
            },
            {
                "separator": "control_03_vis",
                "longName": "CTRL_attr_04",
                "type": "bool",
                "keyable": True,
                "defaultValue": 0,
            },
        ]

    def __add_basic_attributes(self, visibility_ctrl):
        """
        Add the general basic rig switches.
        Based on the self.basic_attributes_data var in the class init.

        Args:
            visibility_ctrl(pmc.PyNode): The rig visibility control.
        """
        attributes_utils.add_pxo_separator_attr(
            visibility_ctrl, self.GEO_VIS_SEP_ATTR_NAME
        )
        attributes_utils.add_attributes_to_node_by_list(
            visibility_ctrl, self.basic_attributes_data
        )

    def _connect_geo_resolution_nodes(
        self, visibility_ctrl, resolution_grps=None
    ):
        """
        Connects all nodes given in the resolution_grps
        list with the resolution enum attr created by the basic attributes.

        Args:
            visibility_ctrl(pmc.PyNode): The rig visibility control.
            resolution_grps(list): List filled with the resolution nodes in the rig.
                                   Strings which needs to be inherited in the names of the nodes are defined in the
                                   PXO_MDL_RESOLUTION_GRP_NAMES class var and can be overriden.

        Requieres:
            Attributes build by the self.__add_basic_attributes method.

        Returns:
            True if successfully.
            _LOGGER.warning() if no resolution_grps are given.

        """
        if resolution_grps:
            for grp in resolution_grps:
                for index, res in enumerate(self.PXO_MDL_RESOLUTION_GRP_NAMES):
                    if res in grp.name(long=None, stripNamespace=True):
                        condition = pmc.createNode("condition")
                        visibility_ctrl.attr(self.RESOLUTION_ATTR_NAME).connect(
                            condition.firstTerm
                        )
                        condition.secondTerm.set(index)
                        condition.colorIfTrueR.set(1)
                        condition.colorIfFalseR.set(0)
                        condition.outColor.outColorR.connect(grp.visibility)
            return True
        _LOGGER.warning(
            f"{list(locals().keys())[-1]} args is None. No resolution nodes connected."
        )

    def _add_custom_attributes(
        self, visibility_ctrl, custom_attributes_data=None
    ):
        """
        Add custom attributes to given vis ctrl.
        This custom attributes can have any purpose.

        Args:
            visibility_ctrl(pmc.PyNode): The rig visibility control.
            custom_attributes_data(list): The custom attributes data list which can look like this:
                                          [
                                          {
                                            "separator": "control_01_vis",
                                            "longName": "CTRL_attr_01",
                                            "type": "bool",
                                            "keyable": True,
                                            "defaultValue": 0,
                                          },
                                          {
                                            "separator": "control_02_vis",
                                            "longName": "CTRL_attr_02",
                                            "type": "float",
                                            "keyable": False,
                                            "defaultValue": 0.0,
                                            "hidden": True,
                                            "min": 0.0,
                                            "max": 1.0
                                          }
                                          ]
        """
        for data_dict in custom_attributes_data:
            sep_attr_name = data_dict.get("separator", False)
            if sep_attr_name:
                data_dict.pop("separator")

                if not visibility_ctrl.hasAttr(sep_attr_name):
                    attributes_utils.add_pxo_separator_attr(
                        visibility_ctrl, sep_attr_name
                    )

            attributes_utils.add_attribute_to_node_by_dict(
                visibility_ctrl, data_dict
            )

    def creation(self, visibility_ctrl, resolution_grps=None):
        """
        Creates the rig visibility attributes.
        You can override this method if you need another order of the attributes or something else.

        Args:
            visibility_ctrl(pmc.PyNode): The rig visibility control.
            resolution_grps(list): List filled with the resolution nodes in the rig.
                                   Strings which needs to be inherited in the names of the nodes are defined in the
                                   PXO_MDL_RESOLUTION_GRP_NAMES class var and can be overriden.
        """
        # Create the basic attributes and needs to be on top of the stack and always be used.
        self.__add_basic_attributes(visibility_ctrl)

        # Build the geo vis attributes.
        self._add_custom_attributes(visibility_ctrl, self.geo_attributes_data)

        # Build the overall rig vis attributes.
        self._add_custom_attributes(
            visibility_ctrl, self.overall_rig_attributes_data
        )

        # Build the rig controls vis attributes.
        self._add_custom_attributes(visibility_ctrl, self.ctrl_attributes_data)
        # Connects the geo resolution nodes with the resolution enum attr build with the basic attributes.
        self._connect_geo_resolution_nodes(visibility_ctrl, resolution_grps)


# This is a realy old class which we used in an older repo for building the dragons.
# This class needs a whole rework. But at least this class in now centralized in this repo, and we do not have to work
# with two different repos.
class LinearRibbon(object):
    def __init__(self, guide_root_nd=None):
        """
        Create a linear ribbon system.

        Args:
            guide_root_nd(pmc.PyNode()): The guide root_nd.

        Example:
            The gitlab package has to be in your sys.path.
            Or the class has to be sourced first.
            ### ATTENTION. Will create a new scene. ###
            ### PLS save current file before test this code. ###
            >>> import pymel.core as pmc
            >>> import scripts.reg.build_pre_scripts.pxo_ribbon_rig as ribbon_rig
            >>> pmc.newFile(force=True)
            >>> ### Create some test objects in the scene for parenting.
            >>> jnt_root = pmc.createNode("transform", n="jnt_root")
            >>> root_grp = pmc.createNode("transform", n="root_grp")
            >>> L_jnt_0_0 = pmc.createNode("joint", n="L_test_0_0_jnt")
            >>> L_jnt_0_1 = pmc.createNode("joint", n="L_test_0_1_jnt")
            >>> L_jnt_0_0.addChild(L_jnt_0_1)
            >>> L_jnt_0_0.translate.set(32.93, 0, 10)
            >>> L_jnt_0_1.translate.set(0, 0, -20)
            >>> dup = pmc.duplicate(L_jnt_0_0)[0]
            >>> mirror_grp = pmc.group(em=True, w=True)
            >>> mirror_grp.addChild(dup)
            >>> mirror_grp.scaleX.set(-1)
            >>> pmc.parent(dup, w=True)
            >>> pmc.delete(mirror_grp)
            >>> [node.rename(node.name().replace("L_","R_").replace("_jnt1","_jnt")) for node in [dup,dup.getChildren()[0]]]
            >>> ### Create the guide_ribbon
            >>> L_wingFingerClass = ribbon_rig.LinearRibbon()
            >>> L_wingFingerClass.create_guide_ribbon("wingMembrane", comp_side="L", comp_index=0, spans=4, start_jnt=True, end_jnt=True)
            >>> L_wingFingerClass.root_ctrl.translateX.set(20)
            >>> L_jnt_0_0.addChild(pmc.PyNode("guide_wingMembrane_L_0_0_0_edge_ctrl"))
            >>> L_jnt_0_1.addChild(pmc.PyNode("guide_wingMembrane_L_0_0_1_edge_ctrl"))
            >>> L_wingFingerClass.set_edge_ctrls_parents()
            >>> L_wingFingerClass.unparent_edge_ctrls()
            >>> ### Mirror
            >>> R_mirrored_ribbon = L_wingFingerClass.mirror_guide_ribbon()
            >>> R_wingFingerClass = ribbon_rig.LinearRibbon(R_mirrored_ribbon)
            >>> ### Build
            >>> L_ribbon_rig_root_nd = L_wingFingerClass.build_rig(root_grp, jnt_root)
            >>> R_ribbon_rig_root_nd = R_wingFingerClass.build_rig(root_grp, jnt_root)
            >>> for node in [L_wingFingerClass.root_nd,R_wingFingerClass.root_nd]:
            >>>     node.visibility.set(0)

        """
        self.data_list = [
            {"port_number": 0, "port_name": "normalizedNormal"},
            {"port_number": 1, "port_name": "normalizedTangentU"},
            {"port_number": 2, "port_name": "normalizedTangentV"},
            {"port_number": 3, "port_name": "position"},
        ]
        self.ribbon_nodes_list_attr_name = "ribbon_nodes_list"
        self.component_meta_data_attr_name = "component_meta_data"
        self.root_ctrl_message_attr_name = "root_ctrl"
        self.ribbon_nodes_list_attr_children = [
            "edge_controls",
            "nurbsSurface",
            "surface_trs_nodes",
            "surface_jnt_nodes",
            "loft_curves",
            "membrane_controls",
            "jnt_npos",
            "main_membrane_controls",
            "add_double_linear_nodes",
        ]
        self.parent_attr_name = "parent_nd"
        (
            self.edge_ctrl_message_attr_name,
            self.nurbs_surface_message_attr_name,
            self.surface_trs_nodes_message_attr_name,
            self.surface_jnt_nodes_message_attr_name,
            self.loft_curves_message_attr_name,
            self.membrane_control_message_attr_name,
            self.npo_control_message_attr_name,
            self.main_membrane_controls_message_attr_name,
            self.add_double_linear_nodes_message_attr_name,
        ) = self.ribbon_nodes_list_attr_children
        self.root_nd = None
        self.root_ctrl = None
        self.rig_ctrl_color_dict = {"L": 6, "R": 13, "C": 18}
        self.main_scale_attr_name = "main_scale"
        self.main_membrane_clamp_attr_name = "main_membrane_clamp_value"
        if guide_root_nd:
            self.add_guide_root_nd(guide_root_nd)
        # Be aware that each change of an entry in the list in index of an list
        # item has to be updated in the whole class. Because some items are
        # taken by index in that list. We will need something better here.
        self.comp_meta_data_attr_names = [
            {"name": "comp_type_", "type": "string"},
            {"name": "comp_name_", "type": "string"},
            {"name": "comp_side_", "type": "string"},
            {"name": "comp_index_", "type": "long"},
            {"name": "comp_count_", "type": "long"},
            {"name": "spans", "type": "long"},
            {"name": "start_jnt", "type": "bool"},
            {"name": "end_jnt", "type": "bool"},
            {"name": "jnt_radius", "type": "long"},
            {"name": "surface_degree", "type": "string"},
            {"name": "main_membrane_ctrl", "type": "bool"},
            {"name": "start_joint_swap_edge", "type": "bool"},
            {"name": "end_joint_swap_edge", "type": "bool"},
            {"name": "joints", "type": "long"},
            {"name": "joints_on_surface_direction", "type": "string"},
        ]

    def add_guide_root_nd(self, guide_root_nd):
        """
        Add guide root nd to class. For further use.

        Args:
            guide_root_nd(pmc.PyNode()): The guide root node.

        """
        self.root_nd = guide_root_nd
        self.root_ctrl = self.get_root_ctrl_from_root_nd(guide_root_nd)

    def duplicate_and_rename(self, previous_str_char, new_str_char):
        """
        Duplicate the root_nd stored in the __init__.
        Rename the duplicated root_nd and included nodes.

        Args:
            previous_str_char(str):
            new_str_char(str):

        Return:
             Dict: {"root_nd": dupl_root_nd, "root_ctrl": root_ctrl}

        """
        dupl_root_nd = pmc.duplicate(self.root_nd, un=True)[0]
        root_ctrl = self.get_root_ctrl_from_root_nd(dupl_root_nd)
        root_ctrl.rename(
            root_ctrl.name().replace(previous_str_char, new_str_char)
        )
        dupl_root_nd.rename(
            dupl_root_nd.name()
            .replace(previous_str_char, new_str_char)
            .replace("_grp1", "_grp")
        )
        meta_dict = self.prep_meta_data_dict(root_ctrl)
        [
            node.rename(node.name().replace(previous_str_char, new_str_char))
            for node in meta_dict.get("membrane_ctrls")
        ]
        [
            node.rename(node.name().replace(previous_str_char, new_str_char))
            for node in meta_dict.get("jnt_nodes")
        ]
        [
            node.rename(node.name().replace(previous_str_char, new_str_char))
            for node in meta_dict.get("trs_nodes")
        ]
        [
            node.rename(node.name().replace(previous_str_char, new_str_char))
            for node in meta_dict.get("nurbs_surface")
        ]
        [
            node.rename(node.name().replace(previous_str_char, new_str_char))
            for node in meta_dict.get("loft_curves")
        ]
        [
            node.rename(node.name().replace(previous_str_char, new_str_char))
            for node in meta_dict.get("main_membrane_ctrls")
        ]
        [
            dic.get("edge_ctrl").rename(
                dic.get("edge_ctrl")
                .name()
                .replace(previous_str_char, new_str_char)
            )
            for dic in meta_dict.get("edge_ctrls")
        ]
        return {"root_nd": dupl_root_nd, "root_ctrl": root_ctrl}

    def build_rig(
        self,
        root_grp=None,
        jnt_root=None,
        scale_axes="Z",
        main_membrane_up_axes="X",
        main_membrane_aim_axes="Y",
        main_scale_input=None,
    ):
        """
        Build the actual ribbon rig from guide root_nd stored in the __init__.

        Args:
            root_grp(pmc.PyNode()): Root grp for the new root_nd of the built
            setup.
            jnt_root(pmc.PyNode()): Joint root node for the built joints. I
            f None the joints will stay as child of the membrane controls.
            scale_axes(str): The axes of the scale setup.
            Valid is ["X", "Y", "Z"].
            main_membrane_up_axes(str): The up axes for the main membrane setup.
            Valid is ["X", "Y", "Z"]
            main_membrane_aim_axes(str): The aim axes for the main membrane setup.
            Valid is ["X", "Y", "Z"]
            main_scale_input(pmc.Attribute()): The main scale input.

        Return:
            pmc.PyNode(): The built root_nd.

        """

        def __npo_nd(nd_, description=None):
            """
            Create a position neutralization node.

            Args:
                nd_(pmc.PyNode()): The node to neutralise.
                description(str, optional): Node description.

            Return:
                 pmc.PyNode(): The new node.

            """
            suffix = "_npo"
            if description:
                suffix = f"{description}_npo"
            npo_nd = dag_utils.create_buffer_groups([nd_], suffix)[0]
            return npo_nd

        def __create_main_membrane_setup(
            main_ctrl, npo_, membrane_follow_value_attr
        ):
            """
                       Create the main membrane position follow setup.

                       Args:
                           main_ctrl(pmc.PyNode()): The main membrane ctrl.
                           npo_(pmc.PyNode()): The npo nd of the membrane ctrl to control.
                           membrane_follow_value_attr(pmc.Attribute()): The attribute to
                           define how much the npo will follow.

                       Return:
                           utility_node: The add double linear node to connect
                           another controller to it
            .
            """
            mult_doub_lin_nd = pmc.createNode("multDoubleLinear")
            clamp_nd = pmc.createNode("clamp")
            negative_mult_doub_lin_nd = pmc.createNode("multDoubleLinear")
            add_double_linear_nd = pmc.createNode("addDoubleLinear")
            main_ctrl.attr("translate{}".format(main_membrane_up_axes)).connect(
                add_double_linear_nd.input1
            )
            add_double_linear_nd.output.connect(mult_doub_lin_nd.input1)
            membrane_follow_value_attr.connect(mult_doub_lin_nd.input2)
            negative_mult_doub_lin_nd.input2.set(-1)
            main_ctrl.attr(self.main_membrane_clamp_attr_name).connect(
                clamp_nd.maxR
            )
            main_ctrl.attr(self.main_membrane_clamp_attr_name).connect(
                negative_mult_doub_lin_nd.input1
            )
            negative_mult_doub_lin_nd.output.connect(clamp_nd.minR)
            mult_doub_lin_nd.output.connect(clamp_nd.inputR)
            clamp_nd.outputR.connect(
                npo_.attr("translate{}".format(main_membrane_up_axes))
            )
            return add_double_linear_nd

        def __create_main_membrane_aim_setup(
            stream_nd, angle_plug, clamp_nd_output_plug
        ):
            """
            Create a fake aim setup.

            Args:
                stream_nd(pmc.PyNode()): The node to connect.
                angle_plug(pmc.Attribute()): The angle attribute to define the
                aim value.
                clamp_nd_output_plug(pmc.Attribute()): The clamp output plug.

            """
            rot_mult_double_lin_nd = pmc.createNode("multDoubleLinear")
            math_mult_angle_nd_0 = pmc.createNode("math_MultiplyAngle")
            clamp_nd_output_plug.connect(rot_mult_double_lin_nd.input1)
            rot_mult_double_lin_nd.input2.set(rot_mult_value)
            math_mult_0 = pmc.createNode("math_Multiply")
            math_divide_0 = pmc.createNode("math_Divide")
            math_mult_angle_nd_1 = pmc.createNode("math_MultiplyAngle")
            root_ctrl.attr(self.main_scale_attr_name).connect(
                math_mult_0.input1
            )
            math_mult_0.input2.set(dist_value)
            math_mult_0.output.connect(math_divide_0.input1)
            distance_between.distance.connect(math_divide_0.input2)
            angle_plug.connect(math_mult_angle_nd_1.input1)
            math_divide_0.output.connect(math_mult_angle_nd_1.input2)
            math_mult_angle_nd_1.output.connect(math_mult_angle_nd_0.input1)
            rot_mult_double_lin_nd.output.connect(math_mult_angle_nd_0.input2)
            ctrl_nd = stream_nd.getChildren()[0]
            fake_aim_npo = __npo_nd(ctrl_nd, "fake_aim")
            math_mult_angle_nd_0.output.connect(
                fake_aim_npo.attr("rotate{}".format(main_membrane_aim_axes))
            )
            fake_aim_npo.setLimit(
                "rotateMax{}".format(main_membrane_aim_axes), 85
            )
            fake_aim_npo.setLimit(
                "rotateMin{}".format(main_membrane_aim_axes), -85
            )

        dupl_root_nd_dic = self.duplicate_and_rename("guide_", "")
        root_nd = dupl_root_nd_dic.get("root_nd")
        root_ctrl = dupl_root_nd_dic.get("root_ctrl")
        root_ctrl.addAttr(self.main_scale_attr_name, typ="float", keyable=False)
        root_ctrl.attr(self.main_scale_attr_name).set(1, channelBox=True)
        if main_scale_input:
            main_scale_input.connect(root_ctrl.attr(self.main_scale_attr_name))
        for axe in "XYZ":
            value = root_ctrl.attr("scale{}".format(axe)).get()
            if value < 0:
                neg_mult_doubl_nd = pmc.createNode("multDoubleLinear")
                root_ctrl.attr(self.main_scale_attr_name).connect(
                    neg_mult_doubl_nd.input1
                )
                neg_mult_doubl_nd.input2.set(-1)
                neg_mult_doubl_nd.output.connect(
                    root_ctrl.attr("scale{}".format(axe))
                )
            else:
                root_ctrl.attr(self.main_scale_attr_name).connect(
                    root_ctrl.attr("scale{}".format(axe))
                )
            root_ctrl.attr("scale{}".format(axe)).set(keyable=False, lock=True)
        root_ctrl.getShape().visibility.set(0)
        side = [
            side for side in "CLR" if "_{}_".format(side) in root_nd.name()
        ][0]
        if root_grp:
            root_grp.addChild(root_nd)
        meta_dict = self.prep_meta_data_dict(root_ctrl)
        jnt_list = meta_dict.get("jnt_nodes")
        for jnt in jnt_list:
            pattern = "_{}_".format(side)
            if pattern in jnt.name():
                new_name = "{}_bnd_{}".format(
                    side, jnt.name().replace(pattern, "_")
                )
                jnt.rename(new_name)
            jnt.drawStyle.set(0)
            jnt.overrideEnabled.set(1)
            jnt.overrideColor.set(17)
        npos = [__npo_nd(node) for node in meta_dict.get("membrane_ctrls")]
        [
            node.message.connect(
                root_ctrl.attr(
                    "{}[{}]".format(self.npo_control_message_attr_name, index)
                )
            )
            for index, node in enumerate(npos)
        ]
        if jnt_root:
            [
                jnt_root.addChild(
                    self.matrix_constraint(node, node.getParent())
                )
                for node in meta_dict.get("jnt_nodes")
            ]
            [jnt.jointOrient.set(0, 0, 0) for jnt in meta_dict.get("jnt_nodes")]
            [
                jnt.inverseScale.disconnect()
                for jnt in meta_dict.get("jnt_nodes")
            ]

        [
            edge_ctrl.get("edge_ctrl").getShape().visibility.set(0)
            for edge_ctrl in meta_dict.get("edge_ctrls")
        ]
        [
            membrane_ctrl.overrideColor.set(self.rig_ctrl_color_dict.get(side))
            for membrane_ctrl in meta_dict.get("membrane_ctrls")
        ]
        nurbs_surface = meta_dict.get("nurbs_surface")[0]
        joints_on_surface_direction = meta_dict.get(
            "joints_on_surface_direction"
        )
        if joints_on_surface_direction == "V":
            v_value_0 = 0.5
            u_value_0 = 0
            v_value_1 = 0.5
            u_value_1 = 1
        else:
            v_value_0 = 0
            u_value_0 = 0.5
            v_value_1 = 1
            u_value_1 = 0.5
        length_trs_0 = self.create_transform_on_surbsurface(
            nurbs_surface, "length_0_trs", v_value_0, u_value_0
        )
        length_trs_1 = self.create_transform_on_surbsurface(
            nurbs_surface, "length_1_trs", v_value_1, u_value_1
        )
        distance_between = pmc.createNode("distanceBetween")
        length_decomp_0 = length_trs_0.listHistory(type="decomposeMatrix")[0]
        length_decomp_1 = length_trs_1.listHistory(type="decomposeMatrix")[0]
        length_decomp_0.outputTranslate.connect(distance_between.point1)
        length_decomp_1.outputTranslate.connect(distance_between.point2)
        pmc.delete([length_trs_0, length_trs_1])
        dist_value = distance_between.distance.get()
        remap_value = pmc.createNode("remapValue")
        dis_scale_mult_linear = pmc.createNode("multDoubleLinear")
        dis_scale_mult_linear.input1.set(dist_value)
        root_ctrl.attr(self.main_scale_attr_name).connect(
            dis_scale_mult_linear.input2
        )
        remap_value.inputMin.set(0.1)
        dis_scale_mult_linear.output.connect(remap_value.inputMax)
        distance_between.distance.connect(remap_value.inputValue)
        [
            remap_value.outValue.connect(npo.attr("scale{}".format(scale_axes)))
            for npo in npos
        ]
        for trs in meta_dict.get("trs_nodes"):
            for axe in "XYZ":
                root_ctrl.attr(self.main_scale_attr_name).connect(
                    trs.attr("scale{}".format(axe))
                )
        main_membrane_ctrl = meta_dict.get("main_membrane_ctrls")
        if main_membrane_ctrl:
            main_membrane_ctrl = main_membrane_ctrl[0]
            pmc.delete(main_membrane_ctrl.getChildren(typ="joint"))
            main_membrane_npo = __npo_nd(main_membrane_ctrl)
            len_npos = len(npos)
            if not len_npos % 2:
                mid_ctrls_index_list = [
                    (old_div(len_npos, 2)) - 1,
                    old_div(len_npos, 2),
                ]
            else:
                mid_ctrls_index_list = [old_div(len_npos, 2)]
            if mid_ctrls_index_list:
                main_membrane_ctrl.addAttr(
                    "main_membrane_pos_follow_values",
                    type="enum",
                    keyable=False,
                    en="########",
                )
                main_membrane_ctrl.main_membrane_pos_follow_values.set(
                    channelBox=True, lock=True
                )
                mid_ctrls = [
                    npos[mid_ctrl_index]
                    for mid_ctrl_index in mid_ctrls_index_list
                ]
                up_stream_ctrls = npos[0 : mid_ctrls_index_list[0]]
                up_stream_ctrls.reverse()
                down_stream_ctrls = npos[mid_ctrls_index_list[-1] + 1 :]
                pos_mult_value = 0.85
                pos_decrease_value = 0.65
                rot_mult_value = 0.85
                rot_decrease_value = 0.65
                rot_angle_value = 5
                rot_angle_mult_value = 2.0
                add_double_lin_nd_list = []
                # Create position follow setup.
                for index_, mid_ctrl in enumerate(mid_ctrls):
                    main_membrane_ctrl.addAttr(
                        "mid_nd_follow_value_{}".format(index_),
                        typ="float",
                        dv=pos_mult_value,
                        keyable=False,
                    )
                    main_membrane_ctrl.attr(
                        "mid_nd_follow_value_{}".format(index_)
                    ).set(channelBox=True)
                    main_membrane_add_double_lin_nd = (
                        __create_main_membrane_setup(
                            main_membrane_ctrl,
                            mid_ctrl,
                            main_membrane_ctrl.attr(
                                "mid_nd_follow_value_{}".format(index_)
                            ),
                        )
                    )
                    add_double_lin_nd_list.append(
                        main_membrane_add_double_lin_nd
                    )
                for index, (down_stream_node, up_stream_node) in enumerate(
                    zip_longest(down_stream_ctrls, up_stream_ctrls)
                ):
                    pos_mult_value = pos_mult_value * pos_decrease_value
                    main_membrane_ctrl.addAttr(
                        "down_stream_nd_follow_value_{}".format(index),
                        typ="float",
                        dv=pos_mult_value,
                        keyable=False,
                    )
                    main_membrane_ctrl.addAttr(
                        "up_stream_nd_follow_value_{}".format(index),
                        typ="float",
                        dv=pos_mult_value,
                        keyable=False,
                    )
                    main_membrane_ctrl.attr(
                        "down_stream_nd_follow_value_{}".format(index)
                    ).set(channelBox=True)
                    main_membrane_ctrl.attr(
                        "up_stream_nd_follow_value_{}".format(index)
                    ).set(channelBox=True)
                    down_membrane_add_double_lin_nd = (
                        __create_main_membrane_setup(
                            main_membrane_ctrl,
                            down_stream_node,
                            main_membrane_ctrl.attr(
                                "down_stream_nd_follow_value_{}".format(index)
                            ),
                        )
                    )
                    up_membrane_add_double_lin_nd = (
                        __create_main_membrane_setup(
                            main_membrane_ctrl,
                            up_stream_node,
                            main_membrane_ctrl.attr(
                                "up_stream_nd_follow_value_{}".format(index)
                            ),
                        )
                    )
                    add_double_lin_nd_list.append(
                        down_membrane_add_double_lin_nd
                    )
                    add_double_lin_nd_list.append(up_membrane_add_double_lin_nd)
                for index__, node__ in enumerate(add_double_lin_nd_list):
                    node__.message.connect(
                        root_ctrl.attr(
                            "{}[{}]".format(
                                self.add_double_linear_nodes_message_attr_name,
                                index__,
                            )
                        )
                    )
                # Create fake aim setup.
                main_membrane_ctrl.addAttr(
                    "main_membrane_rot_follow_values",
                    type="enum",
                    keyable=False,
                    en="########",
                )
                main_membrane_ctrl.main_membrane_rot_follow_values.set(
                    channelBox=True, lock=True
                )
                for index, (down_stream_node, up_stream_node) in enumerate(
                    zip_longest(down_stream_ctrls, up_stream_ctrls)
                ):
                    main_membrane_ctrl.addAttr(
                        "down_stream_nd_rot_angle_{}".format(index),
                        typ="doubleAngle",
                        dv=0.0,
                        keyable=False,
                    )
                    main_membrane_ctrl.addAttr(
                        "up_stream_nd_rot_angle_{}".format(index),
                        typ="doubleAngle",
                        dv=0.0,
                        keyable=False,
                    )
                    main_membrane_ctrl.attr(
                        "down_stream_nd_rot_angle_{}".format(index)
                    ).set(rot_angle_value * -1, channelBox=True)
                    main_membrane_ctrl.attr(
                        "up_stream_nd_rot_angle_{}".format(index)
                    ).set(rot_angle_value, channelBox=True)
                    clamp_nd_output_plug = up_stream_node.attr(
                        "translate{}".format(main_membrane_up_axes)
                    ).connections(p=True)[0]
                    __create_main_membrane_aim_setup(
                        up_stream_node,
                        main_membrane_ctrl.attr(
                            "up_stream_nd_rot_angle_{}".format(index)
                        ),
                        clamp_nd_output_plug,
                    )
                    __create_main_membrane_aim_setup(
                        down_stream_node,
                        main_membrane_ctrl.attr(
                            "down_stream_nd_rot_angle_{}".format(index)
                        ),
                        clamp_nd_output_plug,
                    )
                    rot_mult_value = rot_mult_value * rot_decrease_value
                    rot_angle_value = rot_angle_value * rot_angle_mult_value
            main_membrane_npo.message.connect(
                root_ctrl.attr(
                    "{}[{}]".format(
                        self.npo_control_message_attr_name, len_npos + 1
                    )
                )
            )
            for axe in "XYZ":
                if axe is not main_membrane_up_axes:
                    main_membrane_ctrl.attr("translate{}".format(axe)).set(
                        keyable=False, channelBox=False, lock=True
                    )
                main_membrane_ctrl.attr("rotate{}".format(axe)).set(
                    keyable=False, channelBox=False, lock=True
                )
                main_membrane_ctrl.attr("scale{}".format(axe)).set(
                    keyable=False, channelBox=False, lock=True
                )
        self.parent_edge_ctrls(root_ctrl)
        return root_nd

    def mirror_guide_ribbon(self, mirror_axe="-X", new_side_prefix="R"):
        """
        Mirror the guide on given axes.
        Will change entry of parent_nd data of the edge_ctrl also.
        By default mirror on the -X axes and will add the "R_" as the new side
        prefix.

        Args:
            mirror_axe(str): The mirror axes.
            Valid is ["X","Y","Z","-X","-Y","-Z"]
            new_side_prefix(str): The new side prefix of the mirrored guide.


        Return:
             pmc.PyNode(): The mirrored root_nd.

        """
        previous_side_prefix = "L"
        if new_side_prefix == "L":
            previous_side_prefix = "R"
        regex = r"_{side}_|{side}\d|{side}_".format(side=previous_side_prefix)
        dupl_root_nd_dic = self.duplicate_and_rename(
            previous_side_prefix, new_side_prefix
        )
        root_nd = dupl_root_nd_dic.get("root_nd")
        root_ctrl = dupl_root_nd_dic.get("root_ctrl")
        root_ctrl.attr(self.comp_meta_data_attr_names[2].get("name")).set(
            new_side_prefix
        )
        mirror_grp = pmc.group(em=True, w=True)
        mirror_grp.addChild(root_ctrl)
        if mirror_axe == "-X":
            scl_values = (-1, 1, 1)
        elif mirror_axe == "-Y":
            scl_values = (1, -1, 1)
        elif mirror_axe == "-Z":
            scl_values = (1, 1, -1)
        else:
            scl_values = (1, 1, 1)
        mirror_grp.scale.set(scl_values)
        root_nd.addChild(root_ctrl)
        pmc.delete(mirror_grp)
        meta_dict = self.prep_meta_data_dict(root_ctrl)
        for data_dict in meta_dict.get("edge_ctrls"):
            edge_ctrl = data_dict.get("edge_ctrl")
            parent_nd_str = edge_ctrl.parent_nd.get()
            if parent_nd_str:
                match = re.search(regex, parent_nd_str)
                if match:
                    side_str = match.group(0)
                    new_side_str = side_str.replace(
                        previous_side_prefix, new_side_prefix
                    )
                    edge_ctrl.parent_nd.set(
                        parent_nd_str.replace(side_str, new_side_str)
                    )
        return root_nd

    def create_guide_ribbon(
        self,
        name,
        comp_type="linearRibbon",
        comp_side="C",
        comp_index=0,
        ws_vec_list_0=[(10, 0, 10), (10, 0, -10)],
        ws_vec_list_1=[(-10, 0, 10), (-10, 0, -10)],
        spans=1,
        jnt_radius=5,
        surface_degree="linear",
        start_jnt=False,
        end_jnt=False,
        ws_pos=False,
        ws_rot=False,
        main_membrane_ctrl=False,
        comp_count=0,
        start_joint_swap_edge=False,
        end_joint_swap_edge=False,
        joints=False,
        joints_on_surface_direction="V",
    ):
        """
        Create the guide for the ribbon setup.

        Args:
            name(str): Setup name.
            comp_type(str): Component type.
            comp_side(str): Component side.
            comp_index(int): Component index.
            ws_vec_list_0(list): List filled with worldSpace vector arrays.
            ws_vec_list_1(list): List filled with worldSpace vector arrays.
            spans(int): Defines how much spans the ribbon has.
                        And how much joints are on the ribbon.
                        1 span == 1 joint system.
                        But the joints flag can override this flag.
            jnt_radius(int): The jnt size.
            surface_degree(str): Surface degree. Valid is ["linear", "cubic"].
            start_jnt(bool): Create a joint at the start of the nurbsurface.
            end_jnt(bool): Create a joint at the end of the nurbsurface.
            ws_pos(tuple): The control world position. Simple vector data.
            ws_rot(tuple): The control world rotation. Euler data.
            main_membrane_ctrl(bool): Enable main membrane guide
            for main membrane setup.
            comp_count(int): The count of the comp.
            start_joint_swap_edge(bool): Will swap the start joint from the
                                         v_value edge to the middle of the
                                         u_value edge.
            end_joint_swap_edge(bool): Will swap the end joint from the
                                       v_value edge to the middle of the
                                       u_value edge.
            joints(int): The joints number on the surface.
            joints_on_surface_direction(str): Specifie on which direction
                                              the joints are build.
                                              Default is the "v" direction.
                                              Valid values are:
                                              ["V", "U"]


        Return:
            pmc.PyNode(): The root_nd of created ribbon setup.

        """
        comp_name = name
        name = "guide_{}_{}_{}_{}".format(
            comp_name, comp_side, comp_index, comp_count
        )

        def __create_main_follow_ctrl(nurbs_surface):
            """
            Create a main follow ctrl in the middle of the membrane setup.
            Has a joint as child to get a local rotate gizmo for free.

            Args:
                nurbs_surface(pmc.PyNode()): The nurbsSurface node

            Return:
                 pmc.PyNode(): The new created main control.

            """
            jnt = pmc.createNode("joint", n="main_{}_jnt".format(name))
            jnt.displayLocalAxis.set(1)
            jnt.drawStyle.set(2)
            main_control = self.create_control(
                name, "main_membrane", children=jnt
            )
            middle_trs = self.create_transform_on_surbsurface(
                nurbs_surface, "{}_main_membrane".format(name)
            )
            root_nd.addChild(middle_trs)
            middle_trs.addChild(main_control)
            main_control.translate.set(0, 0, 0)
            main_control.rotate.set(0, 0, 0)
            return main_control

        def __create_jnt_on_surface(index_, v_value_=0.5, u_value_=0.5):
            """
            Create the joint on the surface.

            Ags:
                index_(str): The jnt index.
                v_value_: The v position on the surface
                u_value_: The u position on the surface

            Return:
                pmc.PyNode(): The transform on the surface.
                Which is the joints root.

            """
            trs = self.create_transform_on_surbsurface(
                loft_surface,
                "{}_{}".format(name, index_),
                v_value=v_value_,
                u_value=u_value_,
            )
            jnt = pmc.createNode("joint", n="{}_{}_jnt".format(name, index_))
            ctrl = self.create_control(
                "{}_{}".format(name, index_), "membrane", trs, jnt
            )
            jnt.displayLocalAxis.set(1)
            jnt.radius.set(jnt_radius)
            trs.addChild(ctrl)
            jnt.translate.set(0, 0, 0)
            jnt.rotate.set(0, 0, 0)
            jnt.jointOrient.set(0, 0, 0)
            jnt.drawStyle.set(2)
            trs.message.connect(
                root_ctrl.attr(
                    "{}[{}]".format(
                        self.surface_trs_nodes_message_attr_name, index_
                    )
                )
            )
            jnt.message.connect(
                root_ctrl.attr(
                    "{}[{}]".format(
                        self.surface_jnt_nodes_message_attr_name, index_
                    )
                )
            )
            ctrl.message.connect(
                root_ctrl.attr(
                    "{}[{}]".format(
                        self.membrane_control_message_attr_name, index_
                    )
                )
            )
            return trs

        degree = 1

        if surface_degree == "cubic":
            degree = 3

        curve_0 = self.create_curve(
            ws_vec_list_0,
            name=f"{name}_0_rib_crv",
            visibility=False,
        )
        curve_1 = self.create_curve(
            ws_vec_list_1,
            name=f"{name}_1_rib_crv",
            visibility=False,
        )
        curve_ctrls_0 = [
            self.create_control(
                f"{name}_0_{index}",
                "locator",
                loc,
                loc,
            )
            for index, loc in enumerate(curve_0.get("locators"))
        ]
        curve_ctrls_1 = [
            self.create_control(
                f"{name}_1_{index}",
                "locator",
                loc,
                loc,
            )
            for index, loc in enumerate(curve_1.get("locators"))
        ]
        curve_ctrls_list = list(curve_ctrls_0 + curve_ctrls_1)
        [
            pmc.parent(
                ctrl.getChildren(ad=True, type="locator")[0],
                ctrl,
                r=True,
                shape=True,
            )
            for ctrl in curve_ctrls_list
        ]
        [
            pmc.delete(ctrl.getChildren(typ="transform"))
            for ctrl in curve_ctrls_list
        ]
        [
            ctrl.getChildren(typ="locator")[0].visibility.set(0)
            for ctrl in curve_ctrls_list
        ]
        root_ctrl = self.create_control(
            name,
            "root",
            children=curve_ctrls_list,
            ws_pos=ws_pos,
            ws_rot=ws_rot,
        )
        root_ctrl.attr(self.comp_meta_data_attr_names[0].get("name")).set(
            comp_type
        )
        root_ctrl.attr(self.comp_meta_data_attr_names[1].get("name")).set(
            comp_name
        )
        root_ctrl.attr(self.comp_meta_data_attr_names[2].get("name")).set(
            comp_side
        )
        root_ctrl.attr(self.comp_meta_data_attr_names[3].get("name")).set(
            comp_index
        )
        root_ctrl.attr(self.comp_meta_data_attr_names[4].get("name")).set(
            comp_count
        )
        root_ctrl.attr(self.comp_meta_data_attr_names[5].get("name")).set(spans)
        root_ctrl.attr(self.comp_meta_data_attr_names[6].get("name")).set(
            start_jnt
        )
        root_ctrl.attr(self.comp_meta_data_attr_names[7].get("name")).set(
            end_jnt
        )
        root_ctrl.attr(self.comp_meta_data_attr_names[8].get("name")).set(
            jnt_radius
        )
        root_ctrl.attr(self.comp_meta_data_attr_names[9].get("name")).set(
            surface_degree
        )
        root_ctrl.attr(self.comp_meta_data_attr_names[10].get("name")).set(
            main_membrane_ctrl
        )
        root_ctrl.attr(self.comp_meta_data_attr_names[11].get("name")).set(
            start_joint_swap_edge
        )
        root_ctrl.attr(self.comp_meta_data_attr_names[12].get("name")).set(
            end_joint_swap_edge
        ),
        root_ctrl.attr(self.comp_meta_data_attr_names[13].get("name")).set(
            joints
        ),
        root_ctrl.attr(self.comp_meta_data_attr_names[14].get("name")).set(
            joints_on_surface_direction
        )
        [
            ctrl.message.connect(
                root_ctrl.attr(
                    "{}[{}]".format(self.edge_ctrl_message_attr_name, index)
                )
            )
            for index, ctrl in enumerate(curve_ctrls_list)
        ]
        [
            curve.message.connect(
                root_ctrl.attr(
                    "{}[{}]".format(self.loft_curves_message_attr_name, index)
                )
            )
            for index, curve in enumerate(
                [curve_0.get("curve"), curve_1.get("curve")]
            )
        ]
        loft_surface = pmc.loft(
            curve_0.get("curve"),
            curve_1.get("curve"),
            ch=1,
            u=1,
            c=0,
            ar=1,
            d=degree,
            ss=spans,
            rn=0,
            po=0,
            rsn=True,
            n="{}_0_rib_nurb".format(name),
        )[0]
        loft_surface.overrideEnabled.set(1)
        loft_surface.overrideDisplayType.set(2)
        loft_surface.message.connect(
            root_ctrl.attr("{}[0]".format(self.nurbs_surface_message_attr_name))
        )
        pmc.select(loft_surface)
        if not joints:
            joints = spans
        if joints_on_surface_direction == "V":
            pmc.mel.eval("createHair 1 {} 10 0 0 0 0 5 0 2 1 1;".format(joints))
        else:
            pmc.mel.eval("createHair {} 1 10 0 0 0 0 5 0 2 1 1;".format(joints))
        follicle_grp = pmc.PyNode("hairSystem1Follicles")
        follicles = follicle_grp.getChildren(ad=True, type="follicle")
        direction_values = [
            fol.attr("parameter{}".format(joints_on_surface_direction)).get()
            for fol in follicles
        ]
        pmc.delete(
            ["hairSystem1", "hairSystem1OutputCurves", "nucleus1", follicle_grp]
        )
        trs_nodes = []
        start_index = 0
        if start_jnt:
            start_index = 1
            v_val = 0.0
            u_val = 0.5
            if start_joint_swap_edge:
                v_val = 0.5
                u_val = 0.0
            trs = __create_jnt_on_surface(0, v_val, u_val)
            trs_nodes.append(trs)
        for index, value in enumerate(direction_values):
            index = start_index + index
            if joints_on_surface_direction == "V":
                trs = __create_jnt_on_surface(index, v_value_=value)
            else:
                trs = __create_jnt_on_surface(index, u_value_=value)
            trs_nodes.append(trs)
        if end_jnt:
            v_val_ = 1.0
            u_val_ = 0.5
            if end_joint_swap_edge:
                v_val_ = 0.5
                u_val_ = 1.0
            trs = __create_jnt_on_surface(len(trs_nodes), v_val_, u_val_)
            trs_nodes.append(trs)
        root_nd = pmc.createNode("transform", n="{}_root_grp".format(name))
        root_nd.addAttr(self.root_ctrl_message_attr_name, typ="message")
        root_ctrl.message.connect(
            root_nd.attr(self.root_ctrl_message_attr_name)
        )
        root_nd.useOutlinerColor.set(1)
        root_nd.outlinerColor.set(0, 1, 0)
        pmc.parent(
            [
                loft_surface,
                root_ctrl,
                curve_0.get("curve"),
                curve_1.get("curve"),
            ]
            + trs_nodes,
            root_nd,
        )
        if main_membrane_ctrl:
            main_membrane_ctrl = __create_main_follow_ctrl(loft_surface)
            main_membrane_ctrl.addAttr(
                "main_membrane_follow_values",
                type="enum",
                keyable=False,
                en="########",
            )
            main_membrane_ctrl.addAttr(
                self.main_membrane_clamp_attr_name,
                typ="float",
                keyable=False,
                defaultValue=30,
            )
            main_membrane_ctrl.main_membrane_follow_values.set(
                channelBox=True, lock=True
            )
            main_membrane_ctrl.attr(self.main_membrane_clamp_attr_name).set(
                channelBox=True
            )
            main_membrane_ctrl.message.connect(
                root_ctrl.attr(
                    "{}[0]".format(
                        self.main_membrane_controls_message_attr_name
                    )
                )
            )
            main_membrane_ctrl.getParent().message.connect(
                root_ctrl.attr(
                    "{}[1]".format(
                        self.main_membrane_controls_message_attr_name
                    )
                )
            )
        self.root_nd = root_nd
        self.root_ctrl = root_ctrl
        return root_nd

    def prep_meta_data_dict(self, root_ctrl=None):
        """
        Prepare meta data dictionary of the membrane setup.
        Will give a dictionary of the full setup nodes.

        Args:
            root_ctrl(pmc.PyNode()): The root control.
            If none will take stored one on __init__.

        Return:
            Dict:
            {
            'edge_ctrls': [{'edge_ctrl': pmc.PyNode(), 'parent_nd': string'}],
            'jnt_nodes': list,
            'loft_curves': list,
            'membrane_ctrls': list,
            'nurbs_surface': list,
            'trs_nodes': list,
            'main_membrane_ctrls': list,
            'add_double_linear_nodes': list,
            'comp_name_': str,
            'comp_type_': str,
            'comp_side_': str,
            'comp_index_': int,
            'comp_count_': int,
            'npo_nodes': list,
            'spans': int,
            'start_jnt': bool,
            'end_jnt': bool,
            'jnt_radius': int,
            'surface_degree': string,
            'main_membrane_ctrl': bool,
            'start_joint_swap_edge': bool,
            'end_joint_swap_edge': bool,
            'joints': int,
            'joints_on_surface_direction': str
            }
        """
        if not root_ctrl:
            root_ctrl = self.root_ctrl
        result = {}
        edge_ctrl = [
            {
                "edge_ctrl": node,
                "parent_nd": node.attr(self.parent_attr_name).get(),
            }
            for node in root_ctrl.attr(self.edge_ctrl_message_attr_name).get()
        ]
        result["edge_ctrls"] = edge_ctrl
        result["nurbs_surface"] = root_ctrl.attr(
            self.nurbs_surface_message_attr_name
        ).get()
        result["trs_nodes"] = root_ctrl.attr(
            self.surface_trs_nodes_message_attr_name
        ).get()
        result["jnt_nodes"] = root_ctrl.attr(
            self.surface_jnt_nodes_message_attr_name
        ).get()
        result["loft_curves"] = root_ctrl.attr(
            self.loft_curves_message_attr_name
        ).get()
        result["membrane_ctrls"] = root_ctrl.attr(
            self.membrane_control_message_attr_name
        ).get()
        result["main_membrane_ctrls"] = root_ctrl.attr(
            self.main_membrane_controls_message_attr_name
        ).get()
        result["add_double_linear_nodes"] = root_ctrl.attr(
            self.add_double_linear_nodes_message_attr_name
        ).get()
        result["npo_nodes"] = root_ctrl.attr(
            self.npo_control_message_attr_name
        ).get()
        for attr_dict in self.comp_meta_data_attr_names:
            result[attr_dict.get("name")] = root_ctrl.attr(
                attr_dict.get("name")
            ).get()
        return result

    @staticmethod
    def locators_on_cv(
        shape, connect=False, locatorScale=(1, 1, 1), sequence=None
    ):
        """
        Create locators for each curve knot.

        Args:
            shape(pmc.PyNode): The curve shape node.
            connect(bool): Connect locator with curve knot.
            locatorScale(tuple): Locators local scale.
            sequence(int): Sequential creation.
            You can create every second locator for example.

        Return:
            List: All created Locators.

        """
        result = []
        for nm, ps in enumerate(shape.getCVs()):
            loc = pmc.spaceLocator()
            result.append(loc)
            loc.translate.set(ps)
            loc.getShape().localScale.set(locatorScale)
            if connect:
                loc.getShape().worldPosition[0].connect(shape.controlPoints[nm])
        if sequence:
            temp = list(range(len(result)))
            temp = temp[0::sequence]
            while len(temp) > 1:
                for x in range(temp[0] + 1, temp[1]):
                    pmc.delete(result[x])
                temp.remove(temp[0])
        return result

    def create_curve(
        self,
        knotes,
        degree=1,
        locators=True,
        locatorScale=(1, 1, 1),
        name="curve",
        visibility=1,
    ):
        """
        Create a curve based on inputs.
        By default it will have locators to control the curve points.

        Args:
                knotes(list): Curve knotes position.
                              Items can be tuples or pmc.PyNode() object.
                Selected transforms or vector data.
                degree(int): The curve type. By Default is it 1.
                {1:"linear", 3:"cubic"}
                locators(bool): Enable control locators.
                name(str): The curve name.
                visibility(bool): Curve visibility. True by default.

        Returns:
                Dict: {"curve":pmc.PyNode(), "locators":List}

        """
        locs = None
        temp = [
            knot.getMatrix(worldSpace=True).translate
            for knot in knotes
            if isinstance(knot, pmc.nodetypes.Transform)
        ]
        if not temp:
            temp = knotes
        curve = pmc.curve(d=degree, p=temp, n=name)
        curve.visibility.set(visibility)
        if locators:
            locs = self.locators_on_cv(
                curve.getShape(), connect=True, locatorScale=locatorScale
            )
            for count, node in enumerate(locs):
                node.rename("{}_{}_loc".format(name, str(count)))
        return {"curve": curve, "locators": locs}

    def create_transform_on_surbsurface(
        self,
        nurbsSurface,
        name,
        u_value=0.5,
        v_value=0.5,
        turn_on_percentage=True,
        scale=False,
    ):
        """
        Create a transform on a nurbsSurface.

        Args:
            nurbsSurface(pmc.PyNode()): The nurbs surface node.
            u_value(float): The u_value on the nurbs surface.
            v_value(float): The v_value on the nurbs surface
            turn_on_percentage(bool): Enable/Disable pointOnSurface
            calculation as percentage.
            scale(bool): Connect the scale result with transform scale.

        Return:
            pmc.PyNode(): The transform on the nurbsSurface.

        """
        curve_shape = nurbsSurface.getShape()
        axes = ["X", "Y", "Z"]
        p_on_surface = pmc.createNode("pointOnSurfaceInfo")
        p_on_surface.parameterV.set(v_value)
        p_on_surface.parameterU.set(u_value)
        p_on_surface.turnOnPercentage.set(turn_on_percentage)
        four_by_four = pmc.createNode("fourByFourMatrix")
        decomp = pmc.createNode("decomposeMatrix")
        four_by_four.output.connect(decomp.inputMatrix)
        curve_shape.worldSpace[0].connect(p_on_surface.inputSurface)
        for data in self.data_list:
            for port, axe in enumerate(axes):
                port_name = "in{}{}".format(
                    str(data.get("port_number")), str(port)
                )
                p_on_surface.attr(
                    "{}{}".format(data.get("port_name"), axe)
                ).connect(four_by_four.attr(port_name))
        trs = pmc.createNode("transform", n="{}_surf_trs".format(name))
        for channel in [
            ["outputTranslate", "translate"],
            ["outputRotate", "rotate"],
        ]:
            decomp.attr(channel[0]).connect(trs.attr(channel[1]))
        if scale:
            decomp.outputScale.connect(trs.scale)
        return trs

    def create_control(
        self,
        name,
        type="root",
        match_node=None,
        children=None,
        ws_pos=None,
        ws_rot=None,
    ):
        """
        Create control curve.

        Args:
            name(str): Control name. By default it will get the correct suffix.
            type(str): Specific control type.
            Valid is ["root", "membrane", "edge"]
            match_node(pmc.PyNode()): Transform to match position.
            children(pmc.PyNode or List): Controls children.
            ws_pos(tuple): The control world position. Simple vector data.
            ws_rot(tuple): The control world rotation. Euler data.


        Return:
            pmc.PyNode(): Created control.

        """
        if type == "root":
            ctrl = pmc.curve(
                degree=1,
                p=[
                    (10.0, 10.0, 10.0),
                    (10.0, 10.0, -10.0),
                    (-10.0, 10.0, -10.0),
                    (-10.0, -10.0, -10.0),
                    (10.0, -10.0, -10.0),
                    (10.0, 10.0, -10.0),
                    (-10.0, 10.0, -10.0),
                    (-10.0, 10.0, 10.0),
                    (10.0, 10.0, 10.0),
                    (10.0, -10.0, 10.0),
                    (10.0, -10.0, -10.0),
                    (-10.0, -10.0, -10.0),
                    (-10.0, -10.0, 10.0),
                    (10.0, -10.0, 10.0),
                    (-10.0, -10.0, 10.0),
                    (-10.0, 10.0, 10.0),
                ],
                k=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
                n="{}_root_ctrl".format(name),
            )
            col_index = 9
            ctrl.addAttr(
                self.ribbon_nodes_list_attr_name,
                numberOfChildren=len(self.ribbon_nodes_list_attr_children),
                attributeType="compound",
            )
            for attr_ in self.ribbon_nodes_list_attr_children:
                ctrl.addAttr(
                    attr_,
                    type="message",
                    multi=True,
                    parent=self.ribbon_nodes_list_attr_name,
                )
            ctrl.addAttr(
                self.component_meta_data_attr_name,
                numberOfChildren=len(self.comp_meta_data_attr_names),
                attributeType="compound",
            )
            for attr_dic in self.comp_meta_data_attr_names:
                ctrl.addAttr(
                    attr_dic.get("name"),
                    type=attr_dic.get("type"),
                    parent=self.component_meta_data_attr_name,
                )
        elif type == "membrane":
            ctrl = pmc.curve(
                degree=1,
                p=[
                    (0, 0, 1),
                    (0, 0.5, 0.866025),
                    (0, 0.866025, 0.5),
                    (0, 1, 0),
                    (0, 0.866025, -0.5),
                    (0, 0.5, -0.866025),
                    (0, 0, -1),
                    (0, -0.5, -0.866025),
                    (0, -0.866025, -0.5),
                    (0, -1, 0),
                    (0, -0.866025, 0.5),
                    (0, -0.5, 0.866025),
                    (0, 0, 1),
                    (0.707107, 0, 0.707107),
                    (1, 0, 0),
                    (0.707107, 0, -0.707107),
                    (0, 0, -1),
                    (-0.707107, 0, -0.707107),
                    (-1, 0, 0),
                    (-0.866025, 0.5, 0),
                    (-0.5, 0.866025, 0),
                    (0, 1, 0),
                    (0.5, 0.866025, 0),
                    (0.866025, 0.5, 0),
                    (1, 0, 0),
                    (0.866025, -0.5, 0),
                    (0.5, -0.866025, 0),
                    (0, -1, 0),
                    (-0.5, -0.866025, 0),
                    (-0.866025, -0.5, 0),
                    (-1, 0, 0),
                    (-0.707107, 0, 0.707107),
                    (0, 0, 1),
                ],
                k=[
                    0,
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                    7,
                    8,
                    9,
                    10,
                    11,
                    12,
                    13,
                    14,
                    15,
                    16,
                    17,
                    18,
                    19,
                    20,
                    21,
                    22,
                    23,
                    24,
                    25,
                    26,
                    27,
                    28,
                    29,
                    30,
                    31,
                    32,
                ],
                n="{}_default_ctrl".format(name),
            )
            col_index = 17
        elif type == "main_membrane":
            ctrl = pmc.curve(
                degree=1,
                p=[
                    (5.0, 5.0, 5.0),
                    (5.0, 5.0, -5.0),
                    (-5.0, 5.0, -5.0),
                    (-5.0, -5.0, -5.0),
                    (5.0, -5.0, -5.0),
                    (5.0, 5.0, -5.0),
                    (-5.0, 5.0, -5.0),
                    (-5.0, 5.0, 5.0),
                    (5.0, 5.0, 5.0),
                    (5.0, -5.0, 5.0),
                    (5.0, -5.0, -5.0),
                    (-5.0, -5.0, -5.0),
                    (-5.0, -5.0, 5.0),
                    (5.0, -5.0, 5.0),
                    (-5.0, -5.0, 5.0),
                    (-5.0, 5.0, 5.0),
                ],
                k=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
                n="{}_main_ctrl".format(name),
            )
            col_index = 28
        else:
            ctrl = pmc.curve(
                degree=1,
                p=[
                    (
                        2,
                        0,
                        1,
                    ),
                    (2, 0, -1),
                    (1, 0, -1),
                    (1, 0, -2),
                    (-1, 0, -2),
                    (-1, 0, -1),
                    (-2, 0, -1),
                    (-2, 0, 1),
                    (-1, 0, 1),
                    (-1, 0, 2),
                    (1, 0, 2),
                    (1, 0, 1),
                    (2, 0, 1),
                ],
                k=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                n="{}_edge_ctrl".format(name),
            )
            col_index = 18
            ctrl.addAttr(self.parent_attr_name, type="string")
        if match_node:
            ctrl.setMatrix(
                match_node.getMatrix(worldSpace=True), worldSpace=True
            )
        if ws_pos:
            ctrl.translate.set(ws_pos)

        if ws_rot:
            ctrl.rotate.set(ws_rot)

        if children:
            pmc.parent(children, ctrl)

        ctrl.overrideEnabled.set(1)
        ctrl.overrideColor.set(col_index)
        ctrl.visibility.set(keyable=False, channelBox=False, lock=True)

        return ctrl

    def get_root_ctrl_from_root_nd(self, root_nd=None):
        """
        Get corresponding root_ctrl of the root_nd.

        Args:
            root_nd(pmc.PyNode): The root_nd.
            If None will take stored one from __init__.

        Return:
             pmc.PyNode(): Found root_ctrl.

        """
        if not root_nd:
            root_nd = self.root_nd
        return root_nd.attr(self.root_ctrl_message_attr_name).get()

    def set_edge_ctrl_parent(self, edge_ctrl):
        """
        Will take the parent node from given edge ctrl.

        Args:
            edge_ctrl(pmc.PyNode()): The edge ctrl.

        Return:
            None if edge ctrl has no parent.
            None if root_ctrl is actual parent.

        """
        parent = edge_ctrl.getParent()
        if not parent:
            return
        if parent == self.root_ctrl:
            return
        edge_ctrl.attr(self.parent_attr_name).set(parent.name())

    def set_edge_ctrls_parents(self):
        """
        Will take the parent node from each edge
        control of the and entry it as meta data on the edge ctrl.
        """
        meta_data_dict = self.prep_meta_data_dict()
        edge_ctrls = [
            dic.get("edge_ctrl") for dic in meta_data_dict.get("edge_ctrls")
        ]
        [self.set_edge_ctrl_parent(ctrl) for ctrl in edge_ctrls]

    def unparent_edge_ctrls(self):
        """
        Unparent all edge ctrls and parent it back to the root_ctrl.
        """
        meta_data_dict = self.prep_meta_data_dict()
        edge_ctrls = [
            dic.get("edge_ctrl") for dic in meta_data_dict.get("edge_ctrls")
        ]
        [
            self.root_ctrl.addChild(ctrl)
            for ctrl in edge_ctrls
            if not self.root_ctrl.isParentOf(ctrl)
        ]

    def parent_edge_ctrls(self, root_ctrl=None):
        """
        Parent all edge_ctrls to their parent_nd nodes.
        The parent nd nodes are stored as meta data on the edge_ctrl himself.

        Args:
            root_ctrl(pmc.PyNode()): The root ctrl.
            If none will take last stored in __init__.

        """
        # Get the meta data
        regex = r"(^guide_)|(_guide_)"
        meta_data_dict = self.prep_meta_data_dict(root_ctrl)
        for dic in meta_data_dict.get("edge_ctrls"):
            parent_nd_name = dic.get("parent_nd")
            if parent_nd_name:
                match = re.search(regex, parent_nd_name)
                if match:
                    parent_nd_name = parent_nd_name.replace(match.group(0), "")
                if pmc.objExists(parent_nd_name):
                    parent = pmc.PyNode(parent_nd_name)
                    parent.addChild(dic.get("edge_ctrl"))

    def set_main_membrane_clamp_value(self, value, main_membrane_ctrl=None):
        """
        Set the main membrane clamp value on given main_membrane_ctrl.

        Args:
            value(float):
            main_membrane_ctrl(pmc.PyNode()): The main_membrane_ctrl.
            If none will take from actual meta data of current setup.

        """
        if not main_membrane_ctrl:
            meta_data_dict = self.prep_meta_data_dict()
            main_membrane_ctrl = meta_data_dict.get("main_membrane_ctrls")[0]
        main_membrane_ctrl.attr(self.main_membrane_clamp_attr_name).set(value)

    @staticmethod
    def matrix_constraint(
        node, target, translate=True, rotate=True, scale=True
    ):
        """
        Create a matrix Constraint setup the maya way.

        Args:
            node(pmc.PyNode()): The node to constraint.
            target(pmc.PyNode()): The target node.
            translate(bool): Constraint the translate channels.
            rotate(bool): Constraint the rotate channels.
            scale(bool): Constraint the scale channels.

        Return:
            pmc.PyNode(): The constrainted node.

        """
        pmc.parent(node)

        mult_matrix = pmc.createNode("multMatrix")
        target.worldMatrix[0].connect(mult_matrix.matrixIn[0])
        node.parentInverseMatrix[0].connect(mult_matrix.matrixIn[1])
        decomp = pmc.createNode("decomposeMatrix")
        mult_matrix.matrixSum.connect(decomp.inputMatrix)
        if translate:
            decomp.outputTranslate.connect(node.translate)
        if rotate:
            decomp.outputRotate.connect(node.rotate)
        if scale:
            for axe in "XYZ":
                decomp_scale = decomp.attr("outputScale{}".format(axe))
                node_scale = node.attr("scale{}".format(axe))
                if decomp_scale.get() < 0:
                    mult_double_linear = pmc.createNode("multDoubleLinear")
                    mult_double_linear.input2.set(-1)
                    decomp_scale.connect(mult_double_linear.input1)
                    mult_double_linear.connect(node_scale)
                else:
                    decomp_scale.connect(node_scale)
        return node


from maya.api import OpenMaya as om2


def get_axis(axis: str):
    axe_vectors = {
        "X": om2.MVector(1.0, 0.0, 0.0),
        "Y": om2.MVector(0.0, 1.0, 0.0),
        "Z": om2.MVector(0.0, 0.0, 1.0),
        "-X": om2.MVector(-1.0, 0, 0.0),
        "-Y": om2.MVector(0.0, -1.0, 0.0),
        "-Z": om2.MVector(0.0, 0.0, -1.0),
    }

    return axe_vectors.get(axis.upper(), om2.MVector(0.0, 1.0, 0.0))


def orientation_to_upvec():
    return 0, 1, 0


def create_interpolated_pv(
    start: str,
    mid: str,
    end: str,
    # offset_amount: Optional[float] = None,
    name: Optional[str] = None,
    position_blend_setttings: Optional[dict] = None,
    pv_space_blend_settings: Optional[dict] = None,
    aim_settings: Optional[dict] = None,
    upvec_matrix_settings: Optional[dict] = None,
    positional_matrix_settings: Optional[dict] = None,
    aim_to_pos_settings: Optional[dict] = None,
    secondary_aim_setup: Optional[dict] = None,
) -> str:
    """

    Args:
        start (str): Starting node of the interpolated PV system.
        mid (str): Starting node of the interpolated PV system.
        end (str): Starting node of the interpolated PV system.
        # offset_amount (float): Starting node of the interpolated PV system.

        name (str):

        position_blend_setttings (dict):
        pv_space_blend_settings (dict):
        aim_settings (dict):
        upvec_matrix_settings (dict):
        positional_matrix_settings (dict):
        aim_to_pos_settings (dict):
        secondary_aim_setup (dict):

    Returns:
        Str:
    """

    position_blend_setttings = position_blend_setttings or {
        "target[0].weight": 0.5,
        "target[0].useTranslate": True,
        "target[0].useScale": False,
        "target[0].useShear": False,
        "target[0].useRotate": False,
    }

    pv_space_blend_settings = pv_space_blend_settings or {
        "target[0].weight": 0,
        "target[0].useTranslate": True,
        "target[0].useScale": True,
        "target[0].useShear": True,
        "target[0].useRotate": True,
    }

    aim_settings = aim_settings or {
        "primaryMode": 1,
        "primaryInputAxisX": 0,
        "primaryInputAxisY": -1,
        "primaryInputAxisZ": 0,
        "secondaryMode": 1,
        "secondaryInputAxisX": -1,
        "secondaryInputAxisY": 0,
        "secondaryInputAxisZ": 0,
    }

    if secondary_aim_setup:
        secondary_aim_settings = secondary_aim_setup["aim_settings"]
        compare_first_settings = {"input2": 1}
        compare_second_settings = {"input2": 0}

    upvec_matrix_settings = upvec_matrix_settings or {
        "input1": (
            1,
            0,
            0,
            0,
            0,
            1,
            0,
            0,
            0,
            0,
            1,
            0,
            -10,
            0,
            0,
            1,
        ),
    }

    positional_matrix_settings = positional_matrix_settings or {
        "input1": (
            1,
            0,
            0,
            0,
            0,
            1,
            0,
            0,
            0,
            0,
            1,
            0,
            0,
            0,
            20,
            1,
        ),
    }

    aim_to_pos_settings = aim_to_pos_settings or {
        "target[0].weight": 1,
        "target[0].useTranslate": False,
        "target[0].useScale": True,
        "target[0].useShear": True,
        "target[0].useRotate": True,
    }

    name = name or "defaultPvNet"

    # creating the nodes
    middle_position = node.createNode(
        "blendMatrix", name=f"{name}_middlePosition_BMX"
    )

    pv_spaces = node.createNode("blendMatrix", name=f"{name}_pvSpaces_BMX")

    localized_rotation_offset = node.createNode(
        "math_MultiplyMatrix", name=f"{name}_additionalRotation_MMX"
    )

    start_to_end_aim = node.createNode(
        "aimMatrix", name=f"{name}_startToEnd_AMX"
    )

    start_upvector = node.createNode(
        "math_MultiplyMatrix", name=f"{name}_upvecOffset_MMX"
    )

    move_to_middle_node = node.createNode(
        "blendMatrix", name=f"{name}_rotationAdd_BMX"
    )

    positional_offset = node.createNode(
        "math_MultiplyMatrix", name=f"{name}_targetPosition_MMX"
    )

    if secondary_aim_setup:
        pv_aim = node.createNode(
            "aimMatrix", name=f"{name}_startToEndPrimaryPv_AMX"
        )

        compare_first = node.createNode(
            "math_CompareInt", name=f"{name}_startToEndPrimaryPv_CPI"
        )

        compare_second = node.createNode(
            "math_CompareInt", name=f"{name}_startToEndAdjust_CPI"
        )

    # setting default information
    set_from_dict(middle_position, position_blend_setttings)

    set_from_dict(start_to_end_aim, aim_settings)

    set_from_dict(move_to_middle_node, aim_to_pos_settings)

    set_from_dict(start_upvector, upvec_matrix_settings)

    set_from_dict(positional_offset, positional_matrix_settings)

    set_from_dict(pv_spaces, pv_space_blend_settings)

    if secondary_aim_setup:
        set_from_dict(pv_aim, secondary_aim_settings)
        set_from_dict(compare_first, compare_first_settings)
        set_from_dict(compare_second, compare_second_settings)

    else:
        pass

    # connecting
    cmds.connectAttr(f"{start}", f"{localized_rotation_offset}.input2")

    cmds.connectAttr(f"{start}", f"{start_upvector}.input2")

    cmds.connectAttr(
        f"{localized_rotation_offset}.output", f"{start_to_end_aim}.inputMatrix"
    )

    cmds.connectAttr(
        f"{start_upvector}.output", f"{start_to_end_aim}.secondaryTargetMatrix"
    )

    cmds.connectAttr(f"{end}", f"{start_to_end_aim}.primaryTargetMatrix")

    cmds.connectAttr(f"{start}", f"{middle_position}.inputMatrix")

    cmds.connectAttr(f"{end}", f"{middle_position}.target[0].targetMatrix")

    cmds.connectAttr(
        f"{middle_position}.outputMatrix", f"{move_to_middle_node}.inputMatrix"
    )

    cmds.connectAttr(
        f"{move_to_middle_node}.outputMatrix", f"{positional_offset}.input2"
    )

    cmds.connectAttr(
        f"{positional_offset}.output", f"{pv_spaces}.inputMatrix", f=True
    )

    cmds.connectAttr(f"{pv_spaces}.outputMatrix", f"{mid}", f=True)

    if secondary_aim_setup:
        cmds.setAttr(f"{pv_aim}.inputMatrix", l=False)
        cmds.setAttr(f"{pv_aim}.primaryTargetMatrix", l=False)
        cmds.setAttr(f"{pv_aim}.secondaryTargetMatrix", l=False)
        cmds.setAttr(f"{move_to_middle_node}.target[0].weight", l=False)
        cmds.setAttr(f"{move_to_middle_node}.target[1].weight", l=False)
        cmds.setAttr(f"{move_to_middle_node}.target[0].targetMatrix", l=False)
        cmds.setAttr(f"{move_to_middle_node}.target[1].targetMatrix", l=False)
        cmds.setAttr(f"{compare_first}.input1", l=False)
        cmds.setAttr(f"{compare_second}.input1", l=False)

        cmds.connectAttr(
            f"{localized_rotation_offset}.output",
            f"{pv_aim}.inputMatrix",
            f=True,
        )
        cmds.connectAttr(f"{end}", f"{pv_aim}.primaryTargetMatrix", f=True)

        cmds.connectAttr(
            secondary_aim_setup["secondary_aim"],
            f"{pv_aim}.secondaryTargetMatrix",
            f=True,
        )

        cmds.connectAttr(
            f"{compare_first}.output",
            f"{move_to_middle_node}.target[0].weight",
            f=True,
        )
        cmds.connectAttr(
            f"{compare_second}.output",
            f"{move_to_middle_node}.target[1].weight",
            f=True,
        )

        cmds.connectAttr(
            f"{start_to_end_aim}.outputMatrix",
            f"{move_to_middle_node}.target[0].targetMatrix",
            f=True,
        )
        cmds.connectAttr(
            f"{pv_aim}.outputMatrix",
            f"{move_to_middle_node}.target[1].targetMatrix",
            f=True,
        )

        cmds.connectAttr(
            secondary_aim_setup["space_01"], f"{compare_first}.input1", f=True
        )
        cmds.connectAttr(
            secondary_aim_setup["space_02"], f"{compare_second}.input1", f=True
        )

        return f"{positional_offset}.output"

    # if there is no secondary aim setup, just pass it to target matrix
    cmds.connectAttr(
        f"{start_to_end_aim}.outputMatrix",
        f"{move_to_middle_node}.target[0].targetMatrix",
        f=True,
    )

    return f"{positional_offset}.output"


def set_from_dict(node_name: str, data: dict) -> None:
    for k_, v_ in data.items():

        if isinstance(v_, (tuple, list)) and len(v_) == 16:
            cmds.setAttr(f"{node_name}.{k_}", *v_, l=True, type="matrix")
            continue

        cmds.setAttr(f"{node_name}.{k_}", v_, l=True)


def space_blender(
    space_attributes: Union[list, tuple],
    name: str,
    subname: Optional[str] = "default",
) -> tuple:
    default_attr_, default_value_ = space_attributes[0]

    blend_matrix_name = cmds.createNode(
        "blendMatrix", n=f"{name}_{subname}_BMX"
    )

    chooser_input = cmds.createNode("floatConstant", n=f"{name}_{subname}_FLC")

    cmds.setAttr(f"{chooser_input}.inFloat", 0)

    weight_mult = cmds.createNode("math_Multiply", n=f"{name}_{subname}_MLT")

    cmds.setAttr(f"{weight_mult}.input1", 1)

    if not cmds.isConnected(
        f"{default_attr_}", f"{blend_matrix_name}.inputMatrix"
    ):
        cmds.connectAttr(
            f"{default_attr_}", f"{blend_matrix_name}.inputMatrix", f=True
        )

    for iteration_, space_attribute in enumerate(space_attributes[1:]):
        additional_spaces_, additional_values_ = space_attribute

        # get out the ranges value needed to remap
        (old_start_val_, old_end_val_), (
            new_start_val_,
            new_end_val_,
        ) = additional_values_

        individual_choice_name = cmds.createNode(
            "setRange", n=f"{name}_{subname}_{iteration_:03}_SRG"
        )

        cmds.setAttr(
            f"{individual_choice_name}.oldMinX", old_start_val_, l=True
        )
        cmds.setAttr(f"{individual_choice_name}.oldMaxX", old_end_val_, l=True)

        cmds.setAttr(f"{individual_choice_name}.minX", new_start_val_, l=True)
        cmds.setAttr(f"{individual_choice_name}.maxX", new_end_val_, l=True)

        if not cmds.isConnected(
            f"{chooser_input}.outFloat", f"{weight_mult}.input2"
        ):
            cmds.connectAttr(
                f"{chooser_input}.outFloat", f"{weight_mult}.input2", f=True
            )

        cmds.connectAttr(
            f"{weight_mult}.output", f"{individual_choice_name}.valueX", f=True
        )

        cmds.connectAttr(
            f"{individual_choice_name}.outValueX",
            f"{blend_matrix_name}.target[{iteration_}].weight",
            f=True,
        )

        if not cmds.isConnected(
            additional_spaces_,
            f"{blend_matrix_name}.target[{iteration_}].targetMatrix",
        ):
            cmds.connectAttr(
                additional_spaces_,
                f"{blend_matrix_name}.target[{iteration_}].targetMatrix",
                f=True,
            )

    return blend_matrix_name, chooser_input


def space_switcher(
    space_attributes: Union[list, tuple],
    name: str,
    subname: Optional[str] = "default",
    tag: Optional[str] = None,
    iteration: Optional[int] = None,
) -> tuple:

    if len(space_attributes) <= 1:
        _LOGGER.warning(
            f"function of {__qualname__} had insufficient  inputs in space_attributes."
            f"\nTherefore tuple(None, None) will be returned"
        )

        return None, None
    iteration_ = f"_{iteration:03}" if iteration else ""

    blend_matrix_name = node.createNode(
        "blendMatrix",
        n=f"{name}_{subname}{iteration_}_BMX",
        tag=tag,
    )

    chooser_input = node.createNode(
        "floatConstant",
        n=f"{name}_{subname}{iteration_}_FLC",
        tag=tag,
    )

    cmds.setAttr(f"{chooser_input}.inFloat", 0)

    weight_mult = node.createNode(
        "math_Multiply",
        n=f"{name}_{subname}{iteration_}_MLT",
        tag=tag,
    )

    cmds.setAttr(f"{weight_mult}.input1", 1)

    if not cmds.isConnected(
        space_attributes[0], f"{blend_matrix_name}.inputMatrix"
    ):
        cmds.connectAttr(
            space_attributes[0], f"{blend_matrix_name}.inputMatrix", f=True
        )
    for subiteration_, space_attribute in enumerate(space_attributes[1:]):
        individual_choice_name = node.createNode(
            "math_CompareInt",
            n=f"{name}_{subname}{iteration_}_{subiteration_:03}_CPI",
            tag=tag,
        )

        cmds.setAttr(
            f"{individual_choice_name}.input1", subiteration_ + 1, l=True
        )

        if not cmds.isConnected(
            f"{chooser_input}.outFloat", f"{weight_mult}.input2"
        ):
            cmds.connectAttr(
                f"{chooser_input}.outFloat", f"{weight_mult}.input2", f=True
            )

        cmds.connectAttr(
            f"{weight_mult}.output", f"{individual_choice_name}.input2", f=True
        )

        cmds.connectAttr(
            f"{individual_choice_name}.output",
            f"{blend_matrix_name}.target[{subiteration_}].weight",
            f=True,
        )

        if not cmds.isConnected(
            space_attribute,
            f"{blend_matrix_name}.target[{subiteration_}].targetMatrix",
        ):
            cmds.connectAttr(
                space_attribute,
                f"{blend_matrix_name}.target[{subiteration_}].targetMatrix",
                f=True,
            )

    return blend_matrix_name, f"{chooser_input}.inFloat"


def generate_offsets(
    connector: Optional[str] = None,
    operator_transformations: Optional[list] = None,
) -> tuple:
    """
    Calculates the offsets to have a position as MMatrix.

    Args:
        connector (str):
        operator_transformations (list, None):

    Returns:
        Tuple: the offsets that were calculated.
    """

    if connector:
        if isinstance(connector, pmc.PyNode):
            connector = str(connector.longName())

        operator_transformations.insert(
            0, matrix_maths.get_world_matrix(connector)
        )

    operator_positions = [
        matrix_maths.tuple_to_mmatrix(operator_matrix_value)
        for operator_matrix_value in operator_transformations
    ]

    world_inverse_matrix = [
        matrix_maths.invert_matrix(world_mtx)
        for world_mtx in operator_positions
    ]

    offset_mapping = zip(operator_positions[1:], world_inverse_matrix[:-1])

    calculated_offsets = [
        matrix_maths.multiply_matrices(
            child_matrix,
            parent_world_inverse_matrix,
        )
        for (child_matrix, parent_world_inverse_matrix) in offset_mapping
    ]
    if not connector:
        calculated_offsets.insert(0, om2.MMatrix(constants.NULL_MATRIX))

    return tuple(calculated_offsets)


def get_attribute_or_connections(node_name: str, attr: str):
    """Retrieve attribute value or list connections for a given node attribute."""

    cmds.attributeQuery(attr, node=node_name, message=True)

    try:

        if cmds.attributeQuery(attr, node=node_name, message=True):
            return cmds.listConnections(
                f"{node_name}.{attr}",
            )
        else:
            return cmds.getAttr(f"{node_name}.{attr}")

    except Exception as e:
        print(f"Error retrieving {attr} from {node_name}: {e}")
        return None


def sortRBF(name, rbfType=None):
    """Get node wrapped in RBFNode class based on the type of node

    Args:
        name (str): name of the RBFNode in scene
        rbfType (str, optional): type of RBF to get instance from

    Returns:
        RBFNode: instance of RBFNode
    """
    if cmds.objExists(name) and cmds.nodeType(name) in rbf_io.RBF_MODULES:
        rbfType = cmds.nodeType(name)
        return rbf_io.RBF_MODULES[rbfType].RBFNode(name)
    elif rbfType is not None:
        return rbf_io.RBF_MODULES[rbfType].RBFNode(name)


def approximateAndRound(values, tolerance=1e-10, decimalPlaces=4):
    """Approximate small values to zero and rounds the others.

    Args:
        values (list of float): The values to approximate and round.
        tolerance (float): The tolerance under which a value is considered zero.
        decimalPlaces (int): The number of decimal places to round to.

    Returns:
        list of float: The approximated and rounded values.
    """
    newValues = []
    for v in values:
        if abs(v) < tolerance:
            newValues.append(0)
        else:
            newValues.append(round(v, decimalPlaces))
    return newValues


def editPose(setupName, poseIndex):
    """Updates all RBF setup poses on pose index from scene

    Args:
        setupName (str): RBF setup name
        poseIndex (int): pose index to be updated
    """
    allSetupsInfo = {}
    tmp_dict = rbf_node.getRbfSceneSetupsInfo(includeEmpty=False)

    for setupName, nodes in tmp_dict.items():
        rbfNodes = [sortRBF(n) for n in nodes]
        allSetupsInfo[setupName] = sorted(rbfNodes, key=lambda rbf: rbf.name)

    rbfNodes = allSetupsInfo.get(setupName, [])
    driverNode = rbfNodes[0].getDriverNode()[0]
    driverAttrs = rbfNodes[0].getDriverNodeAttributes()
    poseInputs = approximateAndRound(
        rbf_node.getMultipleAttrs(driverNode, driverAttrs)
    )

    for rbfNode in rbfNodes:
        poseValues = approximateAndRound(
            rbfNode.getPoseValues(resetDriven=True)
        )
        rbfNode.addPose(
            poseInput=poseInputs, poseValue=poseValues, posesIndex=poseIndex
        )
        rbfNode.forceEvaluation()


def addPose(setupName, absoluteWorld=True):
    """
    Adds pose into given RBF setup
    Args:
        setupName (str): RBF setup name
        absoluteWorld (bool): whether setup should be done in worldSpace ( default ) or not
    """
    allSetupsInfo = {}
    tmp_dict = rbf_node.getRbfSceneSetupsInfo(includeEmpty=False)

    for setupName, nodes in tmp_dict.items():
        rbfNodes = [sortRBF(n) for n in nodes]
        allSetupsInfo[setupName] = sorted(rbfNodes, key=lambda rbf: rbf.name)

    rbfNodes = allSetupsInfo.get(setupName, [])
    driverNode = rbfNodes[0].getDriverNode()[0]
    driverAttrs = rbfNodes[0].getDriverNodeAttributes()
    poseInputs = approximateAndRound(
        rbf_node.getMultipleAttrs(driverNode, driverAttrs)
    )
    for rbfNode in rbfNodes:
        poseValues = rbfNode.getPoseValues(
            resetDriven=True, absoluteWorld=absoluteWorld
        )
        poseValues = approximateAndRound(poseValues)
        rbfNode.addPose(poseInput=poseInputs, poseValue=poseValues)


def addRBFToSetup(
    setupName,
    driverNode,
    driverControl,
    driverAttrs,
    drivenNode,
    drivenAttrs,
    rbfType="weightDriver",
):
    """
    Adds new driven node into RBF setup ( New RBF button )
    Args:
        setupName (str): RBF setup name
        driverNode (str): driver node name ( Driver in UI )
        driverControl (str): driver node name ( Control in UI )
        driverAttrs (list): str driver attribute list ex ["translateY"]
        drivenNode (str): driven node name
        drivenAttrs (list): str driven attribute list ex ["translateY"]
        rbfType (str): rbf node name

    """
    drivenType = cmds.nodeType(drivenNode)
    if drivenType in ["transform", "joint"]:
        drivenNode_name = rbf_node.get_driven_group_name(drivenNode)
    else:
        drivenNode_name = drivenNode

    # Check if there is an existing rbf node attached
    if cmds.objExists(drivenNode_name):
        if rbf_manager_ui.existing_rbf_setup(drivenNode_name):
            return

    parentNode = False
    if drivenType in ["transform", "joint"]:
        parentNode = True
        drivenNode = rbf_node.addDrivenGroup(drivenNode)

    # Create RBFNode instance, apply settings
    if not setupName:
        setupName = "{}_WD".format(driverNode)
    rbfNode = sortRBF(drivenNode, rbfType=rbfType)
    rbfNode.setSetupName(setupName)
    rbfNode.setDriverControlAttr(driverControl)
    rbfNode.setDriverNode(driverNode, driverAttrs)
    defaultVals = rbfNode.setDrivenNode(
        drivenNode, drivenAttrs, parent=parentNode
    )

    allSetupsInfo = {}
    tmp_dict = rbf_node.getRbfSceneSetupsInfo(includeEmpty=False)

    for setupName, nodes in tmp_dict.items():
        rbfNodes = [sortRBF(n) for n in nodes]
        allSetupsInfo[setupName] = sorted(rbfNodes, key=lambda rbf: rbf.name)

    rbfNodes = allSetupsInfo.get(setupName, [])
    if rbfNodes:
        print(
            "Syncing poses indices from  {} >> {}".format(rbfNodes[0], rbfNode)
        )
        rbfNode.syncPoseIndices(rbfNodes[0])
    else:

        pose_inputs = rbf_node.getMultipleAttrs(driverNode, driverAttrs)
        rbfNode.addPose(poseInput=pose_inputs, poseValue=defaultVals[1::2])

    cmds.select(driverControl)


# ============================ Custom Pose Blender ==========================
# Definitions
POSE_SUFFIX_ZERO = "_pose0"
POSE_SUFFIX = "_pose%s"
POSE_NPO = "_pose_npo"
WADD_MATRIX_SUFFIX = "_pose_wma"
DECOMP_SUFFIX = "_decomp_matrix"
PMA_SUFFIX = "_pose_pma"
PLUG_NAME = "plug_input%i"


def get_parent(transform):
    """
    Returns parent transform of given transform.
        Args:
            transform(str): Transform name.
        Returns:
            transform(str): Parent transform of transform variable.
    """
    parent_transform = cmds.listRelatives(transform, p=1, type="transform")[0]
    return parent_transform


def save_pose(driven, setup_name, replace_index=None):
    """
    Creates pose on next available index, or recreates on desired index
     from driven node transform, also creates 0 root node, matching parent of driven transform.
     (be aware to keep continuity of indices).
        Args:
            driven(str): Transform name.
            setup_name(str): Setup name to group all related nodes.
            replace_index(int): If pose update is desired, this will replace existing pose at given index.

        Returns:
            transform(str): Parent transform of transform variable.
    """
    if not cmds.objExists(driven):
        cmds.error("No {} found in scene, or is not unique.".format(driven))

    root_pose = "{0}_{1}{2}".format(driven, setup_name, POSE_SUFFIX % "0")

    if not replace_index:
        i = replace_index
        pose_grp = "{0}_{1}{2}".format(driven, setup_name, POSE_SUFFIX % str(i))
        if cmds.objExists(pose_grp):
            cmds.delete(pose_grp)

    if replace_index is None:
        i = 1
        pose_grp = "{0}_{1}{2}".format(driven, setup_name, POSE_SUFFIX % str(i))

        while cmds.objExists(pose_grp):
            i = i + 1
            pose_grp = "{0}_{1}{2}".format(
                driven, setup_name, POSE_SUFFIX % str(i)
            )

    parent_grp = get_parent(driven)

    if not cmds.objExists(root_pose):
        root_pose = cmds.group(em=True, n=root_pose)
        cmds.parent(root_pose, parent_grp)
        match_local_matrix(driven, root_pose)

    pose_grp = cmds.group(em=True, n=pose_grp)
    cmds.setAttr(pose_grp + ".ro", cmds.getAttr(driven + ".ro"))
    cmds.parent(pose_grp, parent_grp)
    match_local_matrix(driven, pose_grp)

    return pose_grp


def match_local_matrix(src, dest):
    """
    Simply matches transform of dest to src from worldSpace.
        Args:
            src(str): transform node name.
            dest(str): transform node name.
    """
    mx = cmds.xform(src, q=True, m=True, ws=True)
    cmds.xform(dest, m=mx, ws=True)


def connect_pose(driver_connection, driven, setup_name, pose, index):
    """
    Creates blend via weight add matrix node and decompose on desired translation, rotation axis
    with final connections between driver and driven node.

        Args:
            driver_connection(str): Driving output connection.
            driven(str): Transform node name.
            setup_name(str): Transform node name.
            pose(str): Pose transform node name.
            index(int): index value.

        Returns:
            decomp(str): Decompose node.
    """

    wma = driven + "_" + setup_name + WADD_MATRIX_SUFFIX
    decomp = driven + "_" + setup_name + DECOMP_SUFFIX
    pma = driven + "_" + setup_name + PMA_SUFFIX

    if not cmds.objExists(wma):
        decomp, pma, wma = setup_matrix_blend(decomp, pma, wma)

    cmds.connectAttr(
        driven + "_" + setup_name + POSE_SUFFIX_ZERO + ".m",
        wma + ".wtMatrix[0].matrixIn",
        f=True,
    )
    cmds.connectAttr(
        driver_connection, wma + ".wtMatrix[%i].weightIn" % index, f=True
    )
    cmds.connectAttr(
        pose + ".m", wma + ".wtMatrix[%i].matrixIn" % index, f=True
    )
    cmds.connectAttr(driver_connection, pma + ".input1D[%i]" % index, f=True)

    npo = setup_driven_pose_npo(driven, setup_name)

    for x in "XYZ":
        cmds.connectAttr(
            decomp + ".outputTranslate%s" % x, npo + ".translate%s" % x, f=True
        )

    for x in "XYZ":
        cmds.connectAttr(
            decomp + ".outputRotate%s" % x, npo + ".rotate%s" % x, f=True
        )

    return decomp


def setup_matrix_blend(decomp, pma, wma):
    """
    Prepares weight add matrix node prepared for blending on 0 index as base matrix.
        Args:
            decomp(str): Name for decomposition node.
            pma(str): Name for plus minus average node.
            wma(str): Name for weight matrix add node.

        Returns:
            decomp(str): Decompose matrix node.
            pma(str): Plus minus average node.
            wma(str): Weight add matrix node.
    """
    wma = cmds.createNode("wtAddMatrix", n=wma)
    decomp = cmds.createNode("decomposeMatrix", n=decomp)
    cmds.connectAttr(wma + ".matrixSum", decomp + ".inputMatrix")
    pma = cmds.createNode("plusMinusAverage", n=pma)
    cmds.setAttr(pma + ".operation", 2)
    cmds.setAttr(pma + ".input1D[0]", 1.0)
    clamp = cmds.createNode("clamp")
    cmds.connectAttr(pma + ".output1D", clamp + ".input.inputR")
    cmds.setAttr(clamp + ".maxR", 1)
    cmds.connectAttr(clamp + ".outputR", wma + ".wtMatrix[0].weightIn")

    return decomp, pma, wma


def connect_poses(driver_connection, setup_name):
    """
    Creates blend via weight add matrix node and decompose on desired translation, rotation axis
    with final connections between driver and all driven pose nodes matching setup_name.
        Args:
            driver_connection(str): Driving output connection.
            setup_name(str): Transform node name.
        Returns:
            decomp(str): Decompose node.
    """
    pose_suffix = setup_name + POSE_SUFFIX % ""
    pose_list = _gather_poses(setup_name)

    if not pose_list:
        cmds.warning("No poses found for " + pose_suffix)
        return

    for pose in pose_list:
        driven, index = get_driven(pose, pose_suffix)
        if index > 0:
            connect_pose(
                driver_connection, driven, setup_name, pose, index
            )


def get_driven(pose, pose_suffix):
    """
    Returns driven transform from string split with pose and pose_suffix.
        Args:
            pose(str): Driving output connection.
            pose_suffix(str): Transform node name.

        Returns:
            driven(str): Found driven node.
            index(int): Pose index.
    """
    driven = pose.split("_" + pose_suffix)[0]
    index = pose.split(POSE_SUFFIX % "")[-1]

    return driven, int(index)


def setup_driven_pose_npo(driven, setup_name):
    """
    Creates offset group above driven transform node.
        Args:
            driven(str): Driven transform node name.
            setup_name(str): setup name.
        Returns:
            driven(str): Offset group transform name.
    """
    npo = driven + "_" + setup_name + POSE_NPO
    if cmds.objExists(npo):
        return npo

    npo = cmds.group(em=True, n=npo)
    p = cmds.listRelatives(driven, p=True, type="transform")[0]
    cmds.setAttr(npo + ".ro", cmds.getAttr(p + ".ro"))
    cmds.parent(npo, p)
    match_local_matrix(p, npo)
    cmds.parent(driven, npo)

    return npo


def _gather_poses(setup_name):
    """
    Gathers all pose transform nodes from setup.
        Args:
            setup_name(str): Setup name.
        Returns:
            sorted_pose_list(str): All poses related to setup_name.
    """
    pose_list = cmds.ls(
        "*_{0}{1}".format(setup_name, POSE_SUFFIX % "*"), type="transform"
    )
    sorted_pose_list = []

    for pose in pose_list:
        if pose.endswith(POSE_NPO):
            continue
        sorted_pose_list.append(pose)

    return sorted_pose_list


def save_into_json(setup_name_list, file_path):
    """
    Saves setup with its poses and connections into .json file with .poseDrivers extension.
    Args:
        setup_name_list(list): List full of setups to save.
        file_path(str): File path without extension (ex. "C:\\Users\\user\\Documents\\yourFileName"
    """
    data = {}

    for setup_name in setup_name_list:
        data[setup_name] = {"poses": {}}
        pose_list = _gather_poses(setup_name)

        for pose in pose_list:
            mx = cmds.getAttr(pose + ".m")
            driven, _ = get_driven(pose, setup_name + POSE_SUFFIX % "")
            data[setup_name]["poses"][pose] = {}
            data[setup_name]["poses"][pose]["matrix"] = mx
            data[setup_name]["poses"][pose]["driven"] = driven

            wma = cmds.listConnections(pose + ".m", s=False, d=True)[0]
            i = 1

            while cmds.listConnections(
                wma + ".wtMatrix[%i].weightIn" % i, s=True, d=False
            ):
                data[setup_name]["poses"][pose][
                    PLUG_NAME % i
                ] = cmds.listConnections(
                    wma + ".wtMatrix[%i].weightIn" % i, s=True, d=False, p=True
                )[
                    0
                ]

                i = i + 1

    with open(file_path + ".poseDrivers", "w") as f:
        json.dump(data, f, indent=4, sort_keys=True)


def load_from_json(file_path, replace_str="", with_str=""):
    """
    Load setup and connect from .json file with optional mirror.
    Args:
        file_path(str): Path to file. (ex. "C:\\Users\\user\\Documents\\test.poseDrivers")
        replace_str(str): String to replace during loading.
        with_str(str): Replacement string for replace_str.
    """
    f = open(file_path)
    data = json.load(f)

    for setup_name in data:
        for pose in data[setup_name]["poses"]:
            i = int(pose[-1])
            if i == 0:  # skipping zero, default pose
                continue

            mx = data[setup_name]["poses"][pose]["matrix"]
            driven = data[setup_name]["poses"][pose]["driven"]
            driver_connection = data[setup_name]["poses"][pose][PLUG_NAME % i]
            pose_grp = save_pose(
                driven.replace(replace_str, with_str),
                setup_name.replace(replace_str, with_str),
                replace_index=i,
            )
            t, r = decompose(mx)

            for v, x in zip(t, ["x", "y", "z"]):
                cmds.setAttr(pose_grp + ".t" + x, v)

            for v, x in zip(r, ["x", "y", "z"]):
                cmds.setAttr(pose_grp + ".r" + x, v)

            connect_pose(
                driver_connection.replace(replace_str, with_str),
                driven.replace(replace_str, with_str),
                setup_name.replace(replace_str, with_str),
                pose_grp,
                i,
            )


def decompose(matrix):
    """
    Quick matrix decomposition using Maya decompose node.
        Args:
            matrix(matrix): Matrix value to decompose.
        Returns:
            t(list): Value for all Translations during decomposition.
            r(list): Value for all Rotations from decomposition.
    """
    d = cmds.createNode("decomposeMatrix")
    cmds.setAttr(d + ".inputMatrix", matrix, type="matrix")
    t = cmds.getAttr(d + ".outputTranslate")[0]
    r = cmds.getAttr(d + ".outputRotate")[0]
    cmds.delete(d)
    return t, r


def add_normalized_attr(
    node_name: str = "host_ctrl",
    attr_name: str = "ikFkBlend",
    min_value: float = 0,
    max_value: float = 10,
    tag: Optional[str] = None,
) -> str:

    """
    Creates an attribute and adds it to a small node network that normalizes the values to a range of 0-1.
    Only to be used on a numeric attribute.

    Args:
        node_name (str): Name of the node.
        attr_name (str): Name of the attribute.
        min_value (float): The minimum Value of the .
        max_value (float): .
        tag (Optional[str]): .

    Returns:
        Str: .

    """

    multiplier_amount = float(min_value) + (1.0 / float(max_value))

    cmds.addAttr(
        node_name,
        ln=attr_name,
        dv=0,
        at="double",
        k=True,
        hasMinValue=True,
        hasMaxValue=True,
        minValue=min_value,
        maxValue=max_value,
    )

    _attr_normalize_node = node.createNode(
        "math_Multiply",
        n=f"{node_name}_{attr_name}_normalize_MLT",
        tag=tag,
    )

    cmds.setAttr(f"{_attr_normalize_node}.input2", multiplier_amount, l=True)

    cmds.connectAttr(
        f"{node_name}.{attr_name}", f"{_attr_normalize_node}.input1"
    )

    return f"{_attr_normalize_node}.output"


def add_shader_switch(attr_name, enum_items, main_ctrl, rig_top, geos):
    """
    Module for adding shader switch attributes to rig controls and geometry shapes.

    YTO version

    :param attr_name: Base name for the enum attribute on the main controller.
    :param enum_items: List of enum labels (e.g., ['OFF', 'ON']).
    :param main_ctrl: Name of the main controller node.
    :param rig_top: Name of the top group in the rig hierarchy.
    :param geos: List of geometry nodes (transforms or shapes).

    # add_shader_switch(
        #     attr_name='switch_bloody',
        #     enum_items=['OFF', 'ON'],
        #     main_ctrl='global_0_ctrl',
        #     rig_top='rig_root_grp',
        #     geos=cmds.ls('*:*geo')
        # )
    """
    # Add enum attribute to main controller
    if not cmds.attributeQuery(attr_name, node=main_ctrl, exists=True):
        cmds.addAttr(
            main_ctrl,
            longName=attr_name,
            attributeType='enum',
            enumName=':'.join(enum_items),
            keyable=True
        )

    # Prepare and add corresponding long attribute on rig top
    rig_attr = f"mtoa_constant_{attr_name}"
    if not cmds.attributeQuery(rig_attr, node=rig_top, exists=True):
        cmds.addAttr(
            rig_top,
            longName=rig_attr,
            attributeType='long',
            keyable=False
        )

    # Connect main_ctrl.attr -> rig_top.rig_attr
    src_attr = f"{main_ctrl}.{attr_name}"
    mid_attr = f"{rig_top}.{rig_attr}"
    cmds.connectAttr(src_attr, mid_attr, force=True)

    # Iterate over geometry nodes and propagate the attribute
    for geo in geos:
        print(f"Processing: {geo}")
        shapes = []
        node_type = cmds.nodeType(geo)

        if node_type == 'transform':
            shapes = cmds.listRelatives(geo, shapes=True, noIntermediate=True) or []
        elif node_type in ('mesh', 'nurbsSurface', 'subdiv'):
            shapes = [geo]
        else:
            cmds.warning(
                f"Unsupported node type '{node_type}' for {geo}. Skipping."
            )
            continue

        if not shapes:
            cmds.warning(f"No shape nodes found for {geo}, skipping.")
            continue

        for shape in shapes:
            print(f"  Shape: {shape}")
            # Add long attribute to shape if missing
            if not cmds.attributeQuery(rig_attr, node=shape, exists=True):
                cmds.addAttr(
                    shape,
                    longName=rig_attr,
                    attributeType='long',
                    keyable=False
                )

            # Connect rig_top.rig_attr -> shape.rig_attr
            dest_attr = f"{shape}.{rig_attr}"
            if not cmds.isConnected(mid_attr, dest_attr):
                cmds.connectAttr(mid_attr, dest_attr, force=True)


def create_proximity_wrap(geometry, influences, name=None, **attrs):
    """
    THIS IS A CONVERSION FROM THE CLASS CREATE IN AL1 class ProximityWrap
    Simple function to create Maya's proximityWrap deformer.

    Args:
        geometry (str): Transform or shape to be deformed (mesh, curve, or NURBS surface).
        influences (str or list[str]): Influence geometry that drives the deformation.
        name (str, optional): Name for the deformer node.
        **attrs: Additional attributes including:
            wrapMode (int): Wrapping mode.
            dropoffRateScale (float): Influence dropoff scale.
            smoothInfluences (float): Smooth driver influences.

    Returns:
        str: The proximity wrap deformer node name.
    """

    if isinstance(geometry, (list, tuple)):
        geometry = geometry[0]
    elif not isinstance(geometry, pmc.PyNode):
        geometry = pmc.PyNode(geometry)

    if not name:
        name = str(geometry) + "_proxyWrap"

    print(geometry)
    node_ = pmc.deformer(geometry, type='proximityWrap', name=name)[0]

    influence_list = influences if isinstance(influences, (list, tuple)) else [influences]

    for i, influence in enumerate(influence_list):
        if not isinstance(influence, pmc.PyNode):
            influence_list[i] = pmc.PyNode(influence)

    interface = NodeInterface(str(node_))

    for influence in influence_list:
        shape = influence.listRelatives(shapes=True, fullPath=True, noIntermediate=True)[0]
        interface.addDriver(str(shape))

    for attr, value in attrs.items():
        pmc.setAttr(f"{node_}.{attr}", value)

    return str(node_)


def create_wire_deformer(main_curve, up_curve, geometry_or_vertices,
                         up_controllers, num_twists=10, dropoff_distance=1000000000,
                         rebuild_spans=None, vertex_indices=None):
    """Create wire deformer with twist controls

    Args:
        main_curve: Primary curve that drives the wire deformer
        up_curve: Curve that defines the up vector orientation
        geometry_or_vertices: Mesh/vertices to deform
        up_controllers: List of controllers for rotation up
        num_twists: Number of twist control points along the curve
        dropoff_distance: Wire deformer dropoff distance
        rebuild_spans: Number of spans for curve rebuild (optional)
        vertex_indices: Optional vertex indices

    Returns:
        PyNode: Main group containing all created elements
    """

    # Get parent master and grandparent from first controller's long name
    first_ctrl_long = up_controllers[0].longName()
    hierarchy_parts = str(first_ctrl_long).split('|')

    # Find the last _root before the controller
    master_parent = None
    grandparent = None

    # Get the index of our controller
    ctrl_index = len(hierarchy_parts) - 1

    # Search backwards from controller to find the closest _root
    for i in range(ctrl_index - 1, -1, -1):
        if hierarchy_parts[i].endswith('_root'):
            master_parent = hierarchy_parts[i]
            # Find the controller immediately before this _root
            for j in range(i - 1, -1, -1):
                if '_ctrl' in hierarchy_parts[j]:
                    grandparent = hierarchy_parts[j]
                    break
            break

    main_curve = pmc.PyNode(main_curve)
    up_curve = pmc.PyNode(up_curve)

    all_nodes = pmc.ls(master_parent)

    for node_ in all_nodes:
        if not pmc.hasAttr(node_, 'isGearGuide'):
            master_parent = node_
            break

    master_parent.inheritsTransform.set(0)

    if not up_controllers or len(up_controllers) != num_twists:
        raise ValueError(f"up_controllers must have {num_twists} elements")

    # Process deform targets
    has_vertices = False
    if vertex_indices is not None:
        mesh = pmc.PyNode(geometry_or_vertices)
        parts = []
        for idx in vertex_indices:
            parts.append(f'{idx[0]}:{idx[1]}' if isinstance(idx, tuple) else str(idx))
        deform_targets = [f'{mesh}.vtx[{",".join(parts)}]']
        has_vertices = True
    else:
        targets = geometry_or_vertices if isinstance(geometry_or_vertices, (list, tuple)) else [geometry_or_vertices]
        # Check if targets contain vertices
        for t in targets:
            if '.vtx[' in str(t):
                has_vertices = True
                break
        deform_targets = [t if '.vtx[' in str(t) else pmc.PyNode(t) for t in targets]

    # If no vertices specified, create joint and bind skin
    # Create joint and bind to each geometry
    offsetfix_joint = pmc.joint(name=str(up_controllers[0]) + "offsetFix")
    offsetfix_joint.setParent(grandparent)
    # pmc.makeIdentity(offsetfix_joint, apply=True, translate=True, rotate=True, scale=True)

    # skinCluster binds only single geometry at a time
    skin_clusters = []
    for geo in deform_targets:
        if '.vtx[' in str(geo):
            mesh = str(geo).split('.')[0]
            mesh = pmc.PyNode(mesh)
            vertices = geo
        else:
            mesh = pmc.PyNode(geo)
            vertices = None

        existing_skin = pmc.listHistory(mesh, type='skinCluster')

        if existing_skin:
            skin_cluster = existing_skin[0]

            original_normalize = skin_cluster.normalizeWeights.get()

            skin_cluster.normalizeWeights.set(1)  # 1 = Interactive

            current_influences = pmc.skinCluster(skin_cluster, query=True, influence=True)

            if offsetfix_joint not in current_influences:
                pmc.skinCluster(skin_cluster, edit=True, addInfluence=offsetfix_joint, weight=0.0)

            if vertices:
                pmc.skinPercent(skin_cluster, vertices,
                                transformValue=[(offsetfix_joint, 1.0)])
            else:
                pmc.skinPercent(skin_cluster, mesh,
                                transformValue=[(offsetfix_joint, 1.0)])

            skin_cluster.normalizeWeights.set(original_normalize)

            skin_clusters.append(skin_cluster)
        else:
            if vertices:
                skin_cluster = pmc.skinCluster(offsetfix_joint, mesh, toSelectedBones=True, name=f'{mesh}_skinCluster')
                pmc.skinPercent(skin_cluster, vertices,
                                transformValue=[(offsetfix_joint, 1.0)])
            else:
                skin_cluster = pmc.skinCluster(offsetfix_joint, geo, toSelectedBones=True, name=f'{geo}_skinCluster')

            skin_clusters.append(skin_cluster)

    offsetfix_joint.visibility.set(0)
    if rebuild_spans:
        for curve in [main_curve, up_curve]:
            pmc.rebuildCurve(curve, spans=rebuild_spans, keepRange=0, keepControlPoints=0, degree=3)

    wire_result = pmc.wire(deform_targets, wire=main_curve, dropoffDistance=(0, dropoff_distance), groupWithBase=True)
    wire_deformer = wire_result[0]
    grp = pmc.group(main_curve + "BaseWire")
    pmc.parent(grp, offsetfix_joint)

    main_shape = main_curve.getShape()
    u_min = main_shape.minValue.get()
    u_max = main_shape.maxValue.get()

    main_group = pmc.group(empty=True, name=f'{main_curve}_wire_setup')
    twist_group = pmc.group(empty=True, name=f'{main_curve}_twist_grp', parent=main_group)

    controls = []

    for i in range(num_twists):
        u_norm = float(i) / float(num_twists - 1) if num_twists > 1 else 0.5
        u_actual = u_min + (u_max - u_min) * u_norm

        pmc.select(f'{main_curve}.u[{u_actual}]')
        pmc.dropoffLocator(1.0, 1.0, wire_deformer)

        # Create control
        ctrl = pmc.spaceLocator(name=f'{main_curve}_twistControl_{i:02d}')
        ctrl.setParent(twist_group)
        ctrl.visibility.set(False)

        # Main motion path with Object Rotation Up
        mp_main = pmc.createNode('motionPath', name=f'{main_curve}_mp_main_{i:02d}')
        main_shape.worldSpace[0] >> mp_main.geometryPath
        mp_main.fractionMode.set(True)
        mp_main.uValue.set(u_norm)
        mp_main.follow.set(True)
        mp_main.frontAxis.set(0)  # X as front
        mp_main.upAxis.set(2)  # Z as up

        # Object Rotation Up setup
        mp_main.worldUpType.set(2)
        up_ctrl = pmc.PyNode(up_controllers[i])
        up_ctrl.worldMatrix[0] >> mp_main.worldUpMatrix
        mp_main.worldUpVector.set([0, 1, 0])  # Y axis of controller as up

        # Connect outputs
        mp_main.allCoordinates >> ctrl.translate
        mp_main.rotate >> ctrl.rotate

        # Adjust orientation
        mp_main.sideTwist.set(-90)
        mp_main.inverseUp.set(1)
        mp_main.inverseFront.set(0)

        # Create local locator and group it
        local_loc = pmc.spaceLocator(name=f'{main_curve}_localTwist_{i:02d}')
        local_grp = pmc.group(local_loc, name=f'{main_curve}_localTwist_grp_{i:02d}')

        # Match group transformation to up_ctrl
        pmc.matchTransform(local_grp, up_ctrl)

        # Parent group to grandparent
        local_grp.setParent(grandparent)

        # Parent constraint with maintainOffset=False
        pc = pmc.parentConstraint(up_ctrl, local_loc, maintainOffset=False)
        pc.interpType.set(2)  # 2 = shortest

        # Connect local_loc rotateX directly to wire deformer twist
        local_loc.rotateX.connect(wire_deformer.wireLocatorTwist[i])

        controls.append(ctrl)
        local_loc.visibility.set(0)

    return main_group


def create_buffer_groups(nodes, name_suffix="buffer_grp", use_match_transform=True):
    """
    Create a buffer group for given nodes.

    Args:
        nodes(list): The objects for which buffer creation shall be executed.
                     List of pmc.PyNodes().
        name_suffix(str): Suffix of the buffer nodes.
        use_match_transform(bool): Uses the match transform command to match the nodes WS pos.
                                   If False we use the xForm command to match the nodes WS pos.

    Return:
        List: New buffer groups.

    """
    buffer_nodes = []

    if not isinstance(nodes, list):
        nodes = [nodes]

    for node_ in nodes:

        name = f"{node_.name()}_{name_suffix}"

        if use_match_transform:
            parent_nde = node_.getParent()

            buffer_nde = pmc.createNode("transform", name=name)
            pmc.matchTransform(buffer_nde, node_)
            buffer_nde.addChild(node_)

            if parent_nde:
                parent_nde.addChild(buffer_nde)
            buffer_nodes.append(buffer_nde)

        else:
            buffer_nde = pmc.group(node_, n=name)

            pivot = pmc.xform(node_, query=True, worldSpace=True, rotatePivot=True)
            pmc.xform(buffer_nde, worldSpace=True, rotatePivot=pivot)
            pmc.xform(buffer_nde, worldSpace=True, scalePivot=pivot)

            buffer_nodes.append(buffer_nde)

    return buffer_nodes


def convert_any_pynodes(nodes):
    if not isinstance(nodes, list):
        nodes = [nodes]

    return [str(node_) if isinstance(node_, pmc.PyNode) else node_ for node_ in nodes]



class PinXform(object):
    """
    This allows you to pin a transform so that its parent and child are not affected by transform edits.
    """
    def __init__(self, xform_name):

        self.xform = str(xform_name)
        self.delete_later = []
        self.lock_state = {}

    def pin(self, pin_children=None):
        """
        Create the pin constraints on parent and children.
        """
        if pin_children:
            pin_children = convert_any_pynodes(pin_children)

        if not pin_children:
            pin_children = cmds.listRelatives(self.xform, f=True, type='transform')
        if not pin_children:
            return
        for child in pin_children:
            if not cmds.objectType(child, isAType='transform'):
                continue
            pin = cmds.duplicate(child, po=True, n='pin1')[0]

            try:
                cmds.parent(pin, w=True)
            except Exception:
                pass

            try:
                pin_constraint = cmds.parentConstraint(pin, child, mo=True)[0]
                self.delete_later.append(pin_constraint)
            except Exception:
                pass
            self.delete_later.append(pin)
            pin_parent = cmds.listRelatives(pin, p=True, f=True)
            if pin_parent:
                self.delete_later.append(pin_parent[0])

    def unpin(self):
        """
        Remove the pin. This should be run after pin.
        """
        if self.delete_later:
            cmds.delete(self.delete_later)

    def get_pin_nodes(self):
        """
        Returns:
            list: List of nodes involved in the pinning. Usually includes constraints and empty groups.
        """
        return self.delete_later


class XformTransfer(object):
    """
    Wrap deform joints from one mesh to another.
    """
    def __init__(self):
        self.scope = None
        self.source_mesh = None
        self.target_mesh = None
        self.particles = None
        self._use_delta_mush = False
        self._delta_mush_iterations = 1000

    def _match_particles(self, scope):
        xforms = []
        for transform in self.scope:
            transform_position = cmds.xform(transform, q=True, ws=True, rp=True)
            xforms.append(transform_position)
        self.particles = cmds.particle(p=xforms)[0]

    def _wrap_particles(self):
        if self.particles and self.source_mesh:
            create_wrap_deformer(pmc.PyNode(self.source_mesh), pmc.PyNode(self.particles))

    def _blend_to_target(self):
        cmds.blendShape(self.target_mesh, self.source_mesh, weight=[0, 1], origin='world')

    def _delta_mush_target(self):
        if not self._use_delta_mush:
            return
        mush = cmds.deltaMush(self.source_mesh)[0]
        cmds.setAttr(f'{mush}.smoothingIterations', self._delta_mush_iterations)
        cmds.setAttr(f'{mush}.smoothingStep', .3)
        cmds.setAttr(f'{mush}.inwardConstraint', 1)
        cmds.setAttr(f'{mush}.outwardConstraint', 1)
        cmds.setAttr(f'{mush}.distanceWeight', 1)
        mush2 = cmds.deltaMush(self.source_mesh)[0]
        cmds.setAttr(f'{mush2}.smoothingIterations', 30)

    def _move_to_target(self):
        for inc in range(0, len(self.scope)):
            particle_position = cmds.pointPosition('%s.pt[%s]' % (self.particles, inc))
            transform = self.scope[inc]
            if transform.endswith('_crv'):
                continue
            if cmds.nodeType(transform) == 'joint':
                cmds.move(particle_position[0], particle_position[1], particle_position[2], '%s.scalePivot' % transform,
                          '%s.rotatePivot' % transform, a=True)
            if not cmds.nodeType(transform) == 'joint' and cmds.nodeType(transform) == 'transform':
                cmds.move(particle_position[0], particle_position[1], particle_position[2], transform, a=True)

    def _cleanup(self):
        cmds.delete([self.particles, self.source_mesh])

    def store_relative_scope(self, parent):
        """
        Set all transforms under parent.

        Args:
            parent (str): The name of a parent transform.
        """
        parent = str(parent)
        self.scope = cmds.listRelatives(parent, allDescendents=True, type='transform')
        self.scope.append(parent)

    def set_scope(self, scope):
        """
        Set the transforms to work on.

        Args:
            scope (list): Names of transforms.
        """
        convert_any_pynodes(scope)
        self.scope = scope

    def set_source_mesh(self, name):
        """
        Source mesh must match point order of target mesh.
        """
        self.source_mesh = str(name)

    def set_target_mesh(self, name):
        """
        Target mesh must match point order of source mesh.
        """
        self.target_mesh = str(name)

    def set_use_delta_mush(self, bool_value, iterations):
        self._use_delta_mush = bool_value
        self._delta_mush_iterations = iterations

    def run(self):
        """
        Perform the transfer.
        """
        if not self.scope:
            return

        if not cmds.objExists(self.source_mesh):
            return

        if not cmds.objExists(self.target_mesh):
            return

        self.source_mesh = cmds.duplicate(self.source_mesh)[0]
        self._match_particles(self.scope)
        self._wrap_particles()
        self._blend_to_target()
        self._delta_mush_target()
        self._move_to_target()
        self._cleanup()
