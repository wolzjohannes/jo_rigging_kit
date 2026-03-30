from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from future import standard_library

import logging

from maya.api import OpenMaya as om2 # noqa: import error

from pxo_rigging_kit.maya_utils import exceptions
from pxo_rigging_kit.maya_utils.deformers.operators import skincluster_op

##########################################################
# GLOBALS
##########################################################

_LOGGER = logging.getLogger(f"{__name__}.py")
_LOGGER.setLevel(logging.INFO)


def transfer_skin_cluster(from_name: str,
                          to_names: list,
                          ):
    if not to_names:
        raise exceptions.SkinclusterError("Skin Transfer needs input: to_names:list")

    if isinstance(to_names, str):
        to_names = [to_names]

    skin_operator = skincluster_op.SkinClusterOperator(from_name)
    skin_operator.transfer_deformer(mesh_list=to_names)


def transfer_skin_cluster_selection_based():
    sel_ = om2.MGlobal.getActiveSelectionList()

    it_ = om2.MItSelectionList(sel_, om2.MFn.kTransform)
    sel_filtered = []

    while not it_.isDone():
        dag_path = it_.getDagPath()
        sel_filtered.append(dag_path.fullPathName())

        it_.next()

    try:
        from_name_, *to_names_ = sel_filtered
    except ValueError as e:
        raise exceptions.SkinclusterError(f"Selection for Skin Transfer was Empty: {e}")

    transfer_skin_cluster(from_name_,
                          to_names_,
                          )
