# Author:     Christof Puehringer / Rigging TD

"""
module for giving a baseline version control system that orients itself on creationtime rather than strings

"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Import built-in modules
# from builtins import open
from datetime import datetime
import json
# Import python standard import
import logging
import os

try:
    # Import built-in modules
    from os import scandir
except ImportError:
    from scandir import scandir

# Import third-party modules
from future import standard_library
from pixo_paths.paths import normalize as pixo_normpath

# Import local modules
from pxo_rigging_kit import paths
from pxo_rigging_kit.maya_utils import decorators

standard_library.install_aliases()

##########################################################
# GLOBALS
##########################################################


_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)
DECORATORS = decorators.Decorators()
DECORATORS.debug = True
DECORATORS.logger = _LOGGER

##########################################################
# FUNCTIONS
##########################################################


def get_time(separator="_"):
    """
    Gives back the local machine time.

    Args:
        separator(str): The separator string.

    Returns:
        str: (hour_minute_second)
    """
    now = datetime.now()
    return now.strftime("{}".format(separator).join(["%H", "%M", "%S"]))


def get_date(separator="_"):
    """
    Gives back the local machine date.

    Args:
        separator(str): The separator string.

    Returns:
        str: (year_month_day)
    """
    now = datetime.now()
    return now.strftime("{}".format(separator).join(["%Y", "%m", "%d"]))


def check_and_create_date(path_object):
    """
    Creates a version control system structure which creates a new folder for each day, and for each export time.
    This helps because the files are not lying in a directory where editing them would change the outcome.
    The date and time is more important than the version number because basically we care about the date:
    e.g. 'hey, the skinning we had in shot xyz on day abc was good' --> the version is non important
    And the computer cares about the creation time that does not change by changing files underneath
    As security measure the date is also good if we have the issue of copying over the files.

    Args:
        path_object(path): The path for which version control should be created.

    Returns:
        Path: version control created path
    """
    date_path = os.path.join(path_object, get_date())
    date_path = paths.check_and_create_path(date_path)

    time_path = os.path.join(date_path, get_time())
    time_path = paths.check_and_create_path(time_path)
    return pixo_normpath(time_path)


#   look for latest file in file structure
def get_latest_path(path_object):
    """
    Finds the latest file by creation date and gives back the path

    Args:
        path_object(path): Returns the latest directory for the filepath.

    Returns:
        path: version control created path
    """

    object_paths = list(
        pixo_normpath(x.path) for x in scandir(path_object) if x.is_dir()
    )
    if not object_paths:
        return False

    #    there needs to be added an option to recursively search for the newest item :)
    object_paths.sort(key=os.path.getctime, reverse=True)

    newest_date = max(object_paths, key=os.path.getctime)

    object_paths = list(
        pixo_normpath(x.path) for x in scandir(newest_date) if x.is_dir()
    )
    if not object_paths:
        return False

    newest_path = max(object_paths, key=os.path.getctime)
    return pixo_normpath(newest_path)


def get_latest_file_in_path(
    path_object, file_name, calc_depth=-1, lookup_dict_name="data_lookup.json"
):
    """
    this function scans for the latest file in the path, it is built for [],
    but can be adapted for all version control purposes.
    it only steps two times though, could be made recursive, but recursion makes it slower.


    Args:
        path_object(path): The path to the file.
        file_name(str): The name of the file.
        calc_depth(int): The depth to which the search will go.
        lookup_dict_name(str): The name of the file to be searched for.

    Returns:
        Path: the path to the directory of the file, found.
    """

    # look for all paths that are in the directory
    date_paths = list(x.path for x in scandir(path_object) if x.is_dir())

    # check if there are even paths in the search directory
    if not date_paths:
        return False

    # sort the paths by the creation time
    date_paths.sort(key=os.path.getctime, reverse=True)

    # step through the paths
    for date_iter_, date_path in enumerate(date_paths):

        # break if [calc_depth] value is exceeded
        if date_iter_ == calc_depth:
            return False

        # look for all paths that are in the directory
        time_paths = list(x.path for x in scandir(date_path) if x.is_dir())

        # check if there are even paths in the search directory
        if not time_paths:
            continue

        # sort the paths by the creation time
        time_paths.sort(key=os.path.getctime, reverse=True)

        # step through the paths
        for time_iter_, time_path in enumerate(time_paths):
            # break if [calc_depth] value is exceeded
            if time_iter_ == calc_depth:
                return False

            # compose the suggested newest path to the [lookup_dict.json] file
            newest_data_dict = os.path.normpath(
                os.path.join(time_path, lookup_dict_name)
            )

            # check if filepath exists
            if not os.path.exists(newest_data_dict):
                continue

            # open filepath
            with open(newest_data_dict, "r") as data_lookup_file:
                # check if filename in json dict keys
                if file_name in list(json.load(data_lookup_file).keys()):
                    return time_path

    return False
