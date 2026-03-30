from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library

import logging
import pymel.core as pmc
import mgear.shifter.custom_step as cstp
from pxo_rigging_kit.constants import PXO_ROOT_SET_NAME
from pxo_rigging_kit.constants import PXO_CONTROLS_SET_NAME
from pxo_rigging_kit.constants import PXO_DEFORMERS_SET_NAME
from pxo_rigging_kit.constants import PXO_COMPONENTS_ROOT_SET_NAME

standard_library.install_aliases()


#######################################################
# GLOBALS
#######################################################

logging.basicConfig(level=logging)
_LOGGER = logging.getLogger(__name__ + ".py")

#######################################################
# CLASSES
#######################################################


class CustomShifterStep(cstp.customShifterMainStep):
    """Custom Step description"""

    PXO_ROOT_SET_NAME = PXO_ROOT_SET_NAME
    CONTROLLERS_SET_NAME = PXO_CONTROLS_SET_NAME
    DEFORMERS_SET_NAME = PXO_DEFORMERS_SET_NAME
    COMPONENT_ROOT_SET_NAME = PXO_COMPONENTS_ROOT_SET_NAME

    def __init__(self):
        self.name = "pxo_rig_sets_setup"

    def run(self, stepDict):
        """Run method.

            i.e:  self.mgear_run.global_ctl
                gets the global_ctl from shifter rig build base

            i.e:  self.component("control_C0").ctl
                gets the ctl from shifter component called control_C0

            i.e:  self.custom_step("otherCustomStepName").ctlMesh
                gets the ctlMesh from a previous custom step called
                "otherCustomStepName"

        Returns:
            None: None
        """
        # Get all selection sets
        rig = stepDict["mgearRun"].model

        for node_name in [
            self.PXO_ROOT_SET_NAME,
            self.CONTROLLERS_SET_NAME,
            self.DEFORMERS_SET_NAME,
            self.COMPONENT_ROOT_SET_NAME,
        ]:
            pmc.delete(pmc.ls(f"{node_name}*", sets=True))

        (
            top_set,
            controllers_set,
            component_roots_set,
            deformers_set,
        ) = rig.rigGroups.inputs()[0:4]

        top_set.rename(self.PXO_ROOT_SET_NAME)
        controllers_set.rename(self.CONTROLLERS_SET_NAME)
        component_roots_set.rename(self.COMPONENT_ROOT_SET_NAME)
        deformers_set.rename(self.DEFORMERS_SET_NAME)
