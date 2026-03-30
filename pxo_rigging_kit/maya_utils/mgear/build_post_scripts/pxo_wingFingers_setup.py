"""
Custom script to prepare the fingers component to our needs.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import built-in modules

# Import third-party modules
from future import standard_library

# Import built-in modules
import logging

# Import third-party modules
import mgear.shifter.custom_step as cstp
import pymel.core as pmc

# Import local modules
from pxo_rigging_kit.maya_utils import dag_utils
from pxo_rigging_kit.maya_utils.mgear import mgear_build_utils
from pxo_rigging_kit.maya_utils import paths_utils
from pxo_rigging_kit.maya_utils import attributes_utils
from pxo_rigging_kit.maya_utils.maya_conversion_utils import pymaya_to_pymel as pconv

standard_library.install_aliases()

#######################################################
# GLOBALS
#######################################################

logging.basicConfig(level=logging)
_LOGGER = logging.getLogger(__name__ + ".py")
WING_FINGER_SPREAD_JSON_NAME = "wingFinger_spread.json"

#######################################################
# CLASSES
#######################################################


class CustomShifterStep(cstp.customShifterMainStep):

    COMPONENT = "wingFinger_"
    ROOT_FINGERS_COMPONENT = "rootFingers_"
    ARM_COMP = "arm"
    SPREAD_SET_DRIVEN_KEY_DIC = {
        "first": [
            {
                1: [
                    {"time": 0, "value": 0},
                    {"time": -82, "value": -10.225},
                    {"time": 82, "value": 21.220},
                    {"time": 164, "value": 33.199},
                ],
                2: [
                    {"time": 0, "value": 0},
                    {"time": -82, "value": -25.063},
                    {"time": 82, "value": 39.547},
                    {"time": 164, "value": 48.885},
                ],
                3: [
                    {"time": 0, "value": 0},
                    {"time": -82, "value": -36.869},
                    {"time": 82, "value": 61.739},
                    {"time": 164, "value": 69.656},
                ],
                4: [
                    {"time": 0, "value": 0},
                    {"time": -82, "value": -46.745},
                    {"time": 82, "value": 78.206},
                    {"time": 164, "value": 84.221},
                ],
                "axe": "ry",
            }
        ],
        "middle": [
            {
                0: [
                    {"value": -51.83532549454674, "time": -116.0},
                    {"value": -36.0, "time": -58.0},
                    {"value": 0.0, "time": 0.0},
                    {"value": 46.57251749835597, "time": 58.0},
                ],
                1: [
                    {"value": -28.883128812868062, "time": -116.0},
                    {"value": -18.0, "time": -58.0},
                    {"value": 0.0, "time": 0.0},
                    {"value": 22.209801009978367, "time": 58.0},
                ],
                3: [
                    {"value": 35.16613466250465, "time": -116.0},
                    {"value": 24.000000000000004, "time": -58.0},
                    {"value": 0.0, "time": 0.0},
                    {"value": -21.987765778581572, "time": 58.0},
                ],
                4: [
                    {"value": 62.40562474960514, "time": -116.0},
                    {"value": 43.0, "time": -58.0},
                    {"value": 0.0, "time": 0.0},
                    {"value": -40.67209950379921, "time": 58.0},
                ],
                "axe": "ry",
            }
        ],
        "last": [
            {
                0: [
                    {"value": 52.31869448248603, "time": -140.0},
                    {"value": 0.0, "time": 0.0},
                    {"value": -77.87461948729592, "time": 140.0},
                    {"value": -94.05646829335286, "time": 280.0},
                ],
                1: [
                    {"value": 47.01851386472731, "time": -140.0},
                    {"value": 0.0, "time": 0.0},
                    {"value": -57.555357698205064, "time": 140.0},
                    {"value": -78.77838465898023, "time": 280.0},
                ],
                2: [
                    {"value": 25.148555798425402, "time": -140.0},
                    {"value": 0.0, "time": 0.0},
                    {"value": -41.47160951409943, "time": 140.0},
                    {"value": -64.195329525249, "time": 280.0},
                ],
                3: [
                    {"value": 16.094150068158058, "time": -140.0},
                    {"value": 0.0, "time": 0.0},
                    {"value": -18.597299049879066, "time": 140.0},
                    {"value": -37.066644035093844, "time": 280.0},
                ],
                "axe": "ry",
            },
            {
                0: [
                    {"value": 0.0, "time": -140.0},
                    {"value": 0.0, "time": 0.0},
                    {"value": 2.8180016088866258, "time": 140.0},
                ],
                1: [
                    {"value": 0.0, "time": -140.0},
                    {"value": 0.0, "time": 0.0},
                    {"value": 40.85275170819793, "time": 140.0},
                ],
                2: [
                    {"value": 0.0, "time": -140.0},
                    {"value": 0.0, "time": 0.0},
                    {"value": 68.69091939174643, "time": 140.0},
                ],
                3: [
                    {"value": 0.0, "time": -140.0},
                    {"value": 0.0, "time": 0.0},
                    {"value": 74.82845333751689, "time": 140.0},
                ],
                "axe": "tz",
            },
        ],
    }
    SPREAD_FINGER_ATTRS = [
        (
            "first",
            {
                "longName": "fingers_spread_from_first",
                "niceName": "spread_from_first",
                "attributeType": "float",
                "keyable": True,
            },
        ),
        (
            "middle",
            {
                "longName": "fingers_spread_from_middle",
                "niceName": "spread_from_middle",
                "attributeType": "float",
                "keyable": True,
            },
        ),
        (
            "last",
            {
                "longName": "fingers_spread_from_last",
                "niceName": "spread_from_last",
                "attributeType": "float",
                "keyable": True,
            },
        ),
    ]

    def __init__(self):
        self.name = "pxo_wingFingers_setup"
        self.acting_step_dict = None

    def run(self, stepDict):
        print(stepDict["mgearRun"])
        self.acting_step_dict = stepDict["mgearRun"]
        wing_fingers_comps = mgear_build_utils.get_nonhost_components(
            self.acting_step_dict, self.COMPONENT
        )
        root_finger_comps = mgear_build_utils.get_nonhost_components(
            self.acting_step_dict, self.ROOT_FINGERS_COMPONENT
        )

        host_components = mgear_build_utils.get_host_component(
            self.acting_step_dict, self.ARM_COMP
        )

        arm_hosts = []
        for comp_key in host_components:
            side = mgear_build_utils.get_component_side(
                self.acting_step_dict, comp_key
            )

            all_ctrls = mgear_build_utils.get_component_ctrls(
                self.acting_step_dict, comp_key
            )
            first_ctrl = all_ctrls[0]

            arm_hosts.append((side, first_ctrl))

        arm_hosts=pconv(arm_hosts) #2025

        set_driven_key_dict = paths_utils.get_asset_data_from_json(
            WING_FINGER_SPREAD_JSON_NAME
        )
        if not set_driven_key_dict:
            set_driven_key_dict = self.SPREAD_SET_DRIVEN_KEY_DIC
        for arm_host_tpl in arm_hosts:
            attributes_utils.add_pxo_separator_attr(
                arm_host_tpl[1], "fingersAttrs"
            )
            # add the spread attributes
            self._add_spread_attributes(arm_host_tpl[1])
        for comp_key in wing_fingers_comps:
            index = mgear_build_utils.get_component_index(
                self.acting_step_dict, comp_key
            )
            side = mgear_build_utils.get_component_side(
                self.acting_step_dict, comp_key
            )
            fk_npos = mgear_build_utils.get_component_fk_npos(
                self.acting_step_dict, comp_key
            )

            host = [obj_tpl[1] for obj_tpl in arm_hosts if obj_tpl[0] == side][0]
            # Create the spread setup
            for key, value in set_driven_key_dict.items():
                for data_dict in value:
                    self.create_spread_setup(
                        host,
                        index,
                        side,
                        fk_npos,
                        self.SPREAD_FINGER_ATTRS,
                        data_dict,
                        key,
                    )
        for root_finger_comp_key in root_finger_comps:
            root_fingers_comp_side = mgear_build_utils.get_component_side(
                self.acting_step_dict, root_finger_comp_key
            )
            root_fingers_comp_name = mgear_build_utils.get_component_name(
                self.acting_step_dict, root_finger_comp_key
            )
            root_fingers_comp_index = mgear_build_utils.get_component_index(
                self.acting_step_dict, root_finger_comp_key
            )
            root_fingers_host_component = (
                mgear_build_utils.get_host_from_component(
                    self.acting_step_dict, root_finger_comp_key
                )
            )
            root_fingers_control = mgear_build_utils.get_component_ctrls(
                self.acting_step_dict, root_finger_comp_key
            )[0]
            self.edit_root_fingers_ikref(
                root_fingers_host_component,
                root_fingers_control,
                root_fingers_comp_name,
                root_fingers_comp_side,
                root_fingers_comp_index,
            )

    def _add_spread_attributes(self, arm_host):
        for data_tpl in self.SPREAD_FINGER_ATTRS:
            attributes_utils.add_attribute_to_node_by_dict(
                arm_host, data_tpl[1]
            )

    def create_spread_setup(
        self,
        host,
        comp_index,
        comp_side,
        fk_npos,
        spread_finger_attr_list,
        set_driven_key_dict,
        spread_type,
    ):
        """
        Create the spread setup.

        Args:
            host(pmc.PyNode()): The host control.
            comp_index(int): The component index.
            comp_side(str): The component side.
            fk_npos(list): The component fk npo nodes.
            spread_finger_attr_list(list): This dic includes the attr
                                         longNames on the host control
                                         for further use.
            set_driven_key_dict(dic): This dic includes the set driven key values.
            spread_type(str): The spread type.

        """

        fk_npo = [node for node in fk_npos if "fk0" in node.name()]
        spread_finger_attr_dic = [
            data_tpl[1]
            for data_tpl in spread_finger_attr_list
            if data_tpl[0] == spread_type
        ][0]
        if comp_index in set_driven_key_dict:
            set_driven_key_list = set_driven_key_dict.get(comp_index)
            npo_new_name = f"spread_from_{spread_type}_grp"
            if not pmc.objExists(npo_new_name):
                npo = dag_utils.create_buffer_groups(fk_npo, npo_new_name)[0]
            else:
                npo = pmc.PyNode(npo_new_name)

            for data_dic in set_driven_key_list:

                pmc.setDrivenKeyframe(
                    npo.attr(
                        set_driven_key_dict.get("axe"),
                    ),
                    cd=host.attr(spread_finger_attr_dic.get("longName")),
                    dv=data_dic.get("time"),
                    v=data_dic.get("value"),
                )

            _LOGGER.info(
                f"Spread finger from {spread_type} setup created for {comp_side}_wingFinger_{comp_index}"
            )

    def edit_root_fingers_ikref(
        self, host, control, comp_name, comp_side, comp_index
    ):
        """
        Edit the root fingers_ikref so that is just a space in orientation and skip postion.

        Args:
            host(pmc.PyNode()): The root fingers host control.
            control(pmc.PyNode()): The root fingers control.
            comp_name(str): The component name.
            comp_side(str): The component side.
            comp_index(int): The component index.

        """
        cns_node = control.getParent()
        p_con = cns_node.getChildren(type="parentConstraint")[0]
        for axe in "XYZ":
            cns_node.attr("translate{}".format(axe)).unlock()
            p_con.attr("constraintTranslate{}".format(axe)).disconnect()
        finger_ikref_attr = host.attr("{}_ikref".format(comp_name))
        cns_node.translate.lock()
        attributes_utils.edit_enum_attr(finger_ikref_attr, append_="Auto")
        _LOGGER.info(
            "Edit spaces of {}_{}_{} successful.".format(
                comp_name, comp_side, comp_index
            )
        )
