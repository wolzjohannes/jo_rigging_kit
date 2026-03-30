"""
WIll manage all defualt settings of a rig.
"""

# Import built-in modules
import logging
import os
import pprint
from importlib import reload

# Import third-party modules
from pixo_paths import normalize
from pymel import core as pmc
import maya.cmds as cmds

# Import local modules
from pxo_rigging_kit import constants
reload(constants)

from pxo_rigging_kit.constants import PXO_VIS_DEFAULT_SETTINGS_DIR_NAME
from pxo_rigging_kit.constants import PXO_VIS_DEFAULT_SETTINGS_FILE_NAME
from pxo_rigging_kit.constants import PXO_CTRLS_DEFAULT_SETTINGS_DIR_NAME
from pxo_rigging_kit.constants import PXO_CTRLS_DEFAULT_SETTINGS_FILE_NAME
from pxo_rigging_kit.maya_utils import exceptions
from pxo_rigging_kit.maya_utils import paths_utils
from pxo_rigging_kit.paths import check_and_create_path
from pxo_rigging_kit.paths import read_json_file
from pxo_rigging_kit.paths import write_json_file
from pxo_rigging_kit.versioncontrol_utils import check_and_create_date
from pxo_rigging_kit.versioncontrol_utils import get_latest_path

from pxo_rigging_kit.maya_utils import attributes_utils
from pxo_rigging_kit.maya_utils.rigging import rig_utils
reload(attributes_utils)


##########################################################
# GLOBALS
##########################################################

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.WARNING)
VIS_CTRL_NAME = "visibility_C_0_*_ctrl"

##########################################################
# FUNCTIONS
##########################################################


def _get_visibility_ctrl(namespace=""):
    """
    Get the visibilty control.

    Args:
        namespace(str): A optional namespace with trailing colons.
                        Example: "var_01:"
                        Defaults is "".

    """
    try:
        return pmc.ls(f"{namespace}{VIS_CTRL_NAME}")[0]
    except:
        raise exceptions.MayaNodeNotFound(f"{VIS_CTRL_NAME} not existing")


def _save_default_values(data, dir_name, file_name):
    """
    Save default values to as json files to the asset data folder.

    Args:
        data(list, tuple or dict): The data for saving.
        dir_name(str): The directory name for saving.
        file_name(str): The json file for saving

    Returns:
        String: The export file path.

    """
    export_path = _prep_dyn_default_dir_path(dir_name)
    export_path = check_and_create_path(export_path)
    vers_path = check_and_create_date(export_path)
    _LOGGER.info(f"Default values saved to: {vers_path}")
    return write_json_file(data, vers_path, file_name)


def save_visbility_default_values():
    """
    Save the visibility default values to asset data dir.
    """
    vis_attr_data = attributes_utils.get_ud_attributes(_get_visibility_ctrl())
    data = [
        {"longName": str(data_dict["longName"]), "value": data_dict["value"]}
        for data_dict in vis_attr_data
        if True is any([data_dict["channelBox"], data_dict["keyable"]])
        and False is all([data_dict["hidden"], data_dict["lock"]])
        and data_dict["attrType"] == "bool"
    ]
    _save_default_values(
        data,
        PXO_VIS_DEFAULT_SETTINGS_DIR_NAME,
        PXO_VIS_DEFAULT_SETTINGS_FILE_NAME,
    )


def import_and_apply_visibility_default_values(namespace=""):
    """
    Import the values from asset data directory and apply the visibilty default values.

    Args:
        namespace(str): A optional namespace with trailing colons.
                        Example: "var_01:"
                        Defaults is "".

    Returns:
        List: The imported default data.

    """
    vis_ctrl = _get_visibility_ctrl(namespace)
    import_path = _prep_dyn_default_dir_path(PXO_VIS_DEFAULT_SETTINGS_DIR_NAME)
    latest_vers_dir = normalize(
        os.path.join(
            get_latest_path(import_path), PXO_VIS_DEFAULT_SETTINGS_FILE_NAME
        )
    )
    data_list = read_json_file(latest_vers_dir)
    for data_dict in data_list:
        try:
            vis_attr = vis_ctrl.attr(data_dict["longName"])
        except Exception as e:
            pmc.warning(f"{e}, Will skip this attribute.")
            continue
        value = data_dict["value"]
        if value == True:
            value = 1
        else:
            value = 0
        print(vis_attr, value)
        vis_attr.set(value)
    return data_list


def save_controls_default_values():
    """
    Save the controls default values as json file to the asset data directory.
    """
    excludes_ctrls = [str(_get_visibility_ctrl().name(long=None))]
    data = list(get_controls_attr_data(excludes_ctrls))
    _save_default_values(
        data,
        PXO_CTRLS_DEFAULT_SETTINGS_DIR_NAME,
        PXO_CTRLS_DEFAULT_SETTINGS_FILE_NAME,
    )


def import_and_apply_controls_default_values(namespace=""):
    """
    Import from asset data directory and apply the controls default values.

    Args:
        namespace(str): A optional namespace with trailing colons.
                        Example: "var_01:"
                        Defaults is "".
    """
    import_path = _prep_dyn_default_dir_path(
        PXO_CTRLS_DEFAULT_SETTINGS_DIR_NAME
    )
    latest_vers_dir = normalize(
        os.path.join(
            get_latest_path(import_path), PXO_CTRLS_DEFAULT_SETTINGS_FILE_NAME
        )
    )
    data_list = read_json_file(latest_vers_dir)
    for ctrl_name, attr_dict in data_list:
        try:
            ctrl = pmc.PyNode(f"{namespace}{ctrl_name}")
        except Exception as e:
            pmc.warning(f"{e}. Will skip this ctrl.")
            continue
        if attr_dict:
            for attr_, value in attr_dict.items():
                try:
                    attr_obj = ctrl.attr(attr_)
                except Exception as e:
                    pmc.warning(f"{e}. Will skip this attribute.")
                    continue
                try:
                    attr_obj.set(value)
                except Exception as e:
                    pmc.warning(f"{e}. Will skip this attribute.")
                    continue


def get_controls_attr_data(excluded_ctrls=None):
    """
    Get all attributes values from all rig controls.

    Args:
        excluded_ctrls(list): List filled with control names to exclude from process.

    Returns:
        Generator: ((ctr_name, {attr_name:attr_value}))

    """
    if not excluded_ctrls:
        excluded_ctrls = []
    rig_ctrl_attr_interface_dict = rig_utils.get_anim_interface_attributes(
        rig_utils.get_anim_control_interface()
    )
    for (ctrl, attr_list) in rig_ctrl_attr_interface_dict.items():
        if ctrl in excluded_ctrls:
            continue
        attr_dict = {}
        for attr_ in attr_list:
            try:
                attr_value = cmds.getAttr(".".join([ctrl, attr_]))
            except:
                continue
            attr_dict[attr_] = attr_value
        if attr_dict:
            yield ctrl, attr_dict


def _prep_dyn_default_dir_path(dir_name):
    """
    Prepare the default asset data directory path.

    Args:
        dir_name(str): The directory name.

    Returns:
        String: The directory path.
    """
    data_dir = paths_utils.get_project_paths(pmc.sceneName())
    vis_dir = normalize(os.path.join(data_dir, dir_name))
    return vis_dir
