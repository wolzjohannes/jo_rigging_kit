"""
www.pixomondo.com
Date: 25 / 02 / 2022

syrax_face_rig module
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
from builtins import zip
from ...utils import data
from ...utils import name
from ...utils import nodes as pnodes
from ...modules import freeControls
from ...systems import facialSystem
import pymel.core as pm
class VermithorFaceRig(facialSystem.Facial_system):
    FREECTLS_JNTS = ("eyeOrbicularis_R_0_start_default_faceJnt",
                        "eyeOrbicularis_L_0_start_default_faceJnt",
                        "throat_C_0_start_default_faceJnt")
    ORBICULARIS_PARENT = "C_bnd_upperJaw_0_0_faceJnt"
    THIRD_EYELID_JNTS = ("eyelidThird_R_0_start_default_localJnt",
                         "eyelidThird_L_0_start_default_localJnt")
    def __init__(self):
        self.name = "vermithor"
        rig_path = data.get_rigging_main_dir(type ="face")
        model_path = r"X:\redgun_reg-6344\_library\assets\creature\crt_vermithor\mdl\_publish\reg_crt_vermithor_mdl_v061_awg.mb"
        super(VermithorFaceRig,self).__init__(character_name = self.name ,
                                                rig_data_path = rig_path,
                                                model_path = model_path,
                                                builder_path = None,
                                                root_jnt = "C_bnd_neck_0_0_jnt",
                                                head_jnt = "C_bnd_head_0_0_jnt",
                                                scale = 30,
                                              load_ctls=True,
                                              load_skin=True,
                                               pre_build = self.vermithor_face_pre_build,
                                               upgrade = self.vermithor_face_upgrade,
                                               post_build = self.vermithor_face_post_build)

    def vermithor_face_pre_build(self):
        #getting the eyelid fluid/iris into the no transform group
        global_elements = ["{}EyefluidLower_C_001_high_geo".format(self.name),
                           "{}EyefluidUpper_C_001_high_geo".format(self.name),
                           "{}Cornea_C_001_high_geo".format(self.name),
                           "{}Pupil_C_001_high_geo".format(self.name),
                           "{}Lid_C_001_high_geo".format(self.name),
                           "{}Iris_C_001_high_geo".format(self.name)]
        for element in global_elements:
            element  = pm.PyNode(element)
            element_dup = pm.duplicate(element,
                         n = element.name().replace("_high_",
                                                          "_local_"))[0]
            pm.parent([element_dup],self.base_module.no_transf_grp)
            pm.blendShape([element_dup], element, frontOfChain=True, weight=(0, 1))


    def vermithor_face_upgrade(self):
        self.eye_orbicularis_ctl()


    def vermithor_face_post_build(self):
        elements_to_delete = ['low',
                              'sliced',
                              '{}Muscles_all_high_grp'.format(self.name),
                              '{}Skeleton_all_high_grp'.format(self.name),
                              '{}Claws_C_001_high_grp'.format(self.name),
                              '{}Body_C_001_high_grp'.format(self.name),
                              '{}WingSimProxy_all_high_grp'.format(self.name),
                              '{}Horns_C_002_high_geo'.format(self.name)]
        for e in elements_to_delete:
            try:
                pm.delete(e)
            except:
                pass
        self.eye_in_shift()
        self.iris_connections()
        self.third_eyelid_rig()
        self.throat_connections()
        #self.fake_lips_closing_collision()
        #turning off face modules visibility
        pm.setAttr("vis_C_control_default_ctrl.C_freeControlsMain_prim_vis",0)
        pm.setAttr("vis_C_control_default_ctrl.C_tweakersFace_prim_vis",0)


    def eye_in_shift(self):
        ctl_list = ("eyelid_R_control_default_ctrl","eyelid_L_control_default_ctrl")
        jnts_list = ("eyeIn_R_0_end_default_localJnt","eyeIn_L_0_end_default_localJnt")
        for ctl, jnt in zip(ctl_list,jnts_list):
            side = name.get_side(ctl, with_undescore=0)
            max_output = 1.3
            if side == "L":
                max_output = max_output * (-1)
            pnodes.create_remap_val_node(input = "{}.ty".format(ctl),
                                           inputMin = 0,
                                           inputMax = 1,
                                           outputMin = 0,
                                           outputMax = max_output,
                                           output = "{}.tx".format(jnt),
                                           name = "{}_pushIn_{}_RMV".format("range",side))

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
        for it,ctl in enumerate(ctls_list):
            if not "throat" in ctl.ctl.name():
                #lock and hide translate
                lock_at = ["tz","tx","ty"]
                for at in lock_at:
                    pm.setAttr("{}.{}".format(ctl.ctl,at), l = 1, cb = 0, k =0)
                pm.parentConstraint(self.ORBICULARIS_PARENT, ctl.off, mo = 1)
                pm.parentConstraint(ctl.ctl, self.FREECTLS_JNTS[it], mo = 1)
            else:
                #lock and hide translate
                lock_at = ["tz","tx","ty","rx","ry","rz","ro"]
                for at in lock_at:
                    pm.setAttr("{}.{}".format(ctl.ctl,at), l = 1, cb = 0, k =0)
                    pm.parentConstraint('C_bnd_head_0_0_faceJnt', ctl.off, mo=1)

    def iris_connections(self):
        if pm.objExists("irisBlendshape_grp"):
            for e in pm.listRelatives("irisBlendshape_grp"):
                blend_shape_nd = pm.blendShape([e], "{}Iris_C_001_local_geo".format(self.name),
                                               frontOfChain=True,
                                               weight=(0, 1))
                side = name.get_side(e, with_undescore=0)
                pm.addAttr("eyelid_{}_control_default_ctrl".format(side),
                           ln="iris", type="float",
                           dv=0.0, min=0.0, max=1.0, k=1)
                pm.connectAttr("eyelid_{}_control_default_ctrl.iris".format(side),
                               "{}.{}".format(blend_shape_nd[0],e))

    def third_eyelid_rig(self):
        for e in self.THIRD_EYELID_JNTS:
            side = name.get_side(e, with_undescore=0)
            ctl = "eyelid_{}_control_default_ctrl".format(side)
            pm.addAttr(ctl,
                       ln="eyelid", type="float",
                       dv=0.0, min=0.0, max=1.0, k=1)
            pnodes.create_remap_val_node(input = "{}.eyelid".format(ctl),
                                           inputMin = 0,
                                           inputMax = 1,
                                           outputMin = 0,
                                           outputMax = 110,
                                           output = "{}.ry".format(e),
                                           name = "{}_thirdEyelidRot_{}_RMV".format("range",side))
    def throat_connections(self):
        if pm.objExists("throatBS_grp"):
            pm.addAttr("throatMain0_C_control_default_ctrl",
                       ln="contract", type="float",
                       dv=0.0, min=-1.0, max=1.0, k=1)
            static_mesh = pm.duplicate("{}Gums_C_001_high_geo".format(self.name),
                                       n="{}Gums_C_001_local_geo".format(self.name))[0]
            pm.parent(static_mesh,"no_transf_GRP")
            blend_shape_nd = pm.blendShape(pm.listRelatives("throatBS_grp"), static_mesh,
                                           frontOfChain=True,
                                           weight=(0, 1))
            pm.blendShape([static_mesh], "{}Gums_C_001_high_geo".format(self.name),
                                           frontOfChain=True,
                                           weight=(0, 1))
            for e in ("throatContraction_geo","throatExpansion_geo"):

                if "Contraction" in e:
                    input_max= -1
                    input_min = 0
                else:
                    input_max= 1
                    input_min = 0
                component = name.get_component(e, with_undescore=0)
                pnodes.create_remap_val_node(input="throatMain0_C_control_default_ctrl.contract",
                                             inputMin=input_min,
                                             inputMax=input_max,
                                             outputMin=0,
                                             outputMax=1,
                                             output="{}.{}".format(blend_shape_nd[0],e),
                                             name="{}_{}_RMV".format(component, "C"))

            pm.connectAttr("facial_BS.L_smile", "{}.L_gumSmile".format(blend_shape_nd[0]))
            pm.connectAttr("facial_BS.R_smile", "{}.R_gumSmile".format(blend_shape_nd[0]))
    def fake_lips_closing_collision(self):
        #connectiong the jaw to the fake lips collision
        fake_collision_shapes = ("C_fakeLipsCollision",
                                 "C_fakeLipsCollision0720",
                                 "C_fakeLipsCollision1720",
                                 "C_fakeLipsCollision1920")
        fake_collision_values = ((26.162,34.251),
                                 (8.151,34.512),
                                 (32.203,34.512),
                                 (34.236,34.512))
        for shape,values in zip(fake_collision_shapes,fake_collision_values):
            pnodes.create_remap_val_node(input="C_bnd_lowerJaw_1_0_faceJnt.rz",
                                         inputMin=-values[0],
                                         inputMax=-values[1],
                                         outputMin=0,
                                         outputMax=1,
                                         output="facial_BS.{}".format(shape),
                                         name="{}_{}_RMV".format(shape, "C"))