import pymel.core as pmc
from pxo_rigging_kit.maya_utils.EWAW_rs import node as ewaw_node
from pxo_rigging_kit.maya_utils import decorators

DECORATORS = decorators.Decorators()
DECORATORS.debug = True

SOURCE_MESH_NAME = "body_C_001_render_geo"
FACE_UI_ROOT_NAME = "face_ui_C0_root"
FACS_ROOT_NAME = "faceTweaker_C0_root"
TRANSFER_MESH_PATH = r"X:\redgun3_rg3-18453\_library\assets\characters\chr_genericBiped\mdl\_publish\rg3_chr_genericBiped_mdl_v015_thz.chr_genericBiped_1_default_male_render.abc"
GENERIC_BIPED_GUIDE_TEMPLATE_PATH = r"X:\redgun3_rg3-18453\_library\assets\characters\chr_genericBiped\rig\guides\chr_genericBiped_v008_jwo_RIGGUIDES.mb"
LEFT_FACE_STATIC_ROOTS = ["upperLip_C0_root",
                          "mouthPress_L0_root",
                          "mouthTighten_L0_root",
                          "mouth_C1_root",
                          "mouthPress_R0_root",
                          "mouthTighten_R0_root",
                          "mouthBlow_L0_root",
                          "mouthBlow_R0_root", 
                          "lowerLip_C0_root"]


@DECORATORS.x_timer
def _get_source_body_mesh(path):
    imported_nodes = pmc.importFile(path, returnNewNodes=True)
    body_render_mesh = [node for node in imported_nodes if SOURCE_MESH_NAME in node.name(long=None)]
    if not body_render_mesh:
        raise Exception(f"{SOURCE_MESH_NAME} not in the imported data")
    pmc.parent(body_render_mesh[0], None)
    body_render_mesh[0].rename("transfer_mesh")
    pmc.delete(imported_nodes[0])
    return body_render_mesh[0]

@DECORATORS.x_timer
def _get_face_guides_from_path(path):
    imported_nodes = pmc.importFile(path, returnNewNodes=True)
    face_ui_root = [node for node in imported_nodes if FACE_UI_ROOT_NAME == node.name(long=None) and node.nodeType() == "transform"]
    face_facs_root = [node for node in imported_nodes if FACS_ROOT_NAME == node.name(long=None) and node.nodeType() == "transform"]
    if not all([face_ui_root, face_facs_root]):
        raise Exception(f"{FACS_ROOT_NAME} and {FACE_UI_ROOT_NAME} not in the imported data")
    pmc.parent([face_facs_root, face_ui_root], None)
    pmc.delete([node for node in imported_nodes if "_RIGGUIDES" in node.name(long=None)])
    return face_ui_root[0], face_facs_root[0]

@DECORATORS.x_timer
def _attach_guide_roots_to_transfer_mesh(transfer_mesh, face_root_nodes):
    face_ui_root, face_facs_root = face_root_nodes
    pin_nde_face_tweakers = ewaw_node.createNode(
        "uvPin",
        n="face_tweakers_pin",
        as_type="pymel",
    )
    transfer_mesh_shape = transfer_mesh.getShape(noIntermediate=False)
    transfer_mesh_shape.worldMesh[0].connect(pin_nde_face_tweakers.deformedGeometry)
    transfer_mesh_shape.worldMesh[0].connect(pin_nde_face_tweakers.originalGeometry)
    root_nodes = face_ui_root.getChildren(type="transform") + face_facs_root.getChildren(type="transform")
    constraint_list = [node for node in root_nodes if node.name(long=None) not in LEFT_FACE_STATIC_ROOTS]
    for node in root_nodes:
        node.addAttr("parent_root_nd", type="message")
        parent = node.getParent()
        parent.message.connect(node.parent_root_nd)
    static_roots = [node for node in root_nodes if node.name(long=None) in LEFT_FACE_STATIC_ROOTS]
    tmp_grp = pmc.createNode("transform")
    pmc.delete(pmc.parentConstraint(static_roots, tmp_grp))
    pmc.parent(static_roots, tmp_grp)
    constraint_list.append(tmp_grp)
    for index, root_node in enumerate(constraint_list):
        u_value, v_value = transfer_mesh_shape.getUVAtPoint(
                    root_node.getTranslation(worldSpace=True), space="world"
                )
        pin_nde_face_tweakers.attr(f"coordinate[{index}].coordinateU").set(u_value,
                                                          lock=True,
                                                          )
        pin_nde_face_tweakers.attr(f"coordinate[{index}].coordinateV").set(v_value,
                                                                  lock=True,
                                                                  )
        pin_trs = ewaw_node.createNode("transform",
                          n=f"{root_node.name(long=None)}_pin_trs",
                          as_type="pymel",
                          )
        pin_nde_face_tweakers.attr(f"outputMatrix[{index}]").connect(pin_trs.offsetParentMatrix,
                                                                        force=True,
                                                                        )
        pin_trs.inheritsTransform.set(False,
                              lock=True,
                              )
        pin_trs.setTranslation([0, 0, 0])
        pin_trs.setRotation([0, 0, 0])
        root_node.setParent(pin_trs)
    return root_nodes, pin_nde_face_tweakers

@DECORATORS.x_timer    
def _finalize_swapping(target_mesh, transfer_mesh, root_nodes, uv_pin_node):
    tmp_trgt_mesh = pmc.duplicate(target_mesh)
    pmc.blendShape(tmp_trgt_mesh, transfer_mesh, w=[(0, 1.0)])
    pin_nodes = []
    for node in root_nodes:
        pin_node = node.getParent(generations=2)
        if not pin_node:
            pin_node = node.getParent()
        parent = node.parent_root_nd.get()
        node.setParent(parent)
        pin_nodes.append(pin_node)
    pmc.delete(pin_nodes, transfer_mesh, tmp_trgt_mesh)
        
def execute(target_mesh, transfer_mesh=None, face_root_nodes=None):
    if not transfer_mesh:
        transfer_mesh = _get_source_body_mesh(TRANSFER_MESH_PATH)
    if not face_root_nodes:
        face_root_nodes = _get_face_guides_from_path(GENERIC_BIPED_GUIDE_TEMPLATE_PATH)
    root_nodes, uv_pin_node = _attach_guide_roots_to_transfer_mesh(transfer_mesh, face_root_nodes)
    _finalize_swapping(target_mesh, transfer_mesh, root_nodes, uv_pin_node)
    
execute(pmc.PyNode("rha_02:body_C_001_render_geo"))
