"""
www.pixomondo.com
Date: 01 / 02 / 2022

baseModule module
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
from builtins import zip
from builtins import object
import pymel.core as pm
from ..base import control
from ..utils import constraints


class Base_module(object):
    """
    class to build the main rig structure
    """

    def __init__(self,
                 character_name="new",
                 scale=1.0,
                 snap_ctls_element=None,
                 type="body"):
        """
        It creates the base module for the new rig.

        Args:
            character_name(str): The name we will use for the
                naming of the module.
            scale(float): A float value that changes the controls
                scale and proportions.
            snap_ctls_element(str): Where we want to snap the
                visibility control and toggle control.

        Return:
            None.

        """
        if type == "body":
            type = "rig"
        else:
            type = "{}Rig".format(type)

        #   top group
        self.top_group = pm.group(n="{}_{}_GRP".format(character_name, type), em=True)

        character_name_at = "characterName"
        scene_object_type_at = 'sceneObjectType'
        scene_object_type = "rig"

        for at in [character_name_at, scene_object_type_at]:
            pm.addAttr(self.top_group, ln=at, dt="string")
        #   setting up attributes

        pm.setAttr("{}.{}".format(self.top_group,character_name_at),
                   character_name,
                   type="string",
                   l=True
                   )

        pm.setAttr("{}.{}".format(self.top_group, scene_object_type_at),
                   scene_object_type,
                   type="string",
                   l=True
                   )

        #   make global control
        self.global_ctl = control.Control(component="global",
                                          side="C",
                                          description="control",
                                          subdefinition="default",
                                          shape="circleY",
                                          scale=scale * 10,
                                          lock_hide=["v", "r"],
                                          parent=self.top_group,
                                          no_offset=1
                                          )

        self.main_ctl = control.Control(component="main",
                                        side="C",
                                        description="control",
                                        subdefinition="default",
                                        shape="circleY",
                                        color_name="secondary",
                                        scale=scale * 9,
                                        lock_hide=["v", "s"],
                                        parent=self.global_ctl.ctl,
                                        no_offset=1
                                        )

        pm.connectAttr("{}.sx".format(self.global_ctl.ctl), "{}.sz".format(self.global_ctl.ctl), f=True)
        pm.connectAttr("{}.sx".format(self.global_ctl.ctl), "{}.sy".format(self.global_ctl.ctl), f=True)
        pm.setAttr("{}.sz".format(self.global_ctl.ctl), k=False)
        pm.setAttr("{}.sy".format(self.global_ctl.ctl), k=False)

        #   connect top grp to global and main
        pm.connectAttr("{}.message".format(self.top_group),
                       "{}.rig_ctrl".format(self.global_ctl.ctl), f=True)

        pm.connectAttr("{}.message".format(self.top_group),
                       "{}.rig_ctrl".format(self.main_ctl.ctl), f=True)

        #   model_group
        self.model_grp = pm.group(n="model_GRP", em=True, p=self.top_group)
        self.fast_model_grp = pm.group(n="fast_model_GRP", em=True, p=self.model_grp)
        self.medium_model_grp = pm.group(n="medium_model_GRP", em=True, p=self.model_grp)
        self.slow_model_grp = pm.group(n="slow_model_GRP", em=True, p=self.model_grp)
        self.all_model_grp = pm.group(n="all_model_GRP", em=True, p=self.model_grp)
        self.rig_model_grp = pm.group(n="rig_model_GRP", em=True, p=self.model_grp)

        #   att
        pm.addAttr(self.slow_model_grp, ln="parent_connection", dt="string")
        pm.connectAttr("{}.message".format(self.top_group),
                       "{}.parent_connection".format(self.slow_model_grp), f=True)

        pm.hide(self.rig_model_grp)

        #   other groups
        self.skeleton_grp = pm.group(n="skeleton_GRP", em=True, p=self.main_ctl.ctl)
        self.modules_grp = pm.group(n="modules_GRP", em=True, p=self.main_ctl.ctl)
        self.rig_ctrl_grp = pm.group(n="rig_ctrl_GRP", em=True, p=self.main_ctl.ctl)
        self.no_transf_grp = pm.group(n="no_transf_GRP", em=True, p=self.main_ctl.ctl)
        pm.setAttr("{}.it".format(self.no_transf_grp.name()), 0,  l=True)
        pm.hide(self.no_transf_grp)

        #   world scale
        self.scale_locator = pm.spaceLocator(n="scale_LOC")
        self.scale_locator.inheritsTransform.set(0)
        self.scale_locator.v.set(0)

        pm.connectAttr("{}.sx".format(self.global_ctl.ctl), "{}.sx".format(self.scale_locator), f=True)
        pm.connectAttr("{}.sx".format(self.global_ctl.ctl), "{}.sy".format(self.scale_locator), f=True)
        pm.connectAttr("{}.sx".format(self.global_ctl.ctl), "{}.sz".format(self.scale_locator), f=True)
        pm.parent(self.scale_locator, self.top_group)

        #   adding settings ctrl               #TO DO
        #   adding visibility ctrl
        self.vis_ctl = control.Control(component="vis",
                                       side="C",
                                       description="control",
                                       subdefinition="default",
                                       shape="V",
                                       scale=scale,
                                       lock_hide=["v", "s", "t", "r"],
                                       parent=self.main_ctl.ctl,
                                       no_offset=0
                                       )

        if snap_ctls_element is not None:
            if isinstance(snap_ctls_element, str):
                snap_ctls_element = pm.PyNode(snap_ctls_element)

            constraints.pxoparent(masters=snap_ctls_element,
                                  slaves=self.vis_ctl.off,
                                  maintainOffset=False
                                  )

            # pm.parentConstraint(snap_ctls_element,self.vis_ctl.off, mo = 0)

        main_vis_at_list = ['modelVis', 'jointsVis']
        main_disp_at_list = ['modelDisp', 'jointsDisp']
        main_obj_list = [self.model_grp, self.skeleton_grp]
        main_obj_vis_df_list = [1, 0]

        # add rig visibility connections
        for at, obj, df_val in zip(main_vis_at_list, main_obj_list, main_obj_vis_df_list):
            pm.addAttr(self.vis_ctl.ctl, ln=at, at='enum', enumName='off:on', k=1, dv=df_val)
            pm.setAttr("{}.{}".format(self.vis_ctl.ctl, at), cb=1)
            pm.connectAttr("{}.{}".format(self.vis_ctl.ctl, at), "{}.v".format(obj))

        # add rig display type connections
        for at, obj in zip(main_disp_at_list, main_obj_list):
            pm.addAttr(self.vis_ctl.ctl, ln=at, at='enum', enumName='normal:template:reference', k=1, dv=2)
            pm.setAttr("{}.{}".format(self.vis_ctl.ctl, at), cb=1)
            pm.setAttr("{}.ove".format(obj), 1)
            pm.connectAttr("{}.{}".format(self.vis_ctl.ctl, at), "{}.ovdt".format(obj))

        # add rig display level connection
        displayLevel = 'displayLevel'
        levelGrp = [self.fast_model_grp, self.medium_model_grp, self.slow_model_grp]
        pm.addAttr(self.vis_ctl.ctl, ln=displayLevel, at='enum', enumName='fast:medium:slow', k=1, dv=1)
        pm.setAttr("{}.{}".format(self.vis_ctl.ctl, displayLevel), cb=1)

        #   to do fast medium slow modes connection
