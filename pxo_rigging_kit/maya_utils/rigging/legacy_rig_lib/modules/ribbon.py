"""
www.pixomondo.com
Date: 07 / 02 / 2022

nose module
category : Rigging
subcategory : modules
author : Christof Puehringer / Junior Rigging TD

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
#   external libraries
from builtins import dict
from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import range
from builtins import object
import pymel.core as pm

#   internal libraries
from ..base import module
from ..base import control

from ..utils import joint
from ..utils import name
from ..utils import constraints as pcons
from ..utils import transform
from ..utils import pixomath as pmath


class Ribbon(object):

    def __init__(self,
                 geometry_info=(),
                 placements=None,
                 scale=1,
                 side='C',
                 base_module=None,
                 component_name='ribbon',
                 native=True,
                 controller_spaces=[],
                 host=None):

        """
        builds a ribbon from created curve.

        Args:
            geometry_info():
            placements(tuple):
            scale(float):  The scale which will be applied to
                the module creation.
            base_module(instance): The instance of the main module
                class. It is used to connect the ribbon module to
                the main.

        Return:
            None.

        """
        #   information filled while building
        self.geos = list()

        self.prim_ctls = list()
        self.prim_offs = list()
        self.prim_jnts = list()

        self.ctls = dict()
        self.rivs = dict()
        self.fols = dict()

        #   inheritment from class super
        local_args = locals()
        self._build(local_args)

    #   alternate constructors of class
    @classmethod
    def from_surface(cls):
        local_args = locals()
        cls._build(local_args)
        return cls()

    @classmethod
    def from_geometry(cls):
        local_args = locals()
        cls._build(local_args)
        return cls()

    @classmethod
    def from_vtx_sel(cls):
        local_args = locals()
        cls._build(local_args)
        return cls()

    @classmethod
    def from_obj_sel(cls):
        local_args = locals()
        cls._build(local_args)
        return cls()

    #   methods to read out information from the ribbon
    def get_ctls(self):
        return self.ctls

    def get_rivs(self):
        return self.rivs

    def get_geos(self):
        return self.geos

    def get_fols(self):
        return self.fols

    @staticmethod
    def _decompose_name(object_name):
        """ decomposes the geometry name for further building process

        Args:
            object_name(str): the full name of the object

        Return:
            decomposed(list): [description, subdefinition, side, index]

        """

        side = name.get_side(object_name, with_undescore=False)
        index = name.get_index(object_name, with_undescore=False)

        component = name.get_component(object_name, with_undescore=False)
        description = name.get_description(object_name, with_undescore=False)
        subdefinition = name.get_subdefinition(object_name, with_undescore=False)

        decomposed = [component, description, subdefinition, side, index]

        return decomposed

    #   general control creation
    def _create_control(self,
                        ctl_name='controlName',
                        component='componentName',
                        side='sideName',
                        index='indexName',
                        scale=5.0,
                        placement='',
                        parent='prim'):

        """ instances the control module and class to generate a control based on rivot
        Args:
            placement(PyNode): the object where the control will be snapped to
            side(str): extracted from the for loop
            component(str): extracted from the for loop
            index(str): extracted from the for loop

        Return:
            riv_ctrl(class): created control object
        """
        component_name = '{}{}'.format(component, index)
        if ctl_name:
            component_name = '{}_{}{}'.format(ctl_name, component, index)

        riv_ctrl = control.Control(component=component_name,
                                   side=side,
                                   description='control',
                                   subdefinition='default',
                                   shape="cube",
                                   scale=scale,
                                   color_name="",
                                   move_to=placement,
                                   lock_hide=["v"],
                                   parent=self.module_base.get_grps()[parent])
        return riv_ctrl

    #   methods that work on the ribbon
    @staticmethod
    def _rivet_positions(amount, vposition=0.5):
        """ calculates uv position by lerping between zero and one
        Args:
            amount(int):
            vposition(float):

        Return:
            uv_info(list): returns a list of 2 lists u and v values

        """

        rivet_upositions = pmath.lerp_zero_one(amount)
        rivet_vpositions = [vposition] * amount

        uv_info = [rivet_upositions, rivet_vpositions]
        return uv_info

    @staticmethod
    def _create_follicles(geo=None, amount=None, uvpin=True):
        """ generates follicles based on input on the geometry specified

        Args:
            geo():
            amount(int):

        Return:
            follicles(list):

        """
        if not geo and amount:
            raise ValueError('method _create_follicles needs both geo and amount input')

        upos, vpos = Ribbon._rivet_positions(amount)

        follicles = list()
        if not uvpin:
            for i in range(0, amount):
                fol_decomp = (Ribbon._decompose_name(geo))
                fol_name = '{name}{amount}_{side}_{definition}_fol'.format(name=fol_decomp[0],
                                                                           amount=str(i).zfill(3),
                                                                           side=fol_decomp[3],
                                                                           definition=fol_decomp[2]
                                                                           )

                fol = transform.createFollicle(geo,
                                               uPos=upos[i],
                                               vPos=vpos[i],
                                               name=fol_name
                                               )

                follicles.append(pm.listRelatives(fol, p=1)[0])
        else:
            pin_node = pm.createNode('uvPin')

            pin_node.tangentAxis.set(0, lock=True)
            pin_node.normalAxis.set(2, lock=True)

            geo.worldSpace[0].connect(pin_node.deformedGeometry)

            for i in range(0, amount):
                fol_decomp = (Ribbon._decompose_name(geo))
                fol_name = '{name}{amount}_{side}_{definition}_fol'.format(name=fol_decomp[0],
                                                                           amount=str(i).zfill(3),
                                                                           side=fol_decomp[3],
                                                                           definition=fol_decomp[2]
                                                                           )

                transform_node = pm.createNode('transform', n=fol_name)
                transform_node.translate.set(lock=True)
                transform_node.rotate.set(lock=True)
                transform_node.scale.set(lock=True)
                follicles.append(transform_node)

                pin_node.rename('{name}{amount}_{side}_{definition}_uvp'.format(name=fol_decomp[0],
                                                                                amount=str(i).zfill(3),
                                                                                side=fol_decomp[3],
                                                                                definition=fol_decomp[2]
                                                                                )
                                )

                pin_node.coordinate[i].coordinateU.set(upos[i], lock=True)
                pin_node.coordinate[i].coordinateV.set(vpos[i], lock=True)
                pin_node.outputMatrix[i].connect(transform_node.offsetParentMatrix)

        return follicles

    #   basic build function
    def _build(self, args):
        """

        Args:
            args():

        Return:
            controls():

        """
        #   information gained from class inits
        self.geometry_info = args["geometry_info"]
        self.placements = args["placements"]
        self.scale = args["scale"]
        self.component_name = args['component_name']
        self.base_module = args["base_module"]
        self.controller_spaces = args["controller_spaces"]
        self.host = args["host"]
        self.side = args["side"]

        #   making the basic module
        self.module_base = module.Module(component=self.component_name,
                                         side=self.side,
                                         base_module=self.base_module
                                         )

        #   this part creates the ribbon controls
        #   generating the free controls
        if self.placements:
            if not isinstance(self.placements, tuple):
                self.placements = tuple(self.placements)

            for num, loc in enumerate(self.placements):
                if isinstance(loc, str):
                    loc = pm.PyNode(loc)

                control_name = (Ribbon._decompose_name(loc))
                ctl = self._create_control(ctl_name=control_name[0],
                                           component=control_name[2],
                                           side=control_name[3],
                                           index=control_name[4],
                                           placement=loc,
                                           parent='prim',
                                           scale=self.scale * 0.8
                                           )

                self.prim_ctls.append(ctl)
                self.prim_offs.append(ctl.off)

            for ctl in self.prim_ctls:
                jnt = joint.make_joint_on_element(ctl.ctl, 'jnt', connect=True)
                pm.parent(jnt, self.module_base.get_grps()['joints'])

                self.prim_jnts.append(jnt)

        #   generating the surface pinning
        if len(self.geometry_info) == 2 and not all([True if type(x) == tuple else False for x in self.geometry_info]):
            self.geometry_info = (self.geometry_info)

        for geo_amount_pair in self.geometry_info:
            geometry, amount = geo_amount_pair
            if isinstance(geometry, str):
                geometry = pm.PyNode(geometry)

            geo_shape = geometry.getShape()

            follicles = Ribbon._create_follicles(geo=geo_shape, amount=amount)
            pm.parent(follicles, self.module_base.get_grps()['noT'])

            self.geos.append(geometry)
            self.fols[geometry] = follicles

            #   generating the riveted controls
            if self.host:
                #   create attr for parentConstraint
                self.host.addAttr('Space_Information', at='enum', enumName='########', k=False)
                self.host.Space_Information.set(lock=True, cb=True)

        for geometry, follicles in list(self.fols.items()):

            ctls = list()
            for rev, fol in enumerate(follicles):

                control_name = (Ribbon._decompose_name(fol))
                print(control_name)
                ctl = self._create_control(ctl_name=None,
                                           component=control_name[0],
                                           side=control_name[1],
                                           index='',
                                           placement=fol,
                                           parent='second',
                                           scale=self.scale * 0.5
                                           )

                self.controller_spaces.append(fol)

                pcons.pxoparent(masters=self.controller_spaces,
                                slaves=ctl.off,
                                maintainOffset=True,
                                native=False,
                                space_switch=True,
                                host=self.host
                                )

                ctl.ctl.sx.set(keyable=False, channelBox=False)
                ctl.ctl.sy.set(keyable=False, channelBox=False)
                ctl.ctl.sz.set(keyable=False, channelBox=False)

                self.controller_spaces.pop(-1)

                ctls.append(ctl)

            self.ctls[geometry] = ctls

        #   generating the joints for the bind
        for geometry, ctls in list(self.ctls.items()):
            jnts = list()
            for ctl in ctls:
                jnt = joint.make_joint_on_element(ctl.ctl, 'jnt', connect=False)
                pm.parent(jnt, self.module_base.get_grps()['joints'])
                pcons.pxoparent(masters=ctl.ctl, slaves=jnt, maintainOffset=True, native=False)
                jnts.append(jnt)

                #   pout.color_outliner('ribbon', [ctl.ctl, ctl.off, jnt])

            self.rivs[geometry] = jnts

        pm.parent(self.geos, self.module_base.get_grps()['noT'])
        #   all



