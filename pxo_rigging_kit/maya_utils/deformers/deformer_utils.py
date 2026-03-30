# Author:     Johannes Wolz / Head of Rigging

"""
This module is for managing all deformers in maya which are not Skinclusters or Blendshape nodes.
"""

# Import future modules
from __future__ import absolute_import, division, print_function, unicode_literals
from __future__ import division
from __future__ import print_function

# Import python standart import
import logging
import copy

# Import third-party modules
from future import standard_library

# Import Maya specific modules
import pymel.core as pmc
from maya import cmds as cmds
from maya.internal.nodes.proximitywrap.node_interface import NodeInterface

from pxo_rigging_kit.io_version_control import version_io

standard_library.install_aliases()

##########################################################
# GLOBALS
##########################################################

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)
IO_MANAGER = version_io.ImportExport()

##########################################################
# FUNCTIONS
##########################################################


def apply_tension_deformer(target_mesh: pmc.PyNode, options_dict: dict):
    """
    Applies a tension deformer to given target mesh.

    Args:
        target_mesh(pmc.PyNode()): The target mesh/transform.
        options_dict(dict): The command flacs as keys and values.
                            The command flags can be found here:
                            https://help.autodesk.com/cloudhelp/2022/ENU/Maya-Tech-Docs/PyMel/generated/functions
                            /pymel.core.animation
                            /pymel.core.animation.tension.html?highlight=tension#pymel.core.animation.tension
                            We added additional flags to the options which are not provided by the command.
                            The new flags have shortforms also.
                            These are:
                            "relative" --> "rel"
                            "shear_strength" --> "sst"
                            "bend_strength" --> "bst"
        Example:
                {
                    "name": "lowerLeg_tension_def",
                    "si": 10.0, "ss":1.0, "iwc":0,
                    "owc":0, "relative":0.5,
                    "shear_strength":0.5, "bend_strength":0.5,
                }

    """
    temp_options_dict = copy.deepcopy(options_dict)
    temp_options_dict.pop("relative", None) or temp_options_dict.pop(
        "rel", None
    )
    temp_options_dict.pop("shear_strength", None) or temp_options_dict.pop(
        "sst", None
    )
    temp_options_dict.pop("bend_strength", None) or temp_options_dict.pop(
        "bst", None
    )
    relative = options_dict.get("relative") or options_dict.get("rel")
    shear_strength = options_dict.get("shear_strength") or options_dict.get(
        "sst"
    )
    bend_strength = options_dict.get("bend_strength") or options_dict.get("bst")
    pmc.select(target_mesh)
    tension_def = pmc.tension(**temp_options_dict)
    if relative:
        tension_def.relative.set(relative)
    if shear_strength:
        tension_def.shearStrength.set(shear_strength)
    if bend_strength:
        tension_def.bendStrength.set(bend_strength)
    pmc.select(clear=True)


def serial_apply_tension_deformer(target_mesh: pmc.PyNode, options_list: list):
    """
    With this function you can apply a lot of tension deformers into a stack on top each other.

    Args:
        target_mesh(pmc.PyNode()): The target mesh/transform.
        options_list(list): The command flacs as keys and values for each deformer as dict in this list.
                            Each dict in this represents a deformer in the stack.
        Example:
            [
                {
                    "name": "lowerLeg_tension_def",
                    "si": 10.0, "ss":1.0, "iwc":0,
                    "owc":0, "relative":0.5,
                    "shear_strength":0.5, "bend_strength":0.5,
                 },
                {
                    "name": "upperLeg_tension_def",
                    "si": 30.0, "ss":0.5, "iwc":0,
                    "owc":0, "relative":0.5,
                    "shear_strength":0.0, "bend_strength":0.0,
                 },
                {
                    "name": "shoulder_tension_def",
                    "si": 10.0, "ss":1.0, "iwc":0,
                    "owc":0, "relative":1,
                    "shear_strength":0.5, "bend_strength":0.5,
                 }]

    """
    for data_dict in options_list:
        apply_tension_deformer(target_mesh, data_dict)


def import_tension_weights(options_list: list):
    """
    Imports of the tension deformer weights located in the data folder of the asset.

    Args:
        options_list(list): The command flacs as keys and values for each deformer as dict in this list.
                            Each dict in this represents a deformer in the stack.
                            The name flag as key in the dict defines the target deformer for the imported weights.

    """
    for data_dict in options_list:
        deformer_name = data_dict.get("name")
        IO_MANAGER.load(object_name=deformer_name, data_type="deformer_weights")


def export_tension_weights(deformers: list or str):
    """
    Exports the tension deformer weights to the projects data folder of the asset.

    Args:
        deformers(list or str): List of the names for the deformers you want to export.
                                Or just the name of a single deformer.sss
    """
    if not isinstance(deformers, list):
        deformers = [deformers]
    for deformer in deformers:
        IO_MANAGER.write(object_name=deformer, data_type="deformer_weights")


class ProximityWrap:

    """
    Simple wrapper for Maya's proximityWrap deformer.

    Args:
        target (str): Transform or mesh shape to wrap.
        drivers (str or list[str]): Driver mesh(es) for the wrap.
        name (str, optional): Name for the deformer node.
        **attrs: Additional attributes including:
            wrapMode (int): Wrapping mode.
            dropoffRateScale (float): Influence dropoff scale.
            smoothInfluences (float): Smooth driver influences.
    """
    def __init__(self, target, drivers, name=None, **attrs):
        if not name:
            name=target+"_proxyWrap"
        node = cmds.deformer(target, type='proximityWrap', name=name)[0]
        self.node = node
        self.interface = NodeInterface(node)

        drvs = drivers if isinstance(drivers, (list, tuple)) else [drivers]
        for d in drvs:
            shape = cmds.listRelatives(d, shapes=True, fullPath=True,noIntermediate=True)[0]
            self.interface.addDriver(shape)

        for a, v in attrs.items():
            cmds.setAttr(f"{node}.{a}", v)
        print()
