"""
Custom script for floating joints.
Floating joints are joints without hierarchy
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import built-in modules
import logging
import pprint
from itertools import chain

# Import third-party modules
import pymel.core as pmc
from future import standard_library
import mgear.shifter.custom_step as cstp

# Import local modules
from pxo_rigging_kit.maya_utils.mgear import mgear_build_utils
from pxo_rigging_kit.maya_utils.mgear.build_post_scripts import (
    pxo_bnd_jnt_setup,
)

standard_library.install_aliases()

##########################################################
# GLOBALS
##########################################################

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)

##########################################################
# FUNCTIONS
##########################################################


class CustomShifterStep(
    pxo_bnd_jnt_setup.CustomShifterStep, cstp.customShifterMainStep
):#
    COMPONENT = "visibility"
    def __init__(self):
        self.name = "pxo_floating_jnt_setup"
        self.acting_step_dict = None
        self.bnd_color_index = 18
        self.scale_factor = 2.0
        self.exclude_list = [
            "Dummy",
            "spikes",
            "scales",
            "Frills",
            "strap",
            #"saddle",
            "handle",
            "reinRope",
            "reinPin",
            "masterStrap",
            "strapMid",
            #"saddleRoot",
            "wingMembrane",
            "bigWingMembrane",
            "interpolateTail",
        ]

    def run(self, stepDict=None):
        self.acting_step_dict = stepDict["mgearRun"]
        rig_root_grp = stepDict["mgearRun"].model

        deformers_set = mgear_build_utils.get_deformers_set(stepDict)
        root_set = mgear_build_utils.get_top_set(stepDict)
        self.create_floating_joints(deformers_set, root_set, rig_root_grp)

    def create_floating_joints(
        self, deformer_set, top_set, mgear_rig_root_grp=None, deformers=None, exclude_list=None
    ):
        """
        Creates floating joints which can be used for skinning and speed up a DG evaluated rig.

        Args:
            deformer_set(pmc.PyNode): The deformers set.
            top_set(pmc.PyNode): The top set.
            mgear_rig_root_grp(pmc.PyNode, optional): The mgear rig root grp.
                                                      If given it will be used to connect the jnt_vis with the joints
                                                      visibility.
                                                      Default is None.
            deformers(List): The deformer nodes.
            exclude_list(List): List of strings to exclude from the creation.

        """
        result = []
        tmp_list = []
        if not deformers:
            deformers = deformer_set.members()
        if exclude_list is None:
            exclude_list = self.exclude_list
        if exclude_list:
            for node in deformers:
                for exclude_name in exclude_list:
                    node = pmc.PyNode(node)
                    if exclude_name in node.name(long=None):
                        tmp_list.append(node)
        execute_list = list(set(deformers) - set(tmp_list))
        for node_ in execute_list:
            node_ = pmc.PyNode(node_)
            mtx_con = list(
                set(
                    list(
                        chain.from_iterable(
                            [
                                node_.connections(
                                    s=True,
                                    d=False,
                                    et=True,
                                    type="mgear_matrixConstraint",
                                )
                            ]
                        )
                    )
                )
            )
            if mtx_con:
                driver_nd = mtx_con[0].driverMatrix.connections()[0]
                jnt = pmc.createNode(
                    "joint",
                    n=node_.name(long=None).replace("_bnd_", "_floating_"),
                )
                if mgear_rig_root_grp:
                    mgear_rig_root_grp=pmc.PyNode(mgear_rig_root_grp)
                    mgear_rig_root_grp.jnt_vis.connect(jnt.visibility)
                jnt.setMatrix(driver_nd.getMatrix(worldSpace=True), worldSpace=True)
                jnt.setParent(driver_nd)
                jnt.rotate.set(0.0, 0.0, 0.0)
                jnt.jointOrient.set(0.0, 0.0, 0.0)
                result.append(jnt)
        floating_joints_set = pmc.createNode(
            "objectSet", n="pxo_floating_jnt_set"
        )
        deformer_set = pmc.PyNode(deformer_set)
        deformer_set.addMembers(result)
        floating_joints_set.addMembers(result)
        pmc.PyNode(top_set).addMember(floating_joints_set)
        self.finish_bnd_joints(floating_joints_set, self.scale_factor)
