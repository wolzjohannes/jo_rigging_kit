"""
Custom script to prepare the neck component to our needs.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import pprint

# Import built-in modules
from builtins import dict

# Import third-party modules
from future import standard_library

# Import built-in modules
import logging
from past.utils import old_div

# Import third-party modules
import pymel.core as pmc
import mgear.core.attribute as mgattr
import mgear.core.transform as mgtrans
import mgear.shifter.custom_step as cstp

# Import local modules
from pxo_rigging_kit.maya_utils import attributes_utils
from pxo_rigging_kit.maya_utils import paths_utils
from pxo_rigging_kit.maya_utils.rigging import rig_utils
from pxo_rigging_kit.maya_utils import dag_utils
from pxo_rigging_kit.maya_utils.mgear import mgear_build_utils
from pxo_rigging_kit.maya_utils.maya_conversion_utils import pymaya_to_pymel as pconv


standard_library.install_aliases()

#######################################################
# GLOBALS
#######################################################

logging.basicConfig(level=logging)
_LOGGER = logging.getLogger(__name__ + ".py")
MGEAR_NECK_CUSTOM_SCP_JSON_NAME = "pxo_neck_setup"

#######################################################
# CLASSES
#######################################################


class CustomShifterStep(cstp.customShifterMainStep):

    COMPONENT = "neck_"
    HEAD_COMPONENT = "head_"
    EXCLUDED_HEAD_COMP = "forhead"
    LAST_IK_REF_LOC = "neck_C0_3_ori_ref_loc"
    BIRD_NECK = False
    BIRD_NECK_WEIGHTS = [[0.98,0.02],[0.2,0.8]]
    NECK_IK_ORIENT_DIC = {
        "up_axes": "y",
        "aim_axes": "z",
        "aim_ref_pos": (10, 0, 0),
        "up_ref_pos": (0, -10, 0),
    }
    NECK_IK_SPACE_OBJECTS = [
        ("global", "local_C_0_control_default_ctrl"),
        ("root", "root_C_0_control_default_ctrl"),
        ("flyCon", "flyCon_C_1_control_default_ctrl"),
    ]
    SPLINE_IK_SECTION_FOLLOW_ATTR = {
        "longName": "neck_sub_cons_follow",
        "niceName": "neck_sub_cons_follow",
        "attributeType": "float",
        "minValue": 0.0,
        "maxValue": 1.0,
        "keyable": True,
        "defaultValue": 1.0,
    }
    NECK_Z_ROT_MULT_HID_ATTR_NAME = "z_rot_mult"
    NECK_Z_ROT_MULT_KEY_ATTR_NAME = "neck_ik_z_rot_mult"
    NECK_Z_ROT_CHANNEL_MAPPING = "XZ"
    HEAD_IK_ENUM_NAME = "head_ik"
    NECK_Z_ROT_DIC = {
        "neck_C_0_ik3*_ctrl": [
            {
                "index": 0,
                "mult_value": 0.75,
                "ref_node": "neck_C0_7_scl_ref",
            },
            {
                "index": 0,
                "mult_value": 0.75,
                "ref_node": "neck_C0_6_scl_ref",
            },
            {
                "index": "plus_1",
                "mult_value": 0.5,
                "ref_node": "neck_C0_8_scl_ref",
            },
            {
                "index": "plus_2",
                "mult_value": 0.25,
                "ref_node": "neck_C0_9_scl_ref",
            },
            {
                "index": "minus_1",
                "mult_value": 0.5,
                "ref_node": "neck_C0_5_scl_ref",
            },
            {
                "index": "minus_2",
                "mult_value": 0.25,
                "ref_node": "neck_C0_4_scl_ref",
            },
        ],
        "neck_C_0_ik2*_ctrl": [
            {"index": 0, "mult_value": 1, "ref_node": "neck_C0_4_scl_ref"},
            {
                "index": "plus_1",
                "mult_value": 0.75,
                "ref_node": "neck_C0_5_scl_ref",
            },
            {
                "index": "plus_2",
                "mult_value": 0.5,
                "ref_node": "neck_C0_6_scl_ref",
            },
            {
                "index": "plus_3",
                "mult_value": 0.25,
                "ref_node": "neck_C0_7_scl_ref",
            },
            {
                "index": "minus_1",
                "mult_value": 0.75,
                "ref_node": "neck_C0_3_scl_ref",
            },
            {
                "index": "minus_2",
                "mult_value": 0.5,
                "ref_node": "neck_C0_2_scl_ref",
            },
            {
                "index": "minus_3",
                "mult_value": 0.25,
                "ref_node": "neck_C0_1_scl_ref",
            },
        ],
        "neck_C_0_ik1*_ctrl": [
            {"index": 0, "mult_value": 1, "ref_node": "neck_C0_2_scl_ref"},
            {
                "index": "plus_1",
                "mult_value": 0.75,
                "ref_node": "neck_C0_3_scl_ref",
            },
            {
                "index": "plus_2",
                "mult_value": 0.5,
                "ref_node": "neck_C0_4_scl_ref",
            },
            {
                "index": "plus_3",
                "mult_value": 0.25,
                "ref_node": "neck_C0_5_scl_ref",
            },
            {
                "index": "minus_1",
                "mult_value": 0.5,
                "ref_node": "neck_C0_1_scl_ref",
            },
            {
                "index": "minus_2",
                "mult_value": 0.25,
                "ref_node": "neck_C0_0_scl_ref",
            },
        ],
    }

    def __init__(self):
        self.name = "pxo_neck_setup"
        self.acting_step_dict = None

    def run(self, stepDict):
        self.acting_step_dict = stepDict["mgearRun"]
        neck_component_keys = mgear_build_utils.get_nonhost_components(
            self.acting_step_dict, self.COMPONENT
        )
        head_component_keys = mgear_build_utils.get_nonhost_components(
            self.acting_step_dict,
            self.HEAD_COMPONENT,
            exclude_component_name=self.EXCLUDED_HEAD_COMP,
        )
        for neck_comp_key, head_component_key in zip(
            neck_component_keys, head_component_keys
        ):
            neck_controller = mgear_build_utils.get_component_ctrls(
                self.acting_step_dict, neck_comp_key
            )
            neck_host = mgear_build_utils.get_host_from_component(
                self.acting_step_dict, neck_comp_key
            )
            neck_comp_name = mgear_build_utils.get_component_name(
                self.acting_step_dict, neck_comp_key
            )
            head_controller = mgear_build_utils.get_component_ctrls(
                self.acting_step_dict, head_component_key
            )
            head_host = mgear_build_utils.get_host_from_component(
                self.acting_step_dict, head_component_key
            )
            head_comp_name = mgear_build_utils.get_component_name(
                self.acting_step_dict, head_component_key
            )
            self.tweak_last_neck_ik(neck_controller, neck_host, neck_comp_name)
            self.tweak_head_con(
                head_controller[0], neck_controller, head_comp_name, head_host
            )
            self.tweak_all_spline_sections(neck_controller, neck_host)
            self.change_neck_ik_orientation(neck_controller)
        self.add_ik_z_rot_option()

    def tweak_last_neck_ik(self, controllers, neck_host, component_name):
        """
        Will change the last neck ik to our behaviour.

        Args:
            controllers(list): List of all ik controllers.
            neck_host(pmc.PyNode()): The neck host control.
            component_name(str): The neck component name.

        """
        penultimate_fk_ctrl = [
            node for node in controllers if "fk" in node.name(long=None)
        ][-2]
        last_ik_ctrl = [node for node in controllers if "ik" in node.name()][-1]
        trs_ik_ctrl = rig_utils.create_transfrom_on_position(last_ik_ctrl)
        last_ik_ctrl_npo = last_ik_ctrl.getParent()
        last_ik_ctrl_connections = last_ik_ctrl.worldMatrix[0].connections(
            p=True
        )
        last_ik_ctrl_connections = pconv(last_ik_ctrl_connections)
        for dst_plug in last_ik_ctrl_connections:
            pmc.connectAttr(
                trs_ik_ctrl.worldMatrix[0].name(),
                dst_plug.name(),
                force=True
            )
        last_ik_ctrl.worldMatrix[0].disconnect()
        attributes_utils.unlock_attributes(last_ik_ctrl_npo)
        mgtrans.matchWorldTransform(penultimate_fk_ctrl, last_ik_ctrl_npo)
        if pmc.objExists(self.LAST_IK_REF_LOC):
            pmc.matchTransform(
                last_ik_ctrl_npo,
                pmc.PyNode(self.LAST_IK_REF_LOC),
                pos=True,
                rot=True,
                scl=False,
            )
        else:
            rig_utils.switch_mgear_control_orientation(
                pmc.PyNode(last_ik_ctrl_npo), **self.NECK_IK_ORIENT_DIC
            )
        last_ik_ctrl = pconv(last_ik_ctrl)
        last_ik_ctrl.addChild(trs_ik_ctrl)
        attributes_utils.lock_and_hide_attributes(last_ik_ctrl_npo)
        neck_ik_cns = dag_utils.create_buffer_groups([last_ik_ctrl])[0]
        neck_ik_cns.rename(neck_ik_cns.name().replace("_npo", "_cns"))
        constraint_list = [
            pmc.ls(obj[1])[0]
            for obj in self.NECK_IK_SPACE_OBJECTS
            if pmc.ls(obj[1])
        ]
        enum_list = [
            obj[0] for obj in self.NECK_IK_SPACE_OBJECTS if pmc.ls(obj[1])
        ]
        constraint_list.append(neck_ik_cns)
        pr_con = pmc.parentConstraint(constraint_list, mo=True)
        enum_list.insert(0, "Auto")
        mgattr.addEnumAttribute(
            neck_host,
            "{}_ikref".format(component_name),
            0,
            enum_list,
            "Neck Ik Ref",
        )
        pr_con_weight_list = pr_con.getWeightAliasList()
        for index, weight in enumerate(pr_con_weight_list):
            cond_nd = pmc.createNode("condition")
            neck_host.attr("{}_ikref".format(component_name)).connect(
                cond_nd.firstTerm
            )
            cond_nd.colorIfTrueR.set(1)
            cond_nd.colorIfFalseR.set(0)
            cond_nd.secondTerm.set(index + 1)
            cond_nd.outColorR.connect(weight)
        _LOGGER.info("Head_ik tweak succeed.")

    def tweak_all_spline_sections(self, controllers, host_ctrl):
        """
        Tweak the spline ik setup so that all sub ik controls follow the main
        ik.

        Args:
            controllers(list): List of controlls.
            host_ctrl(pmc.PyNode()): The neck host control.

        """
        p_cons = []
        attributes_utils.add_pxo_separator_attr(host_ctrl, "custom_attrs")
        attributes_utils.add_attribute_to_node_by_dict(
            host_ctrl, self.SPLINE_IK_SECTION_FOLLOW_ATTR
        )
        ik_ctrls = [node for node in controllers if "ik" in node.name()]
        ik_ctrls = pconv(ik_ctrls)
        def _create_parent_con_average_setup(range_tuple, targets):
            average_sub_value = 0.0
            reducing_value = round(
                old_div(1.0, (len(ik_ctrls) - average_index)), 3
            )
            for x in range(range_tuple[0], range_tuple[1]):
                average_sub_value = average_sub_value + reducing_value
                weight_ = 1.0 - average_sub_value
                mgattr.unlockAttribute(ik_ctrls[x])
                sub_ctrl_npo_ = dag_utils.create_buffer_groups([ik_ctrls[x]])[0]
                p_con_ = pmc.parentConstraint(targets, sub_ctrl_npo_, mo=True)
                weight_list = p_con_.getWeightAliasList()
                weight_list[0].set(average_sub_value)
                weight_list[1].set(weight_)
                p_cons.append(p_con_)

        average_index = int(round(old_div(len(ik_ctrls), 2)))
        mid_ctrls = ik_ctrls[average_index]
        attributes_utils.unlock_attributes(mid_ctrls.getParent())
        mdi_ctrl_npo = dag_utils.create_buffer_groups([mid_ctrls])[0]
        p_cons.append(
            pmc.parentConstraint(
                ik_ctrls[-1], ik_ctrls[0], mdi_ctrl_npo, mo=True
            )
        )
        _create_parent_con_average_setup(
            (average_index + 1, len(ik_ctrls) - 1), (ik_ctrls[-1], mid_ctrls)
        )
        _create_parent_con_average_setup(
            (1, average_index), (mid_ctrls, ik_ctrls[0])
        )
        for ci, p_con in enumerate(p_cons):
            p_con.interpType.set(2)
            for i, weight in enumerate(p_con.getWeightAliasList()):
                current_value = weight.get()
                remap_value_nd = pmc.createNode("remapValue", n = "{}_rmv".format(weight))

                host_ctrl.attr(
                    self.SPLINE_IK_SECTION_FOLLOW_ATTR["longName"]
                ).connect(remap_value_nd.inputValue)
                if self.BIRD_NECK:
                    remap_value_nd.outputMax.set(self.BIRD_NECK_WEIGHTS[ci][i])
                else:
                    remap_value_nd.outputMax.set(current_value)
                remap_value_nd.outValue.connect(weight)
        _LOGGER.info("Spline ik setup sub cons follow added.")

    def tweak_head_con(
        self, head_controller, neck_controllers, component_name, head_host
    ):
        """
        Fix the head control space.

        Args:
            head_controller(pmc.PyNode()): The head control.
            neck_controllers(list): The neck controller.
            component_name(str): The head component name.
            head_host(pmc.PyNode()): The head host control.

        """
        last_neck_ik_ctrl = [
            node for node in neck_controllers if "ik" in node.name()
        ][-1]
        head_ik_cns = head_controller.getParent()
        attributes_utils.unlock_attributes(head_ik_cns)
        pr_con = pmc.parentConstraint(last_neck_ik_ctrl, head_ik_cns, mo=True)
        ik_ref_attr = head_host.attr("{}_ikref".format(component_name))
        enums_dic = ik_ref_attr.getEnums()
        keys_list = sorted(enums_dic)
        enums_list = []
        for x in range(len(keys_list)):
            enums_list.append(enums_dic.key(x))
        enums_list.append(self.HEAD_IK_ENUM_NAME)
        pmc.addAttr(ik_ref_attr, edit=True, enumName=":".join(enums_list))
        cond_nd = pmc.createNode("condition")
        pr_con_weight_list = pr_con.getWeightAliasList()
        cond_nd.secondTerm.set(len(pr_con_weight_list) - 1)
        cond_nd.colorIfTrueR.set(1)
        cond_nd.colorIfFalseR.set(0)
        ik_ref_attr.connect(cond_nd.firstTerm)
        cond_nd.outColorR.connect(pr_con_weight_list[-1])
        ik_ref_attr.set(len(enums_list) - 1)
        for axe in "XYZ":
            head_ik_cns.attr("translate{}".format(axe)).disconnect()
        mgattr.lockAttribute(head_ik_cns)
        _LOGGER.info("Head controller tweak succeed.")

    def change_neck_ik_orientation(self, neck_controllers):
        """
        Change the neck ik orientation.

        Args:
            neck_controllers(list): The neck controller objects.

        """
        neck_ik_controls = [node for node in neck_controllers if "_ik" in node.name()][:-1]
        neck_ik_controls = pconv(neck_ik_controls)

        for neck_ik_nd in neck_ik_controls:
            new_trs = rig_utils.exchange_connections_to_new_trs(
                neck_ik_nd, ["controller", "objectSet", "dagPose"]
            )
            rig_utils.switch_mgear_control_orientation(
                neck_ik_nd, **self.NECK_IK_ORIENT_DIC
            )


            npo = dag_utils.create_buffer_groups([neck_ik_nd])[0]
            npo.rename(npo.nodeName().replace("_npo", "_1_npo"))

            neck_ik_nd.addChild(new_trs)

        _LOGGER.info("Neck ik orientation change successful")

    def add_ik_z_rot_option(self):
        """
        Add z rotation option to the neck iks.
        """
        neck_z_rot_dic = paths_utils.get_asset_data_from_json(
            MGEAR_NECK_CUSTOM_SCP_JSON_NAME
        )
        if not neck_z_rot_dic:
            neck_z_rot_dic = self.NECK_Z_ROT_DIC
        neck_z_rot_items = list(neck_z_rot_dic.items())
        for index, item in enumerate(neck_z_rot_items):
            ik_nd = pmc.ls(item[0])
            if ik_nd:
                ik_nd = ik_nd[0]
                keyable_attr = self.NECK_Z_ROT_MULT_KEY_ATTR_NAME
                mgattr.addAttribute(
                    node=ik_nd,
                    longName=keyable_attr,
                    attributeType="float",
                    value=1,
                    minValue=0,
                    maxValue=1,
                )
                for data_dic in item[1]:
                    if pmc.objExists(data_dic.get("ref_node")):
                        ref_nd = pmc.PyNode(data_dic.get("ref_node"))

                        ref_nd=pconv(ref_nd)

                        npo = dag_utils.create_buffer_groups([ref_nd])[0]
                        npo.rename(
                            npo.name().replace("npo", "{}_npo".format(index))
                        )
                        hidden_attr = "{}_{}".format(
                            self.NECK_Z_ROT_MULT_HID_ATTR_NAME,
                            data_dic.get("index"),
                        )
                        mgattr.addAttribute(
                            node=ik_nd,
                            longName=hidden_attr,
                            attributeType=float,
                            value=data_dic.get("mult_value"),
                            minValue=0,
                            maxValue=1,
                            keyable=False,
                        )
                        mult_main = pmc.createNode("math_MultiplyAngle")
                        mult_sub = pmc.createNode("math_MultiplyAngle")
                        ik_nd.attr(
                            "rotate{}".format(
                                self.NECK_Z_ROT_CHANNEL_MAPPING[1]
                            )
                        ).connect(mult_main.input1)
                        ik_nd.attr(keyable_attr).connect(mult_main.input2)
                        ik_nd.attr(hidden_attr).connect(mult_sub.input2)
                        mult_main.output.connect(mult_sub.input1)
                        mult_sub.output.connect(
                            npo.attr(
                                "rotate{}".format(
                                    self.NECK_Z_ROT_CHANNEL_MAPPING[0]
                                )
                            )
                        )
                    else:
                        _LOGGER.warning(
                            f"{data_dic.get('ref_node')} not existing. Can not build the z rotation for that node"
                        )
            else:
                _LOGGER.warning(
                    f"{item[0]} not existing. Will skip the z roattion feature for that node."
                )
        _LOGGER.info("Neck ik control z rotation added.")
