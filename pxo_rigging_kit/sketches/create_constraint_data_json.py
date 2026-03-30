import os

import pymel.core as pmc
import maya.cmds as cmds
from pxo_rigging_kit.maya_utils import pymel_utils
from pxo_rigging_kit.maya_utils import paths_utils
from pxo_rigging_kit import paths
from pxo_rigging_kit.maya_utils import assembly_utils

JSON_FILE_NAME = "pxo_constraint_data.json"
DEBUG = False

def create_asset_geo_constraint_data(asset_root):
    constraint_dict_list = []
    constraints = cmds.listRelatives(asset_root, type="parentConstraint", ad=True) + cmds.listRelatives(asset_root, type="scaleConstraint", ad=True)
    for node in constraints:
        mo = False
        con_type = cmds.nodeType(node)
        trgt_list = cmds.parentConstraint(node, q=True, targetList=True)
        if not trgt_list:
            trgt_list = cmds.scaleConstraint(node, q=True, targetList=True)
        if con_type == "scaleConstraint":
            target_offset = cmds.getAttr(f"{node}.offset")[0]
            if float(sum(target_offset)) != 3.0:
                mo=True
        if con_type == "parentConstraint":
            target_offset = cmds.getAttr(f"{node}.target[0].targetOffsetTranslate")[0] + cmds.getAttr(f"{node}.target[0].targetOffsetRotate")[0]
            if float(sum(target_offset)) != 0.0:
                mo=True
        d_connections = set(cmds.listConnections(node, d=True,s=False, type="transform"))
        constrainted_obj = [node_ for node_ in d_connections if cmds.nodeType(node_) == "transform"][0]
        constraint_dict_list.append({"constraint_type": con_type, "target_list": trgt_list, "constrained_obj": constrainted_obj, "maintainOffset": mo})
    return constraint_dict_list
    
def create_asset_geo_constraint_data_by_asset_assembly():
    asset_assembly_node = assembly_utils.get_asset_assembly_nodes_from_scene()[0]
    asset_assembly_dict = asset_assembly_node.get_assembly_data()[0]
    asset_root = str(asset_assembly_dict.get("asset_root", None).getParent().name())
    return create_asset_geo_constraint_data(asset_root)
    
def save_asset_geo_constraint_data_json():
    result = create_asset_geo_constraint_data_by_asset_assembly()
    asset_data_folder = paths_utils.get_project_paths(pmc.sceneName())
    paths.write_json_file(result, asset_data_folder, JSON_FILE_NAME)
    
def create_constraints_by_data(data_dict_list):
    for data_dict in data_dict_list:
        constraint_type = data_dict.get("constraint_type")
        target = data_dict.get("target_list")[0]
        constraint_obj = [data_dict.get("constrained_obj")]
        maintainOffset = data_dict.get("maintainOffset")
        if not cmds.objExists(constraint_obj[0]):
            if DEBUG:
                cmds.warning(f"Object not exist {constraint_obj[0]}. Will try to find others with any namespace")
            tmp_name = f"*:*{constraint_obj[0].split(':')[-1]}"
            constraint_obj = pmc.ls(tmp_name)
            if not constraint_obj:
                if DEBUG:
                    cmds.warning(f"No object with a any other namespace {tmp_name} found.")
                continue
        if not cmds.objExists(target):
            if DEBUG:
                cmds.warning(f"Object not exist {target}.")
            continue
        if constraint_type == "parentConstraint":
            for node in constraint_obj:
                print(cmds.parentConstraint(target, str(node), mo=maintainOffset))
        if constraint_type == "scaleConstraint":
            for node in constraint_obj:
                print(cmds.scaleConstraint(target, str(node), mo=maintainOffset))

def import_and_apply_constraint_data():
    asset_data_folder = paths_utils.get_project_paths(pmc.sceneName())
    read_file = os.path.join(asset_data_folder, JSON_FILE_NAME)
    if not os.path.exists(read_file):
        raise LookupError(f"{read_file} not exist")
    constraint_data = paths.read_json_file(read_file)
    create_constraints_by_data(constraint_data)
    
import_and_apply_constraint_data()

# save_asset_geo_constraint_data_json()
