# Author:     Christof Puehringer / Rigging TD

"""
Functions for creating a Quadrupedal Scapula setup.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import built-in modules
from builtins import str
import logging
from pprint import pprint
from typing import Optional

# Import third-party modules
from future import standard_library
import numpy as np
import pymel.core as pmc

# Import local modules
from pxo_rigging_kit import constants
from pxo_rigging_kit.maya_utils import dag_utils
from pxo_rigging_kit.maya_utils.EWAW_rs import node
from pxo_rigging_kit.maya_utils.rigging import rig_utils

#######################################################
# GLOBALS
#######################################################
standard_library.install_aliases()

logging.basicConfig(level=logging)
_LOGGER = logging.getLogger(__name__ + ".py")

##########################################################
# FUNCTIONS
##########################################################


def create_basic_scap_joints(start_dag, end_dag, tag: Optional[str] = None):
    """
    Creates a simple joint chain which is ranging from start dag to end dag.

    Args:
        start_dag(pymel.core.PyNode): Dag Transform node.
        end_dag(pymel.core.PyNode): Dag Transform node.

    Returns:
        Tuple: (start_scap_jnt, end_scap_jnt)
    """

    component_jnt_name = "{side}_bnd_{component}".format(
        component=str(end_dag.shortName()).split("_")[0],
        side=str(end_dag.shortName()).split("_")[1],
    )

    start_dag_pos = start_dag.getTranslation(space="world")

    start_scap_jnt = node.createNode(
        "joint", n="{component_name}_jnt".format(component_name=component_jnt_name), as_type="pymel", tag=tag
    )
    start_scap_jnt.setTranslation(start_dag_pos, space="world")
    start_scap_jnt.overrideEnabled.set(True, lock=True)
    start_scap_jnt.overrideColor.set(22, lock=True)

    end_dag_pos = end_dag.getTranslation(space="world")

    end_scap_jnt = node.createNode(
        "joint", n="{component_name}Tip_jnt".format(component_name=component_jnt_name), as_type="pymel", tag=tag
    )
    end_scap_jnt.setTranslation(end_dag_pos, space="world")
    end_scap_jnt.overrideEnabled.set(True, lock=True)
    end_scap_jnt.overrideColor.set(22, lock=True)

    pmc.parent(end_scap_jnt, start_scap_jnt)

    pmc.joint(start_scap_jnt, edit=True, orientJoint="xyz", secondaryAxisOrient="yup")
    end_scap_jnt.jointOrient.set((0, 0, 0))
    end_scap_jnt.rotate.set((0, 0, 0))

    deformer_set_node = pmc.PyNode(constants.PXO_DEFORMERS_SET_NAME)
    pmc.sets(deformer_set_node, addElement=[start_scap_jnt, end_scap_jnt])
    joint_grp_nde = pmc.PyNode(constants.RIG_JOINT_ROOT_NAME)

    pmc.parent(start_scap_jnt, joint_grp_nde)

    return start_scap_jnt, end_scap_jnt


def create_basic_scap_aim(start_dag, end_dag, start_jnt):
    """
    Creates a basic scapula aim from the end dag to the start_jnt, also 'parent_constraints' the position to start_dag.

    Args:
        start_dag(pymel.core.PyNode): Transform Node of the position to start from.
        end_dag(pymel.core.PyNode): Transform Node of the aim location.
        start_jnt(pymel.core.PyNode): Transform Node of the first joint in aimed chain.

    Returns:
        float: Blend target weight.
    """

    # find orientation
    (
        start_translate_world_x,
        start_translate_world_y,
        start_translate_world_z,
    ) = start_dag.getTranslation(space="world")

    x_pos_normalized = np.sign(start_translate_world_x)
    offset_amount = x_pos_normalized * 5.0

    # create nodes needed
    offset_mtx = pmc.createNode("math_MultiplyMatrix")
    aim_mtx = pmc.createNode("aimMatrix")
    blend_mtx = pmc.createNode("blendMatrix")

    fixed_aim_offset_mtx = pmc.createNode("math_MultiplyMatrix")
    fixed_position = pmc.createNode("composeMatrix")

    # create upvector
    offset_mtx.input1.set(
        [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, offset_amount, 1], lock=True
    )

    start_dag.worldMatrix.connect(offset_mtx.input2)

    # create fixed offset for blending aim to no aim
    start_dag_pos = start_dag.getTranslation(space="world")
    end_dag_pos = end_dag.getTranslation(space="world")
    positional_offset = end_dag_pos - start_dag_pos
    fixed_position.inputTranslate.set(positional_offset)

    fixed_position.outputMatrix.connect(fixed_aim_offset_mtx.input1)
    start_dag.worldMatrix.connect(fixed_aim_offset_mtx.input2)

    # blend aim positions
    fixed_aim_offset_mtx.output.connect(blend_mtx.inputMatrix)
    end_dag.worldMatrix.connect(blend_mtx.target[0].targetMatrix)

    # connect to aim
    start_dag.worldMatrix.connect(aim_mtx.inputMatrix)
    end_dag.worldMatrix.connect(aim_mtx.primaryTargetMatrix)
    offset_mtx.output.connect(aim_mtx.secondaryTargetMatrix)

    aim_mtx.secondaryMode.set(1)
    aim_mtx.secondaryInputAxisX.set(0, l=True)
    aim_mtx.secondaryInputAxisY.set(0, l=True)
    aim_mtx.secondaryInputAxisZ.set(1, l=True)

    aim_mtx.outputMatrix.connect(start_jnt.offsetParentMatrix)
    start_jnt.rotate.set((0, 0, 0))
    start_jnt.jointOrient.set((0, 0, 0))
    start_jnt.translate.set((0, 0, 0))

    return blend_mtx.target[0].weight


def create_advanced_scap_lock(
    system_parent, ik_cns_dag, system_root, system_tip, multiplier_attr, additive_attr, length
):
    """
    Creates a node structure that allows the leg to follow the system tip.

    Args:
        system_root(pymel.core.PyNode): Root dag of the component.
        system_tip(pymel.core.PyNode): Tip dag of the component. This has to be the ik control.
        multiplier_attr(pymel.core.Attribute): Multiplying value coming from the Host control.
        additive_attr(pymel.core.Attribute): Additive value coming from the Host control.
        length(float): List of joints in the component.

    Returns:
        Bool: True if operation ran through.
    """

    system_root_name = "{side}_{component}".format(
            component=str(system_root.shortName()).split("_")[1],
            side=str(system_root.shortName()).split("_")[0],
    ) or "C_MISSING"

    # this node is wrong
    offset_mtx = pmc.createNode("math_MultiplyMatrix", n="{0}_offset_mmx".format(system_root_name))
    parent_offset_mtx = pmc.createNode("math_MultiplyMatrix", n="{0}_parentOffset_mmx".format(system_root_name))
    move_in_space_mtx = pmc.createNode("math_MultiplyMatrix", n="{0}_space_mmx".format(system_root_name))

    pick_translate_mtx = pmc.createNode("pickMatrix", n="{0}_pmx".format(system_root_name))

    blend_mtx = pmc.createNode("blendMatrix", n="{0}_bmx".format(system_root_name))

    # create switch
    mult_nde = pmc.createNode("math_Multiply", n="{0}_mlt".format(system_root_name))

    # create manual offset
    clamp_nde = pmc.createNode("math_Clamp", n="{0}_clp".format(system_root_name))
    add_nde = pmc.createNode("math_Add", n="{0}_add".format(system_root_name))

    input_min_attr, input_max_attr, output_attr = rig_utils.create_distance_lerp(
        system_parent, system_tip
    )

    pick_translate_mtx.useScale.set(False, lock=True)
    pick_translate_mtx.useRotate.set(False, lock=True)
    pick_translate_mtx.useShear.set(False, lock=True)

    system_tip.worldMatrix.connect(move_in_space_mtx.input1)
    ik_cns_dag.worldInverseMatrix.connect(move_in_space_mtx.input2)
    move_in_space_mtx.output.connect(pick_translate_mtx.inputMatrix)

    pick_translate_mtx.outputMatrix.connect(offset_mtx.input1)
    system_parent.worldMatrix.connect(offset_mtx.input2)

    system_parent.worldMatrix.connect(blend_mtx.inputMatrix)
    offset_mtx.output.connect(blend_mtx.target[0].targetMatrix)
    blend_mtx.target[0].useShear.set(False, lock=True)
    blend_mtx.target[0].useRotate.set(False, lock=True)
    blend_mtx.target[0].useScale.set(False, lock=True)

    input_min_attr.set(length)
    input_max_attr.set(lock=False)
    input_max_attr.set(0)
    input_max_attr.set(lock=True)

    multiplier_attr.connect(mult_nde.input2)
    output_attr.connect(mult_nde.input1)

    mult_nde.output.connect(add_nde.input1)
    additive_attr.connect(add_nde.input2)

    add_nde.output.connect(clamp_nde.input)

    clamp_nde.output.connect(blend_mtx.target[0].weight)

    blend_mtx.outputMatrix.connect(system_root.offsetParentMatrix, f=True)


    return True


def create_scap_stretch(control_attribute, transform):
    joint_base_length = transform.tx.get()

    addition_node = pmc.createNode("math_Add")
    addition_node.input1.set(joint_base_length)
    control_attribute.connect(addition_node.input2)
    addition_node.output.connect(transform.tx)


def create_scap_interp(start_jnt, tip_jnt, interp_node, end_dag, tag: Optional[str] = None):

    component_jnt_name = "{side}_bnd_{component}".format(
        component=str(start_jnt.shortName()).split("_")[2],
        side=str(start_jnt.shortName()).split("_")[0],
    )

    scap_length = rig_utils.get_distance(start_jnt, tip_jnt)
    upperleg_length = rig_utils.get_distance(start_jnt, interp_node)

    upperleg_relation = upperleg_length/(scap_length+upperleg_length)

    offset_mtx = node.createNode("math_MultiplyMatrix", n="{0}Pos_mmx".format(component_jnt_name), as_type="pymel", tag=tag)
    offset_mtx.input1.set([1.0, 0.0, 0.0, 0.0,
                           0.0, 1.0, 0.0, 0.0,
                           0.0, 0.0, 1.0, 0.0,
                           0.0, 0.0, 140.0, 1.0,
                           ],
                          lock=True
                          )

    positional_mtx = node.createNode("blendMatrix", n="{0}Pos_bmx".format(component_jnt_name), as_type="pymel", tag=tag)
    positional_mtx.target[0].useScale.set(True, lock=True)
    positional_mtx.target[0].useShear.set(False, lock=True)
    positional_mtx.target[0].useRotate.set(False, lock=True)
    positional_mtx.target[0].weight.set(upperleg_relation, lock=True)

    upvec_pos_mtx = node.createNode("blendMatrix", n="{0}UpVecPos_bmx".format(component_jnt_name), as_type="pymel", tag=tag)
    upvec_pos_mtx.target[0].useScale.set(True, lock=True)
    upvec_pos_mtx.target[0].useShear.set(False, lock=True)
    upvec_pos_mtx.target[0].useRotate.set(False, lock=True)
    upvec_pos_mtx.target[0].weight.set(upperleg_relation, lock=True)

    orient_mtx = node.createNode("aimMatrix", n="{0}UpVecPos_amx".format(component_jnt_name), as_type="pymel", tag=tag)
    orient_mtx.secondaryMode.set(1, lock=True)

    adjust_scap_jnt = node.createNode(
            "joint", n="{component_name}Adjust_jnt".format(component_name=component_jnt_name), as_type="pymel", tag=tag
    )

    adjust_scap_jnt.overrideEnabled.set(True, lock=True)
    adjust_scap_jnt.overrideColor.set(22, lock=True)
    deformer_set_node = pmc.PyNode(constants.PXO_DEFORMERS_SET_NAME)

    pmc.sets(deformer_set_node, addElement=adjust_scap_jnt)

    joint_grp_nde = pmc.PyNode(constants.RIG_JOINT_ROOT_NAME)

    pmc.parent(adjust_scap_jnt, joint_grp_nde)

    tip_jnt.worldMatrix.connect(positional_mtx.inputMatrix)
    interp_node.worldMatrix.connect(positional_mtx.target[0].targetMatrix)

    tip_jnt.worldMatrix.connect(offset_mtx.input2)

    offset_mtx.output.connect(upvec_pos_mtx.inputMatrix)

    end_dag.worldMatrix.connect(upvec_pos_mtx.target[0].targetMatrix)

    positional_mtx.outputMatrix.connect(orient_mtx.inputMatrix)
    tip_jnt.worldMatrix.connect(orient_mtx.primaryTargetMatrix)
    upvec_pos_mtx.outputMatrix.connect(orient_mtx.secondaryTargetMatrix)

    orient_mtx.outputMatrix.connect(adjust_scap_jnt.offsetParentMatrix)


def create_scapula_setup(
    host_dag,
    start_dag,
    scap_dag,
    shoulder_dag,
    end_dag,
    ik_cns_dag,
    length,
    middle_div_dag,
    end_div_dag,
        root_name: Optional[str] = None,
        tag: Optional[str] = None,
):
    """
    Creates a quadruped scapula setup comparable to the one found in anims reference lion rig.

    Args:
        host_dag(pymel.core.PyNode): Transform of the host.
        start_dag(pymel.core.PyNode): Transform of the host.
        scap_dag(pymel.core.PyNode): Transform of the host.
        shoulder_dag(pymel.core.PyNode): Transform of the host.
        end_dag(pymel.core.PyNode): Transform of the host.
        ik_cns_dag(pymel.core.PyNode): Transform of the host.
        length(float): the length of the setup.
        middle_div_dag(pymel.core.PyNode):  Transform of the host.
        end_div_dag(pymel.core.PyNode):  Transform of the host.
        root_name(str, None):  name of the sys and attrs.

    Returns:
        Bool: True if done.
    """
    attr_name_root =  root_name or str(scap_dag.shortName()).split("_")[0]

    host_dag.addAttr(
        "{0}Options".format(attr_name_root),
        at="enum",
        enumName=constants.PXO_SEPARATOR_STRING,
        keyable=True,
    )

    host_dag.attr("{0}Options".format(attr_name_root)).set(lock=True)

    host_dag.addAttr(
        "{0}Contribution".format(attr_name_root),
        at="doubleLinear",
        defaultValue=0,
        minValue=0,
        maxValue=1,
        keyable=True,
    )
    host_dag.addAttr(
        "{0}ManualOffset".format(attr_name_root),
        at="doubleLinear",
        defaultValue=0,
        minValue=0,
        maxValue=1,
        keyable=True,
    )

    host_dag.addAttr(
        "{0}LengthOffset".format(attr_name_root),
        at="doubleLinear",
        defaultValue=0,
        minValue=-10,
        maxValue=10,
        keyable=True,
    )

    host_dag.addAttr(
        "{0}NegateOffset".format(attr_name_root),
        at="doubleLinear",
        defaultValue=0,
        minValue=0,
        maxValue=10,
        keyable=True,
    )

    # pmc.parent(ik_cns_dag, shoulder_dag)

    start_jnt, end_jnt = create_basic_scap_joints(start_dag, scap_dag, tag=tag)
    create_basic_scap_aim(shoulder_dag, scap_dag, start_jnt)

    create_scap_stretch(host_dag.attr("{0}LengthOffset".format(attr_name_root)), end_jnt)

    create_advanced_scap_lock(
        start_dag,
            ik_cns_dag,
        shoulder_dag,
        end_dag,
        host_dag.attr("{0}Contribution".format(attr_name_root)),
        host_dag.attr("{0}ManualOffset".format(attr_name_root)),
        length,
    )

    create_scap_interp(start_jnt, end_jnt, middle_div_dag, end_div_dag, tag=tag)

    return True

