# Import built-in modules
from abc import ABC
from abc import abstractmethod
from importlib import reload
import logging
from typing import Optional


# Import third-party modules
from future import standard_library
from maya import cmds

# Import local modules
from pxo_rigging_kit import constants
from pxo_rigging_kit.maya_utils import decorators
from pxo_rigging_kit.maya_utils import openmaya_utils
from pxo_rigging_kit.maya_utils import attributes_utils
from pxo_rigging_kit.maya_utils.rigging import curves_utils

from pxo_rigging_kit.maya_utils.EWAW_rs import matrix_maths, node
from pxo_rigging_kit.maya_utils.EWAW_rs.base_constructs import data

reload(constants)
reload(matrix_maths)
reload(data)
reload(curves_utils)
reload(attributes_utils)
reload(openmaya_utils)
reload(decorators)

##########################################################
# GLOBALS
##########################################################

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)

DECORATORS = decorators.Decorators()
DECORATORS.debug = True
DECORATORS.logger = _LOGGER

standard_library.install_aliases()


##########################################################
# FUNCTIONS
##########################################################


class BaseModule(ABC):

    MODULE_SUFFIX = "GRP"
    is_built = False

    _module_side = "C"
    _module_name = "default"
    _module_index = 0
    _module_parent = None
    _connectable_attributes = None

    def __init__(
            self,

            data_container: Optional[data.DataContainer] = None


    ):
        """
        This class is the master class for our rigging modules.


        """

        # here we build up a default data from the input of the class itself
        # usually this should never come to flourish because we are using data from operators or dictionaries
        # this is just for savekeeping and testing

        # this is where the data does data things :)
        self.data = data_container

        self.host_ctrl = None
        self.all_controls = list()
        self.deformers = list()

        self.data.is_module = True
        self.data.is_operator = False

    # this needs to become its own classmethod or something,
    # it's very tricky to figure out what to do with this
    def _scene_rename(self, old_substring, new_substring):
        if not self.is_built:
            return

        for sub_module in self.sub_modules:
            cmds.rename(f"{sub_module.replace(new_substring, old_substring)}",
                        f"{sub_module.replace(old_substring, new_substring)}")

    @staticmethod
    def _create_module_subnode(module_subgroup: str, ) -> str:
        """

        Args:
            module_subgroup(str):

        Returns:
            Str: the created name of the subgroup
        """
        module_subgroup = cmds.createNode("transform", n=module_subgroup, )

        cmds.addAttr(module_subgroup, ln=constants.EWAW_MD_SUB_TAG, at="bool", dv=True)

        return module_subgroup

    def create_module_base(self):

        if not self.data.comp_host_name:
            HostCreator_ = curves_utils.HostControl()
            self.host_ctrl = HostCreator_.create_curve(name=f"{self.data.comp_composed_name}_Host_ctrl",
                                                       buffer_grp=False,
                                                       scale=(.1, .1, .1,),
                                                       move=(10., 12., .0),
                                                       lock_translate=True,
                                                       lock_rotate=True,
                                                       lock_scale=True,
                                                       lock_visibility=True,
                                                       color_index=self.data.primary_color,
                                                       )

        else:
            self.host_ctrl = self.data.comp_host_name

        self.all_controls.append(self.host_ctrl)

        attributes_utils.add_pxo_separator_attr(self.host_ctrl,
                                                attr_name=f"{self.data.comp_composed_name}_visibility_control",
                                                as_pymel=False,
                                                niceName=f"{self.data.comp_composed_name}_vis")

        for module_subgroup, data__ in self.data.sub_modules.items():
            self._create_module_subnode(module_subgroup)

            parenting_info = data__.get("parent")

            if parenting_info:
                cmds.parent(module_subgroup, parenting_info)

            outliner_info = data__.get("outliner_color")

            if outliner_info:
                cmds.setAttr(f"{module_subgroup}.useOutlinerColor", True)

                for channel_num_, clr_ in enumerate("RGB"):
                    cmds.setAttr(f"{module_subgroup}.outlinerColor{clr_}", outliner_info[channel_num_])

            if module_subgroup != self.data.module_grp_name and self.host_ctrl:
                visibility_name = f"{module_subgroup.split('_')[-2]}_visibility"

                # check if the attribute name would clash with a preexisting attribute
                # this can happen if multiple modules are referring to the same host
                # we then are using the module name too in the longname
                if cmds.attributeQuery(visibility_name, n=self.host_ctrl, exists=True):
                    attr_ = node.addAttr(self.host_ctrl,
                                         nn=visibility_name,
                                         ln=f"{self.data.comp_composed_name}_{visibility_name}",
                                         at="bool",
                                         k=True,
                                         dv=True,
                                         )

                    _LOGGER.warning(f"{visibility_name} was already existing on {self.host_ctrl}, "
                                    f"used {self.data.comp_composed_name}_{visibility_name} instead")

                else:
                    attr_ = node.addAttr(self.host_ctrl,
                                         nn=visibility_name,
                                         ln=visibility_name,
                                         at="bool",
                                         k=True,
                                         dv=True,
                                         )

                cmds.connectAttr(attr_, f"{module_subgroup}.visibility")

        attributes_utils.add_pxo_separator_attr(self.host_ctrl,
                                                attr_name=f"{self.data.comp_composed_name}_module_specific",
                                                as_pymel=False,
                                                niceName=f"{self.data.comp_composed_name}_specs")

        self.connector_name = node.addAttr(f"{self.data.input_grp_name}",
                                           ln="op_connector",
                                           dt="matrix",
                                           )

        # if the host was NOT previously connected, connect the host.
        if not cmds.listConnections(f"{self.host_ctrl}.offsetParentMatrix"):

            cmds.parent(self.host_ctrl,
                        self.data.module_grp_name
                        )

            cmds.connectAttr(self.connector_name,
                             f"{self.host_ctrl}.offsetParentMatrix",
                             f=True,
                             )

    @abstractmethod
    def create_inputs(self):
        pass

    @abstractmethod
    def create_calculations(self):
        pass

    @abstractmethod
    def create_controls(self):
        pass

    @abstractmethod
    def create_outputs(self):
        pass

    @DECORATORS.refresh_suspended()
    @DECORATORS.disable_isolate_select_update()
    @DECORATORS.disable_node_editor_update()
    def build(self):
        """
        building module from operator.

        """

        if self.data.is_built:
            raise RuntimeError(f"{self.data.comp_composed_name} has been built!")

        if cmds.objExists(self.data.module_grp_name):

            raise RuntimeError(f"{self.data.module_grp_name} already exists in the scene.\n"
                               f"Change the data to build anew, or delete the Module.")

        _LOGGER.info(f"operation starting with module: {self.data.comp_type} on {self.data.comp_composed_name}")

        self.create_module_base()

        self.create_inputs()

        self.create_controls()

        self.create_calculations()

        self.create_outputs()

        self.connect()

        self.data.is_built = True

        data_ = self.data.data_to_dict()

        data.dict_to_node(node_name=self.data.module_grp_name,
                          data_dict=data_,
                          )

        _LOGGER.info(f"operation finished with module: {self.data.comp_type} on {self.data.comp_composed_name}")

    @abstractmethod
    def connect(self):
        """
        connects the module to the one above based on data fed into and out of both <3.

        """
        pass

    @abstractmethod
    def disconnect(self):
        """
        disconnects the module from the one above based on data fed into and out of both <3.

        """

        pass

    def unbuild(self):
        """
        Killing the module and reverting to operator.

        """

        if not self.data.is_built:
            _LOGGER.error(f"{self.data.comp_composed_name} has not the 'is_built' attribute."
                          f"Therefore it's assumed it was not built yet.")

        cmds.delete(*list(self.data.sub_modules))

        # this was done before the idea of container came up
        affiliated_node_it = openmaya_utils.get_tagged_nodes(tag=self.data.comp_composed_name)
        affiliated_node_names = tuple(affiliated_node_it)

        if affiliated_node_names:
            cmds.delete(*affiliated_node_names)

        self.data.is_built = False

    def __dict__(self):
        return self.data.data_to_dict()
