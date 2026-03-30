# Author:     Johannes Wolz / Lead Rigging TD

"""
OpenMaya python plugin which establish addAttributeChangedCallback
for the dynamic simple rigs. These enables the proxy switching with
a enum attibute on a rig control.
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
import logging

# Import third-party modules
import maya.api.OpenMaya as om
from maya.api import OpenMaya as om2
import maya.cmds as cmds
import pymel.core as pmc
from maya_proxy_node import interaction

# Import local modules
from pxo_rigging_kit import constants
from pxo_rigging_kit.maya_utils.rigging import rig_utils
from pxo_rigging_kit.maya_utils import pymel_utils

##########################################################
# GLOBAL
##########################################################

AFTER_OPEN_SCENE_CALLBACK_ID = []
PLUGIN_NAME = "pxo_simple_rig_lod_switching"
_LOGGER = logging.getLogger(__name__ + ".py")

##########################################################
# FUNCTIONS
##########################################################


def maya_useNewAPI():
    """
    The presence of this function tells Maya that the plugin produces, and
    expects to be passed, objects created using the Maya Python API 2.0.
    """
    pass


def _get_simple_dynamic_rigs():
    """
    Get all simple dynamic rigs from the scene
    
    Return:
        Empty list if fail.
        List with pmc.PyNodes().
    """
    return [
        node
        for node in rig_utils.get_rig_containers()
        if True is node.hasAttr(constants.SIMPLE_DYN_RIG_META_ATTR) and True is node.attr(constants.SIMPLE_DYN_RIG_META_ATTR).get()
    ]


def _get_bbox_ctrl_from_rig_container(rig_container):
    """
    Get the bbox ctrl from the rig container.
    
    Return:
        Empty list if fail.
        List with pmc.PyNodes().
    """
    return [
        node.getTransform()
        for node in rig_container.getChildren(ad=True, type="nurbsCurve")
        if constants.SIMPLE_RIG_BBOX_CTRL_DECLARATION_NAME in node.name(long=None)
    ]

def _get_callback_nodes():
    """
    Get the callback nodes from the scene
    
    Return:
        False if no simple rigs in the scene.
        List with pmc.PyNodes().
    """
    result = []
    simple_rigs = _get_simple_dynamic_rigs()
    if not simple_rigs:
        return False
    for simple_rig in simple_rigs:
        callback_node = _get_bbox_ctrl_from_rig_container(simple_rig)
        if not callback_node:
            _LOGGER.warning(f"{simple_rig} has no callback node.")
            continue
        sel = om2.MSelectionList()
        sel.add(str(callback_node[0].name()))
        settingsMob = sel.getDependNode(0)
        result.append((settingsMob, callback_node[0]))
    return result

def lod_switch_callback(callback_node):
    """
    
    """
    proxy_reference_nodes = callback_node.attr(constants.PROXY_REF_ND_ATTR).get().split(";")
    enum_dict = callback_node.attr(constants.PROXY_REP_ATTR_NAME).getEnums()
    current_resolution_str = enum_dict.key(callback_node.attr(constants.PROXY_REP_ATTR_NAME).get())
    current_selection = pmc.ls(sl=True)
    for node_name in proxy_reference_nodes:
        proxy_nd = pmc.ls(node_name)
        current_parent = proxy_nd[0].getParent()
        pmc.parent(proxy_nd, None)
        pmc.select(proxy_nd)
        interaction.switch_selected(current_resolution_str)
        pmc.parent(proxy_nd, current_parent)
        pmc.select(clear=True)
    pmc.select(current_selection)


def callback(msg, plug1, plug2, payload):
    """
    Open Maya API callback function. Exectue the real callback.
    Args:
            msg(MMessage): The message given back from the API.
            plug1(MPlug): The first triggered plug of the node.
            plug2(MPlug): The second triggered plug of the node.
            payload(): clientData pass in argument.
    Return:
            The message and the plug of the triggered node.
    """
    # Check if a plug of the channelbox is triggered. If not fall out.
    if msg != 2056:
        return
    # Check if the attribute we want is triggered. If not fall out.
    if not plug1.partialName(
        includeNodeName=False, useAlias=False) == constants.PROXY_REP_ATTR_NAME:
        return
    lod_switch_callback(payload)

def _removeCallbacksFromNode(node_mob):
    """
    Remove all callback stick to a node.
    Args:
            node_mob(MObject): The node to remove all node
                               callbacks from.
    Return:
            Int: Number of callbacks removed
    """
    cbs = om2.MMessage.nodeCallbacks(node_mob)
    cbCount = len(cbs)
    for eachCB in cbs:
        om2.MMessage.removeCallback(eachCB)
    return cbCount

def kill_callbacks():
    """
    Kill all callbacks stored in the global CALLBACK_IDS var.
    """
    _LOGGER.info("Kill pxo dynamic simple rig callbacks.")
    callback_nodes = _get_callback_nodes()
    if not callback_nodes:
        return
    for settingsMob, callback_node in callback_nodes:
        count = _removeCallbacksFromNode(settingsMob)
        _LOGGER.info(f"Removed {count} pxo dynamic simple rig callbacks for {callback_node}.")


def create_node_callbacks():
    """
    Create all callbacks and store the IDs in the global CALLBACK_IDS var.
    """
    _LOGGER.info("Create pxo dynamic simple rig callbacks.")
    callback_nodes = _get_callback_nodes()
    if not callback_nodes:
        return
    for index, (settingsMob, callback_node) in enumerate(callback_nodes):
        count = _removeCallbacksFromNode(settingsMob)
        _LOGGER.info(f"Removed {count} pxo dynamic simple rig callbacks for {callback_node}.")
        om2.MNodeMessage.addAttributeChangedCallback(settingsMob, callback, callback_node)
        _LOGGER.info(f"Added pxo dynamic simple rig callback to {callback_node}.")


def after_open_scene(*args):
    _LOGGER.info("Run after scene open.")
    create_node_callbacks()


def initializePlugin(plugin):
    vendor = "Johannes Wolz"
    version = "0.0.1"

    global AFTER_OPEN_SCENE_CALLBACK_ID
    om.MFnPlugin(plugin, vendor, version)
    create_node_callbacks()
    if not AFTER_OPEN_SCENE_CALLBACK_ID:
        AFTER_OPEN_SCENE_CALLBACK_ID.append(
            om.MSceneMessage.addCallback(
                om.MSceneMessage.kAfterOpen,
                after_open_scene,
            )
        )


def uninitializePlugin(plugin):
    global AFTER_OPEN_SCENE_CALLBACK_ID
    om.MMessage.removeCallbacks(AFTER_OPEN_SCENE_CALLBACK_ID)
    AFTER_OPEN_SCENE_CALLBACK_ID = []
    kill_callbacks()


if __name__ == "__main__":
    """
    For Development Only

    Specialized code that can be executed through the script editor to speed up the development process.

    For example: scene cleanup, reloading the plugin, loading a test scene
    """

    # Any code required before unloading the plug-in (e.g. creating a new scene)


    # Reload the plugin
    cmds.evalDeferred('if cmds.pluginInfo("{0}", q=True, loaded=True): cmds.unloadPlugin("{0}")'.format(PLUGIN_NAME))
    cmds.evalDeferred('if not cmds.pluginInfo("{0}", q=True, loaded=True): cmds.loadPlugin("{0}")'.format(PLUGIN_NAME))


    # Any setup code to help speed up testing (e.g. loading a test scene)
