# Author:     Christof Puehringer / Rigging TD
#             Johannes Woz / Head of Rigging

"""
Module for layering the skincluster as a stack.
This is a new approach to create deformation stacks in a gpu friendly way.
This manages skinlayer creation data and proxy mesh creations for a nondestructive rig build.

Example:

>>> import pymel.core as pmc
>>> from pxo_rigging_kit.maya_utils.deformers.utilities import skincluster_layering
# With this you create the skinlayer proxy meshes from selected geos. It will create an amount of 2 by default.
# This will create the proxie meshes and the corresponding object sets.
# We use the objects sets as processing data instead of meta attributes.
>>> skincluster_layering.create_skin_merge_sets_from_selection()
# Or use this if you want to create the proxies wit a given node. It will create an amount of 2 by default.
# This will create the proxie meshes and the corresponding object sets.
# We use the objects sets as processing data instead of meta attributes.
>>> skincluster_layering.create_skin_merge_proxies_and_sets(node)
# When you have your proxies skinned you can create the stack with this.
>>> skincluster_layering.create_skincluster_stacks()
"""


# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from future import standard_library

# Import built-in modules
# Import standart python modules
from pprint import pprint
import random
import logging
import numpy as np  # noqa: import error

# Import maya modules
from maya.api import OpenMaya as om2  # noqa: import error
from pymel import core as pmc

from pxo_rigging_kit import constants

from pxo_rigging_kit.constants import SKINLAYER_LOOKUP_EXPORT_NAME
from pxo_rigging_kit.constants import SKIN_LAYER_FLAG
from pxo_rigging_kit.constants import SKIN_LAYER_GEO_TAG
from pxo_rigging_kit.constants import SKIN_LAYER_INDEX
from pxo_rigging_kit.constants import SKIN_MERGE_DESTINATION_FLAG
from pxo_rigging_kit.constants import SKIN_MERGE_FLAG
from pxo_rigging_kit.constants import PXO_FILEPATH_SCIF
from pxo_rigging_kit.constants import LOCALIZE_INF_LOOKUP_EXPORT_NAME
from pxo_rigging_kit.constants import RIG_SYS_CONTROL_TAG
from pxo_rigging_kit.constants import PRE_BND_MTX_TRS_DATA_LOOKUP_EXPORT_NAME

# Import locals
from pxo_rigging_kit.io_version_control.version_io import ImportExport

from pxo_rigging_kit.maya_utils import decorators
from pxo_rigging_kit.maya_utils import exceptions

from pxo_rigging_kit.maya_utils.dag_utils import delete_hidden_shapes
from pxo_rigging_kit.maya_utils.dag_utils import get_deform_shape

from pxo_rigging_kit.maya_utils.deformers.operators.skincluster_op import SkinClusterOperator, get_skin_cluster

from pxo_rigging_kit.maya_utils.openmaya_utils import get_complete_components_om2
from pxo_rigging_kit.maya_utils.openmaya_utils import get_dag_path_om2
from pxo_rigging_kit.maya_utils.openmaya_utils import get_mfn_mesh_om2
from pxo_rigging_kit.maya_utils.openmaya_utils import get_mfn_skin_om2

from pxo_rigging_kit.maya_utils.rigging import rig_utils


##########################################################
# GLOBALS
##########################################################

standard_library.install_aliases()

_LOGGER = logging.getLogger(f"{__name__}.py")
_LOGGER.setLevel(logging.INFO)

DECORATORS = decorators.Decorators()
DECORATORS.debug = True
DECORATORS.logger = _LOGGER

DEFAULT_ROOT_SUFFIX = "_root"


##########################################################
# DYNAMIC LOCALS
##########################################################

_MERGE_BASE_NAME = "SKINMERGE"
_LAYER_BASE_NAME = "SKINLAYER"
_DEFAULT_MESH_NAME = "MESH_NAME"

##########################################################
# DYNAMIC FUNCTIONS
##########################################################


def create_skin_proxy_layer_sets(geo_name=None, layer_amount=2):
    """
    Creates the skin proxy layer sets.
    Which we use to know which mesh is which layer and which mesh is the targt mesh.

    Args:
        geo_name(str): The target mesh name. The name will be included in the sets name.
                       If None will use a placeholder in the name. Holder is "MESH_NAME".
        layer_amount(int): The amount of layers you want to create.
                           Default is 2.

    Returns:
            Dict: {
                   "skin_merge_root_set": pmc.PyNode(),
                   "skin_merge_layers_set": {"0": pmc.PyNode(), "1": pmc.PyNode()},
                   "destination_set": pmc.PyNode()
                   }

    """
    if not geo_name:
        geo_name = _DEFAULT_MESH_NAME

    root_set = pmc.createNode(
        "objectSet",
        n=f"{_MERGE_BASE_NAME}_{geo_name}_set",
    )

    layer_sets = [
        pmc.createNode(
            "objectSet",
            n=f"{_LAYER_BASE_NAME}_{layer_idx}_{geo_name}_set",
        )
        for layer_idx in range(layer_amount)
    ]

    destination_set = [
        pmc.createNode(
            "objectSet",
            n=f"{_MERGE_BASE_NAME}_{geo_name}_destination_set",
        )
    ]

    root_set.addMembers(destination_set + layer_sets)

    root_set.addAttr(
        SKIN_MERGE_FLAG,
        at="bool",
        dv=1,
        keyable=False,
    )

    destination_set[0].addAttr(
        SKIN_MERGE_DESTINATION_FLAG,
        at="bool",
        dv=1,
        keyable=False,
    )

    for (index, layer_set) in enumerate(layer_sets):
        layer_set.addAttr(SKIN_LAYER_FLAG,
                          at="bool",
                          dv=1,
                          keyable=False,
                          )

        layer_set.addAttr(SKIN_LAYER_INDEX,
                          dv=index,
                          at="long",
                          keyable=False,
                          )

    if pmc.objExists("delete_on_publish"):
        pmc.PyNode("delete_on_publish").addMembers(root_set)

    return {
        "skin_merge_root_set": root_set,
        "skin_merge_layers_set": {
            f"{index}": layer_set
            for (index, layer_set) in enumerate(layer_sets)
        },
        "destination_set": destination_set[0],
    }


def create_skin_merge_proxies_and_sets(geometry=None, layer_amount=2):
    """
    Creates the skin merge proxies and the sets.
    And it will fill the sets with the corresponding meshes.

    Args:
        geometry(pmc.PyNode()): The geometrie you want to create the proxies from.
        layer_amount(int): The amount of layers you want to create.
                           Default is 2.

    """
    geo_name = None

    if geometry:
        geo_name = geometry.name(long=None, stripNamespace=True)

    layer_sets_dict = create_skin_proxy_layer_sets(geo_name, layer_amount)
    layer_sets = layer_sets_dict["skin_merge_layers_set"]

    if not geometry:
        return False

    mesh_duplicates = []

    mesh_duplicate_names = [
        f"{_LAYER_BASE_NAME}_{index}_{geo_name}"
        for index in range(layer_amount)
    ]
    # TODO: this needs fixing
    ground_color_rgb = (
        random.uniform(0, 1),
        random.uniform(0, 1),
        random.uniform(0, 1),
    )

    for layer_number, mesh_name in enumerate(mesh_duplicate_names):

        try:
            mesh_dupl = pmc.PyNode(mesh_name)

        except pmc.MayaNodeError:
            mesh_dupl = pmc.duplicate(geometry, n=mesh_name)[0]
            pmc.parent(mesh_dupl, None)
            delete_hidden_shapes(mesh_dupl)

            mesh_dupl.useOutlinerColor.set(True)
            mesh_dupl.outlinerColorR.set(ground_color_rgb[0] * layer_number)
            mesh_dupl.outlinerColorG.set(ground_color_rgb[1])
            mesh_dupl.outlinerColorB.set(ground_color_rgb[2])

            for user_defined_attr in mesh_dupl.listAttr(ud=True):
                user_defined_attr.delete()

            mesh_dupl.addAttr(SKIN_LAYER_GEO_TAG,
                              at="bool",
                              )

            mesh_dupl.attr(SKIN_LAYER_GEO_TAG).set(True,
                                                   l=True,
                                                   )

            if pmc.objExists("delete_on_publish"):
                pmc.sets("delete_on_publish",
                         forceElement=mesh_dupl,
                         )

        mesh_duplicates.append(mesh_dupl)

    layer_sets_dict["destination_set"].addMember(geometry)

    for (index, layer_set) in enumerate(mesh_duplicates):
        layer_sets[str(index)].addMember(layer_set)

    return mesh_duplicates


def create_skin_merge_sets_from_selection(layer_amount=3):
    """
    Create the skin merge proxies and sets from selection in maya.

    Args:
        layer_amount(int): The amount of layers you want to create.
                           Default is 3.

    Returns:
        List: Created layer meshes as pmc.PyNodes.

    """
    selection = pmc.ls(sl=True)
    return sum([create_skin_merge_proxies_and_sets(node, layer_amount) for node in selection], [])


def get_skin_merge_sets():
    """
    Get the skin merge sets from the scene.

    Returns:
        None if none exists.
        List filled with data dict:
        [{"root_set": pmc.PyNode(), "destination_set": [pmc.PyNode()], "layer_sets": [pmc.PyNode()]}]

    """
    root_sets = [
        node
        for node in pmc.ls(type="objectSet")
        if node.hasAttr(SKIN_MERGE_FLAG)
        and node.attr(SKIN_MERGE_FLAG).get() is True
    ]

    if not root_sets:
        return

    result = [
        {
            "root_set": root_set,
            "destination_set": [
                node
                for node in root_set.members()
                if node.hasAttr(SKIN_MERGE_DESTINATION_FLAG)
                and node.attr(SKIN_MERGE_DESTINATION_FLAG).get() is True
            ],
            "layer_sets": [
                node
                for node in root_set.members()
                if node.hasAttr(SKIN_LAYER_FLAG)
                and node.attr(SKIN_LAYER_FLAG).get() is True
            ],
        }
        for root_set in root_sets
    ]
    return result


def get_skin_merge_data(as_strings=False):
    """
    Get the skin merge data.

    Args:
        as_strings(bool): The data as strings.
                          If False will generate pmc.PyNode().

    Returns:
        None if no exists.
        List filled with data dict:
        [{"destination": pmc.PyNode/or string, "skin_layers": {"0": pmc.PyNode, "1": pmc.PyNode}}]
    """
    result = []
    skin_merge_sets = get_skin_merge_sets()

    if not skin_merge_sets:
        return

    for data_dict in skin_merge_sets:
        temp_dict = {}
        layer_sets = data_dict["layer_sets"]

        if as_strings:
            temp_dict["destination"] = str(
                data_dict["destination_set"][0]
                .members()[0]
                .name(long=False)
            )
        else:
            temp_dict["destination"] = data_dict["destination_set"][0].members()[0]

        temp_dict["skin_layers"] = {}

        if not layer_sets:
            continue

        if as_strings:
            temp_dict["skin_layers"] = {
                f"{node.attr(SKIN_LAYER_INDEX).get()}": [
                    str(node_) for node_ in node.members()
                ][0]
                for node in layer_sets
            }
        else:
            temp_dict["skin_layers"] = {
                str(node.attr(SKIN_LAYER_INDEX).get()): node.members()[
                    0
                ]
                for node in layer_sets
            }

        result.append(temp_dict)
    return result


def try_matrix_set(plug, value):
    """
    Try to set the matrix skin port.
    Will just pass with a RuntimeError if failing because of anything.

    Args:
        plug(pmc.Attribute): The matrix plug.
        value(float): The values to set

    """
    try:
        plug.set(value)
    except RuntimeError:
        pass


def try_matrix_connect(plug, target):
    """
    Try to connect the matrix skin port.
    Will just pass with a RuntimeError if failing because of anything.

    Args:
        plug(pmc.Attribute): The matrix plug.
        target(pmc.Attribute): The values to set

    """
    try:
        if plug not in target.inputs():
            plug.connect(target)

    except RuntimeError:
        pass


def transfer_skincluster(source, source_skin, target, target_skin):
    """
    Transfer the source skincluster to given target.
    Will grab matrix and pre bind matrix inputs as well.

    Args:
        source(pmc.PyNode or str): The source mesh.
        source_skin(pmc.PyNode): The source skin cluster name.
        target(pmc.PyNode): The target mesh.
        target_skin(pmc.PyNode): The target skin cluster name.

    """
    source_shape = get_deform_shape(source)
    source_dp = get_dag_path_om2(source_shape.longName())
    source_mfn = get_mfn_skin_om2(source_skin)
    source_mesh = get_mfn_mesh_om2(get_deform_shape(source))

    components, _ = get_complete_components_om2(source_mesh)

    weights, influence_count = source_mfn.getWeights(source_dp, components)

    # copy over input values / connections
    bind_inputs = [
        (x.inputs(plugs=True)[0] if x.isConnected() else None)
        for x in source_skin.bindPreMatrix
    ]

    bind_values = [x.get() for x in source_skin.bindPreMatrix]
    mat_inputs = [
        (x.inputs(plugs=True)[0] if x.isConnected() else None)
        for x in source_skin.matrix
    ]
    mat_values = [x.get() for x in source_skin.matrix]

    for index, bind_value, mat_value in zip(
        range(influence_count), bind_values, mat_values
    ):
        # can't be guaranteed what state things will be in at this point
        # so set them in a try/catch
        try_matrix_set(target_skin.bindPreMatrix[index], bind_value)
        try_matrix_set(target_skin.matrix[index], mat_value)

    for index, bind_input, mat_input in zip(
        range(influence_count), bind_inputs, mat_inputs
    ):
        if bind_input:
            try_matrix_connect(bind_input, target_skin.bindPreMatrix[index])

        if mat_input:
            try_matrix_connect(mat_input, target_skin.matrix[index])

    # copy over weights
    target_mfn = get_mfn_skin_om2(target_skin)
    target_shape = get_deform_shape(target)
    target_mesh = get_mfn_mesh_om2(target_shape)
    target_dp = get_dag_path_om2(target_shape.longName())
    components, _ = get_complete_components_om2(target_mesh)
    all_indices = om2.MIntArray(range(influence_count))

    target_mfn.setWeights(target_dp, components, all_indices, weights)

    # same as with loading and saving, we want to normalize and
    # recache the bind matrices
    pmc.skinPercent(target_skin, target_shape, normalize=True)  # tere is a flag in setWeights, not sure if this is smart
    target_skin.recacheBindMatrices()


@DECORATORS.x_timer
def transfer_skin_layer(source, target, index):
    """
    Transfer skin layer mesh data over.
    Will grab matrix and pre bind matrix inputs as well.

    Args:
        source(pmc.PyNode): The source mesh.
        target(pmc.PyNode): The target mesh.
        index(int): The layer index

    """
    # TODO: add proper skincluster getter
    source_shape = source.getShape(noIntermediate=True) if source.type() == 'transform' else source

    history = pmc.listHistory(source_shape, pruneDagObjects=True)

    skins = [h for h in history if h.type() == 'skinCluster']

    source_skin = skins[0] if skins else None

    if not source_skin:
        raise RuntimeError(f"Source mesh '{source}' has no skinCluster to transfer from.")

    target_shape = target.getShape(noIntermediate=True) if target.type() == 'transform' else target

    target_history = pmc.listHistory(target_shape, pruneDagObjects=True)

    all_target_skins = [h for h in target_history if h.type() == 'skinCluster']

    skin_layer_name = f"{target.name(long=None, stripNamespace=True)}_LAYER_{index}_SKC"

    if all_target_skins:
        target_skin = pmc.deformer(
            target, type="skinCluster", n=skin_layer_name
        )[0]
    else:
        source_influences = source_skin.influenceObjects()
        pmc.select(source_influences, target, r=True)
        target_skin = pmc.skinCluster(tsb=True, mi=3, dr=4.0, n=skin_layer_name)

    target_skin.weightDistribution.set(1)
    transfer_skincluster(source, source_skin, target, target_skin)


def decompose_skincluster_layering():
    raise NotImplementedError()


def get_skinclusters_from_shape(shape_node):
    """

    Args:
        shape_node(pymel.core.PyNode): The shape node which shall be queried.

    Returns:
        List: Skinclusters found in the deformation stack of the shape.
    """
    return list(
            filter(
                    lambda x: x.type() == "skinCluster", rig_utils.get_deformers_for_shape(shape_node)
            )
    )


def create_skincluster_stacks():
    """
    Create the skincluster stacks based on the skin layer data in the scene.
    """

    skin_merge_data = get_skin_merge_data()
    if not skin_merge_data:
        return

    for data_dict in skin_merge_data:
        layers = data_dict["skin_layers"]
        destination_mesh = data_dict["destination"]

        skin_cluster = get_skin_cluster(pmc.PyNode(destination_mesh))

        if skin_cluster:
            pmc.skinCluster(skin_cluster, edit=True, unbind=True)

        if not layers:
            _LOGGER.warning(
                f"{destination_mesh}: has no skin layer data for stacking. Will skip it."
            )
            continue

        for layer_index, layer_mesh in sorted(layers.items()):

            transfer_skin_layer(layer_mesh,
                                destination_mesh,
                                layer_index,
                                )


def save_skinlayer_data(export_path=None, prettyprint=True):
    """
    Save the skinlayer data as json file for a rebuild.

    Args:
        export_path(str): The export path
                          If None it auto generate a directory with version control
                          in the data directory of the asset we are working on.
                          But this requieres an PXO anv whihc you will have when you are working with PXO save/load.
                          Default is None.

        prettyprint(bool): Will pretty print the data dict into the script editor.
                           Default is False.

    """
    skin_layer_data = get_skin_merge_data(True)

    if not skin_layer_data:
        raise LookupError("No data dict exist for pre bind matrix transforms")

    io_manager = ImportExport()

    io_manager.write(
        object_name=SKINLAYER_LOOKUP_EXPORT_NAME,
        data_to_write=skin_layer_data,
        data_type="json",
    )

    if prettyprint:
        pprint(skin_layer_data)

    return skin_layer_data


def load_skinlayer_data(import_path=None,
                        prettyprint=True
                        ):
    """
    Load the skinlayer data from json file and rebuild the layer geos.

    Args:
        import_path(str): The json file path.
                          If None will take latest file found in the version control
                          directory of the assets data directory.
                          Default is None.
        prettyprint(bool): Will pretty print the data dict into the script editor.
                           Default is False.

    Returns:
        List: Created layer meshes as pmc.PyNodes.

    """

    io_manager = ImportExport()

    import_data = io_manager.load(
        object_name=SKINLAYER_LOOKUP_EXPORT_NAME,
        data_type="json",
        data_file_name=None,
        version=-1,
        as_path=False,
    )

    result = []

    for data_dict in import_data:
        destination_mesh = data_dict["destination"]

        destination_mesh = pmc.PyNode(destination_mesh)

        amount = len(data_dict["skin_layers"].keys())

        merge_meshes = create_skin_merge_proxies_and_sets(destination_mesh, amount)

        result.extend(merge_meshes)

    if prettyprint:
        pprint(result)

    return result


@DECORATORS.x_timer
def create_bind_pre_matrix_transforms(geo):
    """
    Create the transforms which are connected to the pre bind matrix of the skin cluster.
    The transforms are in the same world space position like the connected joint influences and can be used to
    reset the rest pose of each influence.

    Args:
        geo(pmc.PyNode): The geometry with the connected skin cluster.

    Returns:
        List: pmc.PyNodes().

    """

    skin_operator = SkinClusterOperator(geo.longName())
    skin_operator.gather_scene_internal_data()

    joints_pack = np.column_stack((skin_operator.influences["index"],
                                   skin_operator.influences["name"],
                                   )
                                  )

    joints_pack = joints_pack.tolist()

    transforms = []

    for pkg in joints_pack:
        jnt_name = pkg[1]

        trs_name = f"{jnt_name.split('|')[-1]}_bindPre_trs"

        jnt = pmc.PyNode(jnt_name)

        try:
            trs = pmc.PyNode(trs_name)
            rig_utils.compare_world_positions(jnt, trs)

        except pmc.MayaNodeError:
            trs = create_pre_bnd_mtx_ws_transform(
                trs_name, jnt, skin_operator.deformer_name
            )

        transforms.append((pkg[0], trs))

    for index, trs in transforms:
        trs.worldInverseMatrix[0].connect(pmc.PyNode(skin_operator.deformer_name).bindPreMatrix[index])

    return transforms


def create_pre_bnd_mtx_ws_transform(trs_name,
                                    src_bnd_jnt=None,
                                    src_skin_cluster_name="",
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
        src_bnd_jnt(str or pmc.PyNode()): The Joint which is the matrix input of the skin cluster.
                                          If string is given the created transform will be world origin and
                                          the given string is the value of the source bind joint meta attribute
                                          on the transform.
                                          If None transform gets no entry in the source bind joint meta attribute and
                                          the created transform will be world origin.
                                          This attribute is used to find the matrix port ID of the given bind joint
                                          which represent the same port ID at the pre bin matrix plug for the transform.
                                          Furthermore, the transform will be in the
                                          world space position of this transform.

        src_skin_cluster_name(str): Source skin cluster name as value of the source skin cluster meta attribute.
                                  This attribute is used to connect the transform to the corresponding skin cluster.
                                  Default is an empty string.

        parent_nd(str): Parent node name as value for the parent_nd meta attribute.
                        This attribute exist for parenting and un-parenting of the transform.
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
        src_skin_cluster_name
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
        and node.attr(constants.SKIN_PRE_BND_MTX_WS_TRS_TAG).get() is True
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
                f"{ws_trs} has no parent node specified "
                f"in {constants.PARENT_ND_ATTR_NAME} attribute. Will skip it."
            )
            continue

        parent_nd = pmc.PyNode(parent_nd_str)
        parent_nd.addChild(ws_trs)


def unparent_pre_bnd_mtx_ws_transforms(ws_transforms=None):
    """
    Un-parent the pre bind matrix transforms into open space.

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


def get_skincluster_mtx_ports_index_from_bnd_jnt(jnt):
    """
    Get the skin cluster matrix port indexes from given joint.
    The joint can be an influence of multiple skin clusters.

    Args:
        jnt(pmc.PyNode): The joint to act on.

    Returns:
        Dict: {"skinCluster1": 45, "skinCluster2": 15}

    """
    skinclusters = jnt.worldMatrix[0].connections(type="skinCluster")
    return {str(skc.name()): skc.indexForInfluenceObject(jnt) for skc in skinclusters}


def connect_pre_bnd_mtx_ws_transforms_to_skincluster(ws_transforms=None):
    """
    Connect the transforms to the given source skin cluster which is defined in the metadata on the transform.

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
                f"{source_jnt_name} not part of source skin cluster {master_skin_cluster_name}"
            )

        ws_trs.setMatrix(source_jnt.getMatrix(worldSpace=True),
                         worldSpace=True,
                         )

        safe_ws_transforms.append((ws_trs, mtx_port,
                                   master_skin_cluster,
                                   )
                                  )

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
                "ws_pos": pmc.xform(ws_trs,
                                    t=True,
                                    ws=True,
                                    query=True
                                    ),
                "ws_rot": pmc.xform(ws_trs,
                                    ro=True,
                                    ws=True,
                                    query=True
                                    ),
                "ws_scale": pmc.xform(ws_trs,
                                      s=True,
                                      ws=True,
                                      query=True
                                      ),
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
            src_skin_cluster_name=master_skc,
            parent_nd=parent_nd,
        )

        ws_transforms.append(trs)

    connect_pre_bnd_mtx_ws_transforms_to_skincluster(ws_transforms)

    parent_pre_bnd_mtx_ws_transforms(ws_transforms)


"""
This module manages to localize skin influences.
"""


##########################################################
# FUNCTIONS
##########################################################


@DECORATORS.x_timer
@DECORATORS.undo
def localize_skin_influences(
    mesh_trs, constraint_nd_type=constants.MGEAR_MATRIX_CONSTRAINT,
):
    """
    Localize the skin influences of mesh with skin cluster inputs.
    This can be used for skin cluster stacking and the localized influences
    prevents the geo before a double transformation.

    Args:
        mesh_trs(pmc.PyNode): The mesh transform with skin cluster input.
        constraint_nd_type(str): The consraint type which is the driver of the influence.
                                 Default is the global var MGEAR_MATRIX_CONSTRAINT.

    """
    constraint_nd_type_ = constants.CONSTRAINT_TYPES[constraint_nd_type]

    skin_operator = SkinClusterOperator(mesh_trs.longName())
    skin_operator.gather_scene_internal_data()

    all_influences = [
        pmc.PyNode(inf) for inf in skin_operator.influences["name"]
    ]

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

    for pack_dict in inf_pack:
        infl = pack_dict["bnd_jnt"]

        ctrl = pack_dict["ctrl"]

        constraint = pack_dict["constraint"]

        if not ctrl:
            raise LookupError(f"No rig control existing for {infl}")

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

        for axe in "XYZ":
            infl.attr(f"scale{axe}").unlock()
            infl.attr(f"scale{axe}").disconnect()
            infl.attr(f"scale{axe}").set(1.0)

        infl.translate.set(0.0, 0.0, 0.0)
        infl.rotate.set(0.0, 0.0, 0.0)
        infl.jointOrient.set(0.0, 0.0, 0.0)

        infl.useOutlinerColor.set(True)
        infl.outlinerColor.set(0.5,1,0)

        if constraint_nd_type_ == constants.MGEAR_MATRIX_CONSTRAINT_NAME:
            parent_jnt = infl.getParent()

            math_mult_nd_0 = pmc.createNode("math_MultiplyMatrix")
            math_mult_nd_0.input1.set(jnt_ws_mtx)

            parent_jnt.worldInverseMatrix[0].connect(math_mult_nd_0.input2)

            math_mult_nd_1 = pmc.createNode("math_MultiplyMatrix")

            ctrl.matrix.connect(math_mult_nd_1.input1)

            math_mult_nd_0.output.connect(math_mult_nd_1.input2)

            if not pmc.isConnected(math_mult_nd_1.output, infl.offsetParentMatrix):
                math_mult_nd_1.output.connect(infl.offsetParentMatrix, f=True)

        elif constraint_nd_type_ == constants.DIRECT_CONNECTION_NAME:
            ctrl.translate.connect(infl.translate, f=True)
            ctrl.rotate.connect(infl.rotate, f=True)
            ctrl.scale.connect(infl.scale, f=True)

            infl.offsetParentMatrix.set(jnt_ws_mtx)

        else:
            raise NotImplementedError(f"Behaviour was requested"
                                      f" that was not yet implemented. {constraint_nd_type_}"
                                      )

        if constraint:
            pmc.delete(constraint)

    mesh_trs.addAttr(constants.SKIN_LOCALIZATION_TYPE_ATTR, dt="string")

    _LOGGER.debug("Finished localizing operation.")


def save_localize_data(mesh_list,
                       prettyprint=False, ):
    """
    Save the localize data as json file for easier rebuild.

    Args:
        mesh_list(list): A list filled with meshes as pmc.PyNodes

        prettyprint(bool): Will pretty print the data dict into the script editor.
                           Default is False.

    """

    # the actual stuff
    io_manager = ImportExport()

    data_list = [
        {
            "mesh":              f"{mesh_trs.name(long=None)}",
            "constrain_nd_type": mesh_trs.attr(constants.SKIN_LOCALIZATION_TYPE_ATTR).get(),
        }
        for mesh_trs in mesh_list
        if mesh_trs.hasAttr(constants.SKIN_LOCALIZATION_TYPE_ATTR)
    ]

    _LOGGER.info(f"Found: {data_list} to export as localization data")

    if not data_list:
        raise LookupError("No data dict exist for pre bind matrix transforms.")

    io_manager.write(
            object_name=LOCALIZE_INF_LOOKUP_EXPORT_NAME,
            data_to_write=data_list,
            data_type="json",
    )

    if prettyprint:
        pprint(data_list)

    return True


def localize_skin_influences_for_selection(
        constraint_nd_type: str = constants.MGEAR_MATRIX_CONSTRAINT_NAME,
):
    """
    Localize skin influences for selected meshes.

    Args:
        constraint_nd_type(str): The contsraint type which is the driver of the influence.
                                 Default is the global var MGEAR_MATRIX_CONSTRAINT.

    """

    mesh_list = pmc.selected()

    for mesh in mesh_list:
        localize_skin_influences(mesh,
                                 constraint_nd_type,
                                 )


def save_localize_data_from_selection():
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
    save_localize_data(mesh_list,
                       )


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


def load_and_execute_localize_data(prettyprint=False):
    """
    Load the localize data and create localizing setups based on the saved data.

    Args:
        import_path(str, path, bool): If false, searches in scene directory, if str or path given, it looks there.

    """
    data_list = _read_localize_data(prettyprint=prettyprint)

    for data_dict in data_list:
        mesh_trs = pmc.PyNode(data_dict["mesh"])
        constrain_type = data_dict["constrain_nd_type"]
        localize_skin_influences(mesh_trs, constrain_type)


def main():
    pass


if __name__ == "__main__":
    main()
