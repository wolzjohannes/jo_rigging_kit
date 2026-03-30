"""
www.pixomondo.com
Date: 07 / 02 / 2022

pixoSkin module
category : Rigging
subcategory : utils
author : Michele Trabona / Rigging TD

"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
#   system modules
from future import standard_library
standard_library.install_aliases()
import time

#   maya modules
import pymel.core as pm

from . import data
from . import joint as pxojt

import mgear.core.skin as skin



try:
    from ngSkinTools.mllInterface import MllInterface
except:
    pm.warning("ngSkinTools not available")
try:
    from ngSkinTools2 import api as ngst_api
except:
    pm.warning("ngSkinTools2 not available")



def pixo_import_skin(path,geo_list = None):
    latest_vers = []
    if geo_list:
        for geo in geo_list:
            geo_skin = data.get_the_latest_file_version(path,
                                                        file_name=geo)
            latest_vers.append(geo_skin)
    else:
        latest_vers = data.get_all_latest_versions(path)
    for version in latest_vers:
        file_path_name = r"{}\{}".format(path, version)
        print(file_path_name)
        skin.importSkin(filePath=file_path_name)
        pm.select(cl = 1)


def pixo_export_skin (path,objects):
    start_time = time.time()
    pxojt.unlock_all_joints()

    for obj in objects:
        file_name = data.next_previous_version_file_name(path,
                                                         obj,
                                                         with_ext=0)
        file_path_name = r"{}\{}.jSkin".format(path, file_name)
        skin.exportSkin(filePath=file_path_name, objs=[obj])

    end_time = time.time()
    elapsed_time = end_time - start_time
    print('\n******* skin export finished *******\ntime needed to execute: {}\n\n'.format(elapsed_time))

def ngSkin2_transfer_weights(
    source,
    target,
    name_mapping_list=[("L_*", "L_*"), ("R_*", "R_*"), ("C_*", "C_*")],
    jnt_label_matching=True,
    jnt_distance_matching=True,
    jnt_name_matching=True,
):
    """
    Will transfer skinWeights and layer data from souce object to target object.
    If target object has no skincluster will create a new one with same inluences
    from the source skinCluster.
    If source object has no ngSkin layer initialized it will create a baselayer.
    No need to create ngSkin layers for the target objects. Will do by default.

    Args:
        source(pm.PyNode()): The source object.
        target(pm.PyNode()): The target object.
        name_mapping_list(list): The name mapping.
        Example: [("L_*", "L_*"), ("R_*", "R_*"), ("C_*", "C_*")]
        jnt_label_matching(bool): Enabel label matching.
        jnt_distance_matching(bool): Enable distance matching.
        jnt_name_matching(bool): Enable_distance matching.

    Return:
        True if successfully. None if target object has no skinCluster.

    """
    pm.select(cl=True)
    source_skinCluster = source.listHistory(type="skinCluster")
    if not source_skinCluster:
        pm.error("{} has no skinCluster.".format(source.name()))
        return

    source_skinCluster = source_skinCluster[0]
    infl_config = ngst_api.InfluenceMappingConfig.transfer_defaults()
    infl_config.globs = name_mapping_list
    infl_config.use_label_matching = jnt_label_matching
    infl_config.use_distance_matching = jnt_distance_matching
    infl_config.use_name_matching = jnt_name_matching
    influence_list = source_skinCluster.getInfluence()
    target_skinCluster = target.listHistory(type="skinCluster")

    if not target_skinCluster:
        pm.select(source)
        pm.select(target, add=True)
        target_skinCluster = pm.skinCluster(influence_list, target, tsb=True)

    try:
        source_layers = ngst_api.init_layers(source.name())
        source_base_layer = source_layers.add("base_weights")
        ngst_api.transfer_layers(
            source.name(),
            target.name(),
            vertex_transfer_mode="closestPoint",
            influences_mapping_config=infl_config,
        )
        print("# Info: Skinweigts and ngSkinLayers transfered from {} to {}".format(source.name(), target.name()))
        source_layers.delete(source_base_layer)
        return True

    except:
        pm.error(
            "Unable to transfer skinweights from {} to {}".format(
                source, target
            )
        )


def ngSkin_transfer_weights(source, target):
    pm.select(cl=True)
    source_skinCluster = source.listHistory(type="skinCluster")
    if not source_skinCluster:
        pm.error("{} has no skinCluster.".format(source.name()))
        return

    source_skinCluster = source_skinCluster[0]
    influence_list = source_skinCluster.getInfluence()
    target_skinCluster = target.listHistory(type="skinCluster")
    if not target_skinCluster:
        pm.select(source)
        pm.select(target, add=True)
        target_skinCluster = pm.skinCluster(influence_list, target, tsb=True)
    try:
        mll = MllInterface()
        influenceDic = {}
        mll.setCurrentMesh(source.name())
        mll.initLayers()
        mll.deleteLayer(0)
        BaseLayer = mll.createLayer(name="base_weights")
        influenceList = mll.listInfluenceIndexes()
        mll.setCurrentMesh(target.name())
        mll.initLayers()
        mll.setCurrentMesh(source.name())
        for influ in influenceList:
            influenceDic[influ] = influ
        mll.transferWeights(target.name(), influenceDic, "closestPoint")
        mll.setCurrentMesh(source.name())
        mll.deleteLayer(BaseLayer)
        print("# Info: Skinweights transfered from {} to {}. DONE".format(
            source, target
        ))
        return True
    except:
        pm.error(
            "Unable to transfer skinweights from {} to {}".format(
                source, target
            )
        )





"""
import json
import legacy_rig_lib.utils.data as data
import pymel.core as pm


def remove_unused_influences(path_data):
    weight_info = data.read_json_file(path_data)
    wts = weight_info['objDDic'][0]['weights']
    
    wts_new = {inf:wts[inf] for inf in wts if bool(wts.get(inf))}

    weight_info['objDDic'][0]['weights'] = wts_new
    with open(path_data, 'w') as fp:
        json.dump(weight_info, fp, indent=4, sort_keys=True)
    

def remove_all_folder_unused_influences(path_data):
    start = pm.timerX()
    
    files = data.read_folders_files(path_data)
    
    for file in files:
        path = "{}/{}".format(path_data,file)
        remove_unused_influences(path)
    elapsed_time = pm.timerX(startTime=start)
    print(('Total time: ', elapsed_time))


main_path= r"X:\redgun_reg-6344\_library\assets\props\prp_saddleArrax\rig_prop\data\skincluster"
remove_all_folder_unused_influences(main_path)
"""





"""

import cPickle as pickle
import json
import legacy_rig_lib.utils.data as data
reload(data)
import pymel.core as pm
def search_replace_influences_names(main_path,search,replace):
    dict_ = data.read_json_file(main_path)
    wts = dict_['objDDic'][0]['weights']
    for inf in wts.keys():
        new_inf_name = inf.replace(search,replace)
        wts[new_inf_name]= wts.pop(inf)
    dict_['objDDic'][0]['weights'] =   wts     
    with open(main_path, 'w') as fp:
        json.dump(dict_, fp, indent=4, sort_keys=True)
    

def search_replace_folder_influences_names(main_path,search,replace):
    start = pm.timerX()
    
    files = data.read_folders_files(main_path)
    
    for file in files:
        path = "{}/{}".format(main_path,file)
        search_replace_influences_names(path,search,replace)
    totalTime = pm.timerX(startTime=start)
    print(('Total time: ', totalTime))
    

main_path= r"X:\redgun_reg-6344\_library\assets\props\prp_saddleArrax\rig_prop\data\skincluster"
search_replace_folder_influences_names(main_path,"_Jnt","_jnt")



import pymel.core as pm
    
def findRelatedSkinCluster(geo):
    skincluster = mel.eval('findRelatedSkinCluster ' + geo)
    if skincluster == '' or len(pm.ls(skincluster, type='skinCluster')) == 0:
        skincluster = pm.ls(pm.listHistory(geo), type='skinCluster')
        if len(skincluster) == 0:
            return None
    return pm.ls(skincluster)[0]
def copySkinWeightBetweenMesh(selection=pm.ls(sl=True)):

    sourceMesh = selection[0]
    destinationMesh = selection[1]
    sourceSkinCluster = mel.eval('findRelatedSkinCluster ' + sourceMesh)
    destinationSkinCluster = mel.eval('findRelatedSkinCluster ' + destinationMesh)
    pm.copySkinWeights(ss=sourceSkinCluster, ds=destinationSkinCluster, mirrorMode='YZ',
                       surfaceAssociation='closestPoint', influenceAssociation='closestJoint')
def copyBind(source, destination, sa='closestPoint', ia='closestJoint'):

    # Get Shape and skin from Object
    skinCluster = findRelatedSkinCluster(source)
    if skinCluster:
        skin = skinCluster
    else:
        print('Missing source SkinCluster')
    # Get joint influence of the skin
    influnces = skin.getInfluence(q=True)  # influences is joint
    # Bind destination Mesh
    # pm.select(influnces[0])
    # pm.select(destination, add=True)
    # mel.eval('SmoothBindSkin;')
    pm.skinCluster(influnces, destination, dr=4.0)
    # copy skin wheights form source
    pm.select(source)
    pm.select(destination, add=True)
    pm.copySkinWeights(noMirror=True, surfaceAssociation=sa, influenceAssociation=ia)
    pm.select(cl=True)

sel = pm.selected()
for e in sel[1:]:
    copyBind(sel[0], e)

import cPickle as pickle
import json
import legacy_rig_lib.utils.data as data
import pymel.core as pm

def get_short_name(main_path):
    dict_ = data.read_json_file(main_path)
    wts = dict_['objDDic'][0]['weights']
    for inf in wts.keys():
        new_inf_name = inf.split('|')[-1]
        wts[new_inf_name]= wts.pop(inf)
    dict_['objDDic'][0]['weights'] = wts     
    with open(main_path, 'w') as fp:
        json.dump(dict_, fp, indent=4, sort_keys=True)
    

def get_folder_nice_names(main_path):
    start = pm.timerX()
    
    files = data.read_folders_files(main_path)
    
    for file in files:
        path = "{}/{}".format(main_path,file)
        get_short_name(path)
    totalTime = pm.timerX(startTime=start)
    print(('Total time: ', totalTime))
    

main_path= r"X:\redgun_reg-6344\_library\assets\props\prp_saddleSyrax\rig_prop\data\skincluster"
get_folder_nice_names(main_path)

"""