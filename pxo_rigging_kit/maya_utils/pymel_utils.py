# Author:     Johannes Wolz / Lead Rigging TD

"""
Utils code for optimize pymel to our needs.
Here we will create custom pymel node classes and pass it as virtual classes
into pymel for further use.
Really important are the dict PXO_UUID_DICT in the constants module.
Thats where we will store the pxo uuids as constant variables.
So we can use them in a lot of different modules.
If you want to create a new PXO node you have to inherit
the PxoBaseMetaNode class.
A __init__ is not allowed in your new class.
And you have to give the new node a unique pxo uuid.
You can generate that with the function generate_uuid_from_string()
from the core module.
Then you have to pass the new generated uuid to the PXO_UUID_DICT.
Finally you have to pass the constants variable in the UUID variable of the
your new class.
For detailed exploration pls read the code of PxoAssetAssemblyMetaNode class.
And the pymel github link:
https://github.com/LumaPictures/pymel/blob/master/examples/customClasses.py

To Do:

PxoAssetAssemblyMetaNode:
- The multiple work you have to do with the ModelComponent class in
  the model_utils and the population_from_dict is not good.
  Need to improve it.
- Keep the ModelComponent class in the model_utils in sync with the
  PxoAssetAssemblyMetaNode is stupid. Needs to be capsuled and simpler.
- The UUID creation workflow has to be improved and simplified.
- Json file import, export support.
- Last to new assemble comparison.
  To check which is the difference between model updates.

"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Import built-in modules
from builtins import object
from builtins import str
from builtins import super
import logging

# Import third-party modules
from future import standard_library
import maya.cmds as cmds
import pixo_paths
import pymel.all as pmc

# Import local modules
from pxo_rigging_kit import constants
from pxo_rigging_kit import core
from pxo_rigging_kit.maya_utils import attributes_utils
from pxo_rigging_kit.maya_utils import decorators
from pxo_rigging_kit.maya_utils import exceptions
from pxo_rigging_kit.maya_utils import model_utils
from pxo_rigging_kit.maya_utils import paths_utils
import pxo_rigging_kit.versioncontrol_utils as vctl

standard_library.install_aliases()

##########################################################
# GLOBAL
##########################################################

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)
DECORATORS = decorators.Decorators()
DECORATORS.debug = True
DECORATORS.logger = _LOGGER
CUSTOM_PXO_NODETYPES = ["network", "container", "dagContainer"]

##########################################################
# FUNCTIONS
##########################################################


def set_pxo_uuid(node, uuid_list=None):
    """
    Set the uuid string

    Args:
        uuid_(list): The uuid string list.

    """
    node.attr(constants.PXO_UUID_ATTR_NAME).unlock()
    current_value = [node.attr(constants.PXO_UUID_ATTR_NAME).get()]
    uuid_list = current_value + uuid_list
    uuid = process_pxo_uuid(uuid_list)
    node.attr(constants.PXO_UUID_ATTR_NAME).set(uuid)
    node.attr(constants.PXO_UUID_ATTR_NAME).lock()


@DECORATORS.x_timer
def get_pxo_uuid(node, as_representation=False):
    """
    Get the pxo uuid string.

    Args:
        node(pmc.PyNode()): The node to get the uuid from.
        as_representation(bool): Gives back the word representation of the uuid.
                                 Default is False.

    Result:
        Raise exceptions.PxoPymelNodeClassError
        if node to not have the pxo uuid attr.
        String: The pxo uuid as string.

    """
    if not node.hasAttr(constants.PXO_UUID_ATTR_NAME):
        raise exceptions.PxoPymelNodeClassError("Given node is no pxo node.")
    result = node.attr(constants.PXO_UUID_ATTR_NAME).get()
    if as_representation:
        result = result.split(constants.UUID_SEPERATOR)
        temp_list = []
        for uuid_ in result:
            for key, value in list(constants.PXO_UUID_DICT.items()):
                if uuid_ == value:
                    temp_list.append(key)
        result = ";".join(temp_list).replace(";", constants.UUID_SEPERATOR)
    return result


def process_pxo_uuid(uuid_list):
    """
    Stitch together a pxo uuid from given pxo uuids.

    Args:
        uuid_list(list): The uuid strings for stitching.

    """
    return r";".join(uuid_list).replace(";", constants.UUID_SEPERATOR)


@DECORATORS.x_timer
def get_custom_pxo_nodes_from_scene(nodes_types_list=None):
    """
    Get all custom nodes with the pxo_uuid attribute in the scene.

    Args:
        nodes_types_list(list): Node types to search for.
                                If None will take
                                CUSTOM_PXO_NODETYPES global var.

    Return:
        Empty list if fail.
        List:
            List of pmc.PyNode().

    """
    nodes_list = []
    if not nodes_types_list:
        nodes_types_list = CUSTOM_PXO_NODETYPES
    for node_type in nodes_types_list:
        nodes_list.extend(cmds.ls(typ=node_type))
    return [
        pmc.PyNode(node)
        for node in nodes_list
        if cmds.listAttr(node, ud=True)
        and constants.PXO_UUID_ATTR_NAME in cmds.listAttr(node, ud=True)
    ]


def get_list_item_by_str(search_string, in_items):
    """
    Filters through a list of pymel.core.PyNodes to find the node containing the search_string.
    Only first occurence will be returned.

    Args:
        search_string(str): String to search for, suggested format: '_fooBar_'
        in_items(list): List of pymel.core.PyNodes.

    Returns:
        pymel.core.PyNode: Node in list matching the search string.
    """
    string_items = [str(x.shortName()) for x in in_items if not isinstance(x, str)]
    matching_items = [x for x in string_items if search_string in x]

    if not matching_items:
        _LOGGER.warning(
            "{0} not found in {1}".format(search_string, ", ".join(string_items))
        )
        return

    if len(matching_items) > 1:
        _LOGGER.warning("multiple items matching the search_string found")

    return [pmc.PyNode(x) for x in matching_items][0]

##########################################################
# CLASSES
##########################################################


class PxoBaseNode(object):
    """
    The Pxo Base node class template.
    All new Pxo nodes should inherit these class.
    """

    UUID = ""
    DATA_BUNCH_ATTR_REF_NAME = "pxo_data_bunch_ref"

    @classmethod
    def add_pxo_uuid_attr(cls, obj):
        """
        Add the pxo uuid attr.

        Args:
            obj(pmc.PyNode()): The target node.

        """
        pmc.addAttr(
            obj,
            longName=constants.PXO_UUID_ATTR_NAME,
            niceName=constants.PXO_UUID_ATTR_NAME,
            type="string",
        )
        obj.attr(constants.PXO_UUID_ATTR_NAME).set(cls.UUID, lock=True)

    def _set_pxo_uuid(self, uuid_list=None):
        """
        Set the uuid string

        Args:
            uuid_list(list): The uuid strings.

        """
        set_pxo_uuid(self, uuid_list)

    def get_raw_pxo_uuid(self):
        """
        Get the raw uuid string.
        """
        return get_pxo_uuid(self)

    def get_pxo_uuid_representation(self):
        """
        Get the word representation of the pxo uuid.
        """
        return get_pxo_uuid(self, True)

    def add_data_bunch_ref_attr(self, value=""):
        """
        Add a string attribute which acts as reference attribute for further use.
        It will store component attribute names separated wit a "|".
        Attribute name is DATA_BUNCH_ATTR_REF_NAME.

        Args:
            value(string): Attributes name to store.

        """
        if not self.hasAttr(self.DATA_BUNCH_ATTR_REF_NAME):
            pmc.addAttr(
                self,
                longName=self.DATA_BUNCH_ATTR_REF_NAME,
                niceName=self.DATA_BUNCH_ATTR_REF_NAME,
                type="string",
            )
        attr_obj = self.attr(self.DATA_BUNCH_ATTR_REF_NAME)
        attr_obj.unlock()
        current_value = attr_obj.get()
        if current_value:
            value = "|".join([current_value, value])
        attr_obj.set(value)
        attr_obj.lock()

    def add_meta_data_from_dict(self, meta_data_dict):
        """
        Add meta data compound attr based on a meta data dict.

        Args:
            meta_data_dict(dict): The meta data dict.
                                  Which should look like this:
                                  {
                                    your_compound_attr_name: [
                                    {
                                        "longName": your_attr_name,
                                        "typ": your_attr_typ,
                                        "connect_attr": pmc.Attribute(this is optional),
                                    },
                                    {
                                        "longName": your_attr_name,
                                        "typ": your_attr_typ,
                                        "connect_attr": pmc.Attribute(this is optional),
                                    }
                                    ]
                                  }

        """
        meta_data_keys = list(meta_data_dict.keys())
        self.add_data_bunch_ref_attr("|".join(meta_data_keys))
        for key in meta_data_keys:
            meta_data_list = meta_data_dict[key]
            pmc.addAttr(
                self,
                longName=key,
                niceName=key,
                type="compound",
                numberOfChildren=len(meta_data_list),
            )
            for attr_data_dict in meta_data_list:
                temp_dict = attr_data_dict.copy()
                temp_dict.pop("connect_attr", None)
                temp_dict["parent"] = key
                temp_dict["keyable"] = False
                pmc.addAttr(self, **temp_dict)
            for attr_data_dict_ in meta_data_list:
                connect_attr = attr_data_dict_.get("connect_attr")
                if connect_attr:
                    connect_attr.connect(self.attr(attr_data_dict_["longName"]))

    def get_data_bunch_from_attr_name(self, name):
        """
        Gives a dict back stored as compound attribute on the node.

        Args:
            name(str): The compound attribute name.

        Return:
            Dict: {"attr_name":{"data_ports":"value"}}

        """
        data_ports = self.attr(name).children()
        return {
            name: {
                str(attr_.name(includeNode=False)): attr_.get() for attr_ in data_ports
            }
        }

    def get_data_bunch_from_bunch_ref_attr(self):
        """
        Get the whole meta data dict stored as compound attribute on the node.

        Return:
            Dict:
                {"attr_name":{"data_ports":"value"},
                "attr_name":{"data_ports":"value"}}
        """
        result = {}
        keys = str(self.attr(self.DATA_BUNCH_ATTR_REF_NAME).get()).split("|")
        for key in keys:
            result.update(self.get_data_bunch_from_attr_name(key))
        return result


class PxoContainerRigBaseNode(PxoBaseNode):
    # The UUID is essential for creation.
    # You have to set it here as static varibale.
    # You can get it from the constants module.
    # If you need a non existing UUID in the
    # constants module you have to generate before.
    # You find further information in the module docstring.
    CONTAINER_TYPE = "None"
    UUID = process_pxo_uuid(
        [
            constants.PXO_UUID_DICT["rig"],
            constants.PXO_UUID_DICT["container"],
        ]
    )

    IMAGE_PATH = pixo_paths.normalize(constants.PXO_RIG_ROOT_CONTAINER_LOGO_PATH)
    META_LOD_MASTER = constants.LOD_MASTER
    META_LOD_RIG = constants.LOD_RIG
    META_LOD_INDEX_ATTR = constants.LOD_INDEX_META_ATTR
    META_LOD_NAME_ATTR = constants.LOD_NAME_META_ATTR
    META_LOWEST_LOD_ATTR = constants.LOD_LOWEST_META_ATTR
    META_HIGHEST_LOD_ATTR = constants.LOD_HIGHEST_META_ATTR
    META_PXO_UNUSED_DAG_NODES_ATTR = constants.PXO_UNUSED_NODES_META_ATTR
    META_SCRIPT_NDS_ATTR = constants.SCRIPT_NODES_META_ATTR
    META_ASSET_ASSEMBLY_NAME = "asset_assembly"
    META_RIG_WIP_VERSION_ATTR_NAME = "rig_wip_version"
    META_ASSET_NAME_ATTR_NAME = "asset_name"
    META_GUIDE_VERSION_ATTR_NAME = constants.GUIDE_VERSION_ATTR_NAME
    META_RIG_WIP_PATH_ATTR_NAME = "rig_wip_path"
    META_RIG_PUBLISH_VERSION_NAME = "rig_publish_version"
    RIG_ROOT_META_DATA = {
        "pxo_rig_meta_data": [
            {"longName": META_ASSET_ASSEMBLY_NAME, "typ": "message"},
            {
                "longName": META_RIG_WIP_VERSION_ATTR_NAME,
                "typ": "long",
            },
            {"longName": META_ASSET_NAME_ATTR_NAME, "typ": "string"},
            {"longName": META_GUIDE_VERSION_ATTR_NAME, "typ": "long"},
            {"longName": META_RIG_WIP_PATH_ATTR_NAME, "typ": "string"},
            {"longName": META_RIG_PUBLISH_VERSION_NAME, "typ": "long"},
            {
                "longName": META_LOD_RIG,
                "typ": "bool",
            },
            {
                "longName": META_LOD_MASTER,
                "typ": "string",
            },
            {
                "longName": META_LOWEST_LOD_ATTR,
                "typ": "bool",
            },
            {
                "longName": META_HIGHEST_LOD_ATTR,
                "typ": "bool",
            },
            {
                "longName": META_LOD_INDEX_ATTR,
                "typ": "long",
            },
            {
                "longName": META_LOD_NAME_ATTR,
                "typ": "string",
            },
            {
                "longName": META_PXO_UNUSED_DAG_NODES_ATTR,
                "typ": "message",
                "multi": True,
            },
            {
                "longName": META_SCRIPT_NDS_ATTR,
                "typ": "message",
                "multi": True,
            },
        ],
    }
    META_SUB_CONTAINER_ATTR_NAMR = "sub_containers"
    RIG_SUB_CONTAINER_NAME = "RIG_SETUP"
    MODEL_ASSET_SUB_CONTAINER_NAME = "MODEL_ASSETS"
    XTRA_SUB_CONTAINER_NAME = "XTRA"
    NO_TRANSFORM_SUB_CONTAINER_NAME = "NO_TRANSFORM"
    RIG_ROOT_SUB_CONTAINERS = [
        RIG_SUB_CONTAINER_NAME,
        MODEL_ASSET_SUB_CONTAINER_NAME,
        XTRA_SUB_CONTAINER_NAME,
        NO_TRANSFORM_SUB_CONTAINER_NAME,
    ]
    ADVANCED_CONTAINER = False

    @classmethod
    def _isVirtual(cls, obj, name):
        """
        This actual creates the node. If a specific tag is found.
        If not it will create a default node.
        PyMEL code should not be used inside the callback,
        only API and maya.cmds.
        Args:
            obj(pmc.PyNode()): The network node.
            name(str): The nodes name.

        Return:
            True if node with tag exist.
            PxoPymelNodeClassError if fail.

        """
        fn = pmc.api.MFnDependencyNode(obj)
        try:
            if fn.hasAttribute(constants.PXO_UUID_ATTR_NAME):
                plug = fn.findPlug(constants.PXO_UUID_ATTR_NAME)
                if plug.asString() == cls.UUID:
                    return True
        except:
            raise exceptions.PxoPymelNodeClassError(
                "Can not create custom pymel node class."
                " Node with this tag {} is missing".format(constants.PXO_UUID_ATTR_NAME)
            )

    @classmethod
    def _preCreateVirtual(cls, **kwargs):
        """This is called before creation. python allowed."""
        return kwargs

    @classmethod
    def _postCreateVirtual(cls, obj):
        """
        This is called after creation, pymel/maya.cmds allowed.
        It will create a set of attributes. And the important check up tag for
        the meta node.

        Args:
            obj(str): The new created node.
                      This variable is passed by the
                      class automatically no need to give.
        """
        cls.add_pxo_uuid_attr(obj)
        cls.set_image(obj)
        obj.containerType.set(cls.CONTAINER_TYPE)
        obj.creator.set(paths_utils.get_user_name())
        obj.creationDate.set(" | ".join([vctl.get_date("/"), vctl.get_time(":")]))

    @classmethod
    def list(cls, *args, **kwargs):
        """ Returns all instances the node in the scene """

        kwargs["type"] = cls.__melnode__
        return [node for node in pmc.ls(*args, **kwargs) if isinstance(node, cls)]

    @classmethod
    def set_image(cls, obj, image_path=False):
        """
        Set the container image.

        Args:
            obj(pmc.PyNode): The container node.
            image_path(str): The image path.

        """
        if not image_path:
            image_path = cls.IMAGE_PATH
        obj.iconName.set(image_path)

    def set_black_box_mode(self, value):
        """
        Set container node to black box mode.
        """
        self.blackBox.set(value)

    def add_nodes(self, nodes_list, force=False):
        """
        Will add nodes from given list to the container.

        Args:
            nodes_list(list): The new container members.
            force(bool): If specified with -addNode, nodes will be
                         disconnected from their current containers before
                         they are added to new one.
                         Default is False.
        """
        self.addNode(nodes_list, it=True, isd=True, ish=True, ihb=True, iha=True, inc=True, force=force)

    def publish_nodes(self, nodes_list):
        """
        Publish given nodes from list.
        So it is available for user when the container is set to black box mode.

        Args:
            nodes_list(list): List with pymel nodes you want to make
                              available in black box mode.
        """
        for node in nodes_list:
            type_ = node.type()
            publish_name = str(node.name(long=True, stripNamespace=True)).replace("|", "_")
            pmc.containerPublish(self, publishNode=(publish_name, type_))
            pmc.containerPublish(self, bindNode=(publish_name, node))

    def set_meta_data(self):
        """
        Add the meta data attributes to the container node.
        """
        self.add_meta_data_from_dict(self.RIG_ROOT_META_DATA)

    def set_sub_containers(self):
        """
        Add the subcontainers meta data to root container node.
        """
        if self.ADVANCED_CONTAINER:
            sub_containers = [
                PxoContainerRigSubNode(name=sub_name)
                for sub_name in self.RIG_ROOT_SUB_CONTAINERS
            ]
        else:
            sub_containers = [
                PxoDagContainerRigSubNode(name=sub_name)
                for sub_name in self.RIG_ROOT_SUB_CONTAINERS
            ]
        self.add_nodes(sub_containers)
        sub_containers_temp_dict = {
            self.META_SUB_CONTAINER_ATTR_NAMR: [
                {
                    "longName": node.name(long=None),
                    "typ": "message",
                    "connect_attr": node.message,
                }
                for node in sub_containers
            ]
        }
        self.add_meta_data_from_dict(sub_containers_temp_dict)

    def set_meta_asset_name(self, name):
        """
        Set asset name as meta data.

        Args:
            name(str): Set value.
        """
        self.attr(self.META_ASSET_NAME_ATTR_NAME).set(name)

    def set_meta_asset_assembly_node(self, node):
        """
        Connect asset assembly node to container meta port.

        Args:
            node(pmc.PyNode): The asset asssembly node.
        """
        node.message.connect(self.attr(self.META_ASSET_ASSEMBLY_NAME))

    def set_meta_rig_wip_path(self, path):
        """
        Set the rig work in progress file path as meta data.

        Args:
            path(str): File path to set.
        """
        self.attr(self.META_RIG_WIP_PATH_ATTR_NAME).set(path)

    def set_meta_rig_wip_version(self, version):
        """
        Set rig work in progress version number as meta data.

        Args:
            version(int): The set value.
        """
        self.attr(self.META_RIG_WIP_VERSION_ATTR_NAME).set(version)

    def set_meta_rig_publish_version(self, version):
        """
        Set rig work publish version number as meta data.

        Args:
            version(int): The set value.
        """
        self.attr(self.META_RIG_PUBLISH_VERSION_NAME).set(version)

    def set_meta_guide_version(self, version):
        """
        Set rig guide version number as meta data.

        Args:
            version(int): The set value.
        """
        self.attr(self.META_GUIDE_VERSION_ATTR_NAME).set(version)

    def set_meta_lod_rig(self, value):
        """
        Define rig as lod rig on a bool meta attribute.

        Args:
            value(bool): True or False

        """
        self.attr(self.META_LOD_RIG).set(value)

    def set_meta_lod_master(self, path_str):
        """
        Set the lod master version path as sting in the meta data.

        Args:
            path_str(str): The path to the master rig version

        """
        self.attr(self.META_LOD_MASTER).set(path_str, type="string")

    def set_meta_lod_index(self, index):
        """
        Set rig lod index as meta data.

        Args:
            index(int): The set value.
        """
        self.attr(self.META_LOD_INDEX_ATTR).set(index)

    def set_meta_lod_name(self, name):
        """
        Set rig lod name as meta data.

        Args:
            name(str): The set name.
        """
        self.attr(self.META_LOD_NAME_ATTR).set(name)

    def set_meta_lowest_lod(self, value):
        """
        Set lowest lod meta data.

        Args:
            value(bool): The set value.
        """
        self.attr(self.META_LOWEST_LOD_ATTR).set(value)

    def set_meta_highest_lod(self, value):
        """
        Set highest lod meta data.

        Args:
            value(bool): The set value.
        """
        self.attr(self.META_HIGHEST_LOD_ATTR).set(value)

    def set_pxo_unused_nodes(self, nodes_list):
        """
        Connect given nodes to pxo unused nodes port as
        protection against the killing from the publish process.

        Args:
            nodes_list(list): List of pmc.PyNode()
        """
        attributes_utils.connect_multi_attributes(
            self, self.META_PXO_UNUSED_DAG_NODES_ATTR, nodes_list
        )

    def set_script_nodes(self, nodes_list):
        """
        Connect given script nodes with the meta data multi attribute.

        Args:
            nodes_list(list): List of pmc.PyNode()
        """
        attributes_utils.connect_multi_attributes(
            self, self.META_SCRIPT_NDS_ATTR, nodes_list
        )

    def get_rig_wip_path(self):
        """
        Get the rig working in progress file path.

        Return:
            String: The path.
        """
        return self.attr(self.META_RIG_WIP_VERSION_ATTR_NAME).get()

    def get_meta_data(self, meta_data_name):
        """
        Get all meta data by meta data name(compound attribute name).

        Return:
            List: The meta data stored in the attributes
                  of the compound attribute.
        """
        return self.attr(meta_data_name).get()

    def get_meta_asset_name(self):
        """
        Get the asset name from meta data.

        Return:
            String: The asset name.
        """
        return self.attr(self.META_ASSET_NAME_ATTR_NAME).get()

    def get_meta_asset_assembly_node(self):
        """
        Get the asset assembly node.

        Return:
            pmc.PyNode(): The asset assembly node.
        """
        return self.attr(self.META_ASSET_ASSEMBLY_NAME).get()

    def get_meta_rig_wip_version(self):
        """
        Get the rig work in progress version number:

        Return:
            Integer: The version.
        """
        return self.attr(self.META_RIG_WIP_VERSION_ATTR_NAME).get()

    def get_meta_rig_publish_version(self):
        """
        Get the rig publish version number:

        Return:
            Integer: The version.
        """
        return self.attr(self.META_RIG_PUBLISH_VERSION_NAME).get()

    def get_meta_guide_version(self):
        """
        Get the rig guide version number:

        Return:
            Integer: The version.
        """
        return self.attr(self.META_GUIDE_VERSION_ATTR_NAME).get()

    def get_meta_rig_wip_path(self):
        """
        Get the rig work in progress file path.

        Return:
            String: The path.
        """
        return self.attr(self.META_RIG_WIP_VERSION_ATTR_NAME).get()

    def get_meta_pxo_unused_nodes(self):
        """
        Get all connected nodes.

        Return:
            List: Filled with pmc.PyNode().
        """
        return self.attr(self.META_PXO_UNUSED_DAG_NODES_ATTR).get()

    def get_meta_script_nodes(self):
        """
        Get all connected nodes.

        Return:
            List: Filled with pmc.PyNode().
        """
        return self.attr(self.META_SCRIPT_NDS_ATTR).get()

    def get_subcontainer_by_str(self, string):
        if not string in self.RIG_ROOT_SUB_CONTAINERS:
            raise exceptions.PxoPymelNodeClassError("{} not exist as subcontainer.")
        return self.attr(string).get()


class PxoBaseMetaNode(pmc.nt.Network, PxoBaseNode):
    """
    Creates a network node which works as our base custom PXO MetaNode node.
    """

    # The UUID is essential for creation.
    # You have to set it here as static varibale.
    # You can get it from the constants module.
    # If you need a non existing UUID in the
    # constants module you have to generate before.
    # You find further information in the module docstring.
    UUID = constants.PXO_UUID_DICT["meta"]

    @classmethod
    def list(cls, *args, **kwargs):
        """ Returns all instances the node in the scene """

        kwargs["type"] = cls.__melnode__
        return [node for node in pmc.ls(*args, **kwargs) if isinstance(node, cls)]

    @classmethod
    def _isVirtual(cls, obj, name):
        """
        This actual creates the node. If a specific tag is found.
        If not it will create a default node.
        PyMEL code should not be used inside the callback,
        only API and maya.cmds.
        Args:
            obj(pmc.PyNode()): The network node.
            name(str): The nodes name.

        Return:
            True if node with tag exist.
            PxoPymelNodeClassError if fail.

        """
        fn = pmc.api.MFnDependencyNode(obj)
        try:
            if fn.hasAttribute(constants.PXO_UUID_ATTR_NAME):
                plug = fn.findPlug(constants.PXO_UUID_ATTR_NAME)
                if plug.asString() == cls.UUID:
                    return True
        except:
            raise exceptions.PxoPymelNodeClassError(
                "Can not create custom pymel node class."
                " Node with this tag {} is missing".format(constants.PXO_UUID_ATTR_NAME)
            )

    @classmethod
    def _preCreateVirtual(cls, **kwargs):
        """This is called before creation. python allowed."""
        return kwargs

    @classmethod
    def _postCreateVirtual(cls, obj):
        """
        This is called after creation, pymel/maya.cmds allowed.
        It will create a set of attributes. And the important check up tag for
        the meta node.

        Args:
            obj(str): The new created node.
                      This variable is passed by the
                      class automatically no need to give.
        """
        cls.add_pxo_uuid_attr(obj)
        obj.lock()

    def delete_(self):
        """
        Unlock and delete custom pxo_node.
        """
        self.unlock()
        pmc.delete(self)

    @DECORATORS.edit_locked_obj
    def set_locked_non_multi_attr(self, attr_obj, value):
        """
        Set value of non locked multi attribute.

        Args:
            attr_obj(pmc.Attribute): The Attribute to set.
            value(float, int, str): The value to set.

        """

        @DECORATORS.edit_locked_obj
        def execute(attr_obj_):
            attr_obj_.set(value)

        execute(attr_obj)

    @DECORATORS.edit_locked_obj
    def connect_locked_multi_attr(self, attr_obj, nodes_list):
        """
        Connect locked multi attribute with given nodes.

        Args:
            attr_obj(pmc.Attribute): The Attribute to connected with.
            nodes_list(list): The nodes to connect to the multi attribute.
                              Will take the message attribute of the node
                              and connect it with multi attribute index.

        """

        @DECORATORS.edit_locked_obj
        def execute(attr_obj_):
            for index, node in enumerate(nodes_list):
                node.message.connect(pmc.PyNode(attr_obj_[index]))

        execute(attr_obj)

    @DECORATORS.edit_locked_obj
    def connect_locked_attr(self, attr_obj, connect_attr_obj):
        """
        Connect given attribute with locked attribute.

        Args:
            attr_obj(pmc.Attribute): The target attribute to connect with.
            connect_attr_obj(pmc.Attribute): The source attribute to connect with.

        """

        @DECORATORS.edit_locked_obj
        def execute(attr_obj_):
            connect_attr_obj.connect(attr_obj_)

        execute(attr_obj)


class PxoAssetAssemblyMetaNode(PxoBaseMetaNode):
    """
    This will create a pxo asset assembly node for asset assembly
    data management during the rig build.
    """

    # The UUID is essential for creation.
    # You have to set it here as static variable.
    # You can get it from the constants module.
    # If you need a non existing UUID in the
    # constants module you have to generate it before.
    # You find further information in the module docstring.
    UUID = process_pxo_uuid(
        [
            constants.PXO_UUID_DICT["meta"],
            constants.PXO_UUID_DICT["rig"],
            constants.PXO_UUID_DICT["asset_assembly"],
        ]
    )
    # These are static variables for nodes attributes creation.
    # They have to be in sync with the ModelComponent class in the model_utils.
    # Thats stupid as well. Need a better way.
    ASSET_NAME = constants.PXO_ASSET_ASSEMBLY_NODE_ASSET_NAME_ATTR
    ASSET_ROOT = constants.PXO_ASSET_ASSEMBLY_NODE_ASSET_ROOT_NODE
    ASSEMBLED_ASSETS = constants.PXO_ASSET_ASSEMBLY_NODE_ASSEMBLED_ASSET_ATTR
    COMPONENTS = constants.PXO_ASSET_ASSEMBLY_NODE_COMPONENTS_ATTR_SUFFIX
    INVALID_COMPONENTS = constants.PXO_ASSET_ASSEMBLY_NODE_INVALID_COMP_ATTR_SUFFIX
    VERSION = constants.PXO_ASSET_ASSEMBLY_NODE_VERSION_ATTR
    PUBLISH_PATH = constants.PXO_ASSET_ASSEMBLY_NODE_ASSET_PUBLISH_PATH
    COMPONENTS_ROOT = constants.PXO_ASSET_ASSEMBLY_NODE_COMPONENTS_ROOT_ATTR_SUFFIX
    TAGGED_GEO = constants.PXO_ASSET_ASSEMBLY_NODE_TAGGED_GEO_ATTR_NAME
    USE_KEY_REGEX = constants.PXO_ASSET_ASSEMBLY_NODE_USE_KEY_REGEX_ATTR_NAME
    INVALID_SUFFIX = constants.PXO_ASSET_ASSEMBLY_NODE_INVALID_COMP_ATTR_SUFFIX
    RESOLUTION = constants.PXO_ASSET_ASSEMBLY_NODE_RESOLUTION_NAME_ATTR
    # Default attributes
    # When insert a new attribute here i have to change the index order in
    # get_assembly_data() method. This is stupid. Need a better way.
    # They should be automatic in sync.
    DEFAULT_ATTRIBUTES = [
        {"longName": ASSET_NAME, "type": "string", "parent": None, "multi": False},
        {"longName": VERSION, "type": "long", "parent": None, "multi": False},
        {"longName": PUBLISH_PATH, "type": "string", "parent": None, "multi": False},
        {"longName": ASSET_ROOT, "type": "message", "parent": None, "multi": False},
        {
            "longName": TAGGED_GEO,
            "type": "bool",
            "parent": None,
            "keyable": False,
            "multi": False
        },
        {
            "longName": USE_KEY_REGEX,
            "type": "bool",
            "parent": None,
            "keyable": False,
            "multi": False
        },
        {
            "longName": RESOLUTION,
            "type": "message",
            "parent": None,
            "keyable": False,
            "multi": True
        }
    ]
    ASSET_ATTR_SUFFIX = "asset"

    @DECORATORS.x_timer
    def populate_from_data_list(self, data_list, connect=True):
        """
        Populate the node with given data from data list.
        Will create all needed attributes dynamically.

        Args:
            data_list(list): The data list. List is filled with data dictionaries.
                             Example:
                            [{'asset_name': 'crt_vhagar_mdl',
                              'asset_root': nt.PxoAsset(u'crt_vhagar_mdl'),
                              'components': {'arm': {nt.Transform(u'crt_vhagar_mdl|mid|arm'):
                                                    [nt.Transform(u'crt_vhagar_mdl|mid|arm|pSphere3')]},
                                             'body': {nt.Transform(u'crt_vhagar_mdl|low|body'):
                                                     [nt.Transform(u'crt_vhagar_mdl|low|body|pSphere1')]},
                                             'head': {nt.Transform(u'crt_vhagar_mdl|mid|head'):
                                                     [nt.Transform(u'crt_vhagar_mdl|mid|head|pSphere2')]}},
                              'publish_path': 'not found from scene list',
                              'tagged_geo': False,
                              'use_key_regex': False,
                              'version': 0}]
            connect(bool): Connect with given nodes from data_dict.
                           Default is True.

        """
        # The whole code below has to be more dynamic. Is to hard coded.
        self.unlock()
        asset_names = [data_dict[self.ASSET_NAME] for data_dict in data_list]
        dupl_asset_name = core.get_duplicates_in_list(asset_names)
        if dupl_asset_name:
            raise exceptions.PxoModelAssetError(
                "{} exist more then ones. This is invalid. Pls remove.".format(
                    dupl_asset_name
                )
            )
        if not attributes_utils.has_attr(self, self.ASSEMBLED_ASSETS):
            cmds.addAttr(
                self.name(),
                longName=self.ASSEMBLED_ASSETS,
                at="compound",
                numberOfChildren=len(data_list),
            )
        for index in range(len(data_list)):
            data_dict_ = data_list[index]
            asset_name = data_dict_[self.ASSET_NAME]
            asset_components = list(data_dict_[self.COMPONENTS].keys())
            invalid_components = data_dict_.get(self.INVALID_COMPONENTS)
            invalid_components_count = 0
            if invalid_components:
                invalid_components = list(data_dict_[self.INVALID_COMPONENTS].keys())
                invalid_components_count = len(invalid_components)
            cmds.addAttr(
                self.name(),
                longName=asset_name,
                at="compound",
                numberOfChildren=len(self.DEFAULT_ATTRIBUTES)
                + (len(asset_components) * 2)
                + (invalid_components_count * 2),
                parent=self.ASSEMBLED_ASSETS,
            )
            for attr_dict in self.DEFAULT_ATTRIBUTES:
                temp_dict = attr_dict.copy()
                temp_dict["parent"] = asset_name
                temp_dict["longName"] = "{}_{}_{}".format(
                    self.ASSET_ATTR_SUFFIX, index, attr_dict["longName"]
                )
                try:
                    cmds.addAttr(
                        self.name(),
                        longName=temp_dict["longName"],
                        at=temp_dict["type"],
                        parent=temp_dict["parent"],
                        multi= temp_dict["multi"]
                    )
                except:
                    cmds.addAttr(
                        self.name(),
                        longName=temp_dict["longName"],
                        dt=temp_dict["type"],
                        parent=temp_dict["parent"],
                        multi= temp_dict["multi"]
                    )
            # This part can be summarized in function in this method.
            # And maybe deleted because we get the components right away from the ModelComponents class and not
            # really from the node connections. But we leave it as it is for now maybe we find a usage for it.
            for component in asset_components:
                cmds.addAttr(
                    self.name(),
                    longName="{}_{}_{}_{}".format(
                        self.ASSET_ATTR_SUFFIX,
                        index,
                        component.replace(":", "_"),
                        self.COMPONENTS_ROOT,
                    ),
                    at="message",
                    parent=asset_name,
                )
                cmds.addAttr(
                    self.name(),
                    longName="{}_{}_{}_{}".format(
                        self.ASSET_ATTR_SUFFIX,
                        index,
                        component.replace(":", "_"),
                        self.COMPONENTS,
                    ),
                    at="message",
                    multi=True,
                    parent=asset_name,
                )
            if invalid_components:
                for invalid_component in invalid_components:
                    self.addAttr(
                        self.name(),
                        longName="{}_{}_{}_{}_{}".format(
                            self.ASSET_ATTR_SUFFIX,
                            index,
                            invalid_component.replace(":", "_"),
                            self.COMPONENTS_ROOT,
                            self.INVALID_SUFFIX,
                        ),
                        at="message",
                        parent=asset_name,
                    )
                    self.addAttr(
                        self.name(),
                        longName="{}_{}_{}_{}_{}".format(
                            self.ASSET_ATTR_SUFFIX,
                            index,
                            invalid_component.replace(":", "_"),
                            self.COMPONENTS,
                            self.INVALID_SUFFIX,
                        ),
                        at="message",
                        multi=True,
                        parent=asset_name,
                    )
        if connect:
            for index__, data_dict__ in enumerate(data_list):
                asset_name_ = data_dict__[self.ASSET_NAME]
                asset_components_ = list(data_dict__[self.COMPONENTS].keys())
                invalid_components_ = data_dict__.get(self.INVALID_COMPONENTS)
                resolution_groups = data_dict__[self.RESOLUTION]
                root_attr = self.attr(self.ASSEMBLED_ASSETS).attr(asset_name_)
                root_attr.attr(
                    "{}_{}_{}".format(self.ASSET_ATTR_SUFFIX, index__, self.ASSET_NAME)
                ).set(asset_name_)
                root_attr.attr(
                    "{}_{}_{}".format(self.ASSET_ATTR_SUFFIX, index__, self.VERSION)
                ).set(data_dict__[self.VERSION])
                root_attr.attr(
                    "{}_{}_{}".format(
                        self.ASSET_ATTR_SUFFIX, index__, self.PUBLISH_PATH
                    )
                ).set(data_dict__[self.PUBLISH_PATH])
                data_dict__[self.ASSET_ROOT].message.connect(
                    self.attr(self.ASSEMBLED_ASSETS)
                    .attr(asset_name_)
                    .attr(
                        "{}_{}_{}".format(
                            self.ASSET_ATTR_SUFFIX, index__, self.ASSET_ROOT
                        )
                    )
                )
                root_attr.attr(
                    "{}_{}_{}".format(self.ASSET_ATTR_SUFFIX, index__, self.TAGGED_GEO)
                ).set(data_dict__[self.TAGGED_GEO])
                root_attr.attr(
                    "{}_{}_{}".format(
                        self.ASSET_ATTR_SUFFIX, index__, self.USE_KEY_REGEX
                    )
                ).set(data_dict__[self.USE_KEY_REGEX])
                if resolution_groups:
                    for node_index, node in enumerate(resolution_groups):
                        node.message.connect(root_attr.attr("{}_{}_{}".format(self.ASSET_ATTR_SUFFIX, index__, self.RESOLUTION))[node_index])
                # This part can be summarized in function in this method.
                # And maybe deleted because we get the components right away from the ModelComponents class and not
                # really from the node connections. But we leave it as it is for now maybe we find a usage for it.
                for component_ in asset_components_:
                    component_root = list(
                        data_dict__[self.COMPONENTS][component_].keys()
                    )[0]
                    component_root.message.connect(
                        root_attr.attr(
                            "{}_{}_{}_{}".format(
                                self.ASSET_ATTR_SUFFIX,
                                index__,
                                component_.replace(":", "_"),
                                self.COMPONENTS_ROOT,
                            )
                        )
                    )
                    component_nodes = data_dict__[self.COMPONENTS][component_][
                        component_root
                    ]
                    for index, node in enumerate(component_nodes):
                        node.message.connect(
                            root_attr.attr(
                                "{}_{}_{}_{}".format(
                                    self.ASSET_ATTR_SUFFIX,
                                    index__,
                                    component_.replace(":", "_"),
                                    self.COMPONENTS,
                                )
                            )[index]
                        )
                if invalid_components_:
                    invalid_components_ = list(
                        data_dict__[self.INVALID_COMPONENTS].keys()
                    )
                    for invalid_component_ in invalid_components_:
                        invalid_component_root = list(
                            data_dict__[self.INVALID_COMPONENTS][
                                invalid_component_
                            ].keys()
                        )[0]
                        invalid_component_root.message.connect(
                            root_attr.attr(
                                "{}_{}_{}_{}_{}".format(
                                    self.ASSET_ATTR_SUFFIX,
                                    index__,
                                    invalid_component_.replace(":", "_"),
                                    self.COMPONENTS_ROOT,
                                    self.INVALID_SUFFIX,
                                )
                            )
                        )
                        invalid_component_nodes = data_dict__[self.INVALID_COMPONENTS][
                            invalid_component_
                        ][invalid_component_root]
                        for index, node in enumerate(invalid_component_nodes):
                            node.message.connect(
                                root_attr.attr(
                                    "{}_{}_{}_{}_{}".format(
                                        self.ASSET_ATTR_SUFFIX,
                                        index__,
                                        invalid_component_.replace(":", "_"),
                                        self.COMPONENTS,
                                        self.INVALID_SUFFIX,
                                    )
                                )[index]
                            )
        self.lock()

    def get_assembly_data(self, as_PyNodes=True):
        """
        Get the assembled data.

        Return:
            List: List filled with data dictionaries.

        """
        result_list = []
        assembled_assets = self.attr(self.ASSEMBLED_ASSETS).children()
        for asset_attr in assembled_assets:
            port_children_attributes = asset_attr.children()
            # This part has to be optimized. More dynamically.
            # Going over list index is a kind of hard coded.
            asset_name = port_children_attributes[0].get()
            version = port_children_attributes[1].get()
            publish_path = port_children_attributes[2].get()
            asset_root = port_children_attributes[3].get()
            tagged_geo = port_children_attributes[4].get()
            use_key_regex = port_children_attributes[5].get()
            model_component_instance = model_utils.ModelComponents(asset_root, asset_name, version, publish_path, tagged_geo,
                                                       use_key_regex)
            result_list.append(model_component_instance.__dict__(as_PyNodes))
        return result_list


# Establish this node just for backwards compatibility.
# For the old LOD workflow.
# This will be exchanged with
class PxoRigMetaNode(PxoBaseMetaNode):
    # The UUID is essential for creation.
    # You have to set it here as static variable.
    # You can get it from the constants module.
    # If you need a non existing UUID in the
    # constants module you have to generate it before.
    # You find further information in the module docstring.
    UUID = process_pxo_uuid(
        [
            constants.PXO_UUID_DICT["meta"],
            constants.PXO_UUID_DICT["rig"],
        ]
    )
    RIG_ROOT_ND_ATTR = {"longName": constants.RIG_ROOT_ATTR, "typ": "message"}
    LOD_INDEX_ATTR = {"longName": constants.LOD_INDEX_META_ATTR, "typ": "long"}
    LOD_NAME_ATTR = {"longName": constants.LOD_NAME_META_ATTR, "typ": "string"}
    LOWEST_LOD_ATTR = {
        "longName": constants.LOD_LOWEST_META_ATTR,
        "typ": "bool",
    }
    HIGHEST_LOD_ATTR = {
        "longName": constants.LOD_HIGHEST_META_ATTR,
        "typ": "bool",
    }
    PXO_UNUSED_DAG_NODES = {
        "longName": constants.PXO_UNUSED_NODES_META_ATTR,
        "typ": "message",
        "multi": True,
    }
    SCRIPT_NDS_ATTR = {
        "longName": constants.SCRIPT_NODES_META_ATTR,
        "typ": "message",
        "multi": True,
    }

    @classmethod
    def _postCreateVirtual(cls, obj):
        super(PxoRigMetaNode, cls)._postCreateVirtual(obj)
        obj.unlock()
        for attr_dict in [
            cls.LOD_INDEX_ATTR,
            cls.LOD_NAME_ATTR,
            cls.LOWEST_LOD_ATTR,
            cls.HIGHEST_LOD_ATTR,
            cls.PXO_UNUSED_DAG_NODES,
            cls.SCRIPT_NDS_ATTR,
            cls.RIG_ROOT_ND_ATTR,
        ]:
            pmc.addAttr(obj, **attr_dict)
            obj.attr(attr_dict["longName"]).lock()
        obj.lock()

    def set_lod_index(self, value):
        """
        Set lod index.

        Args:
            value(int): The lod index.

        """
        self.set_locked_non_multi_attr(
            self.attr(self.LOD_INDEX_ATTR["longName"]), value
        )

    def set_lod_name(self, value):
        """
        Set the lod name.

        Args:
            value(str): The lod name.
        """
        self.set_locked_non_multi_attr(self.attr(self.LOD_NAME_ATTR["longName"]), value)

    def set_lowest_lod(self, value):
        """
        Set to lowest lod.

        Args:
            value(bool): Set it to lowest lod.

        """
        self.set_locked_non_multi_attr(
            self.attr(self.LOWEST_LOD_ATTR["longName"]), value
        )

    def set_highest_lod(self, value):
        """
        Set to highest lod.

        Args:
            value(bool): Set it to highest lod.

        """
        self.set_locked_non_multi_attr(
            self.attr(self.HIGHEST_LOD_ATTR["longName"]), value
        )

    def set_pxo_unused_dag_nodes(self, nodes_list):
        """
        Connect given nodes to unused dag nodes multi attribute.
        To prevent from killing during publish.

        Args:
            nodes_list(list): The nodes to safe protection from killing.

        """
        self.connect_locked_multi_attr(
            self.attr(self.PXO_UNUSED_DAG_NODES["longName"]), nodes_list
        )

    def set_script_nodes(self, nodes_list):
        """
        Connect given script nodes to script_nodes multi attribute.
        """
        self.connect_locked_multi_attr(
            self.attr(self.SCRIPT_NDS_ATTR["longName"]), nodes_list
        )

    def set_rig_root_nd(self, node):
        """
        Connect rig root node message attribute with meta nd.
        """
        self.connect_locked_attr(
            self.attr(self.RIG_ROOT_ND_ATTR["longName"]), node.message
        )

    def get_rig_root_nd(self):
        """
        Get rig root node from meta node.
        """
        return self.attr(constants.RIG_ROOT_ATTR).get()


class PxoContainerRigRootNode(pmc.nt.Container, PxoContainerRigBaseNode):
    """
    Creates a network node which works as our base custom PXO MetaNode node.
    """

    # The UUID is essential for creation.
    # You have to set it here as static variable.
    # You can get it from the constants module.
    # If you need a non existing UUID in the
    # constants module you have to generate before.
    # You find further information in the module docstring.
    CONTAINER_TYPE = "root"
    UUID = process_pxo_uuid(
        [constants.PXO_UUID_DICT[CONTAINER_TYPE], PxoContainerRigBaseNode.UUID]
    )
    ADVANCED_CONTAINER = True


class PxoDagContainerRigRootNode(pmc.nt.DagContainer, PxoContainerRigBaseNode):
    """
    Creates a Dag Container node as our rig root node.
    """

    # The UUID is essential for creation.
    # You have to set it here as static variable.
    # You can get it from the constants module.
    # If you need a non existing UUID in the
    # constants module you have to generate before.
    # You find further information in the module docstring.
    CONTAINER_TYPE = "root"
    UUID = process_pxo_uuid(
        [constants.PXO_UUID_DICT[CONTAINER_TYPE], PxoContainerRigBaseNode.UUID]
    )

    def add_nodes(self, nodes_list, force=False):
        pmc.parent(nodes_list, self)

    def getSubcontainers(self):
        return [
            node
            for node in self.getChildren()
            if node.type() == "transform" or node.type() == "dagContainer"
        ]

    def getNodeList(self):
        return self.getChildren(ad=True)

    @classmethod
    def _postCreateVirtual(cls, obj):
        super(PxoDagContainerRigRootNode, cls)._postCreateVirtual(obj)
        for channel in ["translate", "rotate", "scale"]:
            for axe in ["X", "Y", "Z"]:
                obj.attr("{}{}".format(channel, axe)).set(keyable=False, lock=True)


class PxoContainerRigSubNode(PxoContainerRigRootNode):
    # The UUID is essential for creation.
    # You have to set it here as static variable.
    # You can get it from the constants module.
    # If you need a non existing UUID in the
    # constants module you have to generate before.
    # You find further information in the module docstring.
    CONTAINER_TYPE = "sub"
    UUID = process_pxo_uuid(
        [constants.PXO_UUID_DICT[CONTAINER_TYPE], PxoContainerRigBaseNode.UUID]
    )
    IMAGE_PATH = pixo_paths.normalize(constants.PXO_RIG_SUB_CONTAINER_LOGO_PATH)


class PxoDagContainerRigSubNode(PxoDagContainerRigRootNode):
    # The UUID is essential for creation.
    # You have to set it here as static variable.
    # You can get it from the constants module.
    # If you need a non existing UUID in the
    # constants module you have to generate before.
    # You find further information in the module docstring.
    CONTAINER_TYPE = "sub"
    UUID = process_pxo_uuid(
        [constants.PXO_UUID_DICT[CONTAINER_TYPE], PxoContainerRigBaseNode.UUID]
    )
    IMAGE_PATH = pixo_paths.normalize(constants.PXO_RIG_SUB_CONTAINER_LOGO_PATH)




##########################################################
# REGISTER VIRTUAL CLASSES IN PYMEL
##########################################################

pmc.factories.registerVirtualClass(PxoBaseMetaNode, nameRequired=False)
pmc.factories.registerVirtualClass(PxoAssetAssemblyMetaNode, nameRequired=False)
pmc.factories.registerVirtualClass(PxoContainerRigRootNode, nameRequired=False)
pmc.factories.registerVirtualClass(PxoDagContainerRigRootNode, nameRequired=False)
pmc.factories.registerVirtualClass(PxoContainerRigSubNode, nameRequired=False)
pmc.factories.registerVirtualClass(PxoDagContainerRigSubNode, nameRequired=False)
pmc.factories.registerVirtualClass(PxoRigMetaNode, nameRequired=False)