"""Extend the default `BaseMayaActions` hooks for the anim curve laoding.

Default `BaseMayaActions` hooks can be found in the built package at:
    {build_root}/build_output/bundle_cache/app_store/tk-multi-loader2/v1.19.2/
        hooks/tk-maya_actions
    Under the name `MayaActions`.

"""
# Import built-in modules.
import os
import logging

# Import third-party modules.
import sgtk  # pylint: disable=import-error
from studiolibrarymaya import animitem

# Import local modules.
from pxo_rigging_kit.maya_utils.rigging import rig_utils

_LOGGER = logging.getLogger(__name__ + ".py")
BaseMayaActions = sgtk.get_hook_baseclass()
NAME = "name"
P_RAMETERS = "params"
CAPTION = "caption"
DESCRIPTION = "description"


class MayaActions(BaseMayaActions):
    """Override and extend `BaseMayaActions`.

    Super class `BaseMayaActions` hooks can be found at:
    `{build_root}/build_output/bundle_cache/git/tk-maya.git/v1.0.1/hooks
    /tk-multi-loader2/tk-maya_actions`.

    """

    # Ignore `C901:` This module must be refactored, is too complex.
    def generate_actions(
        self, sg_publish_data, actions, ui_area
    ):  # noqa: WPS213, C901
        """See superclass method.

        Args:
            sg_publish_data (dict): Shotgun data dictionary with all the
                standard publish fields.
            actions (list of str): List of action strings which have been
                defined in the app configuration.
            ui_area (str): String denoting the UI Area (see superclass).

        Returns:
            (list of dict): each with keys name, params, caption and
                description.

        """
        action_instances = super(MayaActions, self).generate_actions(
            sg_publish_data, actions, ui_area
        )
        if "import_studio_library_anim" in actions:
            action_instances.append(
                {
                    NAME: "import_studio_library_anim",
                    P_RAMETERS: None,
                    CAPTION: "Import studio library anim.",
                    DESCRIPTION: "Will import studio library anim curves and replace all in the scene.",  # noqa: E501
                }
            )

        if "load_lod_rig" in actions:
            action_instances.append(
                {
                    NAME: "load_lod_rig",
                    P_RAMETERS: None,
                    CAPTION: "Load LOD Rig",
                    DESCRIPTION: "Create a pxoReference node as rig container with proxy level"
                                 " rigs of the selected rig into the current scene.",  # noqa: E501
                }
            )

        # Sort actions based on `actions`, as defined in the Loader config.
        return sorted(
            action_instances, key=lambda action: actions.index(action[NAME])
        )

    def execute_action(self, name, params, sg_publish_data):
        """See superclass.

        Args:
            name (str): Action name representing one of the items returned by
                `generate_actions`.
            params (dict): Params data, as specified by `generate_actions`.
            sg_publish_data (dict): Shotgun data dictionary with all the
                standard publish fields.

        """
        self.parent.log_debug("Execute action called for action %s. " % name)
        self.parent.log_debug("Parameters: %s." % params)
        self.parent.log_debug("Publish Data: %s" % sg_publish_data)

        path = self.get_publish_path(sg_publish_data).replace(os.path.sep, "/")

        if not os.path.exists(path):
            raise IOError(f"File not found on disk - '{path}")

        sgid = sg_publish_data["id"]

        if name == "import_studio_library_anim":
            namespace = "{}:".format(sg_publish_data.get("sg_namespace"))
            anim_controls = rig_utils.get_anim_control_interface(
                True, namespace
            )
            animitem.load(
                path,
                objects=anim_controls,
                option="replace all",
                connect=False,
                currentTime=False,
                namespace=namespace,
            )

        if name == "load_lod_rig":
            rig_utils.create_rig_pxo_reference_from_sgid(sgid)

        # Execute actions defined in the classed higher in the MRO.
        super(MayaActions, self).execute_action(name, params, sg_publish_data)
