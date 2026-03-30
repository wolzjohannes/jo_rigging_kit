# Author:     Johannes Wolz / Lead Rigging TD

"""
Gui module for the hik FK/IK match and Tpose data saving.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Import built-in modules
from builtins import object
from builtins import zip
import os

# Import third-party modules
from future import standard_library
import pixo_paths
import pymel.core as pmc

# Import local modules
from pxo_rigging_kit.constants import HIK_IK_FK_MATCH_JSON_NAME
from pxo_rigging_kit.maya_utils import paths_utils
from pxo_rigging_kit.maya_utils.rigging import mocap_utils

standard_library.install_aliases()


class MainWindow(object):
    """
    Main Window for the save hik data description tool.
    """

    def __init__(self):
        self.name = "PXO save Tpose & FK/IK match data"
        self.template = pmc.uiTemplate(self.name, force=True)
        self.template.define(
            pmc.frameLayout, mh=5, mw=5, labelVisible=True, bv=True, width=300
        )
        self.template.define(pmc.textField, width=210)
        self.template.define(pmc.button, width=60, height=18)
        self.template.define(pmc.separator, height=10)
        self.scene_check_box = None
        self.project_check_box = None
        self.apply_button = None
        self.export_button = None
        self.close_button = None
        self.win = None
        self.l_side_char = None
        self.r_side_char = None
        self.arm_token = None
        self.leg_token = None
        self.text_field_blend_attr = None
        self.text_field_blend_attr_box = None
        self.text_field_fk_ctrls_0 = None
        self.text_field_fk_ctrls_1 = None
        self.text_field_fk_ctrls_2 = None
        self.text_field_ik_ctrl = None
        self.text_field_ik_upvec_ctrl = None
        self.text_field_fk_ctrls_button_0 = None
        self.text_field_fk_ctrls_button_1 = None
        self.text_field_fk_ctrls_button_2 = None
        self.text_field_ik_ctrl_button = None
        self.text_field_ik_upvec_ctrl_button = None

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
                    with pmc.frameLayout(label="Statics"):
                        with pmc.columnLayout():
                            with pmc.rowLayout(numberOfColumns=2, cw2=(100, 200)):
                                pmc.text("L Side Char")
                                self.l_side_char = pmc.textField(width=100)
                            with pmc.rowLayout(numberOfColumns=2, cw2=(100, 200)):
                                pmc.text("R Side Char")
                                self.r_side_char = pmc.textField(width=100)
                            with pmc.rowLayout(numberOfColumns=2, cw2=(100, 200)):
                                pmc.text("Arm limb token")
                                self.arm_token = pmc.textField(width=100)
                            with pmc.rowLayout(numberOfColumns=2, cw2=(100, 200)):
                                pmc.text("Leg limb token")
                                self.leg_token = pmc.textField(width=100)
                    pmc.separator()
                    with pmc.frameLayout(label="Blend_attribute"):
                        with pmc.columnLayout():
                            with pmc.rowLayout(numberOfColumns=2):
                                self.text_field_blend_attr = pmc.textField()
                                self.text_field_blend_attr_box = pmc.button(label="Get")
                    pmc.separator()
                    with pmc.frameLayout(label="Left_arm_controls"):
                        with pmc.columnLayout():
                            with pmc.frameLayout(label="Fk_control_0", bv=False):
                                with pmc.rowLayout(numberOfColumns=2):
                                    self.text_field_fk_ctrls_0 = pmc.textField()
                                    self.text_field_fk_ctrls_button_0 = pmc.button(
                                        label="Get"
                                    )
                            with pmc.frameLayout(label="Fk_control_1", bv=False):
                                with pmc.rowLayout(numberOfColumns=2):
                                    self.text_field_fk_ctrls_1 = pmc.textField()
                                    self.text_field_fk_ctrls_button_1 = pmc.button(
                                        label="Get"
                                    )
                            with pmc.frameLayout(label="Fk_control_2", bv=False):
                                with pmc.rowLayout(numberOfColumns=2):
                                    self.text_field_fk_ctrls_2 = pmc.textField()
                                    self.text_field_fk_ctrls_button_2 = pmc.button(
                                        label="Get"
                                    )
                            with pmc.frameLayout(label="Ik_control", bv=False):
                                with pmc.rowLayout(numberOfColumns=2):
                                    self.text_field_ik_ctrl = pmc.textField()
                                    self.text_field_ik_ctrl_button = pmc.button(
                                        label="Get"
                                    )
                            with pmc.frameLayout(label="Ik_upvec_control", bv=False):
                                with pmc.rowLayout(numberOfColumns=2):
                                    self.text_field_ik_upvec_ctrl = pmc.textField()
                                    self.text_field_ik_upvec_ctrl_button = pmc.button(
                                        label="Get"
                                    )
                    pmc.separator()
                    with pmc.rowLayout(numberOfColumns=3):
                        self.apply_button = pmc.button(
                            label="Apply",
                            width=98,
                            height=35,
                            c=pmc.Callback(self.save),
                        )
                        self.export_button = pmc.button(
                            label="Save",
                            width=98,
                            height=35,
                            c=pmc.Callback(self.export),
                        )
                        self.close_button = pmc.button(
                            label="Close",
                            width=98,
                            height=35,
                            c=pmc.Callback(self.close),
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
            self.text_field_blend_attr_box.setCommand(pmc.Callback(self.set_blend_attr))
            self.l_side_char.setText("L")
            self.r_side_char.setText("R")
            self.arm_token.setText("arm")
            self.leg_token.setText("leg")
            for textfield_, button_ in zip(
                [
                    self.text_field_fk_ctrls_0,
                    self.text_field_fk_ctrls_1,
                    self.text_field_fk_ctrls_2,
                    self.text_field_ik_ctrl,
                    self.text_field_ik_upvec_ctrl,
                ],
                [
                    self.text_field_fk_ctrls_button_0,
                    self.text_field_fk_ctrls_button_1,
                    self.text_field_fk_ctrls_button_2,
                    self.text_field_ik_ctrl_button,
                    self.text_field_ik_upvec_ctrl_button,
                ],
            ):
                button_.setCommand(pmc.Callback(self.set_control, textfield_))

    def check_box_change(self, source_box, target_box):
        source_box.setEnable(False)
        target_box.setEnable(True)
        target_box.setValue(True)

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
        l_side_char = self.l_side_char.getText()
        r_side_char = self.r_side_char.getText()
        arm_token = self.arm_token.getText()
        leg_token = self.leg_token.getText()
        text_field_blend_attr = self.text_field_blend_attr.getText()
        text_field_fk_ctrls_0 = self.text_field_fk_ctrls_0.getText()
        text_field_fk_ctrls_1 = self.text_field_fk_ctrls_1.getText()
        text_field_fk_ctrls_2 = self.text_field_fk_ctrls_2.getText()
        text_field_ik_ctrl = self.text_field_ik_ctrl.getText()
        text_field_ik_upvec_ctrl = self.text_field_ik_upvec_ctrl.getText()
        if not all(
            [
                l_side_char,
                r_side_char,
                arm_token,
                leg_token,
                text_field_blend_attr,
                text_field_fk_ctrls_0,
                text_field_fk_ctrls_1,
                text_field_fk_ctrls_2,
                text_field_ik_ctrl,
                text_field_ik_upvec_ctrl,
            ]
        ):
            raise ValueError("Not every textfield has an entry")
        host_ctrl, blend_attr = text_field_blend_attr.split(".")
        file_path = pixo_paths.normalize(
            os.path.join(export_path, "{}.json".format(HIK_IK_FK_MATCH_JSON_NAME))
        )
        fk_ik_match_data_dict = {
            "fk_ik_blend_attr": blend_attr.replace(arm_token, "LIMB"),
            "host_ctrl": host_ctrl.replace(arm_token, "LIMB").replace(
                "_{}_".format(l_side_char), "_*_"
            ),
            "limb_dict": {"arm": arm_token, "leg": leg_token},
            "left_limb_side_char": l_side_char,
            "right_limb_side_char": r_side_char,
            "fk_list": [
                text_field_fk_ctrls_0.replace(arm_token, "LIMB").replace(
                    "_{}_".format(l_side_char), "_*_"
                ),
                text_field_fk_ctrls_1.replace(arm_token, "LIMB").replace(
                    "_{}_".format(l_side_char), "_*_"
                ),
                text_field_fk_ctrls_2.replace(arm_token, "LIMB").replace(
                    "_{}_".format(l_side_char), "_*_"
                ),
            ],
            "ik_ctrl": text_field_ik_ctrl.replace(arm_token, "LIMB").replace(
                "_{}_".format(l_side_char), "_*_"
            ),
            "upv_ctrl": text_field_ik_upvec_ctrl.replace(arm_token, "LIMB").replace(
                "_{}_".format(l_side_char), "_*_"
            ),
        }
        mocap_utils.hik_save_fk_ik_match_data_as_json(file_path, fk_ik_match_data_dict)

    def set_blend_attr(self):
        host_ctrl = pmc.ls(sl=True)
        selected_attr = pmc.channelBox(
            "mainChannelBox", q=True, sma=True, soa=True, sha=True
        )
        if not all([host_ctrl, selected_attr]):
            raise AttributeError("No blend attribute selected.")
        self.text_field_blend_attr.setText(
            ".".join(
                [
                    host_ctrl[0].name(long=None, stripNamespace=True),
                    selected_attr[0],
                ]
            )
        )

    def set_control(self, textfield_obj):
        selection = pmc.ls(sl=True)
        if not selection:
            raise RuntimeError("No control selected")
        textfield_obj.setText(selection[0].name(long=None, stripNamespace=True))

    def export(self):
        self.save()
        self.win.delete()

    def close(self):
        self.win.delete()
