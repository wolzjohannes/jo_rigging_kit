# mgear / pixo dynamic joints post script
# www.pixomondo.com
# Date: 04 / 24 / 2023
# Artist: Christof Puehringer / Rigging TD

"""
Utility code to generate mesh poly planes as island for mesh or controls pinning.
"""

# Import built-in modules
import itertools
import logging
import math
from typing import Optional

# Import third-party modules
import pymel.core as pmc

# Import local modules
from pxo_rigging_kit.core import list_split
from pxo_rigging_kit.maya_utils import dag_utils
from pxo_rigging_kit.maya_utils import attributes_utils
from pxo_rigging_kit.maya_utils.EWAW_rs import node

#######################################################
# GLOBALS
#######################################################

logging.basicConfig(level=logging)
_LOGGER = logging.getLogger(__name__ + ".py")

#######################################################
# FUNCTIONS
#######################################################


def calc_subdivisions(inputs, desired_count=2500):
    """
    Function used to determine the subdivision amount needed
    for the pin geo to be thrown onto the gpu.

    Args:
        inputs(list): Objects to be calculated for.
        desired_count(int): Desired polygon count.

    Returns:
        Int: The calculated subdivision lvl.

    """
    inputs_length = len(inputs)
    subdiv_combined = desired_count / inputs_length
    subdiv_lvl = int(math.ceil(math.sqrt(subdiv_combined)))

    if subdiv_lvl <= 1:
        return 1

    return subdiv_lvl


def build_pin_mesh_separately(
    root_ndes: list,
    desired_count: int = 2500,
    radius: float = 0.1,
    use_desired_count: bool = False,
    pre_rotate: Optional[tuple] = None,
    use_directly: bool = False,
    mesh_shape: str = "square"
):
    """
    Creates PolyPlanes on the locations of the children of the root node, for later pinning.

    Args:
        root_ndes(list): List containing all pymel.core.PyNode(root_node) items.
        desired_count(int): Count of the polys per pin
        radius(float): The width for each island poly plane.
        use_desired_count(bool): If it should use a desired count, if not a simple tri is created.
        pre_rotate(tuple): Specifies if the mesh islands needs a pre rotate to fit the mesh asset better.
                           If None there is no pre rotate.
                           Example could be: (90.0, 0.0, 0.0).
        use_directly(bool): Will use the given nodes.
                            If None will use the parent nodes of the given nodes.

        mesh_shape (str):  what kind of mesh we want. Valids: 'triangle', 'square'.

    Returns:
        List: List of all the maya.pymel.core.PyNode(pin_mesh) nodes.

    """

    pin_meshes = list()

    subdiv_value = 0

    if use_desired_count:
        subdiv_value = calc_subdivisions(root_ndes, desired_count=desired_count)

    for root_nde in root_ndes:

        proxy_plane = create_proxy_mesh(radius,
                                        root_nde,
                                        subdiv_value,
                                        mesh_shape=mesh_shape)

        npo_nde = root_nde if use_directly else root_nde.getChildren()[0]

        if len(proxy_plane)>1:
            proxy_plane = proxy_plane[0]

        if pre_rotate:
            proxy_plane.rotate.set(pre_rotate)
            pmc.makeIdentity(
                proxy_plane,
                r=True,
                s=False,
                t=False,
                pn=True,
                apply=True,
            )

        proxy_plane.setTranslation(
            npo_nde.getTranslation(space="world"), worldSpace=True
        )

        proxy_plane.setRotation(
            npo_nde.getRotation(space="world"), worldSpace=True
        )
        if not pre_rotate:
            pmc.parent(proxy_plane, npo_nde)
            # pmc.xform(proxy_plane, r=True, ro=(0, 0, 0))
            pmc.xform(proxy_plane, r=True, ro=(0, -90, 270))
            pmc.parent(proxy_plane, world=True)
        pin_meshes.append(proxy_plane)

    return pin_meshes


def create_proxy_mesh(radius: float,
                      root_nde: pmc.PyNode,
                      subdivisions: int,
                      mesh_shape="square"
                      ) -> list:
    """
    Creates a mesh based on predefined parameters to keep sub-mesh creation standardized.

    ATTENTION:  Future projects should be using triangles, but for backwards compatibility we use squares for now.
                polyDiscs do not have a return Value, this is why we need to take the extra steps of doing it using selection.
                They also do not have a name, so we need to rename afterward.

    Args:
        radius (float): dimensions of single submesh.
        root_nde (pmc.PyNode): the root node.
        subdivisions (int): amount of subdivs.
        mesh_shape (str): what kind of mesh we want. Valids: 'triangle', 'square'.

    Returns:
        List: Contains Transform and Mesh.
    """
    pmc.select(cl=True)

    name = f"{root_nde.shortName()}_intermediateGeo"

    _valid_types = {"triangle": {"geo_operation": pmc.polyDisc,
                                 "kwargs": {
                                     "subdivisions": subdivisions,
                                     "radius": radius,
                                     "sides": 3}
                                 },

                    "square": {"geo_operation": pmc.polyPlane,
                               "kwargs": {
                                   "subdivisionsX": subdivisions,
                                   "subdivisionsY": subdivisions,
                                   "width": radius,
                                   "height": radius,
                               }
                               },
                    }

    op = _valid_types.get(mesh_shape, None)

    if not op:
        raise ValueError(f"{mesh_shape} could not be found in {_valid_types}. Please pick a valid type")

    op["geo_operation"](**op["kwargs"])

    geometry_transform = pmc.selected()[0]

    geometry_transform.rename(name)

    return [geometry_transform, geometry_transform.getShape()]


def build_combined_pin_mesh(
        root_ndes,
        rotate=False,
        pin_node_split_amount=2,
        ribbon_node_split_amount=2,
        desired_count=2500,
        system_name="default",
        radius=0.1,
        pre_rotate: Optional[tuple] = None,
        scale_connection=None,
        use_directly=False,
        mesh_shape: str = "square",
):

    """
    Unites the Pin Meshes into one, and creates a uv pinning based on that

    Args:
        root_ndes(list): List of maya.pymel.core.PyNode(root_node).
        rotate(bool): Rotation applied to uv islands.
        pin_node_split_amount(int): Amount of pin node sharing per system.
        ribbon_node_split_amount(int): Amount of geo node sharing per system.
        desired_count(int): PolyCount of geo node sharing per system.
        system_name(str): Name the system will get.
        radius (float): how big the uniform patch should be.
        pre_rotate(tuple): Specifies if the mesh islands needs a pre rotate to fit the mesh asset better.
                           If None there is no pre rotate.
                           Example could be: (90.0, 0.0, 0.0)
        scale_connection(str, None): if there is a scale to be connected, it will go in here.
        use_directly(bool): if it should be plugged in directly.

        mesh_shape (str):  what kind of mesh we want. Valids: 'triangle', 'square'.


    Returns:
        Tuple:  (maya.pymel.core.PyNode(combined_mesh),
                maya.pymel.core.PyNode(uv_pin))

    """
    rotate_option = 0
    if rotate:
        rotate_option = 2

    root_ndes = list(x if isinstance(x, pmc.PyNode) else pmc.PyNode(x) for x in root_ndes)
    pin_reducing = list(list_split(root_ndes, pin_node_split_amount))
    ribbon_reducing = list(list_split(pin_reducing, ribbon_node_split_amount))

    ribbon_nodes = list()
    pin_nodes = list()

    for ribbon_grp in ribbon_reducing:
        pin_roots = list(itertools.chain.from_iterable(ribbon_grp))
        if len(pin_roots) == 1:
            pin_mesh = build_pin_mesh_separately(
                    pin_roots,
                    desired_count=desired_count,
                    radius=radius,
                    pre_rotate=pre_rotate,
                    use_directly=use_directly,
                    mesh_shape=mesh_shape,
            )[0]

            ribbon_nde = pin_mesh.rename(
                f"{system_name}Pin_C_001_geo"
            )

            ribbon_shape = ribbon_nde.getShape()
        else:
            pin_meshes = build_pin_mesh_separately(
                    pin_roots,
                    desired_count=desired_count,
                    radius=radius,
                    pre_rotate=pre_rotate,
                    use_directly=use_directly,
                    mesh_shape=mesh_shape,
            )

            ribbon_nde = pmc.polyUnite(
                pin_meshes,
                name=f"{system_name}Pin_C_001_geo",
                constructionHistory=False,
            )[0]
            ribbon_shape = ribbon_nde.getShape()

        pmc.polyMultiLayoutUV(
            ribbon_shape, scale=1, rotateForBestFit=rotate_option, layout=2
        )
        ribbon_nodes.append(ribbon_nde)

        for pin_iter_, pin_grp in enumerate(ribbon_grp):

            pin_nde = node.createNode(
                "uvPin",
                n=f"{system_name}Pin_C_{pin_iter_:03}_uvp",
                as_type="pymel",
            )

            ribbon_shape.worldMesh[0].connect(pin_nde.deformedGeometry)
            ribbon_shape.worldMesh[0].connect(pin_nde.originalGeometry)

            for iteration_, root_nde in enumerate(pin_grp):
                npo_nde = root_nde if use_directly else root_nde.getChildren()[0]

                for a in pmc.listAttr(npo_nde):
                    npo_nde.attr(a).unlock()

                u_value, v_value = ribbon_shape.getUVAtPoint(
                    root_nde.getTranslation(worldSpace=True), space="world"
                )

                pin_nde.attr(f"coordinate[{iteration_}].coordinateU").set(u_value,
                                                                          lock=True,
                                                                          )

                pin_nde.attr(f"coordinate[{iteration_}].coordinateV").set(v_value,
                                                                          lock=True,
                                                                          )

                if not use_directly:
                    pin_trs = node.createNode("transform",
                                              n=f"{npo_nde.name(long=None)}_pin_trs",
                                              as_type="pymel",
                                              )

                    pin_nde.attr(f"outputMatrix[{iteration_}]").connect(pin_trs.offsetParentMatrix,
                                                                        force=True,
                                                                        )

                    pin_trs.setParent(npo_nde.getParent())
                    ctrl = npo_nde.getChildren(type="transform")

                    buffer_grp = dag_utils.create_buffer_groups(ctrl)
                    pmc.parent(buffer_grp, None)
                    attributes_utils.unlock_attributes(npo_nde)
                    npo_nde.setParent(pin_trs)
                    pmc.parent(buffer_grp, npo_nde)

                    pin_trs.inheritsTransform.set(False,
                                                  lock=True,
                                                  )

                    pin_trs.setTranslation([0, 0, 0])
                    pin_trs.setRotation([0, 0, 0])

                    local_mtx = ctrl[0].getMatrix(objectSpace=True)
                    ctrl[0].offsetParentMatrix.set(local_mtx)
                    pmc.xform(ctrl[0], matrix=pmc.dt.Matrix())
                    print("wtf is happening in here??????")

                else:
                    pin_nde.attr(f"outputMatrix[{iteration_}]").connect(npo_nde.offsetParentMatrix,
                                                                        force=True,
                                                                        )

                    npo_nde.inheritsTransform.set(False,
                                                  lock=True,
                                                  )

                    npo_nde.setTranslation([0, 0, 0])
                    npo_nde.setRotation([0, 0, 0])

                if scale_connection:
                    scale_attr = pmc.Attribute(scale_connection)
                    global_scale_to_tweaker = node.createNode("math_MatrixFromTRS",
                                                              n=f"{system_name}_pin_{pin_iter_:03}_MFT",
                                                              as_type="pymel",
                                                              )

                    global_scale_times_tweaker = node.createNode("math_MultiplyMatrix",
                                                                 n=f"{system_name}_pin_{pin_iter_:03}_MMX",
                                                                 as_type="pymel",
                                                                 )

                    for axis in "XYZ":
                        scale_attr.connect(global_scale_to_tweaker.attr(f"scale{axis}"))

                    pin_nde.attr(f"outputMatrix[{iteration_}]").connect(global_scale_times_tweaker.input2)

                    global_scale_to_tweaker.output.connect(global_scale_times_tweaker.input1)

                    if use_directly:
                        global_scale_times_tweaker.output.connect(pin_trs.offsetParentMatrix,
                                                                  force=True,
                                                                  )
                    else:
                        global_scale_times_tweaker.output.connect(npo_nde.offsetParentMatrix,
                                                                  force=True,
                                                                  )

            #     npo_nde.inheritsTransform.set(False, lock=True)
            #     npo_nde.setTranslation([0, 0, 0])
            #     npo_nde.setRotation([0, 0, 0])
            #     pmc.parent(buffer_grp, npo_nde)
            #
            pin_nodes.append(pin_nde)
    return ribbon_nodes, pin_nodes
