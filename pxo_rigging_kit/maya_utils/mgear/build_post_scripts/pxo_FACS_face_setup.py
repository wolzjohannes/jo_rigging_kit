"""
Custom step for FACS face rig tweaking.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import third-party modules
from future import standard_library
import maya.cmds as cmds
import mgear.shifter.custom_step as cstp
import pymel.core as pmc

# Import built-in modules
import logging

# Import local modules
from pxo_rigging_kit.maya_utils import attributes_utils
from pxo_rigging_kit.maya_utils.mgear import mgear_build_utils
from pxo_rigging_kit.maya_utils.rigging import rig_utils
from pxo_rigging_kit.maya_utils.rigging import mesh_islands


standard_library.install_aliases()

##########################################################
# GLOBALS
##########################################################

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)

##########################################################
# FUNCTIONS
##########################################################


class CustomShifterStep(cstp.customShifterMainStep):

    COMPONENT = "face_ui"
    FACE_TWEAKERS_COMPONENT = "faceTweaker_"
    UPPER_LIP_COMPONENT = "upperLip_"
    LOWER_LIP_COMPONENT = "lowerLip_"
    V_MOUTH_SHAPES = "v_mouth_shapes"
    SETUP_GRP = "setup"

    def __init__(self):
        self.name = "pxo_FACS_face_setup"
        self.acting_step_dict = None
        self.mouth_settings = {
            "mouth_siderot": 5,
            "mouth_vertrot": 5,
            "mouth_fronttrans": 0,
            "mouth_verttrans": 0,
            "mouth_floowlips": 0,
            "mouth_lipsAlignSpeed": 0.3,
        }
        self.mouth_host_name = "face_ui_C_0_ctrl"
        self.mgear_mouth_jaw_ctrl = "mouth_C_0_jaw_ctrl"
        self.face_bs = "face_bs"
        self.eye_lock_ctrl = "eye_SIDE_0_ik_ctrl"
        self.eye_fk_ctrl = "eye_SIDE_0_fk_ctrl"
        self.face_cam_name = "face_FACS_UI"
        self.global_ctrl = "global_0_ctrl"
        self.tweaker_buffer_grps = "*Tweaker_*_ctrl_buffer_grp"

    def run(self, stepDict):
        self.acting_step_dict = stepDict["mgearRun"]
        face_ui_components = mgear_build_utils.get_nonhost_components(
            self.acting_step_dict,
            self.COMPONENT,
        )
        face_ui_ctrl = [
            mgear_build_utils.get_component_ctrls(
                self.acting_step_dict, face_ui_comp
            )
            for face_ui_comp in face_ui_components
        ][0][0]

        face_tweaker_components = mgear_build_utils.get_nonhost_components(
            self.acting_step_dict,
            self.FACE_TWEAKERS_COMPONENT,
        )

        face_tweaker_ctrl = [
            mgear_build_utils.get_component_ctrls(
                self.acting_step_dict, face_tweaker_comp
            )
            for face_tweaker_comp in face_tweaker_components
        ][0][0]

        upper_lip_components = mgear_build_utils.get_nonhost_components(
            self.acting_step_dict,
            self.UPPER_LIP_COMPONENT,
        )

        upper_lip_ctrl = [
            mgear_build_utils.get_component_ctrls(
                self.acting_step_dict, u_lip_comp
            )
            for u_lip_comp in upper_lip_components
        ][0][0]

        lower_lip_components = mgear_build_utils.get_nonhost_components(
            self.acting_step_dict,
            self.LOWER_LIP_COMPONENT,
        )

        lower_lip_ctrl = [
            mgear_build_utils.get_component_ctrls(
                self.acting_step_dict, v_lip_comp
            )
            for v_lip_comp in lower_lip_components
        ][0][0]

        v_mouth_shapes_components = mgear_build_utils.get_nonhost_components(
            self.acting_step_dict,
            self.V_MOUTH_SHAPES,
        )
        v_mouth_shapes_ctrl = [
            mgear_build_utils.get_component_ctrls(
                self.acting_step_dict, v_shape_comp
            )
            for v_shape_comp in v_mouth_shapes_components
        ][0][0]
        self._add_blendshape_channels(
            upper_lip_ctrl, lower_lip_ctrl, v_mouth_shapes_ctrl
        )
        self._create_face_rig_mesh_islands(face_ui_ctrl, face_tweaker_ctrl)
        self._fix_face_tweakers_scale_issue(face_ui_ctrl)
        # self._tweak_face_ui_shape(face_ui_ctrl)
        self._add_face_ui_camera(face_ui_ctrl)
        self._apply_mouth_settings()
        self._connect_mouth_ui_ctrl_with_mgear_jaw()
        self._hide_control_shapes()

    def _tweak_face_ui_shape(self, control):
        """
        Will set the shape node of given control to display type reference.

        Args:
            control(pmc.PyNode): The face ui main control

        """
        face_ui_ctrl_shape = control.getShape()
        face_ui_ctrl_shape.overrideEnabled.set(1)
        face_ui_ctrl_shape.overrideDisplayType.set(2)

    def _add_face_ui_camera(self, control):
        """
        Add camera to the face ui as GUI for the animators.

        Args:
            control(pmc.PyNode): The main face ui rig control

        """
        camera_shape = pmc.createNode("camera")
        camera = camera_shape.getTransform()
        camera.rename(self.face_cam_name)

        pmc.parent(camera, control)
        pmc.matchTransform(camera, control)
        camera.translateY.set(0.5)
        camera.translateZ.set(40)
        attributes_utils.lock_and_hide_attributes(camera)
        camera.visibility.set(0)

        camera_shape.horizontalFilmAperture.set(1.29)
        camera_shape.focalLength.set(30.000)
        camera_shape.verticalFilmOffset.set(-0.05)

    def _apply_mouth_settings(self):
        """
        Will apply the default values to the mouth control.
        """

        for key, value in self.mouth_settings.items():
            cmds.setAttr(f"{self.mouth_host_name}.{key}", value)

    def _connect_mouth_ui_ctrl_with_mgear_jaw(self):
        """
        Will connect the mouth face ui control with the jaw control of the rig.
        """
        rig_utils.set_driven_key(
            {
                f"{self.mouth_host_name}.translateY": [1,0, -1],
                f"{self.mgear_mouth_jaw_ctrl}.translateY": [3,0, -5]
            }
        )
        rig_utils.set_driven_key(
            {
                f"{self.mouth_host_name}.translateX": [1,0, -1],
                f"{self.mgear_mouth_jaw_ctrl}.translateX": [-3,0, 3]
            }
        )
        if pmc.objExists(self.face_bs):
            rig_utils.set_driven_key(
                {
                    f"{self.mouth_host_name}.translateY": [0, 0.07],
                    f"{self.face_bs}.close_mouth": [0, 1]
                }
            )
        for side in ["_L_", "_R_"]:
            mult_value = 1.0
            if side == "_R_":
                mult_value = -1.0
            rig_utils.set_driven_key(
                {
                    f"{self.eye_lock_ctrl.replace('_SIDE_', side)}.translateY": [0, -1.0],
                    f"{self.eye_fk_ctrl.replace('_SIDE_', side)}.rotateX": [0, -16]
                }
            )
            rig_utils.set_driven_key(
                {
                    f"{self.eye_lock_ctrl.replace('_SIDE_', side)}.translateY": [0, 1.0],
                    f"{self.eye_fk_ctrl.replace('_SIDE_', side)}.rotateX": [0, 16]
                }
            )
            rig_utils.set_driven_key(
                {
                    f"{self.eye_lock_ctrl.replace('_SIDE_', side)}.translateX": [0, -1.0],
                    f"{self.eye_fk_ctrl.replace('_SIDE_', side)}.rotateY": [0, mult_value*20]
                }
            )
            rig_utils.set_driven_key(
                {
                    f"{self.eye_lock_ctrl.replace('_SIDE_', side)}.translateX": [0, 1.0],
                    f"{self.eye_fk_ctrl.replace('_SIDE_', side)}.rotateY": [0, mult_value*-20]
                }
            )

    def _hide_control_shapes(self):
        """
        Will hide specific face rig control shapes.
        """
        pmc.PyNode(self.mgear_mouth_jaw_ctrl).getShape().visibility.set(0)
        for side in ["_L_", "_R_"]:
            pmc.PyNode(
                self.eye_fk_ctrl.replace("_SIDE_", side)
            ).getShape().visibility.set(0)

    def _add_blendshape_channels(
        self, upper_lip_ctrl, lower_lip_ctrl, v_shape_ctrl
    ):
        lips_attr_name_list = [
            "L_mouth_pucker",
            "R_mouth_pucker",
            "L_mouth_pull",
            "R_mouth_pull",
            "L_mouth_push",
            "R_mouth_push",
            "L_mouth_roll_in",
            "R_mouth_roll_in",
            "L_mouth_roll_out",
            "R_mouth_roll_out",
        ]
        v_shapes_attr_name_list = [
            "affricate",
            "dental_lip",
            "explosive",
            "lip_open",
            "open",
            "tight",
            "tight_o",
            "wide",
        ]
        for attr_name in lips_attr_name_list:
            for node in [upper_lip_ctrl, lower_lip_ctrl]:
                if not node.hasAttr(attr_name):
                    node.addAttr(
                        attr_name, type="float", min=0.0, max=1.0, keyable=True
                    )
        for attr_name_ in v_shapes_attr_name_list:
            if not v_shape_ctrl.hasAttr(attr_name_):
                v_shape_ctrl.addAttr(
                    attr_name_, type="float", min=0.0, max=1.0, keyable=True
                )

    def _create_face_rig_mesh_islands(self, face_ui_ctrl, face_tweakers_ctrl):
        face_facs_subroot_nodes = face_ui_ctrl.getChildren(type="transform")

        face_tweakers_subroot_nodes = face_tweakers_ctrl.getChildren(
            type="transform",
        )
        face_facs_pin_mesh = mesh_islands.build_combined_pin_mesh(
            face_facs_subroot_nodes,
            rotate=True,
            pin_node_split_amount=100,
            ribbon_node_split_amount=100,
            desired_count=10,
            system_name="faceFACS",
            radius=0.75,
            pre_rotate=(90.0, 0.0, 0.0),
        )[0][0]

        face_tweakers_island_mesh = mesh_islands.build_combined_pin_mesh(
            face_tweakers_subroot_nodes,
            rotate=True,
            pin_node_split_amount=100,
            ribbon_node_split_amount=100,
            desired_count=10,
            system_name="faceTweaker",
            radius=0.5,
        )[0][0]

        pin_mesh_list = [face_facs_pin_mesh, face_tweakers_island_mesh]

        for node in pin_mesh_list:
            node.hide()

        pmc.parent(pin_mesh_list, self.SETUP_GRP)

    def _fix_face_tweakers_scale_issue(self, face_ui_ctrl):
        pin_nodes = [
            node
            for node in face_ui_ctrl.getChildren(ad=True, type="transform")
            if "_pin_" in node.name(long=None)
        ]
        for node in pmc.ls(self.tweaker_buffer_grps) + pin_nodes:
            for axe in ["X", "Y", "Z"]:
                pmc.PyNode(self.global_ctrl).main_scale.connect(
                    node.attr(f"scale{axe}")
                )
