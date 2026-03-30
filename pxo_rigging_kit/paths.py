# Author:     Christof Puehringer / Rigging TD

"""
module for path interactions
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Import built-in modules
import errno
import json

# Import python standard import
import logging
import os

try:
    # Import built-in modules
    from pathlib import Path
except:
    pass

try:
    # Import built-in modules
    from os import scandir
except ImportError:
    from scandir import scandir


# Import third-party modules
from future import standard_library
from pixo_paths.paths import normalize as pixo_normpath

# Import local modules
from pxo_rigging_kit.maya_utils import exceptions

standard_library.install_aliases()

##########################################################
# GLOBALS
##########################################################

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)


##########################################################
# FUNCTIONS
##########################################################


def check_and_create_path(path):
    """
    Looks if a path is existing already, if False: a new path is created if True: the path is returned as is.

    Args:
        path(path): the path that is checked.

    Returns:
        normpath: the path that is wanted.
    """
    path = pixo_normpath(path)
    if not os.path.exists(path):
        try:
            os.mkdir(path)
            return pixo_normpath(path)

        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise

    else:
        return path


def read_folders_of_directory(path):
    """
    Goes through directory and returns all items that are directories as well(folders).

    Args:
        path(path):  The path to be queried.

    Returns:
        List: All directories in the path in a sorted manner.
    """
    if not path:
        _LOGGER.warning("found nothing, was given NONE")
    folders = list(x.name for x in scandir(path) if x.is_dir())
    folders.sort()
    return folders


def read_files_of_directory(path):
    """
    Goes through directory and returns all items that are files.

    Args:
        path(path):  The path to be queried

    Returns:
        List: All files in the path in a sorted manner.
    """
    if not path:
        _LOGGER.warning("found nothing, was given NONE")
        return None

    files = list(x.name for x in scandir(path) if x.is_file())
    files.sort()
    return files


def read_json_file(path):
    """
    Reads the file at path location, needs the [.json] suffix to work.

    Args:
        path(path):  The path to the file.

    Returns:
        Str: Json data.
    """
    with open(path) as p:
        return json.load(p)


def write_json_file(data, file_path, file_name):
    """
    Writes a file at [file_path], with the name of [file_name] that contains the data from [data].

    Args:
        data: The data to be written.
        file_path(path): Path to the location where it will be stored.
        file_name(str): Name of the file with [.json] suffix

    Returns:
        Str: File Path.
    """

    file_path_name = pixo_normpath(os.path.join(file_path, file_name))

    with open(file_path_name, "w") as out_file:
        json.dump(data, out_file, indent=4)
        return file_path_name


def get_package_root_path():
    """
    Return the package root path.
    """
    root_path = os.environ.get(
        "REZ_PXO_RIGGING_KIT_ROOT", False
    ) or os.path.join(__file__.split("pxo_rigging_kit")[0], "pxo_rigging_kit")
    return pixo_normpath(root_path)


def get_package_icons_path():
    """
    Return the package icons path.
    """
    package_root_path = get_package_root_path()
    return pixo_normpath(os.path.join(package_root_path, "icons"))


def get_package_default_settings_path():
    """
    Return the package default settings path.
    """

    package_root_path = get_package_root_path()
    return pixo_normpath(os.path.join(package_root_path, "default_settings"))


def get_guides_template_path():
    """
    Get guides template path in the repository
    """
    return pixo_normpath(
        os.path.join(get_package_root_path(), "guide_templates")
    )


def get_mgear_post_script_path():
    """
    Get the megar post script path of the repo.
    """
    return pixo_normpath(
        os.path.join(
            get_package_root_path(),
            "site-packages",
            "pxo_rigging_kit",
            "maya_utils",
            "mgear",
            "build_post_scripts",
        )
    )


def get_mgear_pre_script_path():
    """
    Get the megar pre script path of the repo.
    """
    return pixo_normpath(
        os.path.join(
            get_package_root_path(),
            "site-packages",
            "pxo_rigging_kit",
            "maya_utils",
            "mgear",
            "build_pre_scripts",
        )
    )


def check_directory_if_empty(dir_path):
    """
    Check if the directory is empty

    Args:
        dir_path(str): Directory path.

    Return:
        None if epmty.
        Iterlist if not empty.

    """
    dir_path = pixo_normpath(dir_path)

    if not os.path.exists(dir_path):
        raise exceptions.SzeneSetupError("path does not exist")

    return not next(scandir(dir_path), None)


def delete_directories_if_empty(dir_path):
    """
    Delete empty directory

    Args:
        dir_path(str): Directory path.

    Return:
        False if no child directories exist.
        False if directory is full with files.
        True if successfully.

    """
    paths_to_delete = list()
    dir_path = pixo_normpath(dir_path)

    if not os.path.exists(dir_path):
        raise exceptions.SzeneSetupError("path does not exist")

    if not check_directory_if_empty(dir_path):
        _LOGGER.debug(f"directory [{str(dir_path)}] is full")
        return False

    paths_to_delete.append(dir_path)

    parent_path = os.path.dirname(dir_path)

    paths_to_delete += list(x.path for x in scandir(parent_path) if x.is_dir())

    paths_to_delete = list(set(paths_to_delete))

    if not paths_to_delete:
        return False

    for path_to_delete in paths_to_delete:
        try:
            os.rmdir(path_to_delete)
        except OSError as e:
            _LOGGER.warning(f"Error: {dir_path} : {e.strerror}")

    if check_directory_if_empty(parent_path):
        try:
            os.rmdir(parent_path)
        except OSError as e:
            _LOGGER.warning(f"Error: {dir_path} : {e.strerror}")

    return True


def get_latest_file_in_dir(dir_path, file_type):
    """
    Get latest file of specific type in given directory.

    Args:
        dir_path(str): Directory path
        file_type(str): The file type.

    Returns:
        String: The latest file path.

    """
    p = Path(dir_path)
    files = sorted(list(p.glob("*.{}".format(file_type))))
    return max(files, key=lambda x: x.stat().st_ctime)
