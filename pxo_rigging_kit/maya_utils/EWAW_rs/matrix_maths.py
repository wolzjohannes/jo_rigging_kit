from maya.api import OpenMaya as om2
from pymel import core as pmc


# functions to help and deal with OpenMaya matrix maths
def get_world_matrix(dag_node: str) -> om2.MMatrix:
    """
    Gets the World Matrix of a dag node based on its string.
    Make sure if the string is unique in the scene.

    Args:
        dag_node (str): Name of the dag node to be queried.

    Returns:
        om2.MMatrix (world_matrix): The world matrix of the dag node as an om2.MMatrix object.

    """

    base_object = om2.MGlobal.getSelectionListByName(dag_node)

    sel_dag = base_object.getDagPath(0)

    world_matrix = sel_dag.inclusiveMatrix()

    return world_matrix


def invert_matrix(matrix_object: om2.MMatrix) -> om2.MMatrix:
    """
    Takes a maya.api.OpenMaya.MMatrix and inverses it.
    Using the function set of the om2.MTransformationMatrix.

    Args:
        matrix_object (om2.MMatrix): The matrix that needs to be inversed.

    Returns:
        om2.MMatrix (inverse_matrix): The inverted version of the MMatrix.

    """

    matrix_transformation_object = om2.MTransformationMatrix(matrix_object)

    inverse_matrix = matrix_transformation_object.asMatrixInverse()

    return inverse_matrix


def multiply_matrices(matrix_one: om2.MMatrix,
                      matrix_two: om2.MMatrix,
                      ) -> om2.MMatrix:
    """
    Multiplies two matrices together, split out for readability.
    # might be unneccesary wrapper.

    Args:
        matrix_one (om2.MMatrix): The first Matrix of the Operation Input.
        matrix_two (om2.MMatrix): The second Matrix of the Operation Input.

    Returns:
        om2.MMatrix (multed_matrix): The Matrix Product of the Operation.

    """

    matrix_product = matrix_one * matrix_two

    return matrix_product


def mmatrix_to_tuple(in_matrix: om2.MMatrix) -> tuple:
    """
    Conversion of maya.api.OpenMaya.MMatrix to a Tuple of len() == 16.
    Mainly a wrapper to keep code more readable in the way it happens, maybe a useless wrapper.

    Args:
        in_matrix (om2.MMatrix): Matrix to be converted into a cmds/mel readable format.

    Returns:
        Tuple: The filled 4x4 Matrix as Tuple of length == 16.
    """
    return tuple(in_matrix)


def pmatrix_to_tuple(in_matrix: pmc.dt.Matrix) -> tuple:
    """
    Conversion of pymel.core.dt.Matrix to a Tuple of len() == 16.

    Args:
        in_matrix (pmc.dt.Matrix): Matrix to be converted into a cmds/mel readable format.

    Returns:
        Tuple: The filled 4x4 Matrix as Tuple of length == 16.
    """

    return tuple(in_matrix.__melobject__())


def pmatrix_to_mmatrix(in_matrix: pmc.dt.Matrix) -> om2.MMatrix:
    """
    Conversion of pymel.core.dt.Matrix to an om2.MMatrix.

    Args:
        in_matrix (pmc.dt.Matrix): The Pymel Matrix that will be converted into an maya.api.OpenMaya.MMatrix.

    Returns:
        om2.MMatrix: The newly created matrix.
    """

    out_matrix = pmatrix_to_tuple(in_matrix)

    return om2.MMatrix(out_matrix)


def tuple_to_mmatrix(in_tuple: tuple) -> om2.MMatrix:
    """
    Converts a Tuple of length == 16 into an om2.MMatrix.

    Args:
        in_tuple (tuple): Tuple of the 4x4 matrix to be converted, mirrors how we get data from cmds.

    Returns:
        om2.MMatrix: The newly created matrix.
    """
    tuple_len = len(in_tuple)

    if tuple_len != 16:
        raise IndexError(f"The length of a tuple to matrix conversion always needs to be 16 since 4x4.\n"
                         f"Current length is {tuple_len}.")

    return om2.MMatrix(in_tuple)


def distance_between_matrices(matrix_1: om2.MMatrix,
                              matrix_2: om2.MMatrix
                              ) -> float:
    """
    Calculates the distance between the Positions represented by the input matrices.

    Args:
        matrix_1 (om2.MMatrix): First Matrix.
        matrix_2 (om2.MMatrix): Second Matrix.

    Returns:
        Float (length): The distance calculated.
    """

    position_one = get_position_from_matrix(matrix_1)
    position_two = get_position_from_matrix(matrix_2)

    one_to_two = position_one - position_two

    return one_to_two.length()


def get_position_from_matrix(in_matrix: om2.MMatrix,
                             space: int = om2.MSpace.kWorld
                             ) -> om2.MVector:
    """
    Queries the world position from the matrix.

    Args:
        in_matrix (om2.MMatrix): maya api2 matrix you need the position from.
        space (int): usually the OpenMaya.MSpace constant, which represents an integer.

    Returns:
        om2.MVector (out_vector): the position in worldspace.

    """

    om_transformation_matrix_two = om2.MTransformationMatrix(in_matrix)

    out_vector = om_transformation_matrix_two.translation(space)

    return out_vector


def get_matrix_from_point(in_point: om2.MPoint,
                          space: int = om2.MSpace.kWorld
                          ) -> om2.MMatrix:
    """
    Turns MPoint to MMatrix.

    Args:
        in_matrix (om2.MPoint): maya api2 matrix you need the position from.
        space (int): usually the OpenMaya.MSpace constant, which represents an integer.

    Returns:
        om2.MMatrix (out_vector): the position in worldspace.

    """
    identity_matrix = om2.MMatrix()

    modifying_matrix = om2.MTransformationMatrix(identity_matrix)

    translate_vector = om2.MVector((in_point.x, in_point.y, in_point.z))

    modifying_matrix.setTranslation(translate_vector, space)

    resulting_mmatrix = modifying_matrix.asMatrix(interp=1.0)

    return resulting_mmatrix


def matrix_from_variables(tx: float = 0.0, ty: float = 0.0, tz: float = 0.0,
                          rx: float = 0.0, ry: float = 0.0, rz: float = 0.0,
                          sx: float = 1.0, sy: float = 1.0, sz: float = 1.0,
                          ro: int = 1,
                          space: int = om2.MSpace.kWorld) -> tuple:
    """
    Tuple of length of 16 (which corresponds a 4x4 matrix)

    Args:
        tx (float): Translate X component.
        ty (float): Translate Y component.
        tz (float): Translate Z component.

        rx (float): Rotate X component.
        ry (float): Rotate Y component.
        rz (float): Rotate Z component.

        sx (float): Scale X component.
        sy (float): Scale Y component.
        sz (float): Scale Z component.

        ro (int): Rotation order.
        space (int): The space.

    Returns:
        Tuple: Tuple of length of 16 (which corresponds a 4x4 matrix).

    """

    identity_matrix = om2.MMatrix()

    modifying_matrix = om2.MTransformationMatrix(identity_matrix)

    scale_value = (sx, sy, sz)

    euler_rotation = om2.MEulerRotation((rx, ry, rz), order=ro)

    translate_vector = om2.MVector((tx, ty, tz))

    modifying_matrix.setScale(scale_value, space=space)
    modifying_matrix.setRotation(euler_rotation)
    modifying_matrix.setTranslation(translate_vector, space=space)

    resulting_mmatrix = modifying_matrix.asMatrix(interp=1.0)

    return tuple(resulting_mmatrix)


def isolate_rotation_matrix(value: om2.MMatrix) -> om2.MMatrix:
    """
    Uses Matrix Operations to set the Translation to zero and the Scale to 1.
    Thusfore only having Rotation in the Matrix.

    Args:
        value (om2.MMatrix): Value to be changed.

    Returns:
        om2.MMatrix: Value that has its values set to zero.

    """

    value_ = om2.MTransformationMatrix(value)

    value_.setTranslation(om2.MVector(0.0, 0.0, 0.0, ),
                          om2.MSpace.kWorld
                          )

    value_.setScale((1.0, 1.0, 1.0,),
                    om2.MSpace.kWorld
                    )

    value = value_.asMatrix()

    return value


def mirror_jointlike(matrix: tuple,
                     mirror_axis: str,
                     behaviour: bool = True,
                     ) -> tuple:

    """
    Implements mirror behaviour based on the Mirror Joint Tool.

    Args:
        matrix (tuple): The Matrix to be mirrored.
        mirror_axis (str): Axes to be mirrored around as a plane.
        behaviour (bool): If true will mirror the Matrix.

    Returns:
        Tuple (matrix_): Mirrored Matrix.

    """

    mirror_ops = {"YZ": (12, (1, 10, ), (2, 11, )),
                  "ZY": (12, (1, 10, ), (2, 11, )),
                  "XZ": (13, (0, 9, ), (2, 11, )),
                  "ZX": (13, (0, 9, ), (2, 11, )),
                  "XY": (14, (0, 9, ), (1, 10, )),
                  "YX": (14, (0, 9, ), (1, 10, )),
                  }

    matrix_ = list(matrix)

    mirror_axis_ = mirror_ops.get(mirror_axis.upper(), False)

    if not mirror_axis_:
        raise ValueError(f"Your mirror axis was not found in the mirror_ops dict. "
                         f"The keys that are available are {' | '.join(mirror_ops)}"
                         )

    # fold out the values for easier readability
    mirror_translate, mirror_axis_1, mirror_axis_2 = mirror_axis_[0]

    # setting the values
    matrix_[mirror_translate] *= -1

    if not behaviour:
        return tuple(matrix_)

    slice_1, slice_2 = mirror_axis_1
    slice_3, slice_4 = mirror_axis_2

    matrix_[slice_1:slice_2:4] = [n * -1 for n in matrix_[slice_1:slice_2:4]]
    matrix_[slice_3:slice_4:4] = [n * -1 for n in matrix_[slice_3:slice_4:4]]

    return tuple(matrix_)


def mirror_scalewise(matrix: tuple,
                     mirror_axis: str,
                     ) -> tuple:
    """
    Implements mirror behaviour based on Scaling it around an axis.

    Args:
        matrix (tuple): The Matrix to be mirrored.
        mirror_axis (str): The axis to which the matrix should be scaled by.

    Returns:
        Tuple (matrix_): Mirrored Matrix.
    """

    mirror_matrices = {"X": (-1.0, 0.0, 0.0, 0.0,
                             0.0, 1.0, 0.0, 0.0,
                             0.0, 0.0, 1.0, 0.0,
                             0.0, 0.0, 0.0, 1.0,
                             ),

                       "Y": (1.0, 0.0, 0.0, 0.0,
                             0.0, -1.0, 0.0, 0.0,
                             0.0, 0.0, 1.0, 0.0,
                             0.0, 0.0, 0.0, 1.0,
                             ),

                       "Z": (1.0, 0.0, 0.0, 0.0,
                             0.0, 1.0, 0.0, 0.0,
                             0.0, 0.0, -1.0, 0.0,
                             0.0, 0.0, 0.0, 1.0,
                             ),
                       }

    mirror_axis_ = mirror_matrices.get(mirror_axis.upper(), False)

    if not mirror_axis_:
        raise ValueError(f"Your mirror axis was not found in the mirror_ops dict. "
                         f"The keys that are available are {' | '.join(mirror_matrices)}"
                         )

    matrix_api_ = tuple_to_mmatrix(matrix)
    mirror_matrix = tuple_to_mmatrix(mirror_axis_)

    mirrored_matrix = matrix_api_ * mirror_matrix

    return mmatrix_to_tuple(mirrored_matrix)


def get_axis_alignment(object_name: str,
                       axis: str = "+Z",
                       direction_only: bool = True
                       ) -> float:
    """
    Checks the object names matrix against the world axis.
    It is using the dot product for it, so the value ranges between -1 and 1.

    Args:
        object_name (str): Name of the object of which the axis orient should be gathered.
        axis (str): The axis we want to check against in world space.
        direction_only (bool): If direction_only is true, then we do not get the actual values but either -1, 0, or 1.

    Returns:
        Float(dir_check): Checking if the direction is the same.

    """

    axe_vectors = {"+X":  om2.MVector(1.0, 0.0, 0.0),
                   "+Y":  om2.MVector(0.0, 1.0, 0.0),
                   "+Z":  om2.MVector(0.0, 0.0, 1.0),

                   "-X": om2.MVector(-1.0, 0, 0.0),
                   "-Y": om2.MVector(0.0, -1.0, 0.0),
                   "-Z": om2.MVector(0.0, 0.0, -1.0),
                   }

    mtx_vectors = {"+X":  (0, 3),
                   "+Y":  (4, 7),
                   "+Z":  (8, 11),

                   "-X": (0, 3),
                   "-Y": (4, 7),
                   "-Z": (8, 11),
                   }

    axis = axis.upper()

    if axis not in axe_vectors:
        raise LookupError(f"The Axis of : {axis} does not exist in the lookup table of valid axe vectors. "
                          f"Valid options are {' | '.join(axe_vectors.keys())}")

    # convert the matrix from world to a state where it can be used rotational only.
    obj_world_matrix = get_world_matrix(object_name)
    obj_rot_matrix = isolate_rotation_matrix(obj_world_matrix)
    obj_rot_tpl = mmatrix_to_tuple(obj_rot_matrix)

    # get the corresponding info from the lookups
    axe_vec = axe_vectors.get(axis,
                              (1.0, 0.0, 0.0)
                              )

    mtx_axis_start, mtx_axis_end = mtx_vectors.get(axis,
                                                   (0, 3)
                                                   )

    # create a normalized vector out of the matrix rows
    mtx_vec = om2.MVector(obj_rot_tpl[mtx_axis_start:mtx_axis_end]).normalize()

    # dot it together to find out the angle between as dot
    dir_check = mtx_vec * axe_vec

    if not direction_only:
        return dir_check

    if dir_check > 0:
        return 1

    elif dir_check < 0:
        return -1

    elif dir_check == 0:
        return 0

    else:
        raise ValueError("this is for sanity, i do not know if this ever should happen, guess is no!")


def axis_alignment(build_axis, mtx_0_vec, mtx_1_vec, mtx_2_vec):
        ab_vec = mtx_0_vec - mtx_1_vec
        ac_vec = mtx_0_vec - mtx_2_vec

        ab_vec_normalized = ab_vec.normal()
        ac_vec_normalized = ac_vec.normal()

        ab_x_ac_orthogonal = ab_vec_normalized ^ ac_vec_normalized
        ab_x_ac_ac_orthogonal = ab_x_ac_orthogonal ^ ac_vec_normalized

        direction_upper_ = ab_x_ac_ac_orthogonal * build_axis

        upper_direction_mult = (direction_upper_ > 0) - (direction_upper_ < 0)

        return upper_direction_mult



def calculate_distances(lra_mmatrices: tuple) -> tuple:
    """
    AAAA

    Args:
        lra_mmatrices (): .

    Returns:
        Tuple: .

    """

    # combine the matrices
    mmatrices_combined = tuple((lra_mmatrices[x],
                                lra_mmatrices[x + 1]
                                )
                               for x
                               in range(len(lra_mmatrices) - 1)
                               )

    distances = tuple(distance_between_matrices(mmatrix_one,
                                                             mmatric_two
                                                             )
                      for mmatrix_one, mmatric_two
                      in mmatrices_combined
                      )

    total_distance = sum(distances)

    return total_distance, distances


def convert_lra_mtxtuples_to_mmatrices(data_transform_tpls: tuple) -> tuple:
    """
    Turns an iterable of tuples back to a tuple of OpenMaya.MMatrices.

    Args:
        data_transform_tpls (tuple): A tuple of tuples of length 16 each which represents a 4x4 matrix.

    Returns:
        Tuple: The converted mmatrices.

    """

    return tuple(tuple_to_mmatrix(transform)
                 for transform
                 in data_transform_tpls
                 )