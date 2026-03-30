

from importlib import reload

import logging
from pprint import pprint

from future import standard_library

from typing import Optional

from maya import cmds
from pymel import core as pmc

import pxo_rigging_kit.maya_utils.rigging.rig_utils
from pxo_rigging_kit.maya_utils.EWAW_rs import matrix_maths
from pxo_rigging_kit.maya_utils.EWAW_rs.base_constructs import module
from pxo_rigging_kit.maya_utils.EWAW_rs.base_constructs import data
from pxo_rigging_kit.maya_utils.EWAW_rs import TO_REFACTOR as TO_REFACTOR_PLS
from pxo_rigging_kit.maya_utils.rigging import curves_utils, rig_utils

reload(module)
reload(TO_REFACTOR_PLS)
##########################################################
# GLOBALS
##########################################################

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)
standard_library.install_aliases()


class Main(module.BaseModule):
    """
    builds the implementation of a module, gets the basic build inherited from BaseModule.

    """
    def __init__(self,
                 build_axis: str = "Y",
                 comp_name: str = "__BASE_MODULE__",
                 comp_type: str = "default",
                 connector: Optional[str] = None,
                 comp_index: int = 0,
                 comp_side: str = "C",
                 comp_subplacement_transforms: list = None,
                 comp_lra_transforms: list = None,
                 comp_parent_name: Optional[str] = None,
                 data_container: Optional[data.DataContainer] = None
                 ):
        """
        This class is the master class for our rigging modules.


        """

        super().__init__(build_axis=build_axis,
                         comp_name=comp_name,
                         comp_type=comp_type,
                         connector=connector,
                         comp_index=comp_index,
                         comp_side=comp_side,
                         comp_subplacement_transforms=comp_subplacement_transforms,
                         comp_lra_transforms=comp_lra_transforms,
                         comp_parent_name=comp_parent_name,
                         data_container=data_container
                         )

        print(self.data)


        # information created in class instance
        self.connector_attrs = list()
        self.controller_offset_attrs = list()
        self.controller_attrs = list()
        self.calculation_attrs = list()
        self.deformers = list()

    def create_inputs(self):

        # empty list for saveguarding
        self.controller_offset_attrs = []
        self.connector_attrs = []
        if not self.data.comp_subplacement_transforms:
            return


        main_and_sub = self.data.comp_subplacement_transforms[:]
        main_and_sub.insert(0, self.data.comp_root_transforms)

        # check how it should be placed into the parent space
        cmds.addAttr(f"{self.data.input_grp_name}", ln="op_connector", dt="matrix")

        if self.data.connector:
            connector_world_mtx = matrix_maths.get_world_matrix(self.data.connector)
            connector_world_tuple = matrix_maths.mmatrix_to_tuple(connector_world_mtx)
            cmds.setAttr(f"{self.input_grp_name}.op_connector", *connector_world_tuple, type="matrix")

            self.connector_attrs.append(f"{self.input_grp_name}.op_connector")

        # positions from the guides themselves
        cmds.addAttr(f"{self.data.input_grp_name}", ln="op_positions", dt="matrix", multi=True)

        for iteration__, (name, value) in enumerate(zip(self.data.comp_subplacement_names, self.data.comp_subplacement_transforms)):
            attr_name = f"{self.data.input_grp_name}.op_positions[{iteration__}]"
            pmc.setAttr(attr_name, value, type="matrix")
            self.controller_attrs.append(attr_name)

        offset_values = rig_utils.generate_offsets(connector=None,
                                                                                      operator_transformations=main_and_sub,
                                                                                      )
        # offsets from the guides themselves
        cmds.addAttr(f"{self.data.input_grp_name}", ln="op_offsets", dt="matrix", multi=True)

        for iteration__, value in enumerate(offset_values):
            attr_name = f"{self.data.input_grp_name}.op_offsets[{iteration__}]"
            pmc.setAttr(attr_name, value, type="matrix")
            self.controller_offset_attrs.append(attr_name)

    def create_controls(self):
        """

        Returns:

        """
        offsets = self.controller_offset_attrs
        positions = self.controller_attrs

        controller_offset = 0

        controls = list()
        multiplies = list()

        # empty that list for saveguarding
        self.calculation_attrs = []

        # this is a total mess, its split out so its easier to troubleshoot when what happens
        if self.connector_attrs:
            # sets the offset to 1 so the list for the matrix connections will not use the connector ctrl
            controller_offset = 1

            ConnectorCreator_ = curves_utils.BoxControl()
            ConnectorCreator_.create_curve(name=f"{self.data.comp_composed_name}_connector_ctrl",
                                           buffer_grp=False
                                           )

            ctrl_name = str(ConnectorCreator_.control.shortName())

            controls.append(ctrl_name)
            cmds.connectAttr(self.connector_attrs[0], f"{ctrl_name}.offsetParentMatrix")

        for iteration_, _ in enumerate(offsets):

            PrimaryCreator_ = curves_utils.ConeControl()
            PrimaryCreator_.create_curve(name=f"{self.data.comp_composed_name}_primary_{iteration_:03}_ctrl",
                                         buffer_grp=False
                                         )

            ctrl_name = str(PrimaryCreator_.control.shortName())

            controls.append(ctrl_name)

        for iteration_, offset in enumerate(offsets):
            mult_mtx_name = cmds.createNode("math_MultiplyMatrix", n=f"{offset}_to_{controls[iteration_]}")

            cmds.connectAttr(f"{offset}", f"{mult_mtx_name}.input1", f=True)

            # we need to skip the first iteration, if we do not, we create a cycle
            if iteration_ != 0:
                cmds.connectAttr(f"{controls[iteration_-1]}.worldMatrix", f"{mult_mtx_name}.input2", f=True)

            multiplies.append(mult_mtx_name)

        for mult_mtx_name, controller in zip(multiplies,
                                             controls
                                             ):

            cmds.connectAttr(f"{mult_mtx_name}.output", f"{controller}.offsetParentMatrix")

        # parents the controls under the primaries group for now :)
        cmds.parent(controls, self.data.primaries_grp_name)

        # create outputs of the control system
        # not sure if the edge of this should be in here or in the create calculations
        for iteration_, ctrl_name_ in enumerate(controls):
            calc_name = f"{self.data.calculation_grp_name}.ctrl_postition_{iteration_:03}"
            cmds.addAttr(self.data.calculation_grp_name, ln=f"ctrl_postition_{iteration_:03}", dt="matrix")

            cmds.connectAttr(f"{ctrl_name_}.worldMatrix",
                             calc_name,
                             )

            self.calculation_attrs.append(calc_name)

    def create_calculations(self):

        # empty list for saveguarding
        self.output_attrs = []
        calc_attrs = self.calculation_attrs[:]

        pprint(calc_attrs)

        if self.data.connector:
            print("yippie")
            calc_attrs = self.calculation_attrs[1:]
            self.output_attrs.append(self.calculation_attrs[0])

        attr_lengths = len(calc_attrs)
        for idx_ in range(attr_lengths):
            flip = 1 if idx_ < attr_lengths-1 else -1
            aim_matrix_ = cmds.createNode("aimMatrix")
            mul_matrix_ = cmds.createNode("math_MultiplyMatrix")
            bld_matrix_ = cmds.createNode("blendMatrix")

            cmds.setAttr(f"{mul_matrix_}.input1",
                         *(1, 0, 0, 0,
                           0, 1, 0, 0,
                           0, 0, 1, 0,
                           0, 10, 0, 1,
                           ),
                         type="matrix"
                         )
            cmds.connectAttr(calc_attrs[idx_], f"{mul_matrix_}.input2")

            cmds.connectAttr(f"{mul_matrix_}.output", f"{aim_matrix_}.secondaryTargetMatrix")
            cmds.setAttr(f"{aim_matrix_}.secondaryMode", 1, l=True)

            cmds.connectAttr(f"{calc_attrs[idx_ + flip]}", f"{aim_matrix_}.primaryTargetMatrix")
            cmds.connectAttr(f"{calc_attrs[idx_]}", f"{aim_matrix_}.inputMatrix")



            cmds.connectAttr(f"{calc_attrs[idx_]}", f"{bld_matrix_}.inputMatrix")
            cmds.connectAttr(f"{aim_matrix_}.outputMatrix", f"{bld_matrix_}.target[0].targetMatrix")

            attr_name_ = f"{self.data.output_grp_name}.deformation_position_{idx_:03}"
            cmds.addAttr(self.data.output_grp_name, ln=f"deformation_position_{idx_:03}", dt="matrix")
            cmds.connectAttr(f"{bld_matrix_}.outputMatrix", attr_name_)
            self.output_attrs.append(attr_name_)

        return

    def create_outputs(self):
        """

        Returns:

        """
        self.deformers = []
        output_attrs = self.output_attrs[:]

        for idx_, output_ in enumerate(output_attrs):
            jnt_name = cmds.createNode("joint", n=f"{self.data.comp_composed_name}_output_{idx_:03}_jnt")

            cmds.connectAttr(output_, f"{jnt_name}.offsetParentMatrix")

            self.deformers.append(jnt_name)

        cmds.parent(self.deformers, self.data.output_grp_name)

    def connect(self):
        """
        connects the module to the one above.

        """
        pass

    def disconnect(self):
        """
        disconnects the module to the one above.

        """

        pass
