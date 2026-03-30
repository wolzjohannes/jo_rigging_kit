# Author:     Johannes Wolz / Lead Rigging TD

"""
Gui module for the blendshape export maya intecration.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Import built-in modules
from builtins import object
from builtins import str
from importlib import reload

# Import third-party modules
from future import standard_library
# Import Maya specific modules
import pymel.core as pmc

# Import local modules
from pxo_rigging_kit.maya_utils import paths_utils
from pxo_rigging_kit.maya_utils.deformers import blendshape_utils

standard_library.install_aliases()
reload(blendshape_utils)

##########################################################
# CLASSES
##########################################################


class MainWindow(object):
    """
    Main Window for the blendshape export tool.
    """

    def __init__(self):
        self.name = "PXO save blendshape setup"
        self.template = pmc.uiTemplate(self.name, force=True)
        self.template.define(
            pmc.textScrollList,
            width=200,
            height=180,
            ams=True,
        )
        self.template.define(
            pmc.frameLayout,
            labelVisible=False,
            mh=5,
            mw=5,
            bgs=True,
            hlc=(0.5, 0.5, 0.5),
        )
        self.template.define(pmc.columnLayout, rs=10)
        self.template.define(pmc.button, width=100, height=25)
        self.blenshapes_nodes_list = None
        self.numpy_check_box = None
        self.shp_check_box = None
        self.apply_button = None
        self.export_button = None
        self.close_button = None
        self.versioned_check_box = None
        self.path_text_field = None
        self.blendshape_nodes_list = []
        self.win = None
        self.export_path = paths_utils.get_project_paths(pmc.sceneName())
        self.as_shp_file = False
        self.text_scroll_field = None
        self.export_blendshapes_names_list = []
        self.populate_blendshape_nodes_list()

    def show(self):
        """
        Gui constructer method.
        """

        with pmc.window(self.name, s=False) as win:
            self.win = win
            if win.exists(self.name):
                pmc.deleteUI(self.name)
            with self.template:
                with pmc.rowLayout(numberOfColumns=2):
                    with pmc.columnLayout():
                        with pmc.frameLayout():
                            pmc.text("Blendshape nodes list", align="left")
                            self.text_scroll_field = pmc.textScrollList(
                                append=self.blendshape_nodes_list
                            )
                            pmc.text("Select blendshapes you want to export")
                    with pmc.columnLayout():
                        with pmc.columnLayout():
                            with pmc.frameLayout(
                                width=300, height=85, borderVisible=True
                            ):
                                pmc.text("File types")
                                self.numpy_check_box = pmc.checkBox(
                                    label="numpy",
                                    value=True,
                                    cc=pmc.Callback(
                                        self._check_change_command, "numpy"
                                    ),
                                )
                                self.shp_check_box = pmc.checkBox(
                                    label="shp",
                                    value=False,
                                    cc=pmc.Callback(self._check_change_command, "shp"),
                                )
                            pmc.separator(height=10)
                            with pmc.frameLayout(width=300, borderVisible=True):
                                pmc.text("Export directory")
                                self.versioned_check_box = pmc.checkBox(
                                    label="Versioned in project data path.",
                                    cc=pmc.Callback(self.enable_custom_version_path),
                                    value=True,
                                )
                                self.path_text_field = pmc.textFieldButtonGrp(
                                    bl="Path",
                                    enable=False,
                                    bc=pmc.Callback(self.open_file_dialoge),
                                    fileName=self.export_path,
                                )
                            with pmc.rowLayout(numberOfColumns=3):
                                self.apply_button = pmc.button(
                                    label="Apply", c=pmc.Callback(self.apply)
                                )
                                self.export_button = pmc.button(
                                    label="Export", c=pmc.Callback(self.export)
                                )
                                self.close_button = pmc.button(
                                    label="Close",
                                    c=pmc.Callback(self.close_window),
                                )
            win.setTitle(self.name)
        self.get_export_file_type()

    def enable_custom_version_path(self):
        """
        Enable the custom version path as export path.
        Gui will always show the project data path if disabled.
        """
        value = self.versioned_check_box.getValue()
        if value:
            self.export_path = paths_utils.get_project_paths(pmc.sceneName())
            self.path_text_field.setFileName(self.export_path)
            self.path_text_field.setEnable(False)
            return
        self.path_text_field.setFileName("")
        self.path_text_field.setEnable(True)
        self.export_path = ""

    def populate_blendshape_nodes_list(self):
        """
        Populate the blendshapes nodes list
        with all blendshapes nodes from the scene.
        """
        self.blendshape_nodes_list = pmc.ls(typ="blendShape")
        if not self.blendshape_nodes_list:
            self.blendshape_nodes_list = ["None"]

    def open_file_dialoge(self):
        """
        Open the maya file dialoge. For the custom export path.
        """
        start_dir = paths_utils.get_root_path(pmc.sceneName(), "asset")
        export_path = pmc.fileDialog2(bbo=1, spe=True, dir=start_dir, cap="Path", fm=2)
        if export_path:
            self.export_path = str(export_path[0])
            self.path_text_field.setFileName(self.export_path)

    def get_export_file_type(self):
        """
        Get the export file path.
        From the gui checkboxes.
        """
        if self.numpy_check_box.getValue():
            self.as_shp_file = False
        elif self.shp_check_box.getValue():
            self.as_shp_file = True
        else:
            raise ValueError("No file type checkbox enabled.")

    def _check_change_command(self, box_type):
        """
        Switches the file type checkbox vise versa.
        """
        if box_type == "numpy":
            self.shp_check_box.setValue(0)
            self.numpy_check_box.setValue(1)
        elif box_type == "shp":
            self.numpy_check_box.setValue(0)
            self.shp_check_box.setValue(1)
        else:
            raise AttributeError("Given param value not valid.")
        self.get_export_file_type()

    def close_window(self):
        """
        Close the window.
        """
        self.win.delete()

    def apply(self):
        """
        Export command for the apply button.
        """
        self.export_blendshapes_names_list = [
            str(name) for name in self.text_scroll_field.getSelectItem()
        ]
        if self.export_blendshapes_names_list:
            blendshape_utils.save_to_PXO_BSHP_directory(
                self.export_blendshapes_names_list,
                self.export_path,
                self.as_shp_file,
            )
        else:
            raise IndentationError("No blendshapes selected for export.")

    def export(self):
        """
        Export command for the export button.
        """
        self.apply()
        self.close_window()
