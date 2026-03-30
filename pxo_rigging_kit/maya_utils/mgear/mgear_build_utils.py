# Author:     Christof Puehringer / Rigging TD

"""
Functions to make the build and filtering process less messy.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import third-party modules
from future import standard_library

# Import built-in modules
from builtins import str

from importlib import reload
from pprint import pprint
from typing import Union, Optional

# Import third-party modules

# Import built-in modules
import logging

# Import third-party modules
import pymel.core as pmc
from maya.api import OpenMaya as om2

# Import locals
from pxo_rigging_kit import constants
from pxo_rigging_kit.constants import ADDIT_SCRIPTS_DECLA_NAME
from pxo_rigging_kit.maya_utils import attributes_utils


from pxo_rigging_kit.maya_utils.attributes_utils import cleanup_transform_attributes
from pxo_rigging_kit.maya_utils.rigging import rig_utils
from pxo_rigging_kit.maya_utils.rigging import mesh_islands
from pxo_rigging_kit.maya_utils.maya_conversion_utils import pymaya_to_pymel as pconv


standard_library.install_aliases()
reload(rig_utils)
#######################################################
# GLOBALS
#######################################################

logging.basicConfig(level=logging)
_LOGGER = logging.getLogger(__name__ + ".py")

##########################################################
# FUNCTIONS
##########################################################


def get_nonhost_components(
    step_dict,
    component_name,
    host_name=constants.HOST_COMP_NAME,
    exclude_component_name=None,
    include_capitalization=False
):
    """
    Filters all components for the component name while excluding items with [host_name] in them.

    Args:
        step_dict(mgear.shifter.custom_step.stepDict["mgearRun"]): The step dict for the run method in the custom step.
        component_name(str): The rig component name of the host
        host_name(str): The declaration string for the host.
                        Default is constants.HOST_COMP_NAME variable.
        exclude_component_name(str or list of str or None): The component/components you want to exclude from the list.
                                                    Default is None.
        include_capitalization(bool): Will inlcude all components with the capitalized component name.
                                      Default is False


    Returns:
        List: Matching components as list of strings.
    """

    non_hosts = [
        str(comp)
        for comp in list(step_dict.components.keys())
        if host_name not in comp
    ]

    rest_comps = [
        str(comp)
        for comp in non_hosts
        if component_name in comp
    ]

    if include_capitalization:
        rest_comps = [str(comp) for comp in rest_comps if component_name.capitalize() in comp]

    if exclude_component_name:
        if isinstance(exclude_component_name, list):
            rest_comps = []
            for comp in rest_comps:
                for exc_comp in exclude_component_name:
                    if exc_comp not in comp:
                        rest_comps.append(str(comp))
        else:
            rest_comps = [
                str(comp)
                for comp in rest_comps
                if not exclude_component_name in comp
            ]
    rest_comps.sort()

    return rest_comps


def get_all_components(step_dict, exclude_comp=None):
    result = [
        str(comp)
        for comp in list(step_dict.components.keys())
        if exclude_comp not in comp
    ]
    return result


def get_host_from_component(step_dict, comp_key):
    """
    Returns the host of the component. From given component.

    Args:
        step_dict(mgear.shifter.custom_step.stepDict["mgearRun"]): The step dict for the run method in the custom step.
        comp_key(str): Name of the component.

    Returns:
        pymel.core.PyNode: Host of the component.
    """

    component = step_dict.components.get(comp_key)

    return pconv(component.uihost)


def get_host_component(
    step_dict, component_name, host_name=constants.HOST_COMP_NAME
):
    """
    Get the host component.

    Args:
        step_dict(mgear.shifter.custom_step.stepDict["mgearRun"]): The step dict for the run method in the custom step.
        component_name(str): The rig component name of the host.
        host_name(str): The declaration string for the host.
                        Default is constants.HOST_COMP_NAME variable.

    Returns:

    """
    comp_name = "{0}{1}".format(component_name, host_name)
    hosts = [comp for comp in step_dict.components.keys() if comp_name in comp]
    return hosts


def get_component_name(step_dict, comp_key):
    """
    Returns the components name.

    Args:
        step_dict(mgear.shifter.custom_step.stepDict["mgearRun"]): The step dict for the run method in the custom step.
        comp_key(str): Name of the component.

    Returns:
        Str: Name of the component.
    """

    component = step_dict.components.get(comp_key)
    return component.name


def get_component_side(step_dict, comp_key):
    """
    Returns the components side.

    Args:
        step_dict(mgear.shifter.custom_step.stepDict["mgearRun"]): The step dict for the run method in the custom step.
        comp_key(str): Name of the component.

    Returns:
        Str: Side of the component.
    """

    component = step_dict.components.get(comp_key)
    return component.side


def get_component_index(step_dict, comp_key):
    """
    Returns the components index.

    Args:
        step_dict(mgear.shifter.custom_step.stepDict["mgearRun"]): The step dict for the run method in the custom step.
        comp_key(str): Name of the component.

    Returns:
        Int: Index of the component.
    """

    component = step_dict.components.get(comp_key)
    return component.index


def get_component_jnts(step_dict, comp_key):
    """
    Returns the joints that are part of input component.

    Args:
        step_dict(mgear.shifter.custom_step.stepDict["mgearRun"]): The step dict for the run method in the custom step.
        comp_key(str): Name of the component.

    Returns:
        List of joints as pymel.core.PyNodes.
    """

    component = step_dict.components.get(comp_key)
    return pconv(component.groups.get("deformers"))


def get_component_ctrls(step_dict, comp_key, sort_ctrls=False):
    """
    Returns the controls that are part of input component.

    Args:
        step_dict(mgear.shifter.custom_step.stepDict["mgearRun"]): The step dict for the run method in the custom step.
        comp_key(str): Name of the component.
        sort_ctrls(bool): sorting of the controls.

    Returns:
        List: List of controls as pymel.core.PyNodes.
    """

    component = step_dict.components.get(comp_key)

    controllers = component.groups.get("controllers")
    if not controllers:
        return

    if not sort_ctrls:
        return pconv(controllers)

    return pconv(controllers)


def get_component_root(step_dict, comp_key):
    """
    Returns the components root.

    Args:
        step_dict(mgear.shifter.custom_step.stepDict["mgearRun"]): The step dict for the run method in the custom step.
        comp_key(str): Name of the component.

    Returns:
        pymel.core.PyNode: Component root of specific component.
    """

    component = step_dict.components.get(comp_key)

    component_roots = component.groups.get("componentsRoots")
    if not component_roots:
        return

    return pconv(component_roots[0])


def get_component_fk_npos(step_dict, comp_key):
    """
    Returns the components npos.

    Args:
        step_dict(mgear.shifter.custom_step.stepDict["mgearRun"]): The step dict for the run method in the custom step.
        comp_key(str): Name of the component.

    Returns:
        None if fail.
        List: All fk npos.
    """

    component = step_dict.components.get(comp_key)
    component_npo = component.fk_npo
    return component_npo


def get_component_object(step_dict, comp_key):
    return step_dict.components.get(comp_key)


def get_top_set(step_dict):
    """
    Get the mgear top rig object set.

    Args:
        step_dict(mgear.shifter.custom_step.stepDict["mgearRun"]): The step dict for the run method in the custom step.

    Returns:
        pmc.PyNode(): The object set.
    """
    rig = step_dict["mgearRun"].model
    return rig.rigGroups.inputs()[0]


def get_controlers_set(step_dict):
    """
    Get the mgear controller rig object set.

    Args:
        step_dict(mgear.shifter.custom_step.stepDict["mgearRun"]): The step dict for the run method in the custom step.

    Returns:
        pmc.PyNode(): The object set.
    """
    rig = step_dict["mgearRun"].model
    controlers_set = pconv(rig.rigGroups.inputs()[1])
    return controlers_set


def get_comp_roots_set(step_dict):
    """
    Get the mgear component root rig object set.

    Args:
        step_dict(mgear.shifter.custom_step.stepDict["mgearRun"]): The step dict for the run method in the custom step.

    Returns:
        pmc.PyNode(): The object set.
    """
    rig = step_dict["mgearRun"].model
    return rig.rigGroups.inputs()[2]


def get_deformers_set(step_dict):
    """
    Get the mgear component root rig object set.

    Args:
        step_dict(mgear.shifter.custom_step.stepDict["mgearRun"]): The step dict for the run method in the custom step.

    Returns:
        pmc.PyNode(): The object set.
    """

    print("fucking hell we are in deformers set")
    pprint(step_dict)
    pprint(step_dict["mgearRun"])

    rig = step_dict["mgearRun"].model
    pprint(rig)
    pprint(rig.rigGroups)
    return pconv(rig.rigGroups.inputs()[3])


def construct_component_templates(limbs=("arm", "leg"), sides=("R", "L", "C")):
    return [f"{x}_{y}" for x in limbs for y in sides]


##########################################################
# Classes
##########################################################


class MgearFakeComponentClass(object):
    """
    Creates a mgear fake component class.
    So you can pass things into the stepDict.
    And use it like a normal mgear component.
    """

    def __init__(self, root_nd=None):
        """
        Args:
            root_nd(pmc.PyNode()): The root nd.
        """
        self.root_nodes = []
        self.name = None
        self.side = None
        self.index = 0
        self.count = 0
        self.groups = {}
        self.build_data = {}
        self.uihost = None
        if root_nd:
            self.add_root_nd(root_nd)
            self.set_component_root_list()

    def set_name(self, name):
        self.name = name

    def set_side(self, side):
        self.side = side

    def set_index(self, index):
        self.index = index

    def set_count(self, count):
        self.count = count

    def set_controls_list(self, list_):
        self.groups["controllers"] = list_

    def set_component_root_list(self):
        self.groups["componentsRoots"] = self.root_nodes

    def set_deformers_list(self, list_):
        self.groups["deformers"] = list_

    def add_root_nd(self, root_nd):
        self.root_nodes.append(root_nd)

class AssetBuildAddition(object):

    def __init__(self, acting_step_dict=None):
        self.name = ADDIT_SCRIPTS_DECLA_NAME
        self.acting_step_dict = acting_step_dict

    def run(self):
        raise NotImplemented("This method is essential and needs to be"
                             " implemented as executer of the additional build step.")


class BetterRibbon:
    """
    Creates a 'better ribbon' setup for a given FK/IK component by duplicating,
    offsetting, and rebuilding curves, then setting up joints and skin clusters
    to drive the rig.
    """

    def __init__(self, fk_ik_component, rebuild_curve=None, remove_fk=False, ugn=False, rebuild_main_curve = None):
        """
        Initialize the BetterRibbon instance.

        :param fk_ik_component: str, the base name of the fk/ik component.
        :param rebuild_curve: int, optional rebuild resolution for curves.
        :param remove_fk: bool, whether to remove the FK node after setup.
        :param ugn: bool, flag passed to offsetCurve (default False).
        """
        self.fk_ik_component = fk_ik_component
        self.rebuild_curve = rebuild_curve
        self.remove_fk = remove_fk
        self.ugn = ugn
        self.rebuild_main_curve = rebuild_main_curve

        # Attributes to store nodes and settings for later access:
        self.ik_curve_main = None
        self.ik_cuve_upv = None
        self.fk_curve_main = None
        self.fk_curve_upv = None
        self.fk_curve_main_dupl = None
        self.fk_curve_upv_offs = None
        self.fk_curve_upv_dupl = None
        self.curves = []
        self.ik_controllers = []
        self.jnts = []
        self.skin_cluster_upv = None
        self.skin_cluster_main = None

        #L_bnd_UppRope_0_0_jnt

    def get_mgear_data(self):
        self.comp_name, sideIndex = self.fk_ik_component.split("_")
        self.side, self.index = sideIndex[0], "".join(sideIndex[1:])

        # Build search pattern for IK controllers using f-string formatting.
        search_pattern = f"{self.comp_name}_{self.side}_{self.index}_ik*_ctrl"
        print(search_pattern)
        self.ik_controllers = pmc.ls(search_pattern)

        # Build search pattern for skin joints using f-string formatting.
        search_pattern = f"{self.side}_bnd_{self.comp_name}{self.index}*_jnt"
        self.skinJnt = pmc.ls(search_pattern)

    def build(self):
        """
        Build the better ribbon setup. This method creates duplicate curves,
        rebuilds them if needed, reconnects their outputs, sets up joints and
        skin clusters, and optionally removes the FK node.
        """
        _LOGGER.info(f"Building better ribbon for {self.fk_ik_component}")

        self.get_mgear_data()

        # --- Get the original curves ---
        self.ik_curve_main = pmc.PyNode(f"{self.fk_ik_component}_mstIK_crv")
        self.ik_cuve_upv = pmc.PyNode(f"{self.fk_ik_component}_upvIK_crv")
        self.fk_curve_main = pmc.PyNode(f"{self.fk_ik_component}_mst_crv")
        self.fk_curve_upv = pmc.PyNode(f"{self.fk_ik_component}_upv_crv")

        # --- Duplicate and offset curves ---
        self.fk_curve_main_dupl = pmc.duplicate(
            self.fk_curve_main,
            n=self.fk_curve_main.nodeName().replace("crv", "FKrbldCrv")
        )[0]

        self.fk_curve_upv_offs = pmc.offsetCurve(
            self.fk_curve_upv,
            n=self.fk_curve_upv.nodeName().replace("crv", "IKrbld"),
            ugn=self.ugn
        )[0]
        pmc.delete(self.fk_curve_upv_offs, ch=True)
        self.fk_curve_upv_offs.v.set(0)
        self.fk_curve_upv_offs.setParent(self.ik_curve_main.parent(0))

        self.fk_curve_upv_dupl = pmc.duplicate(
            self.fk_curve_upv_offs,
            n=self.fk_curve_upv.nodeName().replace("crv", "FKrbldCrv")
        )[0]

        # --- Rebuild curves if requested ---
        if self.rebuild_curve:
            pmc.rebuildCurve(self.fk_curve_upv_dupl, s=self.rebuild_curve, d=2, tol=0.01)
            pmc.delete(self.fk_curve_upv_dupl, ch=True)
            pmc.rebuildCurve(self.fk_curve_main_dupl, s=self.rebuild_curve, d=2, tol=0.01)
            pmc.delete(self.fk_curve_main_dupl, ch=True)

        if self.rebuild_main_curve:
            pmc.rebuildCurve(self.fk_curve_main, s=self.rebuild_main_curve, d=2, tol=0.01)
            pmc.rebuildCurve(self.fk_curve_upv_offs, s=self.rebuild_main_curve, d=2, tol=0.01)


        # --- Reconnect connections from original curves to the duplicates ---
        for connection in self.ik_curve_main.worldSpace[0].listConnections():
            self.fk_curve_main_dupl.worldSpace[0].connect(connection.geometryPath, f=True)

        for connection in self.ik_cuve_upv.worldSpace[0].listConnections():
            self.fk_curve_upv_dupl.worldSpace[0].connect(connection.geometryPath, f=True)

        for connection in self.fk_curve_upv.worldSpace[0].listConnections():
            self.fk_curve_upv_offs.worldSpace[0].connect(connection.geometryPath, f=True)

        # --- Delete the original curves that are no longer needed ---
        pmc.delete(self.ik_curve_main, self.ik_cuve_upv, self.fk_curve_upv)

        # --- Unlock and zero attributes on the curves and disable inherit transform ---
        self.curves = [
            self.fk_curve_upv_offs,
            self.fk_curve_main_dupl,
            self.fk_curve_upv_dupl,
            self.fk_curve_main
        ]
        for crv in self.curves:
            attributes_utils.unlock_and_zero_attributes(crv)
            crv.inheritsTransform.set(0)

        # --- Create joints for the IK controllers ---
        for ik_c in self.ik_controllers:
            joint_name = ik_c.nodeName().replace("ctrl", "rbjnt")
            jnt = pmc.joint(n=joint_name)
            jnt.v.set(0)
            pmc.delete(pmc.parentConstraint(ik_c, jnt))
            jnt.setParent(ik_c)
            self.jnts.append(jnt)

        _LOGGER.info(f"Created joints: {self.jnts}")

        # --- Create skin clusters for the curves ---
        print(self.jnts)
        self.skin_cluster_upv = pmc.skinCluster(self.jnts, self.fk_curve_upv_dupl, tsb=True, maximumInfluences=2)
        print("Skin Cluster (upv):", self.skin_cluster_upv)
        self.skin_cluster_main = pmc.skinCluster(self.jnts, self.fk_curve_main_dupl, tsb=True, maximumInfluences=2)
        print("Skin Cluster (main):", self.skin_cluster_main)

        # --- Optionally remove the FK node ---
        if self.remove_fk:
            pmc.delete(self.fk_ik_component + "_fk0_npo")

        return self


class BetterRibbon2:
    """
    Creates a 'better ribbon' setup for a given chain_FK_variable_IK component by duplicating,
    offsetting, and rebuilding curves, then setting up joints and skin clusters
    to drive the rig.

    The ribbon can not be set to MGear options: fixedLength
    The ribbon needs to have MGear options: axtra Tweakers

    The FK of the ribbon is used for the associations,
    so on island and mesh it will use their worldspace to generate relationships.

    # TODO: this only works with tweakers activated and no fixed length.

    """

    VALID_SURFACE_ASSOCIATIONS = {"island", "loft", "mesh"}

    def __init__(self,
                 fk_ik_component: str,
                 offset_value: float = 0.1,
                 surface_association: Optional[str] = None,
                 radius: float = 5.0,
                 is_stretchable: bool = True,
                 driver_mesh: Optional[str] = None,
                 rebuild_curve: Optional[int] = None,
                 smooth_curve: Optional[int] = None,
                 auto_skin_curve: bool = False,
                 auto_skin_easing: bool = False,
                 use_wire_deformer: Optional[list] = False,
                 keep_lengt = True

                 ):
        """

        Args:
            fk_ik_component (str): Name of the component.

            offset_value (float): How much the newly created upv curves will be offset.

            surface_association (str): Declare the Type of better ribbon.

            radius (float): If the surface association creates Polygonal geometry you give the dimensions here.

            is_stretchable (bool): If you want the ribbon to be stretchable, you can declare it here.

            driver_mesh (str, None): If you chose a surface association that needs an input mesh, you assign it here.

            rebuild_curve (int, None): If you want to rebuild the curves, you can give the number of spans here.

            smooth_curve (int, None): If you want to smooth the curves, you can give the amount of smoothing here.

            auto_skin_curve (bool): tag for having the curve skinned automatically in a parametric fashion.


        """

        self.fk_ik_component = fk_ik_component

        if not surface_association:
            _LOGGER.warning("surface_association was not given defaulting to triangle")

        if surface_association not in self.VALID_SURFACE_ASSOCIATIONS:
            _LOGGER.warning(f"surface_association: {surface_association} "
                            f"was not in VALID_SURFACE_ASSOCIATIONS, "
                            f"defaulting to triangle"
                            )

        self.surface_association = surface_association

        if driver_mesh and not pmc.objExists(driver_mesh):
            raise ValueError("mesh is missing")

        if driver_mesh and isinstance(driver_mesh, pmc.PyNode):
            driver_mesh = driver_mesh

        elif driver_mesh and isinstance(driver_mesh, six.string_types):
            driver_mesh = pmc.PyNode(driver_mesh)

        self.driver_mesh = driver_mesh

        self.offset_value = offset_value
        self.radius = radius
        self.is_stretchable = is_stretchable
        self.rebuild_curve = rebuild_curve
        self.smooth_curve = smooth_curve
        self.auto_skin_curve = auto_skin_curve
        self.auto_skin_easing = auto_skin_easing
        self.use_wire_deformer = use_wire_deformer
        self.keep_lengt = keep_lengt
        # Attributes to store nodes and settings for later access:
        self.ik_curve_main = None
        self.ik_cuve_upv = None
        self.fk_curve_main = None
        self.fk_curve_upv = None
        self.fk_curve_main_dupl = None
        self.fk_curve_upv_offs = None
        self.fk_curve_upv_dupl = None

        self.skin_cluster_upv = None
        self.skin_cluster_main = None

        self.setup_grp = None
        self.deformer_grp = None

        self.fk_controllers = None
        self.skin_jnt = None
        self.tweak_joint_grp = None
        self.pre_curve = None
        self.pre_curve_upv = None
        self.post_curve = None
        self.post_curve_upv = None
        self.fk_component = None
        self.host = None
        self.attribute_list = None

        self.comp_name = None
        self.side = None
        self.index = None
        self.reconstructed_name = None

        self.curves = []
        self.ik_controllers = []
        self.jnts = []
        self.created_joints = []

    def get_mgear_data(self):
        """Extract component data from mGear naming convention, find controllers/joints and get curves."""

        self.comp_name, sideIndex = self.fk_ik_component.split("_")
        self.side, self.index = sideIndex[0], sideIndex[1:]

        self.reconstructed_name = f"{self.comp_name}_{self.side}{self.index}"

        # Build search pattern for IK controllers using f-string formatting.
        search_pattern = f"{self.comp_name}_{self.side}_{self.index}_ik*_ctrl"
        _LOGGER.debug(search_pattern)

        self.ik_controllers = pmc.ls(search_pattern)
        search_pattern = f"{self.comp_name}_{self.side}_{self.index}_fk*_ctrl"
        _LOGGER.debug(search_pattern)

        self.fk_controllers = pmc.ls(search_pattern)

        # Build search pattern for skin joints using f-string formatting.
        search_pattern = f"{self.side}_bnd_{self.comp_name}_{self.index}*_jnt"

        self.skin_jnt = pmc.ls(search_pattern)

        _LOGGER.debug(f"{self.reconstructed_name}_mstIK_crv")

        self.tweak_joint_grp = pmc.ls(f"{self.reconstructed_name}_extraTweak*_ctrl")

        self.pre_curve = pmc.PyNode(f"{self.reconstructed_name}_mstIK_crv")
        self.pre_curve_upv = pmc.PyNode(f"{self.reconstructed_name}_upvIK_crv")
        self.post_curve = pmc.PyNode(f"{self.reconstructed_name}_mst_crv")
        self.post_curve_upv = pmc.PyNode(f"{self.reconstructed_name}_upv_crv")

        self.fk_component = pmc.PyNode(f"{self.reconstructed_name}_fk0_npo")
        self.host = None

        setup_groups = pmc.ls("setup", type="transform")
        if setup_groups:
            self.setup_grp = pmc.PyNode(setup_groups[0])

        vis_host = pmc.listConnections(f'{self.ik_controllers[0]}Shape.visibility')
        if vis_host:
            self.host = vis_host[0]

        self.attribute_list = attributes_utils.list_attrs_with_prefix(self.host,self.comp_name)


    def _create_mesh_from_curves(self,loft=False):
        """Create mesh from curves using convert_curves_to_plane function with proper naming."""
        self.driver_mesh, _, _, self.loft = convert_curves_to_plane(
            self.post_curve, self.post_curve_upv, self.offset_value,
        )
        self.driver_mesh = pmc.PyNode(self.driver_mesh)

        mesh_name = f"{self.comp_name}_{self.side}{self.index}_ribbon_geo"
        self.driver_mesh.rename(mesh_name)

        self.driver_mesh.visibility.set(0)

        self.driver_mesh.setParent(self.setup_grp)

    def _setup_controllers(self):
        """Setup UV pin and joint creation for IK controllers with proper naming."""
        parents = []

        for ik_control in self.ik_controllers:
            parent = pmc.PyNode(ik_control.getParent())
            parents.append(parent)
            cleanup_transform_attributes(parent)
            cleanup_transform_attributes(ik_control)

        rig_utils.create_uv_pin_setup(
            self.driver_mesh,
            parents,
            pin_directly=False,
            use_out_translate=False,
            keep_in_hierarchy=True,
        )

    def _reconnect_curves(self):
        """Reconnect curve outputs from pre to post curves."""

        if self.rebuild_curve:
            pmc.rebuildCurve(self.post_curve,
                             spans=self.rebuild_curve,
                             d=2,
                             tol=0.01
                             )
            pmc.delete(self.post_curve, ch=True)

            pmc.rebuildCurve(self.post_curve_upv,
                             spans=self.rebuild_curve,
                             d=2,
                             tol=0.01
                             )
            pmc.delete(self.post_curve_upv, ch=True)

        #create curve lenght for up and post

        #create multiply divide that calculate the length same as we do for scale

        for connection in self.pre_curve.worldSpace[0].listConnections():
            self.post_curve.worldSpace[0].connect(connection.geometryPath, f=True)
            #if self.keep_lengt == True
            # connect the lengt to the current lengt using the scale

        for connection in self.pre_curve_upv.worldSpace[0].listConnections():
            self.post_curve_upv.worldSpace[0].connect(
                connection.geometryPath, f=True
            )

        pmc.delete(self.post_curve,
                   constructionHistory=True
                   )

        pmc.delete(self.post_curve_upv,
                   constructionHistory=True
                   )



    def _cleanup(self):
        connected_attrs = pmc.listConnections(f'{self.fk_controllers[0]}Shape.visibility',
                                              plugs=True
                                              )

        pmc.delete(self.fk_component)
        pmc.delete(self.pre_curve, self.pre_curve_upv)

        for jnt in self.created_joints:
            jnt.visibility.set(0)

        if not connected_attrs:
            return

        for att_ in connected_attrs:
            pmc.deleteAttr(att_)

        #reorder_Attr =
        print(self.attribute_list)
        attributes_utils.move_attrs_to_bottom(
            self.host,
            self.attribute_list
        )

    def _create_island_for_controller(self):
        parents = []

        for ik_control in self.ik_controllers:
            parent = pmc.PyNode(ik_control.getParent())
            parents.append(parent)

            cleanup_transform_attributes(parent)
            cleanup_transform_attributes(ik_control)

        if not parents:
            raise ValueError

        base_mesh, self.uv_pin_node = mesh_islands.build_combined_pin_mesh(
            parents,
            rotate=True,
            pin_node_split_amount=2000,
            ribbon_node_split_amount=2000,
            use_directly=True,
            desired_count=1,
            radius=self.radius,
            system_name=f"{self.reconstructed_name}_",
            pre_rotate=(90, 0, 135),
            mesh_shape="triangle",
        )

        self.driver_mesh = base_mesh[0]
        self.driver_mesh.setParent(self.setup_grp)

    def _create_joints(self, parent_inherit: bool):
        created_joints = []

        for index_, ik_control in enumerate(self.ik_controllers):
            pmc.select(ik_control)
            joint_name = f"{self.reconstructed_name}_{ik_control.name().split('_')[-2]}_ik{index_}_drvJnt"

            new_joint = pmc.joint(n=joint_name)
            created_joints.append(new_joint)

            try:
                ik_control.getParent().inheritsTransform.set(parent_inherit)
            except:
                pass

        return created_joints

    def build(self):

        self.get_mgear_data()

        if self.surface_association == "island":
            self._create_island_for_controller()
            INHERIT_PARENT = False

        elif self.surface_association == "mesh":
            self._setup_controllers()
            INHERIT_PARENT = True

        elif self.surface_association == "loft":
            self._create_mesh_from_curves()
            self._setup_controllers()
            INHERIT_PARENT = True

        else:  # this is up for discussion
            self._create_island_for_controller()
            INHERIT_PARENT = False

        self.created_joints = self._create_joints(parent_inherit=INHERIT_PARENT)
        self._reconnect_curves()

        skin_cluster_name = f"{self.comp_name}_ribbon_SKC"

        _LOGGER.debug(self.post_curve)

        pmc.skinCluster(self.created_joints,
                        pmc.PyNode(self.post_curve_upv),
                        n=skin_cluster_name
                        )

        pmc.skinCluster(self.created_joints,
                        pmc.PyNode(self.post_curve),
                        n=skin_cluster_name
                        )

        if self.auto_skin_curve:
            for i in range(10):
                auto_skin_curve(self.post_curve, self.auto_skin_easing)
                auto_skin_curve(self.post_curve_upv, self.auto_skin_easing)

        if self.smooth_curve:
            smooth_att_name = "smoothness"
            attr_name = f"{self.comp_name}_{smooth_att_name}"

            self.post_curve,smooth_node_1 = pmc.smoothCurve(self.post_curve.cv[:],
                                                            ch=1,
                                                            rpo=1,
                                                            s=self.smooth_curve
                                                            )

            self.post_curve_upv,smooth_node_2 = pmc.smoothCurve(self.post_curve_upv.cv[:],
                                                                ch=1,
                                                                rpo=1,
                                                                s=self.smooth_curve
                                                                )

            if not self.host.hasAttr(attr_name):
                self.host.addAttr(attr_name,
                                  nn=smooth_att_name,
                                  at='float',
                                  dv=self.smooth_curve,
                                  min=0.0,
                                  max=200,
                                  k=True
                                  )

            smooth_attr = self.host.attr(attr_name)

            smooth_attr.setKeyable(True)
            smooth_attr.connect(smooth_node_1.smoothness)
            smooth_attr.connect(smooth_node_2.smoothness)

            self.attribute_list.append(attr_name)

        pprint(self.post_curve)
        if self.is_stretchable and not self.use_wire_deformer:
            create_curve_joints_setup(self.post_curve,
                                      self.skin_jnt,
                                      self.host,
                                      attribute_name = f"{self.comp_name}_Stretch",
                                      squash_attribute_name = f"{self.comp_name}_Squash"
                                      )

            self.attribute_list.append(f"{self.comp_name}_Stretch")

        if self.use_wire_deformer:
            pmc.delete(self.skin_jnt,
                       self.tweak_joint_grp,
                       )

            wire_grp = rig_utils.create_wire_deformer(
                main_curve=self.post_curve,
                up_curve=self.post_curve_upv,
                geometry_or_vertices=self.use_wire_deformer,
                up_controllers=self.ik_controllers,
                num_twists=len(self.ik_controllers)
            )
            if self.rebuild_curve:
                pmc.rebuildCurve(self.post_curve,
                                 spans=self.rebuild_curve,
                                 d=2,
                                 tol=0.01
                                 )

                pmc.rebuildCurve(self.post_curve_upv,
                                 spans=self.rebuild_curve,
                                 d=2,
                                 tol=0.01
                                 )
            wire_grp.setParent(self.setup_grp)
        self._cleanup()
        group_node = pmc.group(self.post_curve, self.post_curve_upv, name=self.pre_curve.name().replace('_crv', '_grp'))
        # print("#################################################################################"+group_node)
        attributes_utils.cleanup_transform_attributes(self.post_curve)
        attributes_utils.cleanup_transform_attributes(self.post_curve_upv)

        group_node.inheritsTransform.set(False)

        # Set rotation and translation to 0
        self.post_curve.t.set(0, 0, 0)
        self.post_curve.r.set(0, 0, 0)

        self.post_curve_upv.t.set(0, 0, 0)
        self.post_curve_upv.r.set(0, 0, 0)


        _LOGGER.info(f"Better ribbon setup completed for {self.fk_ik_component}")


def convert_curves_to_plane(curve1: Union[str, pmc.PyNode],
                            curve2: Union[str, pmc.PyNode],
                            offset_value: float = 0.5,
                            keep_loft: bool = False,
                            return_loft: bool = False,
                            ) -> tuple:

   if isinstance(curve1, str):
       curve1 = pmc.PyNode(curve1)

   if isinstance(curve2, str):
       curve2 = pmc.PyNode(curve2)

   if offset_value is not None:
       curve1= pmc.offsetCurve(curve1,
                                   d=offset_value,
                                   ch=False
                                   )  # add _ to unpack var and have healthy existence erroring if not there

       curve2= pmc.offsetCurve(curve2,
                                   d=-offset_value,
                                   ch=False
                                   )  # add _ to unpack var and have healthy existence erroring if not there
   curve1 = curve1[0]

   curve2 = curve2[0]

   loft_surface= pmc.loft(curve1,
                           curve2,
                           n="loftedSurface1",
                           ch=True,
                           u=True,
                           c=False,
                           ar=True,
                           d=3,
                           ss=1,
                           rn=False,
                           )
   loft_surface = loft_surface[0]

   if return_loft:
       if offset_value is not None:
           pmc.delete(curve1, curve2)
           curve1, curve2 = None, None
       return None, curve1, curve2, loft_surface

   rebuilt_surface= pmc.rebuildSurface(loft_surface,
                                        ch=1,
                                        rpo=1,
                                        rt=0,
                                        end=1,
                                        kr=0,
                                        kcp=0,
                                        kc=0,
                                        su=0,
                                        du=3,
                                        sv=100,
                                        dv=3,
                                        tol=0.01,
                                        fr=0,
                                        dir=2)
   rebuilt_surface = rebuilt_surface[0]

   poly_mesh= pmc.nurbsToPoly(rebuilt_surface,
                                  mnd=1,
                                  ch=1,
                                  f=2,
                                  pt=1,
                                  pc=200,
                                  chr=0.9,
                                  ft=0.01,
                                  mel=0.001,
                                  d=0.1,
                                  ut=3,
                                  un=1,
                                  vt=1,
                                  vn=1,
                                  uch=0,
                                  ucr=0,
                                  cht=0.2,
                                  es=0,
                                  ntr=0,
                                  mrt=1,
                                  uss=1)
   poly_mesh= poly_mesh[0]

   pmc.delete(poly_mesh, ch=True)

   if not keep_loft:
       pmc.delete(loft_surface, rebuilt_surface)
       loft_surface = None  # set it to None since it does not exist anymore.

   if offset_value is not None:
       pmc.delete(curve1, curve2)
       curve1, curve2 = None, None  # set it to None since it does not exist anymore.

   return poly_mesh, curve1, curve2, loft_surface


def create_curve_joints_setup(curve: pmc.PyNode,
                              joint_list: list,
                              host_node: Optional[pmc.PyNode] = None,
                              attribute_name="stretch",
                              squash_attribute_name="squash"
                              ):

    curve_info = pmc.arclen(curve, ch=True)
    curve_info.rename(f'{curve}_CVI')
    initial_length = curve_info.arcLength.get()
    scale_node = pmc.createNode('multiplyDivide', name=f'{curve}_scaleMultiply')
    scale_node.operation.set(2)
    scale_node.input2X.set(initial_length)
    curve_info.arcLength.connect(scale_node.input1X)

    # Get motion paths connected to the main curve
    mp_list = curve.worldSpace[0].listConnections(source=False, destination=True, type='motionPath')

    # Get motion paths from upv curve
    upv_curve_name = curve.name().replace('_mst_', '_upv_')
    try:
        upv_curve = pmc.PyNode(upv_curve_name)
        upv_mp_list = upv_curve.worldSpace[0].listConnections(source=False, destination=True, type='motionPath')
        mp_list.extend(upv_mp_list)
    except:
        pass

    if host_node:
        if not host_node.hasAttr(attribute_name):
            host_node.addAttr(attribute_name,
                              nn=attribute_name.split("_")[-1],
                              at='float',
                              dv=1.0,
                              min=0.0,
                              max=1.0,
                              k=True,
                              )
        if not host_node.hasAttr(squash_attribute_name):
            host_node.addAttr(squash_attribute_name,
                              nn=squash_attribute_name.split("_")[-1],
                              at='float',
                              dv=1.0,
                              min=0.0,
                              k=True,
                              )
        blend_node = pmc.createNode('blendTwoAttr', name=f'{curve}_hostBlend_BTA')
        blend_node.input[0].set(1.0)
        scale_node.outputX.connect(blend_node.input[1])
        host_node.attr(attribute_name).connect(blend_node.attributesBlender)

        # Setup stretch for joints
        for joint in joint_list:
            blend_node.output.connect(joint.scaleX, force=True)

        # Setup stretch for motion paths
        for mp in mp_list:
            # Store initial U value
            initial_u = mp.uValue.get()

            # Calculate absolute position (initial_u * initial_length)
            absolute_pos_node = pmc.createNode('multiplyDivide', name=f'{mp}_absolutePos_MD')
            absolute_pos_node.operation.set(1)  # Multiply
            absolute_pos_node.input1X.set(initial_u)
            absolute_pos_node.input2X.set(initial_length)

            # Calculate dynamic U value (absolute_position / current_length)
            dynamic_u_node = pmc.createNode('multiplyDivide', name=f'{mp}_dynamicU_MD')
            dynamic_u_node.operation.set(2)  # Divide
            absolute_pos_node.outputX.connect(dynamic_u_node.input1X)
            curve_info.arcLength.connect(dynamic_u_node.input2X)

            # Create condition node: if current_length < initial_length, force stretch on
            condition_node = pmc.createNode('condition', name=f'{mp}_stretchCondition')
            condition_node.operation.set(4)  # Less than
            curve_info.arcLength.connect(condition_node.firstTerm)
            condition_node.secondTerm.set(initial_length)
            condition_node.colorIfTrueR.set(1.0)  # Force stretch on when shorter
            host_node.attr(attribute_name).connect(condition_node.colorIfFalseR)

            # Blend between fixed U and dynamic U based on conditioned stretch attribute
            u_blend_node = pmc.createNode('blendTwoAttr', name=f'{mp}_uBlend_BTA')
            dynamic_u_node.outputX.connect(u_blend_node.input[0])
            u_blend_node.input[1].set(initial_u)
            condition_node.outColorR.connect(u_blend_node.attributesBlender)

            # Connect blended U to motion path
            u_blend_node.output.connect(mp.uValue, force=True)
    else:
        for joint in joint_list:
            scale_node.outputX.connect(joint.scaleX, force=True)

    # _create_gaussian_squash(curve, joint_list, scale_node, host_node, squash_attribute_name)

    for jnt in joint_list:
        jnt.inheritsTransform.set(False)

    return

def _create_gaussian_squash(curve: pmc.PyNode,
                            joint_list: list,
                            stretch_node: pmc.PyNode,
                            host_node: Optional[pmc.PyNode] = None,
                            squash_attribute_name: str = "squash",
                            ):

    """YZ = min(1, S^(-0.5)); smooth endpoints (0) via Hann window; optional global squash."""
    import math

    if len(joint_list) < 2:
        return

    if host_node and not host_node.hasAttr(squash_attribute_name):
        host_node.addAttr(squash_attribute_name, at='float', k=True, min=0, max=1, dv=1)

    # Volume term: S^(-0.5)
    pow_md = pmc.createNode('multiplyDivide', n=f'{curve}_volPreservePow_MD')
    pow_md.operation.set(3)  # Power
    stretch_node.outputX.connect(pow_md.input1X)
    pow_md.input2X.set(-0.5)

    # Clamp so it never goes above 1 (no bulge when S < 1)
    clamp_nd = pmc.createNode('clamp', n=f'{curve}_volPreserve_CLAMP')
    clamp_nd.minR.set(1)
    clamp_nd.maxR.set(500.0)
    pow_md.outputX.connect(clamp_nd.inputR)

    sigma = 0.3
    last = len(joint_list) - 1
    denom = float(last)

    for i, jnt in enumerate(joint_list):
        t = i / denom  # 0..1
        gauss = math.exp(-((t - 0.5) ** 2) / (2 * sigma ** 2))
        hann  = 0.5 - 0.5 * math.cos(2 * math.pi * t)  # 0 at ends, smooth
        w = gauss * hann  # smooth, exactly 0 on first/last

        fall_bta = pmc.createNode('blendTwoAttr', n=f'{jnt}_squashFalloff_BTA')
        fall_bta.input[0].set(1.0)
        clamp_nd.outputR.connect(fall_bta.input[1])  # lerp(1, min(1, S^-0.5), w)
        fall_bta.attributesBlender.set(w)

        if host_node:
            fin_bta = pmc.createNode('blendTwoAttr', n=f'{jnt}_squashFinal_BTA')
            fin_bta.input[0].set(1.0)
            fall_bta.output.connect(fin_bta.input[1])
            host_node.attr(squash_attribute_name).connect(fin_bta.attributesBlender)
            fin_bta.output.connect(jnt.scaleY, f=True)
            fin_bta.output.connect(jnt.scaleZ, f=True)
        else:
            fall_bta.output.connect(jnt.scaleY, f=True)
            fall_bta.output.connect(jnt.scaleZ, f=True)



def auto_skin_curve(curve, use_easing=False):
    """
    Reskins a NURBS curve so each CV is influenced only by the two *nearest*
    joints already attached to its skinCluster.

    Args:
        curve: The NURBS curve to reskin
        use_easing: If True, applies ease in/out interpolation for smoother transitions
    """
    curve = pmc.PyNode(curve)
    skin = pmc.PyNode(pmc.listHistory(curve, type='skinCluster')[0])
    skin.maxInfluences.set(2)
    joints = skin.influenceObjects()
    joint_pos = {j: j.getRotatePivot(space='world') for j in joints}

    for cv in curve.cv:
        cv_pos = cv.getPosition(space='world')

        distances = []
        for joint in joints:
            distance = (cv_pos - joint_pos[joint]).length()
            distances.append((distance, joint))

        (d1, j1), (d2, j2) = sorted(distances)[:2]

        if use_easing:
            # Calculate normalized distance ratio [0,1]
            total_dist = d1 + d2
            ratio = d1 / total_dist if total_dist > 0 else 0.5

            # Apply cubic ease in/out
            if ratio < 0.5:
                eased_ratio = 2 * ratio * ratio
            else:
                eased_ratio = 1 - 2 * (1 - ratio) * (1 - ratio)

            w2 = eased_ratio
            w1 = 1.0 - w2
        else:
            # Original inverse distance weighting
            inv_d1 = 1.0 / d1
            inv_d2 = 1.0 / d2
            total_inv = inv_d1 + inv_d2
            w1 = inv_d1 / total_inv
            w2 = inv_d2 / total_inv

        pmc.skinPercent(skin, cv, transformValue=[(j1, w1), (j2, w2)])

