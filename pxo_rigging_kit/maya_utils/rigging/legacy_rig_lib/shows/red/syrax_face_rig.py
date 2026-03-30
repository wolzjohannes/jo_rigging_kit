"""
www.pixomondo.com
Date: 05 / 03 / 2022

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
from ...utils import pixoSkin
import pymel.core as pm


class Syrax_face_rig(facialSystem.Facial_system):
    FREECTLS_JNTS = ("eyeOrbicularis_R_0_start_default_faceJnt",
                     "eyeOrbicularis_L_0_start_default_faceJnt",
                     "throat_C_0_start_default_faceJnt")
    ORBICULARIS_PARENT = "C_bnd_upperJaw_0_0_faceJnt"
    THIRD_EYELID_JNTS = ("eyelidThird_R_0_start_default_localJnt",
                         "eyelidThird_L_0_start_default_localJnt")

    def __init__(self):
        self.name = "syrax"
        rig_path = data.get_rigging_main_dir(type="face")
        model_path = "X:/redgun_reg-6344/_library/assets/creature/crt_syrax/mdl/_publish/reg_crt_syrax_mdl_v087_ial.mb"
        super(Syrax_face_rig, self).__init__(character_name=self.name,
                                             rig_data_path=rig_path,
                                             model_path=model_path,
                                             builder_path=None,
                                             root_jnt="C_bnd_neck_0_0_jnt",
                                             head_jnt="C_bnd_head_0_0_jnt",
                                             scale=10,
                                             pre_build=self.syrax_face_pre_build,
                                             upgrade=self.syrax_face_upgrade,
                                             post_build=self.syrax_face_post_build)

    def syrax_face_pre_build(self):

        global_elements = ["{}EyefluidLower_C_001_high_geo".format(self.name),
                           "{}EyefluidUpper_C_001_high_geo".format(self.name),
                           "{}Iris_C_001_high_geo".format(self.name),
                           "{}Cornea_C_001_high_geo".format(self.name),
                           "{}Pupil_C_001_high_geo".format(self.name),
                           "{}Lid_C_001_high_geo".format(self.name)]

        for element in global_elements:
            element = pm.PyNode(element)
            element_dup = pm.duplicate(element,
                                       n=element.name().replace("_high_",
                                                                "_local_"))[0]
            pm.parent([element_dup], "no_transf_GRP")
            pm.blendShape([element_dup], element, frontOfChain=True, weight=(0, 1))

    def syrax_face_upgrade(self):
        self.eye_orbicularis_ctl()

    def syrax_face_post_build(self):

        elements_to_delete = ['low',
                              'sliced',
                              'syraxMuscles_all_high_grp',
                              'syraxSkeleton_all_high_grp',
                              'syraxClaws_C_001_high_grp',
                              'syraxBody_C_001_high_grp',
                              'syraxWingSimProxy_all_high_grp']
        for e in elements_to_delete:
            try:
                pm.delete(e)
            except:
                pass
        self.eye_in_shift()
        self.iris_connections()
        self.third_eyelid_rig()
        self.throat_connections()
        #turning off face modules visibility
        pm.setAttr("vis_C_control_default_ctrl.C_freeControlsMain_prim_vis",0)
        pm.setAttr("vis_C_control_default_ctrl.C_tweakersFace_prim_vis",0)
        # importing the tweaker skinning
        main_path = data.get_rigging_main_dir(type="face")
        path = r"{}/data/skincluster".format(main_path)
        pixoSkin.pixo_import_skin(path, geo_list=["face_tweaker_geo"])



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
                pm.parentConstraint('C_bnd_head_0_0_faceJnt', ctl.off, mo =1)
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
            """
            #eyelid correctives
            blend_shape_nd = pm.blendShape(pm.listRelatives("thirdEyelid_shapes_grp"),
                                           "{}Lid_C_001_local_geo".format(self.name),
                                           frontOfChain=True,
                                           weight=(0, 1))[0]
            for bs_shape in pm.listRelatives("thirdEyelid_shapes_grp"):
                side = bs_shape.name()[0]
                jnt_name = "eyelidThird_{}_0_start_default_localJnt".format(side)
                if "half" in bs_shape.name():
                    pnodes.create_remap_val_node(input="{}.ry".format(jnt_name),
                                                 inputMin=0,
                                                 inputMax=50.662,
                                                 outputMin=0,
                                                 outputMax=1,
                                                 output="{}.{}".format(blend_shape_nd,bs_shape),
                                                 name="{}_thirdEyelidHalfRot_{}_RMV".format("range", side))
                else:
                    pnodes.create_remap_val_node(input="{}.ry".format(jnt_name),
                                                 inputMin=50.662,
                                                 inputMax=110,
                                                 outputMin=0,
                                                 outputMax=1,
                                                 output="{}.{}".format(blend_shape_nd,bs_shape),
                                                 name="{}_thirdEyelidFullRot_{}_RMV".format("range", side))
                """
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
            for e in pm.listRelatives("throatBS_grp"):

                if "Contraction" in e.name():
                    input_max= -1
                    input_min = 0
                else:
                    input_max= 1
                    input_min = 0
                component = name.get_component(e.name(), with_undescore=0)
                pnodes.create_remap_val_node(input="throatMain0_C_control_default_ctrl.contract",
                                             inputMin=input_min,
                                             inputMax=input_max,
                                             outputMin=0,
                                             outputMax=1,
                                             output="{}.{}".format(blend_shape_nd[0],e),
                                             name="{}_{}_RMV".format(component, "C"))
