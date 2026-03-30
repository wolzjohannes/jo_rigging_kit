# Import third-party modules
import pymel.core as pmc


def set_channels_to_default(dag_transform_node, channel_names=("translate", "rotate", "scale", "jointOrient")):
    for attr_axis_ in "XYZ":
        for attr_channel_ in channel_names:
            attr_name_ = "{0}{1}".format(attr_channel_, attr_axis_)

            if attr_channel_ != "scale":
                dag_transform_node.attr(attr_name_).set(0)
            else:
                dag_transform_node.attr(attr_name_).set(1)


for ctl in pmc.selected():
    mtx_const = ctl.worldMatrix.listConnections()[0]
    jnt = mtx_const.listConnections(source=False, destination=True)[0]

    ctl_parent = ctl.getParent()
    jnt_parent = jnt.getParent()

    # control operations
    pmc.delete(mtx_const)
    ctl.attr("matrix").connect(jnt.offsetParentMatrix)

    # joint operations
    for attr_axis_ in "XYZ":
        for attr_channel_ in ("translate", "rotate", "scale"):
            attr_name_ = "{0}{1}".format(attr_channel_, attr_axis_)
            jnt_parent.attr(attr_name_).set(jnt.attr(attr_name_).get())

            if attr_channel_ != "scale":
                jnt.attr(attr_name_).set(0)
            else:
                jnt.attr(attr_name_).set(1)

        jo_name_ = "{0}{1}".format("jointOrient", attr_axis_)
        ro_name_ = "{0}{1}".format("rotate", attr_axis_)

        rotation_value = jnt.attr(jo_name_).get() + jnt_parent.attr(ro_name_).get()

        jnt_parent.attr(ro_name_).set(rotation_value)
        jnt.attr(jo_name_).set(0)

    parent_matrix = ctl_parent.worldMatrix.get()

    offset_comp = pmc.createNode("math_MultiplyMatrix")
    offset_comp.input1.set(parent_matrix)
    ctl.attr("matrix").connect(offset_comp.input2)
    offset_comp.output.connect(jnt.offsetParentMatrix, f=True)

    set_channels_to_default(jnt, channel_names=("translate", "rotate", "scale", "jointOrient"))
    jnt.setParent(world=True)
    set_channels_to_default(jnt, channel_names=("translate", "rotate", "scale", "jointOrient"))

for i in pmc.selected():
    mtx_mult = i.attr("matrix").listConnections()[0]

    mtx_input_values = mtx_mult.input1.get()
    mtx_mult.input2.disconnect()
    mtx_mult.input2.set(mtx_input_values)

    i.attr("matrix").connect(mtx_mult.input1)