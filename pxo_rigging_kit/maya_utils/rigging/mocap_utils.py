# Author:     Johannes Wolz / Lead Rigging TD

"""
Utils code for mocap data management.
It will handle HIK as well.
The problem with HIK is that is hardly connected to the HIK userinterface.
If you want to connect or handle all the HIK nodes in a effective way
you have to use code which interact with the HIK ui in maya.
For the most functions you will need a hik description dictionary which
looks like this:

{
    "RightHandIndex1": "finger_R_0_fk0_ctrl",
    "RightHandPinky1": "finger_R_3_fk0_ctrl",
    "LeftHandMiddle1": "finger_L_1_fk0_ctrl",
    "LeftToeBase": "foot_L_0_fk0_ctrl",
    "Spine1": "spine_C_0_fk0_ctrl",
    "Spine3": "spine_C_0_fk2_ctrl",
    "Spine2": "spine_C_0_fk1_ctrl",
    "LeftHandIndex2": "finger_L_0_fk1_ctrl",
    "LeftHandIndex3": "finger_L_0_fk2_ctrl",
    "RightHandRing2": "finger_R_2_fk1_ctrl",
    "LeftHandIndex1": "finger_L_0_fk0_ctrl",
    "LeftHand": "arm_L_0_fk2_ctrl",
    "Neck": "neck_C_0_fk0_ctrl",
    "RightHandIndex2": "finger_R_0_fk1_ctrl",
    "Head": "neck_C_0_ik_ctrl",
    "RightHand": "arm_R_0_fk2_ctrl",
    "LeftFootExtraFinger1": "foot_L_0_fk1_ctrl",
    "RightHandIndex3": "finger_R_0_fk2_ctrl",
    "LeftArm": "arm_L_0_fk0_ctrl",
    "RightHandPinky3": "finger_R_3_fk2_ctrl",
    "RightHandPinky2": "finger_R_3_fk1_ctrl",
    "LeftHandThumb2": "thumb_L_0_fk1_ctrl",
    "LeftHandThumb3": "thumb_L_0_fk2_ctrl",
    "LeftHandThumb1": "thumb_L_0_fk0_ctrl",
    "LeftLeg": "leg_L_0_fk1_ctrl",
    "LeftForeArm": "arm_L_0_fk1_ctrl",
    "RightForeArm": "arm_R_0_fk1_ctrl",
    "RightToeBase": "foot_R_0_fk0_ctrl",
    "Spine": "spine_C_0_ik0_ctrl",
    "LeftUpLeg": "leg_L_0_fk0_ctrl",
    "LeftFoot": "leg_L_0_fk2_ctrl",
    "LeftHandMiddle2": "finger_L_1_fk1_ctrl",
    "LeftHandMiddle3": "finger_L_1_fk2_ctrl",
    "RightHandRing1": "finger_R_2_fk0_ctrl",
    "LeftShoulder": "shoulder_L_0_ctrl",
    "LeftHandPinky1": "finger_L_3_fk0_ctrl",
    "Hips": "body_C_0_ctrl",
    "RightFoot": "leg_R_0_fk2_ctrl",
    "RightHandThumb2": "thumb_R_0_fk1_ctrl",
    "RightHandThumb3": "thumb_R_0_fk2_ctrl",
    "RightHandThumb1": "thumb_R_0_fk0_ctrl",
    "RightArm": "arm_R_0_fk0_ctrl",
    "LeftHandPinky3": "finger_L_3_fk2_ctrl",
    "Reference": "local_C_0_ctrl",
    "LeftHandPinky2": "finger_L_3_fk1_ctrl",
    "LeftHandRing3": "finger_L_2_fk2_ctrl",
    "RightUpLeg": "leg_R_0_fk0_ctrl",
    "LeftHandRing1": "finger_L_2_fk0_ctrl",
    "RightHandMiddle1": "finger_R_1_fk0_ctrl",
    "RightHandMiddle2": "finger_R_1_fk1_ctrl",
    "RightLeg": "leg_R_0_fk1_ctrl",
    "RightHandMiddle3": "finger_R_1_fk2_ctrl",
    "LeftHandRing2": "finger_L_2_fk1_ctrl",
    "RightHandRing3": "finger_R_2_fk2_ctrl",
    "RightFootExtraFinger1": "foot_R_0_fk1_ctrl",
    "RightShoulder": "shoulder_R_0_ctrl"
}
For target_rig and mocap data we will need such a hik description dict.
We can get that data from three different levels:

LEVEL_1 ---> ./scene/data(two json files.)
LEVEL_2 -------> ./project(two json files.)
LEVEL_3 ------------> .pxo_rigging_kit.yaml config file
                      (mocap_utils:hik_target_char_description,
                       mocap_utils:hik_source_char_description)

The config entry is always the fall back but you can store json files
to override these for projects or even for each maya scene you working on.

To Do:
- Get rid of maya HIK and write our own retarget solution.

"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Import built-in modules
from builtins import dict
from builtins import range
from builtins import str
from collections import namedtuple
import logging
import os
from xml.etree import cElementTree as ET
from importlib import reload

# Import third-party modules
from future import standard_library
import pixo_paths
import pymel.core as pmc
from studiolibrarymaya import animitem

# Import local modules
from pxo_rigging_kit import core
from pxo_rigging_kit import paths
from pxo_rigging_kit.constants import HIK_IK_FK_MATCH_JSON_NAME
from pxo_rigging_kit.constants import HIK_SOURCE_RIG_CHAR_DESCRIPTION_NAME
from pxo_rigging_kit.constants import HIK_TARGET_RIG_CHAR_DESCRIPTION_NAME
from pxo_rigging_kit.maya_utils import dag_utils
from pxo_rigging_kit.maya_utils import decorators
from pxo_rigging_kit.maya_utils import exceptions
from pxo_rigging_kit.maya_utils import paths_utils
from pxo_rigging_kit.maya_utils import scene_utils
from pxo_rigging_kit.maya_utils.rigging import rig_utils

standard_library.install_aliases()

##########################################################
# GLOBALS
##########################################################
reload(decorators)
_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)
DECORATORS = decorators.Decorators()
DECORATORS.debug = True
DECORATORS.logger = _LOGGER

DEFAULT_HIK_DEF_ATTRIBUTES = [
    "Reference",
    "Hips",
    "LeftUpLeg",
    "LeftLeg",
    "LeftFoot",
    "RightUpLeg",
    "RightLeg",
    "RightFoot",
    "Spine",
    "LeftArm",
    "LeftForeArm",
    "LeftHand",
    "RightArm",
    "RightForeArm",
    "RightHand",
    "Head",
    "LeftToeBase",
    "RightToeBase",
    "LeftShoulder",
    "RightShoulder",
    "Neck",
    "LeftFingerBase",
    "RightFingerBase",
    "Spine1",
    "Spine2",
    "Spine3",
    "Spine4",
    "Spine5",
    "Spine6",
    "Spine7",
    "Spine8",
    "Spine9",
    "Neck1",
    "Neck2",
    "Neck3",
    "Neck4",
    "Neck5",
    "Neck6",
    "Neck7",
    "Neck8",
    "Neck9",
    "LeftUpLegRoll",
    "LeftLegRoll",
    "RightUpLegRoll",
    "RightLegRoll",
    "LeftArmRoll",
    "LeftForeArmRoll",
    "RightArmRoll",
    "RightForeArmRoll",
    "HipsTranslation",
    "LeftHandThumb1",
    "LeftHandThumb2",
    "LeftHandThumb3",
    "LeftHandThumb4",
    "LeftHandIndex1",
    "LeftHandIndex2",
    "LeftHandIndex3",
    "LeftHandIndex4",
    "LeftHandMiddle1",
    "LeftHandMiddle2",
    "LeftHandMiddle3",
    "LeftHandMiddle4",
    "LeftHandRing1",
    "LeftHandRing2",
    "LeftHandRing3",
    "LeftHandRing4",
    "LeftHandPinky1",
    "LeftHandPinky2",
    "LeftHandPinky3",
    "LeftHandPinky4",
    "LeftHandExtraFinger1",
    "LeftHandExtraFinger2",
    "LeftHandExtraFinger3",
    "LeftHandExtraFinger4",
    "RightHandThumb1",
    "RightHandThumb2",
    "RightHandThumb3",
    "RightHandThumb4",
    "RightHandIndex1",
    "RightHandIndex2",
    "RightHandIndex3",
    "RightHandIndex4",
    "RightHandMiddle1",
    "RightHandMiddle2",
    "RightHandMiddle3",
    "RightHandMiddle4",
    "RightHandRing1",
    "RightHandRing2",
    "RightHandRing3",
    "RightHandRing4",
    "RightHandPinky1",
    "RightHandPinky2",
    "RightHandPinky3",
    "RightHandPinky4",
    "RightHandExtraFinger1",
    "RightHandExtraFinger2",
    "RightHandExtraFinger3",
    "RightHandExtraFinger4",
    "LeftFootThumb1",
    "LeftFootThumb2",
    "LeftFootThumb3",
    "LeftFootThumb4",
    "LeftFootIndex1",
    "LeftFootIndex2",
    "LeftFootIndex3",
    "LeftFootIndex4",
    "LeftFootMiddle1",
    "LeftFootMiddle2",
    "LeftFootMiddle3",
    "LeftFootMiddle4",
    "LeftFootRing1",
    "LeftFootRing2",
    "LeftFootRing3",
    "LeftFootRing4",
    "LeftFootPinky1",
    "LeftFootPinky2",
    "LeftFootPinky3",
    "LeftFootPinky4",
    "LeftFootExtraFinger1",
    "LeftFootExtraFinger2",
    "LeftFootExtraFinger3",
    "LeftFootExtraFinger4",
    "RightFootThumb1",
    "RightFootThumb2",
    "RightFootThumb3",
    "RightFootThumb4",
    "RightFootIndex1",
    "RightFootIndex2",
    "RightFootIndex3",
    "RightFootIndex4",
    "RightFootMiddle1",
    "RightFootMiddle2",
    "RightFootMiddle3",
    "RightFootMiddle4",
    "RightFootRing1",
    "RightFootRing2",
    "RightFootRing3",
    "RightFootRing4",
    "RightFootPinky1",
    "RightFootPinky2",
    "RightFootPinky3",
    "RightFootPinky4",
    "RightFootExtraFinger1",
    "RightFootExtraFinger2",
    "RightFootExtraFinger3",
    "RightFootExtraFinger4",
    "LeftInHandThumb",
    "LeftInHandIndex",
    "LeftInHandMiddle",
    "LeftInHandRing",
    "LeftInHandPinky",
    "LeftInHandExtraFinger",
    "RightInHandThumb",
    "RightInHandIndex",
    "RightInHandMiddle",
    "RightInHandRing",
    "RightInHandPinky",
    "RightInHandExtraFinger",
    "LeftInFootThumb",
    "LeftInFootIndex",
    "LeftInFootMiddle",
    "LeftInFootRing",
    "LeftInFootPinky",
    "LeftInFootExtraFinger",
    "RightInFootThumb",
    "RightInFootIndex",
    "RightInFootMiddle",
    "RightInFootRing",
    "RightInFootPinky",
    "RightInFootExtraFinger",
    "LeftShoulderExtra",
    "RightShoulderExtra",
    "LeafLeftUpLegRoll1",
    "LeafLeftLegRoll1",
    "LeafRightUpLegRoll1",
    "LeafRightLegRoll1",
    "LeafLeftArmRoll1",
    "LeafLeftForeArmRoll1",
    "LeafRightArmRoll1",
    "LeafRightForeArmRoll1",
    "LeafLeftUpLegRoll2",
    "LeafLeftLegRoll2",
    "LeafRightUpLegRoll2",
    "LeafRightLegRoll2",
    "LeafLeftArmRoll2",
    "LeafLeftForeArmRoll2",
    "LeafRightArmRoll2",
    "LeafRightForeArmRoll2",
    "LeafLeftUpLegRoll3",
    "LeafLeftLegRoll3",
    "LeafRightUpLegRoll3",
    "LeafRightLegRoll3",
    "LeafLeftArmRoll3",
    "LeafLeftForeArmRoll3",
    "LeafRightArmRoll3",
    "LeafRightForeArmRoll3",
    "LeafLeftUpLegRoll4",
    "LeafLeftLegRoll4",
    "LeafRightUpLegRoll4",
    "LeafRightLegRoll4",
    "LeafLeftArmRoll4",
    "LeafLeftForeArmRoll4",
    "LeafRightArmRoll4",
    "LeafRightForeArmRoll4",
    "LeafLeftUpLegRoll5",
    "LeafLeftLegRoll5",
    "LeafRightUpLegRoll5",
    "LeafRightLegRoll5",
    "LeafLeftArmRoll5",
    "LeafLeftForeArmRoll5",
    "LeafRightArmRoll5",
    "LeafRightForeArmRoll5",
]

MOCAP_DATA_NAMESPACE = "moc_01"
HIK_TARGET_RIG_NAMESPACE = "char_01"
HIK_MOCAP_DATA_CHAR_DESC_NAME = "mocap_data"
HIK_TARGET_RIG_CHAR_DESC_NAME = "target_rig"
HIK_NODES_LIST = [
    pmc.nt.HikHandle,
    pmc.nt.HikSolver,
    pmc.nt.HikEffector,
    pmc.nt.HikFKJoint,
    pmc.nt.HikFloorContactMarker,
    pmc.nt.HikGroundPlane,
    pmc.nt.HikIKEffector,
    pmc.nt.HIKCharacterNode,
    pmc.nt.HIKRetargeterNode,
    pmc.nt.HIKSK2State,
    pmc.nt.HIKSolverNode,
    pmc.nt.HIKState2SK,
]
MOCAP_DATA_TYPE = ".fbx"

DECORATORS = decorators.Decorators()
DECORATORS.debug = True
DECORATORS.logger = _LOGGER

##########################################################
# FUNCTIONS
##########################################################


def hik_add_biped_definition(
    char_name, lock_def=False, hik_dict=None, namespace=None
):
    """
    Add a HIK biped definition.

    Args:
        char_name(str): The definition name.
        lock_def(bool): Will lock the definition.
                        Default is False.
        hik_dict(Dict): The data dict for the target joint binding.
                        If None will take it from pxo_rigging_kit.yaml
                        config file.
                        Default is None.
        namespace(str): The namespace for the target object.
                        Without ":".
                        Default is None.

    """
    if not hik_dict:
        hik_dict = hik_get_data_descriptions_from_config()
    if not pmc.pluginInfo("mayaHIK", loaded=1, q=1):
        pmc.loadPlugin("mayaHIK")
    if not pmc.pluginInfo("mayaCharacterization", loaded=1, q=1):
        pmc.loadPlugin("mayaCharacterization")
    if not pmc.pluginInfo("OneClick", loaded=1, q=1):
        pmc.loadPlugin("OneClick")
    try:
        pmc.mel.hikSelectDefinitionTab()
    except:
        pmc.runtime.ToggleCharacterControls(1)
    character_ = None
    character_nodes = pmc.ls(type=pmc.nt.HIKCharacterNode)
    pmc.mel.hikCreateDefinition()
    pmc.mel.hikUpdateCharacterList()
    pmc.mel.hikUpdateSourceList()
    pmc.mel.hikSelectDefinitionTab()
    for char in pmc.ls(type=pmc.nt.HIKCharacterNode):
        if char not in character_nodes:
            pmc.rename(char, char_name)
            character_ = char
    if not character_:
        return
    pmc.mel.hikSetCurrentCharacter(character_)
    pmc.mel.hikRenameConnectedNodes(character_, "Character1")
    for channel, source in list(hik_dict.items()):
        if namespace:
            source = ":".join([namespace, source])
        source_node = pmc.PyNode(source)
        if not source_node.hasAttr("Character"):
            pmc.addAttr(source_node, sn="Character", at="message")
        source_node.Character.connect(
            pmc.Attribute("{}.{}".format(character_.nodeName(), channel))
        )
        attributes = [
            source_node.translate,
            source_node.rotate,
            source_node.scale,
        ]
        for attr in attributes:
            for child in attr.children():
                child.set(l=False)
            attr.set(l=False)
    if lock_def:
        pmc.mel.hikCharacterLock(char_name, True, 1)
    else:
        pmc.mel.hikToggleLockDefinition()
    pmc.mel.hikSelectDefinitionTab()


def hik_switch_ui_list(char_name, list_type):
    """
    Switch the "character" or "source" list in the
    HIK ui to given character name.
    This is needed because the switching triggers a lot of mel code.
    For example this triggers the connection of the
    target_rig with the mocap_rig.

    Args:
        char_name(str): The character name in the HIK menu.
        list_type(str): The list to trigger. Valid are ["source", "character"].

    """
    pmc.mel.hikUpdateCharacterList()
    pmc.mel.hikUpdateSourceList()
    pmc.mel.hikSelectDefinitionTab()
    menu_name = "hik{}List".format(list_type.capitalize())
    option_menu_grp = pmc.optionMenuGrp(
        menu_name, query=True, itemListLong=True
    )
    if list_type == "source":
        char_name = " {}".format(char_name)

    for idx_, item in enumerate(option_menu_grp, 1):
        # This is the name of the option menu that lives in the
        # HIK window globally
        optMenu = "{}|OptionMenu".format(menu_name)
        menu_item = pmc.menuItem(item, query=True, label=True)
        # IMPORTANT! On this check, notice the space before "newSourceHere";
        # I found this is how the dropdown
        # menu in HIK stores the different strings so be sure to include that
        # first space before your string
        # But is just for the source.
        if menu_item == char_name:
            pmc.optionMenu(optMenu, edit=True, select=idx_)

            if list_type == "source":
                pmc.mel.hikUpdateCurrentSourceFromUI()
            else:
                pmc.mel.hikUpdateCurrentCharacterFromUI()

            pmc.mel.hikUpdateContextualUI()
            pmc.mel.eval("hikControlRigSelectionChangedCallback")
            break

    pmc.mel.hikSelectDefinitionTab()


def hik_connect_character_with_source(char_name, target_char_name):
    """
    Connect the HIK character with source.

    Args:
        char_name(str): The HIK character name of the target rig.
        target_char_name(str): The HIK source name of the mocap rig.

    """
    hik_switch_ui_list(char_name, "character")
    hik_switch_ui_list(target_char_name, "source")


def hik_validate_mocap_data(data_list, source_hik_dict, namespace=None):
    """
    Will compare hik description with given nodes data.
    It is invalid if node names from dict not exist in given nodes data.

    Args:
        data_list(list): Nodes data list.
        source_hik_dict(dict): Source HIK description.
        namespace(str): Nodes namespace without ":".
                        Default is None.
    Return:
        True if valid.
        If invalid raise exceptions.HikCharacterDefinitionError

    """
    target_objects_list = list(source_hik_dict.values())
    if namespace:
        target_objects_list = [
            ":".join([namespace, obj_name]) for obj_name in target_objects_list
        ]
    for node_name in target_objects_list:
        if node_name not in data_list:
            raise exceptions.HikCharacterDefinitionError(
                "Mocap data not equal with hik definition."
                "\nSome objects in the hik definition not existing in mocap data."
                "\nPls create fitting hik definition."
            )
    return True


def hik_convert_char_description_template_to_dict(xml_path):
    """
    Convert a HIK description template xml file into a dictionary we can use.

    Args:
        xml_path(str): The xml template path.

    Return:
        Dictionary: The converted template data.

    """
    result_dict = {}
    with open(xml_path, "r") as f:
        data = f.read()
    xml_data = ET.XML(str(data))
    hik_dict = core.xml_to_dict(xml_data)
    remap_list = hik_dict["config_root"]["match_list"]["item"]
    for data_dict in remap_list:
        if data_dict["@value"]:
            result_dict[data_dict["@key"]] = data_dict["@value"].split(":")[-1]
    return result_dict


def hik_get_char_description_from_character(char_def_name):
    """
    Get HIK description from given HIK character name.

    Args:
        char_def_name(str): HIK character name.

    Return:
        Dictionary: The extracted hik description data.

    """
    all_def_nodes = pmc.ls(type=pmc.nt.HIKCharacterNode)
    if char_def_name not in all_def_nodes:
        raise exceptions.HikCharacterDefinitionError(
            "No character definition node with name: {} exist".format(
                char_def_name
            )
        )
    def_node = pmc.PyNode(char_def_name)
    result_dict = {
        def_key: str(
            def_node.attr(def_key)
            .connections(s=True, d=False)[0]
            .name(long=None, stripNamespace=True)
        )
        for def_key in DEFAULT_HIK_DEF_ATTRIBUTES
        if def_node.hasAttr(def_key) and def_node.attr(def_key).isConnected()
    }
    return result_dict


def hik_save_char_description_as_json(
    file_path, char_def_name=None, template_path=None
):
    """
    Save character description as json file.

    Args:
        file_path(str): The saving path.
        char_def_name(str): The HIK char name.
                            Will take the data from given HIK definition.
        template_path(str): The xml template path.
                            Will take the data from given xml template file.

    Return:
        Raise exceptions.HikCharacterDefinitionError
        if no char_def_name or template_path given.

    """
    data_dict = {}
    file_path = pixo_paths.normalize(file_path)
    if char_def_name:
        data_dict = hik_get_char_description_from_character(char_def_name)
    if template_path:
        data_dict = hik_convert_char_description_template_to_dict(template_path)
    if not data_dict:
        raise exceptions.HikCharacterDefinitionError(
            "Character Definition is None. Maybe Character"
            " Node has no incoming conenctions or template xml file is empty."
        )
    path, file_name = os.path.split(file_path)
    paths.write_json_file(data_dict, pixo_paths.normalize(path), file_name)
    _LOGGER.info("HIK description data dict saved to: {}".format(file_path))


def hik_save_fk_ik_match_data_as_json(file_path, data_dict):
    """
    Save Tpose and fk/ik match data as json file.

    Args:
        file_path(str): The saving path.

    """
    fk_ik_match_data_dict = hik_get_fk_ik_match_data_from_config()
    fk_ik_match_data_dict.update(data_dict)
    path, file_name = os.path.split(file_path)
    paths.write_json_file(
        fk_ik_match_data_dict, pixo_paths.normalize(path), file_name
    )
    _LOGGER.info("Tpose & FK/IK match data saved to: {}".format(file_path))


def hik_get_fk_ik_match_data_from_directory_level(level):
    """
    Will search about a fk/ik match data json file on given level.
    File name are global var: HIK_IK_FK_MATCH_JSON_NAME

    Args:
        level(str): Directory level.
                    Valid are:
                    "project": ./project
                    "scene": ./project/shot/task/shot_number/data
                             or
                             ./project/_library/assets/asset_category/assets_name/task/data.

    Return:
        raise OSError if given level gives no valid path back.
        None if no json file found or if one of the json files missing.
        Tuple: (host_fk_blend_list, fk_blend_value, left_limb_side_char)

    """
    if level == "scene":
        try:
            data_path = paths_utils.get_project_paths(
                pmc.sceneName(), "shot_task"
            )
        except:
            data_path = paths_utils.get_project_paths(
                pmc.sceneName(), "asset_task"
            )
    elif level == "project":
        data_path = paths_utils.get_root_path(pmc.sceneName(), "project")
    else:
        raise OSError("Level {} gives no result path.".format(level))
    data_json_path = pixo_paths.normalize(
        os.path.join(
            data_path,
            "{}.json".format(HIK_IK_FK_MATCH_JSON_NAME),
        )
    )
    if not os.path.exists(data_json_path):
        _LOGGER.info("No FK/IK match json file found in: {}".format(data_path))
        return
    data = paths.read_json_file(data_json_path)
    _LOGGER.info("FK/IK match json data found in: {}".format(data_path))
    return data


def hik_get_data_descriptions_from_directory_level(level):
    """
    Get hik data description from directory level. Two json files are needed
    one for each rig. Target and mocap rig.
    Will search about json file on given level.
    File names are global vars:
    HIK_TARGET_RIG_CHAR_DESCRIPTION_NAME, HIK_SOURCE_RIG_CHAR_DESCRIPTION_NAME.

    Args:
        level(str): Directory level.
                    Valid are:
                    "project": ./project
                    "scene": ./project/shot/task/shot_number/data
                             or
                             ./project/_library/assets/asset_category/assets_name/task/data.

    Return:
        raise OSError if given level gives no valid path back.
        None if no json file found or if one of the json files missing.
        Tuple: (target_rig_dict, mocap_rig_dict)

    """
    if level == "scene":
        try:
            data_path = paths_utils.get_project_paths(
                pmc.sceneName(), "shot_task"
            )
        except:
            data_path = paths_utils.get_project_paths(
                pmc.sceneName(), "asset_task"
            )
    elif level == "project":
        data_path = paths_utils.get_root_path(pmc.sceneName(), "project")
    else:
        raise OSError("Level {} gives no result path.".format(level))
    target_rig_desc_path = pixo_paths.normalize(
        os.path.join(
            data_path,
            "{}.json".format(HIK_TARGET_RIG_CHAR_DESCRIPTION_NAME),
        )
    )
    source_rig_desc_path = pixo_paths.normalize(
        os.path.join(
            data_path,
            "{}.json".format(HIK_SOURCE_RIG_CHAR_DESCRIPTION_NAME),
        )
    )
    if not all(
        [
            os.path.exists(target_rig_desc_path),
            os.path.exists(source_rig_desc_path),
        ]
    ):
        _LOGGER.info(
            "No hik data description pack found in: {}".format(data_path)
        )
        return
    _LOGGER.info("Hik descriptions found in: {}".format(data_path))
    return paths.read_json_file(target_rig_desc_path), paths.read_json_file(
        source_rig_desc_path
    )


def hik_get_data_descriptions_from_config():
    """
    Get target_rig and mocap_rig hik description
    from pxo_rigging_kit.yaml config file.

    Return:
        raise EnvironmentError if fail.
        Tuple: (target_rig_dict, mocap_rig_dict)

    """
    try:
        hik_target_data_dict = core.get_config(
            "mocap_utils:hik_target_char_description"
        )
        hik_source_data_dict = core.get_config(
            "mocap_utils:hik_source_char_description"
        )
        _LOGGER.info("Hik descriptions found in package config .yaml file.")
        return hik_target_data_dict, hik_source_data_dict
    except:
        raise EnvironmentError(
            "No pxo_rigging_kit.yaml config exist."
            " Or these keys are missing:"
            " [mocap_utils:hik_target_char_description,"
            " mocap_utils:hik_source_char_description]"
        )


def hik_get_fk_ik_match_data_from_config():
    """
    Get fk/ik match data from pxo_rigging_kit.yaml config file.

    Return:
        raise EnvironmentError if fail.
        Dict:
            {
            'right_limb_side_char': 'R',
            'fk_blend_attr_value': 0,
            'ik_ctrl': 'LIMB_*_0_ik_ctrl',
            'limb_dict': {'arm':"arm", 'leg':"leg"},
            'left_limb_side_char': 'L',
            'upv_ctrl': 'LIMB_*_0_upv_ctrl',
            'fk_ik_blend_attr': 'LIMB_blend',
            'host_ctrl': 'LIMBHost_*_0_ctrl',
            'fk_list':
            ['LIMB_*_0_fk0_ctrl', 'LIMB_*_0_fk1_ctrl', 'LIMB_*_0_fk2_ctrl']
            }


    """
    try:
        result = core.get_config("mocap_utils")
        result.pop("hik_target_char_description")
        result.pop("hik_source_char_description")
        _LOGGER.info("FK/IK match data found in package config .yaml file.")
        return result
    except:
        raise EnvironmentError(
            "No pxo_rigging_kit.yaml config exist."
            + " Or these keys are missing:"
            + " [mocap_utils:host_fk_blend_list,"
            + " mocap_utils:fk_blend_attr_value,"
            + " mocap_utils:left_limb_side_char]"
        )


def hik_get_data_descriptions_level_by_level():
    """
    Get HIK description for target and mocap rig from three different levels.
    Will return it as soon as he can find one.
    First will search about json files in ./project/shot/task/shot_number/data
    or ./project/_library/assets/asset_category/assets_name/task/data.
    Second will search about json files in ./project.
    Finally take the description stored in the pxo_rigging_kit.yaml config file.

    Return:
        Tuple: (target_rig_dict, mocap_rig_dict)

    """
    data_dict_tuple = hik_get_data_descriptions_from_directory_level("scene")
    if not data_dict_tuple:
        data_dict_tuple = hik_get_data_descriptions_from_directory_level(
            "project"
        )
    if not data_dict_tuple:
        data_dict_tuple = hik_get_data_descriptions_from_config()
    return data_dict_tuple


def hik_get_fk_ik_matching_data_level_by_level():
    """
    Get FK/IK match data from different levels.
    Will return it as soon as he can find one.
    First will search about json files in ./project/shot/task/shot_number/data
    or ./project/_library/assets/asset_category/assets_name/task/data.
    Second will search about json files in ./project.
    Finally take the description stored in the pxo_rigging_kit.yaml config file.

    Return:
        Dict:
            {
            'right_limb_side_char': 'R',
            'fk_blend_attr_value': 0,
            'ik_ctrl': 'LIMB_*_0_ik_ctrl',
            'limb_dict': {'arm':"arm", 'leg':"leg"},
            'left_limb_side_char': 'L',
            'upv_ctrl': 'LIMB_*_0_upv_ctrl',
            'fk_ik_blend_attr': 'LIMB_blend',
            'host_ctrl': 'LIMBHost_*_0_ctrl',
            'fk_list':
            ['LIMB_*_0_fk0_ctrl', 'LIMB_*_0_fk1_ctrl', 'LIMB_*_0_fk2_ctrl']
            }
    """
    data_dict = hik_get_fk_ik_match_data_from_directory_level("scene")
    if not data_dict:
        data_dict = hik_get_fk_ik_match_data_from_directory_level("project")
    if not data_dict:
        data_dict = hik_get_fk_ik_match_data_from_config()
    return data_dict


def hik_add_target_rig_description(char_name, rig_data_list, namespace=None):
    """
    Add target rig hik description.

    Args:
        char_name(str): HIK character name.
        rig_data_list(list): All rig related nodes.
        namespace(str): The rig namespace without ":".
                        Default is None.

    """
    rig_hik_description = hik_get_data_descriptions_level_by_level()[0]
    hik_validate_mocap_data(rig_data_list, rig_hik_description, namespace)
    hik_add_biped_definition(
        char_name, hik_dict=rig_hik_description, namespace=namespace
    )
    _LOGGER.info("Added {} hik description to target rig.".format(char_name))


def hik_add_mocap_data_description(mocap_data, namespace=MOCAP_DATA_NAMESPACE):
    """
    Add mocap rig hik description.

    Args:
        mocap_data(list): All mocap related nodes.
        namespace(str): The mocap rig namespace without ":".
                        Default is global var: MOCAP_DATA_NAMESPACE

    """
    mocap_data_hik_description = hik_get_data_descriptions_level_by_level()[1]
    hik_validate_mocap_data(mocap_data, mocap_data_hik_description, namespace)
    hik_add_biped_definition(
        HIK_MOCAP_DATA_CHAR_DESC_NAME,
        hik_dict=mocap_data_hik_description,
        namespace=namespace,
    )
    _LOGGER.info(
        "Added {} hik description to mocap rig.".format(
            HIK_MOCAP_DATA_CHAR_DESC_NAME
        )
    )


def hik_import_and_connect_mocap(
    char_name,
    mocap_data_path,
    source_hik_dict=None,
    namespace=MOCAP_DATA_NAMESPACE,
    zero_out_joint_rotates=False,
    snap_mocap_hip_to_target_hip=False,
    target_hik_dict=None,
):
    """
    Import the mocap rig and auto connect it with the HIK character.
    Add a hik description and validate it with the mocap data.
    If validation fails will print exceptions.HikCharacterDefinitionError
    and skip connection.
    Will not raise error to keep below processes running.

    Args:
        char_name(str):  HIK character name.
        mocap_data_path(str): The mocap data path.
        source_hik_dict(dict): The source hik description corresponding
                               to the mocap_data. If not given will try to get it.
        namespace(str): Mocap rig namespace without ":".
                        Default is global var: MOCAP_DATA_NAMESPACE
        zero_out_joint_rotates(bool): Set the mocap rig hierarchy rotate values to zero.
                                      Default is False.
        snap_mocap_hip_to_target_hip(bool): Snap the mocpa data hip to the target rig hip.
                                            Default is False.
        target_hik_dict(dict): The character hik description corresponding
                               to the target_rig.

    """
    valid_mocap_nd_types = ["transform", "joint"]
    valid = True
    if not source_hik_dict:
        source_hik_dict = hik_get_data_descriptions_level_by_level()[1]
    if not target_hik_dict:
        target_hik_dict = hik_get_data_descriptions_level_by_level()[0]
    mocap_data = pmc.importFile(
        mocap_data_path,
        force=True,
        returnNewNodes=True,
        importTimeRange="override",
        importFrameRate=True
    )
    # Here we make sure that no namespace comes with the mocap data.
    mocap_data = [node.rename(node.name(stripNamespace=True, long=None)) for node in mocap_data]
    scene_utils.add_objects_to_namespace(mocap_data, namespace)

    try:
        hik_validate_mocap_data(mocap_data, source_hik_dict, namespace)

    except exceptions.HikCharacterDefinitionError as e:
        valid = False
        _LOGGER.info(e)

    if not valid:
        return

    if zero_out_joint_rotates:
        for node in [node_ for node_ in mocap_data if node_.nodeType() == "joint"]:
            if not node.rotate.isLocked():
                node.rotate.set(0, 0, 0)
            else:
                _LOGGER.warning(f"{node.name()} rotate value not setable yet. Will skip.")
    if snap_mocap_hip_to_target_hip:
        target_hip = pmc.PyNode(
            "{}:{}".format(
                HIK_TARGET_RIG_NAMESPACE, target_hik_dict.get("Hips")
            )
        )
        source_hip = pmc.PyNode(
            "{}:{}".format(
                MOCAP_DATA_NAMESPACE, source_hik_dict.get("Hips")
            )
        )
        pmc.matchTransform(
            source_hip, target_hip, pos=True, rot=True, scl=False, piv=False
        )
    pmc.mel.hikUpdateSourceList()
    hik_add_biped_definition(
        HIK_MOCAP_DATA_CHAR_DESC_NAME,
        True,
        hik_dict=source_hik_dict,
        namespace=namespace,
    )
    hik_connect_character_with_source(
        char_name, HIK_MOCAP_DATA_CHAR_DESC_NAME
    )
    _LOGGER.info(
        "Mocap data imported from {} and connected to to: {}".format(
            mocap_data_path, char_name
        )
    )


def hik_import_target_rig(
    char_name,
    file_path,
    namespace=HIK_TARGET_RIG_NAMESPACE,
    validate_t_pose=True,
    set_arm_tpose=False,
    set_leg_tpose=False,
):
    """
    Import the target rig and add hik description.
    Validate it with the rig nodes.
    If validation fails will print exceptions.HikCharacterDefinitionError
    and skip connection.
    Will not raise error to keep below processes running.

    Args:
        char_name(str): HIK character name.
        file_path(str): Rig file path.
        namespace(str): Rig namespace without ":".
                        Default is global var: HIK_TARGET_RIG_NAMESPACE.
        validate_t_pose(str): Automatic rig t pose validation.
                              This will create a confirm box if t pose is invalid.
        set_arm_tpose(bool): This will set the target arms to Tpose.
                             The validate_t_pose flag will override this flag.
                             If you want to use these pls set the validate_t_pose flag to False.
        set_leg_tpose(bool): This will set the target legs to Tpose.
                             The validate_t_pose flag will override this flag.
                             If you want to use these pls set the validate_t_pose flag to False.

    """
    valid = True
    rig_hik_description = hik_get_data_descriptions_level_by_level()[0]
    rig_data = pmc.importFile(file_path, ns=namespace, returnNewNodes=True)

    try:
        hik_validate_mocap_data(rig_data, rig_hik_description, namespace)

    except exceptions.HikCharacterDefinitionError as e:

        valid = False

        _LOGGER.info(e)

    if not valid:
        return

    if validate_t_pose:
        validate_t_pose = hik_validate_target_rig_tpose()
        if not validate_t_pose.arm:
            set_arm_tpose = pmc.confirmBox(
                title="Validate ## ARM ## Tpose",
                message="It seems that the arms of the rig not in Tpose."
                + " Do you want to set Tpose.",
            )
        if not validate_t_pose.leg:
            set_leg_tpose = pmc.confirmBox(
                title="Validate ## LEG ## Tpose",
                message="It seems that the legs of the rig not in Tpose."
                + "Do you want to set Tpose.",
            )
    if set_arm_tpose:
        hik_set_tpose(rig_hik_description, namespace)
    if set_leg_tpose:
        hik_set_tpose(rig_hik_description, namespace, "leg")
    hik_add_biped_definition(
        char_name, hik_dict=rig_hik_description, namespace=namespace
    )
    _LOGGER.info("Target rig imported from: {}".format(file_path))


@DECORATORS.refresh_suspended()
@DECORATORS.dg_evaluation()
@DECORATORS.undo
def hik_bake_mocap_to_target_rig(
    namespace=HIK_TARGET_RIG_NAMESPACE,
    clean_scene=True,
    bake_on_override_layer=True,
):
    """
    Bake the connected mocap animation to target rig.
    Switch off the viewport during processing.
    Save the current file before processing for safety.

    Args:
        namespace(str): The target rig namespace without ":".
                        Default is global var: HIK_TARGET_RIG_NAMESPACE
        clean_scene(bool): Clean the scene from mocap data and all HIK nodes.
                           Default is True.
        bake_on_override_layer(bool): Bake anim on a override anim layer.
                                      Default is True.

    """
    pmc.saveFile(force=True, type="mayaAscii")
    rig_hik_description = hik_get_data_descriptions_level_by_level()[0]
    rig_controls_list = list(rig_hik_description.values())
    if namespace:
        rig_controls_list = [
            "{0}:{1}".format(namespace, ctrl_name)
            for ctrl_name in rig_controls_list
        ]
    start_frame = pmc.playbackOptions(q=True, minTime=True)
    end_frame = pmc.playbackOptions(q=True, maxTime=True)
    pmc.bakeResults(
        rig_controls_list,
        simulation=True,
        time=(start_frame, end_frame),
        sampleBy=1,
        oversamplingRate=1,
        disableImplicitControl=True,
        preserveOutsideKeys=True,
        sparseAnimCurveBake=False,
        removeBakedAttributeFromLayer=False,
        removeBakedAnimFromLayer=False,
        bakeOnOverrideLayer=bake_on_override_layer,
        minimizeRotation=True,
        at=["tx", "ty", "tz", "rx", "ry", "rz"],
    )

    if not clean_scene:
        _LOGGER.info("Bake mocap data to target rig successfully without cleaning the scene.")

        return

    target_rig_root_nd = dag_utils.get_root_node_from_child_node(
        pmc.PyNode(rig_controls_list[0])
    )
    hik_nodes = dag_utils.get_nodes_from_nodes_class_list(HIK_NODES_LIST)
    pmc.delete(hik_nodes)
    dag_utils.delete_scene_root_nodes(target_rig_root_nd)
    hik_nodes_1 = dag_utils.get_nodes_from_nodes_class_list(HIK_NODES_LIST)
    pmc.delete(hik_nodes_1)

    _LOGGER.info("Bake mocap data to target rig successfully with cleaning the scene.")


def hik_mgear_bake_fk_to_ik(
    namespace=HIK_TARGET_RIG_NAMESPACE,
    fk_ik_match_data=None,
    to_anim_layer=True,
):
    """
    Bake mgear fk limbs animation to ik limbs.

    Args:
        namespace(str): The target rig namespace without ":".
                        Default is global var: HIK_TARGET_RIG_NAMESPACE

        fk_ik_match_data(dict): Ik fk match data. Optional.
                                If None will take it level by level.
                                Default is None.
        to_anim_layer(bool): Bake to an anim layer. Default is True

    """
    pmc.evaluationManager(mode="off")
    if not fk_ik_match_data:
        fk_ik_match_data = hik_get_fk_ik_matching_data_level_by_level()
    limbs_list = list(fk_ik_match_data["limb_dict"].values())
    for limb in limbs_list:
        for side in [
            fk_ik_match_data["left_limb_side_char"],
            fk_ik_match_data["right_limb_side_char"],
        ]:
            temp_args_dict = dict()
            temp_args_dict["blend_attr"] = fk_ik_match_data[
                "fk_ik_blend_attr"
            ].replace("LIMB", limb)
            temp_args_dict["host_ctrl_name"] = (
                fk_ik_match_data["host_ctrl"]
                .replace("LIMB", limb)
                .replace("*", side)
            )
            temp_args_dict["fk_list"] = [
                ctrl.replace("LIMB", limb).replace("*", side)
                for ctrl in fk_ik_match_data["fk_list"]
            ]
            temp_args_dict["ik_ctrl_name"] = (
                fk_ik_match_data["ik_ctrl"]
                .replace("LIMB", limb)
                .replace("*", side)
            )
            temp_args_dict["upv_ctrl_name"] = (
                fk_ik_match_data["upv_ctrl"]
                .replace("LIMB", limb)
                .replace("*", side)
            )
            temp_args_dict["namespace"] = namespace
            temp_args_dict["to_anim_layer"] = to_anim_layer
            rig_utils.mgear_match_ik_fk_in_range(**temp_args_dict)
    _LOGGER.info(
        "Match mgear ik controls to fk controls for playback range successfully."
    )


def hik_set_tpose(
    rig_hik_description=None,
    namespace=HIK_TARGET_RIG_NAMESPACE,
    limb_type="arm",
    fk_ik_match_data=None,
):
    """
    Set the hik target rig in tpose.

    Args:
        rig_hik_description(dict): The target rig hik description data.
                                   If non will take the data level by level.
                                   Default is None.
        namespace(str): The target rig namespace without ":".
                        Default is global var: HIK_TARGET_RIG_NAMESPACE
        limb_type(str): The limb type.
                        Valid values are ["arm", "leg"].
                        Default is "arm"
        fk_ik_match_data(dict): Ik fk match data. Optional.
                                If None will take it level by level.
                                Default is None.

    """
    if not rig_hik_description:
        rig_hik_description = hik_get_data_descriptions_level_by_level()[0]
    if not fk_ik_match_data:
        fk_ik_match_data = hik_get_fk_ik_matching_data_level_by_level()
    host_ctr = fk_ik_match_data["host_ctrl"]
    blend_attr = fk_ik_match_data["fk_ik_blend_attr"]
    blend_value = fk_ik_match_data["fk_blend_attr_value"]
    left_limb_side_char = fk_ik_match_data["left_limb_side_char"]
    limb = fk_ik_match_data["limb_dict"][limb_type]
    if namespace:
        namespace = "{}:".format(namespace)
    else:
        namespace = ""
    fk_ctr_list = [
        rig_hik_description["LeftArm"],
        rig_hik_description["LeftForeArm"],
        rig_hik_description["LeftHand"],
    ]
    if limb_type != "arm":
        fk_ctr_list = [
            rig_hik_description["LeftUpLeg"],
            rig_hik_description["LeftLeg"],
        ]
    host = "".join(
        [
            namespace,
            host_ctr.replace("LIMB", limb).replace("*", left_limb_side_char),
        ]
    )
    blend_attr = blend_attr.replace("LIMB", limb)
    fk_attr_list = ["".join([namespace, fk_ctrl]) for fk_ctrl in fk_ctr_list]
    set_rig_tpose(fk_attr_list, host, blend_attr, blend_value, limb_type)


def hik_validate_target_rig_tpose(
    rig_hik_description=None, namespace=HIK_TARGET_RIG_NAMESPACE
):
    """
    Validate the hik target rig Tpose by worldspace angle in the scene.

    Args:
        rig_hik_description(dict): The target rig hik description data.
                                   If non will take the data level by level.
                                   Default is None.
        namespace(str): The target rig namespace without ":".
                        Default is global var: HIK_TARGET_RIG_NAMESPACE

    Return:
        namedtuple:
                (arm:True or False, leg:True or False)

    """
    if not rig_hik_description:
        rig_hik_description = hik_get_data_descriptions_level_by_level()[0]
    if not namespace:
        namespace = ""
    else:
        namespace = "{}:".format(namespace)
    left_arm = "{}{}".format(namespace, rig_hik_description["LeftArm"])
    left_elbow = "{}{}".format(namespace, rig_hik_description["LeftForeArm"])
    left_leg = "{}{}".format(namespace, rig_hik_description["LeftUpLeg"])
    left_knee = "{}{}".format(namespace, rig_hik_description["LeftLeg"])
    return validate_rig_tpose(left_arm, left_elbow, left_leg, left_knee)

# In the future we would need a gui interface for that as well.
# We leave it like this for the moment.


@DECORATORS.undo
@DECORATORS.refresh_suspended()
def hik_batch_retarget_to_anim_studio_library(
    save_dir_name,
    target_rig_path,
    mocap_data_dir,
    zero_out_joint_rotates_in_mocap=False,
    snap_mocap_hip_to_target_hip=False,
    set_arm_tpose=False,
    set_leg_tpose=False,
):
    """
    Batch retarget a bunch of mocap data in serial to given target rig and export it as studio library anim.
    Because this is a batch process no QC, playblast thumbnail or anim tweaking happens.
    What you get is raw anim data for given target rig.
    Keep in mind that you will need the corresponding hik description dict for the target and mocap rig.
    You can get and store these dict like we describe in the top module doc string.
    And you have to save a emtpy initial scene in a pixo anim task scene.
    The saved studio library will have the same name like the mocap data.

    Args:
         save_dir_name(str): The studio library save path.
         target_rig_path(str): Path to the target rig.
         mocap_data_dir(str): Path to the mocap data.
         zero_out_joint_rotates_in_mocap(bool): This will zero out all rotate values of the mocap data rig.
                                                This can be a way to set the mocap rig back to Tpose.
                                                Default value is False.
         snap_mocap_hip_to_target_hip(bool): This will snap the mocap rig root/hip to the root/hip of the target rig.
                                             This is useful if if the mocap rig is taller and the target rig
                                             feet would fly above the origin after retargeting.
                                             Default is False.
         set_arm_tpose(bool): This will set the target arms to Tpose.
                              Default is False.
         set_leg_tpose(bool): This will set the target legs to Tpose.
                              Default is False.

    Example:
        >>> from pxo_rigging_kit.maya_utils.rigging import mocap_utils
        >>> save_dir_name = r"X:\_animation\mocap_data"
        >>> target_rig_path = r"X:\woodwalkers_wow-4823\_library\assets\characters\chr_preGenericWoman\rig
                                  \_publish\wow_chr_preGenericWoman_rig_v004_jwo.mb"
        >>> mocap_data_dir = r"X:\_animation\mocap_data\test"
        >>> mocap_utils.hik_batch_retarget_to_anim_studio_library(save_dir_name, target_rig_path,
                                                                  mocap_data_dir, True, True, True, True)

    """
    current_scene = None
    if not current_scene:
        current_scene = pmc.sceneName()

    mocap_data = [
        mocap
        for mocap in os.listdir(mocap_data_dir)
        if MOCAP_DATA_TYPE in mocap
    ]

    if not os.path.exists(save_dir_name):
        os.mkdir(save_dir_name)

    for fbx in mocap_data:
        path = pixo_paths.normalize(os.path.join(mocap_data_dir, fbx))

        pmc.newFile(force=True)
        pmc.saveAs(current_scene, force=True)

        export_path = pixo_paths.normalize(
                os.path.join(save_dir_name, fbx.split(".fbx")[0])
        )

        try:
            hik_import_target_rig(
                HIK_TARGET_RIG_CHAR_DESC_NAME,
                target_rig_path,
                validate_t_pose=False,
                set_arm_tpose=set_arm_tpose,
                set_leg_tpose=set_leg_tpose,
            )

            hik_import_and_connect_mocap(
                HIK_TARGET_RIG_CHAR_DESC_NAME,
                path,
                zero_out_joint_rotates=zero_out_joint_rotates_in_mocap,
                snap_mocap_hip_to_target_hip=snap_mocap_hip_to_target_hip,
            )
            start_frame = pmc.playbackOptions(query=True, minTime=True)
            end_frame = pmc.playbackOptions(query=True, maxTime=True)

            pmc.playbackOptions(animationStartTime=start_frame)
            pmc.playbackOptions(animationEndTime=end_frame)

            pmc.currentTime(start_frame)

            hik_bake_mocap_to_target_rig(bake_on_override_layer=False)
            hik_mgear_bake_fk_to_ik(to_anim_layer=False)
            rig_control_interface = rig_utils.get_anim_control_interface(
                as_strings=True, namespace="{}:".format(HIK_TARGET_RIG_NAMESPACE)
            )
            animitem.save(
                export_path,
                objects=rig_control_interface,
                frameRange=(start_frame, end_frame),
                bakeConnected=True,
            )
            _LOGGER.info(
                "{} mocap exported as studio library to: {}".format(
                    fbx, save_dir_name
                )
            )
        except:
            pmc.warning("Retarget failed for: {}".format(path))




@DECORATORS.undo
def set_rig_tpose(
    fk_ctrl_name_list,
    host_ctrl_name,
    blend_attr,
    fk_value,
    limb_typ="arm",
    side_str="L",
):
    """
    Set a character biped rig to Tpose.
    The values for the Tpose are calculate by the
    worldspace angle of the given fk controls.

    Args:
        fk_ctrl_name_list(list): The fk control names as strings in a list.
        host_ctrl_name(str): The host control with the fk/ik blend attribute.
        blend_attr(str): The fk/ik blend attribute name.

        limb_typ(str): The type of the limb. Valid values are ["arm", "leg"].
                       Default is "arm".
        side_str(str): The actual control side.
                       Valid values are ["L", "R", "l", "r"]
                       Default is "L".

    """
    opposite_side_str = ""
    if side_str == "L":
        opposite_side_str = "R"
    elif side_str == "R":
        opposite_side_str = "L"
    elif side_str == "l":
        opposite_side_str = "r"
    elif side_str == "r":
        opposite_side_str = "l"
    t_pose_rot_values = (0, 0, 0)
    if limb_typ != "arm":
        t_pose_rot_values = (0, 0, -90)
    fk_ctrl_name_list = [
        pmc.PyNode(ctrl_name) for ctrl_name in fk_ctrl_name_list
    ]
    pmc.PyNode(host_ctrl_name).attr(blend_attr).set(fk_value)
    pmc.PyNode(
        host_ctrl_name.replace(
            "_{}_".format(side_str), "_{}_".format(opposite_side_str)
        )
    ).attr(blend_attr).set(fk_value)
    for x in range(len(fk_ctrl_name_list)):
        try:
            obj_1 = fk_ctrl_name_list[x + 1]
        except IndexError:
            continue

        obj_0 = fk_ctrl_name_list[x]
        distance_ = rig_utils.get_distance(obj_0, obj_1)
        temp_jnt_0 = pmc.createNode("joint")
        temp_jnt_1 = pmc.createNode("joint")
        temp_jnt_0.addChild(temp_jnt_1)
        z_angle = rig_utils.get_angle(obj_0, obj_1, "z")
        y_angle = rig_utils.get_angle(obj_0, obj_1, "y")
        temp_jnt_1.translateX.set(distance_)
        pmc.matchTransform(
            temp_jnt_0, obj_0, pos=True, rot=False, scl=False, piv=False
        )
        temp_jnt_0.rotate.set(0, y_angle, z_angle)
        p_con = pmc.parentConstraint(temp_jnt_0, obj_0, mo=True)
        temp_jnt_0.rotate.set(t_pose_rot_values)
        pmc.delete(p_con)
        pmc.delete(temp_jnt_0)
        r_ctrl = pmc.PyNode(
            obj_0.name(long=None).replace(
                "_{}_".format(side_str), "_{}_".format(opposite_side_str)
            )
        )
        r_ctrl.rotate.set(obj_0.rotate.get())


def validate_rig_tpose(
    left_arm_fk_ctrl, left_elbow_fk_ctrl, left_leg_fk_ctrl, left_knee_fk_ctrl
):
    """
    Validate the rig Tpose.

    Args:
        left_arm_fk_ctrl(str): The left arm fk control name.
        left_elbow_fk_ctrl(str): The left elbow control name.
        left_leg_fk_ctrl(str): The left leg fk control name.
        left_knee_fk_ctrl(str): The left knee fk control name.

    Return:
        namedtuple:
                (arm:True or False, leg:True or False)

    """
    arm_dot = rig_utils.get_dot_product(
        pmc.PyNode(left_arm_fk_ctrl), pmc.PyNode(left_elbow_fk_ctrl), "z"
    )
    leg_dot = rig_utils.get_dot_product(
        pmc.PyNode(left_leg_fk_ctrl), pmc.PyNode(left_knee_fk_ctrl), "z"
    )
    arm_validation = rig_utils.is_almost_equal(arm_dot, 0.0, 0.1, 3)
    leg_validation = rig_utils.is_almost_equal(leg_dot, -1.0, 0.001, 3, False)
    result = namedtuple("result", ["arm", "leg"])
    return result(arm_validation, leg_validation)
