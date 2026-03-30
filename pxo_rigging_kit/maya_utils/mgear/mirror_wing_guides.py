from pymel import core as pmc

import logging
from re import search as regex_search
from future import standard_library

from pxo_rigging_kit.maya_utils import decorators
from pxo_rigging_kit.maya_utils.rigging import rig_utils

##########################################################
# GLOBALS
##########################################################

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)
RIG_ROOT_SUB_CONTAINERS = ["MGEAR", "MODEL_ASSETS", "XTRA", "NO_TRANSFORM"]
DECORATORS = decorators.Decorators()
DECORATORS.debug = True
DECORATORS.logger = _LOGGER
standard_library.install_aliases()


def mirror_sq_st_curves(name, side="R"):

    previous_side_prefix = "L"
    if side == "L":
        previous_side_prefix = "R"
    regex = r"_{side}_|{side}\d|{side}_".format(side=previous_side_prefix)
    name = "guide_{}_sq_st_{}_*_crv_grp".format(name, previous_side_prefix)
    selection = pmc.ls(name)
    if selection:
        for node in selection:
            dup = pmc.duplicate(node, un=True)[0]
            all_nodes = dup.getChildren(ad=True, type="transform")
            path_locs = [loc for loc in all_nodes if "_path_loc" in loc.name()]
            curve_nd = \
            [shape_.getTransform() for shape_ in dup.getChildren(ad=True) if shape_.nodeType() == "nurbsCurve"][0]
            curve_attrs = []
            locs_attrs = []

            for axe in "XYZ":
                for channel in ["translate", "rotate", "scale"]:
                    curve_attrs.append(curve_nd.attr("{}{}".format(channel, axe)))
                    [locs_attrs.append(loc.attr("{}{}".format(channel, axe))) for loc in path_locs]
            [attr_.unlock() for attr_ in curve_attrs]
            [loc_attr.unlock() for loc_attr in locs_attrs]

            mirror_grp = pmc.createNode("transform", n=dup.name().replace("_grp1", "_mirror_grp"))
            all_nodes.append(mirror_grp)
            pmc.parent(path_locs + [curve_nd], mirror_grp)
            dup.scaleX.set(-1)
            dup.addChild(mirror_grp)
            [attr_.lock() for attr_ in curve_attrs]
            [loc_attr.lock() for loc_attr in locs_attrs]
            dup.rename(dup.name().replace(previous_side_prefix, side).replace("_grp1", "_grp"))

            for node in all_nodes:
                node.rename(node.name().replace(previous_side_prefix, side))
                if node.hasAttr("parent_nd"):
                    parent_nd_str = node.parent_nd.get()
                    match = regex_search(regex, parent_nd_str)
                    if match:
                        old_side = match.group(0)
                        new_side = old_side.replace(previous_side_prefix, side)
                        node.parent_nd.set(parent_nd_str.replace(old_side, new_side))
            logging.info("Mirrored sq/st system: {}".format(node.name()))

    else:
        logging.error("No guides found with name: {}".format(name))


def mirror(names_: tuple = ("wingMembrane", "bigWingMembrane"), sides_: tuple = ("L", "R")):

    with pmc.UndoChunk():
        mirror_sq_st_curves("bigWingMembrane", "R")

        for side_ in sides_:
            for name_ in names_:
                composed_name_base = f"guide_{name_}_{side_}_*_root_grp"
                for composed_name_ in pmc.ls(composed_name_base):

                    WingMembrane = rig_utils.LinearRibbon(composed_name_)
                    WingMembrane.mirror_guide_ribbon()

                    logging.info(f"Mirrored {composed_name_.name()} wingSetup.")


# if __name__ == "__main__":
#     mirror()
#

