from maya import cmds as cmds
from pymel import core as pmc
from importlib import reload
import mtoa.utils as mutils
from pprint import pprint
from pxo_rigging_kit.maya_utils import shader_utils
from pxo_rigging_kit import constants

reload(shader_utils)

RESOLUTION_TYPE = "proxy"


def get_selected():
    sel = pmc.selected()

    transforms_to_convert = [x.getShape() if pmc.objectType(x, isAType="transform") else x for x in sel]

    light_objects = [x for x in transforms_to_convert if pmc.objectType(x) in ("light", "aiMeshLight")]

    return light_objects


def unlock_scales():
    for ctrl in cmds.ls("*_ctrl"):
        for axis_ in "XYZ":
            cmds.setAttr(f"{ctrl}.scale{axis_}", keyable=True, l=False)


def pxo_poly_cylinder(n=None):
    """
    Wrapper for the polyCylinder that creates a cylinder that is minimal density.

    Args:
        n(None, str): the name of the cylinder

    Returns:

    """
    name_ = n or "default_C_000_GEO"

    cone_trs, cone_shp = cmds.polyCylinder(n=name_,
                                           r=1,
                                           h=2,
                                           sx=6,
                                           sy=1,
                                           sz=1,
                                           ax=(0, 1, 0,),
                                           rcp=0,
                                           cuv=3,
                                           ch=1,
                                           )

    cmds.select(f'{name_}.e[18]',
                f'{name_}.e[20]',
                f'{name_}.e[22]',
                f'{name_}.e[24]',
                f'{name_}.e[26]',
                f'{name_}.e[28]',
                )

    cmds.polyDelEdge(cv=False)

    cmds.delete(cone_trs, constructionHistory=True)

    return cone_trs, cone_shp


def create_light(light_type, control_object):
    name_, side_, idx_, suffix_ = control_object.split("_")
    idx_ = idx_.zfill(3)
    object_base_name = f"{side_}_{name_}CAPITALIZED_{idx_}"

    light_module_data = dict()

    (computation_name,
     geometries_name,
     initial_position,
     input_name,
     output_name) = create_module_groups(control_object, object_base_name)

    if "laser" in name_.lower():
        geo_grp, geo_trs, geo_shp = create_light_geometry(geometries_name, object_base_name, func=pxo_poly_cylinder)
        lgt_grp, lgt_trs, lgt_shp = create_light_mesh(geo_trs, object_base_name, )

    elif "light" in name_.lower():
        geo_grp, geo_trs, geo_shp = create_light_geometry(geometries_name, object_base_name, func=cmds.polyCone)
        lgt_grp, lgt_trs, lgt_shp = create_light_object(geometries_name, object_base_name, )

    transforms_name = "module_transforms"

    parent_transforms_name = "module_parent_transforms"

    colors_name = "module_colors"

    ai_exposure_name = "module_aiExposure"

    penumbra_name = "module_penumbra"

    light_representation_name = "module_light_representation"

    set_modulestep_attributes(module_name=input_name,
                              initial_position=initial_position,
                              transforms_name=transforms_name,
                              parent_transforms_name=parent_transforms_name,
                              colors_name=colors_name,
                              ai_exposure_name=ai_exposure_name,
                              penumbra_name=penumbra_name,
                              light_representation_name=light_representation_name,
                              )

    set_modulestep_attributes(module_name=computation_name,
                              initial_position=initial_position,
                              transforms_name=transforms_name,
                              parent_transforms_name=parent_transforms_name,
                              colors_name=colors_name,
                              ai_exposure_name=ai_exposure_name,
                              penumbra_name=penumbra_name,
                              light_representation_name=light_representation_name,
                              )

    set_modulestep_attributes(module_name=output_name,
                              initial_position=initial_position,
                              transforms_name=transforms_name,
                              parent_transforms_name=parent_transforms_name,
                              colors_name=colors_name,
                              ai_exposure_name=ai_exposure_name,
                              penumbra_name=penumbra_name,
                              light_representation_name=light_representation_name,
                              )

    # control to input
    control_anim_offset_parent = control_object.replace("Light", "Anim").replace("Laser", "Anim")

    if cmds.objExists(control_anim_offset_parent):
        cmds.connectAttr(f"{control_anim_offset_parent}.worldMatrix[0]",
                         f"{input_name}.{transforms_name}",
                         f=True
                         )

    connect_modulesteps(ai_exposure_name=ai_exposure_name,
                        colors_name=colors_name,
                        computation_name=computation_name,
                        input_name=input_name,
                        light_representation_name=light_representation_name,
                        penumbra_name=penumbra_name,
                        transforms_name=transforms_name,
                        )

    connect_modulesteps(ai_exposure_name=ai_exposure_name,
                        colors_name=colors_name,
                        computation_name=output_name,
                        input_name=computation_name,
                        light_representation_name=light_representation_name,
                        penumbra_name=penumbra_name,
                        transforms_name=transforms_name,
                        )

    create_switching_network(f"{output_name}.{light_representation_name}",
                             (geo_grp,
                              lgt_grp
                              )
                             )

    #
    cmds.connectAttr(f"{output_name}.{colors_name}.red",
                     f"{lgt_shp}.color.colorR",
                     f=True
                     )

    cmds.connectAttr(f"{output_name}.{colors_name}.green",
                     f"{lgt_shp}.color.colorG",
                     f=True
                     )

    cmds.connectAttr(f"{output_name}.{colors_name}.blue",
                     f"{lgt_shp}.color.colorB",
                     f=True
                     )

    cmds.connectAttr(f"{output_name}.{transforms_name}",
                     f"{lgt_grp}.offsetParentMatrix",
                     f=True
                     )

    # connect stuuuff
    cmds.connectAttr(f"{output_name}.{transforms_name}",
                     f"{geo_grp}.offsetParentMatrix",
                     f=True
                     )

    # create outputs
    light_module_data["input"] = input_name
    light_module_data["input_base_trs"] = transforms_name
    light_module_data["input_parent_trs"] = parent_transforms_name

    light_module_data["input_lgt_color"] = colors_name

    light_module_data["output"] = output_name
    light_module_data["output_trs"] = transforms_name

    light_module_data["output_lgt_color"] = colors_name

    light_module_data["compute"] = computation_name
    light_module_data["compute_trs"] = transforms_name
    light_module_data["compute_lgt_color"] = colors_name

    light_module_data["geo"] = geo_trs

    light_module_data["lgt"] = lgt_trs
    light_module_data["lgt_shape"] = lgt_shp

    return light_module_data


def connect_modulesteps(input_name=None,
                        ai_exposure_name=None,
                        colors_name=None,
                        computation_name=None,
                        light_representation_name=None,
                        parent_transforms_name=None,
                        penumbra_name=None,
                        transforms_name=None,
                        ):

    if not any((input_name,
                ai_exposure_name,
                colors_name,
                computation_name,
                light_representation_name,
                parent_transforms_name,
                penumbra_name,
                transforms_name,)):
        return

    # input to computation
    cmds.connectAttr(f"{input_name}.{transforms_name}",
                     f"{computation_name}.{transforms_name}",
                     f=True
                     )
    cmds.connectAttr(f"{input_name}.{colors_name}",
                     f"{computation_name}.{colors_name}",
                     f=True
                     )
    cmds.connectAttr(f"{input_name}.{ai_exposure_name}",
                     f"{computation_name}.{ai_exposure_name}",
                     f=True
                     )
    cmds.connectAttr(f"{input_name}.{penumbra_name}",
                     f"{computation_name}.{penumbra_name}",
                     f=True
                     )
    cmds.connectAttr(f"{input_name}.{light_representation_name}",
                     f"{computation_name}.{light_representation_name}",
                     f=True
                     )
    return True


def set_modulestep_attributes(initial_position=None,
                              module_name=None,
                              transforms_name=None,
                              parent_transforms_name=None,
                              colors_name=None,
                              ai_exposure_name=None,
                              penumbra_name=None,
                              light_representation_name=None,
                              ):

    if not any((initial_position,
                module_name,
                transforms_name,
                parent_transforms_name,
                colors_name,
                ai_exposure_name,
                penumbra_name,
                light_representation_name,)):

        return

    cmds.addAttr(module_name,
                 longName=transforms_name,
                 at="matrix"
                 )
    cmds.setAttr(f"{module_name}.{transforms_name}",
                 initial_position,
                 type="matrix"
                 )

    cmds.addAttr(module_name,
                 longName=parent_transforms_name,
                 at="matrix"
                 )

    cmds.addAttr(module_name,
                 longName=colors_name,
                 usedAsColor=True,
                 attributeType='float3'
                 )
    cmds.addAttr(module_name,
                 longName='red',
                 attributeType='float',
                 parent=colors_name, dv=1
                 )
    cmds.addAttr(module_name,
                 longName='green',
                 attributeType='float',
                 parent=colors_name, dv=1
                 )
    cmds.addAttr(module_name,
                 longName='blue',
                 attributeType='float',
                 parent=colors_name, dv=1
                 )

    cmds.addAttr(module_name,
                 longName=ai_exposure_name,
                 at="double"
                 )

    cmds.addAttr(module_name,
                 longName=penumbra_name,
                 at="double"
                 )

    cmds.addAttr(module_name,
                 longName=light_representation_name,
                 enumName="none:geometry:light",
                 attributeType='enum',
                 k=True,
                 dv=1)

    return True


def create_module_groups(control_object, object_base_name):

    initial_position = cmds.xform(control_object, matrix=True, q=True, ws=True)

    parent_object = cmds.createNode("transform",
                                    n=f"{object_base_name}_GRP".replace("CAPITALIZED",
                                                                        "Module"
                                                                        )
                                    )

    input_name = cmds.createNode("transform",
                                 n=f"{object_base_name}_GRP".replace("CAPITALIZED",
                                                                     "Input"
                                                                     )
                                 )

    computation_name = cmds.createNode("transform",
                                       n=f"{object_base_name}_GRP".replace("CAPITALIZED",
                                                                           "Computation"
                                                                           )
                                       )

    output_name = cmds.createNode("transform",
                                  n=f"{object_base_name}_GRP".replace("CAPITALIZED",
                                                                      "Output"
                                                                      )
                                  )

    geometries_name = cmds.createNode("transform",
                                      n=f"{object_base_name}_GRP".replace("CAPITALIZED",
                                                                          "Geometry"
                                                                          )
                                      )

    cmds.parent(input_name, parent_object)
    cmds.parent(output_name, parent_object)
    cmds.parent(computation_name, parent_object)
    cmds.parent(geometries_name, parent_object)

    return computation_name, geometries_name, initial_position, input_name, output_name


#
def create_light_mesh(parent_object, object_base_name):

    uber_grp = cmds.createNode("transform", n=f"{object_base_name}_TRS".replace("CAPITALIZED", "LightInput"))
    parent_name = f"{object_base_name}_GRP".replace("CAPITALIZED", "Geometry")

    cmds.select(parent_object)
    mutils.createMeshLight()

    light_trs = cmds.ls(sl=True)[0]
    cmds.select(cl=True)

    light_name = parent_object.replace("GEO", "MLGT")
    cmds.rename(light_trs, light_name)

    light_trs = light_name

    light_shp = cmds.listRelatives(light_trs, shapes=True)[0]

    cmds.parent(light_trs, uber_grp)
    cmds.parent(uber_grp, parent_name)

    cmds.setAttr(f"{light_shp}.showOriginalMesh", True)

    return uber_grp, light_trs, light_shp


def create_switching_network(input_attr, nodes):
    for iteration_, node in enumerate(nodes):
        node_name = node.replace("TRS", "CPI")
        cmds.createNode("math_CompareInt", n=node_name)

        cmds.setAttr(f"{node_name}.input2", iteration_ + 1)
        cmds.setAttr(f"{node_name}.operation", 0)

        cmds.connectAttr(f"{input_attr}", f"{node_name}.input1", f=True)

        cmds.connectAttr(f"{node_name}.output", f"{node}.visibility", f=True)


def create_light_geometry(parent_object, object_base_name, func=None):
    if not func:
        return

    input_name = f"{object_base_name}_TRS".replace("CAPITALIZED", "GeoInput")
    geo_trs_name = f"{object_base_name}_GEO".replace("CAPITALIZED", "GeoCone")
    geo_shp_name = f"{geo_trs_name}Shape"
    uber_grp = cmds.createNode("transform", n=input_name)

    cone_trs, cone_shp = func(n=geo_trs_name)

    cmds.polyProjection(f"{cone_trs}.f[:]", type="Planar", md="x", ch=False)

    cmds.xform(cone_trs, ro=(180, 0, 0), t=(0, 1, 0))

    cmds.parent(cone_trs, uber_grp)
    cmds.parent(uber_grp, parent_object)

    cmds.setAttr(f"{cone_trs}.overrideEnabled", 1)

    for attr_ in ("castsShadows",
                  "aiCastShadows",
                  "receiveShadows",
                  "primaryVisibility",
                  "smoothShading",
                  "visibleInReflections",
                  "visibleInRefractions"):

        cmds.setAttr(f"{geo_shp_name}.{attr_}", False)
    cmds.delete(cone_trs, ch=True)
    return uber_grp, cone_trs, cone_shp


def create_light_object(parent_object, object_base_name):
    """
    Creates a Cone Light

    Args:
        parent_object:
        object_base_name:

    Returns:

    """
    uber_grp = cmds.createNode("transform",
                               n=f"{object_base_name}_TRS".replace("CAPITALIZED",
                                                                   "LightInput"
                                                                   )
                               )
    light_shp = mutils.createLocator("spotLight", asLight=True)[0]

    light_trs = cmds.listRelatives(str(light_shp), parent=True)
    light_trs_name = f"{object_base_name}_LGT".replace("CAPITALIZED",
                                                       "LightCone"
                                                       )
    cmds.rename(light_trs, light_trs_name)
    light_shp = cmds.listRelatives(light_trs_name, children=True)[0]

    cmds.xform(light_trs_name,
               ro=(90, 0, 0),
               s=(1.5385, 1.5385, 1.5385,)
               )

    cmds.parent(light_trs_name, uber_grp)
    cmds.parent(uber_grp, parent_object)

    create_cone_angle_interpolation(light_shp,
                                    object_base_name,
                                    uber_grp
                                    )

    cmds.setAttr(f"{light_trs_name}.overrideEnabled", 1)

    cmds.connectAttr(f"{light_shp}.instObjGroups", "defaultLightSet.dagSetMembers",
                     nextAvailable=True,
                     f=True
                     )

    cmds.delete(light_trs_name, ch=True)

    return uber_grp, light_trs_name, light_shp


def create_cone_angle_interpolation(light_shp, object_base_name, uber_grp):
    """
    A vector based approach to figure out the angle of the light cone, (basically its radius)

    Args:
        light_shp ():
        object_base_name ():
        uber_grp ():

    Returns:
        Str(calc_output_node_name):
    """

    bottom_grp = cmds.createNode("transform",
                                 n=f"{object_base_name}_TRS".replace("CAPITALIZED",
                                                                     "angleCalcBot")
                                 )

    upper_grp = cmds.createNode("transform",
                                n=f"{object_base_name}_TRS".replace("CAPITALIZED",
                                                                    "angleCalcTop")
                                )

    outter_grp = cmds.createNode("transform",
                                 n=f"{object_base_name}_TRS".replace("CAPITALIZED",
                                                                     "angleCalcOut")
                                 )

    cmds.parent([bottom_grp, upper_grp, outter_grp], uber_grp)

    cmds.xform(upper_grp, t=(0, 2, 0))
    cmds.xform(outter_grp, t=(1, 2, 0))
    bottom_trans = cmds.createNode("math_TranslationFromMatrix",
                                   n=bottom_grp.replace("TRS",
                                                        "TFM")
                                   )
    upper_trans = cmds.createNode("math_TranslationFromMatrix",
                                  n=upper_grp.replace("TRS",
                                                      "TFM")
                                  )
    outter_trans = cmds.createNode("math_TranslationFromMatrix",
                                   n=outter_grp.replace("TRS",
                                                        "TFM")
                                   )

    bottom_to_upper = cmds.createNode("math_SubtractVector",
                                      n=upper_grp.replace("TRS",
                                                          "SUB")
                                      )
    bottom_to_outter = cmds.createNode("math_SubtractVector",
                                       n=outter_grp.replace("TRS",
                                                            "SUB")
                                       )

    angle_between = cmds.createNode("math_AngleBetweenVectors",
                                    n=bottom_grp.replace("TRS",
                                                         "ABV")
                                    )

    calc_output_node_name = cmds.createNode("math_MultiplyAngleByInt",
                                            n=bottom_grp.replace("TRS",
                                                                 "MLA")
                                            )

    cmds.connectAttr(f"{bottom_grp}.worldMatrix", f"{bottom_trans}.input")
    cmds.connectAttr(f"{upper_grp}.worldMatrix", f"{upper_trans}.input")
    cmds.connectAttr(f"{outter_grp}.worldMatrix", f"{outter_trans}.input")

    cmds.connectAttr(f"{bottom_trans}.output", f"{bottom_to_upper}.input1")
    cmds.connectAttr(f"{upper_trans}.output", f"{bottom_to_upper}.input2")

    cmds.connectAttr(f"{bottom_trans}.output", f"{bottom_to_outter}.input1")
    cmds.connectAttr(f"{outter_trans}.output", f"{bottom_to_outter}.input2")

    cmds.connectAttr(f"{bottom_to_upper}.output", f"{angle_between}.input1")
    cmds.connectAttr(f"{bottom_to_outter}.output", f"{angle_between}.input2")

    cmds.connectAttr(f"{angle_between}.output", f"{calc_output_node_name}.input1")

    cmds.setAttr(f"{calc_output_node_name}.input2", 2)

    cmds.connectAttr(f"{calc_output_node_name}.output", f"{light_shp}.coneAngle")

    return f"{calc_output_node_name}.output"


def create_lights(light_type, light_controls):
    """

    Args:
        light_type:
        light_controls:

    Returns:

    """
    operations_dict = dict()

    for light_control in light_controls:
        light_info = create_light(light_type, light_control)
        operations_dict[light_control] = light_info

    return operations_dict


def connect_lights_to_controls(light_type, light_modules, master_control):
    """

    Args:
        light_type:
        light_modules:
        master_control:

    Returns:

    """

    # color
    base_colors_name_master = f"{light_type}_override_colors"

    if not cmds.attributeQuery(base_colors_name_master, node=master_control, exists=True):
        cmds.addAttr(master_control, ln=base_colors_name_master, usedAsColor=True, attributeType='float3', k=True)
        cmds.addAttr(master_control, ln=f'{base_colors_name_master}Red', attributeType='float',
                     parent=base_colors_name_master, dv=1, k=True)
        cmds.addAttr(master_control, ln=f'{base_colors_name_master}Green', attributeType='float',
                     parent=base_colors_name_master, dv=1, k=True)
        cmds.addAttr(master_control, ln=f'{base_colors_name_master}Blue', attributeType='float',
                     parent=base_colors_name_master, dv=1, k=True)

    for key_, values_ in light_modules.items():

        cmds.connectAttr(f"{master_control}.{base_colors_name_master}",
                         f"{values_['input']}.{values_['input_lgt_color']}")

        color_blend = cmds.createNode("blendColors", n=key_.replace("TRS", "BLC"))

        vis_seperator_name = "visibility_attributes"
        if not cmds.attributeQuery(vis_seperator_name, node=key_, exists=True):

            cmds.addAttr(key_, ln=vis_seperator_name, enumName="########", attributeType='enum', k=False)
            cmds.setAttr(f"{key_}.{vis_seperator_name}", cb=True, l=True)

        override_type_name = "override_type"
        if not cmds.attributeQuery(override_type_name, node=key_, exists=True):

            cmds.addAttr(key_, ln=override_type_name, enumName="normal:template:reference", attributeType='enum',
                         k=False,
                         dv=2)

            cmds.setAttr(f"{key_}.{override_type_name}", cb=True)

        light_representation_name = "light_representation"
        if not cmds.attributeQuery(light_representation_name, node=key_, exists=True):

            cmds.addAttr(key_, ln=light_representation_name, enumName="none:geometry:light", attributeType='enum',
                         k=True,
                         dv=1)

            cmds.setAttr(f"{key_}.{light_representation_name}", cb=True)

        seperator_name = "color_attributes"
        if not cmds.attributeQuery(seperator_name, node=key_, exists=True):

            cmds.addAttr(key_, ln=seperator_name, enumName="########", attributeType='enum', k=False)
            cmds.setAttr(f"{key_}.{seperator_name}", cb=True, l=True)

        override_blend_name = "color_override_blend"
        if not cmds.attributeQuery(override_blend_name, node=key_, exists=True):

            cmds.addAttr(key_, ln=override_blend_name, dv=0, attributeType='double', k=True, hnv=True, hxv=True, min=0,
                         max=1)

        base_colors_name = "override_colors"
        if not cmds.attributeQuery(base_colors_name, node=key_, exists=True):

            cmds.addAttr(key_, ln=base_colors_name, usedAsColor=True, attributeType='float3', k=True)
            cmds.addAttr(key_, ln='red', attributeType='float', parent=base_colors_name, dv=1, k=True)
            cmds.addAttr(key_, ln='green', attributeType='float', parent=base_colors_name, dv=1, k=True)
            cmds.addAttr(key_, ln='blue', attributeType='float', parent=base_colors_name, dv=1, k=True)

        cmds.connectAttr(f"{values_['compute']}.{values_['compute_lgt_color']}", f"{color_blend}.color2", f=True)
        cmds.connectAttr(f"{key_}.{base_colors_name}", f"{color_blend}.color1", f=True)
        cmds.connectAttr(f"{key_}.{override_blend_name}", f"{color_blend}.blender", f=True)

        cmds.connectAttr(f"{key_}.{light_representation_name}",
                         f"{values_['input']}.module_{light_representation_name}",
                         force=True)

        cmds.connectAttr(f"{color_blend}.output", f"{values_['output']}.{values_['output_lgt_color']}", force=True)

        for axis_ in "XYZ":
            try:
                cmds.setAttr(f"{key_}.scale{axis_}", keyable=True, l=False)

            except:
                pass

        if "light" in key_.lower():

            for axis_ in "XYZ":
                cmds.setAttr(f"{key_}.scale{axis_}", 600)

        else:
            for axis_ in "XZ":
                cmds.setAttr(f"{key_}.scale{axis_}", 4)

            cmds.setAttr(f"{key_}.scaleY", 2800)

        cmds.setAttr(f"{key_}.inheritsTransform", False)
        cmds.connectAttr(f"{values_['compute']}.{values_['compute_trs']}", f"{key_}.offsetParentMatrix", force=True)
        cmds.connectAttr(f"{key_}.worldMatrix[0]", f"{values_['output']}.{values_['output_trs']}", force=True)

        cmds.connectAttr(f"{key_}.{override_type_name}", f"{values_['geo']}.overrideDisplayType", force=True)

        cmds.connectAttr(f"{key_}.{override_type_name}", f"{values_['lgt']}.overrideDisplayType", force=True)

        seperator_name = "intenstity_attrs"
        if not cmds.attributeQuery(seperator_name, node=key_, exists=True):

            cmds.addAttr(key_, ln=seperator_name, enumName="########", attributeType='enum', k=False)
            cmds.setAttr(f"{key_}.{seperator_name}", cb=True, l=True)

        intensity_attr_name = "light_intensity"
        if not cmds.attributeQuery(intensity_attr_name, node=key_, exists=True):

            cmds.addAttr(key_, ln=intensity_attr_name, dv=0, attributeType='double', k=True, hnv=True, hxv=True, min=0,
                         max=1)

        cmds.connectAttr(f"{key_}.{intensity_attr_name}", f"{values_['lgt_shape']}.intensity", force=True)


def connect_light_geo_to_shaders(light_modules):

    for key_, values_ in light_modules.items():
        checker_object, checker_mat = shader_utils.assign_ramp_shader(pmc.PyNode(values_["geo"]),
                                                                      material_name=f"{values_['input']}_msMat")
        seperator_name = "viewport_exposure_attributes"
        if not cmds.attributeQuery(seperator_name, node=key_, exists=True):
            cmds.addAttr(key_, ln=seperator_name, enumName="########", attributeType='enum', k=False)
            cmds.setAttr(f"{key_}.{seperator_name}", cb=True, l=True)

        viewport_exposure_name = "viewport_exposure"
        if not cmds.attributeQuery(viewport_exposure_name, node=key_, exists=True):
            cmds.addAttr(key_, ln=viewport_exposure_name, attributeType='float3', usedAsColor=True, k=False)
            cmds.addAttr(key_, ln='R', attributeType='float', parent=viewport_exposure_name, k=False)
            cmds.addAttr(key_, ln='G', attributeType='float', parent=viewport_exposure_name, k=False)
            cmds.addAttr(key_, ln='B', attributeType='float', parent=viewport_exposure_name, k=False)

        viewport_exposure_darken_name = "viewport_exposure_darken"
        if not cmds.attributeQuery(viewport_exposure_darken_name, node=key_, exists=True):
            cmds.addAttr(key_, ln=viewport_exposure_darken_name, attributeType='float', dv=0, k=True, hnv=True,
                         hxv=True,
                         min=0, max=1)

        cmds.connectAttr(f"{key_}.viewport_exposure_darken",
                         f"{key_}.{viewport_exposure_name}.R",
                         f=True
                         )

        cmds.connectAttr(f"{key_}.viewport_exposure_darken",
                         f"{key_}.{viewport_exposure_name}.G",
                         f=True
                         )

        cmds.connectAttr(f"{key_}.viewport_exposure_darken",
                         f"{key_}.{viewport_exposure_name}.B",
                         f=True
                         )

        pmc.PyNode(key_).attr(viewport_exposure_name).connect(
                checker_object.outTransparency.listConnections()[0].colorEntryList[1].color, f=True)

        pmc.PyNode(values_["output"]).attr(values_["output_lgt_color"]).connect(checker_object.outColor)


def build_advanced_controls(light_type, light_modules, aim_controls):
    for key_, values_ in light_modules.items():
        bruh = (f"{light_type.capitalize()}Aim_", f"{light_type.capitalize()}AimPyr_")

        aim_items = [key_.replace(f"{light_type.capitalize()}_", str_bruh) for str_bruh in bruh if
                     cmds.objExists(key_.replace(f"{light_type.capitalize()}_", str_bruh))]

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
            try:
                cmds.addAttr(values_['input'], ln=blend_weight_name, attributeType='double', dv=0, k=True, hnv=True,
                             hxv=True, min=-1,
                             max=1)
            except:
                pass

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
        if not cmds.attributeQuery(seperator_name, node=key_, exists=True):

            cmds.addAttr(key_, ln=seperator_name, enumName="########", attributeType='enum', k=False)
            cmds.setAttr(f"{key_}.{seperator_name}", cb=True, l=True)

        for iteration_, i in enumerate(values_["input_space_weights"]):

            blend_weight_name = f"blendWeight_{str(iteration_).zfill(3)}"
            if not cmds.attributeQuery(blend_weight_name, node=key_, exists=True):

                cmds.addAttr(key_,
                             ln=blend_weight_name,
                             attributeType='double',
                             dv=0,
                             k=True,
                             hnv=True,
                             hxv=True,
                             min=-1,
                             max=1
                             )

            cmds.connectAttr(f"{key_}.{blend_weight_name}", f"{values_['input']}.{i}", f=True)


def create_mesh_lights():
    cmds.select(cl=True)

    mesh_nodes = set([cmds.listRelatives(x, parent=True)[0]
                      for x in cmds.ls(type="mesh")
                      if f"_{RESOLUTION_TYPE}" in x
                      ]
                     )

    uber_names = set([x.split(":")[-1].split("_")[0]
                      for x in mesh_nodes
                      ])

    mesh_lights_grouped = {uber_name_: [] for uber_name_ in uber_names}

    for iteration_, i in enumerate(set(mesh_nodes)):
        cmds.select(i)
        old_name = i

        if ":" in old_name:
            old_name = old_name.split(":")[-1]

        uber_name = old_name.split("_")[0]

        mtoa.utils.createMeshLight()
        light_tansform = cmds.ls(sl=True)[0]

        light_transform_old = light_tansform
        if ":" in light_transform_old:
            light_transform_old = light_transform_old.split(':')[-1]

        light_name = light_transform_old.replace(f"{RESOLUTION_TYPE}_geo", "MLGT")
        lgt_nme_deconst = light_name.split("_")

        light_name = f"{lgt_nme_deconst[1]}_{lgt_nme_deconst[0]}_{lgt_nme_deconst[2]}_{str(iteration_)}_{lgt_nme_deconst[3]}"

        cmds.rename(light_tansform, light_name)

        light_tansform = light_name

        light_shape = cmds.listRelatives(light_tansform, parent=True)[0]
        cmds.setAttr(f"{light_shape}.aiExposure", 14)
        cmds.parent(light_tansform, world=True)
        mesh_lights_grouped[uber_name].append(light_name)

        cmds.select(cl=True)

    return mesh_lights_grouped


def connect_mesh_lights(mesh_lights, master_control):

    seperator_name = "space_attributes"

    if not cmds.attributeQuery(seperator_name, node=master_control, exists=True):

        cmds.addAttr(master_control, ln=seperator_name, enumName="########", attributeType='enum', k=False)
        cmds.setAttr(f"{master_control}.{seperator_name}", cb=True, l=True)

    base_colors_name = "override_mesh_colors"

    if not cmds.attributeQuery(base_colors_name, node=master_control, exists=True):
        cmds.addAttr(master_control, ln=base_colors_name, usedAsColor=True, attributeType='float3', k=True)
        cmds.addAttr(master_control, ln=f'{base_colors_name}Red', attributeType='float', parent=base_colors_name, dv=1,
                     k=True)
        cmds.addAttr(master_control, ln=f'{base_colors_name}Green', attributeType='float', parent=base_colors_name,
                     dv=1,
                     k=True)
        cmds.addAttr(master_control, ln=f'{base_colors_name}Blue', attributeType='float', parent=base_colors_name, dv=1,
                     k=True)

    light_representation_name = "light_representation"

    for key_, value_ in mesh_lights.items():
        controller_name = f"{key_}_C_0_ctrl"

        if cmds.objExists(controller_name):
            pass

        else:
            if "kiosk" in key_ or "commercial" in key_:
                controller_name = "kioskLights_C_0_ctrl"

            else:
                controller_name = "podLights_C_0_ctrl"

        if not cmds.attributeQuery(light_representation_name, node=controller_name, exists=True):
            seperator_name = "representation_attributes"
            cmds.addAttr(controller_name, ln=seperator_name, enumName="########", attributeType='enum', k=False)
            cmds.setAttr(f"{controller_name}.{seperator_name}", cb=True, l=True)

            cmds.addAttr(controller_name,
                         ln=light_representation_name,
                         enumName="none:geometry:light",
                         attributeType="enum",
                         k=True, dv=1
                         )

            seperator_name = "color_attributes"
            cmds.addAttr(controller_name, ln=seperator_name, enumName="########", attributeType='enum', k=False)
            cmds.setAttr(f"{controller_name}.{seperator_name}", cb=True, l=True)

            cmds.addAttr(controller_name, ln='color_override_blend', attributeType='float', dv=0, k=True, hnv=True,
                         hxv=True,
                         min=0, max=1)

            cmds.addAttr(controller_name, ln=base_colors_name, usedAsColor=True, attributeType='float3', k=True)
            cmds.addAttr(controller_name, ln=f'{base_colors_name}Red', attributeType='float', parent=base_colors_name,
                         dv=1, k=True)
            cmds.addAttr(controller_name, ln=f'{base_colors_name}Green', attributeType='float', parent=base_colors_name,
                         dv=1, k=True)
            cmds.addAttr(controller_name, ln=f'{base_colors_name}Blue', attributeType='float', parent=base_colors_name,
                         dv=1, k=True)

            cmds.addAttr(controller_name, ln='light_visible', attributeType='float', dv=0, k=True, hnv=True, hxv=True,
                         min=0, max=1)

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

            cmds.connectAttr(f"{controller_name}.light_visible", f"{v_}Shape.lightVisible")

            try:
                mat_, shd_ = shader_utils.assign_shader(
                        object_to_shade=pmc.PyNode(v_).getShape().attr("inMesh").listConnections()[0].getParent(),
                        material_name=f"{v_}_msMat",
                        material_type="surfaceShader",
                        material_color=(1, 1, 1),
                        material_transp=(0, 0, 0),
                        material_refl=(0, 0, 0),
                )
            except:
                continue

            cmds.connectAttr(f"{master_control}.{base_colors_name}", f"{light_colors_bld}.color2")
            cmds.connectAttr(f"{controller_name}.{base_colors_name}", f"{light_colors_bld}.color1")
            cmds.connectAttr(f"{controller_name}.color_override_blend", f"{light_colors_bld}.blender")

            pmc.PyNode(light_colors_bld).attr("output").connect(mat_.outColor)


def sort_mesh_lights(mesh_lights):
    for key_, value_ in mesh_lights.items():
        cmds.group(value_, n=f"C_meshLight{key_}_000_GRP")


def tag_mesh_lights(mesh_lights):
    for key_, value_ in mesh_lights.items():
        for light_ in value_:
            if "divider" in key_:
                cmds.setAttr(f"{light_}Shape.aiAov", "divider", type="string", )

            elif "kiosk" in key_ and "Laser" not in key_:
                cmds.setAttr(f"{light_}Shape.aiAov", "kiosk", type="string", )

            elif "kioskLaser" in key_:
                cmds.setAttr(f"{light_}Shape.aiAov", "kioskLaser", type="string", )

            elif "mainsection" in key_:
                cmds.setAttr(f"{light_}Shape.aiAov", "mainsection", type="string", )

            else:
                cmds.setAttr(f"{light_}Shape.aiAov", key_, type="string", )


def mesh_lights_to_set(mesh_lights):
    for key_, value_ in mesh_lights.items():
        if "mainsection" in key_:
            key_ = "mainsection"

        elif "kiosk" in key_ and "Laser" not in key_ or "commercial" in key_:
            key_ = "kiosk"

        elif "kioskLaser" in key_:
            key_ = "kioskLaser"

        else:
            key_ = key_

        shapes_ = [cmds.listRelatives(val_, shapes=True)[0] for val_ in value_]

        mesh_light_set_name = f"_{key_}_"
        if not cmds.objExists(mesh_light_set_name):
            cmds.sets(empty=True, name=mesh_light_set_name, )

        cmds.sets(shapes_, edit=True, forceElement=mesh_light_set_name, )
        cmds.sets(value_, edit=True, forceElement=mesh_light_set_name, )

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

    cmds.sets(empty=True, name=constants.PXO_ADD_SET_NAME, )
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

            light_trs = [cmds.listRelatives(light_shp, parent=True)[0] for light_shp in v_]
            cmds.sets(light_trs, edit=True, forceElement=name_subset)

            for lgts_ in v_:
                cmds.setAttr(f"{lgts_}.aiAov", name_subset_aov_name, type="string", )

        cmds.sets(name_set, edit=True, forceElement="_light_selects_")
    return resultdict


def build_rig_on_controls(light_type, aim_controls):

    # lights
    light_controls = cmds.ls(f"*{light_type.capitalize()}_*_ctrl")

    light_modules = create_lights(light_type, light_controls)

    connect_lights_to_controls(light_type, light_modules, "openerHost_C_0_ctrl")
    connect_light_geo_to_shaders(light_modules)

    light_modules = build_advanced_controls(light_type, light_modules, aim_controls)

    connect_transform_sys_to_controls(light_modules)

    return light_modules


def get_index(item):
    return int("".join(item.split("_")[-2][1:]))


def create_zipped_groups(names=("fanLaser_C_*_ctrl", "fanLaserAim_C_*_ctrl",)):

    name_grps = list()
    for name_grp in names:

        sel_names = sorted([x for x in cmds.listRelatives(name_grp[0], ad=True, fullPath=True) if
                            cmds.objectType(x, isAType="transform") and "sizeRef" not in x and x.split("_")[
                                -1] == "root"], key=get_index, )

        aim_names = sorted([x for x in cmds.listRelatives(name_grp[-1], ad=True, fullPath=True) if
                            cmds.objectType(x, isAType="transform") and "sizeRef" not in x and x.split("_")[
                                -1] == "root"], key=get_index, )

        name_grps.append(list(zip(sel_names, aim_names)))

    return name_grps


def create_fan_groups(names=("fanLaserSelGrp_C*_root", "fanLaserAims_C*_root")):
    return zip(cmds.ls(names[0]), cmds.ls(names[1]))


def create_curve_inbetween(zipped_groups):
    created_curve_gathered = list()

    for grp_iteration_, zipped_group in enumerate(zipped_groups):
        created_curves = dict()
        created_curves["curve"] = list()
        created_curves["points"] = list()
        created_curves["controls"] = list()

        for iteration_, zipped_parts in enumerate(zipped_group):

            points = [(0, 0, 0,) for _ in range(len(zipped_parts))]

            sub_name = "lightSlice"

            curve_name = f"{sub_name}_C_{str(iteration_).zfill(3)}_{grp_iteration_}_CRV"
            trs = cmds.curve(n=curve_name, p=points, degree=1)
            shp = cmds.listRelatives(trs, shapes=True)[0]
            cmds.rename(shp, f"{curve_name}Shape")

            cmds.delete(curve_name, ch=True)

            cmds.setAttr(f"{curve_name}.overrideEnabled", True)
            cmds.setAttr(f"{curve_name}.overrideDisplayType", 1)
            created_curves["curve"].append(curve_name)
            created_curves["points"].append(points)
            created_curves["controls"].append(zipped_parts)

        created_curve_gathered.append(created_curves)

    return created_curve_gathered


def create_position_to_curve_pin(created_curve_gathered):
    for created_curves in created_curve_gathered:
        for iteration_, control_object in enumerate(created_curves["controls"]):
            for it_boy_, ctl_obj in enumerate(control_object):
                trs_nde = f"{created_curves['curve'][iteration_]}_{str(it_boy_)}_trs"
                cmds.createNode("math_TranslationFromMatrix", n=trs_nde)

                cmds.connectAttr(f"{ctl_obj}.worldMatrix[0]", f"{trs_nde}.input")

                cmds.connectAttr(f"{trs_nde}.output",
                                 f"{created_curves['curve'][iteration_]}Shape.controlPoints[{str(it_boy_)}]")


def create_loft_of_curves(created_curve_gathered):
    loft_names = list()
    for iteration_, created_curves in enumerate(created_curve_gathered, 1):

        loft_name = f"mandatoryNamespace:lightSlice_C_{str(iteration_).zfill(3)}_{RESOLUTION_TYPE}_geo"
        cmds.loft(*created_curves["curve"], ch=True, n=loft_name, polygon=1)
        loft_names.append(loft_name)

    return loft_names


def merge_two_dicts(x, y):
    z = x.copy()  # start with keys and values of x
    z.update(y)  # modifies z with keys and values of y
    return z


def main():
    # creation part
    shader_utils.clear()

    aim_controls = cmds.ls("aimControl_*_*_ctrl")

    fans = create_fan_groups()
    zipped_groups = create_zipped_groups(names=fans)

    curves_inbetween = create_curve_inbetween(zipped_groups)

    create_position_to_curve_pin(curves_inbetween)

    create_loft_of_curves(curves_inbetween)

    mesh_lights = create_mesh_lights()

    connect_mesh_lights(mesh_lights, "openerHost_C_0_ctrl")
    sort_mesh_lights(mesh_lights)

    laser_items = build_rig_on_controls("laser", aim_controls)

    lasers_dict = {laser_name.split("_")[0]: [] for laser_name, laser_item in laser_items.items()}

    lasers_wallah = [lasers_dict[laser_name.split("_")[0]].append(laser_item["lgt"]) for laser_name, laser_item in
                     laser_items.items()]

    mesh_lights = merge_two_dicts(mesh_lights, lasers_dict)

    build_rig_on_controls("light", aim_controls)

    unlock_scales()

    lights_to_set()

    tag_mesh_lights(mesh_lights)

    mesh_lights_to_set(mesh_lights)

    # TO DO:
    ' Geometries into a set '
    ' Vis and Display for the LightSlice '


if __name__ == "__main__":
    main()

