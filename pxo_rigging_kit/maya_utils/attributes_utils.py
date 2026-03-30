# Author:     Christof Puehringer / Rigging TD

"""
Util code to manage the channel box.
"""
# Import future modules
from __future__ import absolute_import, division, print_function, unicode_literals
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import built-in modules
from builtins import str
import logging
import os
from typing import Union

# Import third-party modules
from future import standard_library

# Import maya modules
import maya.cmds as cmds
from pixo_paths import normalize
import pymel.core as pmc
from pymel import core as pmc

# Import local modules
from pxo_rigging_kit import constants
from pxo_rigging_kit import paths
from pxo_rigging_kit import versioncontrol_utils
from pxo_rigging_kit.maya_utils import decorators
from pxo_rigging_kit.maya_utils import paths_utils
from pxo_rigging_kit.maya_utils.maya_conversion_utils import pymaya_to_pymel as pconv

##########################################################
# GLOBALS
##########################################################

standard_library.install_aliases()
_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)
DECORATORS = decorators.Decorators()
DECORATORS.debug = True
DECORATORS.logger = _LOGGER
_DATA_LOCATION_FOLDER_NAME = "PXO_ATTRIBUTES"
_DATA_LOOKUP_EXPORT_NAME = "attributes_data"

##########################################################
# FUNCTIONS
##########################################################


def refactor_separators_to_pxo_style(nodes_list):
    """
    Adjusts enum attributes names to the pixomondo naming scheme.
    The enum attributes used as attribute categories and separators.

    Args:
        nodes_list(list): The nodes to act on. List of pmc.PyNodes().

    """

    for sel_node in nodes_list:
        attrs = [str(x.shortName()) for x in sel_node.listAttr(ud=True)]
        attr_split = [x.split("_") for x in attrs]
        attr_rightsize = [x for x in attr_split if len(x) == 2]
        attr_pattern = [x[0] for x in attr_rightsize if x[0] == x[1]]

        for i in attr_pattern:
            pmc.addAttr(
                "{}.{}_{}".format(str(sel_node.shortName()), i, i),
                edit=True,
                nn=i,
                en=constants.PXO_SEPARATOR_STRING,
            )
            pmc.renameAttr(
                "{}.{}_{}".format(str(sel_node.shortName()), i, i), i
            )
            sel_node.attr(i).set(lock=True)


def edit_visibility_attr(nodes_list, sort_string="vis"):
    """
    Sets the visibility attrs to non key-able.

    Args:
        nodes_list(list): The nodes to act on. List of pmc.PyNodes().
        sort_string(str): Type of the shape as a string.

    """

    for sel_node in nodes_list:
        [
            x.set(keyable=False, cb=True)
            for x in sel_node.listAttr(ud=True)
            if str(x.shortName()).split("_")[-1] == sort_string
        ]


def get_ud_attributes(node):
    """
    Get the user defined attributes of a node.
    Args:
            node(dagNode): The node the attributes belongs to.
    Return:
            list with dics: The attributes values as keys in a dic.
            Example:
                    [{'attrType': u'double',
                    'usd_attr': Attribute(u'null1.test_float'),
                    'index': 1, 'lock': False, 'defaultValue': 1.0,
                    'maxValue': 10.0, 'value': 0.0, 'minValue': 0.0,
                    'keyable': True, 'channelBox': False,
                    'output': [Attribute(u'null3.translateX')],
                    'input': [Attribute(u'null2.translateX')],
                    'hidden': False, 'enums': None}]
    """
    result = []
    ud_attributes = node.listAttr(ud=True)
    for index, ud_attr in enumerate(ud_attributes):
        attr_dic = {
            "ud_attr": ud_attr,
            "longName": ud_attr.longName(),
            "shortName": ud_attr.shortName(),
            "niceName": pmc.addAttr(ud_attr, niceName=True, query=True),
            "attrType": ud_attr.get(typ=True),
            "value": ud_attr.get(),
            "maxValue": ud_attr.getMax(),
            "minValue": ud_attr.getMin(),
            "hidden": ud_attr.isHidden(),
            "keyable": ud_attr.isKeyable(),
            "defaultValue": pmc.addAttr(str(ud_attr), query=True, dv=True),
            "channelBox": ud_attr.isInChannelBox(),
            "lock": ud_attr.isLocked(),
            "input": ud_attr.connections(s=True, d=False, p=True),
            "output": ud_attr.connections(s=False, d=True, p=True),
            "index": index,
            "parent": ud_attr.getParent(arrays=True),
        }
        try:
            attr_dic["children"] = ud_attr.getChildren()
        except:
            attr_dic["children"] = None
        try:
            attr_dic["enums"] = ud_attr.getEnums()
        except:
            attr_dic["enums"] = None
        result.append(attr_dic)
    return result


def get_message_attributes(node, sort_out_names=None):
    """
    Get the message attributes from given node.

    Args:
        node(pmc.PyNode()): The node to act on.
        sort_out_names(list): The sort out attributes from result.

    Return:
        List: Attributes string.

    """
    result = [attr_ for attr_ in node.listAttr() if attr_.type() == "message"]

    if not result:
        return

    if sort_out_names:
        result = [
            attr__
            for attr__ in result
            if attr__.name(includeNode=False) not in sort_out_names
        ]
    return result


def connect_multi_attributes(node, attribute_name, nodes_list):
    """
    Connect nodes from given list with message multi attribute in serial.

    Args:
        node(pmc.PyNode()): Target node.
        attribute_name(str): The multi attribute name.
        nodes_list(list): List of nodes to connect for.

    """
    attr_obj = node.attr(attribute_name)
    elements_count = attr_obj.evaluateNumElements()
    for index, node in enumerate(nodes_list):
        index_ = elements_count + index
        node.message.connect(attr_obj[index_])


def add_pxo_separator_attr(node, attr_name, as_pymel=True, niceName=None):
    """
    Add separator attr in pxo style.

    Args:
        node(pmc.PyNode(), str): Target node.
        attr_name(str): Attribute name.
        as_pymel(bool): If operation shall be pymel.

    """

    if as_pymel:

        node = node if isinstance(node, pmc.PyNode) else pmc.PyNode(node)
        if niceName:

            node.addAttr(attr_name,
                         typ="enum",
                         nn=niceName,
                         en=constants.PXO_SEPARATOR_STRING,
                         keyable=False,
                         )
        else:
            node.addAttr(attr_name,
                         typ="enum",
                         en=constants.PXO_SEPARATOR_STRING,
                         keyable=False,
                         )

        node.attr(attr_name).set(channelBox=True, lock=True)

    else:
        node = node if isinstance(node, str) else str(node.longName())
        if niceName:
            cmds.addAttr(node,
                         ln=attr_name,
                         at="enum",
                         en=constants.PXO_SEPARATOR_STRING,
                         keyable=False,
                         nn=niceName,
                         )

        else:
            cmds.addAttr(node,
                         ln=attr_name,
                         at="enum",
                         en=constants.PXO_SEPARATOR_STRING,
                         keyable=False,
                         )

        cmds.setAttr(f"{node}.{attr_name}", channelBox=True, lock=True)



def has_attr(node, attr_name):
    """
    Check if node has given attribute and if the given attribute has a value.
    This function is faster then the pymel equivalent.

    Args:
        node(pmc.PyNode or str): Node to check for.
        attr_name(str): The attribute name.

    Return:
        True or False.

    """
    if isinstance(node, pmc.PyNode):
        tag_attr = ".".join([node.name(), attr_name])
    else:
        tag_attr = ".".join([node, attr_name])
    try:
        if cmds.getAttr(tag_attr):
            return True
        else:
            return False
    except:
        return False


def get_next_free_array_index(attr_name, start_index, max_search=10000):
    """
    Iterates over indices of array(maya multi) attributes and returns the next available open Connection.

    Args:
        attr_name(str): Name of the attribute including node name.
        start_index(int): the index to start with
    Returns:
        Int: The next available index
    """

    # assume a max of 10 million connections
    for index_ in range(start_index, start_index + max_search):
        if (
            len(
                cmds.connectionInfo(
                    "{0}[{1}]".format(attr_name, index_), sfd=True
                )
                or []
            )
            == 0
        ):
            return index_

    # No connections mean the first index is available
    return 0


def unlock_attributes(
    node,
    attributes=None,
):
    """Unlock attributes of a node.

    By defaul will unlock the rotation, scale and translation.

    Args:
        node(dagNode): The node with the attributes to unlock.
        attributes (list of str): The list of the attributes to unlock.
                                  If None will take ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz", "v"].
                                  Default is None.

    """
    if attributes is None:
        attributes = ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz", "v")

    for attr_name in attributes:
        node.setAttr(attr_name, lock=False, keyable=True)

def unlock_and_zero_attributes(
    node,
    attributes=None,
):
    """Unlock attributes of a node.

    By defaul will unlock the rotation, scale and translation.

    Args:
        node(dagNode): The node with the attributes to unlock.
        attributes (list of str): The list of the attributes to unlock.
                                  If None will take ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz", "v"].
                                  Default is None.

    """
    if attributes is None:
        attributes = ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz")

    for attr_name in attributes:
        node.setAttr(attr_name, lock=False, keyable=True)
        default_value = 1 if attr_name.startswith("s") else 0
        node.setAttr(attr_name, default_value)



def lock_and_hide_attributes(node, lock=True, hide=True, attributes=None):
    """
    Lock and hide a attribute of the node.
    In Default, it will lock and hide the default channels.
    Args:
            node(dagNode): The node the attribute belongs to.
            lock(bool): Lock/unlock the attribute.
            hide(bool): Hide/Unhide the attribute.
            attributes(list of str): The list with attributes to lock/hide
    Return:
            list: The locked attributes.
    """
    if isinstance(node, str):
        node = pmc.PyNode(node)

    default_attr = ["tx", "ty", "tz", "ro", "rx", "ry", "rz", "sx", "sy", "sz"]
    result = []
    if attributes:
        if not isinstance(attributes, list):
            attributes = [attributes]
    else:
        attributes = default_attr
    for attr_ in attributes:
        node.attr(attr_).set(lock=lock)
        if hide:
            node.attr(attr_).set(keyable=False, channelBox=False)
        result.append(node.attr(attr_))
    return result


def save_attributes_to_json(objects_list, export_path=None):
    """
    Saves attributes values from given objects as json file.

    Args:
        objects_list(list): The objects you want to act on.
        export_path(str): The save place.

    """
    if export_path:
        vers_lod_path = normalize(export_path)

    else:
        export_path = paths_utils.get_project_paths(pmc.sceneName())

        # general save operations
        export_path = os.path.join(
            export_path, constants.ATTRDATA_LOCATION_FOLDER_NAME
        )
        paths.check_and_create_path(export_path)
        vers_lod_path = versioncontrol_utils.check_and_create_date(export_path)

    attrs = {}
    for obj in objects_list:
        obj_name = obj.name()
        obj_attrs = {}
        for attr in obj.listAttr(cb=True):
            if attr.isSettable():
                attr_name = attr.name()
                attr_value = attr.get()
                obj_attrs[attr_name] = attr_value
            attrs[obj_name] = obj_attrs
    paths.write_json_file(
        attrs,
        vers_lod_path,
        "{0}.json".format(constants.ATTRDATA_LOOKUP_EXPORT_NAME),
    )
    _LOGGER.info("Attributes values saved to: {0}".format(vers_lod_path))


def apply_attributes_values(data_dict):
    """
    Applies attributes values from given data dict.

    Args:
        data_dict(dict): Attributes data dict. Looks like this:
                        {
                            "reinRope_L_0_ik0_default_ctrl": {
                                "reinRope_L_0_ik0_default_ctrl.PinOnMesh": 0.0
                            },
                            "reinRope_L_0_ik1_default_ctrl": {
                                "reinRope_L_0_ik1_default_ctrl.PinOnMesh": 0.0
                            },
                            "reinRope_L_0_ik2_default_ctrl": {
                                "reinRope_L_0_ik2_default_ctrl.PinOnMesh": 0.0
                            }
                        }
    """
    for obj, attr_vals in data_dict.items():
        if pmc.objExists(obj):
            for attr, val in attr_vals.items():
                if pmc.objExists(attr) and pmc.PyNode(attr).isSettable():
                    pmc.PyNode(attr).set(val)
                    pmc.addAttr(pmc.PyNode(attr), edit=True, defaultValue=val)


def apply_attributes_values_from_latest_json_file():
    """
    Apply attributes values for latest json file found in the asset data directory.
    """
    import_path = paths_utils.get_project_paths(pmc.sceneName())
    import_path = normalize(
        os.path.join(import_path, constants.ATTRDATA_LOCATION_FOLDER_NAME)
    )
    paths.check_and_create_path(import_path)
    vers_lod_path = versioncontrol_utils.get_latest_path(import_path)
    data_lookup_file = paths.read_files_of_directory(vers_lod_path)
    if not data_lookup_file:
        raise ValueError("no file")
    list_length = len(data_lookup_file)
    if list_length > 1:
        raise ValueError("too many items")
    json_file_location = normalize(
        os.path.join(
            vers_lod_path,
            "{}.json".format(constants.ATTRDATA_LOOKUP_EXPORT_NAME),
        )
    )
    data_lookup_info = paths.read_json_file(json_file_location)
    apply_attributes_values(data_lookup_info)


def select_objects_from_json(json_file_path):
    """
    Selects objects listed in JSON.

    Args:
        json_file_path(str): The path to the json file.

    """
    attrs = paths.read_json_file(json_file_path)
    pmc.select([obj for obj in attrs if pmc.objExists(obj)], replace=True)


def add_enum_attribute(
    node,
    name,
    enum,
    value=0,
    nice_name=None,
    keyable=True,
    hidden=False,
    writable=True,
    channelBox=True,
    lock=False,
):
    """
    Add a enum attribute to the node.
    Args:
            node(dagNode): The node to add the attribute.
            name(str): Longname of the attribute.
            enum(list with str): Names of the enums.
            value(float or int): The value of the attribute.
            keyable(bool): Defines if the attribute is keyable.
            hidden(bool): Defines if the attribute are hidden.
            writable(bool): Defines if the attribute can get input connections.
            channelBox(bool): Defines if the attribute is in the channelbox.
            lock(bool): Lock/Unlock the attribute.

    Return:
            dic: A dic with the enum and their index.
                 Inclusive the attribute name.

    """

    if node.hasAttr(name):
        _LOGGER.error(f"{name} attribute already exist")
        return

    enum_dic = {}
    data_dic = {}

    data_dic["attributeType"] = "enum"

    data_dic["en"] = ":".join(enum)
    data_dic["keyable"] = keyable
    data_dic["hidden"] = hidden
    data_dic["writable"] = writable
    if nice_name:
        data_dic["niceName"] = nice_name

    node.addAttr(name, **data_dic)

    node.attr(name).set(value, lock=lock, keyable=keyable, channelBox=True)
    if not channelBox:
        node.attr(name).set(lock=lock, keyable=False, channelBox=False)

    for x in range(len(enum)):
        enum_dic["index_" + str(x)] = enum[x]

    enum_dic["attributeName"] = name

    return enum_dic


def add_attribute_to_node_by_dict(node, attr_dict):
    """
    Add attribute to given node with given attr_dict.

    Args:
        node(pmc.PyNode): The node which will receive the attribute
        attr_dict(dict): The attribute dict.
                         Each key represents a flag of the addAttr command.
                         The "connect_to" key gives the abillity to connect
                         the attribute directly to a nodes attribute.
                         The value of the connect_to key needs to be pmc.Attribute
                         Example Dict:
                         {
                            "connect_to": [pmc.Attribute('your_node.visibility')]
                            "longName": "Test_attr",
                            "type": "bool",
                            "keyable": True,
                            "defaultValue": 1,
                        }
    """
    _LOGGER.debug(f"ATTR DICT: {attr_dict}")

    connect_to = attr_dict.pop("connect_to", [])
    connect_from = attr_dict.pop("connect_from", [])
    force_connect = attr_dict.pop("force_connect", False)

    _LOGGER.debug(f"FORCE CONNECT: {force_connect}")

    if not node.hasAttr(attr_dict["longName"]):
        pmc.addAttr(node, **attr_dict)

    if not attr_dict.get("hidden", False):
        node.attr(attr_dict["longName"]).set(channelBox=True)

    if attr_dict.get("keyable", False):
        node.attr(attr_dict["longName"]).set(keyable=True)

    if not connect_to and not connect_from:
        return

    for con_attr_to in connect_to:
        if force_connect:
            node.attr(attr_dict["longName"]).connect(con_attr_to, force=True)
        else:
            try:
                node.attr(attr_dict["longName"]).connect(con_attr_to)
            except:
                _LOGGER.warning(f"{con_attr_to} seems to be already connected.")
        # except:
        #     _LOGGER.warning(f"ATTR TO FAILED: {node.attr(attr_dict['longName'])} >>> {con_attr_to}")

    for con_attr_from in connect_from:
        try:
            if force_connect:
                con_attr_from.connect(node.attr(attr_dict["longName"]), force=True)
            else:
                try:
                    con_attr_from.connect(node.attr(attr_dict["longName"]))
                except:
                    _LOGGER.warning(f"{con_attr_from} seems to be already connected.")
        except:
            _LOGGER.warning(f"ATTR FROM FAILED: {con_attr_from} >>> {node.attr(attr_dict['longName'])}")


def add_attributes_to_node_by_list(node, attr_data_list):
    """
    Add attributes by given list to given node.

    Args:
        node(pmc.PyNode): The node which will receive the attribute
        attr_data_list(list): The list is filled with attributes dicts.

    """
    for attr_dict in attr_data_list:
        add_attribute_to_node_by_dict(node, attr_dict)


def edit_enum_attr(
    enum_attr,
    add_=None,
    insert_=None,
    append_=None,
    change_=None,
):
    """
    Easy way to edit a enum attribute.

    Args:
        enum_attr(pymel.core.general.Attribute): The enum attribute.
        add_(str): Attribute to add at the beginning of the enum list.
        insert_(List): Insert a attribute on given index.
        Valid list are: [index, str]
        append_(str): Attribute to add at the end of the enum list.
        change_(List): Change attribute name on given index.
        Valid list are: [index, str]

    """
    enums_dic = enum_attr.getEnums()
    enums_items = list(enums_dic.items())
    enums_names_sorted_list = []
    for x in range(len(enums_items)):
        for tupl_ in enums_items:
            if x is tupl_[1]:
                enums_names_sorted_list.append(tupl_[0])
    if add_:
        if not add_ in enums_names_sorted_list:
            enums_names_sorted_list.insert(0, add_)
    if insert_:
        enums_names_sorted_list.insert(insert_[0], insert_[1])
    if append_:
        if not append_ in enums_names_sorted_list:
            enums_names_sorted_list.append(append_)
    if change_:
        enums_names_sorted_list[change_[0]] = change_[1]
    pmc.addAttr(
        enum_attr, edit=True, enumName=":".join(enums_names_sorted_list)
    )


class BufferAttributeSync:
    """
    A class to synchronize attributes of given controllers with their respective control buffers.

    Attributes:
        buffer_suffix (str): Suffix appended to the control name to find its corresponding buffer.
        to_match (list): List of controller names whose attributes need to be synchronized.
        ignore_attr (list): List of attributes to ignore during synchronization.
    """

    def __init__(self, to_match=None):
        """
        Initializes the BufferAttributeSync instance.

        Args:
            to_match (list, optional): List of controller names to synchronize. Defaults to None.
        """
        self.buffer_suffix = "_controlBuffer"
        self.to_match = to_match
        self.ignore_attr = ["tx", "ty", "tz", "rx", "ry", "rz", "offset_ctrl", "ro", "sx", "sy", "sx"]

    def sync_all_children_of(self, main_father_controller):
        """
        Synchronizes all child controllers of a given parent controller.

        Args:
            main_father_controller (str): The name of the main parent controller.

        This function retrieves all child transform nodes of the given controller, filters them to include only those
        ending with '_ctrl', and updates the 'to_match' list before calling sync_list().
        """
        trl = pmc.PyNode(main_father_controller)

        transform_children = trl.getChildren(type='transform', ad=True)
        transform_children.append(trl)
        filtered_ctrl_names = [child.nodeName() for child in transform_children
                               if child.nodeName().endswith('_ctrl')]

        self.to_match = filtered_ctrl_names
        self.sync_list()

    def sync_list(self):
        """
        Synchronizes the attributes of each controller in the 'to_match' list with their corresponding control buffers.

        This function iterates through the controllers, finds the respective buffer, and ensures that all keyable,
        unlocked attributes in the buffer exist on the controller with the same properties (min, max, type, etc.).
        """
        for control_name in self.to_match:
            if not pmc.objExists(control_name):
                continue

            control = pmc.PyNode(control_name)
            buffer_name = control.name() + self.buffer_suffix

            if not pmc.objExists(buffer_name):
                continue

            buffer = pmc.PyNode(buffer_name)

            for buf in buffer.listAttr(keyable=True, unlocked=True):
                attr_name = buf.attrName()
                if attr_name not in self.ignore_attr and not pmc.hasAttr(control, attr_name):
                    attr_type = buf.type()  # Get attribute type
                    print(buf)
                    control.addAttr(attr_name, at=attr_type, k=True, h=False, min=buf.getMin(), max=buf.getMax())


def cleanup_transform_attributes(objects: Union[list, tuple, str, pmc.PyNode]):

    if not isinstance(objects, (list, tuple)):
        objects = [objects]

    attrs = ('translate',
             'rotate',
             'scale',
             'tx',
             'ty',
             'tz',
             'rx',
             'ry',
             'rz',
             'sx',
             'sy',
             'sz'
             )  # tuple so its immutable

    for obj in objects:
        if isinstance(obj, str):
            obj = pmc.PyNode(obj)

        for attr_name in attrs:
            attr_obj = obj.attr(attr_name)
            attr_obj.unlock()

            # Disconnect all inputs - more aggressive approach
            connections = attr_obj.inputs(plugs=True)
            for conn in connections[:]:  # Use slice copy to avoid iteration issues
                pmc.disconnectAttr(conn, attr_obj)

            attr_obj.setKeyable(True)


def move_attrs_to_bottom(node, attrs):
    """
    recreates each attribute so it appears last in the Channel Box.

    node   : name | PyNode
    attrs  : iterable of attr names or pm.Attribute
    """
    node = pmc.PyNode(node)
    for a in attrs:
        name = str(a).split('.')[-1]
        if not node.hasAttr(name):
            continue
        attr = node.attr(name)
        was_locked = attr.isLocked()
        if was_locked:
            attr.unlock()
        pmc.deleteAttr(attr)
        pmc.undo()
        if was_locked:
            node.attr(name).lock()


def list_attrs_with_prefix(node_name, prefix):
    """
    return attribute names on node_name that start with prefix

    Args:
        node_name:
        prefix:

    Returns:

    """
    node = pmc.PyNode(node_name)
    matching_attrs = []
    for attr in node.listAttr():
        name = attr.attrName()
        if name.startswith(prefix):
            matching_attrs.append(name)
    return matching_attrs