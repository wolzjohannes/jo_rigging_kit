# Author:     Johannes Wolz / Lead Rigging TD

"""
Util module for blendShape data management.
With the utils functions you can mainly export and import whole blendShape
setups. But it contains even functions to edit and create blendShape nodes and
targets.
The export data dict is called blendshape_data_dict.

{
    "base_obj_export": "blendShape1_base_geo.obj",
    "blendshape_node_info": {
        "history_location": 0,
        "name": "blendShape1",
        "origin": 0,
        "topologyCheck": true
    },
    "mesh_data": {
        "mesh_shape": "pSphere1Shape",
        "num_polys": 1000000,
        "num_vertices": 999002,
        "poly_vertex_id_list": "blendShape1_poly_vertex_id.npy",
        "verts_ws_pos_list": "blendShape1_verts_ws_positions.npy"
    },
    "target_deltas": [
        {
            "inbetween_deltas": [
                {
                    "5542": {
                        "name": "pSphere2_0.542",
                        "target_components":
                        "blendShape1_inbetween_deltas_0_5542.npz",
                        "target_points":
                        "blendShape1_inbetween_deltas_0_5542.npz",
                        "weight": 0.542
                    }
                }
            ],
            "target_deltas": "blendShape1_deltas_0.npz",
            "target_index": 0,
            "target_name": "pSphere2"
        },
        {
            "inbetween_deltas": [],
            "target_deltas": "blendShape1_deltas_1.npz",
            "target_index": 1,
            "target_name": "pSphere3"
        }
    ],
    "weight_driver_nodes_data": []
}

The blendshape export directory looks like this:

blendshape1(source blendshape node name):
    - blendshape1_blendshape_data.json (Inherits all data about the blendshape,
                                        the mesh and file names)
    - blendshape1_mesh_data.json (Inherits the needed mesh data and
                                  file names for the mesh validation)
    - blendShape1_base_geo.mb (Export of the base obj geo for a setup transfer)
    - blendShape1_poly_vertex_id.npy (Inherits the poly vertex id array)
    - blendShape1_verts_ws_positions.npy (Inherits the vertices world
                                          position array)
    - inbetween_deltas:
        - blendShape1_inbetween_deltas_0_5542.npz (Delta points and
                                                   component arrays)
    - target_deltas:
        - blendShape1_deltas_0.npz (Delta points and component arrays)


NOT SUPPORTED YET:
- Post Deformer blendshape nodes with numpy array.
- inbetween interpolation curve types.
- Realtive inbetween targets.
- No inbetweens support with .shp file export.

SUPPORTED WEIGHT DIRVER NODES:

can you see in the global

VALID_WEIGHT_DRIVER_NODETYPES

variable


"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import pathlib
# Import built-in modules
# from builtins import open
from builtins import dict
from builtins import int
from builtins import range
from builtins import str
import glob
import json
# Import python standart import
import logging
import os
import pprint
from importlib import reload

# Import third-party modules
from future import standard_library # noqa: import error
from maya import OpenMaya # noqa: import error
from maya import OpenMayaAnim # noqa: import error
import maya.cmds as cmds # noqa: import error
import numpy # noqa: import error

# Import Maya specific modules
import pymel.core # noqa: import error
import pymel.core as pmc # noqa: import error

from pxo_rigging_kit.io_version_control import version_io
# Import local modules
from pxo_rigging_kit.maya_utils import dag_utils
from pxo_rigging_kit.maya_utils import decorators
from pxo_rigging_kit.maya_utils import exceptions
from pxo_rigging_kit.maya_utils import mesh_utils
from pxo_rigging_kit.maya_utils import openmaya_utils
from pxo_rigging_kit.maya_utils import paths_utils
from pxo_rigging_kit.maya_utils import scene_utils
from pxo_rigging_kit.maya_utils.rigging import rig_utils

standard_library.install_aliases()
reload(rig_utils)

##########################################################
# GLOBALS
##########################################################

_LOGGER = logging.getLogger(f"{__name__}.py")
_LOGGER.setLevel(logging.INFO)

DECORATORS = decorators.Decorators()

DECORATORS.debug = True

DECORATORS.logger = _LOGGER

standard_library.install_aliases()


_BLENDSHAPE_INFO_DICT = {
    "origin": [
        (OpenMayaAnim.MFnBlendShapeDeformer.kLocalOrigin, {"origin": "local"}),
        (OpenMayaAnim.MFnBlendShapeDeformer.kWorldOrigin, {"origin": "world"}),
    ],
    "historyLocation": [
        (
            OpenMayaAnim.MFnBlendShapeDeformer.kFrontOfChain,
            {"frontOfChain": True},
        ),
        (OpenMayaAnim.MFnBlendShapeDeformer.kNormal, {"automatic": True}),
        (OpenMayaAnim.MFnBlendShapeDeformer.kPost, {"after": True}),
        (OpenMayaAnim.MFnBlendShapeDeformer.kOther, {"afterReference": True}),
    ],
}

VALID_WEIGHT_DRIVER_NODETYPES = {
    "remapValue",

    "addDoubleLinear",
    "multDoubleLinear",

    "animCurveUU",
    "animCurveTU",

    "multiplyDivide",
    "plusMinusAverage",
    "poseInterpolator",
    "transform",
    "weightDriver",
    "combinationShape",
    "floatConstant",
    "blendWeighted",
    "clamp",
}

VALID_WEIGHT_DRIVER_NDS_WITH_TRS = ["poseInterpolator", "weightDriver"]

WEIGHT_DRIVER_CONNECTIONS_NODES_FILTER = [
    "defaultRenderUtilityList1",
    "MayaNodeEditorSavedTabsInfo",
    "poseInterpolatorManager",
    "hyperLayout4",
]

BLENDSHAPE_DATA_JSON_FILE_NAME_PATTERN = "blendshape_data"
PXO_BSHP_DIR_NAME = "PXO_BSHP"
PXO_BSWGH_DIR_NAME = "PXO_BSWGH"
WEIGHT_DRIVER_DUPLICATE_PREFIX = "DUP"


##########################################################
# FUNCTIONS
##########################################################


def get_blendshape_node_infos(blendshape_node):
    """
    Get infos from given blendshape node.

    Args:
        blendshape_node(str): Blendshape node name.

    Return:
         Dict: {
        "name": blendshape_node,
        "history_location": blendshape_fn.historyLocation(),
        "origin": blendshape_fn.origin(),
        "topologCheck": bool
        }

    """
    blendshape_fn = get_blendshape_fn(blendshape_node)
    top_check_m_plug = blendshape_fn.findPlug("topologyCheck")
    return {
        "name": blendshape_node,
        "history_location": blendshape_fn.historyLocation(),
        "origin": blendshape_fn.origin(),
        "topologyCheck": top_check_m_plug.asBool(),
    }


def get_weight_driver_nodes(blendshape_node):
    """
    Get the connected nodes name and the connected plugs from all weight plugs.

    Args:
        blendshape_node(str): Blendshape node name.

    Return:
         List: [((node_name, node_plug_name), weight_name),
                ((node_name, node_plug_name), weight_name)]

    """
    result = []
    blendshape_fn = get_blendshape_fn(blendshape_node)
    weight_plug = blendshape_fn.findPlug("weight")
    weight_indecies = get_weight_indexes(blendshape_node)
    for x in weight_indecies:
        plug = weight_plug.elementByLogicalIndex(x)
        if plug.isDestination():
            source_nd_name = plug.source().name().split(".")[0]
            result.append(pymel.core.PyNode(source_nd_name))
    return result


def get_weight_driver_node_data(node, node_type):
    """
    Get weight driver node data.

    Args:
        node(pymel.core.PyNode()): Weight driver node.
        node_type(str): The node type.

    Return:
        Dict:
        {
        "node": node,
        "node_type": node_type,
        "destinations": destinations,
        "source": source,
        "parent": parent node,
        "vector_angle_driver_loc": vector angle driver locator,
        "vector_angle_driver_loc_parent": vector_angle_driver_loc_parent
        }

    """
    source = []
    parent_ = None
    vector_angle_driver_loc = None
    vector_angle_driver_loc_parent = None

    destinations_temp = node.connections(
        source=False, destination=True, p=True, scn=True
    )

    destinations_temp = [
        attr_
        for attr_ in destinations_temp
        if attr_.node().name() not in WEIGHT_DRIVER_CONNECTIONS_NODES_FILTER
    ]

    bs_destinations = [
        [
            attr__.connections(
                p=True, source=True, destination=False, scn=True
            )[0].name(),
            "{}.{}".format(
                attr__.node().name(), cmds.aliasAttr(attr__.name(), query=True)
            ),
        ]
        for attr__ in destinations_temp
        if all(
            [
                attr__.node().nodeType() == "blendShape",
                cmds.aliasAttr(attr__.name(), query=True),
            ]
        )
    ]

    non_bs_destinations = [
        [attr__.connections(p=True, scn=True)[0].name(), attr__.name()]
        for attr__ in destinations_temp
        if attr__.node().nodeType() != "blendShape"
    ]

    destinations = bs_destinations + non_bs_destinations

    if node_type != "transform":
        source_temp_list = [
            attr_
            for attr_ in node.connections(
                source=True, destination=False, p=True, scn=True
            )
            if attr_.node().name() not in WEIGHT_DRIVER_CONNECTIONS_NODES_FILTER
        ]
        for attr__ in source_temp_list:
            for attr___ in attr__.connections(p=True, scn=True):
                if attr___.node() == node:
                    source.append([attr__.name(), attr___.name()])

    if node_type in VALID_WEIGHT_DRIVER_NDS_WITH_TRS:
        if node_type == "poseInterpolator" or node_type == "weightDriver":
            parent_ = node.getParent(generations=2)
        else:
            parent_ = node.getParent()

        if parent_:
            parent_ = parent_.name()

        if node_type == "weightDriver":
            vector_angle_driver_loc = node.driverMatrix.connections(
                d=False, s=True, scn=True
            )
            if vector_angle_driver_loc:
                vector_angle_driver_loc = vector_angle_driver_loc[0]
                vector_angle_driver_loc_parent = (
                    vector_angle_driver_loc.getParent()
                )
                if vector_angle_driver_loc_parent:
                    vector_angle_driver_loc_parent = (
                        vector_angle_driver_loc_parent.name()
                    )
    return {
        "node": node,
        "node_type": node_type,
        "destinations": destinations,
        "source": source,
        "parent": parent_,
        "vector_angle_driver_loc": vector_angle_driver_loc,
        "vector_angle_driver_loc_parent": vector_angle_driver_loc_parent,
    }


@DECORATORS.x_timer
def get_weights_drivers_data(blendshape_node):
    """
    Get weights drivers data from given blendshape node.

    Args:
        blendshape_node(str): Blendshape node name.

    Return:
        List:
        [
        {
            "destinations": [
                [
                    "remapValue1_dup.outValue",
                    "test_connections_blendshape_node.weight[0]"
                ],
                [
                    "remapValue1_dup.message",
                    "weight_driver_nodes_set.dnSetMembers[5]"
                ]
            ],
            "node": "remapValue1",
            "node_type": "remapValue",
            "source": [
                [
                    "connections_test_interface_grp.test_float_0",
                    "remapValue1_dup.inputValue"
                ]
            ]
        }
        ]
    """
    weight_driver_nodes_data_list = []

    weight_driver_nodes_list = get_weight_driver_nodes(blendshape_node)

    if not weight_driver_nodes_list:
        return weight_driver_nodes_data_list

    for node in weight_driver_nodes_list:
        node_type = validate_blendshape_weight_driver_node(node)

        weight_driver_node_data = get_weight_driver_node_data(
            node, node_type
        )
        weight_driver_nodes_data_list.append(weight_driver_node_data)

    return weight_driver_nodes_data_list


def _processing_weight_driver_nodes_data_for_export(
    blendshape_node, save_directory=None, file_prefix=None
):
    """
    Process the weight dirver nodes data for json export.

    Args:
        blendshape_node(str): Blendshape node name.
        save_directory(str): The directory to save the files into.
        file_prefix(str): Optional prefix for the name. If None will take the
                          blendshape name. Default is None.

    Return:
        List: [export_dir(str),
               weight_driver_nodes_data_list(list filled with dict)]

    """
    if not file_prefix:
        file_prefix = blendshape_node

    dupl_node_list = []
    # Get the weight drivers nodes data as  a list
    weight_driver_nodes_data_list = get_weights_drivers_data(blendshape_node)
    # We loop through the list and find the drivers. Then we duplicate it.
    # Then we pass the new name of the duplicates into the dict.
    # So we can use it later in the import.
    if not weight_driver_nodes_data_list:
        return

    node_names_list = []
    for data_dict in weight_driver_nodes_data_list:
        # new_name = str(data_dict.get("node").name())
        # if data_dict["node_type"] != "transform":
        node = data_dict.get("node")
        orig_name = node.name()
        new_name = "{}_{}".format(
            node.name(), WEIGHT_DRIVER_DUPLICATE_PREFIX
        )
        data_dict["orig_name"] = orig_name
        if not pymel.core.objExists(new_name):
            duplicate = node.duplicate(n=new_name)[0]
            if data_dict["node_type"] in VALID_WEIGHT_DRIVER_NDS_WITH_TRS:
                shape_nd = duplicate.getShape()
                if shape_nd:
                    new_name_ = new_name.replace("Shape", "")
                    orig_name_ = orig_name.replace("Shape", "")
                    duplicate.rename(new_name_)
                    shape_nd.rename(new_name)
                    node_names_list.append((orig_name_, new_name_))
            dupl_node_list.append(duplicate)
            pymel.core.parent(duplicate, None)
        node_names_list.append((orig_name, new_name))
        if data_dict["node_type"] == "weightDriver":
            driver_loc = data_dict["vector_angle_driver_loc"]
            if driver_loc:
                loc_orig_name = driver_loc.name()
                data_dict[
                    "vector_angle_driver_loc_orig_name"
                ] = loc_orig_name
                driver_loc_new_name = "{}_{}".format(
                    loc_orig_name, WEIGHT_DRIVER_DUPLICATE_PREFIX
                )
                if not pymel.core.objExists(driver_loc_new_name):
                    loc_dup = driver_loc.duplicate(n=driver_loc_new_name)
                    dupl_node_list.extend(loc_dup)
                    pymel.core.parent(loc_dup, None)
                node_names_list.append((loc_orig_name, driver_loc_new_name))
                data_dict["vector_angle_driver_loc"] = driver_loc_new_name
        data_dict["node"] = new_name
    # Here we loop again through weight driver list.
    # And reformat the driver nodes names to the duplicated ones so we
    # can connect it correctly at import.
    for data_dict_ in weight_driver_nodes_data_list:
        source_list = data_dict_.get("source")
        destinations_list = data_dict_.get("destinations")
        for source_data_list in source_list:
            for name_tuple in node_names_list:
                for (
                    index,
                    attr_name,
                ) in enumerate(source_data_list):
                    source_data_list[index] = attr_name.replace(
                        "{}.".format(name_tuple[0]),
                        "{}.".format(name_tuple[1]),
                    )
        for dest_data_list in destinations_list:
            for name_tuple_ in node_names_list:
                for (
                    index_,
                    attr_name_,
                ) in enumerate(dest_data_list):
                    dest_data_list[index_] = attr_name_.replace(
                        "{}.".format(name_tuple_[0]),
                        "{}.".format(name_tuple_[1]),
                    )

    pymel.core.select(dupl_node_list)
    export_dir = os.path.normpath(
        os.path.join(
            save_directory, "{}_weight_driver_nodes".format(file_prefix)
        )
    )
    export_dir = pymel.core.exportSelected(
        export_dir,
        constructionHistory=False,
        force=True,
        channels=False,
        constraints=False,
        expressions=False,
        shader=False,
        preserveReferences=False,
        type="mayaAscii",
    )

    pymel.core.delete(dupl_node_list)
    return [export_dir, weight_driver_nodes_data_list]


# No post blendshape support jet.
def get_blendshape_nodes(
    node, as_string=True, as_pynode=False, as_fn=False, level=10
):
    """
    Get all source blendshape nodes from given shape node.

    Args:
        node(str, pymel.core.PyNode()): Mesh shape node or transform node.
        as_string(bool): Give nodes names back.
        as_pynode(bool): Give PyNodes back.
        as_fn(bool): Give OpenMaya.MFnBlendShapeDeformer back.
        level(int): Define how far you want to travel the deformer stack.
                    So you would find more or less connected blendshape
                    deformers.
                    Default value is 10.

    Return:
        List: All found blendshape nodes.

    """
    if not isinstance(node, pymel.core.PyNode):
        node = pymel.core.PyNode(node)

    bshp_nodes = node.listHistory(type="blendShape",
                                  pdo=True,
                                  levels=level,
                                  )

    if as_pynode:
        return bshp_nodes

    if as_fn:
        return [get_blendshape_fn(node.nodeName())
                for node
                in bshp_nodes
                ]

    if as_string:
        return [str(node.nodeName())
                for node
                in bshp_nodes
                ]


def is_blendshape_node(node):
    """
    Gives back if given node is a blendshape node.

    Args:
        node(str): Name of the node to check.

    Return:
        Bool: True/False

    """
    m_object = openmaya_utils.get_mobject_om1(node)
    return bool(m_object.hasFn(OpenMaya.MFn.kBlendShape))


def get_blendshape_fn(blendshape_node):
    """
    Get the OpenMaya.MFnBlendshapeDeformer from given blendshape node name.

    Args:
        blendshape_node(str): Blendshape node name.

    Return:
         OpenMaya.MFnBlendshapeDeformer.

    """
    m_object = openmaya_utils.get_mobject_om1(blendshape_node)
    if is_blendshape_node(blendshape_node):
        return OpenMayaAnim.MFnBlendShapeDeformer(m_object)


def get_weight_indexes(blendshape_node):
    """
    Get all weight indexes from given blendshape node.

    Args:
        blendshape_node(str): Blendshape node name.

    Return:
         List: All found weight indexes.

    """
    blendshape_fn = get_blendshape_fn(blendshape_node)
    m_int_array = OpenMaya.MIntArray()
    blendshape_fn.weightIndexList(m_int_array)
    return m_int_array


def get_base_objects(blendshape_node):
    """
    Get all base objects from given blendshape node.
    The base object is the shape node connected to the
    blendshape deformer.

    Args:
        blendshape_node(str): Blendshape node name.

    Return:
        Tuple: OpenMaya.MFnMesh objects.

    """
    bshp_node = pymel.core.PyNode(blendshape_node)
    base_objects_list = bshp_node.getBaseObjects()
    base_object_tuple = tuple([openmaya_utils.get_dag_path_om2(node.longName()) for node in base_objects_list])
    return base_object_tuple


def get_weight_names(blendshape_node):
    """
    Get the weight attribute names from given blendshape node.

    Args:
        blendshape_node(str): Blendshape node name.

    Return:
        Tuple: All found weight names. Empty if None.

    """
    weight_names = []
    blendshape_fn = get_blendshape_fn(blendshape_node)
    weight_plug = blendshape_fn.findPlug("weight")

    for x in range(weight_plug.numElements()):
        plug = weight_plug.elementByPhysicalIndex(x)
        weight_names.append(plug.partialName(False, False, False, True))

    return tuple(weight_names)


def get_weight_from_inbetween_plug_index(plug_index):
    """
    Get the weight value from given inbetween plug index.

    Args:
        plug_index(int): The index of the inbetween plug

    Return:
        Float: The weight value.

    """
    return float("0.{}".format(str(plug_index)[1:]))


def get_inbetween_plug_index_from_weight(weight):
    """
    Get the inbetween plug index.

    Args:
        weight(float): The inbetween weight value.

    Return:
        Integer: The plug index.

    """
    return int(str(weight).replace("0.", "5"))


def target_index_exists(blendshape_node, index):
    """
    Check if given target index exist.

    Args:
        blendshape_node(str): Blendshape node name.
        index(int): Index to check for.

    Return:
         Bool: True or False

    """
    indexes = get_weight_indexes(blendshape_node)
    if index in indexes:
        return True
    return False


def get_weight_name_from_index(
    blendshape_node, index, partial_name=False, as_m_object_attr=False
):
    """
    Get weight alias name from given index.

    Args:
        blendshape_node(str): Blendshape node name.
        index(int): The Index to search for.
        partial_name(bool): Gives back as weight name.
        as_m_object_attr: gives back as openMaya.MPlug.Attribute.

    Return:
         String: Weight name
         OpenMaya.MPlug.Attribute object.
         Error if fail.

    """
    blendshape_fn = get_blendshape_fn(blendshape_node)
    weight_plug = blendshape_fn.findPlug("weight")
    try:
        plug = weight_plug.elementByLogicalIndex(index)
        weight_name = plug.partialName(False, False, False, True)
        if not partial_name:
            weight_name = plug.name()
        if as_m_object_attr:
            weight_name = plug.attribute()
        return weight_name
    except:
        raise IndexError(
            "Unable to find weight name for index: {}".format(index)
        )


def get_inbetween_values_from_target_index(blendshape_node, index):
    """
    Get all inbetween weight values from an target by index.

    Args:
        blendshape_node(str): Blendshape node name.
        index(int): The Index to search for.

    Return:
        List: All found values as float.

    """
    result = []
    inbetween_list = get_inbetween_plugs(blendshape_node, index)
    if inbetween_list:
        result = [
            get_weight_from_inbetween_plug_index(list(in_dict.keys()))[0]
            for in_dict in inbetween_list
        ]
    return result


def set_all_weight_values(blendshape_node, value):
    """
    Set all weight values to given value.
    """
    blendshape_fn = get_blendshape_fn(blendshape_node)
    weight_indexes = get_weight_indexes(blendshape_node)
    for index in weight_indexes:
        blendshape_fn.setWeight(index, value)


def disconnect_all_weight_values(blendshape_node):
    """
    Disconent all weight attributes.
    """
    weight_indexes = get_weight_indexes(blendshape_node)
    for index in weight_indexes:
        pymel.core.PyNode(blendshape_node).attr(
            "weight[{}]".format(index)
        ).disconnect()


def rename_weight_name_from_index(blendshape_node, index, new_name):
    """
    Rename weight name found on given index.
    Takes similiar attributes on correlation.
    And add the count of the similiar attributes as suffix

    Args:
        blendshape_node(str): Blendshape node name.
        index(int): The Index to search for.
        new_name(str): The new name.

    """
    attribute_from_index = get_weight_name_from_index(blendshape_node, index)
    alias_attributes = [
        attr
        for attr in cmds.aliasAttr(blendshape_node, query=True)
        if "weight" not in attr
    ]
    similar_attributes = [attr for attr in alias_attributes if new_name in attr]
    if similar_attributes:
        new_name = "{}{}".format(new_name, len(similar_attributes))
    cmds.aliasAttr(new_name, attribute_from_index)


def rename_weight_name_from_index2(blendshape_node, index, new_name):
    """
    Rename weight name found on given index.

    Args:
        blendshape_node(str): Blendshape node name.
        index(int): The Index to search for.
        new_name(str): The new name.

    """
    cmds.aliasAttr(new_name, "{}.weight[{}]".format(blendshape_node, index))


def add_target(
    blendshape_node,
    index=None,
    target="new_target",
    weight=1.0,
    is_inbetween=False,
    keep_target=False
):
    """
    Add a new empty target to blendshape node.

    Args:
        blendshape_node(str): Blendshape node name.
        index(int): The target index.
        target(str, OpenMaya.MObject): Target name or new target with deltas..
        weight(float): The maximum weight the target will have an effect.
        is_inbetween(bool): Define if new target is an inbetween. If it is
                            the index number will define to which
                            target the inbetween belongs to.
        keep_target(bool): If True it will keep the target alive. And it will
                           be still connected to the blendshape node.
                           By Default it is False.

    Return:
        True if succeed.

    """
    blendshape_fn = get_blendshape_fn(str(blendshape_node))
    base_obj = get_base_objects(blendshape_node)[0]

    base_m_object = openmaya_utils.get_mobject_om1(str(base_obj.fullPathName()))

    if is_inbetween:
        if weight == 0.0 or weight == 1.0:
            raise AttributeError(
                "Weight param can not be 0.0 or 1.0 if you add an " "inbetween."
            )
        inb_port = get_inbetween_plug_index_from_weight(weight)
        if isinstance(target, OpenMaya.MObject):
            mfn_mesh = OpenMaya.MFnMesh(target)
            blendshape_fn.addTarget(base_m_object, index, target, weight)
            set_inbetween_name_from_bshp_port(
                blendshape_node, inb_port, index, mfn_mesh.name()
            )
            return True
        blendshape_fn.addTarget(base_m_object, index, weight)
        set_inbetween_name_from_bshp_port(
            blendshape_node, inb_port, index, target
        )
        return True
    if weight < 1.0 and weight > 0.0:
        raise AttributeError(
            "Weights between 0.0 and 1.0 can just be used as inbetween target."
        )
    if isinstance(target, OpenMaya.MObject):
        blendshape_fn.addTarget(base_m_object, index, target, weight)
        if not keep_target:
            dag_modifier = OpenMaya.MDGModifier()
            dag_modifier.deleteNode(target)
        return True
    blendshape_fn.addTarget(base_m_object, index, weight)
    rename_weight_name_from_index2(blendshape_fn.name(), index, target)
    blendshape_fn.setWeight(index, 1.0)
    blendshape_fn.setWeight(index, 0.0)
    return True


@DECORATORS.x_timer
def create_blendshape_node(
    geo_transform,
    name=None,
    origin_enum=0,
    history_location_enum=1,
    targets_list=None,
    inbetweens_list=None,
    topologyCheck=True,
    keep_target=False
):
    """
    Create a new blendshape node.

    Args:
        geo_transform(str, pymel.core.PyNode()): The transform node of the
                                                 geo for the blendshape node
        name(str): Name of the blendshape node. If None will take maya_utils
                   default naming. Default is None.
        origin_enum(int): Enum index in _BLENDSHAPE_INFO_DICT["origin"] for
                          the spaces of the deformation origin. Default is
                          kLocalOrigin.
        history_location_enum(int): Enum index in
                                    _BLENDSHAPE_INFO_DICT["historyLocation"]
                                    for the place in the deformation order of
                                    the mesh.
                                    Default is kNormal("automatic").
        targets_list(list): List with names(str) or OpenMaya.MObjects for the
                            targets of the node. The order of the list is the
                            index order of the targets.
                            Will just add targets if the list is not None.
                            By default is None.
        inbetweens_list(List): The List to add inbetweens.It has to be filled
                               with this template:
                               [
                               {
                               port_index:
                               {
                                 "name": string or OpenMaya.MObject,
                                 "weight": float
                                }
                                }
                                ]
                               The order of the tuples in the list is the index
                               order of the inbetweens belonging.
        topologyCheck(bool): Enable/Disable the topology check of the
                             blendshape node.
        keep_target(bool): If True it will keep the targets alive. And they will
                           be still connected to the blendshape node.
                           By Default it is False.
    """
    if not isinstance(geo_transform, pymel.core.PyNode):
        geo_transform = pymel.core.PyNode(geo_transform)
    mesh_shape_nd_name = [
        str(geo_transform.getShape(noIntermediate=True).name(long=None))
    ]
    mesh_shape_m_obj_array = openmaya_utils.get_m_obj_array(mesh_shape_nd_name)
    bshp_fn = OpenMayaAnim.MFnBlendShapeDeformer()
    bshp_fn.create(
        mesh_shape_m_obj_array,
        _BLENDSHAPE_INFO_DICT.get("origin")[origin_enum][0],
        _BLENDSHAPE_INFO_DICT.get("historyLocation")[history_location_enum][0],
    )
    if targets_list:
        for index, target in enumerate(targets_list):
            add_target(bshp_fn.name(), index, target, keep_target=keep_target)
    if inbetweens_list:
        for index_, list_ in enumerate(inbetweens_list):
            if list_:
                for inbetween_dict in list_:
                    dict_items = list(inbetween_dict.items())
                    for item in dict_items:
                        add_target(
                            bshp_fn.name(),
                            index_,
                            item[1].get("name"),
                            item[1].get("weight"),
                            True,
                        )
    if topologyCheck:
        pymel.core.PyNode(bshp_fn.name()).topologyCheck.set(True)
    if name:
        bshp_fn.setName(name)


def OM_get_blendshape_deltas_from_index(blendshape_node, index, bshp_port=6000):
    """
    Get the blendshape delta values with openMaya.
    This is really fast if you stay in maya_utils.
    But if you want to export this data, it is really slow.
    This is because of the conversion from the openMaya.MPlug.MObject to an
    array we can use further. For that Maya Commands and Mel is faster.

    Args:
        blendshape_node(str): Blendshape node name.
        index(int): The target index.
        bshp_port(int): Port number of the blendshape target. 6000 represents a
                        weight value of 1.0 and 5000 a value of 0.0. 4000 is
                        -1.0.
                        And everything between 6000, 5000 and 4000 are the
                        inbetween targets.
                        This is because the blendshape node supports inbetweens
                        and minus weight values.
                        Default is 6000.

    Return:
        Tuple: (points position as OpenMaya.MObject, affected components as
                OpenMaya.MObject)

    """
    points_pymel_attr = (
        pymel.core.PyNode(blendshape_node)
        .inputTarget[0]
        .inputTargetGroup[index]
        .inputTargetItem[bshp_port]
        .inputPointsTarget
    )
    try:
        points_m_object = points_pymel_attr.__apimplug__().asMObject()
        component_pymel_attr = (
            pymel.core.PyNode(blendshape_node)
            .inputTarget[0]
            .inputTargetGroup[index]
            .inputTargetItem[bshp_port]
            .inputComponentsTarget
        )
        components_m_object = component_pymel_attr.__apimplug__().asMObject()
    except:
        points_m_object = None
        components_m_object = None
    return points_m_object, components_m_object


def get_blendshape_deltas_from_index(blendshape_node, index, bshp_port=6000):
    """
    Get the blendshape deltas.

    Args
        blendshape_node(str): Blendshape node name.
        index(int): The target index.
        bshp_port(int): Port number of the blendshape target. 6000 represents a
                        weight value of 1.0 and 5000 a value of 0.0. 4000 is
                        -1.0.
                        And everything between 6000, 5000 and 4000 are the
                        inbetween targets.
                        This is because the blendshape node supports inbetweens
                        and minus weight values.
                        Default is 6000.

    Return:
        Tuple: (points positions as array, affected components as array)

    """
    pt = cmds.getAttr(
        "{}.inputTarget[0].inputTargetGroup[{}].inputTargetItem["
        "{}].inputPointsTarget".format(blendshape_node, index, bshp_port)
    )
    ct = cmds.getAttr(
        "{}.inputTarget[0].inputTargetGroup[{}].inputTargetItem["
        "{}].inputComponentsTarget".format(blendshape_node, index, bshp_port)
    )
    return pt, ct


@DECORATORS.x_timer
def OM_set_blendshape_deltas_by_index(
    blendshape_node, index, deltas_tuple, bshp_port=6000
):
    """
    Set the blendshape deltas with OpenMaya.

    Args:
        blendshape_node(str): Blendshape node name.
        index(int): The target index.
        deltas_tuple(tuple): Deltas for setting.
                            (points position as OpenMaya.MObject, affected
                            components as OpenMaya.MObject)
        bshp_port(int): Port number of the blendshape target. 6000 represents a
                        weight value of 1.0 and 5000 a value of 0.0. 4000 is
                        -1.0.
                        And everything between 6000, 5000 and 4000 are the
                        inbetween targets.
                        This is because the blendshape node supports inbetweens
                        and minus weight values.
                        Default is 6000.
    """
    # if index not in get_weight_indexes(blendshape_node):
    #     raise AttributeError("Given index not exist. Will abort.")
    if all(deltas_tuple):
        target_points = deltas_tuple[0]
        target_indices = deltas_tuple[1]
        points_pymel_attr = (
            pymel.core.PyNode(blendshape_node)
            .inputTarget[0]
            .inputTargetGroup[index]
            .inputTargetItem[bshp_port]
            .inputPointsTarget
        )
        points_m_plug = points_pymel_attr.__apimplug__()
        points_m_plug.setMObject(target_points)
        component_pymel_attr = (
            pymel.core.PyNode(blendshape_node)
            .inputTarget[0]
            .inputTargetGroup[index]
            .inputTargetItem[bshp_port]
            .inputComponentsTarget
        )
        components_m_plug = component_pymel_attr.__apimplug__()
        components_m_plug.setMObject(target_indices)
    else:
        _LOGGER.warning(
            "Deltas arrays are empty for index: {} and bshp_port: {}".format(
                index, bshp_port
            )
        )


@DECORATORS.x_timer
def set_blendshape_deltas_by_index(
    blendshape_node, index, deltas_tuple, bshp_port=6000
):
    """
    Set the bendshape deltas with maya_utils commands.

    Args:
        blendshape_node(str): Blendshape node name.
        index(int): The target index.
        deltas_tuple(tuple): Deltas for setting.
                            (points position as array,
                            affected components as array)
        bshp_port(int): Port number of the blendshape target. 6000 represents a
                        weight value of 1.0 and 5000 a value of 0.0. 4000 is
                        -1.0.
                        And everything between 6000, 5000 and 4000 are the
                        inbetween targets.
                        This is because the blendshape node supports inbetweens
                        and minus weight values.
                        Default is 6000.
    """
    pt = deltas_tuple[0]
    ct = deltas_tuple[1]
    try:
        cmds.setAttr(
            "{}.inputTarget[0].inputTargetGroup[{}].inputTargetItem[{}"
            "].inputPointsTarget".format(blendshape_node, index, bshp_port),
            len(pt),
            *pt,
            type="pointArray"
        )
    except:
        _LOGGER.warning(
            "Target with index: {} and port: {} has no point values.".format(
                index, bshp_port
            )
        )
    try:
        cmds.setAttr(
            "{}.inputTarget[0].inputTargetGroup[{}].inputTargetItem[{}"
            "].inputComponentsTarget".format(blendshape_node, index, bshp_port),
            len(ct),
            *ct,
            type="componentList"
        )
    except:
        _LOGGER.warning(
            "Target with index: {} and port: {} has no component values.".format(
                index, bshp_port
            )
        )


def set_inbetween_name_from_bshp_port(
    blendshape_node, inbetween_bshp_port, target_index, name
):
    """
    Get the inbetween name from given bshp port number.

    Args:
        blendshape_node(str): Blendshape node name.
        inbetween_bshp_port(int): Port number of the blendshape target.
                                  6000 represents a
                                  weight value of 1.0 and 5000 a value of 0.0.
                                  4000 is -1.0.
                                  And everything between 6000, 5000 and 4000
                                  are the inbetween targets.
                                  This is because the blendshape node supports
                                  inbetweens and minus weight values.
        target_index(int): The target index the inbetween belongs to.
        name(str). Name to set.

    Return:
        Raise exception if fail.
        String if succeed.

    """
    bshp_fn = get_blendshape_fn(blendshape_node)
    m_plug = bshp_fn.findPlug("inbetweenInfoGroup")
    info_plug = m_plug.elementByLogicalIndex(target_index).child(0)
    try:
        info_plug.elementByLogicalIndex(inbetween_bshp_port).child(1).setString(
            name
        )
    except:
        raise AttributeError(
            "Can not find name for inbetween port {} at target index {}.".format(
                inbetween_bshp_port, target_index
            )
        )


def is_target_connected(blendshape_node, index, bshp_port):
    """
    Gets if target plug is connected to an mesh shape.

    Args:
        blendshape_node(str): Blendshape node name.
        index(int): The target index.
        deltas_tuple(tuple): Deltas for setting.
                            (points position as array,
                            affected components as array)
        bshp_port(int): Port number of the blendshape target. 6000 represents a
                        weight value of 1.0 and 5000 a value of 0.0. 4000 is
                        -1.0.
                        And everything between 6000, 5000 and 4000 are the
                        inbetween targets.
                        This is because the blendshape node supports inbetweens
                        and minus weight values.
    Return:
        Bool: True or False.

    """
    return (
        pymel.core.PyNode(blendshape_node)
        .inputTarget[0]
        .inputTargetGroup[index]
        .inputTargetItem[bshp_port]
        .isConnected()
    )


def get_inbetween_name_from_bshp_port(
    blendshape_node, inbetween_bshp_port, target_index
):
    """
    Get the inbetween name from given bshp port number.

    Args:
        blendshape_node(str): Blendshape node name.
        inbetween_bshp_port(int): Port number of the blendshape target.
                                  6000 represents a
                                  weight value of 1.0 and 5000 a value of 0.0.
                                  4000 is -1.0.
                                  And everything between 6000, 5000 and 4000
                                  are the inbetween targets.
                                  This is because the blendshape node supports
                                  inbetweens and minus weight values.
        target_index(int): The target index the inbetween belongs to.

    Return:
        Raise exception if fail.
        String if succeed.

    """
    bshp_fn = get_blendshape_fn(blendshape_node)
    m_plug = bshp_fn.findPlug("inbetweenInfoGroup")
    info_plug = m_plug.elementByLogicalIndex(target_index).child(0)
    try:
        return (
            info_plug.elementByLogicalIndex(inbetween_bshp_port)
            .child(1)
            .asString()
        )
    except:
        raise AttributeError(
            "Can not find name for inbetween port {} at target index {}.".format(
                inbetween_bshp_port, target_index
            )
        )


def get_inbetween_plugs(blendshape_node, index):
    """
    Get all inbetween plug numbers from given target index.

    Args:
        blendshape_node(str): Blendshape node name.
        index(int): The target index.

    Result:
        List: [{port_index: inbetween_name},{5250: "test_inbetween_1"}]
        [] if no inbetweens exist.

    """
    result_list = list()
    input_target_group_plug = _get_input_target_group_plug(blendshape_node)
    input_target_item_plug = input_target_group_plug.elementByLogicalIndex(
        index
    ).child(0)
    array_plug_elements_num = input_target_item_plug.numElements()
    if array_plug_elements_num > 1:
        for x in range(array_plug_elements_num):
            plug_name = (
                input_target_item_plug.elementByPhysicalIndex(x)
                .name()
                .split(".")[-1]
            )
            plug_name = plug_name.split("[")[1].split("]")[0]
            port_index = int(plug_name)
            if port_index != 6000:
                inbetween_name = get_inbetween_name_from_bshp_port(
                    blendshape_node, port_index, index
                )
                result_list.append({port_index: inbetween_name})
    return result_list


def _get_input_target_group_plug(blendshape_node):
    """
    Get the input target group plug. Where all targets are stored.

    Args:
        blendshape_node(str): Blendshape node name.

    Return:
        OpenMaya.MPlug

    """
    try:
        bshp_fn = get_blendshape_fn(blendshape_node)
        m_plug = bshp_fn.findPlug("inputTarget")
        return m_plug.elementByPhysicalIndex(0).child(0)
    except:
        return (
            pymel.core.PyNode(blendshape_node)
            .inputTarget.inputTarget[0]
            .inputTargetGroup.__apimplug__()
        )


def _get_input_target_array_plug_count(blendshape_node):
    """
    Get the target count by the indices of the array plug on the node.

    Args:
        blendshape_node(str): Blendshape node name.

    Return:
        Integer: Count of the plugs.

    """
    input_target_group_plug = _get_input_target_group_plug(blendshape_node)
    m_int_array = OpenMaya.MIntArray()
    return input_target_group_plug.getExistingArrayAttributeIndices(m_int_array)


def get_targets_and_inbetweens_deltas_from_blendshape(
    blendshape_node, as_MObjects=True
):
    """
    Get all deltas of the all inbetweens and targets from given blendshape node.

    Args:
        blendshape_node(str): Blendshape node name.
        as_MObjects(bool): Get the targets and inbetween deltas as
                           OpenMaya.MObject. This is really fast if you stay
                           in the maya_utils session. And do not use the data for
                           an export. Default is True

    Return:
          List: Filled with a multidimensional dict for each target.
          [{"target_name": string,
            "target_index": Integer,
            "target_deltas": {"target_points": points position array
                              or OpenMaya.MObject,
                              "target_components": affected component array
                              or OpenMaya.MObject}
            "inbetween_deltas": [{bshp_port:
                                 {"target_points": points position array or
                                 OpenMaya.MObject,
                                 "target_components": affected component
                                 array or OpenMaya.MObject, "name": String,
                                 "weight": float},
                                 ]

    """
    target_deltas_list = list()
    index_array = get_weight_indexes(blendshape_node)
    for index in index_array:
        target_temp_dict = dict()
        inbetween_temp_list = list()

        if as_MObjects:
            (
                target_temp_dict["target_points"],
                target_temp_dict["target_components"],
            ) = OM_get_blendshape_deltas_from_index(blendshape_node, index)
        else:
            (
                target_temp_dict["target_points"],
                target_temp_dict["target_components"],
            ) = get_blendshape_deltas_from_index(blendshape_node, index)

        inbetween_plugs = get_inbetween_plugs(blendshape_node, index)
        if inbetween_plugs:
            for inbetween_dict in inbetween_plugs:
                port_index = list(inbetween_dict.keys())[0]
                name = get_inbetween_name_from_bshp_port(
                    blendshape_node, port_index, index
                )
                weight = get_weight_from_inbetween_plug_index(port_index)
                inbetween_temp_dict = dict()
                if as_MObjects:
                    (
                        inbetween_temp_dict["target_points"],
                        inbetween_temp_dict["target_components"],
                    ) = OM_get_blendshape_deltas_from_index(
                        blendshape_node, index, port_index
                    )
                else:
                    (
                        inbetween_temp_dict["target_points"],
                        inbetween_temp_dict["target_components"],
                    ) = get_blendshape_deltas_from_index(
                        blendshape_node, index, port_index
                    )
                inbetween_temp_dict["name"] = name
                inbetween_temp_dict["weight"] = weight
                inbetween_temp_list.append({port_index: inbetween_temp_dict})
        target_deltas_list.append(
            {
                "target_name": get_weight_name_from_index(
                    blendshape_node, index, True
                ),
                "target_index": index,
                "target_deltas": target_temp_dict,
                "inbetween_deltas": inbetween_temp_list,
            }
        )
    return target_deltas_list


def get_blendshape_data(
    blendshape_node,
    target_deltas=True,
    deltas_as_MObjects=True,
    mesh_data=True,
    weight_driver_node_data=True,
):
    """
    Get all needed data from given blendshape node.

    Args:
        blendshape_node(str): Blendshape node name.
        target_deltas(bool): Get target deltas or not. Default is True.
        deltas_as_MObjects(bool): Get target deltas as OpenMaya.MObject.
                                  Default is True.
        mesh_data(bool): Get mesh data or not.
        weight_driver_node_data(bool): Get weight driver nodes data.

    Return:
        Dict:
        {
        "blendshape_node_info": {
                                "name": blendshape_node,
                                "history_location":
                                blendshape_fn.historyLocation(),
                                "origin": blendshape_fn.origin(),
                                },
        "mesh_data": {
                    "mesh_shape": string
                    "num_vertices": integer,
                    "num_polys": integer,
                    "poly_vertex_id_list": List with each vertex ID of
                                           each vertex ordered by all polys,
                    "verts_ws_pos_list": List of all worldspace postions
                                         of each vertex of the mesh.
                    },
        "weight_driver_nodes_data": [
                                     ((node_name, node_plug_name), weight_name),
                                     ((node_name, node_plug_name), weight_name)
                                     ]
        "target_deltas": List
        }

    """
    data_dict = dict()
    base_obj = get_base_objects(blendshape_node)[0]

    if mesh_data:
        data_dict["mesh_data"] = mesh_utils.get_mesh_data(base_obj)
    data_dict["blendshape_node_info"] = get_blendshape_node_infos(
        blendshape_node
    )

    if weight_driver_node_data:
        data_dict["weight_driver_nodes_data"] = get_weights_drivers_data(
            blendshape_node
        )
    data_dict["target_deltas"] = None
    if target_deltas:
        data_dict[
            "target_deltas"
        ] = get_targets_and_inbetweens_deltas_from_blendshape(
            blendshape_node, deltas_as_MObjects
        )
    return data_dict


def get_blendshape_data_from_directory(directory):
    """
    Get blendshape data dict from json file in given directory.

    Args:
        directory(str): Blendshape data root directory.

    Return:
        Dict: Found blendshape data dict.
        IOError if fail.

    """
    normalized_dir = os.path.normpath(directory)

    if not os.path.exists(normalized_dir):
        raise IOError(
            f"Can not find blendshape data json. {directory} not exist."
        )

    json_file_path = os.path.join(
        normalized_dir,
        f"*_{BLENDSHAPE_DATA_JSON_FILE_NAME_PATTERN}.json",
    )

    try:
        json_data_file = glob.glob(json_file_path)[-1]

    except:
        raise IOError(
            f"Can not find json file with this pattern: {json_file_path}"
        )

    with open(json_data_file, "r") as json_file:
        blendshape_data_dict = json.load(json_file)
        return blendshape_data_dict


@DECORATORS.x_timer
def save_deltas_as_numpy_arrays(
    blendshape_node, save_directory, file_prefix=None
):
    """
    Save the target and inbetween deltas as numpy array zip file.

    Directory order is:
        - blendshape_name
            - targets_deltas
                - {file_prefix}_deltas_{target_index}.npz
            - inbetween_deltas
                - {file_prefix}_inbetween_deltas_{target_index}.npz

    Args:
        blendshape_node(str): Blendshape node name.
        save_directory(str): The directory to save the files into.
        file_prefix(str): Optional prefix for the files. If None will take the
                          blendshape name. Default is None.

    Return:
        List:
            [
            {
                "inbetween_deltas": [
                    {
                        "5542": "blendShape1_inbetween_deltas_0_5542.npz"
                    }
                ],
                "target_deltas": "blendShape1_deltas_0.npz",
                "target_index": 0,
                "target_name": "pSphere2"
            },
            {
                "inbetween_deltas": [],
                "target_deltas": "blendShape1_deltas_1.npz",
                "target_index": 1,
                "target_name": "pSphere3"
            }
            ]

    """
    if not file_prefix:
        file_prefix = blendshape_node

    blendshape_data_list_temp = (
        get_targets_and_inbetweens_deltas_from_blendshape(
            blendshape_node, False
        )
    )
    deltas_package_dir = os.path.normpath(
        os.path.join(save_directory, "targets_deltas")
    )
    inbetween_deltas_package_dir = os.path.normpath(
        os.path.join(save_directory, "inbetween_deltas")
    )
    # first we care about the target deltas
    if not os.path.exists(deltas_package_dir):
        os.mkdir(deltas_package_dir)


    for delta_dict in blendshape_data_list_temp:

        file_name = f"{file_prefix}_deltas_{delta_dict['target_index']}"

        target_points_list = delta_dict.get("target_deltas").get(
            "target_points"
        )
        target_components_list = delta_dict.get("target_deltas").get(
            "target_components"
        )

        target_points_list_npy_array = numpy.array(
            target_points_list, dtype=object
        )

        target_components_list_npy_array = numpy.array(
            target_components_list, dtype=object
        )

        deltas_npy_array_dir = os.path.normpath(
            f"{deltas_package_dir}/{file_name}"
        )

        numpy.savez_compressed(
            deltas_npy_array_dir,
            points=target_points_list_npy_array,
            components=target_components_list_npy_array,
        )

        delta_dict["target_deltas"] = f"{file_name}.npz"

    # Second we care about the inbetween deltas.
    if not os.path.exists(inbetween_deltas_package_dir):
        os.mkdir(inbetween_deltas_package_dir)

    for delta_dict_ in blendshape_data_list_temp:
        inbetweens_list = delta_dict_.get("inbetween_deltas")

        if inbetweens_list:
            for inb_dict in inbetweens_list:
                port_index = list(inb_dict.keys())[0]

                file_name_ = f"{file_prefix}_inbetween_deltas_{delta_dict_['target_index']}_{port_index}"

                inb_deltas_dict = inb_dict.get(port_index)
                inbetween_points_list = inb_deltas_dict.get("target_points")

                inbetween_components_list = inb_deltas_dict.get(
                    "target_components"
                )
                inbetween_points_list_npy_array = numpy.array(
                    inbetween_points_list, dtype=object
                )
                inbetween_components_list_npy_array = numpy.array(
                    inbetween_components_list, dtype=object
                )
                inb_deltas_npy_array_dir = os.path.normpath(f"{inbetween_deltas_package_dir}/{file_name_}")

                numpy.savez_compressed(
                    inb_deltas_npy_array_dir,
                    points=inbetween_points_list_npy_array,
                    components=inbetween_components_list_npy_array,
                )

                inb_deltas_dict["target_points"] = f"{file_name_}.npz"

                inb_deltas_dict["target_components"] = f"{file_name_}.npz"

    return blendshape_data_list_temp


@DECORATORS.x_timer
def save_deltas_as_shp_file(blendshape_node,
                            save_directory,
                            file_prefix=None
                            ):
    """
    Save deltas as maya_utils ./shp file. That's very fast but has not a good
    inbetween support.

    Args:
        blendshape_node(str): Blendshape node name.
        save_directory(str): The directory to save the files into.
        file_prefix(str): Optional prefix for the name. If None will take the
                          blendshape name. Default is None.

    Return:
        String: The file directory.

    """
    if not file_prefix:
        file_prefix = blendshape_node
    deltas_package_dir = os.path.normpath(
        os.path.join(save_directory, "targets_deltas")
    )
    if not os.path.exists(deltas_package_dir):
        os.mkdir(deltas_package_dir)

    shp_file_path = os.path.normpath(f"{deltas_package_dir}/{file_prefix}.shp")

    cmds.blendShape(blendshape_node, ep=shp_file_path, edit=True)
    return shp_file_path


def save_blendshape_setup(
    blendshape_node, save_directory, file_prefix=None, as_shp_file=False
):
    """
    Save the blendshape data into directory for further usage.
    You can save the data as numpy array or as ./shp file. Default is numpy.

    Args:
        blendshape_node(str): Blendshape node name.
        save_directory(str): The directory to save the files into.
        file_prefix(str): Optional prefix for the name. If None will take the
                          blendshape name. Default is None.
        as_shp_file(bool): Will save the target deltas as shp file.

    Returns:
        True if successfully.
        Raise exceptions.BlendshapeError if failing.

    """

    io_manager = version_io.ImportExport(abstraction_layers=2)

    if not file_prefix:
        file_prefix = blendshape_node

    bshp_data = get_blendshape_data(
        blendshape_node, False, weight_driver_node_data=False
    )

    if not os.path.exists(save_directory):
        _LOGGER.warning(
            f"{save_directory} not exist. Can not save data json file."
        )
        return False

    package_dir = os.path.normpath(os.path.join(save_directory, file_prefix))

    if not os.path.exists(package_dir):
        os.mkdir(package_dir)

    if not as_shp_file:

        history_location = bshp_data.get("blendshape_node_info").get(
            "history_location"
        )

        blendshape_nd_name = bshp_data.get("blendshape_node_info").get("name")
        if not history_location == 0:
            raise exceptions.BlendshapeError(
                "Deformation order {} for {} not supported yet."
                " Pls use the as_shp_file argument and save data as .shp file."
                " But be aware that inbetweens names are not correctly supported "
                "as .shp file".format(history_location, blendshape_nd_name)
            )

    base_obj = get_base_objects(blendshape_node)[0]

    mesh_data_dict = bshp_data.get("mesh_data")
    base_obj_export_name = "{}_base_geo".format(file_prefix)
    bshp_data["base_obj_export"] = "{}.mb".format(base_obj_export_name)
    base_obj_export_dir = os.path.normpath(
        "{}/{}".format(package_dir, base_obj_export_name)
    )

    print("base_obj: ", base_obj, "type: ", type(base_obj))

    temp_dupl = pymel.core.duplicate(base_obj.fullPathName(), n=base_obj_export_name)[0]
    dag_utils.delete_hidden_shapes(temp_dupl)
    pymel.core.parent(temp_dupl, None)
    pymel.core.select(temp_dupl)
    scene_utils.delete_unkown_plugins()
    scene_utils.delete_unkown_nodes()

    pymel.core.exportSelected(
        base_obj_export_dir,
        constructionHistory=False,
        force=True,
        channels=False,
        constraints=False,
        expressions=False,
        shader=False,
        preserveReferences=False,
        type="mayaBinary",
    )
    pymel.core.delete(temp_dupl)

    bshp_data["mesh_data"] = {
        "mesh_shape": mesh_data_dict.get("mesh_shape"),
        "mesh_data_file": mesh_utils.save_mesh_data(
            file_prefix, package_dir, mesh_data_dict
        ),
    }

    if not as_shp_file:
        bshp_data["target_deltas"] = save_deltas_as_numpy_arrays(
            blendshape_node, package_dir, file_prefix
        )
    else:
        bshp_data["target_deltas"] = os.path.basename(
            save_deltas_as_shp_file(blendshape_node, package_dir, file_prefix)
        )

    json_file_dir = os.path.normpath(
        "{}/{}_{}.json".format(
            package_dir, file_prefix, BLENDSHAPE_DATA_JSON_FILE_NAME_PATTERN
        )
    )

    weight_driver_nodes_export_data = (
        _processing_weight_driver_nodes_data_for_export(
            blendshape_node, package_dir, file_prefix
        )
    )

    if weight_driver_nodes_export_data:
        bshp_data["weight_driver_nodes_export_file"] = os.path.basename(
            weight_driver_nodes_export_data[0]
        )

        bshp_data["weight_driver_nodes_data"] = weight_driver_nodes_export_data[
            1
        ]

    with open(json_file_dir, "w") as json_file:
        json.dump(bshp_data, json_file, sort_keys=True, indent=4)
    _LOGGER.info("Blendshape data saved to: {}".format(package_dir))
    # IF WE PLUG IN HERE; IT WILL BE GOODER
    """
       Parameters:
            string      object_name     : The name of the object to export. This name also serves as the folder name. Multiple files can be saved within this folder if used multiple times.
            string      data_type       : The type of data to save. Choosing this parameter will also trigger the export process automatically. Refer to the main documentation for more details.
            any         data_to_write   : This parameter is used only when the type of file to be saved involves a data type storable in a variable.
            string      node_to_export  : If you want to export a specific node rather than a variable. If not provided, it defaults to the value of object_name.
            string      data_category   : The data category is typically determined automatically by the script (_FILE_TRANSLATOR). However, you can specify a different category if needed.
            string      data_file_name  : The desired name for the file. If not specified, the file name will default to the object name with the appropriate extension. Custom names are permissible.
            int         version         : Specifies the version to export. Typically, this will be -1 to denote the latest or a newly created version.
            str/bool    as_path         : If set to true, returns only the path components (version_path, data_file_name, data_type). If set to "full", returns the full path.
            string      receiver_node   : If you want to import data related to a specific node rather than a variable. If not provided, it defaults to the value of object_name.
        
        
            :param object_name: The name of the object to import. This name also serves as the folder name. Multiple files can be retrieved from this folder if used multiple times.
            :param data_type: The type of data to retrieve. Selecting this parameter will also trigger the import process automatically. Refer to the main documentation for more details.
            :string receiver_node: If you want to import data related to a specific node rather than a variable. If not provided, it defaults to the value of object_name.
            :param data_category: The data category is typically determined automatically by the script (_FILE_TRANSLATOR). However, you can specify a different category if needed.
            :param data_file_name: The desired name for the file. If not specified, the file name will default to the object name with the appropriate extension. Custom names are permissible.
            :param version: Specifies the version to import. Typically, this will be -1 to denote the latest or most recent version.
            :param as_path: If 'full', returns the full path of the data file. If True, returns only the path components (version_path, data_file_name, data_type).

    """
    io_manager.write(
        object_name=base_obj.partialPathName(),
        data_type="mb",
        data_file_name="base_object"
    )

    io_manager.write(
        object_name=base_obj.partialPathName(),
        data_to_write=bshp_data,
        data_type="json",
        data_file_name="bshp_data"
    )

    return True


def build_blendshape_setup(
    target, blendshape_data, blendshape_name=False, OM_deltas=True
):
    """
    Build the blendshape setup for given target mesh.

    Args:
        target(str, pymel.core.PyNode()): The transform node of the geo for
                                          the blendshape node.
        blendshape_data(dict): The blendshape data dict for the build.
        blendshape_name(str): The blendshape node name. If False will take
                              name from blendshape_data. Default is False.
        OM_deltas(bool): Set the target deltas with OpenMaya.MObject.

    """
    if not blendshape_name:
        blendshape_name = "{}_new".format(
            blendshape_data.get("blendshape_node_info").get("name")
        )
    target_names_list = [
        target_dict.get("target_name")
        for target_dict in blendshape_data.get("target_deltas")
    ]
    inbetween_list = [
        target_dict.get("inbetween_deltas")
        for target_dict in blendshape_data.get("target_deltas")
    ]
    create_blendshape_node(
        target,
        blendshape_name,
        blendshape_data.get("blendshape_node_info").get("origin"),
        blendshape_data.get("blendshape_node_info").get("history_location"),
        target_names_list,
        inbetween_list,
        blendshape_data.get("blendshape_node_info").get("topologyCheck"),
    )
    for index, target_dict in enumerate(blendshape_data.get("target_deltas")):
        # First we set the target deltas.
        if OM_deltas:
            OM_set_blendshape_deltas_by_index(
                blendshape_name,
                index,
                (
                    target_dict.get("target_deltas").get("target_points"),
                    target_dict.get("target_deltas").get("target_components"),
                ),
            )
        else:
            set_blendshape_deltas_by_index(
                blendshape_name,
                index,
                (
                    target_dict.get("target_deltas").get("target_points"),
                    target_dict.get("target_deltas").get("target_components"),
                ),
            )
        # Second the inbetween deltas
        inbetween_deltas = target_dict.get("inbetween_deltas")
        for inbetween_dict in inbetween_deltas:
            items = list(inbetween_dict.items())
            for item in items:
                if OM_deltas:
                    OM_set_blendshape_deltas_by_index(
                        blendshape_name,
                        index,
                        (
                            item[1].get("target_points"),
                            item[1].get("target_components"),
                        ),
                        item[0],
                    )
                else:
                    set_blendshape_deltas_by_index(
                        blendshape_name,
                        index,
                        (
                            item[1].get("target_points"),
                            item[1].get("target_components"),
                        ),
                        item[0],
                    )


def validate_blendshape_weight_driver_node(node):
    """
    Validate the blendshape weight driver nodes. If we support the nodeType.

    Args:
        node(pymel.core.PyNode()): Node to validate.

    Return:
        pymel.core.PyNode(): If node is valid.
        BlendShapeWeightDriverError if fail.

    """
    node_type = node.nodeType()
    if node_type not in VALID_WEIGHT_DRIVER_NODETYPES:
        raise exceptions.BlendShapeWeightDriverError(
            f"Given node {node} is not a valid blendshape weight driver node."
        )
    return node_type


@DECORATORS.disable_node_editor_update()
@DECORATORS.disable_isolate_select_update()
@DECORATORS.refresh_suspended()
def transfer_blendshape_setup(
    source: str,
    target: str,
    validate_meshes: bool = True,
    disconnect_source_blendshape_ports: bool = False,
    info_box: bool = False,
    force_rebuild_deltas: bool = False,
    smooth_new_deltas_value: float = 2,
):
    """
    Transfer a blendshape setup from source to target.

    Args:
        source(str): The source transform node.
        target(str): The target transform node.
        validate_meshes(bool): Enable/Disable mesh validation before transfer.
                              This makes sure that your transfer result is
                              not problematic. Default is True.
        disconnect_source_blendshape_ports(bool): Enable if you want to
                                                  disconnect the weight
                                                  ports of the source
                                                  blendshape node.
        info_box(bool): Enable a info box in maya as user feedback when
                        we make a automatic transfer.
                        Default is False.

        force_rebuild_deltas (bool): Forces the deltas to be rebuilt.

        smooth_new_deltas_value (float): Delta Mush smooting iterations.

    Return:
        pymel.core.PyNode (target_blendshape_node): The new Blendshape.

    """

    target_blendshape_node = None

    disconnected_source_weights = False
    keep_compare_mesh = False
    validation_result = True
    source_blendshape_nodes = get_blendshape_nodes(source)

    if force_rebuild_deltas:
        validation_result = False
        validate_meshes = False
        info_box = False
        smooth_new_deltas_value = 0

    if len(source_blendshape_nodes) > 1:
        _LOGGER.warning(
            "Source has more then one blendshape."
            " Transfer of multiple blendshape"
            " setups not supported yet."
            " Will just take top one in the stack."
        )

    try:
        source_blendshape_node = source_blendshape_nodes[0]
    except:
        raise exceptions.MayaNodeNotFound(
            "Source node has no blendshape in deformer stack."
        )
    weight_driver_nodes_data = get_weights_drivers_data(source_blendshape_node)

    if validate_meshes:
        validation_result = mesh_utils.validate_meshes(source, target)

    if not validation_result:
        if info_box:
            transfer_confirm = pymel.core.confirmDialog(
                title="Mesh validation check",
                message="The blendshape target mesh seems not to be the"
                " same like the source mesh. Choose an action.",
                button=[
                    "Force delta transfer",
                    "Abort",
                    "Auto generate new deltas",
                ],
                defaultButton="Force delta transfer",
                cancelButton="Abort",
                dismissString="Abort",
                icon="warning"
            )
            if transfer_confirm == "Abort":
                return
            elif transfer_confirm == "Force delta transfer":
                validation_result = True
            else:
                validation_result = False
    if validation_result:
        source_blendshape_nd_name = get_blendshape_nodes(source)[0]
        source_blendshape_data = get_blendshape_data(
            source_blendshape_nd_name, mesh_data=False
        )
        build_blendshape_setup(target, source_blendshape_data)
    else:
        if info_box:
            keep_compare_mesh = pymel.core.confirmBox(
                "Blendshape target transfer.",
                "Do you want to keep the extracted shapes and"
                " the compare mesh in the scene?",
            )
        _LOGGER.warning(
            "Source and target mesh not valid to each other."
            "Will try automatic blendshape data transfer"
        )
        if weight_driver_nodes_data:
            disconnect_all_weight_values(source_blendshape_node)
            disconnected_source_weights = True
        transfer_blendshape_deltas(
            source, target, smooth_new_deltas_value, keep_compare_mesh
        )
    target_blendshape_node = get_blendshape_nodes(target)[-1]

    # This line needs improvement because i causes issues with stacked blendshape node
    # It finds sometimes the wrong blendshape node and then it will not reconnect the blendshapes targets
    # from the source after the transfer.
    source_blendshape_node = get_blendshape_nodes(source)[-1]

    if weight_driver_nodes_data:
        rebuild_weight_driver_nodes_graph(
            weight_driver_nodes_data,
            False,
            source_blendshape_node,
            target_blendshape_node,
            disconnect_source_blendshape_ports,
        )
    if disconnected_source_weights:
        if not disconnect_source_blendshape_ports:
            rebuild_weight_driver_nodes_graph(
                weight_driver_nodes_data,
                False,
                target_blendshape_node,
                source_blendshape_node
            )
    _LOGGER.info(
        "Blendshape setup transferred from {0} to {1}".format(source, target)
    )
    if target_blendshape_node and pmc.objExists(target_blendshape_node):
        return pmc.PyNode(target_blendshape_node)

    return


def import_blendshape_data(directory, target_shape=None):
    """
    Import blendshape data from given directory.

    Args:
        directory(str): Setup directory.
        target_shape(pmc.PyNode): The target mesh shape node.

    """
    normalized_dir = os.path.normpath(directory)

    blendshape_data_dict = get_blendshape_data_from_directory(directory)
    target_deltas_dir = os.path.normpath(
        os.path.join(normalized_dir, "targets_deltas")
    )
    inbetweens_deltas_dir = os.path.normpath(
        os.path.join(normalized_dir, "inbetween_deltas")
    )
    if not os.path.exists(target_deltas_dir):
        raise OSError("Directory not exist: {}".format(target_deltas_dir))
    if not target_shape:
        target_shape = pymel.core.PyNode(
            blendshape_data_dict.get("mesh_data").get("mesh_shape")
        )
    if isinstance(blendshape_data_dict.get("target_deltas"), list):
        for delta_data_dict in blendshape_data_dict.get("target_deltas"):
            npy_file = os.path.normpath(
                os.path.join(
                    target_deltas_dir, delta_data_dict.get("target_deltas")
                )
            )
            np_data = numpy.load(npy_file, allow_pickle=True)
            target_points = np_data["points"]
            target_points = target_points.tolist()
            target_components = np_data["components"].tolist()
            np_data.close()
            delta_data_dict["target_deltas"] = {
                "target_points": target_points,
                "target_components": target_components,
            }
            if delta_data_dict.get("inbetween_deltas"):
                for inbetween_data_dict in delta_data_dict.get(
                    "inbetween_deltas"
                ):
                    items = list(inbetween_data_dict.items())
                    for item in items:
                        inb_npy_file = os.path.normpath(
                            os.path.join(
                                inbetweens_deltas_dir,
                                item[1].get("target_points"),
                            )
                        )
                        inb_np_data = numpy.load(
                            inb_npy_file, allow_pickle=True
                        )
                        item[1]["target_points"] = inb_np_data[
                            "points"
                        ].tolist()
                        item[1]["target_components"] = inb_np_data[
                            "components"
                        ].tolist()
                        inb_np_data.close()
        build_blendshape_setup(
            target_shape.getTransform().name(),
            blendshape_data_dict,
            blendshape_data_dict.get("blendshape_node_info").get("name"),
            False,
        )
        _LOGGER.info(
            "Blendshape setup build with numpy arrays from {}.".format(
                target_deltas_dir
            )
        )
    else:
        shp_file = os.path.normpath(
            os.path.join(
                normalized_dir,
                "targets_deltas",
                blendshape_data_dict.get("target_deltas"),
            )
        )
        create_blendshape_node(
            target_shape.getTransform().name(),
            blendshape_data_dict.get("blendshape_node_info").get("name"),
            blendshape_data_dict.get("blendshape_node_info").get("origin"),
            blendshape_data_dict.get("blendshape_node_info").get(
                "history_location"
            ),
            topologyCheck=blendshape_data_dict.get("blendshape_node_info").get(
                "topologyCheck"
            ),
        )
        pymel.core.PyNode(
            blendshape_data_dict.get("blendshape_node_info").get("name")
        ).ip(shp_file)
        _LOGGER.info(
            "Blendshape setup build with '.shp' file from {}.".format(shp_file)
        )


def import_blendshape_setup(directory, validate_meshes=True, info_box=False):
    """
    Import blendshape setup from given directory.

    Args:
        directory(str): Setup directory.
        validate_meshes(bool): Enable/Disable mesh validation before import.
                              This makes sure that your import result is
                              not problematic.
                              Default is True.
        info_box(bool): Enable an info box in maya as user feedback when
                        we make an automatic transfer.
                        Default is False.

    """
    keep_compare_mesh = False
    validation_result = True
    normalized_dir = os.path.normpath(directory)
    blendshape_data_dict = get_blendshape_data_from_directory(directory)
    temp_import = []
    compare_mesh_shape = []
    compare_mesh_trs = []
    mesh_shape = "None"
    if validate_meshes:
        _LOGGER.info("Start mesh validation.")
        mesh_trs = pymel.core.PyNode(
            blendshape_data_dict.get("mesh_data").get("mesh_shape")
        ).getTransform()
        mesh_shape = mesh_trs.getShape().name()
        base_geo_path = os.path.normpath(
            os.path.join(
                normalized_dir,
                blendshape_data_dict.get("base_obj_export"),
            )
        )
        temp_import = pymel.core.importFile(base_geo_path, returnNewNodes=True)
        compare_mesh_shape = [
            node for node in temp_import if node.nodeType() == "mesh"
        ][0]
        compare_mesh_trs = compare_mesh_shape.getTransform()
        validation_result = mesh_utils.validate_meshes(
            compare_mesh_trs,
            mesh_shape,
        )
        _LOGGER.info("Mesh validation finished.")
    if not validation_result:
        if info_box:
            transfer_confirm = pymel.core.confirmDialog(
                title="Mesh validation check",
                message="The blendshape target mesh [{}] seems not to be the"
                " same like the exported version. Choose an action.".format(
                    mesh_shape
                ),
                button=[
                    "Force delta import",
                    "Abort",
                    "Auto generate new deltas",
                ],
                defaultButton="Force delta import",
                cancelButton="Abort",
                dismissString="Abort",
                icon="warning"
            )
            if transfer_confirm == "Abort":
                pymel.core.delete(temp_import)
                return
            elif transfer_confirm == "Force delta import":
                validation_result = True
            else:
                validation_result = False
    if not validation_result:
        if info_box:
            keep_compare_mesh = pymel.core.confirmBox(
                "Blendshape target transfer.",
                "Do you want to keep the extracted shapes and"
                " the compare mesh in the scene?",
            )
        _LOGGER.warning(
            "Mesh for blendshape data import is not valid."
            " Will try automatic blendshape data transfer."
        )
        orig_shape_name = blendshape_data_dict.get("mesh_data").get(
            "mesh_shape"
        )
        base_geo = pymel.core.PyNode(orig_shape_name)
        base_geo_trs = base_geo.getTransform()
        base_geo_trs_renamed = False
        try:
            base_geo_trs.rename("{}_temp".format(base_geo_trs.name()))
            base_geo_trs_renamed = True
        except:
            _LOGGER.info(
                "Base geo is a reference or a locked node. Unable to rename before transfer."
            )
        import_blendshape_data(directory, compare_mesh_shape)
        transfer_blendshape_deltas(
            compare_mesh_trs,
            base_geo_trs,
            keep_transfer_meshes=keep_compare_mesh,
        )

        if base_geo_trs_renamed:
            base_geo_trs.rename(base_geo_trs.name().replace("_temp", ""))
    if validation_result:
        import_blendshape_data(directory)
    if blendshape_data_dict.get(
        "weight_driver_nodes_data"
    ) and blendshape_data_dict.get("weight_driver_nodes_export_file"):
        weight_driver_nodes_data = blendshape_data_dict.get(
            "weight_driver_nodes_data"
        )
        weight_driver_nodes_file_path = os.path.join(
            normalized_dir,
            blendshape_data_dict.get("weight_driver_nodes_export_file"),
        )
        _import_and_connect_weightdrivers(
            weight_driver_nodes_file_path, weight_driver_nodes_data
        )
    if not keep_compare_mesh:
        pymel.core.delete(compare_mesh_trs)

def _clear_scene_from_weightdriver_nodes(directory):
    """
    Will clear the scene from preexisting weight driver nodes.

    Args:
        directory(str): Setup directory.

    """
    blendshape_data_dict = get_blendshape_data_from_directory(directory)
    weight_driver_nodes_data = None
    if blendshape_data_dict.get(
        "weight_driver_nodes_data"
    ) and blendshape_data_dict.get("weight_driver_nodes_export_file"):
        weight_driver_nodes_data = blendshape_data_dict.get(
            "weight_driver_nodes_data"
        )
    if weight_driver_nodes_data:
        for data_dict in weight_driver_nodes_data:

            if data_dict.get("orig_name"):
                if data_dict["node_type"] != "transform":
                    try:
                        pymel.core.delete(data_dict.get("orig_name"))
                    except:
                        pass

            if data_dict.get("node"):
                if data_dict["node_type"] != "transform":
                    try:
                        pymel.core.delete(data_dict.get("node"))
                    except:
                        continue


def _import_and_connect_weightdrivers(
    weight_driver_node_file_path, weight_driver_nodes_data
):
    """
    Import and connect the weightdrivers.

    Args:
        weight_driver_node_file_path(str): The path to exported weightdriver nodes.
        weight_driver_nodes_data(dict): The weightdriver nodes data for the reparenting and reconnecting.

    """
    # Here we import the weightdriver nodes.
    pymel.core.importFile(weight_driver_node_file_path)

    # Here we rebuild the whole driver graph. Be aware that the imported nodes has a new prefix
    # which is defined in the module var WEIGHT_DRIVER_DUPLICATE_PREFIX. So the nodes are always
    # unique at the import state.
    rebuild_weight_driver_nodes_graph(weight_driver_nodes_data)
    # Rebuild the parent relationships
    reparent_weight_driver_nodes(weight_driver_nodes_data)
    # Clean the scene from unnessecary node duplicates and connections.
    _clean_and_remap_weight_driver_nodes(weight_driver_nodes_data)


def _clean_and_remap_weight_driver_nodes(weight_driver_nodes_data_list):
    """
    Here we try to make a clean node tree. We check if the original node driver node exist.
    If it exists we will remap the connections from the duplicate to original node and delete the duplicate.
    If just the duplicate exist we will take the duplicate keep the connections and rename it to the original name.

    Args:
        weight_driver_nodes_data_list(list): List filled with weight driver
                                             node data dict for each
                                             weight driver node.
    """
    print("THIS IS THE KILLING FUNCTION")

    delete_list = []
    connect_list = []
    rename_list = []

    # we fill our list for a later do it section
    for data_dict in weight_driver_nodes_data_list:
        destinations = data_dict["destinations"]
        _orig_name = data_dict.get("orig_name")

        if not _orig_name:
            continue

        try:
            orig_nd = pymel.core.PyNode(data_dict.get("orig_name"))

        except pymel.core.general.MayaNodeError:
            orig_nd = False

        try:
            dup_node = pymel.core.PyNode(data_dict.get("node"))

        except pymel.core.general.MayaNodeError:
            dup_node = False

        # If the orig node and duplicated node from import coexist in the scene.
        # We place the node duplicate in the delete list.
        if orig_nd and dup_node:
            # We create a remapped attribute connection if the orig node
            # exist and place it as tuple in connect list.
            for port_list in destinations:
                try:
                    source_port = pymel.core.PyNode(
                        port_list[0].replace(
                            data_dict.get("node"),
                            data_dict.get("orig_name"),
                        )
                    )
                except:
                    source_port = None
                try:
                    dest_port = pymel.core.PyNode(port_list[1])
                except:
                    dest_port = None
                connect_list.append((source_port, dest_port))
            if hasattr(dup_node, "getTransform"):
                trs = dup_node.getTransform()
                if trs:
                    delete_list.append(trs)
            else:
                delete_list.append(dup_node)
            # # If the driver node is a SHAPE weightdriver we add the driver matrix locator to the delete list.
            if data_dict["node_type"] == "weightDriver":
                try:
                    vector_angle_driver_loc = pymel.core.PyNode(
                        data_dict["vector_angle_driver_loc"]
                    )
                    delete_list.append(vector_angle_driver_loc)
                except:
                    continue
        if dup_node and not orig_nd:
            rename_list.append((dup_node, data_dict.get("orig_name")))
            if data_dict["node_type"] == "weightDriver":
                try:
                    vector_angle_driver_loc = pymel.core.PyNode(
                        data_dict["vector_angle_driver_loc"]
                    )
                    rename_list.append(
                        (
                            vector_angle_driver_loc,
                            data_dict.get("vector_angle_driver_loc_orig_name"),
                        )
                    )
                except:
                    continue

    # This is the do it section where we delete the duplicates,
    # remap connections and rename duplicates to orig names.
    print("DELETE LIST: ", delete_list)
    if delete_list:
        _LOGGER.info("PROCESSING: Weightdriver duplicates killing.")

        delete_list = list(set(delete_list))
        pymel.core.delete(delete_list)

        _LOGGER.info(
            "Delete driver node duplicates if orig driver nodes already exists."
        )
    print("CONNECT LIST: ", connect_list)

    if connect_list:
        _LOGGER.info("PROCESSING: Connection remapping.")
        connect_list = list(set(connect_list))
        for source_port, dest_port in connect_list:
            if source_port and dest_port:
                if not source_port.isConnectedTo(dest_port):
                    source_port.connect(dest_port, f=True)
        _LOGGER.info("Remap connections from driver nodes duplicates to origin driver nodes.")

    print("RENAME LIST: ", rename_list)

    if rename_list:
        _LOGGER.info("PROCESSING: Weight driver duplicates.")
        rename_list = list(set(rename_list))
        renamed_list = []

        for rm_nd, orig_name in rename_list:
            if not pymel.core.objExists(rm_nd):
                continue

            renamed_list.append(rm_nd)
            rm_nd.rename(orig_name)
            rm_nd = pymel.core.PyNode(orig_name)

            if not hasattr(rm_nd, "getTransform"):
                continue

            trs = rm_nd.getTransform()

            if not trs:
                continue

            shape_name = trs.getShape().name(long=None)
            trs_name = shape_name.replace("Shape", "")
            trs.rename(trs_name)

        _LOGGER.info(
            "Renamed node driver duplicates to orig name if no duplicates exist."
        )

    _LOGGER.info("Successfully cleaned weight driver nodes in scene.")
    print("KILLING FUNCTION OVER")

def transfer_blendshape_deltas(
    source_mesh, target_mesh, result_smoothing=2, keep_transfer_meshes=False,
):
    """
    Transfer the blendshape deltas from source mesh to target mesh.
    This is based on a wrap deformer and deltamush.
    This command is not undoable.

    Args:
        source_mesh(str): Name of the source mesh shape node.
        target_mesh(str): Name of the target mesh shape node.
        result_smoothing(int): This will smooth aout the results a bit. Is
                               very interesting if the target mesh has a
                               higher subdiv as the source mesh.
                               Default is 2.
        keep_transfer_meshes(bool): Keep the transfer meshes in the scene.
                                    Default is False.
        include_current_target_mesh_position: ---
    """
    target_shapes_list = []
    target_shapes_list_name = []
    inbetween_shapes_list = []

    source_trs = pymel.core.PyNode(source_mesh).getTransform()
    target_trs = pymel.core.PyNode(target_mesh).getTransform()

    shapes_extract_target = target_trs.duplicate(n="evaluation_mesh")[0]

    dag_utils.delete_hidden_shapes(shapes_extract_target)
    pymel.core.parent(shapes_extract_target, None)
    source_blendshape_fn = get_blendshape_nodes(source_mesh, as_fn=True)[0]
    source_blendshape_info_data = get_blendshape_node_infos(
        source_blendshape_fn.name()
    )
    source_blendshape_fn.setName(
        f"{source_blendshape_info_data.get('name')}_old"
    )
    source_weight_indeces = get_weight_indexes(source_blendshape_fn.name())
    wrap_deformer = rig_utils.create_wrap_deformer(
        source_trs, shapes_extract_target
    )
    delta_mush = pymel.core.deltaMush(ignoreSelected=True, si=result_smoothing)
    delta_mush.setGeometry(shapes_extract_target)
    extract_grp = pymel.core.createNode("transform", n="extracted_shapes_grp")
    for index in source_weight_indeces:
        source_blendshape_fn.setWeight(index, 1.0)
        weight_name = get_weight_name_from_index(
            source_blendshape_fn.name(), index, True
        )
        extracted_target_shape = shapes_extract_target.duplicate()[0]
        extracted_target_shape.setParent(extract_grp)
        extracted_target_shape.rename(weight_name)
        extracted_target_shape_nd = extracted_target_shape.getShape(
            noIntermediate=True
        )
        extracted_target_shape_nd.rename(weight_name)
        target_shapes_list.append(extracted_target_shape_nd.__apimobject__())
        target_shapes_list_name.append(extracted_target_shape_nd)
        source_blendshape_fn.setWeight(index, 0.0)
        inbetween_plugs_list = get_inbetween_plugs(
            source_blendshape_fn.name(), index
        )
        temp_inb_list = []
        if inbetween_plugs_list:
            for inb_dict in inbetween_plugs_list:
                port_index = list(inb_dict.keys())[0]
                inb_name = inb_dict.get(port_index)
                weight = get_weight_from_inbetween_plug_index(port_index)
                source_blendshape_fn.setWeight(index, weight)
                extract_name = "{}_{}_{}".format(weight_name, index, port_index)
                extract_inb_target_shape = shapes_extract_target.duplicate()[0]
                extract_inb_target_shape_nd = (
                    extract_inb_target_shape.getShape().rename(inb_name)
                )
                extract_inb_target_shape.setParent(extract_grp)
                extract_inb_target_shape.rename(extract_name)
                temp_inb_list.append(
                    {
                        port_index: {
                            "name": extract_inb_target_shape_nd.__apimobject__(),
                            "weight": weight,
                        }
                    }
                )
                source_blendshape_fn.setWeight(index, 0.0)
        inbetween_shapes_list.append(temp_inb_list)
    create_blendshape_node(
        target_trs,
        source_blendshape_info_data.get("name"),
        source_blendshape_info_data.get("origin"),
        source_blendshape_info_data.get("history_location"),
        target_shapes_list,
        inbetween_shapes_list,
        source_blendshape_info_data.get("topologCheck"),
    )
    if not keep_transfer_meshes:
        pymel.core.delete(
            [wrap_deformer, delta_mush, shapes_extract_target, extract_grp]
        )
    _LOGGER.info(
        "Blendshape deltas transferred from {} to {}".format(
            source_mesh, target_mesh
        )
    )


def rebuild_blendshape_setup(mesh_trs):
    """
    Rebuild the blendshape setup of given mesh.

    Args:
        mesh_trs: Mesh transform with belndshape input.

    """
    interim_mesh = mesh_trs.duplicate(n="INTERIM_MESH")[0]
    dag_utils.delete_hidden_shapes(interim_mesh)
    transfer_blendshape_setup(
        mesh_trs,
        interim_mesh,
        validate_meshes=False,
        disconnect_source_blendshape_ports=True,
    )
    old_bshp = get_blendshape_nodes(mesh_trs, as_string=True)[0]
    cmds.delete(old_bshp)
    transfer_blendshape_setup(
        interim_mesh,
        mesh_trs,
        disconnect_source_blendshape_ports=True,
        force_rebuild_deltas=True,
    )
    pymel.core.delete(interim_mesh)
    new_bshp = get_blendshape_nodes(mesh_trs, as_pynode=True)[0]
    new_bshp.rename(old_bshp)


def rebuild_weight_driver_nodes_graph(
    weight_driver_nodes_data_list,
    force=False,
    source_blendshape_node=None,
    target_blendshape_node=None,
    disconnect_source_blendshape_ports=False,
):
    """
    Rebuild weight driver graph based on a weight driver nodes data dict.

    Args:
        weight_driver_nodes_data_list(list): List filled with weight driver
                                             node data dict for each
                                             weight driver node.
        force(bool): Force the rebuild of the connections. Default is False.

        source_blendshape_node(str): The source blendshape node name.
                                     Needed if you want to transfer
                                     the connections from source to target
                                     blendshape. Default is None.

        target_blendshape_node(str): The target blendshape node name.
                                     Needed if you want to transfer
                                     the connections from source to target
                                     blendshape. Default is None.

        disconnect_source_blendshape_ports(bool): Enable if you want to
                                                  disconnect the weight
                                                  ports of the source
                                                  blendshape node.

    """

    source_connected_nodes_list = []
    dest_connected_nodes_list = []

    def __connect_nodes(connect_attr_list):
        connected_port_count = 0

        for connect_attr in connect_attr_list:
            attr_0 = pymel.core.Attribute(connect_attr[0])

            try:
                attr_1 = pymel.core.Attribute(connect_attr[1])

            except:
                _LOGGER.warning(
                    "{} not found unable to connect.".format(connect_attr[1])
                )
                continue

            if force:
                attr_0.connect(attr_1, force=True)
                connected_port_count += 1
                continue

            if not attr_1.isConnected():
                attr_0.connect(attr_1)
                connected_port_count += 1
            else:
                _LOGGER.debug(
                    "{} is already connected. Will skip this port.".format(
                        attr_1
                    )
                )
        return connected_port_count

    for data_dict in weight_driver_nodes_data_list:
        source_list = data_dict.get("source")
        destination_list = data_dict.get("destinations")
        if source_blendshape_node and target_blendshape_node:
            for attr_list in destination_list:
                if disconnect_source_blendshape_ports:
                    pymel.core.Attribute(attr_list[1]).disconnect()
                attr_list[1] = attr_list[1].replace(
                    "{}.".format(source_blendshape_node),
                    "{}.".format(target_blendshape_node),
                )
        source_connected_port_count = __connect_nodes(source_list)
        dest_connected_port_count = __connect_nodes(destination_list)
        source_connected_nodes_list.append(
            (
                data_dict.get("node"),
                "connected_ports: {}".format(source_connected_port_count),
                "ports_count: {}".format(len(source_list)),
            )
        )
        dest_connected_nodes_list.append(
            (
                data_dict.get("node"),
                "connected_ports: {}".format(dest_connected_port_count),
                "ports_count: {}".format(len(destination_list)),
            )
        )
    _LOGGER.info(
        "Weight driver node source ports reconnected:\n{}".format(
            source_connected_nodes_list
        )
    )
    _LOGGER.info(
        "Weight driver node destination ports reconnected:\n{}".format(
            dest_connected_nodes_list
        )
    )


def reparent_weight_driver_nodes(weight_driver_nodes_data_list):
    """
    Reparent weight driver nodes based on the weight driver nodes list.

    Args:
        weight_driver_nodes_data_list(list): List filled with weight driver
                                             node data dict for each
                                             weight driver node.
    """

    for data_dict in weight_driver_nodes_data_list:
        parent = data_dict.get("parent")
        vector_angle_driver_loc = data_dict.get("vector_angle_driver_loc")
        if parent:
            if data_dict.get("node_type") in VALID_WEIGHT_DRIVER_NDS_WITH_TRS:
                node = pymel.core.PyNode(data_dict.get("node"))
                trs = pymel.core.PyNode(node).getTransform()
                pymel.core.parent(trs, parent)
        if vector_angle_driver_loc:
            loc_parent = data_dict.get("vector_angle_driver_loc_parent")
            if loc_parent:
                pymel.core.parent(vector_angle_driver_loc, loc_parent)
    _LOGGER.info("Weight driver nodes reparented.")


def save_blendshape_setup_pack(
    blendshape_node_name_list, directory, as_shp_files=False
):
    """
    Save blendshape setup as pack.
    That means you can save more then one setup at once.

    Args:
        blendshape_node_name_list(list): Blendshape nodes to save
                                         as setup in the pack.
        directory(str): The save dircetory.
        as_shp_files(bool): Save blendshape deltas as .shp file.

    """
    normalized_dir = os.path.normpath(directory)
    for blendshape_node in blendshape_node_name_list:
        save_blendshape_setup(
            blendshape_node, normalized_dir, as_shp_file=as_shp_files
        )
    _LOGGER.info("Saved blendshape pack to: {}".format(normalized_dir))


def import_blendshape_setup_pack(directory, info_box=False):
    """
    Import blendshape setups from a pack directory.

    Args:
        directory(str): The save dircetory.
        info_box(bool): Enable a info box in maya as user feedback when
                        we make a automatic transfer.
                        Default is False.
    """
    normalized_dir = os.path.normpath(directory)
    dir_list = os.listdir(normalized_dir)
    for dir_ in dir_list:
        _clear_scene_from_weightdriver_nodes(os.path.join(normalized_dir, dir_))
    _LOGGER.info("Cleaned scene from preexisting weight driver nodes.")
    for dir__ in dir_list:
        import_blendshape_setup(
            os.path.join(normalized_dir, dir__), info_box=info_box,
        )
    _LOGGER.info("Imported blendshape pack from: {}".format(normalized_dir))


def save_blendshape_setup_with_version_control(
    blendshape_node_name_list, directory, as_shp_files=False
):
    """
    Save blendshape setup pack with version control. That means each pack
    Will be saved in a version folder. And you can not override a version folder.
    It will always save a new one. So we make sure we are not losing data.

    Args:
        blendshape_node_name_list(list): Blendshape nodes to save
                                         as setup in the pack.
        directory(str): The save directory.
        as_shp_files(bool): Save blendshape deltas as .shp file.

    """
    normalized_dir = os.path.normpath(directory)

    if not os.path.exists(normalized_dir):
        raise OSError(f"{normalized_dir} not exist. Abort saving.")

    get_all_versions_in_dir = glob.glob(os.path.join(directory, "v*"))

    version_number = len(get_all_versions_in_dir) + 1

    version_string = f"v{version_number:03}"

    save_dir = os.path.join(directory, version_string)

    os.mkdir(save_dir)

    save_blendshape_setup_pack(
        blendshape_node_name_list, save_dir, as_shp_files
    )


def import_blendshape_setup_with_version_control(directory, info_box=False):
    """
    Import blendshape setup pack with version control.
    That means it will always import the latest version folder
    with this name pattern: 'v***'.

    Args:
        directory(str): The import directory.
        info_box(bool): Enable an info box in maya as user feedback when
                        we make an automatic transfer.
                        Default is False.

    """

    def _sort_by_version_number(version_name):
        return int(version_name.stem.split("v")[-1])

    dir_path = pathlib.Path(directory)
    sorted_versions = sorted(dir_path.glob("v*"), key=_sort_by_version_number)

    if not sorted_versions:
        raise IOError(
            f"No blendshapes pack versions found in {directory}."
        )

    import_path = sorted_versions[-1]

    import_name = str(import_path.resolve())

    import_blendshape_setup_pack(import_name,
                                 info_box=info_box,
                                 )


def save_to_PXO_BSHP_directory(
    blendshape_node_name_list, directory, as_shp_files=False
):
    """
    Save versioned blendshape setup pack to a PXO_BSHP folder.

    Args:
        blendshape_node_name_list(list): Blendshape nodes to save
                                         as setup in the pack.
        directory(str): The save dircetory.
        as_shp_files(bool): Save blendshape deltas as .shp file.

    """

    pxo_bshp_path = os.path.normpath(
        os.path.join(
            directory,
            PXO_BSHP_DIR_NAME,
        )
    )

    if not os.path.exists(pxo_bshp_path):
        os.mkdir(pxo_bshp_path)

    save_blendshape_setup_with_version_control(
        blendshape_node_name_list, pxo_bshp_path, as_shp_files
    )


def import_from_PXO_BSHP_directory(directory, info_box=False):
    """
    Import latest versioned blendshape setup pack from PXO_BSHP directory.

    Args:
        directory(str): The import directory.
        info_box(bool): Enable a info box in maya as user feedback when
                        we make a automatic transfer.
                        Default is False.
    """
    pxo_bshp_path = os.path.normpath(
        os.path.join(
            directory,
            PXO_BSHP_DIR_NAME,
        )
    )

    if not os.path.exists(pxo_bshp_path):
        raise IOError(f"{pxo_bshp_path} not exist")

    import_blendshape_setup_with_version_control(
        pxo_bshp_path, info_box=info_box
    )

# Inbetween extraction is missing
def extract_targets(target_geo, static_target_name=None, result_smoothing=2, evaluation_mesh=True):
    """
    Will extract all targets blendshapes as geo.

    Args:
        target_geo(pmc.PyNode): The target geo with the blendshape node.
        static_target_name(str): Name of the target which should be always fully activated.
                                 Default is None.
        result_smoothing(int): Result smoothing value.
                               If False will skip it.
                               Default is 2.
        evaluation_mesh(bool or pmc.PyNode):
                               Take the given geo to extract shapes from via a wrap deformer if pmc.PyNode is given.
                               Will create a evaluation mesh and wrap it over the source if True boolean is given.
                               This eval mesh will produce the extracted shapes.
                               If False the extracted shapes are generated directly from the source mesh.
                               Set it on False if the asset has a closed mouth or something similar where
                               vertices distance is too small.
                               Default is True.
    """
    source_shape = target_geo.getShape(noIntermediate=True).name()
    shapes_extract_target = target_geo
    wrap_deformer = None

    if evaluation_mesh:
        shapes_extract_target = evaluation_mesh

        if not isinstance(evaluation_mesh, pmc.PyNode):
            shapes_extract_target = target_geo.duplicate(n="evaluation_mesh")[0]
        dag_utils.delete_hidden_shapes(shapes_extract_target)

        pymel.core.parent(shapes_extract_target, None)

        wrap_deformer = rig_utils.create_wrap_deformer(
        target_geo, shapes_extract_target
        )
        if result_smoothing:
            delta_mush = pymel.core.deltaMush(
                ignoreSelected=True, si=result_smoothing
            )
            delta_mush.setGeometry(shapes_extract_target)
    source_blendshape_fn = get_blendshape_nodes(source_shape, as_fn=True)[0]
    source_weight_indeces = get_weight_indexes(source_blendshape_fn.name())

    extract_grp = pymel.core.createNode("transform",
                                        n="extracted_shapes_grp"
                                        )

    weight_driver_nodes_data = get_weights_drivers_data(
        source_blendshape_fn.name()
    )
    if weight_driver_nodes_data:
        disconnect_all_weight_values(source_blendshape_fn.name())

    if static_target_name:

        cmds.setAttr(
            f"{source_blendshape_fn.name()}.{static_target_name}", 1.0
        )

    for index in source_weight_indeces:
        source_blendshape_fn.setWeight(index, 1.0)
        weight_name = get_weight_name_from_index(
            source_blendshape_fn.name(), index, True
        )

        temp_static_name = ""
        if static_target_name:
            temp_static_name = static_target_name
        if weight_name != temp_static_name:
            source_blendshape_fn.setWeight(index, 1.0)
            target_dupl = shapes_extract_target.duplicate(n=weight_name)[0]
            target_dupl.setParent(extract_grp)
            source_blendshape_fn.setWeight(index, 0.0)

    if static_target_name:
        cmds.setAttr(
            f"{source_blendshape_fn.name()}.{static_target_name}", 0.0
        )

    if evaluation_mesh:
        pymel.core.delete([wrap_deformer, shapes_extract_target])
    if weight_driver_nodes_data:
        rebuild_weight_driver_nodes_graph(
            weight_driver_nodes_data,
        )


def rename_scene_blendshape_nodes():
    """
    Rename all blendshapes in the scene to the current driver shape name.
    """
    scene_blendshape_nodes = cmds.ls(typ="blendShape")
    execute_list = [
        (node, get_base_objects(node)[0].name())
        for node in scene_blendshape_nodes
    ]
    for data_tuple in execute_list:
        new_name = "{}_BLS".format(data_tuple[1].split("Shape")[0].split(":")[-1])
        cmds.rename(data_tuple[0], new_name)


def export_blendshape_weights(blendshapes):

    # TODO add versioning
    """Exports weights of blendshapes to XML files at the specified path."""
    export_path = ""
    export_path = paths_utils.get_project_paths(pmc.sceneName())

    export_path = os.path.join(export_path, PXO_BSWGH_DIR_NAME)

    for blendshape in blendshapes:
        if pmc.objExists(blendshape):
            pmc.deformerWeights(f"{blendshape}.xml",
                                path=export_path,
                                export=True,
                                deformer=blendshape
                                )


def import_blendshape_weights():
    """Imports weights from XML files named after deformers at the specified path."""

    # TODO add versioning
    import_path = paths_utils.get_project_paths(pmc.sceneName())
    import_path = os.path.join(import_path, PXO_BSWGH_DIR_NAME)

    if not os.path.exists(import_path):
        pmc.error(import_path)
        return

    for file in os.listdir(import_path):
        if file.endswith('.xml'):
            # full_path = os.path.join(export_path,f"{blendshape}.xml")
            deformer_name = os.path.basename(file).replace(".xml", "")

            if not pmc.objExists(deformer_name):
                continue

            pmc.deformerWeights(f"{deformer_name}.xml",
                                path=import_path,
                                im=True,
                                deformer=deformer_name
                                )

def _legacy_mirror_blendshape_targets(source_bhsp_nd_name, extract_geo, specific_w_name=None, target_mirror_side="R"):
    """
    Will mirror blendshape targets from given source blendshape node.

    Args:
        source_bhsp_nd_name(str): The source blendshape node with targets.
        extract_geo(str, pmc.PyNode): The extarct geo.
        specific_w_name(str): Flag can be used for mirror a specific blendshape target.
        target_mirror_side(str): The side to mirror to.
                                 Default is "R".

    Returns:
        List: List of all targets as pmc.PyNode()

    """
    result_list = []
    source_side_str = "L_"
    if target_mirror_side == "L":
        source_side_str = "R_"
    weight_names = [name for name in get_weight_names(source_bhsp_nd_name) if source_side_str in name]
    if specific_w_name:
        weight_names = [name for name in weight_names if specific_w_name in name]
    for w_name in weight_names:
        w_attr = pmc.PyNode(f"{source_bhsp_nd_name}.{w_name}")
        plug_d = w_attr.connections(s=True, d=False, p=True)
        if plug_d:
            w_attr.disconnect()
        w_attr.set(1.0)
        geo_name = w_name.replace(f"{source_side_str}", f"{target_mirror_side}_")
        tmp_dup = pmc.duplicate(extract_geo, n=geo_name)
        result_list.extend(result_list)
        pmc.parent(tmp_dup, None)
        w_attr.set(0.0)
        if plug_d:
            plug_d[0].connect(w_attr)
    return result_list


def create_mirrored_blendshape_targets(source_bhsp_nd_name, specific_w_name=None):
    """
    Will mirror blendshape targets from given source blendshape node.

    Args:
        source_bhsp_nd_name(str): The source blendshape node with targets.

    Returns:
        List: List of all targets as pmc.PyNode()

    """
    source_geo = pmc.PyNode(get_base_objects(source_bhsp_nd_name)[0].name()).getTransform()
    deformed_shape = source_geo.getShape(noIntermediate=True)
    deformed_shape_m_obj = deformed_shape.__apimobject__()
    pass_geo = pmc.duplicate(source_geo, n="pass_geo")[0]
    result = pmc.duplicate(source_geo, n="result_geo")[0]
    dag_utils.delete_hidden_shapes(pass_geo)
    dag_utils.delete_hidden_shapes(result)
    pmc.parent([pass_geo, result], None)
    create_blendshape_node(pass_geo, name="pass_bshp", targets_list=[deformed_shape_m_obj], keep_target=True)
    pmc.PyNode("pass_bshp.w[0]").set(1.0)
    pass_geo.scaleX.unlock()
    pass_geo.scaleX.set(-1.0)
    wrap_deformer = rig_utils.create_wrap_deformer(
        pass_geo, result
    )
    result_list=_legacy_mirror_blendshape_targets(source_bhsp_nd_name, result, specific_w_name)
    pmc.delete([wrap_deformer, pass_geo, result]+pmc.ls("pass_bshp*"))
    return result_list




