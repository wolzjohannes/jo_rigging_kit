"""
Custom script to prepare the claws component to our needs.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import third-party modules
from future import standard_library

# Import built-in modules
import logging
from itertools import chain

# Import third-party modules
import pymel.core as pmc
import mgear.shifter.custom_step as cstp

# Import local modules
from pxo_rigging_kit.maya_utils.rigging import rig_utils
from pxo_rigging_kit.maya_utils import dag_utils
from pxo_rigging_kit.maya_utils.mgear import mgear_build_utils
from pxo_rigging_kit.maya_utils import attributes_utils
from pxo_rigging_kit.maya_utils.maya_conversion_utils import pymaya_to_pymel as pconv


standard_library.install_aliases()

#######################################################
# GLOBALS
#######################################################

logging.basicConfig(level=logging)
_LOGGER = logging.getLogger(__name__ + ".py")

#######################################################
# FUNCTIONS
#######################################################


def _get_claw_type_from_comp(comp_obj):
    """
    Get the claw type from mgear component object.

    Args:
        comp_obj(mgear python object): The component object.

    Returns:
        String: The claw type.

    """
    claw_type = comp_obj.name.split("Claw")[0]
    for leg_type in ["front", "hind"]:
        if leg_type in claw_type:
            claw_type = claw_type.replace(leg_type, "")
            claw_type.lower()
    return claw_type


#######################################################
# CLASSES
#######################################################


class CustomShifterStep(cstp.customShifterMainStep):

    CLAW_COMPONENT = "Claw_"
    CLAW_NAILS_COMPONENTS = "ClawNail_"
    LEG_COMPONENT = "leg_"
    CLAW_IK_ENUM_NAME = "leg_ik"
    THUMB_COMPONENT = "thumb"
    CLAW_ATTR_CONNECT_ANGLES_DICT = {
        "claw_spread": "Y",
        "claw_shifting": "Y",
        "claw_curl": "Z",
        "claw_curl_nice_A": "Z",
        "claw_curl_nice_B": "Z",
        "claw_pressure": "Z",
    }
    MULT_ATTR_VALUES_DICT = {
        "claw_spread": {
            "index": -0.5,
            "middle": 0.0,
            "ring": 0.5,
            "pinky": 0.5,
            "thumb": 0.0
        },
        "claw_curl": {"index": 0.5, "middle": 0.5, "ring": 0.5, "pinky": 0.5,"thumb": 0.5},
        "claw_curl_nice_A": {
            "index": 0.25,
            "middle": 0.5,
            "ring": 0.5,
            "pinky": 0.75,
            "thumb": 0.5
        },
        "claw_curl_nice_B": {
            "index": 0.75,
            "middle": 0.5,
            "ring": 0.5,
            "pinky": 0.25,
            "thumb": 0.5
        },
        "claw_shifting": {
            "index": 0.5,
            "middle": 0.5,
            "ring": 0.5,
            "pinky": 0.5,
            "thumb": 0.5
        },
        "claw_pressure": {
            "index": 0.5,
            "middle": 0.5,
            "ring": 0.5,
            "pinky": 0.5,
            "thumb": 0.5
        },
    }
    MULT_SEC_ATTR_LIST = [
        "claw_curl",
        "claw_curl_nice_A",
        "claw_curl_nice_B",
        "claw_pressure",
    ]

    def __init__(self):
        self.name = "pxo_leg_claws_setup"
        self.acting_step_dict = None
        self.claw_attributes_list = [
            {"longName": "claw_spread", "type": "doubleAngle", "keyable": True},
            {"longName": "claw_curl", "type": "doubleAngle", "keyable": True},
            {
                "longName": "claw_curl_nice_A",
                "type": "doubleAngle",
                "keyable": True,
            },
            {
                "longName": "claw_curl_nice_B",
                "type": "doubleAngle",
                "keyable": True,
            },
            {
                "longName": "claw_shifting",
                "type": "doubleAngle",
                "keyable": True,
            },
            {
                "longName": "claw_pressure",
                "type": "doubleAngle",
                "keyable": True,
            },
        ]

    def run(self, stepDict):
        self.acting_step_dict = stepDict["mgearRun"]
        claw_component_keys = mgear_build_utils.get_nonhost_components(
            self.acting_step_dict, self.CLAW_COMPONENT
        )
        leg_component_keys = mgear_build_utils.get_nonhost_components(
            self.acting_step_dict, self.LEG_COMPONENT
        )
        claw_nail_component_keys = mgear_build_utils.get_nonhost_components(
            self.acting_step_dict, self.CLAW_NAILS_COMPONENTS
        )
        for comp_key in claw_component_keys + claw_nail_component_keys:
            name = mgear_build_utils.get_component_name(
                self.acting_step_dict, comp_key
            )
            index = mgear_build_utils.get_component_index(
                self.acting_step_dict, comp_key
            )
            controllers = mgear_build_utils.get_component_ctrls(
                self.acting_step_dict, comp_key
            )
            side = mgear_build_utils.get_component_side(
                self.acting_step_dict, comp_key
            )
            leg_controllers = list(
                chain.from_iterable(
                    [
                        mgear_build_utils.get_component_ctrls(
                            self.acting_step_dict, leg_comp_key
                        )
                        for leg_comp_key in leg_component_keys
                        if mgear_build_utils.get_component_side(
                            self.acting_step_dict, leg_comp_key
                        )
                        == side
                    ]
                )
            )
            host = mgear_build_utils.get_host_from_component(
                self.acting_step_dict, comp_key
            )
            self.tweak_claw_ik_spaces(
                controllers, leg_controllers, host, name, side, index
            )
        claw_comp_dict = {"L": [], "R": []}
        for claw_comp_key in claw_component_keys:
            claw_component = mgear_build_utils.get_component_object(
                self.acting_step_dict, claw_comp_key
            )
            side = mgear_build_utils.get_component_side(
                self.acting_step_dict, claw_comp_key
            )
            if side in claw_comp_dict:
                data_dict = {
                    "claw_comp": claw_component,
                    "claw_ui_host": mgear_build_utils.get_host_from_component(
                        self.acting_step_dict, claw_comp_key
                    ),
                }
                data_list = claw_comp_dict.get(side)
                data_list.append(data_dict)
                claw_comp_dict[side] = data_list
        for item in list(claw_comp_dict.items()):
            for data_dict_ in item[1]:
                # Create the claw attributes per side.
                self.create_claw_attributes(
                    data_dict_.get("claw_comp"),
                    data_dict_.get("claw_ui_host"),
                    "claw_",
                )
        for item_ in list(claw_comp_dict.items()):
            for data_dict__ in item_[1]:
                self.create_claw_attributes_connections(
                    data_dict__.get("claw_comp"),
                    data_dict__.get("claw_ui_host"),
                    "claw_",
                )

    def create_claw_attributes(self, comp_obj, comp_host, attr_suffix=""):
        """
        Create the claw attributes to the comp_host.

        Args:
            comp_obj(mgear python object): The component object.
            comp_host(pmc.PyNode()): The component host.
            attr_suffix(str, optional): If you want a attribute suffix.

        """
        fk_controls = [
            ctrl
            for ctrl in comp_obj.groups.get("controllers")
            if "_fk" in ctrl.name()
        ]
        claw_typ = _get_claw_type_from_comp(comp_obj)
        for attr__ in self.claw_attributes_list:
            fk_section_range = 1
            if attr__.get("longName") in self.MULT_SEC_ATTR_LIST:
                fk_section_range = len(fk_controls)

            for fk_sect in range(fk_section_range):
                mult_attr_name = "{}{}_{}_fk{}_mult_factor".format(
                    attr_suffix, attr__.get("longName"), claw_typ, fk_sect
                )
                mult_value = 1
                mult_value_dict = self.MULT_ATTR_VALUES_DICT.get(
                    attr__.get("longName")
                )
                if mult_value_dict:
                    if claw_typ in mult_value_dict:
                        mult_value = mult_value_dict.get(claw_typ)

                if not comp_host.hasAttr(mult_attr_name):
                    comp_host.addAttr(
                        mult_attr_name,
                        type="float",
                        keyable=False,
                        max=1,
                        min=-1,
                        dv=mult_value,
                    )
        if not comp_host.hasAttr("clawAttr"):
            attributes_utils.add_pxo_separator_attr(comp_host, "clawAttr")
        for attr_ in self.claw_attributes_list:
            try:
                pmc.addAttr(comp_host, **attr_)
            except:
                continue

    def create_claw_attributes_connections(
        self, comp_obj, comp_host, attr_suffix=""
    ):
        """
        Setup up the claw control on the host control for a nicer claw control.

        Args:
            comp_obj(mgear python object): The component object.
            comp_host(pmc.PyNode()): The component host.
            attr_suffix(str, optional): If you want a attribute suffix.

        """
        fk_controls = [
            ctrl
            for ctrl in comp_obj.groups.get("controllers")
            if "_fk" in ctrl.name()
        ]
        claw_typ = _get_claw_type_from_comp(comp_obj)
        claw_attr_connect_angles_dict = self.CLAW_ATTR_CONNECT_ANGLES_DICT
        for attr_data_dict in self.claw_attributes_list:
            fk_section_range = 1
            if attr_data_dict.get("longName") in self.MULT_SEC_ATTR_LIST:
                fk_section_range = len(fk_controls)
            for fk_sect in range(fk_section_range):
                mult_attr_name = "{}{}_{}_fk{}_mult_factor".format(
                    attr_suffix,
                    attr_data_dict.get("longName"),
                    claw_typ,
                    fk_sect,
                )

                buffer_grp = rig_utils.create_buffer_groups(
                    [pmc.PyNode(fk_controls[fk_sect].name())],#2025
                    f"{attr_data_dict.get('longName')}_grp",
                )[0]
                mult_angle_nd = pmc.createNode("math_MultiplyAngle")
                comp_host.attr(attr_data_dict.get("longName")).connect(
                    mult_angle_nd.input1
                )
                comp_host.attr(mult_attr_name).connect(mult_angle_nd.input2)
                mult_angle_nd.output.connect(
                    buffer_grp.attr(
                        "rotate{}".format(
                            claw_attr_connect_angles_dict.get(
                                attr_data_dict.get("longName")
                            )
                        )
                    )
                )

    def tweak_claw_ik_spaces(
        self,
        controllers,
        leg_controls,
        host_control,
        component_name,
        component_side,
        component_index,
    ):
        """
        At al claw iks a new space for the leg ik.

        Args:
            controllers(list): The claw controllers.
            leg_controls(list): The leg controllers.
            host_control(pmc.PyNode()): The host component.
            component_name(str): The claw component name.
            component_side(str): The claw component side.
            component_index(int): The claw component index.

        """
        try:
            ikcns_ctrl = [
                node for node in controllers if "ikcns" in node.name()
            ][0]
        except:
            _LOGGER.warning(
                "No `ikcns` nodes exist in {}. Will abort this step.".format(
                    controllers
                )
            )
            return
        ikcns_ctrl_cns = ikcns_ctrl.getParent()
        leg_ik_ctrl = [node for node in leg_controls if "_ik_" in node.name()][
            0
        ]
        pr_con = pmc.parentConstraint(leg_ik_ctrl, ikcns_ctrl_cns, mo=True)
        ik_ref_attr = host_control.attr("{}_ikref".format(component_name))
        enums_str = pmc.attributeQuery(
            ik_ref_attr.name(includeNode=False),
            node=ik_ref_attr.node(),
            listEnum=True,
        )[0]
        pmc.addAttr(
            ik_ref_attr,
            edit=True,
            enumName=":".join([enums_str, self.CLAW_IK_ENUM_NAME]),
        )
        cond_nd = pmc.createNode("condition")
        pr_con_weight_list = pr_con.getWeightAliasList()
        cond_nd.secondTerm.set(len(pr_con_weight_list) - 1)
        cond_nd.colorIfTrueR.set(1)
        cond_nd.colorIfFalseR.set(0)
        ik_ref_attr.connect(cond_nd.firstTerm)
        cond_nd.outColorR.connect(pr_con_weight_list[-1])
        ik_ref_attr.set(len(enums_str.split(":")))
        _LOGGER.info(
            "Foot claw tweak for {}_{}{} succeed.".format(
                component_name, component_side, component_index
            )
        )
