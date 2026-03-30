import mgear.shifter.custom_step as cstp
import pymel.core as pmc
from pymel.core.datatypes import Matrix

class CustomShifterStep(cstp.customShifterMainStep):
    """Custom Step description
    """

    def setup(self):
        """
        Setting the name property makes the custom step accessible
        in later steps.

        i.e: Running  self.custom_step("pxo_clean_sliced")  from steps ran after
             this one, will grant this step.
        """
        self.name = "pxo_clean_sliced"

    def run(self):
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
        pmc.delete(pmc.ls("*:*proxy_geo_parentOffset_mMtx*"))

        for n in pmc.ls("*:*proxy_geo"):
            n.offsetParentMatrix.set(Matrix())

        return
