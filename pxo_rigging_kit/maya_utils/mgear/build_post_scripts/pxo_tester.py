"""
Custom script to prepare the clavicle component to our needs.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import built-in modules
from builtins import dict
from pprint import pprint

# Import third-party modules
from future import standard_library

# Import built-in modules
import logging

# Import third-party modules
import mgear.shifter.custom_step as cstp

# Import local modules
from pxo_rigging_kit.maya_utils.mgear import mgear_build_utils

from typing import Any, Dict, List, Optional
import mgear.shifter as shifter

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

    COMPONENT = "clavicle"

    def __init__(self):
        self.name = "pxo_clavicle_setup"
        self.acting_step_dict = None

    def run(self, stepDict):
        pprint(stepDict)
        self.acting_step_dict = stepDict["mgearRun"]

        accessor = RigAccessor(rig=self.acting_step_dict)
        accessor.summarize()


class RigAccessor:
    """
    Accessor for mGear Shifter Rig objects.
    Wraps mgear.shifter.Rig and provides clean, string-based access
    to rig metadata, options, groups, components, and build steps.
    """

    def __init__(self, rig: shifter.Rig) -> None:
        if not isinstance(rig, shifter.Rig):
            raise TypeError("RigAccessor requires a mgear.shifter.Rig instance")
        self._rig = rig

    # --- Metadata ---
    @property
    def rig_root_grp(self) -> str:
        return str(getattr(self._rig, "model", ""))

    @property
    def global_ctrl(self) -> str:
        return str(getattr(self._rig, "global_ctl", ""))

    @property
    def setup_grp(self) -> str:
        return str(getattr(self._rig, "setupWS", ""))

    @property
    def jnt_org(self) -> str:
        return str(getattr(self._rig, "jnt_org", ""))

    @property
    def options(self) -> Dict[str, Any]:
        return getattr(self._rig, "options", {})

    @property
    def user_name(self) -> str:
        return self._get_option("user", "")

    @property
    def rig_root(self) -> str:
        return self._get_option("rig_name", "")

    @property
    def joint_base_name(self) -> str:
        return self._get_option("joint_name_rule", "")

    @property
    def ctrl_base_name(self) -> str:
        return self._get_option("ctl_name_rule", "")

    # --- World Control ---
    @property
    def use_world_ctl(self) -> bool:
        """Return 'True' or 'False' as string."""

        return True if self._get_option("worldCtl", False) else False

    @property
    def world_ctl_name(self) -> str:
        return self._get_option("worldCtlName", "world_ctl")

    # --- Groups ---
    @property
    def model(self) -> str:
        """Return the rig model node name as string."""
        model = getattr(self._rig, "model", None)
        return str(model) if model else ""

    @property
    def groups(self) -> Dict[str, str]:
        """Return rig groups as a dict of string names."""
        groups = getattr(self._rig, "groups", {})
        return {k: str(v) for k, v in groups.items() if v}

    @property
    def controllers_list(self) -> str:
        return self.groups.get("controllers", "")

    @property
    def component_roots_list(self) -> str:
        return self.groups.get("componentsRoots", "")

    @property
    def joints_list(self) -> str:
        return self.groups.get("deformers", "")

    @property
    def locals_grp(self) -> str:
        return self.groups.get("locals_grp", "")

    @property
    def extra_grp(self) -> str:
        return self.groups.get("extra_grp", "")

    # --- Components ---
    @property
    def component_names(self) -> List[str]:
        """Return component names as strings."""
        comps = getattr(self._rig, "components", [])
        return [str(getattr(c, "name", c)) for c in comps]

    @property
    def component_objects(self) -> List[str]:
        """Return component names as strings."""
        comps = getattr(self._rig, "components", [])
        return list(comps.values())

    def get_component(self, name: str) -> str:
        """Return a component by name as string, or empty if not found."""
        for comp in getattr(self._rig, "components", []):
            if getattr(comp, "name", "") == name:
                return str(comp.name)
        return ""

    def get_component_by_side(self, side: str) -> str:
        """Return a component by name as string, or empty if not found."""
        for comp in getattr(self._rig, "components", []):
            if getattr(comp, "side", "") == side:
                return str(comp.side)
        return ""

    def get_components_by_type(self, comp_type: str) -> List[str]:
        """Return all components of a given type as strings."""
        return [
            str(getattr(c, "name", c))
            for c in getattr(self._rig, "components", [])
            if getattr(c, "type", "") == comp_type
        ]

    @property
    def arms(self) -> List[str]:
        return self.get_components_by_type("arm")

    @property
    def legs(self) -> List[str]:
        return self.get_components_by_type("leg")

    @property
    def spines(self) -> List[str]:
        return self.get_components_by_type("spine")

    @property
    def heads(self) -> List[str]:
        return self.get_components_by_type("head")

    # --- Guides ---
    @property
    def guides(self) -> str:
        """Return guide network name as string."""
        guides = getattr(self._rig, "guides", None)
        return str(guides) if guides else ""

    # --- Build Steps ---
    @property
    def steps(self) -> List[str]:
        return [str(s) for s in getattr(self._rig, "steps", [])]

    # --- ATTRIBUTES ---
    @property
    def attr_user(self) -> str:
        """Return guide network name as string."""
        _user_attr = getattr(self._rig, "user_att", None)
        return str(_user_attr) if _user_attr else ""

    # --- Utility ---
    def _get_option(self, key: str, default: Optional[Any] = None) -> str:
        return str(self.options.get(key, default))

    def has_step(self, step_name: str) -> bool:
        return step_name in self.steps

    def summarize(self):
        print("#"*20)
        print("#"*20)
        print("groups")
        print("user_attribute:", self.attr_user)

        print("rig root grp:", self.rig_root_grp)
        print("global_ctrl:", self.global_ctrl)
        print("setup grp:", self.setup_grp)
        print("joint org:", self.jnt_org)

        print("data")
        print("~" * 20)
        print("options:", self.options)
        print("steps:", self.steps)
        print("control world:", self.world_ctl_name)

        print("~" * 20)
        print("groups:", self.groups)
        print("controllers list:", self.controllers_list)
        print("joints list:", self.joints_list)
        print("component_roots list:", self.component_roots_list)
        print("locals_grp:", self.locals_grp)
        print("extra_grp:", self.extra_grp)
        print("component names:", self.component_names)
        print("arms:", self.arms)

        print("~" * 20)
        print("left_components:", self.get_component_by_side("L"))
        print("~" * 20)

        for attr_name in self._rig.__dict__:
            value = getattr(self._rig, attr_name)
            print(attr_name, "=", value)

        print("=" * 20)
        print("=" * 20)

        for component_ in self.component_objects:
            ca_ = ComponentAccessor(component_)
            print(ca_.summarize())


class ComponentAccessor:
    """
    Helper class to explore mGear Component objects
    from the stepDict['components'] dictionary.
    """

    def __init__(self, component):
        self._component = component

    @property
    def name(self):
        return getattr(self._component, "name", None)

    @property
    def guide(self):
        return getattr(self._component, "guide", None)

    @property
    def nodes(self):
        return getattr(self._component, "mgear_nodes", [])

    @property
    def controls(self):
        return getattr(self._component, "ctl", [])

    @property
    def joints(self):
        """Return deform joints created by this component"""
        return getattr(self._component, "jnt", [])

    @property
    def deformers(self):
        """Return deformers (skinClusters, lattices, etc.)"""
        return getattr(self._component, "deformers", [])

    @property
    def settings(self):
        return getattr(self._component, "settings", {})

    @property
    def connections(self):
        return getattr(self._component, "connections", {})

    def summarize(self):
        print("|"*40)

        for attr_name in self._component.__dict__:
            value = getattr(self._component, attr_name)
            print(attr_name, "=", value)
            print("-" * 10)

        print("|" * 40)

        return {
            "name": self.name,
            "controls": self.controls,
            "joints": self.joints,
            "deformers": self.deformers,
            "settings": self.settings,
            "connections": self.connections,
        }

