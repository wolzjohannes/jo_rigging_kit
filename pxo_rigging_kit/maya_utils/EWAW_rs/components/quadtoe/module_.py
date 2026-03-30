

from importlib import reload

import logging
from pprint import pprint

from future import standard_library

from typing import Optional

from maya import cmds
from pymel import core as pmc

import pxo_rigging_kit.maya_utils.rigging.rig_utils
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
                 l=True
                 )

    cmds.setAttr(f"{single_out_rotation}.useScale",
                 0,
                 l=True
                 )

    cmds.setAttr(f"{single_out_rotation}.useShear",
                 0,
                 l=True
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
        self.deformers = list()

    def create_inputs(self):
        connector = self.data.comp_parent_name

        if not self.data.comp_lra_transforms:
            main_and_sub = list(self.data.comp_subplacement_transforms[:])

        main_and_sub = list(self.data.comp_lra_transforms[1:])

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

        self.global_scale_connection_attr = node.addAttr(f"{self.data.input_grp_name}",
                                                         ln="global_scale",
                                                         at="double",
                                                         dv=1,
                                                         )

        offset_values = rig_utils.generate_offsets(connector=connector,
                                                   operator_transformations=main_and_sub,
                                                   )

        # offsets from the guides themselves
        cmds.addAttr(f"{self.data.input_grp_name}", ln="op_offsets", dt="matrix", multi=True)

        for iteration__, value in enumerate(offset_values):
            attr_name = f"{self.data.input_grp_name}.op_offsets[{iteration__}]"
            cmds.setAttr(attr_name, value, type="matrix")
            self.controller_offset_attrs.append(attr_name)

        self.space_control_relation = dict()
        self.space_control_attrs = list()

        # control aim spaces
        for control_space in self.data.comp_spaces:
            control_space_connection_attr = node.addAttr(self.data.input_grp_name,
                                                         ln=f"{self.data.comp_composed_name}_{control_space}_space",
                                                         at="matrix",
                                                         )
            self.space_control_attrs.append(control_space_connection_attr)
            control_space_attr = node.addAttr(self.data.input_grp_name,
                                              ln=f"{self.data.comp_composed_name}_{control_space}_space_composed",
                                              at="matrix",
                                              multi=True)

            parent_world_matrix = matrix_maths.get_world_matrix(control_space)
            inverted_parent_matrix = matrix_maths.invert_matrix(parent_world_matrix)

            self.space_control_relation[control_space_attr] = list()
            for iteration_, child_world_tuple in enumerate(main_and_sub):
                child_world_matrix = matrix_maths.tuple_to_mmatrix(child_world_tuple)
                child_into_parent_space = matrix_maths.multiply_matrices(child_world_matrix, inverted_parent_matrix)
                matrix_tuple = matrix_maths.mmatrix_to_tuple(child_into_parent_space)

                cmds.setAttr(f"{control_space_attr}[{iteration_}]",
                             *matrix_tuple,
                             type="matrix"
                             )

                self.space_control_relation[control_space_attr].append(f"{control_space_attr}[{iteration_}]")

        space_attrs = node.addAttr(self.host_ctrl,
                                   ln=f"spaces_{self.data.comp_composed_name}",
                                   at="enum",
                                   enumName=':'.join(self.data.comp_spaces),
                                   k=True,
                                   )

    def create_controls(self):
        """

        Returns:

        """
        offsets = self.controller_offset_attrs

        multiplies = list()

        self.prim_controls = list()

        FkCreator_ = curves_utils.ArrowsOnBallControl()

        for iteration_, _ in enumerate(offsets):

            ctrl_name = FkCreator_.create_curve(
                    name=f"{self.data.comp_composed_name}_fk_{iteration_:03}_ctrl",
                    color_index=self.data.primary_color,
                    buffer_grp=False,
                    scale=(.2, .2, .2),
                    tag=self.data.comp_composed_name,

            )

            self.prim_controls.append(ctrl_name)

        for iteration_, offset in enumerate(offsets):
            mult_mtx_name = node.createNode("math_MultiplyMatrix",
                                            n=f"{self.data.comp_composed_name}_fk_{iteration_:03}_MMX",
                                            tag=self.data.comp_composed_name,
                                            )

            cmds.connectAttr(f"{offset}", f"{mult_mtx_name}.input1", f=True)

            # we need to skip the first iteration, if we do not, we create a cycle
            if iteration_ != 0:
                cmds.connectAttr(f"{self.prim_controls[iteration_ - 1]}.worldMatrix",
                                 f"{mult_mtx_name}.input2",
                                 f=True
                                 )

            else:
                global_scale_to_tweaker = node.createNode("math_MatrixFromTRS",
                                                          n=f"{self.data.comp_composed_name}_tweakerScaling_MFT",
                                                          tag=self.data.comp_composed_name
                                                          )

                global_scale_times_tweaker = node.createNode("math_MultiplyMatrix",
                                                             n=f"{self.data.comp_composed_name}_tweakerScaling_MMX",
                                                             tag=self.data.comp_composed_name
                                                             )

                for axis in "XYZ":
                    cmds.connectAttr(self.global_scale_connection_attr,
                                     f"{global_scale_to_tweaker}.scale{axis}"
                                     )

                cmds.connectAttr(f"{self.data.input_grp_name}.op_connector",
                                 f"{global_scale_times_tweaker}.input2"
                                 )

                cmds.connectAttr(f"{global_scale_to_tweaker}.output",
                                 f"{global_scale_times_tweaker}.input1"
                                 )

                cmds.connectAttr(f"{global_scale_times_tweaker}.output",
                                 f"{mult_mtx_name}.input2",
                                 f=True
                                 )


            multiplies.append(mult_mtx_name)

        for mult_mtx_name, controller in zip(multiplies,
                                             self.prim_controls
                                             ):

            cmds.connectAttr(f"{mult_mtx_name}.output", f"{controller}.offsetParentMatrix")

        # parents the controls under the primaries group for now :)
        cmds.parent(self.prim_controls, self.data.primaries_grp_name)

        # create outputs of the control system
        # not sure if the edge of this should be in here or in the create calculations
        for iteration_, ctrl_name_ in enumerate(self.prim_controls):
            calc_name = f"{self.data.calculation_grp_name}.ctrl_postition_{iteration_:03}"
            cmds.addAttr(self.data.calculation_grp_name, ln=f"ctrl_postition_{iteration_:03}", dt="matrix")

            cmds.connectAttr(f"{ctrl_name_}.worldMatrix",
                             calc_name,
                             )

            self.calculation_attrs.append(calc_name)

        self.all_controls.extend(self.prim_controls)

    def create_calculations(self):



        blend_matrix_outputs = list()
        blend_matrix_names = list()
        self.blend_matrix_weight_attrs = list()

        for iteration_, prim_control in enumerate(self.prim_controls, 1):
            spaces_ = []

            for space_index, space_ in enumerate(self.space_control_relation):
                mult_mtx_name = f"{self.data.comp_composed_name}_{self.data.comp_spaces[space_index]}_{iteration_:03}_MMX"

                mult_name = node.createNode("math_MultiplyMatrix",
                                            n=mult_mtx_name,
                                            tag=self.data.comp_composed_name)

                cmds.connectAttr(f"{space_}[{iteration_}]",
                                 f"{mult_name}.input1"
                                 )

                cmds.connectAttr(self.space_control_attrs[space_index],
                                 f"{mult_name}.input2"
                                 )

                spaces_.append(f"{mult_name}.output")

            blend_matrix_name, weight_attr = rig_utils.space_switcher(space_attributes=spaces_,
                                                                      name=self.data.comp_composed_name,
                                                                      subname="toeSpace",
                                                                      iteration=iteration_,
                                                                      tag=self.data.comp_composed_name,
                                                                      )

            blend_matrix_outputs.append(f"{blend_matrix_name}.outputMatrix")
            blend_matrix_names.append(blend_matrix_name)
            self.blend_matrix_weight_attrs.append(weight_attr)

        # adapted_aim_positions = blend_matrix_outputs[1:]
        adapted_aim_positions = blend_matrix_outputs[1:]
        adapted_aim_up_objects = blend_matrix_outputs[0:-1]
        adapted_finger_controls = self.prim_controls[:-1]

        created_aim_matrix = None
        cmds.setAttr(self.blend_matrix_weight_attrs[0], 2)
        aim_matrices = list()
        for iteration_, (finger_control, finger_aim, finger_up) in enumerate(zip(adapted_finger_controls,
                                                                                 adapted_aim_positions,
                                                                                 adapted_aim_up_objects,
                                                                                 )
                                                                             ):

            control_node, created_aim_matrix = create_object_rotation_aim(finger_control,
                                                                          finger_aim,
                                                                          finger_up,
                                                                          created_aim_matrix,
                                                                          iteration=iteration_,
                                                                          name=self.data.comp_composed_name,
                                                                          tag=self.data.comp_composed_name,
                                                                          first_connection=blend_matrix_outputs[0]
                                                                          )

            aim_matrices.append(created_aim_matrix)
        self.first_aim_matrix = aim_matrices[0]

    def create_outputs(self):
        """

        Returns:

        """
        self.deformers = []
        output_attrs = self.calculation_attrs

        for idx_, output_ in enumerate(output_attrs):
            jnt_name = node.createNode("joint",
                                       n=f"{self.data.comp_composed_name}_output_{idx_:03}_JNT",
                                       tag=self.data.comp_composed_name,
                                       )

            cmds.connectAttr(output_,
                             f"{jnt_name}.offsetParentMatrix",
                             )

            cmds.setAttr(f"{jnt_name}.inheritsTransform", False, l=True)

            self.deformers.append(jnt_name)

        cmds.parent(self.deformers,
                    self.data.output_grp_name,
                    )

    def connect(self):
        """
        connects the module to the one above.

        """

        compare_for_space_switch = node.createNode("math_CompareInt",
                                                   n=f"{self.data.comp_composed_name}_CRI",
                                                   tag=self.data.comp_composed_name
                                                   )

        select_for_space_switch = node.createNode("math_Select",
                                                  n=f"{self.data.comp_composed_name}_SLC",
                                                  tag=self.data.comp_composed_name
                                                  )

        cmds.connectAttr(f"{self.host_ctrl}.ikFkBlend", f"{compare_for_space_switch}.input1")
        cmds.connectAttr(f"{compare_for_space_switch}.output", f"{select_for_space_switch}.condition")
        cmds.setAttr(f"{select_for_space_switch}.input1", 3)

        for i in self.blend_matrix_weight_attrs:
            previous_settings = cmds.getAttr(i)
            cmds.setAttr(f"{select_for_space_switch}.input2", previous_settings)

            cmds.connectAttr(f"{select_for_space_switch}.output", i)

        for comp_space_node_name_, comp_space_control_attr_ in zip(self.data.comp_spaces,
                                                                   self.space_control_attrs,
                                                                   ):

            cmds.connectAttr(f"{comp_space_node_name_}.worldMatrix",
                             comp_space_control_attr_,
                             )
        cmds.connectAttr("global_0_ctrl.main_scale", self.global_scale_connection_attr)

        # connect the funnies
        self.deformer_set_name = f"{self.data.comp_composed_name}_deformers_SET"
        cmds.sets(self.deformers, n=self.deformer_set_name)

        self.controller_set_name = f"{self.data.comp_composed_name}_controllers_SET"

        cmds.sets(self.all_controls, n=self.controller_set_name)

        node.addAttr(self.deformer_set_name, ln=self.data.comp_composed_name, at="message")
        node.addAttr(self.controller_set_name, ln=self.data.comp_composed_name, at="message")

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
