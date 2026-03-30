

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
from pxo_rigging_kit.maya_utils.rigging import rig_utils, curves_utils, mesh_islands

reload(mesh_islands)
reload(module)
reload(TO_REFACTOR_PLS)
reload(rig_utils)

##########################################################
# GLOBALS
##########################################################

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)
standard_library.install_aliases()


import pymel.core as pmc



import maya.cmds as cmds
import pymel.core as pmc
from maya import OpenMaya





def build_output_network(muscles_dict, preexisting_joints=False):
    influence_groups = list()
    for key, values in muscles_dict.items():

        if not preexisting_joints:
            influence_objects = list()
            for iteration_, value in enumerate(values):
                num = str(iteration_ + 1).zfill(3)
                influence_object = pmc.joint(n='{key}_bnd_{numberation}_jnt'.format(network_name=_NETWORK_NAME,
                                                                                    key=key,
                                                                                    numberation=num,
                                                                                    )
                                             )
                influence_object.overrideEnabled.set(True, lock=True)
                influence_object.overrideColor.set(24, lock=True)
                influence_object.inheritsTransform.set(False, lock=True)

                pmc.select(cl=True)

                influence_objects.append(influence_object)

                out_info_node = pmc.PyNode('{key}_out_001_grp'.format(network_name=_NETWORK_NAME,
                                                                      key=key)).attr(
                        '{}_deformMatrix'.format(value)).connect(
                        influence_object.offsetParentMatrix)

            influence_group = pmc.group(influence_objects, n='{key}_outJoints_grp'.format(key=key))
            influence_groups.append(influence_group)
            return influence_groups

        else:
            for iteration_, value in enumerate(values):
                influence_object = pmc.PyNode(value).affiliated_jnt.get()
                pmc.PyNode('{key}_out_001_grp'.format(network_name=_NETWORK_NAME,
                                                      key=key)).attr(
                        '{}_deformMatrix'.format(value)).connect(
                        influence_object.offsetParentMatrix, f=True)

                #influence_groups.append(influence_group)

            return None

def build_c_muscle_spline_setup(muscles_dict):
    _create_component_masters(muscles_dict)
    _create_c_muscle_splines(muscles_dict)
    _create_result_network(muscles_dict)


def test_build_c_muscle_spline_setup(input_grps=None, preexisting_joints=None):
    comp_dict = compose_dictionary(input_grps=input_grps)

    print(comp_dict)

    build_c_muscle_spline_setup(comp_dict)
    build_output_network(comp_dict, preexisting_joints=preexisting_joints)



def build_slerp_ramp(prefix, control_obj, attrs_out):
    """
    Take a collection of objects and interpolate them along a curve.
    It uses a master remapValue that drives multiple remapValues
    to simulate the effect of a multi-out curve node.
    References to "attr", because it was originally written for attring ribbon IK
    But it can interpolate any custom attributes you wish
    """
    # The master attr profile curve.
    master_name = "{}_master_ribbon_lerp_rmv".format(prefix)

    master_remap = pmc.createNode("remapValue", n=master_name)

    # set the range to the count of attr objects.
    master_remap.inputMax.set(len(attrs_out) - 1)

    # set to smooth interpolation.
    master_remap.value[0].value_Interp.set(2)

    p_start_name = "{}_startValue".format(prefix)

    p_mid_name = "{}_midValue".format(prefix)

    p_end_name = "{}_endValue".format(prefix)

    attr_start_name = "{}_startPosition".format(prefix)

    attr_mid_name = "{}_midPosition".format(prefix)

    attr_end_name = "{}_endPosition".format(prefix)

    remap_start_name = "{}_minRemap".format(prefix)

    remap_end_name = "{}_maxRemap".format(prefix)

    attr_type_name = "{}_interpolation".format(prefix)

    position_start = node.addAttr(control_obj,
                                  at="double",
                                  ln=p_start_name,
                                  min_val=0.0,
                                  max_val=1.0,
                                  default_val=0.0
                                  )

    p_mid = node.addAttr(control_obj,
                         at="double",
                         ln=p_mid_name,
                         min_val=0.0,
                         max_val=1.0,
                         default_val=1
                         )

    p_end = node.addAttr(control_obj,
                         at="double",
                         ln=p_end_name,
                         min_val=0.0,
                         max_val=1.0,
                         default_val=0
                         )

    attr_start = node.addAttr(control_obj,
                              at="double",
                              ln=attr_start_name,
                              min_val=0.0,
                              max_val=1.0,
                              default_val=0.0
                              )

    attr_mid = node.addAttr(control_obj,
                            at="double",
                            ln=attr_mid_name,
                            min_val=0.0001,
                            max_val=0.9999,
                            default_val=0.5
                            )

    attr_end = node.addAttr(control_obj,
                            at="double",
                            ln=attr_end_name,
                            min_val=0.0,
                            max_val=1.0,
                            default_val=1.0
                            )

    remap_min = node.addAttr(control_obj,
                             at="double",
                             ln=remap_start_name,
                             default_val=0.0
                             )

    remap_max = node.addAttr(control_obj,
                             at="double",
                             ln=remap_end_name,
                             default_val=1
                             )

    # attrType interpolation 0: none 1: linear 2: smooth 3: spline
    attr_type = node.addAttr(control_obj,
                             at="long",
                             ln=attr_type_name,
                             min_val=0,
                             max_val=2,
                             default_val=2
                             )

    attr_start.connect(master_remap.value[0].value_Position)
    attr_mid.connect(master_remap.value[1].value_Position)
    attr_end.connect(master_remap.value[2].value_Position)

    position_start.connect(master_remap.value[0].value_FloatValue)
    p_mid.connect(master_remap.value[1].value_FloatValue)
    p_end.connect(master_remap.value[2].value_FloatValue)

    attr_type.connect(master_remap.value[0].value_Interp)
    attr_type.connect(master_remap.value[1].value_Interp)
    attr_type.connect(master_remap.value[2].value_Interp)

    for iteration_, attr_out in enumerate(attrs_out):
        attr_profile_name = '{}_lerp_profile_{}_rmv'.format(prefix, iteration_ + 1)
        attr_profile = pmc.createNode('remapValue', n=attr_profile_name)

        attr_profile.inputMax.set(len(attrs_out) - 1)
        attr_profile.inputValue.set(iteration_)

        remap_min.connect(attr_profile.outputMin)
        remap_max.connect(attr_profile.outputMax)

        master_remap.value[0].value_Position.connect(attr_profile.value[0].value_Position)
        master_remap.value[0].value_FloatValue.connect(attr_profile.value[0].value_FloatValue)
        master_remap.value[0].value_Interp.connect(attr_profile.value[0].value_Interp)

        master_remap.value[1].value_Position.connect(attr_profile.value[1].value_Position)
        master_remap.value[1].value_FloatValue.connect(attr_profile.value[1].value_FloatValue)
        master_remap.value[1].value_Interp.connect(attr_profile.value[1].value_Interp)

        master_remap.value[2].value_Position.connect(attr_profile.value[2].value_Position)
        master_remap.value[2].value_FloatValue.connect(attr_profile.value[2].value_FloatValue)
        master_remap.value[2].value_Interp.connect(attr_profile.value[2].value_Interp)

        attr_profile.outValue.connect(attr_out)


def add_slerps_to_muscle_spline():
    for node in pmc.selected():
        for _ATTR_NAME in _FALLOFF_ATTRS:
            attrs_out_man = sorted(
                    [attribute_ for attribute_ in node.listAttr() if
                     attribute_.shortName().split('_')[-1] == _ATTR_NAME])

            # The first argument is just a string prefix to make the contol attributes unique

            # You can also specify lists of attributes to drive multiple things at once.
            if attrs_out_man:
                build_slerp_ramp(_ATTR_NAME, node, attrs_out_man)


# test_build_c_muscle_spline_setup(input_grps=None, preexisting_joints=True)



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

        self.lra_mmatrices = list()
        self.total_length = None
        self.segment_lengths = list()
        self.total_length_attr = None
        self.segment_length_attrs = list()
        self.prim_controls = list()
        self.sec_controls = list()

        self._MUSCLE_SIM_ATTRS = {'tangentLength':     0.1,
                             'jiggle':            10,
                             'rest':              24,
                             'cycle':             9,
                             'jiggleImpact':      1,
                             'jiggleImpactStart': 0.1,
                             'jiggleImpactStop':  0.1,
                             'squash_value':       1,
                             }
        self._FALLOFF_ATTRS = ('jiggle', 'squash_value')

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

        self.lra_mmatrices = matrix_maths.convert_lra_mtxtuples_to_mmatrices(tuple(self.data.comp_lra_transforms))
        self.total_length, self.segment_lengths = matrix_maths.calculate_distances(self.lra_mmatrices)

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

        self.u_vals = self.calculate_u_values()

    def create_controls(self):
        """

        Returns:

        """

        self.prim_controls = self._create_prim_ctrls()
        self.sec_controls = self._create_secondary_ctrls()

        self._adapt_host_ctrl()

        self.all_controls.extend(self.prim_controls)

    def _adapt_host_ctrl(self):
        node.addAttr(self.host_ctrl,
                     ln='restLength',
                     at='double',
                     dv=self.total_length,
                     k=True
                     )

        for it_, val_ in enumerate(self.u_vals):
            node.addAttr(self.host_ctrl,
                         ln=f"att_{it_}_uValue",
                         at='double',
                         dv=val_,
                         k=True
                         )

        # TO CALC# component_master.addAttr('{}_controlMatrix'.format(value), at='matrix')
        node.addAttr(self.host_ctrl,
                     ln=f"global_simulation_attrs",
                     at='enum',
                     enumName=constants.PXO_SEPARATOR_STRING,
                     k=True
                     )

        global_local_blend = rig_utils.add_normalized_attr(node_name=self.host_ctrl,
                                                      attr_name=f"global_local_blend",
                                                      min_value=0,
                                                      max_value=10,
                                                      tag=self.data.comp_composed_name,
                                                      )
        global_attrs = list()
        for name_, default_value_ in self._MUSCLE_SIM_ATTRS.items():
            att_ = node.addAttr(self.host_ctrl, ln=f"global_{name_}", at='double', dv=float(default_value_), k=True)
            global_attrs.append(att_)

        node.addAttr(self.host_ctrl,
                     ln=f"local_simulation_attrs",
                     at='enum',
                     enumName=constants.PXO_SEPARATOR_STRING,
                     k=True
                     )

        self.attr_ref = self._MUSCLE_SIM_ATTRS.copy()

        for att_ in self.attr_ref:
            self.attr_ref[att_] = list()

        for sec_ctrl_ in self.sec_controls:
            node.addAttr(self.host_ctrl,
                         ln=f"{sec_ctrl_}_sim",
                         at='enum',
                         enumName=constants.PXO_SEPARATOR_STRING,
                         k=True
                         )

            local_attrs = list()
            for name_, default_value_ in self._MUSCLE_SIM_ATTRS.items():
                att_ = node.addAttr(self.host_ctrl,
                             ln=f"{sec_ctrl_}_{name_}",
                             nn=f"{name_}",
                             at='double',
                             dv=float(default_value_),
                             k=True,
                             )
                local_attrs.append(att_)



            for glob_, loc_, name in zip(global_attrs,local_attrs, self.attr_ref):
                blend_name = node.createNode("math_Lerp",
                                             n=f"{self.data.comp_composed_name}_{name}_LRP",
                                             tag=self.data.comp_composed_name)

                cmds.connectAttr(global_local_blend,
                                 f"{blend_name}.alpha"
                                 )

                cmds.connectAttr(glob_,
                                 f"{blend_name}.input1"
                                 )

                cmds.connectAttr(loc_,
                                 f"{blend_name}.input2"
                                 )

                self.attr_ref[name].append(f"{blend_name}.output")

            pprint(self.attr_ref)
    def _create_prim_ctrls(self):
        _prim_controls = list()
        # create ribbon master controls
        FkCreator_ = curves_utils.SphereControl()
        for ctrl_sub_name in ("Start", "End"):

            ctrl_name = FkCreator_.create_curve(
                    name=f"{self.data.comp_composed_name}_ribbon{ctrl_sub_name}_{0:03}_ctrl",
                    color_index=self.data.primary_color,
                    buffer_grp=False,
                    scale=(1, 1, 1),
                    tag=self.data.comp_composed_name,

            )

            _prim_controls.append(ctrl_name)
        # parents the controls under the primaries group for now :)
        cmds.parent(_prim_controls, self.data.primaries_grp_name)
        # create outputs of the control system
        # not sure if the edge of this should be in here or in the create calculations
        for iteration_, ctrl_name_ in enumerate(_prim_controls):
            calc_name = f"{self.data.calculation_grp_name}.ctrl_postition_{iteration_:03}"

            cmds.addAttr(self.data.calculation_grp_name,
                         ln=f"ctrl_postition_{iteration_:03}",
                         dt="matrix",
                         )

            cmds.connectAttr(f"{ctrl_name_}.worldMatrix",
                             calc_name,
                             )

            self.calculation_attrs.append(calc_name)

        start_value_ = self.controller_attrs[0]
        end_value_ = self.controller_attrs[-1]

        start_offset_ = self.controller_offset_attrs[0]
        end_offset_ = self.controller_offset_attrs[-1]



        return _prim_controls

    def _create_secondary_ctrls(self):
        _sec_controls = list()
        # create ribbon master controls
        FkCreator_ = curves_utils.SphereControl()

        for ctrl_idx in range(len(self.controller_attrs)):

            ctrl_name = FkCreator_.create_curve(
                    name=f"{self.data.comp_composed_name}_ribbonSub_{ctrl_idx:03}_ctrl",
                    color_index=self.data.secondary_color,
                    buffer_grp=False,
                    scale=(.3, .3, .3),
                    tag=self.data.comp_composed_name,

            )

            _sec_controls.append(ctrl_name)
        # parents the controls under the primaries group for now :)
        cmds.parent(_sec_controls, self.data.secondaries_grp_name)
        # create outputs of the control system
        # not sure if the edge of this should be in here or in  create calculations
        for iteration_, ctrl_name_ in enumerate(_sec_controls):

            calc_name = node.addAttr(self.data.calculation_grp_name,
                         ln=f"ribbonSubCtrl_postition_{iteration_:03}",
                         dt="matrix",
                         )

            cmds.connectAttr(f"{ctrl_name_}.worldMatrix",
                             calc_name,
                             )

            self.calculation_attrs.append(calc_name)
        return _sec_controls

    def create_calculations(self):

        for ctl_, mtx_ in zip(self.sec_controls, self.data.comp_lra_transforms):
            cmds.xform(ctl_,
                       matrix=mtx_,
                       worldSpace=True,
                       )

        island_mesh, uv_pin_node = mesh_islands.build_combined_pin_mesh(self.sec_controls,
                                                                        rotate=True,
                                                                        pin_node_split_amount=100,
                                                                        ribbon_node_split_amount=100,
                                                                        desired_count=100,
                                                                        system_name=self.data.comp_composed_name,
                                                                        radius=2.5,
                                                                        scale_connection=None,
                                                                        use_directly=True,
                                                                        )

        poly_ribbon_drivers = list()

        for ctl_ in self.prim_controls:
            driver_joint = node.createNode("joint",
                                           n=ctl_.replace(constants.CTRL_EXTENSION,
                                                          constants.JNT_EXTENSION,
                                                          ),
                                           tag=self.data.comp_composed_name,
                                           )


            cmds.connectAttr(f"{ctl_}.worldMatrix",
                             f"{driver_joint}.offsetParentMatrix",
                             f=True
                             )

            poly_ribbon_drivers.append(driver_joint)

        cmds.skinCluster(*poly_ribbon_drivers,
                         island_mesh[0].longName(),
                         tsb=True,
                         )

        cmds.parent(poly_ribbon_drivers, self.data.calculation_grp_name)
        cmds.parent(island_mesh, self.data.calculation_grp_name)

    def create_outputs(self):
        """

        Returns:

        """
        spline_shape = node.createNode("cMuscleSpline",
                                      n=f"{self.data.comp_composed_name}_CMCShape",
                                      tag=self.data.comp_composed_name)

        spline_transform = cmds.listRelatives(spline_shape, parent=True)
        cmds.rename(spline_transform, f"{self.data.comp_composed_name}_CMC")
        cmds.parent(spline_transform, self.data.calculation_grp_name)

        for iteration_, ctl_ in enumerate(self.sec_controls):

            cmds.connectAttr(f"{ctl_}.worldMatrix",
                             f"{spline_shape}.controlData[{iteration_}].insertMatrix",
                             f=True,
                             )

            cmds.connectAttr(f"{self.host_ctrl}.att_{iteration_}_uValue",
                             f"{spline_shape}.readData[{iteration_}].readU",
                             f=True,
                             )

            for attr_name, attr_att in self.attr_ref.items():
                if attr_name == 'squash_value':
                    continue
                pprint(attr_att)
                cmds.connectAttr(attr_att[iteration_],
                                 f"{spline_shape}.controlData[{iteration_}].{attr_name}",
                                 f=True,
                                 )

        cmds.connectAttr("time1.outTime", f"{spline_shape}.settings.inTime")
        # master_node.restLength.set(spline_shape.outLen.get())# master_node.restLength.set(spline_shape.outLen.get())# master_node.restLength.set(spline_shape.outLen.get())

        normalize_length = node.createNode('math_Divide',
                                          n=f"{self.data.comp_composed_name}_baseLength_DIV",
                                           tag=self.data.comp_composed_name)

        normalize_scale = node.createNode('math_Multiply',
                                         n=f"{self.data.comp_composed_name}_baseLength_MLT",
                                          tag=self.data.comp_composed_name)

        cmds.setAttr(f"{normalize_scale}.input1",
                     1,
                     l=True,
                     )

        cmds.connectAttr(f"{spline_shape}.outLen", f"{normalize_length}.input2")
        cmds.connectAttr(f"{self.host_ctrl}.restLength", f"{normalize_scale}.input2")
        cmds.connectAttr(f"{normalize_scale}.output", f"{normalize_length}.input1")

        # muscle_shape.curveLengthnormalize_scale.input1
        for iteration_, value in enumerate(self.sec_controls):
            power_scale = node.createNode("math_Power",
                                         n=f"{self.data.comp_composed_name}_squash {iteration_:03}_POW",
                                         tag=self.data.comp_composed_name,
                                         )

            bld_mtx = node.createNode('blendMatrix',
                                     n=f"{self.data.comp_composed_name}_{value}_{iteration_}_BMX",
                                     tag=self.data.comp_composed_name,
                                     )

            comp_mtx = node.createNode("composeMatrix",
                                       n=f"{self.data.comp_composed_name}_{value}_{iteration_}_CMX",
                                       tag=self.data.comp_composed_name,
                                       )




            cmds.setAttr(f"{bld_mtx}.target[0].useRotate", False, lock=True)
            cmds.setAttr(f"{bld_mtx}.target[0].useShear", False, lock=True)

            cmds.connectAttr(f"{normalize_length}.output", f"{power_scale}.input")
            cmds.connectAttr(self.attr_ref["squash_value"][iteration_], f"{power_scale}.exponent")
            cmds.connectAttr(f"{spline_shape}.outputData[{iteration_}].outTranslate", f"{comp_mtx}.inputTranslate")
            cmds.connectAttr(f"{value}.worldMatrix", f"{bld_mtx}.inputMatrix")
            cmds.connectAttr(f"{comp_mtx}.outputMatrix", f"{bld_mtx}.target[0].targetMatrix")

            for axis in "XYZ":
                cmds.connectAttr(f"{power_scale}.output", f"{comp_mtx}.inputScale{axis}")

            jnt= node.createNode("joint",
                            name=f"{self.data.comp_composed_name}_JNT",
                            tag=self.data.comp_composed_name)

            cmds.connectAttr(f"{bld_mtx}.outputMatrix",
                             f"{jnt}.offsetParentMatrix",
                             f=True,
                             )

        return
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
        return
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

    def calculate_u_values(self,
                          start_value=0
                          ):


        total_u_values = list()
        value_adapted = start_value

        for seg_len_ in self.segment_lengths:
            total_u_values.append(value_adapted)
            value_adapted += seg_len_ / self.total_length

        total_u_values.append(value_adapted)

        return tuple(total_u_values)