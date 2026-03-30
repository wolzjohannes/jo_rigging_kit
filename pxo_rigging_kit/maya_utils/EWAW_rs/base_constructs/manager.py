
import logging
from pathlib import Path
from pprint import pprint

from future import standard_library
from importlib import reload

from pxo_rigging_kit import constants
from pxo_rigging_kit.maya_utils import openmaya_utils, paths_utils
from pxo_rigging_kit.maya_utils.EWAW_rs.base_constructs import data
from pymel import core as pmc
reload(data)

##########################################################
# GLOBALS                                                #
##########################################################


_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)
standard_library.install_aliases()


##########################################################
# CLASSES                                                #
##########################################################


class Manager(object):

    _OP_BUILD = dict()
    _MD_BUILD = dict()
    _DT_BUILD = dict()

    _BUILD = {"operators": _OP_BUILD,
              "modules": _MD_BUILD,
              "data": _DT_BUILD,
              "op_nodes": set(),
              "md_nodes": set(),
              }

    def __init__(self):
        _LOGGER.debug("Manager running.")

    def collect_operators(self):
        """


        """

        self._gather_operators()

        for op_node in self._BUILD["op_nodes"]:
            op_class = data.register_operator_from_node_name(node_name=op_node)

            op_name = op_class.data.comp_composed_name

            self._BUILD["operators"][op_name] = op_class

        # TODO: BAD prints :-)
        print()
        _LOGGER.info("Finished: Collect Operators method.")
        print()

    def collect_modules(self):
        """


        """

        self._gather_modules()

        for md_node in self._BUILD["md_nodes"]:
            md_class = data.register_module_from_node_name(node_name=md_node)

            md_name = md_class.data.comp_composed_name

            self._BUILD["modules"][md_name] = md_class

        # TODO: BAD prints :-)
        print()
        _LOGGER.info("Finished: Collect Modules method.")
        print()

    def build_operators(self):
        """


        """

        if not self._BUILD["operators"]:
            raise KeyError

        for op_name_, op_cls_ in self._BUILD["operators"].items():
            _LOGGER.debug(f"The data of {op_name_} will start its operation!")
            op_cls_.build()

    def re_build_operators(self):
        """


        """

        if not self._BUILD["operators"]:
            raise KeyError

        for op_name_, op_cls_ in self._BUILD["operators"].items():
            _LOGGER.debug(f"The data of {op_name_} will start its operation!")
            op_cls_.rebuild()

        # TODO: BAD prints :-)
        print()
        _LOGGER.info("Finished: Rebuilding Operators method.")
        print()

    def build_modules(self):
        """


        """

        # check if the dictionary is even filled
        if not self._BUILD["operators"]:
            raise KeyError("The _BUILD queue is empty for operators! Load the Operators in the queue.")

        # sort out the build order
        sorted_build = create_sorted_build_order(self._BUILD["operators"])

        for lyr_idx_, lyr_content_ in sorted_build:
            if not lyr_content_:
                raise

            for op_name_, operator_class_ in lyr_content_:
                _LOGGER.debug(f"The data of {op_name_} will start its operation!")

                # loads the new data from node to operator
                operator_class_.update_data()

                # converts the data from the operator class to the module class
                module_from_operator = operator_class_.data.data_to_module()

                # builds the module
                module_from_operator.build()

                self._BUILD["modules"][op_name_] = module_from_operator

    def un_build_modules(self):
        """


        """

        if not self._BUILD["modules"]:
            raise KeyError("The _BUILD queue is empty for modules! Load the Modules in the queue.")

        for md_name_, md_class_ in self._BUILD["modules"].items():
            _LOGGER.debug(f"The data of {md_name_} will start its operation!")

            md_class_.unbuild()

    def save_operators(self):
        """

        """

        if not self._BUILD["operators"]:
            raise KeyError("")

        for op_name_, op_class_ in self._BUILD["operators"].items():
            _LOGGER.debug(f"Saving Operator: {op_name_}.")
            op_class_.data.is_built = False

            op_class_.data.save()

        # TODO: BAD prints :-)
        print()
        _LOGGER.info("Finished: Saving Operators method.")
        print()

    def save_modules(self):
        """

        """

        if not self._BUILD["modules"]:
            raise KeyError("")

        for md_name_, md_class_ in self._BUILD["modules"].items():
            _LOGGER.debug(f"Saving Module: {md_name_}.")
            md_class_.data.is_built = False

            md_class_.data.save()

        # TODO: BAD prints :-)
        print()
        _LOGGER.info("Finished: Saving Modules method.")
        print()

    def load_operators(self):
        """

        """

        self.load_data()

        if not self._BUILD["data"]:
            raise

        for data_name, data_cls in self._BUILD["data"].items():

            _LOGGER.debug(f"Loading Data: {data_name}.")

            loaded_operator = data_cls.data_to_operator()

            self._BUILD["operators"][data_name] = loaded_operator

        print()
        _LOGGER.info("Finished: Load Operators method.")
        print()

    def load_data(self):
        """

        """

        data_path = Path(paths_utils.get_project_paths(pmc.sceneName()))

        ewaw_path = data_path.joinpath(constants.RIGGING_SYSTEM_NAME)

        path_iteration = ewaw_path.iterdir()

        if not path_iteration:
            raise FileNotFoundError("")

        for vcs_path in path_iteration:

            op_name = vcs_path.name

            _LOGGER.debug(f"Converting Operator: {op_name}.")

            free_data = data.DataContainer()

            free_data.load(name=vcs_path.name)

            self._BUILD["data"][op_name] = free_data

        print()
        _LOGGER.info("Finished: Load Data method.")
        print()



    def _gather_operators(self) -> set:
        """
        Gathers the operators found in the scene based on their tag in the constants.

        Returns:
            Set: The nodes found with the corresponding tag

        """

        operator_nodes = openmaya_utils.get_tagged_nodes(tag=constants.EWAW_OP_TAG)

        if not operator_nodes:
            raise RuntimeError(f"Could not find any operator nodes in the scene "
                               f"tagged with the attribute: {constants.EWAW_OP_TAG}.")

        self._BUILD["op_nodes"] = operator_nodes

        return operator_nodes

    def _gather_modules(self) -> set:
        """
        Gathers the modules found in the scene based on their tag in the constants.

        Returns:
            Set: The nodes found with the corresponding tag

        """

        module_nodes = openmaya_utils.get_tagged_nodes(tag=constants.EWAW_MD_TAG)

        if not module_nodes:
            raise RuntimeError(f"Could not find any module nodes in the scene "
                               f"tagged with the attribute: {constants.EWAW_MD_TAG}.")

        self._BUILD["md_nodes"] = module_nodes

        return module_nodes


def create_sorted_build_order(queue_: dict
                              ) -> list:
    """
    Based on the build_layer attribute in the class data the queue will be sorted.

    Args:
        queue_ (dict):

    Returns:
        List:
    """

    build_order_ = dict()
    for op_name_, operator_class_ in queue_.items():
        layer = f"{operator_class_.data.build_layer}"
        existing_layer = build_order_.get(layer, False)

        if not existing_layer:
            build_order_[layer] = [(op_name_,
                                    operator_class_,
                                    ),
                                   ]
        else:
            build_order_[layer].append((op_name_,
                                        operator_class_,
                                        )
                                       )
    sorted_build = sorted(build_order_.items())
    return sorted_build