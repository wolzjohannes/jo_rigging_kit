# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import built-in modules
from builtins import str
import getpass
from importlib import reload
import json
# Import python standart import
import logging
import os
import pprint
import re

# Import third-party modules
from future import standard_library
from maya_scene_io import export_scene
from maya_scene_io.paths import get_temp_path
import pixo_naming
import pixo_paths
from pixo_paths.paths import normalize as pixo_normpath
# Import maya modules
import pymel.core as pmc

# Import local modules
from pxo_rigging_kit.maya_utils import decorators

#######################################################
# GLOBALS
#######################################################

standard_library.install_aliases()
_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)
DECORATORS = decorators.Decorators()
DECORATORS.debug = True
DECORATORS.logger = _LOGGER

##########################################################
# FUNCTIONS
##########################################################


# add outliner to metadata for guides
def append_to_json_dict(dict_path, file_path, file_name):
    """
    Opens a json file in the specified file_path with the dedicated file_name and appends the data to the dict path.

    Args:
        written_data: The data to be written.
        dict_path: the dictionary keys under wich i
        file_path(path): Path to the location where it will be stored.
        file_name(str): Name of the file with [.json] suffix

    Returns:
        Str: File Path.
    """

    file_path_name = pixo_normpath(os.path.join(file_path, file_name))
    with open(file_path_name, "r") as operating_file:
        dictionary_file = json.load(operating_file)
        path_to_object = list()

        return path_to_object, get_recursively(dictionary_file, dict_path, path_to_object)

def save_file():
    dragon_name = "dragonWild"
    attributes_dict_list = []

    membrane_main_controls = pmc.ls("*ingMembrane_*_*_*_main_ctrl")
    membrane_main_non_guides = [ctl for ctl in membrane_main_controls if "guide" not in ctl.shortName()]

    for node in membrane_main_non_guides:
        ud_attributes = []
        for attr_ in node.listAttr(ud=True):
            if not attr_.type() == "enum":
                attr_name = attr_.attrName(longName=True)
                if "PXM" not in attr_name:
                    ud_attributes.append(attr_name)
        for attr__ in ud_attributes:
            if "clamp" in attr__:
                ud_attributes.remove(attr__)
        for attr_name_ in ud_attributes:
            data_dict = {"control":   node.name(),
                         "attribute": attr_name_,
                         "value":     node.attr(attr_name_).get()}
            attributes_dict_list.append(data_dict)

    with open(r"C:\Users\christof.puehringer\Desktop\lololol.json", "w") as out_file:
        json.dump(attributes_dict_list, out_file, indent=4)

    #print(get_recursively(dictionary_file, dict_path))


def get_recursively(dictionary_file, dict_path, path_to_object):
    """
    Takes a dict with nested lists and dicts,
    and searches all dicts for a key of the field
    provided.
    """
    fields_found = []

    for iteration_, (key, value) in enumerate(dictionary_file.items()):

        if key == dict_path:
            fields_found.append(value)

        elif isinstance(value, dict):
            results = get_recursively(dictionary_file, dict_path, path_to_object)
            for result in results:
                fields_found.append(result)
                path_to_object.append(key)

        elif isinstance(value, (list, tuple)):
            for item in value:
                if isinstance(item, dict):

                    more_results = get_recursively(dictionary_file, dict_path, path_to_object)
                    for another_result in more_results:
                        path_to_object.append(iteration_)
                        fields_found.append(another_result)

    return fields_found


append_to_json_dict("dragonWild", r"C:\Users\christof.puehringer\gitlab\mgear-post-scripts-for-cr2\scripts\reg", "rig_default_settings.json")