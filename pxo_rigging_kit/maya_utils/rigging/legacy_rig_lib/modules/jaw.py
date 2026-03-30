"""
www.pixomondo.com
Date: 02 / 02 / 2022

jaw module
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
from ..utils import transform
from ..utils import nodes as pnodes


class Jaw(object):
    def __init__(self,
                 jaw_start,
                 scale = 1,
                 oriz_limit = None,
                 vert_limit = None,
                 shift_value = None,
                 base_module = None              #TO CONNECT
                 ):
        """
        It builds the jaw module.

        Args:
            jaw_start(pm.PyNode(),str): The name og the main
                jaw joint.
            scale(float):  The scale which will be applied to
                the module creation.
            oriz_limit(float): The orizontal rotation limit
                for the jaw.
            vert_limit(float):  The vertical rotation limit
                for the jaw.
            shift_value(float):  The translation we wish to
                give to the jaw while rotating.
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
        jaw_start = args["jaw_start"]
        self.scale = args["scale"]
        oriz_limit = args["oriz_limit"]
        vert_limit = args["vert_limit"]
        shift_value = args["shift_value"]

        #getting the side
        self.side = name.get_side(jaw_start, with_undescore=0)
        #making the basic module
        self.module_base = module.Module(component="jaw",
                                         side=self.side)
        #making the control
        self.jaw_ctl = self._controls_builder(jaw = jaw_start,
                                oriz_limit= oriz_limit,
                                vert_limit = vert_limit)
        if not shift_value == None:
            self._make_shift_system(shift_value,vert_limit)
        #constraint the joint to the control                                #TO DO MATRIX CONSTRAINT
        pm.parentConstraint(self.jaw_ctl.ctl, pm.PyNode(jaw_start))

    def _controls_builder(self, jaw = None,
                         oriz_limit = None,
                         vert_limit = None,
                         ):

        main_ctl = control.Control(component="jaw",
                                   side=self.side,
                                   description="control",
                                   subdefinition="default",
                                   shape="cube",
                                   scale=self.scale,
                                   move_to=jaw,
                                   lock_hide=["s", "rx", "v", "t"],
                                   parent = self.module_base.get_grps()["prim"])
        if not oriz_limit == None:
            pm.transformLimits(main_ctl.ctl, ry=[-oriz_limit, oriz_limit], ery=[1, 1])
        if not vert_limit == None:
            pm.transformLimits(main_ctl.ctl, rz=[vert_limit, 0], erz=[1, 0])

        return main_ctl
    def _make_shift_system(self,shift_value,vert_limit):
        buf_shift_grp = transform.make_extra_buffer(self.jaw_ctl.ctl,
                                                    extra_name = "shift")[0]
        #adding attributes to the top module grp
        pm.addAttr(self.module_base.get_grps()["top"], ln="jawShift", type="float", dv=shift_value, k=1)
        remap_jaw_shift =pnodes.create_remap_val_node(input = "{}.rz".format(self.jaw_ctl.ctl),
                                       inputMin = 0,
                                       inputMax = vert_limit,
                                       outputMin = 0,
                                       outputMax = "{}.jawShift".format(self.module_base.get_grps()["top"].name()),
                                       output = "{}.tx".format(buf_shift_grp.name()),
                                       name = "{}Jaw{}RMV".format("shift",self.side))
        return remap_jaw_shift
    def get_ctrls (self):
        ctrls_dic = {"main" : self.jaw_ctl}

