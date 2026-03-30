import mgear.shifter.custom_step as cstp
from mgear import rigbits
import pymel.core as pmc
from maya import cmds
import os
from pxo_rigging_kit.maya_utils.post_and_pre_build import localize_skin_influences_setup
from pxo_rigging_kit.maya_utils import attributes_utils
from pxo_rigging_kit.maya_utils.deformers import blendshape_utils
from pxo_rigging_kit.maya_utils.mgear import mgear_build_utils

import importlib

importlib.reload(localize_skin_influences_setup)


class CustomShifterStep(cstp.customShifterMainStep):
    """Custom Step description
    """

    def setup(self):
        """
        Setting the name property makes the custom step accessible
        in later steps.

        i.e: Running  self.custom_step("pxo_character_custom")  from steps ran after
             this one, will grant this step.
        """
        self.face_vis_controller = None
        self.name = "pxo_character_custom"
        project_path = pmc.workspace(query=True, rootDirectory=True)
        self.data_path = os.path.normpath(os.path.join(project_path, "data"))
        if pmc.objExists("face_ui_C_0_ctrl"):
            self.face_vis_controller = pmc.PyNode("face_ui_C_0_ctrl")


    def run(self):
        """Run method.

            i.e:  self.mgear_run.global_ctl
                gets the global_ctl from shifter rig build base

            i.e:  self.component("control_C0").ctl
                gets the ctl from shifter component called control_C0

            i.e:  self.custom_step("otherCustomStepName").ctlMesh
                gets the ctlMesh from a previous custom step called
                "otherCustomStepName"

        Returns:
            None: None
        """
        fix_hand = True
        global_root_guide = cmds.ls("chr_genericBiped_*_RIGGUIDES")
        if global_root_guide:
            if cmds.attributeQuery("fixhandrotation", node=f"{global_root_guide[0]}|global_C0_root",exists = True):
                fix_hand = cmds.getAttr("global_C0_root.fixhandrotation")

        if fix_hand:
            self.fix_hand_rotation()

        if self.face_vis_controller is None:
            cmds.warning("Self attribute has face is false, face is not build")
            return

        self.attribute_manager()


        skin_layer_0 = cmds.ls("SKINLAYER_0*geo")
        if skin_layer_0:
            cmds.select(skin_layer_0)
            localize_skin_influences_setup.localize_skin_influences_for_selection()
            blendshape_utils.import_from_PXO_BSHP_directory(
                self.data_path, True)


        return

    def fix_hand_rotation(self):
        for side in ("L", "R"):
            ctl = pmc.PyNode(f"arm_{side}_0_ik_ctrl")
            rigbits.addNPO(ctl)

    def attribute_manager(self):
        # Comment this out because it was making issues and created wrong attributes.
        # attributes_utils.BufferAttributeSync().sync_all_children_of(self.face_vis_controller)

        attributes_utils.add_pxo_separator_attr(self.face_vis_controller, "Face_rig_controls")

        if not self.face_vis_controller.hasAttr("FACS_ctrls"):
            self.face_vis_controller.addAttr("FACS_ctrls", at="bool", dv=True, k=True, h=False)
        if not self.face_vis_controller.hasAttr("Tweakers_ctrls"):
            self.face_vis_controller.addAttr("Tweakers_ctrls", at="bool", dv=False, k=True, h=False)

        for cildren in self.face_vis_controller.getChildren(type='transform'):
            cildren.v.unlock()
            pmc.connectAttr(self.face_vis_controller.FACS_ctrls, cildren.v, f=True)

        pmc.connectAttr(self.face_vis_controller.Tweakers_ctrls,
                        pmc.PyNode("global_0_ctrl|faceTweaker_C0_root").v, f=True)
