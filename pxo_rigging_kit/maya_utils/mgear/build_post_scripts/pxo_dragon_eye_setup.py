# mgear / pixo dragon eye setup.
# Artist: Johannes Wolz / Rigging TD

"""
Mgear post script to build the dragon eye setup.
This setup is really naming sensitive.
Pls do not rename the guide objects.
You will need the guide objects:
- Joints hierarchy:
    - guide_eyeOrbicularis_L_0_start_default_jnt
    - guide_eyeOrbicularis_R_0_start_default_jnt
- Eyelid curve nodes:
    - eyelidUpper_L_0_ribbon_default_jnt
    - eyelidLower_L_0_ribbon_default_jnt
    - eyelidUpper_R_0_ribbon_default_jnt
    - eyelidLower_R_0_ribbon_default_jnt

You can find a guide template as maya file in this package with the name:
- guides_dragons_eye_setup.ma

We aware that you have to bind and prepare the skinClusters
for these nurbs objects after build:

- "eyelidUpper_L_0_ribbon_default_nrb".
- "eyelidLower_L_0_ribbon_default_nrb".
- "eyelidUpper_R_0_ribbon_default_nrb".
- "eyelidLower_R_0_ribbon_default_nrb".

With these joints for each side:
- C_bnd_upperJaw_0_0_jnt
- eyelidUpper_L_0_end_default_jnt
- eyelidLower_L_0_end_default_jnt

The "eye_L_0_end_default_jnt" has to be skinned to the eyeball.

These joints has to be skinned to the characters body/face:
- eyelidUpperTweak*_L_control_default_faceJnt
- eyelidLowerTweak*_L_control_default_faceJnt

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library

from builtins import zip

import logging
import pymel.core as pmc
import mgear.shifter.custom_step as cstp
import pxo_rigging_kit.maya_utils.rigging.legacy_rig_lib.modules.eye

import pxo_rigging_kit.maya_utils.rigging.legacy_rig_lib.modules.eye
from pxo_rigging_kit.maya_utils.maya_conversion_utils import pymaya_to_pymel

from pxo_rigging_kit.maya_utils.rigging.legacy_rig_lib.utils import nodes as pnodes
from pxo_rigging_kit.maya_utils.rigging.legacy_rig_lib.modules import freeControls
from pxo_rigging_kit.maya_utils.rigging.legacy_rig_lib.utils import name
from pxo_rigging_kit.maya_utils.rigging.legacy_rig_lib.modules import eyelid

from pxo_rigging_kit.maya_utils.paths_utils import get_asset_infos
from pxo_rigging_kit.maya_utils.rigging import rig_utils
from pxo_rigging_kit.maya_utils import paths_utils
from pxo_rigging_kit.maya_utils.exceptions import MayaNodeNotFound
from pxo_rigging_kit.maya_utils.mgear import mgear_build_utils

standard_library.install_aliases()

#######################################################
# GLOBALS
#######################################################

logging.basicConfig(level=logging)
_LOGGER = logging.getLogger(__name__ + ".py")
EYELID_RANGES_JSON_NAME = "pxo_eyelid_ranges.json"

#######################################################
# CLASSES
#######################################################


class CustomShifterStep(cstp.customShifterMainStep):
    FREECTLS_JNTS = (
        "eyeOrbicularis_L_0_start_default_jnt",
        "eyeOrbicularis_R_0_start_default_jnt",
    )
    ORBICULARIS_PARENT = "C_bnd_upperJaw_0_0_jnt"
    EYE_SETUP_GRP_NAME = "eye_setup_grp"
    EYE_LID_DEV_GRP_NAME = "eyelidLocalDef*_grp"
    SETUP_GRP = "setup"
    HEAD_HOST = "headHost_C_0_control_default_ctrl"
    FACS_CONTROLS_VIS_ATTR = "FACS_controls_vis"
    EYE_LID_SYSTEM_VIS_ATTR = "EYE_control_vis"
    EYE_LID_MODULES = "eyelid_SIDE_primCtl_GRP"
    CTL_LIST = (
        "eyelid_R_control_default_ctrl",
        "eyelid_L_control_default_ctrl",
    )

    JNTS_LIST = ("eye_R_0_end_default_jnt", "eye_L_0_end_default_jnt")
    EYE_SYS_PARENT_ND = "upperJaw_C_0_fk0_*_ctrl"
    GUIDE_EYE_ORBI_JNT = "guide_eyeOrbicularis_*_0_start_default_jnt"
    EYE_START_JNT = "eye_SIDE_0_start_default_jnt"
    EYELID_START_JNTS = [
        "eyelidUpper_SIDE_0_start_default_jnt",
        "eyelidLower_SIDE_0_start_default_jnt",
    ]
    EYE_LID_CURVES_JNTS = [
        "eyelidUpper_SIDE_0_ribbon_default_jnt",
        "eyelidLower_SIDE_0_ribbon_default_jnt",
    ]
    HEAD_JNT = "C_bnd_head_0_0_jnt"
    GUIDE_SUFFIX = "guide"
    EYELID_CTRL_NAME = "eyelid_*_control_default_ctrl"
    SECOND_EYE_LID_GUIDES = "*_bnd_secondEyelid_*_0_jnt_LOC_GRP_{}".format(
        GUIDE_SUFFIX
    )
    CTRL_BUFFER_SUFFIX = "_controlBuffer"
    EYE_GUIDE_SETUP = "guide_eye_setup"
    DEFORMER_SET = "deformers_set"

    EYE_LID_JNTS = "eyelid*Tweak*_*_control_default_faceJnt"
    EYE_LID_OFFSET_JNTS = "eyelid*Tweak*_*_control_default_faceOffsetJnt"
    EYES_CTRL_ROOT = "eyeOrbicularisMain0_*_control_default_offsetCtrl"
    GLOBAL_CTRL = "global_0_default_ctrl"
    EYE_LID_CTRL_BF_GRP = "eyelid*Tweak*_*_control_default_offsetCtrl"
    EYE_RIVET_GRP = "eyelidUpperTweak_*_*_ribbon_default_rivet"


    def __init__(self):
        self.name = "pxo_eye_setup_2"
        self.orbi_ctrls = []
        self.orbi_root_grp = []
        self.eye_jnts = []
        self.eye_lid_values_default_dict = {
                "vert_ranges": [[[-30, 30], [-8, 8]], [[-30, 30], [-8, 8]]],
                "oriz_ranges": [[[-50, 50], [-8, 8]], [[-50, 50], [-5, 5]]],
                "aim_shift_mult": 5,
                "eyelid_scale": 4,
                "main_ctl_offset": 5
            }
        self.asset_name = str(get_asset_infos(pmc.sceneName(), "asset_name"))
        self.eye_lid_name = "eyelid"
        self.iris_dilator_muscle_name = "iris_dilator_muscle"

    def run(self, stepDict):
        ranges_dict = paths_utils.get_asset_data_from_json(
            EYELID_RANGES_JSON_NAME
        )
        if not ranges_dict:
            ranges_dict = self.eye_lid_values_default_dict

        self.get_guide_joints()

        eyes = [
            pxo_rigging_kit.maya_utils.rigging.legacy_rig_lib.modules.eye.Eye(
                eye_start=self.EYE_START_JNT.replace("_SIDE_", f"_{side}_"),
                scale=10,
                aim_shift_mult=ranges_dict.get("aim_shift_mult"),
                side=side,
            )
            for side in "LR"
        ]

        self.eye_orbicularis_ctl()

        _LOGGER.info(self.orbi_ctrls)

        eye_lids = [
            self._create_eyelid_instance(
                ranges_dict, side, self.orbi_ctrls[id_]
            )
            for id_, side in enumerate("LR")
        ]
        self.eye_in_shift()

        self.finish_eye_system(
            [eyes[0].module_base.top_grp, eyes[1].module_base.top_grp],
            [eye_lids[0].module_base.top_grp, eye_lids[1].module_base.top_grp],
            stepDict
        )
        self.create_second_eyelid_system()
        self.tweak_control_shapes()
        self.create_bind_joints(step_dict=stepDict)

    def _create_eyelid_instance(self, ranges_dict, side, scaling_control):

        _eyelid_starts = [
            str_obj.replace("_SIDE_", f"_{side}_")
            for str_obj in self.EYELID_START_JNTS
        ]

        return eyelid.Eyelid(
            eyelid_starts=_eyelid_starts,
            eye_jnt=self.EYE_START_JNT.replace("_SIDE_", f"_{side}_"),
            head_jnts=self.HEAD_JNT,
            scale=ranges_dict["eyelid_scale"],
            fleshy_eyelids=1,
            vert_ranges=ranges_dict["vert_ranges"],
            oriz_ranges=ranges_dict["oriz_ranges"],
            main_ctl_offset=ranges_dict["main_ctl_offset"],
            ribbon_curves=[
                str_obj.replace("_SIDE_", f"_{side}_")
                for str_obj in self.EYE_LID_CURVES_JNTS
            ],
            side=side,
            scaling_control=scaling_control,
        )

    def eye_in_shift(self):
        """
        Creates the eye shift in mechanism like a crocodile.
        """
        for ctl, jnt in zip(self.CTL_LIST, self.JNTS_LIST):
            side = name.get_side(ctl, with_undescore=False)
            max_output = 1.3

            if side == "L":
                max_output = max_output * (-1)

            pnodes.create_remap_val_node(
                input=f"{ctl}.ty",
                inputMin=0,
                inputMax=1,
                outputMin=0,
                outputMax=max_output,
                output=f"{jnt}.tx",
                name=f"{'range'}_pushIn_{side}_RMV",
            )

        _LOGGER.info("Eye shift in mechanise applied.")

    def eye_orbicularis_ctl(self):
        """
        Creates the eye orbiularis control.
        """

        free_ctls_mod = freeControls.FreeControls(
            name="Main",
            scale=10.0,
            elements_list=self.FREECTLS_JNTS,
            create_controls=True,
            side="C",
            make_jnt=0,
            seperate_hierarchy=True,
        )

        ctls_list = free_ctls_mod.ctls_list

        for it, ctl in enumerate(ctls_list):
            if "throat" not in ctl.ctl.name():

                pmc.parentConstraint(self.ORBICULARIS_PARENT, ctl.off, mo=True)

                scale_offset_grp = pmc.createNode(
                    "transform", n=ctl.ctl.name().replace("ctrl", "jntOffset")
                )
                pmc.matchTransform(scale_offset_grp, self.FREECTLS_JNTS[it])
                pmc.parent(self.FREECTLS_JNTS[it], scale_offset_grp)
                pmc.parent(
                    scale_offset_grp, free_ctls_mod.module_base.joints_grp
                )

                rig_utils.pxo_constraining(
                    masters=ctl.ctl,
                    slaves=scale_offset_grp,
                    maintainOffset=True,
                    name=None,
                    skipRotate=("x", "y", "z"),
                    skipTranslate=("x", "y", "z"),
                    skipScale=None,
                    native=False,
                    space_switch=False,
                    host=None,
                )

                pmc.parentConstraint(ctl.ctl, self.FREECTLS_JNTS[it], mo=True)

            else:
                # lock and hide translate
                lock_at = ["tz", "tx", "ty", "rx", "ry", "rz", "ro"]
                for at in lock_at:
                    pmc.setAttr(f"{ctl.ctl}.{at}", l=1, cb=0, k=0)
                    eye_sys_parent = pmc.ls(self.EYE_SYS_PARENT_ND)

                    if not eye_sys_parent:
                        raise MayaNodeNotFound(f"{self.EYE_SYS_PARENT_ND} not existing.")

                    pmc.parentConstraint(eye_sys_parent, ctl.off, mo=1)

        self.orbi_ctrls = [ctrl.ctl for ctrl in ctls_list]
        self.orbi_root_grp = free_ctls_mod.module_base.top_grp

        _LOGGER.info("The Eye orbicularis control created.")

    def finish_eye_system(self, eye_modules, eyelid_root_grp, stepDict):
        """
        That method will parent, delete and connect nodes of the
        dragon eye system.

        Args:
            eye_modules[list]: The eye root top nodes in a list.
            eyelid_root_grp[list]: The eyelid root top nodes in a list.

        """
        main_grp = pmc.createNode("transform", n=self.EYE_SETUP_GRP_NAME)

        eye_lid_def_grp = pmc.ls(self.EYE_LID_DEV_GRP_NAME)

        pmc.delete(eye_lid_def_grp)

        if not pmc.objExists(f"{self.HEAD_HOST}.{self.FACS_CONTROLS_VIS_ATTR}"):

            pmc.PyNode(self.HEAD_HOST).addAttr(
                self.FACS_CONTROLS_VIS_ATTR, at="bool", keyable=True
            )
            pmc.PyNode(self.HEAD_HOST).attr(self.FACS_CONTROLS_VIS_ATTR).set(
                cb=True, keyable=False
            )

        facs_ctrl_vis_attr = pmc.PyNode(self.HEAD_HOST).attr(
            self.FACS_CONTROLS_VIS_ATTR
        )

        facs_ctrl_vis_attr.connect(main_grp.visibility)

        for jnt in self.eye_jnts:

            jnt.visibility.set(0)

        for side in ["_L_", "_R_"]:

            for ctrl, grp in zip(self.orbi_ctrls, eye_modules):

                if side in ctrl.nodeName() and side in grp.nodeName():
                    offset_trs = pmc.createNode(
                        "transform", n="{0}_offset_trs".format(grp.node())
                    )
                    ctrl.worldMatrix[0].connect(offset_trs.offsetParentMatrix)
                    grp.setParent(offset_trs)
                    offset_trs.setParent(main_grp)

                    eye_lid_grp = pmc.PyNode(
                        self.EYE_LID_MODULES.replace("_SIDE_", side)
                    )

                    offset_trs_1 = pmc.createNode(
                        "transform",
                        n=f"{eye_lid_grp.nodeName()}_offset_trs",
                    )

                    ctrl.worldMatrix[0].connect(offset_trs_1.offsetParentMatrix)

                    offset_trs_1.setParent(eye_lid_grp.getParent())

                    eye_lid_grp.setParent(offset_trs_1)

        pmc.parent(self.orbi_root_grp, eyelid_root_grp, main_grp)

        pmc.PyNode(self.SETUP_GRP).addChild(main_grp)

        all_controls = [node for node
                        in main_grp.getChildren(ad=True, type="transform")
                        if node.hasAttr("rig_ctrl") is True
                        ]

        rig = stepDict["mgearRun"].model

        controller_set_ = rig.rigGroups.inputs()[1]
        controller_set = pymaya_to_pymel(controller_set_)

        controller_set.addMembers(all_controls)
        _LOGGER.info("Eye setup finished.")

    def get_guide_joints(self):
        """
        Get the guide joints in scene.
        And create the actual eye lid driver joints.
        """
        guide_nodes = pmc.ls(self.GUIDE_EYE_ORBI_JNT)
        if not guide_nodes:
            raise LookupError(
                "No eye guide joints existing with the name: {}.".format(
                    self.GUIDE_EYE_ORBI_JNT
                )
            )
        duplicates = pmc.duplicate(guide_nodes)
        pmc.parent(duplicates, None)
        hierarchy = []
        hierarchy.extend(duplicates)
        [hierarchy.extend(node.getChildren(ad=True)) for node in duplicates]
        hierarchy = list(set(hierarchy))

        for node in hierarchy:
            new_name = (
                node.nodeName().replace("guide_", "").replace("_jnt1", "_jnt")
            )
            node.rename(new_name)

        self.eye_jnts = duplicates

    def create_second_eyelid_system(
        self,
        anim_blend_values=(35.313, 140, 0),
        translate_push_values=(5.5, 5.067),
    ):
        """
        Create a second eyelid system.
        If no guide nodes in the scene will just return None.

        Args:
            anim_blend_values(tuple): The anim blend values for rotation of the second eyelid joints.
                                      Default is (35.313, 140, 0).
            translate_push_values(tuple): The push values of the end joints of the second eyelid joints.
                                          Default is (7.0, 5.067).

        """
        eyelid_ctrls = pmc.ls(self.EYELID_CTRL_NAME)
        second_eye_lid_guides = pmc.ls(self.SECOND_EYE_LID_GUIDES)
        if not second_eye_lid_guides:
            return
        second_eye_lid_root_nodes = [
            guide_nd.duplicate()[0] for guide_nd in second_eye_lid_guides
        ]
        [
            node.rename(
                node.name(long=None).replace(
                    "_{}1".format(self.GUIDE_SUFFIX), ""
                )
            )
            for node in second_eye_lid_root_nodes
        ]
        for guide_nd in second_eye_lid_root_nodes:
            child_nodes = guide_nd.getChildren(ad=True)
            for child_nd in child_nodes:
                child_nd.rename(
                    child_nd.name(long=None).replace(
                        "_{}".format(self.GUIDE_SUFFIX), ""
                    )
                )
        for side in ["L", "R"]:
            eyelid_ctrl = [
                node
                for node in eyelid_ctrls
                if "{}_".format(side) in node.name(long=None)
            ][0]
            second_eye_lid_root_nodes_by_side = [
                node
                for node in second_eye_lid_root_nodes
                if "{}_".format(side) in node.name(long=None)
            ]
            if not eyelid_ctrl.hasAttr(self.eye_lid_name):
                eyelid_ctrl.addAttr(
                    self.eye_lid_name,
                    type="float",
                    min=0.0,
                    max=1.0,
                    keyable=True,
                )
            if not eyelid_ctrl.hasAttr(self.iris_dilator_muscle_name):
                eyelid_ctrl.addAttr(
                    self.iris_dilator_muscle_name,
                    type="float",
                    min=0.0,
                    max=1.0,
                    keyable=True,
                )
            second_eyelid_joints = [
                node.getChildren(ad=True, type="joint")
                for node in second_eye_lid_root_nodes_by_side
            ]
            second_eye_lid_locs = [
                node.getChildren(ad=True, type="locator")[0].getTransform()
                for node in second_eye_lid_root_nodes_by_side
            ]
            eyelid_attr = eyelid_ctrl.attr(self.eye_lid_name)
            for jnt_tuple in second_eyelid_joints:
                anim_blend_nd = pmc.createNode("animBlendNodeAdditiveRotation")
                anim_blend_nd.inputA.set(anim_blend_values)
                eyelid_attr.connect(anim_blend_nd.weightA)
                anim_blend_nd.output.connect(jnt_tuple[1].rotate)
                if "secondEyelid_0_" in jnt_tuple[0].name(
                    long=False
                ) or "secondEyelid_1_" in jnt_tuple[0].name(long=False):
                    color_blend_nd = pmc.createNode("blendColors")
                    eyelid_attr.connect(color_blend_nd.blender)
                    color_blend_nd.color1R.set(translate_push_values[0])
                    color_blend_nd.color2R.set(translate_push_values[1])
                    color_blend_nd.outputR.connect(jnt_tuple[0].translateX)
            for locator in second_eye_lid_locs:
                if "secondEyelid_0_" in locator.name(
                    long=False
                ) or "secondEyelid_1_" in locator.name(long=False):
                    anim_blend_nd_1 = pmc.createNode(
                        "animBlendNodeAdditiveRotation"
                    )
                    eye_start_jnt = pmc.PyNode(
                        self.EYE_START_JNT.replace("SIDE", side)
                    )
                    eye_start_jnt.rotate.connect(anim_blend_nd_1.inputA)
                    anim_blend_nd_1.output.connect(locator.rotate)
                    anim_blend_nd_1.weightA.set(0.25)
            parent_nd = [
                pmc.PyNode(node_name)
                for node_name in self.FREECTLS_JNTS
                if "_{}_".format(side) in node_name
            ][0]
            for sec_eye_lid_root in second_eye_lid_root_nodes_by_side:
                parent_nd.addChild(sec_eye_lid_root)

    def tweak_control_shapes(self):
        """
        Tweak the control shapes. To the shape we specifie before as _controlBuffer shape.
        """
        try:
            eye_guides_grp = pmc.PyNode(self.EYE_GUIDE_SETUP)
        except Exception as e:
            print(e)
            return
        buffer_controls = [node for node in eye_guides_grp.getChildren() if self.CTRL_BUFFER_SUFFIX in node.name(long=None)]
        if not buffer_controls:
            _LOGGER.info(f"No control buffer shapes found in {eye_guides_grp}. Will abort.")
            return
        for buffer_ctrl in buffer_controls:
            try:
                ctl = pmc.PyNode(
                    buffer_ctrl.replace(self.CTRL_BUFFER_SUFFIX, "")
                )
            except:
                continue
            buffer_shape = buffer_ctrl.getShape()

            if not buffer_shape:
                continue

            buffer_shape.worldSpace[0].connect(
                ctl.getShape().create, force=True
            )
            pmc.delete(ctl.getShape(), ch=True)

    def create_bind_joints(self, step_dict):
        """
        Create the bind joints.
        """
        jnt_root = pmc.PyNode(self.ORBICULARIS_PARENT)

        try:
            def_set = pmc.PyNode(self.DEFORMER_SET)

        except:
            def_set = mgear_build_utils.get_deformers_set(step_dict=step_dict)

        _jnt_list = self._build_list_to_duplicate()

        for node in _jnt_list:

            side = node.name(long=None).split("_")[1]
            jnt_name = f"{side}_bnd_{node.name(long=None).replace(f'_{side}_', '_')}"

            jnt = pmc.createNode("joint", n=jnt_name)
            jnt.radius.set(110)
            jnt.overrideEnabled.set(1)
            jnt.overrideColor.set(5)

            jnt_root.addChild(jnt)

            rig_utils.pxo_constraining(node, jnt)
            jnt.jointOrient.set(0.0, 0.0, 0.0)
            def_set.addMember(jnt)

    def _build_list_to_duplicate(self):
        """Returns the list to duplicate"""

        _jnt_list = list()

        _jnt_list.extend(pmc.ls(self.EYE_LID_JNTS))
        _jnt_list.extend(pmc.ls(self.EYE_LID_OFFSET_JNTS))
        _jnt_list.extend(pmc.ls(self.FREECTLS_JNTS))
        _jnt_list.extend(pmc.ls(self.JNTS_LIST))

        return _jnt_list

    def fix_scaling_issue(self):
        """
        Will tweak the eye rig for a correct scaleing with the main scale attr on the gloabl ctrl
        """
        for eye_root in pmc.ls(self.EYES_CTRL_ROOT):
            for axe in ["X", "Y", "Z"]:
                tgt_scale = eye_root.attr(f"scale{axe}")
                current_value = tgt_scale.get()
                mult_double_lin = pmc.createNode("multDoubleLinear")
                mult_double_lin.input2.set(current_value)
                glob_axe = pmc.PyNode(f"{self.GLOBAL_CTRL}.scale{axe}")
                glob_axe.connect(mult_double_lin.input1)
                mult_double_lin.output.connect(tgt_scale)
        for node in pmc.ls(self.EYE_LID_CTRL_BF_GRP):
            for axe in ["X", "Y", "Z"]:
                glob_axe = pmc.PyNode(f"{self.GLOBAL_CTRL}.scale{axe}")
                tgt_scale = node.attr(f"scale{axe}")
                glob_axe.connect(tgt_scale)
        for node in pmc.ls(self.EYE_RIVET_GRP):
            for axe in ["X", "Y", "Z"]:
                glob_axe = pmc.PyNode(f"{self.GLOBAL_CTRL}.scale{axe}")
                tgt_scale = node.attr(f"scale{axe}")
                glob_axe.connect(tgt_scale)



