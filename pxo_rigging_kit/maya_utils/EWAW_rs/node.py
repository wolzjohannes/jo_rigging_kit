from copy import deepcopy

import maya.cmds as cmds
from maya import OpenMaya as om1
from maya.api import OpenMaya as om2
from pymel import core as pmc

from typing import Optional, Union
import logging

from pxo_rigging_kit.maya_utils import openmaya_utils

##########################################################

# GLOBALS

##########################################################

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)


# create nodes with tags, so we can search for them AND KILL THEM AAAAALLLL
def createNode(*args,
               tag: Optional[str] = None,
               as_type: str = "cmds",
               **kwargs,
               ) -> Union[str, pmc.PyNode, om1.MObject ,om2.MObject]:

    _available_types = ("cmds",
                        "pymel",
                        "maya_api_1",
                        "maya_api_2"
                        )

    node = cmds.createNode(*args, **kwargs)

    if tag:
        cmds.addAttr(node, ln=tag, at="message")

    if isinstance(node, str):
        node_mobj = openmaya_utils.get_mobject_om2(node)

        if openmaya_utils.is_of_type(node_mobj,
                                     om2.MFn.kJoint,
                                     ):
            pass

    if as_type == "cmds":
        return node

    elif as_type == "pymel":
        return pmc.PyNode(node) if isinstance(node, str) else tuple(pmc.PyNode(nde_) for nde_ in node)

    elif as_type == "maya_api_1":
        return openmaya_utils.get_mobject_om1(node)
        # return node if isinstance(node, str) else tuple(pmc.PyNode(nde_) for nde_ in node)

    elif as_type == "maya_api_2":
        return openmaya_utils.get_mobject_om2(node)
        # return node if isinstance(node, str) else tuple(pmc.PyNode(nde_) for nde_ in node)

    else:
        _LOGGER.warning(f"no valid type was given: you gave {as_type}, "
                        f"available are {' | '.join(_available_types)}.\n"
                        f"therefore giving you a cmds node")
        return node


def addAttr(*args, **kwargs) -> str:
    """
    Wrapper to add attributes to a node. This will ignore the creation and return the attr if it already exists.

    Args:
        *args: The arguments you would normally put into the cmds.addAttr.
        **kwargs: The keyworded arguments you would normally put into the cmds.addAttr.

    Returns:
        Str(attr_name_full_): The attribute plus node name.

    """

    node_name_ = args[0]
    _LOGGER.debug(f"Node name given was: {node_name_}")

    try:
        attr_name_ = kwargs["ln"]
    except KeyError:
        attr_name_ = kwargs["longName"]

    try:
        try:
            parent_name_ = f".{kwargs['p']}."
        except KeyError:
            parent_name_ = f".{kwargs['parent']}."

    except KeyError:
        parent_name_ = "."

    attr_name_full_ = f"{node_name_}{parent_name_}{attr_name_}"

    if cmds.objExists(attr_name_full_):
        _LOGGER.debug(f"{attr_name_full_} already existed")
        return attr_name_full_

    cmds.addAttr(*args, **kwargs)

    return attr_name_full_

# We alread yhave this in the attibutes_utils.py
def add_from_dict(node_name: str, adds: dict, sets: dict):
    """
    This adds attributes from a dict and sets the values as default values.

    Args:
        node_name:
        adds:
        sets:

    Returns:

    """

    raise NotImplementedError("still needs to be done.")
    # Add Attrbiutes
    addAttr = {

        "separator_00":    {
            "longName":      "separator_00",
            "attributeType": "enum",
            "niceName":      " ",
            "enumName":      " ",
            "setAttr":       {
                "keyable":    False,
                "channelBox": True,
                "lock":       True,
            }
        },

        "controllerSize":  {
            "longName":      "controllerSize",
            "attributeType": "float",
            "minValue":      0.01,
            "defaultValue":  round(size[-1] * 0.75),
            "setAttr":       {
                "keyable":    False,
                "channelBox": True,
                "lock":       False,
            }
        },

        "separator_01":    {
            "longName":      "separator_01",
            "attributeType": "enum",
            "niceName":      " ",
            "enumName":      " ",
            "setAttr":       {
                "keyable":    False,
                "channelBox": True,
                "lock":       True,
            }
        },

        "blendTranslateX": {
            "longName":      "blendTranslateX",
            "attributeType": "float",
            "minValue":      0,
            "maxValue":      100,
            "defaultValue":  100,
            "setAttr":       {
                "keyable":    True,
                "channelBox": True,
                "lock":       False,
            }
        },

        "blendTranslateY": {
            "longName":      "blendTranslateY",
            "attributeType": "float",
            "minValue":      0,
            "maxValue":      100,
            "defaultValue":  100,
            "setAttr":       {
                "keyable":    True,
                "channelBox": True,
                "lock":       False,
            }
        },

        "blendTranslateZ": {
            "longName":      "blendTranslateZ",
            "attributeType": "float",
            "minValue":      0,
            "maxValue":      100,
            "defaultValue":  100,
            "setAttr":       {
                "keyable":    True,
                "channelBox": True,
                "lock":       False,
            }
        },

        "blendRotateX":    {
            "longName":      "blendRotateX",
            "attributeType": "float",
            "minValue":      0,
            "maxValue":      100,
            "defaultValue":  100,
            "setAttr":       {
                "keyable":    True,
                "channelBox": True,
                "lock":       False,
            }
        },

        "blendRotateY":    {
            "longName":      "blendRotateY",
            "attributeType": "float",
            "minValue":      0,
            "maxValue":      100,
            "defaultValue":  100,
            "setAttr":       {
                "keyable":    True,
                "channelBox": True,
                "lock":       False,
            }
        },

        "blendRotateZ":    {
            "longName":      "blendRotateZ",
            "attributeType": "float",
            "minValue":      0,
            "maxValue":      100,
            "defaultValue":  100,
            "setAttr":       {
                "keyable":    True,
                "channelBox": True,
                "lock":       False,
            }
        },

    }

    for key, value in deepcopy(addAttr).items():
        setAttr = value.pop("setAttr")

        # Add attribute
        cmds.addAttr(
                node_name,
                **value
        )

        # Set attribute
        cmds.setAttr(
                f"{node_name}.{value['longName']}",
                **setAttr
        )

    setAttr = {

        "scaleX":      {
            "keyable":    False,
            "channelBox": False,
            "lock":       True,
        },

        "scaleY":      {
            "keyable":    False,
            "channelBox": False,
            "lock":       True,
        },

        "scaleZ":      {
            "keyable":    False,
            "channelBox": False,
            "lock":       True,
        },

        "visibility":  {
            "keyable":    False,
            "channelBox": True,
            "lock":       False,
        },

        "rotateOrder": {
            "keyable":    False,
            "channelBox": True,
            "lock":       False,
        },

    }

    # Set default attributes
    for attr, setAttr in deepcopy(setAttr).items():
        cmds.setAttr(
                f"{transform}.{attr}",
                **setAttr,
        )
