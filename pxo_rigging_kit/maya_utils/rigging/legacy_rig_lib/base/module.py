"""
www.pixomondo.com
Date: 28 / 01 / 2022

module module
category : Rigging
subcategory : base
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
from ..utils import attributes


class Module(object):
    """
        class to build the module rig function
    """
    def __init__(self,
                 component="new",
                 side="",
                 base_module=None):

        self.component = component
        self.side = side
        self.top_grp = pm.group(n="{}_{}_module_GRP".format(component, side), em=True)
        self.control_grp = pm.group(n="{}_{}_primCtl_GRP".format(component, side), em=True, p=self.top_grp)
        self.secondary_grp = pm.group(n="{}_{}_secondCtl_GRP".format(component, side), em=True, p=self.top_grp)
        self.joints_grp = pm.group(n="{}_{}_joints_GRP".format(component, side), em=True, p=self.top_grp)
        self.extraElements_grp = pm.group(n="{}_{}_extraElements_GRP".format(component, side), em=True, p=self.top_grp)
        self.noTransf_grp = pm.group(n="{}_{}_noTransf_GRP".format(component, side), em=True, p=self.top_grp)

        # removing the inherit transform from the grp
        pm.setAttr("{}.it".format(self.noTransf_grp), 0, l=1)
        self.add_base_attrs()

        if not base_module == None:
            self.connect_to_base_module( base_module)
            self.parent_to_base_module( base_module)

    def add_base_attrs (self, connect = 1):
        attrs_list = ("primCtl_vis", "secondCtl_vis", "joints_vis", "extraElements_vis", "noTransf_vis")
        vis_off = ("extraElements_vis", "noTransf_vis", "joints_vis")
        for at in attrs_list:
            pm.addAttr(self.top_grp, ln=at, type="long", dv=1, min=0, max=1, k=1)
        if connect:
            children = pm.listRelatives(self.top_grp,ad = 1 , type = "transform")
            for c in children:
                for at in attrs_list:
                    if at.split("_")[0] in c.name():
                        pm.connectAttr("{}.{}".format(self.top_grp.name(),at), "{}.v".format(c), f =1)
                    if at in vis_off:
                        pm.setAttr("{}.{}".format(self.top_grp.name(),at),0)


    def get_grps (self):
        grps_dic = {"top" : self.top_grp,
                    "prim" : self.control_grp,
                    "second" : self.secondary_grp,
                    "joints" : self.joints_grp,
                    "extra" : self.extraElements_grp,
                    "noT" : self.noTransf_grp}
        return grps_dic
    def connect_to_base_module(self,base_module):

        at_name = "{}_{}_set".format(self.side,self.component)
        attributes.add_section(base_module.vis_ctl.ctl, at_name=at_name)
        prim_at_name = "{}_{}_prim_vis".format(self.side,self.component)
        second_at_name = "{}_{}_second_vis".format(self.side, self.component)

        pm.addAttr(base_module.vis_ctl.ctl, ln=prim_at_name, type="long", dv=1, min=0, max=1, k=False)
        pm.addAttr(base_module.vis_ctl.ctl, ln=second_at_name, type="long", dv=1, min=0, max=1, k=False)

        base_module.vis_ctl.ctl.attr(prim_at_name).set(channelBox=True)
        base_module.vis_ctl.ctl.attr(second_at_name).set(channelBox=True)

        pm.connectAttr("{}.{}".format(base_module.vis_ctl.ctl, prim_at_name),
                       "{}.primCtl_vis".format(self.top_grp))

        pm.connectAttr("{}.{}".format(base_module.vis_ctl.ctl, second_at_name),
                       "{}.secondCtl_vis".format(self.top_grp))

    def parent_to_base_module(self, base_module):
        pm.parent(self.top_grp,base_module.modules_grp)