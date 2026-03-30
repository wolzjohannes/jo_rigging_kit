"""
www.pixomondo.com
Date: 22 / 03 / 2022

rivet controls
category : Rigging
subcategory : modules
author : Christof Puehringer / Junior Rigging TD

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import object
import pymel.core as pm
from ..base import module
from ..base import control
from ..utils import name
from ..utils import transform
from ..utils import joint
from ..utils import constraints
#reload(constraints)


class RivetControls(object):
    def __init__(self,
                 name="New",
                 scale=10.0,
                 moving_mesh=None,
                 dummies_rivet_grp=None,
                 create_controls=1,
                 seperate_hierarchy=1,
                 make_jnt=1,
                 base_module=None,
                 host=False,
                 controller_spaces=None):

        """
        class to rivet joints to the closest location to locators on mesh

        Args:

            scale(float):  The scale which will be applied to
                the module creation.

            moving_mesh(pyNode,str): The name of the mesh onto which the rivots are applied.

            dummies_rivet_grp(pyNode,str): group of all locators to be rivoted.

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

    def _build(self, args):
        self.name = args["name"]
        self.scale = args["scale"]
        self.moving_mesh = args["moving_mesh"]
        self.dummies_rivet_grp = args["dummies_rivet_grp"]
        self.create_controls = args["create_controls"]
        self.seperate_hierarchy = args["seperate_hierarchy"]
        self.make_jnt = args["make_jnt"]
        self.base_module = args["base_module"]
        self.host = args["host"]
        self.controller_spaces = args["controller_spaces"]

        #   internal attributes which are semi static
        self.suffix = 'jnt'
        self.follicleSuffix = 'rivFol'
        self.jointParent = None

        #   outputs that are available
        self.joint_output = list()

        #   checks and converts the mesh input
        if isinstance(self.moving_mesh, str):
            self.moving_mesh = pm.PyNode(self.moving_mesh)

        #   making the basic module for rivet
        self.module_base = module.Module(component="rivets{}".format(self.name),
                                         side="C",
                                         base_module=self.base_module)

        #   actual build of the system
        self._controls_builder()

    def _controls_builder(self):
        """

        Return:
            skinning_joints(list): list of PyNodes which can be used for further skinning
        """

        #   gets all transforms underneath the input of self.dummies_rivet_grp
        all_dummies_list = pm.listRelatives(self.dummies_rivet_grp, c= 1, type= "transform")
        self.rivet_nodes = []

        #   iterate over pymel objects
        for dummy_rivet in all_dummies_list:

            #   gets the side, naming and index from the dummy_rivet
            side = name.get_side(dummy_rivet, with_undescore=False)
            component = name.get_component(dummy_rivet, with_undescore=False)
            ind = name.get_index(dummy_rivet, with_undescore=False)

            #   rivets the on the surface
            rivet_node = self.rivet_on_face(dummy_rivet, side, component, ind)
            pm.parent(rivet_node, self.module_base.noTransf_grp)
            self.rivet_nodes.append(rivet_node)

            #   checks for bool input in self.create_controls and then chooses if control creation is needed
            if self.create_controls:
                fc_ctl = self.rivet_ctl_maker(dummy_rivet, side, component, ind)
                pm.matchTransform(fc_ctl.off, dummy_rivet)

                #   sort out if rivet has a space switch
                constraint_masters = rivet_node
                constraint_switch = False

                if self.controller_spaces:
                    constraint_masters = self.controller_spaces
                    constraint_masters.append(rivet_node[0])
                    constraint_switch = True

                constraints.pxoparent(masters=constraint_masters,
                                      slaves=fc_ctl.off,
                                      maintainOffset=True,
                                      native=False,
                                      host=self.host,
                                      space_switch=constraint_switch
                                      )

                self.jointParent = fc_ctl.ctl

            else:
                #   THIS MIGHT NEED A CHANGE, SINCE IT SEEMS A BIT DIRTY
                self.jointParent = rivet_node[0]

            if self.make_jnt:
                #   after the sorting out, self.jointParent takes over
                rivot_joint = joint.make_joint_on_element(self.jointParent,
                                                          suffix=self.suffix,
                                                          connect=0)

                #   freezing to avoid the flip
                pm.makeIdentity(rivot_joint,
                                apply=1, t=1,
                                r=1, s=0, n=0,
                                pn=1)

                #   checks for bool input in self.seperate_hierarchy and then creates the controlstructure for joints
                if self.seperate_hierarchy:
                    pm.parent(rivot_joint, self.module_base.joints_grp)

                    constraints.pxoparent(masters=self.jointParent,
                                          slaves=rivot_joint,
                                          native=True
                                          )

                else:
                    extra_buf = transform.make_extra_buffer(rivot_joint,
                                                            "maintainPos",
                                                            buffer_number=1,
                                                            move_to=1
                                                            )[0]
                    pm.parent(extra_buf, self.jointParent)

                self.joint_output.append(rivot_joint)

        return self.joint_output

    def rivet_on_face(self, dummy, side, component, index):
        """ uses pymel to get the uv position of closest faceCenter and then applies a nFollicle to it

        Args:

            dummy(PyNode): the object where the control will be snapped to
            side(str): extracted from the for loop
            component(str): extracted from the for loop
            index(str): extracted from the for loop

        Return:
            fol_transform(PyNode): transform node of the created Follicle
        """

        position = dummy.getTranslation(w=1)

        face_id_ah = self.moving_mesh.getShape().getClosestPoint(position, space='world')[1]

        pm.select(self.moving_mesh.name() + '.f[' + str(face_id_ah) + ']')

        fol = transform.attachToGeo()
        fol.v.set(1)

        fol_transform = pm.listRelatives(fol, p=1)
        pm.rename(fol_transform, '{}{}_{}_{}'.format((component+self.name),
                                                     index,
                                                     side,
                                                     self.follicleSuffix))

        return fol_transform

    def rivet_ctl_maker(self, dummy, side, component, index):
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
        riv_ctrl = control.Control(component='{}{}{}'.format(component,
                                                             self.name,
                                                             index),
                                   side=side,
                                   description= 'control',
                                   subdefinition="default",
                                   shape="cube",
                                   scale= self.scale,
                                   color_name="",
                                   move_to= dummy,
                                   lock_hide=["s",  "v"],
                                   parent = self.module_base.get_grps()["prim"])
        return riv_ctrl
