# Author:     Johannes Wolz / Lead Rigging TD

"""
Utils code to manage openMaya workflows.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Import built-in modules
from builtins import str
from typing import Union
from future import standard_library

# Import third-party modules
from maya import OpenMaya # noqa: import error
from maya.api import OpenMaya as om2 # noqa: import error
from maya.api import OpenMayaAnim as oma2 # noqa: import error#

from pymel import core as pmc
# Import Maya specific modules
import pymel.core
import six
from typing import Optional
standard_library.install_aliases()

##########################################################
# FUNCTIONS
##########################################################


def get_mobject_om1(node):
    """
    Gives back an MObject.

    Args:
        node(str, pymel.core.PyNode()): The nodes name as
                                        string or as
                                        pymel.core.PyNode object.

    Return:
        OpenMaya.MObject: For given node.

    """
    if isinstance(node, pymel.core.PyNode):
        return node.__apimobject__()
    else:
        try:
            node = str(node)
            om_sel = OpenMaya.MSelectionList()
            om_sel.add(node)
            node = OpenMaya.MObject()
            om_sel.getDependNode(0, node)
            return node
        except:
            raise RuntimeError(
                "Unable to get MObject from given string: {}".format(node)
            )


def get_dag_path(node, type):
    """
    Gives back the DAG path on an given node.

    Args:
        node(str): The nodes unique name.
        type(OpenMaya node type): For example: OpenMaya.MFn.kMesh.

    Return:
         OpenMaya dag_path object.

    """
    om_sel = OpenMaya.MSelectionList()
    om_sel.add(node)
    iter_sel = OpenMaya.MItSelectionList(om_sel, type)
    dag_path = OpenMaya.MDagPath()
    iter_sel.getDagPath(dag_path)
    return dag_path


def get_m_obj_array(objects):
    """
    Returns the objects as MObjectArray.

    Args:
        objects(list): List filled with objects names as string.

    Return:
        OpenMaya.MObjectArray.

    """
    m_array = OpenMaya.MObjectArray()
    for idx, obj in enumerate(objects):
        m_array.insert(get_mobject_om1(obj), idx)
    return m_array


def rename_node(object: Union[str, om2.MObject],
                new_name: str) -> str:
    """
    Rename a node.

    Args:
        object(str, om2.MObject): Nodes name.
        new_name(str): New name.

    Return:
        Str (new_name): New node name.

    """

    if isinstance(object, six.string_types):
        m_obj = get_mobject_om2(object)

    elif isinstance(object, om2.MObject):
        m_obj = object

    else:
        raise TypeError(
            f"{object} is a not supported object type. You need a string or a om2.MObject"
        )

    m_dag_mod = om2.MDagModifier()
    m_dag_mod.renameNode(m_obj, new_name)

    m_dag_mod.doIt()

    return new_name


def get_m_int_array(index):  # check where this is used
    """
    Turns index into OpenMaya.MIntArray

    Args:
        index(int, list, OpenMaya.MIntArray):

    Returns:
        OpenMaya.MIntArray: the array created
    """
    if type(index) != OpenMaya.MIntArray:
        array = OpenMaya.MIntArray()
        if type(index) == list:
            for i in index:
                array.append(i)
        else:
            array.append(index)

        return array

    return index


def get_component(index):  # look when this is used
    """
    Turns index into OpenMaya.MFn.kMeshVertComponent

    Args:
        index(int, OpenMaya.MIntArray): Indices to create component for

    Returns:
         OpenMaya.MFn.kMeshVertComponent: Initialized component(s)
    """
    # convert input to an MIntArray if it not already is one
    indices = get_m_int_array(index)
    # initialize component(s)
    vert_comp = OpenMaya.MFn.kMeshVertComponent

    component = OpenMaya.MFnSingleIndexedComponent().create(vert_comp)
    OpenMaya.MFnSingleIndexedComponent(component).addElements(indices)

    return component


def get_mobject_om2(name):
    """
    Get the MObject wiht OpenMaya2

    Args:
        name(str): Maya object name.

    Returns:
        OpenMaya2.MObject

    """
    if isinstance(name, pmc.PyNode):
        name = name.longName()

    sel = om2.MGlobal.getSelectionListByName(name)
    return sel.getDependNode(0)


def get_mfn_dependency_node_om2(name):
    """
    Get the MObject wiht OpenMaya2

    Args:
        name(str): Maya object name.

    Returns:
        OpenMaya2.MObject

    """
    mobj = get_mobject_om2(name)
    return om2.MFnDependencyNode(mobj)

def get_mfn_deformer(name):
    mobj = get_mobject_om2(name)

    if mobj.hasFn(om2.MFn.kSkinClusterFilter):
        return oma2.MFnSkinCluster(mobj)

def get_dag_path_om2(name):
    """
    Get the dag path with OpenMaya2

    Args:
        name(str): Maya object name.

    Returns:
        OpenMaya2.MDagPath

    """

    if isinstance(name, pmc.PyNode):
        name = name.longName()

    sel = om2.MGlobal.getSelectionListByName(name)
    return sel.getDagPath(0)


def get_mfn_skin_om2(skin_ob):
    """
    Get the MFnSkinCluster with OpenMaya2.

    Args:
        skin_ob(MObject): The MObject of the skincluster.

    Returns:
        OpenMaya2.MFnSkinCluster

    """
    print(skin_ob)
    if isinstance(skin_ob, pmc.PyNode):
        skin_ob = get_mobject_om2(skin_ob.longName())
    print("skin_object:", skin_ob)
    print("skin_object_type:", type(skin_ob))
    return oma2.MFnSkinCluster(skin_ob)


def get_mfn_mesh_om2(mesh_ob):
    """
    Get the MFnMesh with OpenMaya2.

    Args:
        mesh_ob(MObject): The MObject of the mesh.

    Returns:
        OpenMaya2.MFnMesh

    """
    if isinstance(mesh_ob, pmc.PyNode):
        mesh_ob = get_mobject_om2(mesh_ob.longName())
    return om2.MFnMesh(mesh_ob)


def get_complete_components_om2(mesh):
    """
    Return an object component for all the vertices
    on the specified mesh, for specifying vertices
    in the skin weights transfer tools.

    Args:
        mesh: Mesh you wish to have components for type mesh: om2.MFnMesh or pm.nt.Mesh

    Returns:
            MObject: Representing the selection of all vertices on the mesh
            as om2.MFnSingleIndexedComponent

    """
    if mesh.hasFn(om2.MFn.kMesh):
        fn_mesh = om2.MFnMesh(mesh)
        vtx_count = fn_mesh.numVertices
        comp_type = om2.MFn.kMeshVertComponent

        fn = om2.MFnSingleIndexedComponent()
        component = fn.create(comp_type)
        fn.addElements(range(vtx_count))

    elif mesh.hasFn(om2.MFn.kNurbsCurve):
        fn_curve = om2.MFnNurbsCurve(mesh)
        vtx_count = fn_curve.numCVs
        comp_type = om2.MFn.kCurveCVComponent

        fn = om2.MFnSingleIndexedComponent()
        component = fn.create(comp_type)
        fn.addElements(range(vtx_count))

    elif mesh.hasFn(om2.MFn.kNurbsSurface):
        fn_surf = om2.MFnNurbsSurface(mesh)
        u_count = fn_surf.numCVsInU
        v_count = fn_surf.numCVsInV

        fn = om2.MFnDoubleIndexedComponent()
        component = fn.create(om2.MFn.kSurfaceCVComponent)

        # Add all CVs in U/V grid
        for u in range(u_count):
            for v in range(v_count):
                fn.addElement(u, v)

        vtx_count = u_count * v_count

    else:
        raise RuntimeError(f"Object {mesh} is neither mesh, curve, nor surface")

    return component, vtx_count


def get_tagged_nodes(tag: Optional[str] = None, mfn_type: Optional[om2.MFn] = None) -> set:
    """
    Searches the whole DG for Nodes that have a specific attribute as tag.
    What is not implemented yet is to search for the TYPE of tag attribute (eg: bool).

    Args:
        tag (str, None):
        mfn_type (str): YET TO BE IMPLEMENTED!

    Returns:
        Set (found_node_names): All found nodes as Set of absolute names.
    """
    found_node_names = set()

    if not tag:
        return found_node_names

    dg_iteration = om2.MItDependencyNodes()
    dg_mfn = om2.MFnDependencyNode()

    while not dg_iteration.isDone():

        dg_object = dg_iteration.thisNode()

        if mfn_type and not dg_object.hasFn(mfn_type):
            dg_iteration.next()
            continue

        dg_mfn.setObject(dg_object)

        if dg_mfn.hasAttribute(tag):
            found_node_names.add(dg_mfn.absoluteName().lstrip(":"))

        dg_iteration.next()

    return found_node_names


def get_node_iterations(name: Optional[str] = None) -> list:
    """
    Searches the whole DG for Nodes that have a .

    Args:
        tag (str, None):
        tag_type (str): YET TO BE IMPLEMENTED!

    Returns:
        Set (found_node_names): All found nodes as Set of absolute names.
    """

    found_node_names = set()
    sel = om2.MSelectionList()

    #sel.add(op_name.replace(self.comp_index_name, "*")

def is_of_type(m_object, fn_type):
    """
    Check if the MObject has a certain MFn Type.

    Args:
        m_object(om2.MObject):
        fn_type(om2.MFn):

    Returns:
        Bool
    """
    return m_object.hasFn(fn_type)


def get_long_name(dag_name: str) -> str:
    """
    Gives back the long name of the input string as a node.

    Args:
        dag_name(str): Name of the

    Returns:
        Str: Full name of the object.
    """
    sel = om2.MSelectionList()

    try:
        sel.add(dag_name)

    except (RuntimeError, TypeError):  # If it doesn't exist, or is not a string, or already an MObject, it will error
        return False

    sel_dag = sel.getDagPath(0)

    return str(sel_dag.fullPathName())

