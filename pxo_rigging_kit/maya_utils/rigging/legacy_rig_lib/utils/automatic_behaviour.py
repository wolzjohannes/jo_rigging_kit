from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
# mgear / automated behaviours
# www.pixomondo.com
# Date: 26 / 07 / 2022
# Artist: Christof Puehringer / Junior Rigging TD

#   external libraries
from future import standard_library
standard_library.install_aliases()
from builtins import zip
from builtins import str
from builtins import range
import pymel.core as pm
import logging

logging.basicConfig(level=logging)
_LOGGER = logging.getLogger(__name__ + ".py")

'''
the data for attrs should be 
{'name':'attr', 'speed':int, 'strength': int, 'offset':int, 'low_bound': int, 'high_bound':int}

'''


SINE_TOKEN_STATIC = 'sin'
ENUM_TOKEN_STATIC = '########'

DEFAULT_ATTR_INPUT = {'name': 'default_attr',
                      'speed': 1,
                      'strength': 1,
                      'offset': 0,
                      'shift': 0,
                      'low_bound': 0,
                      'high_bound': 1
                      }

TRANSFORM_EXCEPTIONS = ('translateX', 'translateY', 'translateZ',
                        'rotateX', 'rotateY', 'rotateZ',
                        'scaleX', 'scaleY', 'scaleZ'
                        )

TIME_NODE = pm.PyNode('time1')


def add_sine(input_node,
             input_attrs,
             host=None,
             frame_rate=24
             ):
    """ adds a sine network to offset groups above input_node

    Args:
        input_node(str/PyNode):
        input_attrs(list->dicts):[{'name':'attr',
                                   'speed':float,
                                   'strength': float,
                                   'offset':float,
                                   'low_bound': float,
                                   'high_bound':float}, ...]
        frame_rate(int): 24
        host(host):
    """
    #   get current selection
    sel = pm.selected()

    #   set up input and output nodes
    '''
        if isinstance(input_node, str):
        input_node = pm.PyNode(input_node)

    node = input_node

    node_name = node.shortName()
    parent = node.getParent()

    #   create offsets
    parent_offset = pm.createNode('transform',
                                  n='{}_calcInputPosition_pos'.format(node_name),
                                  ss=True
                                  )

    calc_output = pm.createNode('transform',
                                n='{}_calcOutputPosition_pos'.format(node_name),
                                ss=True
                                )

    #   check for parent node
    pm.parent(parent_offset, node)

    if parent:
        pm.parent(parent_offset, parent)
        pm.matchTransform(parent_offset, parent)

    pm.parent(calc_output, parent_offset)
    pm.matchTransform(calc_output, parent_offset)

    pm.matchTransform(calc_output, node)
    pm.parent(node, calc_output)
    {'node': node, 'parent': parent, 'parent_offset': parent_offset, 'calc_output': calc_output}
    '''

    baseline_prep = create_offsets(input_node)
    node, parent, parent_offset, calc_output = baseline_prep['node'], \
                                               baseline_prep['parent'], \
                                               baseline_prep['parent_offset'], \
                                               baseline_prep['calc_output']

    node_name = node.shortName()

    #   check for attrs
    if isinstance(input_attrs, str):
        DEFAULT_ATTR_INPUT['name'] = input_attrs
        attrs = [DEFAULT_ATTR_INPUT]

    elif isinstance(input_attrs, dict):
        attrs = [input_attrs]

    elif isinstance(input_attrs, list):
        attrs = input_attrs

    else:
        raise ValueError('the input is incorrect')

    #   check for input control
    if not host:
        if sel:
            host = sel[0]
        else:
            host = parent_offset

    else:
        if isinstance(host, str):
            host = pm.PyNode(host)

        host = host

    #    inputCalcNodeModification
    offset_attrs = list()
    envelope_attrs = list()
    auto_switch_attrs = list()
    speed_attrs = list()
    time_attrs = list()

    attribute_name = '_'.join(node_name.split('_')[0:-1])
    progress = '{}_{}ManualProgress'.format(attribute_name, SINE_TOKEN_STATIC)
    envelop = '{}_{}Envelope'.format(attribute_name, SINE_TOKEN_STATIC)
    auto_switch = '{}_{}TimeProgress'.format(attribute_name, SINE_TOKEN_STATIC)
    controls = '{}_{}Controls'.format(attribute_name, SINE_TOKEN_STATIC)

    host.addAttr(controls,
                 at='enum',
                 enumName=ENUM_TOKEN_STATIC,
                 keyable=True
                 )
    host.attr(controls).set(lock=True)

    host.addAttr(envelop,
                 at='double',
                 defaultValue=0,
                 min=0,
                 hasMinValue=True,
                 max=1,
                 hasMaxValue=True,
                 keyable=True
                 )

    host.addAttr(progress,
                 at='doubleAngle',
                 keyable=True
                 )
    host.addAttr(auto_switch,
                 at='enum',
                 enumName='disabled:enabled',
                 keyable=True,
                 defaultValue=0
                 )

    #   time attributes
    time_mult = pm.createNode('math_Multiply',
                              n='{}_{}FrameRateAdjust_mlA'.format(SINE_TOKEN_STATIC, attribute_name)
                              )
    time_mult.isHistoricallyInteresting.set(False)
    time_mult.input2.set(.25, lock=True)
    TIME_NODE.outTime.connect(time_mult.input1)

    for attr in attrs:
        options = '{}_{}_{}Options'.format(attribute_name, attr['name'], SINE_TOKEN_STATIC)
        speed = '{}_{}_{}Speed'.format(attribute_name, attr['name'], SINE_TOKEN_STATIC)
        strength = '{}_{}_{}Strength'.format(attribute_name, attr['name'], SINE_TOKEN_STATIC)
        offset = '{}_{}_{}Offset'.format(attribute_name, attr['name'], SINE_TOKEN_STATIC)
        shift = '{}_{}_{}Shift'.format(attribute_name, attr['name'], SINE_TOKEN_STATIC)
        name = '{}_{}_{}Attr'.format(attribute_name, attr['name'], SINE_TOKEN_STATIC)

        #   check for this, if even needed maybe
        low_bound = '{}_{}_{}Lowbound'.format(attribute_name, attr['name'], SINE_TOKEN_STATIC)
        high_bound = '{}_{}_{}Highbound'.format(attribute_name, attr['name'], SINE_TOKEN_STATIC)

        sine_name = '{}_{}_{}Output'.format(attribute_name, attr['name'], SINE_TOKEN_STATIC)

        host.addAttr(options,
                     at='enum',
                     enumName=ENUM_TOKEN_STATIC,
                     keyable=True
                     )
        host.attr(options).set(lock=True)

        #   check for the output if it actually is a transform ;)
        if not attr['name'] in TRANSFORM_EXCEPTIONS:
            calc_output.addAttr(sine_name,
                                attributeType='doubleAngle'
                                )
        else:
            sine_name = attr['name']

        input_names = list(attr.keys())
        attr_amount = len(input_names)-1

        host.addAttr(name,
                     numberOfChildren=attr_amount,
                     attributeType='compound',
                     keyable=True
                     )

        if 'speed' in input_names:
            host.addAttr(speed,
                         parent=name,
                         at='double',
                         defaultValue=attr['speed'],
                         keyable=True
                         )

            speed_multiplier = pm.createNode('math_MultiplyAngle',
                                   n='{}_{}Speed_mlA'.format(attribute_name, attr['name'])
                                   )
            speed_multiplier.isHistoricallyInteresting.set(False)

        if 'strength' in input_names:
            host.addAttr(strength,
                         parent=name,
                         at='double',
                         defaultValue=attr['strength'],
                         keyable=True
                         )

            strength_multiplier = pm.createNode('math_MultiplyAngle',
                                                n='{}_{}Strength_mlA'.format(attribute_name, attr['name'])
                                                )
            strength_multiplier.isHistoricallyInteresting.set(False)

        if 'offset' in input_names:
            host.addAttr(offset,
                         parent=name,
                         at='double',
                         defaultValue=attr['offset'],
                         keyable=True
                         )
            offset_add = pm.createNode('math_AddAngle',
                                n='{}_{}Offset_adA'.format(attribute_name, attr['name'])
                                )
            offset_add.isHistoricallyInteresting.set(False)

        if 'shift' in input_names:
            host.addAttr(shift,
                         parent=name,
                         at='double',
                         defaultValue=attr['shift'],
                         keyable=True
                         )

            shift_add = pm.createNode('math_AddAngle',
                                      n='{}_{}Shift_adA'.format(attribute_name, attr['name'])
                                      )
            shift_add.isHistoricallyInteresting.set(False)

        if 'low_bound' in input_names:
            host.addAttr(low_bound,
                         parent=name,
                         at='double',
                         defaultValue=attr['low_bound'],
                         smn=attr['low_bound'],
                         hsn=True,
                         smx=attr['high_bound'],
                         hsx=True,
                         keyable=True
                         )

            low = pm.createNode('math_Max',
                                n='{}_{}Clamp_max'.format(attribute_name, attr['name'])
                                )

            low.isHistoricallyInteresting.set(False)

        if 'high_bound' in input_names:
            host.addAttr(high_bound,
                         parent=name,
                         at='double',
                         defaultValue=attr['high_bound'],
                         smn=attr['low_bound'],
                         hsn=True,
                         smx=attr['high_bound'],
                         hsx=True,
                         keyable=True
                         )

            high = pm.createNode('math_Min',
                                 n='{}_{}Clamp_min'.format(attribute_name, attr['name'])
                                 )
            high.isHistoricallyInteresting.set(False)

        modulo_offset = pm.createNode('math_Add',
                                      n='{}_{}ModuloOffset_mlA'.format(attribute_name, attr['name'])
                                      )
        modulo_offset.isHistoricallyInteresting.set(False)
        modulo_offset.input2.set(0)

        sinoid_multiplier = pm.createNode('math_Multiply',
                                          n='{}_{}SinoidMult_mlt'.format(attribute_name, attr['name'])
                                          )
        sinoid_multiplier.isHistoricallyInteresting.set(False)
        sinoid_multiplier.input2.set(1.57079632679, lock=True)

        sine_node = pm.createNode('math_SinAngle',
                                  n='{}_{}SineConversion_sin'.format(attribute_name, attr['name'])
                                  )
        sine_node.isHistoricallyInteresting.set(False)

        #   on off switch
        on_off_multiplier = pm.createNode('math_MultiplyAngle',
                                          n='{}_{}OnOff_mlA'.format(envelop, attr['name'])
                                          )
        on_off_multiplier.isHistoricallyInteresting.set(False)

        #    build the system

        #   offset the time
        #   build speed multiplier
        time_mult.output.connect(speed_multiplier.input1)
        host.attr(speed).connect(speed_multiplier.input2)

        #   build offset addition

        host.attr(offset).connect(modulo_offset.input1)
        host.attr(progress).connect(modulo_offset.input2)
        modulo_offset.output.connect(sinoid_multiplier.input1)

        speed_multiplier.output.connect(offset_add.input1)
        sinoid_multiplier.output.connect(offset_add.input2)

        #   build sine conversion
        offset_add.output.connect(sine_node.input)

        #   build in clamping
        sine_node.output.connect(low.input1)
        host.attr(low_bound).connect(low.input2)
        low.output.connect(high.input1)

        host.attr(high_bound).connect(high.input2)
        high.output.connect(strength_multiplier.input1)

        #   build in strength multiplier
        host.attr(strength).connect(strength_multiplier.input2)

        #   build in the value shift
        strength_multiplier.output.connect(shift_add.input1)
        host.attr(shift).connect(shift_add.input2)

        #   connect to envelope of master
        shift_add.output.connect(on_off_multiplier.input1)
        host.attr(envelop).connect(on_off_multiplier.input2)

        #   connect to output
        on_off_multiplier.output.connect(calc_output.attr(sine_name))

        envelope_attrs.append((host.attr(envelop), on_off_multiplier.input2))
        speed_attrs.append((host.attr(speed), speed_multiplier.input2))
        offset_attrs.append((host.attr(offset), modulo_offset.input1))
        time_attrs.append((time_mult.output, speed_multiplier.input1))

    return envelope_attrs, speed_attrs, offset_attrs, time_attrs


def add_sine_system(host, subhost, input_nodes, input_attrs, sin_offset=0, mopath_options=None):
    """

    :param host:
    :param subhost:
    :param input_nodes:
    :param input_attrs:
    :param sin_offset: the amount of which the sine is offset
    :param mopath_options: {'variant': str('mgear'/'custom')
                            'control': PyNode,
                            'points': int,
                            'curve': PyNode,
                            'masters': list(PyNodes),
                            'slaves': list(PyNodes)
                            }
    :return:
    """
    power_connections = list()
    offset_connections = list()
    envelope_connections = list()
    speed_connections = list()
    time_connections = list()

    input_amount = len(input_nodes)
    host_nde = pm.PyNode(host)
    subhost_nde = pm.PyNode(subhost)

    #   check for a sin offset statement

    if sin_offset:
        host_attr = '{}_system_attributes'.format(SINE_TOKEN_STATIC)
        if not host_nde.hasAttr(host_attr):
            host_nde.addAttr(host_attr,
                             at='enum',
                             enumName=ENUM_TOKEN_STATIC,
                             keyable=True
                             )

            host_nde.attr('{}_system_attributes'.format(SINE_TOKEN_STATIC)).set(lock=True)

        sin_envelope_attr = '{}_system_envelope'.format(SINE_TOKEN_STATIC)
        if not host_nde.hasAttr(sin_envelope_attr):
            host_nde.addAttr(sin_envelope_attr,
                             at='enum',
                             enumName='back=-1:front={}'.format(str(input_amount+1)),
                             defaultValue=-1,
                             keyable=True
                             )
            host_nde.attr(sin_envelope_attr).set(input_amount+1)

        sin_direction_attr = '{}_system_direction'.format(SINE_TOKEN_STATIC)
        if not host_nde.hasAttr(sin_direction_attr):
            host_nde.addAttr(sin_direction_attr,
                             at='enum',
                             enumName='front=1:back=2',
                             keyable=True,
                             defaultValue=1
                             )

        sin_speed_attr = '{}_system_speed'.format(SINE_TOKEN_STATIC)
        if not host_nde.hasAttr(sin_speed_attr):
            host_nde.addAttr(sin_speed_attr,
                             at='double',
                             keyable=True,
                             dv=1,
                             )

        sin_offset_attr = '{}_system_offset'.format(SINE_TOKEN_STATIC)
        if not host_nde.hasAttr(sin_offset_attr):
            host_nde.addAttr(sin_offset_attr,
                             at='long',
                             keyable=True,
                             dv=sin_offset,
                             min=1,
                             hasMinValue=True,
                             max=input_amount+1,
                             hasMaxValue=True
                             )

        for x in range(len(input_nodes)):
            modulo = create_float_modulo()
            host_nde.attr(sin_offset_attr).connect(modulo['input2'])
            modulo['input1'].set(x+1)
            power_connections.append(modulo['output'])

        path_time_attrs = None
        if mopath_options:
            if mopath_options['variant'] == 'custom':
                path_time_attrs = create_path_curve(host_nde,
                                                    sin_speed_attr,
                                                    mopath_under=mopath_options['control'],
                                                    mopath_objects=mopath_options['slaves'],
                                                    subdivs=mopath_options['points']
                                                    )

            elif mopath_options['variant'] == 'mgear':
                path_time_attrs = connect_to_mopath(host_nde,
                                                    sin_speed_attr,
                                                    mopath_curve=mopath_options['curve'],
                                                    master_objects=mopath_options['masters'],
                                                    mopath_objects=mopath_options['slaves']
                                                    )

            else:
                pass

    for i in input_nodes:
        envelope, speeds, offsets, times = add_sine(i,
                                                    input_attrs,
                                                    host=subhost_nde
                                                    )
        envelope_connections.append(envelope)
        speed_connections.append(speeds)
        offset_connections.append(offsets)
        time_connections.append(times)

    #   check if all requirements are met
    power_rules = [sin_offset, power_connections]
    if all(power_rules):
        for x, i in enumerate(power_connections):
            for number in range(0, len(input_attrs)):
                add = pm.createNode('math_Add')
                add.isHistoricallyInteresting.set(False)

                adjust = pm.createNode('math_Multiply', n='adjust')
                adjust.isHistoricallyInteresting.set(False)

                individual_control_attr = offset_connections[x][number][0]
                individual_offset_node = offset_connections[x][number][1]

                i.connect(adjust.input1)
                adjust.input2.set(1, lock=True)

                adjust.output.connect(add.input1)
                individual_control_attr.connect(add.input2)

                add.output.connect(individual_offset_node,
                                   force=True
                                   )

    if envelope_connections:
        for y, i in enumerate(envelope_connections):
            for x in i:
                envelope_in = x[0]
                envelope_out = x[1]

                combo = pm.createNode('math_Max')
                combo.isHistoricallyInteresting.set(False)

                compare = pm.createNode('math_Compare')
                compare.isHistoricallyInteresting.set(False)

                compare_floor = pm.createNode('math_Compare')
                compare_floor.isHistoricallyInteresting.set(False)

                floor = pm.createNode('math_Floor')
                floor.isHistoricallyInteresting.set(False)

                subtract = pm.createNode('math_Subtract')
                subtract.isHistoricallyInteresting.set(False)

                absolute = pm.createNode('math_Absolute')
                absolute.isHistoricallyInteresting.set(False)

                selector = pm.createNode('math_Select')
                selector.isHistoricallyInteresting.set(False)

                envelope_in.connect(combo.input1)

                host_nde.attr(sin_envelope_attr).connect(compare.input1)
                compare.input2.set(y, lock=True)
                host_nde.attr(sin_direction_attr).connect(compare.operation)

                # this can be cut
                host_nde.attr(sin_envelope_attr).connect(floor.input)
                host_nde.attr(sin_envelope_attr).connect(subtract.input1)
                floor.output.connect(subtract.input2)

                subtract.output.connect(absolute.input)
                absolute.output.connect(selector.input2)
                compare.output.connect(selector.input1)

                floor.output.connect(compare_floor.input1)
                compare_floor.input2.set(y, lock=True)
                compare_floor.operation.set(0, lock=True)

                compare_floor.output.connect(selector.condition)

                #   here exchange multiply for compare output
                selector.output.connect(combo.input2)

                combo.output.connect(envelope_out, force=True)

    if speed_connections:
        for i in speed_connections:
            for x in i:
                speed_in = x[0]
                speed_out = x[1]

                multiplier = pm.createNode('math_Multiply', n='shit')
                multiplier.isHistoricallyInteresting.set(False)

                speed_in.connect(multiplier.input1)
                host_nde.attr(sin_speed_attr).connect(multiplier.input2)

                multiplier.output.connect(speed_out, force=True)

    if time_connections and path_time_attrs:
        for i in time_connections:
            for x in i:
                # TIME_NODE.outTime, time_mult.input1
                # time_choice.input[0], time_choice.output
                time_in, time_out = x
                mopath_in, mopath_out = path_time_attrs

                time_in.connect(mopath_in, force=True)
                mopath_out.connect(time_out, force=True)

    return True


def create_float_modulo(input_multiply=180):
    """ function to create a float modulo
    wraps it in a way so it is kinda resembling PyMel node interaction

    args:
    input_multiply(float): multiply value, this needs most likely to be adjusted for nodes

    Returns:
        Dict: dict filled with input attrs and output attr, these need to be connected after the fact
    """

    div_nde = pm.createNode('math_Divide', n='float_modulo_div')
    div_nde.isHistoricallyInteresting.set(False)

    floor_nde = pm.createNode('math_Floor', n='float_modulo_flr')
    floor_nde.isHistoricallyInteresting.set(False)

    sub_nde = pm.createNode('math_Subtract', n='float_modulo_sub')
    sub_nde.isHistoricallyInteresting.set(False)

    mult_nde = pm.createNode('math_Multiply', n='float_modulo_mul')
    mult_nde.isHistoricallyInteresting.set(False)

    div_nde.output.connect(floor_nde.input)

    div_nde.output.connect(sub_nde.input1)
    floor_nde.output.connect(sub_nde.input2)

    sub_nde.output.connect(mult_nde.input1)
    mult_nde.input2.set(input_multiply)

    output = {'input1': div_nde.input1, 'input2': div_nde.input2, 'output': mult_nde.output}
    return output


def create_offsets(input_node):
    """

    Returns:
         Dict:
    """
    if isinstance(input_node, str):
        input_node = pm.PyNode(input_node)

    node = input_node

    node_name = node.shortName()
    parent = node.getParent()

    #   create offsets
    parent_offset = pm.createNode('transform',
                                  n='{}_calcInputPosition_pos'.format(node_name),
                                  ss=True
                                  )

    calc_output = pm.createNode('transform',
                                n='{}_calcOutputPosition_pos'.format(node_name),
                                ss=True
                                )

    #   check for parent node
    if parent:
        pm.parent(parent_offset, parent)
        pm.matchTransform(parent_offset, parent)

    pm.parent(calc_output, parent_offset)
    pm.matchTransform(calc_output, parent_offset)

    pm.matchTransform(calc_output, node)
    pm.parent(node, calc_output)

    return {'node': node, 'parent': parent, 'parent_offset': parent_offset, 'calc_output': calc_output}


def create_path_curve(host,
                      host_speed_attr,
                      mopath_under=None,
                      mopath_objects=None,
                      subdivs=20
                      ):

    #   empty list:
    xyz_uppered = ['X', 'Y', 'Z']

    #   add host attributes
    mopath_options_attr = '{}_mopath_options'.format(SINE_TOKEN_STATIC)
    if not host.hasAttr(mopath_options_attr):
        host.addAttr(mopath_options_attr,
                     at='enum',
                     keyable=True,
                     enumName=ENUM_TOKEN_STATIC
                     )
        host.attr(mopath_options_attr).set(lock=True)

    space_switch_attr = '{}_mopath_spaces'.format(SINE_TOKEN_STATIC)
    if not host.hasAttr(space_switch_attr):
        host.addAttr(space_switch_attr,
                     at='enum',
                     enumName='free:mopath',
                     keyable=True,
                     dv=1)

    mopath_progression_attr = '{}_mopath_progress'.format(SINE_TOKEN_STATIC)
    if not host.hasAttr(mopath_progression_attr):
        host.addAttr(mopath_progression_attr,
                     at='double',
                     keyable=True,
                     dv=0,
                     min=0,
                     hasMinValue=True,
                     max=100,
                     hasMaxValue=True
                     )

    #   create curve
    curve_name = '{}_curve_path'.format(SINE_TOKEN_STATIC)
    if not pm.objExists(curve_name):
        points = [(0, 0, x) for x in range(subdivs)]
        mopath_crv = pm.curve(p=points, n=curve_name)
        mopath_crv_shape = mopath_crv.getShape()
        mopath_crv_shape.overrideEnabled.set(True, lock=True)
        mopath_crv_shape.overrideColor.set(21, lock=True)
        host.attr(space_switch_attr).connect(mopath_crv.visibility)
        mopath_crv.visibility.set(channelBox=False)
        pm.parent(mopath_crv, mopath_under)

        for path_obj in mopath_objects:
            #   get parent node
            offset_prep = create_offsets(path_obj)
            parent_node, out_node = offset_prep['parent_offset'], offset_prep['calc_output']

            #   create calculation network for position
            point_curve_info = pm.createNode('pointOnCurveInfo')
            point_curve_info.isHistoricallyInteresting.set(False)
            point_curve_info.turnOnPercentage.set(True, lock=True)

            axis = pm.createNode('math_AxisFromMatrix')
            axis.isHistoricallyInteresting.set(False)
            axis.axis.set(1, lock=True)

            cross_prod = pm.createNode('math_CrossProduct')
            cross_prod.isHistoricallyInteresting.set(False)

            construct_matrix = pm.createNode('fourByFourMatrix')
            construct_matrix.isHistoricallyInteresting.set(False)

            shear_neg = pm.createNode('pickMatrix')
            shear_neg.isHistoricallyInteresting.set(False)
            shear_neg.useTranslate.set(True, lock=True)
            shear_neg.useRotate.set(True, lock=True)
            shear_neg.useScale.set(False, lock=True)
            shear_neg.useShear.set(False, lock=True)

            negate_parent = pm.createNode('math_MultiplyMatrix')
            negate_parent.isHistoricallyInteresting.set(False)

            space_choice = pm.createNode('choice')
            space_choice.isHistoricallyInteresting.set(False)

            decomp = pm.createNode('decomposeMatrix')
            decomp.isHistoricallyInteresting.set(False)

            #   connect network
            mopath_crv_shape.worldSpace[0].connect(point_curve_info.inputCurve)
            host.attr(mopath_progression_attr).connect(point_curve_info.parameter)
            mopath_crv.worldMatrix[0].connect(axis.input)

            for x, i in enumerate(xyz_uppered):
                point_curve_info.attr('position{}'.format(i)).connect(construct_matrix.attr('in3{}'.format(str(x))))

                point_curve_info.attr('normalizedTangent{}'.format(i)).connect(
                    construct_matrix.attr('in0{}'.format(str(x))))

                axis.attr('output{}'.format(i)).connect(construct_matrix.attr('in1{}'.format(str(x))))

                axis.attr('output{}'.format(i)).connect(cross_prod.attr('input1{}'.format(i)))
                point_curve_info.attr('normalizedTangent{}'.format(i)).connect(cross_prod.attr('input2{}'.format(i)))
                cross_prod.attr('output{}'.format(i)).connect(construct_matrix.attr('in2{}'.format(str(x))))

            construct_matrix.output.connect(shear_neg.inputMatrix)

            host.attr(space_switch_attr).connect(space_choice.selector)
            shear_neg.outputMatrix.connect(negate_parent.input1)
            parent_node.getParent().worldInverseMatrix.connect(negate_parent.input2)
            negate_parent.output.connect(space_choice.input[1])

            parent_node.matrix.connect(space_choice.input[0])

            space_choice.output.connect(decomp.inputMatrix)

            for i in xyz_uppered:
                try:
                    decomp.attr('outputTranslate{}'.format(i)).connect(out_node.attr('translate{}'.format(i)))
                    decomp.attr('outputRotate{}'.format(i)).connect(out_node.attr('rotate{}'.format(i)))
                    decomp.attr('outputScale{}'.format(i)).connect(out_node.attr('scale{}'.format(i)))
                except:
                    pass

        #   create calculation network for speed
        construct_matrix = pm.createNode('curveInfo')
        construct_matrix.isHistoricallyInteresting.set(False)

        progression_multiplier = pm.createNode('math_Multiply')
        progression_multiplier.isHistoricallyInteresting.set(False)

        speed_multiplier = pm.createNode('math_Multiply')
        speed_multiplier.isHistoricallyInteresting.set(False)
        speed_multiplier.input1.set(2, lock=True)

        prog_speed_multiplier = pm.createNode('math_Multiply', n='yolo')
        prog_speed_multiplier.isHistoricallyInteresting.set(False)

        length_multiply = pm.createNode('math_Multiply')
        length_multiply.isHistoricallyInteresting.set(False)
        length_multiply.input2.set(.01, lock=True)

        time_choice = pm.createNode('choice', n='{}_mopath_time_cho'.format(SINE_TOKEN_STATIC))
        time_choice.isHistoricallyInteresting.set(False)

        #   connect
        mopath_crv_shape.worldSpace[0].connect(construct_matrix.inputCurve)
        construct_matrix.arcLength.connect(progression_multiplier.input1)

        host.attr(mopath_progression_attr).connect(length_multiply.input1)
        length_multiply.output.connect(progression_multiplier.input2)

        host.attr(host_speed_attr).connect(speed_multiplier.input2)

        progression_multiplier.output.connect(prog_speed_multiplier.input1)
        speed_multiplier.output.connect(prog_speed_multiplier.input2)

        host.attr(space_switch_attr).connect(time_choice.selector)
        prog_speed_multiplier.output.connect(time_choice.input[1])
        return time_choice.input[0], time_choice.output
    else:
        time_choice = pm.PyNode('{}_mopath_time_cho'.format(SINE_TOKEN_STATIC))
        return time_choice.input[0], time_choice.output


def connect_to_mopath(host,
                      host_speed_attr,
                      mopath_curve=None,
                      master_objects=None,
                      mopath_objects=None
                      ):

    #   empty list:
    xyz_uppered = ['X', 'Y', 'Z']

    #   add host attributes
    mopath_options_attr = '{}_mopath_options'.format(SINE_TOKEN_STATIC)
    if not host.hasAttr(mopath_options_attr):
        host.addAttr(mopath_options_attr,
                     at='enum',
                     keyable=True,
                     enumName=ENUM_TOKEN_STATIC
                     )
        host.attr(mopath_options_attr).set(lock=True)

    space_switch_attr = '{}_mopath_spaces'.format(SINE_TOKEN_STATIC)
    if not host.hasAttr(space_switch_attr):
        host.addAttr(space_switch_attr,
                     at='enum',
                     enumName='free:mopath',
                     keyable=True,
                     dv=1
                     )

    mopath_progression_attr = '{}_mopath_progress'.format(SINE_TOKEN_STATIC)
    if not host.hasAttr(mopath_progression_attr):
        host.addAttr(mopath_progression_attr,
                     at='double',
                     keyable=True,
                     dv=0,
                     min=0,
                     hasMinValue=True,
                     max=100,
                     hasMaxValue=True
                     )

    #   create calculation network for speed
    construct_matrix = pm.createNode('curveInfo')
    construct_matrix.isHistoricallyInteresting.set(False)

    progression_multiplier = pm.createNode('math_Multiply')
    progression_multiplier.isHistoricallyInteresting.set(False)

    speed_multiplier = pm.createNode('math_Multiply')
    speed_multiplier.isHistoricallyInteresting.set(False)
    speed_multiplier.input1.set(2, lock=True)

    prog_speed_multiplier = pm.createNode('math_Multiply', n='yolo')
    prog_speed_multiplier.isHistoricallyInteresting.set(False)

    length_multiply = pm.createNode('math_Multiply')
    length_multiply.isHistoricallyInteresting.set(False)
    length_multiply.input2.set(.01, lock=True)

    time_choice = pm.createNode('choice', n='{}_mopath_time_cho'.format(SINE_TOKEN_STATIC))
    time_choice.isHistoricallyInteresting.set(False)

    #   connect
    mopath_curve.getShape().worldSpace[0].connect(construct_matrix.inputCurve)
    construct_matrix.arcLength.connect(progression_multiplier.input1)

    host.attr(mopath_progression_attr).connect(length_multiply.input1)
    length_multiply.output.connect(host.attr('mopath_C0_position'), f=True)

    host.attr('mopath_C0_position').connect(progression_multiplier.input2)

    host.attr(host_speed_attr).connect(speed_multiplier.input2)

    progression_multiplier.output.connect(prog_speed_multiplier.input1)
    speed_multiplier.output.connect(prog_speed_multiplier.input2)

    host.attr(space_switch_attr).connect(time_choice.selector)
    prog_speed_multiplier.output.connect(time_choice.input[1])

    if len(master_objects) == len(mopath_objects):
        combined_list = list(zip(master_objects, mopath_objects))
        for i in combined_list:
            pm.parentConstraint(i[0], i[1])

    return time_choice.input[0], time_choice.output

