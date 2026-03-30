# Author:     Christof Puehringer / Rigging TD

"""
methods for chopping the rig.
"""

# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Import built-in modules
from builtins import int
from builtins import str
from builtins import zip
from itertools import chain
# Import python standard import
import logging

# Import third-party modules
from future import standard_library
import maya.cmds as cmds
# Import Maya specific modules
import pymel.core as pmc

try:
    # Import third-party modules
    import ngSkinTools2
    from ngSkinTools2.api import InfluenceMappingConfig
    from ngSkinTools2.api import VertexTransferMode
    from ngSkinTools2.api import import_export
    from ngSkinTools2.api import layers
    from ngSkinTools2.operations import removeLayerData
    from ngSkinTools2.ui import mainwindow

except:
    pmc.warning("Unable to import ngSkinTools2")

# Import local modules
from pxo_rigging_kit import constants
from pxo_rigging_kit.maya_utils import dag_utils
from pxo_rigging_kit.maya_utils import decorators
from pxo_rigging_kit.maya_utils import exceptions
from pxo_rigging_kit.maya_utils import shader_utils
from pxo_rigging_kit.maya_utils.deformers import blendshape_utils
from pxo_rigging_kit.maya_utils.deformers.operators import skincluster_op


from importlib import reload
reload(skincluster_op)

standard_library.install_aliases()

##########################################################
# GLOBALS
##########################################################

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.DEBUG)
DECORATORS = decorators.Decorators()
DECORATORS.debug = True
DECORATORS.logger = _LOGGER

# universal, script internal naming
_SPLIT_NAME_TOKEN = 'splitMsh'
_GEO_NAME_TOKEN = 'geo'
_CHOPPER_NAME_TOKEN = 'chopperMsh'


##########################################################
# FUNCTIONS
##########################################################


def create_split_mapping(layer_iter=0, add=True, update=True):
    """
    Creates the initial split mapping from selected edges and saves these in the component tags of the shape.

    Args:
        layer_iter(int): The amount of layers to be created.
        add(bool): Enable add to component tags.
                   Default is True.
        update(bool): Update existing component tags.

    Returns:
          pmc.PyNode: The network note with the generated chop data as meta data attributes.

    """
    edges = cmds.ls(sl=True, fl=True)
    edges_cleaned = set([str(x).split(".")[-1] for x in edges])

    shape_name = str(edges[0]).split(".")[0]

    layer_iter_name = str(layer_iter)
    layer_name = "{0}_{1}".format(constants.CHOP_LAYER_NAME, layer_iter_name)

    existing_tags = gather_component_tags(shape_name)

    # figure out the layer naming :)
    iter_counter = layer_iter
    while layer_name in existing_tags and add:
        layer_iter_name = str(iter_counter)
        layer_name = "{0}_{1}".format(constants.CHOP_LAYER_NAME, layer_iter_name)
        iter_counter += 1

    # get the naming right
    cmds.setAttr(
        "{0}.componentTags[{1}].componentTagName".format(shape_name, layer_iter_name),
        layer_name,
        type="string",
    )

    # figure out the whole schtik
    # add preexisting edges, remove duplicates, query all layers
    if not add and update:
        preexisting_edges = set([str(x).split(".")[-1]
                                 for x
                                 in gather_component_tag_components(shape_name, layer_name)]
                                )

        edges_cleaned.update(preexisting_edges)

    edges_length = len(edges_cleaned)
    cmds.setAttr(
        "{0}.componentTags[{1}].componentTagContents".format(shape_name, layer_iter_name),
        edges_length,
        *edges_cleaned,
        type="componentList"
    )
    geo = pmc.PyNode(shape_name).getTransform()
    chop_data = pmc.createNode("network", n=str(geo).replace('_geo', "_ntw"))
    chop_data.addAttr("master_geo", at="message")
    chop_data.addAttr("is_chopper_network", at="bool", dv=True)

    geo.addAttr("master_geo", at="message")

    chop_data.attr("master_geo").connect(geo.attr("master_geo"), f=True)

    return chop_data


def gather_component_tags(shape_name):
    """
    Gathers all component tags that are part of the mesh.

    Args:
        shape_name(str): Name of the shape of which the tags shall be queried.

    Returns:
        List: list(str(layer_name),
                   str(layer_name),
                   ...
                   )
    """
    return [
        str(layer)
        for layer in cmds.geometryAttrInfo(
            "{0}.outMesh".format(shape_name), componentTagNames=True
        )
    ]


def gather_component_tag_components(shape_name, tag_name):
    """
    Questions the component tags that are part of the layer to get a list of edges.

    Args:
        shape_name(str): Name of the shape node to be queried.
        tag_name(str): Name of the layer tag to be queried.

    Returns:
        List: list(str(edge_index),
                   str(edge_index),
                   str(edge_index),
                   ...
                   )
    """
    return [
        str(edge_name)
        for edge_name in cmds.geometryAttrInfo(
            "{0}.outMesh".format(shape_name),
            components=True,
            componentTagExpression=tag_name,
        )
    ]


def create_chop_geos():
    """
    Creates a chopping geo with sublayers based on the component tags of the geometry.

    Returns:
        Tuple: tuple(list(split_mesh_transforms),
                     list(split_meshes),
                     pymel.core.PyNode(chopping_geo)
                     )

    """

    output_info = list()

    for geo, chop_master in get_geo_network_names_from_scene():
        chop_master_nde = pmc.PyNode(chop_master)
        chopping_geo = pmc.PyNode(geo).duplicate()[0]
        # rename chop master geo
        chopping_name = "{0}_{1}".format(_CHOPPER_NAME_TOKEN, geo)
        chopping_geo.rename(chopping_name)

        shape_nodes = chopping_geo.getShapes(noIntermediate=True)

        if not shape_nodes:
            return

        shape_node = shape_nodes[0]
        shape_name = str(shape_node.longName())
        chop_layers = gather_component_tags(shape_name)

        if not chop_layers:
            return

        layers_combined = set()
        for layer in chop_layers:
            chop_layer_info = gather_component_tag_components(shape_name, layer)
            layers_combined.update(chop_layer_info)

        com = list("{0}.{1}".format(shape_name, val) for val in layers_combined)

        pmc.select(com)
        pmc.mel.eval("performDetachComponents;")
        cmds.polySeparate(chopping_name)
        pmc.select(clear=True)

        if len(chopping_geo.getShapes()) == 1:
            create_orig_shape(chopping_geo.getShape())

        pmc.delete(chopping_name, constructionHistory=True)

        for axis in "xyz":
            for transformation in "srt":
                chopping_geo.attr("{0}{1}".format(transformation, axis)).set(lock=False)

        transform, shape_node = dag_utils.delete_hidden_shapes(chopping_geo)
        chopped_master_shape_nodes = chopping_geo.getShapes()

        if not chopped_master_shape_nodes:
            raise exceptions.ChopperError("somehow the shapenode was deleted during chopping process")

        chopped_master_shape_names = [
            str(node.shortName()) for node in chopped_master_shape_nodes
        ]

        split_meshes = [
            child.getShapes()[0]
            for child in chopping_geo.getChildren()
            if str(child.shortName()) not in chopped_master_shape_names
        ]
        split_mesh_transforms = [
            split_mesh.getParent().rename(
                "{0}_{1}_{2}_geo".format(chopping_name, _SPLIT_NAME_TOKEN, str(iteration_))
            )
            for iteration_, split_mesh in enumerate(split_meshes)
        ]

        tag_system(split_mesh_transforms, split_meshes, chopping_geo, chop_master_nde)

        colorize_system(chop_master_nde, shape_node, split_meshes)
        shape_node.template.set(True)

        output_info.append((split_mesh_transforms, split_meshes, chopping_geo))

    return output_info


def get_geo_network_names_from_scene():
    """
    Get all geo network node names from the scene.

    Returns:
        List: All geo names with existing chop data.

    """
    geo_names = [
        (str(cmds.connectionInfo('{0}.master_geo'.format(network), destinationFromSource=True)[0].split(".")[0]),
         str(network))
        for network
        in cmds.ls(type="network")
        if cmds.attributeQuery(constants.CHOP_NTW_ND_TAG_NAME,
                               n=network,
                               exists=True)
        and cmds.connectionInfo('{0}.master_geo'.format(network), destinationFromSource=True)
        ]
    if not geo_names:
        exceptions.ChopperError("there are no split mapped meshes in the scene")
    return geo_names


def adjust_chop_geos():
    """
    Adjusts the chop geometries based on their assigned shaders.
    """
    for geo, chop_master in get_geo_network_names_from_scene():
        chop_master_nde = pmc.PyNode(chop_master)

        chopping_shape = None

        master_geo = pmc.PyNode(str(geo))
        chopping_name = "{0}_{1}".format(_CHOPPER_NAME_TOKEN, geo.split(":")[-1])

        if not pmc.objExists(chopping_name):
            exceptions.ChopperError("there was no node found in the scene called {0}".format(chopping_name))

        chopping_node = pmc.PyNode(chopping_name)

        chopping_shapes = chopping_node.getShapes()

        if chopping_shapes:
            chopping_shape = chopping_node.getShapes()[0]

        wrap_name = "{0}_{1}_pWrp".format(constants.CHOP_LAYER_NAME, chopping_name)
        if pmc.objExists(wrap_name):
            wrap_deformer = pmc.PyNode(wrap_name)
            clear_wrap_drivers(wrap_deformer)

        # get shaders from the master node
        shaders = [
            mat
            for mat in master_geo.attr(constants.CHOP_SYSTEM_TAG).listConnections(
                destination=True
            )
            if pmc.objectType(mat, isType="lambert") and not mat.hasAttr("isFullMesh")
        ]

        # get shading engines from the master node
        shading_engines = [
            shader.outColor.listConnections(destination=True)[0]
            for shader in shaders
            if len(shader.outColor.listConnections(destination=True)) == 1
            and pmc.objectType(
                shader.outColor.listConnections(destination=True)[0], isType="shadingEngine"
            )
        ]

        # find all shaded geometries associated with the shading engines
        shaded_geos = [
            list(set(shading_engine.dagSetMembers.listConnections(source=True)))
            for shading_engine in shading_engines
        ]

        # find geos that have multiple shaders assigned and should be split because of that
        geos_with_more_than_one_shader = [x for x in shaded_geos if shaded_geos.count(x) != 1]
        if geos_with_more_than_one_shader:
            unpacked_geos = set(chain.from_iterable(geos_with_more_than_one_shader))

            # get the associated shaders of the geometries
            for unpacked_geo in unpacked_geos:

                # remove all instances of unpacked_geo from shaded_geos
                shaded_geos[:] = (shaded_geo for shaded_geo in shaded_geos if shaded_geo != [unpacked_geo])

                # split the geometry and remove the original geometry
                split_geometries = split_geo_by_shader(unpacked_geo)

                # add the newly created geometries to the shaded_geos list
                shaded_geos.extend(split_geometries)

        # clean up all the shapes to get rid of useless shape nodes
        cleaned_geos = [
            dag_utils.delete_hidden_shapes(shaded_geo)
            for shaded_geos_opened in shaded_geos
            for shaded_geo in shaded_geos_opened
        ]

        new_transforms = merge_geo_by_shader(shaded_geos)

        if not new_transforms:
            exceptions.ChopperError("No new geos were created for item of shaded geos.")

        intermediate_transforms = [
            transform.rename("intermediate")
            for transform in new_transforms
            if pmc.objExists(transform)
        ]

        # rename ouput transforms that are splitshapes into the correct naming style
        renamed_transforms = [
            geo.rename("{0}_split_{1}_geo".format(chopping_name, str(iteration_)))
            for iteration_, geo in enumerate(intermediate_transforms)
        ]

        renamed_shapes = [
            renamed_transform.getShape() for renamed_transform in renamed_transforms
        ]

        pmc.parent(renamed_transforms, world=True)
        pmc.parent(renamed_transforms, chopping_name)

        tag_system(renamed_transforms, renamed_shapes, chopping_node, chop_master_nde)

        colorize_system(chop_master_nde, chopping_shape, renamed_shapes)


def merge_geo_by_shader(shaded_geos):
    """
    Combine geos by applied shaders.

    Args:
        shaded_geos(list): The shaded geos.

    Returns:
        List: The geos of the new megred geos.

    """
    new_transforms = list()
    # iterate over the composed list coming from the shading connection
    for geos in shaded_geos:
        # check if  there are geos in shaded_geos and skip if there are none
        if not geos:
            continue

        # if there is one, skip and, append the geo to the new transforms
        if len(geos) == 1:
            # check if  there are geos in shaded_geos and skip if there are none
            if not pmc.objExists(geos[0]):
                continue

            new_transforms.append(geos[0])
            continue

        new_geo_transform, new_geo_shape = pmc.polyUnite(*geos, n="result")
        merge_mesh(new_geo_transform)
        pmc.delete(new_geo_transform, constructionHistory=True)

        # pmc.parent(new_geo_transform, chopping_name)
        new_transforms.append(new_geo_transform)
    return new_transforms


def split_geo_by_shader(unpacked_geo):
    """
    Split the geos by applied shaders.

    Args:
        unpacked_geo(pmc.PyNode): The geos to split.

    Returns:
        List: All new splitted geos.

    """
    # find the faces effected
    parent_group = unpacked_geo.getParent()
    unpacked_shape = unpacked_geo.getShape()
    unpacked_shading_engines = set(unpacked_shape.listConnections(type="shadingEngine"))
    split_meshes = list()

    for unpacked_shading_engine in unpacked_shading_engines:
        material = unpacked_shading_engine.surfaceShader.listConnections(source=True, destination=False)[0]
        pmc.select(material)

        pmc.hyperShade(objects="")
        faces = pmc.selected()

        edges = pmc.polyListComponentConversion(faces, fromFace=True, toEdge=True, border=True)

        split_meshes.append(edges)

    # write boarder edges into the master set
    # split the geometry
    pmc.select(edges)
    pmc.mel.eval("performDetachComponents;")
    cmds.polySeparate(str(unpacked_geo.shortName()))
    pmc.select(clear=True)
    pmc.delete(unpacked_geo, constructionHistory=True)
    children = unpacked_geo.getChildren()

    pmc.parent(children, parent_group)
    pmc.delete(unpacked_geo)

    return [[child] for child in children if pmc.objExists(child)]


def merge_mesh(input_transform):
    """
    Takes the input transform and merges all the vertices based on their boarder.

    Args:
        input_transform(pmc.PyNode): The geo for the vertice merging.

    Returns:
        pmc.PyNode(): The merged geo.

    """
    all_vertices = pmc.polyListComponentConversion(input_transform, toFace=True)
    boarder_edges = pmc.polyListComponentConversion(all_vertices, fromFace=True, toEdge=True, border=True)
    boarder_vertices = pmc.polyListComponentConversion(boarder_edges, fromEdge=True, toVertex=True)
    pmc.polyMergeVertex(boarder_vertices, d=0.001)

    return input_transform


def adjust_chop_wrap(geo):
    """
    Adjusts the wrap to the new circumstances (updated split mapping).

    Args:
        geo(str): Name of the geo for which the wrap shall be adjusted.

    Returns:
        pmc.PyNode: Proximity wrap
        None: skips out when the geo has no chopping geo associated with it.

    """
    chopping_name, chopping_node, chopping_shape = geo_to_chopping_geo(geo)
    if not chopping_node and not chopping_shape:
        return

    # find if there is an existing chop setup
    wrap_name = "{0}_{1}_pWrp".format(constants.CHOP_LAYER_NAME, chopping_name)
    if pmc.objExists(wrap_name):
        wrap_deformer = pmc.PyNode(wrap_name)
        clear_wrap_drivers(wrap_deformer)
        set_wrap_drivers()
        return wrap_deformer

    return create_chop_wrap()


def create_chop_wrap():
    """
    Creates the wrap deformer based on the chop performed (the first time).

    Returns:
        pymel.core.PyNode: The deformer as PyNode.
    """
    for geo, chop_master in get_geo_network_names_from_scene():
        chop_master_nde = pmc.PyNode(chop_master)

        chopping_name, chopping_node, chopping_shape = geo_to_chopping_geo(geo)

        if not chopping_node and not chopping_shape:
            return

        # needs transforms to shapes as well :)
        wrap_name = "{0}_{1}_pWrp".format(constants.CHOP_LAYER_NAME, chopping_name)
        wrap_deformer = pmc.createNode("proximityWrap", n=wrap_name)
        wrap_deformer.falloffScale.set(0.01)

        # tagging the wrap deformer as a part of the chop system
        chop_master_nde.addAttr(constants.CHOP_WRAP_TAG,
                                at="message"
                                )

        wrap_deformer.addAttr(constants.CHOP_SYSTEM_TAG,
                              at="message"
                              )
        wrap_deformer.addAttr(constants.CHOP_WRAP_TAG,
                              at="message"
                              )

        chop_master_nde.attr(constants.CHOP_SYSTEM_TAG).connect(wrap_deformer.attr(constants.CHOP_SYSTEM_TAG))
        chop_master_nde.attr(constants.CHOP_WRAP_TAG).connect(wrap_deformer.attr(constants.CHOP_WRAP_TAG))

        wrap_deformer.wrapMode.set(2, lock=True)
        wrap_deformer.maxDrivers.set(2, lock=True)

        # generating an originalShape
        chopping_shape_orig = create_orig_shape(chopping_shape,
                                                chop_connection=chop_master_nde.attr(constants.CHOP_SYSTEM_TAG)
                                                )

        # connecting the wrap master to the wrap node
        chopping_shape.worldMesh.connect(wrap_deformer.input[0].inputGeometry)
        chopping_shape_orig.worldMesh.connect(wrap_deformer.originalGeometry[0])

        set_wrap_drivers()
        return wrap_deformer


def set_wrap_drivers():
    """
    Sets the drivers for the Chop Output.
    """
    for geo, chop_master in get_geo_network_names_from_scene():
        chop_master_nde = pmc.PyNode(chop_master)

        chop_deformers = chop_master_nde.attr("chop_wrap_deformer").listConnections(
            destination=True, source=False, shapes=True
        )

        if not chop_deformers:
            exceptions.ChopperError()

        sub_meshes = chop_master_nde.attr(constants.CHOP_OUTCONNECT_MESH_TAG).listConnections(
            destination=True, source=False, shapes=True
        )

        _LOGGER.info(sub_meshes)

        if not sub_meshes:
            exceptions.ChopperError()

        sub_meshes.sort(key=lambda sub_mesh: int(str(sub_mesh.shortName()).split("_")[-2]))

        sub_mesh_origs = [create_orig_shape(sub_mesh, chop_connection=chop_master_nde.attr(constants.CHOP_SYSTEM_TAG))
                          for sub_mesh
                          in sub_meshes
                          ]

        sub_mesh_org = list(zip(sub_meshes, sub_mesh_origs))

        for iteration_, (shp, orig) in enumerate(sub_mesh_org):
            orig.outMesh.connect(
                chop_deformers[0].attr(
                    "drivers[{0}].driverBindGeometry".format(str(iteration_))
                )
            )

            shp.worldMesh[0].connect(
                chop_deformers[0].attr("drivers[{0}].driverGeometry".format(str(iteration_)))
            )


def clear_wrap_drivers(wrap_deformer):
    """
    Removes all drivers from the wrap deformer to either clean it up or just make it available for further connections.

    Args:
        wrap_deformer(pymel.core.PyNode): The wrap deformer node.

    Returns:
        None: If no drivers available.

    """
    open_driver_attrs = list(wrap_deformer.drivers)

    if not open_driver_attrs:
        return

    for driver_attr in wrap_deformer.drivers:

        pmc.disconnectAttr(driver_attr.driverGeometry)
        pmc.disconnectAttr(driver_attr.driverBindGeometry)


def geo_to_chopping_geo(geo):
    """
    Traverses from the geo to the chopping geo.

    Args:
        geo(str): The name of the geometry that is chopped.

    Returns:
        Tuple: If able returns tuple(str(chopping_name),
                                     pymel.core.PyNode(chopping_node),
                                     pymel.core.PyNode(chopping_shape)).

               If not it will return a tuple filled with None.

    """
    chopping_node = None
    chopping_shape = None
    chopping_shapes = None

    master_geo = pmc.PyNode(str(geo))
    chopping_name = "{0}_{1}".format(_CHOPPER_NAME_TOKEN, str(master_geo.shortName()).split(":")[-1])

    if pmc.objExists(chopping_name):
        chopping_node = pmc.PyNode(chopping_name)

    if chopping_node:
        chopping_shapes = chopping_node.getShapes()

    if chopping_shapes:
        chopping_shape = chopping_node.getShapes()[0]

    return chopping_name, chopping_node, chopping_shape


def tag_system(split_mesh_transforms, split_meshes, chopping_geo, master_geo):
    """
    Adds tags to the system for easier navigation.

    Args:
        split_mesh_transforms(list): Transform nodes.
        split_meshes(list): Shape nodes.

        chopping_geo(pymel.core.PyNode): Chopping geo node.
        master_geo(pymel.core.PyNode): Master geo node.

    """

    [
        mesh_transform.addAttr(constants.CHOP_INPUT_MESH_TAG, at="bool", dv=True)
        for mesh_transform in split_mesh_transforms
        if not pmc.attributeQuery(
            constants.CHOP_INPUT_MESH_TAG, node=mesh_transform, exists=True
        )
    ]

    # add the connection from the chop network to the submeshes
    if not pmc.attributeQuery(constants.CHOP_OUTCONNECT_MESH_TAG, node=master_geo, exists=True):
        master_geo.addAttr(constants.CHOP_OUTCONNECT_MESH_TAG, at="message")

    [
        split_mesh.addAttr(constants.CHOP_OUTCONNECT_MESH_TAG, at="message")
        for split_mesh in split_meshes
        if not pmc.attributeQuery(
            constants.CHOP_OUTCONNECT_MESH_TAG, node=split_mesh, exists=True
        )
    ]

    [
        master_geo.attr(constants.CHOP_OUTCONNECT_MESH_TAG).connect(
            split_mesh.attr(constants.CHOP_OUTCONNECT_MESH_TAG), force=True
        )
        for split_mesh in split_meshes
    ]

    # add the connection from the chop network to the resultmesh
    if not pmc.attributeQuery(constants.CHOP_INCONNECT_MESH_TAG, node=master_geo, exists=True):
        master_geo.addAttr(constants.CHOP_INCONNECT_MESH_TAG, at="message")

    if not pmc.attributeQuery(constants.CHOP_INCONNECT_MESH_TAG, node=chopping_geo, exists=True):
        chopping_geo.addAttr(constants.CHOP_INCONNECT_MESH_TAG, at="message")

    if not pmc.isConnected(master_geo.attr(constants.CHOP_INCONNECT_MESH_TAG),
                           chopping_geo.attr(constants.CHOP_INCONNECT_MESH_TAG)
                           ):
        master_geo.attr(constants.CHOP_INCONNECT_MESH_TAG).connect(chopping_geo.attr(constants.CHOP_INCONNECT_MESH_TAG))

    # add to master geo
    if not pmc.attributeQuery(constants.CHOP_SYSTEM_TAG, node=master_geo, exists=True):
        master_geo.addAttr(constants.CHOP_SYSTEM_TAG, at="message")

    if not pmc.attributeQuery(constants.CHOP_SYSTEM_TAG, node=master_geo, exists=True):
        master_geo.addAttr(constants.CHOP_SYSTEM_TAG, at="message")

    if not pmc.attributeQuery(
        constants.CHOP_SYSTEM_TAG, node=chopping_geo.getShape(), exists=True
    ):
        chopping_geo.getShape().addAttr(constants.CHOP_SYSTEM_TAG, at="message")

    [
        split_mesh.addAttr(constants.CHOP_SYSTEM_TAG, at="message")
        for split_mesh in split_meshes
        if not pmc.attributeQuery(
            constants.CHOP_SYSTEM_TAG, node=split_mesh, exists=True
        )
    ]

    split_meshes.append(chopping_geo.getShape())
    [
        master_geo.attr(constants.CHOP_SYSTEM_TAG).connect(
            chopping_comp.attr(constants.CHOP_SYSTEM_TAG), force=True)

        for chopping_comp in split_meshes
    ]

    # add the connections for skinclusters
    if not pmc.attributeQuery(constants.CHOP_SKIN_TAG, node=master_geo, exists=True):
        master_geo.addAttr(constants.CHOP_SKIN_TAG, at="message")

    # add the connections for blendshapes
    if not pmc.attributeQuery(constants.CHOP_BLENDSHAPE_TAG, node=master_geo, exists=True):
        master_geo.addAttr(constants.CHOP_BLENDSHAPE_TAG, at="message")


def create_color_shader(master_geo):
    """
    Create chop rig color shaders.

    Args:
        master_geo(pmc.PyNode): The master geo of the split.

    Returns:
        Tuple: (Material, Shader)

    """
    if isinstance(master_geo, str):
        master_geo = pmc.PyNode(master_geo)

    material, shader = shader_utils.create_shader_random(material_name="{0}_splitMsh".format(str(master_geo.shortName())))

    if not pmc.attributeQuery(constants.CHOP_SYSTEM_TAG, node=master_geo, exists=True):
        master_geo.addAttr(constants.CHOP_SYSTEM_TAG, at="message")

    if not pmc.attributeQuery(constants.CHOP_SYSTEM_TAG, node=material, exists=True):
        material.addAttr(constants.CHOP_SYSTEM_TAG, at="message")

    if not pmc.isConnected(
            master_geo.attr(constants.CHOP_SYSTEM_TAG),
            material.attr(constants.CHOP_SYSTEM_TAG),
    ):

        master_geo.attr(constants.CHOP_SYSTEM_TAG).connect(material.attr(constants.CHOP_SYSTEM_TAG))
    return material, shader

def connect_wrap(master_geo, wrap_node):
    """
    Connect wrap deformer to given geo.

    Args:
        master_geo(pmc.PyNode): The geo driven by the wrap deformer.
        wrap_node(pmc.PyNode): The proxymity wrap node.

    """
    wrap_node.outGeo.connect(master_geo.getShape().inMesh)


def disconnect_wrap(master_geo, wrap_node):
    """
    Disconnect the wrap node from given master geo.

    Args:
        master_geo(pmc.PyNode): The geo driven by the wrap deformer.
        wrap_node(pmc.PyNode): The proxymity wrap node.

    """
    wrap_node.outGeo.disconnect(master_geo.getShape().inMesh)


def transfer_deformers():
    """
    Transfer skincluster and blendshape data from source mesh to all choped meshes.

    Returns:
        Tuple: New skincluster names, New blendshape names

    """
    _LOGGER.info("started transferring deformers, depending on data, this could take a while")

    skincluster_names = list()
    blendshape_names = list()

    for geo, chop_master in get_geo_network_names_from_scene():
        chop_master_nde = pmc.PyNode(chop_master)
        split_meshes = chop_master_nde.attr(constants.CHOP_OUTCONNECT_MESH_TAG).listConnections(source=False,
                                                                                                destination=True
                                                                                                )

        if not split_meshes:
            raise exceptions.ChopperError("no splitmeshes found")

        master_geo = chop_master_nde.attr("master_geo").listConnections(source=False,
                                                                        destination=True
                                                                        )

        if not master_geo:
            raise exceptions.ChopperError("no splitmeshes found")

        if skincluster_op.get_skin_cluster(master_geo[0]):

            skin_main_operator = skincluster_op.SkinClusterOperator(master_geo[0])
            new_split_clusters = skin_main_operator.transfer_deformer(mesh_list=split_meshes
                                                                      )
            to_skin_cluster_names = [to_skin_cluster_name for (geo_name,
                                                               to_skin_cluster_name,
                                                               skin_split_operator
                                                               )
                                     in new_split_clusters
                                     ]

            [skin_split_operator.rebuild_pruned() for (geo_name,
                                                       to_skin_cluster_name,
                                                       skin_split_operator
                                                       )
             in new_split_clusters
             ]

            for to_skin_cluster_name in to_skin_cluster_names:
                if not pmc.attributeQuery(constants.CHOP_SKIN_TAG, node=pmc.PyNode(to_skin_cluster_name), exists=True):
                    pmc.PyNode(to_skin_cluster_name).addAttr(constants.CHOP_SKIN_TAG, at="message")

                chop_master_nde.attr(constants.CHOP_SKIN_TAG).connect(
                    pmc.PyNode(to_skin_cluster_name).attr(constants.CHOP_SKIN_TAG))

        for split_mesh in split_meshes:

            if blendshape_utils.get_blendshape_nodes(master_geo[0]):

                blendshape_node = blendshape_utils.transfer_blendshape_setup(master_geo[0],
                                                                             split_mesh,
                                                                             smooth_new_deltas_value=0
                                                                             )

                blendshape_node.rename(str(split_mesh.shortName()).replace("geo", "blS"))

                # add the connections for blendshapes
                if not pmc.attributeQuery(constants.CHOP_BLENDSHAPE_TAG, node=blendshape_node, exists=True):
                    blendshape_node.addAttr(constants.CHOP_BLENDSHAPE_TAG, at="message")

                chop_master_nde.attr(constants.CHOP_BLENDSHAPE_TAG).connect(blendshape_node.attr(constants.CHOP_BLENDSHAPE_TAG))


        return skincluster_names, blendshape_names


def apply_deformers():
    """
    Applies the new created deformers back to the master geo
    """
    for geo, chop_master in get_geo_network_names_from_scene():
        chop_master_nde = pmc.PyNode(chop_master)

        geo_nde = pmc.PyNode(geo)

        wrap_ndes = chop_master_nde.attr(constants.CHOP_WRAP_TAG).listConnections()

        if not wrap_ndes:
            raise exceptions.ChopperError("no wrap nodes connected to the scene")

        master_shapes = geo_nde.getShapes(noIntermediate=True)
        all_shapes = set(geo_nde.getShapes())

        intermediate_shapes = all_shapes - set(master_shapes)
        if not len(master_shapes) == 1:
            raise exceptions.ChopperError()

        for i in intermediate_shapes:
            inter_connections = i.outMesh.listConnections()
            pmc.delete(inter_connections)

        master_inputs = master_shapes[0].inMesh.listConnections()

        if not master_inputs:
            pass

        wrap_ndes[0].outputGeometry[0].connect(master_shapes[0].inMesh, f=True)


def colorize_system(master_geo, shape_node, split_meshes):
    """
    Assigns shaders to all meshes that are part of the system and integrates them into the system.

    Args:
        master_geo (pymel.core.PyNode): The geo Transform that is the master of the chop sub-meshes.
        shape_node (pymel.core.PyNode): The geo Shape that is the master of the chop submeshes.
        split_meshes (list): list(pymel.core.PyNode,
                                  pymel.core.PyNode,
                                  ...
                                  )

    """

    shader_utils.clear_generated_materials()

    # create shaders for look
    clown_shaders = shader_utils.assign_to_meshes_random(
        poly_objects=split_meshes
    )

    grey_object, grey_shader = shader_utils.assign_shader(
        object_to_shade=shape_node,
        material_type="blinn",
        material_name="default_{object}_bsMat".format(
            object=str(shape_node.shortName())
        ),
    )

    grey_shader.addAttr("isFullMesh", at="bool")

    # create attributes for system affiliation
    if not pmc.attributeQuery(constants.CHOP_SYSTEM_TAG, node=grey_shader, exists=True):
        grey_shader.addAttr(constants.CHOP_SYSTEM_TAG, at="message")

    [
        clown_shader.addAttr(constants.CHOP_SYSTEM_TAG, at="message")
        for clown_shader in clown_shaders
        if not pmc.attributeQuery(
            constants.CHOP_SYSTEM_TAG, node=clown_shader, exists=True
        )
    ]

    # unify system shaders
    clown_shaders.append(grey_shader)
    sys_shaders = clown_shaders

    # connect the shader attributes to system master transform
    if not pmc.attributeQuery(constants.CHOP_SYSTEM_TAG, node=master_geo, exists=True):
        master_geo.addAttr(constants.CHOP_SYSTEM_TAG, at="message")

    [
        master_geo.attr(constants.CHOP_SYSTEM_TAG).connect(
            sys_shader.attr(constants.CHOP_SYSTEM_TAG)
        )
        for sys_shader in sys_shaders
        if not pmc.isConnected(
            master_geo.attr(constants.CHOP_SYSTEM_TAG),
            sys_shader.attr(constants.CHOP_SYSTEM_TAG),
        )
    ]


def create_orig_shape(shape, chop_connection=None):
    """
    Duplicates the shape to create an OriginalShape pre deformation.

    Args:
        shape(pymel.core.PyNode): The shape on which will be operated on.
        chop_connection(pymel.core.PyNode.attr):

    Returns:
        pymel.core.PyNode: the new Original Shape

    """
    shape_orig = shape.duplicate(
        n="{0}Orig".format(str(shape.shortName())), addShape=True
    )[0]

    shape_orig.intermediateObject.set(True)

    if not chop_connection and shape_orig.hasAttr(constants.CHOP_SYSTEM_TAG):
        return shape_orig

    if not shape_orig.hasAttr(constants.CHOP_SYSTEM_TAG):
        shape_orig.addAttr(constants.CHOP_SYSTEM_TAG, at="message")

    if chop_connection and pmc.isConnected(chop_connection, shape_orig.attr(constants.CHOP_SYSTEM_TAG)):
        return shape_orig

    if chop_connection:
        chop_connection.connect(shape_orig.attr(constants.CHOP_SYSTEM_TAG))

    return shape_orig

def build_chopper_system():
    """
    Build the chopper system.
    This just can be used when the splitting data exists.
    """
    create_chop_geos()
    create_chop_wrap()
    transfer_deformers()
    apply_deformers()

