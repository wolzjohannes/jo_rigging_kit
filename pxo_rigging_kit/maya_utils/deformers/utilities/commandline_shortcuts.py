

# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from typing import List, Dict, Set

from future import standard_library

import logging

from maya import cmds as cmds

from pxo_rigging_kit.maya_utils import decorators, exceptions
from pxo_rigging_kit.maya_utils.deformers.handlers.deformer_handler import run_deformer_handler_no_ui
from pxo_rigging_kit.maya_utils.deformers.operators import skincluster_op
from pxo_rigging_kit.maya_utils.deformers.utilities.supply import get_external_skinclusters, get_internal_skinclusters

##########################################################
# GLOBALS
##########################################################

standard_library.install_aliases()

_LOGGER = logging.getLogger(f"{__name__}.py")
_LOGGER.setLevel(logging.INFO)

DECORATORS = decorators.Decorators()
DECORATORS.debug = True
DECORATORS.logger = _LOGGER

##########################################################
# FUNCTIONS
##########################################################


def _get_selected_internals():
    selected = set(cmds.ls(sl=True, exactType="transform"))

    internal = set(get_internal_skinclusters())

    transforms = sorted(selected & internal)

    return transforms


@DECORATORS.x_timer
def skincluster_export(transforms: List,
                       additional_parameters: Dict | None = None,
                       ):
    """Convenience wrapper for exporting skinClusters."""
    return run_deformer_handler_no_ui(
        transforms=transforms,
        operation="export",
        deformer_type="skin_cluster",
        additional_parameters=additional_parameters,
    )


@DECORATORS.x_timer
def skincluster_import(transforms: List[str],
                       additional_parameters: Dict | None = None):
    """Convenience wrapper for importing skinClusters."""

    return run_deformer_handler_no_ui(
        transforms=transforms,
        operation="import",
        deformer_type="skin_cluster",
        additional_parameters=additional_parameters,
    )


@DECORATORS.x_timer
def skincluster_prune(transforms: List[str],
                      additional_parameters: Dict | None = None,
                      ):
    """Convenience wrapper for pruning skinClusters."""

    return run_deformer_handler_no_ui(
        transforms=transforms,
        operation="prune",
        deformer_type="skin_cluster",
        additional_parameters=additional_parameters,
    )


@DECORATORS.x_timer
def skincluster_rename(transforms: List[str],
                       additional_parameters: Dict | None = None):
    """Convenience wrapper for renaming skinClusters."""

    return run_deformer_handler_no_ui(
        transforms=transforms,
        operation="rename",
        deformer_type="skin_cluster",
        additional_parameters=additional_parameters,
    )


def skincluster_transfer(from_geo: str,
                         to_geos: List[str]
                         ) -> Set:

    skin_main_operator = skincluster_op.SkinClusterOperator(from_geo)

    new_split_clusters = skin_main_operator.transfer_deformer(mesh_list=to_geos
                                                              )
    return new_split_clusters


def skincluster_import_newest():
    """Convenience wrapper for exporting selected skinClusters."""

    transforms = get_external_skinclusters()

    skincluster_import(transforms=transforms)

def skincluster_transfer_selected():

    selected = cmds.ls(sl=True, exactType="transform")
    if not selected or len(selected) <= 1:
        raise exceptions.SkinclusterError(f"Transfer Selection was {selected}, it should be: 1st item == From item, rest == To items")

    from_geo, *to_geos = selected
    print(from_geo)
    print(to_geos)
    skincluster_transfer(from_geo,
                         to_geos
                         )

def skincluster_export_selected():
    """Convenience wrapper for exporting selected skinClusters."""

    transforms = _get_selected_internals()

    skincluster_export(transforms=transforms)


def skincluster_import_selected():
    """Convenience wrapper for exporting selected skinClusters."""

    selected = set(cmds.ls(sl=True, exactType="transform"))
    external = set(get_external_skinclusters())

    transforms = sorted(selected & external)

    skincluster_import(transforms=transforms)


def skincluster_prune_selected():
    """Convenience wrapper for exporting selected skinClusters."""

    transforms = _get_selected_internals()

    skincluster_prune(transforms=transforms)


def skincluster_rename_selected():
    """Convenience wrapper for exporting selected skinClusters."""

    transforms = _get_selected_internals()

    skincluster_rename(transforms=transforms)



