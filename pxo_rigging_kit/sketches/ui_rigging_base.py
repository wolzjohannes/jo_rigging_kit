# Import built-in modules
import logging
import os
import sys

# Import third-party modules
try:
    from PySide6 import QtCore
    from PySide6 import QtGui
    from PySide6 import QtWidgets
except ImportError:
    from PySide2 import QtCore
    from PySide2 import QtGui
    from PySide2 import QtWidgets

import maya.OpenMaya as om2
import maya.OpenMayaUI as om2ui
import maya.cmds as cmds
try:
    from shiboken2 import wrapInstance
except ModuleNotFoundError:
    from shiboken6 import wrapInstance

# Import local modules
from pxo_rigging_kit.maya_utils import decorators

try:
    # Import built-in modules
    import importlib as imp
except ModuleNotFoundError:
    # Import built-in modules
    import imp

_LOGGER = logging.getLogger("lol")
_LOGGER.setLevel(logging.INFO)


def maya_main_window():
    """
    Return the Maya main window widget as a Python object
    """
    main_window_ptr = om2ui.MQtUtil.mainWindow()
    if sys.version_info.major >= 3:
        return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)
    else:
        return wrapInstance(long(main_window_ptr), QtWidgets.QWidget)


class PxoRiggingKitUiBase(QtWidgets.QDialog):

    def __init__(self, parent=maya_main_window(), module_name="pxo_rigging_kit"):
        super(PxoRiggingKitUiBase, self).__init__(parent)
        self._MODEL_NAME = module_name
        self._MODULE_NAME = "ui_{0}".format(self._MODEL_NAME)

        self._window_object_name = "{0}_window".format(self._MODULE_NAME)
        self._window_display_name = self._MODULE_NAME.replace("_", " ").title()

        self.update_model()
        self.set_standardized_layout()

    def set_standardized_layout(self):
        self.setWindowTitle(self._window_display_name)
        self.setMinimumSize(300, 80)
        self.setWindowFlags(self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint)

    def update_model(self):
        [imp.reload(mod)
         for mod in sys.modules.copy()
         if mod.startswith(self._MODEL_NAME)
         ]

    def __str__(self):
        return self._MODULE_NAME

    @property
    def window_object_name(self):
        return self._window_object_name

    @window_object_name.setter
    def window_object_name(self, value):
        self._window_object_name = value

    @property
    def window_display_name(self):
        return self._window_display_name

    @window_display_name.setter
    def window_display_name(self, value):
        self._window_display_name = value.replace("_", " ").title()


if __name__ == "__main__":
    # Define Maya Main Window
    maya_wdw = maya_main_window()
    base_window_test = PxoRiggingKitUiBase(module_name="decorators")
    _LOGGER.info(base_window_test.window_object_name)

    # Check if the recycle window is a child of the Maya Main Window
    instanced_main_window = maya_wdw.findChild(QtWidgets.QDialog, base_window_test.window_object_name)

    # Check if window exists
    if instanced_main_window:
        try:
            instanced_main_window.close()
            instanced_main_window.deleteLater()

            _LOGGER.info("ney")

        except:
            pass

        _LOGGER.info("yaaay2")
        base_window_test.setObjectName(base_window_test.window_object_name)
        base_window_test.show()
        _LOGGER.info("yaaay3")

    else:
        # Window does not exist | Create a new one!
        base_window_test.setObjectName(base_window_test.window_object_name)
        base_window_test.set_standardized_layout()
        base_window_test.show()
_LOGGER.info(base_window_test.window_object_name)
