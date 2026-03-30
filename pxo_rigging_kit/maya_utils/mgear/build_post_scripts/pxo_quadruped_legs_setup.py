"""
Custom script to prepare the mgear quadrupad legs to our needs.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import built-in modules
import itertools
from importlib import reload
from pprint import pprint

# Import third-party modules
from future import standard_library

standard_library.install_aliases()
# Import built-in modules
from builtins import str
from builtins import zip
import logging

# Import third-party modules
import mgear.shifter.custom_step as cstp
import pymel.core as pmc

# Import local modules
from pxo_rigging_kit import constants
from pxo_rigging_kit.maya_utils import dag_utils
from pxo_rigging_kit.maya_utils import pymel_utils
from pxo_rigging_kit.maya_utils.mgear import mgear_build_utils
from pxo_rigging_kit.maya_utils.post_and_pre_build import scapula_setup
from pxo_rigging_kit.maya_utils.rigging import rig_utils
reload(scapula_setup)
#######################################################
# GLOBALS
#######################################################

logging.basicConfig(level=logging)
_LOGGER = logging.getLogger(__name__ + ".py")


#######################################################
# CLASSES
#######################################################


class CustomShifterStep(cstp.customShifterMainStep):

    LEG_COMPONENT = "leg"
    FOOT_COMPONENT = "foot_"
    SCAPULA_COMPONENT = "scapula"
    SHOULDER_COMPONENT = "shoulder_"
    SHOULDER_TRANS_COMPONENT = "shoulderTranslate_"
    FINGER_COMPONENT = ("toeIndex_", "toeMiddle_", "toeRing_", "toePinky_",)
    FINGER_CONTROL_COMPONENT = ("toeSplayFront_", "toeSplayBack_")

    HOST_COMPONENT = "Host"

    REPLACE_STRINGS = {
        "fk1": ("bk0", "bk1", "bk2",),
        "ik": ("roll", )
    }

    def __init__(self):
        self.name = "pxo_quadruped_leg_setup"
        self.acting_step_dict = None

        self.host_dag = None
        self.claws_host_dag = None
        self.start_dag = None
        self.end_dag = None

        self.scap_dag = None

        self.shoulder_dag = None
        self.shoulder_translate_dag = None

        self.roll_dag = None
        self.ik_cns_dag = None

        self.joints = None
        self.finger_controls = None
        self.div_dag_mid = None
        self.div_dag_end = None

    def run(self, stepDict):
        self.acting_step_dict = stepDict["mgearRun"]

        # First find the components

        shoulder_component_keys = mgear_build_utils.get_nonhost_components(
                self.acting_step_dict, self.SHOULDER_COMPONENT, self.HOST_COMPONENT
        )

        shoulder_translate_component_keys = mgear_build_utils.get_nonhost_components(
                self.acting_step_dict, self.SHOULDER_TRANS_COMPONENT, self.HOST_COMPONENT
        )

        def sort_by_index(arg):
            return arg.split("_")[1][1]

        grouped_components = list(
                zip(
                        sorted(shoulder_component_keys, key=sort_by_index, reverse=True),
                        sorted(shoulder_translate_component_keys, key=sort_by_index, reverse=True),
                )
        )

        for comp in grouped_components:

            shoulder_dag = mgear_build_utils.get_component_ctrls(
                    self.acting_step_dict, comp[0]
            )
            if shoulder_dag:
                self.shoulder_dag = shoulder_dag[-1]

            shoulder_translate_dag = mgear_build_utils.get_component_ctrls(
                    self.acting_step_dict, comp[1]
            )
            if shoulder_translate_dag:
                self.shoulder_translate_dag = shoulder_translate_dag[-1]

            create_shoulder_aim(self.shoulder_dag, self.shoulder_translate_dag)


def create_shoulder_aim(shoulder_fk, shoulder_translate):
    shoulder_aim = shoulder_fk.getChildren(type="transform")[0]

    shoulder_translate_offset = dag_utils.create_buffer_groups([shoulder_translate])[0]

    rig_utils.pxo_constraining(shoulder_fk,
                               shoulder_translate_offset,
                               maintainOffset=True,
                               name=None,
                               skipRotate=None,
                               skipTranslate=None,
                               skipScale=None,
                               native=False,
                               )

    rig_utils.pxo_constraining(shoulder_translate,
                               shoulder_aim,
                               maintainOffset=True,
                               name=None,
                               skipRotate=None,
                               skipTranslate=None,
                               skipScale=None,
                               native=False,
                               )

