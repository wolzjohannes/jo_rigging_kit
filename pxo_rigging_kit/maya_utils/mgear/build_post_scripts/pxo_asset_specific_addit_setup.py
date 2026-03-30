"""
Custom step to run asset specific custom steps located in the asset data folder.
Each custom step needs a specific declaration. You can find the declaration in this variable:
>>> from pxo_rigging_kit.constants import ADDIT_SCRIPTS_DECLA_NAME
The additional custom script file needs to have a derivate of the:
>>> from pxo_rigging_kit.maya_utils.mgear.mgear_build_utils import AssetBuildAddition
This class has a run() method this run method will be executed.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import built-in modules
import logging
import sys
import importlib.util


# Import third-party modules
from future import standard_library
import mgear.shifter.custom_step as cstp
import pymel.core as pmc

# Import local modules
from pxo_rigging_kit.maya_utils import paths_utils
from pxo_rigging_kit.constants import WILDCARD
from pxo_rigging_kit.constants import ADDIT_SCRIPTS_DECLA_NAME

standard_library.install_aliases()

##########################################################
# GLOBALS
##########################################################

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)

##########################################################
# CLASSES
##########################################################


class CustomShifterStep(cstp.customShifterMainStep):
    def __init__(self):
        self.name = "pxo_asset_specific_addit_setup"
        self.acting_step_dict = None

    def run(self, stepDict):
        self.acting_step_dict = stepDict["mgearRun"]
        run_additional_scripts(self.acting_step_dict)


def run_additional_scripts(acting_step_dict):
    """
    Run all additional scripts found in the asset data directory in a serial loop.
    All scripts which have the same additional declaration in the name will be found.
    The file name decalration is definite in this variable:
    constants.ADDIT_SCRIPTS_DECLA_NAME.

    Args:
        acting_step_dict(dict): The mgear step dictionary.

    """
    list_asset_data_dir = paths_utils.list_data_dir(pmc.sceneName())

    additional_scripts = [
        (key, path)
        for (key, path) in list_asset_data_dir.items()
        if key.startswith(ADDIT_SCRIPTS_DECLA_NAME.split(WILDCARD)[0])
           and key.endswith(ADDIT_SCRIPTS_DECLA_NAME.split(WILDCARD)[-1])
    ]

    if not additional_scripts:
        _LOGGER.info("No additional scripts found. Will skip")
        return

    for module, path in additional_scripts:
        module = module.split(".")[0]
        spec = importlib.util.spec_from_file_location(module, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[module] = mod
        spec.loader.exec_module(mod)
        pxo_addit_class = mod.AssetAddition(acting_step_dict)
        _LOGGER.info(f"Run asset additional script: {module}")
        pxo_addit_class.run()


