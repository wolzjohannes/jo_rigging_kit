"""
www.pixomondo.com
Date: 01 / 02 / 2022

facialSystem module
category : Rigging
subcategory : systems
author : Michele Trabona / Rigging TD

"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals

from builtins import super
from future import standard_library
standard_library.install_aliases()
from past.utils import old_div
import pymel.core as pm
from ..utils import name
from ..utils import joint
from ..utils import constraints
from ..modules import eye
from ..modules import eyelid
from ..modules import facialBS
from ..modules import nose
from ..modules import tweakers
from . import baseSystem

"""
Quick facial function to make a first rig test

"""
character_name = "vhagar_face"


class Facial_system(baseSystem.Base_system):

    r_eyelid_start_jnt_list = ["eyelidUpper_R_0_start_default_faceJnt", "eyelidLower_R_0_start_default_faceJnt"]
    r_eye_jnt = "eye_R_0_start_default_faceJnt"
    r_eyelid_ribbon_crvs = ["eyelidUpper_R_0_ribbon_default_jnt", "eyelidLower_R_0_ribbon_default_jnt"]
    l_eyelid_start_jnt_list = ["eyelidUpper_L_0_start_default_faceJnt", "eyelidLower_L_0_start_default_faceJnt"]
    l_eye_jnt = "eye_L_0_start_default_faceJnt"
    l_eyelid_ribbon_crvs = ["eyelidUpper_L_0_ribbon_default_jnt","eyelidLower_L_0_ribbon_default_jnt"]
    nose_jnt = "nose_C_0_start_default_faceJnt"
    nostril_jnts = ["nostril_L_0_start_default_faceJnt","nostril_R_0_start_default_faceJnt"]
    head_jnts = ["C_bnd_head_0_0_localJnt","C_bnd_head_0_0_faceJnt"]
    eyelid_main_ctl_offset = 10
    EYE_MODULE_PARENT = "C_bnd_upperJaw_0_0_faceJnt"
    NOSE_MODULE_PARENT = "C_bnd_upperJaw_0_2_faceJnt"

    def __init__(self,
                 character_name="new",
                 rig_data_path=None,
                 model_path=None,
                 builder_path=None,
                 root_jnt=None,
                 head_jnt=None,
                 scale=1.0,
                 build_bs = 1,
                 load_skin=1,
                 load_deformers=0,
                 load_ctls = 1,
                 go_to_T_pose=0,
                 pre_build = None,
                 upgrade = None,
                 post_build = None

                 ):

        """
        It will build the facial rig system.

        Args:
            character_name(str): The name we will insert
                on the base module name.
            model_path(str): Model path directory.
            builder_path(str):  Builder path directory.
            root_jnt(pm.PyNode(),str): The root joint
                that will be used for the skeleton connections.
            head_jnt(pm.PyNode(),str): The head joint
                that will be used to snap the visibility control.
            scale(float): The scale value which will be applied
                on all the modules.
            load_skin(bool): It lets the user to choose if the
                skin will or will not be loaded.
            load_deformers(bool):It lets the user to choose if the
                deformers will or will not be loaded.
            go_to_T_pose(bool):It lets the user to choose if the
                pose will or will not be applied before the
                control creation.
        Return:
            None.

        """

        self.character_name = character_name
        self.rig_data_path = rig_data_path
        self.model_path = model_path
        self.builder_path = builder_path
        self.root_jnt = root_jnt
        self.head_jnt = head_jnt
        self.scale = scale
        self.build_bs = build_bs
        self.load_skin = load_skin
        self.load_deformers = load_deformers
        self.go_to_T_pose = go_to_T_pose
        self.custom_pre_build = pre_build
        self.custom_upgrade = upgrade
        self.custom_post_build = post_build

        super(Facial_system, self).__init__(character_name,
                                            rig_data_path,
                                            model_path,
                                            builder_path,
                                            root_jnt,
                                            head_jnt,
                                            scale,
                                            load_skin,
                                            load_deformers,
                                            load_ctls,
                                            go_to_T_pose,
                                            type="face")

    def pre_build(self):
        """
        It is a instance class and it will be executed
        after the load of all the files needed and
        after the base module creation.

        """
        #   setting up the joints
        local_root_jnt = pm.duplicate(self.root_jnt)[0]

        #   getting local the joint chain and renaming
        self.local_joint_chain = joint.get_joint_chain(local_root_jnt)

        name.renamer_change_suffix(self.local_joint_chain, "localJnt")
        pm.parent(local_root_jnt,
                  self.base_module.no_transf_grp)

        #   make static mesh
        self.face_geo = pm.ls("{}Head_*_high_*geo".format(self.character_name))[0]
        static_mesh = pm.duplicate(self.face_geo,
                                   n = "face_local_geo")[0]

        pm.parent(static_mesh, self.base_module.no_transf_grp)
        facial_bs = pm.blendShape(static_mesh, self.face_geo, n = "main_facial_BS")[0]
        pm.setAttr("{}.{}".format(facial_bs.name(), static_mesh.name()), 1)

        if self.build_bs:
            pm.parent("facialBS_geo",self.base_module.no_transf_grp)
            facial_bs = pm.blendShape("facialBS_geo", static_mesh, n="connect_BS")[0]
            pm.setAttr("{}.{}".format(facial_bs.name(), "facialBS_geo"), 1)

        if not self.custom_pre_build == None:
            self.custom_pre_build()


    def upgrade(self):
        """
        It is a instance class and it will be executed
        after the creation of extra joints and the load
        of the skin and deformers.

        """
        #tagging the original chain for the body connection
        face_joint_chain = joint.get_joint_chain(self.root_jnt)
        for jnt in face_joint_chain:
            if jnt.hasAttr("ObjTag"):
                if jnt.ObjTag.get() == "bodyRig":
                    if jnt.hasAttr("connection_tag"):
                        constraints.remove_connection_tag(jnt)
                    constraints.connection_tag (jnt, "pConstraint", jnt)
        name.renamer_change_suffix(face_joint_chain, "faceJnt")
        self.face_head_jnt = pm.ls("*head*faceJnt")[0]
        for jnt in self.local_joint_chain:
            if not jnt.hasAttr("ObjTag"):
                parent_jnt = name.change_suffix(jnt.name(), "faceJnt")
                constraints.connection_tag(jnt,
                                           "rConnection",
                                           parent_jnt)

        #connect the tagged local joints
        constraints.connect_by_tag(self.local_joint_chain)
        if not self.custom_upgrade == None:
            self.custom_upgrade()

    def post_build(self):
        pm.setAttr("{}.extraElements_vis".format(
            self.r_lid.module_base.top_grp),
            0)
        pm.setAttr("{}.extraElements_vis".format(
            self.l_lid.module_base.top_grp),
            0)
        #hiding_secondary ctls
        pm.setAttr ("vis_C_control_default_ctrl.R_eyelid_second_vis",0)
        pm.setAttr("vis_C_control_default_ctrl.L_eyelid_second_vis", 0)

        #parent constraint the modules and ctls groups
        pm.parentConstraint(self.EYE_MODULE_PARENT,
            self.r_eye.module_base.top_grp,
                            mo =1)
        pm.parentConstraint(self.EYE_MODULE_PARENT,
            self.l_eye.module_base.top_grp,
                            mo =1)
        pm.parentConstraint(self.NOSE_MODULE_PARENT,
            self.nose.module_base.top_grp,
                            mo =1)
        pm.parentConstraint(self.EYE_MODULE_PARENT,
            self.r_lid.module_base.control_grp,
                            mo =1)
        pm.parentConstraint(self.EYE_MODULE_PARENT,
                            self.l_lid.module_base.control_grp,
                            mo=1)
        pm.parentConstraint(self.EYE_MODULE_PARENT,
                            self.r_lid.module_base.secondary_grp,
                            mo=1)
        pm.parentConstraint(self.EYE_MODULE_PARENT,
                            self.l_lid.module_base.secondary_grp,
                            mo=1)
        if self.custom_post_build is not None:
            self.custom_post_build()
        pm.delete("skeleton_grp")

    def rig_builder(self):

        #   R eye
        self.r_eye = eye.Eye(eye_start=self.r_eye_jnt,
                             scale=old_div(self.scale, 3),
                             aim_shift_mult=5,
                             base_module=self.base_module)
        #   L eye
        self.l_eye = eye.Eye(eye_start= self.l_eye_jnt,
                             scale=old_div(self.scale, 3),
                             aim_shift_mult=5,
                             base_module = self.base_module)
        #   R eyelid
        self.r_lid = eyelid.Eyelid(eyelid_starts=self.r_eyelid_start_jnt_list,
                                   eye_jnt=self.r_eye_jnt,
                                   head_jnts=self.head_jnts,
                                   scale=self.scale,
                                   fleshy_eyelids=1,
                                   vert_ranges=[[[-45, 45], [-42, 42]],
                                   [[-45, 45], [-42, 42]]],
                                   oriz_ranges=[[[-40, 40], [-8, 8]],
                                   [[-40, 40], [-5, 5]]],
                                   main_ctl_offset=self.eyelid_main_ctl_offset,
                                   ribbon_curves=self.r_eyelid_ribbon_crvs,
                                   base_module = self.base_module)

        #   L eyelid
        self.l_lid = eyelid.Eyelid(eyelid_starts=self.l_eyelid_start_jnt_list,
                                   eye_jnt=self.l_eye_jnt,
                                   head_jnts=self.head_jnts,
                                   scale=self.scale,
                                   fleshy_eyelids=1,
                                   vert_ranges=[[[-45, 45], [-42, 42]],
                                   [[-45, 45], [-42, 42]]],
                                   oriz_ranges=[[[-40, 40], [-8, 8]],
                                   [[-40, 40], [-5, 5]]],
                                   main_ctl_offset=self.eyelid_main_ctl_offset,
                                   ribbon_curves=self.l_eyelid_ribbon_crvs,
                                   base_module = self.base_module)
        #   nose
        self.nose = nose.Nose(start_jnt=self.nose_jnt,
                              secondary_jnts=self.nostril_jnts,
                              scale=self.scale,
                              base_module = self.base_module)

        facialBS.FacialBS(bs_mesh="facialBS_geo",
                          dummies_ctl_grp="dummie_shapes_grp",
                          moving_mesh=self.face_geo,
                          scale=self.scale,
                          base_module = self.base_module)

        tweakers.Tweakers(
                        name = "Face",
                        moving_mesh=self.face_geo,
                          mesh = "face_local_geo",
                    dummies_locs_grp="dummies_tweaker_grp",
                          scale=self.scale,
                          base_module = self.base_module)

        print ("******* Rig-Builder Executed *******")

