from maya.api import OpenMaya as om2

import uuid
from hashlib import sha256

SALT = "PXO_RIGGING_"


def generate_salted_hashed_uuid(name: str, type: str = "nde") -> tuple:
    encrypter = sha256()
    salted_name = f"{SALT}{name}"

    encrypter.update(salted_name.encode("utf-8"))
    sha_to_hex = encrypter.hexdigest()

    sliced_sha_hex = sha_to_hex[::2]

    hex_to_uuid = str(uuid.UUID(hex=sliced_sha_hex, is_safe=uuid.SafeUUID.unknown))

    savekept_uuid = f"{type}_{hex_to_uuid}"

    return name, savekept_uuid


def obfiscate_scene_destructive() -> set:
    # iterate over all the
    scene_nodes_iterator = om2.MItDependencyNodes()
    scene_renamer = om2.MDGModifier()
    names = set()

    while not scene_nodes_iterator.isDone():
        m_obj = scene_nodes_iterator.thisNode()

        dep_node = om2.MFnDependencyNode(m_obj)

        if any((dep_node.isLocked,
                dep_node.isDefaultNode,
                dep_node.isFromReferencedFile,
                m_obj.apiTypeStr in ("kReference", ""),
                )
               ):

            scene_nodes_iterator.next()
            continue

        old_name, new_name = generate_salted_hashed_uuid(dep_node.uniqueName())
        scene_renamer.renameNode(m_obj, new_name)
        names.add((old_name, new_name))

        scene_nodes_iterator.next()

    scene_renamer.doIt()
    return names


def obfiscate_attrs_destructive() -> set:
    # iterate over all the
    scene_nodes_iterator = om2.MItDependencyNodes()

    attrs = set()

    while not scene_nodes_iterator.isDone():
        m_obj = scene_nodes_iterator.thisNode()

        dep_node = om2.MFnDependencyNode(m_obj)

        if not dep_node.attributeCount():
            scene_nodes_iterator.next()
            continue

        for att_idx in range(dep_node.attributeCount()):
            att_ = dep_node.attribute(att_idx)
            plug_name = om2.MFnAttribute(att_).name

            plug_ = dep_node.findPlug(att_, 0)

            old_name, new_name = generate_salted_hashed_uuid(plug_name,
                                                             type="att"
                                                             )

            dep_node.setAlias(new_name, plug_name, plug_, add=True)

            attrs.add((old_name, new_name))

        scene_nodes_iterator.next()

    return attrs


def main():
    name_correspondance = obfiscate_scene_destructive()

    # np.array
    # np.array

    att_correspondance = obfiscate_attrs_destructive()
    # np.array
    # np.array



if __name__ == "__main__":
    main()