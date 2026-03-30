# Import built-in modules
from abc import ABC
from abc import abstractmethod
from importlib import reload
import logging
from pathlib import PurePath
from pprint import pprint
from typing import Optional

# Import third-party modules
from future import standard_library
from maya import cmds
from maya_proxy_node import asset_node
import pymel.core as pmc

# Import local modules
from pxo_rigging_kit import constants
from pxo_rigging_kit.maya_utils import openmaya_utils
from pxo_rigging_kit.maya_utils.EWAW_rs import container
from pxo_rigging_kit.maya_utils.rigging import curves_utils, rig_utils
from pxo_rigging_kit.maya_utils.EWAW_rs import matrix_maths, node
from pxo_rigging_kit.maya_utils.EWAW_rs.base_constructs import data
from pxo_rigging_kit.maya_utils import decorators

reload(rig_utils)
reload(curves_utils)
reload(constants)
reload(data)
reload(node)
reload(container)

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


class Main(ABC):

    NAMING_RULE = constants.NAMING_RULE
    OPERATOR_EXTENSION = constants.OPERATOR_EXTENSION
    LRA_EXTENSION = constants.LRA_EXTENSION
    DIAMOND_CTRL_COLOR = 18
    ROOT_ND_MESSAGE_ATTR = "root_nd"
    META_COMPONENT_ATTR_NAME = constants.EWAW_ATTR_DATA

    IS_EWAW_RIG = constants.EWAW_OP_TAG

    COMP_NAME_STR = "comp_name"
    COMP_TYPE_STR = "comp_type"
    COMP_INDEX_STR = "comp_index"
    COMP_SIDE_STR = "comp_side"
    COMP_HOST_STR = "comp_host_name"
    COMP_PARENT_STR = "comp_parent_name"
    COMP_SPACE_STR = "comp_spaces_names"
    BUILD_AXIS_STR = "build_axis"

    # TODO: BAD we can make that better pls take a look into. PLS take look how we did it in the pymel_utils
    # TODO: In line 1478. Maybe it would be a good idea to place that node into the pymel_utils.py as virtualClass
    # TODO: as the others.
    _PATH = PurePath(
        r"C:\Users\christof.puehringer\gitlab\pxo_rigging_kit\icons\operator_icon"
    )

    def __init__(
        self,
        data_container: Optional[data.DataContainer] = None,
        data_dict: Optional[dict] = None,
    ):
        """
        This class is the master class for our component operators.

        Args:

            data_container(data.DataContainer): The dataclass used to transfer data from and to EWAW_rs constructs.
            data_dict(dict): The dataclass used to transfer data from and to EWAW_rs constructs. TODO

        Examples:


        """

        if data_container:
            self.data = data_container

            _LOGGER.info("data class was given, using data class.")

        elif data_dict:
            self.data = data.DataContainer()
            self.data.dict_to_data(data_dict)

            _LOGGER.info("No data class was given, using data dict.")

        else:
            raise ValueError("BOTH ARE NOT WORKING")

        self.op_root_nd = None
        self.data.is_module = False
        self.data.is_operator = True

    def build_op_root_nd(self):
        """
        Builds the op root nd.

        Returns:
            pmc.PyNode(self.op_root_nd): The operators rood node.

        """
        self.op_root_nd = pmc.PyNode(
            container.create_container(
                container_name=self.data.op_name,
                file_path=self._PATH,
            )
        )

        return self.op_root_nd

    def set_op_root_nd(self):
        """
        Sets the root to specified world position.
        """

        cmds.xform(
            self.data.comp_root_name,
            matrix=self.data.comp_root_transforms,
            worldSpace=True,
        )

    def _generate_build_axis_mult_tpl(self):
        """
        Generates the build axes mult tpl

        Returns:
            Tuple: The generated build axes tuple.

        """
        return constants.AXIS_MAP.get(
            self.data.build_axis.upper(),
            (1.0, 0.0, 0.0),
        )

    def build_op_controls(self, root_nd=None):
        """
        Build the operators controls.

        Args:
            root_nd(pmc.PyNode()): The operator root node.
                                   If None will take the class self.op_root_nd

        Returns:
            Tuple: (root_ctrl, [All sub_ctlrs])

        """
        if not root_nd:
            root_nd = self.op_root_nd.name()
        else:
            root_nd = root_nd.name()

        diamond_ctrl_inst = curves_utils.DiamondControl()

        diamond_ctrl_inst.create_curve(
            self.data.comp_root_name,
            color_index=self.DIAMOND_CTRL_COLOR,
            buffer_grp=False,
            as_type="operator",
        )

        sub_opr_nodes = list()
        sub_ctrl_count = self.data.comp_subplacement_amount

        if sub_ctrl_count:

            sub_ctrl_inst = curves_utils.JointControl()

            for x in range(sub_ctrl_count):

                sub_ctrl_inst.create_curve(
                    f"{self.data.comp_composed_name}_sub{x:03}_{constants.OPERATOR_SUB_EXTENSION}",
                    buffer_grp=False,
                    scale=[0.5, 0.5, 0.5],
                    as_type="operator",
                )

                sub_opr_nodes.append(sub_ctrl_inst.control)

            if len(sub_opr_nodes) > 1:
                for index, sub_ctrl in enumerate(sub_opr_nodes):

                    try:
                        sub_ctrl.addChild(sub_opr_nodes[index + 1])

                    except IndexError:
                        _LOGGER.debug("ran out of list for parenting")

                for sub_ctrl in sub_opr_nodes:
                    axis_mult = self._generate_build_axis_mult_tpl()
                    # TODO: we removed this, now it is coming back
                    axis_factor = 4

                    axis_mult_factored_in = tuple(
                        axis_factor * axis for axis in axis_mult
                    )

                    sub_ctrl.translate.set(axis_mult_factored_in)

            diamond_ctrl_inst.control.addChild(sub_opr_nodes[0])

            curve_result = curves_utils.create_curve_from_transforms(
                [diamond_ctrl_inst.control] + sub_opr_nodes,
                cv_driver="loc",
                name=f"{self.data.comp_composed_name}_boneIndicator_crv",
            )

            curve_result[0].overrideEnabled.set(True)
            curve_result[0].overrideDisplayType.set(2)
            curve_result[0].inheritsTransform.set(False)
            curve_result[0].hiddenInOutliner.set(True)

            diamond_ctrl_inst.control.addChild(curve_result[1][0])

            for loc, sub_ctrl in zip(
                curve_result[1], [diamond_ctrl_inst.control] + sub_opr_nodes
            ):
                loc_shape = loc.getShape()
                loc_shape.visibility.set(0)
                cmds.parent(loc_shape.name(), sub_ctrl.name(), r=True, s=True)
                cmds.delete(loc.name())

            diamond_ctrl_inst.control.addChild(curve_result[0])

        diamond_ctrl_inst_root_nd_message_attr = node.addAttr(
            diamond_ctrl_inst.control.name(),
            longName=self.ROOT_ND_MESSAGE_ATTR,
            at="message",
            keyable=False,
        )

        if root_nd:
            cmds.connectAttr(
                f"{root_nd}.message",
                diamond_ctrl_inst_root_nd_message_attr,
            )

        self.main_opr_node = diamond_ctrl_inst.control
        self.sub_opr_nodes = sub_opr_nodes

        return diamond_ctrl_inst.control, self.sub_opr_nodes

    def set_sub_operator_controls(self):
        """
        Sets the Operator controls to pre-saved values if they exist.

        """

        if not all(
            (
                self.data.comp_subplacement_names,
                self.data.comp_subplacement_transforms,
            )
        ):
            _LOGGER.warning("NO SUBOPERATORS TO BE SET IN DATA!")
            return
        # TODO: We need to remove the pprints
        pprint(self.data.comp_subplacement_names)
        pprint(self.data.comp_subplacement_transforms)
        for subplacement_name, world_matrix in zip(
            self.data.comp_subplacement_names,
            self.data.comp_subplacement_transforms,
        ):
            cmds.xform(
                subplacement_name,
                matrix=world_matrix,
                worldSpace=True,
            )

    def set_sub_lra_controls(self):
        """
        Sets the Operator controls to pre-saved values if they exist.

        """

        for lra_name, world_matrix in zip(
            self.data.comp_lra_names, self.data.comp_lra_transforms
        ):
            cmds.xform(
                lra_name,
                matrix=world_matrix,
                worldSpace=True,
            )

    def build_lra_controls(self, main_opr_node=None, sub_opr_nodes=None):
        """
        Build the local rotation axes controls.

        Args:
            main_opr_node(pmc.PyNode): The diamond root ctrl.
                                         If None will take class var self.root_ctrl
            sub_opr_nodes(list): The sub controls.
                            If False we will build lra controls without the sub_ctrls.
                            If None we use the class var self.sub_ctrls.
                            Default is None
        """
        if not main_opr_node:
            main_opr_node = self.main_opr_node

        if sub_opr_nodes is None:
            sub_opr_nodes = self.sub_opr_nodes

        # gets rid of the ugly if else, shows their relationship better, makes the lookup easier to follow
        # even better would be to split this into its own function set or smthn, maybe not?.

        if not sub_opr_nodes:
            sub_opr_nodes = []

        lra_nodes = []
        objects_to_lra = [main_opr_node] + sub_opr_nodes
        objects_to_lra_amount = len(objects_to_lra)

        lra_control_inst = curves_utils.LocalRotateAxesControl()

        lra_control_inst.create_curve(
            f"{self.data.comp_composed_name}_main_{constants.LRA_EXTENSION.upper()}",
            scale=(0.5, 0.5, 0.5),
            color_index=False,
            lock_translate=True,
            lock_scale=True,
            lock_visibility=True,
            as_type="operator",
            buffer_grp=False,
            scale_display=4,
        )

        lra_nodes.append(pmc.PyNode(lra_control_inst.control))

        main_opr_node.addChild(pmc.PyNode(lra_control_inst.control))

        for index_, parent_obj in enumerate(sub_opr_nodes):
            lra_control_inst.create_curve(
                f"{self.data.comp_composed_name}_sub{index_:03}_{constants.LRA_EXTENSION}",
                scale=(0.5, 0.5, 0.5),
                color_index=False,
                lock_translate=True,
                lock_scale=True,
                lock_visibility=True,
                as_type="operator",
                buffer_grp=False,
                scale_display=4,
            )

            lra_nodes.append(pmc.PyNode(lra_control_inst.control))

            parent_obj.addChild(pmc.PyNode(lra_control_inst.control))

        if len(lra_nodes) > 1:
            for index_, lra_nd in enumerate(lra_nodes):
                cmds.setAttr(
                    f"{lra_nd.name()}.inheritsTransform",
                    False,
                )

                aim_mtrx_node = node.createNode(
                    "aimMatrix",
                    n=f"{self.data.comp_composed_name}_lraAim_{index_:03}_AMX",
                    tag=self.data.opr_composed_name,
                )

                aim_object = lra_nd.name()
                up_object = lra_nd.getParent().name()

                # here we check if we are already at the end of the list by finding the next node.
                try:
                    aim_to = sub_opr_nodes[index_].name()

                except IndexError:
                    cmds.connectAttr(
                        f"{up_object}.worldMatrix[0]",
                        f"{aim_object}.offsetParentMatrix",
                    )
                    continue

                aim_mtrx_data = {
                    "primaryMode": 1,
                    "primaryInputAxisX": 1,
                    "primaryInputAxisY": 0,
                    "primaryInputAxisZ": 0,
                    "primaryTargetVectorX": 0,
                    "primaryTargetVectorY": 0,
                    "primaryTargetVectorZ": 0,
                    "secondaryMode": 2,
                    "secondaryInputAxisX": 0,
                    "secondaryInputAxisY": 1,
                    "secondaryInputAxisZ": 0,
                    "secondaryTargetVectorX": 0,
                    "secondaryTargetVectorY": 1,
                    "secondaryTargetVectorZ": 0,
                }

                rig_utils.set_from_dict(
                    node=aim_mtrx_node,
                    data=aim_mtrx_data,
                )

                cmds.connectAttr(
                    f"{up_object}.worldMatrix[0]",
                    f"{aim_mtrx_node}.inputMatrix",
                )

                cmds.connectAttr(
                    f"{aim_to}.worldMatrix[0]",
                    f"{aim_mtrx_node}.primaryTargetMatrix",
                )

                cmds.connectAttr(
                    f"{up_object}.worldMatrix[0]",
                    f"{aim_mtrx_node}.secondaryTargetMatrix",
                )

                cmds.connectAttr(
                    f"{aim_mtrx_node}.outputMatrix",
                    f"{aim_object}.offsetParentMatrix",
                )
        self.data.comp_lra_names = tuple(x.longName() for x in lra_nodes)

    def pre_build_process(self):
        """
        In this method the operator can be modified before the build.
        Just override it in your class derivation.
        """
        _LOGGER.debug(
            f"{self.pre_build_process.__name__} for {self.data.comp_name} not implemented yet."
        )

    def post_build_process(self):
        """
        In this method the operator can be modified after the build.
        Just override it in your class derivation.
        For instance, you can lock or hide control attributes or modifie the metadata.
        """
        _LOGGER.debug(
            f"{self.post_build_process.__name__} for {self.data.comp_name} not implemented yet."
        )

    @DECORATORS.disable_isolate_select_update()
    def build(self):
        """
        The basic build method.
        """

        # if a new node should be created, then all the data in it needs to be updated.
        if cmds.objExists(self.data.op_name):
            cmds.select(self.data.op_name)

            raise RuntimeError(
                f"The {self.data.op_name} already exists, tell build method to build new"
            )

        self.pre_build_process()

        self.build_op_root_nd()

        self.build_op_controls()

        self.op_root_nd.addChild(self.main_opr_node)

        self.build_lra_controls()

        # setting the transforms based on data provided
        self.set_op_root_nd()
        self.set_sub_operator_controls()
        self.set_sub_lra_controls()

        data_ = self.data.data_to_dict()
        data.dict_to_node(
            node_name=self.data.op_name,
            data_dict=data_,
        )

        self.post_build_process()

        container.publish_children(
            container_name=self.data.op_name,
        )

        container.update_container_display(
            container_name=self.data.op_name,
            display_type="process",
        )

    def rebuild(self):
        """
        Rebuilds current instance of the Operator in the Scene.
        """
        cmds.delete(self.data.op_name)
        self.build()

    def build_new(self):
        """
        Builds a new instance of the Operator in the Scene.
        """

        self.update_sub_and_lra_names()
        self.build()

    def update_sub_and_lra_names(self):
        """
        Updates the index and all its dependencies.
        """

        self.data.try_to_update = True

        self.data.comp_index = self.data.comp_index

        self.data.comp_subplacement_names = self.data.comp_subplacement_amount

        if self.data.comp_lra_names:
            self.data.comp_lra_names = self.data.comp_lra_amount

        self.data.try_to_update = False

    def update_data(self):
        updated_data = data.node_to_dict(self.data.op_name)
        self.data.dict_to_data(
            data=updated_data,
        )

    def __dict__(self):
        return self.data.data_to_dict()
