"""
www.pixomondo.com
Date: 22 / 03 / 2022

rivet controls
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
from ..utils import joint


class FreeControls(object):
    def __init__(self,
                 name="New",
                 scale=10.0,
                 elements_list=None,
                 create_controls=None,
                 make_jnt=1,
                 side=None,
                 seperate_hierarchy=0,
                 base_module=None,
                 ):
        """
        class to rivet joints to the closest location to locators on mesh

        Args:

            scale(float):  The scale which will be applied to
                the module creation.

            moving_mesh(pyNode,str): The name of the mesh onto which the rivots are applied.

            dummies_grp(pyNode,str): group of all locators to be rivoted.

            create_controls(bool): checks if controlcreation is wanted.
            seperate_hierarchy(bool): checks if joints should be put into seperate joint hierarchy.

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

        self.name = args["name"]

        self.scale = args["scale"]

        self.elements_list = args["elements_list"]

        self.create_controls = args["create_controls"]

        self.seperate_hierarchy = args["seperate_hierarchy"]

        self.make_jnt = args["make_jnt"]

        self.base_module = args["base_module"]
        self.side = args["side"]
        #   internal attributes which are semi static
        self.suffix = 'jnt'

        self.ctls_list = []
        self.joint_output = []

        if not self.side:
            self.side = "C"

        #   making the basic module for rivet
        self.module_base = module.Module(component=f"freeControls{self.name}",
                                         side=self.side,
                                         base_module=self.base_module)

        #   actual build of the system
        self._controls_builder()

    def _controls_builder(self):
        """

        Return:
            skinning_joints(list): list of PyNodes which can be used for further skinning
        """

        #   iterate over pymel objects
        for element in self.elements_list:

            #   gets the side, naming and index from the element
            side = name.get_side(element, with_undescore=False)
            component = name.get_component(element, with_undescore=False)
            ind = name.get_index(element, with_undescore=False)

            #   checks for bool input in self.create_controls and then chooses if control creation is needed
            if self.create_controls:
                fc_ctl = self.ctl_maker(element, side, component, ind)
                pm.matchTransform(fc_ctl.off, element)
                self.jointParent = fc_ctl.ctl

            if self.make_jnt:
                #   after the sorting out, self.jointParent takes over
                jnt = joint.make_joint_on_element(self.jointParent,
                                                  suffix=self.suffix,
                                                  connect=0)
                #   freezing to avoid the flip
                pm.makeIdentity(jnt,
                                apply=1, t=1,
                                r=1, s=0, n=0,
                                pn=1)

                #   checks for bool input in self.seperate_hierarchy and then creates the controlstructure for joints
                if self.seperate_hierarchy:
                    pm.parent(jnt, self.module_base.joints_grp)
                    pm.parentConstraint(self.jointParent, jnt)

                else:
                    extra_buf = transform.make_extra_buffer(jnt,
                                                            "maintainPos",
                                                            buffer_number=1,
                                                            move_to=1)[0]
                    pm.parent(extra_buf, self.jointParent)

                #   this seems like it is needed for the connection of module to the whole rig /
                self.joint_output.append(jnt)

    def ctl_maker(self, dummy, side, component, index):
        """ instances the control module and class to generate a control based on rivot

        Args:

            dummy(PyNode): the object where the control will be snapped to
            side(str): extracted from the for loop
            component(str): extracted from the for loop
            index(str): extracted from the for loop

        Return:
            riv_ctrl(class): created control object
        """

        # format(component, side, description, subdefinition)
        ctl = control.Control(component=f"{component}{self.name}{index}",
                              side=side,
                              description="control",
                              subdefinition="default",
                              shape="cube",
                              scale=self.scale,
                              color_name="",
                              move_to=dummy,
                              lock_hide=["v"],
                              parent=self.module_base.get_grps()["prim"])

        self.ctls_list.append(ctl)

        return ctl
