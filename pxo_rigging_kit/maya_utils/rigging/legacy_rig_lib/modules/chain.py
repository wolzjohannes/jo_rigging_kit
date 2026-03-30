"""
www.pixomondo.com
Date: 21 / 03 / 2022

tweaker module
category : Rigging
subcategory : modules
author : Christos Orfanidis / Junior Rigging Artist

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import object
from ..base import module
from ..base import control
from ..utils import name
from ..utils import joint


class Chain(object):
    def __init__(self,
                 scale = 1.0,
                 specific_name = "new",
                 start_joint = None,
                 base_module = None
                 ):
        """
        It builds the joint chain module.

        Args:

            scale(10):  The scale which will be applied to
                the module creation.
            specific_name (str): specific chain name.
            start_joint(pyNode,str): The name the start joint of the
            chain.
            base_module(instance): The instance of the main module
                class. It is used to connect the chain module to
                the main.
        Return:
            None.

        """

        local_args = locals()

        self._build(local_args)

    def _build(self,
               args):
        self.scale = args["scale"]
        self.specific_name = args["specific_name"]
        self.start_joint = args["start_joint"]
        self.base_module = args["base_module"]

        #getting side
        self.side = name.get_side(self.start_joint, with_undescore=0)

        #making the basic module
        self.module_base = module.Module(component="chain{}".format(self.specific_name),
                                         side=self.side,
                                         base_module=self.base_module)

        self._controls_builder()

    def _controls_builder(self):
        joints_list = joint.get_joint_chain(self.start_joint)
        ctls_chain = []
        for it, jnt in enumerate(joints_list):
            parent = ""
            if len(ctls_chain) > 0:
                parent = ctls_chain[-1].ctl
            component= name.get_component(jnt.name(), with_undescore=0)
            chain_control = control.Control(component ="{}{}".format(component, it),
                                            side = self.side,
                                            shape = "cube",
                                            scale = self.scale,
                                            color_index = -1,
                                            color_name = "",
                                            lock_hide = ["s","v"],
                                            rot_order = 3,
                                            move_to = jnt,
                                            translate_to = "",
                                            rotate_to = "",
                                            parent = parent,
                                            no_offset = 0)
            ctls_chain.append(chain_control)

            #FOR each joint make a control wich is parented to the previous create control.
