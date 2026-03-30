from maya import cmds

from pathlib import PurePath

from pxo_rigging_kit.constants import ICON_SUBNAMES
from pxo_rigging_kit.maya_utils.EWAW_rs import node


def create_container(container_name: str,
                     file_path: PurePath,
                     container_type: str = "dagContainer",
                     ) -> str:

    """
    Creates a container node.

    Args:
        container_name (str): Name of the container node.
        file_path (PurePath): File path to the icons.
        container_type (str): Type of the container, right now its dagContainer.

    Returns:
        Str: Name of the container node created.
    """

    container_name_composed = f"{container_name}"
    icon_path_name = "icon_path"

    # Create container node
    container_name = node.createNode(
            container_type,
            name=container_name_composed,
    )

    node.createNode("choice",
                    name=f"{container_name_composed}_CHO")

    for k_, v_ in ICON_SUBNAMES.items():

        icon_path_base = file_path.joinpath(f"{k_}.png")

        icon_path_name_ = node.addAttr(container_name_composed,
                                       ln=f"{icon_path_name}{k_}",
                                       dt="string",
                                       )

        cmds.setAttr(
                icon_path_name_,
                icon_path_base.as_posix(),
                type="string",
        )

        cmds.connectAttr(icon_path_name_,
                         f"{container_name_composed}_CHO.input[{v_}]"
                         )

    cmds.connectAttr(f"{container_name_composed}_CHO.output",
                     f"{container_name_composed}.iconName",
                     )
    attrs_ = ("tx", "ty", "tz",
              "rx", "ry", "rz",
              "sx", "sy", "sz",
              )

    for att_ in attrs_:
        cmds.setAttr(f"{container_name}.{att_}",
                     lock=True,
                     channelBox=False,
                     keyable=False,
                     )

    return container_name


def update_container_display(container_name: str,
                             display_type: str = "default"
                             ):
    """
    Updates the display of the container node icon based on the constants.icon_subnames dict.

    Args:
        container_name(str): Name of the container node.
        display_type(str):  Name of the display type without _.

    """

    _container_check(container_name,
                     container_type="dagContainer",
                     )

    # get the channel name from the dictionary, if it is invalid it will be None and raise a LookupError.
    channel = ICON_SUBNAMES.get(f"_{display_type}", None)

    if channel is None:
        raise LookupError(f"{display_type} ---> _{display_type} was not found in the icon subnames dictionary")

    connected_choices = cmds.listConnections(f"{container_name}.iconName")

    if not connected_choices:
        raise ConnectionError(f"{container_name} was not connected to the choice node")

    connected_choice = connected_choices[0]

    cmds.setAttr(f"{connected_choice}.selector",
                 channel
                 )

    cmds.select(container_name)
    cmds.evalDeferred("cmds.select(cl=True)")

    cmds.setAttr(f"{container_name}.blackBox",
                 True
                 )

    cmds.setAttr(f"{container_name}.blackBox",
                 False
                 )


def _container_check(container_name: str,
                     container_type: str = "dagContainer",
                     ) -> bool:
    """
    Checks if the name given is the right type
    Args:
        container_name (str): Name of the container.
        container_type (str): Type of the container.

    Returns:
        True: if it does run through it will return True.
    """
    if not cmds.objExists(container_name):
        raise NameError(f"{container_name} does not exist in the scene")

    if not cmds.objectType(container_name,
                           isAType=container_type,
                           ):
        raise TypeError(f"{container_name} is not of type {container_type}")

    return True


def publish_children(container_name: str,
                     ):
    """
    Publishes all children of the container.

    Args:
        container_name(str): Name of the container node.

    """

    # checking if the container is valid
    _container_check(container_name,
                     container_type="dagContainer",
                     )

    # check if container even has children
    children_ = cmds.listRelatives(container_name, ad=True)

    if not children_:
        raise IndexError(f"{container_name} has no children.")

    # getting the types of the children of the container and bundle them up with the name
    children_and_types = [(child_name, cmds.objectType(child_name))
                          for child_name in children_
                          if not cmds.objectType(child_name, isAType="nurbsCurve")
                          ]

    # publishing the children of the container
    for publish_name, type_ in children_and_types:
        cmds.containerPublish(container_name, publishNode=(publish_name, type_))
        cmds.containerPublish(container_name, bindNode=(publish_name, publish_name))
