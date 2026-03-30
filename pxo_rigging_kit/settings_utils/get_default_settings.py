"""
Module to get the path to the default settings for usage in other packages as well.


Example:

"""

# Import built-in modules
from functools import wraps
import inspect
import logging
import os

# Import third-party modules
from pixo_paths import normalize

# Import local modules
from pxo_rigging_kit.constants import DEFAULT_SETTING_FILE_NAMES
from pxo_rigging_kit.maya_utils import decorators
from pxo_rigging_kit.maya_utils import exceptions
from pxo_rigging_kit.paths import read_json_file

##########################################################
# GLOBALS
##########################################################

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.WARNING)
DECORATORS = decorators.Decorators()
DECORATORS.debug = True
DECORATORS.logger = _LOGGER

##########################################################
# DYNAMIC FUNCTIONS
##########################################################


@DECORATORS.get_default_settings_wrp
def get_default_setting_file(*args, file_functionality=None):
    loc_folder = args[0]

    if not file_functionality:
        exceptions.DefaultSettingsArgumentError()

    if file_functionality not in DEFAULT_SETTING_FILE_NAMES.keys():
        exceptions.DefaultSettingsSettingsError()

    file_name = DEFAULT_SETTING_FILE_NAMES[file_functionality]
    file_path = normalize(os.path.join(loc_folder, file_name))

    if not os.path.exists(file_path):
        exceptions.DefaultSettingsImportError()

    return file_path


def get_default_control_visibility_data():
    file_path = get_default_setting_file(file_functionality="controlVisibility")

    return read_json_file(file_path)


def get_default_wing_attr_data():
    file_path = get_default_setting_file(file_functionality="wingAttributes")

    return read_json_file(file_path)


