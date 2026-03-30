def proxy_all_guides():
    ribbon_guides = gather_all_guides()

    if not ribbon_guides:
        return

    skinning_proxies = list()

    for ribbon_net in ribbon_guides:
        proxy = build_skinning_proxy(ribbon_net)
        skinning_proxies.append(proxy)

    if len(skinning_proxies) > 1:
        ribbon_nde = pmc.polyUnite(skinning_proxies,
                                   name='mergedSkinProxy_C_001_geo',
                                   constructionHistory=False
                                   )[0]

        ribbon_shape = ribbon_nde.getShape()

        pmc.polyMultiLayoutUV(ribbon_shape,
                              scale=1,
                              rotateForBestFit=2,
                              layout=2
                              )

        return ribbon_nde.rename('skinProxy_C_001_geo')

    return skinning_proxies[0]


def build_skinning_proxy(ribbon_net):
    face_count = 1
    vertex_count = 4

    if isinstance(ribbon_net, str):
        ribbon_net = pmc.PyNode(ribbon_net)

    component_name = ribbon_net.ribbon_guide.get()

    start_nde = ribbon_net.start_pos.get()
    end_nde = ribbon_net.end_pos.get()

    translate_start = start_nde.getTranslation(worldSpace=True)
    translate_end = end_nde.getTranslation(worldSpace=True)

    # Create vertex positions
    vertices = OpenMaya.MFloatPointArray()
    vertices.append(OpenMaya.MFloatPoint(translate_start[0] + .01, translate_start[1], translate_start[2] + 1))
    vertices.append(OpenMaya.MFloatPoint(translate_start[0] + .01, translate_start[1], translate_start[2] - 1))

    # inbetween vertices

    vertices.append(OpenMaya.MFloatPoint(translate_end[0] - .01, translate_end[1], translate_end[2] + 1))
    vertices.append(OpenMaya.MFloatPoint(translate_end[0] - .01, translate_end[1], translate_end[2] - 1))

    # Vertex count for this polygon face
    face_vertexes = OpenMaya.MIntArray()
    face_vertexes.append(vertex_count)

    # Vertex indexes for this polygon face
    vertex_indexes = OpenMaya.MIntArray()
    vertex_indexes.append(2)
    vertex_indexes.append(3)
    vertex_indexes.append(1)
    vertex_indexes.append(0)

    # Create mesh
    mesh_object = OpenMaya.MObject()
    mesh = OpenMaya.MFnMesh()
    mesh.create(vertex_count, face_count, vertices, face_vertexes, vertex_indexes, mesh_object)
    mesh.updateSurface()

    # Assign default shading
    cmds.sets(mesh.name(), edit=True, forceElement="initialShadingGroup")
    skin_geo = pmc.PyNode(str(mesh.name())).getParent().rename('skinProxy_C_001_geo')
    return skin_geo