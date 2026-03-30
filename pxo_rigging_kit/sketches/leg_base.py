from maya import cmds as cmds

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import object
import pymel.core as pm



"""
class RiggingModule(object):
    '''
        The order in which it will calculate is:
            Data from other Modules flows into this via self.input_edge.
            Inflowing Data is Modified by User Input and goes into self.calculation_edge.
            Calculated Data flows out via output_edge.

        To integrate it into our own system, only connect should be overwritten
    '''

    def __init__(self,
                 component="default",
                 side="C",
                 ):

        self._component = component
        self._side = side

        self.module_folder = cmds.group(n=f"{component}_{side}_module_GRP", em=True)
        self.control_grp = cmds.group(n=f"{component}_{side}_primaryControls_GRP", em=True, p=self.module_folder)
        self.secondary_grp = cmds.group(n=f"{component}_{side}_secondaryControls_GRP", em=True, p=self.module_folder)

        self.input_edge = cmds.group(n=f"{component}_{side}_input_GRP", em=True, p=self.module_folder)
        self.calculation_edge = cmds.group(n=f"{component}_{side}_calc_GRP", em=True, p=self.module_folder)
        # everything under this group should not be influenced by viewport actions, for example iks that would double.
        cmds.setAttr(f"{self.calculation_edge}.it", 0, lock=1)

        # under this folder there can be joints
        self.output_edge = cmds.group(n=f"{component}_{side}_output_GRP", em=True, p=self.module_folder)

        self.add_default_attrs()

        if not base_module == None:
            self.connect_to_base_module( base_module)
            self.parent_to_base_module( base_module)

    @property
    def component(self):
        _LOGGER.info("Get radius")
        return self._component

    @component.setter
    def component(self, value):
        _LOGGER.info("set component name")
        if not isinstance(value, str):
            raise TypeError("the component name always has to be of string")

        self._component = value

    @component.deleter
    def component(self):
        print("delete component name")

        del self._component

    def add_default(self, ):
        attrs_list = (
            ("primary_visibility", 1),
            ("secondary_visibility", 1),
            ("input_visibility", 1),
            ("calculation_visibility", 1),
            ("output_visibility", 1),
            )
        
        vis_off = ("extraElements_vis", "noTransf_vis", "joints_vis")

        for at in attrs_list:
            pm.addAttr(self.top_grp, ln=at, type="long", dv=1, min=0, max=10, k=1)

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
"""
from typing import Optional

for i in range(3):
    cmds.addAttr("leg_ik_MOD|input", ln=f"hip_input", at="matrix")
    cmds.addAttr("leg_ik_MOD|input", ln=f"bias", at="double", dv=0, minValue=-10, maxValue=10, hasMinValue=True,
                 hasMaxValue=True)
    cmds.addAttr(ln=f"contribution", at="double", dv=0, minValue=-10, maxValue=10, hasMinValue=True, hasMaxValue=True,
                 k=True)

cmds.addAttr("leg_ik_MOD|input", ln=f"root_{str(i).zfill(3)}", at="matrix")

for i in range(3):
    cmds.addAttr("leg_tweak_MOD|calc", ln=f"tweaker_ctl_mtx{str(i).zfill(3)}", at="matrix", )


def ten_to_one(from_node: Optional[str] = None, from_attr: Optional[str] = None) -> str:

    has_valid_attr = True

    # the 10 to one will always be created if and how we connect it, is the question
    node = cmds.createNode("math_Multiply", )
    return_attr = f"{node}.output"

    cmds.setAttr(f"{node}.input2", 0.1, l=True)

    if not from_node:
        print("no attr to connect to given")
        has_valid_node = False

    if not cmds.objExists(from_node):
        print("no attr to connect to given")
        has_valid_node = False

    if not from_attr:
        print("no attr to connect to given")
        has_valid_attr = False

    if not cmds.attributeQuery(from_attr, n=from_node, exists=True):
        print("no attr to connect to found")
        has_valid_attr = False

    if has_valid_attr:
        connected_items = cmds.listConnections(f"{from_node}.{from_attr}", source=True, destination=False)

    if connected_items:
        print(connected_items)

    return node



ten_to_one(from_node="pSphere1", from_attr="tx")


def to_index_name(index_num: int, fill_amount: int = 3) -> str:
    return str(index_num).zfill(fill_amount)


"""
# host_attrs
cmds.addAttr("HOST", ln=f"contribution", at="double", dv=0, minValue=-10, maxValue=10, hasMinValue=True, hasMaxValue=True, k=True)
cmds.addAttr("HOST", ln=f"ik_fk_blend", at="double", dv=0, minValue=-10, maxValue=10, hasMinValue=True, hasMaxValue=True, k=True)
cmds.addAttr("HOST", ln=f"pv_hip_to_foot", at="double", dv=0, minValue=-10, maxValue=10, hasMinValue=True, hasMaxValue=True, k=True)

for i in range(4):
    cmds.addAttr("HOST", ln=f"follow_rotation_{to_index_name(i)}", at="double", dv=0, minValue=0, maxValue=10, hasMinValue=True, hasMaxValue=True, k=True)

# ik_inputs
cmds.addAttr("leg_ik_MOD|input", ln=f"hip_input", at="matrix")
cmds.addAttr("leg_ik_MOD|input", ln=f"base_input", at="matrix")

cmds.addAttr("leg_ik_MOD|input", ln=f"bias", at="double", dv=0, minValue=-10, maxValue=10, hasMinValue=True, hasMaxValue=True)
cmds.addAttr("leg_ik_MOD|input", ln=f"stretch", at="double", dv=0, minValue=0, maxValue=10, hasMinValue=True, hasMaxValue=True)
cmds.addAttr("leg_ik_MOD|input", ln=f"contribution", at="double", dv=0, minValue=-10, maxValue=10, hasMinValue=True, hasMaxValue=True)
cmds.addAttr("leg_ik_MOD|input", ln=f"pv_hip_to_foot", at="double", dv=0, minValue=-10, maxValue=10, hasMinValue=True, hasMaxValue=True)

# ik_cals
cmds.addAttr("leg_ik_MOD|calc", ln=f"leg_tip_input", at="matrix")
# ik_output
# fk_inputs
for i in range(4):
    cmds.addAttr("leg_ik_MOD|output", ln=f"ik_matrix_{to_index_name(3)}", at="matrix")

# fk_inputs
for i in range(4):
    cmds.addAttr("leg_fk_MOD|input", ln=f"follow_rotation_{to_index_name(i)}", at="double", dv=0, minValue=0, maxValue=10, hasMinValue=True, hasMaxValue=True)

cmds.addAttr("leg_fk_MOD|input", ln=f"bias", at="double", dv=0, minValue=-10, maxValue=10, hasMinValue=True, hasMaxValue=True)
cmds.addAttr("leg_fk_MOD|input", ln=f"stretch", at="double", dv=0, minValue=0, maxValue=10, hasMinValue=True, hasMaxValue=True)
cmds.addAttr("leg_fk_MOD|input", ln=f"contribution", at="double", dv=0, minValue=-10, maxValue=10, hasMinValue=True, hasMaxValue=True)


# fk_outputs
for i in range(4):
    cmds.addAttr("leg_fk_MOD|output", ln=f"fk_control_world_mtx_{to_index_name(i)}", at="matrix")


# blend_inputs
for i in range(4):
    cmds.addAttr("leg_blend_MOD|input", ln=f"fk_control_world_mtx_{to_index_name(i)}", at="matrix")


for i in range(4):
    cmds.addAttr("leg_blend_MOD|input", ln=f"ik_control_world_mtx_{to_index_name(i)}", at="matrix")


for i in range(4):
    cmds.addAttr("leg_blend_MOD|input", ln=f"ik_fk_blend_value{to_index_name(i)}", at="double", dv=0, minValue=0, maxValue=10, hasMinValue=True, hasMaxValue=True)


for i in range(4):
    cmds.addAttr("leg_blend_MOD|output", ln=f"ik_fk_blend_matrix{to_index_name(3)}", at="matrix")


# tweaker_inputs
for i in range(4):
    cmds.addAttr("leg_tweak_MOD|input", ln=f"tweaker_base_matrix{to_index_name(3)}", at="matrix")
for i in range(4):
    cmds.addAttr("leg_tweak_MOD|calc", ln=f"tweaker_adjusted_matrix{to_index_name(3)}", at="matrix")


for i in range(4):
    cmds.addAttr("leg_tweak_MOD|output", ln=f"tweaker_modified_matrix{to_index_name(i)}", at="matrix")


for i in range(4):
    cmds.addAttr("leg_tweak_MOD|output", ln=f"tweaker_modified_matrix{to_index_name(i)}", at="matrix")


# footIK_inputs
for i in range(5):
    cmds.addAttr(f"foot_ik_MOD|input", ln=f"base_value_{to_index_name(i)}", at="matrix")
    
    cmds.addAttr(f"foot_ik_MOD|output", ln=f"ik_position_{to_index_name(i)}", at="matrix")
    
    cmds.connectAttr(f"footIk_{to_index_name(i)}_JNT.worldMatrix[0]", f"foot_ik_MOD|output.ik_position_{to_index_name(i)}")
    
# footFK_inputs
for i in range(5):
    
    cmds.addAttr(f"foot_fk_MOD|output", ln=f"fk_position_{to_index_name(i)}", at="matrix")
    cmds.connectAttr(f"footFk_{to_index_name(i)}_JNT.worldMatrix[0]", f"foot_fk_MOD|output.fk_position_{to_index_name(i)}")


# footBlend_inputs
for i in range(5):

    cmds.addAttr("foot_blend_MOD|input", ln=f"ik_matrix_{to_index_name(i)}", at="matrix")

    cmds.addAttr("foot_blend_MOD|input", ln=f"fk_matrix_{to_index_name(i)}", at="matrix")    

    cmds.addAttr("foot_blend_MOD|input", ln=f"blend_attr_{to_index_name(i)}", at="double", dv=0, minValue=0, maxValue=10, hasMinValue=True, hasMaxValue=True)
    
    cmds.addAttr("foot_blend_MOD|calc", ln=f"blend_attr_{to_index_name(i)}", at="double", dv=0, minValue=0, maxValue=1, hasMinValue=True, hasMaxValue=True)


    cmds.addAttr("foot_blend_MOD|calc", ln=f"ik_matrix_{to_index_name(i)}", at="matrix")

    cmds.addAttr("foot_blend_MOD|calc", ln=f"fk_matrix_{to_index_name(i)}", at="matrix")



    cmds.addAttr("foot_blend_MOD|output", ln=f"blended_matrix_{to_index_name(i)}", at="matrix")


# create nodes
for i in range(5):

    cmds.createNode("blendMatrix", n=f"fk_ik_blend{to_index_name(i)}_BMX")


# create connections
for i in range(5):

    cmds.connectAttr("HOST.ik_fk_blend", f"foot_blend_MOD|input.blend_attr_{to_index_name(i)}")
    
    multiplier_node = ten_to_one()
    
    cmds.connectAttr(f"foot_blend_MOD|input.blend_attr_{to_index_name(i)}", f"{multiplier_node}.input1",)

    cmds.connectAttr(f"{multiplier_node}.output", f"foot_blend_MOD|calc.blend_attr_{to_index_name(i)}")


    cmds.connectAttr(f"foot_ik_MOD|output.ik_position_{to_index_name(i)}", f"foot_blend_MOD|input.ik_matrix_{to_index_name(i)}")
    
    cmds.connectAttr(f"foot_fk_MOD|output.fk_position_{to_index_name(i)}", f"foot_blend_MOD|input.fk_matrix_{to_index_name(i)}")




    cmds.connectAttr(f"foot_blend_MOD|input.ik_matrix_{to_index_name(i)}", f"foot_blend_MOD|calc.ik_matrix_{to_index_name(i)}")

    cmds.connectAttr(f"foot_blend_MOD|input.fk_matrix_{to_index_name(i)}", f"foot_blend_MOD|calc.fk_matrix_{to_index_name(i)}")


    cmds.connectAttr(f"foot_blend_MOD|calc.blend_attr_{to_index_name(i)}", f"fk_ik_blend{to_index_name(i)}_BMX.target[0].weight")

    cmds.connectAttr(f"foot_blend_MOD|calc.fk_matrix_{to_index_name(i)}", f"fk_ik_blend{to_index_name(i)}_BMX.inputMatrix")

    cmds.connectAttr(f"foot_blend_MOD|calc.ik_matrix_{to_index_name(i)}", f"fk_ik_blend{to_index_name(i)}_BMX.target[0].targetMatrix")



    cmds.connectAttr(f"fk_ik_blend{to_index_name(i)}_BMX.outputMatrix", f"foot_blend_MOD|output.blended_matrix_{to_index_name(i)}")

    cmds.connectAttr(f"foot_blend_MOD|output.blended_matrix_{to_index_name(i)}", f"footBlended_{to_index_name(i)}_JNT.offsetParentMatrix")






"""