"""
Custom script to prepare the mgear quadrupad legs to our needs.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import built-in modules
import logging
import itertools

# Import third-party modules
from future import standard_library
from maya import cmds
import mgear.shifter.custom_step as cstp
from pymel import core as pmc

# Import local modules
from pxo_rigging_kit.maya_utils.mgear import mgear_build_utils
from pxo_rigging_kit.maya_utils.rigging import rig_utils

#######################################################
# GLOBALS
#######################################################
standard_library.install_aliases()

logging.basicConfig(level=logging)
_LOGGER = logging.getLogger(__name__ + ".py")

#######################################################
# CLASSES
#######################################################


class CustomShifterStep(cstp.customShifterMainStep):
    """

    """

    def __init__(self):
        self.name = "pxo_crowd_post"

        self.limbs = ("arm", "leg")
        self.sides = ("R", "L", "C")

        self.max_expected_subdivs = 20
        self.acting_step_dict = None

    def run(self, stepDict):
        self.acting_step_dict = stepDict["mgearRun"]

        def construct_component_templates(limbs=("arm", "leg"), sides=("R", "L", "C")):
            return [f"{x}_{y}" for x in limbs for y in sides]

        limb_templates = construct_component_templates(limbs=self.limbs,
                                                       sides=self.sides,
                                                       )

        limb_components = [mgear_build_utils.get_nonhost_components(self.acting_step_dict,limb_template)
                           for limb_template in limb_templates
                           ]

        limb_components = [limb_component for limb_component in limb_components if limb_component]

        limb_components_flattened = set(itertools.chain.from_iterable(limb_components))

        limb_component_and_joints = {limb_component: mgear_build_utils.get_component_jnts(self.acting_step_dict,
                                                                                          comp_key=limb_component)[0:-1]
                                     for limb_component in limb_components_flattened
                                     }

        limb_component_and_joints_sorted = sort_limb_components_and_joints(limb_component_and_joints)

        for (keeps, deletes) in limb_component_and_joints_sorted.values():

            keeps_old = keeps.copy()
            keeps_parent = keeps_old[0].getParent()

            for keep in keeps:
                pmc.parent(keep, world=True)

            keeps.reverse()

            for iteration_ in range(len(keeps)-1):
                pmc.parent(keeps[iteration_],
                           keeps[iteration_+1]
                           )

            pmc.delete(deletes)

            for iteration_, keep in enumerate(keeps_old):
                keep_name_old = keep.shortName()
                keep_name_decomposed = keep_name_old.split("_")

                keep_name_decomposed[4] = str(iteration_)

                keep_name_new = "_".join(keep_name_decomposed)
                keep.rename(keep_name_new)

            pmc.parent(keeps_old[0], keeps_parent)

            # re-constrain

            constraint_master_new = remove_mgear_constraining(keeps_old)

            add_pxo_constraining(constraint_master_new, keeps_old)


def sort_limb_components_and_joints(limb_component_and_joints):
    limb_component_and_joints_sorted = dict()
    for key, value in limb_component_and_joints.items():
        keeps = list()
        deletes = list()

        val_len = len(value)

        for val in range(val_len):
            if val == 0 or val == val_len - 1 or val == int(val_len / 2):
                keeps.append(value[val])

            else:
                deletes.append(value[val])
        limb_component_and_joints_sorted[key] = (keeps, deletes,)
    return limb_component_and_joints_sorted


def add_pxo_constraining(constraint_master_new, keeps_old):

    for attr in keeps_old[1].listAttr():
        try:
            attr.set(l=False)
        except:
            pass

    rig_utils.pxo_constraining([constraint_master_new],
                               [keeps_old[1]],
                               maintainOffset=False,
                               name=None,
                               skipRotate=None,
                               skipTranslate=None,
                               skipScale=None,
                               native=False,
                               space_switch=False,
                               host=None,
                               constraint_tag=None,
                               use_parent_offset_mtx=False,
                               )
    for axis in "XYZ":
        keeps_old[1].attr(f"jointOrient{axis}").set(0)


def remove_mgear_constraining(keeps_old):
    matrix_constraint = keeps_old[1].translate.listConnections()[0]
    constraint_master_old = matrix_constraint.driverMatrix.listConnections()[0]
    constraint_master_name = constraint_master_old.shortName()
    constraint_master_name_new = constraint_master_name.split("div")
    constraint_master_name_new_seg = constraint_master_name_new[-1].split("_")
    constraint_master_name_new_seg[0] = str(int(constraint_master_name_new_seg[0]) + 1)
    constraint_master_name_new[-1] = "_".join(constraint_master_name_new_seg)
    constraint_master_name = "div".join(constraint_master_name_new)
    constraint_master_new = pmc.PyNode(constraint_master_name)

    # kill off joint
    pmc.delete(matrix_constraint)
    return constraint_master_new

