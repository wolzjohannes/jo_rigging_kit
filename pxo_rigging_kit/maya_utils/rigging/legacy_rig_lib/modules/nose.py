"""
www.pixomondo.com
Date: 07 / 02 / 2022

nose module
category : Rigging
subcategory : modules
author : Michele Trabona / Rigging TD

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from future import standard_library
standard_library.install_aliases()
from builtins import object
import pymel.core as pm
from ..base import module
from ..base import control
from ..utils import name
from ..base import cageCore


class Nose(object):
    def __init__(self,
                 start_jnt,
                 secondary_jnts,
                 scale = 10,
                 base_module =None
                 ):
        """
        It builds fk controls for the nose joints.

        Args:
            start_jnt(pm.PyNode(),str): The name og the main
                nose joint.
            secondary_jnts(pm.PyNode(),str,list): Secondary nose
                joints list (like nostrils exc...).
            scale(float):  The scale which will be applied to
                the module creation.
            base_module(instance): The instance of the main module
                class. It is used to connect the nose module to
                the main.
        Return:
            None.

        """
        local_args = locals()

        self._build(local_args)

    def _build(self,
               args):
        start_jnt = args["start_jnt"]
        self.scale = args["scale"]
        secondary_jnts = args["secondary_jnts"]
        base_module = args["base_module"]

        #making the basic module
        self.module_base = module.Module(component="nose",
                                         side="C",
                                         base_module = base_module)
        self.ctls = self._controls_builder(start_jnt = start_jnt,
                                           secondary_jnts = secondary_jnts)


    def _controls_builder(self,
                          start_jnt = None,
                         secondary_jnts = None
                         ):
        iter_list = [start_jnt] + secondary_jnts
        ctls_obj_list = []
        for jnt in iter_list:
            if isinstance(jnt, str):
                jnt = pm.PyNode(jnt)
            component_name = name.get_component(jnt.name(), with_undescore = 0)
            side = name.get_side(jnt.name(), with_undescore=0)
            shape = None
            parent = ""
            if side == "C":
                shape = "cube"
            else:
                parent = ctls_obj_list[0].ctl
                shape = "circleX"
            ctrl = control.Control(component=component_name,
                                   side= side,
                                   description="control",
                                   subdefinition="default",
                                   shape=shape,
                                   scale=self.scale,
                                   move_to=jnt,
                                   lock_hide=["s", "v", "t"],
                                   parent = parent)
            if parent == "":
                pm.parent(ctrl.off, self.module_base.get_grps()["prim"])
            # parenting the joint to the ctl                                      #TO DO matrix constraint
            pm.parentConstraint(ctrl.ctl,jnt)
            ctls_obj_list.append(ctrl)

        return ctls_obj_list

        def get_ctl_list(self):
            return self.ctls

    @staticmethod
    def build_cage():
        nose_cage_dic = {'main_name': u'nose_C_',
 'name_list': [[u'nose_C_0_start_default_faceJnt nose_C_0_end_default_faceJnt'],
               [u'nostril_L_0_start_default_faceJnt nostril_L_0_end_default_faceJnt'],
               [u'nostril_R_0_start_default_faceJnt nostril_R_0_end_default_faceJnt']],
 'parents_name': [u'unknown',
                  u'nose0_C_cageCtl_default_ctrl',
                  u'nose0_C_cageCtl_default_ctrl'],
 'positions_list': [[(2.220446049250313e-16,0.0,1.0,0.0,
                      0.0,1.0,0.0,0.0,
                      -1.0,0.0,2.220446049250313e-16,0.0,
                      0.0,0.0,0.0,1.0),
                     (2.220446049250313e-16,0.0,1.0,0.0,
                      0.0,1.0,0.0,0.0,
                      -1.0,0.0,2.220446049250313e-16,0.0,
                      0.0,0.0,5.0,1.0)],
                    [(0.447213595499958,0.0,0.894427190999916,0.0,
                      0.0,1.0,0.0,0.0,
                      -0.894427190999916,0.0,0.447213595499958,0.0,
                      1.0,0.0,1.0,1.0),
                     (0.4472135954999579,
                      0.0,
                      0.8944271909999159,
                      0.0,
                      0.0,
                      1.0,
                      0.0,
                      0.0,
                      -0.8944271909999159,
                      0.0,
                      0.4472135954999579,
                      0.0,
                      3.0,
                      0.0,
                      5.0,
                      1.0)],
                    [(0.4472135954999584,
                      6.162975822039155e-33,
                      -0.8944271909999156,
                      0.0,
                      1.0953573965284051e-16,
                      -1.0,
                      5.476786982642033e-17,
                      0.0,
                      -0.8944271909999156,
                      -1.2246467991473535e-16,
                      -0.44721359549995854,
                      0.0,
                      -1.0,
                      0.0,
                      1.0,
                      1.0),
                     (0.4472135954999584,
                      6.162975822039155e-33,
                      -0.8944271909999156,
                      0.0,
                      1.0953573965284051e-16,
                      -1.0,
                      5.476786982642033e-17,
                      0.0,
                      -0.8944271909999156,
                      -1.2246467991473535e-16,
                      -0.44721359549995854,
                      0.0,
                      -2.999999999999999,
                      -4.898587196589408e-16,
                      5.0,
                      1.0)]]}

        cageCore.Cage.build_cage_from_dict(nose_cage_dic)

    @staticmethod
    def extract_joints(cage_name):
        joints_chain = cageCore.Cage.joints_maker(cage_name)
        #fixing joint heararchy

        pm.parent(joints_chain[1][0],joints_chain[2][0],joints_chain[0][0])