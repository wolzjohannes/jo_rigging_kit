"""
www.pixomondo.com
Date: 09 / 02 / 2022

data module
category : Rigging
subcategory : utils
author : Michele Trabona / Rigging TD

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from builtins import int
from builtins import open
from future import standard_library
standard_library.install_aliases()
from builtins import str
import re
import os
import json
import pymel.core as pm
from . import name
import pixo_naming


def get_model_dir():
    asset_root = pixo_naming.get("asset_root", {})
    return asset_root + "/mdl/_publish"


def make_rig_dir(asset_name):
    asset_root = pixo_naming.get("asset_root", {})
    set_asset_folders(asset_root, asset_name)


def get_rigging_main_dir(type="face"):
    asset_root = pixo_naming.get("asset_root", {})
    if type == "face":
        return asset_root + "/rig_face"
    if type == "prop":
        return asset_root + "/rig_prop"
    elif type == "lod2":
        return asset_root + "/rig_2/_publish"


def set_asset_folders(path, asset_name, specific="face"):
    asset_dic = {"first_layer": ["data",
                                 "work_scenes",
                                 "builder",
                                 "controlShapes",
                                 "controlShapesLOD",
                                 "in_progress",
                                 "transfer"],

                 "second_layer": {"data": ["skincluster",
                                           "deformers",
                                           "constraint"]}}

    asset_main_path = "{}/{}/rig_{}".format(path, asset_name, specific)
    folder_check(asset_main_path)

    for first_layer_element in asset_dic["first_layer"]:
        asset_first_layer_element_path = "{}/{}".format(asset_main_path,
                                                        first_layer_element)
        folder_check(asset_first_layer_element_path)

        if len(list(asset_dic["second_layer"].keys())) > 0:
            second_layer_list = None
            try:
                second_layer_list = asset_dic["second_layer"][first_layer_element]

            except:

                pass

            if second_layer_list != None:
                for second_layer_element in asset_dic["second_layer"][first_layer_element]:
                    asset_second_layer_element_path = "{}/{}".format(asset_first_layer_element_path,
                                                                     second_layer_element)
                    folder_check(asset_second_layer_element_path)


def folder_check(dirPath):

    if not os.path.exists(dirPath):
        os.makedirs(dirPath)


def write_json_file(data, path, file_name):

    file_name = next_previous_version_file_name(path,
                                                file_name,
                                                with_ext=0
                                                )

    file_path_name = "{}/{}.json".format(path, file_name)
    with open(file_path_name, 'w') as out_file:
        json.dump(data, out_file)


def read_json_file(path):
    f = open(path)
    # returns JSON object as
    # a dictionary
    data = json.load(f)
    return data


def write_maya_file(path,file_name, ext="mb"):

    file_name = next_previous_version_file_name(path,
                                                file_name,
                                                with_ext=0
                                                )

    file_path_name = "{}/{}.{}".format(path, file_name, ext)
    pm.saveAs(file_path_name, f=True)


def export_maya_file (path, file_name, objects, ext="mb"):
    pm.select(objects)
    file_name = next_previous_version_file_name(path,
                                                file_name,
                                                with_ext=0
                                                )

    file_path_name = "{}/{}.{}".format(path, file_name, ext)
    pm.exportSelected(file_path_name)


def read_folders_files(path):
    files = []
    for file in os.listdir(path):
        if os.path.isfile(os.path.join(path, file)):
            files.append(file)
            files = sorted(files)
    return files


def get_file_version_number(file_name):
    version_number = re.findall('[0-9]+', file_name)[-1]
    return int(version_number)


def check_file_with_name(path, file_name):
    files_list = read_folders_files(path)
    files_with_same_name = []

    for file in files_list:
        if file_name == name.remove_suffix(file, with_undescore=0):
            files_with_same_name.append(file)

    return files_with_same_name


def get_the_latest_file_version (path, file_name, with_ext=1):
    files_list = check_file_with_name(path, file_name)
    file_versions = []
    right_files_list = []
    latest_version = None

    if len(files_list) > 0:
        for file in files_list:
            version = get_file_version_number(file)
            right_files_list.append(file)
            file_versions.append(version)
        file_versions.sort()
        higher_number = file_versions[-1]

        for r_file in right_files_list:
            r_file_version = get_file_version_number(r_file)
            if higher_number == r_file_version :
                latest_version = r_file
        if not with_ext:
            latest_version = latest_version.split(".")[0]
    return latest_version


def next_previous_version_file_name(path, file_name, with_ext=1, version=1):

    if not version == 1 and not version == -1:
        return None
    file_name_vers = get_the_latest_file_version(path=path,
                                                 file_name=file_name,
                                                 with_ext=with_ext)
    new_file_name = None
    if file_name_vers is None:
        return "{}_v01".format(file_name)
    else:
        old_vers_num = get_file_version_number(file_name_vers)

        inter = get_latest_element_interval(old_vers_num,
                                            file_name_vers
                                            )

        new_vers_number = str(old_vers_num + version)
        new_file_name = "{}{}{}".format(file_name_vers[:inter[0]],
                                        new_vers_number,
                                        file_name_vers[inter[1]:]
                                        )

    return new_file_name


def get_all_latest_versions(path):
    all_files = read_folders_files(path)
    run = 0
    latest_versions = []
    if len(all_files) > 0:
        while run == 0:
            element_a = name.remove_suffix(all_files[0],
                                           with_undescore=0
                                           )

            latest = get_the_latest_file_version(path,
                                                 element_a)
            latest_versions.append(latest)
            all_files.remove(all_files[0])

            for e in all_files:
                if element_a == name.remove_suffix(e, with_undescore=0):
                    all_files.remove(e)
            if len(all_files) == 0:
                run += 1
    else:
        return None
    return list(set(latest_versions))


def get_latest_element_interval(element, name_check):
    element = str(element)
    lenght_element = len(element)
    pattern = re.compile((element))
    matches = pattern.finditer(name_check)
    indices = []
    for match in matches:
        indices.append(match.start())
    idx_a = indices[-1]
    idx_b = idx_a + lenght_element

    return idx_a, idx_b

