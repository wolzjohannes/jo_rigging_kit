from pymel import core as pmc  # noqa: import error

from pxo_rigging_kit import constants
from pxo_rigging_kit.io_version_control import version_io
from pxo_rigging_kit.maya_utils import paths_utils


def _get_external_items(import_location: str):
    _ALLOWED_OBJECT_TYPES = ["mesh", "nurbsSurface", "nurbsCurve"]

    export_path = paths_utils.get_project_paths(pmc.sceneName()) / import_location

    scene_items = set(
        mesh.getParent().shortName()
        for mesh in pmc.ls(typ=_ALLOWED_OBJECT_TYPES,
                           noIntermediate=True,
                           )
    )

    exported_geo_nodes = version_io.list_scene_directory_overlap(scene_items=scene_items,
                                                                 directory=export_path,
                                                                 )

    return exported_geo_nodes


def _get_internal_items(type_in_scene: str):

    return sorted(list(
        set(
            [
                str(skc.getGeometry()[0].getParent().shortName())
                for skc in pmc.ls(exactType=type_in_scene)
                if skc.getGeometry()
            ]
        )
    ))


def get_external_skinclusters():
    return _get_external_items(constants.PXO_FILEPATH_SKIN)


def get_internal_skinclusters():
    return _get_internal_items("skinCluster")


def get_external_blendshapes():
    return _get_external_items(constants.PXO_FILEPATH_BSHP)


def get_internal_blendshapes():
    return _get_internal_items("blendShape")

