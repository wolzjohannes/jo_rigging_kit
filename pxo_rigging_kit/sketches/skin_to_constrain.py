# Author:     Christof Puehringer / Rigging TD

"""
NOT FINISHED OR IMPLEMENTED AT ALL!
WARNING WARNING WARNING





What needs to happen in this module is, that a skincluster gets converted into constraint,
this needs to be linked to the vertices being sampled, the position pf the joints and an average weighting.

"""




# Import built-in modules
import ast

# Import third-party modules
import numpy
import pymel.core as pmc

# Import local modules
from pxo_rigging_kit.maya_utils import dag_utils
from pxo_rigging_kit.maya_utils.deformers.operators import skincluster_op

skin_operator = skincluster_op.SkinClusterOperator("MESH_NAME")

# Skin plane setup code
base_plane = pmc.PyNode("pPlane1")
root_nodes = set(dag_utils.get_root_node_from_child_node(node, "root") for node in pmc.ls(sl=True))
for node in root_nodes:
    match_plane = base_plane.duplicate(n="{}_match_pl_geo".format(node.name(long=None)))[0]
    pmc.matchTransform(match_plane, node)
    match_plane.addAttr("root_nd", type="string", keyable=False)
    match_plane.addAttr("constrain_nodes", type="string", keyable=False)
    match_plane.root_nd.set(node.name(), type="string")

# Here we save the weights into a string attribute for further usage
planes = pmc.ls("goads_*_root_match_pl_geo")
for node in planes:
    skin_operator = skincluster_op.SkinClusterOperator(node)
    # FROM HERE . . .
    skin_operator.gather_scene_internal_data()
    inf_list = skin_operator.influence_names.tolist()

    skin_weights = skin_operator.uncompressed_weights

    in_weights = skin_operator.compressed_weights
    in_legend = skin_operator.compressed_legend

    temp_dict = {}
    for inf_id, weight in in_weights:
        inf_name = inf_list[int(inf_id)].split("|")[-1]
        if not temp_dict.get(inf_name, None):
            temp_dict[inf_name] = [weight]
        else:
            temp_list = temp_dict[inf_name]
            temp_list.append(weight)
            temp_dict[inf_name] = temp_list

    # . . . TO HERE NOTHING WOEKS

    node.constrain_nodes.set(str(temp_dict), type="string")


# plane skinweights to scale constraint weights.
planes = pmc.ls("goads_*_root_match_pl_geo")
for plane in planes:
    root_nd = pmc.PyNode(plane.root_nd.get())
    constrain_dict = ast.literal_eval(str(plane.constrain_nodes.get()))
    con_drivers = list(constrain_dict.keys())
    p_con = pmc.parentConstraint(con_drivers, root_nd, mo=True)
    s_con = pmc.scaleConstraint(con_drivers, root_nd, mo=True)
    for p_attr, s_attr in zip(p_con.getWeightAliasList(), s_con.getWeightAliasList()):
        p_con_driver = p_attr.name(False).split("W")[0]
        s_con_driver = s_attr.name(False).split("W")[0]
        p_attr.set(numpy.mean(constrain_dict[p_con_driver]))
        s_attr.set(numpy.mean(constrain_dict[s_con_driver]))




# Import third-party modules
# Revert the UV pin setup
import pymel.core as pmc
import pymel.core.datatypes as dt

# Import local modules
from pxo_rigging_kit.maya_utils.rigging import rig_utils

goads_ik_cns = pmc.ls("goads_*_ik_cns")
zero_matrix = dt.TransformationMatrix()
for node in goads_ik_cns:
    match_trs = rig_utils.create_transfrom_on_position(node)
    input_plug = node.offsetParentMatrix.connections(source=True, d=False, p=True)
    if input_plug:
        input_plug = input_plug[0]
    node.addAttr("uvp_input", type="string")
    node.uvp_input.set(str(input_plug), type="string")
    node.offsetParentMatrix.disconnect()
    node.offsetParentMatrix.set(zero_matrix)
    node.inheritsTransform.unlock()
    node.inheritsTransform.set(True)
    pmc.matchTransform(node, match_trs)
    pmc.delete(match_trs)
