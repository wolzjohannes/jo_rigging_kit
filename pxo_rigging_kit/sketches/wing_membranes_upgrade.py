# Import built-in modules
import sys

# Import third-party modules
from maya import OpenMaya as om2
import pymel.core as pmc

if (sys.version_info.major == 3 and sys.version_info.major < 10) or sys.version_info.major < 3:
    # Import built-in modules
    from itertools import tee

    def pairwise(iterable):
        "s -> (s0,s1), (s1,s2), (s2, s3), ..."
        a, b = tee(iterable)
        next(b, None)
        return zip(a, b)

else:
    # Import built-in modules
    from itertools import pairwise


def get_normalized_middle(object_start, object_middle, object_end):
    out_dict = dict()

    position_start = om2.MPoint(object_start.getTranslation(space="world"))
    position_mid = om2.MPoint(object_middle.getTranslation(space="world"))
    position_end = om2.MPoint(object_end.getTranslation(space="world"))

    vector_start = om2.MVector(position_start)
    vector_mid = om2.MVector(position_mid)
    vector_end = om2.MVector(position_end)

    vector_start_end = position_end - position_start
    vector_start_mid = position_mid - position_start
    vector_mid_end = position_end - position_mid

    len_start_end = vector_start_end.length()
    len_start_mid = vector_start_mid.length()
    len_mid_end = vector_mid_end.length()

    start_to_end_composed = len_start_mid + len_mid_end
    start_mid_percentile = len_start_mid / start_to_end_composed
    mid_end_percentile = len_mid_end / start_to_end_composed
    check_sum = start_mid_percentile + mid_end_percentile

    point_mid = om2.MVector(position_start + vector_start_end * start_mid_percentile)

    vector_position_start = point_mid - om2.MVector(position_start)
    vector_position_mid = point_mid - om2.MVector(position_mid)
    vector_position_end = point_mid - om2.MVector(position_end)

    normalized_vector_mid = vector_position_mid.normal()
    normalized_vector_start_mid = vector_start_mid.normal()

    crossed_up_vector_one = normalized_vector_mid ^ normalized_vector_start_mid
    normalized_up_vector_one = crossed_up_vector_one.normal()

    crossed_up_vector_two = normalized_vector_mid ^ normalized_up_vector_one
    normalized_up_vector_two = crossed_up_vector_two.normal()

    output_matrix_world = compose_matrix(normalized_up_vector_one,
                                         normalized_up_vector_two,
                                         normalized_vector_mid,
                                         point_mid)

    # calculation final output
    out_dict["output_matrix"] = output_matrix_world
    out_dict["output_vector_one"] = normalized_up_vector_one
    out_dict["output_vector_two"] = normalized_up_vector_two
    out_dict["output_vector_three"] = normalized_vector_mid
    out_dict["output_position"] = point_mid

    # calculation byproduct output
    out_dict["inner_ratio"] = start_mid_percentile
    out_dict["outter_ratio"] = start_mid_percentile

    out_dict["checksum"] = check_sum

    # returns the points
    out_dict["start_position_one"] = position_start
    out_dict["start_position_two"] = position_mid
    out_dict["start_position_three"] = position_end

    # returns the vectors
    out_dict["start_vector_one"] = vector_start
    out_dict["start_vector_two"] = vector_mid
    out_dict["start_vector_three"] = vector_end

    # returns the points
    out_dict["vector_position_start"] = vector_position_start
    out_dict["vector_position_mid"] = vector_position_mid
    out_dict["vector_position_end"] = vector_position_end

    return out_dict


def compose_matrix(normalized_up_vector_one, normalized_up_vector_two, normalized_vector_mid, point_mid):

    matrix_data = vectors_and_position_to_matrix(normalized_vector_mid,
                                                 normalized_up_vector_one,
                                                 normalized_up_vector_two,
                                                 point_mid)

    output_matrix_world = om2.MMatrix(matrix_data)
    return output_matrix_world


def lerp_positions(vector_mid, position_mid, segments=4):
    positions = list()
    for segment in range(0, segments):

        new_vec = position_mid + (vector_mid * float((1.0 / (segments - 1)) * segment))
        positions.append(new_vec)

    return positions


def vectors_and_position_to_matrix(vec_0, vec_1, vec_2, pos_0):
    util = om2.MScriptUtil()
    new_matrix = om2.MMatrix()

    vec_0.normalize()
    vec_1.normalize()
    vec_2.normalize()

    # make 16 element list
    built_matrix_array = [*vec_0, 0.0,
                          *vec_1, 0.0,
                          *vec_2, 0.0,
                          *pos_0, 1.0
                          ]

    # use scriptUtil class to convert list to MMatrix
    util.createMatrixFromList(built_matrix_array, new_matrix)
    return new_matrix
    # new_transformation_matrix = om2.MTransformationMatrix(new_matrix)


def create_lerped_objects(input_info_data,
                          lerp_position_0="vector_position_mid",
                          lerp_position_1="start_vector_two",
                          compose_vector_0="output_vector_one",
                          compose_vector_1="output_vector_two",
                          compose_vector_2="output_vector_three",
                          direction=1
                          ):

    lerp_point_data = lerp_positions(input_info_data[lerp_position_0],
                                                        input_info_data[lerp_position_1]
                                                        )[::direction]

    lerp_matrix_data = [compose_matrix(input_info_data[compose_vector_0],
                                       input_info_data[compose_vector_1],
                                       input_info_data[compose_vector_2],
                                       position__
                                       )
                        for position__
                        in lerp_point_data
                        ]

    output_objects = [pmc.sphere()[0]
                      for position__
                      in lerp_point_data
                      ]

    matrix_objects_combined = list(zip(output_objects, lerp_matrix_data))

    [node[0].setTransformation(node[1]) for node in matrix_objects_combined]

    return output_objects


def create_aim_matrix():
    pass


if __name__ == "__main__":
    objects = pmc.selected()

    output_data = get_normalized_middle(objects[0],
                                        objects[1],
                                        objects[2]
                                        )

    sphere_ = pmc.sphere()[0]
    sphere_.setTransformation(output_data["output_matrix"])

    # positions of middle matrices
    elbow_fks = create_lerped_objects(output_data,
                                      lerp_position_0="vector_position_mid",
                                      lerp_position_1="start_vector_two",
                                      compose_vector_0="output_vector_one",
                                      compose_vector_1="output_vector_two",
                                      compose_vector_2="output_vector_three",
                                      direction=1
                                      )

    create_lerped_objects(output_data,
                          lerp_position_0="vector_position_start",
                          lerp_position_1="start_vector_one",
                          compose_vector_0="output_vector_one",
                          compose_vector_1="output_vector_two",
                          compose_vector_2="output_vector_three",
                          direction=1
                          )

    create_lerped_objects(output_data,
                          lerp_position_0="vector_position_end",
                          lerp_position_1="start_vector_three",
                          compose_vector_0="output_vector_one",
                          compose_vector_1="output_vector_two",
                          compose_vector_2="output_vector_three",
                          direction=-1
                          )

    [pmc.parent(parenting_pair[1], parenting_pair[0]) for parenting_pair in pairwise(elbow_fks)]

