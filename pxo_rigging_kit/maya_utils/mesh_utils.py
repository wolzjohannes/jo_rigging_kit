# Author:     Johannes Wolz / Lead Rigging TD

"""
Utils code to handle maya meshes
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Import built-in modules
from builtins import range
from builtins import str
from builtins import zip
import json
# Import python standart import
import logging
import os
from typing import Union, Optional, List

import numpy as np
# Import third-party modules
from future import standard_library
from maya import OpenMaya
from maya.api import OpenMaya as om2

import maya.cmds as cmds

import numpy
# Import Maya specific modules
import pymel.core
import six

# Import local modules
from pxo_rigging_kit.maya_utils import decorators
from pxo_rigging_kit.maya_utils import exceptions
from pxo_rigging_kit.maya_utils import openmaya_utils

standard_library.install_aliases()

##########################################################
# GLOBALS
##########################################################

_LOGGER = logging.getLogger(f"{__name__}.py")
_LOGGER.setLevel(logging.INFO)
DECORATORS = decorators.Decorators()
DECORATORS.debug = True
DECORATORS.logger = _LOGGER

VERTS_WS_POS_TOLERANCE = 1e-6

standard_library.install_aliases()

##########################################################
# FUNCTIONS
##########################################################


@DECORATORS.x_timer
def get_mesh_data(incoming_object: Union[str, om2.MFnMesh]) -> dict:
    """
    Get data from given mesh. Like vertices number and vertex IDs and etc.

    Args:
        incoming_object(str, om2.MFnMesh): The mesh shape to get the data from.

    Return:
        Dict: {
        "mesh_shape": string
        "num_vertices": integer,
        "num_polys": integer,
        "poly_vertex_id_list": List with each vertex ID of
                               each vertex ordered by all polys,
        "verts_ws_pos_list": List of all worldspace positions
                             of each vertex of the mesh.
        }

    """
    _NOT_VALID_TYPE_ERR = (f"{incoming_object} of type {type(incoming_object)} "
                           f"is not a recognized geometry type "
                           )

    if isinstance(incoming_object, (om2.MFnNurbsSurface, om2.MFnNurbsCurve, om2.MFnMesh)):
        mesh_shape = incoming_object

    elif isinstance(incoming_object, (om2.MDagPath, six.string_types)):

        if isinstance(incoming_object, six.string_types):
            incoming_object = openmaya_utils.get_dag_path_om2(incoming_object)

        if incoming_object.hasFn(om2.MFn.kMesh):
            mesh_shape = om2.MFnMesh(incoming_object)

        elif incoming_object.hasFn(om2.MFn.kNurbsSurface):
            mesh_shape = om2.MFnNurbsSurface(incoming_object)

        elif incoming_object.hasFn(om2.MFn.kNurbsCurve):
            mesh_shape = om2.MFnNurbsCurve(incoming_object)

        else:
            raise ValueError(_NOT_VALID_TYPE_ERR)

    else:
        raise ValueError(_NOT_VALID_TYPE_ERR)

    if mesh_shape.hasObj(om2.MFn.kMesh):

        geometry_points = mesh_shape.getPoints(space=om2.MSpace.kWorld)

        num_vertices = mesh_shape.numVertices
        num_polys = mesh_shape.numPolygons

        poly_vertex_ids = []
        for x in range(num_polys):
            m_int_array = mesh_shape.getPolygonVertices(x)
            poly_vertex_ids.extend(list(m_int_array))

    elif mesh_shape.hasObj(om2.MFn.kNurbsSurface):

        geometry_points = mesh_shape.cvPositions(space=om2.MSpace.kWorld)

        u_cv = mesh_shape.numCVsInU
        v_cv = mesh_shape.numCVsInV

        num_vertices = len(geometry_points)

        num_polys = (u_cv - 1) * (v_cv - 1)
        poly_vertex_ids = []

        for v in range(v_cv - 1):
            for u in range(u_cv - 1):
                i0 = v * u_cv + u
                i1 = i0 + 1
                i2 = i0 + u_cv + 1
                i3 = i0 + u_cv

                poly_vertex_ids.append([i0, i1, i2, i3])

    elif mesh_shape.hasObj(om2.MFn.kNurbsCurve):

        geometry_points = mesh_shape.cvPositions(space=om2.MSpace.kWorld)
        num_vertices = len(geometry_points)
        num_polys = num_vertices - 1

        poly_vertex_ids = [[i, i + 1]
                           for i
                           in range(num_vertices - 1)
                           ]

    else:
        raise ValueError(f"{mesh_shape} is not a recognized geometry type")

    verts_ws_pos_list = [
        (
            geometry_points[x].x,
            geometry_points[x].y,
            geometry_points[x].z,
        )
        for x in range(num_vertices)
    ]

    return {
        "mesh_shape": str(mesh_shape.name()),
        "num_vertices": int(num_vertices),
        "num_polys": num_polys,
        "poly_vertex_id_list": poly_vertex_ids,
        "verts_ws_pos_list": verts_ws_pos_list,
    }


def save_mesh_data(file_prefix: str,
                   directory: str,
                   mesh_data_dict: Optional[dict] = None,
                   mesh_shape: Optional[Union[str, om2.MFnMesh]] = None) -> str:
    """
    Save mesh data as json file.
    Vertex ids and ws position of each vertex wil be saved as numpy array.
    Each numpy array will be saved at the same location as the json file.
    And each array file name is stored in the json file.

    Args:
        file_prefix(str): File prefix for the file_name.
        directory(str): Directory to save.
        mesh_data_dict(dict, optional): Mesh data for saving if you have one.
                                        If not given will take mesh data from
                                        given mesh_shape.
                                        Default is False.
        mesh_shape(str, OpenMaya.MFnMesh, optional): The mesh shape to get
                                                     the data from. If you do
                                                     not have a mesh_data_dict.

    Return:
        String: File name.

    """
    if not mesh_data_dict:
        mesh_data_dict = get_mesh_data(mesh_shape)

    poly_vertex_id_npy_name = f"{file_prefix}_poly_vertex_id"
    verts_pos_npy_name = f"{file_prefix}_verts_ws_positions"

    poly_vertex_id_np_array = numpy.array(
        mesh_data_dict.get("poly_vertex_id_list"), dtype=object
    )

    mesh_data_dict[str("poly_vertex_id_list")] = f"{file_prefix}.npy"

    vertex_ws_pos_np_array = numpy.array(
        mesh_data_dict.get("verts_ws_pos_list"), dtype=object
    )
    mesh_data_dict[str("verts_ws_pos_list")] = f"{verts_pos_npy_name}.npy"

    poly_vertex_id_npy_dir = os.path.normpath(
        "{}/{}".format(directory, poly_vertex_id_npy_name)
    )
    verts_pos_npy_dir = os.path.normpath(f"{directory}/{verts_pos_npy_name}")

    numpy.save(poly_vertex_id_npy_dir, poly_vertex_id_np_array)
    numpy.save(verts_pos_npy_dir, vertex_ws_pos_np_array)

    json_file_dir = os.path.normpath(f"{directory}/{file_prefix}_mesh_data.json")

    with open(json_file_dir, "w") as json_file:
        json.dump(mesh_data_dict, json_file, sort_keys=True, indent=4)

    return os.path.basename(json_file_dir)


def _compare_mesh_data(
    mesh_data_dict_0, mesh_data_dict_1, verts_ws_pos_tolerance=VERTS_WS_POS_TOLERANCE
):
    """
    Compare mesh data dictionaries.

    Args:
        mesh_data_dict_0(dict): Source mesh data dict.
        mesh_data_dict_1(dict): Target mesh data dict.
        verts_ws_pos_tolerance(float): Vertex ws position check tolerance.

    Return:
         Dict:
         {
        "vertex_count": True/False (Vertex count equal or not),
        "poly_count": True/False (Poly count equal or not),
        "vertex_ws_pos": True/False (Vertex WS positions equal or not),
        "poly_vertex_id_list": True/False (Vertex IDs equal or not),
        "verts_ws_pos_list": [],
        }

    """
    vertex_count, poly_count, vertex_ids, vertex_ws_pos = True, True, True, True
    _errors = []

    if mesh_data_dict_0.get("num_vertices") != mesh_data_dict_1.get("num_vertices"):
        vertex_count = False
        _errors.append("Vertex count not equal.")

    if mesh_data_dict_0.get("num_polys") != mesh_data_dict_1.get("num_polys"):
        poly_count = False
        _errors.append("Poly count not equal.")

    if mesh_data_dict_0.get("poly_vertex_id_list") != mesh_data_dict_1.get(
        "poly_vertex_id_list"
    ):
        vertex_ids = False
        _errors.append("Vertex IDs not equal.")

    vertex_ws_compare_list = compare_vertex_ws_positions(
        mesh_data_dict_0.get("verts_ws_pos_list"),
        mesh_data_dict_1.get("verts_ws_pos_list"),
        verts_ws_pos_tolerance,
    )

    if vertex_ws_compare_list:
        vertex_ws_pos = False
        _errors.append(
            "World position of some vertices are not matching with compared ones."
        )

    if _errors:
        _LOGGER.error(r"\n".join(_errors))

    return {
        "vertex_count": vertex_count,
        "poly_count": poly_count,
        "vertex_ws_pos": vertex_ws_pos,
        "poly_vertex_id_list": vertex_ids,
        "verts_ws_pos_list": vertex_ws_compare_list,
    }


def compare_vertex_ws_positions(
    verts_ws_pos_list_0, verts_ws_pos_list_1, tolerance=VERTS_WS_POS_TOLERANCE
):
    """
    Compare vertex vectors with each other. And if the distance between them
    are bigger then the given tolerance it will return the vertex IDs in a list.

    Args:
        verts_ws_pos_list_0(list): List of vector arrays.
        verts_ws_pos_list_1(list): List of vector arrays.
        tolerance(float): Distance tolerance.
                          Default is VERTS_WS_POS_TOLERANCE.

    Return:
        List: If True filled with vertex IDs as integers.
              False if fail.
              None if the distance of the vectors in given tolerance.

    """
    arr0 = numpy.asarray(verts_ws_pos_list_0, dtype=np.float32) # lowering the precision ?
    arr1 = numpy.asarray(verts_ws_pos_list_1, dtype=np.float32) # lowering the precision ?

    diff = arr0 - arr1
    sq_dist = numpy.sum(diff * diff, axis=1)

    mask = sq_dist > tolerance * tolerance
    indices = numpy.where(mask)[0]

    return indices.tolist()


# This function has a problem and needs to be optimized.
# Because of the converting issue of an array to an numpy array and vise versa.
# We getting weird rounding issues in the world space coordinates of the vertices.
# So it always appears as off and invalid even if you increase the tolerance.
def check_mesh_data_from_json(
    json_file_path,
    diff_poly_vertex_id=False,
    diff_poly_vertex_id_color_on_mesh=False,
    diff_vertx_ws_pos=False,
    diff_vertx_ws_color_on_mesh=False,
    verts_ws_pos_tolerance=VERTS_WS_POS_TOLERANCE,
):
    """
    Check a mesh based from a saved json file.

    Args:
        json_file_path(str): Path to the saved json file.
        diff_poly_vertex_id(bool): Gives back the vertex ids which are
                                   different in a new dict_key. If a difference
                                   exist. Else None.
        diff_poly_vertex_id_color_on_mesh(bool): Will give the vertices
                                                 with a different
                                                 vertex id a red color.
                                                 So we see the
                                                 difference in the viewport.
        diff_vertx_ws_pos(bool): Gives back the vertices which are different
                                 in ws position in a new dict_key. If
                                 difference exist. Else None.
        diff_vertx_ws_color_on_mesh(bool): Will give the vertices with a
                                           different ws position a blue
                                           color. So we see the difference
                                           in the viewport.
        verts_ws_pos_tolerance(float): Vertex ws position check tolerance.

    Return:
        Dict:
        {
        "vertex_count": vertex_count,
        "poly_count": poly_count,
        "poly_vertex_id_list": vertex_ids,
        "vertex_ws_pos": vertex_ws_pos,
        "verts_ws_pos_list": List,
        "diff_poly_vertex_id": List (just if diff_poly_vertex_id flag is
                                     enabled)
        }

    """
    base_name = os.path.basename(json_file_path)
    data_dir = os.path.normpath(json_file_path.split(base_name)[0])

    with open(json_file_path, "r") as json_file:
        mesh_data_dict = json.load(json_file)

    poly_vertex_id_list_file = os.path.join(
        data_dir, mesh_data_dict.get("poly_vertex_id_list")
    )

    verts_ws_pos_list_file = os.path.join(
        data_dir, mesh_data_dict.get("verts_ws_pos_list")
    )

    base_obj = str(mesh_data_dict.get("mesh_shape"))
    poly_vertex_np_data = numpy.load(poly_vertex_id_list_file, allow_pickle=True)
    verts_ws_pos_np_data = numpy.load(verts_ws_pos_list_file, allow_pickle=True)
    mesh_data_dict["poly_vertex_id_list"] = poly_vertex_np_data.tolist()
    mesh_data_dict["verts_ws_pos_list"] = verts_ws_pos_np_data.tolist()

    if not pymel.core.objExists(base_obj):
        _LOGGER.error("{} not exist. Abort mesh data check.".format(base_obj))
        return False

    current_mesh_data = get_mesh_data(base_obj)

    compare_mesh_data_dict = _compare_mesh_data(
        mesh_data_dict, current_mesh_data, verts_ws_pos_tolerance
    )

    compare_mesh_data_dict = _diff_mesh_data(
        diff_poly_vertex_id,
        diff_poly_vertex_id_color_on_mesh,
        diff_vertx_ws_pos,
        diff_vertx_ws_color_on_mesh,
        compare_mesh_data_dict,
        mesh_data_dict,
        current_mesh_data,
        base_obj,
    )
    return compare_mesh_data_dict


def check_mesh_data(
    source_mesh,
    target_mesh,
    diff_poly_vertex_id=False,
    diff_poly_vertex_id_color_on_mesh=False,
    diff_vertx_ws_pos=False,
    diff_vertx_ws_color_on_mesh=False,
    verts_ws_pos_tolerance=VERTS_WS_POS_TOLERANCE,
):
    """
    Check two meshes with each other.

    Args:
        source_mesh(str): The source mesh shape node.
        target_mesh(str): The target mesh shape node.
        diff_poly_vertex_id(bool): Gives back the vertex ids which are
                                   different in a new dict_key. If a difference
                                   exist. Else None.
        diff_poly_vertex_id_color_on_mesh(bool): Will give the vertices with a
                                                 different vertex id a red
                                                 color. So we see the
                                                 difference in the viewport.
        diff_vertx_ws_pos(bool): Gives back the vertices which are different
                                 in ws position in a new dict_key. If
                                 difference exist. Else None.
        diff_vertx_ws_color_on_mesh(bool): Will give the vertices with a
                                           different ws position a blue color.
                                           So we see the difference in the
                                           viewport.
        verts_ws_pos_tolerance(float): Vertex ws position check tolerance.

    Return:
        Dict:
        {
        "vertex_count": vertex_count,
        "poly_count": poly_count,
        "poly_vertex_id_list": vertex_ids,
        "vertex_ws_pos": vertex_ws_pos,
        "verts_ws_pos_list": List,
        "diff_poly_vertex_id": List (just if diff_poly_vertex_id flag is
                                     enabled)
        }

    """
    source_mesh = pymel.core.PyNode(source_mesh)
    target_mesh = pymel.core.PyNode(target_mesh)

    if source_mesh.nodeType() == "transform":
        source_mesh = source_mesh.getShape().name(long=None)

    if target_mesh.nodeType() == "transform":
        target_mesh = target_mesh.getShape().name(long=None)

    if not pymel.core.uniqueObjExists(source_mesh):
        raise exceptions.MayaNodeNameUniqueness("Source mesh shape name not unique.")

    if not pymel.core.uniqueObjExists(target_mesh):
        raise exceptions.MayaNodeNameUniqueness("Target mesh shape name not unique.")

    source_dag_path = openmaya_utils.get_dag_path_om2(source_mesh)
    target_dag_path = openmaya_utils.get_dag_path_om2(target_mesh)

    if source_dag_path.hasFn(om2.MFn.kMesh) and target_dag_path.hasFn(om2.MFn.kMesh):
        source_shape_mfn = om2.MFnMesh(source_dag_path)
        target_shape_mfn = om2.MFnMesh(target_dag_path)

    elif source_dag_path.hasFn(om2.MFn.kNurbsSurface) and target_dag_path.hasFn(om2.MFn.kNurbsSurface):
        source_shape_mfn = om2.MFnNurbsSurface(source_dag_path)
        target_shape_mfn = om2.MFnNurbsSurface(target_dag_path)

    elif source_dag_path.hasFn(om2.MFn.kNurbsCurve) and target_dag_path.hasFn(om2.MFn.kNurbsCurve):
        source_shape_mfn = om2.MFnNurbsCurve(source_dag_path)
        target_shape_mfn = om2.MFnNurbsCurve(target_dag_path)

    else:
        raise exceptions.MeshError(f"types of {source_mesh.name()} and {target_mesh.name()} do not match")

    mesh_data_dict_0 = get_mesh_data(source_shape_mfn)
    mesh_data_dict_1 = get_mesh_data(target_shape_mfn)

    compare_mesh_data_dict = _compare_mesh_data(
        mesh_data_dict_0, mesh_data_dict_1, verts_ws_pos_tolerance
    )
    compare_mesh_data_dict = _diff_mesh_data(
        diff_poly_vertex_id,
        diff_poly_vertex_id_color_on_mesh,
        diff_vertx_ws_pos,
        diff_vertx_ws_color_on_mesh,
        compare_mesh_data_dict,
        mesh_data_dict_0,
        mesh_data_dict_1,
        target_mesh,
    )
    return compare_mesh_data_dict


@DECORATORS.x_timer
def _diff_two_arrays(source_list, target_list, use_order_index=False):
    """
    Find the difference of two arrays.

    Args:
        source_list(List): The source list.
        target_list(List): The target list to compare.
        use_order_index(bool): Will take the index of the list object with
                               the difference

    Return:
        List: Filled with the difference of the two arrays.

    """
    diff_list = []
    if len(source_list) != len(target_list):
        raise IndexError("Arrays do not have the same length.")

    for index, (id_source_list, id_target_list) in enumerate(
        zip(source_list, target_list)
    ):
        if id_source_list != id_target_list:
            if use_order_index:
                diff_list.append(index)
            else:
                diff_list.extend(id_target_list)
    return diff_list


def _diff_color_on_mesh_func(diff_list: List,
                             target_mesh: str,
                             color_tuple: tuple,
                             ):
    """
    Shows the vertex differences in the viewport.

    Args:
        diff_list(List): List with vertex numbers.
        target_mesh(str): The mesh for coloring.
        color_tuple(tuple): The color rgb values.

    """
    target_mesh_node = pymel.core.PyNode(target_mesh)

    if target_mesh_node.nodeType() != "mesh":
        return

    color_list = [f"{target_mesh}.vtx[{vtx_id}]"
                  for vtx_id
                  in diff_list
                  ]

    target_mesh_node.setDisplayColors(True)

    cmds.softSelect(sse=0)

    cmds.select(color_list)

    cmds.polyColorPerVertex(rgb=color_tuple, cdo=True)

    cmds.polyOptions(cm="ambientDiffuse")

    cmds.select(clear=True)


def _diff_mesh_data_arrays(
    compare_mesh_data_dict,
    mesh_data_dict_0,
    mesh_data_dict_1,
    array_name,
    result_dict_key,
    use_order_index=False,
):
    """
    Diff the mesh data arrays and gives back the updated given compare data
    dict.

    Args:
        compare_mesh_data_dict(dict): The dict with the result of the mesh
                                      comparison. Will be used to store the
                                      result in a given dict key.
        mesh_data_dict_0(dict): The source mesh data dict.
        mesh_data_dict_1(dict): The target mesh data dict.
        array_name(str): The key in the data dict.
                         So we can get the array we want to compare.
        result_dict_key(str): Key name to store the result in the
                              compare_mesh_data_dict.
        use_order_index(bool): Will take the index of the list object with
                               the difference.

    Return:
        Dict:
        {
        "vertex_count": vertex_count,
        "poly_count": poly_count,
        "poly_vertex_id_list": vertex_ids,
        "verts_ws_pos_list": vertex_ws_pos,
        "result_dict_key": diff_list
        }

    """
    diff_list = None

    if not compare_mesh_data_dict.get(array_name):
        diff_list = _diff_two_arrays(
            mesh_data_dict_0.get(array_name),
            mesh_data_dict_1.get(array_name),
            use_order_index,
        )

    compare_mesh_data_dict[result_dict_key] = diff_list

    return compare_mesh_data_dict


def _diff_mesh_data(
    diff_poly_vertex_id,
    diff_poly_vertex_id_color_on_mesh,
    diff_vertx_ws_pos,
    diff_vertx_ws_color_on_mesh,
    compare_mesh_data_dict,
    mesh_data_dict_0,
    mesh_data_dict_1,
    target_mesh,
):
    """
    Will differentiate the mesh data.

    Args:
        diff_poly_vertex_id(bool): Gives back the vertex ids which are
                                   different in a new dict_key. If a difference
                                   exist. Else None.
        diff_poly_vertex_id_color_on_mesh(bool): Will give the vertices with a
                                                 different vertex id a red
                                                 color. So we see the
                                                 difference in the viewport.
        diff_vertx_ws_pos(bool): Gives back the vertices which are different
                                 in ws position in a new dict_key. If
                                 difference exist. Else None.
        diff_vertx_ws_color_on_mesh(bool): Will give the vertices with a
                                           different ws position a blue color.
                                           So we see the difference in the
                                           viewport.
        compare_mesh_data_dict(dict): The dict with the result of the mesh
                                      comparison. Will be used to store the
                                      result in a given dict key.
        mesh_data_dict_0(dict): Source mesh data dict.
        mesh_data_dict_1(dict): Target mesh data dict.
        target_mesh(str): The mesh which will get vertex color if
                          diff_poly_vertex_id_color_on_mesh or
                          diff_vertx_ws_color_on_mesh is set..

    Return:
        Dict:
        {
        "vertex_count": vertex_count,
        "poly_count": poly_count,
        "poly_vertex_id_list": vertex_ids,
        "verts_ws_pos_list": vertex_ws_pos,
        "diff_poly_vertex_id": List,
        "diff_verts_ws_pos": List,
        }
    """
    if diff_poly_vertex_id:
        compare_mesh_data_dict = _diff_mesh_data_arrays(
            compare_mesh_data_dict,
            mesh_data_dict_0,
            mesh_data_dict_1,
            "poly_vertex_id_list",
            "diff_poly_vertex_id",
        )
        if diff_poly_vertex_id_color_on_mesh:
            if compare_mesh_data_dict.get("diff_poly_vertex_id"):
                _diff_color_on_mesh_func(
                    compare_mesh_data_dict.get("diff_poly_vertex_id"),
                    target_mesh,
                    (1.0, 0.0, 0.0),
                )
    if diff_vertx_ws_pos:
        if (
            compare_mesh_data_dict.get("vertex_count")
            and compare_mesh_data_dict.get("poly_count")
            and compare_mesh_data_dict.get("poly_vertex_id_list")
        ):
            if diff_vertx_ws_color_on_mesh:
                if compare_mesh_data_dict.get("verts_ws_pos_list"):
                    _diff_color_on_mesh_func(
                        compare_mesh_data_dict.get("verts_ws_pos_list"),
                        target_mesh,
                        (0.0, 0.0, 1.0),
                    )
    return compare_mesh_data_dict


def validate_meshes(source_mesh=None, target_mesh=None, json_file_dir=False):
    """
    Compare two meshes and validate it. You can do it with given source and
    target mesh. Or from a json_file.

    Args:
        source_mesh(str): The source mesh shape node or transform.
        target_mesh(str): The target mesh shape node or transform.
        json_file_path(str): Path to the saved json file.

    Return:
        Succeed:
            Dict: {
            "mesh_shape": string
            "num_vertices": integer,
            "num_polys": integer,
            "poly_vertex_id_list": List with each vertex ID of
                                   each vertex ordered by all polys,
            "verts_ws_pos_list": List of all worldspace positions
                                 of each vertex of the mesh.
            }

        Fail:
            False.

    """
    if not json_file_dir:
        mesh_data_dict = check_mesh_data(source_mesh, target_mesh)
    else:
        mesh_data_dict = check_mesh_data_from_json(json_file_dir)

    if not mesh_data_dict.get("vertex_count"):
        _LOGGER.error(
            "The vertex count is not equal. New blendshape would "
            "not work probably. Exit execution."
        )
        return False

    if not mesh_data_dict.get("poly_count"):
        _LOGGER.error(
            "The poly count is not equal. New blendshape would "
            "not work probably. Exit execution."
        )
        return False

    if not mesh_data_dict.get("poly_vertex_id_list"):
        _LOGGER.error(
            "The vertex IDs not equal. New blendshape would "
            "not work probably. Exit execution. To get the vertices with "
            "different IDs. Use this command: "
            "`mesh_utils.check_mesh_data_from_json(json_file_dir, "
            "diff_poly_vertex_id=True, "
            "diff_poly_vertex_id_color_on_mesh=True)` or "
            "`mesh_utils.check_mesh_data(source_mesh, target_mesh, "
            "diff_poly_vertex_id=True, "
            "diff_poly_vertex_id_color_on_mesh=True)`"
        )
        return False

    if not mesh_data_dict.get("vertex_ws_pos"):
        _LOGGER.error(
            "The world position of some vertices are different. "
            "Blendshape targets would have wrong results. "
            "Exit execution. To get the vertices with "
            "different world position. Use this command: "
            "`mesh_utils.check_mesh_data_from_json(json_file_dir, "
            "diff_vertx_ws_pos=True, diff_vertx_ws_color_on_mesh=True)` or "
            "'mesh_utils.check_mesh_data(source_mesh, target_mesh"
            "diff_vertx_ws_pos=True, diff_vertx_ws_color_on_mesh=True)'"
        )
        return False
    return mesh_data_dict


def sel_to_meshes():
    """
    Turns selection to meshes.

    Returns:
        List(meshes_selected): The meshes that were selected.
    """
    return [
        trs
        for trs in pymel.core.selected()
        if trs.getShape() and trs.getShape().nodeType() == "mesh"
    ]


def get_vertices_center(verts):
    """
    Given a list of vertex components, return their center position in world space.
    """

    verts = cmds.ls(verts, flatten=True)

    positions = [cmds.pointPosition(v, world=True) for v in verts]

    count = len(positions)
    if count == 0:
        return None

    avg_x = sum(p[0] for p in positions) / count
    avg_y = sum(p[1] for p in positions) / count
    avg_z = sum(p[2] for p in positions) / count

    return avg_x, avg_y, avg_z
