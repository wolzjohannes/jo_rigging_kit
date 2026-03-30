# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Import built-in modules
# Import python standart import
import logging

import pxo_rigging_kit.maya_utils.rigging.curves_utils

try:
    from importlib import reload
except:
    pass

import json

# Import third-party modules
from future import standard_library
import pymel.core as pmc
import maya.cmds as cmds
import maya.internal.nodes.proximitywrap.node_interface as ifc # used in Maya 2022


# Import local modules
from pxo_rigging_kit.maya_utils.rigging import rig_utils
from pxo_rigging_kit.maya_utils import dag_utils
from pxo_rigging_kit.maya_utils import attributes_utils
from pxo_rigging_kit.constants import PXO_ROOT_SET_NAME
from pxo_rigging_kit.constants import PXO_DEFORMERS_SET_NAME
from pxo_rigging_kit.constants import PXO_CONTROLS_SET_NAME
from pxo_rigging_kit.constants import RIG_SYS_CONTROL_TAG
from pxo_rigging_kit.maya_utils import paths_utils
from pxo_rigging_kit.constants import PXO_CONTROLS_SET_NAME
from pxo_rigging_kit.constants import PXO_DEFORMERS_SET_NAME
from pxo_rigging_kit.constants import PXO_ROOT_SET_NAME
from pxo_rigging_kit.constants import RIG_SYS_CONTROL_TAG
from pxo_rigging_kit.maya_utils import attributes_utils
from pxo_rigging_kit.maya_utils import dag_utils
from pxo_rigging_kit.maya_utils.rigging import rig_utils

standard_library.install_aliases()

##########################################################
# GLOBALS
##########################################################

FEATHERS_GEO_REF_ATTR = "feather_geo"
FEATHERS_START_SET_NAME = "feathers_start_locs_set"
FEATHERS_END_SET_NAME = "feathers_end_locs_set"
FEATHERS_START_LOCS_GRP = "feathers_start_locs_grp"
FEATHERS_END_LOCS_GRP = "feathers_end_locs_grp"
FEATHERS_SETUP_LOCS_SET_NAME = "feathers_setup_proxy_locs"
FEATHERS_PROXY_MESH = "wing_feathers_setup_proxy_0_geo"
FEATHERS_PROXY_LOCAL_MESH = "wing_feathers_setup_proxy_local_0_geo"
FEATHERS_PROXY_ILAND_MESH = "wing_feathers_setup_proxy_0_iland_geo"
FEATHER_SYS_ROOT_NAME = "feathers_sys_0_grp"
PXM_FEATHERS_BND_SET_NAME = "feathers_deformers_set"
RIG_COMPONENT_ROOT_SUFFIX = "_root"
FEATHER_SEG_CTRL_BUFFER_GRP_NAME = "feathers_seg_ctrl_buffer_grp"
WING_SEG_CTRL_NAME_PATTERN = "WINGTYPE_SIDE_INDEX_DESCRIPTION_ctrl"
WING_SEG_CTRL_BUFFER_SUFFIX = "_ctrl_controlBuffer"
PROXY_SCALE_TRANSFER = "prox_wrap"
SCALE_OUTPUT_TRANSFORM = "global_0_ctrl"

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)

##########################################################
# FUNCTIONS
##########################################################


def generate_object_feather_locs(
    feather_geos,
    start_vtx_list=[0, 4],
    end_vtx_list=[160],
    start_loc_set_name=FEATHERS_START_SET_NAME,
    end_loc_set_name=FEATHERS_END_SET_NAME,
):
    """
    Generate the feather start and end locs to place as guides into the guide template.

    Args:
        feather_geos(list): The feather geos.
        start_vtx_list(list): The start vertices of the each feather geo. This will be used to place the start locs.
                              We get the middle point of the vertices and take that as position for the loc.
                              Default is [0,4].
        end_vtx_list(List): The end vertices of the each feather geo. This will be used to place the end locs.
                            We get the middle point of the vertices and take that as position for the loc.
                            Default is [160]

    Returns:
        Tuple:
            (List(start_locs), List(end_locs))

    """
    start_set_members = []
    end_set_members = []
    start_locs_grp = pmc.createNode("transform", n=FEATHERS_START_LOCS_GRP)
    end_locs_grp = pmc.createNode("transform", n=FEATHERS_END_LOCS_GRP)

    for node in feather_geos:
        pmc.select(
            "{}.vtx{}".format(
                node.name(), str(start_vtx_list).replace(",", ":")
            )
        )
        clu = pmc.cluster()
        loc_0 = pmc.spaceLocator(n="{}_start_loc".format(node.name()))
        loc_0.addAttr(FEATHERS_GEO_REF_ATTR, type="string")
        loc_0.attr(FEATHERS_GEO_REF_ATTR).set(str(node.name()))
        pmc.matchTransform(loc_0, clu)
        pmc.delete(clu)
        pmc.select("{}.vtx[{}]".format(node.name(), start_vtx_list[-1]))
        clu = pmc.cluster()
        loc_1 = pmc.spaceLocator(n="{}_aim_loc".format(node))
        pmc.matchTransform(loc_1, clu)
        pmc.delete([clu])

        if not end_vtx_list:
            end_vtx = node.vtx[-1]
            pmc.select(end_vtx)
        else:
            pmc.select(
                "{}.vtx{}".format(
                    node.name(), str(end_vtx_list).replace(",", ":")
                )
            )
        clu = pmc.cluster()
        loc_2 = pmc.spaceLocator(n="{}_end_loc".format(node.name()))
        pmc.matchTransform(loc_2, clu)
        aim_con = pmc.aimConstraint(
            clu,
            loc_0,
            aim=(1.0, 0.0, 0.0),
            upVector=(0.0, 0.0, 1.0),
            wu=(0.0, 0.0, 1.0),
            wut="object",
            wuo=loc_1,
        )
        pmc.delete([clu, loc_1, aim_con])
        pmc.matchTransform(
            loc_2, loc_0, pos=False, rot=True, piv=False, scl=False
        )
        start_set_members.append(loc_0)
        end_set_members.append(loc_2)

    pmc.select(clear=True)
    start_feathers_set = pmc.sets(n=start_loc_set_name)
    start_feathers_set.addMembers(start_set_members)
    pmc.parent(start_set_members, start_locs_grp)
    end_feathers_set = pmc.sets(n=end_loc_set_name)
    end_feathers_set.addMembers(end_set_members)
    pmc.parent(end_set_members, end_locs_grp)

    return start_set_members, end_set_members


def create_aim_drv_joints(
    feathers_start_locs,
    driver_jnt_name_PATTERN="SIDE_DRV_WINGTYPE_INDEX_jnt",
):
    """
    Create the aim driver joints. This joints will be driver for each feather.
    All of the logic is based on the feathers start locators and their names.

    Args:
        feathers_start_locs(list): The feathers start locs.
        driver_jnt_name_PATTERN(str): The driver jont name pattern.
                                      Example: SIDE_DRV_WINGTYPE_INDEX_jnt
                                      SIDE = Joint side. We get that from the locators name.
                                      INDEX = Joint index number.
                                              This is based on the list index of each locator in the list.
                                      WINGTYPE = Primary,Secondary, etc. wing type name coming from locator.
                                      Default is "SIDE_DRV_WINGTYPE_INDEX_jnt"

    Returns:
        Tuple:
            (drv_jnts, drv_buffer_grps)
    """
    drv_jnts = []

    for index, start_loc in enumerate(feathers_start_locs):
        side = None
        name_error = "No {} found in {}, make sure locators match template: WINGTYPE_INDEX_SIDE_start_loc (primaryFeather_12_L_start_loc)."

        for temp_side in ["L", "R", "C"]:
            side_ = "_{}_".format(temp_side)

            if side_ in start_loc.name():
                side = temp_side

        if not side:
            raise NameError(name_error.format(side_, start_loc))

        try:
            wing_type = start_loc.name().split("_")[0]
        except:
            raise NameError(name_error.format("wing type", start_loc))
        try:
            locator_index = str(start_loc.name().split("_")[1])
        except:
            raise NameError(name_error.format("index", start_loc))

        end_loc = pmc.PyNode(start_loc.name().replace("_start_", "_end_"))
        skin_geo = pmc.PyNode(start_loc.attr(FEATHERS_GEO_REF_ATTR).get())
        drv_jnt_name = driver_jnt_name_PATTERN.replace("SIDE", side).replace(
            "INDEX", locator_index).replace("WINGTYPE",wing_type)

        drv_jnt = pmc.createNode("joint", n=drv_jnt_name)
        drv_jnt_end = pmc.createNode(
            "joint", n=drv_jnt_name.replace("_jnt", "_end_jnt")
        )
        drv_jnt.drawStyle.set(2)
        drv_jnt_end.drawStyle.set(2)
        drv_jnt.addAttr(FEATHERS_GEO_REF_ATTR, type="string")
        drv_jnt.attr(FEATHERS_GEO_REF_ATTR).set(str(skin_geo.name()))
        drv_jnt.addChild(drv_jnt_end)
        pmc.matchTransform(drv_jnt, start_loc)
        pmc.matchTransform(
            drv_jnt_end, end_loc, pos=True, rot=False, piv=False, scl=False
        )
        drv_jnt_end.translateY.set(0.0)
        drv_jnt_end.translateZ.set(0.0)
        drv_jnts.append((drv_jnt, drv_jnt_end))

    drv_buffer_grps = dag_utils.create_buffer_groups(
        [jnt[0] for jnt in drv_jnts]
    )
    for jnt_tuple in drv_jnts:

        jnt_tuple[0].rotate.set(0.0, 0.0, 0.0)
        jnt_tuple[0].jointOrient.set(0.0, 0.0, 0.0)

    return drv_jnts, drv_buffer_grps


def create_jnt_segments(drv_jnts, segments=5, normal_axis="X"):
    """
    Create a joint segments under the each driver joint.
    The joints are evenly distributed over the bone length.

    Args:
        drv_jnts(list): The driver joints.
        segments(int):  The count of segment joints as child from.
                        Default is 5.
        normal_axis(str): The bone normal axes where the segmented joints are distributed.
                          Valid is ["X","Y","Z"]
                          Default is "X".

    Returns:
        List:
            [(drv_jnt,[jnt,jnt,jnt]),(drv_jnt,[jnt,jnt,jnt])]
    """
    result = []
    for strt_jnt, end_jnt in drv_jnts:
        segments_jnts = [
            pmc.createNode(
                "joint", n=strt_jnt.name().replace("_jnt", "_{}_jnt".format(x))
            )
            for x in range(segments + 1)
        ]
        dag_utils.create_hierarchy_from_list(segments_jnts)
        pmc.matchTransform(segments_jnts[0], strt_jnt)
        bone_length = end_jnt.attr("translate{}".format(normal_axis)).get()

        for jnt in segments_jnts[1:]:
            jnt.attr("translate{}".format(normal_axis)).set(
                bone_length / float(segments)
            )

        result.append((strt_jnt, segments_jnts))
        segments_jnts[0].setParent(strt_jnt)
        segments_jnts[0].rotate.set(0.0, 0.0, 0.0)
        segments_jnts[0].jointOrient.set(0.0, 0.0, 0.0)
        segments_jnts[0].visibility.set(0)

    return result


def aim_the_driver_chains(
    aim_dict, aim_vec=(1.0, 0.0, 0.0), upvec=(0.0, 1.0, 0.0)
):
    """
    Aim the aim driver joints to the end locator.

    Args:
        fk0_ctrl_list(List): The driver joints.
    """
    upvec_ = [x * 10.0 for x in upvec]
    upvec = [x * -1.0 for x in upvec if x < -1.0]

    for item in aim_dict.items():
        fk_0_ctrl = item[0]
        aim_obj = item[1]
        parent = fk_0_ctrl.getParent()
        orient_buffer_grp = dag_utils.create_buffer_groups(
            [fk_0_ctrl], "orient_grp"
        )[0]
        root_nd = dag_utils.get_root_node_from_child_node(fk_0_ctrl, "_root")
        upvec_trs = pmc.createNode(
            "transform", n="{}_upvec_trs".format(fk_0_ctrl.name())
        )
        pmc.matchTransform(upvec_trs, fk_0_ctrl)
        upvec_trs.setParent(root_nd)
        upvec_trs.translate.set(upvec_)
        pmc.parent(fk_0_ctrl, None)
        rig_utils.create_aim_matrix(
            orient_buffer_grp,
            aim_obj.worldMatrix[0],
            upvec_trs.worldMatrix[0],
            parent.worldMatrix[0],
            parent.worldInverseMatrix[0],
            aim_vec,
            upvec,
        )
        ctrl_buffer_grp = dag_utils.create_buffer_groups([fk_0_ctrl])[0]
        fk_0_ctrl.setParent(ctrl_buffer_grp)
        ctrl_buffer_grp.setParent(orient_buffer_grp)


def aim_the_wingFeathers_comps(fk0_ctrls, aim_objects):
    """
    Aim the wingFeathers rig components to the aim objects.
    Be aware that the list of the controls and aim objects needs the same length.

    Args:
        fk0_ctrls(list): The first fk control from each fk rig component
        aim_objects: The aim objects which can be controls as well.

    """
    if len(aim_objects) != len(fk0_ctrls):
        raise RuntimeError(
            "fk0_ctrls list and aim_objects list not the same length."
        )

    aim_dict = {
        ctrl: aim_obj for (ctrl, aim_obj) in zip(fk0_ctrls, aim_objects)
    }

    aim_the_driver_chains(aim_dict)


def pin_feather_edge_ctrl_setup(proxy_iland_mesh, feather_curvature_controls):
    """
    Pin the feather edge controls to the proxy iland mesh.
    The proxy iland mesh is a mesh which follow the rig and influences.
    On this mesh will the edge controller be pinned these controls influences the proxy mesh edges.

    Args:
        proxy_iland_mesh(pmc.PyNode()): A cut out geo from the orignal proxy mesh.
                                        Basically the edge faces cutted out.
        feather_curvature_controls(list): The feather edge control

    Returns:
        pin_trs_nodes(list):

    """
    root_nds = [
        dag_utils.get_root_node_from_child_node(ctrl, RIG_COMPONENT_ROOT_SUFFIX)
        for ctrl in feather_curvature_controls
    ]
    pmc.parent(root_nds, None)
    pin_trs_nodes = rig_utils.create_uv_pin_setup(proxy_iland_mesh, root_nds)

    return pin_trs_nodes


def pin_wing_drv_setups(proxy_mesh, aim_drv_jnts_buffer_grps, aim_objects):
    """
    Pin the wing driver joints to the proxy mesh.

    Args:
        proxy_mesh(pmc.PyNode()): The wing proxy mesh which is skinned to actually rig.
        aim_drv_jnts_buffer_grps(List): The buffer grp of the aim driver joints.
        aim_objects(List): The aim objects of the aim driver joints.

    Returns:
        List: The buffer groups of the aim objects pinned to the mesh.

    """
    pin_trs_nodes_aim_drv = rig_utils.create_uv_pin_setup(
        proxy_mesh, aim_drv_jnts_buffer_grps
    )
    rig_utils.create_uv_pin_setup(proxy_mesh, aim_objects, True)

    return pin_trs_nodes_aim_drv


def create_ik_spline_setup(
    driver_jnt_pkg, proxy_mesh, uv_pin_offset_vec=(1.0, 0.0, 0.0)
):
    """
    Create the ik spline setup for each driver and segment joint setup.
    And will pin each point of the spline curve onto the given proxy mesh.
    Furthermore it setups the advanced twist controls for the correct twisting.

    Args:
        driver_jnt_pkg(list): A list of tuples like these: (start_jnt, (segment_jnt, segment_jnt))
        proxy_mesh(pmc.PyNode): The proxy driver mesh.
        uv_pin_offset_vec(tuple): This value is really important.
                                  It will offset the first segment joint and prevent the his children.
                                  This is important because of the uvPin node.
                                  Without these some pin coordinates was failing and the pins ended in the world origin.

    Returns:
        Tuple: (drv_locs_list, twist_trs_list, ik_handle_list)
    """
    twist_trs_list = []
    drv_locs = []
    ik_handle_list = []

    for pkg in driver_jnt_pkg:
        strt_jnt = pkg[0]
        seg_pkg = pkg[1]
        seg_pkg[1].setParent(strt_jnt)
        seg_pkg[0].translate.set(uv_pin_offset_vec)
        seg_pkg[1].setParent(seg_pkg[0])
        driver_curve_name = "{}_drv_crv".format(seg_pkg[0].name())
        twist_start_trs = rig_utils.create_transfrom_on_position(
            seg_pkg[0], "{}_strt_twist_trs".format(seg_pkg[0].nodeName())
        )
        end_start_trs = rig_utils.create_transfrom_on_position(
            seg_pkg[-1], "{}_end_twist_trs".format(seg_pkg[-1].nodeName())
        )
        drv_curve, drv_locs_ = pxo_rigging_kit.maya_utils.rigging.curves_utils.create_curve_from_transforms(
            seg_pkg, name=driver_curve_name, cv_driver="loc",
        )

        drv_curve.visibility.set(0)
        ikHandle = pmc.ikHandle(
            sj=seg_pkg[0],
            ee=seg_pkg[-1],
            c=drv_curve,
            ccv=False,
            sol="ikSplineSolver",
            n="{}_IKHNDL".format(strt_jnt.name()),
        )[0]
        ikHandle.addAttr(FEATHERS_GEO_REF_ATTR, type="string")
        ikHandle.attr(FEATHERS_GEO_REF_ATTR).set(
            strt_jnt.attr(FEATHERS_GEO_REF_ATTR).get()
        )
        ik_handle_list.append(ikHandle)
        ikHandle.visibility.set(0)
        ikHandle.dTwistControlEnable.set(1)
        ikHandle.dWorldUpType.set(4)
        twist_start_trs.worldMatrix[0].connect(ikHandle.dWorldUpMatrix)
        end_start_trs.worldMatrix[0].connect(ikHandle.dWorldUpMatrixEnd)
        ikHandle.setParent(strt_jnt)
        drv_locs.extend(drv_locs_)
        twist_trs_list.extend([twist_start_trs, end_start_trs])
        seg_pkg[1].visibility.set(0)

    rig_utils.create_uv_pin_setup(proxy_mesh, drv_locs, True)
    twist_trs_list = rig_utils.create_uv_pin_setup(
        proxy_mesh, twist_trs_list, pin_directly=False
    )

    return drv_locs, twist_trs_list, ik_handle_list


def generate_system_root_node(child_lists, parent_nd):
    """
    Create the system root node.

    Args:
        child_lists(List): The root nodes children.
        parent_nd(pmc.PyNode): The root nodes parent.

    Returns:
        pmc.PyNode(): The new root node.

    """
    root_nd = pmc.createNode("transform", n=FEATHER_SYS_ROOT_NAME)
    pmc.parent(child_lists, root_nd)
    parent_nd.addChild(root_nd)
    return root_nd


def create_curl_setup(
    controls_list,
    host_ctrl,
    attr_name,
    wing_type,
    curl_axes,
    create_attr_separator=True,
    negate = False
):
    """
    Create the feathers curls setup.

    Args:
        controls_list(joints): The segmented joints for each driver joint.
        host_ctrl(pmc.PyNode): The attributes host control.
        attr_name(str): The curl attributes name.
        wing_type(str): The wing type.
                        For example ["primary","secondary","tail"].
        side(str): The wing feathers side.
        curl_axes(str): The rotation axes where the curl should happen.
                        Valid is ["X", "Y", "Z"].
        create_attr_separator(bool): Enable/Disable separator attribute.

    """

    if create_attr_separator:
        attributes_utils.add_pxo_separator_attr(
            host_ctrl, "{}_curl_setup".format(wing_type)
        )

    host_ctrl.addAttr(attr_name, type="doubleAngle", keyable=True)
    host_ctrl.addAttr(
        "{}_offset".format(attr_name),
        type="float",
        keyable=True,
        min=0.0,
        max=10.0,
        dv=5.0,
    )
    mult_value = 1.0 / len(controls_list)
    if negate:
        mult_value = mult_value *-1

    offset_value = mult_value

    for segm_list in controls_list:
        for child_nd in segm_list:
            mult_mtx = child_nd.offsetParentMatrix.connections()[0]
            decomp_mtx = pmc.createNode("decomposeMatrix")
            rot_blndf = pmc.createNode("animBlendNodeAdditiveRotation")
            compose_mtx = pmc.createNode("composeMatrix")
            mult_mtx.matrixSum.connect(decomp_mtx.inputMatrix)
            decomp_mtx.outputRotate.connect(rot_blndf.inputA)
            host_ctrl.attr(attr_name).connect(
                rot_blndf.attr("inputB{}".format(curl_axes))
            )
            decomp_mtx.outputTranslate.connect(compose_mtx.inputTranslate)
            decomp_mtx.outputScale.connect(compose_mtx.inputScale)
            decomp_mtx.outputShear.connect(compose_mtx.inputShear)
            decomp_mtx.outputQuat.connect(compose_mtx.inputQuat)
            rot_blndf.output.connect(compose_mtx.inputRotate)
            compose_mtx.outputMatrix.connect(
                child_nd.offsetParentMatrix, force=True
            )
            anim_curve_uu = pmc.createNode("animCurveUU")
            anim_curve_uu.addKey(0.0, 0.0, "smooth", "smooth")
            anim_curve_uu.addKey(5.0, offset_value, "smooth", "smooth")
            anim_curve_uu.addKey(10.0, 1.0, "smooth", "smooth")
            anim_curve_uu.output.connect(rot_blndf.weightB)
            host_ctrl.attr("{}_offset".format(attr_name)).connect(
                anim_curve_uu.input
            )


def create_bnd_joints(
    ctrl_pkg_list,
    parent_nd,
    name_pattern="SIDE_BND_FEATHERTYPE_INDEX_DESCRIPTION_jnt",
    pxo_deformers_set=None,
    pxo_root_set=None,
):
    """
    Create the bind joints.

    Args:
        segment_jnts_list(): The segmented joints for each driver joint.
        parent_nd(pmc.PyNode): The bind joints parent.

    Returns:
        List: The created bind joints.

    """
    deformers_set = pmc.createNode("objectSet", n=PXM_FEATHERS_BND_SET_NAME)

    if not pxo_deformers_set:
        pxo_deformers_set = pmc.PyNode(PXO_DEFORMERS_SET_NAME)

    if not pxo_root_set:
        pxo_root_set = pmc.PyNode(PXO_ROOT_SET_NAME)

    pxo_root_set.addMember(deformers_set)

    for sgm_list in ctrl_pkg_list:
        skn_geo = sgm_list[0].attr(FEATHERS_GEO_REF_ATTR).get()
        temp_list = []

        for ctrl in sgm_list:
            name_split = ctrl.split("_")
            side = name_split[1]
            index = name_split[2]
            description = name_split[3]
            feather_type = name_split[0]
            name = (
                name_pattern.replace("SIDE", side)
                .replace("INDEX", index)
                .replace("DESCRIPTION", description)
                .replace("FEATHERTYPE", feather_type)
            )
            bnd_jnt = pmc.createNode("joint", n=name)
            bnd_jnt.addAttr(FEATHERS_GEO_REF_ATTR, type="string")
            bnd_jnt.attr(FEATHERS_GEO_REF_ATTR).set(skn_geo)
            rig_utils.create_worldspace_matrix_constraint(bnd_jnt, ctrl)
            temp_list.append(bnd_jnt)

        dag_utils.create_hierarchy_from_list(temp_list)
        temp = [jnt.jointOrient.set(0.0, 0.0, 0.0) for jnt in temp_list]
        deformers_set.addMembers(temp_list)
        pxo_deformers_set.addMembers(temp_list)
        pmc.parent(temp_list[0], parent_nd)

    return deformers_set.members()


def skin_geos_from_feathers_jnts(feathers_bnd_jnts):
    """
    Skin the goes based on the joints message input in the FEATHERS_GEO_REF_ATTR attribute of the joint.

    Args:
        feathers_bnd_jnts(List): The feathers bind joints.

    """
    skin_geos = set(
        [
            bnd_jnt.attr(FEATHERS_GEO_REF_ATTR).get()
            for bnd_jnt in feathers_bnd_jnts
        ]
    )

    for geo in skin_geos:
        bnd_jnt = [
            jnt
            for jnt in feathers_bnd_jnts
            if geo in jnt.attr(FEATHERS_GEO_REF_ATTR).get()
        ]
        pmc.skinCluster(
            bnd_jnt,
            pmc.PyNode(geo),
            sm=0,
            sw=0.5,
            swi=50,
            dr=5.0,
            bm=0,
            mi=2,
            tsb=True,
        )


def hide_driver(driver_objects):
    """
    Hide the whole driver setup.

    Args:
        driver_objects(list): All the driver buffer groups.

    """
    for obj in driver_objects:
        obj.visibility.set(0)


def sort_start_locs_by_side(feathers_start_locs, l_side=True, r_side=True, c_side=True, zfill_value = 3):
    """
    Sort the start locators by name, index and side.

    Args:
        feathers_start_locs: The feathers start locs.
        l_side(bool): Gives back the left locators.
                      Default is True.
        r_side(bool): Gives back the right locators.
                      Default is True.

    Returns:
        List: The sorted locators.

    """
    result = []
    l_locs = []
    r_locs = []
    c_locs = []

    for loc in feathers_start_locs:

        if "_L_" in loc.name():
            l_locs.append(loc)
        elif "_C_" in loc.name():
            c_locs.append(loc)
        else:
            r_locs.append(loc)

    if l_side:
        result.extend(l_locs)
    if r_side:
        result.extend(r_locs)
    if c_side:
        result.extend(c_locs)

    #sort by number splitted by _
    index_list = []

    for r in result:
        for x in r.split("_"):
            if x.isnumeric():
                index_list.append(x.zfill(zfill_value) + "_" + r)
                break

    sorted_index_list = index_list.copy()
    sorted_index_list.sort()

    sorted_result = []

    for i, s in enumerate(sorted_index_list):
        sorted_result.append(result[index_list.index(s)])

    return sorted_result


def create_tweak_control_setup(
    driver_jnt_pkg,
    name_pattern=WING_SEG_CTRL_NAME_PATTERN,
    ctrl_buffer_suffix=WING_SEG_CTRL_BUFFER_SUFFIX,
    controlers_set=None,
):
    """
    Create the tweak control setup so the animators have fk controls for deeper adjustments.

    Args:
        driver_jnt_pkg(list): The driver jnts as tuoles in a list.
        name_pattern(str): The control name pattern.
        ctrl_buffer_suffix(str): The buffer ctrl group name suffix.
        controlers_set(pmc.PyNode): The controllers set.

    Returns:
        List: [[ctrl, ctrl, ctrl], [ctrl, ctrl, ctrl]]

    """
    result = []
    if not controlers_set:
        controlers_set = pmc.PyNode(PXO_CONTROLS_SET_NAME)


    for pkg in driver_jnt_pkg:
        strt_jnt = pkg[0]
        seg_pkg = pkg[1]
        skn_geo = strt_jnt.attr(FEATHERS_GEO_REF_ATTR).get()
        start_jnt_name_split = strt_jnt.nodeName().split("_")
        side = start_jnt_name_split[0]
        wing_type = start_jnt_name_split[2]
        index_ = start_jnt_name_split[-2]
        name = (
            name_pattern.replace("SIDE", side)
            .replace("INDEX", index_)
            .replace("WINGTYPE", wing_type)
        )

        controls = _setup_tweaker_controls(name, ctrl_buffer_suffix, seg_pkg, skn_geo)

        dag_utils.create_hierarchy_from_list(controls)
        controls[0].setParent(strt_jnt)
        controlers_set.addMembers(controls)

        for ctrl, seg_jnt in zip(controls, seg_pkg):
            _setup_variable_matrix_chain(ctrl, seg_jnt)

        result.append(controls)

    return result


def _setup_variable_matrix_chain(ctrl, seg_jnt):
    parent_seg_jnt = seg_jnt.getParent()
    mult_mtx = pmc.createNode("multMatrix")
    seg_jnt.worldMatrix[0].connect(mult_mtx.matrixIn[0])
    parent_seg_jnt.worldInverseMatrix[0].connect(mult_mtx.matrixIn[1])
    mult_mtx.matrixSum.connect(ctrl.offsetParentMatrix)
    rig_utils.reset_transform(ctrl)


def _setup_tweaker_controls(name_pattern, ctrl_buffer_suffix, seg_pkg, skn_geo):
    controls = []

    for index, node in enumerate(seg_pkg):
        ctrl_buffer_obj = None
        name = name_pattern.replace("DESCRIPTION", "fk{}".format(index))

        ctrl = _setup_tweaker_ctl(name, skn_geo)

        if pmc.objExists(name.replace("_ctrl", ctrl_buffer_suffix)):
            ctrl_buffer_obj = pmc.PyNode(
                name.replace("_ctrl", ctrl_buffer_suffix)
            )

        pmc.matchTransform(ctrl, node)

        if ctrl_buffer_obj:
            buffer_shape = ctrl_buffer_obj.getShape(noIntermediate=True)
            ctrl_shape = ctrl.getShape(noIntermediate=True)
            dag_utils.swap_curve_shapes(ctrl_buffer_obj, ctrl)
            color = buffer_shape.overrideColor.get()

        controls.append(ctrl)
        ctrl.addAttr(RIG_SYS_CONTROL_TAG, type="bool", keyable=False)

    return controls


def _setup_tweaker_ctl(name, skn_geo):
    """
    Creates basic controller with extra feather attribute.
        Args:
            name(str): Name.
            skn_geo(str): Skin geo name.

        Returns:
            ctrl(pyNode): Controller.
    """
    ctrl = pmc.circle(n=name, ch=False)[0]
    ctrl.visibility.set(keyable=False, lock=True)
    ctrl.addAttr(FEATHERS_GEO_REF_ATTR, type="string")
    ctrl.addAttr("shifterName", type="string")
    ctrl.attr("shifterName").set(name)
    ctrl.attr(FEATHERS_GEO_REF_ATTR).set(skn_geo)
    return ctrl


def create_control_buffer_shapes(
    ctrls_list, ctrl_buffer_suffix=WING_SEG_CTRL_BUFFER_SUFFIX
):
    """
    Create the control buffer shapes. So the artist can specify the look of the segment controls.
    It will create a root group for the shapes.
    If already existing it will not delete the old one this has to be managed by the artist himself.

    Args:
        ctrls_list(List): The already shaped controls.
        ctrl_buffer_suffix(str): The buffer controls name suffix.
                                 Default is WING_SEG_CTRL_BUFFER_SUFFIX variable.

    """
    root_grp = pmc.createNode("transform", n=FEATHER_SEG_CTRL_BUFFER_GRP_NAME)
    buffer_crls = [
        node.duplicate(n=node.nodeName().replace("_ctrl", ctrl_buffer_suffix))[
            0
        ]
        for node in ctrls_list
    ]
    pmc.parent(buffer_crls, root_grp)
    temp_delete = [node.getChildren(type="transform") for node in buffer_crls]
    pmc.delete(temp_delete)


def create_wind_effect(local_mesh, proxy_mesh, arm_host_controls):
    """
    Create the wind effect based on textureDeformer based in the guide.

    Args:
        local_mesh(pmc.PyNode()): The local mesh connected with the guide texture deformer.
        proxy_mesh(pmc.PyNode()): The wing feathers proxy mesh which drives each feather joint chain.
        arm_host_controls(list): The arm host controls for attributes placement.

    Returns:
        pmc.PyNode: The textureDeformer handle.
    """
    local_mesh_dup = local_mesh.duplicate(un=True)[0]
    noise_nd, txt_def_handle, txt_def_nd, txt_place_2d = _gather_wind_nodes(local_mesh_dup)

    pmc.blendShape(local_mesh_dup, proxy_mesh, w=(0, 1.0), at=True)
    ATTR_PACK = [
        {"longName": "wind_progress", "type": "float", "keyable": True},
        {
            "longName": "wind_strength",
            "type": "float",
            "keyable": True,
            "min": 0.0,
            "max": 1.0,
            "dv": 0.0,
        },
        {
            "longName": "wind_offset",
            "type": "float",
            "keyable": True,
            "min": 0.0,
            "max": 1.0,
            "dv": 0.0,
        },
        {
            "longName": "wind_noise",
            "type": "float",
            "keyable": True,
            "min": 0.0,
            "max": 1.0,
            "dv": 0.175,
        },
        {
            "longName": "wind_frequency",
            "type": "float",
            "keyable": True,
            "min": 0.0,
            "max": 10.0,
            "dv": 0.5,
        },
    ]
    for index, host_ctrl in enumerate(arm_host_controls):
        attributes_utils.add_pxo_separator_attr(
            host_ctrl, "wingFeathers_effects"
        )
        for attr_dict in ATTR_PACK:
            if index is 1:
                proxy_nd = arm_host_controls[0]
                long_name = attr_dict["longName"]
                proxy_attr = proxy_nd.attr(long_name)
                attr_dict["proxy"] = proxy_attr

            pmc.addAttr(host_ctrl, **attr_dict)

        if index is 0:
            host_ctrl.wind_progress.connect(txt_place_2d.offsetU)
            host_ctrl.wind_strength.connect(txt_def_nd.strength)
            host_ctrl.wind_offset.connect(txt_def_nd.offset)
            host_ctrl.wind_noise.connect(noise_nd.noise)
            host_ctrl.wind_frequency.connect(noise_nd.noiseFreq)

    return [local_mesh_dup, txt_def_handle]


def _gather_wind_nodes(local_mesh_dup):
    """
    Gathers deformation nodes for wind setup.
        Args:
            local_mesh_dup(pyNde): Geometry with deformations needed for wind setup.

        Returns:
            Tuple:
                noise_nd(pmc.PyNode()): Ramp node.
                txt_def_handle(pmc.PyNode()): Texture deformer handle node.
                txt_def_nd(pmc.PyNode()): Texture deformer node.
                txt_place_2d(pmc.PyNode()): Place 2d texture node.
    """
    noise_nd = [
        node
        for node in pmc.listHistory(local_mesh_dup)
        if isinstance(node, pmc.nt.Ramp)
    ][0]
    txt_def_handle = [
        node
        for node in pmc.listHistory(local_mesh_dup)
        if isinstance(node, pmc.nt.TextureDeformerHandle)
    ][0]
    txt_def_nd = [
        node
        for node in pmc.listHistory(local_mesh_dup)
        if isinstance(node, pmc.nt.TextureDeformer)
    ][0]
    txt_place_2d = [
        node
        for node in pmc.listHistory(local_mesh_dup)
        if isinstance(node, pmc.nt.Place2dTexture)
    ][0]
    return noise_nd, txt_def_handle, txt_def_nd, txt_place_2d


def create_roll_twist_setup(
    type_,
    ikhandle_list,
    host_ctrl,
    attr_name,
    wing_type,
    create_attr_separator=True,
    negate = False
):
    """
    Create the roll twist setup based on the ik handle setup.

    Args:
        type_(str): Specifies which system you want to create valid values are ["roll", "twist"].
        ikhandle_list(list): All spline ik handles genrate for the wing feathers.
        host_ctrl(pmc.pmc.PyNode()): The host control for the anim attributes.
        attr_name(str): The setup control attribute name.
        wing_type(str): The wing type. Valid values are ["Primary", "Secondary", "Tertial", "Tail"].
        side(str): The side of the setup. Valid values are ["L", "R", "C"].
        create_attr_separator(bool): Create a separator attribute.

    """
    if create_attr_separator:
        attributes_utils.add_pxo_separator_attr(
            host_ctrl, "{}_{}_setup".format(wing_type, type_)
        )
    host_ctrl.addAttr(attr_name, type="doubleAngle", keyable=True)
    host_ctrl.addAttr(
        "{}_offset".format(attr_name),
        type="float",
        keyable=True,
        min=0.0,
        max=10.0,
        dv=5.0,
    )
    mult_value = 1.0 / len(ikhandle_list)

    if negate:
        mult_value = mult_value * -1

    for ik_handle in ikhandle_list:
        mult_angle_nd = _setup_ik_roll_twist(host_ctrl, attr_name, mult_value)
        mult_angle_nd.output.connect(ik_handle.attr(type_))


def _setup_ik_roll_twist(host_ctrl, attr_name, offset_value):
    """
    Creates specified setup on host_ctrl and outputs node prepared for further connection.
        Args:
            host_ctrl(pmc.PyNode()): Ctrl pyNode.
            attr_name(str): Attribute name.
            offset_value(float): Offset float value.
        Return:
            mult_angle_nd(pmc.PyNode()): Math multiply angle node.
    """
    mult_angle_nd = pmc.createNode("math_MultiplyAngle")
    host_ctrl.attr(attr_name).connect(mult_angle_nd.input1)
    anim_curve_uu = pmc.createNode("animCurveUU")
    anim_curve_uu.addKey(0.0, 0.0, "smooth", "smooth")
    anim_curve_uu.addKey(5.0, offset_value, "smooth", "smooth")
    anim_curve_uu.addKey(10, 1.0, "smooth", "smooth")
    host_ctrl.attr("{}_offset".format(attr_name)).connect(
        anim_curve_uu.input
    )
    anim_curve_uu.output.connect(mult_angle_nd.input2)

    return mult_angle_nd


def create_proxy_geo_from_feather_locs(feather_locs, mirror = False):
    """
    Create a proxy geometrie from feather locators or transforms.
    The feathers locs or transfrom represents the start and end point for each feather.

    Args:
        feather_locs(list): List with pmc.PyNodes().
        mirror(bool): Mirrors geometry from left to right side.
    """
    delete_list = []
    feather_locs = sort_start_locs_by_side(feather_locs, True, True, c_side=True)
    aim_drv_jnts, aim_drv_jnts_buffer_grps = create_aim_drv_joints(feather_locs)
    seg_pkg_list = create_jnt_segments(aim_drv_jnts)
    curve_list = [
        pxo_rigging_kit.maya_utils.rigging.curves_utils.create_curve_from_transforms(pkg[1], True, cv_driver="loc")[0]
        for pkg in seg_pkg_list
    ]
    srf = pmc.loft(curve_list, ch=False, u=1, c=0, ar=1, po=0, ss=2, rn=0, d=1, rsn=False)[0]
    geo = cmds.nurbsToPoly(srf.name(),mnd = 1 ,ch = False,f = 3,pt = 1,pc = 200,
                           chr = 0.9,ft = 0.01,mel = 0.001,d = 0.1,ut = 1,un = 3,
                           vt = 1,vn = 3,uch = 0,ucr = 0,cht = 0.2,es = 0,ntr = 0,
                           mrt = 0,uss = 1)
    pmc.delete(srf)

    if mirror:
        dup_geo = geo.duplicate()[0]
        dup_geo.scaleX.set(-1.0)
        pmc.polyUnite(geo, dup_geo, ch=False)

    delete_list.extend(aim_drv_jnts)
    delete_list.extend(aim_drv_jnts_buffer_grps)
    delete_list.extend(curve_list)
    pmc.delete(delete_list)

def attach_body_feathers(attach_dic, suffix = "PROXWRAP", setup_scale = False):
    """
    Create proximityWrap deformer for feather geometries driven by driver list with falloff_scale,
    wrap mode, smooth influences settings from dictionary.

    Args:
        attach_dic: Dictionary of feathers as main key and the subkeys with list of drivers, faloff scale, wrap mode, smooth influences attr values.
                    For example attach_dic = {"body_feather_geo":{"driver_list":["body_geo"], "falloff_scale":5, "wrap_mode":0, "smooth_influences":10 }}

    Returns:
        pwrap_list(list): Returns pmc.PyNode list
    """
    pwrap_list = []
    ci = 0
    # pre-creates cluster and joint for further scaling
    if setup_scale:
        jnt = PROXY_SCALE_TRANSFER + "_jnt"
        clstr = PROXY_SCALE_TRANSFER + "_clstr"
        scale_transform = pmc.PyNode(SCALE_OUTPUT_TRANSFORM)

        if not pmc.objExists(jnt):
            jnt = pmc.joint(n=jnt)
            pmc.parent(jnt, "setup")
            pmc.hide(jnt)

        else:
            jnt = pmc.PyNode(jnt)

    for feather_geo in attach_dic:
        i = 0
        pwrap_name = "{}_{}".format(feather_geo, suffix)

        if ":" in feather_geo:  # strip potential namespace
            pwrap_name = "{}_{}".format(feather_geo.split(":")[-1], suffix)

        if setup_scale:
            if not pmc.objExists(clstr):
                clstr = pmc.createNode("cluster", n=clstr)
                jnt.matrix >> clstr.matrix
                scale_transform.scale >> jnt.scale
            else:
                clstr = pmc.PyNode(clstr)

        feather_geo = pmc.PyNode(feather_geo)
        pwrap = pmc.deformer(feather_geo, type="proximityWrap", n=pwrap_name)[0]
        pwrap_list.append(pwrap)

        pwni = ifc.NodeInterface(pwrap.name())

        if setup_scale:
            orig = pmc.listConnections(pwrap.originalGeometry[i], s=True, d=False, p=True)[0]
            input = pmc.listConnections(pwrap.input[i].inputGeometry, s=True, d=False, p=False)[0]

            orig >> clstr.input[ci].inputGeometry
            orig >> clstr.originalGeometry[ci]

            clstr.outputGeometry[ci] >> pwrap.originalGeometry[i]
            clstr.outputGeometry[ci] >> input.inputGeometry

            ci = ci + 1

        for body_geo in attach_dic[feather_geo.name()]["driver_list"]:
            shapes = cmds.listRelatives(body_geo, type="shape", ni=True)
            shape = None

            # safety check so Deformed shape gets used on reference
            for s in shapes:
                if s.endswith("Deformed"):
                    shape = s

            if shape == None:
                shape = shapes[0]

            pwni.addDriver(shape)

            if setup_scale:
                con_list = pmc.listConnections(clstr.input, s=True, d=False, p=True)
                origDriver = pmc.listConnections(pwrap.drivers[i].driverBindGeometry, s=True, d=False, p=True)[0]


                origDriver >> clstr.input[ci].inputGeometry
                origDriver >> clstr.originalGeometry[ci]

            i = i + 1
            ci = ci + 1

        if setup_scale:
            md = pmc.createNode("multiplyDivide")
            scale_transform.scaleX >> md.input1X
            scale_transform.scaleX >> md.input1Y
            scale_transform.scaleX >> md.input1Z
            md.input2X.set(attach_dic[feather_geo.name()]["falloff_scale"])
            md.outputX >> pwrap.falloffScale
        else:
            pwrap.falloffScale.set(attach_dic[feather_geo.name()]["falloff_scale"])

        pwrap.smoothInfluences.set(attach_dic[feather_geo.name()]["smooth_influences"])
        pwrap.wrapMode.set(attach_dic[feather_geo.name()]["wrap_mode"])

    return pwrap_list


def gather_feather_data(file="pxo_bird_feather_setup.json"):
    """
    Reads json file and return it as data from rig data folder.

    Args:
        file(str): File to read.

    Returns:
        data(dic): Returns dictionary
    """

    list_asset_data_dir = paths_utils.list_data_dir(pmc.sceneName())
    data = None
    for key in list_asset_data_dir:
        if key == file:
            f = open(list_asset_data_dir[key])
            data = json.load(f)

    if data == None:
        raise ValueError("{} not found in current rig data, please create or add one.".format(file))

    return data
