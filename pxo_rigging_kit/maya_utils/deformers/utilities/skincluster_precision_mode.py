import logging
import numpy # noqa: import error
from typing import Optional

from maya import cmds # noqa: import error
from maya.api import OpenMaya as om2 # noqa: import error
import pymel.core as pmc # noqa: import error

from pxo_rigging_kit import constants
from pxo_rigging_kit.io_version_control.version_io import ImportExport
from pxo_rigging_kit.maya_utils import model_utils, exceptions, decorators
from pxo_rigging_kit.maya_utils.deformers.operators.skincluster_op import SkinClusterOperator, get_skin_cluster
from pxo_rigging_kit.maya_utils.openmaya_utils import get_tagged_nodes

_LOGGER = logging.getLogger(f"{__name__}.py")
_LOGGER.setLevel(logging.INFO)

DECORATORS = decorators.Decorators()
DECORATORS.debug = True
DECORATORS.logger = _LOGGER


##########################################################
# FUNCTIONS
##########################################################


def _make_skin_cluster_deformation_local(geo):
    """
    Localizes the calculation of the skin cluster by converting the joints world space to the object space of the geometry.

    Args:
        geo(pymel.core.PyNode): Geometry for which operations should be performed.

    Returns:
        None
    """

    if not get_skin_cluster(geo):
        return

    geo_name = f"{geo.shortName()}"
    geo_parent_name = f"{geo.getParent().longName()}"

    geo_world_attr_name = f"{geo_parent_name}.worldInverseMatrix[0]"

    skin_operator = SkinClusterOperator(geo.longName())

    skin_operator.rebuild_pruned()

    names = skin_operator.influence_names.tolist()

    mult_nodes = create_matrix_mult_from_influences(
        names=names, geo_name=geo_name
    )

    for index_, name_ in enumerate(names):
        id_name = str(index_)
        name_name = str(name_)
        mult_node_name = str(mult_nodes[index_])

        cmds.connectAttr(
            f"{name_name}.worldMatrix[0]",
            f"{mult_node_name}.input1",
        )

        cmds.connectAttr(
            geo_world_attr_name,
            f"{mult_node_name}.input2",
        )

        cmds.connectAttr(
            f"{mult_node_name}.output",
            f"{skin_operator.deformer_name}.matrix[{id_name}]",
            force=True,
        )

    skin_operator.deformer_node.addAttr(
            constants.SKIN_PRECISION_MODE_NODE_TAG, at="bool", dv=True
        )

    return True


def create_matrix_mult_from_influences(names: Optional[str] = None,
                                       geo_name: str = "default"
                                       ):
    """
    Creates the multiply matrix nodes needed for the skin save mode.

    Args:
        names(list | None): List of the influences as string.
        geo_name(str): Name of the geo as string.

    Returns:
        List(mult_matrices): Names of the mult matrix nodes as str.
    """

    mult_matrices = list()

    for iteration_, name_str in enumerate(names):
        clean_name = str(name_str).split("|")[-1]

        object_space_mult_name = f"invert{clean_name}{iteration_}_{geo_name}_mMtx"

        object_space_mult_nde = pmc.createNode(
            "math_MultiplyMatrix", n=object_space_mult_name
        )

        object_space_mult_nde.addAttr(
            constants.SKIN_PRECISION_MODE_NODE_TAG, at="bool", dv=True
        )

        object_space_mult_nde.isHistoricallyInteresting.set(False, lock=True)

        mult_matrices.append(object_space_mult_name)

    return mult_matrices


def correct_rig_world_precision_issue(control_node=None):
    """
    Searches the scene for a tagged node, or takes the provided one.
    Moves the inputs of the skin-cluster into the space of the control.
    And constraints the mdl root nd to the tagged control which is the specified root node for the system.

    Args:
        control_node(pymel.core.PyNode): The object that is the control under which the system will be generated.

    Returns:
        None
    """
    skin_precision_parent_tag_ = constants.SKIN_PRECISION_MODE_NODE_TAG

    revert_rig_world_precision_issue()

    sel = pmc.selected()

    if sel:
        sel = sel[0]

    control_node = control_node or get_world_precision_sys_root_ctrl() or sel

    if not control_node:
        raise exceptions.SkinPrecisionError("No master control node was found!")

    mdl_geos, mdl_roots = model_utils.get_mdl_geos()
    _LOGGER.info(f"Got model geos {mdl_geos} and roots {mdl_roots}.")

    for transform_ in mdl_geos:
        _make_skin_cluster_deformation_local(transform_)

    _LOGGER.info("Made Skin Clusters local.")

    constraints_ = [
        pmc.parentConstraint(control_node, mdl_root)
        for mdl_root
        in mdl_roots
    ]

    for const_ in constraints_:
        const_.addAttr(skin_precision_parent_tag_, at="bool", dv=True)
        const_.interpType.set(2, lock=True)

    # here needs to be an option to add the tagging bruh
    _LOGGER.info("Added constraints for Skin Cluster precision mode")


def revert_rig_world_precision_issue(remove_tagging=False):
    """
    Searches scene for tagged nodes, then removes them.
    The inputs of the skin clusters are coming from joints worldMatrices again.

    Returns:
        Bool: True if run through.
    """
    skin_precision_parent_tag_ = constants.SKIN_PRECISION_MODE_NODE_TAG
    mdl_geos, mdl_roots = model_utils.get_mdl_geos()

    # connection hop from weight info back
    mult_matrix_nodes = [
        x
        for x in pmc.ls(type="math_MultiplyMatrix")
        if x.hasAttr(skin_precision_parent_tag_)
    ]

    parent_constraints = [
        x
        for x in pmc.ls(type="parentConstraint")
        if x.hasAttr(skin_precision_parent_tag_)
    ]

    if not mult_matrix_nodes and not parent_constraints:
        _LOGGER.info("Found no tagged precision nodes!")
        return

    matrix_outputs = [
        x.output.listConnections(destination=True, plugs=True)[0]
        for x in mult_matrix_nodes
    ]

    matrix_inputs = [
        x.input1.listConnections(source=True, plugs=True)[0]
        for x in mult_matrix_nodes
    ]

    matrix_combined = list(zip(matrix_inputs, matrix_outputs))

    [
        matrix_input.connect(matrix_output, force=True)
        for matrix_input, matrix_output in matrix_combined
    ]

    pmc.delete(mult_matrix_nodes)
    pmc.delete(parent_constraints)

    for mdl_root in mdl_roots:
        for axis in "xyz":
            for transform_type in "rt":
                mdl_root.attr(f"{transform_type}{axis}").set(0)

            for transform_type in "s":
                mdl_root.attr(f"{transform_type}{axis}").set(1)

    if remove_tagging:
        remove_precision_mode_tagged_nodes()
        _LOGGER.info("Ran conversion operation in remove tagging mode")

    else:
        deactivate_precision_mode_tagged_nodes()
        _LOGGER.info("Ran conversion operation in deactivate tagging mode")

    return True


def set_world_precision_sys_root_ctrl(control_node: Optional[pmc.PyNode] = None):
    """
    Tags either the given control or the first in selection as the master node for the skin cluster save mode.

    Args:
        control_node(pmc.PyNode | None): the node to be set as SKIN_SAVE_MODE_PARENT.

    Returns:
        None
    """

    skin_precision_parent_tag_ = constants.SKIN_PRECISION_PARENT_TAG

    sel = pmc.selected()

    if sel:
        sel = sel[0]

    control_node = control_node or sel

    if not control_node:
        raise exceptions.SkinPrecisionError(
            "No input given for [set_tagged_control()]!"
        )

    remove_precision_mode_tagged_nodes()

    control_node.addAttr(skin_precision_parent_tag_,
                         at="bool",
                         )

    control_node.attr(skin_precision_parent_tag_).set(True,
                                                      lock=True,
                                                      )
    _LOGGER.info(f"Added tagging for skincluster precision mode for {control_node.longName()}")


def get_world_precision_sys_root_ctrl():
    """
    Searches the scene for tagged controls, returns the first found. If multiples are found, throws an error.

    Returns:
        pymel.core.PyNode: The tagged node.
    """
    skin_precision_parent_tag_ = constants.SKIN_PRECISION_PARENT_TAG

    tagged_nodes = get_tagged_nodes(tag=skin_precision_parent_tag_,
                                    mfn_type=om2.MFn.kTransform)

    # checks if set is empty by converting it into bool --> if bool True its not empty
    if not bool(tagged_nodes):
        _LOGGER.info(
            f"No node was tagged with {skin_precision_parent_tag_}."
        )
        return

    if len(tagged_nodes) > 1:
        exceptions.SkinPrecisionError(
            f"Too many nodes were tagged with [{skin_precision_parent_tag_}]"
        )

    _LOGGER.info(f"Found {tagged_nodes}")

    found_master = tagged_nodes.pop()

    _LOGGER.info(f"Picked {found_master}")

    found_master_node = pmc.PyNode(found_master)

    return found_master_node


def remove_precision_mode_tagged_nodes():
    """Removes all tags that are from the skin cluster save mode.

    Returns:
        None
    """

    skin_precision_parent_tag_ = constants.SKIN_PRECISION_PARENT_TAG

    tagged_node = get_world_precision_sys_root_ctrl()

    if not tagged_node:
        _LOGGER.info("No tagged node found. Skipping Removal."
                     )
        return

    if not tagged_node.hasAttr(skin_precision_parent_tag_):
        _LOGGER.info(f"No Tag Attr {skin_precision_parent_tag_} found. "
                     f"No tag removed from {tagged_node.longName()}."
                     f"Skipping Removal."
                     )
        return

    # unlock the attr
    tagged_node.attr(skin_precision_parent_tag_).set(lock=False)

    # delete the attr
    pmc.deleteAttr(tagged_node.attr(skin_precision_parent_tag_))

    _LOGGER.info(f"Removed the tag for skincluster precision mode on {tagged_node.longName()}.")


def deactivate_precision_mode_tagged_nodes():
    """Removes all tags that are from the skin cluster save mode.

    Returns:
        None
    """

    skin_precision_parent_tag_ = constants.SKIN_PRECISION_PARENT_TAG

    tagged_node = get_world_precision_sys_root_ctrl()

    tagged_node.attr(skin_precision_parent_tag_).set(lock=False)
    tagged_node.attr(skin_precision_parent_tag_).set(False, lock=True)

    _LOGGER.info(f"Deactivated the tag for skincluster precision mode on {tagged_node.longName()}.")


def _get_export_data():
    skin_precision_parent_tag_ = constants.SKIN_PRECISION_PARENT_TAG

    tagged_node = get_world_precision_sys_root_ctrl()

    tagged_name = str(tagged_node.longName())

    try:
        active = tagged_node.attr(skin_precision_parent_tag_).get()

    except pmc.general.MayaAttributeError as e:
        raise exceptions.SkinPrecisionError(f"Could not get precision tag: {skin_precision_parent_tag_}. {e}.")

    export_data_ = {tagged_name: active}

    _LOGGER.info(f"Found Data: {export_data_} for Export.")

    return export_data_


def save():
    export_data = _get_export_data()

    io_manager = ImportExport()

    io_manager.write(
        object_name=f"body_long_test",
        data_to_write=export_data,
        data_type=constants.JSON,
        data_category=constants.PXO_FILEPATH_SKPC,
    )


def load():
    io_manager = ImportExport()

    import_data = io_manager.load(
        object_name="body_long_test",
        data_type=constants.JSON,
        data_file_name=None,
        version=-1,
        as_path=False,
        data_category=constants.PXO_FILEPATH_SKPC,

    )

    for ctrl_key in import_data:
        set_world_precision_sys_root_ctrl(control_node=pmc.PyNode(ctrl_key))

    correct_rig_world_precision_issue()
