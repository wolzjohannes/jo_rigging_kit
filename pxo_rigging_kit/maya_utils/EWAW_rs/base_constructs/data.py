import importlib
import importlib.util
import sys

import inspect
import math
import pathlib
from copy import deepcopy
from importlib import reload
import typing
from pprint import pprint, pformat

from future import standard_library

import logging
from typing import Optional, Any, Union
from dataclasses import dataclass, asdict, field

from maya import cmds
from pymel import core as pmc

from pxo_rigging_kit import constants
from pxo_rigging_kit.maya_utils import openmaya_utils

from pxo_rigging_kit.maya_utils.EWAW_rs import node
from pxo_rigging_kit.maya_utils.EWAW_rs import matrix_maths
from pxo_rigging_kit.maya_utils.EWAW_rs.base_constructs import operator

from pxo_rigging_kit.maya_utils.rigging import rig_utils
from pxo_rigging_kit.io_version_control.version_io import ImportExport

reload(matrix_maths)
reload(constants)
reload(openmaya_utils)
reload(rig_utils)

##########################################################
# GLOBALS
##########################################################

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)
standard_library.install_aliases()


class DataclassProperty(property):
    def __set__(self, obj, value):
        if isinstance(value, property):
            # dataclasses tries to set a default and uses the
            # getattr(cls, name). But the real default will come
            # from: `_attr = field(..., default=...)`.
            return
        super().__set__(obj, value)


@dataclass
class DataContainer:
    """

    """
    # those values are needed so the property setter can find private values
    # those private values will NOT show up in the dictionary representations etc
    # we need these to set the INIT to False, if the init is False those Values will not be called
    # we need default values on those, because PRE PY3.10 we can not make the kwargs and args save

    # the metadata is still in consideration with it i want to give the dicts information about the attribues
    _comp_name: str = field(default="EWAW", init=False, repr=False)
    _comp_type: str = field(default="EWAW", init=False, repr=False)
    _comp_index: int = field(default=0, init=False, repr=False)
    _connectable_attributes: Optional[str] = field(default_factory=list, init=False, repr=False)
    _comp_subplacement_names: Optional[Union[tuple, int]] = field(default_factory=tuple, init=False, repr=False)
    _comp_lra_names: Optional[Union[tuple, int]] = field(default_factory=tuple, init=False, repr=False)
    _comp_side: str = field(default="C", init=False, repr=False)
    _connector: str = field(default="", init=False, repr=False)
    _module_parent: str = field(default="", init=False, repr=False)

    _is_operator: bool = field(default=False, init=False, repr=False)
    _is_module: bool = field(default=False, init=False, repr=False)

    _is_built: bool = field(default=False, init=False, repr=False)

    _try_to_update: bool = field(default=False, init=False, repr=False)

    #
    #
    # the data we have, know and love
    build_layer: int = field(default=0,
                             repr=True,
                             init=True,
                             )

    is_operator: bool = field(default=None,
                              repr=True,
                              init=True,
                              )

    is_module: bool = field(default=None,
                            repr=True,
                            init=True,
                            )

    is_built: bool = field(default=False,
                           repr=True,
                           init=True,
                           )

    comp_type:  str = field(default="defaultCompType",
                            repr=True,
                            init=True,
                            )

    build_axis: str = field(default="-Y",
                            repr=True,
                            init=True,
                            )

    comp_index: int = field(default=0,
                            repr=True,
                            init=True,
                            )

    comp_name:  str = field(default="defaultCompName",
                            repr=True,
                            init=True,
                            )

    comp_parent_name:  str = field(default="defaultCompName",
                                   repr=True,
                                   init=True,
                                   )

    comp_host_name:  str = field(default="defaultCompHostName",
                                 repr=True,
                                 init=True,
                                 )

    comp_spaces_names:  str = field(default="",
                                    repr=True,
                                    init=True,
                                    )

    op_name:  str = field(default="defaultCompName",
                          repr=True,
                          init=True,
                          )

    comp_side:  str = field(default="defaultCompSide",
                            repr=True,
                            init=True,
                            )

    # these should be mutually exclusive in their truth,
    # they can both be false, if the DATA exists, but not any scene OBJECTS

    misc_info: dict = field(default_factory=dict,
                            repr=True,
                            init=True,
                            )

    # defaults
    comp_root_name: Optional[str] = field(default=None,
                                          repr=True,
                                          init=True,
                                          )

    comp_root_transforms: Optional[tuple] = field(default=None,
                                                  repr=True,
                                                  init=True,
                                                  )

    comp_lra_names: Optional[tuple] = field(default=None,
                                            repr=True,
                                            init=True,
                                            )

    comp_subplacement_names: Optional[tuple] = field(default=None,
                                                     repr=True,
                                                     init=True,
                                                     )

    comp_lra_transforms: Optional[tuple] = field(default=None,
                                                 repr=True,
                                                 init=True,
                                                 )

    comp_subplacement_transforms: Optional[tuple] = field(default=None,
                                                          repr=True,
                                                          init=True,
                                                          )

    @DataclassProperty
    def try_to_update(self):
        return self._try_to_update

    @try_to_update.setter
    def try_to_update(self, value: bool):
        self._try_to_update = value

    @DataclassProperty
    def output_grp_parent(self):
        return self.module_grp_name

    @DataclassProperty
    def op_name(self):
        return f"{self.comp_composed_name}_root"

    @DataclassProperty
    def op_node(self):
        return pmc.PyNode(self.op_name)

    @DataclassProperty
    def comp_root_name(self):
        name_ = f"{self.comp_composed_name}_main_{constants.OPERATOR_EXTENSION}"

        if cmds.objExists(name_):
            name_ = openmaya_utils.get_long_name(name_)

        return name_

    @DataclassProperty
    def md_name(self):
        return f"{self.comp_composed_name}_{constants.MODULE_EXTENSION}"

    @DataclassProperty
    def comp_subplacement_amount(self):
        return len(self.comp_subplacement_names)

    @DataclassProperty
    def comp_subplacement_names(self):
        return self._comp_subplacement_names

    @comp_subplacement_names.setter
    def comp_subplacement_names(self, value: Union[int, tuple, list]):
        if isinstance(value, int):
            sub_ext = constants.OPERATOR_SUB_EXTENSION
            self._comp_subplacement_names = tuple(f"{self.comp_composed_name}_sub{x:03}_{sub_ext}"
                                                  for x in range(value)
                                                  )

        elif isinstance(value, (tuple, list)):
            self._comp_subplacement_names = value

        else:
            raise ValueError("when setting the subplacement names there are only two types allowed:\n"
                             "Tuple, List or Integer."
                             )

    @DataclassProperty
    def comp_subplacement_nodes(self):
        return tuple(pmc.PyNode(trs) for trs in self.comp_subplacement_names)

    @DataclassProperty
    def comp_lra_names(self):
        return self._comp_lra_names

    @comp_lra_names.setter
    def comp_lra_names(self, value: Union[int, tuple, list]):
        if isinstance(value, int):
            self._comp_lra_names = tuple(f"{self.comp_composed_name}_sub{x:03}_{constants.LRA_EXTENSION}"
                                         for x in range(value)
                                         )

        elif isinstance(value, (tuple, list)):
            self._comp_lra_names = value

        else:
            raise ValueError("when setting the subplacement names there are only two types allowed:\n"
                             "Tuple, List or Integer."
                             )

    @DataclassProperty
    def comp_lra_nodes(self):
        return tuple(pmc.PyNode(lra)
                     for lra
                     in self.comp_lra_names
                     )

    @DataclassProperty
    def comp_lra_amount(self):
        return len(self.comp_lra_names)

    @DataclassProperty
    def comp_parent_node(self):
        return pmc.PyNode(self.comp_parent_name)

    @DataclassProperty
    def primary_color(self):
        return constants.EWAW_CTRL_COLORS.get(self.comp_side, "C").get("primary", 17)

    @DataclassProperty
    def secondary_color(self):
        return constants.EWAW_CTRL_COLORS.get(self.comp_side, "C").get("secondary", 17)

    @DataclassProperty
    def comp_root_node(self):
        return pmc.PyNode(self.comp_root_name)

    @DataclassProperty
    def comp_spaces(self):
        if not isinstance(self.comp_spaces_names, str, ):
            return None

        return tuple(space_name for space_name
                     in self.comp_spaces_names.split(",")
                     if cmds.objExists(space_name)
                     )

    @DataclassProperty
    def comp_combined_transforms(self) -> tuple:

        lra_mmtx = tuple(matrix_maths.tuple_to_mmatrix(lra_) for lra_ in self.comp_lra_transforms)
        trs_mmtx = tuple(matrix_maths.tuple_to_mmatrix(trs_) for trs_ in self.comp_subplacement_transforms)

        comb_mmtx = tuple(matrix_maths.multiply_matrices(lra_, trs_) for lra_, trs_ in zip(lra_mmtx, trs_mmtx))

        comb_tpl = tuple(matrix_maths.mmatrix_to_tuple(comb_) for comb_ in comb_mmtx)

        return comb_tpl

    @DataclassProperty
    def comp_name(self):
        return self._comp_name

    @comp_name.setter
    def comp_name(self, value: str):
        self._comp_name = f"{value}"

    @DataclassProperty
    def is_module(self):
        return self._is_module

    @is_module.setter
    def is_module(self, value: bool):
        self._is_module = value

    @DataclassProperty
    def is_operator(self):
        return self._is_operator

    @is_operator.setter
    def is_operator(self, value: bool):
        self._is_operator = value

    @DataclassProperty
    def comp_index(self):
        return self._comp_index

    @comp_index.setter
    def comp_index(self, value: int):
        """
        Sets the index of the component, if there already exists one of its index, remaps it to the max.
        """
        _composed = self.comp_composed_name.replace(self.comp_index_name,
                                                    f"{value:0>3}",
                                                    )
        # TODO: we should distinguish between the operator and the module. this is not in yet :(
        # it seems like we are failing in the updating, either too early or too late?
        _operator = f"{_composed}_root"
        _module = f"{_composed}_{constants.EWAW_MD_TAG}"

        current_operator = cmds.ls(_operator)

        current_module = cmds.ls(_module)

        if self.try_to_update:
            if not current_operator:
                self._comp_index = value

            else:
                scene_comps = cmds.ls(_operator.replace(self.comp_index_name, "*"))

                if scene_comps:
                    _idx = len(scene_comps)

                    # this can be made a LOT smarter, now it only takes the maximum length,
                    # but it should be able to slot in.
                    if self._comp_index < _idx:
                        self._comp_index = _idx

                    # if they are bigger than the amount of nodes in the scene, proceed with value
                    else:
                        self._comp_index = value

                # if there are none of this operator in the scene, proceed with value
                else:
                    self._comp_index = value

        else:
            self._comp_index = value

    @DataclassProperty
    def comp_index_name(self):
        return f"{self.comp_index:0>3}"

    @DataclassProperty
    def connectable_attributes(self):
        return self._connectable_attributes

    @connectable_attributes.setter
    def connectable_attributes(self, value: list):
        self._connectable_attributes = list(value)

    @DataclassProperty
    def comp_side(self):
        return self._comp_side

    @comp_side.setter
    def comp_side(self, value: str):
        self._comp_side = f"{value}"

    @DataclassProperty
    def comp_composed_name(self):
        return f"{self.comp_side}_{self.comp_name}_{self.comp_index:03}"

    @DataclassProperty
    def opr_composed_name(self):
        return f"{self.comp_side}_{self.comp_name}Opr_{self.comp_index:03}"

    @DataclassProperty
    def comp_composed_joint_name(self):
        return f"{self.comp_side}_bnd_{self.comp_name}_{self.comp_index:03}"

    @DataclassProperty
    def connector(self):
        return self._connector

    @connector.setter
    def connector(self, value: Optional[str]):
        if value:
            self._connector = f"{value}"
        else:
            self._connector = None

        if self.is_built:
            print("YET TO IMPLEMENT")

    @DataclassProperty
    def module_parent(self):
        return self._module_parent

    @module_parent.setter
    def module_parent(self, value: Optional[str]):
        if value:
            self._module_parent = f"{value}"
        else:
            self._module_parent = None

        if self.is_built:
            print("YET TO IMPLEMENT")

    @DataclassProperty
    def module_grp_name(self):
        return f"{self.comp_composed_name}_{constants.MODULE_EXTENSION}"

    @DataclassProperty
    def ctrl_grp_name(self):
        return f"{self.comp_composed_name}_controls_{constants.MODULE_SUB_EXTENSION}"

    @DataclassProperty
    def primaries_grp_name(self):
        return f"{self.comp_composed_name}_primary_{constants.MODULE_SUB_EXTENSION}"

    @DataclassProperty
    def secondaries_grp_name(self):
        return f"{self.comp_composed_name}_secondary_{constants.MODULE_SUB_EXTENSION}"

    @DataclassProperty
    def input_grp_name(self):
        return f"{self.comp_composed_name}_input_{constants.MODULE_SUB_EXTENSION}"

    @DataclassProperty
    def calculation_grp_name(self):
        return f"{self.comp_composed_name}_calculation_{constants.MODULE_SUB_EXTENSION}"

    @DataclassProperty
    def output_grp_name(self):
        return f"{self.comp_composed_name}_output_{constants.MODULE_SUB_EXTENSION}"

    @DataclassProperty
    def ctrl_grp_parent(self):
        return self.module_grp_name

    @DataclassProperty
    def primaries_grp_parent(self):
        return self.ctrl_grp_name

    @DataclassProperty
    def secondaries_grp_parent(self):
        return self.ctrl_grp_name

    @DataclassProperty
    def input_grp_parent(self):
        return self.module_grp_name

    @DataclassProperty
    def calculation_grp_parent(self):
        return self.module_grp_name

    @DataclassProperty
    def output_grp_parent(self):
        return self.module_grp_name

    @DataclassProperty
    def sub_modules(self):
        return {self.module_grp_name: {"parent": self.module_parent,
                                       "outliner_color": constants.COLORS["magenta"]
                                       },
                self.input_grp_name: {"parent": self.input_grp_parent,
                                      "outliner_color": constants.COLORS["blue"]
                                      },
                self.ctrl_grp_name: {"parent": self.ctrl_grp_parent,
                                     "outliner_color": constants.COLORS["yellow"]
                                     },
                self.primaries_grp_name: {"parent": self.primaries_grp_parent,
                                          "outliner_color": constants.COLORS["orange"]
                                          },
                self.secondaries_grp_name: {"parent": self.secondaries_grp_parent,
                                            "outliner_color": constants.COLORS["dark_orange"]
                                            },
                self.calculation_grp_name: {"parent": self.calculation_grp_parent,
                                            "outliner_color": constants.COLORS["red"]
                                            },
                self.output_grp_name: {"parent": self.output_grp_parent,
                                       "outliner_color": constants.COLORS["turquoise"]
                                       },
                }

    def dict_to_data(self, data: dict):
        """
        Feeds given dictionary into the DataContainer DataClass.

        Args:
            data (dict): Sets the Data of this Class to the values of a dictionary.

        """

        for key, value in data.items():
            if hasattr(self, key):
                try:

                    setattr(self, key, value)

                except AttributeError as e:
                    _LOGGER.debug(f"{e}: {key} = {value} ---> is not a settable attribute, skipping for now.")

    def data_to_dict(self) -> dict:
        """
        Converts the DataContainer DataClass data into a dictionary.

        Returns:
            Dict: Resulting dictionary containing the data of DataContainer.

        """

        return {k: v for k, v in asdict(self).items() if k[0] != "_"}

    def sanity_check(self,
                     verbose: bool = True,
                     ) -> bool:
        """
        Performs a sanity check to ensure if all the data is correct.

        Checking:
            - operator dict == data dict.
            - lra names == lra_transforms.
            - subplacement names == subplacement transforms.

        """
        if not self.comp_lra_names and not self.comp_lra_transforms:
            lra_check = True
        else:
            lra_check = len(self.comp_lra_names) == len(self.comp_lra_transforms)

        pprint(self.comp_subplacement_names)
        pprint(self.comp_subplacement_transforms)
        if not self.comp_subplacement_names and not self.comp_subplacement_transforms:
            operator_check = True
        else:
            operator_check = len(self.comp_subplacement_names) == len(self.comp_subplacement_transforms)

        try:
            op_dict = self.operator_to_dict()

        except RuntimeError as e:
            _LOGGER.warning(f"Operator Dictionary failed on the conversion: {e}.")
            op_dict = None

        try:
            md_dict = self.module_to_dict()

        except RuntimeError as e:
            _LOGGER.warning(f"Module Dictionary failed on the conversion: {e}.")
            md_dict = None

        self.comp_subplacement_names = tuple(
            openmaya_utils.get_long_name(sub_ctrl) for sub_ctrl in self.comp_subplacement_names
        )

        dt_dict = self.data_to_dict()
        dt_dict.pop("is_operator")
        dt_dict.pop("is_module")

        if md_dict and op_dict:
            op_dict["is_built"] = True
            dt_dict["is_built"] = True

        op_serialization_check = advanced_serialization_check(dt_dict,
                                                              op_dict,
                                                              verbose
                                                              )

        md_serialization_check = advanced_serialization_check(dt_dict,
                                                              md_dict,
                                                              verbose
                                                              )

        combined_serialization = any((op_serialization_check,
                                      md_serialization_check,
                                      )
                                     )

        return all((lra_check, operator_check, combined_serialization))



    def operator_to_dict(self):
        operator_data = node_to_dict(node_name=self.op_name)

        return operator_data

    def module_to_dict(self):
        module_data = node_to_dict(node_name=self.md_name)

        return module_data

    def mirror_data(self,
                    axis: str = "X",
                    with_debug_objects: bool = False,
                    ) -> Union[tuple, bool]:
        """
        Mirrors its own data around specified axis, if with debug objects is on, it will create Transform nodes.

        Args:
            axis (str): Axis around which to Mirror the data around (Uses scaling).
            with_debug_objects (bool): Create empty transforms.

        Returns:
            Tuple: If it successfully mirrored it will return the values. If not it will return False.

        """

        mirroring_ = constants.MIRROR.get(self.comp_side.upper(), False)

        if not mirroring_:
            _LOGGER.error(f"the data of : {self.comp_composed_name}"
                          f"with the side indicator of {self.comp_side} could not be mirrored."
                          f"permitted side indicators are :{' | '.join(constants.MIRROR)}!"
                          )
            return False

        prev_node_ = None
        # setting the first node
        mtx_tuple_new_root = matrix_maths.mirror_scalewise(self.comp_root_transforms,
                                                           mirror_axis=axis,
                                                           )

        if with_debug_objects:
            node_name_ = node.createNode("transform",
                                         )

            cmds.xform(node_name_,
                       matrix=mtx_tuple_new_root,
                       )

            prev_node_ = node_name_

        mirrored_subplacement_data_ = self._mirror_transform_data(axis,
                                                                  self.comp_subplacement_transforms,
                                                                  prev_node_,
                                                                  with_debug_objects=with_debug_objects
                                                                  )

        prev_node_ = None
        mirrored_lra_data_ = self._mirror_transform_data(axis,
                                                         self.comp_lra_transforms,
                                                         prev_node_,
                                                         with_debug_objects=with_debug_objects
                                                         )

        # setting the data
        self.comp_root_transforms = mtx_tuple_new_root
        self.comp_subplacement_transforms = mirrored_subplacement_data_
        self.comp_lra_transforms = mirrored_lra_data_

        self.comp_side = mirroring_[0]
        self.comp_index = self.comp_index

        self.comp_subplacement_names = len(self.comp_subplacement_names)
        self.comp_lra_names = len(self.comp_lra_names)

        self.comp_parent_name = self.comp_parent_name.replace(mirroring_[1][0],
                                                              mirroring_[1][1],
                                                              )

        return mtx_tuple_new_root, mirrored_subplacement_data_, mirrored_lra_data_

    @staticmethod
    def _mirror_transform_data(axis: str,
                               previous_lra_data_: tuple,
                               prev_node_: Union[str, None],
                               with_debug_objects: bool = False,
                               ) -> tuple:

        mirrored_lra_data_ = list()

        for mtx_tuple in previous_lra_data_:

            mtx_tuple_new = matrix_maths.mirror_scalewise(mtx_tuple,
                                                          mirror_axis=axis,
                                                          )

            mirrored_lra_data_.append(mtx_tuple_new)

            if with_debug_objects:
                node_name_ = node.createNode("transform",
                                             )

                cmds.xform(node_name_,
                           matrix=mtx_tuple_new,
                           )

                if prev_node_:
                    cmds.parent(node_name_,
                                prev_node_,
                                )

                prev_node_ = node_name_

        return tuple(mirrored_lra_data_)

    def save(self):
        """
        Saves data to the VCS.

        """

        if not self.sanity_check(verbose=True):
            raise ValueError(f"Sanity check was not passed on {self.comp_composed_name}. "
                             f"Saving operation stopped."
                             )

        _LOGGER.debug(f"Sanity check passed on {self.comp_composed_name}.")

        io_manager = ImportExport()

        io_manager.write(
                object_name=f"{self.comp_composed_name}",
                data_to_write=self.data_to_dict(),
                data_type="json",
                data_category=constants.RIGGING_SYSTEM_NAME,
        )

    def load(self, name: Optional[str] = None):
        """
        Loads data from the VCS and updates the data class with it.

        """

        io_manager = ImportExport()

        if not name:
            name = self.comp_composed_name

        imported_data = io_manager.load(
                object_name=name,
                version=-1,
                data_type="json",
                data_category=constants.RIGGING_SYSTEM_NAME,
        )

        # since json can not save tuples, this is used to convert all the lists to tuples,
        # we deal with unjustly converted lists in the modules themselves.
        modified_data = {k: tuple(v) if isinstance(v, list) else v for k, v in imported_data.items()}

        self.dict_to_data(modified_data)

    def data_to_system(self,
                       verbose: bool = False,
                       system_type: str = "operator",
                       ):

        system_type_ = system_type
        path_ = get_component_path(self.comp_type, file_name=system_type_)

        if verbose:
            _LOGGER.info(f"found path: {path_.resolve()}")

        system_module = import_from_path(module_namespace=f"{self.comp_type}_{system_type_}_",
                                         file_path=path_,
                                         verbose=verbose,
                                         )

        new_system = system_module.Main(data_container=self)

        return new_system

    def data_to_operator(self,
                         verbose: bool = True,
                         ):
        system_type_ = "operator"
        operator_ = self.data_to_system(verbose=verbose,
                                        system_type=system_type_,
                                        )

        return operator_

    def data_to_module(self,
                       verbose: bool = True,
                       ):

        system_type_ = "module"
        module_ = self.data_to_system(verbose=verbose,
                                      system_type=system_type_,
                                      )

        return module_

    def check_existance(self):
        _LOGGER.warning(f"OPERATOR MODULE: {self.comp_type}_operator_" in sys.modules)
        raise NotImplementedError("This has not been implemented yet, we are having issues with the scope")


def register_data_from_node_name(node_name: str, tag: str) -> DataContainer:
    """
    Converts a node into data class.

    Args:
        node_name (str): Name of the node.
        tag (str): From Constants, giving if its of type.

    Returns:
        DataContainer (new_system_data_): New DataContainer instance.

    """

    if not cmds.objExists(node_name):
        raise NameError(f"The node: {node_name} was not found in the scene.")

    if not cmds.attributeQuery(tag,
                               node=node_name,
                               exists=True
                               ):
        raise AttributeError(f"The node: {node_name} has no attribute: {tag}.\n"
                             f"Therefore it is not seen as an ewaw object.")

    # opening up a new DataContainer node
    new_system_data_ = DataContainer()

    # reading node into a dictionary
    old_data = node_to_dict(node_name)

    # filling the opened up DataContainer with the node information
    new_system_data_.dict_to_data(data=old_data,
                                  )
    return new_system_data_


def register_operator_from_node_name(node_name: str):
    """
    Registers existing Operator node as a new Operator class.

    Args:
        node_name (str): Name of the node to be converted.

    Returns:
        operator: The new operator class.

    """

    new_operator_data_ = register_data_from_node_name(node_name,
                                                      tag=constants.EWAW_OP_TAG,
                                                      )

    # creates a new instance of the operator from the data class
    return new_operator_data_.data_to_operator(verbose=True, )


def register_module_from_node_name(node_name: str):
    """
    Registers existing Operator node as a new Module class.

    Args:
        node_name (str): Name of the node to be converted.

    Returns:
        operator: The new operator class.

    """

    new_module_data_ = register_data_from_node_name(node_name,
                                                      tag=constants.EWAW_MD_TAG,
                                                      )

    # creates a new instance of the operator from the data class
    return new_module_data_.data_to_module(verbose=True, )


def check_if_matrices(item: Any) -> bool:
    """
    Checks if the item is a matrix or consists of an iterable of matrices.

    Args:
        item (Any): Input item to be checked.

    Returns:
        Bool: True if only matrix data.

    """

    # check the validity of the data
    if isinstance(item, (str, int, float, type(None))):
        return False

    if not len(item) == 16:
        sub_item_check = all(len(x) == 16 for x in item)

        if not sub_item_check:
            return False

    return True


def advanced_serialization_check(dt_dict: dict,
                                 op_dict: dict,
                                 verbose: bool
                                 ) -> bool:


    if not op_dict:
        return False

    op_dict.pop("is_operator")

    op_dict.pop("is_module")

    lazy_is_equal = op_dict == dt_dict

    if lazy_is_equal:
        return True

    thorough_is_equal = accurate_dict_check(dt_dict,
                                            op_dict,
                                            verbose,
                                            )
    if thorough_is_equal:
        return True

    return False


def accurate_dict_check(first_item: dict,
                        second_item: dict,
                        verbose: bool
                        ) -> bool:

    if verbose:

        first_item = dict_value_list_to_tuple(first_item)

        second_item = dict_value_list_to_tuple(second_item)

        # converting the dictionaries to sets, so we can easily figure out differences.
        dt_dict_set = set(first_item.items())

        op_dict_set = set(second_item.items())

        differences_ = op_dict_set ^ dt_dict_set

        if not differences_:
            return True

        close_number_match_check = check_if_almost_equal(differences_)

        if close_number_match_check:
            return True

    return False





def get_component_path(comp_type: str,
                       file_name: str
                       ) -> pathlib.Path:

    """
    Gets the components module path.

    Args:
        comp_type (str): Type of component, reference to all is found in EWAW_rs.components.
        file_name (str): Name of the file, means if it's a module or operator.

    Returns:
        pathlib.Path: File Path to the module.

    """

    # get the path to the data class
    file_path_ = pathlib.Path(__file__).resolve()

    # work your way up the predefined hierarchy to reach the ewaw_rs root
    base_constructs_path = file_path_.parent
    ewaw_rs_root = base_constructs_path.parent

    # change name to components path and step down
    components_path = ewaw_rs_root.joinpath("components")

    # check if its a valid directory
    if not components_path.exists():
        raise ModuleNotFoundError("components direcory does not exist")

    if not components_path.is_dir():
        raise ModuleNotFoundError("components is not a directory")

    if not components_path.iterdir():
        raise ModuleNotFoundError("components directory is empty")

    # check if the name is in the direcory
    _name_check = comp_type in (comp_path.name for comp_path in components_path.iterdir())
    if not _name_check:
        raise ModuleNotFoundError(f"{comp_type} is not in components directory")

    # get a scan of all components
    current_potential_components = tuple(comp_path for comp_path
                                         in components_path.iterdir()
                                         if comp_type == comp_path.name
                                         )

    # check the amount of components with that exact name (it has to be 1)
    _path_len_check = len(current_potential_components)

    if _path_len_check > 1:
        raise IndexError("Too many paths with this name, name is not unique.")

    elif _path_len_check < 1:
        raise IndexError("No path of this name exists.")

    module_directory = current_potential_components[0]
    module_path = module_directory.joinpath(f"{file_name}_.py")

    if not module_path.exists():
        raise NotImplementedError(f"Module direcory: {module_directory.resolve()} does not contain init file.")

    # give back valid path to init file
    return module_path


def import_from_path(module_namespace: str,
                     file_path: pathlib.Path,
                     verbose: bool = False,
                     ):
    """
    Takes a Path, converts it into a module reference and loads the module reference.

    Args:
        module_namespace (str): The alias name of the module that will be imported.
        file_path (Path): Path to the module.
        verbose (bool): If true prints the module spec.

    Returns:
        Module (loaded_module_): The module that was loaded.

    """

    importlib.invalidate_caches()

    # Create a module spec
    spec = importlib.util.spec_from_file_location(module_namespace, file_path)

    if verbose:
        _LOGGER.info(spec)

    # Load the module from the spec
    loaded_module_ = importlib.util.module_from_spec(spec)

    # sys.modules[module_name] = __module_
    spec.loader.exec_module(loaded_module_)

    return loaded_module_


def create_comparison_dictionary(returned_values: set,
                                 check_func=check_if_matrices
                                 ) -> dict:
    """
    Turns a difference set into a dictionary to help comparing its values.

    Args:
        returned_values (set): Set to be turned into a comparison dictionary where the attr name is key.
        check_func (func): Function for checking values, since this might be used for other types too.

    Returns:
        Dict (comparison_helper): Dictionary where attr name is key, and its items are the differences.

    """

    comparison_helper = dict()

    for name_, data_ in returned_values:
        if not comparison_helper.get(name_, False):
            comparison_helper[name_] = list()

        if check_func(data_):
            comparison_helper[name_].append(data_)

    return comparison_helper


def create_compare_pairs(comparison_helper: dict) -> list:
    """
    Pairs up the compare items for easier comparison into a list of zips.

    Args:
        comparison_helper (dict): Dict that will be searched.

    Returns:
        List (compare_items): List of zipped items to compare against each other.

    """

    compare_items = list()
    for compare_item in comparison_helper.values():

        if not isinstance(compare_item, list):
            raise TypeError("the compare items are not in a list")

        if not len(compare_item) == 2:
            raise IndexError("only one item to compare was registered")

        compare_items.append(zip(*compare_item))

    if not compare_items:
        raise ValueError("there were no compare items")

    return compare_items


def compare_pairs_of_items(compare_items: list,
                           abs_tolerance: float = 1e-13,
                           ) -> True:
    """
    Compares the zipped items of a list with each other.

    Args:
        compare_items (list): The list of zip objects.
        abs_tolerance (float): The absolute tolerance to compare the values by.

    Returns:
        True: If the compare ran through without an error, it will return True.

    """

    for compare_item in compare_items:

        for id_, (first_, second_) in enumerate(compare_item):
            try:
                subpairs_ = zip(first_,
                                second_,
                                )
            except TypeError:
                pprint(compare_items)

            for idx_, (subpair_first_, subpair_second_) in enumerate(subpairs_):

                closeness_check = math.isclose(subpair_first_,
                                               subpair_second_,
                                               rel_tol=1,
                                               abs_tol=abs_tolerance
                                               )

                if not closeness_check:
                    raise ValueError(f"{id_}: {idx_} |--->   {subpair_first_} != {subpair_second_}")

    return True


def dict_value_list_to_tuple(input_obj: dict) -> dict:
    """
    Turns list values of dictionary into tuple for faster compare, hash-ability and fixed size.

    Args:
        input_obj (dict): Dictionary to have its values converted from list to tuple.

    Returns:
        True: Once it is run through, it will return True to show it's done.

    """

    for k_, v_ in input_obj.items():
        if isinstance(v_, list):
            input_obj[k_] = tuple(v_)

    return input_obj


def check_if_almost_equal(returned_values: set,
                          abs_tolerance: float = 1e-6,
                          ) -> bool:
    """
    Checks the Set for almost equal numbers.
    This expects matrices to have floating point precision errors.

    Args:
        returned_values (set): Set to be checked for almost equal values.
        abs_tolerance (float): Tolerance to look for, its only absolute and not relative value.

    Returns:
        Bool: True if contents are almost equal.

    """

    comparison_helper = create_comparison_dictionary(returned_values)

    try:
        compare_items = create_compare_pairs(comparison_helper)

    except IndexError as e:
        _LOGGER.warning(f"{e} : comparison helper --> {comparison_helper}")
        return False

    try:
        compare_pairs_of_items(compare_items,
                               abs_tolerance=abs_tolerance
                               )
        return True

    except ValueError as e:
        _LOGGER.warning(f"{e} : comparison helper --> {pformat(comparison_helper)}")
        return False


def nodes_to_names_and_transforms(attributes_dict: dict,
                                  names: str,
                                  nodes: str,
                                  transforms: str,
                                  ):
    """
    Takes a dictionary and adds name and transform entries instead of the node entry.
    This function is heavily flawed, have fun with that.
    # TODO: figure out how to make this in a sensible way (ducktyped or something)

    Args:
        attributes_dict (dict): .
        names (str): .
        nodes (str): .
        transforms (str): .

    """

    subplacement_nodes = attributes_dict.pop(nodes, False)

    if subplacement_nodes:
        attributes_dict[names] = tuple(
            openmaya_utils.get_long_name(sub_ctrl) for sub_ctrl in subplacement_nodes
        )

        attributes_dict[transforms] = tuple(
            matrix_maths.mmatrix_to_tuple(
                    matrix_maths.get_world_matrix(sub_ctrl)
            )
            for sub_ctrl in subplacement_nodes
        )


def node_to_dict(node_name: str,
                 ) -> dict:
    """
    Turns the given node to a dictionary that can be used by the data class.

    Args:
        node_name (str): Name of the node to get the dictionary from.

    Returns:
        Dict: The resulting dictionary gathered from the node.

    """

    attr_collector_attr = f"{node_name}.{constants.EWAW_ATTR_DATA}"

    if not cmds.objExists(node_name):
        raise RuntimeError(f"The node: {node_name} does not exist in the scene.")

    if not cmds.attributeQuery(constants.EWAW_ATTR_DATA, node=node_name, exists=True):
        raise RuntimeError(f"The node: {node_name} has not the attribute called: {constants.EWAW_ATTR_DATA} "
                           f"needed for ewaw conversion to dict.")

    # get all the data from the given node that has the attribute of constants.EWAW_ATTR_DATA.
    meta_data = cmds.listAttr(attr_collector_attr)

    if not meta_data:
        raise LookupError(f"{attr_collector_attr}: there are no sub-attrs")

    # slice away the first entry which should be the clean attribute declared in constants.EWAW_ATTR_DATA.
    meta_data_ = meta_data[1:]

    # makes sure that message attr connections give back the names of connected nodes
    attributes_dict = {
        attr: rig_utils.get_attribute_or_connections(node_name, attr)
        for attr in meta_data_
    }

    #
    # this is where we actually retrieve the data
    #
    if not attributes_dict.get("comp_parent_name", None):
        op_parent_ = cmds.listRelatives(node_name,
                                        fullPath=True,
                                        parent=True,
                                        )

        attributes_dict["comp_parent_name"] = str(op_parent_[0]
                                                  if op_parent_
                                                  else ""
                                                  )

    if attributes_dict.pop("comp_root_nd", None):
        # WE HAVE A PROBLEM HERE SARGENT
        root_name_list = rig_utils.get_attribute_or_connections(node_name,
                                                                attr="comp_root_nd",
                                                                )
        if not root_name_list:
            raise RuntimeError(f"{node_name}.comp_root_nd was not found.")

        # converts it to its long name
        attributes_dict["comp_root_name"] = openmaya_utils.get_long_name(root_name_list[0])

        attributes_dict["comp_root_transforms"] = matrix_maths.mmatrix_to_tuple(
            matrix_maths.get_world_matrix(attributes_dict["comp_root_name"])
        )

    nodes_ = "comp_subplacement_nodes"
    names_ = "comp_subplacement_names"
    transforms_ = "comp_subplacement_transforms"

    nodes_to_names_and_transforms(attributes_dict,
                                  names_,
                                  nodes_,
                                  transforms_,
                                  )

    nodes_ = "comp_lra_nodes"
    names_ = "comp_lra_names"
    transforms_ = "comp_lra_transforms"

    nodes_to_names_and_transforms(attributes_dict,
                                  names_,
                                  nodes_,
                                  transforms_,
                                  )

    if attributes_dict.get(constants.EWAW_OP_TAG, None):
        attributes_dict["op_name"] = node_name

    elif attributes_dict.get(constants.EWAW_MD_TAG, None):
        attributes_dict["op_name"] = node_name

    else:
        raise LookupError(f"The node {node_name} has no attribute that is associated with EWAW.\n"
                          f"Tags missing are either {constants.EWAW_OP_TAG} or {constants.EWAW_MD_TAG}.")

    return attributes_dict


def dict_to_node(node_name: str,
                 data_dict: dict,
                 node_type: str = "operator"
                 ):
    """
    Adds dict information to a node, will error if the node does not exist.
    It takes the attribute information from constants.EWAW_ATTR_TYPES.

    Args:
        node_name (str): Name of the node to which attributes should be added.
        data_dict (dict): Data to be added, will be compared to constants.EWAW_ATTR_TYPES for the attr info.
        node_type (str): The type of EWAW node to which the attr should be added.
                         This is in relation to their functionality and NOT their identity.

    """

    # this is an idea on how to handle the data at its export stage,
    # I decided to adjust it in the DataDict instead (pre conversion).
    # Still here in the case we need it
    '''
    node_tag = constants.EWAW_NODE_TYPES.get(node_type, False)

    if not node_tag:
        raise RuntimeError(f"{node_type} was not found in {' | '.join(constants.EWAW_NODE_TYPES)}.\n "
                           f"Therefore it can not transfer the data to this type of node.")

    # unpacking the values into usable variables for easier reading
    # (module_tag_name, module_value), (operator_tag_name, operator_value) = node_tag

    # data_dict[module_tag_name] = module_value
    # data_dict[operator_tag_name] = operator_value
    '''

    # check for existence
    if not cmds.objExists(node_name):
        raise RuntimeError(f"The node: {node_name} does not exist in the scene.")

    if cmds.attributeQuery(constants.EWAW_ATTR_DATA, node=node_name, exists=True):
        raise AttributeError(f"The attribute: {constants.EWAW_ATTR_DATA} already exists on node: {node_name}.")

    att_types_conversion = deepcopy(constants.EWAW_ATTR_TYPES)

    attr_types_new = data_dict_to_attr_types(data_dictionary=data_dict,
                                             compare_dict=att_types_conversion,
                                             )

    add_attr_data_to_node(attr_types_new,
                          node_name=node_name,
                          )


def data_dict_to_attr_types(data_dictionary: dict,
                            compare_dict: typing.OrderedDict,
                            ) -> list:
    """
    Turns the dictionary into a list of instructions to be used for the attr conversion to dict.

    Args:
        data_dictionary (dict): The dictionary that gets turned into attribute types.
        compare_dict (typing.OrderedDict): The dictionary that the data is compared against to find the right conversion.

    Returns:
        List (instructions_): Instructions for the further conversion.

    """

    instructions_ = list()

    for k_, v_ in data_dictionary.items():

        new_key = compare_dict.get(k_, False)

        if not new_key:
            continue

        new_key["OLD_KEY"] = k_

        new_key["VALUE"] = v_

        instructions_.append(new_key)

    return instructions_


def add_attr_data_to_node(attr_data: list,
                          node_name: str,
                          ):
    """
    Adds the attribute instructions to the node.

    Args:
        attr_data (list): List of instructions.
        node_name (str): Name of the node onto which we want to add the data.

    """

    node.addAttr(node_name,
                 ln=constants.EWAW_ATTR_DATA,
                 at="compound",
                 numberOfChildren=len(attr_data),
                 )

    setting_set = add_ewaw_subattrs(attr_data, node_name)

    handle_ewaw_subattrs(setting_set)


def handle_ewaw_subattrs(setting_set: set):
    """
    Handles the attributes: based on instructions it either sets or connects them.

    Args:
        setting_set (set): Instructions set.

    """

    for att_name, conversion, value, dt_ in setting_set:

        cmds.setAttr(f"{att_name}", cb=True, k=False)

        if conversion:
            connect_ewaw_subattrs(att_name, value)

        else:
            set_ewaw_subatt(att_name, dt_, value)


def set_ewaw_subatt(att_name: str,
                    dt_: str,
                    value: typing.Any,
                    ):
    """
    Sets the attributes based on instructions.

    Args:
        att_name (str): Name of attribute.
        dt_ (str): Type of attribute.
        value (typing.Any): Value of attribute.

    """

    if dt_:
        cmds.setAttr(f"{att_name}",
                     value,
                     type=dt_,
                     )

    else:
        cmds.setAttr(f"{att_name}",
                     value,
                     )


def connect_ewaw_subattrs(att_name: str,
                          value: typing.Any,
                          ):
    """
    Connects the attributes based on instructions.

    Args:
        att_name (str): Name of attribute.
        value (typing.Any): Value of attribute.

    """

    if not isinstance(value, (tuple, list, set)):

        cmds.connectAttr(f"{value}.message",
                         f"{att_name}",
                         f=True,
                         )
    else:

        for it_, val_ in enumerate(value):

            cmds.connectAttr(f"{val_}.message",
                             f"{att_name}[{it_}]",
                             f=True,
                             )


def add_ewaw_subattrs(attr_data: list,
                      node_name: str,
                      ) -> set:
    """
    Adds the attributes based on a list of dicts, then returns a set of data that needs to be set.
    The reason this is not done in one go is:
    Maya does not allow setting of compound members of an unfinished / not fully created compound.

    Args:
        attr_data (list): Attribute instructions gathered.
        node_name (str): Name of the node.

    Returns:
        Set: After adding the Attributes they need to be set.
             This instruction set hands it off to fn(set_ewaw_subattrs).

    """

    setting_set = set()

    for att_ in attr_data:

        att_name, conversion, dt_, value = get_ewaw_helper_data_from_dict(att_)

        if not att_name:
            raise ValueError

        att_name = node.addAttr(node_name,
                                **att_,
                                k=True,
                                parent=constants.EWAW_ATTR_DATA,
                                )

        # we strictly want to skip types of NoneType, not any instance or anything.
        if isinstance(value, type(None)):
            continue

        try:
            setting_set.add((att_name,
                             conversion,
                             value,
                             dt_,)
                            )

        except TypeError as e:
            pprint(f"{att_name}: {e}")


    return setting_set


def get_ewaw_helper_data_from_dict(att_: dict) -> tuple:
    """
    Extracts the data from the attribute info dictionary.

    Args:
        att_ (dict): Attribute information as a dictionary.

    Returns:
        Tuple (att_name, conversion, dt_, value): Gathered Values of the attribute.

    """

    _ = att_.pop("OLD_KEY",
                 False,
                 )
    value = att_.pop("VALUE",
                     False,
                     )
    conversion = att_.pop("CONVERT",
                          False,
                          )
    att_name = att_.get("longName",
                        False,
                        )

    dt_ = att_.get("dataType",
                   False,
                   )
    return att_name, conversion, dt_, value


def naming(type, subindex, suffix):
    #return f"{self.data.comp_composed_name}_{type}_{subindex}_{suffix}"
    raise NotImplementedError