import maya.cmds as cmds
import pxr
import ufe
from mayaUsd import lib as mayaUsdLib
from mayaUsd.lib import proxyAccessor

USD_SCHEMA = "UsdSchemaBase"

def create_default_assembly_rig_setup(asset_name):
    stage_driver_grp = cmds.ls(sl=True)
    assembly_rig_stage_shape=cmds.listRelatives(stage_driver_grp)[0]
    stage = mayaUsdLib.GetPrim(assembly_rig_stage_shape).GetStage()
    rig_grp = cmds.group(n=f"{asset_name}_rig", em=True)

    # create default control setup
    grp = cmds.group(n="root_001_trx", em=True)
    cmds.group(n="root_001_OFFSET")
    root_grp = cmds.group(n="root_001_GRP")
    root_ctrl = cmds.circle(c=[0, 0, 0], nr=[0, 1, 0], sw=360, r=10, d=3, ut=0, s=8, ch=False, n="root_001_CTRL")[0]
    cmds.setAttr(f"{root_ctrl}.overrideEnabled", True)
    cmds.setAttr(f"{root_ctrl}.overrideColor", 17)
    cmds.parent(root_ctrl, grp)

    grp = cmds.group(n="rootOffset_001_TRN", em=True)
    cmds.group(n="rootOffset_001_OFFSET")
    root_offset_grp = cmds.group(n="rootOffset_001_GRP")
    root_offset_ctrl = cmds.circle(c=[0, 0, 0], nr=[0, 1, 0], sw=360, r=8, d=3, ut=0, s=8, ch=False, n="rootOffset_001_CTRL")[0]
    cmds.parent(root_offset_ctrl, grp)
    cmds.parent(root_offset_grp, root_ctrl)

    # parent control setup unde rrig group
    cmds.parent(root_grp, rig_grp)
    cmds.select(cl=True)

    locator = cmds.spaceLocator(n="root_LOC")[0]
    cmds.parent(locator, stage_driver_grp)

    cmds.parentConstraint(root_offset_ctrl, locator, mo=False)
    cmds.scaleConstraint(root_offset_ctrl, locator)

    connect_maya_node_to_usd_prim(assembly_rig_stage_shape, locator)

def connect_maya_node_to_usd_prim(assembly_rig_stage_shape, maya_node, translate_op=True, rotate_op=True, scale_op=True):
    cmds.select(assembly_rig_stage_shape)
    global_selection = ufe.GlobalSelection.get()
    ufe_object = global_selection.front()
    ufe_hierarchy = ufe.Hierarchy.hierarchy(ufe_object)
    ufe_object = ufe_hierarchy.children()[0]
    if USD_SCHEMA not in ufe_object.ancestorNodeTypes():
        return
    stage_path, prim_path = proxyAccessor.getDagAndPrimFromUfe(ufe_object)
    stage = mayaUsdLib.GetPrim(stage_path).GetStage()
    prim = stage.GetPrimAtPath(prim_path)
    x_formable = pxr.UsdGeom.Xformable(prim)
    if translate_op and not prim.GetAttribute("xformOp:translate").IsValid():
        translate = x_formable.AddTranslateOp()
        translate.Set(pxr.Gf.Vec3f([0, 0, 0]))
    if rotate_op and not prim.GetAttribute("xformOp:rotateXYZ").IsValid():
        rotate = x_formable.AddRotateXYZOp()
        rotate.Set(pxr.Gf.Vec3f([0, 0, 0]))
    if scale_op and not prim.GetAttribute("xformOp:scale").IsValid():
        scale = x_formable.AddScaleOp()
        scale.Set(pxr.Gf.Vec3f([1, 1, 1]))
    reset_set = ["!resetXformStack!"]
    if translate_op:
        reset_set.append("xformOp:translate")
    if rotate_op:
        reset_set.append("xformOp:rotateXYZ")
    if scale_op:
        reset_set.append("xformOp:scale")
    prim.GetAttribute("xformOpOrder").Set(reset_set)
    for src_attr, target_attr_name in {
        f"{maya_node}.translate": "xformOp:translate",
        f"{maya_node}.rotate": "xformOp:rotateXYZ",
        f"{maya_node}.scale": "xformOp:scale",
    }.items():
        accessor = proxyAccessor.getOrCreateAccessPlug(ufeObject=ufe_object,
                                            usdAttrName=target_attr_name)
        accessor_attr = f"{stage_path}.{accessor}"
        cmds.connectAttr(src_attr, accessor_attr, force=True)

create_default_assembly_rig_setup("veh_heli")


import maya.cmds as cmds
import pxr
import ufe
from mayaUsd import lib as mayaUsdLib
from mayaUsd.lib import proxyAccessor

def connect_maya_node_to_usd_prim(maya_node, translate_op=True, rotate_op=True, scale_op=True):
    global_selection = ufe.GlobalSelection.get()
    ufe_object = global_selection.front()
    stage_path, prim_path = proxyAccessor.getDagAndPrimFromUfe(ufe_object)
    stage = mayaUsdLib.GetPrim(stage_path).GetStage()
    prim = stage.GetPrimAtPath(prim_path)
    x_formable = pxr.UsdGeom.Xformable(prim)
    if translate_op and not prim.GetAttribute("xformOp:translate").IsValid():
        translate = x_formable.AddTranslateOp()
        translate.Set(pxr.Gf.Vec3f([0, 0, 0]))
    if rotate_op and not prim.GetAttribute("xformOp:rotateXYZ").IsValid():
        rotate = x_formable.AddRotateXYZOp()
        rotate.Set(pxr.Gf.Vec3f([0, 0, 0]))
    if scale_op and not prim.GetAttribute("xformOp:scale").IsValid():
        scale = x_formable.AddScaleOp()
        scale.Set(pxr.Gf.Vec3f([1, 1, 1]))
    reset_set = ["!resetXformStack!"]
    if translate_op:
        reset_set.append("xformOp:translate")
    if rotate_op:
        reset_set.append("xformOp:rotateXYZ")
    if scale_op:
        reset_set.append("xformOp:scale")
    prim.GetAttribute("xformOpOrder").Set(reset_set)
    tra_locator = cmds.spaceLocator(n=f"{maya_node}_LOC")[0]
    cmds.parentConstraint(maya_node, tra_locator, mo=True)
    cmds.scaleConstraint(maya_node, tra_locator)
    for src_attr, target_attr_name in {
        f"{tra_locator}.translate": "xformOp:translate",
        f"{tra_locator}.rotate": "xformOp:rotateXYZ",
        f"{tra_locator}.scale": "xformOp:scale",
    }.items():
        accessor = proxyAccessor.getOrCreateAccessPlug(ufeObject=ufe_object,
                                            usdAttrName=target_attr_name)
        accessor_attr = f"{stage_path}.{accessor}"
        cmds.connectAttr(src_attr, accessor_attr, force=True)

connect_maya_node_to_usd_prim("door_C_001_CTRL")

