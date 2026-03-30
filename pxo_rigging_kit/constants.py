# Import built-in modules
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import built-in modules
import os.path

# Import third-party modules
from future import standard_library
from maya_pyblish_plugins.constants import LOD_MASTER
import pixo_paths
from collections import OrderedDict

# Import local modules
from pxo_rigging_kit.paths import get_package_icons_path
from pxo_rigging_kit.paths import get_package_root_path
from pxo_rigging_kit.paths import get_guides_template_path
from pxo_rigging_kit.paths import get_mgear_pre_script_path
from pxo_rigging_kit.paths import get_mgear_post_script_path

standard_library.install_aliases()

try:
    from maya_pyblish_plugins.constants import LOD_MASTER
except ImportError:
    LOD_MASTER = "lod_master"

CONFIG_FILE_NAME = "pxo_rigging_kit"

PXO_PROJECT_SGID = "PXO_PROJECT_SGID"

# file type
MAYA_WORKFILE_EXTENSION = ".ma"
JSON = "json"
NPY = "npy"

NG_PLUGIN_EXECUTABLE = "ngSkinTools2.mll"

# filepaths for version IO
PXO_FILEPATH_TEST = "PXO_TEST"

PXO_FILEPATH_DFRM = "PXO_DFRM"
PXO_FILEPATH_DFRM = "PXO_DFRM"

PXO_FILEPATH_BSHP = "PXO_BSHP"

PXO_FILEPATH_SKIN = "PXO_SKIN"
PXO_FILEPATH_SKPC = "PXO_SKPC"
PXO_FILEPATH_SLYR = "PXO_SLYR"
PXO_FILEPATH_SPRC = "PXO_SPRC"
PXO_FILEPATH_SCIF = "PXO_SKIF"


PXO_MODEL_ASSET_TYPE_DICT = {
    "name": "pxo_asset_type",
    "value": 1
}

PXO_MODEL_ROOT_COMPONENT_TYPE_DICT = {
    "name": "pxo_asset_component",
    "value": "default",
}

PXO_EXPORT_GEO = "PXM_export_geometry"
PXO_MODEL_ASSET_RENDER_GEO = {
    "name": "pxo_asset_usage",
    "value": 0
}

PXO_UUID_ATTR_NAME = "pxo_uuid"

UUID_SEPERATOR = "|"

PXO_UUID_DICT = {
    "meta": "e9a23cbc-4551-5895-1716-b440c3d165e0",
    "mdl": "20f35e63-0daf-44db-fa4c-3f68f5399d8c",
    "asset_assembly": "a0f0bb9b-285d-4c85-1720-030efd321efb",
    "rig": "631cc152-ec7c-7d64-cd88-c87adf45a707",
    "container": "5f0b6ebc-4bea-1028-5ba2-b8a6ce78b863",
    "root": "63a9f0ea-7bb9-8050-796b-649e85481845",
    "sub": "8a68dc3e-925e-acf9-2633-be230722a140",
}

PXO_ASSET_GEO_ROOT = "PXM_asset_geo_root"
PXO_ASSET_NAME_ATTR = "PXM_asset_name"
PXO_ASSET_ASSEMBLY_NODE_ASSEMBLED_ASSET_ATTR = "assembled_assets"
PXO_ASSET_ASSEMBLY_NODE_ASSET_NAME_ATTR = "asset_name"
PXO_ASSET_ASSEMBLY_NODE_VERSION_ATTR = "version"
PXO_ASSET_ASSEMBLY_NODE_COMPONENTS_ROOT_ATTR_SUFFIX = "components_root"
PXO_ASSET_ASSEMBLY_NODE_COMPONENTS_ATTR_SUFFIX = "components"
PXO_ASSET_ASSEMBLY_NODE_INVALID_COMP_ATTR_SUFFIX = "invalid_components"
PXO_ASSET_ASSEMBLY_NODE_NAME = "pxo_asset_assembly_NTW"
PXO_ASSET_ASSEMBLY_NODE_ASSET_PUBLISH_PATH = "publish_path"
PXO_ASSET_ASSEMBLY_NODE_ASSET_ROOT_NODE = "asset_root"
PXO_ASSET_ASSEMBLY_NODE_TAGGED_GEO_ATTR_NAME = "tagged_geo"
PXO_ASSET_ASSEMBLY_NODE_USE_KEY_REGEX_ATTR_NAME = "use_key_regex"
PXO_ASSET_ASSEMBLY_NODE_RESOLUTION_NAME_ATTR = "resolution_groups"

INVALID_ASSET_ASSEMBLY_MODEL_COMPONENT_ATTR_SUFFIX = "invalid"

PXO_SEPARATOR_STRING = "########"
PACKAGE_ROOT_PATH = get_package_root_path()
ICONS_PATH = get_package_icons_path()

GUIDES_TEMPLATE_PATH = get_guides_template_path()
MGEAR_POST_SCRIPT_PATH = get_mgear_post_script_path()
MGEAR_PRE_SCRIPT_PATH = get_mgear_pre_script_path()

WILDCARD = "_*_"
ADDIT_SCRIPTS_DECLA_NAME = f"pxo{WILDCARD}additions.py"

PXO_RIG_ROOT_CONTAINER_LOGO = "rig_root.png"
PXO_RIG_SUB_CONTAINER_LOGO = "rig_sub.png"
PXO_RIG_ROOT_CONTAINER_LOGO_PATH = pixo_paths.normalize(f"$XBMLANGPATH\{PXO_RIG_ROOT_CONTAINER_LOGO}")
PXO_RIG_SUB_CONTAINER_LOGO_PATH = pixo_paths.normalize(f"$XBMLANGPATH\{PXO_RIG_SUB_CONTAINER_LOGO}")
LOD_ROOT_SET_META_ATTR_NAME = "LOD_root_set"
LOD_SUB_SET_META_ATTR_NAME = "LOD_sub_set"
IS_LOD_MASTER = "is_lod_master"
LOD_MASTER_NUMBER = "lod_master_number"
LOD_RIG = "lod_rig"
LOD_INDEX_META_ATTR = "lod_index"
LOD_SUB_SET_TYPE_META_ATTR_NAME = "LOD_sub_set_type"
LOD_NAME_META_ATTR = "lod_name"
LOD_LOWEST_META_ATTR = "lowest_lod"
LOD_HIGHEST_META_ATTR = "highest_lod"

PXO_UNUSED_NODES_META_ATTR = "pxo_unused_dag_nodes"
SCRIPT_NODES_META_ATTR = "script_nodes"
RIG_ROOT_ATTR = "rig_root_node"
RIG_SETUP_ROOT_NAME = "rig_root_grp"

GLOBAL_CTRL_NAME = "global_0_*_ctrl"

RIG_META_ND_NAME = "rig_root_meta_nd"
PXO_CONTROLS_SET_NAME = "controllers_set"
PXO_ADD_SET_NAME = "additional_container_publishes_set"
PXO_DEFORMERS_SET_NAME = "deformers_set"
PXO_ADDITIONAL_PUBLISHES_SET_NAME = "additional_container_publishes_set"
PXO_ROOT_SET_NAME = "pxm_rig_root_set"

PXO_COMPONENTS_ROOT_SET_NAME = "components_root_set"

PXO_ANIMATION_CTRL_TAG = "PXM_export_animation"
PXO_ANIMATION_LGT_TAG = "PXM_export_light"
MGEAR_MATRIX_CONSTRAINT = "mgear_matrixConstraint"

HIK_TARGET_RIG_CHAR_DESCRIPTION_NAME = "hik_target_rig_description"
HIK_SOURCE_RIG_CHAR_DESCRIPTION_NAME = "hik_source_rig_description"
HIK_IK_FK_MATCH_JSON_NAME = "hik_ik_fk_match_data"
GUIDE_VERSION_ATTR_NAME = "guide_version"
GUIDE_TAG_NAME = "ismodel"
MAYA_ARNOLD_ATTR_PREFIX = "mtoa_constant"
RIG_SYS_CONTROL_TAG = "isCtl"
HOST_COMP_NAME = "Host"

SKIN_PRECISION_MODE_NODE_TAG = "skin_savemode_node"
SKIN_PRECISION_PARENT_TAG = "skin_savemode_master"

PXO_MDL_RESOLUTION_GRP_NAMES = ["proxy",
                                "render",
                                # "mdl_prx",
                                # "default",
                                # "low",
                                # "mid",
                                # "high",
                                ]
RIG_PROXY_ID = 459
SKIN_LAYER_INDEX = "skin_merge_layer_index"
SKIN_MERGE_FLAG = "is_skin_merge_set"
SKIN_LAYER_FLAG = "is_skin_merge_layer"
LOD_SET_NAME_META_ATTR = "set_name"

SKIN_MERGE_DESTINATION_FLAG = "is_skin_merge_destination"
SKIN_PRE_BND_MTX_SRCE_JNT_ATTR_NAME = "pre_bnd_mtx_source_joint"
SKIN_PRE_BND_MTX_WS_TRS_TAG = "is_pre_bnd_mtx_ws_trs"
SKIN_PRE_BND_MTX_WS_TRS_MASTER_SKINCLUSTER_ATTR_NAME = "master_skincluster"
PARENT_ND_ATTR_NAME = "parent_nd"
PRE_BND_MTX_TRS_DATA_LOOKUP_EXPORT_NAME = "pre_mtx_trs_data_dict"
PRE_BND_MTX_TRS_DATA_LOCATION_FOLDER_NAME = "PXO_PRE_MTX_TRS"
SKINLAYER_LOOKUP_EXPORT_NAME = "skinlayer_data_dict"
SKINLAYER_DATA_LOCATION_FOLDER_NAME = "PXO_SKINLAYER"
SKIN_LAYER_GEO_TAG = "PXM_skinlayer_geometry"

LOCALIZE_INF_LOOKUP_EXPORT_NAME = "skin_inf_localize_data_dict"

MGEAR_MATRIX_CONSTRAINT_NAME = "mgear_mtx"
DIRECT_CONNECTION_NAME = "direct"
CONSTRAINT_TYPES = {MGEAR_MATRIX_CONSTRAINT_NAME: "mgear_matrixConstraint",
                    DIRECT_CONNECTION_NAME: "None",
                    }

SKIN_LOCALIZATION_TYPE_ATTR = "skin_inf_localize_type"

IK_REF_ENUM_STR = "ref"

# shader utils module
SHADER_UTILS_TAG = "from_shader_utils"
BLEND_CONNECTION_TAG = "is_input_edge"
TEXTURE_TAG = "is_texture"
FILE_TAG = "is_file"
VARIATION_TAG = "is_var_texture"
SINGLE_TAG = "is_single_texture"
SINGLES_TAG = "is_single"
DISPLACEMENT_TAG = "is_displacement"
MULTIPLES_TAG = "is_multiples"
MAX_INDEX = "max_index"
VARIANT_INDEX = "variant_index"
VIS_CTRL_TOKEN = ("visibility_C_0_control_default_ctrl", "visibility_C_0_ctrl")

AVAILABLE_SHADERS = {
    "lambert": "ms",
    "blinn": "ms",
    "phong": "ms",
    "phongE": "ms",
    "arnold": "ar",
    "surfaceShader": "ms",
}
UV_REPETITION = 1

SHADER_PROPERTIES = {
    "lambert": {
        "color": ("color", "clr", TEXTURE_TAG),
        "reflection": (None, None, TEXTURE_TAG),
        "displacement": ("normalCamera", "dsp", DISPLACEMENT_TAG),
        "transparency": (None, None, TEXTURE_TAG),
    },
    "blinn": {
        "color": ("color", "clr", TEXTURE_TAG),
        "reflection": ("specularColor", "spr", TEXTURE_TAG),
        "displacement": ("normalCamera", "dsp", DISPLACEMENT_TAG),
        "transparency": ("transparency", None, TEXTURE_TAG),
    },
    "phongE": {
        "color": ("color", "clr", TEXTURE_TAG),
        "reflection": ("specularColor", "spr", TEXTURE_TAG),
        "displacement": ("normalCamera", "dsp", DISPLACEMENT_TAG),
        "normal": ("normalCamera", "nrm", DISPLACEMENT_TAG),
        "transparency": (None, None, TEXTURE_TAG),
        "specular": ("specularColor", "spec", TEXTURE_TAG)
    },
    "surfaceShader": {
        "color": ("outColor", "clr", TEXTURE_TAG),
        "reflection": (None, None, TEXTURE_TAG),
        "displacement": (None, None, DISPLACEMENT_TAG),
        "normal": (None, None, DISPLACEMENT_TAG),
        "transparency": ("outTransparency", "trs", TEXTURE_TAG),
    },
}
NODE_SUFFIXES = {"file": "txt", "checker": "ckr"}
UDIM_STRINGS = ["oneUdim", "oneUdimXgen", "animTex"]
UDIM_EXCLUSION_STRING = ["Head", "rgb"]

# Joint
RIG_JOINT_ROOT_NAME = "jnt_org"
ROTATE_ORDER_DICT = {"xyz": 0, "yzx": 1, "zxy": 2, "xzy": 3, "yxz": 4, "zyx": 5}

# chop settings
CHOP_NTW_ND_TAG_NAME = "is_chopper_network"
CHOP_LAYER_NAME = "chop_layer"
CHOP_SET_NAME = "chop_set"
CHOP_SYSTEM_TAG = "chop_system"
CHOP_INPUT_MESH_TAG = "chop_input_geo"
CHOP_OUTPUT_MESH_TAG = "chop_output_geo"
CHOP_INCONNECT_MESH_TAG = "chop_resultmesh"
CHOP_OUTCONNECT_MESH_TAG = "chop_submesh"
CHOP_WRAP_TAG = "chop_wrap_deformer"
CHOP_SKIN_TAG = "chop_skin_deformer"
CHOP_BLENDSHAPE_TAG = "chop_bls_deformer"
GUIDES_PUBLISH_DIR_NAME = "guides"

# pxo_constraint function
PXO_CONSTRAINT_TAG = "PXO_constraint"
PXO_CONSTRAINT_OBJECT_NAME = "PXO_constrained_object"
PXO_CONSTRAINT_GROUPED = "PXO_constraint_group"

# pxo settings
PXO_VIS_DEFAULT_SETTINGS_DIR_NAME = "PXO_RIG_VIS_SETTINGS"
PXO_VIS_DEFAULT_SETTINGS_FILE_NAME = "pxo_rig_visibility_defaults.json"
PXO_CTRLS_DEFAULT_SETTINGS_DIR_NAME = "PXO_RIG_CTRLS_SETTINGS"
PXO_CTRLS_DEFAULT_SETTINGS_FILE_NAME = "pxo_rig_controls_defaults.json"

DEFAULT_SETTING_FILE_NAMES = {
    "controlVisibility": "default_controlVisibility_attributeOrder.json",
    "wingAttributes": "default_controlVisibility_attributeOrder.json",
}

SCENE_SETTING_FILE_NAMES = {
    "controlVisibility": "scene_controlVisibility_attributeOrder.json",
    "wingAttributes": "scene_controlVisibility_attributeOrder.json",
}

# pxo attributes settings
ATTRDATA_LOCATION_FOLDER_NAME = "PXO_ATTRIBUTES"
ATTRDATA_LOOKUP_EXPORT_NAME = "attributes_data"


# pxo version_io
LOOK_UP_IO = "look_up_table"
DEFAULT_DATA_FOLDER_NAME = "PXO_MISC"

SEPARATOR = "__SEP__"
NAMESPACE = ":"

DATA_NAMES_DICT = {
    "npy": ["npy", "np", "numpy"],
    "json": ["json", "js", "jsn"],
    "obj": ["obj", "object", "export"],
    "ng": ["ng", "ngskin", "ngsk"],
    "xml": ["export_deformer_weights", "deformer_weights", "export_deformer",  "xml_wights"],
    "ma": ["ma"],
    "mb": ["mb"],
    "abc": ["abc", "alembic"]

}

SIDES_MAP = {"L_": "R_",
             "R_": "L_",
             "_L_": "_R_",
             "_R_": "_L_",
             "l_": "r_",
             "r_": "l_",
             "_r_": "_l_",
             "_l_": "_r_",
             }

AXIS_MAP = {"x"    : (1.0, 0.0, 0.0),
            "y"    : (0.0, 1.0, 0.0),
            "z"    : (0.0, 0.0, 1.0),
            "-x"   : (-1.0, 0.0, 0.0),
            "-y"   : (0.0, -1.0, 0.0),
            "-z"   : (0.0, 0.0, -1.0),
            }


NULL_MATRIX = (1, 0, 0, 0,
               0, 1, 0, 0,
               0, 0, 1, 0,
               0, 0, 0, 1,
               )

# EWAW Rig constants
COLORS = {"blue": (0.616,
                   0.816,
                   0.922,
                   ),
          "red": (0.902,
                  0.105,
                  0.100,
                  ),
          "dark_orange": (0.798,
                          0.422,
                          0.066,
                          ),
          "turquoise": (0.788,
                        0.922,
                        0.635,
                        ),
          "orange": (0.898,
                     0.522,
                     0.066,
                     ),
          "yellow": (0.921,
                     0.792,
                     0.220,
                     ),
          "magenta": (0.898,
                      0.765,
                      0.929,
                      ),
          }
RIGGING_SYSTEM_NAME = "PXO_EWAW"
EWAW_ATTR_DATA = "EWAW_rig_meta_data"

EWAW_OP_TAG = "is_operator"
EWAW_MD_TAG = "is_module"

EWAW_OP_SUB_TAG = f"{EWAW_OP_TAG}_subitem"
EWAW_MD_SUB_TAG = f"{EWAW_MD_TAG}_subitem"

EWAW_NODE_TYPES = {"operator": ((EWAW_MD_TAG, False),
                                (EWAW_OP_TAG, True)),

                   "module": ((EWAW_MD_TAG, True),
                              (EWAW_OP_TAG, False)),
                   }

EWAW_TYPES = (EWAW_OP_TAG,
              EWAW_MD_TAG,
              EWAW_OP_SUB_TAG,
              EWAW_MD_SUB_TAG,
              )

EWAW_CTRL_COLORS = {"R": {"primary": 13,
                          "secondary": 20,
                          },

                    "L": {"primary": 6,
                          "secondary": 18,
                          },

                    "C": {"primary": 17,
                          "secondary": 22,
                          },
                    }
MIRROR = {"L": ("R", ("L_", "R_")),
          "R": ("L", ("R_", "L_")),
          }

OPERATOR_EXTENSION = "OPRT"
MODULE_EXTENSION = "MDLE"

OPERATOR_SUB_EXTENSION = "opr"
MODULE_SUB_EXTENSION = "mdu"

CTRL_EXTENSION = "ctrl"
JNT_EXTENSION = "JNT"
GRP_EXTENSION = "grp"
LRA_EXTENSION = "lra"

NAMING_RULE = ["side",
               "comp_name",
               "index",
               "extension",
               ]

ICON_SUBNAMES = {"_default": 0,
                 "_process": 1,
                 "_success": 2,
                 "_error":   3,
                 }

EWAW_ATTR_TYPES = OrderedDict(
        [
            ('build_layer',
             {'attributeType': 'long', 'longName': 'build_layer'}),

            ('is_built',
             {'attributeType': 'bool', 'defaultValue': False, 'longName': 'is_built'}),

            ('misc_info',
             {'dataType': 'string', 'longName': 'misc_info'}),

            ('is_operator',
             {'attributeType': 'bool', 'defaultValue': True, 'longName': 'is_operator'}),

            ('is_module',
             {'attributeType': 'bool', 'defaultValue': True, 'longName': 'is_module'}),

            ('comp_index',
             {'attributeType': 'long', 'longName': 'comp_index'}),

            ('comp_name',
             {'dataType': 'string', 'longName': 'comp_name'}),

            ('comp_side',
             {'dataType': 'string', 'longName': 'comp_side'}),

            ('comp_type',
             {'dataType': 'string', 'longName': 'comp_type'}),

            ('comp_spaces_names',
             {'dataType': 'string', 'longName': 'comp_spaces_names'}),

            ('comp_parent_name',
             {'dataType': 'string', 'longName': 'comp_parent_name'}),

            ('comp_host_name',
             {'dataType': 'string', 'longName': 'comp_host_name'}),

            ('build_axis',
             {'dataType': 'string', 'longName': 'build_axis'}),

            ('comp_subplacement_names',
             {'attributeType': 'message', 'longName': 'comp_subplacement_nodes', 'multi': True, "CONVERT": True}),

            ('comp_lra_names',
             {'attributeType': 'message', 'longName': 'comp_lra_nodes', 'multi': True, "CONVERT": True}),

            ('comp_root_name',
             {'attributeType': 'message', 'longName': 'comp_root_nd', "CONVERT": True}),

        ]
)

