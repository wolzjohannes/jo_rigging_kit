# Author:     Christof Puehringer / Rigging TD

"""
Code to create the proxy slice in a quite fast way.

Examples:

    - Slicing a mesh based on its absolutized joint influences, this will take the selection:
    >>> from importlib import reload

    >>> from pxo_rigging_kit.maya_utils.deformers.utilities import skincluster_proxyslicing
    >>> reload(skincluster_proxyslicing)

    >>> skincluster_proxyslicing.main()

"""


# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from future import standard_library

# Import built-in modules
from builtins import dict
from builtins import int
from builtins import str
import colorsys
from importlib import reload
import logging
import numpy as np # noqa: import error
import random

import pymel.core as pmc
import maya.cmds as cmds # noqa: import error
import maya.OpenMaya as OpenMaya # noqa: import error
from maya.api import OpenMaya as om2 # noqa: import error

from pxo_rigging_kit.maya_utils import decorators
from pxo_rigging_kit.maya_utils.dag_utils import delete_hidden_shapes
from pxo_rigging_kit.maya_utils.deformers.operators.skincluster_op import SkinClusterOperator
from pxo_rigging_kit.maya_utils.shader_utils import non_connected_to_initial_shading_grp


##########################################################
# GLOBALS
##########################################################

standard_library.install_aliases()

_LOGGER = logging.getLogger(f"{__name__}.py")
_LOGGER.setLevel(logging.DEBUG)
DECORATORS = decorators.Decorators()

DECORATORS.debug = True
DECORATORS.logger = _LOGGER

##########################################################
# FUNCTIONS
##########################################################


def get_mean_vert_pos(geometry_transform, axis="Z"):
    """
    Returns the average vertex position.

    Usages:
        sorting geometry shells by average vertex position

    Args:
        geometry_transform:
        axis(str):

    Returns:
        the mean average of vtx pos z
    """

    axis_dict = {"X": 0,
                 "Y": 1,
                 "Z": 2,
                 }

    sel = om2.MGlobal.getSelectionListByName(geometry_transform)
    dag_path = sel.getDagPath(0, )

    mesh_fn = om2.MFnMesh(dag_path)
    positions = mesh_fn.getPoints()

    gen_points = [(x[0], x[1], x[2]) for x in positions]

    mesh_points = np.asarray(gen_points,
                             dtype=np.float64,
                            )

    mean_val = np.mean(mesh_points, axis=0)
    return mean_val[axis_dict.get(axis.upper(), 2)]


# @DECORATORS.x_timer
def get_mesh_face_iter(mesh_dag_path, face_id=None):
    """
    Creates a MItMeshPoligon-Iterator object for Mesh Faces to run with the get Face Vertex Indices.

    Args:
        mesh_dag_path(OpenMaya.MDagPath):     The path to the mesh itself.
        face_id(None, int):                   Can run on a specific face as well if face ID is given.

    Returns:
        OpenMaya.MItMeshPolygon:              OpenMaya-Iterator for faces to be used in further search operations.
    """

    mesh_face_it = OpenMaya.MItMeshPolygon(mesh_dag_path)

    if not face_id:
        return mesh_face_it

    # Initialize faceId
    mesh_face_util = OpenMaya.MScriptUtil(0)
    mesh_face_ptr = mesh_face_util.asIntPtr()
    mesh_face_it.setIndex(face_id, mesh_face_ptr)

    # Return result
    return mesh_face_it


# @DECORATORS.x_timer
def get_face_vertex_indices(face_iter, face_id):
    """
    Queries the face IDs for their unique vertex ids based on the OpenMaya.MItMeshPolygon operator and the face ID.

    Args:
        face_iter (OpenMaya.MItMeshPolygon):    The iterator object to run in conjunction with.
        face_id (int):                          The index of the face ID.

    Returns:
        Set:                                    The set containing the unique face vertices.
    """

    # Create faceId MScriptUtil
    face_id_util = OpenMaya.MScriptUtil()
    face_id_util.createFromInt(0)
    face_id_ptr = face_id_util.asIntPtr()

    # Get face vertex indices
    face_vtx_array = OpenMaya.MIntArray()
    face_iter.setIndex(int(face_id), face_id_ptr)
    face_iter.getVertices(face_vtx_array)

    # Return result
    return set(face_vtx_array)


@DECORATORS.x_timer
def convert_verts_to_face_id(mesh_dag_path):
    """
    Takes the vertices of the mesh and gathers information about the face IDs they belong to.
    Also figures out the vertex IDs and which vertices are in their retrospective faces.

    Args:
        mesh_dag_path(OpenMaya.MDagPath):                   The path to the mesh itself.

    Returns:
        Tuple(face_ids, vertex_ids, vertex_ids_in_face):    (list(face_ids),
                                                            numpy.array(vertex_ids),
                                                            list(vertex_ids_in_face),
                                                            )
    """

    iterator_ = OpenMaya.MItMeshVertex(mesh_dag_path)
    face_iter = get_mesh_face_iter(mesh_dag_path)

    face_ids = list()
    vertex_ids_in_face = list()

    vertex_ids = np.fromiter(range(iterator_.count()), int)

    while not iterator_.isDone():

        # get normal data
        face_id = OpenMaya.MIntArray()
        iterator_.getConnectedFaces(face_id)

        face_ids.append(tuple(face_id))

        # Get MItMeshPolygon
        vertex_ids_in_face.append(tuple((get_face_vertex_indices(face_iter,
                                                                 face_id_item
                                                                 )
                                         for face_id_item in face_id
                                         )
                                        )
                                  )
        iterator_.next()

    return face_ids, vertex_ids, vertex_ids_in_face


@DECORATORS.x_timer
def perform_split_mesh(faces_sorted,
                       input_dag_node):
    """
    Duplicates, cleans and splits the mesh based on its sorted faces IDs.

    Args:
        faces_sorted (dict):       Sorted faces of the mesh to be sliced.
        input_dag_node (str):      Name of the mesh to be sliced.

    Returns:
        List(separated_meshes):    All the resulting split meshes of the operation.
    """

    # create duplicate of input_dag_node and delete all its hidden shapes
    input_dag_node = delete_hidden_shapes(pmc.duplicate(input_dag_node)[0])[0]

    # get the name of the node
    input_dag_name = str(input_dag_node.shortName())

    created_sets = list()
    for (id_, inf_), face_list_ in faces_sorted.items():
        face_name_base = input_dag_name.replace("|", "")

        created_set = cmds.sets(*[f"{face_name_base}.f[{face_}]"
                                  for face_ in face_list_
                                  ],
                                n=f"{face_name_base}__{inf_.split('|')[-1]}"
                                )

        created_sets.append(created_set)

    # creates a set containing the mesh splits
    cmds.sets(*created_sets, n="mesh_split")

    # extracts the faces to get to the splitmeshes
    for inf_, face_list_ in faces_sorted.items():
        extract_faces(pmc.PyNode(input_dag_node).getShape().__apimfn__(), face_list_)

    # kills off operations that will impact the performance and functionality by deleting the history
    cmds.delete(input_dag_name, constructionHistory=True)

    # create seperate meshes from the extracted faces
    separated_meshes = cmds.polySeparate(input_dag_name, constructionHistory=False)

    # remove the polySeperate Operations by deleting the history
    cmds.delete(input_dag_name, constructionHistory=True)

    return separated_meshes


@DECORATORS.x_timer
def sort_and_tag_seperated_meshes(input_dag_node):
    """
    Sorts and tags the created meshes based on the maya set called mesh_split.

    Args:
        input_dag_node (str):     Name of the mesh that was sliced.

    Returns:
        List (mesh_contents):     The sliced meshes that were in the mesh_split set and have been tagged and renamed.
    """

    if ":" in input_dag_node:
        namespace_index = input_dag_node.find(":")
        input_dag_node = input_dag_node[namespace_index:]

    new_mesh_name_root, side, number, assignment, suffix = input_dag_node.split("_")
    new_mesh_name = f"{new_mesh_name_root}_{side}_{'NUMBER'}_{'sliced'}_{suffix}"

    split_mesh_grp = new_mesh_name.replace("NUMBER", "001").replace(suffix, "grp")

    split_sets = cmds.sets("mesh_split", q=True)

    mesh_contents = [(recompose_mesh(x), x.split("__")[-1])
                     if "eye" not in x
                     else (recompose_mesh(x), "C_bnd_head_0_0_jnt")
                     for x in split_sets
                     ]

    [cmds.addAttr(mesh_info[0],
                  longName="parent_nd",
                  dt="string"
                  )
     for mesh_info in mesh_contents
     ]

    [cmds.addAttr(cmds.listRelatives(mesh_info[0], shapes=True)[0],
                  longName="mtoa_constant_parent_nd",
                  dt="string"
                  )
     for mesh_info in mesh_contents
     if cmds.listRelatives(mesh_info[0], shapes=True)
     ]

    [cmds.addAttr(mesh_info[0],
                  longName="is_sliced_geo",
                  at="bool",
                  dv=True
                  )
     for mesh_info in mesh_contents
     ]

    [cmds.setAttr("{0}.parent_nd".format(mesh_info[0]),
                  mesh_info[1],
                  type="string",
                  l=True
                  )
     for mesh_info in mesh_contents
     ]

    [cmds.setAttr("{0}.mtoa_constant_parent_nd".format(cmds.listRelatives(mesh_info[0], shapes=True)[0]),
                  mesh_info[1],
                  type="string",
                  l=True
                  )
     for mesh_info in mesh_contents
     if cmds.listRelatives(mesh_info[0], shapes=True)
     ]

    mesh_contents_sorted = sorted(mesh_contents, key=lambda x: get_mean_vert_pos(x[0]))

    cmds.createNode("transform", n=split_mesh_grp)
    cmds.parent([mesh_info[0] for mesh_info in mesh_contents_sorted], split_mesh_grp)

    new_mesh_names = [new_mesh_name.replace("NUMBER", str(number_).zfill(len(str(len(mesh_contents_sorted)))))
                      for number_, _
                      in enumerate(mesh_contents_sorted)
                      ]

    [cmds.rename(mesh_info[0],
                 new_mesh_names[number_]
                 )
     for number_, mesh_info
     in enumerate(mesh_contents_sorted)
     ]

    return new_mesh_names


@DECORATORS.x_timer
def recompose_mesh(inner_set):
    """
    Combines the items in the inner sets, so their separated mesh islands together to one mesh based on their influence.

    Args:
        inner_set (str):                        Name of the inner mesh that needs to be combined.

    Returns:
        Str (inner_mesh, inner_set_meshes):     The combined mesh that contains all the faces with a specific influence.
    """

    inner_set_faces = cmds.sets(inner_set, q=True)
    inner_set_meshes = list(set([x.split(".")[0] for x in inner_set_faces]))

    if len(inner_set_meshes) > 1:
        inner_mesh = cmds.polyUnite(*inner_set_meshes,
                                    n='intermediate_split',
                                    constructionHistory=False,
                                    )
        return str(inner_mesh[0])

    return str(inner_set_meshes[0])


@DECORATORS.x_timer
def map_face_vert_inf(vertex_of_face, weights_sorted_indexed, face_ids):
    """
    Create a list that maps the vertices grouped to the influences by their face association.

    Args:
        vertex_of_face (list):              List with vertices and their other vertices in the face.
        weights_sorted_indexed (dict):      Dictionary containing the weights sorted by their index.
        face_ids (list):                    List containing the face IDs.

    Returns:
        List (face_vert_inf_map):           list(dict(vertex_of_face_iteration: set(vertices_of_face)),
                                                 dict(vertex_of_face_iteration: set(vertices_of_face)),
                                                 dict(vertex_of_face_iteration: set(vertices_of_face)),...
                                                 )
    """

    face_vert_inf_map = list()

    for iteration_, vertices_of_face in enumerate(vertex_of_face):
        face_vert_map = dict()

        for itr_, face_grouped in enumerate(vertices_of_face):
            inf_map = set()

            for vertex_ in face_grouped:
                inf_map.add((vertex_,
                             weights_sorted_indexed[vertex_]
                             )
                            )

            face_vert_map[face_ids[iteration_][itr_]] = inf_map
        face_vert_inf_map.append(face_vert_map)

    return face_vert_inf_map


@DECORATORS.x_timer
def absolutize_face_weights(face_vert_inf_map):
    """
    Get a list filled with dictionaries of the face ID and their maximum influence.

    Args:
        face_vert_inf_map (list):    The dictionary of the face_vertex influence map.

    Returns:
        List (return_list):          list(dict(face_id: most_frequent_influence),
                                          dict(face_id: most_frequent_influence),
                                          dict(face_id: most_frequent_influence),...
                                          )
    """

    return_list = list()

    for i in face_vert_inf_map:
        face_id_and_max_inf = dict()

        for face_id_, face_component in i.items():
            face_id_and_max_inf[face_id_] = most_frequent([jnt_[1]
                                                           for jnt_
                                                           in face_component
                                                           ]
                                                          )

        return_list.append(face_id_and_max_inf)

    return return_list


@DECORATORS.x_timer
def sort_face_weights(face_vert_inf_map):
    """
    Sort out the face weights from the face_vert_inf_map per influences.

    Args:
        face_vert_inf_map (dict):    The dictionary of the face_vertex influence map.

    Returns:
        Dict(influences_sorted):     dict(influence: set(),
                                          influence: set(),...
                                          )
    """

    influences = set()

    for face_inf_combo in face_vert_inf_map:
        influences.update(face_inf_combo.values())

    influences_sorted = dict_comp_influence_sort(influences)

    combo_to_inf(face_vert_inf_map, influences_sorted)

    return influences_sorted


@DECORATORS.x_timer
def combo_to_inf(face_vert_inf_map, influences_sorted):
    """
    Remaps the face_vert_inf_map to the sorted influences.

    Args:
        face_vert_inf_map (dict):   The dictionary of the face_vertex influence map.
        influences_sorted (dict):   The dictionary to which keys the face vertex association will be added to.

    """

    [influences_sorted[inf_].add(face_)
     for face_inf_combo
     in face_vert_inf_map
     for face_, inf_
     in face_inf_combo.items()
     if face_ not in influences_sorted[inf_]
     ]


@DECORATORS.x_timer
def dict_comp_influence_sort(influences):
    """
    Create a dictionary containing sets to better sort the vertices.

    Args:
        influences(Set): The influences set that needs to be rebuilt into a dict.

    Returns:
        Dict: Dictionary of sets.
    """

    return {influence: set()
            for influence
            in influences
            }


def extract_faces(shape_fn, faces_):
    """
    Uses OpenMaya to extract the specified faces from the polygon shape.

    Args:
        shape_fn (OpenMaya.MFnMesh):     The MFn of the Maya mesh.
        faces_ (list):                   The list containing the indices of the mesh.

    Returns:
        True: When done will return a True statement.
    """
    # create an open array to initialize and create disk space

    face_int_array = OpenMaya.MIntArray()

    # append face ids to this array
    for face_ in faces_:
        face_int_array.append(face_)

    # extract faces based on the array
    shape_fn.extractFaces(face_int_array, None)

    return True


def most_frequent(input_influence_objects):
    """
    Get the most frequent occurring item in the face.

    Args:
        input_influence_objects(list): The influence

    Returns:
        Int(max): The maximum in the set that is the amount of the influence occurrence.
    """

    return max(set(input_influence_objects),
               key=input_influence_objects.count
               )


@DECORATORS.x_timer
def create_proxyslice(geo_to_slice=None):

    if not geo_to_slice:
        selection = cmds.ls(sl=True)
        if not selection:
            raise ValueError("you have nothing selected")

        geo_to_slice = str(selection[0])

    if isinstance(geo_to_slice, pmc.PyNode):
        geo_to_slice = str(geo_to_slice.longName())

    # initialize the SkinClusterOperator
    skin_operator = SkinClusterOperator(geo_to_slice)
    weights_sorted_indexed = skin_operator.absolutize_deformer()

    face_ids, vertex_ids, vertices_of_face = convert_verts_to_face_id(skin_operator.transform_mdagpath)

    face_vert_inf_map = map_face_vert_inf(vertices_of_face,
                                          weights_sorted_indexed,
                                          face_ids
                                          )

    face_weights_absolutized = absolutize_face_weights(face_vert_inf_map)

    faces_sorted = sort_face_weights(face_weights_absolutized)

    perform_split_mesh(faces_sorted,
                       geo_to_slice
                       )

    mesh_contents = sort_and_tag_seperated_meshes(geo_to_slice)
    non_connected_to_initial_shading_grp()

    return mesh_contents


@DECORATORS.x_timer
def color_proxyslice(mesh_contents, color_base=None):

    shell_number = len(mesh_contents)

    generated_colors = create_lin_hue_rand_satval(shell_number,
                                                  color_base=color_base
                                                  )

    for iteration_, mesh_ in enumerate(mesh_contents):
        sel = om2.MGlobal.getSelectionListByName(mesh_)
        dag_path = sel.getDagPath(0, )

        mesh_fn = om2.MFnMesh(dag_path)

        new_vertex_colors = om2.MColorArray()

        # loop through and determine vertex colors
        it_vtx = om2.MItMeshVertex(dag_path)
        while not it_vtx.isDone():
            new_vertex_colors.append(generated_colors[iteration_])

            it_vtx.next()

        # you have to build this yourself, since the api can't convert a
        # python list to an MIntArray
        vertex_index_list = om2.MIntArray()
        [vertex_index_list.append(j) for j in range(mesh_fn.numVertices)]

        # apply new vertex colors to the mesh
        # (None is an optional dag modifier. You usually don't need it)
        mesh_fn.setVertexColors(new_vertex_colors, vertex_index_list, )

        for attr_name_ in ("castsShadows",
                           "receiveShadows",
                           "motionBlur",
                           "primaryVisibility",
                           "smoothShading",
                           "visibleInReflections",
                           "visibleInRefractions",
                           "doubleSided",
                           ):

            set_bool_val(mesh_fn, attr_name_, False)

        set_bool_val(mesh_fn, "displayColors", True)


def set_bool_val(mesh_fn, attr_name, attr_val):
    """

    Args:
        mesh_fn:
        attr_name:
        attr_val:

    Returns:

    """
    display_colors_plug = mesh_fn.findPlug(attr_name, False)
    display_colors_plug.setBool(attr_val)

    return True


def create_lin_hue_rand_satval(shell_number, color_base=None):
    """
    Creates a list of RGB OpenMaya.MColor instances with a length based on the Shell Number.
    It is linear in Hue, and Random in Saturation and Value.

    Args:
        shell_number(int):
        color_base(tuple):

    Returns:
        List():

    """
    # initializes random generator
    rng_gen = np.random.default_rng()

    if not color_base:
        hue_base = random.uniform(.1, .9)
        sat_base = random.uniform(.25, .45)
        val_base = random.uniform(.35, .35)

    else:
        hue_base, sat_base, val_base = colorsys.rgb_to_hsv(*color_base)

    hue = np.linspace(hue_base - .05, hue_base + .05,
                      num=shell_number,
                      endpoint=True,
                      retstep=False,
                      dtype=None,
                      axis=0,
                      )

    sat = rng_gen.uniform(sat_base - .05, sat_base + .05, shell_number)

    val = rng_gen.uniform(val_base - .05, val_base + .05, shell_number)

    # create the MColor instances
    generated_colors = list()

    for x in np.dstack((hue, sat, val,), )[0]:
        rgb_val = colorsys.hsv_to_rgb(*x)
        om_color = om2.MColor((*rgb_val, 1))

        generated_colors.append(om_color)

    return generated_colors


def apply_proxyslice(geo=None, color_base=None):
    """
    Function summarizes the application of a colored proxyslice.
    It expects an input in geo, if not it aborts.

    Args:
        geo(str): Name of the geometry that will be sliced.

    Returns:
        List(mesh_contents): The result geometries.
    """

    if not geo:
        raise ValueError("No geometry transform was given, aborting the operation")

    mesh_contents = create_proxyslice(geo_to_slice=geo)
    color_proxyslice(mesh_contents, color_base=color_base)

    return mesh_contents


def main():
    """
    Function summarizes the application of a colored proxyslice.
    It expects an input in geo, if not it aborts.

    Args:
        geo(str): Name of the geometry that will be sliced.

    Returns:
        list(mesh_contents): The result geometries.
    """

    mesh_contents = create_proxyslice()

    color_proxyslice(mesh_contents, color_base=(0.23529,
                                                0.24313,
                                                0.20005
                                                )
                     )


if __name__ == "__main__":
    main()
