"""
www.pixomondo.com
Date: 10 / 03 / 2022

stagWhite_face_rig module
category : Rigging
subcategory : systems
author : Michele Trabona / Rigging TD

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from builtins import super
from future import standard_library
standard_library.install_aliases()
from ...utils import data
from ...modules import freeControls
from ...systems import facialSystem
import pymel.core as pm


class StagWhite_face_rig(facialSystem.Facial_system):
    FREECTLS_JNTS = ("eyeOrbicularis_R_0_start_default_faceJnt",
                     "eyeOrbicularis_L_0_start_default_faceJnt"
                     )
    ORBICULARIS_PARENT = "C_bnd_neck_0_head_faceJnt"


    def __init__(self):
        self.name = "stagWhite"
        rig_path = data.get_rigging_main_dir(type="face")
        model_path = "X:/redgun_reg-6344/_library/assets/creature/crt_stagWhite/rig_face/in_progress/model_test/model_with_cutout.mb"
        super(StagWhite_face_rig, self).__init__(character_name=self.name,
                                             rig_data_path=rig_path,
                                             model_path=model_path,
                                             builder_path=None,
                                             root_jnt="C_bnd_neck_0_0_jnt",
                                             head_jnt="C_bnd_neck_0_head_jnt",
                                             scale=10,
                                             load_ctls=1,
                                             load_skin=1,
                                             pre_build=self.stagWhite_face_pre_build,
                                             upgrade=self.stagWhite_face_upgrade,
                                             post_build=self.stagWhite_face_post_build)

    def stagWhite_face_pre_build(self):
        # setting eyelid offset push
        facialSystem.Facial_system.eyelid_main_ctl_offset = 2
        self.EYE_MODULE_PARENT = "C_bnd_neck_0_head_faceJnt"
        self.NOSE_MODULE_PARENT = "C_bnd_neck_0_head_faceJnt"

        # getting the eyelid fluid into the no transform group
        global_elements = [
                           "{}Cornea_C_001_high_geo".format(self.name),
                           "{}Eyeball_C_001_high_geo".format(self.name),
                           "{}Pupil_C_001_high_geo".format(self.name)]

        for element in global_elements:
            element = pm.PyNode(element)
            element_dup = pm.duplicate(element,
                                       n=element.name().replace("_high_",
                                                                "_local_"))[0]
            pm.parent([element_dup], "no_transf_GRP")
            pm.blendShape([element_dup], element, frontOfChain=True, weight=(0, 1))

    def stagWhite_face_upgrade(self):
        self.eye_orbicularis_ctl()

    def stagWhite_face_post_build(self):

        elements_to_delete = ['low',
                              '{}Mouth_C_001_high_grp'.format(self.name),
                              '{}Antler_C_001_high_grp'.format(self.name),
                              '{}Body_C_001_high_grp'.format(self.name),
                              '{}Hoofs_C_001_high_grp'.format(self.name)
                              ]
        for e in elements_to_delete:
            try:
                pm.delete(e)
            except:
                pass

        # turning off face modules visibility
        pm.setAttr("vis_C_control_default_ctrl.C_freeControlsMain_prim_vis",0)
        pm.setAttr("vis_C_control_default_ctrl.C_tweakersFace_prim_vis",0)



    def eye_orbicularis_ctl(self):
        freeCtls_mod = freeControls.FreeControls(name="Main",
                                                 scale=10.0,
                                                 elements_list=self.FREECTLS_JNTS,
                                                 create_controls=1,
                                                 side="C",
                                                 make_jnt=0,
                                                 seperate_hierarchy=0,
                                                 base_module=self.base_module)
        ctls_list = freeCtls_mod.ctls_list
        for it, ctl in enumerate(ctls_list):
            if not "throat" in ctl.ctl.name():
                # lock and hide translate
                lock_at = ["tz", "tx", "ty"]
                for at in lock_at:
                    pm.setAttr("{}.{}".format(ctl.ctl, at), l=1, cb=0, k=0)
                pm.parentConstraint(self.ORBICULARIS_PARENT, ctl.off, mo=1)
                pm.parentConstraint(ctl.ctl, self.FREECTLS_JNTS[it], mo=1)
            else:
                # lock and hide translate
                lock_at = ["tz", "tx", "ty", "rx", "ry", "rz", "ro"]
                for at in lock_at:
                    pm.setAttr("{}.{}".format(ctl.ctl, at), l=1, cb=0, k=0)





"""
import pymel.core as pm 
unknown_nodes=pm.ls(type = "unknown")
for item in unknown_nodes:
    if pm.objExists(item):
        pm.delete(item)

plugin_list = pm.unknownPlugin (query = 1, list= 1)

for plg in plugin_list:
    pm.unknownPlugin (plg,remove = 1)


"""