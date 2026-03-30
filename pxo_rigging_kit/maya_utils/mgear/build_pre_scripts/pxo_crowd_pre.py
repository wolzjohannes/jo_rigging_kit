"""
Custom script to prepare the mgear quadrupad legs to our needs.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import built-in modules
import logging
import itertools

# Import third-party modules
from future import standard_library
from maya import cmds
import mgear.shifter.custom_step as cstp

# Import local modules
from pxo_rigging_kit.maya_utils.mgear import mgear_build_utils

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

    """

    def __init__(self):
        self.name = "pxo_crowd_pre"

        self.limbs = ("arm", "leg")

        self.sides = ("R", "L", "C")
        self.max_expected_subdivs = 20

    def run(self, stepDict):

        limb_templates = mgear_build_utils.construct_component_templates(limbs=self.limbs,
                                                                         sides=self.sides,
                                                                         )

        limb_items = [cmds.ls(f"{limb_template}*_root")
                      for limb_template in limb_templates
                      if cmds.ls(f"{limb_template}*_root")
                      ]

        all_roots_flattened = set(itertools.chain.from_iterable(limb_items))

        all_attributes = [cmds.ls(f"{limb_root}.div{str(iteration_)}")
                          for iteration_ in range(0, self.max_expected_subdivs)
                          for limb_root in all_roots_flattened
                          if cmds.ls(f"{limb_root}.div{str(iteration_)}")
                          ]

        all_attributes_flattened = set(itertools.chain.from_iterable(all_attributes))

        [cmds.setAttr(attribute_flattened, 0) for attribute_flattened in all_attributes_flattened]

        _LOGGER.info("all divs set to zero")