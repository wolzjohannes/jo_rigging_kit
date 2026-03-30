"""
www.pixomondo.com
Date: 04 / 02 / 2022

eye module
category : Rigging
subcategory : modules
author : Michele Trabona / Rigging TD

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
from builtins import object
from pymel.core import datatypes
import pymel.core as pm
from ..base import module
from ..base import control
from ..utils import name
from ..utils import transform
from ..base import cageCore


standard_library.install_aliases()

class Eye(object):
    def __init__(self,
                 eye_start,
                 scale=1,
                 aim_shift_mult=1,
                 base_module=None,
                 side=None
                 ):

        local_args = locals()

        self.side = side
        self._build(local_args)

    def _build(self,
               args):
        eye_start = args["eye_start"]
        self.scale = args["scale"]
        aim_shift_mult = args["aim_shift_mult"]
        base_module = args["base_module"]
        # getting the side
        if not self.side:
            self.side = name.get_side(eye_start, with_undescore=False)

        # making the basic module
        self.module_base = module.Module(component="eye",
                                         side=self.side,
                                         base_module=base_module
                                         )

        ctls = self._controls_builder(eye=eye_start,
                                      aim_shift_mult=aim_shift_mult
                                      )

        # parenting the joint to the ctl                                      #TO DO matrix constraint
        pm.parentConstraint(ctls[0].ctl, pm.PyNode(eye_start))

    def _controls_builder(self,
                          eye=None,
                          aim_shift_mult=None
                          ):

        fk_ctl = control.Control(component="eyeFK",
                                 side=self.side,
                                 description="control",
                                 subdefinition="default",
                                 color_name= "secondary",
                                 shape="cube",
                                 scale=self.scale,
                                 move_to=eye,
                                 lock_hide=["s", "v", "t"],
                                 parent=self.module_base.get_grps()["prim"]
                                 )

        aim_buffer = transform.make_extra_buffer(fk_ctl.ctl, extra_name="aim")[0]
        aim_ctl = control.Control(component="eye",
                                  side=self.side,
                                  description="control",
                                  subdefinition="default",
                                  shape="circleX",
                                  scale=self.scale,
                                  move_to=eye,
                                  lock_hide=["s", "r", "v"],
                                  parent = self.module_base.get_grps()["prim"]
                                  )

        # shifting the eye ctl position
        if isinstance(eye, str):
            eye = pm.PyNode(eye)

        end_jnt = pm.PyNode(pm.listRelatives(eye, ad=1, type="joint")[0])
        vector = end_jnt.getTranslation(ws=1) - eye.getTranslation(ws=1)
        new_translate = aim_ctl.off.getTranslation(ws=1) + (vector * aim_shift_mult)
        aim_ctl.off.setTranslation(new_translate, ws=1)

        # setting up the up object

        # TO DO ADD ANOTHER TARGET IN WS DIRECTION TO HAVE A SMOOTH SWITCH

        up_obj = pm.spaceLocator(n = "eyeUpVector_{}_LOC".format(self.side) )
        pm.delete(pm.parentConstraint(eye,up_obj))
        pm.parent(up_obj,eye)
        up_obj.ty.set(1)
        pm.parent(up_obj,self.module_base.get_grps()["extra"])
        # aim vector definement
        aim_vector = [1, 0, 0]
        if self.side == "R":
            aim_vector = [-1,0,0]
        aim_constraint_fk = pm.aimConstraint(aim_ctl.ctl,
                                             aim_buffer,
                                             weight=1,
                                             aimVector=aim_vector,
                                             upVector=[0, 1, 0],
                                             worldUpType="object",
                                             worldUpObject=up_obj
                                             )
        pm.addAttr(fk_ctl.ctl, ln="aimFollow", type = "float",dv = 1.0, min = 0.0,max = 1.0, k = 1)
        # connect the follow attribute to the constraint
        pm.connectAttr("{}.aimFollow".format(fk_ctl.ctl.name()),
                       "{}.{}W0".format(aim_constraint_fk.name(), aim_ctl.ctl.name()),f =1)

        return [fk_ctl,aim_ctl]

    @staticmethod
    def build_cage():
        eye_cage_dic = {
            'main_name': u'eye_L_',
            'name_list': [[u'eye_L_0_start_default_faceJnt eye_L_0_end_default_faceJnt']],
            'parents_name': ['unknown'],
            'positions_list': [[(2.10942374679e-15, 0.0, 1.0, 0.0,
                                 0.0, 1.0, 0.0, 0.0,
                                 -1.0, 0.0, 2.10942374679e-15, 0.0,
                                 0.0, 0.0, 0.0, 1.0
                                 ),
                                (2.10942374679e-15, 0.0, 1.0, 0.0,
                                 0.0, 1.0, 0.0, 0.0,
                                 -1.0, 0.0, 2.10942374679e-15, 0.0,
                                 -7.54951656745e-15, -9.26275251002e-16, 4.0, 1.0
                                 )
                                ]
                               ]
        }

        cageCore.Cage.build_cage_from_dict(eye_cage_dic)


    @staticmethod
    def extract_joints(cage_name):
        joints_chain = cageCore.Cage.joints_maker(cage_name)
