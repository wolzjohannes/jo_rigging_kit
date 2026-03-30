"""
Custom step to import gSkin data.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import built-in modules
import glob
import logging
import os

# Import third-party modules
from future import standard_library
import mgear.core.skin as mgskin
import mgear.shifter.custom_step as cstp
import pymel.core as pmc

# Import local modules
from pxo_rigging_kit.maya_utils.paths_utils import list_data_dir

standard_library.install_aliases()

##########################################################
# GLOBALS
##########################################################

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)

##########################################################
# FUNCTIONS
##########################################################


class CustomShifterStep(cstp.customShifterMainStep):

    SKINPACK_FILE_TYPE = "gSkinPack"
    G_SKIN_DIR = "gSkin"

    def __init__(self):
        self.name = "import_gSkin_data"
        self.acting_step_dict = None

    def run(self, stepDict):
        # skin pack file extention.
        gSkinPack_type = "*.{}".format(self.SKINPACK_FILE_TYPE)
        g_skin_dir = list_data_dir(pmc.sceneName()).get(self.G_SKIN_DIR, None)
        if not g_skin_dir:
            _LOGGER.warning(
                "No {} folder found in the asset data directory. Abort skin weights import.".format(
                    self.G_SKIN_DIR
                )
            )
            return
        skin_data = glob.glob(os.sep.join([g_skin_dir, gSkinPack_type]))
        # Check if skinPack file exist in dir.
        if not skin_data:
            _LOGGER.warning(
                "No {} file found in {}. Abort skin weights import.".format(
                    gSkinPack_type, g_skin_dir
                )
            )
            return
        # Get the latest skinPack data.
        max_skinPack = max(skin_data, key=os.path.getctime)
        # import mgear gSkin data.
        mgskin.importSkinPack(max_skinPack)
