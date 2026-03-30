# Author:     Johannes Wolz / Lead Rigging TD

"""
Utils for maya scene managament.
Will care about references and namespaces and so on.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Import built-in modules
# Import python standart import
import logging
import re

# Import third-party modules
from future import standard_library
import pymel.core as pmc

# Import local modules
from pxo_rigging_kit.maya_utils import paths_utils

standard_library.install_aliases()

##########################################################
# GLOBALS
##########################################################

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)

##########################################################
# FUNCTIONS
##########################################################


def get_reference_from_node(node):
    """
    Get the reference node from given node.

    Args:
        node(pmc.PyNode()): The node to act on.

    Return:
        None if fail.
        pmc.PyNode() if successfully.

    """
    reference_nodes = pmc.listReferences(
        loaded=True,
        unloaded=False,
        recursive=True,
        references=False,
        refNodes=True,
    )
    for ref_node in reference_nodes:
        if ref_node.containsNode(node):
            return ref_node


def get_filepath_from_referenced_node(node):
    """
    Get the file path from given referenced node.

    Args:
        node(pmc.PyNode()): The referenced node.

    Return:
        String: The path.

    """
    reference_node = get_reference_from_node(node)
    if reference_node:
        return reference_node.fileName(True, False, False)


def import_references(nodes=None, remove_namespaces=True):
    """
    Import references. From given nodes or globally for the whole scene.

    Args:
      nodes(list, optional): Referenced nodes for import. If None will take the whole scene.
      remove_namespaces(bool): Remove namespace corresponding to the reference.

    """
    references = pmc.listReferences(loaded=True, unloaded=False, recursive=True)
    if nodes:
        reference_nodes = pmc.listReferences(
            loaded=True,
            unloaded=False,
            recursive=True,
            references=False,
            refNodes=True,
        )
        used_instance_refs = []
        for node in nodes:
            for ref_node in reference_nodes:
                if ref_node.containsNode(node):
                    used_instance_refs.append(pmc.FileReference(ref_node))
        references = [
            ref
            for ref in pmc.listReferences(
                loaded=True, unloaded=False, recursive=True
            )
            if ref in used_instance_refs and not _is_proxy_reference(ref)
        ]
    for ref in references:
        ref.importContents(removeNamespace=remove_namespaces)


def load_reference(ref_node_name, file_path):
    """
    Load or remap the given reference node to given file_path.

    Args:
        ref_node_name(str): Ref node name.
        file_path(str): File path for the reference.

    """
    ref_node = pmc.PyNode(ref_node_name)
    file_ref = pmc.FileReference(ref_node)
    file_ref.load(file_path)


def _is_proxy_reference(ref_node):
    """
    Check if the reference is a proxy by checking for an attached proxyManager.

    Args:
        ref_node (pymel.core.nodetypes.Reference): The reference node to inspect.

    Returns:
        (bool) If the input of proxyMsg is attached to a proxyManager.

    """
    return bool(
        pmc.listConnections(
            "{0}.proxyMsg".format(ref_node.refNode),
            destination=False,
            type="proxyManager",
        )
    )


def generate_namespace_from_scene_name(scene_name):
    """
    Generate a namespace from asset name.
    Automatic version up if namespace already exist.

    Args:
        scene_name(str): Name of the current scene.

    Result:
        Example:
            String: crt_vhagar --> vha_01, vha_02

    """
    asset_name = paths_utils.get_asset_infos(scene_name, "asset_name")
    namespace = "{}_".format(asset_name.split("_")[-1][0:3])
    pmc.namespace(setNamespace=":")
    scene_namespaces = pmc.namespaceInfo(listOnlyNamespaces=True, recurse=True)
    temp = [nmsp for nmsp in scene_namespaces if re.search(namespace, nmsp)]
    count = len(temp)
    namespace = "{}0{}".format(namespace, count + 1)
    return namespace


def add_objects_to_namespace(objects_list, namespace):
    """
    Add objects from given list to given namespace.

    Args:
        objects_list(list): List filled with pmc.PyNode().
        namespace(str): Namespace without ":"

    """
    scene_namespaces = pmc.namespaceInfo(listOnlyNamespaces=True, recurse=True)
    pmc.namespace(setNamespace=":")
    if namespace not in scene_namespaces:
        pmc.namespace(add=namespace)
        pmc.namespace(setNamespace=":")
    for node in objects_list:
        parent_nmsp = node.namespace()
        if parent_nmsp:
            _LOGGER.warning(
                f"{node} already in {parent_nmsp} namespace. Will skip to avoid nested namespaces"
            )
            continue
        node.rename(":".join([namespace, node.name(long=None)]))


def get_unique_namespace(namespace):
    """
    Get unique namespace from given namespace.

    Args:
        namespace(str): The namespace you want to have as unique one.

    Returns:
        String: New unique namespace.

    """
    pure_nmspc = namespace.split("_")[0]
    similar_nmsp = [
        nmsp for nmsp in pmc.namespaceInfo(lon=True) if pure_nmspc in nmsp
    ]
    return f"{pure_nmspc}_{len(similar_nmsp)+1:02d}"


def delete_unkown_plugins():
    """
    Will delete all unknown plugins.
    """
    unknown_plugins = pmc.unknownPlugin(query=True, list=True)
    if unknown_plugins:
        for plugin in unknown_plugins:
            try:
                pmc.unknownPlugin(plugin, remove=True)
            except Exception as error:
                # Oddly enough, even if a plugin is unknown, it can still have a dependency in the scene.
                # So in this case, we log the error to look at after.
                _LOGGER.warning(
                    "Unknown plugin cannot be removed due to ERROR: {}".format(
                        error
                    )
                )
    _LOGGER.info("Unknown plugins deleted:[{0}]".format(unknown_plugins))


def delete_unkown_nodes():
    """
    Will delete all unknown nodes.
    """
    unkown_nodes = pmc.ls(type="unknown")
    pmc.delete(unkown_nodes)
    _LOGGER.info("Unknown nodes deleted:[{}]".format(unkown_nodes))


def delete_shapes_plugin_data():
    """deletes the shapes plugin data out of the scene

    Returns:
        True: if it worked will return True, else None
    """
    for bls_nde in pmc.ls(type="blendShape"):
        for attr__ in bls_nde.listAttr():
            if "SHAPES" not in attr__.name():
                continue

            if attr__.isConnected():
                [
                    pmc.delete(connected_node)
                    for connected_node in attr__.listConnections()
                ]

            attr__.set(l=False)
            pmc.deleteAttr(attr__)

    return True
