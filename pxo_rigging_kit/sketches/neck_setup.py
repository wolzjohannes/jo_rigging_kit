# mgear / pixo neck setup post script
# www.pixomondo.com
# Date: 27 / 04 / 2022
# Artist: Johannes Wolz / Rigging TD

"""
Custom script to prepare the neck to our needs.
Still under construction not ready for use.
"""
# Import built-in modules
import logging

try:
    # Import built-in modules
    from itertools import pairwise

except ImportError:
    from pxo_rigging_kit.core import pairwise

# Import local modules
from pxo_rigging_kit.maya_utils import dag_utils

#######################################################
# GLOBALS
#######################################################

logging.basicConfig(level=logging)
_LOGGER = logging.getLogger(__name__ + ".py")

#######################################################
# CLASSES
#######################################################


# Import third-party modules
import pymel.core as pmc


def generate_spaces(ik_controls):
    start = ik_controls[0]
    inbetweens = ik_controls[1:-1]

    node_outputs = list()
    for inbetween in inbetweens:
        mult_mtx_nde = pmc.createNode("math_MultiplyMatrix")

        inbetween_ws = pmc.datatypes.Matrix(inbetween.getMatrix(worldSpace=True))
        invert_ws = pmc.datatypes.Matrix(start.getMatrix(worldSpace=True)).inverse()

        new_mtx = inbetween_ws * invert_ws
        start.worldMatrix.connect(mult_mtx_nde.input2)
        mult_mtx_nde.input1.set(new_mtx)
        node_outputs.append(mult_mtx_nde.output)

    return node_outputs


def generate_blend_spaces(combined_spaces):
    for neck_matrix, head_matrix in combined_spaces:
        matrix_blended = pmc.createNode("math_LerpMatrix")
        test_object = pmc.createNode("locator").getParent()

        neck_matrix.connect(matrix_blended.input1)
        head_matrix.connect(matrix_blended.input2)

        matrix_blended.output.connect(test_object.offsetParentMatrix)


def sort_out_neck_follow():
    outputs = list()
    ik_controls = pmc.ls("neck_C_0_ik*_default_ctrl")

    if len(ik_controls) < 3:
        return

    start = ik_controls[0]
    end = ik_controls[-1]

    controls_paired = pairwise(ik_controls)

    dist_calc_nde = pmc.createNode("math_DistanceTransforms")

    extract_start_rotation_nde = pmc.createNode("math_TwistFromMatrix")
    extract_start_rotation_nde.rotationOrder.set(0)

    extract_end_rotation_nde = pmc.createNode("math_TwistFromMatrix")
    extract_end_rotation_nde.rotationOrder.set(0)

    start.worldMatrix.connect(dist_calc_nde.input1)
    end.worldMatrix.connect(dist_calc_nde.input2)

    start.worldMatrix.connect(extract_start_rotation_nde.input)
    end.worldMatrix.connect(extract_end_rotation_nde.input)

    total_distance = dag_utils.get_transforms_distance_combined(ik_controls)
    blend_amount = 0

    for aim_start, aim_end in controls_paired[1:]:
        distance_between = pmc.datatypes.Vector(
            aim_start.getTranslation(space="world")
        ).distanceTo(pmc.datatypes.Vector(aim_end.getTranslation(space="world")))
        blend_amount += float(distance_between) / float(total_distance)

        # create nodes
        distance_mult = pmc.createNode("math_Multiply")
        distance_inverse_mult = pmc.createNode("math_Multiply")

        distance_offset = pmc.createNode("math_MatrixFromTRS")
        distance_inverse_offset = pmc.createNode("math_MatrixFromTRS")

        distance_mtx = pmc.createNode("math_MultiplyMatrix")
        distance_inverse_mtx = pmc.createNode("math_MultiplyMatrix")

        blend_mtx = pmc.createNode("blendMatrix")
        offset_mtx = pmc.createNode("math_MultiplyMatrix")
        aim_mtx = pmc.createNode("aimMatrix")

        # extracted rotation nodes
        rot_to_mtx = pmc.createNode("math_MatrixFromRotation")
        rot_to_mtx.rotationOrder.set(0)
        anim_blend_add_nde = pmc.createNode("animBlendNodeAdditiveRotation")
        anim_blend_add_nde.weightA.set(blend_amount)
        anim_blend_add_nde.weightB.set(1 - blend_amount)
        anim_rot_mtx = pmc.createNode("math_MultiplyMatrix")

        # multiply distance between fraction
        dist_calc_nde.output.connect(distance_mult.input1)
        distance_mult.input2.set(blend_amount, lock=True)
        dist_calc_nde.output.connect(distance_inverse_mult.input1)
        distance_inverse_mult.input2.set(blend_amount - 1.0, lock=True)

        # build a matrix from the distance
        distance_mult.output.connect(distance_offset.translation.translationX)
        distance_inverse_mult.output.connect(
            distance_inverse_offset.translation.translationX
        )

        # multiply built matrix into the space from start and end
        distance_offset.output.connect(distance_mtx.input1)
        distance_inverse_offset.output.connect(distance_inverse_mtx.input1)

        start.worldMatrix.connect(distance_mtx.input2)
        end.worldMatrix.connect(distance_inverse_mtx.input2)

        # build lerp of behaviour
        distance_mtx.output.connect(blend_mtx.inputMatrix)
        distance_inverse_mtx.output.connect(blend_mtx.target[0].targetMatrix)
        blend_mtx.target[0].useRotate.set(0)
        blend_mtx.target[0].useShear.set(0)

        blend_mtx.target[0].weight.set(blend_amount)

        test_object = pmc.createNode("locator").getParent()

        blend_mtx.outputMatrix.connect(offset_mtx.input1)
        offset_mtx.input2.set(
            pmc.datatypes.TransformationMatrix(
                [
                    [
                        1,
                        0,
                        0,
                        0,
                    ],
                    [
                        0,
                        1,
                        0,
                        0,
                    ],
                    [
                        0,
                        0,
                        1,
                        0,
                    ],
                    [
                        20,
                        0,
                        0,
                        1,
                    ],
                ]
            )
        )

        # connect straight forward aim

        outputs.append((aim_mtx.primaryTargetMatrix, blend_mtx.outputMatrix))

        aim_mtx.primaryInputAxisZ.set(1)
        aim_mtx.primaryInputAxisX.set(0)

        aim_mtx.secondaryInputAxisX.set(1)
        aim_mtx.secondaryInputAxisY.set(0)
        aim_mtx.secondaryMode.set(1)

        blend_mtx.outputMatrix.connect(aim_mtx.inputMatrix)
        offset_mtx.output.connect(aim_mtx.secondaryTargetMatrix)

        offset_mtx.output.connect(pmc.sphere()[0].offsetParentMatrix)

        extract_start_rotation_nde.output.connect(anim_blend_add_nde.inputAZ)
        extract_end_rotation_nde.output.connect(anim_blend_add_nde.inputBZ)

        anim_blend_add_nde.output.connect(rot_to_mtx.input)

        rot_to_mtx.output.connect(anim_rot_mtx.input1)
        aim_mtx.outputMatrix.connect(anim_rot_mtx.input2)
        anim_rot_mtx.output.connect(test_object.offsetParentMatrix)

    output_count = len(outputs)
    for iteration_, (aim_inpt, blend_outpt) in enumerate(outputs):
        if output_count - 1 == iteration_:
            end.worldMatrix.connect(aim_inpt)
            break

        outputs[iteration_ + 1][1].connect(aim_inpt)
