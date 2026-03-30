# Author:     Johannes Wolz / Lead Rigging TD

"""
Utils code for rig scene assembly.
This module will handle rigging related scene imports.
For example it will import the asset and rigging related
model publish with the correct namespace and with shotgun hand off checkup.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Import built-in modules
from builtins import str
import logging
from importlib import reload

# Import third-party modules
from future import standard_library
from maya_proxy_node import asset_node
import pymel.core as pmc

# Import local modules
from pxo_rigging_kit import constants
from pxo_rigging_kit.maya_utils import decorators
from pxo_rigging_kit.maya_utils import model_utils
from pxo_rigging_kit.maya_utils import paths_utils
from pxo_rigging_kit.maya_utils import pymel_utils
from pxo_rigging_kit.maya_utils import scene_utils
from pxo_rigging_kit.maya_utils.rigging import rig_utils

standard_library.install_aliases()
reload(model_utils)

##########################################################
# GLOBALS
##########################################################

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)
DECORATORS = decorators.Decorators()
DECORATORS.debug = True
DECORATORS.logger = _LOGGER

HIERARCHY_DATA = {
        lod: model_utils.ASSET_MODEL_COMPONENT_DICT_KEY_LIST
        for lod in model_utils.MODEL_ASSET_HIERARCHY_LOD_TEMPLATE
    }

##########################################################
# FUNCTIONS
##########################################################


def import_model_publish(
    scene_name,
    category=None,
    asset_name=None,
    lod="",
    version_number=None,
    validate_version=True,
    reference=False,
    sg_handoff=True,
):
    """
    Import model publish to corresponding asset from this task and scene.
    Will import latest publish if sg status is hand off.
    Or you can import specific version.
    Furthermore you can validate given version to latest
    publish which sg status is hand off. If given version differ to latest
    will show log window where you can decide which version you want to take.

    Args:
        scene_name(str): Name of the current scene.
        category(str): The asset category. Here you can remap
                       to a different asset type.
                       Valid are ["props", "characters", "creature", "vehicles"]
                       Default is None
        asset_name(str): The asset name. Default is None
        lod(str): File lod. Will give you the appropriate .abc file.
                  If None will always return the .mb file.
                  Valid is ["sliced", "low", "high"].
                  Default is None.
        version_number(int): Gives back given version if exist.
                             If None will give you the latest publish file.
                             Default is None.
        validate_version(bool): Check if given version is latest publish version.
                                If not will show confirmBox for decision.
                                Default is True.
        reference(bool): Reference file. Default is False.
        sg_handoff(bool): Check if SG status is hand off. Default is True

    Return:
        Tuple: (int(version), str(import_path), List(imported nodes))

    """
    version = version_number

    if validate_version:
        version = None

    if sg_handoff:
        mdl_publish_data_dict = paths_utils.get_mdl_publish_file_path_with_sg_hand_off(
            scene_name, category, asset_name, lod, version
        )
    else:
        mdl_publish_data_dict = paths_utils.get_mdl_publish_file_path(
            scene_name, category, asset_name, lod, version
        )

    if validate_version:
        if version_number != mdl_publish_data_dict.get("version"):
            confirm = pmc.confirmBox(
                "Mdl publish import log",
                "Latest model publish version differs"
                " to given version. Do you want to take"
                " latest publish version",
            )
            if not confirm:
                if sg_handoff:
                    mdl_publish_data_dict = (
                        paths_utils.get_mdl_publish_file_path_with_sg_hand_off(
                            scene_name,
                            category,
                            asset_name,
                            lod,
                            version_number,
                        )
                    )
                else:
                    mdl_publish_data_dict = paths_utils.get_mdl_publish_file_path(
                        scene_name,
                        category,
                        asset_name,
                        lod,
                        version_number,
                    )
    import_version = mdl_publish_data_dict.get("version")
    import_path = mdl_publish_data_dict.get("path")

    namespace = scene_utils.generate_namespace_from_scene_name(import_path)

    if reference:
        import_nodes = pmc.createReference(import_path, rnn=True, ns=namespace)
    else:
        import_nodes = pmc.importFile(import_path, rnn=True, r=False, ns=namespace)

    if not asset_name:
        asset_name = paths_utils.get_asset_infos(scene_name, "asset_name")

    _LOGGER.info(
        f"{asset_name} mdl publish version {import_version} imported from {import_path}"
    )

    return (
        import_nodes,
        asset_name,
        import_version,
        import_path,
    )


def get_asset_assembly_nodes_from_scene():
    """
    Get the asset assembly nodes from the scene.

    Return:
        List: Empty if failure. Filled of pmc.PyNode() if successfully.

    """
    return [
        node
        for node in pymel_utils.get_custom_pxo_nodes_from_scene()
        if node.get_raw_pxo_uuid()
        == pymel_utils.process_pxo_uuid(
            [
                constants.PXO_UUID_DICT["meta"],
                constants.PXO_UUID_DICT["rig"],
                constants.PXO_UUID_DICT["asset_assembly"],
            ]
        )
    ]


def assemble_scene(
    scene_name,
    asset_list,
    validate_version=True,
    reference=False,
    sg_handoff=True,
    tagged=False,
    use_key_regex=False,
):
    """
    Assemble the scene with given model assets from the asset_list.
    The asset list has to be filled with dictionaries.
    Each of it represents a asset.
    It will always validate the version with a prompt window for each asset.
    And it will check if the assets are hand of flagged in Shotgrid.
    It will create a PxoAssetAssemblyMetaNode node right away for capsulate
    assembly data for the rig build.

    Args:
        scene_name(str): Name of the current scene.
        asset_list(list): Filled with asset data dictionaries.
                          This data dictionary has to look like this:

                          [{"category":None, "asset_name":None, "lod":"",
                            "version_number":False, "reference": False,
                            "sg_handoff":True},
                           {"category":"props", "asset_name":"prp_saddleSyrax",
                            "lod":"", "version_number":False, "reference": False,
                            "sg_handoff":True}]

                          Explanation:
                          category(str): Asset category like props, characters
                                         or creature. If None will take category
                                         from current rig asset and scene.
                          asset_name(str): The asset name. If None will take
                                           asset name from current rig asset
                                           and scene.
                          lod(str): The mdl lod you want. As string.
                                    Valid is ["sliced", "low", "high"].
                                    If emtpy string will take the master mb file.
                          version_number(int): The version you want to have.
                                               If False will take latest publish.
                          reference(bool): Reference the asset.
                                           That will overwrite the flag
                                           from this function just for this
                                           asset. And only if it exist in data
                                           dictionary.
                          sg_handoff(bool): Check if asset is
                                            hand off flagged in shotgrid.
                                            That will overwrite the flag
                                            from this function just for this
                                            asset. And only if it exist in data
                                            dictionary.
        validate_version(bool): Check if given version is latest publish version.
                                If not will show confirmBox for decision.
                                Default is True.
        reference(bool): Reference file. Default is False.
        sg_handoff(bool): Check if SG status is hand off. Default is True
        tagged(bool): Will take tagged geos as realitive path to find the
                      components roots.
                      If False will take all found mesh geos as relative paths.
        use_key_regex(bool): Take key strings from
                             _ASSET_MODEL_COMPONENT_DICT_KEY_LIST variable
                             for a regex search.
                             If False will take the component_roots name
                             directly as component keys.
                             Default is False.

    Example:
        >>> from pxo_rigging_kit.maya_utils import assembly_utils
        >>> asset_list = [{"category":None, "asset_name":None, "lod":"",
        >>>                "version_number":False},
        >>>               {"category":"props", "asset_name":"prp_saddleSyrax",
        >>>                "lod":"", "version_number":False}]
        >>> assembly_list = assembly_utils.assemble_scene(pmc.sceneName(),
        >>>                                               asset_list)

    Return:
        Tuple: All assembled assets in a list and the created
               PxoAssetAssemblyMetaNode.
              (
              PxoAssetAssemblyMetaNode,
              [(import_nodes(list), asset_name(str),
              import_version(int), import_path(str))]
              )

    """
    assemble_list = []
    for asset_dict in asset_list:
        reference_ = asset_dict.get("reference")
        sg_handoff_ = asset_dict.get("sg_handoff")
        validate_version_ = asset_dict.get("validate_version")
        if not reference_:
            reference_ = reference
        if not sg_handoff_:
            sg_handoff_ = sg_handoff
        if not validate_version:
            validate_version_ = validate_version

        asset = import_model_publish(
            scene_name,
            asset_dict["category"],
            asset_dict["asset_name"],
            asset_dict["lod"],
            asset_dict["version_number"],
            validate_version_,
            reference_,
            sg_handoff_,
        )
        assemble_list.append(asset)

    scene_model_component_list = [
        model_utils.ModelComponents(asset[0][0], asset[1], asset[2], asset[3], tagged, use_key_regex).__dict__()
        for asset in assemble_list
    ]
    rig_root_nd = rig_utils.get_rig_containers()
    asset_assemblies_list = get_asset_assembly_nodes_from_scene()

    if asset_assemblies_list:
        [node.delete_() for node in asset_assemblies_list]

    pxo_asset_assembly_node = pymel_utils.PxoAssetAssemblyMetaNode(
        name=constants.PXO_ASSET_ASSEMBLY_NODE_NAME
    )

    pxo_asset_assembly_node.populate_from_data_list(scene_model_component_list)

    if rig_root_nd:
        rig_root_nd[0].set_meta_asset_assembly_node(pxo_asset_assembly_node)

    return pxo_asset_assembly_node, assemble_list


def create_mdl_asset_hierarchy(
    scene_name,
    hierarchy_data=HIERARCHY_DATA,
    pxo_asset_node=False,
    asset_name=None,
):
    """
    Create mdl asset hierarchy.

    Args:
        scene_name(str): Name of the current scene.
        hierarchy_data(dict): For hierarchy structure creation.
                              Example:
                                  {'slices': ["Body", "Head", "Chest"],
                                   'low': ["Body", "Head", "Chest"],
                                   'mid': ["Body", "Head", "Chest"],
                                   'high': ["Body", "Head", "Chest"]}
        pxo_asset_node(bool): Enable the new pxoAsset node for creation.
                              If False will take legacy approach with tags.
                              Default is True.
        asset_name(str, optional): The asset name. If False will take
                                   asset name from current asset/scene.

    Return:
        pmc.PyNode(): The asset root node

    """
    root_node = None
    result_list = []
    lod_nodes = sorted(list(hierarchy_data.keys()))
    if not asset_name:
        asset_name = "_".join([paths_utils.get_asset_infos(scene_name, "asset_name"), "mdl"])
    asset_data = {
        "asset_name": asset_name,
        "asset_type": "model",
        "usage": "render",
    }
    if not pxo_asset_node:
        root_node = pmc.createNode("transform", n=asset_name)
        result_list.append(root_node)
        root_node.addAttr(
            constants.PXO_ASSET_GEO_ROOT,
            type="bool",
            keyable=False,
            defaultValue=True,
        )
        root_node.addAttr(
            constants.PXO_ASSET_NAME_ATTR,
            type="string",
            keyable=False,
        )
        root_node.attr(constants.PXO_ASSET_NAME_ATTR).set(asset_name)
    for lod_key in lod_nodes:
        component_nodes = [
            pmc.createNode("transform", n=component_name)
            for component_name in hierarchy_data.get(lod_key) if hierarchy_data.get(lod_key, None)
        ]
        if pxo_asset_node:
            asset_data["usage"] = lod_key
            lod_node = asset_node.create_pxo_asset(
                asset_data, lod_key, with_network=True
            )
            result_list.append(lod_node)
        else:
            lod_node = pmc.createNode("transform", n=lod_key)
            lod_node.setParent(root_node)
        if component_nodes:
            pmc.parent(component_nodes, lod_node)
    return result_list


def create_asset_assembly_node_from_scene():
    """
    Create the asset assembly node based on the mdl asset in the scene.

    Return:
        pmc.PyNode(): The new created asset_assembly node.

    """
    model_root_nodes = model_utils.get_model_root_nodes_from_scene()
    asset_assemblies_list = get_asset_assembly_nodes_from_scene()
    if asset_assemblies_list:
        [node.delete_() for node in asset_assemblies_list]
    if model_root_nodes[-1].nodeType() == "pxoAsset":
        scene_model_component_list = model_utils.get_pxo_assets_model_data_list()
    else:
        scene_model_component_list = model_utils.get_legacy_model_data_list()
    pxo_asset_assembly_node = pymel_utils.PxoAssetAssemblyMetaNode(
        name=constants.PXO_ASSET_ASSEMBLY_NODE_NAME
    )
    pxo_asset_assembly_node.populate_from_data_list(scene_model_component_list, True)
    rig_root_nd = rig_utils.get_rig_containers()
    if rig_root_nd:
        rig_root_nd[0].set_meta_asset_assembly_node(pxo_asset_assembly_node)
    return pxo_asset_assembly_node

def __create_asset_assembly_node(mdl_root_nd):
    for node in mdl_root_nd.message.connections():
        if node in get_asset_assembly_nodes_from_scene():
            node.delete_()
    model_component_list = [data_dict for data_dict in model_utils.get_pxo_assets_model_data_list(mdl_root_nd) if data_dict["asset_root"] == mdl_root_nd]
    pxo_asset_assembly_node = pymel_utils.PxoAssetAssemblyMetaNode(
        name=constants.PXO_ASSET_ASSEMBLY_NODE_NAME
    )
    pxo_asset_assembly_node.populate_from_data_list(model_component_list, True)
    return pxo_asset_assembly_node



def compare_rig_assembly_data(assembly_data_list_0, assembly_data_list_1):
    """
    Compare rig assembly data. This function needs two data arrays.
    For example you can get these arrays from the pymel_utils.PxoAssetAssemblyMetaNode().
    They should look like this:
    [
    {
        "publish_path": u"X:/redgun2-previs_r2p-14130/_library/assets/creature
                          /crt_Caraxes/mdl/_publish/
                          r2p_crt_Caraxes_mdl_v014_laf.mb",
        "use_key_regex": False,
        "asset_name": u"crt_Caraxes",
        "version": 14,
        "asset_root": "Car_014:crt_Caraxes_mdl",
        "components": {
            "teeth_C_low_grp": {
                "Car_014:teeth_C_low_grp": [
                    "Car_014:caraxesTeeth_C_001_low_geo",
                    "Car_014:caraxesTeeth_C_001_low_geo",
                ]
            },
            "saddle_C_low_grp": {
                "Car_014:saddle_C_low_grp": [
                    "Car_014:caraxesSaddle_C_001_low_geo",
                    "Car_014:caraxesSaddle_C_001_low_geo",
                ]
            },
            "eye_C_low_grp": {
                "Car_014:eye_C_low_grp": [
                    "Car_014:caraxesCornea_C_001_low_geo",
                    "Car_014:caraxesCornea_C_001_low_geo",
                ]
            },
            "claws_C_low_grp": {
                "Car_014:claws_C_low_grp": [
                    "Car_014:caraxesClaws_C_001_low_geo",
                    "Car_014:caraxesClaws_C_001_low_geo",
                ]
            },
            "body_C_low_grp": {
                "Car_014:body_C_low_grp": [
                    "Car_014:caraxesBody_C_001_low_geo",
                    "Car_014:caraxesBody_C_001_low_geo",
                ]
            },
        },
        "tagged_geo": False,
    }
    ]

    Args:
        assembly_data_list_0(list): First data array.
        assembly_data_list_1(list): Second data array

    Returns:
        None if no differences in the data arrays.
        Else a dictionary with the results of the comparison:
        {
        "lost_assets": lost_assets,
        "added_assets": added_assets,
        "lost_components": lost_components,
        "added_components": added_components,
        "lost_components_objects": lost_components_objects,
        "added_components_objects": added_components_objects,
        }
    """
    lost_components = {}
    added_components = {}
    lost_components_objects = {}
    added_components_objects = {}
    asset_names_0 = sorted(
        [data_dict["asset_name"] for data_dict in assembly_data_list_0]
    )
    asset_names_1 = sorted(
        [data_dict["asset_name"] for data_dict in assembly_data_list_1]
    )
    total_asset_names = list(set(asset_names_0 + asset_names_1))
    difference_asset_name = list(
        set(asset_names_0).symmetric_difference(set(asset_names_1))
    )
    lost_assets = [
        asset_name
        for asset_name in difference_asset_name
        if asset_name in asset_names_0
    ]
    added_assets = [
        asset_name
        for asset_name in difference_asset_name
        if asset_name in asset_names_1
    ]
    asset_data_dict_0 = {
        data_dict["asset_name"]: data_dict["components"]
        for data_dict in assembly_data_list_0
    }
    asset_data_dict_1 = {
        data_dict["asset_name"]: data_dict["components"]
        for data_dict in assembly_data_list_1
    }
    for asset_name_ in total_asset_names:
        if asset_name_ in asset_data_dict_0 and asset_name_ in asset_data_dict_1:
            components_0_dict = asset_data_dict_0[asset_name_]
            components_1_dict = asset_data_dict_1[asset_name_]
            difference_components = list(
                set(list(components_0_dict.keys())).symmetric_difference(
                    set(list(components_1_dict.keys()))
                )
            )
            lost_components_list = [
                dif_comp
                for dif_comp in difference_components
                if dif_comp in components_0_dict
            ]
            added_components_list = [
                dif_comp
                for dif_comp in difference_components
                if dif_comp in components_1_dict
            ]
            if lost_components_list:
                lost_components[asset_name_] = lost_components_list
            if added_components_list:
                added_components[asset_name_] = added_components_list
            total_components = list(
                set(list(components_0_dict.keys()) + list(components_1_dict.keys()))
            )
            for component in total_components:
                if component in components_0_dict and component in components_1_dict:
                    component_key = list(components_0_dict[component].keys())[0]
                    trs_list_0 = components_0_dict[component].get(component_key)
                    trs_list_1 = components_1_dict[component].get(component_key)
                    difference_components_objects = list(
                        set(trs_list_0).symmetric_difference(set(trs_list_1))
                    )
                    lost_component_objects_list = [
                        dif_comp_obj
                        for dif_comp_obj in difference_components_objects
                        if dif_comp_obj in trs_list_0
                    ]
                    added_component_objects_list = [
                        dif_comp_obj
                        for dif_comp_obj in difference_components_objects
                        if dif_comp_obj in trs_list_1
                    ]
                    if lost_component_objects_list:
                        lost_components_objects[component] = lost_component_objects_list
                    if added_component_objects_list:
                        added_components_objects[
                            component
                        ] = added_component_objects_list
    if not any(
        [
            lost_assets,
            added_assets,
            lost_components,
            added_components,
            lost_components_objects,
            added_components_objects,
        ]
    ):
        return
    return {
        "lost_assets": lost_assets,
        "added_assets": added_assets,
        "lost_components": lost_components,
        "added_components": added_components,
        "lost_components_objects": lost_components_objects,
        "added_components_objects": added_components_objects,
    }
