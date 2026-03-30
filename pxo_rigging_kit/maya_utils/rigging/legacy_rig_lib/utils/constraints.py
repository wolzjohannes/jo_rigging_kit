"""
www.pixomondo.com
Date: 02 / 02 / 2022

constraints module
category : Rigging
subcategory : utils
author : Michele Trabona / Rigging TD

"""
from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import str
import pymel.core as pm
from . import name


def connection_tag(
    object, tag_method, parent_name, master_bshp="", bshp_topology_check=True
):  # TO DO check and chenge the attribute if it is there
    # TO DO add more than one constraint possibility on the
    # same attribute
    """
    It is going to add a connection tag

    Args:
        object(pm.PyNode(),str): The object on which we will add the
        attribute.
        tag_method(str): It can be expanded but it will be
        working with different methods:
                        pConstraint : parent constraint.
                        ptConstraint : point constraint.
                        oConstraint : orient constraint.
                        sConstraint : scale constraint.
                        tConnection : translate connection.
                        rConnection : rotate connection.
                        sConnection : scale connection.
                        bsConnection : blendShape connection.

        parent_name(pm.PyNode(),str): The object from which the object will
        get the connection.

    Return:
        None.

    """

    if isinstance(object, str):
        object = pm.PyNode(object)
    if not isinstance(parent_name, str):
        parent_name = parent_name.name()
    if not pm.objExists(object):
        return
    if tag_method and parent_name:
        remove_connection_tag(object)
        for at in ["connection_tag", "connection_parent", "master_bshp"]:
            pm.addAttr(object, ln=at, dt="string")
        object.addAttr("bshp_topology_check", type="bool")
        # setting up attributes
        pm.setAttr(
            "{}.connection_tag".format(object), tag_method, type="string", l=1
        )
        pm.setAttr(
            "{}.connection_parent".format(object),
            parent_name,
            type="string",
            l=1,
        )
        object.master_bshp.set(master_bshp)
        object.bshp_topology_check.set(bshp_topology_check)



def connect_by_tag(objects):
    """
    Connects elements reading their connection tag

    Args:
        objects(pm.PyNode()/str/list): The elements/element
        we need to connect.
    Return:
        None if fail. True if successfully.

    """

    if not isinstance(objects, list):
        objects = [objects]
    for obj in objects:
        if isinstance(obj, str):
            obj = pm.PyNode(obj)
        if obj.hasAttr("connection_tag") and obj.hasAttr("connection_parent"):
            connection_parent_name = obj.connection_parent.get()
            if not pm.objExists(connection_parent_name):
                pm.warning(
                    "{} not exist. Can not connect to {}".format(
                        connection_parent_name, obj.name(int=None)
                    )
                )
                continue
            connection_tag_attr = obj.connection_tag.get()
            connection_parent = pm.PyNode(connection_parent_name)

            if "," in connection_tag_attr:
                connection_tags = connection_tag_attr.split(",")
            else:
                connection_tags = [connection_tag_attr]
            for connection_tag in connection_tags:
                if connection_tag == "pConstraint":
                    pm.parentConstraint(connection_parent, obj, mo=0)
                if connection_tag == "ptConstraint":
                    pm.pointConstraint(connection_parent, obj, mo=0)
                if connection_tag == "oConstraint":
                    pm.orientConstraint(connection_parent, obj, mo=0)
                if connection_tag == "sConstraint":
                    pm.scaleConstraint(connection_parent, obj, mo=0)
                if connection_tag == "tConnection":
                    obj.t.set(l=False)
                    pm.connectAttr(connection_parent.t, obj.t, f=True)
                if connection_tag == "rConnection":
                    obj.r.set(l=False)
                    pm.connectAttr(connection_parent.r, obj.r, f=True)
                if connection_tag == "sConnection":
                    obj.s.set(l=False)
                    pm.connectAttr(connection_parent.s, obj.s, f=True)
                if connection_tag == "bsConnection":
                    pm.blendShape(
                        connection_parent,
                        obj,
                        n="bsConnection_{}".format(connection_parent),
                        topologyCheck=0,
                        frontOfChain=True,
                        weight=(0, 1),
                    )
                if connection_tag == "bsConnection_add":
                    master_bshp = pm.PyNode(obj.master_bshp.get())
                    topology_check = obj.bshp_topology_check.get()
                    latest_weight_index = master_bshp.weightIndexList()[-1]
                    pm.blendShape(
                        master_bshp,
                        topologyCheck=topology_check,
                        edit=True,
                        t=(obj, latest_weight_index + 1, connection_parent, 1),
                        weight=(latest_weight_index + 1, 1)
                    )
    return True


def remove_connection_tag(objects):
    """
    Removes all the connection tags

    Args:
        objects(pm.PyNode()/str/list): The elements/element
        from which we need to remove the tag.
    Return:
        None.

    """
    if not isinstance(objects, list):
        objects = [objects]

    for obj in objects:
        if isinstance(obj, str):
            obj = pm.PyNode(obj)
        if hasattr(obj, "connection_tag") and hasattr(obj, "connection_parent"):
            pm.setAttr("{}.{}".format(obj, "connection_tag"), l=0)
            pm.setAttr("{}.{}".format(obj, "connection_parent"), l=0)
            pm.deleteAttr("{}.{}".format(obj, "connection_tag"))
            pm.deleteAttr("{}.{}".format(obj, "connection_parent"))


def create_transform_on_surbsurface(
    nurbsSurface,
    component,
    index,
    u_value=0.5,
    v_value=0.5,
    turn_on_percentage=True,
    scale=False,
):
    """
    Create a transform on a nurbsSurface.

    Args:
        nurbsSurface(pm.PyNode()): The nurbs surface node.
        component(str): The component name.
        index(int): The index name in case of multiple elements.
        u_value(float): The u_value on the nurbs surface.
        v_value(float): The v_value on the nurbs surface
        turn_on_percentage(bool): Enable/Disable pointOnSurface
        calculation as percentage.
        scale(bool): Connect the scale result with transform scale.

    Return:
        pm.PyNode(): The transform on the nurbsSurface.

    """
    if isinstance(nurbsSurface, str):
        nurbsSurface = pm.PyNode(nurbsSurface)

    data_list = [
        {"port_number": 0, "port_name": "normalizedNormal"},
        {"port_number": 1, "port_name": "normalizedTangentU"},
        {"port_number": 2, "port_name": "normalizedTangentV"},
        {"port_number": 3, "port_name": "position"},
    ]

    curve_shape = nurbsSurface.getShape()
    axes = ["X", "Y", "Z"]

    p_on_surface = pm.createNode("pointOnSurfaceInfo")
    p_on_surface.parameterV.set(v_value)
    p_on_surface.parameterU.set(u_value)
    p_on_surface.turnOnPercentage.set(turn_on_percentage)
    four_by_four = pm.createNode("fourByFourMatrix")
    decomp = pm.createNode("decomposeMatrix")
    four_by_four.output.connect(decomp.inputMatrix)
    curve_shape.worldSpace[0].connect(p_on_surface.inputSurface)
    for data in data_list:
        for port, axe in enumerate(axes):
            port_name = "in{}{}".format(str(data.get("port_number")), str(port))
            p_on_surface.attr(
                "{}{}".format(data.get("port_name"), axe)
            ).connect(four_by_four.attr(port_name))

    c_side = name.get_side(nurbsSurface.name(), with_undescore=1)
    c_description = name.get_description(nurbsSurface.name(), with_undescore=1)
    c_subdefinition = name.get_subdefinition(
        nurbsSurface.name(), with_undescore=0
    )
    transform_name = "{}{}{}{}{}_{}".format(
        component, c_side, index, c_description, c_subdefinition, "rivet"
    )

    trs = pm.createNode("transform", n=transform_name)
    for channel in [
        ["outputTranslate", "translate"],
        ["outputRotate", "rotate"],
    ]:
        decomp.attr(channel[0]).connect(trs.attr(channel[1]))
    if scale:
        decomp.outputScale.connect(trs.scale)
    return trs


def pxoparent(masters=pm.selected()[:-1],
              slaves=pm.selected()[-1:],
              maintainOffset=False,
              name=None,
              skipRotate=None,
              skipTranslate=None,
              skipScale=True,
              weight=None,
              native=True,
              space_switch=False,
              host=None,
              ):

    """
    this function creates the baseline for constraints, right now it just does parentconstraints and has a switch
    this switch changes the maya native constraints to matrix constraints

    Args:
        masters:
        slaves:
        maintainOffset:
        name:
        skipRotate:
        skipTranslate:
        skipScale:
        weight:
        native:
        space_switch:
        host:

    Returns:

    """

    #   sort out slaves and masters
    if not masters and slaves:
        raise ValueError('there was no given input for masters and slaves')
        
    if not isinstance(masters, list):
        masters = [masters]

    if not isinstance(slaves, list):
        slaves = [slaves]

    master_nodes = [pm.PyNode(x) if isinstance(x, str) else x for x in masters]
    slave_nodes = [pm.PyNode(x) if isinstance(x, str) else x for x in slaves]

    #   sort out weight interpolation
    weight_interpolation = 1.0 / len(master_nodes)

    #   sort out skipping behaviour
    if skipRotate is True:
        skipRotate = ['x', 'y', 'z']
    if not skipRotate:
        skipRotate = []

    if skipTranslate is True:
        skipTranslate = ['x', 'y', 'z']
    if not skipTranslate:
        skipTranslate = []

    if skipScale is True:
        skipScale = ['x', 'y', 'z']
    if not skipScale:
        skipScale = []

    #   the basic maya constraint behaviour
    if native:

        for nde in slave_nodes:
            #   sort out naming
            constraint_name = name

            if not constraint_name:
                master_part = master_nodes[0].shortName()
                slave_part = nde.shortName()
                constraint_name = '{master}TO{slave}_prc'.format(master=master_part,
                                                                 slave=slave_part)

            const = pm.parentConstraint(master_nodes, nde,
                                        name=constraint_name,
                                        skipTranslate=skipTranslate,
                                        skipRotate=skipRotate,
                                        weight=weight_interpolation,
                                        maintainOffset=maintainOffset
                                        )
            
            const.interpType.set(2)
            const.template.set(1)
            const.visibility.set(0)

            return [const]

    #   the maya node based setup
    else:
        const = list()
        for nde in slave_nodes:

            #   get the world matrix of the slave node
            slave_world_pos = nde.getMatrix(worldSpace=True)

            #   get the parent of the slave
            parent_node = nde.getParent()

            #   before we go into the master node connections, check if we need a blend node
            blending_node = None

            if len(master_nodes) > 1:
                if not space_switch:

                    matrix_blender = pm.createNode('wtAddMatrix', n='{node}_bMtx'.format(node=nde.name()))
                    blending_node = matrix_blender

                else:
                    if host:
                        master_nodes_names = [x.name() for x in master_nodes]
                        master_nodes_enum = ':'.join(master_nodes_names)
                        host.addAttr(nde.name(), at='enum', enumName=master_nodes_enum, k=False)
                        host.attr(nde.name()).set(cb=True)
                        host.attr(nde.name()).set(len(master_nodes)-1)

                    matrix_chooser = pm.createNode('choice', n='{node}_cho'.format(node=nde.name()))
                    blending_node = matrix_chooser

            for iteration, mst in enumerate(master_nodes):
                matrix_out_attr = mst.worldMatrix[0]

                #   checks if there is an offset to maintain
                if maintainOffset:

                    #   calculates the offset amount
                    master_world_inv = mst.getMatrix(worldSpace=True).inverse()
                    offset_from_master = slave_world_pos * master_world_inv

                    #   applies the offset
                    master_offset_mmtx = pm.createNode('math_MultiplyMatrix',
                                                       n='{node}_masterOffset_mMtx'.format(node=nde.name())
                                                       )

                    master_offset_mmtx.input1.set(offset_from_master, lock=True)

                    #   connects the master to its own offset
                    mst.worldMatrix[0].connect(master_offset_mmtx.input2)
                    matrix_out_attr = master_offset_mmtx.output

                #   adds offset for parent nodes
                parent_offset_mmtx = None
                if parent_node:
                    parent_offset_mmtx = pm.createNode('math_MultiplyMatrix',
                                                       n='{node}_parentOffset_mMtx'.format(node=nde.name())
                                                       )

                    matrix_out_attr.connect(parent_offset_mmtx.input1)
                    parent_node.worldInverseMatrix[0].connect(parent_offset_mmtx.input2)

                    matrix_out_attr = parent_offset_mmtx.output

                #   checks if there are multiple master nodes and connects them
                if blending_node:
                    if not space_switch:

                        mtx_attr = 'wtMatrix[{}].matrixIn'.format(str(iteration))
                        mtx_wgt = 'wtMatrix[{}].weightIn'.format(str(iteration))

                        blending_node.attr(mtx_wgt).set(weight_interpolation)
                        matrix_out_attr.connect(blending_node.attr(mtx_attr))
                        matrix_out_attr = blending_node.matrixSum

                    else:

                        mtx_attr = 'input[{}]'.format(str(iteration))
                        mtx_wgt = 'selector'

                        if not host:
                            blending_node.attr(mtx_wgt).set(len(master_nodes)-1)

                        matrix_out_attr.connect(blending_node.attr(mtx_attr))
                        matrix_out_attr = blending_node.output

            #   last output of the calculation, basically from here it should always stay the same
            if host and space_switch:
                host.attr(nde.name()).connect(blending_node.attr('selector'))

            decompose_matrix = pm.createNode('decomposeMatrix', n='{node}_dMtx'.format(node=nde.name()))
            matrix_out_attr.connect(decompose_matrix.inputMatrix)

            #   finishing up the connections
            #   connect the maths to the slave based on exclusion lists
            axis_list = ['x', 'y', 'z']

            translate_axis = list(set(axis_list) - set(skipTranslate))
            for axe in translate_axis:
                axe_c = axe.capitalize()
                decompose_matrix.attr('outputTranslate{}'.format(axe_c)).connect(nde.attr('translate{}'.format(axe_c)))

            rotate_axis = list(set(axis_list) - set(skipRotate))
            for axe in rotate_axis:
                axe_c = axe.capitalize()
                decompose_matrix.attr('outputRotate{}'.format(axe_c)).connect(nde.attr('rotate{}'.format(axe_c)))

            scale_axis = list(set(axis_list) - set(skipScale))
            for axe in scale_axis:
                axe_c = axe.capitalize()
                decompose_matrix.attr('outputScale{}'.format(axe_c)).connect(nde.attr('scale{}'.format(axe_c)))

        return const


def pxopin(geo, u_pos=0.5, v_pos=0.5, node_name='pin', native=True):
    """
    Args:
        geo(str, pm.PyNode):
        u_pos(float):
        v_pos(float):
        node_name:
        native:

    Returns:
        outnode(pm.PyNode):
    """
    #   sort out naming
    if isinstance(geo, str):
        geo = pm.PyNode(geo)

    base_string = '{}_{}__base'.format(geo.shortName(), node_name)
    
    cross_nde = pm.createNode('math_CrossProduct', name=base_string.replace('__base', '_crss'))
    construct_nde = pm.createNode('fourByFourMatrix', name=base_string.replace('__base', '_fbyf'))
    decompose_nde = pm.createNode('decomposeMatrix', name=base_string.replace('__base', '_dMtx'))
    info_nde = pm.createNode('pointOnSurfaceInfo', name=base_string.replace('__base', '_posi'))

    info_nde.turnOnPercentage.set(True, lock=True)

    geo_shape = geo.getShape()
    geo_shape.worldSpace.connect(info_nde.inputSurface)

    info_nde.normalizedNormal.connect(cross_nde.input1)
    info_nde.normalizedTangentU.connect(cross_nde.input2)

    axis = ['X', 'Y', 'Z']
    for index, axe in enumerate(axis):
        info_nde.attr('normalizedNormal{}'.format(axe)).connect(construct_nde.attr('in0{}'.format(str(index))))
        info_nde.attr('normalizedTangentU{}'.format(axe)).connect(construct_nde.attr('in1{}'.format(str(index))))
        cross_nde.attr('output{}'.format(axe)).connect(construct_nde.attr('in2{}'.format(str(index))))
        info_nde.attr('position{}'.format(axe)).connect(construct_nde.attr('in3{}'.format(str(index))))

    construct_nde.output.connect(decompose_nde.inputMatrix)

    return decompose_nde

