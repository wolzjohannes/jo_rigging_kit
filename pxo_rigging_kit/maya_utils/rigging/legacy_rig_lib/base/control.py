"""
www.pixomondo.com
Date: 25 / 01 / 2022

control module
category : Rigging
subcategory : base
author : Michele Trabona / Rigging TD

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

#   external libraries
from future import standard_library
standard_library.install_aliases()
from builtins import object
import pymel.core as pmc

#   internal libraries
from . import controlShapes
#reload(name)

main_control_attr = "rig_ctrl"


class Control(object):
    def __init__(self,
                 component = "",
                 side = "",
                 description = "control",
                 subdefinition = "default",
                 shape = "cube",
                 scale = 1.0,
                 color_index = -1,
                 color_name = "",
                 lock_hide = ["s","v"],
                 rot_order = 3,
                 move_to = "",
                 translate_to = "",
                 rotate_to = "",
                 parent = "",
                 no_offset = 0
                 ):

        local_args = locals()

        self.ctl = None
        self.off = None

        self._build(local_args)

    def _build(self, args):
        component = args["component"]
        side = args["side"]
        description = args["description"]
        subdefinition = args["subdefinition"]
        shape = args["shape"]
        scale = args["scale"]
        color_index = args["color_index"]
        color_name = args["color_name"]
        lock_hide = args["lock_hide"]
        rot_order = args["rot_order"]
        move_to = args["move_to"]
        translate_to = args["translate_to"]
        rotate_to = args["rotate_to"]
        parent = args["parent"]
        no_offset = args["no_offset"]

        #defining the control's color
        color_index = self._color_maker(side, color_index, color_name)

        #defining control and offset control names
        control_name, offset_name = self._name_maker (component, side, description, subdefinition)

        #check if the control name is unique
        self._check_unique_name(control_name)
        control = self._controlShape_maker( shape, control_name, color_index,scale)

        #setting up the attributes
        self._control_attributes_maker(control, rot_order, lock_hide)

        #adding the offset group if needed
        offset = self._control_offset_maker( control, offset_name, no_offset)

        #parenting the control
        self._parent_control(control, offset, parent, no_offset)

        #snapping the control
        self._match_control_transform(offset, translate_to, rotate_to, move_to)

        control.addAttr("isCtl", at="bool", dv=1)
        control.addAttr("PXM_export_animation", at="bool", dv=1)

        if pmc.objExists("rig_controllers_grp"):
            pmc.sets("rig_controllers_grp", add=control)

        elif pmc.objExists("controllers_set"):
            pmc.sets("controllers_set", add=control)

        else:
            pass

        self.ctl = control
        self.off = offset

    def _check_unique_name(self, control_name):
        check = pmc.ls(control_name)

        if check:
            pmc.error("the control name:{}, is not unique. The control will not be made.".format(control_name))

    def _color_maker (self,side, color_index, color_name):

        def_color_index = 22

        if color_name == "default":
            color_index = -1
        if color_name == "red":
            color_index = 13
        if color_name == "blue":
            color_index = 6
        if color_name == "lightblue":
            color_index = 18
        if color_name == "yellow":
            color_index = 22
        if color_name == "green":
            color_index = 26
        if color_name == "darkgreen":
            color_index = 7
        if color_name == "orange":
            color_index = 31
        if color_name == "lightOrange":
            color_index = 21
        if color_name == "pink":
            color_index = 20
        if color_name == "purple":
            color_index = 9

        if color_name == "secondary" and side == "L":
            color_index = 18
        if color_name == "secondary" and side == "R":
            color_index = 20
        if color_name == "secondary" and side != "R" and side != "L":
            color_index = 26

        if color_index < 0 or color_index >32:

            if side == "L" :
                color_index = 6
            elif side == "R":
                color_index = 13
            else:
                color_index = def_color_index

        return color_index


    def _name_maker (self,component, side, description, subdefinition):

        control_name = "{}_{}_{}_{}_ctrl".format(component,side,description,subdefinition)
        offset_name = "{}_{}_{}_{}_offsetCtrl".format(component,side,description,subdefinition)

        return [control_name, offset_name]

    def _controlShape_maker (self,shape, control_name,color_index,scale):
        #getting the shapes
        if shape == "" or shape == "circle": control = controlShapes.circle()
        elif shape == "circleX": control = controlShapes.circle(normal="x")
        elif shape == "circleY": control = controlShapes.circle(normal="y")
        elif shape == "circleZ": control = controlShapes.circle(normal="z")
        elif shape == "square": control = controlShapes.square()
        elif shape == "squareX": control = controlShapes.square(normal="x")
        elif shape == "squareY": control = controlShapes.square(normal="y")
        elif shape == "squareZ": control = controlShapes.square(normal="Z")
        elif shape == "cube": control = controlShapes.cube()
        elif shape == "locator": control = controlShapes.locator()
        elif shape == "triangleZ": control = controlShapes.triangleZ()
        elif shape == "triangleX": control = controlShapes.triangleX()
        elif shape == "doubleArrowMX": control = controlShapes.double_arrow_minimalX()
        elif shape == "doubleArrowMZ": control = controlShapes.double_arrow_minimalZ()
        elif shape == "V": control = controlShapes.V()
        elif shape == "S": control = controlShapes.S()
        elif shape == "drop": control = controlShapes.drop()
        elif shape == "simpleSphere": control = controlShapes.simpleSphere()



        else:
            pmc.error("the shape: {} is not registered.".format(shape))

        control = pmc.rename(control, control_name)
        #scaling the shape
        pmc.setAttr("{}.s".format(control), scale, scale, scale)
        pmc.makeIdentity(control, a = 1, s = 1)

        #colouring the shape
        for s in pmc.listRelatives(control, s = 1):
            pmc.setAttr("{}.ove".format(s), 1)
            pmc.setAttr("{}.ovc".format(s), color_index)

        return control

    def _control_attributes_maker (self,control, rot_ord, lock_hide):
        pmc.addAttr(control, ln= main_control_attr, dt="string")

        if "r" not in lock_hide:
            pmc.setAttr("{}.ro".format(control), rot_ord, k = 1)

        lock_hide_edit = []
        for a in lock_hide:
            if a == "t" or a == "r" or a == "s":
                for axe in ["x","y","z"]:
                    lock_hide_edit.append(a+axe)
            else:
                lock_hide_edit.append(a)
        for a in lock_hide_edit:
            pmc.setAttr("{}.{}".format(control, a), l = 1, k = 0, cb = 0)

    def _control_offset_maker (self, control, offset_name, no_offset):
        if no_offset:
            return None

        offset = pmc.group(em = 1, n = offset_name)
        pmc.parent(control, offset)

        return offset

    def _parent_control (self, control, offset, control_parent, no_offset):
        " Parenting either the control or the offset group under the parent"
        if not control_parent or not pmc.objExists(control_parent):
            return

        if no_offset:
            pmc.parent(control, control_parent)
        else:
            pmc.parent(offset, control_parent)

    def _match_control_transform(self, offset, translate_to, rotate_to, move_to):
        if not offset or not pmc.objExists(offset):
            return

        if translate_to and pmc.objExists(translate_to):
            pmc.delete(pmc.pointConstraint(translate_to, offset))

        if rotate_to and pmc.objExists(rotate_to):
            pmc.delete(pmc.orientConstraint(rotate_to, offset))

        if move_to and pmc.objExists(move_to):
            pmc.delete(pmc.parentConstraint(move_to, offset))