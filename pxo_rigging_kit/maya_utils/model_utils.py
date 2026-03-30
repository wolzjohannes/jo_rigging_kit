# Author:     Johannes Wolz / Lead Rigging TD

"""
Utils code for model data management in the rig scene.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import pprint
# Import built-in modules
from builtins import next
from builtins import object
from builtins import range
from builtins import str
from builtins import zip
import itertools
import logging
import os
from random import choice
import re
from pathlib import Path

# Import third-party modules
from future import standard_library
from maya import cmds as cmds
import pymel.core
import pymel.core as pmc
from maya_proxy_node import asset_node

# Import local modules
from pxo_rigging_kit import constants
from pxo_rigging_kit import core
from pxo_rigging_kit.constants import PXO_ASSET_NAME_ATTR
from pxo_rigging_kit.maya_utils import attributes_utils
from pxo_rigging_kit.maya_utils import decorators
from pxo_rigging_kit.maya_utils import exceptions
from pxo_rigging_kit.maya_utils import scene_utils
from pxo_rigging_kit.maya_utils import paths_utils
from pxo_rigging_kit.maya_utils import dag_utils

standard_library.install_aliases()

##########################################################
# GLOBALS
##########################################################

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)

DECORATORS = decorators.Decorators()
DECORATORS.debug = True
DECORATORS.logger = _LOGGER

# Here we will try to get components keys defined in the package config if exist.
# If not will take this default ones.
try:
    VALID_MODEL_ROOT_NODE_TYPES = core.get_config(
        "model_utils:valid_model_root_node_type"
    )
except:
    VALID_MODEL_ROOT_NODE_TYPES = ["transform", "pxoAsset"]

try:
    ASSET_MODEL_COMPONENT_DICT_KEY_LIST = core.get_config(
        "model_utils:model_component_keys"
    )
except:
    ASSET_MODEL_COMPONENT_DICT_KEY_LIST = [
        "body",
        "head",
        "arm",
        "claw",
        "scale",
        "eye",
        "horn",
        "mouth",
        "tongue",
        "gum",
        "nail",
        "teeth",
        "tooth",
        "muscle",
        "skeleton",
        "chest",
    ]

try:
    MODEL_ASSET_HIERARCHY_LOD_TEMPLATE = core.get_config(
        "model_utils.lod_template_names"
    )
except:
    MODEL_ASSET_HIERARCHY_LOD_TEMPLATE = ["sliced", "low", "mid", "high"]

##########################################################
# FUNCTIONS
##########################################################


# Obselete function when we switch 100% to the pxoAsset workflow
def _pxm_geo_root_nd_hierarchy_incest_check(node, tag_name):
    """
    Will check if given node has a child with the given tag name.

    Return:
        True if no child has the pxm geo root node tag else raise a exception.

    """
    children = node.getChildren(ad=True, typ="transform")
    for child in children:
        if attributes_utils.has_attr(child, tag_name):
            raise exceptions.ModelAssetRootNodeError(
                "The model asset root nodes related to each other. That is invalid."
            )
    return True


# Obselete function when we switch 100% to the pxoAsset workflow
def _is_valid_mdl_root_nd_type(node):
    """
    Check if node is a valid model root node type.

    Return:
        True or False.
    """
    if cmds.nodeType(str(node.name())) in VALID_MODEL_ROOT_NODE_TYPES:
        return True
    return False


@DECORATORS.x_timer
def get_model_root_nodes(nodes_list):
    """
    Get the model root nodes in the scene. Which can be a god node tagged as
    PXM_asset_geo_root or a pxoAsset node with the meta values:
    pxo_asset_type = 1,

    Args:
        nodes_list(list): A list of nodes to search for.

    Return:
        False if both owrkflow exist at the same time.
        List: All found nodes.

    Raise:
        ModelAssetRootNodeError if legacy and pxoAsset worklfow exist simultaneously.

    """
    pxm_geo_root_nodes = [
        node
        for node in nodes_list
        if attributes_utils.has_attr(node, constants.PXO_ASSET_GEO_ROOT)
        and node.attr(constants.PXO_ASSET_GEO_ROOT).get() == 1
        and _is_valid_mdl_root_nd_type(node)
    ]
    pxo_asset_nodes = [
        node
        for node in nodes_list
        if node.nodeType() == "pxoAsset"
        and node.attr(asset_node.ASSET_TYPE).get() == 1
    ]
    if pxm_geo_root_nodes and pxo_asset_nodes:
        raise exceptions.ModelAssetRootNodeError(
            f"[{pxm_geo_root_nodes},{pxo_asset_nodes}]."
            f" Legacy and pxoAsset workflow exist simultaneously."
            f" This is invalid."
        )
    if pxm_geo_root_nodes:
        return pxm_geo_root_nodes
    if pxo_asset_nodes:
        return pxo_asset_nodes


# Obselete function when we switch 100% to the pxoAsset workflow
def get_model_root_nodes_from_scene():
    """
    Get the model root nodes form scene

    Return:
        List: All found nodes.
        Throw PxoModelAssetError if PXM_asset_geo_root
        tagged nodes and a pxoAsset nodes at the same time in the nodes list.

    """
    valid_nodes = []
    for valid_node_type in VALID_MODEL_ROOT_NODE_TYPES:
        valid_nodes.extend(pmc.ls(typ=valid_node_type))
    valid_nodes = list(set(valid_nodes))
    return get_model_root_nodes(valid_nodes)


# Obselete function when we switch 100% to the pxoAsset workflow
def get_pxm_export_geo_nodes_from_root_node(root_node, tagged=True):
    """
    Get all export geo tagged nodes from given root node.

    Args:
        root_node(pmc.PyNode()): The mdl asset root node.
        tagged(bool): Will return all tagged as PXM_export_geometries geos.

    Return:
        List: All found nodes.

    """
    child_nodes = [
        shape.getTransform()
        for shape in root_node.getChildren(
            ad=True, type="mesh", noIntermediate=True
        )
    ]
    if tagged:
        return [
            node
            for node in child_nodes
            if node.hasAttr(constants.PXO_EXPORT_GEO) is True
            and node.attr(constants.PXO_EXPORT_GEO).get() == True
        ]
    return child_nodes


# Obselete function when we switch 100% to the pxoAsset workflow
@DECORATORS.x_timer
def get_model_component_roots_from_model_root_node(
    model_root_node, filter_type=1
):
    """
    # THIS IS OBSOLETE JUST KEPT FOR THE CASE WE WOULD NEED IT AGAIN #
    Get all model component roots in the hierarchy.
    A component root is a node which summarizes
    all export geo tagged nodes to the same component/part of an asset.

    Args:
        model_root_node(pmc.PyNode()): The god/root node of the asset.
        filter_type(int): Filter the result by:
                          0. PxoAsset or 1. PXM_asset_geo_root
                          Default is 1.

    Result:
        List: All found nodes.
        None if no nodes found.

    """

    def _generate_pxm_export_geo_list():
        # too slow has to be improved
        return [
            node
            for node in childrens
            if node.hasAttr(constants.PXO_EXPORT_GEO) is True
            and node.attr(constants.PXO_EXPORT_GEO).get() == True
        ]

    result = []
    childrens = [
        node
        for node in model_root_node.getChildren(ad=True)
        if node.nodeType() in VALID_MODEL_ROOT_NODE_TYPES
    ]
    if filter_type == 0:
        # too slow has to be improved
        result.extend(
            [
                node
                for node in childrens
                if node.hasAttr(constants.PXO_MODEL_ASSET_TYPE_DICT["name"])
                is True
                and node.attr(constants.PXO_MODEL_ASSET_TYPE_DICT["name"]).get()
                == constants.PXO_MODEL_ASSET_TYPE_DICT["value"]
                and node.hasAttr(constants.PXO_MODEL_ASSET_RENDER_GEO["name"])
                is True
                and node.attr(
                    constants.PXO_MODEL_ASSET_RENDER_GEO["name"]
                ).get()
                == constants.PXO_MODEL_ASSET_RENDER_GEO["value"]
            ]
        )
    elif filter_type == 1:
        temp_list = _generate_pxm_export_geo_list()
        result.extend([node.getParent() for node in temp_list])
    result = list(set(result))
    return result


# Obselete function when we switch 100% to the pxoAsset workflow
@DECORATORS.x_timer
def get_model_component_roots_from_model_root_node2(
    model_root_node, tagged=True
):
    """
    Get all model component roots in the hierarchy.
    A component root is a node which summarizes all export geos to the
    same component/part of an asset.

    Args:
        model_root_node(pmc.PyNode()): The god/root node of the asset.
        tagged(bool): Will take tagged geos as relative path to find the
                      components roots.
                      If False will take all found mesh geos as relative paths.

    Return:
        List: All found component roots.

    """
    export_geos = get_pxm_export_geo_nodes_from_root_node(
        model_root_node, tagged
    )
    parent_nodes = [node.getParent() for node in export_geos]
    return list(set(parent_nodes))


@DECORATORS.x_timer
def _get_permute_regex_string_dict_for_node_names():
    """
    Will permute the component key strings.
    It will generate all possible string variations
    where each character can be upper or lower.
    And create a regex string for further usage.

    Return:
        Example:
        Dict:
        {
        'body': 'bODY|BODy|BodY|BODY|Body|bodY|BoDy|BOdY|BoDY|boDY|bOdy
                |bOdY|body|boDy|bODy|BOdy',
        'head': 'HEAd|heAd|HEAD|hEaD|hEAd|head|HeaD|heaD|HEaD|hEAD|HeAd
                |Head|hEad|heAD|HeAD|HEad',
        'scale': 'scAle|sCaLE|ScalE|sCALe|SCAlE|sCAle|sCAlE|sCALE|SCaLE
                 |sCalE|scaLE|SCaLe|ScAlE|SCALe|ScaLe|sCaLe|ScaLE|sCale
                 |scale|ScALE|scaLe|SCale|scalE|scALe|Scale',
        'eye': 'eYe|eye|Eye|EYE|eyE|EyE|EYe|eYE',
        'skeleton': 'SkELETOn|sKELEtOn|SKELETon|SkELeToN|skeletoN
                     |SkEleTON|skElETOn|SKElETon|SKeLETOn|SKElEton|SkelEtoN
                     |SkElEToN|skeLEton|skeLeTOn|skelEtoN|sKeletOn|SkELETON
                     |skeletON|SKELETOn|skeLETON|sKeLetoN|SkELETon|skeLeton
                     |sKeleton|SkeletOn|SkeLEtON|SKElEtoN|SKeLeton|SKELEToN
                     |skElETon|skEleTOn|SKelEtOn|sKeLetON|sKelEtoN|SKEleTON
                     |SkElETON|SKELETON|skeletOn|sKeLEton|sKeLeTON|SKeLeTON
                     |SkelEtON|SKeLEtON|skelEton|SkElEtON|SkeLeton|SKeletON
                     |SKeLETON|skELeToN|skeLetoN|skEletoN|SkelETON|skelEtON
                     |SkEleToN|skeLEtON|sKELeton|sKELETon|SKEleton|sKELetOn
                     |SKeLeToN|skELETON|SKeleTon|SKeLEton|sKEleToN',
        }

    """
    result_dict = {}
    for key in ASSET_MODEL_COMPONENT_DICT_KEY_LIST:
        str_list = [str.upper, str.lower]
        match_pattern_list = []
        for x in range(1000):
            if len(match_pattern_list) == pow(len(key), len(str_list)):
                break
            str_pattern = "".join(choice(str_list)(letter) for letter in key)
            if str_pattern not in match_pattern_list:
                match_pattern_list.append(str_pattern)
        regex = r"|".join(match_pattern_list)
        result_dict[key] = regex
    return result_dict


def get_model_resolution_nodes(
    model_root_nd, resolution_list=constants.PXO_MDL_RESOLUTION_GRP_NAMES
):
    """
    Get the model resolution nodes.

    Args:
        model_root_nd(pmc.PyNode): The model root node.
        resolution_list(list): List of strings for resolution grp names.
                               Default is constants.PXO_MDL_RESOLUTION_GRP_NAMES.

    Returns:
        List: Filled with pmc.PyNode().
              pxoAsset or pxoReference node if found and accept them as resolution groups.
              Empty if no resolution nodes exist or the names
              are not fitting.

    """
    result = model_root_nd.getChildren(
        ad=True, type="pxoAsset"
    ) + model_root_nd.getChildren(ad=True, type="proxyReferenceAsset")
    if not result:
        for res in resolution_list:
            for grp in model_root_nd.getChildren(typ="transform"):
                grp_name = grp.name(long=None, stripNamespace=True)
                if res in grp_name:
                    result.append(grp)
    return result


def get_pxo_asset_nodes_by_asset_name(model_pxo_assets=None):
    """
    Get all model relevant pxo asset nodes in the scene.
    Gives them back sorted by asset name.

    Args:
        model_pxo_assets(list): The model pxoAsset nodes.
                                If None will take all found model root nodes in the scene.
                                Default is None.

    Returns:
        Dict: {'veh_buickLucerne': [nt.PxoAsset('proxy'), nt.PxoAsset('render')]}

    """
    if not model_pxo_assets:
        model_pxo_assets = get_model_root_nodes_from_scene()
    model_pxo_asset_dict = {}
    for pxoAsset in model_pxo_assets:
        asset_data = asset_node.get_asset_data_from_node(pxoAsset)
        asset_name = asset_data[asset_node.ASSET_NAME]
        if not asset_name in model_pxo_asset_dict:
            model_pxo_asset_dict[asset_name] = [pxoAsset]
        else:
            model_pxo_asset_dict[asset_name] = model_pxo_asset_dict[
                asset_name
            ] + [pxoAsset]
    return model_pxo_asset_dict

# Honestly we can kill this maybe because the gpu cache is not used anymore in EUR.
# Not 100% sure if this is the case also in NA.
def _get_pxo_asset_model_usages(model_pxo_asset_dict):
    """
    Get the model usages. Which means all nodes which are on the same
    level like the other pxoAsset nodes.
    This could be the case when we manually parent the gpu cache version to it.

    Args:
        model_pxo_asset_dict(dict): This should look like this:
                                    {'veh_buickLucerne': [nt.PxoAsset('proxy'), nt.PxoAsset('render')]}

    Returns:
        Dict: {'veh_buickLucerne': [nt.PxoAsset('proxy'), nt.PxoAsset('render'), AnotherNode]}
    """
    excluded_node_types = ["parentConstraint", "pointConstraint", "scaleConstraint", "orientConstraint"]
    result_dict = {}
    exclusion_node_type = ["parentConstraint", "scaleConstraint", "pointConstraint", "orientConstraint"]
    for asset_name, pxo_asset_nodes in model_pxo_asset_dict.items():
        parent_list = []
        for pxo_asset in pxo_asset_nodes:
            parent_nd = pxo_asset.getParent()
            try:
                tmp_list = [node for node in parent_nd.getChildren() if node.nodeType() not in exclusion_node_type]
            except:
                raise exceptions.PxoModelAssetError(
                    f"It seems that {pxo_asset} node has no parent and is a assemble node."
                    f" Be sure if you really need this node if not pls delete."
                )
            parent_list.extend(tmp_list)
        parent_list = [node for node in parent_list if node.nodeType() not in excluded_node_types]
        result_dict[asset_name] = list(sorted(set(parent_list)))
    return result_dict


def get_pxo_assets_model_data_list(model_root_nd=None):
    """
    Get the model data list based on the pxoAsset workflow.
    This function is hierarchy sensitive we assume to have this:

    Tested hierarchy:
        any_group_name
            |-> veh_buickLucerne (This is the asset name)
                |-> default1 (This can have any name, but it comes with this name out of the box from SG loader)
                    |-> proxy (pxoAsset node)
                        |-> bui_01:veh_buickLucerne_default_default_proxy (Maya reference of the model abc publish)
                    |-> render (pxoAsset node)
                        |-> bui_01:veh_buickLucerne_default_default_render (Maya reference of the model abc publish)
                    |-> bui_03:default_prx (pxoReference node)

    Args:
        model_root_nd(pmc.PyNode): The model root node as start entry to find the pxoAsset nodes.
                                   If None will find all pxoAsset nodes in the scene.
                                   Default is None.

    Returns:
        List: [{'asset_name': 'veh_buickLucerne',
              'asset_root': nt.Transform('default1'),
              'components': {'chassis_C_001_high_grp': {
              nt.Transform('bui_12:chassis_C_001_high_grp'): [
              nt.Transform('bui_12:windshieldWipers_C_001_high_geo'),
              nt.Transform('bui_12:tailLights_C_001_high_geo'),
              nt.Transform('bui_12:tailLights_C_002_high_geo'),
              nt.Transform('bui_12:frontLights_C_001_high_geo'),
              nt.Transform('bui_12:windows_C_001_high_geo'),
              nt.Transform('bui_12:plasticFairing_C_001_high_geo'),
              nt.Transform('bui_12:chassis_C_001_high_geo'),
              nt.Transform('bui_12:mirrors_C_001_high_geo'),
              nt.Transform('bui_12:plasticFairing_C_002_high_geo'),
              nt.Transform('bui_12:logos_C_001_high_geo'),
              nt.Transform('bui_12:numberSigns_C_001_high_geo')]}},
              'publish_path': 'x:/welcome_wlm-4119/_library/assets/vehicles/veh_buickLucerne/mdl/
                               _publish/wlm_veh_buickLucerne_mdl_v007_jwo.veh_buickLucerne_1_default_default_proxy.abc,
                               x:/welcome_wlm-4119/_library/assets/vehicles/veh_buickLucerne/mdl/_publish/
                               wlm_veh_buickLucerne_mdl_v007_jwo.veh_buickLucerne_1_default_default_render.abc',
              'resolution_groups': [nt.PxoAsset('proxy'),
                                    nt.PxoAsset('render'),
                                    nt.ProxyReferenceAsset('bui_01:veh_buickLucerne_mdl_prx')],
              'tagged_geo': False,
              'use_key_regex': False,
              'version': 7}]
    """
    result_list = []
    pxo_asset_nodes = None
    if model_root_nd:
        pxo_asset_nodes = [
            node
            for node in model_root_nd.getChildren(ad=True)
            if node.nodeType() == "pxoAsset"
        ]
    model_pxo_asset_dict = get_pxo_asset_nodes_by_asset_name(pxo_asset_nodes)
    model_usage_dict = _get_pxo_asset_model_usages(model_pxo_asset_dict)
    for asset_name, pxo_asset_nodes in model_usage_dict.items():
        # We finding first the pxoAsset nodes and assuming the third generation is a root node transform.
        # Although the first generation could be also a root node. But later in the process it does not matter.
        # Because we travel down the root node and try to find any mesh node from there.
        # We had to go this approach because we realized the crowd assets with pxoAsset components
        # have slight difference in their hierarchy. And with this we cover up the crowd and not crowd mdl assets.
        root_nodes = {node.getParent(generations=2) for node in pxo_asset_nodes}
        """
        if len(root_nodes) > 1:
            raise exceptions.ModelAssetRootNodeError(
                f"{root_nodes} not sharing the same root group. This is invalid"
            )
        """
        file_paths = [
            scene_utils.get_filepath_from_referenced_node(node.getChildren()[0])
            for node in pxo_asset_nodes
            if scene_utils.get_filepath_from_referenced_node(
                node.getChildren()[0]
            )
        ]

        version_numbers = {
            paths_utils.get_version_number_from_basename(Path(path).name)
            for path in file_paths
        }

        if len(version_numbers) > 1:
            raise exceptions.PxoModelAssetError(
                f"PXO Model Asset inherits multiple versions {version_numbers}. "
                f"This is invalid."
            )

        asset_data_inst = ModelComponents(
            list(root_nodes)[0],
            asset_name,
            list(version_numbers)[0],
            ",".join(file_paths),
        )
        data_dict = asset_data_inst.__dict__()
        result_list.append(data_dict)
    return result_list


def get_legacy_model_data_list():
    """
    Get the model data list based on the legacy asset root workflow.

    Returns:
        List: [{'asset_name': 'crt_armyCoHorseC',
               'asset_root': nt.Transform('arm_01:crt_armyCoHorseC_mdl'),
               'components': {'armor_C_high_grp': {nt.Transform('arm_01:armor_C_high_grp'):
                              [nt.Transform('arm_01:chestPlate_C_001_high_geo'),
                               nt.Transform('arm_01:hindArmor_C_001_high_geo'),
                               nt.Transform('arm_01:tailArmor_C_001_high_geo'),
                               nt.Transform('arm_01:headPlate_C_001_high_geo'),
                               nt.Transform('arm_01:neckArmor_C_001_high_geo')]}},
               'publish_path': 'X:/redgun2_rg2-13437/_library/assets/creature/crt_armyCoHorseC/mdl/
                               _publish/rg2_crt_armyCoHorseC_mdl_v005_awg.mb',
               'resolution_groups': [nt.Transform('arm_01:low'),
                                    nt.Transform('arm_01:high')],
               'tagged_geo': False,
               'use_key_regex': False,
               'version': 5}]
    """
    assemble_list = []
    model_root_nodes = get_model_root_nodes_from_scene()
    for model_root_nd in model_root_nodes:
        version = 0
        file_path = scene_utils.get_filepath_from_referenced_node(model_root_nd)
        asset_name = "_".join(
            model_root_nd.name(long=None, stripNamespace=True).split("_")[0:-1]
        )
        if file_path:
            version = paths_utils.get_version_number_from_basename(
                os.path.basename(file_path)
            )
        else:
            file_path = ""
        assemble_list.append(([model_root_nd], asset_name, version, file_path))
    return [
        ModelComponents(asset[0][0], asset[1], asset[2], asset[3]).__dict__()
        for asset in assemble_list
    ]


##########################################################
# CLASSES
##########################################################


class ModelComponents(object):
    """
    This class will sort all input nodes into component,
    component_roots and component nodes.
    By a regex search on the node names or directly from
    component root nodes name.
    Then you can have it back as dictionary if you want.
    """

    COMPONENTS_KEY = constants.PXO_ASSET_ASSEMBLY_NODE_COMPONENTS_ATTR_SUFFIX
    ASSET_NAME_KEY = constants.PXO_ASSET_ASSEMBLY_NODE_ASSET_NAME_ATTR
    ASSET_ROOT_KEY = constants.PXO_ASSET_ASSEMBLY_NODE_ASSET_ROOT_NODE
    VERSION_KEY = constants.PXO_ASSET_ASSEMBLY_NODE_VERSION_ATTR
    PUBLISH_PATH_KEY = constants.PXO_ASSET_ASSEMBLY_NODE_ASSET_PUBLISH_PATH
    INVALID_KEY = constants.PXO_ASSET_ASSEMBLY_NODE_INVALID_COMP_ATTR_SUFFIX
    TAGGED_GEO = constants.PXO_ASSET_ASSEMBLY_NODE_TAGGED_GEO_ATTR_NAME
    USE_KEY_REGEX = constants.PXO_ASSET_ASSEMBLY_NODE_USE_KEY_REGEX_ATTR_NAME
    RESOLUTION_GRP_KEY = constants.PXO_ASSET_ASSEMBLY_NODE_RESOLUTION_NAME_ATTR

    def __init__(
        self,
        model_root_nd,
        asset_name,
        version,
        asset_path,
        tagged=False,
        use_key_regex=False,
        capitalize_regex=True,
        upper_regex=False,
        permute_component_regex=False,
        regex_pre_str="",
        regex_post_str="",
        strip_component_namespaces=False,
    ):
        """
        Args:
            model_root_nd(list): The nodes list as input.
            asset_name(str): The asset name.
            version(int): The asset version.
            asset_path(str): The asset path.
            tagged(bool): Will take tagged geos as relative path to find the
                          components roots. If False will take all
                          found mesh geos as relative paths.
                          Default is False.
            use_key_regex(bool): Take key strings from
                                _ASSET_MODEL_COMPONENT_DICT_KEY_LIST variable
                                for a regex search.
                                If False will take the component_roots name
                                directly as component keys.
                                Default is False.
            capitalize_regex(bool): Capitalize the string regex for searching.
                                    Default is True.
            upper_regex(bool): Upper the string regex for searching.
                               Default is False.
            permute_component_regex(bool): Use a permuted string regex
                                             for searching.
                                             This will allow upper and lowercase
                                             issues in the component name.
                                             Be aware this can cause issues if
                                             you have multiple declarations.
                                             Default is False.
            regex_pre_str(string): Add given string as pre string to search
                                   regex. So you can make your search more
                                   specific. Default is None.
            regex_post_str(string): Add given string as post string to search
                                    regex. So you can make your search more
                                    specific. Default is None.
            strip_component_namespaces(bool): Will strip the namespace of all component transform nodes.
                                              Default is False.
        """
        self.asset_name = asset_name
        self.asset_root = model_root_nd
        self.version = version
        self.publish_path = asset_path
        self.components = []
        self.components_roots = []
        self.components_nodes = []
        self.resolution_groups = []
        self.invalid_components = []
        self.invalid_component_roots = []
        self.invalid_component_nodes = []
        self.capitalize_regex = capitalize_regex
        self.upper_regex = upper_regex
        self.permute_component_regex = permute_component_regex
        self.regex_pre_str = regex_pre_str
        self.regex_post_str = regex_post_str
        self.use_key_regex = use_key_regex
        self.tagged = tagged
        self.strip_component_namespaces = strip_component_namespaces
        self._process_model_component_dict()

    @DECORATORS.x_timer
    def _process_model_component_dict(self):
        """
        Will sort given nodes into components,
        component_roots and component_nodes.
        By regex or by given found component root nodes.
        """
        component_root_nodes = get_model_component_roots_from_model_root_node2(
            self.asset_root, self.tagged
        )

        self.resolution_groups = get_model_resolution_nodes(self.asset_root)
        for node in component_root_nodes:
            if not self.use_key_regex:
                component = str(
                    node.name(
                        long=None,
                        stripNamespace=self.strip_component_namespaces,
                    )
                )
                export_geos = get_pxm_export_geo_nodes_from_root_node(
                    node, self.tagged
                )
                self.components.append(component)
                self.components_roots.append(node)
                self.components_nodes.append(export_geos)
            else:
                permute_regex_dict = {}
                if self.permute_component_regex:
                    permute_regex_dict = (
                        _get_permute_regex_string_dict_for_node_names()
                    )
                valid_regex_count = 0
                for key in ASSET_MODEL_COMPONENT_DICT_KEY_LIST:
                    regex = key
                    if self.upper_regex:
                        regex = regex.upper()
                    if self.permute_component_regex:
                        regex = permute_regex_dict[key]
                    if self.capitalize_regex:
                        regex = regex.capitalize()
                    regex = r"".join(
                        [self.regex_pre_str, regex, self.regex_post_str]
                    )
                    match = re.search(
                        regex, node.name(long=None, stripNamespace=True)
                    )
                    if match:
                        child_nodes = get_pxm_export_geo_nodes_from_root_node(
                            node, self.tagged
                        )
                        valid_regex_count = valid_regex_count + 1
                        if valid_regex_count != 2:
                            self.components.append(key)
                            self.components_roots.append(node)
                            self.components_nodes.append(child_nodes)
                        else:
                            self.invalid_components.append(match.group(0))
                            self.invalid_component_roots.append(node)
                            self.invalid_component_nodes.append(child_nodes)
                            _LOGGER.warning(
                                "Object name {} has"
                                " more then one description."
                                " Can not"
                                " sort"
                                " to"
                                " an"
                                " unique"
                                " component."
                                " Will move it"
                                " to invalid section".format(node.name())
                            )
                    ### Need a proper else because i miss the nodes
                    # which are not a match

    def __dict__(self, as_PyNodes=True):
        """
        Returns the sorted components data as dictionary.
        """

        def _process(components, components_roots, components_nodes):
            it = iter([components, components_roots, components_nodes])
            the_len = len(next(it))
            if not all(len(l) == the_len for l in it):
                raise ValueError(
                    "components, components_roots"
                    " and components_nodes lists do not have the same length."
                )
            components_dict = {}
            for component_, component_root_, component_nodes_ in zip(
                components, components_roots, components_nodes
            ):
                if as_PyNodes:
                    components_dict[component_] = {
                        component_root_: component_nodes_
                    }
                else:
                    components_dict[component_] = {
                        str(component_root_.nodeName()): [
                            str(node.nodeName()) for node in component_nodes_
                        ]
                    }
            return components_dict

        if not as_PyNodes:
            self.asset_root = str(self.asset_root.nodeName())

        result_dict = {
            self.ASSET_NAME_KEY: self.asset_name,
            self.VERSION_KEY: self.version,
            self.ASSET_ROOT_KEY: self.asset_root,
            self.PUBLISH_PATH_KEY: self.publish_path,
            self.TAGGED_GEO: self.tagged,
            self.USE_KEY_REGEX: self.use_key_regex,
            self.RESOLUTION_GRP_KEY: self.resolution_groups,
            self.COMPONENTS_KEY: _process(
                self.components, self.components_roots, self.components_nodes
            ),
        }
        if self.invalid_components:
            result_dict[self.INVALID_KEY] = _process(
                self.invalid_components,
                self.invalid_component_roots,
                self.invalid_component_nodes,
            )
        return result_dict


def save_mesh_obj(file_location, geometry_to_export):
    """
    Exports geometry as obj. Filename is geometry name.

    Args:
        file_location(path): The location of the file, with or without extension, but directory and name combined.
                             exp: [foo\bar\lol\file] or [foo\bar\lol\file.obj]
        geometry_to_export(str, pymel.core.PyNode): Geometry name or geometry PyNode to be exported.

    Returns:
        pymel.core.PyNode: The imported object as PyNode
    """

    previously_selected = cmds.ls(sl=True)
    if isinstance(geometry_to_export, str):
        geometry_to_export = pymel.core.PyNode(geometry_to_export)
    if not pymel.core.objExists(geometry_to_export):
        raise exceptions.SzeneSetupError(
            "geometry does not exists in the scene"
        )

    geometry_to_export_str = geometry_to_export.shortName()
    if not file_location.endswith(".obj"):
        geometry_to_export_namespace = geometry_to_export_str.replace(
            ":", "_NAMESPACE_"
        )
        construct_export_location = os.path.normpath(
            os.path.join(
                file_location, "{}.{}".format(geometry_to_export_namespace, "obj")
            )
        )
    else:
        construct_export_location = file_location

    cmds.select(geometry_to_export_str)
    cmds.file(
        construct_export_location,
        force=True,
        options="groups=0;ptgroups=0;materials=0;smoothing=0;normals=1",
        typ="OBJexport",
        pr=True,
        es=True,
    )

    cmds.select(previously_selected)
    return pymel.core.PyNode(geometry_to_export)


def load_mesh_obj(file_location):
    """
    Imports geometry as obj. Renames it to filename.

    Args:
        file_location(path): The location of the file, with or without extension, but directory and name combined.
                             exp: [foo\bar\lol\file] or [foo\bar\lol\file.obj]

    Returns:
        pymel.core.PyNode: The imported geometry as PyNode
    """
    import_path, tail = os.path.split(os.path.normpath(file_location))
    tail = tail.replace(":", "_NAMESPACE_")

    tail, extension = os.path.splitext(tail)
    if not extension == "obj":
        extension = "obj"

    file_name_with_suffix = "{}.{}".format(tail, extension)

    #   check if file exists in directory
    files = pymel.core.getFileList(
        folder=import_path, filespec="*.{}".format(extension)
    )
    if not files:
        raise ValueError("no files found in directory [{}]".format(import_path))
    if file_name_with_suffix not in files:
        raise ValueError(
            "the file [{}] does not exist in directory [{}]".format(
                file_name_with_suffix, import_path
            )
        )
    #   compose whole path
    file_path = os.path.normpath(
        os.path.join(import_path, file_name_with_suffix)
    )
    #   import geometry and change for namespaces
    new_geo = pymel.core.importFile(file_path, i=True, returnNewNodes=True)
    import_name = tail.replace("_NAMESPACE_", ":")

    #   rename imported geo to be legal in scene
    if not pymel.core.objExists(import_name):
        pymel.core.rename(new_geo[0], import_name)
    else:
        pymel.core.rename(new_geo[0], "{}_IMPORTED".format(import_name))

    return new_geo


def get_geo_root():
    """
    Searches the scene for nodes with attr pxo_rigging_kit.constants.ASSETROOT

    Returns:
        asset_geo_roots[0](pymel.core.PyNode()): first asset root found

    """
    asset_geo_roots = [
        x
        for x in pymel.core.ls(transforms=True)
        if pymel.core.objExists("{}.{}".format(x, PXO_ASSET_NAME_ATTR))
        and x.PXM_asset_geo_root.get()
    ]

    if not asset_geo_roots:
        raise exceptions.SzeneSetupError()

    return asset_geo_roots[0]


def get_mdl_geos():
    """
    Searches the scene for geo_root nodes and traverses through their children.
    Returns back all geos that came from modeling, and all model_root nodes.

    Returns:
        Tuple: (list(all_geometries), list(model_root_nodes))
    """

    scene_nodes = pymel.core.ls(transforms=True)
    model_root_nodes = get_model_root_nodes(scene_nodes)
    geometries = [
        model_root_node.getChildren(
            allDescendents=True, type="mesh", noIntermediate=True
        )
        for model_root_node in model_root_nodes
    ]
    if not geometries:
        return

    geometries_flattened = itertools.chain.from_iterable(geometries)
    return (
        list(set([x.getTransform() for x in geometries_flattened])),
        model_root_nodes,
    )
