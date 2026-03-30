"""
The use case for this module is to assign utility shaders for specific rigging tasks.

www.pixomondo.com
Date: 17 / 11 / 2023

shader module
category : Rigging
subcategory : utils
author : Christof Puehringer / Rigging TD


''' to run it in scene:

# assign clown-shading
assign_to_meshes_random()


# assign checker material
assign_checker(object_to_shade,
                   material_name="checker",
                   material_type="lambert"
                   )
from pxo_rigging_kit.maya_utils import shader_utils
from pymel import core as pmc
from importlib import reload

reload(shader_utils)

shader_utils.assign_to_meshes_random()
shader_utils.clear()


shader_utils.assign_checker(pmc.selected()[0],
                   material_name="checker",
                   material_type="lambert"
                   )

# assign one-udim to assets
apply_udim_shader_from_asset_assembly(start_at_asset_no=0,
                                      stop_at_asset_no=1)


# remove generated materials
clear()
'''

"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import built-in modules
from builtins import range
from builtins import round
from builtins import str
import logging
import os
import random as random
from pprint import pprint

# Import third-party modules
from future import standard_library
import maya.cmds as cmds
from maya_scene_io.decorator import disabled_sg_breakdown_refresh
from pixo_paths.paths import normalize as pixo_normpath
import pymel.core as pmc
from importlib import reload

# Import local modules
from pxo_rigging_kit.constants import AVAILABLE_SHADERS
from pxo_rigging_kit.constants import BLEND_CONNECTION_TAG
from pxo_rigging_kit.constants import DISPLACEMENT_TAG
from pxo_rigging_kit.constants import MAX_INDEX
from pxo_rigging_kit.constants import MULTIPLES_TAG
from pxo_rigging_kit.constants import PXO_ASSET_ASSEMBLY_NODE_NAME
from pxo_rigging_kit.constants import SHADER_PROPERTIES
from pxo_rigging_kit.constants import SHADER_UTILS_TAG
from pxo_rigging_kit.constants import SINGLES_TAG
from pxo_rigging_kit.constants import SINGLE_TAG
from pxo_rigging_kit.constants import TEXTURE_TAG
from pxo_rigging_kit.constants import UDIM_EXCLUSION_STRING
from pxo_rigging_kit.constants import UDIM_STRINGS
from pxo_rigging_kit.constants import UV_REPETITION
from pxo_rigging_kit.constants import VARIANT_INDEX
from pxo_rigging_kit.constants import VARIATION_TAG
from pxo_rigging_kit.constants import VIS_CTRL_TOKEN
from pxo_rigging_kit.maya_utils import paths_utils
from pxo_rigging_kit.maya_utils.attributes_utils import (
    get_next_free_array_index,
)
from pxo_rigging_kit.maya_utils.dag_utils import get_deform_shape
from pxo_rigging_kit.maya_utils.mesh_utils import sel_to_meshes
from pxo_rigging_kit.maya_utils.rigging.rig_utils import get_object_size
from pxo_rigging_kit.versioncontrol_utils import get_latest_path
from pxo_rigging_kit import constants

reload(constants)
##########################################################
# GLOBALS
##########################################################

standard_library.install_aliases()

_LOGGER = logging.getLogger(__name__ + ".py")

_LOGGER.setLevel(logging.INFO)
_COLOR_VARIANTS = {
    "light_mode": {
        "checkerboard_color1": (0.64, 0.64, 0.64),
        "checkerboard_color2": (0.45, 0.45, 0.45),
    },
    "dark_mode": {
        "checkerboard_color1": (0.16, 0.16, 0.16),
        "checkerboard_color2": (0.25, 0.25, 0.25),
    },
}


##########################################################
# FUNCTIONS
##########################################################


def assign_shader(
    object_to_shade=None,
    material_name="",
    material_type="lambert",
    material_color=(0.5, 0.5, 0.5),
    material_transp=(0, 0, 0),
    material_refl=(0, 0, 0),
    specular_color=(0.5, 0.5, 0.5),
):
    """
    Function to apply a shader and material to an object.

    Args:
        object_to_shade(pymel.core.PyNode): Object to be shaded.

        material_name(string): Name of the material.

        material_type(string): Type of material assigned.

        material_color(tuple): The color of the material.

        material_transp(tuple): The transparency of the material.

        material_refl(tuple): The reflection of the material.

        specular_color(tuple): The specular of the material.


    Returns:
         Tuple(material, shader): The created maya material.
                                  tuple(pymel.core.PyNode(material),
                                        pymel.core.PyNode(shader)
                                  )

    """

    if not object_to_shade:
        return None

    if material_name == "":
        material_name = "default_{object}_{type}Mat".format(
            object=object_to_shade.shortName(),
            type=AVAILABLE_SHADERS[material_type],
        )

    if not pmc.objExists(material_name):
        #   Create Material
        material = pmc.shadingNode(
            material_type, asShader=True, name=material_name
        )
    else:
        material = pmc.PyNode(material_name)

    for attr_name_ in SHADER_PROPERTIES[material_type]:
        if not attr_name_:
            continue

        if (
            attr_name_ == "color"
            and SHADER_PROPERTIES[material_type][attr_name_][0]
        ):
            try:
                material.attr(
                    SHADER_PROPERTIES[material_type][attr_name_][0]
                ).set(material_color)
            except pmc.MayaAttributeError:
                pass

        elif (
            attr_name_ == "transparency"
            and SHADER_PROPERTIES[material_type][attr_name_][0]
        ):
            try:
                material.attr(
                    SHADER_PROPERTIES[material_type][attr_name_][0]
                ).set(material_transp)
            except pmc.MayaAttributeError:
                pass

        elif (
            attr_name_ == "reflection"
            and SHADER_PROPERTIES[material_type][attr_name_][0]
        ):
            try:
                material.attr(
                    SHADER_PROPERTIES[material_type][attr_name_][0]
                ).set(material_refl)
            except pmc.MayaAttributeError:
                pass

        elif (
            attr_name_ == "specular"
            and SHADER_PROPERTIES[material_type][attr_name_][0]
        ):
            try:
                material.attr(
                    SHADER_PROPERTIES[material_type][attr_name_][0]
                ).set(specular_color)
            except pmc.MayaAttributeError:
                pass

        else:
            continue

    if not material.hasAttr(SHADER_UTILS_TAG):
        material.addAttr(SHADER_UTILS_TAG, at="bool", dv=True)

    #   Create Surface Shader
    shader_name = "{0}SurfaceShader".format(material_name)

    shader = pmc.sets(
        renderable=True,
        noSurfaceShader=True,
        empty=True,
        name=shader_name,
    )

    shader.addAttr(SHADER_UTILS_TAG, at="bool", dv=True)

    #   Connect material to shader
    material.outColor.connect(shader.surfaceShader)

    #   Assign shader to objects
    pmc.sets(shader, edit=True, forceElement=object_to_shade)

    return material, shader


def create_shader(
    material_color=None,
    material_name=None,
    material_type=None,
    str_to_shade=None,
):
    """
    Method to create a single shader and material combination without any other connections made.
    If the inputs are left on None it will create a 50% grey lambert shader named "default_{object}_sMat".

    Args:
        str_to_shade(None/str): Object to be shaded.

        material_name(None/str): Name of the material.

        material_type(None/str): Type of material assigned.

        material_color(None/tuple): The color of the material.

    Returns:
         Tuple(material, shader): The created maya material.
                                  tuple(pymel.core.PyNode(material),
                                        pymel.core.PyNode(shader)
                                  )

    """

    object_to_shade = str_to_shade or "defaultGeometry"

    material_type = material_type or "lambert"

    if material_type not in list(AVAILABLE_SHADERS.keys()):
        _LOGGER.error("the material could not be found in available shaders")

    material_color = material_color or (0.5, 0.5, 0.5)

    material_name = material_name or "default_{object}_{type}Mat".format(
        object=object_to_shade, type=AVAILABLE_SHADERS[material_type]
    )

    if not pmc.objExists(material_name):
        #   Create Material
        pmc.shadingNode(material_type, asShader=True, name=material_name)

    material = pmc.PyNode(material_name)
    material.color.set(material_color)

    if not material.hasAttr("scriptGenerated"):
        material.addAttr("scriptGenerated", dt="string")

    #   Create Surface Shader
    shader_name = "{}SurfaceShader".format(material_name)

    shader = pmc.sets(
        renderable=True, noSurfaceShader=True, empty=True, name=shader_name
    )
    shader.addAttr("scriptGenerated", dt="string")

    #   Connect material to shader
    material.outColor.connect(shader.surfaceShader)

    return material, shader


def create_shader_random(
    material_name=None, material_type=None, str_to_shade=None
):
    """
    Creates a shader with random colors based on the rounding factor of 4 decimal points.

    Args:
        material_name (None/str): Name of the material.

        material_type (None/str): Type of material assigned.

        str_to_shade (None/str): Object to be shaded.

    Returns:
         Tuple(material, shader): The created maya material.
                                  tuple(pymel.core.PyNode(material),
                                        pymel.core.PyNode(shader)
                                        )

    """

    return create_shader(
        material_color=random_color(rounding_factor=4),
        material_name=material_name,
        material_type=material_type,
        str_to_shade=str_to_shade,
    )


def assign_checker(
    object_to_shade,
    material_name="checker",
    material_type="lambert",
    clear_shaders=False,
):
    """
    Assigns a checkered shader to an object.

    Args:
        object_to_shade (pymel.core.PyNode): The object to which the checker will be assigned to.

        material_name (str): The mutable part of the material name.

        material_type (str): The material type.

        clear_shaders(bool): Clear the script generated shaders first.

    Returns:
        pymel.core.PyNode(checker_mat): The checkered material.

    """
    if clear_shaders:
        clear()

    material_name_adapted = "{0}_{1}".format(
        str(object_to_shade.shortName()), material_name
    )

    checker_mat, checker_shader = assign_checker_shader(
        object_to_shade,
        material_name=material_name_adapted,
        material_type=material_type,
    )

    return checker_mat


def create_checker(
    object_to_shade,
    material_name="checker",
    repeat_u=None,
    repeat_v=None,
    tagging="checker",
):
    """
    Assigns a checkered material to the object to shade.

    Args:
        object_to_shade (pymel.core.PyNode): Object to be shaded.

        material_name (str): Name of the material.

        material_type (str): Type of material assigned.

        repeat_u (int): Amount of repeats of the texture in U.

        repeat_v (int): Amount of repeats of the texture in V.

        tagging (str): String to tag nodes with.

    Returns:
        Tuple(mult_outline_node.output, refl_checker_node.outColor): tuple(pymel.core.Attribute(),
                                                                           pymel.core.Attribute()
                                                                           )
    """

    if not (repeat_u and repeat_v):
        repeat_u = get_object_size(object_to_shade) * 0.01
        repeat_v = get_object_size(object_to_shade) * 0.01

    nodes_generated = list()
    checker_node = check_for_existece_and_create(
        node_name="{0}_CHKR".format(material_name),
        node_type="checker",
        tagging=tagging,
    )
    nodes_generated.append(checker_node)

    uv_sample_node = check_for_existece_and_create(
        node_name="{0}_P2DT".format(material_name),
        node_type="place2dTexture",
        tagging=tagging,
    )

    uv_sample_node.outUV.connect(checker_node.uvCoord, f=True)
    uv_sample_node.repeatU.set(
        repeat_u,
    )
    uv_sample_node.repeatV.set(
        repeat_v,
    )

    nodes_generated.append(uv_sample_node)

    # node creation
    integer_node = check_for_existece_and_create(
        node_name="{0}_switcher_fCst".format(material_name),
        node_type="floatConstant",
        tagging=tagging,
    )

    nodes_generated.append(integer_node)

    repeat_node = check_for_existece_and_create(
        node_name="{0}_uvRepeat_fCst".format(material_name),
        node_type="floatConstant",
        tagging=tagging,
    )

    repeat_node.inFloat.set(repeat_u)
    nodes_generated.append(repeat_node)

    # create dark mode info nodes
    light_dark_switch_one_node = check_for_existece_and_create(
        node_name="{0}_darkMode_cCst".format(material_name),
        node_type="blendColors",
        tagging=tagging,
    )

    nodes_generated.append(light_dark_switch_one_node)
    light_dark_switch_one_node.color1.set(
        _COLOR_VARIANTS["dark_mode"]["checkerboard_color1"]
    )
    light_dark_switch_one_node.color2.set(
        _COLOR_VARIANTS["light_mode"]["checkerboard_color1"]
    )

    # create light mode info nodes
    light_dark_switch_two_node = check_for_existece_and_create(
        node_name="{0}_lightMode_cCst".format(material_name),
        node_type="blendColors",
        tagging=tagging,
    )

    nodes_generated.append(light_dark_switch_two_node)

    light_dark_switch_two_node.color1.set(
        _COLOR_VARIANTS["dark_mode"]["checkerboard_color2"]
    )
    light_dark_switch_two_node.color2.set(
        _COLOR_VARIANTS["light_mode"]["checkerboard_color2"]
    )

    # checker nodes
    color_checker_node = check_for_existece_and_create(
        node_name="{0}_color_ckr".format(material_name),
        node_type="checker",
        tagging=tagging,
    )

    nodes_generated.append(color_checker_node)

    refl_checker_node = check_for_existece_and_create(
        node_name="{0}_refl_ckr".format(material_name),
        node_type="checker",
        tagging=tagging,
    )

    refl_checker_node.color1.set(
        (0.05, 0.05, 0.05),
    )
    refl_checker_node.color2.set(
        (0.15, 0.15, 0.15),
    )

    nodes_generated.append(refl_checker_node)

    # uv sampling
    uv_sample_node = check_for_existece_and_create(
        node_name="{0}_p2d".format(material_name),
        node_type="place2dTexture",
        tagging=tagging,
    )

    nodes_generated.append(uv_sample_node)

    uv_mult_ramp_one_u_node = check_for_existece_and_create(
        node_name="{0}_outlineU_mul".format(material_name),
        node_type="multDoubleLinear",
        tagging=tagging,
    )

    uv_mult_ramp_one_u_node.input2.set(
        2,
    )
    nodes_generated.append(uv_mult_ramp_one_u_node)

    uv_mult_ramp_two_u_node = check_for_existece_and_create(
        node_name="{0}_inlineU_mul".format(material_name),
        node_type="multDoubleLinear",
        tagging=tagging,
    )

    uv_mult_ramp_two_u_node.input2.set(
        8,
    )
    nodes_generated.append(uv_mult_ramp_two_u_node)

    uv_mult_ramp_one_v_node = check_for_existece_and_create(
        node_name="{0}_outlineV_mul".format(material_name),
        node_type="multDoubleLinear",
        tagging=tagging,
    )

    uv_mult_ramp_one_v_node.input2.set(
        2,
    )
    nodes_generated.append(uv_mult_ramp_one_v_node)

    uv_mult_ramp_two_v_node = check_for_existece_and_create(
        node_name="{0}_inlineV_mul".format(material_name),
        node_type="multDoubleLinear",
        tagging=tagging,
    )

    uv_mult_ramp_two_v_node.input2.set(
        8,
    )
    nodes_generated.append(uv_mult_ramp_two_v_node)

    # ramp nodes
    outline_ramp_node = check_for_existece_and_create(
        node_name="{0}_outline_rmp".format(material_name),
        node_type="ramp",
        tagging=tagging,
    )

    outline_ramp_node.attr("type").set(
        5,
    )
    outline_ramp_node.interpolation.set(
        0,
    )
    outline_ramp_node.colorEntryList[0].color.set(
        (1, 1, 1),
    )
    outline_ramp_node.colorEntryList[1].position.set(
        0.95,
    )
    outline_ramp_node.colorEntryList[1].color.set(
        (0.88, 0.88, 0.88),
    )

    nodes_generated.append(outline_ramp_node)

    uv_sample_node.outUvFilterSize.connect(checker_node.uvFilterSize)

    inline_ramp_node = check_for_existece_and_create(
        node_name="{0}_inline_rmp".format(material_name),
        node_type="ramp",
        tagging=tagging,
    )

    inline_ramp_node.attr("type").set(
        5,
    )
    inline_ramp_node.interpolation.set(
        0,
    )
    inline_ramp_node.colorEntryList[0].color.set(
        (0, 0, 0),
    )
    inline_ramp_node.colorEntryList[1].position.set(
        0.97,
    )
    inline_ramp_node.colorEntryList[1].color.set(
        (0.25, 0.25, 0.25),
    )

    nodes_generated.append(inline_ramp_node)

    # layering nodes
    mult_outline_node = check_for_existece_and_create(
        node_name="{0}_mul".format(material_name),
        node_type="multiplyDivide",
        tagging=tagging,
    )

    mult_outline_node.operation.set(
        1,
    )
    nodes_generated.append(mult_outline_node)

    add_inline_node = check_for_existece_and_create(
        node_name="{0}_add".format(material_name),
        node_type="plusMinusAverage",
        tagging=tagging,
    )

    add_inline_node.operation.set(
        1,
    )
    nodes_generated.append(add_inline_node)

    # connections
    integer_node.outFloat.connect(light_dark_switch_one_node.blender)
    integer_node.outFloat.connect(light_dark_switch_two_node.blender)

    repeat_node.outFloat.connect(uv_sample_node.repeatU)
    repeat_node.outFloat.connect(uv_sample_node.repeatV)

    uv_sample_node.outU.connect(uv_mult_ramp_one_u_node.input1)
    uv_sample_node.outV.connect(uv_mult_ramp_one_v_node.input1)

    uv_sample_node.outU.connect(uv_mult_ramp_two_u_node.input1)
    uv_sample_node.outV.connect(uv_mult_ramp_two_v_node.input1)

    # connect uv sampling to checker nodes
    uv_sample_node.outUV.connect(color_checker_node.uvCoord)
    uv_sample_node.outUvFilterSize.connect(color_checker_node.uvFilterSize)

    uv_sample_node.outUV.connect(refl_checker_node.uvCoord)
    uv_sample_node.outUvFilterSize.connect(refl_checker_node.uvFilterSize)

    # connect density multiplications to ramps
    uv_mult_ramp_one_u_node.output.connect(outline_ramp_node.uCoord)
    uv_mult_ramp_one_v_node.output.connect(outline_ramp_node.vCoord)
    uv_sample_node.outUvFilterSize.connect(outline_ramp_node.uvFilterSize)

    uv_mult_ramp_two_u_node.output.connect(inline_ramp_node.uCoord)
    uv_mult_ramp_two_v_node.output.connect(inline_ramp_node.vCoord)
    uv_sample_node.outUvFilterSize.connect(inline_ramp_node.uvFilterSize)

    # combine colors
    light_dark_switch_one_node.output.connect(color_checker_node.color1)
    light_dark_switch_two_node.output.connect(color_checker_node.color2)

    color_checker_node.outColor.connect(add_inline_node.input3D[0])

    inline_ramp_node.outColor.connect(add_inline_node.input3D[1])

    add_inline_node.output3D.connect(mult_outline_node.input1)

    outline_ramp_node.outColor.connect(mult_outline_node.input2)

    [
        node.addAttr("scriptGenerated", dt="string")
        for node in nodes_generated
        if not node.hasAttr("scriptGenerated")
    ]

    [
        node.isHistoricallyInteresting.set(False, lock=False)
        for node in nodes_generated
    ]

    return mult_outline_node.output, refl_checker_node.outColor


def assign_checker_shader(
    object_to_shade,
    material_name="checker",
    material_type="phongE",
    repeat_u=None,
    repeat_v=None,
):
    """
    Creates the checker-Shader and the corresponding Checker Texture network.

    Args:
        object_to_shade (pymel.core.PyNode): Object to be shaded.

        material_name (str): Name of the material.

        material_type (str): Type of material assigned.

        repeat_u (None/int): The number of repetition of the texture in U.

        repeat_v (None/int): The number of repetition of the texture in V.

    Returns:
        Tuple (checker_object, checker_mat): Gives back the Shader and the Material as PyMel Objects.
                                             tuple(pymel.core.PyNode(shader),
                                                   pymel.core.PyNode(material)
                                                   )

    """

    # create the material/shader for the checker material
    checker_object, checker_mat = assign_shader(
        object_to_shade=object_to_shade,
        material_name=material_name,
        material_type=material_type,
        material_color=(0.5, 0.5, 0.5),
    )

    # create the checker shading network
    color_tex, refl_tex = create_checker(
        object_to_shade,
        material_name=material_name,
        material_type=material_type,
        repeat_u=repeat_u,
        repeat_v=repeat_v,
    )

    # connect color checker
    color_tex.connect(
        checker_object.attr(SHADER_PROPERTIES[material_type]["color"][0])
    )

    # connect reflection checker
    refl_tex.connect(
        checker_object.attr(SHADER_PROPERTIES[material_type]["reflection"][0])
    )

    checker_object.highlightSize.set(0.2, lock=True)
    checker_object.roughness.set(0.3, lock=True)
    checker_object.reflectivity.set(0, lock=True)

    return checker_object, checker_mat


def create_ramp(material_name="ramp", tagging="ramp"):
    """
    Assigns a checkered material to the object to shade.

    Args:
        material_name (str): Name of the material.

        tagging (str): String to tag nodes with.

    Returns:
        Tuple(mult_outline_node.output, refl_checker_node.outColor): tuple(pymel.core.Attribute(),
                                                                           pymel.core.Attribute()
                                                                           )
    """

    nodes_generated = list()
    checker_node = check_for_existece_and_create(
        node_name="{0}_RAMP".format(material_name),
        node_type="ramp",
        tagging=tagging,
    )
    nodes_generated.append(checker_node)

    uv_sample_node = check_for_existece_and_create(
        node_name="{0}_P2DT".format(material_name),
        node_type="place2dTexture",
        tagging=tagging,
    )

    uv_sample_node.outUV.connect(checker_node.uvCoord, f=True)
    uv_sample_node.repeatU.set(
        1,
    )
    uv_sample_node.repeatV.set(
        1,
    )

    nodes_generated.append(uv_sample_node)

    checker_node.attr("type").set(
        0,
    )
    checker_node.interpolation.set(
        4,
    )
    checker_node.colorEntryList[0].color.set(
        (1, 1, 1),
    )

    checker_node.colorEntryList[0].position.set(
        0.005,
    )

    checker_node.colorEntryList[1].position.set(
        0.25,
    )
    checker_node.colorEntryList[1].color.set(
        (0.0, 0.0, 0.0),
    )

    [
        node.addAttr("scriptGenerated", dt="string")
        for node in nodes_generated
        if not node.hasAttr("scriptGenerated")
    ]

    [
        node.isHistoricallyInteresting.set(False, lock=False)
        for node in nodes_generated
    ]

    return checker_node.outAlpha, checker_node.outColor


def assign_ramp_shader(
    object_to_shade,
    material_name="ramp",
    material_type="surfaceShader",
):
    """
    Creates the checker-Shader and the corresponding Checker Texture network.

    Args:
        object_to_shade (pymel.core.PyNode): Object to be shaded.

        material_name (str): Name of the material.

        material_type (str): Type of material assigned.

    Returns:
        Tuple (checker_object, checker_mat): Gives back the Shader and the Material as PyMel Objects.
                                             tuple(pymel.core.PyNode(shader),
                                                   pymel.core.PyNode(material)
                                                   )

    """

    # create the material/shader for the checker material
    checker_object, checker_mat = assign_shader(
        object_to_shade=object_to_shade,
        material_name=material_name,
        material_type=material_type,
        material_color=(0.5, 0.5, 0.5),
    )

    # create the checker shading network
    color_tex, refl_tex = create_ramp(
        object_to_shade,
        material_name=material_name,
        material_type=material_type,
        repeat_u=1,
        repeat_v=1,
    )

    # connect color checker
    refl_tex.connect(
        checker_object.attr(SHADER_PROPERTIES[material_type]["transparency"][0])
    )

    return checker_object, checker_mat


def random_color(rounding_factor=3):
    """
    Generates a random tuple (RGB Color) of values from 0-1.

    Args:
        rounding_factor (int): The digit to which it will be rounded upon.

    Returns:
        Tuple:  Tuple of random rounded numbers.
                tuple(random_integer_between_0_and_1,
                      random_integer_between_0_and_1,
                      random_integer_between_0_and_1
                )

    """

    return (
        round(random.random(), rounding_factor),
        round(random.random(), rounding_factor),
        round(random.random(), rounding_factor),
    )


def assign_to_meshes_random(poly_objects=None):
    """
    Assigns shader to list of pmc.PyNodes.

    Args:
        poly_objects(list): The objects to which materials will be applied to

    Returns:
        List(objects_changed): The objects that have been changed.

    """

    operation_objects = poly_objects or sel_to_meshes() or pmc.ls(type="mesh")

    if not operation_objects:
        return

    #   get rid of previous clowns
    clear()

    #   apply material and shader
    objects_changed = list()
    for obj in operation_objects:
        assign_shader(object_to_shade=obj, material_color=random_color())
        objects_changed.append(obj)

    return objects_changed


def clear():
    """
    Removes all module generated shaders, materials and nodes, and replaces them with lambert1.

    Returns:
        List(effected_meshes): List of all meshes that were changed.

    """

    #   get all shaders
    all_shaders = pmc.ls(type="shadingEngine")

    #   sort for script-generated shaders
    generated_shaders = [x for x in all_shaders if x.hasAttr(SHADER_UTILS_TAG)]

    #   check if there are any
    if not generated_shaders:
        return None

    #   get script-generated materials
    generated_materials = [
        pmc.listConnections(x.surfaceShader, d=False, s=True)[0]
        for x in generated_shaders
        if pmc.listConnections(x.surfaceShader, d=False, s=True)
        for x in generated_shaders
    ]

    #   get all meshes and store them for deletion and reassignment
    effected_meshes = list()
    for shd in generated_shaders:
        index_amount = pmc.getAttr(shd.dagSetMembers, multiIndices=True)

        if not index_amount:
            continue

        for i in range(0, len(index_amount)):
            attr_name = "dagSetMembers[{}]".format(str(i))

            connections = pmc.listConnections(
                shd.attr(attr_name), d=False, s=True
            )
            if connections:
                effected_meshes.append(connections[0])

    #   apply lambert1 to meshes
    for nde in effected_meshes:
        try:
            pmc.sets("initialShadingGroup", edit=True, forceElement=nde)

        except:
            pass

    #   delete custom nodes
    pmc.delete(generated_shaders, generated_materials)

    pmc.delete(
        [
            effected_node
            for effected_node in cmds.ls()
            if cmds.attributeQuery(
                SHADER_UTILS_TAG, node=effected_node, exists=True
            )
        ]
    )

    return effected_meshes


def clear_generated_materials():
    """
    Removes all module generated shaders and materials, and replaces them with lambert1.

    Returns:
        List (effected_meshes): List of all meshes that were changed.

    """

    #   get all shaders
    all_shaders = pmc.ls(type="shadingEngine")

    #   sort for script-generated shaders
    generated_shaders = [x for x in all_shaders if x.hasAttr(SHADER_UTILS_TAG)]

    #   check if there are any
    if not generated_shaders:
        return None

    #   get script-generated materials
    generated_materials = [
        pmc.listConnections(x.surfaceShader, d=False, s=True)[0]
        for x in generated_shaders
    ]

    #   get all meshes and store them for deletion and reassignment
    effected_meshes = list()
    for shd in generated_shaders:
        index_amount = pmc.getAttr(shd.dagSetMembers, multiIndices=True)

        if not index_amount:
            continue

        for i in range(0, len(index_amount)):
            attr_name = "dagSetMembers[{}]".format(str(i))

            connections = pmc.listConnections(
                shd.attr(attr_name), d=False, s=True
            )
            if connections:
                effected_meshes.append(connections[0])

    #   apply lambert1 to meshes
    for nde in effected_meshes:
        try:
            pmc.sets("initialShadingGroup", edit=True, forceElement=nde)

        except:
            pass

    #   delete custom nodes
    pmc.delete(generated_shaders, generated_materials)

    pmc.delete(
        [
            effected_node
            for effected_node in cmds.ls()
            if cmds.attributeQuery(
                SHADER_UTILS_TAG, node=effected_node, exists=True
            )
        ]
    )

    return effected_meshes


def non_connected_to_initial_shading_grp():
    """
    Connects all non connected meshes to the initial shading group node

    Returns:
        List:  List of connections if successful. None if not.
    """

    non_connected_meshes = [
        mesh
        for mesh in cmds.ls(type="mesh")
        if not cmds.connectionInfo(
            "{}.instObjGroups[0]".format(mesh), isSource=True
        )
    ]

    if not non_connected_meshes:
        return None

    return [
        cmds.connectAttr(
            "{}.instObjGroups[0]".format(mesh),
            "initialShadingGroup.dagSetMembers[{}]".format(
                str(
                    get_next_free_array_index(
                        "initialShadingGroup.dagSetMembers", 0
                    )
                )
            ),
        )
        for mesh in non_connected_meshes
    ]


def assign_one_udim_shader(
    object_to_shade,
    textures_info,
    material_name="one_udim",
    material_type="phongE",
    repeat_uv=1,
):
    """
    Sets up the attributes and connects a one udim shader.

    Args:
        object_to_shade(pymel.core.PyNode): Object of which the one udim needs to be found.

        material_name(str): Name of the new material.

        material_type(str): Name of the type of material.

    Returns:
        Dict(texture_nodes): {"node_function": ((color_node1,blendcolor_node1,
                                                color_node2,blendcolor_node2, ...),
                                                name),
                                                ...
                              }

    """

    material_name_adapted = "{0}_{1}_{2}Mat".format(
        str(object_to_shade.shortName()),
        material_name,
        AVAILABLE_SHADERS[material_type],
    )

    one_udim_mat, one_udim_shader = assign_shader(
        object_to_shade=object_to_shade,
        material_name=material_name_adapted,
        material_type=material_type,
        material_color=(0.5, 0.5, 0.5),
    )

    created_nodes = list()
    for (
        nice_name,
        short_name,
        texture_tag,
        variation_tag,
        uv_repetition,
        file_paths,
    ) in textures_info:

        texture_nodes = texture_to_material(
            one_udim_mat,
            material_name_adapted,
            material_type,
            nice_name,
            uv_repetition,
            file_paths,
        )
        uv_chooser_nodes = [
            connect_uv_switch(tex_node) for tex_node in texture_nodes[0]
        ]

        # work on uv chooser
        for uv_chooser in uv_chooser_nodes:
            udim_connection = get_one_udim_uv_set(object_to_shade)

            if not udim_connection:
                _LOGGER.warning(
                    "{0} has no valid one-udim uv set".format(
                        str(object_to_shade.shortName())
                    )
                )
                continue

            udim_connection.connect(uv_chooser.uvSets[0], f=True)
        created_nodes.append(texture_nodes)

    return created_nodes


def texture_to_material(
    material_object,
    material_name_adapted,
    material_type,
    nice_name,
    repeat_uvs,
    texture_paths=None,
):

    """
    Creates texture network for material.

    Args:
        material_object (pymel.core.PyNode): The PyMel representation of the material node.

        material_name_adapted (str): The material name modified to match this modules naming convention.

        material_type (str): Name of the type of material.

        nice_name (str): The nice name of the material.

        repeat_uvs (float): The amount of repetitions in the UVs.

        texture_paths (None/list): List filled with paths to the textures.

    Returns:
        Tuple(color_nodes, blend_color_node): tuple(list(color_nodes),
                                                    pymel.core.PyNode(blend_color_node)
                                                    )
    """

    # if variation_tag == VARIATION_TAG:
    end_color_name = "{0}_{1}_VARMIX_txt".format(
        nice_name,
        material_name_adapted,
    )
    color_nodes = list()
    switch_nodes = list()

    if not texture_paths:
        return

    for texture_index, texture_path in enumerate(texture_paths):

        if not texture_path:
            texture_path = ""

        color_node_name = "{0}_{1}_{2}_txt".format(
            nice_name, material_name_adapted, str(texture_index)
        )

        select_name = "{0}_{1}_{2}_cmp".format(
            nice_name, material_name_adapted, str(texture_index)
        )

        uv_texture_name = "{0}_{1}_{2}_p2d".format(
            nice_name, material_name_adapted, str(texture_index)
        )
        bump_node_name = "{0}_{1}_{2}_b2d".format(
            nice_name, material_name_adapted, str(texture_index)
        )

        color_node = check_for_existece_and_create(
            color_node_name, "file", tagging=SHADER_UTILS_TAG
        )

        select_node = check_for_existece_and_create(
            select_name, "math_CompareInt", tagging=SHADER_UTILS_TAG
        )
        if not select_node.input2.isLocked():
            select_node.input2.set(texture_index)
            select_node.input2.lock()
        if not select_node.hasAttr("is_variant_switch"):
            select_node.addAttr("is_variant_switch", at="bool", dv=True, k=True)
        if not select_node.hasAttr(VARIANT_INDEX):
            select_node.addAttr(
                VARIANT_INDEX, at="double", dv=texture_index, k=True
            )
        if not select_node.hasAttr(MAX_INDEX):
            select_node.addAttr(
                MAX_INDEX, at="double", dv=len(texture_paths), k=True
            )

        if len(texture_paths) > 1:
            if not select_node.hasAttr(MULTIPLES_TAG):
                select_node.addAttr(MULTIPLES_TAG, at="bool", dv=True, k=True)
        else:
            if not select_node.hasAttr(SINGLES_TAG):
                select_node.addAttr(SINGLES_TAG, at="bool", dv=True, k=True)

        try:
            color_node.defaultColor.set(0, 0, 0)
            color_node.fileTextureName.set(texture_path, type="string")

        except pmc.MayaAttributeError:
            pass

        uv_sample_node = check_for_existece_and_create(
            uv_texture_name, "place2dTexture", tagging=SHADER_UTILS_TAG
        )

        # asdf
        uv_sample_node.outUV.connect(color_node.uvCoord, force=True)
        uv_sample_node.repeatU.set(repeat_uvs)
        uv_sample_node.repeatV.set(repeat_uvs)
        uv_sample_node.outUvFilterSize.connect(
            color_node.uvFilterSize, force=True
        )

        color_nodes.append(color_node)
        switch_nodes.append(select_node)

    end_node = check_for_existece_and_create(
        end_color_name, "layeredTexture", tagging=SHADER_UTILS_TAG
    )

    [
        color_node.outColor.connect(
            end_node.attr("inputs[{0}].color".format(str(color_plug)))
        )
        for color_plug, color_node in enumerate(color_nodes)
    ]

    [
        switch_node.output.connect(
            end_node.attr("inputs[{0}].isVisible".format(str(switch_plug)))
        )
        for switch_plug, switch_node in enumerate(switch_nodes)
    ]

    blend_color_node = pmc.createNode(
        "blendColors",
        n="{0}_{1}_bld".format(nice_name, material_name_adapted),
    )

    blend_color_node.addAttr(SHADER_UTILS_TAG, at="bool", dv=True)
    blend_color_node.addAttr(TEXTURE_TAG, at="bool", dv=True)
    blend_color_node.addAttr(BLEND_CONNECTION_TAG, at="bool", dv=True)

    blend_color_node.blender.set(0)

    if "displacement" in nice_name:
        blend_color_node.color1.set(1, 1, 1)
        blend_color_node.color2.set(0, 0, 0)

        bump_node = check_for_existece_and_create(
            bump_node_name, "bump2d", tagging=SHADER_UTILS_TAG
        )
        bump_node.bumpInterp.set(0)
        bump_node.bumpDepth.set(0.002)

        color_node.alphaIsLuminance.set(True)
        color_node.outAlpha.connect(bump_node.bumpValue, force=True)

        blend_color_node.outputR.connect(color_node.alphaGain, force=True)
        bump_node.outNormal.connect(
            material_object.attr(
                SHADER_PROPERTIES[material_type][nice_name][0]
            ),
            force=True,
        )

    elif "normal" in nice_name:
        file_nd = end_node.connections(type="file")[0]

        bump_node = check_for_existece_and_create(
            bump_node_name, "bump2d", tagging=SHADER_UTILS_TAG
        )

        bump_node.bumpDepth.set(1)
        bump_node.bumpInterp.set(1)
        file_nd.outAlpha.connect(bump_node.bumpValue, force=True)
        bump_node.outNormal.connect(
            material_object.attr(nice_name),
            force=True,
        )
        print(end_node)
        pmc.delete(end_node)

    else:
        end_node.outColor.connect(blend_color_node.color1)
        blend_color_node.color2.set(0.5, 0.5, 0.5)

        blend_color_node.output.connect(
            material_object.attr(nice_name),
            force=True,
        )

    return color_nodes, blend_color_node


def check_for_existece_and_create(node_name, node_type, tagging=None):
    """
    Creates a Node with a specific name, type and tagging. If the node already exists, it will just return the Node.

    Args:
        node_name (str): Name of the node that will be created.

        node_type (str): Type of the node that will be created.

        tagging (None/str): Tag of the node that will be created

    Returns:
        pymel.core.PyNode (created_node): Pymel representation of the node that was created or already exists.

    """

    if not pmc.objExists(node_name):
        created_node = pmc.createNode(
            node_type,
            n=node_name,
        )

    else:
        created_node = pmc.PyNode(node_name)

    if not tagging:
        return created_node

    if not created_node.hasAttr(tagging):
        created_node.addAttr(tagging, at="bool", dv=True)

    return created_node


def connect_uv_switch(tex_node):
    """
    Creates and connects a uvChooser node to the texture node.

    Args:
        tex_node (pymel.core.PyNode): Texture node that needs connecting to the uvChooser.

    Returns:
        pymel.core.PyNode (uv_chooser_node): The chooser node as a pymel node.

    """

    uv_switch_name = str(tex_node.shortName()).replace("txt", "uvc")

    uv_chooser_node = check_for_existece_and_create(
        uv_switch_name, "uvChooser", tagging=SHADER_UTILS_TAG
    )

    uv_chooser_node.outUv.connect(tex_node.uvCoord, force=True)

    return uv_chooser_node


def get_tex_publish_path():
    """
    Gets the Texture Publish path.

    Returns:
        Path (publish_tex_path): Path to the texture publish folder.

    """

    proj_base = pixo_normpath(
        paths_utils.get_root_path(pmc.sceneName(), root_name="asset")
    )

    publish_tex_path = pixo_normpath(os.path.join(proj_base, r"txt/_publish"))

    return publish_tex_path


def get_tex_file(tex_type):
    """
    Finds the Texture file from the texture publish path.

    Args:
        tex_type (str): Type of texture.

    Returns:
        List(file_paths_per_variant): list(path_to_texture,
                                           path_to_texture,
                                           path_to_texture,...
                                           )

    """

    tex_publish_path = get_tex_publish_path()

    valid_tex_publish_paths = [
        x
        for x in os.scandir(tex_publish_path)
        if tex_type in x.name
        and any(ele in x.name for ele in UDIM_STRINGS)
        and not any(ele in x.name for ele in UDIM_EXCLUSION_STRING)
    ]

    if not valid_tex_publish_paths:
        return

    dir_direct_paths = [
        pixo_normpath(publish_path) for publish_path in valid_tex_publish_paths
    ]
    file_paths_per_variant = list()
    for dir_direct_path in dir_direct_paths:

        latest_publish_path_per_file = get_latest_path(dir_direct_path)

        publish_files = [
            pixo_normpath(x.path)
            for x in os.scandir(latest_publish_path_per_file)
            if x.is_file() and x.name.endswith(".tx") or x.name.endswith(".png")
        ]

        if not publish_files:
            _LOGGER.error("no tx or png files in publish folder")
            return

        if len(publish_files) != 1:
            _LOGGER.error("too many tx or png files in publish folder")
            return

        file_paths_per_variant.append(publish_files[0])
    return file_paths_per_variant


def capture_texture_info(material_type):
    """
    Creates a mapping between the material type, its suspected use, and its texture.

    Args:
        material_type (str): The Name of the material type,
                             Available types can be found in the SHADER_PROPERTIES dict.

    Returns:
        List (info_and_paths_combined): list(tuple(*info_and_path_pruned[0],
                                             VARIATION_TAG,
                                             UV_REPETITION,
                                             info_and_path_pruned[1]
                                             ), ...
                                             )

    """

    texture_properties_by_type = [
        SHADER_PROPERTIES[material_type][tex_name]
        for tex_name in SHADER_PROPERTIES[material_type].keys()
        if SHADER_PROPERTIES[material_type][tex_name][0]
    ]

    available_texture_files = [
        get_tex_file(tex_name[1]) for tex_name in texture_properties_by_type
    ]

    info_and_paths = list(
        zip(texture_properties_by_type, available_texture_files)
    )

    # prune info and paths if there are no paths
    info_and_paths_pruned = [
        info_and_path for info_and_path in info_and_paths if info_and_path[1]
    ]

    # get the paths and infos
    info_and_paths_combined = list()
    for info_and_path_pruned in info_and_paths_pruned:
        (
            type_of_attr,
            short_name_of_attr,
            character_of_tex,
        ) = info_and_path_pruned[0]

        if len(info_and_path_pruned[1]) > 1:
            info_and_path_combined = (
                type_of_attr,
                short_name_of_attr,
                character_of_tex,
                VARIATION_TAG,
                UV_REPETITION,
                info_and_path_pruned[1],
            )

            info_and_paths_combined.append(info_and_path_combined)

        else:
            info_and_path_combined = (
                type_of_attr,
                short_name_of_attr,
                character_of_tex,
                VARIATION_TAG,
                UV_REPETITION,
                info_and_path_pruned[1],
            )

            info_and_paths_combined.append(info_and_path_combined)

    return info_and_paths_combined


def apply_udim_shader_to_obj(object_to_shade=None, material_type="phongE"):
    """
    Applies a one udim shader to object.

    Args:
        object_to_shade (pymel.core.PyNode): Object of which the one udim needs to be generated.

        material_type (str): The Name of the material type.
                             Available types can be found in the SHADER_PROPERTIES dict.

    Returns:
        pymel.core.PyNode (object_to_shade): Object of which the one udim needs to be generated.

    """

    if not object_to_shade:
        objects_to_shade = pmc.selected()

        if not objects_to_shade:
            return

        object_to_shade = objects_to_shade[0]

    if not get_one_udim_uv_set(object_to_shade):
        return

    info_and_paths_combined = capture_texture_info(material_type)

    if not info_and_paths_combined:
        _LOGGER.error("after sorting there were no files left")
        return

    return_dict = assign_one_udim_shader(
        object_to_shade, info_and_paths_combined
    )

    if not return_dict:
        _LOGGER.error("could not assign the one udim shader")
        return

    pmc.polyUVSet(
        get_deform_shape(object_to_shade),
        currentUVSet=True,
        uvSet=get_one_udim_uv_set(object_to_shade).get(),
    )

    return object_to_shade


def apply_udim_shader_to_list(
    input_items=None, transparent_objects=(), vis_ctrl=None
):
    """
    Applies the udim shaders to a list of objects, with option to make objects transparent also.

    Args:
        input_items (list): List of pymel.core.PyNodes to which the udim shaders will be applied to.
        transparent_objects (list/tuple): Objects that will get a transparent Shader instead.

    Returns:
        Bool: True if ran through.

    """

    # find objects to operate on
    geo_list = input_items or pmc.selected()

    if not geo_list:
        return False

    # udim shader to input list
    [
        apply_udim_shader_to_obj(object_to_shade=obj_)
        for obj_ in geo_list
        if str(obj_.shortName()) not in transparent_objects
    ]

    # transparent shader to transparent objects list
    [
        assign_shader(
            object_to_shade=obj_,
            material_name="{0}_{1}_{2}Mat".format(
                str(obj_.shortName()), "one_udim", AVAILABLE_SHADERS["blinn"]
            ),
            material_type="blinn",
            material_color=(0, 0, 0),
            material_transp=(1, 1, 1),
            material_refl=(0.6, 0.6, 0.6),
        )
        for obj_ in geo_list
        if str(obj_.shortName()) in transparent_objects
    ]

    connect_nodes_to_host(
        vis_ctrl=vis_ctrl,
    )

    return True


@disabled_sg_breakdown_refresh()
def apply_udim_shader_from_asset_assembly(transparent_objects=None):
    """
    Gets the asset assembly from the rig asset assembly, and applies the one-udim to all of its items.

    Args:

        transparent_objects (list/tuple): Objects that will get a transparent Shader instead.

    Returns:
        Bool: True if ran through.

    """

    clear()

    assembly_dict_ = pmc.PyNode(
        PXO_ASSET_ASSEMBLY_NODE_NAME
    ).get_assembly_data()

    assets_data = _decompose_assembly_dict(
        assembly_dict_, ("_render_", "_proxy_")
    )

    for asset in assets_data:

        if transparent_objects is None:
            transparent_objects = asset[1]
        apply_udim_shader_to_list(
            input_items=list(set(asset[0])),
            transparent_objects=transparent_objects,
        )
    return True


def _decompose_assembly_dict(
    assembly_data,
    component_resolutions=("_render_", "_proxy_"),
    component_types=(
        "muscles",
        "skeleton",
        "Muscles",
        "Skeleton",
        "Proxy",
        "bones",
        "sliced",
    ),
    transparent_geos=(
        "Eyefluid",
        "Cornea",
        "syraxCornea",
        "syraxEyefluid",
        "syraxEyefluidLower",
    ),
):
    """
    Maybe the most unstable function in this whole module, made to get data out of the rig asset assembly dict.

    Args:
        assembly_data (dict): Assembly data dict gained from the rig asset assembly node.

        component_resolutions (tuple): Filled with strings which we want to find in the names of the components:
                                       Default is ("_high_", "_low_").

        component_types (tuple): Filled with strings which we want to find in the names of the components.
                                 Default is ("muscles", "skeleton", "Proxy").

        transparent_geos (tuple): Filled with strings which we want to find in the names of the components.
                                  Default is ("Eyefluid", "Cornea").

    Returns:
        List (assets_data): List of tuples containing valid nodes of asset and its publishing path.

    """

    assets_data = list()
    for asset_in_scene in assembly_data:
        component_dict = asset_in_scene["components"]

        valid_geos = list()
        for comp_key, comp_val in component_dict.items():
            if any(
                ele in comp_key for ele in component_resolutions
            ) and not any(ele in comp_key for ele in component_types):
                valid_geos.extend(*comp_val.values())

        publish_path = pixo_normpath(
            os.path.dirname(
                os.path.dirname(
                    os.path.dirname(
                        pixo_normpath(asset_in_scene["publish_path"])
                    )
                )
            )
        )
        transparent_geo_out = [
            geo
            for geo in valid_geos
            if any(ele in geo.shortName() for ele in transparent_geos)
        ]
        assets_data.append((valid_geos, transparent_geo_out, publish_path))

    return assets_data


def get_one_udim_uv_set(object_to_shade):
    """
    Get the UV-Set that corresponds with items in _UDIM_STRINGS.

    Args:
        object_to_shade (pymel.core.PyNode): Object of which the one udim needs to be found.

    Returns:
        pymel.core.Attribute (uvSetName): Attribute of the uvSet Name.

    """

    shading_shape = get_deform_shape(object_to_shade)

    for uv_sets in shading_shape.uvSet:
        if uv_sets.uvSetName.get() in UDIM_STRINGS:
            return uv_sets.uvSetName

    return


def connect_nodes_to_host(
    vis_ctrl=None,
):
    """
    Connects blend nodes that are matching the conditions to the vis_ctrl.

    Args:
        vis_ctrl (pymel.core.PyNode): The node to which the shader needs connected.

    Returns:
        pymel.core.PyNode (vis_ctrl): The node to which the shader needs connected.

    """

    blend_nodes = [
        x
        for x in pmc.ls(type="blendColors")
        if pmc.hasAttr(x, BLEND_CONNECTION_TAG, checkShape=False)
    ]

    compare_nodes = [
        x
        for x in pmc.ls(type="math_CompareInt")
        if pmc.hasAttr(x, MULTIPLES_TAG, checkShape=False)
    ]

    bump_2d_nodes = pmc.ls(type="bump2d")

    if not vis_ctrl:
        _LOGGER.warning("vis control not specified")

        check_for_vis_ctrls = [
            vis_ctrl_token
            for vis_ctrl_token in VIS_CTRL_TOKEN
            if pmc.objExists(vis_ctrl_token)
        ]

        if not check_for_vis_ctrls:
            _LOGGER.warning("also no vis control found that matches standard")
            return

        _LOGGER.info(
            "since nothing was specified using {0}".format(
                check_for_vis_ctrls[-1]
            )
        )
        vis_ctrl = pmc.PyNode(check_for_vis_ctrls[-1])
    if blend_nodes:
        for blend_node in blend_nodes:

            tex_tag = blend_node.hasAttr(TEXTURE_TAG)
            disp_tag = blend_node.hasAttr(DISPLACEMENT_TAG)

            if not any((tex_tag, disp_tag)):
                _LOGGER.warning("missing tag to find right connection")
                continue

            if tex_tag:
                vis_ctrl.attr("texture_display").connect(
                    blend_node.blender, force=True
                )
                continue
            elif disp_tag:
                vis_ctrl.attr("bump_map_display").connect(
                    blend_node.blender, force=True
                )
    else:
        _LOGGER.warning("no valid blendColors nodes have been found")

    if bump_2d_nodes:
        for bump_nd in bump_2d_nodes:
            vis_ctrl.attr("bump_map_display").connect(
                bump_nd.bumpDepth, force=True
            )

    if any(compare_nodes) and vis_ctrl.hasAttr("texture_variations"):

        index_num_of_vars = max(
            [
                compare_node.attr(VARIANT_INDEX).get()
                for compare_node in compare_nodes
            ]
        )
        max_num_of_vars = (
            max(
                [
                    compare_node.attr(MAX_INDEX).get()
                    for compare_node in compare_nodes
                ]
            )
            - 1
        )

        vis_ctrl.attr("texture_variations").set(channelBox=True)
        enum_names_adapted = [
            "tex_{0}".format(str(ind + 1))
            for ind in range(int(index_num_of_vars))
        ]
        enum_str = ":".join(enum_names_adapted)
        vis_ctrl.attr("texture_variations").setEnums(enum_str)

        for compare_node in compare_nodes:
            ind_max_num_of_vars = compare_node.attr(MAX_INDEX).get() - 1
            ind_index_num_of_vars = compare_node.attr(VARIANT_INDEX).get()

            if ind_index_num_of_vars < ind_max_num_of_vars < max_num_of_vars:
                compare_node.operation.set(5)

            vis_ctrl.attr("texture_variations").connect(
                compare_node.input1, force=True
            )
    else:
        _LOGGER.warning(
            "No valid compare nodes found or vis control misses teh texture variations attribute."
        )
