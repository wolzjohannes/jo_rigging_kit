# pxo_rigging_kit / pixo animation converter
# www.pixomondo.com
# Date: 10 / 10 / 2023
# Artist: Christof Puehringer / Rigging TD

"""
Remapping the animation from one naming convention to another.
"""

# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import built-in modules
import json
import logging
from os import scandir
import pathlib
import re

# Import third-party modules
# external libraries
from future import standard_library

#######################################################
# GLOBALS
#######################################################
standard_library.install_aliases()

logging.basicConfig(level=logging)
_LOGGER = logging.getLogger(__name__ + ".py")

#######################################################
# CLASSES
#######################################################


class RemapStudioLibrary(object):
    def __init__(self, starting_directory=None):
        self.folders = {}
        self.progress_map = None
        self.start_dir = pathlib.Path(starting_directory) or pathlib.Path(r"")

        self.old_naming_convention = re.compile()
        self.new_naming_convention = re.compile()

        self.file_pattern = ""
        self.file_finder = self.find_files()

    @property
    def starting_filepath(self):
        return self.start_dir

    @starting_filepath.setter
    def starting_filepath(self, dir_name):
        if not dir_name:
            self.start_dir = None
            raise ValueError("No path_given, defaulting to None")

        self.start_dir = dir_name

    def find_project_folders(self):
        """
        Search the folder structures for studio library files
        Returns:

        """
        self.folders = scandir(self.start_dir)
        self.progress_map = zip(self.folders,)

    def find_files(self):
        """
        Search for the file
        Returns:

        """

        pathlib.Path(self.start_dir).glob('*.txt')
        yield

    def check_existing_path(self, custom_path=None):

        path_to_check = pathlib.Path(custom_path) or self.start_dir

        if not path_to_check:
            raise IOError("not in scene")

        return path_to_check

    def walk_through_files(self):
        for file in self.file_finder:
            with open(file, 'a') as progress_file:
                for line in progress_file:
                    if "lol" in line:
                        print("ayo")

    def save_naming_conventions(self):
        pass