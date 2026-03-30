"""
This module manages to localize skin influences.

# build the localized data for selection
>>> from pxo_rigging_kit.maya_utils.post_and_pre_build.localize_skin_influences_setup import localize_skin_influences_for_selection
>>> localize_skin_influences_for_selection()


# save the localized data for selection
>>> from pxo_rigging_kit.maya_utils.post_and_pre_build.localize_skin_influences_setup import save_localize_data_from_selection
>>> save_localize_data_from_selection()


# save the localized data for selection
>>> from pxo_rigging_kit.maya_utils.post_and_pre_build.localize_skin_influences_setup import load_and_execute_localize_data
>>> load_and_execute_localize_data(import_path=None)



"""

# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Import built-in modules
# Import python standart import
import logging
import os

# Import third-party modules
from future import standard_library

import numpy as np
from pprint import pprint
import pymel.core as pmc

from pxo_rigging_kit import constants

from pxo_rigging_kit.constants import PXO_FILEPATH_SCIF
from pxo_rigging_kit.constants import LOCALIZE_INF_LOOKUP_EXPORT_NAME
from pxo_rigging_kit.constants import RIG_SYS_CONTROL_TAG
from pxo_rigging_kit.constants import PRE_BND_MTX_TRS_DATA_LOOKUP_EXPORT_NAME
from pxo_rigging_kit.constants import MGEAR_MATRIX_CONSTRAINT

from pxo_rigging_kit.maya_utils import decorators
from pxo_rigging_kit.maya_utils import exceptions

from pxo_rigging_kit.maya_utils.deformers.operators.skincluster_op import SkinClusterOperator
from pxo_rigging_kit.maya_utils.rigging import rig_utils

from pxo_rigging_kit.io_version_control.version_io import ImportExport


##########################################################
# GLOBALS
##########################################################

standard_library.install_aliases()

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)
DECORATORS = decorators.Decorators()
DECORATORS.debug = True
DECORATORS.logger = _LOGGER
DEFAULT_ROOT_SUFFIX = "_root"

##########################################################
# HELPER FUNCTIONS
##########################################################


def get_skincluster_mtx_ports_index_from_bnd_jnt(jnt):
    """
    Get the skincluster matrix port indexes from given joint.
    The joint can be an influence of multiple skinclusters.

    Args:
        jnt(pmc.PyNode): The joint to act on.

    Returns:
        Dict: {"skinCluster1": 45, "skinCluster2": 15}

    """

    skinclusters = jnt.worldMatrix[0].connections(type="skinCluster")
    return {str(skc.name()): skc.indexForInfluenceObject(jnt) for skc in skinclusters}


@DECORATORS.x_timer
def create_bind_pre_matrix_transforms(geo):
    """
    Create the transforms which are connected to the pre bind matrix of the skincluster.
    The transforms are in the same world space position like the connected joint influences and can be used to
    reset the rest pose of each influence.

    Args:
        geo(pmc.PyNode): The geometry with the connected skincluster.

    Returns:
        List: pmc.PyNodes().

    """

    skin_operator = SkinClusterOperator(geo.longName())
    skin_operator.gather_scene_internal_data()

    joints_pack = np.column_stack((skin_operator.influences["index"], skin_operator.influences["name"]))
    joints_pack = joints_pack.tolist()

    transforms = []
    for pkg in joints_pack:
        trs_name = "{0}_bindPre_trs".format(pkg[1].split("|")[-1])
        jnt = pmc.PyNode(pkg[1])
        try:
            trs = pmc.PyNode(trs_name)
            rig_utils.compare_world_positions(jnt, trs)
        except:
            trs = create_pre_bnd_mtx_ws_transform(
                trs_name, jnt, skin_operator.deformer_name
            )
        transforms.append((pkg[0], trs))

    for index, trs in transforms:
        trs.worldInverseMatrix[0].connect(pmc.PyNode(skin_operator.deformer_name).bindPreMatrix[index])

    return transforms


def create_pre_bnd_mtx_ws_transform(
    trs_name,
    src_bnd_jnt=None,
    src_skinluster_name="",
    parent_nd="",
    ws_pos=None,
    ws_rot=None,
    ws_scale=None,
):

    """
    Create a transform which represents the pre bind matrix input for the given transform.
    This transform is in world space and resets the default place of the skinning for the given source bind joint.
    The transform owns a bunch of meta attributes which are used for recreation, parenting and and and.

    Args:
        trs_name(str): The transform name.
        src_bnd_jnt(str or pmc.PyNode()): The Jjint which is the matrix input of the skincluster.
                                          If string is given the created transform will be world origin and
                                          the given string is the value of the source bind joint meta attribute
                                          on the transform.
                                          If None transform gets no entry in the source bind joint meta attribute and
                                          the created transform will be world origin.
                                          This attribute is used to find the matrix port ID of the given bind joint
                                          which represent the same port ID at the pre bin matrix plug for the transform.
                                          Furthermore, the transform will be in the
                                          world space position of this transform.
        src_skinluster_name(str): Source skincluster name as value of the source skincluster meta attribute.
                                  This attribute is used to connect the transform to the corresponding skincluster.
                                  Default is an empty string.
        parent_nd(str): Parent node name as value for the parent_nd meta attribute.
                        This attribute exist for parenting and unparenting of the transform.
                        Default is an empty string.
        ws_pos(tuple): World position of the transform.
                       This will override the world position of the source joint for the transform.
                       Default is None.
        ws_rot(tuple): World rotation of the transform.
                       This will override the world rotation of the source joint for the transform.
                       Default is None.
        ws_scale(tuple): World scale of the transform.
                         This will override the world scale of the source joint for the transform.
                         Default is None.

    Returns:
            pmc.PyNode(): Created transform.

    """
    jnt_name = ""

    if src_bnd_jnt:
        if not isinstance(src_bnd_jnt, str):
            trs = rig_utils.create_transfrom_on_position(src_bnd_jnt, trs_name)
            jnt_name = str(src_bnd_jnt.name(long=None))
        else:
            trs = pmc.createNode("transform", n=trs_name)
            jnt_name = src_bnd_jnt
    else:
        trs = pmc.createNode("transform", n=trs_name)

    trs.addAttr(
        constants.SKIN_PRE_BND_MTX_SRCE_JNT_ATTR_NAME,
        type="string",
        keyable=False,
    )
    trs.addAttr(
        constants.SKIN_PRE_BND_MTX_WS_TRS_TAG,
        type="bool",
        keyable=False,
        dv=True,
    )
    trs.addAttr(constants.PARENT_ND_ATTR_NAME, type="string")
    trs.addAttr(
        constants.SKIN_PRE_BND_MTX_WS_TRS_MASTER_SKINCLUSTER_ATTR_NAME,
        type="string",
    )
    trs.attr(constants.SKIN_PRE_BND_MTX_WS_TRS_MASTER_SKINCLUSTER_ATTR_NAME).set(
        src_skinluster_name
    )
    trs.attr(constants.SKIN_PRE_BND_MTX_SRCE_JNT_ATTR_NAME).set(jnt_name)
    trs.attr(constants.PARENT_ND_ATTR_NAME).set(parent_nd)

    if ws_pos:
        trs.translate.set(ws_pos)

    if ws_rot:
        trs.rotate.set(ws_rot)

    if ws_scale:
        trs.scale.set(ws_scale)

    return trs


def get_pre_bnd_mtx_ws_transforms_from_scene():
    """
    Gets all pre bind matrix transforms of the scene.

    Returns:
        List: Filled with pmc.PyNodes.

    """
    return [
        node
        for node in pmc.ls(type="transform")
        if node.hasAttr(constants.SKIN_PRE_BND_MTX_WS_TRS_TAG)
        and node.attr(constants.SKIN_PRE_BND_MTX_WS_TRS_TAG).get() == True
    ]


def parent_pre_bnd_mtx_ws_transforms(ws_transforms=None):
    """
    Parent the pre bind matrix transforms to corresponding parent node
    which are defined in the meta attributes of the transform.

    Args:
        ws_transforms(list): Given transforms to act on if None will try to find all valid transforms in the scene
                             Default is None.

    """

    ws_transforms = ws_transforms or get_pre_bnd_mtx_ws_transforms_from_scene()

    for ws_trs in ws_transforms:
        parent_nd_str = ws_trs.attr(constants.PARENT_ND_ATTR_NAME).get()

        if not parent_nd_str:
            _LOGGER.warning(
                "{0} has no parent node specified in {1} attribute. Will skip it.".format(
                    ws_trs, constants.PARENT_ND_ATTR_NAME
                )
            )
            continue

        parent_nd = pmc.PyNode(parent_nd_str)
        parent_nd.addChild(ws_trs)


def unparent_pre_bnd_mtx_ws_transforms(ws_transforms=None):
    """
    Unparent the pre bind matrix transforms into open space.

    Args:
        ws_transforms(list): Given transforms to act on if None will try to find all valid transforms in the scene
        Default is None.
    """
    if not ws_transforms:
        ws_transforms = get_pre_bnd_mtx_ws_transforms_from_scene()
    pmc.parent(ws_transforms, None)


def set_parent_nd_pre_bnd_mtx_ws_transforms(ws_transforms=None):
    """
    Set the parent node meta attribute to actual parent of the pre bind mtx transforms.

    Args:
        ws_transforms(list): Given transforms to act on if None will try to find all valid transforms in the scene
        Default is None.

    """
    if not ws_transforms:
        ws_transforms = get_pre_bnd_mtx_ws_transforms_from_scene()

    for ws_trs in ws_transforms:
        parent_nd = ws_trs.getParent()
        if parent_nd:
            ws_trs.attr(constants.PARENT_ND_ATTR_NAME).set(parent_nd.name(long=None))


def connect_pre_bnd_mtx_ws_transforms_to_skincluster(ws_transforms=None):
    """
    Connect the transforms to the given source skincluster which is defined in the metadata on the transform.

    Args:
        ws_transforms(list): Given transforms to act on if None will try to find all valid transforms in the scene.
                             Default is None.

    """
    if not ws_transforms:
        ws_transforms = get_pre_bnd_mtx_ws_transforms_from_scene()
    safe_ws_transforms = []
    for ws_trs in ws_transforms:

        source_jnt_name = ws_trs.attr(
            constants.SKIN_PRE_BND_MTX_SRCE_JNT_ATTR_NAME
        ).get()

        source_jnt = pmc.PyNode(source_jnt_name)

        master_skin_cluster_name = ws_trs.attr(
            constants.SKIN_PRE_BND_MTX_WS_TRS_MASTER_SKINCLUSTER_ATTR_NAME
        ).get()

        master_skin_cluster = pmc.PyNode(master_skin_cluster_name)

        mtx_ports = get_skincluster_mtx_ports_index_from_bnd_jnt(source_jnt)

        mtx_port = str(mtx_ports.get(master_skin_cluster_name, False))

        if not mtx_port:
            raise exceptions.SkinclusterError(
                "{0} not part of source skincluster {1}".format(
                    source_jnt_name, master_skin_cluster_name
                )
            )

        ws_trs.setMatrix(source_jnt.getMatrix(worldSpace=True), worldSpace=True)

        safe_ws_transforms.append((ws_trs, mtx_port, master_skin_cluster))

    for safe_trs, mtx_port, master_skin_cluster in safe_ws_transforms:

        safe_trs.worldInverseMatrix[0].connect(
            master_skin_cluster.bindPreMatrix[int(mtx_port)]
        )


def get_pre_bnd_mtx_ws_transforms_data(ws_transforms=None):

    """
    Get the pre bind matrix tranform metadata as dict.

    Args:
        ws_transforms(list): Given transforms to act on if None will try to find all valid transforms in the scene.
                             Default is None.

    Returns:
        List: Filled with data dicts for each transform.
              [{"ws_trs": "L_bnd_hand_C_001_jnt_pre_bind_trs", "ws_pos": (10, 10, 10),
                "ws_rot": (10, 10, 10), "ws_scale": (1.0, 1.0, 1.0), "parent_nd": "my_buffer_grp",
                "source_bnd_jnt": "L_bnd_hand_C_001_jnt", "master_skin_cluster": "skinCluster1"}]

    """

    ws_transforms = ws_transforms or get_pre_bnd_mtx_ws_transforms_from_scene()

    if not ws_transforms:
        return

    return [
            {
                "ws_trs": str(ws_trs.name(long=None)),
                "ws_pos": pmc.xform(ws_trs, t=True, ws=True, query=True),
                "ws_rot": pmc.xform(ws_trs, ro=True, ws=True, query=True),
                "ws_scale": pmc.xform(ws_trs, s=True, ws=True, query=True),
                "parent_nd": str(ws_trs.attr(constants.PARENT_ND_ATTR_NAME).get()),
                "source_bnd_jnt": str(
                    ws_trs.attr(constants.SKIN_PRE_BND_MTX_SRCE_JNT_ATTR_NAME).get()
                ),
                "master_skin_cluster": str(
                    ws_trs.attr(
                        constants.SKIN_PRE_BND_MTX_WS_TRS_MASTER_SKINCLUSTER_ATTR_NAME
                    ).get()
                ),
            }
            for ws_trs in ws_transforms
        ]


def save_pre_bnd_mtx_ws_transforms_data(prettyprint=False):

    """
    Saves the pre bind matrix data dict as json file with version control.
    With this we can rebuild the whole nodes in the scene.

    Args:
        prettyprint(bool): Will pretty print the data dict into the script editor.
                           Default is False.

    """

    # the actual stuff
    io_manager = ImportExport()

    data_dict = get_pre_bnd_mtx_ws_transforms_data()
    if not data_dict:
        raise LookupError("No data dict exist for pre bind matrix transforms")

    io_manager.write(
            object_name=PRE_BND_MTX_TRS_DATA_LOOKUP_EXPORT_NAME,
            data_to_write=data_dict,
            data_type="json",
    )

    if prettyprint:
        pprint(data_dict)

    return True


def _read_pre_bnd_mtx_ws_transforms_data(prettyprint=False):

    """
    Reads the json data and returns the data as list filled with data dicts.

    Args:
        prettyprint(bool): Will pretty print the data dict into the script editor.
                           Default is False.

    Returns:
        List: Filled with data dicts for each transform.
              [{"ws_trs": "L_bnd_hand_C_001_jnt_pre_bind_trs", "ws_pos": (10, 10, 10),
                "ws_rot": (10, 10, 10), "ws_scale": (1.0, 1.0, 1.0), "parent_nd": "my_buffer_grp",
                "source_bnd_jnt": "L_bnd_hand_C_001_jnt", "master_skin_cluster": "skinCluster1"}]

    """

    io_manager = ImportExport()

    data_lookup_info = io_manager.load(
            object_name=PRE_BND_MTX_TRS_DATA_LOOKUP_EXPORT_NAME,
            data_type="json"
    )

    if prettyprint:
        pprint(data_lookup_info)

    return data_lookup_info



def import_pre_bnd_mtx_ws_transforms_data(prettyprint=False):
    """
    Import the pre bind matrix transforms data json.

    Args:
        prettyprint(bool): Will pretty print the data dict into the script editor.
                           Default is False.
    """
    data_list = _read_pre_bnd_mtx_ws_transforms_data(prettyprint)

    ws_transforms = []
    for data_dict in data_list:
        ws_trs_name = data_dict["ws_trs"]
        parent_nd = data_dict["parent_nd"]
        source_bnd_jnt = pmc.PyNode(data_dict["source_bnd_jnt"])
        master_skc = data_dict["master_skin_cluster"]
        trs = create_pre_bnd_mtx_ws_transform(
            ws_trs_name,
            src_bnd_jnt=source_bnd_jnt,
            src_skinluster_name=master_skc,
            parent_nd=parent_nd,
        )
        ws_transforms.append(trs)
    connect_pre_bnd_mtx_ws_transforms_to_skincluster(ws_transforms)
    parent_pre_bnd_mtx_ws_transforms(ws_transforms)


"""
This module manages to localize skin influences.
"""



CONSTRAINT_TYPES = {"mgear_mtx": "mgear_matrixConstraint",
                    "direct": "None",
                    }

##########################################################
# FUNCTIONS
##########################################################

@DECORATORS.x_timer
@DECORATORS.undo
def localize_skin_influences(
    mesh_trs, constraint_nd_type="mgear_mtx",
):
    """
    Localize the skin incluences of mesh with skincluster inputs.
    This can be used for skincluster stacking and the localized influences
    prefends the geo before a double transformation.

    Args:
        mesh_trs(pmc.PyNode): The mesh transform with skincluster input.
        constraint_nd_type(str): The contsraint type which is the driver of the influence.
                                 Default is the global var MGEAR_MATRIX_CONSTRAINT.

    """
    constraint_nd_type_ = CONSTRAINT_TYPES[constraint_nd_type]

    skin_operator = SkinClusterOperator(mesh_trs.longName())
    skin_operator.gather_scene_internal_data()

    all_influences = [
        pmc.PyNode(inf) for inf in skin_operator.influences["name"]
    ]

    # create our own influence pack with scene data
    inf_pack = []

    for inf in all_influences:
        temp_dict = {}
        ctrl = [
            node
            for node in inf.listHistory()
            if node.hasAttr(RIG_SYS_CONTROL_TAG)
        ]
        temp_dict["bnd_jnt"] = inf
        temp_dict["constraint"] = [
            node
            for node in inf.listHistory()
            if node.nodeType() == constraint_nd_type_
        ]
        temp_dict["ctrl"] = ctrl
        if ctrl:
            ctrl = ctrl[0]
            temp_dict["ctrl"] = ctrl

        temp_dict[
            "mtx_index"
        ] = get_skincluster_mtx_ports_index_from_bnd_jnt(inf)

        inf_pack.append(temp_dict)

    # iterate through the infos
    for pack_dict in inf_pack:

        infl = pack_dict["bnd_jnt"]
        ctrl = pack_dict["ctrl"]
        constraint = pack_dict["constraint"]

        if not ctrl:
            raise LookupError(f"No rig control existing for {infl}.")

        jnt_ws_mtx = infl.getMatrix(worldSpace=True)

        parent_jnt = infl.getParent()

        math_mult_nd_0 = pmc.createNode("math_MultiplyMatrix")
        math_mult_nd_0.input1.set(jnt_ws_mtx)

        parent_jnt.worldInverseMatrix[0].connect(math_mult_nd_0.input2)
        math_mult_nd_1 = pmc.createNode("math_MultiplyMatrix")

        ctrl.matrix.connect(math_mult_nd_1.input1)
        math_mult_nd_0.output.connect(math_mult_nd_1.input2)

        infl.translate.unlock()
        infl.translate.disconnect()

        infl.rotate.unlock()
        infl.rotate.disconnect()

        infl.shear.unlock()
        infl.shear.disconnect()

        for axe in "XYZ":
            infl.attr(f"scale{axe}").unlock()
            infl.attr(f"scale{axe}").disconnect()
            infl.attr(f"scale{axe}").set(1.0)

        infl.translate.set(0.0, 0.0, 0.0)
        infl.rotate.set(0.0, 0.0, 0.0)
        infl.jointOrient.set(0.0, 0.0, 0.0)

        infl.useOutlinerColor.set(True)
        infl.outlinerColor.set(0.5, 1, 0)

        # infl.scale.unlock()
        # infl.scale.set(1.0, 1.0, 1.0)

        # if we are choosing the type of None, we assume floating joints
        # --> this makes the whole rig faster because of direct connections:)

        if constraint_nd_type == "mgear_mtx":
            parent_jnt = infl.getParent()

            math_mult_nd_0 = pmc.createNode("math_MultiplyMatrix")
            math_mult_nd_0.input1.set(jnt_ws_mtx)

            parent_jnt.worldInverseMatrix[0].connect(math_mult_nd_0.input2)

            math_mult_nd_1 = pmc.createNode("math_MultiplyMatrix")

            ctrl.matrix.connect(math_mult_nd_1.input1)

            math_mult_nd_0.output.connect(math_mult_nd_1.input2)

            if not pmc.isConnected(math_mult_nd_1.output, infl.offsetParentMatrix):

                math_mult_nd_1.output.connect(infl.offsetParentMatrix, f=True)

        elif constraint_nd_type == "direct":
            ctrl.translate.connect(infl.translate, f=True)
            ctrl.rotate.connect(infl.rotate, f=True)
            ctrl.scale.connect(infl.scale, f=True)

            infl.offsetParentMatrix.set(jnt_ws_mtx)

        else:
            raise NotImplementedError("behaviour was requested that was not implemented.")

        if constraint:
            pmc.delete(constraint)

    _LOGGER.debug("Finished localizing operation.")


def save_localize_data(
    mesh_list,
    constraint_nd_type="mgear_mtx",
    prettyprint=False,
):
    """
    Save the localize data as json file for easier rebuild.

    Args:
        mesh_list(list): A list filled with meshes as pmc.PyNodes

        constraint_nd_type(str): The contsraint type which is the driver of the influence.
                                 Default is the global var MGEAR_MATRIX_CONSTRAINT.

        prettyprint(bool): Will pretty print the data dict into the script editor.
                           Default is False.

    """

    # the actual stuff
    io_manager = ImportExport()

    mesh_list = [str(node.name(long=None)) for node in mesh_list]

    data_list = [
        {
            "mesh":              mesh_name,
            "constrain_nd_type": constraint_nd_type,
        }
        for mesh_name in mesh_list
    ]

    if not data_list:
        raise LookupError("No data dict exist for pre bind matrix transforms")

    io_manager.write(
            object_name=LOCALIZE_INF_LOOKUP_EXPORT_NAME,
            data_to_write=data_list,
            data_type="json",
    )

    if prettyprint:
        pprint(data_list)

    return True


def localize_skin_influences_for_selection(
    constraint_nd_type="mgear_mtx"
):
    """
    Localize skin influences for selected meshes.

    Args:
        constraint_nd_type(str): The contsraint type which is the driver of the influence.
                                 Default is the global var MGEAR_MATRIX_CONSTRAINT.

    """

    mesh_list = pmc.selected()
    for mesh in mesh_list:
        localize_skin_influences(mesh, constraint_nd_type)


def save_localize_data_from_selection(
    export_path=None, constraint_nd_type="mgear_mtx"
):
    """
    Save the localize data for selected meshes as json files.

    Args:
        export_path(str, path, bool): The export path.
                                      If None will take the data directory of the
                                      asset and create version control srtucture.
        constraint_nd_type(str): The contsraint type which is the driver of the influence.
                                 Default is the global var MGEAR_MATRIX_CONSTRAINT.

    """
    mesh_list = pmc.selected()
    save_localize_data(mesh_list, export_path, constraint_nd_type)


def _read_localize_data(prettyprint=False):
    """
    Read the localize data.

    Args:
        prettyprint(bool): Will pretty print the data dict into the script editor.
                           Default is False.
    """
    io_manager = ImportExport()

    data_lookup_info = io_manager.load(
            object_name=PXO_FILEPATH_SCIF, data_type="json"
    )

    if prettyprint:
        pprint(data_lookup_info)

    return data_lookup_info


def load_and_execute_localize_data(import_path=None):
    """
    Load the localize data and create localizing setups based on the saved data.

    Args:
        import_path(str, path, bool): If false, searches in scene directory, if str or path given, it looks there.

    """
    data_list = _read_localize_data(import_path)
    for data_dict in data_list:
        mesh_trs = pmc.PyNode(data_dict["mesh"])
        constrain_type = data_dict["constrain_nd_type"]
        localize_skin_influences(mesh_trs, constrain_type)


def main():
    raise NotImplementedError()


if __name__ == "__main__":
    main()