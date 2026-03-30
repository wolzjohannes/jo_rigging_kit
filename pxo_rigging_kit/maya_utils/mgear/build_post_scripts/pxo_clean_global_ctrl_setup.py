from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
import pymel.core as pmc
import mgear.shifter.custom_step as cstp
import mgear.core.attribute as mgattr
import logging

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
    """Custom Step description
    """
    GLOBAL_CTRL_NAME = "global_0*_ctrl"

    def __init__(self):
        self.name = "pxo_clean_global_ctrl_setup"

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
        global_con = pmc.ls(self.GLOBAL_CTRL_NAME)
        self.finish_global_con(global_con[0])

    def finish_global_con(self, global_con):
        """
        Finish the global control.

        Args:
            global_con(pmc.PyNode()): The global control.

        """
        unused_attr = [
            attr_
            for attr_ in global_con.listAttr(ud=True)
            if attr_.type() == "enum"
        ]
        for attr__ in unused_attr:
            attr__.unlock()
            attr__.delete()

        if not global_con.hasAttr("main_scale"):
            global_con.addAttr(
                "main_scale",
                typ="float",
                keyable=True,
                minValue=0.01,
                defaultValue=1,
            )
        mgattr.unlockAttribute(global_con, ["sx", "sy", "sz"])
        for axe in "XYZ":
            global_con.main_scale.connect(
                    global_con.attr("scale{}".format(axe)), f=True
                )
        mgattr.lockAttribute(global_con, ["sx", "sy", "sz"])
        _LOGGER.info("Finish global control succeed.")
