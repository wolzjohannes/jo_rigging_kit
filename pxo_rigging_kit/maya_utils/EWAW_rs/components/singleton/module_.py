

from importlib import reload

import logging
from pprint import pprint

from future import standard_library

from typing import Optional

from maya import cmds
from pymel import core as pmc

from pxo_rigging_kit import constants
from pxo_rigging_kit.maya_utils.EWAW_rs import matrix_maths, node
from pxo_rigging_kit.maya_utils.EWAW_rs.base_constructs import module
from pxo_rigging_kit.maya_utils.EWAW_rs.base_constructs import data
from pxo_rigging_kit.maya_utils.EWAW_rs import TO_REFACTOR as TO_REFACTOR_PLS
from pxo_rigging_kit.maya_utils.rigging import rig_utils, curves_utils

reload(module)
reload(TO_REFACTOR_PLS)
reload(rig_utils)

##########################################################
# GLOBALS
##########################################################

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)
standard_library.install_aliases()


def create_object_rotation_aim(controller_node: str,
                               primary_attr: str,
                               secondary_attr: str,
                               previous_aim_matrix: Optional[str],
                               name: str = "defaultObjectRotationAim",
                               iteration: Optional[int] = None,
                               tag: Optional[str] = None,
                               first_connection: Optional[str] = None,
                               first_target: Optional[str] = None,
                               ) -> (str, str):

    iteration_ = f"_{iteration:03}" if iteration is not None else ""
    controller_input_attr = f"{controller_node}.offsetParentMatrix"

    inverse_position_node = cmds.listConnections(controller_input_attr)[0]
    inverse_position_attr = f"{inverse_position_node}.output"

    controller_parent_node = cmds.listConnections(f"{inverse_position_node}.input2")[0]
    controller_parent_node_attr = f"{controller_parent_node}.worldMatrix[0]"

    if iteration == 0 and first_connection:
        controller_parent_node_attr = first_connection

    aim_matrix = node.createNode("aimMatrix",
                                 n=f"{name}_aimToNext{iteration_}_AMX",
                                 tag=tag
                                 )

    invert_matrix = node.createNode("math_InverseMatrix",
                                    n=f"{name}_inversion{iteration_}_IMX",
                                    tag=tag)

    find_offset = node.createNode("math_MultiplyMatrix",
                                  n=f"{name}_addOffset{iteration_}_MMX",
                                  tag=tag)

    single_out_rotation = node.createNode("pickMatrix",
                                          n=f"{name}_pickLocalRotation{iteration_}_PMX",
                                          tag=tag)

    add_rotation_to_local_offset = node.createNode("math_MultiplyMatrix",
                                                   n=f"{name}_addRotationToLocalOffset{iteration_}_MMX",
                                                   tag=tag
                                                   )

    inverse_position_node_duplicate = cmds.duplicate(inverse_position_node,
                                                     n=f"{name}_inversionFUCK{iteration_}_MMX"
                                                     )[0]

    aim_matrix_attrs_ = {"primaryMode": 1,
                         "primaryInputAxisX": 1,
                         "primaryInputAxisY": 0,
                         "primaryInputAxisZ": 0,
                         "primaryTargetVectorX": 0,
                         "primaryTargetVectorY": 0,
                         "primaryTargetVectorZ": 0,

                         "secondaryMode": 2,
                         "secondaryInputAxisX": 0,
                         "secondaryInputAxisY": 0,
                         "secondaryInputAxisZ": 1,
                         "secondaryTargetVectorX": 0,
                         "secondaryTargetVectorY": 0,
                         "secondaryTargetVectorZ": 1,
                         }

    rig_utils.set_from_dict(aim_matrix, aim_matrix_attrs_)

    cmds.setAttr(f"{single_out_rotation}.useTranslate",
                 0,
                 l=True,
                 )

    cmds.setAttr(f"{single_out_rotation}.useScale",
                 0,
                 l=True,
                 )

    cmds.setAttr(f"{single_out_rotation}.useShear",
                 0,
                 l=True,
                 )

    # this is to keep the inheritance chain stable and free of the aim, on the first and last is not needed
    # break this and get the strangest fk behaviour that ONLY inherits the one before in the chain but nothin further.

    cmds.connectAttr(secondary_attr,
                     f"{aim_matrix}.secondaryTargetMatrix",
                     f=True
                     )

    cmds.connectAttr(inverse_position_attr,
                     f"{aim_matrix}.secondaryTargetMatrix",
                     f=True
                     )

    if previous_aim_matrix:
        cmds.connectAttr(f"{previous_aim_matrix}.outputMatrix",
                         f"{inverse_position_node}.input2",
                         f=True
                         )

        cmds.connectAttr(secondary_attr,
                         f"{aim_matrix}.secondaryTargetMatrix",
                         f=True
                         )

    cmds.connectAttr(inverse_position_attr,
                     f"{invert_matrix}.input",
                     f=True
                     )

    cmds.connectAttr(inverse_position_attr,
                     f"{aim_matrix}.inputMatrix",
                     f=True
                     )

    cmds.connectAttr(primary_attr,
                     f"{aim_matrix}.primaryTargetMatrix",
                     f=True
                     )

    cmds.connectAttr(f"{aim_matrix}.outputMatrix",
                     f"{find_offset}.input1",
                     f=True
                     )

    cmds.connectAttr(f"{invert_matrix}.output",
                     f"{find_offset}.input2",
                     f=True
                     )

    cmds.connectAttr(f"{find_offset}.output",
                     f"{single_out_rotation}.inputMatrix",
                     f=True
                     )

    cmds.connectAttr(controller_parent_node_attr,
                     f"{inverse_position_node_duplicate}.input2",
                     f=True
                     )

    # we are at the pick to multiply
    cmds.connectAttr(f"{single_out_rotation}.outputMatrix",
                     f"{add_rotation_to_local_offset}.input1",
                     f=True
                     )
    # create the rotational add offset
    cmds.connectAttr(f"{inverse_position_node_duplicate}.output",
                     f"{add_rotation_to_local_offset}.input2",
                     f=True,
                     )

    cmds.connectAttr(f"{add_rotation_to_local_offset}.output",
                     controller_input_attr,
                     f=True
                     )

    # if the iteration is zero we DO NOT need to create the rotational offset, so this goes back
    if iteration == 0:
        cmds.connectAttr(f"{aim_matrix}.outputMatrix",
                         controller_input_attr,
                         f=True,
                         )

    return controller_node, aim_matrix


class Main(module.BaseModule):
    """
    builds the implementation of a module, gets the basic build inherited from BaseModule.

    """
    def __init__(self,
                 data_container: Optional[data.DataContainer] = None
                 ):
        """
        This class is the master class for our rigging modules.


        """

        super().__init__(
                         data_container=data_container
                         )

        # information created in class instance
        self.connector_attrs = list()
        self.controller_offset_attrs = list()
        self.controller_attrs = list()
        self.calculation_attrs = list()

    def create_inputs(self):
        connector = self.data.comp_parent_name

        if not self.data.comp_lra_transforms:
            main_and_sub = list(self.data.comp_subplacement_transforms[:])

        main_and_sub = list(self.data.comp_lra_transforms[:])

        # check how it should be placed into the parent space

        self.connector_attrs.append(self.connector_name)

        cmds.setAttr(self.connector_name,
                     *self.data.comp_root_transforms,
                     type="matrix"
                     )

        if connector:
            cmds.connectAttr(f"{connector}.worldMatrix",
                             f"{self.data.input_grp_name}.op_connector",
                             f=True
                             )

        # positions from the guides themselves
        cmds.addAttr(f"{self.data.input_grp_name}", ln="op_positions", dt="matrix", multi=True)

        for iteration__, (name, value) in enumerate(zip(self.data.comp_lra_names,
                                                        self.data.comp_lra_transforms,
                                                        )
                                                    ):
            attr_name = f"{self.data.input_grp_name}.op_positions[{iteration__}]"
            pmc.setAttr(attr_name, value, type="matrix")
            self.controller_attrs.append(attr_name)

        offset_values = rig_utils.generate_offsets(connector=connector,
                                                   operator_transformations=main_and_sub,
                                                   )
        # offsets from the guides themselves
        cmds.addAttr(f"{self.data.input_grp_name}", ln="op_offsets", dt="matrix", multi=True)

        for iteration__, value in enumerate(offset_values):
            attr_name = f"{self.data.input_grp_name}.op_offsets[{iteration__}]"
            cmds.setAttr(attr_name, value, type="matrix")
            self.controller_offset_attrs.append(attr_name)

    def create_controls(self):
        """

        Returns:

        """

        self.prim_controls = list()

        FkCreator_ = curves_utils.ArrowsOnBallControl()

        ctrl_name = FkCreator_.create_curve(
                name=f"{self.data.comp_composed_name}_fk_{0:03}_ctrl",
                color_index=self.data.primary_color,
                buffer_grp=False,
                scale=(.2, .2, .2),
                tag=self.data.comp_composed_name,

        )

        self.prim_controls.append(ctrl_name)

        # parents the controls under the primaries group for now :)
        cmds.parent(self.prim_controls, self.data.primaries_grp_name)

        # create outputs of the control system
        # not sure if the edge of this should be in here or in the create calculations
        for iteration_, ctrl_name_ in enumerate(self.prim_controls):
            calc_name = f"{self.data.calculation_grp_name}.ctrl_postition_{iteration_:03}"

            cmds.addAttr(self.data.calculation_grp_name,
                         ln=f"ctrl_postition_{iteration_:03}",
                         dt="matrix",
                         )

            cmds.connectAttr(f"{ctrl_name_}.worldMatrix",
                             calc_name,
                             )

            self.calculation_attrs.append(calc_name)

        self.all_controls.extend(self.prim_controls)

    def create_calculations(self):
        connector_attr = self.connector_attrs[0]

        for ctrl_, ctrl_offset_ in zip(self.prim_controls, self.controller_offset_attrs):

            mult_node = node.createNode("math_MultiplyMatrix",
                                        tag=self.data.comp_composed_name,
                                        name=f"{self.data.comp_composed_name}_MMX",
                                        )

            cmds.connectAttr(ctrl_offset_,
                             f"{mult_node}.input1",
                             )

            cmds.connectAttr(connector_attr,
                             f"{mult_node}.input2",
                             )

            cmds.connectAttr(f"{mult_node}.output",
                             f"{ctrl_}.offsetParentMatrix",
                             )

    def create_outputs(self):
        """

        Returns:

        """
        self.deformers = []
        output_attrs = self.calculation_attrs

        for idx_, output_ in enumerate(output_attrs):
            jnt_name = node.createNode("joint",
                                       n=f"{self.data.comp_composed_name}_output_{idx_:03}_jnt",
                                       tag=self.data.comp_composed_name,
                                       )

            cmds.connectAttr(output_,
                             f"{jnt_name}.offsetParentMatrix",
                             )

            cmds.setAttr(f"{jnt_name}.inheritsTransform",
                         False,
                         l=True,
                         )

            self.deformers.append(jnt_name)

        cmds.parent(self.deformers,
                    self.data.output_grp_name,
                    )

    def connect(self):
        """
        connects the module to the one above.

        """

        self.deformer_set_name = f"{self.data.comp_composed_name}_deformers_SET"
        cmds.sets(self.deformers, n=self.deformer_set_name)

        self.controller_set_name = f"{self.data.comp_composed_name}_controllers_SET"
        cmds.sets(self.all_controls, n=self.controller_set_name)

        node.addAttr(self.deformer_set_name,
                     ln=self.data.comp_composed_name,
                     at="message"
                     )

        node.addAttr(self.controller_set_name,
                     ln=self.data.comp_composed_name,
                     at="message"
                     )

        cmds.sets(self.deformer_set_name,
                  add=constants.PXO_DEFORMERS_SET_NAME,
                  e=True,
                  )

        cmds.sets(self.controller_set_name,
                  add=constants.PXO_CONTROLS_SET_NAME,
                  e=True,
                  )

    def disconnect(self):
        """
        disconnects the module to the one above.

        """

        pass
