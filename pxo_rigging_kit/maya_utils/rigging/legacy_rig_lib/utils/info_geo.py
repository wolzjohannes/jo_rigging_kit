from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
import pymel.core as pm
import maya.api.OpenMaya as om
import operator


def get_vertex_pos_of_mesh(mesh):
    selection_list = om.MSelectionList()
    selection_list.add(mesh)

    dag_path = selection_list.getDagPath(0)
    mpoint_array = om.MFnMesh(dag_path).getPoints()

    point_dic = {}
    for mpoint in mpoint_array:
        index = om.MFnMesh(dag_path).getClosestPoint(mpoint, space=om.MSpace.kWorld)[1]
        face_vertices = om.MFnMesh(dag_path).getPolygonVertices(index)

        vertex_distances = ((vertex, om.MFnMesh(dag_path).getPoint(vertex, om.MSpace.kWorld).distanceTo(mpoint))
                            for vertex in face_vertices)

        point_dic[min(vertex_distances, key=operator.itemgetter(1))[0]] = [mpoint[0], mpoint[1], mpoint[2]]

    return point_dic


def get_nearest_vertices_to_list_pos(mesh, list_pos):
    selection_list = om.MSelectionList()
    selection_list.add(mesh)

    dag_path = selection_list.getDagPath(0)
    mfn_mesh = om.MFnMesh(dag_path)

    point_dic = {}
    for pos in list_pos:
        mpoint = om.MPoint(pos)

        index = mfn_mesh.getClosestPoint(mpoint, space=om.MSpace.kWorld)[1]
        face_vertices = mfn_mesh.getPolygonVertices(index)

        vertex_distances = ((vertex, mfn_mesh.getPoint(vertex, om.MSpace.kWorld).distanceTo(mpoint))
                            for vertex in face_vertices)

        point_dic[min(vertex_distances, key=operator.itemgetter(1))[0]] = pos

    return point_dic

def getting_matching_verices(meshA, meshB, tollerance = 0.1):
    geoA_vertices_pos = get_vertex_pos_of_mesh(meshA)
    geoB_vertices_pos = get_vertex_pos_of_mesh(meshB)
    list_connections = []
    for key_a in list(geoA_vertices_pos.keys()):
        vec_a = om.MVector(geoA_vertices_pos[key_a][0],
        geoA_vertices_pos[key_a][1],
        geoA_vertices_pos[key_a][2])
        for key_b in list(geoB_vertices_pos.keys()):
            vec_b = om.MVector(geoB_vertices_pos[key_b][0],
            geoB_vertices_pos[key_b][1],
            geoB_vertices_pos[key_b][2])
            if (vec_a-vec_b).length() < tollerance:
                list_connections.append((key_a,key_b))
    list_connections =  tuple(list_connections)
    return list_connections

def connect_meshes_inOut(mesh_a, mesh_b,meshDisplay = (0,0)):
    shape_a = get_first_last_def_shape(mesh_a,shape = meshDisplay[0])
    shape_b = get_first_last_def_shape(mesh_b,shape = meshDisplay[1])
    pm.connectAttr('{}.outMesh'.format(shape_a), '{}.inMesh'.format(shape_b), f=1)


def get_first_last_def_shape(mesh, shape = 1):
    shapes = pm.listRelatives(mesh, shapes=1)
    for sh in shapes:
        if pm.getAttr('{}.intermediateObject'.format(sh)) == shape:
            return sh


def combine_meshes_list(meshes, geo_name = None, new_mesh = 1):
    if not geo_name:
        geo_name = 'combined_geo'
    if new_mesh:
        meshes = pm.duplicate(meshes)
    combined_mesh = pm.polyUnite(meshes, ch=0, mergeUVSets=1, name=geo_name)[0]
    return combined_mesh

def copy_meshes_list(meshes, searchReplace = None,parent = None):
    dup_list = []
    for mesh in meshes:
        new_mesh = pm.duplicate(mesh,n = mesh.name().replace(searchReplace[0],searchReplace[1]))[0]
        if parent:
            pm.parent(new_mesh,parent)
        else:
            pm.parent(new_mesh,w  = 1)
        dup_list.append(new_mesh)
    return dup_list

'''
import legacy_rig_lib.utils.info_geo as ing
reload(ing)
import pymel.core as pm
main_geo = 'pSphere1'
geos_association_tuples = {}
for geo in pm.selected():
    vert_associatiion_tuple = ing.getting_matching_verices(main_geo,geo.name())
    geos_association_tuples[geo.name()] = vert_associatiion_tuple
bifrost_node = 'bifrostGraphShape1'
for main_it, key in enumerate( geos_association_tuples.keys()):
    for second_it, (main_id, child_id) in enumerate(geos_association_tuples[key]): 
        pm.setAttr('{}.main_geo_IDs[{}].main_geo_IDs_A[{}]'.format(bifrost_node,
                                                                    main_it,
                                                                    second_it),main_id)
        pm.setAttr('{}.children_IDs[{}].children_IDs_A[{}]'.format(bifrost_node,
                                                                    main_it,
                                                                    second_it),child_id)
                                                                    '''