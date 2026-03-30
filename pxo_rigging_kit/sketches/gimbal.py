from maya import cmds as cmds


def create_module_groups(control_object, object_base_name):

    initial_position = cmds.xform(control_object, matrix=True, q=True, ws=True)
    object_base_name_adapted = f"{object_base_name}CAPITALIZED"

    parent_object = cmds.createNode("transform",
                                    n=f"{object_base_name_adapted}_GRP".replace("CAPITALIZED",
                                                                                "Module"
                                                                                )
                                    )

    input_name = cmds.createNode("transform",
                                 n=f"{object_base_name_adapted}_GRP".replace("CAPITALIZED",
                                                                             "Input"
                                                                             )
                                 )

    computation_name = cmds.createNode("transform",
                                       n=f"{object_base_name_adapted}_GRP".replace("CAPITALIZED",
                                                                                   "Computation"
                                                                                   )
                                       )

    output_name = cmds.createNode("transform",
                                  n=f"{object_base_name_adapted}_GRP".replace("CAPITALIZED",
                                                                              "Output"
                                                                              )
                                  )

    geometries_name = cmds.createNode("transform",
                                      n=f"{object_base_name_adapted}_GRP".replace("CAPITALIZED",
                                                                                  "Geometry"
                                                                                  )
                                      )

    cmds.parent(input_name, parent_object)
    cmds.parent(computation_name, parent_object)
    cmds.parent(output_name, parent_object)

    cmds.parent(geometries_name, parent_object)

    return computation_name, geometries_name, initial_position, input_name, output_name


def create_offcenter_rotations(object_base_name):

    object_base_name_ = object_base_name

    aim_mtx_0_name = f"{object_base_name_}_0_AIM"
    aim_mtx_1_name = f"{object_base_name_}_1_AIM"
    aim_mtx_2_name = f"{object_base_name_}_2_AIM"

    tfm_0_name = f"{object_base_name_}_0_TFM"
    tfm_1_name = f"{object_base_name_}_1_TFM"
    tfm_2_name = f"{object_base_name_}_2_TFM"

    pick_mtx_name = f"{object_base_name_}_1_PMX"
    pick_aimmtx_name = f"{object_base_name_}_0_PMX"

    vec_prod_name = f"{object_base_name_}_2_VPR"

    offset_pos_0_name = f"{object_base_name_}_0_MMX"
    offset_pos_1_name = f"{object_base_name_}_1_MMX"
    offset_pos_2_name = f"{object_base_name_}_2_MMX"

    aim_offset_mtx_name = f"{object_base_name_}baseAim_2_MMX"

    aim_mmx_name = f"{object_base_name_}_AIMNEG_MMX"

    return_nodes = {"parent_control": {
        "pick_mtx": pick_mtx_name,
        "vec_prod": vec_prod_name,
    },
        "aim_control":                {
            "tfm":            tfm_1_name,
            "mmx":            aim_mmx_name,
            "aim":            aim_mtx_1_name,
            "pick_mtx":       pick_aimmtx_name,
            "aim_offset_mtx": aim_offset_mtx_name,
        },
        "base_control":               {
            "tfm":   tfm_0_name,
            "aim":   aim_mtx_1_name,
            "off_0": offset_pos_0_name,
            "off_1": offset_pos_1_name,
            "off_2": offset_pos_2_name,
        },

        "output":                     {"mtx_one":   aim_mtx_0_name,
                                       "mtx_two":   aim_mtx_1_name,
                                       "mtx_three": aim_mtx_2_name,
                                       },

    }

    # create matrices to points
    base_pos = cmds.createNode("math_TranslationFromMatrix", n=tfm_0_name)

    aim_pos = cmds.createNode("math_TranslationFromMatrix", n=tfm_1_name)

    shape_last_point_pos = cmds.createNode("math_TranslationFromMatrix", n=tfm_2_name)

    # create offset spaces
    base_aim_up = cmds.createNode("composeMatrix")

    rot_location_two = cmds.createNode("composeMatrix")

    rot_location_three = cmds.createNode("composeMatrix")

    # create vectors
    aim_to_base = cmds.createNode("math_SubtractVector")

    aim_to_secondo = cmds.createNode("math_SubtractVector")

    # create pick
    parent_world_rot_mtx = cmds.createNode("pickMatrix", n=pick_mtx_name)
    aim_world_tns_mtx = cmds.createNode("pickMatrix", n=pick_aimmtx_name)

    # create normalization
    aim_ctrl_pos_norm = cmds.createNode("math_NormalizeVector")

    # create add vectors
    add_pos_on_top = cmds.createNode("math_AddVector")

    # create dot
    project_vec_on_rot = cmds.createNode("math_DotProduct")

    # create dot
    rotate_vec_based_on_mtx = cmds.createNode("vectorProduct", n=vec_prod_name)

    # create multiplies
    parent_world_rot_into_ctrl_ws = cmds.createNode("math_MultiplyMatrix", n=aim_mmx_name)

    matrix_mult_1 = cmds.createNode("math_MultiplyMatrix")

    matrix_mult_2 = cmds.createNode("math_MultiplyMatrix", n=aim_offset_mtx_name)

    matrix_mult_3 = cmds.createNode("math_MultiplyMatrix")

    offset_0_mtx = cmds.createNode("math_MultiplyMatrix", n=offset_pos_0_name)
    offset_1_mtx = cmds.createNode("math_MultiplyMatrix", n=offset_pos_1_name)
    offset_2_mtx = cmds.createNode("math_MultiplyMatrix", n=offset_pos_2_name)

    # create aims
    rotation_out_0 = cmds.createNode("aimMatrix", n=aim_mtx_0_name)

    rotation_out_1 = cmds.createNode("aimMatrix", n=aim_mtx_1_name)

    rotation_out_2 = cmds.createNode("aimMatrix", n=aim_mtx_2_name)

    # modify nodes
    cmds.setAttr(f"{rotate_vec_based_on_mtx}.normalizeOutput", True, l=True)
    cmds.setAttr(f"{rotate_vec_based_on_mtx}.operation", 3, l=True)
    cmds.setAttr(f"{rotate_vec_based_on_mtx}.input1Y", 1, l=True)

    cmds.setAttr(f"{parent_world_rot_mtx}.useTranslate", False, l=True)
    cmds.setAttr(f"{parent_world_rot_mtx}.useScale", False, l=True)
    cmds.setAttr(f"{parent_world_rot_mtx}.useShear", False, l=True)

    cmds.setAttr(f"{aim_world_tns_mtx}.useRotate", False, l=True)
    cmds.setAttr(f"{aim_world_tns_mtx}.useScale", False, l=True)
    cmds.setAttr(f"{aim_world_tns_mtx}.useShear", False, l=True)

    cmds.setAttr(f"{base_aim_up}.inputTranslateY", 500, l=True)

    cmds.setAttr(f"{rotation_out_0}.primaryInputAxisX", 0, l=True)
    cmds.setAttr(f"{rotation_out_0}.primaryInputAxisY", 1, l=True)

    cmds.setAttr(f"{rotation_out_0}.secondaryInputAxisX", 1, l=True)
    cmds.setAttr(f"{rotation_out_0}.secondaryInputAxisY", 0, l=True)

    cmds.setAttr(f"{rotation_out_0}.secondaryMode", 1, l=True)
    cmds.setAttr(f"{rotation_out_1}.secondaryMode", 1, l=True)
    cmds.setAttr(f"{rotation_out_2}.secondaryMode", 1, l=True)

    # connect nodes
    cmds.connectAttr(f"{base_pos}.output", f"{aim_to_base}.input1")

    cmds.connectAttr(f"{aim_pos}.output", f"{aim_to_base}.input2")
    cmds.connectAttr(f"{aim_pos}.output", f"{aim_ctrl_pos_norm}.input")

    cmds.connectAttr(f"{rotate_vec_based_on_mtx}.output", f"{project_vec_on_rot}.input1")
    cmds.connectAttr(f"{aim_to_base}.output", f"{project_vec_on_rot}.input2")

    cmds.connectAttr(f"{parent_world_rot_mtx}.outputMatrix", f"{aim_mmx_name}.input1")
    cmds.connectAttr(f"{aim_world_tns_mtx}.outputMatrix", f"{aim_mmx_name}.input2")

    cmds.connectAttr(f"{project_vec_on_rot}.output", f"{add_pos_on_top}.input2Y")
    cmds.connectAttr(f"{aim_ctrl_pos_norm}.output", f"{add_pos_on_top}.input1")

    cmds.connectAttr(f"{add_pos_on_top}.output", f"{rot_location_two}.inputTranslate")

    cmds.connectAttr(f"{rot_location_two}.outputMatrix", f"{matrix_mult_1}.input1")
    cmds.connectAttr(f"{aim_mmx_name}.output", f"{matrix_mult_1}.input2")

    # cmds.connectAttr(f"{offset_pos_0_name}.output", f"{base_pos}.input")

    cmds.connectAttr(f"{base_aim_up}.outputMatrix", f"{aim_offset_mtx_name}.input1")
    cmds.connectAttr(f"{rot_location_three}.outputMatrix", f"{matrix_mult_3}.input1")

    cmds.connectAttr(f"{offset_pos_0_name}.output", f"{rotation_out_0}.inputMatrix")
    cmds.connectAttr(f"{aim_offset_mtx_name}.output", f"{rotation_out_0}.primaryTargetMatrix")
    cmds.connectAttr(f"{matrix_mult_1}.output", f"{rotation_out_0}.secondaryTargetMatrix")

    cmds.connectAttr(f"{offset_pos_1_name}.output", f"{rotation_out_1}.inputMatrix")
    cmds.connectAttr(f"{matrix_mult_3}.output", f"{rotation_out_1}.primaryTargetMatrix")
    cmds.connectAttr(f"{aim_offset_mtx_name}.output", f"{rotation_out_1}.secondaryTargetMatrix")

    cmds.connectAttr(f"{offset_pos_2_name}.output", f"{rotation_out_2}.inputMatrix")

    return return_nodes


def connect_nodes(operating_nodes,
                  input_name,
                  computation_name,
                  output_name,
                  ):

    operating_nodes_ = operating_nodes

    for group_node in (input_name,
                       computation_name,
                       output_name,
                       ):

        # cmds.addAttr(f"{group_node}", ln="mtx_parent", dt="matrix")

        cmds.addAttr(f"{group_node}", ln="mtx_parent", dt="matrix")
        cmds.addAttr(f"{group_node}", ln="mtx_base", dt="matrix")
        cmds.addAttr(f"{group_node}", ln="mtx_aim", dt="matrix")

        cmds.addAttr(f"{group_node}", ln="mtx_0_in", dt="matrix")
        cmds.addAttr(f"{group_node}", ln="mtx_1_in", dt="matrix")
        cmds.addAttr(f"{group_node}", ln="mtx_2_in", dt="matrix")

        cmds.addAttr(f"{group_node}", ln="mtx_0_out", dt="matrix")
        cmds.addAttr(f"{group_node}", ln="mtx_1_out", dt="matrix")
        cmds.addAttr(f"{group_node}", ln="mtx_2_out", dt="matrix")

        cmds.addAttr(f"{group_node}", ln="mtx_0_rot_position_offset", dt="matrix")
        cmds.addAttr(f"{group_node}", ln="mtx_1_rot_position_offset", dt="matrix")
        cmds.addAttr(f"{group_node}", ln="mtx_2_rot_position_offset", dt="matrix")


    pick_mtx = operating_nodes_["parent_control"]["pick_mtx"]
    vec_prod = operating_nodes_["parent_control"]["vec_prod"]

    aim_control_tfm = operating_nodes_["aim_control"]["tfm"]
    aim_control_pmx = operating_nodes_["aim_control"]["pick_mtx"]
    aim_control_aim = operating_nodes_["aim_control"]["aim"]

    tfm = operating_nodes_["base_control"]["tfm"]
    aim = operating_nodes_["base_control"]["aim"]

    offset_0 = operating_nodes_["base_control"]["off_0"]
    offset_1 = operating_nodes_["base_control"]["off_1"]
    offset_2 = operating_nodes_["base_control"]["off_2"]

    mtx_0 = operating_nodes_["output"]["mtx_one"]
    mtx_1 = operating_nodes_["output"]["mtx_two"]
    mtx_2 = operating_nodes_["output"]["mtx_three"]

    mtx_aim_up_offset = operating_nodes_["aim_control"]["aim_offset_mtx"]

    mtx_output_0_name = f"{output_name}.mtx_0_out"
    mtx_output_1_name = f"{output_name}.mtx_1_out"
    mtx_output_2_name = f"{output_name}.mtx_2_out"



    # module preparations
    cmds.connectAttr(f"{input_name}.mtx_base",
                     f"{computation_name}.mtx_base", )

    cmds.connectAttr(f"{input_name}.mtx_parent",
                     f"{computation_name}.mtx_parent", )

    cmds.connectAttr(f"{input_name}.mtx_aim",
                     f"{computation_name}.mtx_aim", )

    cmds.connectAttr(f"{input_name}.mtx_0_rot_position_offset",
                     f"{computation_name}.mtx_0_rot_position_offset",
                     )

    cmds.connectAttr(f"{input_name}.mtx_1_rot_position_offset",
                     f"{computation_name}.mtx_1_rot_position_offset",
                     )

    cmds.connectAttr(f"{input_name}.mtx_2_rot_position_offset",
                     f"{computation_name}.mtx_2_rot_position_offset",
                     )

    # module calculations
    cmds.connectAttr(f"{computation_name}.mtx_base",
                     f"{offset_0}.input2",
                     f=True,
                     )

    cmds.connectAttr(f"{computation_name}.mtx_0_rot_position_offset",
                     f"{offset_0}.input1",
                     f=True,
                     )

    cmds.connectAttr(f"{computation_name}.mtx_base",
                     f"{offset_1}.input2",
                     f=True,
                     )

    cmds.connectAttr(f"{computation_name}.mtx_1_rot_position_offset",
                     f"{offset_1}.input1",
                     f=True,
                     )

    cmds.connectAttr(f"{computation_name}.mtx_base",
                     f"{offset_2}.input2",
                     f=True,
                     )

    cmds.connectAttr(f"{computation_name}.mtx_2_rot_position_offset",
                     f"{offset_2}.input1",
                     f=True,
                     )

    cmds.connectAttr(f"{computation_name}.mtx_parent",
                     f"{pick_mtx}.inputMatrix",
                     f=True,
                     )

    cmds.connectAttr(f"{computation_name}.mtx_parent",
                     f"{vec_prod}.matrix",
                     f=True,
                     )

    cmds.connectAttr(f"{computation_name}.mtx_aim",
                     f"{aim_control_tfm}.input",
                     f=True,
                     )

    cmds.connectAttr(f"{computation_name}.mtx_aim",
                     f"{aim_control_pmx}.inputMatrix",
                     f=True,
                     )

    cmds.connectAttr(f"{computation_name}.mtx_aim",
                     f"{aim_control_aim}.primaryTargetMatrix",
                     f=True,
                     )

    cmds.connectAttr(f"{computation_name}.mtx_base",
                     f"{tfm}.input",
                     f=True,
                     )

    cmds.connectAttr(f"{computation_name}.mtx_base",
                     f"{mtx_aim_up_offset}.input2",
                     f=True,
                     )

    cmds.connectAttr(f"{computation_name}.mtx_base",
                     f"{output_name}.mtx_base", )

    cmds.connectAttr(f"{computation_name}.mtx_aim",
                     f"{output_name}.mtx_aim", )

    cmds.connectAttr(f"{computation_name}.mtx_parent",
                     f"{output_name}.mtx_parent", )
    # module outs
    cmds.connectAttr(f"{mtx_0}.outputMatrix", mtx_output_0_name, f=True, )
    cmds.connectAttr(f"{mtx_1}.outputMatrix", mtx_output_1_name, f=True, )
    cmds.connectAttr(f"{mtx_2}.outputMatrix", mtx_output_2_name, f=True, )

    return mtx_output_0_name, mtx_output_1_name, mtx_output_2_name


def create_geo(object_base_name, geometries_name, output_name):
    for i in range(3):
        mtx_name = f"{object_base_name}Indicator_{str(i)}_GEO"

        cmds.polyCone(n=mtx_name)

        cmds.xform(mtx_name,
                   m=(0, -10, 0, 0,
                      250, 0, 0, 0,
                      0, 0, 10, 0,
                      0, 0, 0, 1,
                      ),
                   )

        cmds.parent(mtx_name, geometries_name)
        cmds.connectAttr(f"{output_name}.mtx_{str(i)}_out", f"{mtx_name}.offsetParentMatrix")

    return True


def create_jnt(object_base_name, output_name):
    jnt_base_name = f"{object_base_name}Base_bnd_C_000_JNT"
    cmds.createNode("joint", n=jnt_base_name)

    cmds.parent(jnt_base_name, output_name)

    cmds.connectAttr(f"{output_name}.mtx_base", f"{jnt_base_name}.offsetParentMatrix")

    for i in range(3):
        jnt_name = f"{object_base_name}_bnd_C_{str(i).zfill(3)}_JNT"

        cmds.createNode("joint", n=jnt_name)

        cmds.parent(jnt_name, output_name)
        cmds.connectAttr(f"{output_name}.mtx_{str(i)}_out", f"{jnt_name}.offsetParentMatrix")

    return True

def connect_to_rotation_controllers(aim_object,
                                    control_object,
                                    parent_object,
                                    object_base_name,
                                    ):
    # create
    (computation_name,
     geometries_name,
     initial_position,
     input_name,
     output_name) = create_module_groups(control_object, object_base_name)

    output_dict = create_offcenter_rotations(object_base_name)

    connect_nodes(output_dict,
                  input_name,
                  computation_name,
                  output_name,
                  )

    #create_geo(object_base_name, geometries_name, output_name)
    create_jnt(object_base_name, output_name)

    aim_locator_name = control_object.replace("ctrl", "loc")
    cmds.spaceLocator(n=aim_locator_name)
    cmds.matchTransform(aim_locator_name, aim_object)
    cmds.parent(aim_locator_name, aim_object)

    cmds.xform(f"{aim_locator_name}", translation=(0.03, 5, 0))
    cmds.setAttr(f"{input_name}.mtx_0_rot_position_offset", (1, 0, 0, 0,
                                                             0, 1, 0, 0,
                                                             0, 0, 1, 0,
                                                             0, -72.829, 0, 1,
                                                             ),
                 type="matrix")

    cmds.connectAttr(f"{control_object}.worldMatrix", f"{input_name}.mtx_base")
    cmds.connectAttr(f"{aim_locator_name}.worldMatrix", f"{input_name}.mtx_aim")

    cmds.connectAttr(f"{parent_object}.worldMatrix", f"{input_name}.mtx_parent")


# set up the main function
def main():
    for i in range(9):

        aim_object = f"backBatteryLight_C_{str(i)}_ctrl"
        control_object = f"backBatteryAnim_C_{str(i)}_ctrl"
        parent_object = f"backBatteryAnim_C{str(i)}_ik_cns"
        object_base_name = f"batteryLightGeoGimbal_{str(i).zfill(3)}_"

        connect_to_rotation_controllers(aim_object,
                                        control_object,
                                        parent_object,
                                        object_base_name, )

    for i in range(28):

        aim_object = f"circleLight_C_{str(i)}_ctrl"
        control_object = f"circleAnim_C_{str(i)}_ctrl"
        parent_object = f"circleAnim_C{str(i)}_ik_cns"
        object_base_name = f"spotLightGeoGimbal_{str(i).zfill(3)}_"

        connect_to_rotation_controllers(aim_object,
                                        control_object,
                                        parent_object,
                                        object_base_name, )


if __name__ == "__main__":
    main()

