from maya import cmds as cmds
from pymel import core as pmc
from importlib import reload
import mtoa.utils as mutils

from pxo_rigging_kit.maya_utils import shader_utils

reload(shader_utils)


def unlock_scales():
    for ctrl in cmds.ls("*_ctrl"):
        for axis_ in "XYZ":
            cmds.setAttr(f"{ctrl}.scale{axis_}", keyable=True, l=False)


def create_light(control_object):
    name_, side_, idx_, suffix_ = control_object.split("_")
    idx_ = idx_.zfill(3)
    object_base_name = f"{side_}_{name_}CAPITALIZED_{idx_}"

    light_module_data = dict()

    initial_position = cmds.xform(control_object, matrix=True, q=True, ws=True)

    parent_object = cmds.createNode("transform", n=f"{object_base_name}_GRP".replace("CAPITALIZED", "Module"))

    input_name = cmds.createNode("transform", n=f"{object_base_name}_GRP".replace("CAPITALIZED", "Input"))

    computation_name = cmds.createNode("transform", n=f"{object_base_name}_GRP".replace("CAPITALIZED", "Computation"))

    output_name = cmds.createNode("transform", n=f"{object_base_name}_GRP".replace("CAPITALIZED", "Output"))

    geometries_name = cmds.createNode("transform", n=f"{object_base_name}_GRP".replace("CAPITALIZED", "Geometry"))

    cmds.parent(input_name, parent_object)
    cmds.parent(output_name, parent_object)
    cmds.parent(computation_name, parent_object)
    cmds.parent(geometries_name, parent_object)

    geo_grp, geo_trs, geo_shp = create_light_geometry(control_object, geometries_name, object_base_name)
    lgt_grp, lgt_trs, lgt_shp = create_light_object(control_object, geometries_name, object_base_name)

    base_transforms_name = "base_transforms"
    cmds.addAttr(input_name, ln=base_transforms_name, at="matrix")
    cmds.setAttr(f"{input_name}.{base_transforms_name}", initial_position, type="matrix")

    base_colors_name = "base_colors"
    cmds.addAttr(input_name, ln=base_colors_name, usedAsColor=True, attributeType='float3')
    cmds.addAttr(input_name, ln='red', attributeType='float', parent=base_colors_name, dv=1)
    cmds.addAttr(input_name, ln='green', attributeType='float', parent=base_colors_name, dv=1)
    cmds.addAttr(input_name, ln='blue', attributeType='float', parent=base_colors_name, dv=1)

    base_aiExposure_name = "base_aiExposure"
    cmds.addAttr(input_name, ln=base_aiExposure_name, at="double")

    base_penumbra_name = "base_penumbra"
    cmds.addAttr(input_name, ln=base_penumbra_name, at="double")

    light_representation_name = "light_representation"
    cmds.addAttr(input_name, ln=light_representation_name, enumName="none:geometry:light", attributeType='enum', k=True,
                 dv=1)

    # computational node
    compute_transforms_name = "compute_transforms"
    cmds.addAttr(computation_name, ln=compute_transforms_name, at="matrix")
    cmds.setAttr(f"{input_name}.{base_transforms_name}", initial_position, type="matrix")
    cmds.connectAttr(f"{input_name}.{base_transforms_name}", f"{computation_name}.{compute_transforms_name}", f=True)

    compute_colors_name = "compute_colors"
    cmds.addAttr(computation_name, ln=compute_colors_name, usedAsColor=True, attributeType='float3')
    cmds.addAttr(computation_name, ln='red', attributeType='float', parent=compute_colors_name, dv=1)
    cmds.addAttr(computation_name, ln='green', attributeType='float', parent=compute_colors_name, dv=1)
    cmds.addAttr(computation_name, ln='blue', attributeType='float', parent=compute_colors_name, dv=1)
    cmds.connectAttr(f"{input_name}.{base_colors_name}", f"{computation_name}.{compute_colors_name}", f=True)

    compute_aiExposure_name = "compute_aiExposure"
    cmds.addAttr(computation_name, ln=compute_aiExposure_name, at="double")
    cmds.connectAttr(f"{input_name}.{base_aiExposure_name}", f"{computation_name}.{compute_aiExposure_name}", f=True)

    compute_penumbra_name = "compute_penumbra"
    cmds.addAttr(computation_name, ln=compute_penumbra_name, at="double")
    cmds.connectAttr(f"{input_name}.{base_penumbra_name}", f"{computation_name}.{compute_penumbra_name}", f=True)

    light_representation_name = "light_representation"
    cmds.addAttr(computation_name, ln=light_representation_name, enumName="none:geometry:light", attributeType='enum',
                 k=True, dv=1)

    cmds.connectAttr(f"{input_name}.{light_representation_name}", f"{computation_name}.{light_representation_name}",
                     f=True)

    # result node
    parent_transforms_name = "base_parent_transforms"
    cmds.addAttr(input_name, ln=parent_transforms_name, at="matrix")

    control_parent = cmds.listRelatives(str(control_object), parent=True)[0]
    cmds.connectAttr(f"{control_parent}.worldMatrix[0]", f"{input_name}.{parent_transforms_name}", f=True)

    result_transforms_name = "result_transforms"
    cmds.addAttr(output_name, ln=result_transforms_name, at="matrix")
    cmds.connectAttr(f"{computation_name}.{compute_transforms_name}", f"{output_name}.{result_transforms_name}", f=True)

    result_aiExposure_name = "result_aiExposure"
    cmds.addAttr(output_name, ln=result_aiExposure_name, at="double")
    cmds.connectAttr(f"{computation_name}.{compute_aiExposure_name}", f"{output_name}.{result_aiExposure_name}", f=True)

    result_penumbra_name = "result_penumbra"
    cmds.addAttr(output_name, ln=result_penumbra_name, at="double")
    cmds.connectAttr(f"{computation_name}.{compute_penumbra_name}", f"{output_name}.{result_penumbra_name}", f=True)

    result_colors_name = "result_colors"
    cmds.addAttr(output_name, ln=result_colors_name, usedAsColor=True, attributeType='float3')

    cmds.addAttr(output_name, ln='red', attributeType='float', parent=result_colors_name)
    cmds.addAttr(output_name, ln='green', attributeType='float', parent=result_colors_name)
    cmds.addAttr(output_name, ln='blue', attributeType='float', parent=result_colors_name)

    light_representation_name = "light_representation"
    cmds.addAttr(output_name, ln=light_representation_name, enumName="none:geometry:light", attributeType='enum',
                 k=True, dv=1)

    cmds.connectAttr(f"{computation_name}.{light_representation_name}", f"{output_name}.{light_representation_name}",
                     f=True)

    create_switching_network(f"{output_name}.{light_representation_name}", (geo_grp, lgt_grp))

    #
    cmds.connectAttr(f"{computation_name}.{compute_colors_name}", f"{output_name}.{result_colors_name}", f=True)
    cmds.connectAttr(f"{output_name}.{result_colors_name}.red", f"{lgt_shp}.color.colorR", f=True)
    cmds.connectAttr(f"{output_name}.{result_colors_name}.green", f"{lgt_shp}.color.colorG", f=True)
    cmds.connectAttr(f"{output_name}.{result_colors_name}.blue", f"{lgt_shp}.color.colorB", f=True)

    # connect stuuuff
    cmds.connectAttr(f"{output_name}.{result_transforms_name}", f"{geo_grp}.offsetParentMatrix", f=True)
    cmds.connectAttr(f"{output_name}.{result_transforms_name}", f"{lgt_grp}.offsetParentMatrix", f=True)

    light_module_data["input"] = input_name
    light_module_data["input_base_trs"] = base_transforms_name
    light_module_data["input_parent_trs"] = parent_transforms_name

    light_module_data["input_lgt_color"] = base_colors_name

    light_module_data["output"] = output_name
    light_module_data["output_trs"] = result_transforms_name

    light_module_data["output_lgt_color"] = result_colors_name

    light_module_data["compute"] = computation_name
    light_module_data["compute_trs"] = compute_transforms_name
    light_module_data["compute_lgt_color"] = compute_colors_name

    light_module_data["geo"] = geo_trs
    light_module_data["lgt"] = lgt_trs

    return light_module_data


def create_switching_network(input_attr, nodes):
    for iteration_, node in enumerate(nodes):
        node_name = node.replace("TRS", "CPI")
        cmds.createNode("math_CompareInt", n=node_name)

        cmds.setAttr(f"{node_name}.input2", iteration_ + 1)
        cmds.setAttr(f"{node_name}.operation", 0)

        cmds.connectAttr(f"{input_attr}", f"{node_name}.input1", f=True)

        cmds.connectAttr(f"{node_name}.output", f"{node}.visibility", f=True)


def create_light_geometry(control_object, parent_object, object_base_name):

    uber_grp = cmds.createNode("transform", n=f"{object_base_name}_TRS".replace("CAPITALIZED", "GeoInput"))
    cone_trs, cone_shp = cmds.polyCone(n=f"{object_base_name}_GEO".replace("CAPITALIZED", "GeoCone"))

    cmds.xform(cone_trs, ro=(180, 0, 0), t=(0, 1, 0))

    cmds.parent(cone_trs, uber_grp)
    cmds.parent(uber_grp, parent_object)

    cmds.setAttr(f"{cone_trs}.overrideEnabled", 1)

    for attr_ in ("castsShadows",
                  "receiveShadows",
                  "primaryVisibility",
                  "smoothShading",
                  "visibleInReflections",
                  "visibleInRefractions"):

        cmds.setAttr(f"{cone_trs}.{attr_}", False)

    return uber_grp, cone_trs, cone_shp


def create_light_object(control_object, parent_object, object_base_name):
    uber_grp = cmds.createNode("transform", n=f"{object_base_name}_TRS".replace("CAPITALIZED", "LightInput"))
    light_shp = mutils.createLocator("spotLight", asLight=True)[0]

    light_trs = cmds.listRelatives(str(light_shp), parent=True)
    light_trs_name = f"{object_base_name}_LGT".replace("CAPITALIZED", "LightCone")
    cmds.rename(light_trs, light_trs_name)
    light_shp = cmds.listRelatives(light_trs_name, children=True)[0]

    cmds.xform(light_trs_name, ro=(90, 0, 0), s=(1.5385, 1.5385, 1.5385,))

    cmds.parent(light_trs_name, uber_grp)
    cmds.parent(uber_grp, parent_object)

    create_cone_angle_interpolation(light_shp, object_base_name, uber_grp)

    cmds.setAttr(f"{light_trs_name}.overrideEnabled", 1)

    cmds.connectAttr(f"{light_shp}.instObjGroups", "defaultLightSet.dagSetMembers", nextAvailable=True, f=True)

    return uber_grp, light_trs_name, light_shp


def create_cone_angle_interpolation(light_shp, object_base_name, uber_grp):
    bottom_grp = cmds.createNode("transform", n=f"{object_base_name}_TRS".replace("CAPITALIZED", "angleCalcBot"))
    upper_grp = cmds.createNode("transform", n=f"{object_base_name}_TRS".replace("CAPITALIZED", "angleCalcTop"))
    outter_grp = cmds.createNode("transform", n=f"{object_base_name}_TRS".replace("CAPITALIZED", "angleCalcOut"))

    cmds.parent([bottom_grp, upper_grp, outter_grp], uber_grp)

    cmds.xform(upper_grp, t=(0, 2, 0))
    cmds.xform(outter_grp, t=(1, 2, 0))
    bottom_trans = cmds.createNode("math_TranslationFromMatrix", n=bottom_grp.replace("TRS", "TFM"))
    upper_trans = cmds.createNode("math_TranslationFromMatrix", n=upper_grp.replace("TRS", "TFM"))
    outter_trans = cmds.createNode("math_TranslationFromMatrix", n=outter_grp.replace("TRS", "TFM"))

    bottom_to_upper = cmds.createNode("math_SubtractVector", n=upper_grp.replace("TRS", "SUB"))
    bottom_to_outter = cmds.createNode("math_SubtractVector", n=outter_grp.replace("TRS", "SUB"))

    angle_between = cmds.createNode("math_AngleBetweenVectors", n=bottom_grp.replace("TRS", "ABV"))

    angle_times_two = cmds.createNode("math_MultiplyAngleByInt", n=bottom_grp.replace("TRS", "MLA"))

    cmds.connectAttr(f"{bottom_grp}.worldMatrix", f"{bottom_trans}.input")
    cmds.connectAttr(f"{upper_grp}.worldMatrix", f"{upper_trans}.input")
    cmds.connectAttr(f"{outter_grp}.worldMatrix", f"{outter_trans}.input")

    cmds.connectAttr(f"{bottom_trans}.output", f"{bottom_to_upper}.input1")
    cmds.connectAttr(f"{upper_trans}.output", f"{bottom_to_upper}.input2")

    cmds.connectAttr(f"{bottom_trans}.output", f"{bottom_to_outter}.input1")
    cmds.connectAttr(f"{outter_trans}.output", f"{bottom_to_outter}.input2")

    cmds.connectAttr(f"{bottom_to_upper}.output", f"{angle_between}.input1")
    cmds.connectAttr(f"{bottom_to_outter}.output", f"{angle_between}.input2")

    cmds.connectAttr(f"{angle_between}.output", f"{angle_times_two}.input1")

    cmds.setAttr(f"{angle_times_two}.input2", 2)

    cmds.connectAttr(f"{angle_times_two}.output", f"{light_shp}.coneAngle")


def create_lights(light_controls):
    operations_dict = dict()

    for light_control in light_controls:
        light_info = create_light(light_control)
        operations_dict[light_control] = light_info

    return operations_dict


def connect_lights_to_controls(light_modules, master_control):

    # color
    base_colors_name = "override_colors"
    cmds.addAttr(master_control, ln=base_colors_name, usedAsColor=True, attributeType='float3', k=True)
    cmds.addAttr(master_control, ln='red', attributeType='float', parent=base_colors_name, dv=1, k=True)
    cmds.addAttr(master_control, ln='green', attributeType='float', parent=base_colors_name, dv=1, k=True)
    cmds.addAttr(master_control, ln='blue', attributeType='float', parent=base_colors_name, dv=1, k=True)

    for key_, values_ in light_modules.items():

        cmds.connectAttr(f"{master_control}.{base_colors_name}", f"{values_['input']}.{values_['input_lgt_color']}")

        color_blend = cmds.createNode("blendColors", n=key_.replace("TRS", "BLC"))

        vis_seperator_name = "visibility_attributes"
        cmds.addAttr(key_, ln=vis_seperator_name, enumName="########", attributeType='enum', k=False)
        cmds.setAttr(f"{key_}.{vis_seperator_name}", cb=True, l=True)

        override_type_name = "override_type"
        cmds.addAttr(key_, ln=override_type_name, enumName="normal:template:reference", attributeType='enum', k=True,
                     dv=2)

        light_representation_name = "light_representation"
        cmds.addAttr(key_, ln=light_representation_name, enumName="none:geometry:light", attributeType='enum', k=True,
                     dv=1)

        seperator_name = "color_attributes"
        cmds.addAttr(key_, ln=seperator_name, enumName="########", attributeType='enum', k=False)
        cmds.setAttr(f"{key_}.{seperator_name}", cb=True, l=True)

        override_blend_name = "color_override_blend"
        cmds.addAttr(key_, ln=override_blend_name, dv=0, attributeType='double', k=True, hnv=True, hxv=True, min=0,
                     max=1)

        base_colors_name = "override_colors"

        cmds.addAttr(key_, ln=base_colors_name, usedAsColor=True, attributeType='float3', k=True)
        cmds.addAttr(key_, ln='red', attributeType='float', parent=base_colors_name, dv=1, k=True)
        cmds.addAttr(key_, ln='green', attributeType='float', parent=base_colors_name, dv=1, k=True)
        cmds.addAttr(key_, ln='blue', attributeType='float', parent=base_colors_name, dv=1, k=True)

        cmds.connectAttr(f"{values_['compute']}.{values_['compute_lgt_color']}", f"{color_blend}.color2")
        cmds.connectAttr(f"{key_}.{base_colors_name}", f"{color_blend}.color1")
        cmds.connectAttr(f"{key_}.{override_blend_name}", f"{color_blend}.blender")

        cmds.connectAttr(f"{key_}.{light_representation_name}", f"{values_['input']}.{light_representation_name}",
                         force=True)

        cmds.connectAttr(f"{color_blend}.output", f"{values_['output']}.{values_['output_lgt_color']}", force=True)

        for axis_ in "XYZ":
            cmds.setAttr(f"{key_}.scale{axis_}", 600)

        cmds.setAttr(f"{key_}.inheritsTransform", False)
        cmds.connectAttr(f"{values_['compute']}.{values_['compute_trs']}", f"{key_}.offsetParentMatrix", force=True)
        cmds.connectAttr(f"{key_}.worldMatrix[0]", f"{values_['output']}.{values_['output_trs']}", force=True)

        cmds.connectAttr(f"{key_}.{override_type_name}", f"{values_['geo']}.overrideDisplayType", force=True)
        cmds.connectAttr(f"{key_}.{override_type_name}", f"{values_['lgt']}.overrideDisplayType", force=True)


def connect_light_geo_to_shaders(light_modules):
    shader_utils.clear()

    for key_, values_ in light_modules.items():
        checker_object, checker_mat = shader_utils.assign_ramp_shader(pmc.PyNode(values_["geo"]),
                                                                      material_name=f"{values_['input']}_msMat")

        seperator_name = "viewport_exposure_attributes"
        cmds.addAttr(key_, ln=seperator_name, enumName="########", attributeType='enum', k=False)
        cmds.setAttr(f"{key_}.{seperator_name}", cb=True, l=True)

        viewport_exposure_name = "viewport_exposure"
        cmds.addAttr(key_, ln=viewport_exposure_name, attributeType='float3', usedAsColor=True, k=False)
        cmds.addAttr(key_, ln='R', attributeType='float', parent=viewport_exposure_name, k=False)
        cmds.addAttr(key_, ln='G', attributeType='float', parent=viewport_exposure_name, k=False)
        cmds.addAttr(key_, ln='B', attributeType='float', parent=viewport_exposure_name, k=False)

        cmds.addAttr(key_, ln='viewport_exposure_darken', attributeType='float', dv=0, k=True, hnv=True, hxv=True,
                     min=0, max=1)
        cmds.connectAttr(f"{key_}.viewport_exposure_darken", f"{key_}.{viewport_exposure_name}.R")
        cmds.connectAttr(f"{key_}.viewport_exposure_darken", f"{key_}.{viewport_exposure_name}.G")
        cmds.connectAttr(f"{key_}.viewport_exposure_darken", f"{key_}.{viewport_exposure_name}.B")

        pmc.PyNode(key_).attr(viewport_exposure_name).connect(
                checker_object.outTransparency.listConnections()[0].colorEntryList[1].color, f=True)

        pmc.PyNode(values_["output"]).attr(values_["output_lgt_color"]).connect(checker_object.outColor)


def build_advanced_controls(light_modules, aim_controls):
    for key_, values_ in light_modules.items():
        aim_items = [key_.replace("Light_", "LightAim_")]
        aim_items.extend(aim_controls)

        default_bld_mtx = cmds.createNode("blendMatrix", n=values_['input'].replace("GRP", "BDM"))

        mul_mtx = cmds.createNode("math_MultiplyMatrix", n=values_['input'].replace("GRP", "MTM"))

        comp_mtx = cmds.createNode("composeMatrix", n=values_['input'].replace("GRP", "CPM"))
        cmds.setAttr(f"{comp_mtx}.inputTranslateX", 10)

        cmds.connectAttr(f"{values_['input']}.{values_['input_base_trs']}", f"{mul_mtx}.input2")
        cmds.connectAttr(f"{comp_mtx}.outputMatrix", f"{mul_mtx}.input1")

        cmds.connectAttr(f"{values_['input']}.{values_['input_base_trs']}", f"{default_bld_mtx}.inputMatrix")

        blend_weight_names = list()

        for iteration_, aim_control in enumerate(aim_items):
            blend_weight_name = f"{aim_control}_blendWeight"
            blend_weight_names.append(blend_weight_name)

            cmds.addAttr(values_['input'], ln=blend_weight_name, attributeType='double', dv=0, k=True, hnv=True,
                         hxv=True, min=-1,
                         max=1)

            aim_mtx = cmds.createNode("aimMatrix", n=aim_control.replace("ctrl", "AIM"))

            cmds.setAttr(f"{aim_mtx}.primaryInputAxisX", 0)
            cmds.setAttr(f"{aim_mtx}.primaryInputAxisY", 1)
            cmds.setAttr(f"{aim_mtx}.primaryInputAxisZ", 0)

            cmds.setAttr(f"{aim_mtx}.secondaryInputAxisX", 1)
            cmds.setAttr(f"{aim_mtx}.secondaryInputAxisY", 0)
            cmds.setAttr(f"{aim_mtx}.secondaryInputAxisZ", 0)

            cmds.setAttr(f"{aim_mtx}.secondaryMode", 1)

            cmds.connectAttr(f"{values_['input']}.{values_['input_base_trs']}", f"{aim_mtx}.inputMatrix")
            cmds.connectAttr(f"{aim_control}.worldMatrix[0]", f"{aim_mtx}.primaryTargetMatrix")

            cmds.connectAttr(f"{mul_mtx}.output", f"{aim_mtx}.secondaryTargetMatrix")

            cmds.connectAttr(f"{aim_mtx}.outputMatrix", f"{default_bld_mtx}.target[{str(iteration_)}].targetMatrix")
            cmds.connectAttr(f"{values_['input']}.{blend_weight_name}",
                             f"{default_bld_mtx}.target[{str(iteration_)}].weight")

        cmds.connectAttr(f"{default_bld_mtx}.outputMatrix", f"{values_['compute']}.{values_['compute_trs']}", f=True)
        values_["input_space_weights"] = blend_weight_names

    return light_modules


def connect_transform_sys_to_controls(light_modules):
    for key_, values_ in light_modules.items():

        seperator_name = "space_attributes"
        cmds.addAttr(key_, ln=seperator_name, enumName="########", attributeType='enum', k=False)
        cmds.setAttr(f"{key_}.{seperator_name}", cb=True, l=True)

        for iteration_, i in enumerate(values_["input_space_weights"]):

            blend_weight_name = f"blendWeight_{str(iteration_).zfill(3)}"
            cmds.addAttr(key_, ln=blend_weight_name, niceName=i, attributeType='double', dv=0, k=True, hnv=True,
                         hxv=True, min=-1,
                         max=1)

            cmds.connectAttr(f"{key_}.{blend_weight_name}", f"{values_['input']}.{i}")


def create_mesh_lights():
    cmds.select(cl=True)

    mesh_nodes = set([cmds.listRelatives(x, parent=True)[0]
                      for x in cmds.ls(type="mesh")
                      if not "_proxy" in x
                      ]
                     )

    uber_names = set([x.split(":")[-1].split("_")[0]
                      for x in mesh_nodes
                      ])

    mesh_lights_grouped = {uber_name_: [] for uber_name_ in uber_names}

    for i in set(mesh_nodes):

        uber_name = i.split(":")[-1].split("_")[0]

        cmds.select(i)
        mtoa.utils.createMeshLight()
        light_tansform = cmds.ls(sl=True)[0]
        light_name = f"{light_tansform.split(':')[-1].replace('render_geo', 'MLGT')}"
        light_name_deconstructed = light_name.split("_")

        light_name = f"{light_name_deconstructed[1]}_{light_name_deconstructed[0]}_{light_name_deconstructed[2]}_{light_name_deconstructed[3]}"

        cmds.rename(light_tansform, light_name)

        light_tansform = light_name

        light_shape = cmds.listRelatives(light_tansform, parent=True)[0]

        cmds.parent(light_tansform, world=True)
        mesh_lights_grouped[uber_name].append(light_name)

        cmds.select(cl=True)

    return mesh_lights_grouped


def connect_mesh_lights(mesh_lights, master_control):

    base_colors_name = "override_mesh_colors"
    cmds.addAttr(master_control, ln=base_colors_name, usedAsColor=True, attributeType='float3', k=True)
    cmds.addAttr(master_control, ln=f'{base_colors_name}Red', attributeType='float', parent=base_colors_name, dv=1,
                 k=True)
    cmds.addAttr(master_control, ln=f'{base_colors_name}Green', attributeType='float', parent=base_colors_name, dv=1,
                 k=True)
    cmds.addAttr(master_control, ln=f'{base_colors_name}Blue', attributeType='float', parent=base_colors_name, dv=1,
                 k=True)

    light_representation_name = "light_representation"

    for key_, value_ in mesh_lights.items():

        controller_name = f"{key_}_C_0_ctrl"

        if cmds.objExists(controller_name):
            pass

        else:
            controller_name = "podLights_C_0_ctrl"

        if not cmds.attributeQuery(light_representation_name, node=controller_name, exists=True):

            cmds.addAttr(controller_name,
                         ln=light_representation_name,
                         enumName="none:geometry:light",
                         attributeType="enum",
                         k=True, dv=1
                         )

            cmds.addAttr(controller_name, ln=base_colors_name, usedAsColor=True, attributeType='float3', k=True)
            cmds.addAttr(controller_name, ln=f'{base_colors_name}Red', attributeType='float', parent=base_colors_name,
                         dv=1, k=True)
            cmds.addAttr(controller_name, ln=f'{base_colors_name}Green', attributeType='float', parent=base_colors_name,
                         dv=1, k=True)
            cmds.addAttr(controller_name, ln=f'{base_colors_name}Blue', attributeType='float', parent=base_colors_name,
                         dv=1, k=True)

        for v_ in value_:

            visibility_geo_choice = cmds.createNode("math_CompareInt", n=v_.replace("MLGT", "geo_COND"))

            light_colors_bld = cmds.createNode("blendColors", n=v_.replace("MLGT", "BLDC"))

            visibility_lgt_choice = cmds.createNode("math_CompareInt", n=v_.replace("MLGT", "light_COND"))

            cmds.connectAttr(f"{controller_name}.{light_representation_name}", f"{visibility_geo_choice}.input1")
            cmds.connectAttr(f"{controller_name}.{light_representation_name}", f"{visibility_lgt_choice}.input1")

            cmds.setAttr(f"{visibility_geo_choice}.input2", 2)
            cmds.setAttr(f"{visibility_lgt_choice}.input2", 1)

            cmds.connectAttr(f"{visibility_geo_choice}.output", f"{v_}.visibility")
            cmds.connectAttr(f"{visibility_lgt_choice}.output", f"{v_}Shape.showOriginalMesh")

            mat_, shd_ = shader_utils.assign_shader(
                    object_to_shade=pmc.PyNode(v_).getShape().attr("inMesh").listConnections()[0].getParent(),
                    material_name=v_,
                    material_type="surfaceShader",
                    material_color=(1, 0.5, 0.5),
                    material_transp=(0, 0, 0),
                    material_refl=(0, 0, 0),
            )

            cmds.connectAttr(f"{master_control}.{base_colors_name}", f"{light_colors_bld}.color1")
            cmds.connectAttr(f"{controller_name}.{base_colors_name}", f"{light_colors_bld}.color2")

            pmc.PyNode(light_colors_bld).attr("output").connect(mat_.outColor)


def sort_mesh_lights(mesh_lights):
    for key_, value_ in mesh_lights.items():
        cmds.group(value_, n=f"C_meshLight{key_}_000_GRP")


def tag_mesh_lights(mesh_lights):
    for key_, value_ in mesh_lights.items():
        for light_ in value_:
            cmds.setAttr(f"{light_}Shape.aiAov", key_, type="string", )


def mesh_lights_to_set(mesh_lights):
    for key_, value_ in mesh_lights.items():

        shapes_ = [cmds.listRelatives(val_, shapes=True)[0] for val_ in value_]

        mesh_light_set_name = f"_{key_}_"
        cmds.sets(empty=True, name=mesh_light_set_name, )
        cmds.sets(shapes_, edit=True, forceElement=mesh_light_set_name)
        cmds.sets(value_, edit=True, forceElement=mesh_light_set_name)

        cmds.sets(mesh_light_set_name, edit=True, forceElement="_light_selects_")


def lights_to_set():

    light_names = cmds.ls(type="light")

    light_name_bases = [lgt.split("_")[1] for lgt in light_names]
    light_name_prefix = [lgt.split("_")[0] for lgt in light_names]

    sort_names_helper = zip(light_name_prefix, light_name_bases, light_names)

    resultdict = {light_name: {"C": [], "R": [], "L": []} for light_name in set(light_name_bases)}

    for sorted_tripples in sort_names_helper:
        resultdict[sorted_tripples[1]][sorted_tripples[0]].append(sorted_tripples[-1])

    cmds.select(cl=True)

    cmds.sets(empty=True, name="additional_container_publishes_set", )
    cmds.sets("additional_container_publishes_set", edit=True, forceElement="pxm_rig_root_set")

    cmds.sets(empty=True, name="_light_selects_")
    cmds.sets("_light_selects_", edit=True, forceElement="additional_container_publishes_set")

    for key__, value__ in resultdict.items():
        name_set = f"_{key__.replace('Light', '').replace('Cone', '')}_"
        cmds.sets(empty=True, name=name_set, )

        for k_, v_ in value__.items():
            if not v_:
                continue
            name_subset = f"_{k_}_{key__.replace('Light', '').replace('Cone', '')}_"
            name_subset_aov_name = f"{k_}_{key__.replace('Light', '').replace('Cone', '')}"

            cmds.sets(empty=True, name=name_subset)

            cmds.sets(name_subset, edit=True, forceElement=name_set)
            cmds.sets(v_, edit=True, forceElement=name_subset)

            light_shape = cmds.listRelatives(v_, parent=True)[0]
            cmds.sets(light_shape, edit=True, forceElement=name_subset)

            for lgts_ in v_:
                cmds.setAttr(f"{lgts_}.aiAov", name_subset_aov_name, type="string", )

        cmds.sets(name_set, edit=True, forceElement="_light_selects_")
    return resultdict


light_controls = cmds.ls("*Light_*_ctrl")
aim_controls = cmds.ls("aimControl_*_*_ctrl")

unlock_scales()

mesh_lights = create_mesh_lights()
sort_mesh_lights(mesh_lights)

light_modules = create_lights(light_controls)

connect_lights_to_controls(light_modules, "openerHost_C_0_ctrl")
connect_light_geo_to_shaders(light_modules)
light_modules = build_advanced_controls(light_modules, aim_controls)

connect_transform_sys_to_controls(light_modules)

lights_to_set()
tag_mesh_lights(mesh_lights)
mesh_lights_to_set(mesh_lights)
connect_mesh_lights(mesh_lights, "openerHost_C_0_ctrl")