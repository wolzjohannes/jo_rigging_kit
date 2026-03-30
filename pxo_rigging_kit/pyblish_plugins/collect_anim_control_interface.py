"""
Collect the anim controller interface and its corresponding attributes
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Import third-party modules
from future import standard_library
from pyblish import api as pyblish_api

# Import local modules
from pxo_rigging_kit.maya_utils.rigging import rig_utils

standard_library.install_aliases()


class CollectAnimControllerInterface(pyblish_api.InstancePlugin):
    """Collect the anim controller interface and its corresponding attributes"""

    offset = 0.47
    order = pyblish_api.CollectorOrder + offset
    label = "Collect Anim Controller Interface"
    families = ["rig"]
    hosts = ["maya"]
    targets = ["local"]

    def process(self, instance):
        """Discover and collect animation controller attributes into the context.

        Args:
            instance (pyblish.api.Instance): Instance object passed down from
                Pyblish.

        """
        anim_control_interface = rig_utils.get_anim_control_interface()
        anim_controls_interface_attributes = rig_utils.get_anim_interface_attributes(
            anim_control_interface
        )
        instance.data["AnimControllerInterface"] = anim_control_interface
        instance.data[
            "AnimControllerInterfaceAttributes"
        ] = anim_controls_interface_attributes
        self.log.info(
            "{0} controllers and there attributes collected.".format(
                len(anim_controls_interface_attributes)
            )
        )
