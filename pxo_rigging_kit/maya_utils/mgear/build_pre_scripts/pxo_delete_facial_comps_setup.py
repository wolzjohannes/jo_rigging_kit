# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import built-in modules
import logging

# Import third-party modules
from future import standard_library
import maya.cmds as cmds
import mgear.shifter.custom_step as cstp

#######################################################
# GLOBALS
#######################################################
standard_library.install_aliases()

logging.basicConfig(level=logging)
_LOGGER = logging.getLogger(__name__ + ".py")

#######################################################
# CLASSES
#######################################################


class CustomShifterStep(cstp.customShifterMainStep):

    """
    Will delete face specific components before the build.
    """

    FACE_FACS_COMP = "face_ui_C0_root"
    FACE_TWEAKERS_DUMMY = "faceTweakerDummy_C0_root"
    FACE_TWEAKERS_ROOT = "faceTweakerCollect_C0_root"

    def __init__(self):
        self.name = "pxo_delete_facial_comps_setup"

    def run(self, stepDict):
        try:
            cmds.delete(self.FACE_FACS_COMP)
        except:
            pass
        try:
            cmds.delete(self.FACE_TWEAKERS_DUMMY)
        except:
            pass
        try:
            cmds.delete(self.FACE_TWEAKERS_ROOT)
        except:
            pass