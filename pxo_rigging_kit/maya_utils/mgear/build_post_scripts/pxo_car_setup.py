"""
Custom script for a car setup
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import built-in modules
from builtins import dict
from builtins import int
from builtins import object
from builtins import range
from builtins import str
from builtins import zip
import logging
from typing import Optional

# Import third-party modules
from future import standard_library
import mgear.shifter.custom_step as cstp
from past.utils import old_div
import pymel.core as pm
import pymel.core.datatypes as dt

from pxo_rigging_kit.maya_utils.maya_conversion_utils import pymaya_to_pymel

#######################################################
# GLOBALS
#######################################################

ENUM_TOKEN_STATIC = "########"
standard_library.install_aliases()
logging.basicConfig(level=logging)
_LOGGER = logging.getLogger(__name__ + ".py")

#######################################################
# FUNCTIONS
#######################################################


def insert_two_offsets(node):
    if not node:
        node = pm.selected()[0]

    node_name = node.shortName()
    parent = node.getParent()

    #   create and adapt nodes

    #   create offsets
    parent_offset = pm.createNode('transform',
                                  n=f'{node_name}_calcInputPosition_pos'
                                  )

    offset = pm.createNode('transform',
                           n=f'{node_name}_calcOutputPosition_pos'
                           )

    #   check for parent node
    pm.parent(parent_offset,
              node
              )

    if parent:
        pm.parent(parent_offset, parent)
        pm.matchTransform(parent_offset, parent)

    pm.parent(offset, parent_offset)
    pm.matchTransform(offset, parent_offset)

    pm.matchTransform(offset, node)
    pm.parent(node, offset)

    return node, parent, offset, parent_offset


def split_list(a_list):
    """splits list into two

    :param a_list: list to be split
    :return: tuple result
    """
    half = len(a_list) // 2
    return a_list[:half], a_list[half:]

#######################################################
# CLASSES
#######################################################


class DynamicOffset(object):
    """ test run
    jiggle = DynamicOffset()
    jiggle.build_calc_network()
    jiggle.connect_to_rig()
    """

    def __init__(self):
        #   aux variables
        self.xyz_uppered = ['X', 'Y', 'Z']

        #   build variables
        self.dynamic_enhanced_node = None
        self.node_name = None
        self.parent = None

        #   animated nodes
        self.spring_node = None
        self.blend_matrix = None
        self.recenter_matrix = None
        self.compose_offset = None

        #   base settings
        self.default_spring_vals = {'time': True,
                                    'stiffness': 0.2,
                                    'damping': 0.1,
                                    'intensity': 1}

        self.default_trans_contribution = 0.3

        self.offset_aim = 400

        self.control_attrs = dict()

    def build_calc_network(self, node=None):
        if not node:
            self.dynamic_enhanced_node = pm.selected()[0]
        else:
            self.dynamic_enhanced_node = node

        self.node_name = self.dynamic_enhanced_node.shortName()
        self.parent = self.dynamic_enhanced_node.getParent()

        #   create and adapt nodes

        #   create offsets
        parent_offset = pm.createNode('transform', n='{}_calcInputPosition_pos'.format(self.node_name))
        offset = pm.createNode('transform', n='{}_calcOutputPosition_pos'.format(self.node_name))

        #   check for parent node
        pm.parent(parent_offset, self.dynamic_enhanced_node)
        if self.parent:
            pm.parent(parent_offset, self.parent)
            pm.matchTransform(parent_offset, self.parent)

        pm.parent(offset, parent_offset)
        pm.matchTransform(offset, parent_offset)

        pm.matchTransform(offset, self.dynamic_enhanced_node)
        pm.parent(self.dynamic_enhanced_node, offset)

        #   create calculation

        self.compose_offset = pm.createNode('composeMatrix', n=f'{self.node_name}_calc_cMtx')
        self.compose_offset.inputTranslateY.set(self.offset_aim)

        invert_offset = pm.createNode('math_Multiply', n=f'{self.node_name}_calc_fMul')

        invert_offset.input1.set(-1, lock=True)
        invert_offset.input2.set(self.offset_aim)

        aim_offset = pm.createNode('math_MultiplyMatrix', n=f'{self.node_name}_calc_mMtx')
        aim_offset.input1.set([1, 0, 0, 0,
                               0, 1, 0, 0,
                               0, 0, 1, 0,
                               0, self.offset_aim, 0, 1])

        aim_upvec = pm.createNode('math_MultiplyMatrix', n=f'{self.node_name}_calc_mMtx')
        aim_upvec.input1.set([1, 0, 0, 0,
                              0, 1, 0, 0,
                              0, 0, 1, 0,
                              0, 0, 90, 1],
                             lock=True)

        aim_position = pm.createNode('math_TranslationFromMatrix', n=f'{self.node_name}_calc_tMtx')

        self.spring_node = pm.createNode('mgear_springNode', n=f'{self.node_name}_calc_mMtx')
        for key, value in list(self.default_spring_vals.items()):
            self.spring_node.attr(key).set(value)

        spring_translation = pm.createNode('composeMatrix', n=f'{self.node_name}_calc_cMtx')

        for s in self.xyz_uppered:
            spring_translation.attr(f'inputRotate{s}').set(lock=True)
            spring_translation.attr(f'inputScale{s}').set(lock=True)
            spring_translation.attr(f'inputShear{s}').set(lock=True)

        aim_matrix = pm.createNode('aimMatrix', n=f'{self.node_name}_calc_aMtx')
        active_axes = (0, 1, 0)

        for turn, i in enumerate(active_axes):
            aim_matrix.attr(f'primaryInputAxis{self.xyz_uppered[turn]}').set(i, lock=True)

            aim_matrix.attr(f'primaryTargetVector{self.xyz_uppered[turn]}').set(i, lock=True)

        aim_matrix.primaryMode.set(1, lock=True)

        active_axes = (0, 0, 1)

        for turn, i in enumerate(active_axes):
            aim_matrix.attr(f'secondaryInputAxis{self.xyz_uppered[turn]}').set(i, lock=True)
            aim_matrix.attr(f'secondaryTargetVector{self.xyz_uppered[turn]}').set(i, lock=True)

        aim_matrix.secondaryMode.set(1, lock=True)

        #   create blend between rotation wiggle and translation wiggle
        self.blend_matrix = pm.createNode('blendMatrix', n=f'{self.node_name}_calc_bMtx')

        self.blend_matrix.target[0].translateWeight.set(1., lock=True)
        self.blend_matrix.target[0].rotateWeight.set(0., lock=True)
        self.blend_matrix.target[0].scaleWeight.set(0., lock=True)
        self.blend_matrix.target[0].shearWeight.set(0., lock=True)

        self.blend_matrix.target[0].weight.set(self.default_trans_contribution)

        invert_weight = pm.createNode('math_Multiply', n=f'{self.node_name}_calc_fMul')
        invert_weight.input1.set(-self.offset_aim)
        invert_weight.input2.set(self.default_trans_contribution)

        compose_inversion = pm.createNode('composeMatrix', n=f'{self.node_name}_calc_cMtx')
        compose_inversion.inputTranslateY.set(-(self.offset_aim * self.default_trans_contribution))

        self.recenter_matrix = pm.createNode('math_MultiplyMatrix', n=f'{self.node_name}_calc_mMtx')

        invert_matrix = pm.createNode('math_MultiplyMatrix', n=f'{self.node_name}_calc_mMtx')

        decompose_matrix = pm.createNode('decomposeMatrix', n=f'{self.node_name}_calc_dMtx')

        #   connect nodes
        self.compose_offset.outputMatrix.connect(aim_offset.input1)
        parent_offset.worldMatrix[0].connect(aim_offset.input2)

        aim_offset.output.connect(aim_position.input)
        aim_position.output.connect(self.spring_node.goal)

        self.spring_node.output.connect(spring_translation.inputTranslate)
        spring_translation.outputMatrix.connect(aim_matrix.primaryTargetMatrix)

        parent_offset.worldMatrix[0].connect(aim_upvec.input2)
        aim_upvec.output.connect(aim_matrix.secondaryTargetMatrix)

        parent_offset.worldMatrix[0].connect(aim_matrix.inputMatrix)

        spring_translation.outputMatrix.connect(self.blend_matrix.target[0].targetMatrix)
        aim_matrix.outputMatrix.connect(self.blend_matrix.inputMatrix)

        self.blend_matrix.outputMatrix.connect(self.recenter_matrix.input2)

        self.compose_offset.inputTranslateY.connect(invert_offset.input2)
        invert_offset.output.connect(invert_weight.input1)
        self.blend_matrix.target[0].weight.connect(invert_weight.input2)
        invert_weight.output.connect(compose_inversion.inputTranslateY)

        compose_inversion.outputMatrix.connect(self.recenter_matrix.input1)

        self.recenter_matrix.output.connect(invert_matrix.input1)
        parent_offset.worldInverseMatrix[0].connect(invert_matrix.input2)
        invert_matrix.output.connect(decompose_matrix.inputMatrix)

        for axis in self.xyz_uppered:
            decompose_matrix.attr(f'outputTranslate{axis}').connect(offset.attr(f'translate{axis}'))
            decompose_matrix.attr(f'outputRotate{axis}').connect(offset.attr(f'rotate{axis}'))
            decompose_matrix.attr(f'outputScale{axis}').connect(offset.attr(f'scale{axis}'))

        #   sort out connections that can be modified

        for key, value in list(self.default_spring_vals.items()):
            self.control_attrs[key] = (value, self.spring_node.attr(key))

        self.control_attrs['goalDistance'] = (self.offset_aim,
                                              self.compose_offset.inputTranslateY
                                              )

        self.control_attrs['translationContribution'] = (self.default_trans_contribution,
                                                         self.blend_matrix.target[0].weight
                                                         )

    def connect_to_rig(self, control_object=None):

        if not control_object:
            control_object = pm.selected()[0]

        if not control_object:
            raise ValueError

        if not self.control_attrs:
            raise ValueError

        #   add separator
        control_object.addAttr('dynamicJiggle',
                               at='enum',
                               enumName=ENUM_TOKEN_STATIC,
                               keyable=True,
                               )

        control_object.dynamicJiggle.set(lock=True)

        #   create and connect attrs based on control_attrs dict
        for key, value in list(self.control_attrs.items()):
            if key == 'time':
                attr_type = 'bool'
                control_object.addAttr(key,
                                       at=attr_type,
                                       dv=value[0],
                                       keyable=True,
                                       )
                control_object.attr(key).connect(value[1])

            elif key == 'goalDistance':
                attr_type = 'double'

                control_object.addAttr(key,
                                       at=attr_type,
                                       dv=value[0],
                                       keyable=True,
                                       )
                control_object.attr(key).connect(value[1])

            else:
                attr_type = 'double'

                control_object.addAttr(key,
                                       at=attr_type,
                                       dv=value[0],
                                       keyable=True,
                                       hxv=True,
                                       hnv=True,
                                       min=0,
                                       max=1
                                       )
                control_object.attr(key).connect(value[1])


class WheelRotation(object):
    """ test run
    jiggle = DynamicOffset()
    jiggle.build_calc_network()
    jiggle.connect_to_rig()
    """
    ROTATION_EXPRESSION = ["float $radius = AMOUNT;",
                           "//  positional vectors and scene operations",
                           "vector $wheel_old_vector = `xform -q -t -ws OLD_POSITION`;",
                           "vector $wheel_vector = `xform -q -t -ws POSITION`;",
                           "matchTransform -position DIRECTION POSITION;",
                           "xform -os -r -t 0 0 10 DIRECTION;",
                           "vector $forward_vector = `xform -q -t -ws DIRECTION`;",
                           "//  vector operations",
                           "vector $wheel_direction_vector = ($forward_vector - $wheel_vector);",
                           "vector $translate_vector = ($wheel_vector - $wheel_old_vector);",
                           "float $distance = mag($translate_vector);",
                           "float $dot_product = dotProduct($translate_vector, $wheel_direction_vector, 1);",
                           "//  apply calculation",
                           "RO.rotateRA = RO.rotateRA + (-1*(360*(($distance * $dot_product) / (-6.283 * $radius))));",
                           "//  change old position;",
                           "xform -t ($wheel_vector.x) ($wheel_vector.y) ($wheel_vector.z) OLD_POSITION;",
                           "//  reset frames;",
                           "if (frame == 1001){",
                           "RO.rotateRA = 0;"
                           "};"
                           ]

    ROTATION_EXPRESSION_FORMATTED = '\n'.join(ROTATION_EXPRESSION)

    def __init__(self,
                 diameter: Optional[float] = 1.0,
                 rotation_axis: Optional[str] = 'X',
                 wheel_objects=None,
                 circumference_objects=None,
                 ):

        self.setup_node = pm.PyNode('setup')
        self.wheel_objects = wheel_objects
        self.circumference_objects = circumference_objects
        self.wheel_node = None
        self.node_name = None
        self.parent = None

        self.steer_value = None

        self.radius = diameter

        self.rotation_axis = rotation_axis

        self.control_attrs = dict()

    def build_calc_network(self, nodes=None):
        if not nodes:
            nodes = self.wheel_objects

        if not nodes:
            nodes = pm.selected()

        if not nodes:
            raise ValueError

        for iterations, node in enumerate(nodes):

            self.wheel_node = node

            if self.radius is None:
                box_min = abs(float(self.wheel_node.getAttr('boundingBoxMinY')))
                box_max = float(self.wheel_node.getAttr('boundingBoxMaxY'))
                self.radius = (box_max + box_min)*2

            self.node_name = self.wheel_node.shortName()
            self.parent = self.wheel_node.getParent()

            #   create and adapt nodes

            #   create offsets
            parent_offset = pm.createNode('transform', n=f'{self.node_name}_calcInputPosition_pos')
            offset = pm.createNode('transform', n=f'{self.node_name}_calcOutputPosition_pos')

            #   check for parent node
            pm.parent(parent_offset, self.wheel_node)
            if self.parent:
                pm.parent(parent_offset, self.parent)
                pm.matchTransform(parent_offset, self.parent)

            pm.parent(offset, parent_offset)
            pm.matchTransform(offset, parent_offset)

            pm.matchTransform(offset, self.wheel_node)
            pm.parent(self.wheel_node, offset)

            #   create vector nodes
            #   basically the aim vector
            direction = pm.createNode('transform', n=f'{self.node_name}_calcDirection_pos')
            pm.parent(direction, self.circumference_objects[iterations])
            pm.matchTransform(direction, parent_offset)
            direction.translateZ.set(10)

            #   position to be aimed from
            position = pm.createNode('transform', n=f'{self.node_name}_calcPosition_pos')
            pm.parent(position, offset)
            pm.matchTransform(position, offset)

            #   old position
            old_position = pm.createNode('transform', n=f'{self.node_name}_calcOldPosition_pos')
            pm.parent(old_position, self.setup_node)
            pm.matchTransform(old_position, parent_offset)

            #   create tuples for exchanging parameters
            string_variables = (('AMOUNT', str(self.radius)),
                                ('OLD_POSITION', old_position.shortName()),
                                ('DIRECTION', direction.shortName()),
                                ('POSITION', position.shortName()),
                                ('RO', offset.shortName()),
                                ('RA', self.rotation_axis))

            #   localize expression
            expression_adapted = WheelRotation.ROTATION_EXPRESSION_FORMATTED

            #   insert variables into expression
            for r in string_variables:
                expression_adapted = expression_adapted.replace(r[0], r[1])

            #   create expression
            expression_node = pm.expression(n=f'{self.node_name}_expr', string=expression_adapted)

            #   share expression attributes
            self.control_attrs[expression_node.name()] = (0, expression_node.nodeState)

    def build_steering_setup(self, nodes=None):
        if not nodes:
            nodes = self.circumference_objects

        if not nodes:
            nodes = pm.selected()

        if not nodes:
            raise ValueError

        for iterations, node in enumerate(nodes):
            self.wheel_node = node

            if self.radius is None:
                box_min = abs(float(self.wheel_node.getAttr('boundingBoxMinY')))
                box_max = float(self.wheel_node.getAttr('boundingBoxMaxY'))
                self.radius = box_max + box_min

            self.node_name = self.wheel_node.shortName()
            self.parent = self.wheel_node.getParent()

            if '_L_' in self.node_name:
                remap_min, remap_max = 0, 1.3

            else:
                remap_min, remap_max = -.3, 1

            #   create and adapt nodes

            #   create offsets
            parent_offset = pm.createNode('transform', n=f'{self.node_name}_calcInputPosition_pos')
            offset = pm.createNode('transform', n=f'{self.node_name}_calcOutputPosition_pos')

            #   check for parent node
            pm.parent(parent_offset, self.wheel_node)
            if self.parent:
                pm.parent(parent_offset, self.parent)
                pm.matchTransform(parent_offset, self.parent)

            pm.parent(offset, parent_offset)
            pm.matchTransform(offset, parent_offset)

            pm.matchTransform(offset, self.wheel_node)
            pm.parent(self.wheel_node, offset)

            steer_remap = pm.createNode('remapValue')
            steer_remap.inputMin.set(-10, lock=True)
            steer_remap.inputMax.set(10, lock=True)
            steer_remap.value[2].value_FloatValue.set(0.5, lock=True)
            steer_remap.value[2].value_Position.set(0.5, lock=True)
            steer_remap.value[2].value_Interp.set(1, lock=True)

            steer_remap.value[0].value_Interp.set(1, lock=True)
            steer_remap.value[0].value_FloatValue.set(remap_min, lock=True)
            steer_remap.value[0].value_Position.set(0, lock=True)

            steer_remap.value[1].value_Interp.set(1, lock=True)
            steer_remap.value[1].value_FloatValue.set(remap_max, lock=True)
            steer_remap.value[1].value_Position.set(1, lock=True)

            steer_remap.outputMin.set(-70, lock=True)
            steer_remap.outputMax.set(70, lock=True)

            self.steer_value = steer_remap.inputValue
            steer_remap.outValue.connect(offset.rotateY)

            #   add rotational values to
            wheel_spin_master = pm.listRelatives(self.wheel_node, shapes=False, children=True, type='transform')[-1]

            #   create offsets
            parent_spin_offset = pm.createNode('transform',
                                               n='{}_calcInputPosition_pos'.format(wheel_spin_master.shortName())
                                               )

            offset_spin = pm.createNode('transform',
                                        n='{}_calcOutputPosition_pos'.format(wheel_spin_master.shortName())
                                        )

            #   check for parent node
            pm.parent(parent_spin_offset, self.wheel_node)
            pm.matchTransform(parent_spin_offset, self.wheel_node)

            pm.parent(offset_spin, parent_spin_offset)
            pm.matchTransform(offset_spin, parent_spin_offset)

            pm.matchTransform(offset_spin, wheel_spin_master)
            pm.parent(wheel_spin_master, offset_spin)

            point_1 = self.wheel_objects[iterations].getTranslation(space="world")

            point_2 = self.circumference_objects[iterations].getTranslation(space="world")

            distance = (point_2 - point_1).length()

            steering_radius = pm.createNode('math_Multiply')
            steering_radius.input1.set(distance)
            steering_radius.input2.set(6.283, lock=True)

            fraction_divide = pm.createNode('math_Divide')
            offset.rotateY.connect(fraction_divide.input1)
            fraction_divide.input2.set(360, lock=True)

            steering_distance = pm.createNode('math_Multiply')
            steering_radius.output.connect(steering_distance.input1)
            fraction_divide.output.connect(steering_distance.input2)

            wheel_radius = pm.createNode('math_Multiply')
            wheel_radius.input1.set(self.radius/2.0, lock=True)
            wheel_radius.input2.set(6.283, lock=True)

            steering_circumference = pm.createNode('math_Divide')
            steering_distance.output.connect(steering_circumference.input1)
            wheel_radius.output.connect(steering_circumference.input2)

            steering_amount = pm.createNode('math_Multiply')
            steering_circumference.output.connect(steering_amount.input1)
            steering_amount.input2.set(-360, lock=True)

            if '_R_' in offset_spin.shortName():

                steering_out = pm.createNode('math_MultiplyByInt')
                steering_amount.output.connect(steering_out.input1)
                steering_out.input2.set(-1, lock=True)
                steering_amount = steering_out

            steering_amount.output.connect(offset_spin.rotateX)

            #   add controls
            self.control_attrs[f'{self.node_name}Steering'] = (0, self.steer_value)

        #   steering wheel automated
        steering_node = pm.PyNode('steeringWheel_C_0_ctrl')
        steering_node_name = str(steering_node.shortName())
        steering_node_parent = steering_node.getParent()

        #   create offsets
        parent_steering_wheel_offset = pm.createNode('transform',
                                                     n=f'{steering_node_name}_calcInputPosition_pos',
                                                     )

        steering_wheel_offset = pm.createNode('transform',
                                              n=f'{steering_node_name}_calcOutputPosition_pos',
                                              )

        #   check for parent node
        pm.parent(parent_steering_wheel_offset, steering_node)
        if self.parent:
            pm.parent(parent_steering_wheel_offset, steering_node_parent)
            pm.matchTransform(parent_steering_wheel_offset, steering_node_parent)

        pm.parent(steering_wheel_offset, parent_steering_wheel_offset)
        pm.matchTransform(steering_wheel_offset, parent_steering_wheel_offset)

        pm.matchTransform(steering_wheel_offset, steering_node)
        pm.parent(steering_node, steering_wheel_offset)

        steering_wheel_mult = pm.createNode('math_Multiply')
        steering_wheel_mult.output.connect(steering_wheel_offset.rotateX)

        self.control_attrs['steeringWheel'] = (0, steering_wheel_mult)

    def connect_to_rig(self, control_object=None):
        if not control_object:
            control_object = pm.selected()[0]

        if not control_object:
            raise ValueError

        if not self.control_attrs:
            raise ValueError

        #   add separator
        control_object.addAttr('wheelRotations',
                               at='enum',
                               enumName=ENUM_TOKEN_STATIC,
                               keyable=True,
                               )

        control_object.wheelRotations.set(lock=True)

        steer_attrs = [x.split('_')[1] for x in list(self.control_attrs.keys()) if 'Spin' in x]

        most_used = max(steer_attrs, key=steer_attrs.count)
        steer_count = steer_attrs.count(most_used)

        for x in range(steer_count):
            control_object.addAttr(f'wheelSteer_{x}',
                                   at='double',
                                   dv=0,
                                   keyable=True,
                                   hxv=True,
                                   hnv=True,
                                   min=-10,
                                   max=10
                                   )

        #   create and connect attrs based on control_attrs dict
        for key, value in list(self.control_attrs.items()):
            if '_expr' in key:
                attr_new_name = '_'.join(key.split('_')[0:3])
                control_object.addAttr(attr_new_name,
                                       at='enum',
                                       dv=value[0],
                                       keyable=True,
                                       enumName='off=1:on=0'
                                       )

                control_object.attr(attr_new_name).connect(value[1])
            elif 'steeringWheel' in key:
                control_object.addAttr(key,
                                       at='double',
                                       dv=value[0],
                                       keyable=True,
                                       )

                control_object.attr(key).connect(value[1].input1)
                control_object.wheelSteer_0.connect(value[1].input2)
            else:
                steer_index = key.split('_')[2]
                control_object.attr(f'wheelSteer_{steer_index}').connect(value[1])


class CollisionSetup(object):
    def __init__(self, diameter=1.0, deformation_objects=None, wheel_objects=None):
        self.setup_node = pm.PyNode('setup')

        self.deformation_objects = deformation_objects
        self.wheel_objects = wheel_objects

        self.wheel_node = None
        self.node_name = None
        self.parent = None
        self.diameter = diameter

        self.sections = 8
        self.width = 0.2
        self.joint_amount = 80
        self.uv_divisions = 1.0 / self.joint_amount - 1

        self.collision_joints = list()
        self.squash = None
        self.trans = None

        self.control_attrs = dict()

    def build_collision_setup(self, mesh_node=None, transforms_in=None):

        if not transforms_in:
            self.deformation_objects = self.deformation_objects

        if not self.deformation_objects:
            self.deformation_objects = pm.selected()

        if not self.deformation_objects:
            raise ValueError

        if not mesh_node:
            transform_node = pm.polyPlane(n='proxyPlane',
                                          sx=100,
                                          sy=100,
                                          w=2000,
                                          h=2000,
                                          constructionHistory=False,
                                          )[0]

            mesh_node = transform_node.getShape()
            pm.parent(transform_node, self.setup_node)

        self.sections = old_div(len(self.deformation_objects), len(self.wheel_objects))

        for it, trnsf in enumerate(self.deformation_objects):
            self.wheel_node = trnsf

            self.node_name = self.wheel_node.shortName()
            self.parent = self.wheel_node.getParent()

            #   create offsets
            parent_offset = pm.createNode('transform',
                                          n=f'{self.node_name}_calcInputPosition_pos',
                                          )

            offset = pm.createNode('transform',
                                   n=f'{self.node_name}_calcOutputPosition_pos',
                                   )

            #   check for parent node
            pm.parent(parent_offset, self.wheel_node)
            if self.parent:
                pm.parent(parent_offset, self.parent)
                pm.matchTransform(parent_offset, self.parent)

            pm.parent(offset, parent_offset)
            pm.matchTransform(offset, parent_offset)

            pm.matchTransform(offset, self.wheel_node)
            pm.parent(self.wheel_node, offset)

            #   getting the translate from the transform WM

            translate_from_mat = pm.createNode("math_TranslationFromMatrix",
                                               n=f'{self.node_name}_calcCollision_tfmx',
                                               )

            pm.connectAttr(f"{parent_offset}.worldMatrix[0]",
                           f"{translate_from_mat}.input")

            #   getting the closest point on mesh
            cls_point = pm.createNode("closestPointOnMesh",
                                      n=f'{self.node_name}_calcCollision_cpom',
                                      )

            pm.connectAttr(f"{mesh_node}.worldMatrix[0]",
                           f"{cls_point}.inputMatrix",
                           )

            pm.connectAttr(f"{mesh_node}.outMesh",
                           f"{cls_point}.inMesh",
                           )

            #   connect the locator translation to the cls point
            pm.connectAttr(f"{translate_from_mat}.output",
                           f"{cls_point}.inPosition",
                           )

            #   finding the vector from the transf to the nearest point
            diff_vector = pm.createNode("math_SubtractVector",
                                        n=f'{self.node_name}_calcCollision_vsub',
                                        )

            pm.connectAttr("{}.output".format(translate_from_mat),
                           "{}.input1".format(diff_vector))
            pm.connectAttr("{}.position".format(cls_point),
                           "{}.input2".format(diff_vector))

            #   normalizing the diff_vec
            normal_vec = pm.createNode("math_NormalizeVector", n='{}_calcCollision_norm'.format(self.node_name))

            pm.connectAttr("{}.output".format(diff_vector),
                           "{}.input".format(normal_vec))

            #   dot product between diff vector and geo normal
            dot_node = pm.createNode("math_DotProduct", n='{}_calcCollision_dot'.format(self.node_name))
            pm.connectAttr("{}.normal".format(cls_point),
                           "{}.input1".format(dot_node))
            pm.connectAttr("{}.output".format(normal_vec),
                           "{}.input2".format(dot_node))

            #   checking the dot product and generating bool if less then zero
            compare = pm.createNode("math_Compare", n='{}_calcCollision_compare'.format(self.node_name))
            pm.setAttr("{}.operation".format(compare), 1)
            pm.connectAttr("{}.output".format(dot_node),
                           "{}.input1".format(compare))

            #   feeding the bool in a selection
            selector = pm.createNode("math_SelectVector", n='{}_calcCollision_select'.format(self.node_name))
            pm.connectAttr("{}.output".format(compare),
                           "{}.condition".format(selector))
            pm.connectAttr("{}.output".format(translate_from_mat),
                           "{}.input1".format(selector))
            pm.connectAttr("{}.position".format(cls_point),
                           "{}.input2".format(selector))

            localization = pm.createNode('math_SubtractVector', n='{}_calcCollision_negateWorld'.format(self.node_name))
            pm.connectAttr("{}.output".format(translate_from_mat),
                           "{}.input1".format(localization))
            pm.connectAttr("{}.output".format(selector),
                           "{}.input2".format(localization))

            invert = pm.createNode('math_MultiplyByInt', n='{}_calcCollision_invert'.format(self.node_name))
            invert.input2.set(-1, lock=True)
            pm.connectAttr("{}.outputY".format(localization),
                           "{}.input1".format(invert))

            self.squash = pm.createNode('math_Multiply', n='{}_calcCollision_squashMult'.format(self.node_name))
            pm.connectAttr("{}.output".format(invert),
                           "{}.input1".format(self.squash))
            self.squash.input2.set(1)

            scale_add = pm.createNode('math_Add', n='{}_calcCollision_additive'.format(self.node_name))
            pm.connectAttr("{}.output".format(self.squash),
                           "{}.input1".format(scale_add))
            scale_add.input2.set(1, lock=True)

            self.trans = pm.createNode('math_Multiply', n='{}_calcCollision_transMult'.format(self.node_name))
            pm.connectAttr("{}.outputY".format(localization),
                           "{}.input1".format(self.trans))
            self.trans.input2.set(1)

            #   generating an output for the transform

            pm.connectAttr("{}.output".format(self.trans),
                           "{}.translateY".format(offset))

            pm.connectAttr("{}.output".format(scale_add),
                           "{}.scaleX".format(offset))

            pm.connectAttr("{}.output".format(scale_add),
                           "{}.scaleZ".format(offset))

            self.control_attrs['{}Squash'.format(self.node_name)] = (0, self.squash.input2)
            self.control_attrs['{}Trans'.format(self.node_name)] = (0, self.trans.input2)

    def build_deformation_setup(self, nodes=None):
        if not nodes:
            nodes = self.wheel_objects

        if not nodes:
            nodes = pm.selected()

        if not nodes:
            raise ValueError

        decomposed_control_names = [x.name() for x in self.deformation_objects]

        recomposed_joint_names = ['*_bnd_wheelDeformation_*_jnt'.format(x.split('_')[1])
                                  for x in decomposed_control_names
                                  ]

        joints_of_skin = pm.ls(recomposed_joint_names)

        deformation_setup_node = pm.createNode('transform', n='wheels_deformation_GRP')
        deformation_setup_node.inheritsTransform.set(False, lock=True)
        pm.parent(deformation_setup_node, self.setup_node)

        for iterations, node in enumerate(nodes):
            self.wheel_node = node

            if self.diameter is None:
                box_min = abs(float(self.wheel_node.getAttr('boundingBoxMinY')))
                box_max = float(self.wheel_node.getAttr('boundingBoxMaxY'))
                self.diameter = (box_max + box_min) * 0.95

            self.node_name = self.wheel_node.shortName()
            self.parent = self.wheel_node.getParent()

            wheel_proxy = pm.cylinder(name='{}_calcWheelProxy_geo'.format(self.node_name),
                                      sections=self.sections,
                                      heightRatio=self.width,
                                      axis=(1, 0, 0),
                                      radius=self.diameter / 2.0,
                                      constructionHistory=False)[0]

            pm.matchTransform(wheel_proxy, self.wheel_node)
            wheel_proxy.rotateX.set(67.5)
            pm.parent(wheel_proxy, deformation_setup_node)
            pm.makeIdentity(wheel_proxy, apply=True)

            #   skin geometry
            skin_name = wheel_proxy.name().replace('_geo', 'skC')
            specific_cluster = joints_of_skin[iterations*self.sections:(iterations+1)*self.sections]

            wheel_proxy_skin = pm.skinCluster(specific_cluster,
                                              wheel_proxy,
                                              n=skin_name,
                                              maximumInfluences=self.sections,

                                              )

            for i in range(self.sections):
                pm.skinPercent(wheel_proxy_skin,
                               wheel_proxy.cv[0:3][i],
                               transformValue=[(specific_cluster[i], 1)]
                               )

            uv_pinning = pm.createNode('uvPin', n='{}_calcWheelProxy_uvPn'.format(self.node_name))
            wheel_proxy.getShape().worldSpace[0].connect(uv_pinning.deformedGeometry)

            wheel_setup_node = pm.createNode('transform', n='{}_deformation_GRP'.format(self.node_name))
            wheel_setup_node.inheritsTransform.set(False, lock=True)
            pm.parent(wheel_setup_node, deformation_setup_node)

            #   create deformation joints
            side = ('Inner', 'Outter')
            count_joints = 0
            for value, s in enumerate(side):
                group_node = pm.createNode('transform', n='{}{}_deformation_GRP'.format(self.node_name, s))
                group_node.inheritsTransform.set(False, lock=True)
                pm.parent(group_node, wheel_setup_node)

                count_position = 0
                for x in range(0, self.joint_amount + 1):
                    uv_pinning.attr('coordinate[{}].coordinateV'.format(count_joints)).set(count_position, lock=True)
                    uv_pinning.attr('coordinate[{}].coordinateU'.format(count_joints)).set(value, lock=True)

                    pm.select(clear=True)
                    deform_joint = pm.joint(n='{}_calcDeform{}_{}_jnt'.format(self.node_name, s, str(x)))
                    pm.connectAttr(uv_pinning.attr('outputMatrix[{}]'.format(count_joints)),
                                   deform_joint.offsetParentMatrix)
                    self.collision_joints.append(deform_joint)
                    pm.select(clear=True)
                    pm.parent(deform_joint, group_node)

                    count_position += self.uv_divisions
                    count_joints += 1

    def connect_to_rig(self, control_object=None):
        if not control_object:
            control_object = pm.selected()[0]

        if not control_object:
            raise ValueError

        if not self.control_attrs:
            raise ValueError

        #   add separator
        control_object.addAttr('automaticDeformation',
                               at='enum',
                               enumName=ENUM_TOKEN_STATIC,
                               keyable=True
                               )

        control_object.automaticDeformation.set(lock=True)

        control_object.addAttr('wheelSquash',
                               at='double',
                               dv=0,
                               keyable=True,
                               hxv=True,
                               hnv=True,
                               min=-10,
                               max=10
                               )

        control_object.addAttr('wheelTrans',
                               at='double',
                               dv=0,
                               keyable=True,
                               hxv=True,
                               hnv=True,
                               min=0,
                               max=10
                               )

        #   create and connect attrs based on control_attrs dict
        for key, value in list(self.control_attrs.items()):
            if key == 'deformingMesh':
                attr_type = 'mesh'
                control_object.addAttr(key,
                                       dt=attr_type,
                                       dv=value[0],
                                       keyable=True
                                       )

                control_object.attr(key).connect(value[1])

            elif 'Squash' in key:
                control_object.wheelSquash.connect(value[1])

            elif 'Trans' in key:
                control_object.wheelTrans.connect(value[1])

            else:
                attr_type = 'double'

                control_object.addAttr(key,
                                       at=attr_type,
                                       dv=value[0],
                                       keyable=True
                                       )

                control_object.attr(key).connect(value[1])


def adapt_controls():
    axis = ['X', 'Y', 'Z']

    #   Organise top node
    asset_geo_roots = [x for x in pm.ls(transforms=True)
                       if pm.objExists('{}.PXM_asset_geo_root'.format(x))
                       ]

    if not asset_geo_roots or len(asset_geo_roots) > 1:
        raise ValueError

    asset_geo_root = asset_geo_roots[0]
    asset_name = asset_geo_root.split('_')[-2]
    asset_type = asset_geo_root.split('_')[0].split(':')[-1]

    rig_group = pm.PyNode('rig_root_grp')
    global_control = pm.PyNode('global_0_ctrl')
    vis_control = pm.PyNode('visibility_C_0_ctrl')

    asset_group = pm.group(n='{}_{}_rig'.format(asset_type, asset_name),
                           em=True
                           )

    pm.parent(rig_group, asset_group)
    pm.parent(asset_geo_root, asset_group)

    # Global ctrl main scale attribute and lock & hide scale channels
    global_control.addAttr('main_scale',
                           at='double',
                           min=0.001,
                           hnv=True,
                           dv=1,
                           k=True)

    for x in axis:
        global_control.main_scale.connect(global_control.attr('scale{}'.format(x)))
        global_control.attr('scale{}'.format(x)).set(lock=True,
                                                     k=False,
                                                     channelBox=False)

    # Connect attributes for geo, ctl and joint visibility
    for x in axis:
        vis_control.attr('translate{}'.format(x)).set(lock=True, keyable=False)
        vis_control.attr('rotate{}'.format(x)).set(lock=True, keyable=False)
        vis_control.attr('scale{}'.format(x)).set(lock=True, keyable=False)
    vis_control.rotateOrder.set(lock=True, keyable=False)

    vis_control.addAttr('model_display_type', at='enum', dv=2, enumName='normal:template:reference')
    vis_control.model_display_type.set(cb=True)

    vis_control.addAttr('mgear_jnt_vis', at='bool', keyable=False)
    vis_control.mgear_jnt_vis.set(False, cb=True)
    vis_control.addAttr('mgear_ctl_vis', at='bool', keyable=False)
    vis_control.mgear_ctl_vis.set(True, cb=True)
    vis_control.addAttr('mgear_ctl_vis_on_playback', at='bool', keyable=False)
    vis_control.mgear_ctl_vis_on_playback.set(False, cb=True)
    vis_control.addAttr('mgear_ctl_x_ray', at='bool', keyable=False)
    vis_control.mgear_ctl_x_ray.set(False, cb=True)

    vis_control.mgear_jnt_vis.connect(rig_group.jnt_vis)
    vis_control.mgear_ctl_vis.connect(rig_group.ctl_vis)
    vis_control.mgear_ctl_vis_on_playback.connect(rig_group.ctl_vis_on_playback)
    vis_control.mgear_ctl_x_ray.connect(rig_group.ctl_x_ray)

    asset_geo_root.overrideEnabled.set(True)
    vis_control.model_display_type.connect(asset_geo_root.drawOverride.overrideDisplayType)

    # connect geos
    complexity_groups = asset_geo_root.getChildren()
    naming_decomposition = dict()

    complexity_levels = [x.getChildren()[0] for x in complexity_groups]
    for i in complexity_levels:
        geometry_groups = [(x.shortName().split(':')[-1], x) for x in i.getChildren()]
        naming_decomposition[i.shortName().split(':')[-1]] = geometry_groups
    for key, value in list(naming_decomposition.items()):
        vis_control.addAttr(key,
                            at='enum',
                            enumName=ENUM_TOKEN_STATIC,
                            keyable=False
                            )

        vis_control.attr(key).set(lock=True, cb=True)

        for v in value:
            vis_control.addAttr(v[0],
                                at='bool',
                                dv=True,
                                keyable=False
                                )

            vis_control.attr(v[0]).set(True, cb=True)
            vis_control.attr(v[0]).connect(v[1].visibility)

    # Rename sets
    pm.rename('mgear_rig_grp_sets_grp', 'pxm_rig_root_set')
    pm.rename('mgear_rig_grp_componentsRoots_grp', 'components_root_set')
    pm.rename('mgear_rig_grp_controllers_grp', 'controllers_set')
    pm.rename('mgear_rig_grp_deformers_grp', 'deformers_set')

    pm.select(cl=True)
    pm.viewFit()


class CustomShifterStep(cstp.customShifterMainStep):

    CHASSIS_COMPONENT, DEFORM_COMPONENT, SPIN_COMPONENT, ROTATION_COMPONENT, MOVEMENT_COMPONENT = 'chassis', \
                                                                                                  'wheelDeformation_', \
                                                                                                  'wheelSpin_', \
                                                                                                  'wheelRot_', \
                                                                                                  'movementHost_'

    def __init__(self):
        self.name = "pxo_car_setup"
        self.pxo_rigging_kit = None

    def run(self, stepDict):

        #   chassis controls
        chassis_components_keys = [
            comp
            for comp in list(stepDict["mgearRun"].components.keys())
            if self.CHASSIS_COMPONENT in comp
        ]
        #   Get the chassis root.
        if chassis_components_keys:
            #   get leg components
            chassis = [stepDict["mgearRun"].components.get(x)
                       for x
                       in chassis_components_keys
                       ]

            #   get component controls
            if chassis:
                chassis_ctrls = [chassis_grp.groups.get('controllers')[0]
                                 for chassis_grp
                                 in chassis
                                 ]

                _LOGGER.info('car jiggle info gathered')

                jiggle = DynamicOffset()

                chassis_ctrls_ = sorted([pymaya_to_pymel(pymaya_nd)
                                         for pymaya_nd
                                         in chassis_ctrls
                                         ]
                                        )

                jiggle.build_calc_network(chassis_ctrls_[1])

                jiggle.connect_to_rig(chassis_ctrls_[0])

                _LOGGER.info('jiggle setup finished')

        #   sort out movementHost controls
        movement_components_keys = [comp for comp in list(stepDict["mgearRun"].components.keys())
                                    if self.MOVEMENT_COMPONENT in comp
                                    ]

        #   Get the leg component root.
        movement_components = list()
        movement_ctrls_ = list()

        if movement_components_keys:
            movement_components = [stepDict["mgearRun"].components.get(x)
                                   for x in movement_components_keys
                                   ]

        if movement_components:
            movement_ctrls_ = [x.groups.get('controllers')[0]
                              for x in movement_components
                              ]

            if movement_ctrls_:
                movement_ctrls = pymaya_to_pymel(movement_ctrls_[0])
                _LOGGER.info('car movement host info gathered')

        #   sort out rotate controls
        rotate_components_keys = [comp for comp in list(stepDict["mgearRun"].components.keys())
                                  if self.ROTATION_COMPONENT in comp
                                  ]

        #   Get the leg component root.
        rotate_components = list()
        rotate_sorted = list()

        if rotate_components_keys:
            rotate_components = [stepDict["mgearRun"].components.get(x)
                                 for x in rotate_components_keys]

        if rotate_components:
            rotate_ctrls_ = [x.groups.get('controllers')[0]
                            for x in rotate_components]

            rotate_ctrls = [pymaya_to_pymel(pymaya_nd) for pymaya_nd in rotate_ctrls_]

            #   get the indexes for sorting
            rotate_indices = [int(x.index)
                              for x in rotate_components]

            #   get the sides for sorting
            rotate_sides = [x.side
                            for x in rotate_components]

            #   combine the lists and sort
            rotate_controls_sorted = list(zip(rotate_sides, rotate_indices, rotate_ctrls))
            rotate_controls_sorted.sort()

            #   create a list of tuples out of the sort
            rotate_sorted = [x for z, y, x in rotate_controls_sorted]
            _LOGGER.info('wheel rotate info gathered')

        #   sort out spin controls
        spin_components_keys = [comp for comp in list(stepDict["mgearRun"].components.keys())
                                if self.SPIN_COMPONENT in comp
                                ]

        #   Get the leg component root.
        spin_components = list()
        spin_sorted = list()
        if spin_components_keys:
            spin_components = [stepDict["mgearRun"].components.get(x)
                               for x in spin_components_keys
                               ]

        if spin_components:
            spin_ctrls_ = [x.groups.get('controllers')[0]
                          for x in spin_components]

            spin_ctrls = [pymaya_to_pymel(pymaya_nd) for pymaya_nd in spin_ctrls_]

            #   get the indexes for sorting
            spin_indices = [int(x.index)
                            for x in spin_components]

            #   get the sides for sorting
            spin_sides = [x.side
                          for x in spin_components]

            #   combine the lists and sort
            spin_controls_sorted = list(zip(spin_sides, spin_indices, spin_ctrls))
            spin_controls_sorted.sort()

            #   create a list of tuples out of the sort
            spin_sorted = [x for z, y, x in spin_controls_sorted]
            _LOGGER.info('wheel spin info gathered')

        #   wheel deformation
        wheel_deform_component_keys = [comp for comp in list(stepDict["mgearRun"].components.keys())
                                       if self.DEFORM_COMPONENT in comp
                                       ]

        #   Get the leg component root.
        wheel_deforms_sorted = list()
        deform_components = list()
        if wheel_deform_component_keys:
            #   get leg components
            deform_components = [stepDict["mgearRun"].components.get(x)
                                 for x in wheel_deform_component_keys]

            #   get component controls
            deform_ctrls = [x.groups.get('controllers')[0]
                            for x in deform_components]

            #   get the indexes for sorting
            deform_indices = [int(x.index)
                              for x in deform_components]

            #   get the sides for sorting
            deform_sides = [x.side
                            for x in deform_components]

            #   combine the lists and sort
            deform_controls_sorted = list(zip(deform_sides,
                                              deform_indices,
                                              deform_ctrls
                                              )
                                          )

            deform_controls_sorted.sort()

            #   create a list of tuples out of the sort
            wheel_deforms_sorted = [x for z, y, x in deform_controls_sorted]

            deforms_left, deforms_right = split_list(wheel_deforms_sorted)

            deforms_left_front, deforms_left_back = split_list(deforms_left)
            deforms_right_front, deforms_right_back = split_list(deforms_right)

            _LOGGER.info('wheel deform info gathered')

        #   add functions to wheels
        if rotate_sorted and spin_sorted and movement_ctrls:

            wheel_rotations = WheelRotation(diameter=None,
                                            circumference_objects=rotate_sorted,
                                            wheel_objects=spin_sorted
                                            )

            wheel_rotations.build_steering_setup()
            wheel_rotations.build_calc_network()
            wheel_rotations.connect_to_rig(movement_ctrls)

        if wheel_deforms_sorted and spin_sorted and movement_ctrls:
            #   add dynamic squash
            fake_collision = CollisionSetup(diameter=None,
                                            deformation_objects=wheel_deforms_sorted,
                                            wheel_objects=spin_sorted
                                            )

            fake_collision.build_collision_setup()
            fake_collision.build_deformation_setup()
            fake_collision.connect_to_rig(movement_ctrls)

        _LOGGER.info('rig build finished')
