# Import built-in modules
import os
import re

# Import third-party modules
from maya import cmds as mc
from maya.api import OpenMaya as om2
from maya.api import OpenMayaAnim as oma2
from pymel import core as pmc

# Import local modules
from pxo_rigging_kit.maya_utils.dag_utils import delete_hidden_shapes

# ======================================================================

layer_re = re.compile("(LAYER_)([0-9]+)")

_MERGE_FLAG = "is_skin_merge_grp"
_MERGE_DESTINATION_NAME = "skin_merge_destination_name"
_MERGE_DESTINATION_CONNECTION = "skin_merge_destination_connection"
_MERGE_SOURCE_CONNECTION = "skin_merge_source_connection"

_LAYER_FLAG = "is_skin_merge_layer"
_LAYER_INDEX = "skin_merge_layer_index"
_LAYER_DESTINATION_NAME = "skin_merge_layer_destination_name"
_LAYER_DESTINATION_CONNECTION = "skin_merge_layer_destination_connection"
_LAYER_SOURCE_NAME = "skin_merge_layer_source_name"
_LAYER_SOURCE_CONNECTION = "skin_merge_layer_source_connection"

_MERGE_BASE_NAME = "SKINMERGE"
_LAYER_BASE_NAME = "SKINLAYER"


def create_structure_for_split(geometry=pmc.selected()[0], layer_amount=2):
    geometry_name = str(geometry.shortName())

    merge_group = create_merge_group(geometry_name)
    layers = create_layer_structure(geometry_name, layer_amount)

    connect_layers_to_merge_group(merge_group, layers)
    connect_merge_group_to_geo(merge_group, geometry_name)

    # fills the created layers
    [fill_layer_structure(geometry_name, layer) for layer in layers]


def create_merge_group(geometry_name):

    splitter_name = "{0}_{1}_grp".format(_MERGE_BASE_NAME, geometry_name)

    if not pmc.objExists(splitter_name):
        extras_node = pmc.createNode("transform", n=splitter_name)
    else:
        extras_node = pmc.PyNode(splitter_name)

    # tag as skin merge group
    extras_node.addAttr(_MERGE_FLAG, at="bool", dv=1)

    # name of the geometry that will be influenced
    extras_node.addAttr(_MERGE_DESTINATION_NAME, dt="string")

    # connection to the geometry that will be influenced
    extras_node.addAttr(_MERGE_DESTINATION_CONNECTION, at="message")

    # connection to the geometries that will influence
    extras_node.addAttr(_MERGE_SOURCE_CONNECTION, at="message")

    return extras_node


def create_layer_structure(geometry_name, layer_amount):
    layers = [pmc.createNode("transform",
                             n="{0}{1}_{2}_grp".format(_LAYER_BASE_NAME,
                                                       str(layer_index),
                                                       geometry_name
                                                       )
                             )
              for layer_index
              in range(0, layer_amount)
              if not pmc.objExists("{0}{1}_{2}_grp".format(_LAYER_BASE_NAME,
                                                           str(layer_index),
                                                           geometry_name
                                                           )
                                   )
              ]

    # tag as skin merge group
    [layer.addAttr(_LAYER_FLAG, at="bool", dv=1) for layer in layers]

    # give layer an index
    [layer.addAttr(_LAYER_INDEX, at="long", dv=layer_index)
     for layer_index, layer
     in enumerate(layers)
     ]

    # give layer an index
    [layer.addAttr(_LAYER_DESTINATION_NAME, dt="string") for layer in layers]
    [layer.attr(_LAYER_DESTINATION_NAME).set(geometry_name) for layer in layers]

    [layer.addAttr(_LAYER_DESTINATION_CONNECTION, at="message") for layer in layers]

    [layer.addAttr(_LAYER_SOURCE_NAME, dt="string") for layer in layers]
    [layer.attr(_LAYER_SOURCE_NAME).set("placeholder") for layer in layers]

    [layer.addAttr(_LAYER_SOURCE_CONNECTION, at="message") for layer in layers]

    [layer.useOutlinerColor.set(True) for layer in layers]

    [layer.outlinerColorR.set((1/len(layers)*layer_number)) for layer_number, layer in enumerate(layers)]

    [layer.outlinerColorG.set(.7) for layer in layers]

    [layer.outlinerColorB.set(.7) for layer in layers]

    return layers


def fill_layer_structure(geometry_name,
                         layer
                         ):

    layer_group = layer
    layer_geometry = pmc.duplicate(geometry_name)

    delete_hidden_shapes(layer_geometry, rename="{0}_{1}_geo".format(_LAYER_BASE_NAME, geometry_name))

    pmc.parent(layer_geometry, layer_group)


def connect_layers_to_merge_group(merge_group, layers):

    [merge_group.attr(_MERGE_SOURCE_CONNECTION).connect(layer.attr(_LAYER_SOURCE_CONNECTION)) for layer in layers]

    pmc.parent(layers, merge_group)


def connect_merge_group_to_geo(merge_group, geometry_name):

    splitter_target_node = pmc.PyNode(geometry_name)
    splitter_target_node.addAttr(_MERGE_DESTINATION_CONNECTION, at="message")
    merge_group.attr(_MERGE_DESTINATION_CONNECTION).connect(splitter_target_node.attr(_MERGE_DESTINATION_CONNECTION))

    merge_group.attr(_MERGE_DESTINATION_NAME).set(str(geometry_name))


# ======================================================================
# om2 utilities
def get_mobject(name):
    sel = om2.MGlobal.getSelectionListByName(name)
    return sel.getDependNode(0)


# ---------------------------------------------------------------------
def get_dag_path(name):
    sel = om2.MGlobal.getSelectionListByName(name)
    return sel.getDagPath(0)


# ---------------------------------------------------------------------
def get_mfn_skin(skin_ob):
    if isinstance(skin_ob, pmc.PyNode):
        skin_ob = get_mobject(skin_ob.longName())
    return oma2.MFnSkinCluster(skin_ob)


# ---------------------------------------------------------------------
def get_mfn_mesh(mesh_ob):
    if isinstance(mesh_ob, pmc.PyNode):
        mesh_ob = get_mobject(mesh_ob.longName())
    return om2.MFnMesh(mesh_ob)


# ---------------------------------------------------------------------
def get_complete_components(mesh):
    """
    Return an object component for all the vertices
    on the specified mesh, for specifying vertices
    in the skin weights transfer tools.

    :param mesh: Mesh you wish to have components for
    :type mesh: om2.MFnMesh or pm.nt.Mesh
    :return: an MObject representing the selection of all vertices on the mesh
    :rtype: om2.MFnSingleIndexedComponent
    """
    assert isinstance(mesh, om2.MFnMesh), "Mesh must be an MFnMesh or pm.nt.Mesh instance."
    comp = om2.MFnSingleIndexedComponent()
    ob = comp.create(om2.MFn.kMeshVertComponent)
    comp.setCompleteData(mesh.numVertices)
    return ob


# ======================================================================
def get_good_weights_path(mesh):
    path = os.path.abspath(os.sep.join((mc.workspace(q=True, rd=True), "data", mesh + ".skinweights")))
    return path


# ---------------------------------------------------------------------
def try_matrix_set(plug, value):
    try:
        plug.set(value)
    except RuntimeError:
        pass


# ---------------------------------------------------------------------
def try_matrix_connect(plug, target):
    try:
        if not plug in target.inputs():
            plug >> target
    except RuntimeError:
        pass


# ======================================================================
def copy_skin_weights(source, source_skin, target, target_skin):
    source_shape = get_deform_shape(source)
    source_dp = get_dag_path(source_shape.longName())
    source_mfn = get_mfn_skin(source_skin)
    source_mesh = get_mfn_mesh(get_deform_shape(source))
    components = get_complete_components(source_mesh)

    weights, influence_count = source_mfn.getWeights(source_dp, components)

    # copy over input values / connections
    bind_inputs = [(x.inputs(plugs=True)[0] if x.isConnected() else None) for x in source_skin.bindPreMatrix]
    bind_values = [x.get() for x in source_skin.bindPreMatrix]
    mat_inputs = [(x.inputs(plugs=True)[0] if x.isConnected() else None) for x in source_skin.matrix]
    mat_values = [x.get() for x in source_skin.matrix]

    for index, bind_value, mat_value in zip(range(influence_count), bind_values, mat_values):
        # can't be guaranteed what state things will be in at this point
        # so set them in a try/catch
        try_matrix_set(target_skin.bindPreMatrix[index], bind_value)
        try_matrix_set(target_skin.matrix[index], mat_value)

    for index, bind_input, mat_input in zip(range(influence_count), bind_inputs, mat_inputs):
        if bind_input:
            try_matrix_connect(bind_input, target_skin.bindPreMatrix[index])
        if mat_input:
            try_matrix_connect(mat_input, target_skin.matrix[index])

    # copy over weights
    target_mfn = get_mfn_skin(target_skin)
    target_shape = get_deform_shape(target)
    target_mesh = get_mfn_mesh(target_shape)
    target_dp = get_dag_path(target_shape.longName())
    components = get_complete_components(target_mesh)
    all_indices = om2.MIntArray(range(influence_count))

    target_mfn.setWeights(target_dp, components, all_indices, weights)

    # same as with loading and saving, we want to normalize and
    # recache the bind matrices
    pmc.skinPercent(target_skin, target_shape, normalize=True)
    target_skin.recacheBindMatrices()


# ---------------------------------------------------------------------
def copy_skin_layer(source, target):
    # bugfix:
    # Building the first skincluster on a mesh manually is a Bad Idea.
    # Not sure what else gets set by the command, but if you don't instead
    # allow the command to make the skin and then move the weights you run
    # into issues.

    source_skin = get_skin_cluster(source)

    all_target_skins = list(filter(lambda x: x.type() == "skinCluster", get_deformers_for_shape(target)))

    if len(all_target_skins):
        target_skin = pmc.deformer(target, type='skinCluster', n='MERGED__' + source_skin.name())[0]
    else:
        # no skins yet-- make sure to use this command
        source_influences = source_skin.influenceObjects()
        pmc.select(source_influences, target, r=True)
        target_skin = pmc.skinCluster(tsb=True, mi=3, dr=4.0, n=target + "_skC")

    # never don't neighbors
    target_skin.weightDistribution.set(1)  # neigbors

    copy_skin_weights(source, source_skin, target, target_skin)


# ---------------------------------------------------------------------
def transfer_skins(mesh, layer_meshes):
    clean_deformation(mesh)

    current_time = pmc.currentTime(q=True)
    pmc.currentTime(0)

    for layer_mesh in layer_meshes:
        copy_skin_layer(layer_mesh, mesh)

    pmc.currentTime(current_time)


# ======================================================================
def get_layer_transforms(geometry_name):
    splitter_name = "{0}_skinmerge_grp".format(geometry_name)
    splitter_node = pmc.PyNode(splitter_name)
    result = [lyr_node for lyr_node in splitter_node.getChildren() if layer_re.match(str(lyr_node.shortName()))]

    return result


# ---------------------------------------------------------------------
def mesh_to_face_layers(geometry_name, connect_original=False):
    geometry_node = pmc.PyNode(geometry_name)

    # grab transform
    geometry_node = geometry_node.getParent() if geometry_node.type() == "mesh" else geometry_node

    all_duplicates = []

    for layer in get_layer_transforms(geometry_name):
        layer_name = str(layer)
        dummy_name = layer_name + "_DUMMY"
        duplicate_name = "_".join((layer_name, geometry_name))

        # fail early if the name already exists
        assert not pmc.objExists(duplicate_name), "{} already exists.".format(duplicate_name)

        # add dummy joints to hold skinweights
        if not pmc.objExists(dummy_name):
            dummy = pmc.createNode("joint", n=dummy_name)
            pmc.parent(dummy, layer)

        duplicate = pmc.duplicate(geometry_node, rr=True)[0]
        duplicate.rename(duplicate_name)
        pmc.parent(duplicate, layer)

        all_duplicates.append(duplicate)

    # blendshape chaining
    all_duplicates = list(sorted(all_duplicates))
    all_duplicates_len = int(len(all_duplicates))

    for index in range(1, all_duplicates_len):
        source = all_duplicates[index - 1]
        target = all_duplicates[index]
        pmc.blendShape(
                source,
                target,
                weight=(0, 1),
                before=True,
                name="{0}_INPUT".format(target)
        )

    if connect_original:
        # finally, connect to original mesh
        pmc.blendShape(
                all_duplicates[-1],
                geometry_node,
                weight=(0, 1),
                before=True,
                name="{0}_INPUT".format(geometry_name)
        )


# ======================================================================
def get_deform_shape(ob):
    """
    Gets the visible geometry shape regardless of whether or not
    the object is deformed or not.
    :param ob: The object to check.
    :returns: The object's deform shape.
    """
    ob = pmc.PyNode(ob)
    if ob.type() in ["nurbsSurface", "mesh", "nurbsCurve"]:
        ob = ob.getParent()
    shapes = pmc.PyNode(ob).getShapes()
    if len(shapes) == 1:
        return shapes[0]
    else:
        real_shapes = [x for x in shapes if not x.intermediateObject.get()]
        return real_shapes[0] if len(real_shapes) else None


# ---------------------------------------------------------------------
def get_deformers_for_shape(item):
    """
    Get the deformers from an object's history that only
    effect that particular mesh, and not inputs from other
    meshes (IE, meshes driving blendshapes).
    """
    result = []
    geometry_filters = pmc.ls(pmc.listHistory(item), type="geometryFilter")
    shape = get_deform_shape(item)

    if shape is not None:
        shapeSets = pmc.ls(pmc.listConnections(str(shape)), type="objectSet")

    for deformer in geometry_filters:

        defSet = pmc.ls(pmc.listConnections(deformer), type="objectSet")

        if defSet:
            defSet = defSet[0]

        if defSet in shapeSets:
            result.append(deformer)

    return result


# ---------------------------------------------------------------------
def get_skin_cluster(item):
    deformers = get_deformers_for_shape(item)
    skins = list(filter(lambda x: x.type() == "skinCluster", deformers))

    assert len(skins) < 2, "Cannot use get_skin_cluster on meshes with stacked skins."

    skin = skins[0] if len(skins) else None
    if skin:
        ## I got into the habit of doing this any time
        ## I touch a skin. Neighbors should be the
        ## default but AD doesn't want to change old
        ## workflows.
        skin.weightDistribution.set(1)  ## neigbors

    return skin


# ---------------------------------------------------------------------
def get_layer_shapes_for_mesh(mesh):
    layers = get_layer_transforms()
    all_children = sum([x.getChildren() for x in layers], [])
    mesh_targets = filter(lambda x: x.name().endswith(mesh.rpartition(":")[-1]), all_children)
    return list(mesh_targets)


# ---------------------------------------------------------------------
def clean_deformation(x):
    pmc.delete(get_deformers_for_shape(x))


# ======================================================================
# build

"""
create_structure_for_split(layer_amount=2)

target = "vha_01:vhagarBody_C_001_high_geo"

## Set up the duplicate editing system
mesh_to_face_layers(target)


## you can also get the layers shapes for the target directly
layer_shapes = get_layer_shapes_for_mesh(target)

## and this does the final transfer
transfer_skins(target, layer_shapes)

"""
