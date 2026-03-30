import os
import glob

import pymel.core as pmc
from pxo_rigging_kit.maya_utils import paths_utils
from pxo_rigging_kit.maya_utils import attributes_utils
from pxo_rigging_kit.maya_utils import scene_utils
import pixo_paths

VIS_CONTROL = "visibility_C_0_*_ctrl"
IMPORTED_NODES = []

# pmc.openFile(r"X:\redgun3_rg3-18453\_library\assets\creature\crt_sheepstealer\rig\rg3_crt_sheepstealer_rig_v016_jwo.ma", force=True)

def get_latest_previs_shd_file():
    asset_task_root = os.path.join(paths_utils.get_root_path(pmc.sceneName(), "asset"), "asset_previz")
    publish_folder = pixo_paths.normalize(os.path.join(asset_task_root, "_publish"))
    if not os.path.exists(publish_folder):
        raise Exception(f"{publish_folder} not found.")
    list_of_files = glob.glob(os.path.join(publish_folder, "*"))
    latest_file = max(list_of_files, key=os.path.getctime)
    return latest_file
    
def import_previs_shd_file():
    latest_file = get_latest_previs_shd_file()
    included_nodes = pmc.importFile(latest_file, returnNewNodes=True)
    [node.unlock() for node in included_nodes]
    return included_nodes
    
def assign_shader_to_rig_geos(imported_nodes):
    shading_engines = []
    mesh_nodes = set(node.getTransform() for node in imported_nodes if node.nodeType() == "mesh")
    for node in mesh_nodes:
        target_nodes = pmc.ls(f"*:{node.name(long=None)}")
        if not target_nodes:
            pmc.warning(f"No target node exist for {node}")
            continue
        for target_nd in target_nodes:
            shading_engines.append(transfer_src_shd_to_trgt(node, target_nd))
    return set(shading_engines)


def transfer_src_shd_to_trgt(source, target_nd):
    """
    Will transfer exsiting shader tree to target geo.
    Source objects is the first selected one. All others are the targets.
    If a uvChosser setup is included it will make the corresponding connections.
    But we always assume that the uvSet[1] is the oneUdim set in every object.
    """
    source_shape = source.getShape()
    shading_engine = [node for node in source_shape.connections() if node.nodeType() == "shadingEngine" and "initialShadingGroup" not in node.nodeName()]
    try:
        shading_engine = shading_engine[0]
    except:
        raise Exception(f"No shading engine found for {source_shape}")
    target_shape = target_nd.getShape(noIntermediate=True)
    pmc.sets(shading_engine, e=True, fe=target_shape)
    uv_chosser_nodes = shading_engine.listHistory(type="uvChooser")
    for uv_ch_nd in uv_chosser_nodes:
        index = attributes_utils.get_next_free_array_index(uv_ch_nd.uvSets.name(), 0)
        target_shape.uvSet[1].uvSetName.connect(uv_ch_nd.attr(f"uvSets[{index}]"))
    return shading_engine

 
# def _create_shd_set(imported_nodes):
#     shd_import_set = pmc.createNode("objectSet", n="shd_set")
#     shd_import_set.addMembers(imported_nodes)
#     pmc.PyNode("pxm_rig_root_set").addMember(shd_import_set)

def _clean_the_scene(imported_nodes):
    temp = [node for node in imported_nodes if node.nodeType() == "mesh" or node.nodeType() == "transform"]
    parent_nd_nodes = pmc.ls("parent_nd*")
    pmc.delete(temp+parent_nd_nodes)
    scene_utils.delete_unkown_nodes()
    scene_utils.delete_unkown_plugins()
    pmc.mel.eval("MLdeleteUnused;")
    
def _create_shd_blend_setup(shading_engines):
    vis_control = pmc.ls(VIS_CONTROL)
    if len(vis_control) > 1:
        raise ValueError(f"To much visibility controls: {vis_control}")
    try:
        vis_control = vis_control[0]
    except:
        raise ValueError("No visibility control existing.")
    for shd_e in shading_engines:
        shader = shd_e.surfaceShader.connections()[0]
        file_nd = shader.color.connections()
        if file_nd:
            file_nd = file_nd[0]
            blend_color = pmc.createNode("blendColors")
            vis_control.texture_display.connect(blend_color.blender)
            blend_color.color2R.set(0.5)
            blend_color.color2G.set(0.5)
            blend_color.color2B.set(0.5)
            file_nd.outColor.connect(blend_color.color1)
            blend_color.output.connect(shader.color, force=True)
            bump_nd = shader.normalCamera.connections()
            if not bump_nd:
                continue
            bump_nd = bump_nd[0]
            dpth_value = bump_nd.bumpDepth.get()
            mult_dpl_lin = pmc.createNode("multDoubleLinear")
            mult_dpl_lin.input1.set(dpth_value)
            vis_control.bump_map_display.connect(mult_dpl_lin.input2)
            mult_dpl_lin.output.connect(bump_nd.bumpDepth)
        
def run_shd_apply():
    global IMPORTED_NODES
    imported_nodes = import_previs_shd_file()
    IMPORTED_NODES = imported_nodes
    shading_engines = assign_shader_to_rig_geos(imported_nodes)
    _create_shd_blend_setup(shading_engines)
    # _create_shd_set(imported_nodes)
    _clean_the_scene(imported_nodes)

def main():
    run_shd_apply()


if __name__ == "__main__":
    main()
# for node in IMPORTED_NODES:
#     try:
#         pmc.delete(node)
#     except:
#         continue
# IMPORTED_NODES = []
