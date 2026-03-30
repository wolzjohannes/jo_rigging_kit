# Author:     Johannes Wolz / Lead Rigging TD

"""
Util code to manage the dag graph.
"""

# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import built-in modules
from builtins import range
from builtins import str
import logging
import re

import six
# Import third-party modules
from future import standard_library
# Import Maya specific modules
import pymel.core as pmc

try:
    # Import built-in modules
    from itertools import pairwise

except ImportError:
    # Import local modules
    from pxo_rigging_kit.core import pairwise

# Import local modules
from pxo_rigging_kit.maya_utils import attributes_utils
from pxo_rigging_kit.maya_utils.rigging import rig_utils

standard_library.install_aliases()

##########################################################
# GLOBALS
##########################################################

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)
SUB_SETS_LIST = ["roots", "geo", "non_dag", "dag", "visibility"]

##########################################################
# FUNCTIONS
##########################################################


def delete_hidden_shapes(transform_node, rename=True):
    """
    Delete all hidden shape nodes from given transform.

    Args:
        transform_node(pmc.PyNode()): Transform node.
        rename(str or bool): Rename the orig hidden shape as only shape.
                     Disable these option when you are working with referenced objects.
                     Default is True

    Returns:
        Tuple: (pymel.core.PyNode(transform),
                pymel.core.PyNode(new_shape))
    """
    shape_nd = transform_node.getShape(noIntermediate=True)

    if not shape_nd:
        return transform_node, None

    pmc.delete([shape for shape in transform_node.getShapes() if shape != shape_nd])
    shape_nd.visibility.set(1)
    shape_nd.lodVisibility.set(1)
    shape_nd.intermediateObject.set(0)
    if rename:
        shape_nd.rename("{}Shape".format(transform_node.name()))
    return transform_node, shape_nd


def show_node(node):
    """
    Make given node visible no matter what.
    """
    node.unlock()
    if node.visibility.isConnected():
        node.visibility.disconnect()
    node.visibility.unlock()
    node.visibility.set(1)


def create_buffer_groups(nodes, name_suffix="buffer_grp", use_match_transform=True):
    """
    Create a buffer group for given nodes.

    Args:
        nodes(list|PyNode|str): The objects for which buffer creation shall be executed.
        name_suffix(str): Suffix of the buffer nodes.
        use_match_transform(bool): Uses the match transform command to match the nodes WS pos.
                                   If False we use the xForm command to match the nodes WS pos.

    Return:
        list: New buffer groups.
    """
    # minimal normalization: accept single node or name
    if not isinstance(nodes, (list, tuple)):
        nodes = [nodes]
    nodes = [pmc.PyNode(node) for node in nodes]

    buffer_nodes = []
    for node in nodes:

        name = "{0}_{1}".format(node.name(), name_suffix)

        if use_match_transform:
            parent_nde = node.getParent()

            buffer_nde = pmc.createNode("transform", name=name)
            pmc.matchTransform(buffer_nde, node)
            buffer_nde.addChild(node)

            if parent_nde:
                parent_nde.addChild(buffer_nde)
            buffer_nodes.append(buffer_nde)

        else:
            buffer_nde = pmc.group(node,n=name)

            pivot = pmc.xform(node, query=True, worldSpace=True, rotatePivot=True)
            pmc.xform(buffer_nde, worldSpace=True, rotatePivot=pivot)
            pmc.xform(buffer_nde, worldSpace=True, scalePivot=pivot)

            buffer_nodes.append(buffer_nde)

    return buffer_nodes


def is_nodetype(node, type):
    """
    Check if node is node type.

    Args:
        node(pmc.PyNode): Node to check.
        type(str): Node type.

    Return:
        True or False

    """
    if node.nodeType() == type:
        return True
    return False


def has_parent(node):
    """
    Check if node has parent.

    Args:
        node(pmc.PyNode): Node to check.

    Return:
        True or False.

    """
    if node.getParent():
        return True
    return False


def is_root_node(node, type="transform", by_suffix="_root"):
    """
    Check if node is a hierarchy root node.

    Args:
        node(pmc.PyNode): Node to check.
        type(str): Node type. Default is "transform"

    Return:
        True or False.

    """
    if by_suffix:
        if re.search(r"{}$".format(by_suffix), node.name()):
            return True
    else:
        if is_nodetype(node, type) and has_parent(node) is False:
            return True
    return False


def get_scene_root_nodes(sort_out_node=None):
    """
    Get all root nodes in the scene.

    Args:
        sort_out_node(pmc.PyNode): Node which should not be included.
                                   Default is None.

    Return:
        List: All found nodes.

    """
    assemblies_list = pmc.ls(assemblies=True)
    if sort_out_node:
        if sort_out_node in assemblies_list:
            assemblies_list.remove(sort_out_node)
    return assemblies_list


def get_root_node_from_child_node(node, by_suffix=None):
    """
    Get hierarchy root node from given node.
    This can be the assembled node or a node with given name suffix in the hierarchy

    Args:
        node(pmc.PyNode): The child node.
        by_suffix(str or None): Search root node by string.

    Return:
        None if fail by suffix.
        pmc.PyNode()

    """
    assemble_node = node.getParent(generations=-1)
    if by_suffix:
        root_nd = None
        node_ = node
        while not root_nd:
            if node_ == assemble_node:
                break
            parent = node_.getParent()
            if is_root_node(parent, by_suffix=by_suffix):
                root_nd = parent
            node_ = parent
        return root_nd
    return assemble_node


def delete_scene_root_nodes(keep_node=None):
    """
    Delete all root nodes in the scene.

    Args:
        keep_node(pmc.PyNode): Node you want to keep.

    """
    scene_root_nodes = get_scene_root_nodes(keep_node)
    pmc.delete(scene_root_nodes)


def get_nodes_from_nodes_class_list(class_list):
    """
    Get nodes from given pymel nodes class.

    Args:
        class_list(list): Class list.

    Return:
        List:
            pmc.PyNode()
        None if no found.

    """
    return [
        pmc.ls(type=node_class)[0]
        for node_class in class_list
        if pmc.ls(type=node_class)
    ]


def get_ancestors(node, node_type=None):
    """
    Get all hierarchy ancestors.

    Args:
        node(pmc.PyNode()): The node to start from.
        node_type(str): The nodetypes you are searching for.
                        Be aware that search proccess will break
                        as soon as the correct node type is not found.

    Return:
        Empty array if fail.
        List:
            List of pmc.PyNode()

    """
    parent_nodes = []
    while node.getParent() is not None:
        parent_nd = node.getParent()
        if node_type:
            if parent_nd.nodeType() != node_type:
                break
        parent_nodes.append(parent_nd)
        node = parent_nd
    return parent_nodes


def get_dag_sorted(dag_items):
    """
    Sorts a list of dag nodes based on their longNames to get their hierarchical structure.

    Args:
        dag_items(list): The random list.

    Returns:
        List(dag_items): The sorted list.
    """
    dag_items.sort(key=lambda joint_node: len(str(joint_node.longName())))
    return dag_items


def get_transforms_distance_combined(transforms):
    """
    Calculates the combined length of all distances between the transforms in the list. Order very much matters.

    Args:
        transforms: List of Transform nodes, order very much matters.

    Returns:
        Float: Distances combined.
    """
    return sum(
        [
            pmc.datatypes.Vector(x[0].getTranslation(space="world")).distanceTo(
                pmc.datatypes.Vector(x[1].getTranslation(space="world"))
            )
            for x in pairwise(get_dag_sorted(transforms))
        ]
    )


def create_hierarchy_from_list(object_list):
    """
    Create a hierarchy from given list

    Args:
        object_list(list): List with pmc.PyNodes().

    """
    for x in range(len(object_list)):
        try:
            object_list[x].addChild(object_list[x+1])
        except:
            break


def swap_curve_shapes(source_node, target_node, keep_color_index=False, mirror=False, reel_swap=True):
    """
    Swap curve shapes.

    Args:
        source_node(pmc.PyNode): The source curve node.
        target_node(pmc.PyNode): The target curve node.
        keep_color_index(bool): Will keep the already existing shape colors.
                                Default is False
        mirror(bool): Will mirror the shapes over in the -1 X axes.
                      Default is False.
        reel_swap(bool): Will exchange the original shape nodes of the target node.
                         But all connections of the original shape nodes will be lost.
                         If False we transfer the worldspace data of the source shapes.
                         So we can keep the orginal shape node connections.
                         Default Is True.

    Returns:
        ValueError: If the reel_swap flag is set to False and the shape nodes count of
                    the source node and target node is not identical.

    """
    color_index = None
    delete_list = []
    # added ability to swap multiple shapes
    dpl_source = source_node.duplicate(n="tmp_{}".format(source_node.name(long=None)))[0]
    delete_list.append(dpl_source)
    pmc.delete(dpl_source.getChildren(type="transform"))
    if mirror:
        attributes_utils.unlock_attributes(dpl_source)
        mirror_grp = pmc.createNode("transform", n="mirror_grp")
        dpl_source.setParent(mirror_grp)
        mirror_grp.scaleX.set(-1.0)
        pmc.makeIdentity(mirror_grp, apply=True)
        ws_ps_dummy = rig_utils.create_transfrom_on_position(target_node, name="target_ws_ps_dummy_trs")
        dpl_source.setParent(ws_ps_dummy)
        pmc.makeIdentity(dpl_source, apply=True)
        delete_list.append(mirror_grp)
        delete_list.append(ws_ps_dummy)
    source_shapes = dpl_source.getShapes(noIntermediate=True)
    target_shapes = target_node.getShapes(noIntermediate=True)
    if reel_swap:
        if target_shapes:
            if keep_color_index:
                color_index = target_shapes[0].overrideColor.get()
        pmc.delete(target_shapes)
        for shape in source_shapes:
            if color_index:
                shape.overrideColor.set(color_index)
            pmc.parent(shape, target_node, relative=True, shape=True)
            shape.rename("{}Shape".format(target_node.name(long=None)))
    else:
        if not len(source_shapes) == len(target_shapes):
            raise ValueError(f"Shapes count from source and target nodes not identical.")
        for s_shape, t_shape in zip(source_shapes, target_shapes):
            s_shape.worldSpace[0].connect(t_shape.create)
            pmc.delete([s_shape, t_shape], ch=True)
    pmc.delete(delete_list)


def get_deform_shape(object_):
    """
    Gets the visible geometry shape regardless of whether
    the object is deformed or not.

    Args:
        object_(str, pymel.core.PyNode):    The object to check.

    Returns:
        pmc.PyNode():                       The object's deform shape.

    """

    if isinstance(object_, six.string_types):
        object_ = pmc.PyNode(object_)

    if not isinstance(object_, pmc.PyNode):
        _LOGGER.warning("could not convert input")
        return

    if object_.type() in ["nurbsSurface", "mesh", "nurbsCurve"]:
        object_ = object_.getParent()

    shapes = pmc.PyNode(object_).getShapes()

    if len(shapes) == 1:
        return shapes[0]

    else:
        real_shapes = [x for x
                       in shapes
                       if not x.intermediateObject.get()
                       ]

        return real_shapes[0] if real_shapes else None


def rename_shapes_to_transform_name(trs):
    """
    Rename shapes to transform name.

    Args:
        trs(pmc.PyNode): The transform node with the corresponding shape node.

    """
    try:
        shapes = trs.getShapes()
    except:
        shapes = None
    if shapes:
        new_name = "{0}Shape".format(trs.name(long=None))
        for shape in shapes:
            shape.rename(new_name)


def get_valid_objects(
        search_type="nurbsCurve",
        search_strings=("Host", "ctrl"),
        exclude_strings=("controlBuffer"),
):
    """
    Takes a [],[],and[] and returns a list with all the items meeting the conditions.

    Args:
        search_type(str):
        search_strings:
        exclude_strings:

    Returns:
        List: List containing the transforms of the related search type.
    """
    return list(
        set(
            [
                x.getParent()
                for x in pmc.ls(type=search_type)
                if not any(z in x.shortName().split(":")[-1] for z in exclude_strings)
                and all(
                    y in x.getParent().shortName().split(":")[-1]
                    for y in search_strings
                )
            ]
        )
    )
