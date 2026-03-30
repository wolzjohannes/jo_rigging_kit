# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import pathlib

# Import built-in modules
from builtins import str
import getpass
import sys

# Import python standart import
import logging
import os
import re
import shutil


# Import third-party modules
from future import standard_library
from maya_scene_io import export_scene
from maya_scene_io.paths import get_temp_path
from mgear.shifter import guide
from mgear.shifter import guide_manager
from mgear.shifter import io
import pixo_paths

# Import maya modules
from maya import cmds  # noqa: import error
from maya.api import OpenMaya as om2 # noqa: import error
import pymel.core as pmc
import pymel.core.datatypes as dt


# Import local modules
from pxo_rigging_kit import constants
from pxo_rigging_kit import paths
from pxo_rigging_kit.constants import GUIDES_PUBLISH_DIR_NAME
from pxo_rigging_kit.core import get_config
from pxo_rigging_kit.core import get_index_as_int
from pxo_rigging_kit.maya_utils import dag_utils
from pxo_rigging_kit.maya_utils import decorators
from pxo_rigging_kit.maya_utils import exceptions
from pxo_rigging_kit.maya_utils import paths_utils
from pxo_rigging_kit.maya_utils import scene_utils
from pxo_rigging_kit.maya_utils.rigging import rig_utils
from pxo_rigging_kit.maya_utils import mesh_utils

#######################################################
# GLOBALS
#######################################################

standard_library.install_aliases()
_LOGGER = logging.getLogger(f"{__name__}.py")
_LOGGER.setLevel(logging.INFO)
DECORATORS = decorators.Decorators()
DECORATORS.debug = True
DECORATORS.logger = _LOGGER
GUIDES_BUFFER_CRV_GRP_ROOT_ND_NAME = "controllers_org"
PRE_SCRIPT_ATTR_NAME = ""
#######################################################
# GLOBALS
#######################################################

##########################################################
# VARS
##########################################################
ui_interesting = {'ui': 'interesting'}

UNWANTED_PXO_NODES = {"PXO_lookdev_merge*",
                      "aiPxoProxySwitch*",
                      "pxo_asset_assembly_NTW*",
                      "delete_on_publish*",
                      "pxm_rig_root_set*",
                      "components_root_set*",
                      "controllers_set*",
                      "deformers_set*",
                      "rig_root_grp_geo_grp*",
                      "sceneConfigurationScriptNode*",
                      "uiConfigurationScriptNode*",
                      }

##########################################################
# FUNCTIONS
##########################################################


def get_guide_root_nd_from_selection():
    """
    Get the guide root node from selection

    Return:
        None if fail. pmc.PyNode() if successfuly.

    """
    selection = pmc.ls(sl=True)
    if selection:
        selection = selection[0]
    if selection.hasAttr("ismodel") and selection.ismodel.get() is True:
        return selection
    else:
        pmc.error("Selection is not a mgear guide root node.")
        return


def refactor_path(string_, target_path, script_typ="build_pre_scripts"):
    """
    Refactor the path.

    Args:
        string_(str): The string path to change.
        target_path(str): The new target path.
        Valid value is ["build_pre_scripts", "build_post_scripts"]

    Return:
        String: The new string.

    """
    filename = os.path.basename(string_.split("|")[1])
    ref_path = pixo_paths.normalize(
        os.path.join(target_path, script_typ, filename)
    )
    return str(r"{}| {}".format(string_.split("|")[0], ref_path))


def change_custom_steps_entries(
    guide_root_nd, target_path, pre_scripts=True, post_scripts=True
):
    """
    Change the guide custom steps.

    Args:
        guide_root_nd(pmc.PyNode()): The guide root node.
        target_path(str): The new target path.
        pre_scripts(bool): Edit the pre scripts.
        post_scripts(bool): Edit the post scripts.

    """
    if pre_scripts:
        pre_cu_sc = guide_root_nd.preCustomStep.get()
        pre_cu_sc = pre_cu_sc.split(",")
        new_pre_cu_sc = []
        for string_ in pre_cu_sc:
            new_pre_cu_sc.append(refactor_path(string_, target_path))
        guide_root_nd.preCustomStep.set(",".join(new_pre_cu_sc))
    if post_scripts:
        post_cu_sc = guide_root_nd.postCustomStep.get()
        post_cu_sc = post_cu_sc.split(",")
        new_post_cu_sc = []
        for string_ in post_cu_sc:
            new_post_cu_sc.append(
                refactor_path(string_, target_path, "build_post_scripts")
            )
        guide_root_nd.postCustomStep.set(",".join(new_post_cu_sc))
    _LOGGER.info("m-gear custom steps refactored to path {}".format(target_path))


def lite_chain_01_guide_from_curves(curves):
    """
    Generates a lite_chain_01 based on given curves.

    Args:
        curves(list): List of curve pmc.PyNode().

    """
    pmc.select(cl=True)
    for crv in curves:

        cvs = crv.getShape().getCVs(space="world")

        if pmc.objExists("guide"):
            pmc.select("guide")

        guide_manager.draw_comp("lite_chain_01", parent=None, showUI=False)
        root_comp = pmc.selected()[0]

        guide_subs = list()
        guide_subs.append(root_comp)

        guide_locs = [
            x
            for x in root_comp.listRelatives(
                allDescendents=True, type="transform"
            )
            if "_loc" in str(x.shortName())
        ]
        guide_locs.sort(key=get_index_as_int)

        guide_subs.extend(guide_locs)

        for iteration_, sub in enumerate(guide_subs):
            sub.setTranslation(cvs[iteration_], space="world")

        decomposed_curve_name = str(crv.shortName()).split("_")

        # This is a critical part of the code. This requires a fixed naming convention.
        if len(decomposed_curve_name) == 4:
            name_, side_, index_ = decomposed_curve_name[0:-1]
        else:
            raise ValueError("We only assume it to be one")
        guide.Rig().updateProperties(root_comp, name_, side_, str(index_))


def control_01_guide_from_transforms(
    transforms,
    comp_name_index=0,
    side_index=1,
    index_num_index=False,
    split_char="_",
    joint=True,
    control_shape="sphere",
    control_size=1.0,
):
    """
    Creates control_01 guides based on given transforms.

    Args:
        transforms(list): List of transforms in the scene.
        comp_name_index(int): Index where we find the component name in the name of the selected transforms.
        side_index(int): Index where we find the component side in the name of the selected transforms.
        index_num_index(int): Index where we find the component index in the name of the selected transforms.
                              If False a 0 is hardcoded into the name of the control_01 guide.
                              Default is False.
        split_char(str): The character for the name splitting.
                         Default is "_".
        joint(bool): Define if the control needs a bind joint.
        control_shape(str): The shape of the builded control curve.
                            Default is "sphere".
        control_size(float): The control size.
                             Default is 1.0.

    """
    pmc.select(cl=True)
    for trf in transforms:
        if pmc.objExists("guide"):
            pmc.select("guide")
        guide_manager.draw_comp("control_01", parent=None, showUI=False)
        root_comp = pmc.selected()[0]
        pmc.matchTransform(root_comp, trf)
        root_comp.neutralRotation.set(False)
        root_comp.joint.set(joint)
        root_comp.icon.set(str(control_shape))
        root_comp.ctlSize.set(control_size)
        decomposed_trf_name = str(trf.shortName()).split(split_char)
        comp_name = decomposed_trf_name[comp_name_index]
        side_ = decomposed_trf_name[side_index]
        index_ = 0
        if index_num_index is not False:
            index_ = int(decomposed_trf_name[index_num_index])
        guide.Rig().updateProperties(root_comp, comp_name, side_, str(index_))


def select_guide_root_nd_from_component(component):
    """
    Select the guides root node from given component.

    Args:
        component(pmc.PyNode): The given component node.

    """
    root_nd = dag_utils.get_root_node_from_child_node(component)
    pmc.select(root_nd)


def set_pre_and_post_scripts_to_user(
    prestring="Users",
    poststring="gitlab",
    attrs_=("preCustomStep", "postCustomStep"),
):
    """
    Goes through all guide root nodes in the scene, and replaces the user string with the current user.

    Args:
        prestring(str): String that comes in front of the user-name.
        poststring(str): String that comes after the user-name.
        attrs_(tuple): Attributes that need their user replaced.

    Returns:
        Bool: True when finished.

    """

    all_guides_in_scene = get_scene_guides()
    if not all_guides_in_scene:
        return

    user_name = str(getpass.getuser())

    find_path_pattern = re.compile(
        r"[{0}]+/[A-Za-z]+\.[A-Za-z]+/[{1}]+".format(prestring, poststring)
    )

    for guide_nd in all_guides_in_scene:
        for attr_name_ in attrs_:
            if not guide_nd.hasAttr(attr_name_):
                continue

            attribute_to_replace = str(guide_nd.attr(attr_name_).get())

            if not attribute_to_replace:
                continue

            replaced = find_path_pattern.sub(
                r"{0}/{1}/{2}".format(prestring, user_name, poststring),
                attribute_to_replace,
            )

            guide_nd.attr(attr_name_).set(replaced)

    return True


def get_scene_guides():
    """
    Get the guides from the scene. Could be more then one.

    Returns:
        List or None.

    """
    all_transforms_in_scene = pmc.ls(type="transform")
    all_guides_in_scene = [
        guide_nd
        for guide_nd in all_transforms_in_scene
        if guide_nd.hasAttr("ismodel") and guide_nd.ismodel.get() is True
    ]
    return all_guides_in_scene


def get_guide_root_nd():
    """
    Get rig guide root node in the scene.

    Return:
        Raise exceptions.MayaNodeNotFound if no guide root node found.
        Raise ValueError if more then one guide root node exist.
        pmc.PyNode(): The guide root node if successfully.

    """
    guide_root_nodes_list = [
        node
        for node in pmc.ls(type="transform")
        if node.hasAttr(constants.GUIDE_TAG_NAME)
        and node.attr(constants.GUIDE_TAG_NAME).get()
    ]
    if not guide_root_nodes_list:
        raise exceptions.MayaNodeNotFound(
            "No guide node exist or '{}' tag are off.".format(
                constants.GUIDE_TAG_NAME
            )
        )
    if len(guide_root_nodes_list) == 2:
        raise ValueError(
            "More then one guide node exists: {}".format(guide_root_nodes_list)
        )
    return guide_root_nodes_list[0]

def get_ctrl_naming_rule():
    guide_root_nd = get_guide_root_nd()
    return str(guide_root_nd.ctl_name_rule.get())


def get_guide_meta_data():
    """
    Get the meta data from rig guide root node.

    Return:
        Dict: {constants.GUIDE_VERSION_ATTR_NAME: guide_version}
    """
    guide_root_nd = get_guide_root_nd()
    try:
        guide_version = guide_root_nd.attr(
            constants.GUIDE_VERSION_ATTR_NAME
        ).get()
    except:
        guide_version = 0
    return {constants.GUIDE_VERSION_ATTR_NAME: guide_version}


def lazy_sel_guide():
    """
    Select guides only when it is unique.

    Returns:
        False if it not exists or when it is not unique.

    """
    scene_guides = get_scene_guides()

    if not scene_guides or len(scene_guides) > 1:
        return False

    pmc.select(scene_guides[0])


@DECORATORS.x_timer
def last_guide_standing():
    """
    Will kill all assemblie nodes and objects sets in the scene.
    But the rig guide nodes will survive.
    """
    temp_list = []
    guide_root_nodes = get_scene_guides()
    if len(guide_root_nodes) > 1:
        raise exceptions.MayaNodeNameUniqueness("Guide node is not unique.")
    pmc.parent(guide_root_nodes, None)
    scene_assemblies = [
        node for node in pmc.ls(assemblies=True) if node not in guide_root_nodes
    ]
    object_set = pmc.ls(type="objectSet")
    temp_list.extend(scene_assemblies)
    temp_list.extend(object_set)
    scene_utils.import_references()
    pmc.delete(temp_list)


def _unlock_and_delete(stem):
    for x in cmds.ls(stem):
        cmds.lockNode(x, lock=False)
        cmds.delete(x)


def import_cleaned(guide_path):
    guide_path_ = pathlib.Path(guide_path).resolve()
    pmc.importFile(str(guide_path_))

    file_basename = guide_path_.stem
    for name_stem in UNWANTED_PXO_NODES:
        print(f"removing:  {file_basename}_{name_stem}")
        _unlock_and_delete(f"{file_basename}_{name_stem}")


@DECORATORS.x_timer
def remove_unwanted_nodes():
    """
    Will kill all nodes that are automatically created by pixo.
    """

    def _get_controllers_fast() -> set:
        """
        Searches the DG for om2.MFn.kControllerTags and puts them into a set, to delete later.
        Returns:

        """
        control_tags = set()

        iter_ = om2.MItDependencyNodes(om2.MFn.kControllerTag)
        node_pointer = om2.MFnDependencyNode()

        while not iter_.isDone():
            node_pointer.setObject(iter_.thisNode())
            control_tags.add(node_pointer.name())
            iter_.next()

        return control_tags

    for name_stem in UNWANTED_PXO_NODES:
        _unlock_and_delete(f"::{name_stem}")

    cmds.delete(_get_controllers_fast())


@DECORATORS.x_timer
def _get_guides_publish_path():
    """
    Get the guides publish path if path not exist will create one.

    Returns:
        String: The path.

    """

    root_path = paths_utils.get_root_path(pmc.sceneName(),
                                          root_name="asset_task",
                                          )

    publish_path = pixo_paths.normalize(
        os.path.join(root_path, GUIDES_PUBLISH_DIR_NAME)
    )

    if not os.path.exists(publish_path):
        os.mkdir(publish_path)

    return publish_path


@DECORATORS.x_timer
def generate_guides_publish_name(
    pub_file_name_pattern=("ASSET_NAME", "VERSION", "USER"),
    asset_name_token_index=0,
    version_name_token_index=1,
    user_name_token_index=2,
    guides_suffix="RIGGUIDES",
):
    """
    Generates the publishing guides file name.
    This requieres a file taking place in the PXO environment.
    This means the file needs to be saved with the PXO save/load.

    Args:
        pub_file_name_pattern(tuple): Defines the name pattern.
                                     If the name pattern will be modified the token indexes
                                     needs to be adjusted as well.
                                     Default is ["ASSET_NAME", "VERSION", "USER"].
        asset_name_token_index(int): The index of the asset pattern in the pub_file_name_pattern arg.
                                     Default is 0 == "ASSET_NAME".
        version_name_token_index(int): The index of the version pattern in the pub_file_name_pattern arg.
                                  Default is 1 == "VERSION".
        user_name_token_index(int): The index of the user pattern in the pub_file_name_pattern arg.
                               Default is 1 == "USER".
        guides_suffix(str): The rig guide suffix name.
                            Default is "RIGGUIDES".

    Returns:
        String: The new name.

    """
    pub_file_name_pattern_tmp = list(pub_file_name_pattern)

    pub_file_name_pattern_tmp.append(guides_suffix)
    current_version = paths_utils.get_version_number_from_basename(
        pmc.sceneName()
    )
    current_user_abr = paths_utils.get_user_abbr(pmc.sceneName())
    asset_name = paths_utils.get_asset_infos(pmc.sceneName(), "asset_name")
    file_name_pattern = "_".join(pub_file_name_pattern_tmp)
    file_name = file_name_pattern.replace(
        pub_file_name_pattern_tmp[asset_name_token_index], str(asset_name)
    )
    file_name = file_name.replace(
        pub_file_name_pattern_tmp[version_name_token_index],
        "v{}".format(str(current_version).zfill(3)),
    )
    file_name = file_name.replace(
        pub_file_name_pattern_tmp[user_name_token_index], str(current_user_abr)
    )
    return file_name


@DECORATORS.x_timer
def rename_guide_root_nd(guides_name):
    """
    Rename the guides root node of the scene to given name.

    Args:
        guides_name(str): The new name.

    """
    guide_root_nodes = get_scene_guides()
    if guide_root_nodes:
        for node in guide_root_nodes:
            node.rename(guides_name)


def publish_guides(safe_mode: bool = True,
                   type_mode: str = "sgt",
                   ):
    """
    Publish the guides in the scene to the asset rig task folder into a new directory.
    The directory name is defined in the pxo_rigging_kit.constants module in the
    GUIDES_PUBLISH_DIR_NAME variable.

    Args:
        safe_mode(bool): Save and rename the current file before execute the publishing steps.
                         This will prevent a corruption of the source scene.

    """
    publish_path = _get_guides_publish_path()
    guides_publish_file_name = generate_guides_publish_name()

    # remove pxo related nodes, remove controller nodes
    if safe_mode:
        pmc.saveFile(force=True, type="mayaAscii")
        temp_path = get_temp_path(".mb")
        temp_file = pixo_paths.normalize(
            os.path.join(temp_path, "NO_WORKFILE.mb")
        )
        pmc.renameFile("NO_WORKFILE")
        remove_unwanted_nodes()

        scene_utils.delete_unkown_plugins()

        scene_utils.delete_unkown_nodes()

        pmc.exportAll(temp_file)
        _LOGGER.info(f"Cleanup Operations for saver export concluded.")

    # kill all but last
    last_guide_standing()

    # change name into context
    rename_guide_root_nd(guides_publish_file_name)

    # get the name
    guide_root_nd = get_scene_guides()

    for node in guide_root_nd:
        node.visibility.set(1)

    guide_publish_path = os.path.join(
        publish_path, f"{guides_publish_file_name}"
    )

    pmc.select(guide_root_nd)

    if type_mode == "sgt":
        path_ = f"{guide_publish_path}.sgt"

        io.export_guide_template(filePath=path_)
        _LOGGER.info(f"Guide saved to: {path_}")
        return True

    options = {
        "force": True,
        "type": "mayaBinary",
        "shader": False,
        "channels": True,
        "constraints": True,
        "expressions": True,
    }

    path_ = f"{guide_publish_path}.mb"
    export_scene.export_type(path_,
                             extension="mb",
                             nodes=None,
                             options=options,
                             overrides={}
                             )

    _LOGGER.info(f"Guide saved to: {path_}")
    return True


def load_latest_guides(guide_file_type="mb"):
    """
    Loads the latest published mgear guides.

    Args:
        guide_file_type(str): The guides file type.

    """

    publish_path = _get_guides_publish_path()
    latest_guide_path = paths.get_latest_file_in_dir(
        publish_path, guide_file_type
    )
    pmc.importFile(filepath=latest_guide_path)
    _LOGGER.info("Guide loaded from to: {0}".format(latest_guide_path))


def mgear_guide_on_selected_crv():
    """
    Distribute the guide on a curve, based on selection
    select first the curve and then the guide root.
    """

    elem = pmc.selected()

    if len(elem) != 2:
        return -1
    if elem[0].getShape().type() != "nurbsCurve":
        return -1
    if "root" not in elem[1].name():
        return -1

    crv = elem[0]
    guide_root = elem[1]
    children = pmc.ls(guide_root.name().replace("_root", "*_loc"))
    children.insert(0, guide_root)
    positions = rig_utils.distribute_locators_on_curve(crv, len(children), True)

    for guide, point in zip(children, positions):
        pmc.move(guide, point, worldSpace=True)


def get_buffer_root_grp_from_guide(
    guide_root_nd, buffer_crv_root_name=GUIDES_BUFFER_CRV_GRP_ROOT_ND_NAME
):
    """
    Get buffer curve root node with specified name.
    Default name is GUIDES_BUFFER_CRV_GRP_ROOT_ND_NAME.

    Args::
        guide_root_nd(pmc.PyNode): The guides root node.
        buffer_crv_root_name(str): The controllers_org node name.
                                   Default is GUIDES_BUFFER_CRV_GRP_ROOT_ND_NAME.

    Returns:
        List: pmc:PyNode.
        Empty list: If no node exist with given name as child of the guide_root_nd.

    """
    return [
        node
        for node in guide_root_nd.getChildren()
        if node.name(long=None) == buffer_crv_root_name
    ]


def get_buffer_root_grp_from_scene(
    buffer_crv_root_name=GUIDES_BUFFER_CRV_GRP_ROOT_ND_NAME,
):
    ctrl_buffer_grp = pmc.ls(buffer_crv_root_name)
    if len(ctrl_buffer_grp) > 1:
        raise exceptions.MayaNodeNotFound(
            f"More then one buffer root grp with the name {buffer_crv_root_name} found in the scene."
        )
    try:
        return ctrl_buffer_grp[0]
    except:
        raise exceptions.MayaNodeNotFound(
            f"No buffer root grp with the name {buffer_crv_root_name} exist."
        )


def import_guide_template_from_repo(
    template_name, file_format="sgt", guides_template_path=None
):
    """
    Will import guide template for given template_name.
    If guide template is a mgear .sgt file it will import it with mgear import template func.

    Args:
        template_name(str): The template name
        guides_template_path(str): Path for the template path. This serves as override.
                                   If None will take constants.GUIDES_TEMPLATE_PATH.
                                   Default is None.

    Returns:
        pmc.PyNode(): Guide root node
        FileNotFoundError if no file for template name exist.

    """
    guide_path = get_guide_template_from_config(
        template_name, file_format, guides_template_path
    )
    if not guide_path:
        raise FileNotFoundError(
            f"Guide template file for {template_name} not found in repo."
        )
    if file_format == "sgt":
        io.import_guide_template(guide_path[0])
    else:
        pmc.importFile(guide_path[0])
    try:
        guide_root_name = generate_guides_publish_name()
        rename_guide_root_nd(guide_root_name)
    except:
        _LOGGER.warning(
            "Guide root name wasn't generatable will take standart name"
        )
    return get_guide_root_nd()


def get_guides_template_config():
    """
    Get the guides template config values form package config file.

    Return:
        raise EnvironmentError if fail.
        Tuple: (guide_templates_data_dict, guide_template_file_formats)

    """
    try:
        guide_templates = get_config("guide_templates:templates")
        guide_template_file_formats = get_config(
            "guide_templates:templates_file_formats"
        )
        return guide_templates, guide_template_file_formats
    except:
        raise EnvironmentError(
            "No pxo_rigging_kit.yaml config exist."
            " Or these keys are missing:"
            " [guide_templates:templates,"
            " mocap_utils:hik_source_char_description]"
        )


def get_guide_template_from_config(
    template_name, file_format="sgt", guides_template_path=None
):
    """
    Get guide templates based on the repo config.

    Args:
        template_name(str): Template name.
        file_format(str): File format.
                          Valid values are ["mb", "sgt"]
        guides_template_path(str): Path for the template path. This serves as override.
                                   If None will take constants.GUIDES_TEMPLATE_PATH.
                                   Default is None.

    Returns:
        List: Guide template path.
        Empty list if template file not exist in the repo.

    """
    if not guides_template_path:
        guides_template_path = constants.GUIDES_TEMPLATE_PATH
    (
        guide_templates_data_dict,
        guide_templates_format,
    ) = get_guides_template_config()
    guide_template_dict = guide_templates_data_dict.get(template_name, False)
    if not guide_template_dict:
        raise AttributeError(
            f"{template_name} not found in guides template config."
        )
    if not file_format in guide_templates_format:
        raise TypeError(f"File format: {file_format} not valid.")
    result = [
        pixo_paths.normalize(entry.path)
        for entry in os.scandir(pixo_paths.normalize(guides_template_path))
        if entry.name == f"{guide_template_dict['template']}.{file_format}"
    ]
    return result


def get_custom_scripts_from_repo(
    asset_name, pre_scripts_paths=None, post_scripts_paths=None
):
    """
    Get the post and pre script dtored in the repo.

    Args:
        asset_name: The asset name.
        pre_scripts_paths(str): Path to the pre scripts. This flag srves as override.
                                If None will find automatically the scripts in this repo.
                                Default is None.
        post_scripts_paths(str): Path to the post scripts. This flag srves as override.
                                If None will find automatically the scripts in this repo.
                                Default is None.

    Returns:
        Tuple: [pre_scripts_paths], [post_scripts_paths]
    """
    if not pre_scripts_paths:
        pre_scripts_paths = constants.MGEAR_PRE_SCRIPT_PATH

    if not post_scripts_paths:
        post_scripts_paths = constants.MGEAR_POST_SCRIPT_PATH

    def _get_after_build_scripts(scripts_ref, scripts_paths):
        if not scripts_ref:
            return []

        _LOGGER.debug(f"SCRIPTS PATH: {scripts_paths}")
        scripts_path_ = pathlib.Path(scripts_paths)

        if not scripts_path_.exists():
            raise EnvironmentError("the scripts path searched does not exist on disk")

        result = list()
        for individual_script in scripts_ref:
            individual_script_path = scripts_path_ / f"{individual_script}"

            if not individual_script_path.exists():
                _LOGGER.error(f"{str(individual_script_path.resolve())} not exist. Will skip.")
                continue

            result.append(str(individual_script_path.resolve()))

        return result

    (
        guide_templates_data_dict,
        guide_templates_format,
    ) = get_guides_template_config()

    guide_template_dict = guide_templates_data_dict.get(asset_name, False)
    if not guide_template_dict:
        raise AttributeError(f"No template data dict exist for {asset_name}.")

    pre_scripts = guide_template_dict.get("pre_scripts")
    post_scripts = guide_template_dict.get("post_scripts")

    pre_scripts = _get_after_build_scripts(
        pre_scripts,
        pre_scripts_paths,
    )

    post_scripts = _get_after_build_scripts(
        post_scripts,
        post_scripts_paths,
    )
    return pre_scripts, post_scripts


def get_guide_templates_from_asset_context(file_format="sgt"):
    """
    Will find the guides template in guides folder of the current asset context.

    Args:
        file_format(str): Template file format. Valid values are ["sgt", "mb"]

    Returns:
        Generator: All found template paths.

    """
    guides = None
    guide_publish_path = _get_guides_publish_path()
    if guide_publish_path:
        guides = {
            entry.name.replace(f".{file_format}", ""): entry.path
            for entry in os.scandir(guide_publish_path)
            if entry.name.endswith(f".{file_format}")
        }
    return guides


def clone_custom_scripts_to_asset_dir(
    asset_name,
    override="Yes",
    confirm_box=True,
    pre_scripts_paths=None,
    post_scripts_paths=None,
):
    """
    Clone the custom scripts from the repo to the asset scripts dir.

    Args:
        asset_name(str): The asset name.
        override(str): With this flag you can override already existing scripts or a add them as copy.
                       Valid values ["Yes", "No", "Add as copy"]
                       Default value is "Yes"
        confirm_box(bool): Enable/Disable the clone custom step confirm box if custom step already exist.
        pre_scripts_paths(str): Path to the pre scripts. This flag srves as override.
                                If None will find automatically the scripts in this repo.
                                Default is None.
        post_scripts_paths(str): Path to the post scripts. This flag srves as override.
                                If None will find automatically the scripts in this repo.
                                Default is None.

    Returns:
        Tuple: [new_pre_script_paths],[new_post_script_paths]

    """
    try:
        custom_scripts_folder = paths_utils.get_project_paths(
            pmc.sceneName(), path_type="scripts"
        )
    except:
        custom_scripts_folder = paths_utils.get_project_paths(
            pmc.sceneName(), "shot_task", "scripts"
        )

    def _clone_process(script_paths):
        result = []
        override_tmp = override
        if script_paths:
            for script_path in script_paths:
                new_path = pixo_paths.normalize(
                    os.path.join(
                        custom_scripts_folder, os.path.basename(script_path)
                    )
                )
                if os.path.exists(new_path):
                    if confirm_box:
                        override_tmp = pmc.confirmBox(
                            f"Clone custom step: {os.path.basename(new_path)}",
                            "The custom steps you want to clone is already cloned. Do you want to override it?",
                            "Yes",
                            "No",
                            "Add as copy",
                        )
                if override_tmp == "Yes":
                    shutil.copy(script_path, new_path)
                if override_tmp == "Add as copy":
                    new_path = new_path.replace(".py", "_COPY.py")
                    shutil.copy(script_path, new_path)
                result.append(new_path)
        return result

    pre_scripts_paths, post_scripts_paths = get_custom_scripts_from_repo(
        asset_name, pre_scripts_paths, post_scripts_paths
    )

    return _clone_process(pre_scripts_paths), _clone_process(post_scripts_paths)


def _add_asset_custom_scripts_to_guide_root(
    guide_root_nd, pre_custom_scripts, post_custom_scripts
):
    """
    Will add the cloned custom steps to guide root node.

    Args:
        guide_root_nd(pmc.PyNode): The guide root of the new imported template.
        pre_custom_scripts(list): The pre custom step.
        post_custom_scripts(list): The post custom step.

    """
    pre_custom_scripts = ",".join(
        [
            f"{os.path.basename(path).split('.')[0]} | {path}"
            for path in pre_custom_scripts
        ]
    )
    post_custom_scripts = ",".join(
        [
            f"{os.path.basename(path).split('.')[0]} | {path}"
            for path in post_custom_scripts
        ]
    )
    guide_root_nd.preCustomStep.set(pre_custom_scripts, type="string") # noqa
    guide_root_nd.postCustomStep.set(post_custom_scripts, type="string") # noqa


@DECORATORS.dg_evaluation()
@DECORATORS.refresh_suspended()
def import_guide_template_with_custom_steps_from_repo(
    asset_name,
    file_type="sgt",
    override_custom_steps="Yes",
    override_confirm_box=True,
):
    """
    Import the guide template from the repo and add the corresponding post script to it.
    All post scripts will be cloned to the asset scripts directory before we add them to the guide root node.

    Args:
        asset_name(str): The asset you want to import.
        file_type(str): The file type you want to use.
                        Valid values are ["mb", "sgt"]
                        Default is "sgt".
        override_custom_steps(str): With this flag you can override already existing scripts or a add them as copy.
                       Valid values ["Yes", "No", "Add as copy"]
                       Default value is "Yes"
        override_confirm_box(bool): Enable/Disable the clone custom step confirm box if custom step already exist.

    """
    guide_root_nd = import_guide_template_from_repo(asset_name, file_type)

    pre_custom_steps, post_custom_steps = clone_custom_scripts_to_asset_dir(
        asset_name, override_custom_steps, override_confirm_box
    )
    _add_asset_custom_scripts_to_guide_root(
        guide_root_nd, pre_custom_steps, post_custom_steps
    )
    return guide_root_nd


class GuideAdapter:
    #this new class is a prototype, need a lot of refiment is here to not loose the prototype
    def __init__(self, plane_size=1.0):
        self.plane_size = plane_size
        self.start_mesh = None
        self.end_mesh = None
        self.reposition_nodes = None
        self.bs_attr = None
        self.data = []
        self.planes = []

    def repositioning(self):
        self.create_planes()
        self.create_wrap()

    def create_planes(self):
        if not self.reposition_nodes:
            pmc.warning("Repositioning nodes are not prepared. Run prepare() first.")
            return

        self.data = []

        for node in self.reposition_nodes:
            try:
                plane = pmc.polyPlane(w=self.plane_size, h=self.plane_size, sx=1, sy=1, name=f"{node}_plane")[0]
                self.planes.append(plane)
                node_position = pmc.xform(node, query=True, translation=True, worldSpace=True)

                locator = pmc.spaceLocator(name=f"{node}_locator")
                pmc.xform(locator, translation=node_position, worldSpace=True)

                pmc.xform(plane, translation=node_position, worldSpace=True)
                rig_utils.create_uv_pin_setup(plane, [locator], True)

                self.data.append({"locator": locator, "plane": plane, "object": node})
                pmc.parentConstraint(locator, node, mo=True)
            except:
                pmc.warning(node)

        return self.data

    def create_wrap(self):
        pmc.select(clear=True)
        pmc.select(self.planes)
        pmc.select(self.start_mesh, add=True)
        pmc.runtime.CreateWrap()

        pmc.warning("Wrap deformer created using planes and start mesh.")


#       usage example
#     adapter = GuideAdapter(plane_size=1.0)
#     adapter.reposition_nodes = pmc.ls(sl=True)
#     adapter.start_mesh = pmc.PyNode("body_C_001_render_geo")
#     adapter.bs_attr = "blendShape1.body_C_001_render_geo1"
#     adapter.repositioning()

class TransferGuides(object):
    """
    Tool for transferring guides from a position relative to source_mesh to a position relative to target_mesh.
    """

    def __init__(self):

        self.source_guides = None
        self.target_guides = None

        self.source_mesh = None
        self.target_mesh = None

        self.pinned_xforms = {}

        self._alignment_fix = True
        self._delta_mush_fix = False
        self._delta_mush_iterations = 1000

    def _pin(self, xform):

        pin_inst = rig_utils.PinXform(xform)
        pin_inst.pin()

        self.pinned_xforms[xform] = pin_inst

    def _unpin(self, xform):
        pin_inst = self.pinned_xforms.get(xform)
        if pin_inst:
            pin_inst.unpin()
            self.pinned_xforms.pop(xform)

    def xform_transfer(self, source_mesh, target_mesh, transforms):

        transfer = rig_utils.XformTransfer()

        transfer.set_source_mesh(source_mesh)
        transfer.set_target_mesh(target_mesh)
        transfer.set_scope(transforms)
        transfer.set_use_delta_mush(self._delta_mush_fix, self._delta_mush_iterations)
        transfer.run()

    def _align_transforms(self, source_relatives, target_relatives):
        for target_transform in target_relatives:
            target_base = rig_utils.get_basename(target_transform)

            for source_transform in source_relatives:
                if source_transform.endswith(target_base):
                    position = cmds.xform(source_transform, q=True, ws=True, t=True)
                    cmds.xform(target_transform, ws=True, t=position)

    def _align_x_to_zero(self, source_relatives, target_relatives):
        """
        align X translate axis to zero on matching transforms in target_relatives.
        Needed for some guides sitting on the center line.
        transferred source is used for position of Y and Z

        Args:
            source_relatives (list): List of all relatives of the source guide group:
            target_relatives (list): List of all relatives of the target guide group:
        """
        pos_skip = ['global_C0', 'local_C0']
        align_x_at_zero = ['spine', 'neck', 'hip', 'body']

        for target_transform in target_relatives:
            target_base = rig_utils.get_basename(target_transform)

            do_pos = True

            for skip in pos_skip:
                if target_base.find(skip) > -1:
                    do_pos = False
                    break

            if not do_pos:
                continue

            align_x_zero = False
            for align in align_x_at_zero:
                if target_base.find(align) > -1:
                    align_x_zero = True
                    break

            for source_transform in source_relatives:
                if source_transform.endswith(target_base):

                    if not cmds.objExists(source_transform):
                        continue
                    position = cmds.xform(source_transform, q=True, ws=True, t=True)
                    if align_x_zero:
                        position[0] = 0
                    cmds.xform(target_transform, ws=True, t=position)

    def _aim(self, target_transform):
        """
        Args:
            target_transform (str): target transform corresponding to source transform:
        """
        target_base = rig_utils.get_basename(target_transform)

        loc = None

        children = cmds.listRelatives(target_transform, f=True, type='transform')

        if children:

            self._pin(target_transform)

            constraint = None
            loc = cmds.spaceLocator()[0]
            cmds.matchTransform(loc, children[0], rot=True, position=True, pivots=False)
            parent = cmds.listRelatives(target_transform, p=True, f=True)

            if target_base.startswith('foot') and target_base.endswith('root'):
                child_loc = loc
                custom_loc = cmds.spaceLocator()[0]
                loc = [child_loc, custom_loc]
                pos = cmds.xform(target_transform, q=True, ws=True, t=True)
                pos[1] += 1
                cmds.xform(custom_loc, ws=True, t=pos)

                constraint = cmds.aimConstraint(custom_loc, target_transform, wuo=child_loc,
                                                wut='object', wu=[0, 1, 0], aim=[0, 1, 0],
                                                u=[1, 0, 0])

            elif parent:
                constraint = cmds.aimConstraint(loc, target_transform, wuo=parent[0],
                                                wut='objectrotation', wu=[0, 1, 0])
            else:
                constraint = cmds.aimConstraint(loc, target_transform)

            self._unpin(target_transform)

            if constraint:
                cmds.delete(constraint)
            if loc:
                cmds.delete(loc)

        else:
            if target_base.endswith('_2_loc'):
                cmds.setAttr('%s.rotateX' % target_transform, 0)
                cmds.setAttr('%s.rotateY' % target_transform, 0)
                cmds.setAttr('%s.rotateZ' % target_transform, 0)

    def _align_aim(self, source_relatives, target_relatives):
        """
        Needed for guides like the finger. Aims each guide in the list at its first child unless filtered out.

        Args:
            source_relatives (list): List of all relatives of the source guide group:
            target_relatives (list): List of all relatives of the target guide group:
        """

        aim_skip = ['spine',
                    'neck',
                    'mouth',
                    'shoulder',
                    'hip',
                    'global_C0',
                    'local_C0',
                    'body_C0',
                    'Host',
                    'visibility_C0',
                    'eye_L0_root',
                    'eye_R0_root',
                    'leg_L0_root',
                    'leg_R0_root']

        for target_transform in target_relatives:
            target_base = rig_utils.get_basename(target_transform)

            do_aim = True
            for skip in aim_skip:
                if target_base.find(skip) > -1:
                    do_aim = False
                    break

            if not do_aim:
                continue

            self._aim(target_transform)

    def _align_orient(self, target_relatives):
        """
        Aligns orient on some needed guides

        Args:
            target_relatives (list): List of all relatives of the target guide group
        """
        for target_transform in target_relatives:
            target_base = rig_utils.get_basename(target_transform)

            if target_base.endswith('eff'):

                parent = cmds.listRelatives(target_transform, p=True, f=True)
                if parent:

                    self._pin(target_transform)
                    cmds.matchTransform(target_transform, parent[0], rot=True, position=False, pivots=False)
                    self._unpin(target_transform)

                if target_base.startswith('leg'):
                    cmds.setAttr(f'{target_transform}.translateX', 0)
                    cmds.setAttr(f'{target_transform}.translateY', 0)

            if target_base.endswith('_loc'):
                children = cmds.listRelatives(target_transform, type = 'transform')

                if not children:
                    cmds.setAttr(f'{target_transform}.rotateX', 0)
                    cmds.setAttr(f'{target_transform}.rotateY', 0)
                    cmds.setAttr(f'{target_transform}.rotateZ', 0)

    def _fix_eyes(self, target_relatives):
        """
        Fixes the eye look not aligned to the root (eye socket)
        """
        for target in target_relatives:
            target_base = rig_utils.get_basename(target)

            if target_base.startswith('eye') and target_base.endswith('look'):
                parent = cmds.listRelatives(target, p=True, f=True)[0]
                if parent:
                    parent_position = cmds.xform(parent, q=True, ws=True, t=True)
                    position = cmds.xform(target, q=True, ws=True, t=True)
                    aligned_position = (parent_position[0], parent_position[1], position[2])
                    cmds.xform(target, ws=True, t=aligned_position)

    def _fix_lookat(self, target_relatives):
        """
        Fixes the eye lookat not sitting between eye looks.
        """
        for target in target_relatives:
            target_base = rig_utils.get_basename(target)

            if target_base.startswith('lookAt') and target_base.endswith('root'):
                parent = cmds.listRelatives(target, p=True, f=True)[0]
                children = cmds.listRelatives(parent, f = True, type = 'transform')

                eye_looks = []

                for child in children:
                    child_base = rig_utils.get_basename(child)

                    if child_base.startswith('eye') and child_base.endswith('root'):
                        sub_children = cmds.listRelatives(child, type = 'transform', f = True)

                        for sub_child in sub_children:
                            sub_child_base = rig_utils.get_basename(sub_child)

                            if sub_child_base.startswith('eye') and sub_child_base.endswith('look'):
                                eye_looks.append(pmc.PyNode(sub_child))

                if len(eye_looks) > 1:

                    midpoint = rig_utils.get_avg_object_center(eye_looks)
                    cmds.xform(target, ws = True, t = midpoint)

    def _fix_wrists(self, target_relatives):
        """
        Fix for the wrists sometimes not being aligned to the elbow after transfer.
        """

        for target in target_relatives:
            target_base = rig_utils.get_basename(target)

            if target_base.startswith('arm') and target_base.endswith('eff'):
                parent = cmds.listRelatives(target, p=True, f=True)
                grand_parent = cmds.listRelatives(parent, p=True, f=True)

                if parent and grand_parent:
                    parent = parent[0]
                    grand_parent = grand_parent[0]

                    wrist_position = cmds.xform(target, q=True, ws=True, t=True)

                    self._pin(target)

                    cmds.matchTransform(parent, grand_parent, rot=True, position=False, pivots=False)
                    cmds.matchTransform(parent, target, rot=False, position=True, pivots=False)

                    position = cmds.xform(parent, q=True, os=True, t=True)
                    position[0] += -.4
                    cmds.xform(parent, os=True, t=position)

                    cmds.matchTransform(target, grand_parent, rot=True, position=False, pivots=False)
                    cmds.xform(target, ws=True, t=wrist_position)

                    self._unpin(target)

    def _fix_hands(self, target_relatives):
        """
        Fix for the meta and thumb orientations
        """
        for target in target_relatives:
            target_base = rig_utils.get_basename(target)

            if target_base.startswith('arm') and target_base.endswith('eff'):
                children = cmds.listRelatives(target, type='transform', f=True)

                meta = None
                thumb = None

                for child in children:
                    child_base = rig_utils.get_basename(child)

                    if child_base.startswith('meta') and child_base.endswith('root'):
                        meta = child
                        break

                if meta:
                    parent = cmds.listRelatives(meta, p=True, f=True)
                    if parent:
                        parent = parent[0]

                    meta_x_axis = (0, -1, 0)
                    meta_y_axis = (0, 0, -1)
                    meta_z_axis = (-1, 0, 0)
                    meta_matrix = rig_utils.build_matrix(meta_x_axis, meta_y_axis, meta_z_axis)

                    loc = cmds.spaceLocator(n='temp_loc')[0]
                    if parent:
                        loc = cmds.parent(loc, parent)
                    cmds.xform(loc, os=True, matrix=meta_matrix)
                    self._pin(meta)
                    cmds.matchTransform(meta, loc, rot=True, position=False, pivots=False)
                    self._unpin(meta)

                    children = cmds.listRelatives(meta, type='transform', f=True, ad=True)
                    children.reverse()

                    for child in children:
                        child_base = rig_utils.get_basename(child)

                        if child_base.startswith('thumbRoll') and child_base.endswith('root'):
                            thumb = child
                        elif child_base.startswith('meta') and not child_base.endswith('_blade') and not child_base.endswith('Constraint1'):
                            self._pin(child)
                            cmds.setAttr(f'{child}.rotateX', 0)
                            cmds.setAttr(f'{child}.rotateY', 0)
                            cmds.setAttr(f'{child}.rotateZ', 0)
                            self._unpin(child)

                    if thumb:
                        thumb_x_axis = (0, 0, 1)
                        thumb_y_axis = (1, 0, 0)
                        thumb_z_axis = (0, 1, 0)
                        thumb_matrix = rig_utils.build_matrix(thumb_x_axis, thumb_y_axis, thumb_z_axis)

                        loc = cmds.parent(loc, meta)
                        cmds.xform(loc, os=True, matrix=thumb_matrix)
                        self._pin(thumb)
                        cmds.matchTransform(thumb, loc, rot=True, position=False, pivots=False)
                        self._unpin(thumb)

                    cmds.delete(loc)

    def _fix_finger_aims(self, target_relatives):

        for target_transform in target_relatives:

            parent = cmds.listRelatives(target_transform, p=True, f=True)

            target_base = rig_utils.get_basename(target_transform)

            if target_base.startswith('thumbRoll'):
                continue

            if target_base.startswith('thumb') or target_base.startswith('finger'):

                children = cmds.listRelatives(target_transform, type='transform', f=True)
                if not children:
                    continue

                constraint = None

                self._pin(target_transform)
                loc = cmds.spaceLocator()
                cmds.matchTransform(loc, children[0], rot=True, position=True, pivots=False)

                if target_base.startswith('thumb') and target_base.endswith('root'):
                    constraint = cmds.aimConstraint(loc, target_transform, wu=[0, 1, 0],
                                                    u=[0, -1, 0], wuo=parent[0], wut='objectrotation')
                elif target_base.startswith('thumb') and target_base.endswith('loc'):
                    constraint = cmds.aimConstraint(loc, target_transform, wu=[0, 0, 0],
                                                    u=[0, 1, 0], wuo=parent[0], wut='objectrotation')
                elif target_base.startswith('finger') and target_base.endswith('root'):
                    constraint = cmds.aimConstraint(loc, target_transform, wu=[0, 1, 0],
                                                    u=[0, 1, 0], wuo=parent[0], wut='objectrotation')
                else:
                    constraint = cmds.aimConstraint(loc, target_transform, wu=[0, 0, 0],
                                                    u=[0, 1, 0], wuo=parent[0], wut='objectrotation')

                self._unpin(target_transform)

                if constraint:
                    cmds.delete(constraint)
                if loc:
                    cmds.delete(loc)

    def _fix_feet(self, target_relatives):
        for target_transform in target_relatives:
            target_base = rig_utils.get_basename(target_transform)
            if target_base.startswith('foot') and target_base.endswith('root'):

                parent = cmds.listRelatives(target_transform, p=True, f=True)

                if parent:
                    parent = parent[0]

                    ankle_base = rig_utils.get_basename(parent)
                    side = 'L'
                    if ankle_base.find('_R0_') > -1:
                        side = 'R'

                    x_axis = (0, 0, -1)
                    y_axis = (0, 1, 0)
                    z_axis = (1, 0, 0)
                    if side == 'R':
                        x_axis = (0, 0, 1)
                        y_axis = (0, -1, 0)
                        z_axis = (1, 0, 0)

                    matrix = rig_utils.build_matrix(x_axis, y_axis, z_axis)

                    loc = cmds.spaceLocator(n='temp_loc')[0]
                    if parent:
                        loc = cmds.parent(loc, target_transform)
                    cmds.xform(loc, os=True, matrix=matrix)
                    cmds.parent(loc, w=True)

                    self._pin(parent)
                    cmds.matchTransform(parent, loc, rot=True, position=False, pivots=False)
                    self._unpin(parent)
                    cmds.delete(loc)

                relatives = cmds.listRelatives(target_transform, ad=True, type='transform', f=True)
                if not relatives:
                    continue
                for rel in relatives:
                    if rel.endswith('_crv'):
                        continue

                    cmds.matchTransform(rel, target_transform, rot=True, position=False, pivots=False)

                    if rel.endswith('_loc') or rel.endswith('_heel'):
                        cmds.setAttr('%s.translateZ' % rel, 0)

    def set_source(self, source_guide, source_mesh):
        """
        Used to set the source guide group and the source mesh
        Guides in the source guide group should be positioned relative to source mesh.

        The position of the source guide relative to the source mesh
        will be used to position target guides relative to target mesh.

        Args:
            source_guide (str): source guide group name
            source_mesh (str): source mesh name
        """
        self.source_guide = str(source_guide)
        self.source_mesh = str(source_mesh)

    def set_target(self, target_guide, target_mesh):
        """
        Used to set the target guide group and the target mesh.
        Guides under the target guide group will be transformed to match the target mesh based on the source.
        Often this target guide group is freshly generated from the guide template manager.

        Args:
            target_guide (str): target guide group name
            target_mesh (str): target mesh name
        """
        self.target_guide = str(target_guide)
        self.target_mesh = str(target_mesh)

    def set_alignment_fix(self, bool_value):
        self._alignment_fix = bool_value

    def set_delta_mush_fix(self, bool_value, iterations = 1000):
        self._delta_mush_fix = bool_value
        self._delta_mush_iterations = iterations

    @DECORATORS.undo
    def transfer(self):
        """
        Perform the transfer by transforming the target guides
        """
        if not all([self.source_guide,
                    self.source_mesh,
                    self.target_guide,
                    self.target_mesh]):
            return

        source_duplicate = cmds.duplicate(self.source_guide)[0]

        source_relatives = cmds.listRelatives(source_duplicate, ad=True, f=True, type='transform')
        target_relatives = cmds.listRelatives(self.target_guide, ad=True, f=True, type='transform')

        end_strings = ('controlBuffer', '_blade','sizeRef','Constraint1','crv')
        source_relatives = [item for item in source_relatives if not item.endswith(end_strings)]
        target_relatives = [item for item in target_relatives if not item.endswith(end_strings)]

        source_relatives.reverse()
        target_relatives.reverse()

        self.xform_transfer(self.source_mesh, self.target_mesh, source_relatives)

        if self._alignment_fix:
            self._align_x_to_zero(source_relatives, target_relatives)
            self._align_aim(source_relatives, target_relatives)
            self._fix_eyes(target_relatives)
            self._fix_lookat(target_relatives)
            self._fix_wrists(target_relatives)
            self._fix_hands(target_relatives)
            self._fix_feet(target_relatives)
            self._fix_finger_aims(target_relatives)
            self._align_orient(target_relatives)
        else:
            self._align_transforms(source_relatives, target_relatives)

        cmds.delete(source_duplicate)


@DECORATORS.x_timer
def last_guide_standing():
    """
    Will kill all assemblie nodes and objects sets in the scene.
    But the rig guide nodes will survive.
    """
    temp_list = []
    guide_root_nodes = get_scene_guides()
    if len(guide_root_nodes) > 1:
        raise exceptions.MayaNodeNameUniqueness("Guide node is not unique.")
    pmc.parent(guide_root_nodes, None)
    scene_assemblies = [
        node for node in pmc.ls(assemblies=True) if node not in guide_root_nodes
    ]
    object_set = pmc.ls(type="objectSet")
    temp_list.extend(scene_assemblies)
    temp_list.extend(object_set)
    scene_utils.import_references()
    pmc.delete(temp_list)


@DECORATORS.x_timer
def _get_guides_publish_path():
    """
    Get the guides publish path if path not exist will create one.

    Returns:
        String: The path.

    """
    root_path = paths_utils.get_root_path(pmc.sceneName(), "asset_task")
    publish_path = pixo_paths.normalize(
        os.path.join(root_path, GUIDES_PUBLISH_DIR_NAME)
    )
    if not os.path.exists(publish_path):
        os.mkdir(publish_path)
    return publish_path


@DECORATORS.x_timer
def generate_guides_publish_name(
    pub_file_name_pattern=("ASSET_NAME", "VERSION", "USER"),
    asset_name_token_index=0,
    version_name_token_index=1,
    user_name_token_index=2,
    guides_suffix="RIGGUIDES",
):
    """
    Generates the publishing guides file name.
    This requieres a file taking place in the PXO environment.
    This means the file needs to be saved with the PXO save/load.

    Args:
        pub_file_name_pattern(tuple): Defines the name pattern.
                                     If the name pattern will be modified the token indexes
                                     needs to be adjusted as well.
                                     Default is ["ASSET_NAME", "VERSION", "USER"].
        asset_name_token_index(int): The index of the asset pattern in the pub_file_name_pattern arg.
                                     Default is 0 == "ASSET_NAME".
        version_name_token_index(int): The index of the version pattern in the pub_file_name_pattern arg.
                                  Default is 1 == "VERSION".
        user_name_token_index(int): The index of the user pattern in the pub_file_name_pattern arg.
                               Default is 1 == "USER".
        guides_suffix(str): The rig guide suffix name.
                            Default is "RIGGUIDES".

    Returns:
        String: The new name.

    """
    pub_file_name_pattern_tmp = list(pub_file_name_pattern)

    pub_file_name_pattern_tmp.append(guides_suffix)
    current_version = paths_utils.get_version_number_from_basename(
        pmc.sceneName()
    )
    current_user_abr = paths_utils.get_user_abbr(pmc.sceneName())
    asset_name = paths_utils.get_asset_infos(pmc.sceneName(), "asset_name")
    file_name_pattern = "_".join(pub_file_name_pattern_tmp)
    file_name = file_name_pattern.replace(
        pub_file_name_pattern_tmp[asset_name_token_index], str(asset_name)
    )
    file_name = file_name.replace(
        pub_file_name_pattern_tmp[version_name_token_index],
        "v{}".format(str(current_version).zfill(3)),
    )
    file_name = file_name.replace(
        pub_file_name_pattern_tmp[user_name_token_index], str(current_user_abr)
    )
    return file_name


@DECORATORS.x_timer
def rename_guide_root_nd(guides_name):
    """
    Rename the guides root node of the scene to given name.

    Args:
        guides_name(str): The new name.

    """
    guide_root_nodes = get_scene_guides()
    if guide_root_nodes:
        for node in guide_root_nodes:
            node.rename(guides_name)


@DECORATORS.dg_evaluation()
@DECORATORS.refresh_suspended()
def import_guide_template_with_custom_steps_from_repo(
    asset_name,
    file_type="sgt",
    override_custom_steps="Yes",
    override_confirm_box=True,
):
    """
    Import the guide template from the repo and add the corresponding post script to it.
    All post scripts will be cloned to the asset scripts directory before we add them to the guide root node.

    Args:
        asset_name(str): The asset you want to import.
        file_type(str): The file type you want to use.
                        Valid values are ["mb", "sgt"]
                        Default is "sgt".
        override_custom_steps(str): With this flag you can override already existing scripts or a add them as copy.
                       Valid values ["Yes", "No", "Add as copy"]
                       Default value is "Yes"
        override_confirm_box(bool): Enable/Disable the clone custom step confirm box if custom step already exist.

    """
    guide_root_nd = import_guide_template_from_repo(asset_name, file_type)
    pre_custom_steps, post_custom_steps = clone_custom_scripts_to_asset_dir(
        asset_name, override_custom_steps, override_confirm_box
    )
    _add_asset_custom_scripts_to_guide_root(
        guide_root_nd, pre_custom_steps, post_custom_steps
    )
    return guide_root_nd


def get_generic(asset_name=None):
    asset_root_path = os.environ['PXO_ASSETS_ROOT']

    pattern = '*.ma'

    path = None
    if asset_name:
        path = os.path.join(asset_root_path, 'characters', asset_name, 'rig')

    if not path:
        path = os.path.join(asset_root_path, 'characters', 'chr_genericMale', 'rig')
    if not os.path.exists(path):
        path = os.path.join(asset_root_path, 'characters', 'chr_genMan', 'rig')

    import glob

    def _get_latest_file(directory, pattern="*"):
        # Get all files matching the pattern
        files = glob.glob(os.path.join(directory, pattern))
        if not files:
            return None  # No files found
        # Return the file with the latest modification time
        latest_file = max(files, key=os.path.getmtime)
        return latest_file
    latest = _get_latest_file(path, pattern)

    return latest


def transfer_generic(source_path,
                     target_mesh=None,
                     target_guide=None,
                     alignment_fix=True,
                     delta_mush_fix=True,
                     delta_mush_iterations=1000
                     ):

    asset_name = os.environ.get('PXO_ASSET', None)

    if not asset_name:
        _LOGGER.warning('No asset set', extra=ui_interesting)
        return

    asset_code = asset_name[4:7]
    source_geo = 'body_C_001_render_geo'

    if target_mesh:
        split_name = target_mesh.split(':')
        split_name = split_name[-1].split('|')
        source_geo = split_name[-1]
    if not target_mesh:
        target_mesh = f'{asset_code}_02:{source_geo}'

    if target_guide and not cmds.objExists(target_guide):
        _LOGGER.warning(f'No target guide group found: {target_guide}', extra=ui_interesting)
        return

    if cmds.objExists(target_mesh):
        _LOGGER.info(f'Target mesh found: {target_mesh}', extra=ui_interesting)
    else:
        _LOGGER.warning(f'No target mesh found: {target_mesh}', extra=ui_interesting)
        return

    guide_group = f'{asset_name}_v001_lv_RIGGUIDES'

    if not target_guide:
        if cmds.objExists(guide_group):
            _LOGGER.warning('Guides found in scene. Please specify the guide group in the UI or remove existing guides.', extra=ui_interesting)
            return
        else:
            _LOGGER.info('Guides not supplied. Loading from Guide Templates', extra=ui_interesting)
            target_guide = import_guide_template_from_repo('Biped')
            cmds.refresh()

    if source_path and os.path.exists(source_path):
        generic_path = source_path
    else:
        generic_path = get_generic()

    _LOGGER.info('Referencing generic: %s' % generic_path, extra=ui_interesting)

    cmds.file(generic_path, reference=True, namespace='transfer_temp')
    cmds.refresh()

    guides = cmds.ls('transfer_temp:*RIGGUIDES', type='transform')

    if guides:
        guides_name = guides[0].replace('transfer_temp:', '')
        _LOGGER.info(f'Working with source guides: {guides_name}', extra=ui_interesting)
    else:
        _LOGGER.warning('No source guides found. Please check that workfile has guides.', extra=ui_interesting)
        cmds.file(generic_path, removeReference=True)
        return

    source_guide = guides[0]
    source_mesh = f'transfer_temp:gen_02:{source_geo}'
    source_mesh_nicename = source_mesh.replace('transfer_temp:', '')

    if not source_mesh or not cmds.objExists(source_mesh):
        source_mesh = cmds.ls(f'transfer_temp:*:{source_geo}')
        if source_mesh:
            source_mesh = source_mesh[0]
        else:
            source_mesh = None

    if source_mesh:
        _LOGGER.info(f'Working with source mesh: {source_mesh_nicename}', extra=ui_interesting)
    else:
        _LOGGER.warning(f'Source mesh not found: {source_mesh_nicename}', extra=ui_interesting)
        #cmds.file(generic_path, removeReference=True)
        return

    result = mesh_utils.check_mesh_data(source_mesh, target_mesh)
    dup_source = None
    if not result['vertex_count']:
        _LOGGER.warning('Published generic mesh does not match target mesh. ', extra=ui_interesting)
        _LOGGER.warning('Trying a uv point transfer, but might not work.', extra=ui_interesting)

        dup_source = cmds.duplicate(target_mesh)[0]

        cmds.transferAttributes(
            source_mesh,
            dup_source,
            transferPositions=1,
            transferNormals=0,
            transferColors=0,
            transferUVs=0,
            sampleSpace=3,
            searchMethod=3,
            flipUVs=False,
            colorBorders=False
        )
        cmds.delete(dup_source, ch=True)

        source_mesh = dup_source

    transfer_inst = TransferGuides()
    transfer_inst.set_source(source_guide, source_mesh)
    transfer_inst.set_target(target_guide, target_mesh)
    transfer_inst.set_delta_mush_fix(delta_mush_fix, delta_mush_iterations)
    transfer_inst.set_alignment_fix(alignment_fix)
    transfer_inst.transfer()

    cmds.file(generic_path, removeReference=True)
    if dup_source:
        cmds.delete(dup_source)


def is_mgear_root(transform):

    if not cmds.objExists(f'{transform}.isGearGuide'):
        return False

    test_attributes = ['comp_type', 'comp_name', 'comp_side', 'comp_index']

    if not transform.endswith('_root'):
        return False

    for attribute in test_attributes:
        if not cmds.objExists(f'{transform}.{attribute}'):
            return False

    return True


def find_mgear_root(transform):
    test = transform
    parent = cmds.listRelatives(test, p=True, f=True)

    inc = 0
    while not is_mgear_root(test) and parent:
        test = parent[0]
        parent = cmds.listRelatives(parent, p=True, f=True)

        if inc > 1000:
            break
        inc += 1

    if is_mgear_root(test):
        return test


def find_mgear_roots_from_selection():
    selection = cmds.ls(sl=True, l=True)

    if not selection:
        return

    found = []
    visited = set()
    for thing in selection:
        if thing in visited:
            continue
        root = find_mgear_root(thing)
        if root and root not in visited:
            found.append(root)
            visited.add(root)

    return found


def find_components(comp_type):

    transforms = cmds.ls(type = 'transform', l = True)
    found = []
    for transform in transforms:
        comp_type_attr = f'{transform}.comp_type'
        if not cmds.objExists(f'{transform}.isGearGuide'):
            continue
        if not cmds.objExists(comp_type_attr):
            continue
        sub_comp_type = cmds.getAttr(comp_type_attr)

        if sub_comp_type == comp_type:
            found.append(transform)

    return found


def get_guide_transforms():
    try:
        target_guide = get_guide_root_nd()
    except Exception:
        return []

    target_guide = target_guide.name()

    target_relatives = cmds.listRelatives(target_guide, ad=True, f=True, type='transform')
    end_strings = ('controlBuffer', '_blade', 'sizeRef', 'Constraint1', 'crv')
    target_relatives = [item for item in target_relatives if not item.endswith(end_strings)]
    target_relatives.reverse()

    return target_relatives


def get_guide_part(suffix, parts):

    for key in parts:
        if key.endswith(suffix):
            return parts[key].name()


def aim_guide(guide_transform):
    """
    Args:
        guide_transform (str): target transform corresponding to source transform:
    """
    target_base = rig_utils.get_basename(guide_transform)

    children = cmds.listRelatives(guide_transform, f=True, type='transform')

    if children:

        pin_inst = rig_utils.PinXform(guide_transform)
        pin_inst.pin()

        constraint = None
        loc = cmds.spaceLocator()[0]
        cmds.matchTransform(loc, children[0], rot=True, position=True, pivots=False)
        parent = cmds.listRelatives(guide_transform, p=True, f=True)

        if parent:
            constraint = cmds.aimConstraint(loc, guide_transform, wuo=parent[0],
                                            wut='objectrotation', wu=[0, 1, 0])
        else:
            constraint = cmds.aimConstraint(loc, guide_transform)

        pin_inst.unpin()

        if constraint:
            cmds.delete(constraint)
        if loc:
            cmds.delete(loc)

    else:
        if target_base.endswith('_2_loc'):
            cmds.setAttr('%s.rotateX' % guide_transform, 0)
            cmds.setAttr('%s.rotateY' % guide_transform, 0)
            cmds.setAttr('%s.rotateZ' % guide_transform, 0)

def align_body(guide_transforms=None):

    if not guide_transforms:
        guide_transforms = get_guide_transforms()
    if not guide_transforms:
        _LOGGER.warning('Found no guides to align', extra=ui_interesting)
        return

    for target_transform in guide_transforms:
        align_center(target_transform)
        align_aim(target_transform)

    roots = [t for t in guide_transforms if t.endswith('_root')]
    if not roots:
        _LOGGER.warning('Found no guide roots.', extra=ui_interesting)
    align_components(roots)

    for target_transform in guide_transforms:
        align_hands(target_transform)
        align_look_at(target_transform)

    for target_transform in guide_transforms:
        target_base = rig_utils.get_basename(target_transform)
        if target_base.endswith('eff'):

            parent = cmds.listRelatives(target_transform, p=True, f=True)
            if parent:
                pin_inst = rig_utils.PinXform(target_transform)
                pin_inst.pin()
                cmds.matchTransform(target_transform, parent[0], rot=True, position=False, pivots=False)
                pin_inst.unpin()

        if target_base.endswith('_loc'):
            children = cmds.listRelatives(target_transform, type='transform', f=True)

            if not children:
                cmds.setAttr(f'{target_transform}.rotateX', 0)
                cmds.setAttr(f'{target_transform}.rotateY', 0)
                cmds.setAttr(f'{target_transform}.rotateZ', 0)


def align_hands(target_transform):

    target_base = rig_utils.get_basename(target_transform)

    if target_base.startswith('arm') and target_base.endswith('eff'):
        children = cmds.listRelatives(target_transform, type='transform', f=True)

        meta = None
        thumb = None

        for child in children:
            child_base = rig_utils.get_basename(child)

            if child_base.startswith('meta') and child_base.endswith('root'):
                meta = child
                break

        if meta:
            parent = cmds.listRelatives(meta, p=True, f=True)
            if parent:
                parent = parent[0]

            meta_x_axis = (0, 0, -1)
            meta_y_axis = (0, 1, 0)
            meta_z_axis = (-1, 0, 0)
            meta_matrix = rig_utils.build_matrix(meta_x_axis, meta_y_axis, meta_z_axis)

            loc = cmds.spaceLocator(n='temp_loc')[0]
            if parent:
                loc = cmds.parent(loc, parent)
            cmds.xform(loc, os=True, matrix=meta_matrix)
            pin_inst = rig_utils.PinXform(meta)
            pin_inst.pin()
            cmds.matchTransform(meta, loc, rot=True, position=False, pivots=False)
            pin_inst.unpin()

            children = cmds.listRelatives(meta, type='transform', f=True, ad=True)
            children.reverse()

            for child in children:
                child_base = rig_utils.get_basename(child)

                if child_base.startswith('thumbRoll') and child_base.endswith('root'):
                    thumb = child
                elif child_base.startswith('meta') and not child_base.endswith(
                        '_blade') and not child_base.endswith('Constraint1'):
                    pin_inst = rig_utils.PinXform(child)
                    pin_inst.pin()
                    cmds.setAttr(f'{child}.rotateX', 0)
                    cmds.setAttr(f'{child}.rotateY', 0)
                    cmds.setAttr(f'{child}.rotateZ', 0)
                    pin_inst.unpin()

            if thumb:
                thumb_x_axis = (0, 0, 1)
                thumb_y_axis = (1, 0, 0)
                thumb_z_axis = (0, 1, 0)
                thumb_matrix = rig_utils.build_matrix(thumb_x_axis, thumb_y_axis, thumb_z_axis)

                loc = cmds.parent(loc, meta)
                cmds.xform(loc, os=True, matrix=thumb_matrix)
                pin_inst = rig_utils.PinXform(thumb)
                pin_inst.pin()
                cmds.matchTransform(thumb, loc, rot=True, position=False, pivots=False)
                pin_inst.unpin()

            cmds.delete(loc)


def align_look_at(target_transform):

    target_base = rig_utils.get_basename(target_transform)

    if target_base.startswith('lookAt') and target_base.endswith('root'):
        parent = cmds.listRelatives(target_transform, p=True, f=True)[0]
        children = cmds.listRelatives(parent, f=True, type='transform')

        eye_looks = []

        for child in children:
            child_base = rig_utils.get_basename(child)

            if child_base.startswith('eye') and child_base.endswith('root'):
                sub_children = cmds.listRelatives(child, type='transform', f=True)

                for sub_child in sub_children:
                    sub_child_base = rig_utils.get_basename(sub_child)

                    if sub_child_base.startswith('eye') and sub_child_base.endswith('look'):
                        eye_looks.append(pmc.PyNode(sub_child))

        if len(eye_looks) > 1:
            midpoint = rig_utils.get_avg_object_center(eye_looks)
            cmds.xform(target_transform, ws=True, t=midpoint)


def align_center(target_transform, axis = 'X'):
    """
    align X translate axis to zero on matching transforms in target_relatives.
    Needed for some guides sitting on the center line.
    transferred source is used for position of Y and Z

    Args:
        target_transform (str): target transform to align axis to
    """
    pos_skip = ['global_C0', 'local_C0']
    align_to_center = ['spine', 'neck', 'hip', 'body', 'mouth']
    align_axis = [0, 1, 1]
    if axis == 'Y':
        align_axis = [1, 0, 1]
    if axis == 'Z':
        align_axis = [1, 1, 0]

    target_base = rig_utils.get_basename(target_transform)

    do_pos = True

    for skip in pos_skip:
        if target_base.find(skip) > -1:
            do_pos = False
            break

    if not do_pos:
        return

    align_center = False
    for align in align_to_center:
        if target_base.find(align) > -1:
            align_center = True
            break

    if align_center:
        pin_inst = rig_utils.PinXform(target_transform)
        pin_inst.pin()
        position = cmds.xform(target_transform, q=True, ws=True, t=True)
        position[0] *= align_axis[0]
        position[1] *= align_axis[1]
        position[2] *= align_axis[2]
        cmds.xform(target_transform, ws=True, t=position)
        pin_inst.unpin()


def align_aim(target_transform):
    """
    Needed for guides like the finger. Aims each guide in the list at its first child unless filtered out.

    Args:
        target_transform (str): The guide transform to aim
    """

    aim_skip = ['spine',
                'neck',
                'mouth',
                'shoulder',
                'hip',
                'global_C0',
                'local_C0',
                'body_C0',
                'Host',
                'visibility_C0',
                'eye_L0_root',
                'eye_R0_root',
                'leg_L0_root',
                'leg_R0_root']

    target_base = rig_utils.get_basename(target_transform)

    do_aim = True
    for skip in aim_skip:
        if target_base.find(skip) > -1:
            do_aim = False
            break

    if not do_aim:
        return

    aim_guide(target_transform)


@DECORATORS.log_run_end
def align_components(roots=None):
    if not roots:
        roots = cmds.ls('*_root', type = 'transform')
    skip_components = ['ui_slider_01']

    if not roots:
        _LOGGER.warning('Found no components to align.', extra=ui_interesting)
        return

    for root in roots:

        component_type = cmds.getAttr(f'{root}.comp_type')
        if component_type in skip_components:
            continue

        root = pmc.PyNode(root)

        function_name = f'align_{component_type}'
        function_command = f'{function_name}(root)'

        if hasattr(sys.modules[__name__], function_name):
            exec(function_command)


def get_guide_parts(root):
    rig_inst = guide.Rig()
    rig_inst.setFromHierarchy(root)
    guide_inst = next(iter(rig_inst.components.values()))

    parts = guide_inst.getObjects(root, False)
    return parts


def get_sclera_center(scelera_mesh):
    verts = 'vtx[121:136]'
    mesh_verts = f'{scelera_mesh}.{verts}'
    center = mesh_utils.get_vertices_center(mesh_verts)
    return center


def fix_eye_pivot(eye_root):
    """
    Tries to place the eye guide at the center of the eye.
    """
    eyes = cmds.ls('*sclera_?*_geo', type='transform', l=True)
    eyes_namespace = cmds.ls('*:*sclera_?*_geo', type='transform', l=True)
    eyes += eyes_namespace

    eye_root_base = rig_utils.get_basename(eye_root)
    if eye_root_base.startswith('eye_') and eye_root_base.endswith('_root'):

        guide_position = cmds.xform(eye_root, q=True, ws=True, t=True)
        vec_guide = dt.Vector(guide_position)
        closest_distance = None
        closest = None

        for eye in eyes:
            eye_vector = get_sclera_center(eye)
            vec_eye = dt.Vector(eye_vector)

            distance = vec_guide.distanceTo(vec_eye)

            if closest_distance is None:
                closest_distance = distance
                closest = eye_vector
            else:
                if distance < closest_distance:
                    closest_distance = distance
                    closest = eye_vector

        if closest:
            cmds.xform(eye_root, ws=True, t=closest)


def align_arm_2jnt_01(guide_root):
    root = pmc.PyNode(guide_root)
    parts = get_guide_parts(root)
    root = root.name()

    elbow = get_guide_part('elbow', parts)
    wrist = get_guide_part('wrist', parts)
    effector = get_guide_part('eff', parts)

    elbow_loc = cmds.spaceLocator(n='elbow_temp_loc')[0]
    cmds.matchTransform(elbow_loc, elbow, rot = True, position=True)

    wrist_loc = cmds.spaceLocator(n='wrist_temp_loc')[0]
    cmds.matchTransform(wrist_loc, wrist, rot=True, position=True)

    pin_inst = rig_utils.PinXform(root)
    pin_inst.pin()
    constraint = cmds.aimConstraint(elbow_loc, root, wuo=wrist_loc, wut='object',
                                    wu=[0, 1, 0], aim=[1, 0, 0],
                                    u=[0, 0, 1])
    cmds.delete(elbow_loc)
    pin_inst.unpin()

    pin_inst = rig_utils.PinXform(elbow)
    pin_inst.pin()
    constraint = cmds.aimConstraint(wrist_loc, elbow,
                                    wu=[0, 1, 0], wuo=root, wut='objectrotation', aim=[1, 0, 0],
                                    u=[0, 1, 0])
    cmds.delete(wrist_loc)
    pin_inst.unpin()

    pin_inst = rig_utils.PinXform(wrist)
    pin_inst.pin()

    cmds.matchTransform(wrist, elbow, rot=True, position=False, pivots=False)

    pin_inst.unpin()

    pin_inst = rig_utils.PinXform(effector)
    pin_inst.pin()

    cmds.matchTransform(effector, wrist, rot=True, position=True, pivots=False)

    position = cmds.xform(effector, q=True, os=True, t=True)
    position[0] += .2
    cmds.xform(effector, os=True, t=position)

    pin_inst.unpin()


def align_chain_01(guide_root):

    root = pmc.PyNode(guide_root)
    parts = get_guide_parts(root)
    root = root.name()

    comp_name = cmds.getAttr(f'{root}.comp_name')

    if comp_name == 'hip':
        align_custom_hip(guide_root)
        return

    locs = list(parts.values())
    end_loc = []

    locs = [loc.name() for loc in locs]
    locs.reverse()

    first_loc = get_guide_part('0_loc', parts)
    parent = cmds.listRelatives(root, p = True, f = True)

    pin_inst = rig_utils.PinXform(root)
    pin_inst.pin()
    cmds.setAttr(f'{root}.rotate', *[0, 0, 0])
    loc = cmds.spaceLocator()
    cmds.matchTransform(loc, first_loc, rot=True, position=True, pivots=False)
    if parent:
        constraint = cmds.aimConstraint(loc, root, wu=[0, 1, 0],
                                    u=[0, 1, 0], wuo=parent[0], wut='objectrotation')
    else:
        constraint = cmds.aimConstraint(loc, root, wu=[0, 1, 0],
                                        u=[0, 1, 0])
    cmds.delete(loc)
    pin_inst.unpin()

    for loc in locs:
        if not loc.endswith('_loc'):
            continue

        children = cmds.listRelatives(loc, type='transform', f = True)
        if not children:
            end_loc.append(loc)
            continue
        child = children[0]
        split_name = child.split('|')[-1]
        if not split_name in locs:
            end_loc.append(loc)
            continue

        if split_name.endswith('root'):
            continue

        child_loc = cmds.spaceLocator()[0]
        cmds.matchTransform(child_loc, child, rot=True, position=True)

        pin_inst = rig_utils.PinXform(loc)
        pin_inst.pin()

        cmds.aimConstraint(child_loc, loc, u=[0, 1, 0], wu=[0, 1, 0], aim=[1, 0, 0], wuo=root, wut='objectrotation')
        cmds.delete(child_loc)
        pin_inst.unpin()

    for loc in end_loc:
        pin_inst = rig_utils.PinXform(loc)
        pin_inst.pin()
        cmds.setAttr(f'{loc}.rotate', *[0, 0, 0])
        pin_inst.unpin()

def align_control_01(guide_root):

    root = pmc.PyNode(guide_root)
    root = root.name()

    comp_name = cmds.getAttr(f'{root}.comp_name')

    if comp_name == 'lookAt':
        align_custom_eye_look(guide_root)
        return

def align_custom_hip(guide_root):
    root = pmc.PyNode(guide_root)
    parts = get_guide_parts(root)
    root = root.name()

    comp_type = cmds.getAttr(f'{root}.comp_type')
    comp_name = cmds.getAttr(f'{root}.comp_name')

    if comp_name != 'hip' and comp_type != 'chain_01':
        return

    loc0 = get_guide_part('0_loc', parts)
    loc1 = get_guide_part('1_loc', parts)

    pin_inst = rig_utils.PinXform(loc0)
    pin_inst.pin()
    cmds.setAttr(f'{loc0}.rotate', *[0, 0, 0])
    cmds.setAttr(f'{loc0}.translateX', 0)
    cmds.setAttr(f'{loc0}.translateZ', 0)
    pin_inst.unpin()

    pin_inst = rig_utils.PinXform(loc1)
    pin_inst.pin()
    cmds.setAttr(f'{loc1}.rotate', *[0,0,0])
    cmds.setAttr(f'{loc1}.translateX', 0)
    cmds.setAttr(f'{loc1}.translateZ', 0)
    pin_inst.unpin()


def align_custom_eye_look(guide_root):

    root = pmc.PyNode(guide_root)
    root = root.name()

    eye_guides = find_components('eye_01')
    found = []
    for eye_guide in eye_guides:
        eye_node = pmc.PyNode(eye_guide)
        eye_parts = get_guide_parts(eye_node)
        look = get_guide_part('look', eye_parts)
        if look and cmds.objExists(look):
            found.append(look)

    if not found:
        return

    if len(eye_guides) > 1:
        midpoint = rig_utils.get_avg_object_center(found)
        cmds.xform(root, ws=True, t=midpoint)

        for eye in found:
            position = cmds.xform(eye, q=True, ws=True, t=True)
            new_position = [position[0], position[1], midpoint[2]]
            cmds.xform(eye, ws=True, t=new_position)

    cmds.select(root)


def align_leg_2jnt_01(guide_root):
    root = pmc.PyNode(guide_root)
    parts = get_guide_parts(root)
    root = root.name()

    knee = get_guide_part('knee', parts)
    ankle = get_guide_part('ankle', parts)
    effector = get_guide_part('eff', parts)

    knee_loc = cmds.spaceLocator(n='knee_temp_loc')[0]
    cmds.matchTransform(knee_loc, knee, rot = True, position=True)

    ankle_loc = cmds.spaceLocator(n='ankle_temp_loc')[0]
    cmds.matchTransform(ankle_loc, ankle, rot=True, position=True)

    pin_inst = rig_utils.PinXform(root)
    pin_inst.pin()
    cmds.aimConstraint(knee_loc, root, wuo=ankle_loc, wut='object',
                        wu=[0, 1, 0], aim=[1, 0, 0],
                        u=[0, -1, 0])

    cmds.delete(knee_loc)
    pin_inst.unpin()

    pin_inst = rig_utils.PinXform(knee)
    pin_inst.pin()
    cmds.aimConstraint(ankle_loc, knee,
                        wu=[0, 1, 0], wuo=root, wut='objectrotation', aim=[1, 0, 0],
                        u=[0, 1, 0])
    cmds.delete(ankle_loc)
    pin_inst.unpin()

    pin_inst = rig_utils.PinXform(ankle)
    pin_inst.pin()

    cmds.matchTransform(ankle, knee, rot=True, position=False, pivots=False)

    pin_inst.unpin()

    pin_inst = rig_utils.PinXform(effector)
    pin_inst.pin()

    cmds.matchTransform(effector, ankle, rot=True, position=True, pivots=False)

    position = cmds.xform(effector, q=True, os=True, t=True)
    position[0] -= 1
    position[1] += 2.5
    cmds.xform(effector, os=True, t=position)

    pin_inst.unpin()


def align_eye_01(guide_root):
    root = pmc.PyNode(guide_root)
    parts = get_guide_parts(root)
    root = root.name()

    look = get_guide_part('look', parts)

    fix_eye_pivot(root)

    root_position = cmds.xform(root, q=True, ws=True, t=True)
    position = cmds.xform(look, q=True, ws=True, t=True)
    aligned_position = (root_position[0], root_position[1], position[2])
    cmds.xform(look, ws=True, t=aligned_position)

    look_loc = cmds.spaceLocator(n='look_temp_loc')[0]
    cmds.matchTransform(look_loc, look, rot=True, position=True)

    pin_inst = rig_utils.PinXform(root)
    pin_inst.pin()
    constraint = cmds.aimConstraint(look_loc, root,
                                    wu=[0, 1, 0], aim=[0, 0, 1],
                                    u=[0, 0, 1])
    pin_inst.unpin()
    cmds.delete(look_loc)


def align_foot_bk_01(guide_root):

    root = pmc.PyNode(guide_root)
    parts = get_guide_parts(root)
    root = root.name()
    side = cmds.getAttr(f'{root}.comp_side')
    loc0 = get_guide_part('0_loc', parts)
    loc1 = get_guide_part('1_loc', parts)
    loc2 = get_guide_part('2_loc', parts)
    heel = get_guide_part('heel', parts)
    inpivot = get_guide_part('inpivot', parts)
    outpivot = get_guide_part('outpivot', parts)

    child_loc = cmds.spaceLocator()[0]
    cmds.matchTransform(child_loc, loc0, rot=True, position=True, pivots=False)
    custom_loc = cmds.spaceLocator()[0]
    locs = [child_loc, custom_loc]
    pos = cmds.xform(root, q=True, ws=True, t=True)
    pos[1] += 1
    cmds.xform(custom_loc, ws=True, t=pos)

    pin_inst = rig_utils.PinXform(root)
    pin_inst.pin()
    constraint = cmds.aimConstraint(custom_loc, root, wuo=child_loc,
                                    wut='object', wu=[0, 1, 0], aim=[0, 1, 0],
                                    u=[1, 0, 0])
    pin_inst.unpin()
    cmds.delete(constraint)
    cmds.delete(locs)

    parent = cmds.listRelatives(root, p=True, f=True)

    if parent:
        parent = parent[0]
        x_axis = (0, 0, -1)
        y_axis = (0, 1, 0)
        z_axis = (1, 0, 0)
        if side == 'R':
            x_axis = (0, 0, 1)
            y_axis = (0, -1, 0)
            z_axis = (1, 0, 0)
        matrix = rig_utils.build_matrix(x_axis, y_axis, z_axis)
        loc = cmds.spaceLocator(n='temp_loc')[0]
        if parent:
            loc = cmds.parent(loc, root)
        cmds.xform(loc, os=True, matrix=matrix)
        cmds.parent(loc, w=True)
        pin_inst = rig_utils.PinXform(parent)
        pin_inst.pin()
        cmds.matchTransform(parent, loc, rot=True, position=False, pivots=False)
        pin_inst.unpin()
        cmds.delete(loc)

    children = [loc0,
                loc1,
                loc2,
                heel,
                inpivot,
                outpivot]

    for child in children:
        cmds.matchTransform(child, root, rot=True, position=False, pivots=False)
        if child.endswith('_loc') or child.endswith('_heel'):
            cmds.setAttr('%s.translateZ' % child, 0)


def align_meta_01(guide_root):

    root = pmc.PyNode(guide_root)
    parts = get_guide_parts(root)
    root = root.name()

    locs = list(parts.values())
    end_loc = []

    locs = [loc.name() for loc in locs]
    locs.reverse()

    for loc in locs:
        if not loc.endswith('_loc'):
            continue

        children = cmds.listRelatives(loc, type='transform',f=True)
        if not children:
            end_loc.append(loc)
            continue

        up_found = None
        for child in children:
            if child in locs:
                up_found = child
                break

        aim_found = []
        for child in children:
            if child in locs:
                continue
            if not child.endswith('root'):
                continue
            aim_found.append(child)
        if not aim_found:
            end_loc.append(loc)

        if aim_found:

            child = aim_found[0]

            child_loc = cmds.spaceLocator()[0]
            cmds.matchTransform(child_loc, child, rot=True, position=True)

            up_object = None
            up_loc = None

            if up_found:
                up_object = up_found
                up_loc = cmds.spaceLocator()[0]
                cmds.matchTransform(up_loc, up_object, position=True)

            pin_inst = rig_utils.PinXform(loc)
            pin_inst.pin()
            if up_object:
                cmds.aimConstraint(child_loc,
                                   loc,
                                   u=[1, 0, 0], wu=[0, 1, 0], aim=[0, 0, 1], wuo=up_loc, wut='object')
            else:
                cmds.aimConstraint(child_loc, loc, u=[0, 1, 0], wu=[0, 1, 0], aim=[0, 0, 1], wuo=root, wut='objectrotation')
            cmds.delete(child_loc)
            if up_object:
                cmds.delete(up_loc)
            pin_inst.unpin()

    for loc in end_loc:
        pin_inst = rig_utils.PinXform(loc)
        pin_inst.pin()
        cmds.setAttr(f'{loc}.rotate', *[0, 0, 0])
        pin_inst.unpin()


def align_neck_ik_01(guide_root):
    root = pmc.PyNode(guide_root)
    parts = get_guide_parts(root)
    root = root.name()

    head = get_guide_part('head', parts)
    neck = get_guide_part('neck', parts)
    tan0 = get_guide_part('tan0', parts)
    tan1 = get_guide_part('tan1', parts)
    effector = get_guide_part('eff', parts)
    curve = get_guide_part('neck_crv', parts)

    children = [neck, tan0, tan1, head, effector]
    child_loc = cmds.spaceLocator()[0]
    cmds.matchTransform(child_loc, root, position = True)

    tangent = cmds.pointOnCurve(curve, parameter=.001, nt=True)
    cmds.xform(child_loc, r=True, t=tangent)

    pin_inst = rig_utils.PinXform(root)
    pin_inst.pin()
    cmds.aimConstraint(child_loc, root, u=[0, 1, 0], wu=[0, 0, -1], aim=[0, 0, 1])
    cmds.delete(child_loc)
    pin_inst.unpin()

    for child in children:
        pin_inst = rig_utils.PinXform(child)
        pin_inst.pin()
        cmds.setAttr(f'{child}.translateX', 0)
        cmds.xform(child, ws=True, ro=[0, 0, 0])
        pin_inst.unpin()


def align_mouth_02(guide_root):
    root = pmc.PyNode(guide_root)
    parts = get_guide_parts(root)
    root = root.name()

    rotcenter = get_guide_part('rotcenter', parts)
    lipup = get_guide_part('lipup', parts)
    liplow = get_guide_part('liplow', parts)
    jaw = get_guide_part('jaw', parts)

    guides = [rotcenter,lipup, liplow, jaw]

    for guide in guides:
        pin_inst = rig_utils.PinXform(guide)
        pin_inst.pin()
        cmds.setAttr(f'{guide}.translateX', 0)
        cmds.xform(guide, ws = True, ro = [0,0,0])
        pin_inst.unpin()


def align_chain_IK_spline_variable_FK_01(guide_root):
    root = pmc.PyNode(guide_root)
    parts = get_guide_parts(root)
    root = root.name()

    locs = list(parts.values())
    locs = [loc.name() for loc in locs]
    locs.reverse()
    end_loc = []

    for loc in locs:
        if not loc.endswith('_loc'):
            continue

        children = cmds.listRelatives(loc, type='transform', f = True)
        if not children:
            end_loc.append(loc)
            continue
        child = children[0]
        split_name = child.split('|')[-1]
        if not split_name in locs:
            end_loc.append(loc)
            continue

        if split_name.endswith('root'):
            continue

        child_loc = cmds.spaceLocator()[0]
        cmds.matchTransform(child_loc, child, rot=True, position=True)

        pin_inst = rig_utils.PinXform(loc)
        pin_inst.pin()
        cmds.aimConstraint(child_loc, loc, u=[0, 1, 0], wu=[0, 1, 0], aim=[1, 0, 0], wuo = root, wut = 'objectrotation')
        cmds.delete(child_loc)
        pin_inst.unpin()

    for loc in end_loc:
        pin_inst = rig_utils.PinXform(loc)
        pin_inst.pin()
        cmds.setAttr(f'{loc}.rotate', *[0, 0, 0])
        pin_inst.unpin()


def remove_facial():

    facial_roots = ['faceTweakerDummy_C0_root', 'faceTweakerCollect_C0_root', 'face_ui_C0_root']
    existing = cmds.ls(facial_roots)
    if existing:
        cmds.delete(existing)
    else:
        _LOGGER.warning('Could not find any facial to remove', extra=ui_interesting)


def batch_duplicate_selected_guides(sym=False):
    """
    Will duplicate selected guide in one go.

    Args:
        sym(bool): Will mirror the duplicated guides.
                   Default is False.

    """
    selection = pmc.ls(sl=True)
    for node in selection:
        pmc.select(node)
        guide_manager.duplicate(sym)
        pmc.select(clear=True)
