from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
# export skin weights

#   python base libraries
from builtins import dict
from builtins import open
from builtins import int
from builtins import round
from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import range
import os
import json
import numpy as np
from time import time as timer
from datetime import datetime


#   maya libraries
import maya.OpenMaya as om
import pymel.core as pm

import logging

import rig_lib.utils.data as data

logging.basicConfig(level=logging)
_LOGGER = logging.getLogger(__name__ + ".py")

''' sample code to be used in scene
import legacy_rig_lib.utils.imp_exp_skinning as newSkin
reload(newSkin)

newSkin.export_skin_weights()

newSkin.import_skin_weights()

'''

allowed_object_types = ['mesh', 'nurbsSurface']

path_file = pm.sceneName()
just_path_file = os.path.dirname(path_file)

g_bind_path = os.path.join(just_path_file, 'data', 'gBind')
g_skin_path = os.path.join(just_path_file, 'data', 'gSkin')


def check_and_create_path(path):
    if not os.path.exists(path):
        try:
            os.mkdir(path)
            return path

        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise

    else:
        return path


#   create structure for version control
def get_time():
    now = datetime.now()
    return now.strftime("%H_%M_%S")


def get_date():
    now = datetime.now()
    return now.strftime("%Y_%m_%d")


def check_and_create_date(path_object):
    date_path = os.path.join(path_object, get_date())
    date_path = check_and_create_path(date_path)

    time_path = os.path.join(date_path, get_time())
    time_path = check_and_create_path(time_path)
    return time_path


#   look for latest file in file structure
def get_latest_path(path_object):
    files = os.listdir(path_object)
    paths = [os.path.join(path_object, basename) for basename in files]

    if not paths:
        return False

    newest_date = max(paths, key=os.path.getctime)
    files = os.listdir(newest_date)
    paths = [os.path.join(newest_date, basename) for basename in files]

    if not paths:
        return False

    newest_time = max(paths, key=os.path.getctime)
    return newest_time


def write_json_file(skinning_data, file_path, file_name):
    file_path_name = os.path.join(file_path, file_name)

    with open(file_path_name, 'w') as out_file:
        json.dump(skinning_data, out_file)


def get_geo_root():
    asset_geo_roots = [x for x in pm.ls(transforms=True)
                       if pm.objExists('{}.PXM_asset_geo_root'.format(x))
                       and x.PXM_asset_geo_root.get()]

    if not asset_geo_roots or len(asset_geo_roots) > 1:
        raise ValueError

    else:
        return asset_geo_roots[0]


def get_selected_object_skinned_joints(geo):
    skin_cluster_str = 'findRelatedSkinCluster("{}")'.format(geo)
    skin_cluster = pm.mel.eval(skin_cluster_str)
    jnts = cmds.ls(cmds.skinCluster(skin_cluster, query=True, inf=True))
    return jnts


def write_dict(name_geo, joints, skin_cluster):
    element_dic = {"name_geo": name_geo, "joints": joints, "skin_cluster": skin_cluster}
    return element_dic


def export_skin_weights():
    _LOGGER.info("SKIN EXPORT STARTED")

    sel = pm.selected()
    if not sel:
        geo_root = get_geo_root()
        all_transforms = pm.listRelatives(geo_root,
                                          allDescendents=True,
                                          type='transform'
                                          )

        sel = all_transforms

    if not sel:
        raise ValueError('nothing was selected')

    geometries = [x for x in sel
                  if x.getShape()
                  and x.getShape().type() in allowed_object_types]

    if not geometries:
        raise ValueError('there were no valid geometries in the selection')

    geometry_amount = len(geometries)
    _LOGGER.info("'{amount}' valid geometries found in scene".format(amount=geometry_amount))

    vers_skin_path = check_and_create_date(g_skin_path)
    vers_bind_path = check_and_create_date(g_bind_path)

    total_start_time = timer()
    for geo in geometries:
        geometry_name = geo.name().split(":")[-1]
        file_name = '{}.json'.format(geometry_name)

        skin_clusters = pm.ls(pm.listHistory(geo), type='skinCluster')

        if not skin_clusters:
            continue
        skin_cluster = skin_clusters[0]
        skin_cluster.normalizeWeights.set(1)
        jnts = get_selected_object_skinned_joints(geo)
        skinning_data = write_dict(geometry_name, jnts, skin_cluster.shortName())
        write_json_file(skinning_data, vers_bind_path, file_name)
        pm.deformerWeights('{}'.format(file_name),
                           export=True,
                           deformer=skin_cluster,
                           format="JSON",
                           path=vers_skin_path
                           )
        print('')
    total_end_time = format(round(timer() - total_start_time, 4), '.4f')
    _LOGGER.info("\nSKIN EXPORT CONCLUDED\nELAPSED TIME TAKEN: {}\nCLUSTERS EXPORTED: {} / {}\n________________________".format(total_end_time,
                                                                                                                                1,
                                                                                                                                2
                                                                                                                                ))


# import skin weights
def import_skin_weights():
    _LOGGER.info("\nSKIN IMPORT STARTED\n")

    vers_skin_path = get_latest_path(g_skin_path)
    vers_bind_path = get_latest_path(g_bind_path)

    files = data.read_folders_files(vers_bind_path)
    pm.select(d=True)
    temp_jnt = pm.joint(name="TEMP_jnt")
    pm.select(cl=True)

    name_space = get_geo_root().shortName().split(':')[0]

    max_length = len((max(files, key=len)))
    file_amount = len(files)
    file_count = 0

    _LOGGER.info("{amount} skin files found in directory".format(amount=file_amount))
    total_start_time = timer()
    for file in files:
        file_length = len(file)
        padding_adjust_length = max_length - file_length
        path = os.path.join(vers_bind_path, file)

        start_time = timer()

        #   get data from file
        file_name = '{}'.format(file)
        skinning_data = data.read_json_file(path)
        name_geo = skinning_data['name_geo']
        joints = skinning_data['joints']
        skin_cluster = skinning_data['skin_cluster']

        #   check file data missing
        if not (name_geo and joints and skin_cluster):
            raise ValueError

        #   create whole name
        composed_name = '{name_space}:{name_geo}'.format(name_space=name_space,
                                                         name_geo=name_geo)

        if pm.objExists(skin_cluster):
            pm.skinCluster(composed_name, edit=True, unbind=True)

        skin_cls = pm.skinCluster(temp_jnt,
                                  composed_name,
                                  name=skin_cluster,
                                  toSelectedBones=True,
                                  bindMethod=0,
                                  skinMethod=0,
                                  normalizeWeights=1,
                                  removeUnusedInfluence=False
                                  )

        pm.skinCluster(skin_cluster,
                       edit=True,
                       addInfluence=joints,
                       wt=0
                       )

        pm.deformerWeights(file_name,
                           im=True,
                           deformer=skin_cluster,
                           format="JSON",
                           path=vers_skin_path,
                           method="index"
                           )

        pm.skinCluster(skin_cluster,
                       e=True,
                       ri=temp_jnt
                       )

        end_time = format(round(timer() - start_time, 4), '.4f')
        file_count += 1
        _LOGGER.info("imported:'{data_file}'{buffer}in: {seconds} seconds".format(data_file=file_name,
                                                                                  buffer=''.ljust(padding_adjust_length + 5, ' '),
                                                                                  seconds=str(end_time)))
    total_end_time = format(round(timer() - total_start_time, 4), '.4f')

    pm.delete(temp_jnt)
    _LOGGER.info("\nSKIN IMPORT CONCLUDED\nELAPSED TIME TAKEN: {}\nCLUSTERS IMPORTED: {} / {}\n________________________".format(total_end_time,
                                                                                                                                file_count,
                                                                                                                                file_amount
                                                                                                                                ))


def om_skin_export():
    # poly mesh and skinCluster name
    cluster_node = pm.PyNode('skinCluster2287')
    cluster_name = cluster_node.shortName().split(':')[-1].split('|')[-1]

    skin_fn = cluster_node.__apimfn__()

    shape_node = pm.PyNode('vha_01:vhagarBody_C_001_high_geoShape')
    shape_fn = shape_node.__apimfn__()

    #   point positions
    mesh_points = om.MPointArray()
    shape_fn.getPoints(mesh_points, om.MSpace.kWorld)
    point_positions = dict()

    total_start_time = timer()

    for vertex_id in range(mesh_points.length()):
        point_positions[vertex_id] = [mesh_points[vertex_id][0], mesh_points[vertex_id][1], mesh_points[vertex_id][2]]

    print(point_positions)
    print(format(round(timer() - total_start_time, 4), '.4f'))

    #   vertex position getter
    total_start_time = timer()
    vertex_positions = [[mesh_points[x][0], mesh_points[x][1], mesh_points[x][2]]
                        for x in range(mesh_points.length())]
    faster = np.array(vertex_positions)
    print(faster)
    print(format(round(timer() - total_start_time, 4), '.4f'))

    #   skincluster
    # get the MDagPath for all influence
    inf_dagpaths = om.MDagPathArray()
    skin_fn.influenceObjects(inf_dagpaths)

    # create a dictionary whose key is the MPlug index id and
    # whose value is the influence list id
    inf_ids = dict()
    influences = list()

    for x in range(inf_dagpaths.length()):
        inf_path = inf_dagpaths[x].fullPathName()
        inf_id = int(skin_fn.indexForInfluenceObject(inf_dagpaths[x]))
        inf_ids[inf_id] = x
        influences.append(inf_path)

    # get the MPlug for the weightList and weights attributes
    weight_list_plug = skin_fn.findPlug('weightList')
    weight_list_attribute = weight_list_plug.attribute()

    weight_plug = skin_fn.findPlug('weights')
    weight_attribute = weight_plug.attribute()

    weight_influence_ids = om.MIntArray()

    # the weights are stored in dictionary, the key is the vertId,
    # the value is another dictionary whose key is the influence id and
    # value is the weight for that influence
    weights = dict()
    for vertex_id in range(weight_list_plug.numElements()):
        vertex_weights = {}
        # tell the weights attribute which vertex id it represents
        weight_plug.selectAncestorLogicalIndex(vertex_id, weight_list_attribute)

        # get the indice of all non-zero weights for this vert
        weight_plug.getExistingArrayAttributeIndices(weight_influence_ids)

        # create a copy of the current weight_plug
        influence_plug = om.MPlug(weight_plug)
        for inf_id in weight_influence_ids:
            # tell the influence_plug it represents the current influence id
            influence_plug.selectAncestorLogicalIndex(inf_id, weight_attribute)

            # add this influence and its weight to this verts weights
            try:
                vertex_weights[inf_ids[inf_id]] = influence_plug.asDouble()
            except KeyError:
                # assumes a removed influence
                pass

        weights[vertex_id] = vertex_weights
    print('weights:')
    print(weights)


