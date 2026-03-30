# Author:     Johannes Wolz / Lead Rigging TD

"""
Utils code to manage folder and path navigation in the pxo asset environment.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import pathlib
# Import built-in modules
from builtins import int
from builtins import str
import glob

# Import python standart import
import logging
import os
import re

# Import third-party modules
from future import standard_library
import pymel.core as pmc

# Import pxo packages
import pixo_naming
import pixo_paths
from pixo_shotgun import shotgun

# Import local modules
from pxo_rigging_kit import paths
from pxo_rigging_kit import constants
from pxo_rigging_kit.maya_utils import exceptions

standard_library.install_aliases()

##########################################################
# GLOBALS
##########################################################

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)
_VERSION_PATTERN = r"_v\d*_"

##########################################################
# FUNCTIONS
##########################################################


def get_root_path(scene_name, root_name):
    """
    Get root path from scene name.

    Args:
        scene_name(str): Name of the current scene.
        root_name(str): The root you want to have.
                        Valid is ["project", "category", "asset_name", "asset_task",
                                  "shot_task"]

    Return:
        String: The root path.
        exceptions.PixoNamingError() if fail.

    """
    pattern = pixo_naming.get_pattern(f"{root_name}_root")
    match = re.match(pattern, scene_name)
    if match:
        return match.group(0)
    else:
        raise exceptions.PixoNamingError()


def get_project_paths(scene_name,
                      task_type="asset_task",
                      path_type="data",
                      ) -> pathlib.Path:
    """
    Get the path to the data folder from your maya scene/project.
    Which is in you case the asset most of the time.

    Args:
        scene_name(str): Name of the current scene.
        task_type(str): The type of the task.
                        Valid are ["asset_task", "shot_task"].
                        Default is "asset_task".

    Return:
        String: The data path.

    """
    root_path = get_root_path(scene_name, task_type)
    data_path = pixo_paths.normalize(os.path.join(root_path, path_type))

    if not os.path.exists(data_path):
        raise IOError(f"{path_type} path not exist.")

    return pathlib.Path(data_path)


def get_mdl_path2(scene_name, category, asset_name):
    """
    Get the mdl path specified by category and asset name.

    Args:
        scene_name(str): Name of the current scene.
        category(str): The asset category.
                       Valid is ["props", "creature", "characters", "vehicles"]
        asset_name(str): The name of the asset.

    Return:
        String: the mdl path.
        If not exist IOError.

    """
    category_path = get_root_path(scene_name, "category")
    assets_path = os.path.split(category_path)[0]
    path = pixo_paths.normalize(
        os.path.join(assets_path, category, asset_name, "mdl")
    )
    if not os.path.exists(path):
        raise IOError("{} not exists.".format(path))
    return path


def get_mdl_path(scene_name):
    """
    Get the path to the mdl root directory from your asset.

    Args:
        scene_name(str): Name of the current scene.

    Return:
        String: The mdl path.
        If fail exceptions.PixoNamingError()

    """
    pattern = pixo_naming.get_pattern("asset_task_root")
    match = re.match(pattern, scene_name)
    if match:
        values = match.groupdict()
        values["task_type"] = "mdl"
        values["task_name"] = None
        return pixo_naming.get("asset_task_root", values)
    else:
        raise exceptions.PixoNamingError()


def get_mdl_publish_dir_path(scene_name, category=None, asset_name=None):
    """
    Get the modeling publish path.

    Args:
        scene_name(str): Name of the current scene.

    Return:
        String: The mdl publish path.
        If fail IOError.

    """
    mdl_path = get_mdl_path(scene_name)
    if category and asset_name:
        mdl_path = get_mdl_path2(scene_name, category, asset_name)
    publish_path = pixo_paths.normalize(os.path.join(mdl_path, "_publish"))
    if not os.path.exists(publish_path):
        raise IOError("{} not exist".format(publish_path))
    return publish_path


def get_version_number_from_basename(base_name):
    """
    Get the version number from given file basename.

    Args:
        base_name(str): File basename.

    Return:
        Int: Version number.
        If fail NameError.

    """
    match = re.search(_VERSION_PATTERN, base_name)
    if match:
        value = str(match.group())
        match_ = re.search(r"\d+", value)
        version = int(match_.group())
        return version
    else:
        raise NameError(
            "Can not find version token with this pattern: {}".format(
                _VERSION_PATTERN
            )
        )


def get_mdl_publish_file_path(
    scene_name, category=None, asset_name=None, lod="", version_number=None
):
    """
    Get mdl publish file path.

    Args:
        scene_name(str): Name of the current scene.
        category(str): The asset category. Here you can remap
                       to a different asset type.
                       Valid are ["props", "characters", "creature", "vehicles"]
                       Default is None
        asset_name(str): The asset name. Default is None
        lod(str): File lod. Will give you the appropriate .abc file.
                  If None will always return the .mb file.
                  Valid is ["sliced", "low", "high"].
                  Default is None.
        version_number(int): Gives back given version if exist.
                             If None will give you the latest publish file.
                             Default is None.

    Example:
        >>> import pymel.core as pmc
        >>> from pxo_rigging_kit.maya_utils import paths_utils
        >>> scene_name = pmc.sceneName()
        >>> paths_utils.get_mdl_publish_file_path(scene_name, "sliced", 22)

    Return:
        Dict:
        {'path': 'X:\redgun_reg-6344\_library\assets\creature\crt_vhagar\
                  mdl\_publish\reg_crt_vhagar_mdl_v022_lku.sliced.abc',
         'version': 22}
         If fail IOError.


    """
    result_dict = {}
    file_type = "mb"
    if lod:
        file_type = "abc"
    search_pattern = "*{}.{}".format(lod, file_type)
    search_path = pixo_paths.normalize(
        os.path.join(
            get_mdl_publish_dir_path(scene_name, category, asset_name),
            search_pattern,
        )
    )
    publish_file_path_list = glob.glob(search_path)
    if version_number is None:
        publish_file_path_list = [
            max(publish_file_path_list, key=os.path.getctime)
        ]
        version_number = get_version_number_from_basename(
            os.path.basename(str(publish_file_path_list[0]))
        )
    for file_path in publish_file_path_list:
        base_name = os.path.basename(file_path)
        version = get_version_number_from_basename(base_name)
        result_dict[version] = file_path
    try:
        return {
            "path": pixo_paths.normalize(result_dict[version_number]),
            "version": version_number,
        }
    except:
        raise IOError(
            "Searched publish version: {} not exist".format(version_number)
        )


def list_data_dir(scene_name):
    """
    List all folder of the data directory.

    Args:
        scene_name(str): Name of the current scene.

    Return:
        Dict:
        {
         'sandBox': 'X:\\redgun_reg-6344\\_library\\assets\\creature
                     \\crt_vhagar\\rig_0\\data\\sandBox',
         'gSkin': 'X:\\redgun_reg-6344\\_library\\assets\\creature
                   \\crt_vhagar\\rig_0\\data\\gSkin'
        }

    """
    data_dir = get_project_paths(scene_name)
    ls_dir = os.listdir(data_dir)
    result_dict = {
        dir_name: pixo_paths.normalize(os.path.join(data_dir, dir_name))
        for dir_name in ls_dir
    }
    return result_dict


def get_asset_infos(scene_name, info_type):
    """
    Get asset infos.

    Args:
        scene_name(str): Name of the current scene.
        info_type(str): Info you want.
                        Valid is ['project',
                                  'task_type',
                                  'asset_name',
                                  'projects_root',
                                  'task_name',
                                  'asset_category']

    Return:
        String: The info you want.
        If fail exceptions.PixoNamingError()

    """
    pattern = pixo_naming.get_pattern("asset_task_root")
    match = re.match(pattern, scene_name)
    if match:
        values = match.groupdict()
        try:
            return values[info_type]
        except:
            raise KeyError("Given info_type: {} not valid".format(info_type))
    else:
        raise exceptions.PixoNamingError()


def get_mdl_publish_file_path_with_sg_hand_off(
    scene_name, category=None, asset_name=None, lod="", version_number=None
):
    """
    Get model publish path with shotgrid hand off status. If no category
    and asset name given will take default category and asset name
    from current rig file/task.

    Args:
        scene_name(str): Name of the current scene.
        category(str): The asset category. Here you can remap
                       to a different asset type.
                       Valid are ["props", "characters", "creature", "vehicles"]
                       Default is None
        asset_name(str): The asset name. Default is None
        lod(str): File lod. Will give you the appropriate .abc file.
                  If None will always return the .mb file.
                  Valid is ["sliced", "low", "high"].
                  Default is None.
        version_number(int): Gives back given version if exist.
                             If None will give you the latest publish file.
                             Default is None.

    Return:
        Dict:
        {'path': 'X:\redgun_reg-6344\_library\assets\creature\crt_vhagar\
                  mdl\_publish\reg_crt_vhagar_mdl_v022_lku.sliced.abc',
         'version': 22}
         If fail IOError.

    """
    if not asset_name:
        asset_name = get_asset_infos(scene_name, "asset_name")
    sg = shotgun.init_shotgun()
    try:
        project_sg_id = int(os.environ[constants.PXO_PROJECT_SGID])
    except:
        raise EnvironmentError(
            "Can not find {} env variable."
            " So we are"
            " unable to"
            " find"
            " shotgun"
            " id"
            " for"
            " project".format(constants.PXO_PROJECT_SGID)
        )
    filters = [
        ["project.Project.id", "is", project_sg_id],
        ["entity.Asset.code", "is", asset_name],
        ["sg_status_list", "is", "hndoff"],
        ["sg_task.Task.sg_task_type.CustomNonProjectEntity05.id", "is", 15],
    ]
    fields = [
        "code",
        "sg_path_scene",
    ]
    handoff_versions = sg.find("Version", filters, fields)
    if handoff_versions:
        version_number_filtered_dict = {}
        for data_dict in handoff_versions:
            sg_path_scene = data_dict.get("sg_path_scene")
            if sg_path_scene:
                file_name = sg_path_scene.get("name")
                if file_name:
                    if (
                        os.path.splitext(file_name)[-1]
                        == constants.MAYA_WORKFILE_EXTENSION
                    ):
                        version = get_version_number_from_basename(file_name)
                        version_number_filtered_dict[version] = data_dict
        if not version_number:
            version_number = max(version_number_filtered_dict.keys())
        if version_number not in version_number_filtered_dict:
            raise exceptions.ShotgridError(
                "The version you searching for is not hand off flagged."
            )
        return get_mdl_publish_file_path(
            scene_name, category, asset_name, lod, version_number
        )
    else:
        raise exceptions.ShotgridError(
            "No mdl published with status handoff found."
        )


def get_user_abbr(scene_name):
    """
    Get the user abbr from scene name.

    Return:
        String: User abbr.
        If fail exceptions.PixoNamingError.
    """
    usr = os.environ.get("PXO_USER_ABBR", None)
    if not usr:
        file_name = os.path.basename(scene_name)
        pattern = pixo_naming.get_pattern("asset_work_file_name")
        match = re.match(pattern, file_name)
        try:
            return match.groupdict().get("user_abbr")
        except:
            raise exceptions.PixoNamingError(
                "Unable to get user abbr from scene name."
            )
    return usr


def get_user_name():
    """
    Get the user name from environ dict.
    """
    try:
        return os.environ["USERNAME"]
    except:
        return os.environ["USER"]


def get_rig_published_files(
    published_file_sgid,
    shotgun_=None,
):
    """Return list of RIG path in ascending order of detail. We use the upstream_published_files data in SG.

    Args:
        published_file_sgid (int): Shotgun ID of a PublishedFile. This is the one that represents the "high" version and
            is listed in the SGTK Loader.
        shotgun_(shotgun_api3.Shotgun), optional: Shotgun instance to use for the query.

    Returns:
        List: List of PublishedFile dicts sorted from lowest to higest LOD.
        None: If SG upstream_published_files field of master rig publish is empty.
        None: If SG published_file_type field is not Rig Proxy for the Rig LODs.

    """
    rig_published_files = []
    if not shotgun_:
        sg = shotgun.init_shotgun()

    fields = (
        "path_cache",  # the path to the published scene file
        "sg_usage",  # the lod level and name
        "sg_namespace",  # for the namespace
        "entity",  # for the asset name,
        "published_file_type",  # to distinguish high and proxy
        "version_number",
        "upstream_published_files",
    )

    # Get additional data of the "high" LOD  i.e. the selected PFE
    rig_published_file = sg.find_one(
        "PublishedFile", [["id", "is", int(published_file_sgid)]], fields
    )

    # Getting all upstream published files which represents all LOD publishes from the master rig.
    proxy_rig_publishes = rig_published_file.get(
        "upstream_published_files", None
    )

    if proxy_rig_publishes:
        rig_published_files = [
            sg.find_one(
                "PublishedFile", [["id", "is", int(data_dict["id"])]], fields
            )
            for data_dict in proxy_rig_publishes
            if sg.find_one(
                "PublishedFile",
                [["id", "is", int(data_dict["id"])]],
                fields,
            )["published_file_type"]["id"]
            == constants.RIG_PROXY_ID
        ]

    return rig_published_files

def get_asset_data_from_json(json_file_name):
    """
    Get asset data from stored json file in the data directory of an asset.

    Args:
        json_file_name(str): The json file name.

    Returns:
        Data: Any data a json file can save.

    """
    data_dir = get_project_paths(pmc.sceneName())
    spread_json = os.path.join(data_dir, json_file_name)
    if not os.path.exists(spread_json):
        return
    return paths.read_json_file(spread_json)