from maya import cmds
from maya.api import OpenMaya as om2


def compile_joint_reset_info() -> list:
    joint_reset_info = []

    active_sel = om2.MGlobal.getActiveSelectionList()
    sel_iter = om2.MItSelectionList(active_sel, om2.MFn.kJoint)

    trs_pointer = om2.MFnDependencyNode()
    skc_pointer = om2.MFnDependencyNode()

    while not sel_iter.isDone():
        current_object = sel_iter.getDependNode()
        trs_pointer.setObject(current_object)

        if not trs_pointer.hasAttribute("worldMatrix"):
            sel_iter.next()
            continue

        mtx = trs_pointer.findPlug("worldMatrix", 0)
        matrix_plug = mtx.elementByLogicalIndex(0)

        if not matrix_plug.isConnected:
            sel_iter.next()
            continue

        out_connections = matrix_plug.destinations()

        if not out_connections:
            sel_iter.next()
            continue

        connected_nodes = [plug_.node() for plug_ in out_connections]
        connected_indices = [plug_.logicalIndex() for plug_ in out_connections]

        valid_nodes = [(node_, index_)
                       for (node_, index_)
                       in zip(connected_nodes, connected_indices)
                       if node_.hasFn(om2.MFn.kSkinClusterFilter)
                       ]

        if not valid_nodes:
            sel_iter.next()
            continue

        current_dag = sel_iter.getDagPath()
        current_name = current_dag.fullPathName()
        current_world_matrix = tuple(current_dag.inclusiveMatrix().inverse())

        target_plug_names = set()

        for node_, index_ in valid_nodes:
            skc_pointer.setObject(node_)

            if not skc_pointer.hasAttribute("bindPreMatrix"):
                continue

            pre_plug = skc_pointer.findPlug("bindPreMatrix", 0)
            pre_index_plug = pre_plug.elementByLogicalIndex(index_)
            target_plug_names.add(pre_index_plug.name())

        joint_reset_info.append((current_name, current_world_matrix, target_plug_names))
        sel_iter.next()

    return joint_reset_info


def reset_selected_joints_bind_pos():
    sel_jnt_info = compile_joint_reset_info()

    for (_, mtx_, plug_names_) in sel_jnt_info or []:

        for plug_name_ in plug_names_:

            cmds.setAttr(plug_name_,
                         mtx_,
                         type="matrix"
                         )


if __name__ == "__main__":
    reset_selected_joints_bind_pos()
