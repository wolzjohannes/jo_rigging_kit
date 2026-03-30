# mgear / pixo dynamic joints post script
# www.pixomondo.com
# Date: 04 / 24 / 2023
# Artist: Christof Puehringer / Rigging TD

"""
basic for lods


from pxo_rigging_kit.maya_utils.lod_utils import save as lod_save

lod_save()


from pxo_rigging_kit.maya_utils.lod_utils import load as lod_load

lod_load()
"""

# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Import built-in modules
from builtins import range
from builtins import str
import logging

# Import python standard import
import os
import os.path
import pprint
from typing import Optional

# Import third-party modules
from future import standard_library
import maya.cmds as cmds
from pixo_paths.paths import normalize as pixo_normpath
import pymel.core as pmc

# Import local modules
from pxo_rigging_kit import constants
from pxo_rigging_kit import paths
from pxo_rigging_kit import versioncontrol_utils
from pxo_rigging_kit.maya_utils import decorators
from pxo_rigging_kit.maya_utils import paths_utils
from pxo_rigging_kit.maya_utils import dag_utils

standard_library.install_aliases()

##########################################################
# GLOBALS
##########################################################

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)
RIG_ROOT_SUB_CONTAINERS = ["MGEAR", "MODEL_ASSETS", "XTRA", "NO_TRANSFORM"]
DECORATORS = decorators.Decorators()
DECORATORS.debug = True
DECORATORS.logger = _LOGGER

# lod names
_DATA_LOOKUP_EXPORT_NAME = "lod_data_dict"
_DATA_LOCATION_FOLDER_NAME = "PXO_LOD"

##########################################################
# FUNCTIONS
##########################################################


def write_lod_set_info(lod_dict=None, export_path=False, prettyprint=True):
    """
    Saves the lod dictionary that was found in the scene.

    Args:
        lod_dict(dict): The lod data dict.
        export_path(str, path, bool): The export path.
                                      If None will take the data directory of the
                                      asset and create version control srtucture.
        prettyprint(bool): Flag to check if output shall be printed.

    Returns:
        Dict: Returns the created LOD dictionary.
    """

    if export_path:
        vers_lod_path = pixo_normpath(export_path)

    else:
        export_path = paths_utils.get_project_paths(pmc.sceneName())

        # general save operations
        export_path = os.path.join(export_path, _DATA_LOCATION_FOLDER_NAME)
        paths.check_and_create_path(export_path)
        vers_lod_path = versioncontrol_utils.check_and_create_date(export_path)

    if not lod_dict:
        lods_dict_ = get_lod_data_dict(strip_namespace=False, long=True)
    else:
        lods_dict_ = lod_dict

    paths.write_json_file(
            lods_dict_,
            vers_lod_path,
            "{}.json".format(_DATA_LOOKUP_EXPORT_NAME),
    )

    if prettyprint:
        pprint.pprint(lods_dict_)

    return lods_dict_


def read_lod_set_info(import_path=False, prettyprint=False):
    """
    Gets the latest version controlled lod set info that was exported as a dict.
    Args:
        import_path(str, path, bool): If false, searches in scene directory, if str or path given, it looks there.
        prettyprint(bool): Checker if result shall be pretty printed.

    Returns:
        Dict: The previously saved lod_dict.
    """
    if not import_path:
        import_path = paths_utils.get_project_paths(pmc.sceneName())

        import_path = pixo_normpath(os.path.join(import_path, _DATA_LOCATION_FOLDER_NAME))
        paths.check_and_create_path(import_path)

        vers_lod_path = versioncontrol_utils.get_latest_path(import_path)
    else:
        vers_lod_path = import_path

    data_file = paths.read_files_of_directory(vers_lod_path)

    if not data_file:
        raise ValueError("no file")

    list_length = len(data_file)

    if list_length > 1:
        raise ValueError("too many items")

    json_file_location = pixo_normpath(
            os.path.join(vers_lod_path, "{}.json".format(_DATA_LOOKUP_EXPORT_NAME))
    )
    data_lookup_info = paths.read_json_file(json_file_location)

    if not isinstance(data_lookup_info, dict):
        raise TypeError("The content of [{}] is not of type dict".format(data_lookup_info))

    if prettyprint:
        pprint.pprint(data_lookup_info)

    return data_lookup_info


def apply_lod_set_info(lod_data_dict):
    """
    Creates the Root set hierarchy and adds the subsets.

    Args:
        lod_data_dict(dict): The lod data dict.

    Returns:
       Dict: The lod data dict.
    """
    lod_sets = lod_data_dict["lod_sets"]

    kill()

    scene_lod_sets = create(lod_set_names=lod_sets)
    for lod, lod_dict in (sorted(lod_data_dict["lods"].items())):
        # get lod meta data
        lod_name = str(lod_dict[constants.LOD_NAME_META_ATTR])
        lowest_lod = lod_dict[constants.LOD_LOWEST_META_ATTR]
        highest_lod = lod_dict[constants.LOD_HIGHEST_META_ATTR]
        set_name = lod_dict[constants.LOD_SET_NAME_META_ATTR]
        lod_master = lod_dict[constants.LOD_MASTER]
        # get sets from scene
        scene_lod_set_data_list = scene_lod_sets[set_name]
        set_obj = scene_lod_set_data_list[0]
        sub_set_objects = scene_lod_set_data_list[1]
        # apply meta data
        set_obj.attr(constants.LOD_NAME_META_ATTR).set(lod_name)
        set_obj.attr(constants.LOD_LOWEST_META_ATTR).set(lowest_lod)
        set_obj.attr(constants.LOD_HIGHEST_META_ATTR).set(highest_lod)
        set_obj.attr(constants.LOD_MASTER).set(lod_master)
        # fill set members
        fill_sub_set(lod_dict, sub_set_objects)
    return get_lod_data_dict(strip_namespace=False, long=True)


def fill_sub_set(lod_dict, sub_sets):
    """
    Method fills the subset with the needed for

    Args:
        lod_dict(dict): The whole dictionary of the lod sets setup.
        sub_set(str): Name of the subset.

    Returns:
        Bool: True if it ran through.
    """
    for sub_set_name, data_list in lod_dict.items():
        set_obj = sub_sets.get(sub_set_name, None)
        if set_obj:
            set_members = []
            for node in data_list:
                node_ = []
                try:
                    node_ = [pmc.PyNode(node)]
                except:
                    pmc.warning(f"{node} not exist or is not unique")
                    continue
                set_members.extend(node_)
            set_obj.addMembers(set_members)


def get_lod_sets():
    """
    Get the lod sets from scene.

    Returns:
        None if not existing.
        Tuple:
            ([lod_sets],[sub_sets])

    """
    lod_sets = [
        node
        for node in pmc.ls(type="objectSet")
        if node.hasAttr(constants.LOD_ROOT_SET_META_ATTR_NAME)
        and node.attr(constants.LOD_ROOT_SET_META_ATTR_NAME).get() == 1
    ]
    sub_sets = [
        node
        for node in pmc.ls(type="objectSet")
        if node.hasAttr(constants.LOD_SUB_SET_TYPE_META_ATTR_NAME)
        and node.attr(constants.LOD_SUB_SET_META_ATTR_NAME).get() == 1
    ]
    if lod_sets and sub_sets:
        return lod_sets, sub_sets


def check_lod_exists(lod_set):
    """
    Checks if Item exists and is an objectSet.

    Args:
        lod_set(str): The name of the set to be checked.

    Returns:
        Bool: True if exists, false if not.
    """
    if cmds.objExists(lod_set) and cmds.objectType(lod_set, isType="objectSet"):
        return True

    return False


def get_lod_data_dict(strip_namespace=False, long=None):
    """
    Get lod data from the lod sets as dictionary.

    Result:
        Dict:
            {
            'lod_sets': [str, str],
            'sub_sets': [str, str],
            'lod_count': int,
            'lods': {
                '0': {'dag': [str, str], 'geo': [str, str],
                      'non_dag': [str, str], 'roots': [str, str],
                      'lod_name': 'proxy', 'lowest_lod': True, 'highest_lod': False,
                      'set_name': 'LOD_0',
                      'lod_master_number': "2",
                      'lod_master': False},
                '1': {'dag': [str, str], 'geo': [str, str],
                       'non_dag': [str, str], 'roots': [str, str],
                       'lod_name': 'low', 'lowest_lod': True, 'highest_lod': False,
                       'set_name': 'LOD_1',
                       'lod_master_number': "2",
                       'lod_master': False},
                '2': {'dag': [str, str], 'geo': [str, str],
                       'non_dag': [str, str], 'roots': [str, str],
                       'lod_name': 'high', 'lowest_lod': False, 'highest_lod': True,
                       'set_name': 'LOD_2',
                       'lod_master_number': "2",
                       'lod_master': True}
             }
    """
    result_dict = {}
    sets = get_lod_sets()

    # exit loop early
    if not sets:
        raise StopIteration(
            "No LOD and LOD sub sets found in the scene."
            " Or maybe the sets do not have the"
            " needed meta data attributes"
        )

    lod_sets = sets[0]
    sub_sets = sets[1]
    temp_dict = {}
    result_dict["lod_sets"] = [
        str(node.name(stripNamespace=strip_namespace)) for node in lod_sets
    ]
    result_dict["sub_sets"] = [
        str(node.name(stripNamespace=strip_namespace)) for node in sub_sets
    ]
    result_dict["lod_count"] = len(lod_sets)
    # First find the master lod
    lod_master_number = None
    for lod_set in lod_sets:
        master_lod = lod_set.attr(constants.LOD_MASTER).get()
        if master_lod:
            lod_master_number = str(lod_set.attr(constants.LOD_INDEX_META_ATTR).get())
    # Setup up the lod dict.
    for lod_set in lod_sets:
        lod_temp_dict = {
            str(
                sub_set.attr(
                    constants.LOD_SUB_SET_TYPE_META_ATTR_NAME
                ).get()
            ): [
                str(node.name(stripNamespace=strip_namespace, long=long))
                for node in sub_set.members()
            ]
            for sub_set in lod_set.members()
            if sub_set in sub_sets
        }
        # fill dict
        lod_temp_dict[constants.LOD_NAME_META_ATTR] = str(lod_set.attr(constants.LOD_NAME_META_ATTR).get())
        lod_temp_dict[constants.LOD_LOWEST_META_ATTR] = lod_set.attr(constants.LOD_LOWEST_META_ATTR).get()
        lod_temp_dict[constants.LOD_HIGHEST_META_ATTR] = lod_set.attr(constants.LOD_HIGHEST_META_ATTR).get()
        lod_temp_dict[constants.LOD_SET_NAME_META_ATTR] = str(lod_set.name(long=None))
        lod_temp_dict[constants.LOD_MASTER] = lod_set.attr(constants.LOD_MASTER).get()
        lod_temp_dict[constants.LOD_MASTER_NUMBER] = lod_master_number

        # fill into temp dict
        temp_dict[str(lod_set.attr(constants.LOD_INDEX_META_ATTR).get())] = lod_temp_dict

    result_dict["lods"] = temp_dict

    return result_dict


def create(amount: int = 5,
           sub_sets: Optional[list] = None,
           lod_set_names: Optional[list] = None,
           ) -> dict:
    """
    Creates LOD sets for a specific Amount.
    This serves as template for the lod sets.

    Args:
        amount(int): The count of lod sets that will be created. Default is 5.
        sub_sets(List): List with strings.
                        Specifies the amount and names of the sub sets.
                        If None default is:
                        ["roots", "geo", "non_dag", "dag"]
        lod_set_names(list): The names for the lod sets. This will override the amount flag.
                             The new amount will be the length of the list.
                             If None will generate default names in this pattern : "LOD_0".
                             Default is None.

    Returns:
        Dict: {
                "LOD_0": [
                         nt.ObjectSet["LOD_0"],
                         {"dag": nt.ObjectSet["LOD_0_dag"], "non_dag": nt.ObjectSet["LOD_0_non_dag"]}
                         ]
               }

    """
    lod_sets_dict = {}
    if not sub_sets:
        sub_sets = dag_utils.SUB_SETS_LIST
    if not lod_set_names:
        lod_set_names = ["LOD_{}".format(value) for value in range(amount)]
    for value, set_name in enumerate(lod_set_names):
        temp_dict = {}
        lod_set = pmc.sets(n=set_name, empty=True)
        lod_set.addAttr(
            constants.LOD_ROOT_SET_META_ATTR_NAME, type="bool", dv=True
        )
        lod_set.attr(constants.LOD_ROOT_SET_META_ATTR_NAME).set(lock=True)
        lod_set.addAttr(constants.LOD_MASTER, type="bool", keyable=False)
        lod_set.addAttr(constants.LOD_INDEX_META_ATTR, type="long", dv=value)
        lod_set.attr(constants.LOD_INDEX_META_ATTR).set(lock=True)
        lod_set.addAttr(constants.LOD_NAME_META_ATTR, type="string")
        lod_set.addAttr(constants.LOD_LOWEST_META_ATTR, type="bool", keyable=False)
        lod_set.addAttr(constants.LOD_HIGHEST_META_ATTR, type="bool", keyable=False)

        for lod_comp in sub_sets:
            lod_comp_set = pmc.sets(
                n=f"LOD_{value}_{lod_comp}", empty=True
            )
            lod_set.add(lod_comp_set)
            lod_comp_set.addAttr(
                constants.LOD_SUB_SET_META_ATTR_NAME, type="bool", dv=True
            )
            lod_comp_set.attr(constants.LOD_SUB_SET_META_ATTR_NAME).set(
                lock=True
            )
            lod_comp_set.addAttr(
                constants.LOD_INDEX_META_ATTR, type="long", dv=value
            )
            lod_comp_set.attr(constants.LOD_INDEX_META_ATTR).set(lock=True)
            lod_comp_set.addAttr(
                constants.LOD_SUB_SET_TYPE_META_ATTR_NAME, type="string"
            )
            lod_comp_set.attr(constants.LOD_SUB_SET_TYPE_META_ATTR_NAME).set(
                lod_comp
            )
            lod_comp_set.attr(constants.LOD_SUB_SET_TYPE_META_ATTR_NAME).lock()
            temp_dict[lod_comp] = lod_comp_set
        lod_sets_dict[lod_set.name(long=False)] = [lod_set, temp_dict]

    return lod_sets_dict


def save(lod_dict=None, strip_namespace=False, long=False, export_path=False):
    """
    Wrapper for the saving of the LOD dict.

    Returns:
        Dict(lod_dict): The dictionary containing the lods
    """
    if not lod_dict:
        lod_dict = get_lod_data_dict(strip_namespace=strip_namespace, long=long)

    return write_lod_set_info(lod_dict, export_path=export_path)


def load(load_path=False, remap_values=None):
    """
    Wrapper for the loading of the LOD dict.

    Args:
        load_path(str, path, bool): If false, searches in scene directory, if str or path given, it looks there.
        remap_values(list): List filled with tuples of replace strings.
                            Examples:
                                 [["vhagar", "syrax"], ["vha_01:", "syr_01:"], ["Vhagar", "Syrax"]]

    Returns:
        Dict(lod_dict): The dictionary containing the lods

    """

    lod_dict = read_lod_set_info(import_path=load_path, prettyprint=False)

    if not lod_dict:
        raise ValueError("LOD dict is empty.")

    if remap_values:
        lod_dict = remap_lod_data_dict(lod_dict, remap_values)

    apply_lod_set_info(lod_dict)

    return lod_dict


def kill() -> bool:
    """
    Removes the preexisting LOD dict.

    Returns:
        bool: True if deleted, false if not
    """

    scene_lod_sets = get_lod_sets()

    if not scene_lod_sets:
        _LOGGER.warning("No LOD sets found in the scene!")
        return False

    try:
        pmc.delete(scene_lod_sets)

    except pmc.general.MayaNodeError as e:
        _LOGGER.warning(f"Unable to delete LOD sets! : {e}")
        return False

    return True


def remap_lod_data_dict(lod_data_dict, remap_values):
    """
    Remap data dict lod values with given remap values.
    This is a pure string remapping.

    Args:
        lod_data_dict(dict): The lod data dict.
        remap_values(list): List filled with tuples of replace strings.
                            Examples:
                                 [["vhagar", "syrax"], ["vha_01:", "syr_01:"], ["Vhagar", "Syrax"]]

    Returns:
        Dict: The same but with remapped strings.

    """

    lod_dict = lod_data_dict["lods"]

    if not lod_dict:
        raise ValueError("LOD dict is empty.")

    for lod in lod_dict:
        data_dict = lod_dict[lod]

        for set_name in data_dict:
            data_value = data_dict[set_name]

            for remap_tuple in remap_values:
                if isinstance(data_value, list):
                    data_value = [str_.replace(remap_tuple[0], remap_tuple[1]) for str_ in data_value]
                if isinstance(data_value, str):
                    data_value = data_value.replace(remap_tuple[0], remap_tuple[1])

            data_dict[set_name] = data_value

    return lod_data_dict


def change_lod_set_number(lod_set_root: pmc.PyNode,
                          new_lod_set_number: int,
                          ):

    lod_sets = lod_set_root.members()
    current_index = lod_set_root.attr(constants.LOD_INDEX_META_ATTR).get()

    for node in lod_sets:
        new_name = node.name(long=None).replace(f"_{current_index}", f"_{str(new_lod_set_number)}")
        node.attr(constants.LOD_INDEX_META_ATTR).unlock()
        node.attr(constants.LOD_INDEX_META_ATTR).set(new_lod_set_number)
        node.attr(constants.LOD_INDEX_META_ATTR).lock()
        node.rename(new_name)

    lod_set_root.rename(lod_set_root.name(long=None).replace(f"_{current_index}",
                                                             f"_{str(new_lod_set_number)}"
                                                             )
                        )

    lod_set_root.attr(constants.LOD_INDEX_META_ATTR).unlock()
    lod_set_root.attr(constants.LOD_INDEX_META_ATTR).set(new_lod_set_number)
    lod_set_root.attr(constants.LOD_INDEX_META_ATTR).lock()
