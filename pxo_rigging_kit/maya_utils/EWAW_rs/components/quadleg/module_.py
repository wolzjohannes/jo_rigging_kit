import itertools
from importlib import reload

import logging

from future import standard_library

from typing import Optional

from maya import cmds, mel
from pymel import core as pmc
from maya.api import OpenMaya as om2

from pxo_rigging_kit import constants
from pxo_rigging_kit.maya_utils import attributes_utils
from pxo_rigging_kit.maya_utils.EWAW_rs.matrix_maths import isolate_rotation_matrix
from pxo_rigging_kit.maya_utils.post_and_pre_build import scapula_setup
from pxo_rigging_kit.maya_utils.rigging.algorythms import de_boor
from pxo_rigging_kit.maya_utils.EWAW_rs import TO_REFACTOR as TO_REFACTOR_PLS

from pxo_rigging_kit.maya_utils.EWAW_rs import matrix_maths, node
from pxo_rigging_kit.maya_utils.EWAW_rs.base_constructs import data, module

from pxo_rigging_kit.maya_utils.rigging import rig_utils, curves_utils


reload(rig_utils)
reload(curves_utils)
reload(de_boor)
reload(matrix_maths)
reload(module)
reload(data)
reload(TO_REFACTOR_PLS)
reload(node)
reload(scapula_setup)

##########################################################
# GLOBALS
##########################################################

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)
standard_library.install_aliases()


def create_ik_solver(start_node: str,
                     end_node: str,
                     new_name: Optional[str],
                     new_subname: Optional[str],
                     solver: str = "ikRPsolver",
                     tag: str = "lol",
                     hdl_sfx: str = "IKH",
                     eff_sfx: str = "EFF",
                     ) -> tuple:
    """

    Args:
        start_node:
        end_node:
        new_name:
        new_subname:
        solver:
        tag:

    Returns:

    """
    new_name_ = new_name or "defaultName"
    new_subname_ = new_subname or "defaultSubname"

    old_ik_handle, old_ik_effector = cmds.ikHandle(sj=start_node,
                                                   ee=end_node,
                                                   sol=solver,
                                                   )

    cmds.addAttr(old_ik_handle, ln=tag, at="message")
    cmds.setAttr(f"{old_ik_handle}.template", 1)

    ik_handle_name, ik_effector_name = (f"{new_name_}_{new_subname_}_{hdl_sfx}",
                                        f"{new_name_}_{new_subname_}_{eff_sfx}")

    cmds.rename(old_ik_handle, ik_handle_name)
    cmds.rename(old_ik_effector, ik_effector_name)

    return ik_handle_name, ik_effector_name


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
        self.lra_mmatrices = None
        self.total_length = None
        self.segment_lengths = None

        self.total_length_attr = None
        self.ik_hip_placement_attr = None
        self.ik_foot_placement_attr = None
        self.global_scale_connection_attr = None
        self.lower_secondary_pv_space_switch_attr = None
        self.upper_secondary_pv_space_switch_attr = None
        self.lower_secondary_input_pv_space_switch_attr = None
        self.upper_secondary_input_pv_space_switch_attr = None

        self.host_ik_fk_attr = None
        self.host_hip_space_switch_attr = None
        self.host_foot_space_switch_attr = None
        self.host_pv_space_switch_attr = None
        self.host_stretch_attr = None
        self.host_blend_attr = None
        self.host_legbend_attr = None
        self.host_lock_hip_attr = None
        self.host_lock_ankle_attr = None
        self.host_foot_follow_attr = None
        self.host_fk_follow_attrs = None

        self.connector_attrs = list()
        self.controller_offset_attrs = list()
        self.controller_offset_rot_only_attrs = list()
        self.fk_static_rotation_attrs = list()
        self.footroll_offset_attrs = list()
        self.controller_attrs = list()
        self.calculation_attrs = list()
        self.segment_length_attrs = list()
        self.space_attrs = dict()

        self.deformers = list()

        self.ik_controls = list()
        self.ik_calculation_attrs = list()

        self.fk_controls = list()
        self.fk_calculation_attrs = list()

        self.footroll_controls = list()

        mel.eval("ik2Bsolver;")
        mel.eval("ikSpringSolver;")

    def create_inputs(self):

        # empty list for saveguarding
        self.controller_offset_attrs = []
        self.connector_attrs = []

        if self.data.comp_lra_transforms:
            total_transforms = list(self.data.comp_lra_transforms[1:])

        else:
            total_transforms = list(self.data.comp_subplacement_transforms[:])

        total_transforms.insert(0,
                                self.data.comp_root_transforms
                                )

        leg_transforms = total_transforms[:7]
        reverse_foot_transforms = total_transforms[4:10]

        # double the second control to have one localised and one global roll
        reverse_foot_transforms.insert(1, reverse_foot_transforms[1])

        self.lra_mmatrices = matrix_maths.convert_lra_mtxtuples_to_mmatrices(tuple(self.data.comp_lra_transforms))
        self.total_length, self.segment_lengths = matrix_maths.calculate_distances(self.lra_mmatrices[1:5])

        # input the lengths
        self.total_length_attr = node.addAttr(f"{self.data.input_grp_name}",
                                              ln="op_length_total",
                                              at="double",
                                              dv=self.total_length
                                              )

        cmds.setAttr(f"{self.data.input_grp_name}.op_length_total",
                     self.total_length,
                     )

        attr_name = node.addAttr(f"{self.data.input_grp_name}",
                                 ln="op_lengths",
                                 at="double",
                                 multi=True,
                                 )

        for iteration__, value in enumerate(self.segment_lengths):
            attr_name_ = f"{attr_name}[{iteration__}]"

            cmds.setAttr(attr_name_,
                         value,
                         )

            self.segment_length_attrs.append(attr_name_)

        # check how it should be placed into the parent space
        self.connector_attrs.append(f"{self.data.input_grp_name}.op_connector")

        cmds.setAttr(f"{self.data.input_grp_name}.op_connector",
                     *self.data.comp_root_transforms,
                     type="matrix"
                     )

        if self.data.connector:
            cmds.connectAttr(f"{self.data.connector}.out_connection",
                             f"{self.data.input_grp_name}.op_connector",
                             f=True
                             )

        # positions from the guides themselves
        attr_name = node.addAttr(f"{self.data.input_grp_name}", ln="op_positions", dt="matrix", multi=True)

        for iteration__, (name, value) in enumerate(zip(self.data.comp_lra_names,
                                                        self.data.comp_lra_transforms
                                                        )
                                                    ):

            attr_name_ = f"{attr_name}[{iteration__}]"
            cmds.setAttr(attr_name_,
                         value,
                         type="matrix"
                         )

            self.controller_attrs.append(attr_name_)

        offset_values = rig_utils.generate_offsets(connector=None,
                                                   operator_transformations=leg_transforms,
                                                   )

        # offsets from the guides themselves
        attr_name = node.addAttr(f"{self.data.input_grp_name}",
                                 ln="op_offsets",
                                 dt="matrix",
                                 multi=True
                                 )

        for iteration__, value in enumerate(offset_values):
            attr_name_ = f"{attr_name}[{iteration__}]"
            cmds.setAttr(attr_name_,
                         value,
                         type="matrix"
                         )

            self.controller_offset_attrs.append(attr_name_)

        # offset rotations from the guides themselves
        node.addAttr(f"{self.data.input_grp_name}",
                     ln="op_offset_rot_only",
                     dt="matrix",
                     multi=True
                     )

        for iteration__, value in enumerate(offset_values):
            # segmenting out the value
            value = isolate_rotation_matrix(value)

            attr_name = f"{self.data.input_grp_name}.op_offset_rot_only[{iteration__}]"
            cmds.setAttr(attr_name,
                         value,
                         type="matrix"
                         )

            self.controller_offset_rot_only_attrs.append(attr_name)

        roll_guides = list(reversed(reverse_foot_transforms))
        foot_roll_offsets = rig_utils.generate_offsets(connector=self.data.comp_subplacement_nodes[3],
                                                       operator_transformations=roll_guides,
                                                       )

        cmds.addAttr(f"{self.data.input_grp_name}",
                     ln="footroll_offsets",
                     dt="matrix",
                     multi=True
                     )

        for iteration__, value in enumerate(foot_roll_offsets):
            attr_name = f"{self.data.input_grp_name}.footroll_offsets[{iteration__}]"
            cmds.setAttr(attr_name,
                         value,
                         type="matrix"
                         )

            self.footroll_offset_attrs.append(attr_name)

        # start of chain attribute
        self.ik_hip_placement_attr = node.addAttr(f"{self.data.input_grp_name}",
                                                  ln="start_of_chain",
                                                  dt="matrix",
                                                  )

        cmds.setAttr(self.ik_hip_placement_attr, *self.data.comp_subplacement_transforms[0], type="matrix")

        # end of chain attribute
        self.ik_foot_placement_attr = node.addAttr(f"{self.data.input_grp_name}",
                                                   ln="end_of_chain",
                                                   dt="matrix",
                                                   )

        cmds.setAttr(self.ik_foot_placement_attr,
                     *self.data.comp_subplacement_transforms[3],
                     type="matrix"
                     )

        # creating the space attributes derived from the data input
        if self.data.comp_spaces:
            for obj_to_switch, position_in_data in (("hip", 0), ("foot", 3), ("pv", 1)):
                space_attr_names_ = list()
                for idx_, space_name in enumerate(self.data.comp_spaces):
                    space_name_ = node.addAttr(f"{self.data.input_grp_name}",
                                               ln=f"space_{obj_to_switch}_{idx_:03}_{space_name}",
                                               dt="matrix"
                                               )

                    cmds.setAttr(space_name_,
                                 *self.data.comp_subplacement_transforms[position_in_data],
                                 type="matrix"
                                 )

                    space_attr_names_.append(space_name_)

                self.space_attrs[obj_to_switch] = space_attr_names_

        # scale attribute global
        self.global_scale_connection_attr = node.addAttr(f"{self.data.input_grp_name}",
                                                         ln="global_scale",
                                                         at="double",
                                                         dv=1,
                                                         )

        self.lower_secondary_input_pv_space_switch_attr = node.addAttr(f"{self.data.input_grp_name}",
                                                                       ln="lower_pv_spaces",
                                                                       at="enum",
                                                                       enumName=":".join(("primaryPV",
                                                                                          "ankleAdjust"
                                                                                          )
                                                                                         ),
                                                                       k=True,
                                                                       )

        self.upper_secondary_input_pv_space_switch_attr = node.addAttr(f"{self.data.input_grp_name}",
                                                                       ln="upper_pv_spaces",
                                                                       at="enum",
                                                                       enumName=":".join(("primaryPV",
                                                                                          "hipAdjust"
                                                                                          )
                                                                                         ),
                                                                       k=True,
                                                                       )

        self._create_host_attributes()

    def _create_host_attributes(self):
        """
        Segments out the creation of host attributes
        This method is here to segment out the code, and make it more readable.

        """

        self.host_ik_fk_attr = rig_utils.add_normalized_attr(node_name=self.host_ctrl,
                                                        attr_name="ikFkBlend",
                                                        min_value=0,
                                                        max_value=10,
                                                        tag=self.data.comp_composed_name,
                                                        )

        attributes_utils.add_pxo_separator_attr(self.host_ctrl, attr_name="ik_attributes", as_pymel=False)

        # actually create the attributes on the host node
        if self.data.comp_spaces:
            enum_name_ = f"{self.data.comp_parent_name}:{':'.join(self.data.comp_spaces)}"
            self.host_hip_space_switch_attr = node.addAttr(self.host_ctrl,
                                                           ln="hip_spaces",
                                                           at="enum",
                                                           enumName=enum_name_,
                                                           k=True,
                                                           )

            self.host_foot_space_switch_attr = node.addAttr(self.host_ctrl,
                                                            ln="foot_spaces",
                                                            at="enum",
                                                            enumName=enum_name_,
                                                            k=True,
                                                            )

            self.host_pv_space_switch_attr = node.addAttr(self.host_ctrl,
                                                          ln="pv_spaces",
                                                          at="enum",
                                                          enumName=enum_name_,
                                                          k=True,
                                                          )

        self.lower_secondary_pv_space_switch_attr = node.addAttr(self.host_ctrl,
                                                                 ln="lower_pv_spaces",
                                                                 at="enum",
                                                                 enumName=":".join(("primaryPV", "ankleAdjust")),
                                                                 k=True,
                                                                 )

        self.upper_secondary_pv_space_switch_attr = node.addAttr(self.host_ctrl,
                                                                 ln="upper_pv_spaces",
                                                                 at="enum",
                                                                 enumName=":".join(("primaryPV", "hipAdjust")),
                                                                 k=True,
                                                                 )

        self.host_stretch_attr = rig_utils.add_normalized_attr(node_name=self.host_ctrl,
                                                          attr_name="stretch",
                                                          min_value=0,
                                                          max_value=10,
                                                          tag=self.data.comp_composed_name,
                                                          )

        self.host_blend_attr = rig_utils.add_normalized_attr(node_name=self.host_ctrl,
                                                        attr_name="plantigrade_bias",
                                                        min_value=-10,
                                                        max_value=10,
                                                        tag=self.data.comp_composed_name,
                                                        )

        self.host_legbend_attr = rig_utils.add_normalized_attr(node_name=self.host_ctrl,
                                                          attr_name="leg_bend_bias",
                                                          min_value=-10,
                                                          max_value=10,
                                                          tag=self.data.comp_composed_name,
                                                          )

        self.host_lock_hip_attr = rig_utils.add_normalized_attr(node_name=self.host_ctrl,
                                                           attr_name="lockHip",
                                                           min_value=0,
                                                           max_value=10,
                                                           tag=self.data.comp_composed_name,
                                                           )

        self.host_lock_ankle_attr = rig_utils.add_normalized_attr(node_name=self.host_ctrl,
                                                             attr_name="aimAnkle",
                                                             min_value=0,
                                                             max_value=10,
                                                             tag=self.data.comp_composed_name,
                                                             )

        self.host_foot_follow_attr = rig_utils.add_normalized_attr(node_name=self.host_ctrl,
                                                              attr_name="footFollow",
                                                              min_value=0,
                                                              max_value=10,
                                                              tag=self.data.comp_composed_name,
                                                              )

        attributes_utils.add_pxo_separator_attr(self.host_ctrl,
                                                attr_name="fk_attributes",
                                                as_pymel=False
                                                )
        self.host_fk_follow_attrs = list()
        for idx_ in range(len(self.controller_offset_attrs)):

            fk_follow_att = rig_utils.add_normalized_attr(node_name=self.host_ctrl,
                                                     attr_name=f"fk_fakeIk_{idx_:03}",
                                                     min_value=0,
                                                     max_value=10,
                                                     tag=self.data.comp_composed_name,
                                                     )

            self.host_fk_follow_attrs.append(fk_follow_att)


    def create_controls(self):
        """
        Derived from base module, this is filled with all the controls and pulls together their info.

        """

        offsets = self.controller_offset_attrs
        rotonly_offsets = self.controller_offset_rot_only_attrs
        positions = self.controller_attrs

        controller_offset = 0

        # empty that list for saveguarding
        self.fk_calculation_attrs = list()
        self.ik_calculation_attrs = list()

        self._create_fk_controls(offsets, rotonly_offsets)
        self._create_tweaker_controls()
        self._create_ik_controls()

        self._create_footroll_controls()
        self._connect_footroll_controls()

    def _create_footroll_controls(self):

        FootrollCreator_ = curves_utils.SpearControl1()

        for iteration_, _ in enumerate(self.footroll_offset_attrs):

            ctrl_name = FootrollCreator_.create_curve(
                    name=f"{self.data.comp_composed_name}_footRoll_{iteration_:03}_{constants.CTRL_EXTENSION}",
                    color_index=self.data.secondary_color,
                    buffer_grp=False,
                    scale=(.3, .3, .3),
                    tag=self.data.comp_composed_name
            )

            self.footroll_controls.append(ctrl_name)

        PawCreator_ = curves_utils.SpearControl1()

        self.paw_control = PawCreator_.create_curve(
                name=f"{self.data.comp_composed_name}_pawPad_{constants.CTRL_EXTENSION}",
                color_index=self.data.secondary_color,
                buffer_grp=False,
                scale=(1.3, 1.3, 1.3),
                tag=self.data.comp_composed_name
        )

    def _connect_footroll_controls(self):
        """
        Segmentation of creation and connection for readability purposes.

        """

        for iteration_, (ctrl_, attr_) in enumerate(zip(self.footroll_controls,
                                                        self.footroll_offset_attrs,
                                                        )
                                                    ):

            mult_mtx_name = node.createNode("math_MultiplyMatrix",
                                            n=f"{self.data.comp_composed_name}_footRoll_{iteration_:03}_MMX",
                                            tag=self.data.comp_composed_name,
                                            )

            cmds.connectAttr(f"{attr_}", f"{mult_mtx_name}.input1", f=True)

            if iteration_ != 0:
                cmds.connectAttr(f"{self.footroll_controls[iteration_ - 1]}.worldMatrix",
                                 f"{mult_mtx_name}.input2",
                                 f=True
                                 )

            else:
                cmds.connectAttr(f"{self.foot_ik_ctrl}.worldMatrix",
                                 f"{mult_mtx_name}.input2",
                                 f=True
                                 )

            cmds.connectAttr(f"{mult_mtx_name}.output",
                             f"{ctrl_}.offsetParentMatrix",
                             f=True
                             )

        cmds.group(self.footroll_controls,
                   n=f"{self.data.comp_composed_name}_ikFootRoll_{constants.GRP_EXTENSION}",
                   )
        cmds.parent(self.paw_control,
                    f"{self.data.comp_composed_name}_ikFootRoll_{constants.GRP_EXTENSION}",
                    )
        cmds.parent(f"{self.data.comp_composed_name}_ikFootRoll_{constants.GRP_EXTENSION}",
                    f"{self.data.comp_composed_name}_ikPrimary_{constants.GRP_EXTENSION}"
                    )

    def _create_ik_controls(self):
        # ik stoooof
        sec_controls = list()
        prim_controls = list()

        # foot controller
        ikFootOffsetCreator_ = curves_utils.FootPrintControl()

        ikFootOffsetCreator_.create_curve(
                name=f"{self.data.comp_composed_name}_ikFootOffset_{constants.CTRL_EXTENSION}",
                buffer_grp=False,
                color_index=self.data.primary_color,
                scale=(5, 5, 5,),
                move=(.0, -2.0, .0,),
                tag=self.data.comp_composed_name,
        )

        self.foot_offset_ik_ctrl = ikFootOffsetCreator_.control_name

        cmds.connectAttr(self.ik_foot_placement_attr, f"{self.foot_offset_ik_ctrl}.offsetParentMatrix")
        sec_controls.append(self.foot_offset_ik_ctrl)

        # foot controller
        ikFootCreator_ = curves_utils.FootPrintControl()
        ikFootCreator_.create_curve(name=f"{self.data.comp_composed_name}_ikFoot_{constants.CTRL_EXTENSION}",
                                    buffer_grp=False,
                                    color_index=self.data.primary_color,
                                    scale=(4, 4, 4,),
                                    move=(.0, -2.0, .0,),
                                    tag=self.data.comp_composed_name,

                                    )
        self.foot_ik_ctrl = ikFootCreator_.control_name

        cmds.connectAttr(f"{self.foot_offset_ik_ctrl}.worldMatrix",
                         f"{self.foot_ik_ctrl}.offsetParentMatrix",
                         )

        prim_controls.append(self.foot_ik_ctrl)

        # hip controller
        ikHipCreator_ = curves_utils.BoxControl()
        ikHipCreator_.create_curve(name=f"{self.data.comp_composed_name}_ikHip_{constants.CTRL_EXTENSION}",
                                   buffer_grp=False,
                                   color_index=self.data.primary_color,
                                   tag=self.data.comp_composed_name,

                                   )
        self.hip_ik_ctrl = ikHipCreator_.control_name
        cmds.connectAttr(self.ik_hip_placement_attr, f"{self.hip_ik_ctrl}.offsetParentMatrix")
        prim_controls.append(self.hip_ik_ctrl)

        # polevector controller
        mainPvCreator_ = curves_utils.SingleArrowFatControl()
        mainPvCreator_.create_curve(name=f"{self.data.comp_composed_name}_ikPv_{constants.CTRL_EXTENSION}",
                                    buffer_grp=False,
                                    scale=(5, 5, 5,),
                                    color_index=self.data.primary_color,
                                    tag=self.data.comp_composed_name,

                                    )
        self.pv_ik_ctrl = mainPvCreator_.control_name
        cmds.connectAttr(self.ik_hip_placement_attr, f"{self.pv_ik_ctrl}.offsetParentMatrix")
        prim_controls.append(self.pv_ik_ctrl)

        # hip adjust controller
        hipAdjustCreator_ = curves_utils.SingleArrowFatControl()
        hipAdjustCreator_.create_curve(name=f"{self.data.comp_composed_name}_ikAdjustHip_{constants.CTRL_EXTENSION}",
                                       buffer_grp=False,
                                       color_index=self.data.primary_color,
                                       tag=self.data.comp_composed_name,

                                       )
        self.ik_adjust_hip = hipAdjustCreator_.control_name
        cmds.connectAttr(self.ik_hip_placement_attr, f"{self.ik_adjust_hip}.offsetParentMatrix")
        sec_controls.append(self.ik_adjust_hip)

        self.main_pv_attr = rig_utils.create_interpolated_pv(f"{self.hip_ik_ctrl}.worldMatrix[0]",
                                                             f"{self.pv_ik_ctrl}.offsetParentMatrix",
                                                             f"{self.foot_ik_ctrl}.worldMatrix[0]",
                                                             name="ikPv",
                                                             )

        # ankle adjust controller
        AnkleAdjustCreator_ = curves_utils.SingleArrowFatControl()
        AnkleAdjustCreator_.create_curve(name=f"{self.data.comp_composed_name}_ikAdjustAnkle_ctrl",
                                         buffer_grp=False,
                                         color_index=self.data.primary_color,
                                         tag=self.data.comp_composed_name,

                                         )
        self.ik_adjust_ankle = AnkleAdjustCreator_.control_name
        cmds.connectAttr(f"{self.foot_ik_ctrl}.worldMatrix[0]", f"{self.ik_adjust_ankle}.offsetParentMatrix")
        sec_controls.append(self.ik_adjust_ankle)

        # upper polevector
        UpperPolevecCreator_ = curves_utils.SingleArrowFatControl()
        UpperPolevecCreator_.create_curve(name=f"{self.data.comp_composed_name}_ikUpperPv_ctrl",
                                          buffer_grp=False,
                                          scale=(2, 2, 2,),
                                          color_index=self.data.secondary_color,
                                          tag=self.data.comp_composed_name,

                                          )
        self.ik_upper_pv = UpperPolevecCreator_.control_name
        cmds.connectAttr(self.ik_hip_placement_attr, f"{self.ik_upper_pv}.offsetParentMatrix")
        sec_controls.append(self.ik_upper_pv)

        # lower polevector
        LowerPolevecCreator_ = curves_utils.SingleArrowFatControl()
        LowerPolevecCreator_.create_curve(name=f"{self.data.comp_composed_name}_ikLowerPv_ctrl",
                                          buffer_grp=False,
                                          scale=(2, 2, 2,),
                                          color_index=self.data.secondary_color,
                                          tag=self.data.comp_composed_name,

                                          )
        self.ik_lower_pv = LowerPolevecCreator_.control_name
        cmds.connectAttr(self.ik_hip_placement_attr,
                         f"{self.ik_lower_pv}.offsetParentMatrix"
                         )
        sec_controls.append(self.ik_lower_pv)
        # unifies all the controls into a uppergroup that seperates fk from ik controls
        ik_primary_control_group = f"{self.data.comp_composed_name}_ikPrimary_grp"
        # bundle shit together
        node.createNode("transform",
                        n=ik_primary_control_group,
                        tag=self.data.comp_composed_name,
                        )

        cmds.parent(prim_controls, ik_primary_control_group)
        cmds.parent(ik_primary_control_group, self.data.primaries_grp_name)
        ik_secondary_control_group = f"{self.data.comp_composed_name}_ikSecondary_grp"

        # bundle shit together
        node.createNode("transform",
                        n=ik_secondary_control_group,
                        tag=self.data.comp_composed_name,
                        )

        cmds.parent(sec_controls,
                    ik_secondary_control_group
                    )
        cmds.parent(ik_secondary_control_group,
                    self.data.secondaries_grp_name
                    )
        self.ik_controls.extend((ik_primary_control_group, ik_secondary_control_group))

        self.all_controls.extend(prim_controls)

        self.all_controls.extend(sec_controls)

    def _create_tweaker_controls(self):

        sec_controls = list()
        prim_controls = list()
        sec_bend_controls = list()

        tweaker_primary_amount = len(self.data.comp_subplacement_transforms[:4])
        tweaker_secondary_amount = tweaker_primary_amount - 1
        bend_nodes_amount = 5

        # tweakers
        PrimaryTweakCreator_ = curves_utils.FatCrossControl()

        self.tweaker_primary_controls = [PrimaryTweakCreator_.create_curve(name=f"{self.data.comp_composed_name}_tweakPrimary_{amnt:03}_ctrl",
                                                                           color_index=self.data.primary_color,
                                                                           buffer_grp=False,
                                                                           tag=self.data.comp_composed_name,
                                                                           )
                                         for amnt
                                         in range(tweaker_primary_amount)
                                         ]

        sec_controls.extend(self.tweaker_primary_controls)

        # create the tweajer subcontrols
        SecondaryTweakCreator_ = curves_utils.CrossControl()
        self.tweaker_secondary_controls = [SecondaryTweakCreator_.create_curve(name=f"{self.data.comp_composed_name}_tweakSecondary_{amnt:03}_ctrl",
                                                                               color_index=self.data.primary_color,
                                                                               buffer_grp=False,
                                                                               tag=self.data.comp_composed_name,
                                                                               )
                                           for amnt
                                           in range(tweaker_secondary_amount)
                                           ]

        BenderCreator_ = curves_utils.SphereControl()
        self.bender_secondary_controls = [tuple(BenderCreator_.create_curve(name=f"{self.data.comp_composed_name}_bend_{limb_amount:03}_limb_{bend_amount:03}_ctrl",
                                                                            color_index=self.data.secondary_color,
                                                                            buffer_grp=False,
                                                                            tag=self.data.comp_composed_name,
                                                                            )
                                                for bend_amount
                                                in range(bend_nodes_amount)
                                                )

                                          for limb_amount
                                          in range(tweaker_secondary_amount)

                                          ]
        sec_controls.extend(self.tweaker_secondary_controls)
        sec_bend_controls.extend(self.bender_secondary_controls)

        # unifies all the controls into an uppergroup that seperates fk from ik controls
        tweaker_primary_control_group = f"{self.data.comp_composed_name}_tweakPrimary_grp"

        # bundle shit together
        if prim_controls:
            node.createNode("transform",
                            n=tweaker_primary_control_group,
                            tag=self.data.comp_composed_name,
                            )

            cmds.parent(prim_controls, tweaker_primary_control_group)
            cmds.parent(tweaker_primary_control_group, self.data.primaries_grp_name)

        tweaker_secondary_control_group = f"{self.data.comp_composed_name}_tweakSecondary_grp"

        # bundle shit together
        if sec_controls:
            node.createNode("transform",
                            n=tweaker_secondary_control_group,
                            tag=self.data.comp_composed_name,
                            )

            cmds.parent(sec_controls, tweaker_secondary_control_group)
            cmds.parent(tweaker_secondary_control_group, self.data.secondaries_grp_name)

        bender_secondary_control_group = f"{self.data.comp_composed_name}bendSecondary_grp"
        if sec_bend_controls:
            bend_concat = tuple(itertools.chain.from_iterable(sec_bend_controls))

            node.createNode("transform",
                            n=bender_secondary_control_group,
                            tag=self.data.comp_composed_name,
                            )

            cmds.parent(bend_concat,
                        bender_secondary_control_group
                        )

            cmds.parent(bender_secondary_control_group,
                        self.data.secondaries_grp_name
                        )

            self.all_controls.extend(list(bend_concat))

        self.all_controls.extend(prim_controls)

        self.all_controls.extend(sec_controls)

    def _create_fk_controls(self, offsets, rotonly_offsets):
        multiplies = list()
        prim_controls = list()

        FkCreator_ = curves_utils.ArrowsOnBallControl()

        for iteration_, _ in enumerate(offsets):

            ctrl_name = FkCreator_.create_curve(
                    name=f"{self.data.comp_composed_name}_fk_{iteration_:03}_ctrl",
                    color_index=self.data.primary_color,
                    buffer_grp=False,
                    scale=(3., 3., 3.),
                    tag=self.data.comp_composed_name,

            )

            prim_controls.append(ctrl_name)

        for iteration_, offset in enumerate(offsets):
            mult_mtx_name = node.createNode("math_MultiplyMatrix",
                                            n=f"{self.data.comp_composed_name}_fk_{iteration_:03}_MMX",
                                            tag=self.data.comp_composed_name,
                                            )

            cmds.connectAttr(f"{offset}", f"{mult_mtx_name}.input1", f=True)

            # we need to skip the first iteration, if we do not, we create a cycle
            if iteration_ != 0:
                cmds.connectAttr(f"{prim_controls[iteration_ - 1]}.worldMatrix",
                                 f"{mult_mtx_name}.input2",
                                 f=True
                                 )

            else:
                cmds.connectAttr(f"{self.data.input_grp_name}.op_connector",
                                 f"{mult_mtx_name}.input2",
                                 f=True
                                 )

            multiplies.append(mult_mtx_name)

        stack_ = list()
        for iteration_, (mult_mtx_name, controller, static_rot_offset) in enumerate(zip(multiplies,
                                                                                        prim_controls,
                                                                                        rotonly_offsets
                                                                                        )
                                                                                    ):

            pick_rot_only_mtx_name = node.createNode("pickMatrix",
                                                     n=f"{self.data.comp_composed_name}_dynamicRotation_{iteration_:03}_PMX",
                                                     tag=self.data.comp_composed_name,
                                                     )

            mult_rot_only_mtx_name = node.createNode("math_MultiplyMatrix",
                                                     n=f"{self.data.comp_composed_name}_staticRotation_{iteration_:03}_MMX",
                                                     tag=self.data.comp_composed_name,
                                                     )

            blend_rot_only_mtx_name = node.createNode("blendMatrix",
                                                      n=f"{self.data.comp_composed_name}_staticRotation_{iteration_:03}_BMX",
                                                      tag=self.data.comp_composed_name,
                                                      )

            cmds.setAttr(f"{pick_rot_only_mtx_name}.useRotate", False, l=True)

            cmds.connectAttr(f"{mult_mtx_name}.output",
                             f"{pick_rot_only_mtx_name}.inputMatrix",)

            cmds.connectAttr(f"{pick_rot_only_mtx_name}.outputMatrix",
                             f"{mult_rot_only_mtx_name}.input2", )

            cmds.connectAttr(static_rot_offset,
                         f"{mult_rot_only_mtx_name}.input1", )

            cmds.connectAttr(f"{mult_mtx_name}.output",
                             f"{blend_rot_only_mtx_name}.inputMatrix",)

            cmds.connectAttr(f"{mult_rot_only_mtx_name}.output",
                             f"{blend_rot_only_mtx_name}.target[0].targetMatrix",)

            cmds.connectAttr(f"{blend_rot_only_mtx_name}.outputMatrix",
                             f"{controller}.offsetParentMatrix"
                             )
            if stack_:

                rotMult = node.createNode("math_MultiplyMatrix",
                                          n=f"{self.data.comp_composed_name}_rotMult_{iteration_:03}_MMX",
                                          tag=self.data.comp_composed_name,
                                          )

                rotMultPick = node.createNode("pickMatrix",
                                              n=f"{self.data.comp_composed_name}_rotMultPick_{iteration_:03}_BMX",
                                              tag=self.data.comp_composed_name,
                                              )

                cmds.connectAttr(static_rot_offset, f"{rotMult}.input1")
                cmds.connectAttr(stack_[-1], f"{rotMult}.input2")

                cmds.connectAttr(f"{rotMult}.output", f"{rotMultPick}.inputMatrix", )

                cmds.setAttr(f"{rotMultPick}.useShear", False, l=True)
                cmds.setAttr(f"{rotMultPick}.useScale", False, l=True)
                cmds.setAttr(f"{rotMultPick}.useTranslate", False, l=True)

                cmds.connectAttr(f"{rotMultPick}.outputMatrix", f"{mult_rot_only_mtx_name}.input1", f=True)

            stack_.append(f"{blend_rot_only_mtx_name}.outputMatrix")
            self.fk_static_rotation_attrs.append(f"{blend_rot_only_mtx_name}.target[0].weight")

        # parents the prim_controls under the primaries group for now :)
        fk_primary_control_group = f"{self.data.comp_composed_name}_fkPrimary_grp"

        # unifies all the prim_controls into a upper group that seperates fk from ik prim_controls
        node.createNode("transform",
                        n=fk_primary_control_group,
                        tag=self.data.comp_composed_name,
                        )

        cmds.parent(prim_controls, fk_primary_control_group)
        cmds.parent(fk_primary_control_group, self.data.primaries_grp_name)

        # create outputs of the control system
        # not sure if the edge of this should be in here or in the create calculations
        for iteration_, ctrl_name_ in enumerate(prim_controls):
            calc_name = f"{self.data.calculation_grp_name}.ctrl_postition_{iteration_:03}"

            cmds.addAttr(self.data.calculation_grp_name,
                         ln=f"ctrl_postition_{iteration_:03}",
                         dt="matrix"
                         )

            cmds.connectAttr(f"{ctrl_name_}.worldMatrix",
                             calc_name,
                             )

            self.fk_calculation_attrs.append(f"{ctrl_name_}.worldMatrix")

        self.fk_controls.append(fk_primary_control_group)
        self.all_controls.extend(prim_controls)

    def create_calculations(self):

        # empty list for save guarding
        calc_attrs = self.fk_calculation_attrs[:]
        calc_attrs.insert(0, self.connector_attrs[0])

        self._create_fk_calculations(calc_attrs)
        self._create_ik_calculations()

        self._create_footroll_calculations()

    def _create_footroll_calculations(self):
        ankle = self.footroll_controls[-1]
        toe = self.footroll_controls[-4]

        aim_matrix = node.createNode("aimMatrix",
                                     n=f"{self.data.comp_composed_name}_pawPad_AMX",
                                     tag=self.data.comp_composed_name,
                                     )

        blend_matrix = node.createNode("blendMatrix",
                                       n=f"{self.data.comp_composed_name}_pawPad_BMX",
                                       tag=self.data.comp_composed_name,
                                       )

        aim_matrix_attrs_ = {"primaryMode":            1,
                             "primaryInputAxisX":      1,
                             "primaryInputAxisY":      0,
                             "primaryInputAxisZ":      0,
                             "primaryTargetVectorX":   0,
                             "primaryTargetVectorY":   0,
                             "primaryTargetVectorZ":   0,

                             "secondaryMode":          2,
                             "secondaryInputAxisX":    0,
                             "secondaryInputAxisY":    1,
                             "secondaryInputAxisZ":    0,
                             "secondaryTargetVectorX": 0,
                             "secondaryTargetVectorY": 1,
                             "secondaryTargetVectorZ": 0,
                             }

        rig_utils.set_from_dict(aim_matrix, aim_matrix_attrs_)

        cmds.connectAttr(f"{toe}.worldMatrix",
                         f"{aim_matrix}.primaryTargetMatrix")

        cmds.connectAttr(f"{self.ankle_chain[-2]}.worldMatrix",
                         f"{aim_matrix}.inputMatrix")

        cmds.connectAttr(f"{ankle}.worldMatrix",
                         f"{aim_matrix}.secondaryTargetMatrix")

        cmds.connectAttr(f"{ankle}.worldMatrix",
                         f"{blend_matrix}.target[0].targetMatrix",
                         )

        cmds.connectAttr(f"{aim_matrix}.outputMatrix",
                         f"{blend_matrix}.inputMatrix",
                         )
        """
        cmds.connectAttr(f"{blend_matrix}.outputMatrix",
                         f"{self.paw_control}.offsetParentMatrix",
                         )
        """

        self.multiply_matrix_by_scale(f"{blend_matrix}.outputMatrix", self.paw_control)

        cmds.orientConstraint(self.footroll_controls[-1],
                              self.ankle_chain[4],
                              maintainOffset=True,
                              )

        cmds.orientConstraint(self.footroll_controls[-2],
                              self.ankle_chain[3],
                              maintainOffset=True,
                              )

        # this creates weird stretching and might need to be fixed in the future hoeme
        cmds.pointConstraint(self.footroll_controls[-1],
                             self.ankle_chain[4],
                             maintainOffset=False,
                             )

        cmds.connectAttr(self.host_ik_fk_attr, f"{blend_matrix}.target[0].weight")
        self.paw_blend_attr = f"{blend_matrix}.target[0].targetMatrix"
        self.paw_aim_attr = f"{aim_matrix}.inputMatrix"

    @staticmethod
    def _connect_spring_blend(spring_ik_handle_, attr_, name_base, tag) -> None:
        """
        Responsible for connecting a Spring Ik Solver to its bend values.

        Args:
            spring_ik_handle_ (str):
            attr_ (str):
            name_base (str)
        """
        attr_name = "ContributingStrength"
        upper_remap_name = node.createNode("math_Remap",
                                           n=f"{name_base}_upper{attr_name}_RMP",
                                           tag=tag
                                           )

        lower_remap_name = node.createNode("math_Remap",
                                           n=f"{name_base}_lower{attr_name}_RMP",
                                           tag=tag
                                           )

        cmds.connectAttr(attr_, f"{upper_remap_name}.input", f=True)
        cmds.connectAttr(attr_, f"{lower_remap_name}.input", f=True)

        cmds.setAttr(f"{lower_remap_name}.low1", -1)
        cmds.setAttr(f"{lower_remap_name}.high1", 1)
        cmds.setAttr(f"{lower_remap_name}.low2", 1)
        cmds.setAttr(f"{lower_remap_name}.high2", 0)

        cmds.setAttr(f"{upper_remap_name}.low1", -1)
        cmds.setAttr(f"{upper_remap_name}.high1", 1)
        cmds.setAttr(f"{upper_remap_name}.low2", 0)
        cmds.setAttr(f"{upper_remap_name}.high2", 1)

        cmds.connectAttr(f"{upper_remap_name}.output",
                         f"{spring_ik_handle_}.springAngleBias[0].springAngleBias_FloatValue",
                         f=True
                         )

        cmds.connectAttr(f"{lower_remap_name}.output",
                         f"{spring_ik_handle_}.springAngleBias[1].springAngleBias_FloatValue",
                         f=True
                         )

    def _create_ik_calculations(self):

        # first LRA is part of the root node, ignore that for now
        comp_lra_transforms_ = self.data.comp_lra_transforms[1:]
        comp_lra_matrices_ = self.lra_mmatrices[1:]

        type = "forward"
        forward_chain = self._create_ik_joint_hierarchy(comp_lra_transforms_,
                                                        comp_lra_matrices_,
                                                        type,
                                                        connect_to_scale=True,
                                                        )

        cmds.parent(forward_chain[0], self.data.calculation_grp_name)

        type = "backward"
        backward_chain = self._create_ik_joint_hierarchy(comp_lra_transforms_,
                                                         comp_lra_matrices_,
                                                         type,
                                                         connect_to_scale=True,
                                                         )

        cmds.parent(backward_chain[0], self.data.calculation_grp_name)

        type = "spring"
        spring_chain = self._create_ik_joint_hierarchy(comp_lra_transforms_,
                                                       comp_lra_matrices_,
                                                       type,
                                                       connect_to_scale=True,
                                                       )

        cmds.parent(spring_chain[0], self.data.calculation_grp_name)

        type = "hip"
        hip_chain = self._create_ik_joint_hierarchy(comp_lra_transforms_,
                                                    comp_lra_matrices_,
                                                    type,
                                                    )

        cmds.parent(hip_chain[0], self.data.calculation_grp_name)

        type = "ankle"
        self.ankle_chain = self._create_ik_joint_hierarchy(comp_lra_transforms_,
                                                           comp_lra_matrices_,
                                                           type,
                                                           connect_to_scale=True,
                                                           )

        cmds.parent(self.ankle_chain[0], self.data.calculation_grp_name)

        ik_chains_grp = f"{self.data.comp_composed_name}_ikChains_grp"

        node.createNode("transform",
                        n=ik_chains_grp,
                        tag=self.data.comp_composed_name,
                        )

        chains_gathered_ = (forward_chain[0],
                            backward_chain[0],
                            spring_chain[0],
                            hip_chain[0],
                            self.ankle_chain[0],
                            )

        cmds.parent(chains_gathered_,
                    ik_chains_grp
                    )

        [cmds.setAttr(f"{chain_start__}.visibility",
                      False,
                      )

         for chain_start__
         in chains_gathered_
         ]

        cmds.parent(ik_chains_grp, self.data.calculation_grp_name)

        lower_direction_mult, upper_direction_mult = self.get_upper_and_lower_direction_multiplier(spring_chain)

        # since we froze the transformations on the joint chaines
        # we need to reset the jointOrient to have zero rotations
        to_zero_out = (backward_chain[1], forward_chain[2])
        for bend_joint in to_zero_out:
            for axis_ in "XYZ":
                cmds.setAttr(f"{bend_joint}.jointOrient{axis_}", 0)


        forward_handle_, forward_eff_ = create_ik_solver(start_node=forward_chain[0],
                                                         end_node=forward_chain[3],
                                                         solver="ikRPsolver",
                                                         new_name=self.data.comp_composed_name,
                                                         new_subname="forward",
                                                         )

        backward_handle_, backward_eff_ = create_ik_solver(start_node=backward_chain[0],
                                                           end_node=backward_chain[3],
                                                           solver="ik2Bsolver",
                                                           new_name=self.data.comp_composed_name,
                                                           new_subname="backward"
                                                           )

        spring_handle_, spring_eff_ = create_ik_solver(start_node=spring_chain[0],
                                                       end_node=spring_chain[3],
                                                       solver="ikSpringSolver",
                                                       new_name=self.data.comp_composed_name,
                                                       new_subname="spring"
                                                       )

        ankle_handle_, ankle_eff_ = create_ik_solver(start_node=self.ankle_chain[0],
                                                     end_node=self.ankle_chain[2],
                                                     solver="ik2Bsolver",
                                                     new_name=self.data.comp_composed_name,
                                                     new_subname="ankleAdjust"
                                                     )
        for axis_ in "XYZ":
            cmds.setAttr(f"{forward_chain[2]}.jointType{axis_}", False, l=True)
            cmds.setAttr(f"{forward_chain[2]}.rotate{axis_}", False, l=True)

        cmds.setAttr(f"{backward_handle_}.twist", 180, l=True)

        translation_from_ik_hip = node.createNode("math_TranslationFromMatrix",
                                                  n=f"{self.data.comp_composed_name}_ikHip_TFM",
                                                  tag=self.data.comp_composed_name,
                                                  )

        translation_from_ik_pole = node.createNode("math_TranslationFromMatrix",
                                                   n=f"{self.data.comp_composed_name}_ikPole_TFM",
                                                   tag=self.data.comp_composed_name,
                                                   )

        translation_from_ik_foot = node.createNode("math_TranslationFromMatrix",
                                                   n=f"{self.data.comp_composed_name}_ikFoot_TFM",
                                                   tag=self.data.comp_composed_name,
                                                   )

        cmds.connectAttr(f"{self.hip_ik_ctrl}.worldMatrix[0]",
                         f"{translation_from_ik_hip}.input",
                         f=True,
                         )

        cmds.connectAttr(f"{self.pv_ik_ctrl}.worldMatrix[0]",
                         f"{translation_from_ik_pole}.input",
                         f=True,
                         )

        cmds.connectAttr(f"{self.footroll_controls[-1]}.worldMatrix[0]",
                         f"{translation_from_ik_foot}.input",
                         f=True,
                         )

        hip_adjustment = node.createNode("aimMatrix",
                                         n=f"{self.data.comp_composed_name}_hipAdjustment_AMX",
                                         tag=self.data.comp_composed_name,
                                         )

        aim_settings = {"primaryMode": 1,
                        "primaryInputAxisX": 1,
                        "primaryInputAxisY": 0,
                        "primaryInputAxisZ": 0,

                        "secondaryMode": 1,
                        "secondaryInputAxisX": 0,
                        "secondaryInputAxisY": 0,
                        "secondaryInputAxisZ": 1,
                        }

        rig_utils.set_from_dict(hip_adjustment,
                                aim_settings,
                                )

        adjustment_lock = node.createNode("blendMatrix",
                                          n=f"{self.data.comp_composed_name}_adjustmentLock_BMX",
                                          tag=self.data.comp_composed_name,
                                          )

        static_position = node.createNode("math_MultiplyMatrix",
                                          n=f"{self.data.comp_composed_name}_staticLock_MMX",
                                          tag=self.data.comp_composed_name,
                                          )

        second_joint_transform, upper_aim_chooser_input = rig_utils.space_blender(
                space_attributes=((f"{spring_chain[1]}.worldMatrix[0]", ((-1, 1, ),
                                                                         (1, 1, ))
                                   ),
                                  (f"{forward_chain[1]}.worldMatrix[0]", ((-1, 0, ),
                                                                          (1, 0, ))
                                   ),
                                  (f"{backward_chain[1]}.worldMatrix[0]", ((0, 1, ),
                                                                           (0, 1, ))
                                   ),
                                  ),
                name=self.data.comp_composed_name,
                subname="secondJointTrs"
        )
        third_joint_transform, third_joint_chooser_input = rig_utils.space_blender(
                space_attributes=((f"{spring_chain[2]}.worldMatrix[0]", ((-1, 1, ),
                                                                         (1, 1, ))
                                   ),
                                  (f"{forward_chain[2]}.worldMatrix[0]", ((-1, 0, ),
                                                                          (1, 0, ))
                                   ),
                                  (f"{backward_chain[2]}.worldMatrix[0]", ((0, 1, ),
                                                                           (0, 1, ))
                                   ),
                                  ),
                name=self.data.comp_composed_name,
                subname="thirdJointTrs"
        )
        fourth_joint_transform, fourth_joint_chooser_input = rig_utils.space_blender(
                space_attributes=((f"{spring_chain[3]}.worldMatrix[0]", ((-1, 1, ),
                                                                         (1, 1, ))
                                   ),
                                  (f"{forward_chain[3]}.worldMatrix[0]", ((-1, 0, ),
                                                                          (1, 0, ))
                                   ),
                                  (f"{backward_chain[3]}.worldMatrix[0]", ((0, 1, ),
                                                                           (0, 1, ))
                                   ),
                                  ),
                name=self.data.comp_composed_name,
                subname="fourthJointTrs"
        )

        pv_offset = node.createNode("math_MultiplyMatrix",
                                    n=f"{self.data.comp_composed_name}_pvOffset_MMX",
                                    tag=self.data.comp_composed_name,
                                    )

        cmds.setAttr(f"{pv_offset}.input1",
                     *(1, 0, 0, 0,
                       0, 1, 0, 0,
                       0, 0, 1, 0,
                       0, 100, 200, 1,
                       ),
                     type="matrix",
                     l=True)

        cmds.connectAttr(f"{self.pv_ik_ctrl}.worldMatrix[0]",
                         f"{pv_offset}.input2",
                         f=True,
                         )

        cmds.connectAttr(f"{self.hip_ik_ctrl}.worldMatrix[0]",
                         f"{hip_adjustment}.inputMatrix",
                         f=True,
                         )

        cmds.connectAttr(f"{pv_offset}.output",
                         f"{hip_adjustment}.secondaryTargetMatrix",
                         f=True,
                         )

        cmds.connectAttr(f"{second_joint_transform}.outputMatrix",
                         f"{hip_adjustment}.primaryTargetMatrix",
                         f=True,
                         )
        cmds.connectAttr(f"{hip_adjustment}.outputMatrix",
                         f"{adjustment_lock}.inputMatrix",
                         f=True,
                         )

        cmds.connectAttr(f"{static_position}.output",
                         f"{adjustment_lock}.target[0].targetMatrix",
                         f=True,
                         )

        cmds.connectAttr(f"{self.hip_ik_ctrl}.worldMatrix[0]",
                         f"{static_position}.input2",
                         f=True,
                         )

        parent_offset_matrix = matrix_maths.mmatrix_to_tuple(
                matrix_maths.tuple_to_mmatrix(self.data.comp_lra_transforms[1]) * matrix_maths.invert_matrix(
                        matrix_maths.tuple_to_mmatrix(self.data.comp_subplacement_transforms[0])))

        cmds.setAttr(f"{static_position}.input1",
                     *parent_offset_matrix,
                     type="matrix",
                     )

        cmds.connectAttr(f"{adjustment_lock}.outputMatrix",
                         f"{self.ik_adjust_hip}.offsetParentMatrix",
                         f=True,
                         )

        potential_inversion = node.createNode("math_MultiplyMatrix",
                                              n=f"{self.data.comp_composed_name}_mirroredJointAdjust_MMX",
                                              tag=self.data.comp_composed_name
                                              )

        z_axis = matrix_maths.get_axis_alignment(self.data.comp_root_name,
                                                 axis=self.data.build_axis,
                                                 direction_only=True,
                                                 )

        potential_inversion_settings = {"input1": (1, 0, 0, 0,
                                                   0, 1, 0, 0,
                                                   0, 0, z_axis, 0,
                                                   0, 0, 0, 1,
                                                   ),
                                        }

        rig_utils.set_from_dict(potential_inversion,
                                potential_inversion_settings,
                                )

        aim_settings_ = {"primaryMode": 1,
                         "primaryInputAxisX": 0,
                         "primaryInputAxisY": -1,
                         "primaryInputAxisZ": 0,

                         "secondaryMode": 1,
                         "secondaryInputAxisX": 1,
                         "secondaryInputAxisY": 0,
                         "secondaryInputAxisZ": 0,
                         }

        upvec_settings_ = {"input1": (1, 0, 0, 0,
                                      0, 1, 0, 0,
                                      0, 0, 1, 0,
                                      0, -10, 0, 1,
                                      ),
                           }

        distance = 45

        positional_base_settings_ = {"input1": [1, 0, 0, 0,
                                                0, 1, 0, 0,
                                                0, 0, 1, 0,
                                                0, 0, distance, 1,
                                                ],
                                     }

        positional_base_settings_["input1"][14] = lower_direction_mult * distance

        # setting of the secondary aim settings :)
        secondary_aim_setup = dict()

        secondary_aim_setup["aim_settings"] = {"primaryMode": 1,
                                               "primaryInputAxisX": 0,
                                               "primaryInputAxisY": -1,
                                               "primaryInputAxisZ": 0,

                                               "secondaryMode": 1,
                                               "secondaryInputAxisX": 0,
                                               "secondaryInputAxisY": 0,
                                               "secondaryInputAxisZ": -1,
                                               }

        secondary_aim_setup["secondary_aim"] = f"{self.pv_ik_ctrl}.worldMatrix"

        secondary_aim_setup["space_01"] = self.lower_secondary_pv_space_switch_attr
        secondary_aim_setup["space_02"] = self.lower_secondary_pv_space_switch_attr

        rig_utils.create_interpolated_pv(start=f"{self.ik_adjust_hip}.worldMatrix[0]",
                                         mid=f"{self.ik_lower_pv}.offsetParentMatrix",
                                         end=f"{third_joint_transform}.outputMatrix",

                                         name=f"{self.data.comp_composed_name}_ikLowerPv",
                                         aim_settings=aim_settings_,
                                         upvec_matrix_settings=upvec_settings_,
                                         positional_matrix_settings=positional_base_settings_,
                                         secondary_aim_setup=secondary_aim_setup,
                                         )

        positional_base_settings_["input1"][14] = upper_direction_mult * distance

        secondary_aim_setup["space_01"] = self.upper_secondary_pv_space_switch_attr
        secondary_aim_setup["space_02"] = self.upper_secondary_pv_space_switch_attr

        aim_settings_["secondaryInputAxisX"] = 0
        aim_settings_["secondaryInputAxisZ"] = 1

        rig_utils.create_interpolated_pv(start=f"{second_joint_transform}.outputMatrix",
                                         mid=f"{self.ik_upper_pv}.offsetParentMatrix",
                                         end=f"{fourth_joint_transform}.outputMatrix",

                                         name=f"{self.data.comp_composed_name}_ikUpperPv",
                                         aim_settings=aim_settings_,
                                         upvec_matrix_settings=upvec_settings_,
                                         positional_matrix_settings=positional_base_settings_,
                                         secondary_aim_setup=secondary_aim_setup
                                         )

        # fourth_joint_transform
        rig_utils.reset_joint(pmc.PyNode(hip_chain[0]))

        cmds.connectAttr(f"{self.ik_adjust_hip}.worldMatrix[0]",
                         f"{potential_inversion}.input2",
                         f=True,
                         )

        cmds.connectAttr(f"{potential_inversion}.output",
                         f"{hip_chain[0]}.offsetParentMatrix",
                         )

        hip_handle_, hip_eff_ = create_ik_solver(start_node=hip_chain[1],
                                                 end_node=hip_chain[3],
                                                 solver="ik2Bsolver",
                                                 new_name=self.data.comp_composed_name,
                                                 new_subname="hipAdjust",
                                                 )

        to_connect_ = {translation_from_ik_foot: (forward_handle_,
                                                  backward_handle_,
                                                  spring_handle_,
                                                  hip_handle_,
                                                  ),

                       translation_from_ik_hip:  (forward_chain[0],
                                                  backward_chain[0],
                                                  spring_chain[0],
                                                  self.ankle_chain[0],
                                                  ),
                       }

        for translation_, handles_ in to_connect_.items():
            for handle_ in handles_:
                for axis_ in "XYZ":
                    cmds.connectAttr(f"{translation_}.output{axis_}",
                                     f"{handle_}.translate{axis_}",
                                     f=True,
                                     )

        twist = 0 if upper_direction_mult > 0 else 180

        cmds.setAttr(f"{spring_handle_}.twist", twist, l=True)

        handles_ = (forward_handle_,
                    backward_handle_,
                    spring_handle_,
                    )

        for handle_ in handles_:
            cmds.poleVectorConstraint(self.pv_ik_ctrl,
                                      handle_,
                                      )

        cmds.poleVectorConstraint(self.ik_upper_pv,
                                  hip_handle_,
                                  )

        cmds.poleVectorConstraint(self.ik_lower_pv,
                                  ankle_handle_,
                                  )

        ik_handles_grp_name = f"{self.data.comp_composed_name}_ikHandles_{constants.GRP_EXTENSION}"

        node.createNode("transform",
                        n=ik_handles_grp_name,
                        tag=self.data.comp_composed_name,
                        )

        handles_gathered__ = (forward_handle_,
                              backward_handle_,
                              spring_handle_,
                              hip_handle_,
                              ankle_handle_,
                              )

        cmds.parent(handles_gathered__,
                    ik_handles_grp_name,
                    )

        cmds.parent(ik_handles_grp_name,
                    self.data.calculation_grp_name,
                    )

        [cmds.setAttr(f"{handles_start__}.visibility",
                      False,
                      )
         for handles_start__
         in handles_gathered__
         ]

        ankle_aimer = node.createNode("aimMatrix",
                                      n=f"{self.data.comp_composed_name}_ikInverseAnkle_AMX",
                                      tag=self.data.comp_composed_name,
                                      )

        aim_settings = {"primaryMode": 1,
                        "primaryInputAxisX": -1,
                        "primaryInputAxisY": 0,
                        "primaryInputAxisZ": 0,

                        "secondaryMode": 1,
                        "secondaryInputAxisX": 0,
                        "secondaryInputAxisY": 0,
                        "secondaryInputAxisZ": 1,
                        }

        aim_settings["secondaryInputAxisZ"] *= z_axis
        rig_utils.set_from_dict(ankle_aimer,
                                aim_settings,
                                )

        cmds.connectAttr(f"{fourth_joint_transform}.outputMatrix",
                         f"{ankle_aimer}.inputMatrix",
                         f=True,
                         )

        cmds.connectAttr(f"{hip_chain[2]}.worldMatrix[0]",
                         f"{ankle_aimer}.primaryTargetMatrix",
                         f=True,
                         )

        cmds.connectAttr(f"{pv_offset}.output",
                         f"{ankle_aimer}.secondaryTargetMatrix",
                         f=True,
                         )

        static_ankle_lock = node.createNode("blendMatrix",
                                            n=f"{self.data.comp_composed_name}_ikInverseAnkleLock_BMX",
                                            tag=self.data.comp_composed_name,
                                            )

        cmds.connectAttr(f"{ankle_aimer}.outputMatrix",
                         f"{static_ankle_lock}.inputMatrix",
                         f=True,
                         )

        aiming_with_offset_aim = node.createNode("aimMatrix",
                                                 n=f"{self.data.comp_composed_name}_ikInverseAnkleLockToHip_AMX",
                                                 tag=self.data.comp_composed_name,
                                                 )
        aiming_with_offset_aim_settings = {
            "primaryMode": 1,
            "primaryInputAxisX": -1,
            "primaryInputAxisY": 0,
            "primaryInputAxisZ": 0,
            "primaryTargetVectorX": -1,
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
        aiming_with_offset_aim_settings["secondaryInputAxisZ"] *= z_axis
        rig_utils.set_from_dict(aiming_with_offset_aim, aiming_with_offset_aim_settings)

        aiming_with_offset_blend = node.createNode("blendMatrix",
                                                   n=f"{self.data.comp_composed_name}_ikInverseAnkleLockToHip_BMX",
                                                   tag=self.data.comp_composed_name,
                                                   )

        cmds.connectAttr(f"{ankle_aimer}.outputMatrix",
                         f"{aiming_with_offset_blend}.inputMatrix",
                         f=True,
                         )

        cmds.connectAttr(f"{fourth_joint_transform}.outputMatrix",
                         f"{aiming_with_offset_aim}.inputMatrix",
                         f=True,
                         )

        cmds.connectAttr(f"{self.hip_ik_ctrl}.worldMatrix[0]",
                         f"{aiming_with_offset_aim}.primaryTargetMatrix",
                         f=True,
                         )

        cmds.connectAttr(f"{aiming_with_offset_aim}.outputMatrix",
                         f"{aiming_with_offset_blend}.target[0].targetMatrix",
                         f=True,
                         )

        # create the follow for the foot control
        foot_world_mtx = matrix_maths.get_world_matrix(self.foot_ik_ctrl)
        foot_world_inverse_mtx = matrix_maths.invert_matrix(foot_world_mtx)

        ik_adjust_mtx = matrix_maths.tuple_to_mmatrix(cmds.getAttr(f"{aiming_with_offset_blend}.outputMatrix",
                                                                   )
                                                      )

        offset_mtx = matrix_maths.multiply_matrices(ik_adjust_mtx,
                                                    foot_world_inverse_mtx,
                                                    )

        offset_tple = matrix_maths.mmatrix_to_tuple(offset_mtx)

        follow_foot_mmx_name = node.createNode("math_MultiplyMatrix",
                                               n=f"{self.data.comp_composed_name}_followFoot_MMX",
                                               tag=self.data.comp_composed_name,
                                               )

        ik_footroll_mtx = matrix_maths.get_world_matrix(self.footroll_controls[-1],
                                                        )

        footroll_world_inverse_mtx = matrix_maths.invert_matrix(ik_footroll_mtx)

        ik_footroll_offset_mtx = matrix_maths.multiply_matrices(foot_world_mtx,
                                                                footroll_world_inverse_mtx,
                                                                )

        ik_footroll_offset_tple = matrix_maths.mmatrix_to_tuple(ik_footroll_offset_mtx)

        ik_footroll_follow_foot_mmx_name = node.createNode("math_MultiplyMatrix",
                                                           n=f"{self.data.comp_composed_name}_followFootroll_MMX",
                                                           tag=self.data.comp_composed_name,
                                                           )

        cmds.connectAttr(f"{self.footroll_controls[-1]}.worldMatrix",
                         f"{ik_footroll_follow_foot_mmx_name}.input2",
                         )

        cmds.setAttr(f"{ik_footroll_follow_foot_mmx_name}.input1",
                     ik_footroll_offset_tple,
                     type="matrix",
                     l=True,
                     )

        follow_foot_bmx_name = node.createNode("blendMatrix",
                                               n=f"{self.data.comp_composed_name}_followFoot_BMX",
                                               tag=self.data.comp_composed_name,
                                               )

        follow_bmx_settings = {"target[0].useTranslate": True,
                               "target[0].useScale": False,
                               "target[0].useShear": True,
                               "target[0].useRotate": True,
                               }

        rig_utils.set_from_dict(follow_foot_bmx_name,
                                follow_bmx_settings,
                                )

        cmds.connectAttr(f"{ik_footroll_follow_foot_mmx_name}.output",
                         f"{follow_foot_mmx_name}.input2",
                         )

        cmds.setAttr(f"{follow_foot_mmx_name}.input1",
                     offset_tple,
                     type="matrix",
                     l=True,
                     )

        cmds.connectAttr(f"{follow_foot_mmx_name}.output",
                         f"{follow_foot_bmx_name}.target[0].targetMatrix",
                         )

        cmds.connectAttr(f"{aiming_with_offset_blend}.outputMatrix",
                         f"{follow_foot_bmx_name}.inputMatrix",
                         )

        # add to this
        cmds.connectAttr(f"{follow_foot_bmx_name}.outputMatrix",
                         f"{self.ik_adjust_ankle}.offsetParentMatrix",
                         f=True,
                         )

        # here needs massaging
        ankle_restlength = node.createNode("math_MultiplyByInt",
                                           n=f"{self.data.comp_composed_name}_ikInverseAnkleInverseRestLength_MLT",
                                           tag=self.data.comp_composed_name,
                                           )

        ankle_globalscale = node.createNode("math_Multiply",
                                            n=f"{self.data.comp_composed_name}_ikInverseAnkleGlobalScale_MLT",
                                            tag=self.data.comp_composed_name,
                                            )

        ankle_to_mtx = node.createNode("math_MatrixFromTRS",
                                       n=f"{self.data.comp_composed_name}_ikInverseAnkleRestLengthToMtx_TMX",
                                       tag=self.data.comp_composed_name,
                                       )

        ankle_offset = node.createNode("math_MultiplyMatrix",
                                       n=f"{self.data.comp_composed_name}_ikInverseAnkle_MMX",
                                       tag=self.data.comp_composed_name,
                                       )

        cmds.connectAttr(f"{self.segment_length_attrs[2]}",
                         f"{ankle_restlength}.input1",
                         f=True,
                         )

        cmds.setAttr(f"{ankle_restlength}.input2", -1)

        cmds.connectAttr(f"{self.global_scale_connection_attr}",
                         f"{ankle_globalscale}.input2",
                         f=True,
                         )

        cmds.connectAttr(f"{ankle_restlength}.output",
                         f"{ankle_globalscale}.input1",
                         f=True,
                         )

        cmds.connectAttr(f"{ankle_globalscale}.output",
                         f"{ankle_to_mtx}.translationX",
                         f=True,
                         )

        cmds.connectAttr(f"{ankle_to_mtx}.output",
                         f"{ankle_offset}.input1",
                         f=True,
                         )

        cmds.connectAttr(f"{self.ik_adjust_ankle}.worldMatrix[0]",
                         f"{ankle_offset}.input2",
                         f=True,
                         )

        extract_hipInverse = node.createNode("math_TranslationFromMatrix",
                                             n=f"{self.data.comp_composed_name}_ikInverseAnkle_TFM",
                                             tag=self.data.comp_composed_name,
                                             )

        cmds.connectAttr(f"{ankle_offset}.output",
                         f"{extract_hipInverse}.input",
                         )

        for axis_ in "XYZ":
            cmds.connectAttr(f"{extract_hipInverse}.output{axis_}",
                             f"{ankle_handle_}.translate{axis_}",
                             )

        extract_hipInverse_rot = node.createNode("transform",
                                                 n=f"{self.data.comp_composed_name}_ikInverseAnkleRotExtract_POS",
                                                 tag=self.data.comp_composed_name,
                                                 )

        cmds.connectAttr(f"{ankle_offset}.output",
                         f"{extract_hipInverse_rot}.offsetParentMatrix",
                         )

        cmds.orientConstraint(extract_hipInverse_rot,
                              self.ankle_chain[2],
                              )

        cmds.parent(extract_hipInverse_rot,
                    self.data.calculation_grp_name,
                    )

        choice_nodes = (upper_aim_chooser_input,
                        fourth_joint_chooser_input,
                        third_joint_chooser_input,
                        )

        for choice_node in choice_nodes:
            cmds.connectAttr(self.host_blend_attr,
                             f"{choice_node}.inFloat",
                             f=True,
                             )

        cmds.connectAttr(self.host_lock_hip_attr,
                         f"{adjustment_lock}.target[0].weight",
                         f=True,
                         )

        cmds.connectAttr(self.host_lock_ankle_attr,
                         f"{aiming_with_offset_blend}.target[0].weight",
                         f=True,
                         )

        cmds.connectAttr(self.host_foot_follow_attr,
                         f"{follow_foot_bmx_name}.target[0].weight",
                         f=True,
                         )

        self._connect_spring_blend(spring_handle_,
                                   self.host_legbend_attr,
                                   self.data.comp_composed_name,
                                   self.data.comp_composed_name,
                                   )

        self.ik_output_attrs = tuple(f"{calc_output_joint}.worldMatrix[0]" for calc_output_joint in self.ankle_chain)

    def get_upper_and_lower_direction_multiplier(self, spring_chain):

        mtx_0_vec = matrix_maths.get_position_from_matrix(matrix_maths.get_world_matrix(f"{spring_chain[0]}")
                                                          )
        mtx_1_vec = matrix_maths.get_position_from_matrix(matrix_maths.get_world_matrix(f"{spring_chain[1]}")
                                                          )
        mtx_2_vec = matrix_maths.get_position_from_matrix(matrix_maths.get_world_matrix(f"{spring_chain[2]}")
                                                          )
        mtx_3_vec = matrix_maths.get_position_from_matrix(matrix_maths.get_world_matrix(f"{spring_chain[3]}")
                                                          )

        build_axis = om2.MVector(0, 0, 1)

        # calculate directions
        upper_direction_mult = matrix_maths.axis_alignment(build_axis, mtx_0_vec, mtx_1_vec, mtx_2_vec)
        lower_direction_mult = matrix_maths.axis_alignment(build_axis, mtx_1_vec, mtx_2_vec, mtx_3_vec)
        return lower_direction_mult, upper_direction_mult

    @staticmethod
    def _convert_lra_mtxtuples_to_mmatrices(data_transform_tpls: tuple) -> tuple:
        """
        Turns an iterable of tuples back to a tuple of OpenMaya.MMatrices.

        Args:
            data_transform_tpls (tuple): A tuple of tuples of length 16 each which represents a 4x4 matrix.

        Returns:
            Tuple: The converted mmatrices.

        """

        return tuple(matrix_maths.tuple_to_mmatrix(transform)
                     for transform
                     in data_transform_tpls
                     )


    def _create_ik_joint_hierarchy(self,
                                   comp_lra_transforms_: tuple,
                                   mmatrices: tuple,
                                   ik_type_subname: str,
                                   connect_to_scale: bool = False,
                                   ) -> list:

        name_root_ = f"{self.data.comp_composed_name}_{ik_type_subname}"

        # create the joint nodes single
        joint_names = [node.createNode("joint",
                                       n=f"{name_root_}_{iteration_:03}_{constants.JNT_EXTENSION}",
                                       tag=self.data.comp_composed_name,
                                       )
                       for iteration_ in range(len(mmatrices))
                       ]

        # create parenting information
        for_parenting = list(reversed(joint_names))

        # place the joints based on their MMatrix
        [cmds.xform(joint_name,
                    matrix=mmatrix,
                    worldSpace=True,
                    )
         for joint_name, mmatrix
         in zip(joint_names,
                comp_lra_transforms_
                )
         ]

        # freeze the transforms of the joints
        [cmds.makeIdentity(joint_name,
                           apply=True,
                           )
         for joint_name
         in joint_names
         ]

        # parent the joints to chain
        [cmds.parent(for_parenting[joint],
                     for_parenting[joint + 1]
                     ) for joint in range(len(mmatrices) - 1)
        ]

        # check if it should connect to the scale
        if not connect_to_scale:
            return joint_names

        for iteration_, (jnt_, segment_length_attr_) in enumerate(zip(joint_names[1:5],
                                                                      self.segment_length_attrs[:4]
                                                                      ),
                                                                  1):

            mult_name = node.createNode("math_Multiply",
                                        n=f"{name_root_}_globalScale_{iteration_:03}_MLT",
                                        tag=self.data.comp_composed_name,
                                        )

            distance_name = node.createNode("math_DistanceTransforms",
                                            n=f"{name_root_}_ikDistance_{iteration_:03}_DFM",
                                            tag=self.data.comp_composed_name,
                                            )

            multfactor_name = node.createNode("math_Multiply",
                                              n=f"{name_root_}_ikDistance_{iteration_:03}_MLT",
                                              tag=self.data.comp_composed_name,
                                              )

            divfactor_name = node.createNode("math_Divide",
                                             n=f"{name_root_}_ikDistance_{iteration_:03}_DIV",
                                             tag=self.data.comp_composed_name,
                                             )

            selector_name = node.createNode("math_Select",
                                            n=f"{name_root_}_ikDistance_{iteration_:03}_SEL",
                                            tag=self.data.comp_composed_name,
                                            )

            comperator_name = node.createNode("math_Compare",
                                              n=f"{name_root_}_ikDistance_{iteration_:03}_CPR",
                                              tag=self.data.comp_composed_name,
                                              )

            global_compensator_name = node.createNode("math_Multiply",
                                                      n=f"{name_root_}_globalLength_{iteration_:03}_MLT",
                                                      tag=self.data.comp_composed_name,
                                                      )

            lerper_name = node.createNode("math_Lerp",
                                          n=f"{name_root_}_stretchBlend_{iteration_:03}_LRP",
                                          tag=self.data.comp_composed_name,
                                          )

            cmds.setAttr(f"{comperator_name}.operation",
                         2,
                         l=True,
                         )

            cmds.connectAttr(f"{self.total_length_attr}",
                             f"{global_compensator_name}.input1",
                             )

            cmds.connectAttr(f"{self.global_scale_connection_attr}",
                             f"{global_compensator_name}.input2",
                             )

            cmds.connectAttr(f"{global_compensator_name}.output",
                             f"{comperator_name}.input1",
                             )

            cmds.connectAttr(f"{distance_name}.output",
                             f"{comperator_name}.input2",
                             )

            cmds.connectAttr(f"{comperator_name}.output",
                             f"{selector_name}.condition",
                             )

            cmds.connectAttr(f"{self.total_length_attr}",
                             f"{divfactor_name}.input2",
                             )

            cmds.connectAttr(self.segment_length_attrs[iteration_-1],
                             f"{divfactor_name}.input1",
                             )

            cmds.connectAttr(f"{self.hip_ik_ctrl}.worldMatrix[0]",
                             f"{distance_name}.input1",
                             )

            cmds.connectAttr(f"{self.footroll_controls[-1]}.worldMatrix[0]",
                             f"{distance_name}.input2",
                             )

            cmds.connectAttr(f"{distance_name}.output",
                             f"{multfactor_name}.input1",
                             )

            cmds.connectAttr(f"{divfactor_name}.output",
                             f"{multfactor_name}.input2",
                             )

            cmds.connectAttr(f"{multfactor_name}.output",
                             f"{selector_name}.input1",
                             )

            cmds.connectAttr(f"{segment_length_attr_}",
                             f"{mult_name}.input1",
                             )

            cmds.connectAttr(f"{self.global_scale_connection_attr}",
                             f"{mult_name}.input2",
                             )

            cmds.connectAttr(f"{mult_name}.output",
                             f"{selector_name}.input2",
                             )

            cmds.connectAttr(f"{selector_name}.output",
                             f"{lerper_name}.input2",
                             )

            cmds.connectAttr(f"{mult_name}.output",
                             f"{lerper_name}.input1",
                             )

            cmds.connectAttr(self.host_stretch_attr,
                             f"{lerper_name}.alpha",
                             )

            cmds.connectAttr(f"{lerper_name}.output",
                             f"{jnt_}.tx",
                             )

        return joint_names

    def _create_fk_calculations(self, calc_attrs) -> None:

        attr_lengths = len(calc_attrs)
        attr_names_ = list()
        weight_names_ = list()

        for idx_ in range(attr_lengths):

            # flips the aim of the last in chain
            flip = 1 if idx_ < attr_lengths - 1 else -1

            aim_matrix_ = node.createNode("aimMatrix",
                                          n=f"{self.data.comp_composed_name}_fkAiming_{idx_:03}_AMX",
                                          tag=self.data.comp_composed_name,
                                          )

            mul_matrix_ = node.createNode("math_MultiplyMatrix",
                                          n=f"{self.data.comp_composed_name}_fkAiming_{idx_:03}_MMX",
                                          tag=self.data.comp_composed_name,
                                          )

            bld_matrix_ = node.createNode("blendMatrix",
                                          n=f"{self.data.comp_composed_name}_fkAiming_{idx_:03}_BMX",
                                          tag=self.data.comp_composed_name,
                                          )

            cmds.setAttr(f"{mul_matrix_}.input1",
                         *(1, 0, 0, 0,
                           0, 1, 0, 0,
                           0, 0, 1, 0,
                           0, 10, 0, 1,
                           ),
                         type="matrix"
                         )

            cmds.setAttr(f"{aim_matrix_}.primaryInputAxisX",
                         flip,
                         l=True,
                         )

            cmds.connectAttr(calc_attrs[idx_],
                             f"{mul_matrix_}.input2",
                             )

            cmds.connectAttr(f"{mul_matrix_}.output",
                             f"{aim_matrix_}.secondaryTargetMatrix",
                             )

            cmds.setAttr(f"{aim_matrix_}.secondaryMode",
                         1,
                         l=True,
                         )

            cmds.connectAttr(f"{calc_attrs[idx_ + flip]}",
                             f"{aim_matrix_}.primaryTargetMatrix",
                             )
            cmds.connectAttr(f"{calc_attrs[idx_]}",
                             f"{aim_matrix_}.inputMatrix",
                             )

            cmds.connectAttr(f"{calc_attrs[idx_]}",
                             f"{bld_matrix_}.inputMatrix",
                             )

            cmds.connectAttr(f"{aim_matrix_}.outputMatrix",
                             f"{bld_matrix_}.target[0].targetMatrix",
                             )

            attr_names_.append(f"{bld_matrix_}.outputMatrix")
            weight_names_.append(f"{bld_matrix_}.target[0].weight")

        self.fk_output_attrs = tuple(attr_names_)
        self.fk_follow_attrs = tuple(weight_names_)

    def create_outputs(self):
        """

        Returns:

        """

        self.deformers = list()

        self._create_chain_blends()
        self._create_tweaker_calculations()
        self._create_bend()

        tweaker_controls = self.tweaker_primary_controls

        bender_controls = tuple(itertools.chain.from_iterable(self.bender_secondary_controls,
                                                              ))

        output_controls = itertools.chain.from_iterable([tweaker_controls, bender_controls]
                                                        )

        for host_attr_, weight_attr_ in zip(self.host_fk_follow_attrs, self.fk_static_rotation_attrs):
            cmds.connectAttr(host_attr_, weight_attr_)

        for output_ in output_controls:
            output_replaced_ctrl_str = output_.replace(constants.CTRL_EXTENSION,
                                                       constants.JNT_EXTENSION,
                                                       )

            output_replaced_comp_composed = output_replaced_ctrl_str.replace(self.data.comp_composed_name,
                                                                             self.data.comp_composed_joint_name,
                                                                             )

            output_replaced_comp_composed = output_replaced_comp_composed.replace("tweakPrimary",
                                                                                  "hinge",
                                                                                  )

            jnt_name = node.createNode("joint",
                                       n=output_replaced_comp_composed,
                                       tag=self.data.comp_composed_name,
                                       )

            cmds.connectAttr(f"{output_}.worldMatrix[0]", f"{jnt_name}.offsetParentMatrix")

            self.deformers.append(jnt_name)

        for iteration_, foot_output_ in enumerate(self.foot_inputs):
            jnt_name = node.createNode("joint",
                                       n=f"{self.data.comp_composed_name}_foot_{iteration_}_{constants.JNT_EXTENSION}",
                                       tag=self.data.comp_composed_name,
                                       )

            cmds.connectAttr(f"{foot_output_}", f"{jnt_name}.offsetParentMatrix")

            self.deformers.append(jnt_name)

        # create pawPad joint
        paw_jnt_name = node.createNode("joint",
                                       n=f"{self.data.comp_composed_name}_pawPad_{constants.JNT_EXTENSION}",
                                       tag=self.data.comp_composed_name,
                                       )

        cmds.connectAttr(f"{self.paw_control}.worldMatrix", f"{paw_jnt_name}.offsetParentMatrix")
        self.deformers.append(paw_jnt_name)



        # finish up grouping
        cmds.parent(self.deformers, self.data.output_grp_name)

        self.deformer_set_name = f"{self.data.comp_composed_name}_deformers_SET"
        cmds.sets(self.deformers, n=self.deformer_set_name)

        self.controller_set_name = f"{self.data.comp_composed_name}_controllers_SET"

        cmds.sets(self.all_controls, n=self.controller_set_name)

    def _create_bend(self):
        self.output_attrs = tuple(self.tweaker_outputs)
        window_size = 3

        create_tweaker_combos = tuple(tuple(self.tweaker_outputs[i: i + window_size])
                                      for i in range(0, len(self.tweaker_outputs) - window_size + 1, 2)
                                      )
        for iteration_, combo in enumerate(create_tweaker_combos):
            de_boor.create_hh_ribbon(controllers=combo,
                                     curve_points=5,
                                     degree=window_size-1,
                                     name=f"{self.data.comp_composed_joint_name}_bend_{iteration_:03}_limb",
                                     add_data_to=self.data.calculation_grp_name,
                                     output_objects=self.bender_secondary_controls[iteration_],
                                     global_scale=self.global_scale_connection_attr
                                     )

    def _create_tweaker_calculations(self):
        tweaker_endpoints_ = list()

        for tweaker_in, tweaker_prim in zip(self.tweaker_inputs, self.tweaker_primary_controls):

            self.multiply_matrix_by_scale(tweaker_in, tweaker_prim)

            tweaker_endpoints_.append(f"{tweaker_prim}.worldMatrix[0]")

        tweaker_midpoints_ = list()
        for iteration_, secondary_tweaker in enumerate(self.tweaker_secondary_controls):
            tweak_bld = node.createNode("blendMatrix",
                                        n=f"{self.data.comp_composed_name}_tweakerMidPos_{iteration_:03}_BMX",
                                        tag=self.data.comp_composed_name,
                                        )

            tweak_aim = node.createNode("aimMatrix",
                                        n=f"{self.data.comp_composed_name}_tweakerMidPos_{iteration_:03}_AMX",
                                        tag=self.data.comp_composed_name,
                                        )

            bld_data = {"target[0].weight": 0.5,
                        "target[0].useRotate": False,
                        "target[0].useScale": False,
                        "target[0].useShear": False,
                        }

            rig_utils.set_from_dict(node=tweak_bld,
                                    data=bld_data,
                                    )

            aim_data = {
                "primaryMode": 1,

                "primaryInputAxisX": 1,
                "primaryInputAxisY": 0,
                "primaryInputAxisZ": 0,

                "primaryTargetVectorX": 1,
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

            rig_utils.set_from_dict(node=tweak_aim,
                                    data=aim_data,
                                    )

            cmds.connectAttr(f"{self.tweaker_primary_controls[iteration_]}.worldMatrix[0]",
                             f"{tweak_aim}.inputMatrix",
                             )

            cmds.connectAttr(f"{self.tweaker_primary_controls[iteration_]}.worldMatrix[0]",
                             f"{tweak_aim}.secondaryTargetMatrix",
                             )

            cmds.connectAttr(f"{self.tweaker_primary_controls[iteration_+1]}.worldMatrix[0]",
                             f"{tweak_aim}.primaryTargetMatrix",
                             )

            cmds.connectAttr(f"{tweak_aim}.outputMatrix",
                             f"{tweak_bld}.inputMatrix",
                             )

            cmds.connectAttr(f"{self.tweaker_primary_controls[iteration_ + 1]}.worldMatrix[0]",
                             f"{tweak_bld}.target[0].targetMatrix",
                             )

            cmds.connectAttr(f"{tweak_bld}.outputMatrix",
                             f"{secondary_tweaker}.offsetParentMatrix")

            tweaker_midpoints_.append(f"{secondary_tweaker}.worldMatrix[0]")

        merged_tweakers = tuple(tuple(p for p in pair if p is not None)
                                for pair
                                in itertools.zip_longest(tweaker_endpoints_,
                                                         tweaker_midpoints_
                                                         )
                                )

        tweaker_outputs_ = itertools.chain.from_iterable(merged_tweakers)

        self.tweaker_outputs = tuple(tweaker_outputs_)

    def multiply_matrix_by_scale(self,
                                 tweaker_in: str,
                                 tweaker_prim: str,
                                 ):

        global_scale_to_tweaker = node.createNode("math_MatrixFromTRS",
                                                  n=f"{self.data.comp_composed_name}_tweakerScaling_MFT",
                                                  tag=self.data.comp_composed_name
                                                  )
        global_scale_times_tweaker = node.createNode("math_MultiplyMatrix",
                                                     n=f"{self.data.comp_composed_name}_tweakerScaling_MMX",
                                                     tag=self.data.comp_composed_name
                                                     )
        for axis in "XYZ":
            cmds.connectAttr(self.global_scale_connection_attr, f"{global_scale_to_tweaker}.scale{axis}")

        cmds.connectAttr(tweaker_in, f"{global_scale_times_tweaker}.input2")

        cmds.connectAttr(f"{global_scale_to_tweaker}.output", f"{global_scale_times_tweaker}.input1")

        cmds.connectAttr(f"{global_scale_times_tweaker}.output", f"{tweaker_prim}.offsetParentMatrix")

    def _create_chain_blends(self):

        ik_positions = self.ik_output_attrs
        fk_positions = self.fk_output_attrs[2:]

        blended_attrs = list()
        ik_controls_ = self.ik_controls
        fk_controls_ = self.fk_controls

        for ik_ctrl in ik_controls_:
            compare_ik_fk = node.createNode("math_Compare",
                                            n=f"{self.data.comp_composed_name}_CPR",
                                            tag=self.data.comp_composed_name,
                                            )

            cmds.setAttr(f"{compare_ik_fk}.input2", 0)
            cmds.setAttr(f"{compare_ik_fk}.operation", 0)

            cmds.connectAttr(self.host_ik_fk_attr, f"{compare_ik_fk}.input1", f=True)
            cmds.connectAttr(f"{compare_ik_fk}.output", f"{ik_ctrl}.visibility", f=True)

        for fk_ctrl in fk_controls_:

            compare_ik_fk = node.createNode("math_Compare",
                                            n=f"{self.data.comp_composed_name}_CPR",
                                            tag=self.data.comp_composed_name,
                                            )

            cmds.setAttr(f"{compare_ik_fk}.input2", 1)
            cmds.setAttr(f"{compare_ik_fk}.operation", 0)

            cmds.connectAttr(self.host_ik_fk_attr, f"{compare_ik_fk}.input1", f=True)
            cmds.connectAttr(f"{compare_ik_fk}.output", f"{fk_ctrl}.visibility", f=True)

        for idx_, (ik_pos, fk_pos) in enumerate(zip(ik_positions, fk_positions)):

            ik_attr_ = node.addAttr(self.data.calculation_grp_name,
                                    ln=f"ik_mtx_{idx_:03}",
                                    at="matrix",
                                    )

            fk_attr_ = node.addAttr(self.data.calculation_grp_name,
                                    ln=f"fk_mtx_{idx_:03}",
                                    at="matrix",
                                    )

            cmds.connectAttr(ik_pos,
                             ik_attr_,
                             f=True,
                             )

            cmds.connectAttr(fk_pos,
                             fk_attr_,
                             f=True,
                             )

            # change this by checking the scale (i am not sure how to handle this without scaling)
            scale_negate_data = {"input1": [1, 0, 0, 0,
                                            0, 1, 0, 0,
                                            0, 0, 1, 0,
                                            0, 0, 0, 1,
                                            ],
                                 }

            z_axis_val_ = matrix_maths.get_axis_alignment(self.data.comp_root_name,
                                                          axis=self.data.build_axis,
                                                          direction_only=True,
                                                          )

            scale_negate_data["input1"][10] *= z_axis_val_

            scale_negate_name_ = node.createNode("math_MultiplyMatrix",
                                                 n=f"{self.data.comp_composed_name}_ikFkBlendScaleNeg_{idx_:03}_MMX",
                                                 tag=self.data.comp_composed_name,
                                                 )

            rig_utils.set_from_dict(scale_negate_name_, scale_negate_data)

            cmds.connectAttr(fk_attr_,
                             f"{scale_negate_name_}.input2",
                             f=True,
                             )

            ik_fk_blend_name_ = node.createNode("blendMatrix",
                                                n=f"{self.data.comp_composed_name}_ikFkBlend_{idx_:03}_BMX",
                                                tag=self.data.comp_composed_name,
                                                )

            cmds.connectAttr(self.host_ik_fk_attr,
                             f"{ik_fk_blend_name_}.target[0].weight",
                             f=True,
                             )

            cmds.connectAttr(ik_attr_,
                             f"{ik_fk_blend_name_}.inputMatrix",
                             f=True,
                             )

            cmds.connectAttr(f"{scale_negate_name_}.output",
                             f"{ik_fk_blend_name_}.target[0].targetMatrix",
                             f=True,
                             )

            blended_attrs.append(f"{ik_fk_blend_name_}.outputMatrix")

        self.tweaker_inputs = tuple(blended_attrs[:])
        self.foot_inputs = tuple(blended_attrs[-3:])

    def connect(self):
        """
        connects the module to the one above.

        """
        if cmds.objExists("global_0_ctrl") and cmds.attributeQuery("main_scale", node="global_0_ctrl", exists=True):
            cmds.connectAttr("global_0_ctrl.main_scale", self.global_scale_connection_attr)

        # connect without spaceSwitch
        cmds.connectAttr(self.ik_hip_placement_attr,
                         f"{self.hip_ik_ctrl}.offsetParentMatrix",
                         f=True,
                         )

        cmds.connectAttr(self.ik_foot_placement_attr,
                         f"{self.foot_offset_ik_ctrl}.offsetParentMatrix",
                         f=True,
                         )

        cmds.connectAttr(self.foot_inputs[0],
                         self.paw_blend_attr,
                         f=True,
                         )

        cmds.connectAttr(self.foot_inputs[0],
                         self.paw_aim_attr,
                         f=True,
                         )

        if cmds.objExists(constants.PXO_DEFORMERS_SET_NAME):
            cmds.sets(self.deformer_set_name,
                      add=constants.PXO_DEFORMERS_SET_NAME,
                      e=True,
                      )

        if cmds.objExists(constants.PXO_CONTROLS_SET_NAME):
            cmds.sets(self.controller_set_name,
                      add=constants.PXO_CONTROLS_SET_NAME,
                      e=True,
                      )

        connector = self.data.comp_parent_name

        if connector:
            mgear_matrix = matrix_maths.tuple_to_mmatrix(cmds.getAttr(f"{connector}.worldMatrix[0]"))

            connector_matrix = matrix_maths.tuple_to_mmatrix(cmds.getAttr(f"{self.connector_attrs[0]}"))
            start_matrix = matrix_maths.tuple_to_mmatrix(cmds.getAttr(f"{self.ik_hip_placement_attr}"))
            end_matrix = matrix_maths.tuple_to_mmatrix(cmds.getAttr(f"{self.ik_foot_placement_attr}"))

            parent_world_inverse_matrix = matrix_maths.invert_matrix(mgear_matrix)
            offset_matrix_connector = matrix_maths.multiply_matrices(connector_matrix, parent_world_inverse_matrix)
            offset_matrix_start = matrix_maths.multiply_matrices(start_matrix, parent_world_inverse_matrix)
            offset_matrix_end = matrix_maths.multiply_matrices(end_matrix, parent_world_inverse_matrix)

            offset_tuple_connector = matrix_maths.mmatrix_to_tuple(offset_matrix_connector)
            offset_tuple_start = matrix_maths.mmatrix_to_tuple(offset_matrix_start)
            offset_tuple_end = matrix_maths.mmatrix_to_tuple(offset_matrix_end)

            multiplied_offset_connector = node.createNode("math_MultiplyMatrix",
                                                          n=f"{self.data.comp_composed_name}_connector_MMX",
                                                          tag=self.data.comp_composed_name,
                                                          )

            multiplied_offset_start = node.createNode("math_MultiplyMatrix",
                                                      n=f"{self.data.comp_composed_name}_startPos_MMX",
                                                      tag=self.data.comp_composed_name,
                                                      )

            multiplied_offset_end = node.createNode("math_MultiplyMatrix",
                                                    n=f"{self.data.comp_composed_name}_endPos_MMX",
                                                    tag=self.data.comp_composed_name,
                                                    )

            cmds.setAttr(f"{multiplied_offset_connector}.input1",
                         *offset_tuple_connector,
                         type="matrix",
                         )

            cmds.setAttr(f"{multiplied_offset_start}.input1",
                         *offset_tuple_start,
                         type="matrix",
                         )

            cmds.setAttr(f"{multiplied_offset_end}.input1",
                         *offset_tuple_end,
                         type="matrix",
                         )

            cmds.connectAttr(f"{connector}.worldMatrix",
                             f"{multiplied_offset_connector}.input2",
                             )

            cmds.connectAttr(f"{connector}.worldMatrix",
                             f"{multiplied_offset_start}.input2",
                             )

            cmds.connectAttr(f"{connector}.worldMatrix",
                             f"{multiplied_offset_end}.input2",
                             )

            cmds.connectAttr(f"{multiplied_offset_connector}.output",
                             self.connector_attrs[0],
                             )

            cmds.connectAttr(f"{multiplied_offset_start}.output",
                             self.ik_hip_placement_attr,
                             )

            cmds.connectAttr(f"{multiplied_offset_end}.output",
                             self.ik_foot_placement_attr,
                             )

        if self.data.comp_spaces:
            self._connect_spaces()

            # generate the space switches

            hip_spaces = [self.ik_hip_placement_attr, ]
            hip_spaces.extend(self.space_attrs["hip"])

            foot_spaces = [self.ik_foot_placement_attr, ]
            foot_spaces.extend(self.space_attrs["foot"])

            pv_spaces = [self.main_pv_attr, ]
            pv_spaces.extend(self.space_attrs["pv"])

            hip_switcher, hip_switch_attr = rig_utils.space_switcher(hip_spaces,
                                                                     name=self.data.comp_composed_name,
                                                                     subname="hipSpace",
                                                                     tag=self.data.comp_composed_name,
                                                                     )

            foot_switcher, foot_switch_attr = rig_utils.space_switcher(foot_spaces,
                                                                       name=self.data.comp_composed_name,
                                                                       subname="footSpace",
                                                                       tag=self.data.comp_composed_name,
                                                                       )

            pv_switcher, pv_switch_attr = rig_utils.space_switcher(pv_spaces,
                                                                   name=self.data.comp_composed_name,
                                                                   subname="footSpace",
                                                                   tag=self.data.comp_composed_name,
                                                                   )

            cmds.connectAttr(self.host_hip_space_switch_attr, hip_switch_attr, f=True)
            cmds.connectAttr(self.host_foot_space_switch_attr, foot_switch_attr, f=True)
            cmds.connectAttr(self.host_pv_space_switch_attr,  pv_switch_attr, f=True)

            cmds.connectAttr(f"{hip_switcher}.outputMatrix", f"{self.hip_ik_ctrl}.offsetParentMatrix", f=True)
            cmds.connectAttr(f"{foot_switcher}.outputMatrix", f"{self.foot_offset_ik_ctrl}.offsetParentMatrix", f=True)
            cmds.connectAttr(f"{pv_switcher}.outputMatrix", f"{self.pv_ik_ctrl}.offsetParentMatrix", f=True)

        if self.data.misc_info:
            self._connect_mgear(self.data.misc_info,
                    f"{hip_switcher}.outputMatrix",
                                f"{foot_switcher}.outputMatrix",
                                self.tweaker_inputs[0],
                                self.tweaker_inputs[1]
                                )

    def _connect_spaces(self):
        for space_attr_ in ("hip", "foot", "pv"):
            for idx_, space_ in enumerate(self.data.comp_spaces):

                space_matrix = matrix_maths.tuple_to_mmatrix(cmds.getAttr(f"{space_}.worldMatrix[0]"))

                connector_matrix = matrix_maths.tuple_to_mmatrix(cmds.getAttr(self.space_attrs[space_attr_][idx_]
                                                                              )
                                                                 )

                parent_world_inverse_matrix = matrix_maths.invert_matrix(space_matrix)

                offset_matrix_connector = matrix_maths.multiply_matrices(connector_matrix, parent_world_inverse_matrix)

                offset_tuple_connector = matrix_maths.mmatrix_to_tuple(offset_matrix_connector)

                multiplied_offset_connector = node.createNode("math_MultiplyMatrix",
                                                              n=f"{self.data.comp_composed_name}_{space_}_MMX",
                                                              tag=self.data.comp_composed_name,
                                                              )

                cmds.setAttr(f"{multiplied_offset_connector}.input1",
                             *offset_tuple_connector,
                             type="matrix",
                             )

                cmds.connectAttr(f"{space_}.worldMatrix",
                                 f"{multiplied_offset_connector}.input2",
                                 )

                cmds.connectAttr(f"{multiplied_offset_connector}.output",
                                 self.space_attrs[space_attr_][idx_]
                                 )

    def _connect_mgear(self,
                       scapula_guide,
                       start_offset_attr,
                       end_offset_attr,
                       middle_div_attr,
                       end_div_attr):

        start_offset_name = node.createNode("transform",
                                            n=f"{self.data.comp_composed_name}_startOffset_POS",
                                            tag=self.data.comp_composed_name
                                            )

        end_offset_name = node.createNode("transform",
                                          n=f"{self.data.comp_composed_name}_endOffset_POS",
                                          tag=self.data.comp_composed_name
                                          )

        cmds.connectAttr(start_offset_attr,
                         f"{start_offset_name}.offsetParentMatrix"
                         )

        cmds.connectAttr(end_offset_attr,
                         f"{end_offset_name}.offsetParentMatrix"
                         )

        middle_div_name = node.createNode("transform",
                                          n=f"{self.data.comp_composed_name}_startBlendOffset_POS",
                                          tag=self.data.comp_composed_name
                                          )

        end_div_name = node.createNode("transform",
                                       n=f"{self.data.comp_composed_name}_endBlendOffset_POS",
                                       tag=self.data.comp_composed_name
                                       )

        cmds.connectAttr(middle_div_attr,
                         f"{middle_div_name}.offsetParentMatrix"
                         )

        cmds.connectAttr(end_div_attr,
                         f"{end_div_name}.offsetParentMatrix"
                         )

        cmds.parent((start_offset_name,
                     end_offset_name,
                     middle_div_name,
                     end_div_name,
                     ),
                    self.data.calculation_grp_name
                    )

        scapula_setup.create_scapula_setup(
                pmc.PyNode(self.host_ctrl),             # host_dag
                pmc.PyNode(start_offset_name),          # start_dag
                pmc.PyNode(scapula_guide),              # scap_dag
                pmc.PyNode(self.hip_ik_ctrl),           # shoulder_dag
                pmc.PyNode(self.foot_ik_ctrl),          # end_dag
                pmc.PyNode(end_offset_name),            # ik_cns_dag
                self.total_length,                      # total_length
                pmc.PyNode(middle_div_name),            # middle_div_dag
                pmc.PyNode(end_div_name),               # end_div_dag
                root_name=f"{self.data.comp_composed_name}_scapula",
                tag=self.data.comp_composed_name,
        )

    def disconnect(self):
        """
        disconnects the module to the one above.

        """

        pass


