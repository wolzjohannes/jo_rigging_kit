# Author:     Johannes Wolz / Lead Rigging TD

"""
Helpful decorators module.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Import built-in modules
from builtins import object
from functools import wraps
import logging

try:
    from PySide6 import QtCore
    from PySide6 import QtGui
    from PySide6 import QtWidgets
    from shiboken6 import wrapInstance

except ImportError:

    from PySide2 import QtCore
    from PySide2 import QtGui
    from PySide2 import QtWidgets
    from PySide2.QtWidgets import QWidget
    from shiboken2 import wrapInstance

# Import third-party modules
from future import standard_library
# Import Maya specific modules
import pymel.core as pmc
from maya import OpenMayaUI as omui1

import sys
import maya.cmds as cmds

# Import local modules
from pxo_rigging_kit.paths import get_package_default_settings_path
try:
    from contextlib import contextmanager
except ModuleNotFoundError:
    from contextlib2 import contextmanager


standard_library.install_aliases()

##########################################################
# GLOBAL
##########################################################

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(0)

##########################################################
# CLASSES
##########################################################


class Decorators(object):
    def __init__(self):
        """
        Decorator class. Inherits decorators methods which can be useful in
        other packages.
        """
        self.debug = True
        self.logger = _LOGGER

    def x_timer(self, func):
        """
        Decorator which gives you back the execution time of an function
        in maya_utils. Output can only been seen in debug mode. For that you need
        to set the self.debug class variable to True.

        Args:
            func(python object): The function to track the execution time for.

        Return:
            Func: Returns the wrapped function.

        """
        if self.debug:

            @wraps(func)
            def wrapper(*args, **kwargs):
                start = pmc.timerX()
                result = func(*args, **kwargs)
                total_time = pmc.timerX(st=start)

                self.logger.info(
                    f"Func/Method: {func.__name__}(). Executed in: [{total_time}]"
                )

                return result

            return wrapper
        return func

    def undo(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with pmc.UndoChunk():
                result = func(*args, **kwargs)
            return result

        return wrapper

    def edit_locked_obj(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            args[0].unlock()
            result = func(*args, **kwargs)
            args[0].lock()
            return result

        return wrapper

    def requires_plugins(self, plugin_list):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                for plugin_name in plugin_list:
                    pmc.loadPlugin(plugin_name)
                    result = func(*args, **kwargs)
                    return result
            return wrapper
        return decorator

    def get_default_settings_wrp(self, func):
        @wraps(func)
        def wrap(*args, **kwargs):
            location_folder = get_package_default_settings_path()
            return func(location_folder, **kwargs)

        return wrap

    @contextmanager
    def refresh_suspended(self):
        """Suspend and resume Maya's handling of refresh events.

        Yields:
            None

        """

        self.logger.debug("Viewport refreshing suspended.")
        pmc.refresh(suspend=True)

        try:
            yield
        finally:

            self.logger.debug("Viewport refreshing resumed.")
            pmc.refresh(suspend=False)

    @contextmanager
    def dg_evaluation(self):
        self.logger.info("Switched to DG evaluation.")
        evaluation_mode = pmc.evaluationManager(mode=True, query=True)

        if not evaluation_mode:
            raise RuntimeError("There was no evaluation mode found")

        pmc.evaluationManager(mode="off")

        try:
            yield

        finally:
            self.logger.info(f"Switched to originally used [{evaluation_mode[0]}] evaluation.")
            pmc.evaluationManager(mode=evaluation_mode[0])

    @contextmanager
    def parallel_evaluation(self):
        self.logger.info("Switched to Parallel evaluation.")
        evaluation_mode = pmc.evaluationManager(mode=True, query=True)

        if not evaluation_mode:
            raise RuntimeError("There was no evaluation mode found")

        pmc.evaluationManager(mode="parallel")

        try:
            yield

        finally:
            self.logger.info(f"Switched to originally used [{evaluation_mode[0]}] evaluation.")
            pmc.evaluationManager(mode=evaluation_mode[0])

    @contextmanager
    def disable_node_editor_update(self):
        """
        Wrapper designed to work as a mechanism to be able to have the Node Editor open.
        while building big Networks by Script.

        """
        self.logger.debug(f"STARTED: Starting the node editor updating change.")

        # use maya cmds to get the node editor panel

        all_scripted_panels = cmds.getPanel(allScriptedTypes=True)
        if "nodeEditorPanel" not in all_scripted_panels:
            raise RuntimeError()

        current_node_editors = cmds.getPanel(scriptType="nodeEditorPanel")
        if current_node_editors is None:
            raise RuntimeError("could not find the node editor")

        # get the full name of the standard node editor
        current_node_editor_names = tuple(f"{current_node_editor}NodeEditorEd" for current_node_editor in current_node_editors)

        # check if its enabled used to reset after
        previous_states = tuple(cmds.nodeEditor(editor_name, q=True, addNewNodes=True)
                                for editor_name
                                in current_node_editor_names
                                )
        # setting states
        _ = tuple(cmds.nodeEditor(editor_name, e=True, addNewNodes=False)
        for editor_name
            in current_node_editor_names
        )

        self.logger.debug(f"prep done: Turned the Node Editor Updating on creation to False.")

        try:
            yield

        finally:
            _ = tuple(cmds.nodeEditor(editor_name, e=True, addNewNodes=previous_status)
                      for (editor_name, previous_status)
                      in zip(current_node_editor_names, previous_states)
                      )
            logging_info = [f"FINISHED: Reverted the Node Editor: {editor_name} back to {previous_status}."
                            for (editor_name, previous_status)
                            in zip(current_node_editor_names, previous_states)
            ]
            self.logger.debug("\n".join(logging_info))


    @contextmanager
    def disable_isolate_select_update(self):
        all_scripted_panels = cmds.getPanel(all=True)

        named_panels = set(panel_name for panel_name in all_scripted_panels if "modelPanel" in panel_name)
        if not named_panels:
            raise RuntimeError("did not find model panel")

        model_panels = cmds.getPanel(type="modelPanel")
        if model_panels is None:
            raise RuntimeError("could not find the node editor")

        previous_states = tuple(cmds.isolateSelect(editor_name, state=True, query=True)
                                for editor_name
                                in model_panels
                                )

        self.logger.debug("Turned off isolate select.")
        # setting states
        _ = tuple(cmds.isolateSelect(editor_name, state=False,)
                  for editor_name
                  in model_panels
                  )

        try:
            yield

        finally:
            _ = tuple(cmds.isolateSelect(editor_name, state=previous_status,)
                      for (editor_name, previous_status)
                      in zip(model_panels, previous_states)
                      )
            logging_info = [f"FINISHED: Reverted the Node Editor: {editor_name} back to {previous_status}."
                            for (editor_name, previous_status)
                            in zip(model_panels, previous_states)
                            ]
            self.logger.debug("\n".join(logging_info))



    def log_run_end(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            self.logger.info(f'Run\t{func.__name__}', extra={'ui':'interesting'})
            result = func(*args, **kwargs)
            self.logger.info(f'End\t{func.__name__}')

        return wrapper
