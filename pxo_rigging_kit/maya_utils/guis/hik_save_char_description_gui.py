# Author:     Johannes Wolz / Lead Rigging TD

"""
Gui module for the hik description saving.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Import built-in modules
from builtins import object
from builtins import str
import os

# Import third-party modules
from future import standard_library
import pixo_paths
import pymel.core as pmc

# Import local modules
from pxo_rigging_kit.constants import HIK_SOURCE_RIG_CHAR_DESCRIPTION_NAME
from pxo_rigging_kit.constants import HIK_TARGET_RIG_CHAR_DESCRIPTION_NAME
from pxo_rigging_kit.maya_utils import exceptions
from pxo_rigging_kit.maya_utils import paths_utils
from pxo_rigging_kit.maya_utils.rigging import mocap_utils

standard_library.install_aliases()


class MainWindow(object):
    """
    Main Window for the save hik data description tool.
    """

    def __init__(self):
        self.name = "PXO save char descriptions"
        self.template = pmc.uiTemplate(self.name, force=True)
        self.template.define(
            pmc.frameLayout, mh=5, mw=5, labelVisible=True, bv=True, width=300
        )
        self.template.define(pmc.button, width=98, height=35)
        self.template.define(pmc.separator, height=10)
        self.scene_check_box = None
        self.project_check_box = None
        self.target_xml_name_field = None
        self.source_xml_name_field = None
        self.target_char_name_field = None
        self.source_char_name_field = None
        self.apply_button = None
        self.export_button = None
        self.close_button = None
        self.win = None
        self.target_get_button = None
        self.target_set_name_box = None
        self.target_set_xml_box = None
        self.source_set_name_box = None
        self.source_set_xml_box = None
        self.source_get_button = None

    def show(self):
        """
        Gui constructer method.
        """
        with pmc.window(self.name, s=False) as win:
            self.win = win
            if win.exists(self.name):
                pmc.deleteUI(self.name)
            with self.template:
                with pmc.columnLayout():
                    with pmc.frameLayout(label="Directory Level"):
                        with pmc.rowLayout(numberOfColumns=2):
                            self.scene_check_box = pmc.checkBox(
                                label="Scene",
                                enable=False,
                            )
                            self.project_check_box = pmc.checkBox(
                                label="Project",
                                enable=True,
                                value=True,
                            )
                    pmc.separator()
                    with pmc.frameLayout(label="Character"):
                        with pmc.columnLayout():
                            with pmc.rowLayout(numberOfColumns=2):
                                self.target_set_name_box = pmc.checkBox(
                                    label="Set by Character Name", value=True
                                )
                                self.target_set_xml_box = pmc.checkBox(
                                    label="Set by xml template file.",
                                    enable=False,
                                )
                            pmc.separator()
                            self.target_char_name_field = pmc.textField(width=285)
                            pmc.separator()
                            with pmc.rowLayout(numberOfColumns=2):
                                self.target_xml_name_field = pmc.textField(
                                    width=260, enable=False
                                )
                                self.target_get_button = pmc.button(
                                    label="Get",
                                    width=25,
                                    height=19,
                                    enable=False,
                                )
                    pmc.separator()
                    with pmc.frameLayout(label="Source"):
                        with pmc.columnLayout():
                            with pmc.rowLayout(numberOfColumns=2):
                                self.source_set_name_box = pmc.checkBox(
                                    label="Set by Source Name", value=True
                                )
                                self.source_set_xml_box = pmc.checkBox(
                                    label="Set by xml template file.",
                                    enable=False,
                                )
                            pmc.separator()
                            self.source_char_name_field = pmc.textField(width=285)
                            pmc.separator()
                            with pmc.rowLayout(numberOfColumns=2):
                                self.source_xml_name_field = pmc.textField(
                                    width=260, enable=False
                                )
                                self.source_get_button = pmc.button(
                                    label="Get",
                                    width=25,
                                    height=19,
                                    enable=False,
                                )
                    pmc.separator()
                    with pmc.rowLayout(numberOfColumns=3):
                        self.apply_button = pmc.button(
                            label="Apply", c=pmc.Callback(self.save)
                        )
                        self.export_button = pmc.button(
                            label="Save", c=pmc.Callback(self.export)
                        )
                        self.close_button = pmc.button(
                            label="Close", c=pmc.Callback(self.close)
                        )
            win.setTitle(self.name)
            self.scene_check_box.setChangeCommand(
                pmc.Callback(
                    self.check_box_change,
                    self.scene_check_box,
                    self.project_check_box,
                )
            )
            self.project_check_box.setChangeCommand(
                pmc.Callback(
                    self.check_box_change,
                    self.project_check_box,
                    self.scene_check_box,
                )
            )
            self.source_set_name_box.setChangeCommand(
                pmc.Callback(
                    self.set_check_box_change,
                    self.source_set_name_box,
                    self.source_set_xml_box,
                    self.source_char_name_field,
                    self.source_xml_name_field,
                    self.source_get_button,
                )
            )
            self.source_set_xml_box.setChangeCommand(
                pmc.Callback(
                    self.set_check_box_change,
                    self.source_set_xml_box,
                    self.source_set_name_box,
                    self.source_xml_name_field,
                    self.source_char_name_field,
                    self.source_get_button,
                )
            )
            self.target_set_name_box.setChangeCommand(
                pmc.Callback(
                    self.set_check_box_change,
                    self.target_set_name_box,
                    self.target_set_xml_box,
                    self.target_char_name_field,
                    self.target_xml_name_field,
                    self.target_get_button,
                )
            )
            self.target_set_xml_box.setChangeCommand(
                pmc.Callback(
                    self.set_check_box_change,
                    self.target_set_xml_box,
                    self.target_set_name_box,
                    self.target_xml_name_field,
                    self.target_char_name_field,
                    self.target_get_button,
                )
            )
            self.source_get_button.setCommand(
                pmc.Callback(self.get_path, self.source_xml_name_field)
            )
            self.target_get_button.setCommand(
                pmc.Callback(self.get_path, self.target_xml_name_field)
            )

    def lock_character_field(self):
        self.target_char_name_field.setEditable(False)

    def lock_source_field(self):
        self.source_char_name_field.setEditable(False)

    def save(self):
        if self.scene_check_box.getValue():
            try:
                export_path = paths_utils.get_project_paths(
                    pmc.sceneName(), "asset_task"
                )
            except:
                export_path = paths_utils.get_project_paths(
                    pmc.sceneName(), "shot_task"
                )
        if self.project_check_box.getValue():
            export_path = paths_utils.get_root_path(pmc.sceneName(), "project")
        target_char_name = self.target_char_name_field.getText()
        source_char_name = self.source_char_name_field.getText()
        target_char_xml = self.target_xml_name_field.getText()
        source_char_xml = self.source_xml_name_field.getText()
        character = False
        source = False
        if target_char_name or target_char_xml:
            character = True
        if source_char_name or source_char_xml:
            source = True
        target_char_export_path = pixo_paths.normalize(
            os.path.join(
                export_path,
                "{}.json".format(HIK_TARGET_RIG_CHAR_DESCRIPTION_NAME),
            )
        )
        source_char_export_path = pixo_paths.normalize(
            os.path.join(
                export_path,
                "{}.json".format(HIK_SOURCE_RIG_CHAR_DESCRIPTION_NAME),
            )
        )
        if character and source:
            mocap_utils.hik_save_char_description_as_json(
                target_char_export_path, target_char_name, target_char_xml
            )
            mocap_utils.hik_save_char_description_as_json(
                source_char_export_path, source_char_name, source_char_xml
            )
        else:
            raise exceptions.HikCharacterDefinitionError(
                "You have to set"
                " character"
                " and source"
                " for a valid save."
                " Just a save as"
                " bundle is allowed"
            )

    def check_box_change(self, source_box, target_box):
        source_box.setEnable(False)
        target_box.setEnable(True)
        target_box.setValue(True)

    def set_check_box_change(
        self, source_box, target_box, source_field, target_field, get_button
    ):
        source_field.setText("")
        source_field.setEnable(False)
        target_field.setEnable(True)
        if get_button.getEnable():
            get_button.setEnable(False)
        else:
            get_button.setEnable(True)
        self.check_box_change(source_box, target_box)

    def export(self):
        self.save()
        self.win.delete()

    def close(self):
        self.win.delete()

    def get_path(self, target_text_field):
        source_path = paths_utils.get_root_path(pmc.sceneName(), "project")
        result = pmc.fileDialog2(
            cap="Get HIK description xml template file.",
            fm=1,
            ds=2,
            dir=source_path,
            okc="Get",
        )
        if result:
            result = pixo_paths.normalize(str(result[0]))
            target_text_field.setText(result)
