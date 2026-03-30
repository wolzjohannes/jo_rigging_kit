# Author: Johannes Woz / Head of Rigging

"""
Post script to add all our visibility attributes to a visbility control.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import built-in modules
import logging
from importlib import reload
from pymel import core as pmc

# Import third-party modules
from future import standard_library
import mgear.shifter.custom_step as cstp

from pxo_rigging_kit.maya_utils.maya_conversion_utils import pymaya_to_pymel
# Import local modules
from pxo_rigging_kit.maya_utils.rigging import rig_utils
from pxo_rigging_kit.maya_utils.mgear import mgear_build_utils
from pxo_rigging_kit.maya_utils import assembly_utils

# Needs to be imported even if it is not used because the custom pymel classes will be registered.
from pxo_rigging_kit.maya_utils import pymel_utils
from pxo_rigging_kit.maya_utils import scene_utils
from pxo_rigging_kit.maya_utils import exceptions

reload(exceptions)

#######################################################
# GLOBALS
#######################################################

logging.basicConfig(level=logging)
_LOGGER = logging.getLogger(__name__ + ".py")
standard_library.install_aliases()

#######################################################
# CLASSES
#######################################################


class CustomShifterStep(
    rig_utils.RigVisibilitySetup, cstp.customShifterMainStep
):

    COMPONENT = "visibility"
    IK_NAME_PATTERNS = [
        "_ik",
        "_ik0",
        "_ik1",
        "_ik2",
        "_ik3",
        "_ik4",
        "_ik5",
        "_upv",
        "_armTangent",
        "_forearmTangent",
        "_elbowTangent",
        "_tan",
        "_roll",
    ]
    FK_NAME_PATTERN = "_fk"
    C_SIDE_LABEL = "C"
    L_SIDE_LABEL = "L"
    R_SIDE_LABEL = "R"
    IK_TYPE_STR = "ik"
    FK_TYPE_STR = "fk"
    DF_TYPE_STR = "df"
    CTRL_TYPES = (IK_TYPE_STR, FK_TYPE_STR, DF_TYPE_STR)
    SORT_LIST = [
        "local",
        "global",
        "flyCON",
        "body",
        "root",
        "arm",
        "spine",
        "leg",
        "foot",
        "hand",
        "finger",
        "wing",
    ]

    def __init__(self):
        super(CustomShifterStep, self).__init__()
        self.name = "pxo_visibility_setup"
        self.ctrl_attributes_data = []
        self.geo_attributes_data = []
        self.overall_rig_attributes_data = [
            {
                "connect_to": "jnt_vis",
                "force_connect": True,
                "separator": "mgear_controls",
                "longName": "mgear_jnt_vis",
                "type": "bool",
                "keyable": True,
                "defaultValue": 0,
            },
            {
                "connect_to": "ctl_vis",
                "force_connect": True,
                "separator": "mgear_controls",
                "longName": "ctrl_vis",
                "type": "bool",
                "keyable": True,
                "defaultValue": 1,
            },
            {
                "connect_to": "ctl_vis_on_playback",
                "force_connect": True,
                "separator": "mgear_controls",
                "longName": "hidden_ctl_on_playback",
                "type": "bool",
                "keyable": True,
                "defaultValue": 1,
            },
            {
                "connect_to": "ctl_x_ray",
                "force_connect": True,
                "separator": "mgear_controls",
                "longName": "ctl_x_ray",
                "type": "bool",
                "keyable": True,
                "defaultValue": 0,
            },
        ]

    def run(self, stepDict):
        """Run Method.

        Args:

            stepDict(dict): Containing the objects from the previous
            custom step.

        Example:
            stepDict["mgearRun"].global_ctl gets back the global_ctl
            from shifter rig from post step

        """
        resolution_grps = []
        acting_step_dict = stepDict["mgearRun"]
        rig_root_grp = pymaya_to_pymel(stepDict["mgearRun"].model)

        world_ctl_name = stepDict["mgearRun"].options.get("world_ctl_name", False)

        visibility_ctrl = [
            mgear_build_utils.get_component_ctrls(acting_step_dict, comp_key)[0]
            for comp_key in mgear_build_utils.get_nonhost_components(
                acting_step_dict,
                self.COMPONENT,
            )
        ][0]

        # Here we assume that if an asset assembly node is not part of a reference or has no namespce
        # It is safe to use and bounded to the current asset build.
        # We do that because it could be possible to build a rig or asset assembly node in a layout or
        # anim scene. And this scene can be full of asset assembly nodes. But they are usually referenced
        # or have namespaces.
        asset_assembly_nd = [
            node
            for node in assembly_utils.get_asset_assembly_nodes_from_scene()
            if not any(
                [
                    scene_utils.get_reference_from_node(node),
                    node.parentNamespace(),
                ]
            )
        ]

        if len(asset_assembly_nd) > 1:
            raise exceptions.RigAssetAssemblyError(
                f"More then one asset assembly node exist in the scene: {asset_assembly_nd}"
            )
        assembly_data_list = asset_assembly_nd[0].get_assembly_data()

        for data_dict in assembly_data_list:
            resolution_grps.extend(data_dict.get("resolution_groups", []))

        # Here we prep all data lists of the init for the creation
        self._prep_overall_rig_attributes_data(rig_root_grp)

        self._prep_geo_attributes_data(assembly_data_list)

        self._prep_rig_controls_attr_data(acting_step_dict)

        # This is where the attributes are created and connected.
        self.creation(visibility_ctrl, resolution_grps)

        # Connect mdl displ type switch
        for data_dict_ in assembly_data_list:
            data_dict_["asset_root"].overrideEnabled.set(1)
            visibility_ctrl.attr(self.MDL_DISPL_TYPE).connect(
                data_dict_["asset_root"].overrideDisplayType, force=True
            )

        if world_ctl_name:
            pmc.PyNode(world_ctl_name).overrideEnabled.set(True)

    def _prep_overall_rig_attributes_data(self, rig_root_grp):
        """
        Creates the overall rig attributes data for the creations.

        Args:
            rig_root_grp: THe mgear rig root group.

        """
        for overall_rig_data_dict in self.overall_rig_attributes_data:
            overall_rig_data_dict["connect_to"] = [
                rig_root_grp.attr(overall_rig_data_dict["connect_to"])
            ]

    def _prep_geo_attributes_data(self, assembly_data_list):
        """
        Creates the geo attributes data list, so we can create geo visibility attributes.

        Args:
            assembly_data_list(list): The asset assembly data.

        """
        model_component_key_list = []
        for assembly_dict in assembly_data_list:
            model_component_key_list.extend(
                list(assembly_dict["components"])
            )
        for data_dict in assembly_data_list:
            mdl_components = data_dict["components"]
            component_items = sorted(mdl_components.items())
            for comp_grp_name, comp_grp_dict in component_items:
                tmp_dict = {
                    "connect_to": [list(comp_grp_dict.keys())[0].visibility],
                    "longName": comp_grp_name.split(":")[-1].split("_")[0],
                    "type": "bool",
                    "keyable": True,
                    "defaultValue": 1,
                }
                self.geo_attributes_data.append(tmp_dict)

    def _prep_rig_controls_attr_data(self, acting_step_dict):
        """
        Prep the rig_controllers_attr_data for the rig controls visibility creation.
        In an alphabatical order.

        Args:
            acting_step_dict(dict): The mgear build data dict.
        """

        def _get_control_shapes_lod_vis_attr(controls_list):
            """
            Sub function to get the lodVisbility of
            the shape nodes from all nodes in given list.

            Args:
                controls_list(list): The rig controllers list.

            Returns:
                List: List of pmc.Attributes.
                None if fails.

            """
            result = []
            for ctrl in controls_list:
                shapes = ctrl.getShapes()

                for shape in shapes:
                    result.append(shape.lodVisibility)

            return result

        # We're first getting all component keys.
        all_comp_keys = [
            comp_key
            for comp_key in list(acting_step_dict.components.keys())
            if self.COMPONENT not in comp_key
        ]

        # Then we create a temporary dict.
        # With this we can sort all components by side and type.
        tmp_dict = {
            mgear_build_utils.get_component_name(acting_step_dict, comp_key): {
                self.C_SIDE_LABEL: {
                    ctrl_type: [] for ctrl_type in self.CTRL_TYPES
                },
                self.L_SIDE_LABEL: {
                    ctrl_type: [] for ctrl_type in self.CTRL_TYPES
                },
                self.R_SIDE_LABEL: {
                    ctrl_type: [] for ctrl_type in self.CTRL_TYPES
                },
            }
            for comp_key in all_comp_keys
        }

        # Loop again the components and sort them into our temporary dict.
        for comp_key in all_comp_keys:
            side = mgear_build_utils.get_component_side(
                acting_step_dict, comp_key
            )
            comp_name = mgear_build_utils.get_component_name(
                acting_step_dict, comp_key
            )
            all_rig_ctrls = mgear_build_utils.get_component_ctrls(
                acting_step_dict, comp_key
            )
            for ctrl in all_rig_ctrls:
                ctrl_name = ctrl.name(stripNamespace=True, long=None)
                for ik_pattern in self.IK_NAME_PATTERNS:
                    if ik_pattern in ctrl_name:
                        tmp_list = tmp_dict[comp_name][side].get(
                            self.IK_TYPE_STR, []
                        )
                        tmp_dict[comp_name][side][
                            self.IK_TYPE_STR
                        ] = tmp_list + [ctrl]
                        continue
                if self.FK_NAME_PATTERN in ctrl_name:
                    tmp_list = tmp_dict[comp_name][side].get(
                        self.FK_TYPE_STR, []
                    )
                    tmp_dict[comp_name][side][self.FK_TYPE_STR] = tmp_list + [
                        ctrl
                    ]
                else:
                    tmp_list = tmp_dict[comp_name][side].get(
                        self.DF_TYPE_STR, []
                    )
                    tmp_dict[comp_name][side][self.DF_TYPE_STR] = tmp_list + [
                        ctrl
                    ]

        # Now we take our temporary dict and produce our attributes data dicts out of it.
        # Then we append our new attributes data dicts to the ctrl_attributes_data for the creation method.
        # Here we sort the attributes in alphabatical order.
        for comp_name, side_dict in sorted(tmp_dict.items()):
            for side_, type_dict in side_dict.items():
                for tp in sorted(type_dict.keys()):
                    ctrl_data = type_dict.get(tp, False)
                    if ctrl_data:
                        ctrl_dict = {
                            "type": "bool",
                            "keyable": True,
                            "hidden": False,
                            "separator": f"{comp_name}_controls_vis",
                            "defaultValue": 1,
                            "longName": f"{side_}_{comp_name}_{tp}_cons_vis",
                            "connect_to": _get_control_shapes_lod_vis_attr(
                                ctrl_data
                            ),
                        }
                        self.ctrl_attributes_data.append(ctrl_dict)
