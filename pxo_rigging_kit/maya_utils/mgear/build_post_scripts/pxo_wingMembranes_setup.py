"""
Custom script for a wingMembrane animation setup.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import built-in modules
from builtins import dict
from builtins import range
from builtins import str
from builtins import zip
import logging

# Import third-party modules
from future import standard_library
import mgear.shifter.custom_step as cstp
import pymel.core as pmc

# Import local modules
from pxo_rigging_kit.maya_utils import attributes_utils
from pxo_rigging_kit.maya_utils import dag_utils
from pxo_rigging_kit.maya_utils import paths_utils
from pxo_rigging_kit.maya_utils.exceptions import MayaNodeNotFound
from pxo_rigging_kit.maya_utils.mgear import mgear_build_utils
from pxo_rigging_kit.maya_utils.rigging import rig_utils
from pxo_rigging_kit.maya_utils.maya_conversion_utils import pymaya_to_pymel as pconv


#######################################################
# GLOBALS
#######################################################

logging.basicConfig(level=logging)
_LOGGER = logging.getLogger(__name__ + ".py")
standard_library.install_aliases()

#######################################################
# CLASSES
#######################################################


class CustomShifterStep(cstp.customShifterMainStep):

    HOST_COMPONENT = "arm"
    WING_MEMBRANE_COMPONENT = "wingMembrane"
    BIG_WING_MEMBRANE_COMPONENT = "bigWingMembrane"
    JNT_ROOT_NAME = "C_bnd_local_*_jnt"
    ROOT_GRP_NAME = "wingMembrane_components_C_0_grp"
    MAIN_MEMBRANE_UP_AXES = "X"
    MAIN_MEMBRANE_SQUACH_AXES = "Z"
    MAIN_MEMBRANE_AIM_AXES = "Y"
    MAIN_MEMBRANE_BUOYANCY_ATTR_NAME = "membrane_buoyancy_effect"
    ROOT_CTRL_NAME = "root_C_*_ctrl"
    XTRA_COMPONENTS_GRP = "setup"
    GLOBAL_CTRL_NAME = "global_0_*_ctrl"

    def __init__(self):
        """
        This Class created the dragon wingMembranes system. Base of this system
        are the pxo_ribbon_rig. Each wingMembrane consists of multiple
        ribbon rigs. And each ribbon rig is his own class and isolated system.
        So you can pass the root node of each ribbon system to the class and
        you will get all needed data from the meta_data dictionary.
        To build

        Example:
            >>> self.pxo_ribbon_rig.add_guide_root_nd(your_guide_root_nd)
            >>> build_rig_root_nd = self.pxo_ribbon_rig.build_rig()
            >>> self.pxo_ribbon_rig.add_guide_root_nd(build_rig_root_nd)
            >>> meta_data = self.pxo_ribbon_rig.prep_meta_data_dict()
            >>> Result:
            >>> {
            >>> 'edge_ctrls': [{'edge_ctrl': pmc.PyNode(), 'parent_nd': string}],
            >>> 'jnt_nodes': [],
            >>> 'loft_curves': [],
            >>> 'membrane_ctrls': [],
            >>> 'nurbs_surface': [],
            >>> 'trs_nodes': [],
            >>> 'main_membrane_ctrls': [],
            >>> 'add_double_linear_nodes': [],
            >>> 'comp_name_': str,
            >>> 'comp_type_': str,
            >>> 'comp_side_': str,
            >>> 'comp_index_' int,
            >>> 'npo_nodes': [],
            >>> }

        """
        self.name = "pxo_wing_membrane_setup.py"
        self.main_membrane_default_attr_dic = {
            "default": {
                "attr_count": 2,
                "mult_factor": 2,
                "default_value": 0.5,
            },
            "vhagar": {
                "attr_count": 2,
                "mult_factor": 2,
                "default_value": 0.15,
            },
            "syrax": {"attr_count": 2, "mult_factor": 2, "default_value": 0.5},
        }

        self.big_membrane_split_index_dic = {
            "default": [
                {"start": 0, "stop": 4},
                {"start": 5, "stop": 11},
            ],
            "dragon": [
                {"start": 0, "stop": 4},
                {"start": 7, "stop": 11},
            ],
        }
        self.sine_setup_attributes_dict_list = [
            {"longName": "progress", "type": "doubleAngle", "keyable": True},
            {
                "longName": "strength",
                "type": "float",
                "keyable": True,
                "defaultValue": 1.0,
            },
            {
                "longName": "clamp_at_zero",
                "type": "float",
                "keyable": True,
                "hasMinValue": True,
                "hasMaxValue": True,
                "minValue": 0.0,
                "maxValue": 1.0,
            },
            {
                "longName": "speed",
                "type": "float",
                "keyable": True,
                "hasMinValue": True,
                "minValue": 1.0,
            },
            {"longName": "time_offset", "type": "doubleAngle", "keyable": True},
            {
                "longName": "negative_slope",
                "type": "float",
                "keyable": True,
                "hasMinValue": True,
                "hasMaxValue": True,
                "minValue": 0.0,
                "maxValue": 1.0,
            },
        ]
        self.jnt_root_nd = None
        self.pxo_ribbon_rig = None
        self.acting_step_dict = None
        self.global_ctrl = None
        self.root_ctrl = None

    def run(self, stepDict):
        """Run Method.

        Args:

            stepDict(dict): Containing the objects from the previous
            custom step.

        Example:
            stepDict["mgearRun"].global_ctl gets back the global_ctl
            from shifter rig from post step

        """
        self.acting_step_dict = stepDict["mgearRun"]
        # get the global rig ctrl.
        try:
            self.global_ctrl = pmc.ls(self.GLOBAL_CTRL_NAME)[0]
        except:
            raise MayaNodeNotFound(f"{self.GLOBAL_CTRL_NAME} not exist.")
        # find the root ctrl
        try:
            self.root_ctrl = pmc.ls(self.ROOT_CTRL_NAME)[0]
        except:
            raise MayaNodeNotFound(f"{self.ROOT_CTRL_NAME} not exist.")
        # get the mgear sets.
        pxm_root_set = mgear_build_utils.get_top_set(stepDict)
        controllers_set = mgear_build_utils.get_controlers_set(stepDict)
        component_roots_set = mgear_build_utils.get_comp_roots_set(stepDict)
        deformers_set = mgear_build_utils.get_deformers_set(stepDict)
        self.pxo_ribbon_rig = rig_utils.LinearRibbon()
        # First find the wingMembrane component guides.
        root_search_pattern_0 = "guide_{}_*_root_grp".format(
            self.WING_MEMBRANE_COMPONENT
        )
        guide_wing_membranes_root_nodes = pmc.ls(root_search_pattern_0)
        # Second find the bigWingMembrane component guides
        root_search_pattern_1 = "guide_{}_*_root_grp".format(
            self.BIG_WING_MEMBRANE_COMPONENT
        )
        root_search_pattern_2 = "guide_{}_sq_st_*_crv_grp".format(
            self.BIG_WING_MEMBRANE_COMPONENT
        )
        guide_big_wing_membranes_root_nodes = pmc.ls(root_search_pattern_1)
        guide_big_wing_membranes_sq_st_root_nodes = pmc.ls(
            root_search_pattern_2
        )
        # find the jnt root node from mgear hierarchy
        jnt_root_nd = pmc.ls(self.JNT_ROOT_NAME)

        if jnt_root_nd:
            self.jnt_root_nd = jnt_root_nd[0]

        # Find the arm host components
        arm_host_keys = mgear_build_utils.get_host_component(
            self.acting_step_dict, self.HOST_COMPONENT
        )
        for arm_host_key in arm_host_keys:
            arm_host_components = mgear_build_utils.get_component_object(
                self.acting_step_dict, arm_host_key
            )
        # Prep the new root for the wingMembrane rigs.
        root_grp = pmc.createNode("transform", n=self.ROOT_GRP_NAME)

        # Build the mainMembrane rigs build based on the found guides
        build_rig_root_nodes = []
        if guide_wing_membranes_root_nodes:
            for guide_root_nd in guide_wing_membranes_root_nodes:
                self.pxo_ribbon_rig.add_guide_root_nd(guide_root_nd)
                build_rig_root_nd = self.pxo_ribbon_rig.build_rig(
                    root_grp,
                    self.jnt_root_nd,
                    self.MAIN_MEMBRANE_SQUACH_AXES,
                    self.MAIN_MEMBRANE_UP_AXES,
                    self.MAIN_MEMBRANE_AIM_AXES,
                    self.global_ctrl.scaleX,
                )
                build_rig_root_nodes.append(build_rig_root_nd)
            _LOGGER.info("WingMembrane rig build successfully.")
        else:
            _LOGGER.error(
                "No guide root nodes found with the name:"
                + " {}. Will skip this step.".format(root_search_pattern_0)
            )
        # Build the bigWingMembrane rigs based on the guides.
        if guide_big_wing_membranes_sq_st_root_nodes:
            self.build_sq_st_rig_curves(
                guide_big_wing_membranes_sq_st_root_nodes,
                pxm_root_set,
                self.root_ctrl,
                root_grp,
                self.global_ctrl.scaleX,
            )
        else:
            _LOGGER.error(
                "No stretch and squatch support systems for"
                + " bigWingMebrane setups"
                + " found with the name: {}".format(root_search_pattern_2)
                + "Will skip this step."
            )
        if guide_big_wing_membranes_root_nodes:
            for guide_bigWing_root_nd in guide_big_wing_membranes_root_nodes:
                self.pxo_ribbon_rig.add_guide_root_nd(guide_bigWing_root_nd)
                big_wing_build_rig_root_nd = self.pxo_ribbon_rig.build_rig(
                    root_grp,
                    self.jnt_root_nd,
                    self.MAIN_MEMBRANE_SQUACH_AXES,
                    self.MAIN_MEMBRANE_UP_AXES,
                    self.MAIN_MEMBRANE_AIM_AXES,
                    self.global_ctrl.scaleX,
                )
                build_rig_root_nodes.append(big_wing_build_rig_root_nd)
            _LOGGER.info("BigWingMembrane rig build successfully.")
        else:
            _LOGGER.error(
                "No guide root nodes found with the name:"
                + " {}. Will skip this step.".format(root_search_pattern_1)
            )
        if build_rig_root_nodes:
            # Fill the mgear sets.
            for build_rig_root_nd in build_rig_root_nodes:
                self.pxo_ribbon_rig.add_guide_root_nd(build_rig_root_nd)
                meta_data = self.pxo_ribbon_rig.prep_meta_data_dict()
                all_controls = meta_data.get("membrane_ctrls") + meta_data.get(
                    "main_membrane_ctrls"
                )
                controllers_set.addMembers(all_controls)
                deformers_set.addMembers(meta_data.get("jnt_nodes"))
                component_roots_set.add(build_rig_root_nd)
            # Generate setpDict data for further use. Especially for the visibility
            # logic.
            for build_rig_root_nd in build_rig_root_nodes:
                self.pxo_ribbon_rig.add_guide_root_nd(build_rig_root_nd)
                meta_data = self.pxo_ribbon_rig.prep_meta_data_dict()
                all_controls = meta_data.get("membrane_ctrls")
                all_deformers = meta_data.get("jnt_nodes")
                all_controls.append(meta_data.get("main_membrane_ctrls")[0])
                comp_dic_name = "{}_{}{}".format(
                    meta_data.get("comp_name_"),
                    meta_data.get("comp_side_"),
                    meta_data.get("comp_index_"),
                )
                if stepDict["mgearRun"].components.get(comp_dic_name):
                    all_controls = (
                        stepDict["mgearRun"]
                        .components[comp_dic_name]
                        .groups.get("controllers")
                        + all_controls
                    )
                    all_root_nodes = (
                        stepDict["mgearRun"]
                        .components[comp_dic_name]
                        .groups.get("componentsRoots")
                    )
                    all_deformers = (
                        stepDict["mgearRun"]
                        .components[comp_dic_name]
                        .groups.get("deformers")
                        + all_deformers
                    )
                    all_root_nodes.append(build_rig_root_nd)
                    stepDict["mgearRun"].components[comp_dic_name].groups[
                        "controllers"
                    ] = all_controls
                    stepDict["mgearRun"].components[comp_dic_name].groups[
                        "componentsRoots"
                    ] = all_root_nodes
                    stepDict["mgearRun"].components[comp_dic_name].groups[
                        "deformers"
                    ] = all_deformers
                else:
                    mgear_fake_comp_class = mgear_build_utils.MgearFakeComponentClass(
                        build_rig_root_nd
                    )
                    mgear_fake_comp_class.set_name(meta_data.get("comp_name_"))
                    mgear_fake_comp_class.set_side(meta_data.get("comp_side_"))
                    mgear_fake_comp_class.set_index(
                        meta_data.get("comp_index_")
                    )
                    mgear_fake_comp_class.set_count(
                        meta_data.get("comp_count_")
                    )
                    mgear_fake_comp_class.set_controls_list(all_controls)
                    mgear_fake_comp_class.set_deformers_list(all_deformers)
                    stepDict["mgearRun"].components[
                        comp_dic_name
                    ] = mgear_fake_comp_class
                # Hide the nurbs_surfaces and the localAxis.
                [
                    jnt.displayLocalAxis.set(0)
                    for jnt in meta_data.get("jnt_nodes")
                ]
                [
                    nurb_surf.visibility.set(0)
                    for nurb_surf in meta_data.get("nurbs_surface")
                ]
        root_grp.setParent(self.XTRA_COMPONENTS_GRP)

    ### DISABLE THIS AREA.
    ### Because anim dept does not want these feature anymore.
    ### For safety purposes we just comment that out if we need this again.

    # # Generate a list filled with dictionaries.
    # # Here i try to get all needed data based on the wingMembranes.
    # # Because on each wingMembrane consist from multiple LinearRibbon systems.
    # # And each root nodes of such a system gets you all needed data.
    # root_nodes_dic_list = [
    #     {
    #         "root_nodes": stepDict["mgearRun"]
    #         .components[key]
    #         .root_nodes,
    #         "index": stepDict["mgearRun"].components[key].index,
    #         "side": stepDict["mgearRun"].components[key].side,
    #         "name": stepDict["mgearRun"].components[key].name,
    #         "count": stepDict["mgearRun"].components[key].count,
    #     }
    #     for key in list(stepDict["mgearRun"].components.keys())
    #     if "{}_".format(self.WING_MEMBRANE_COMPONENT) in key
    #     or "{}_".format(self.BIG_WING_MEMBRANE_COMPONENT) in key
    # ]
    # # Create membrane_buoyancy_effect effect.
    # for x in range(len(root_nodes_dic_list)):
    #     for setup_side in "LR":
    #         for root_nd_dic in root_nodes_dic_list:
    #             if (
    #                 root_nd_dic.get("index") == x
    #                 and root_nd_dic.get("side") == setup_side
    #                 and root_nd_dic.get("name")
    #                 == self.WING_MEMBRANE_COMPONENT
    #             ):
    #                 root_nodes = root_nd_dic.get("root_nodes")
    #                 self.create_membrane_buoyancy_setup(
    #                     root_nodes,
    #                     arm_host_components,
    #                     x,
    #                     setup_side,
    #                     asset_name,
    #                 )
    # big_mem_index_dic = self.big_membrane_split_index_dic.get(
    #     asset_name
    # )
    # if not big_mem_index_dic:
    #     big_mem_index_dic = self.big_membrane_split_index_dic.get(
    #         "default"
    #     )
    # for range_dic in big_mem_index_dic:
    #     for y in range(range_dic.get("start"), range_dic.get("stop")):
    #         for setup_side in "LR":
    #             for root_nd_dic in root_nodes_dic_list:
    #                 if (
    #                     root_nd_dic.get("index") == 0
    #                     and root_nd_dic.get("side") == setup_side
    #                     and root_nd_dic.get("name")
    #                     == self.BIG_WING_MEMBRANE_COMPONENT
    #                     and root_nd_dic.get("count") == y
    #                 ):
    #                     root_nodes = root_nd_dic.get("root_nodes")
    #                     self.create_membrane_buoyancy_setup(
    #                         root_nodes,
    #                         arm_host_components,
    #                         y,
    #                         setup_side,
    #                         asset_name,
    #                         "big",
    #                     )
    # # Create the wind effect.
    # for z in range(len(root_nodes_dic_list)):
    #     for setup_side in "LR":
    #         for root_nd_dic_ in root_nodes_dic_list:
    #             if (
    #                 root_nd_dic_.get("index") == z
    #                 and root_nd_dic_.get("side") == setup_side
    #                 and root_nd_dic_.get("name")
    #                 == self.WING_MEMBRANE_COMPONENT
    #             ):
    #                 root_nodes_ = root_nd_dic_.get("root_nodes")
    #                 self.create_wind_effect_setup(
    #                     root_nodes_,
    #                     arm_host_components,
    #                     z,
    #                     setup_side,
    #                     root_grp,
    #                 )
    # for root_nd_dic__ in root_nodes_dic_list:
    #     for setup_side_ in "LR":
    #         if (
    #             root_nd_dic__.get("index") == 0
    #             and root_nd_dic__.get("side") == setup_side_
    #             and root_nd_dic__.get("name")
    #             == self.BIG_WING_MEMBRANE_COMPONENT
    #         ):
    #             root_nodes__ = root_nd_dic__.get("root_nodes")
    #             self.create_wind_effect_setup(
    #                 root_nodes__,
    #                 arm_host_components,
    #                 0,
    #                 setup_side_,
    #                 root_grp,
    #                 7,
    #                 "Big",
    #             )
    # _LOGGER.info(
    #     "Build wingMembranes buoyancy and wind setup successfully."
    # )

    def get_arm_host(self, arm_host_components, side):
        """
        Get the arm host from components list by side.

        Args:
            arm_host_components(list): The arm components mgear objects.
            side(str): The side. Valid is ["L", "R"].

        Return:
            pmc.PyNode(): The arm host control.

        """
        arm_host = [
            comp.groups.get("controllers")[0]
            for comp in arm_host_components
            if comp.side == side
        ][0]
        return arm_host

    def create_membrane_buoyancy_setup(
        self,
        root_nodes,
        arm_host_components,
        index,
        side,
        asset_name="crt_crtX",
        attr_prefix=None,
    ):
        """
        Will create a system to bulge the wings to
        create buoyancy effect in the wings.

        Args:
            root_nodes(list): The wingMembrane root nodes.
            arm_host_components(list): All arm host components mgear
                                       class objects.
            index(int): WingMembrane index.
            side(str): WingMembrane side.
            root_grp(pmc.PyNode()): The parent of the new input nodes.
            row_count(int): Determine how much rows of controls
                            we want to setup per wingMembrane.
            asset_name(str): The name of the asset.
            attr_prefix(str, optional): Gives the control attribute a prefix.

        """
        attr_name = "{}_{}".format(self.MAIN_MEMBRANE_BUOYANCY_ATTR_NAME, index)

        if attr_prefix:
            attr_name = "{}_{}".format(attr_prefix, attr_name)
        arm_host = self.get_arm_host(arm_host_components, side)

        if not arm_host.hasAttr("wingMembraneAttrs"):
            attributes_utils.add_pxo_separator_attr(
                arm_host, "wingMembraneAttrs"
            )

        arm_host.addAttr(attr_name, type="float", keyable=True)
        mult_factor = 1.0 / len(root_nodes)
        mult_value = 0.0
        for root_nd in root_nodes:
            self.pxo_ribbon_rig.add_guide_root_nd(root_nd)
            meta_data_dic = self.pxo_ribbon_rig.prep_meta_data_dict()
            add_double_lin_nodes = meta_data_dic.get("add_double_linear_nodes")
            main_ctrl_npo = [
                npo
                for npo in meta_data_dic.get("npo_nodes")
                if "_main_" in npo.name()
            ][0]
            mult_value = mult_value + mult_factor
            mult_doub_lin_nd = pmc.createNode("multDoubleLinear")
            output_attr = arm_host.attr(attr_name)
            if side == "R":
                negate_nd = pmc.createNode("multDoubleLinear")
                arm_host.attr(attr_name).connect(negate_nd.input1)
                negate_nd.input2.set(-1)
                output_attr = negate_nd.output
            output_attr.connect(mult_doub_lin_nd.input1)
            mult_doub_lin_nd.input2.set(mult_value)
            mult_doub_lin_nd.output.connect(
                main_ctrl_npo.attr(
                    "translate{}".format(self.MAIN_MEMBRANE_UP_AXES)
                )
            )
            [
                mult_doub_lin_nd.output.connect(util_nd.input2)
                for util_nd in add_double_lin_nodes
            ]
            main_ctrl = [
                ctrl for ctrl in meta_data_dic.get("main_membrane_ctrls")
            ][0]
            default_settings_dic = self.main_membrane_default_attr_dic.get(
                asset_name
            )
            if not default_settings_dic:
                default_settings_dic = self.main_membrane_default_attr_dic.get(
                    "default"
                )
            attr_value = default_settings_dic.get("default_value")
            for x in range(default_settings_dic.get("attr_count")):
                main_ctrl.attr("down_stream_nd_rot_angle_{}".format(x)).set(
                    attr_value * -1.0
                )
                main_ctrl.attr("up_stream_nd_rot_angle_{}".format(x)).set(
                    attr_value
                )
                attr_value = attr_value * default_settings_dic.get(
                    "mult_factor"
                )

    def create_wind_effect_setup(
        self,
        root_nodes,
        arm_host_components,
        index,
        side,
        root_grp,
        row_count=3,
        attr_prefix="",
    ):
        """
        Create a wind effect based on a sinus node setup.

        Args:
            root_nodes(list): The wingMembrane root nodes.
            arm_host_components(list): All arm host components mgear
                                       class objects.
            index(int): WingMembrane index.
            side(str): WingMembrane side.
            root_grp(pmc.PyNode()): The parent of the new input nodes.
            row_count(int): Determin how much rows of controls
                            we want to setup per wingMembrane.
            attr_prefix(str, optional): Gives the control attribute a prefix.

        Return:
            Dict: Dict with all created data.

        """
        # Create a data dictionary for easier use. Each key represents one row
        # of a membrane.
        data_dict = dict()
        for x in range(row_count):
            data_dict[x] = {
                "name_pattern": "_{}_{}_ROOTNR_{}_".format(side, index, x + 1),
                "membrane_ctlrs_row_list": [],
            }
        arm_host = self.get_arm_host(arm_host_components, side)
        # Get all membrane controls of one row and store it in the data dict.
        for root_index, root_nd in enumerate(root_nodes):
            self.pxo_ribbon_rig.add_guide_root_nd(root_nd)
            meta_data_dic = self.pxo_ribbon_rig.prep_meta_data_dict()
            membrane_ctlrs = meta_data_dic.get("membrane_ctrls")
            for ctrl in membrane_ctlrs:
                for x in range(row_count):
                    temp_dict = data_dict.get(x)
                    search_name_pattern = temp_dict.get("name_pattern").replace(
                        "ROOTNR", str(root_index)
                    )
                    temp_dict["search_name_pattern"] = search_name_pattern
                    if search_name_pattern in ctrl.name():
                        temp_list = temp_dict.get("membrane_ctlrs_row_list")
                        temp_list.append(ctrl)
                        temp_dict["membrane_ctlrs_row_list"] = temp_list
                    data_dict[x] = temp_dict
        # Create the sine setup which is the base of the
        # wind effect for each row of the row_count in the wingMembrane.
        for row_index in range(row_count):
            row_dict = data_dict.get(row_index).copy()
            target_wave_trs_list = dag_utils.create_buffer_groups(
                row_dict.get("membrane_ctlrs_row_list"), "wave_trs"
            )
            row_dict["wave_input_trs_nd"] = rig_utils.create_sine_setup(
                target_wave_trs_list,
                "wingMembrane_{}_{}_{}_wave_setup".format(
                    side, index, row_index + 1
                ),
                row_count,
                self.MAIN_MEMBRANE_UP_AXES,
                None,
                root_grp,
            )
            data_dict[row_index] = row_dict
        attributes_utils.add_pxo_separator_attr(
            arm_host, f"{attr_prefix}wingMembrane_wind_effect_{index}"
        )
        # Get the attributes of the wingMembrane setup from
        # the pxo_rigging_kit_old class and refactor it so that we have the same on
        # on our arm_host control.
        refactored_attributes_dict_list = []
        for attr_data_dict in self.sine_setup_attributes_dict_list:
            if attr_data_dict.get("longName") != "time_offset":
                temp_attr_dict_0 = attr_data_dict.copy()
                nice_name = temp_attr_dict_0.get("longName")
                long_name = "{}_{}wingMembrane_{}".format(
                    temp_attr_dict_0.get("longName"), attr_prefix, index
                )
                temp_attr_dict_0["niceName"] = nice_name
                temp_attr_dict_0["longName"] = long_name
                refactored_attributes_dict_list.append(temp_attr_dict_0)
            else:
                for y in range(row_count):
                    temp_attr_dict_0 = attr_data_dict.copy()
                    nice_name = "{}_{}".format(
                        temp_attr_dict_0.get("longName"), y
                    )
                    long_name = "{}_{}wingMembrane_{}_{}".format(
                        temp_attr_dict_0.get("longName"), attr_prefix, index, y
                    )
                    temp_attr_dict_0["longName"] = long_name
                    temp_attr_dict_0["niceName"] = nice_name
                    refactored_attributes_dict_list.append(temp_attr_dict_0)

        for attr_dict in refactored_attributes_dict_list:
            pmc.addAttr(arm_host, **attr_dict)
        wave_trs_nodes = [
            data_dict.get(r).get("wave_input_trs_nd") for r in range(row_count)
        ]
        time_offset_attr_list = []
        for attr_dict in refactored_attributes_dict_list:
            if "time_offset" not in attr_dict.get("longName"):
                for wave_trs_nd in wave_trs_nodes:
                    arm_host.attr(attr_dict.get("longName")).connect(
                        wave_trs_nd.attr(attr_dict.get("niceName"))
                    )
            else:
                time_offset_attr_list.append(
                    arm_host.attr(attr_dict.get("longName"))
                )
        for attr_index, (wave_trs_nd, time_offset_attr) in enumerate(
            zip(wave_trs_nodes, time_offset_attr_list)
        ):
            time_offset_attr.connect(wave_trs_nd.time_offset)

    def build_sq_st_rig_curves(
        self,
        bigWingMembranes_sq_st_root_nodes,
        pxo_root_set,
        root_ctrl,
        root_grp=None,
        main_scale_input=None,
    ):
        """
        Build the squatch and stretch curve line to
        support the bigWingMembrane systems.

        Args:
            bigWingMembranes_sq_st_root_nodes(list): The root nodes.
            pxo_root_set(pmc.PyNode()): The pxo root set node.
            root_ctrl(pmc.PyNode): The root control.
            root_grp(pmc.PyNode()) The new root group for the build systems.
            main_scale_input(pmc.Attribute()): The main scale input.

        """
        obj_set = pmc.createNode(
            "objectSet", n="bigWingMembrane_sq_st_locs_set"
        )
        if pxo_root_set:
            pxo_root_set.add(obj_set)
        for system_ in bigWingMembranes_sq_st_root_nodes:
            dup = pmc.duplicate(system_, un=True)[0]
            dup.rename(
                dup.name().replace("guide_", "").replace("_grp1", "_grp")
            )
            pmc.parent(dup, root_grp)
            all_nodes = dup.getChildren(ad=True, type="transform")
            for node in all_nodes:
                node.rename(node.name().replace("guide_", ""))
                if node.hasAttr("parent_nd"):
                    parent_nd_name = node.parent_nd.get()
                    if parent_nd_name:
                        parent_nd = pmc.PyNode(parent_nd_name)
                        parent_nd.addChild(node)
                        node.visibility.set(0)
                        obj_set.add(node)
            if main_scale_input:
                loc_nodes = [
                    loc_nd
                    for loc_nd in all_nodes
                    if "_path_loc" in loc_nd.name()
                    and "_grp" not in loc_nd.name()
                ]
                for node in loc_nodes:
                    for axe in "XYZ":
                        node.attr("rotate{}".format(axe)).set(lock=False)
                    self.pxo_ribbon_rig.matrix_constraint(
                        node,
                        root_ctrl,
                        translate=False,
                        scale=False,
                    )
                    for axe in "XYZ":
                        node.attr("scale{}".format(axe)).set(lock=False)
                        main_scale_input.connect(
                            node.attr("scale{}".format(axe))
                        )
                        node.attr("scale{}".format(axe)).set(lock=True)
            dup.visibility.set(0)
            if pmc.objExists(self.BIG_WING_MEMBRANE_COMPONENT):
                pmc.PyNode(self.BIG_WING_MEMBRANE_COMPONENT).addChild(dup)
        _LOGGER.info("Build bigWingMembrane sq/st systems successfully.")

