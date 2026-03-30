"""
Module for rigging control curve shapes creation.

Examples:
    >>> from pxo_rigging_kit.maya_utils.rigging import curves_utils
    >>> crv_inst = curves_utils.LocalRotateAxesControl()
    >>> crv_inst.create_curve(color_index=None)
    >>> print(crv_inst.control, crv_inst.buffer_grp)

"""
from __future__ import (
    division,
    absolute_import,
    print_function,
    unicode_literals,
)

# Import built-in modules
# Import python standart import
import logging
from importlib import reload


# Import third-party modules
# Import maya modules
from pymel import core as pmc

from pxo_rigging_kit import constants
# Import local modules
from pxo_rigging_kit import string_utils
from pxo_rigging_kit.maya_utils import attributes_utils
from pxo_rigging_kit.maya_utils import dag_utils
from pxo_rigging_kit.maya_utils.rigging import rig_utils
reload(dag_utils)
reload(rig_utils)
reload(attributes_utils)

##########################################################
# GLOBALS
##########################################################

_LOGGER = logging.getLogger(f"{__name__}.py")

##########################################################
# FUNCTIONS
##########################################################
def create_nurbs_curve(
    knots,
    degree=1,
    locators=True,
    locatorScale=(1, 1, 1),
    name="curve",
    visibility=1,
):
    """
    Create a curve based on inputs.
    By default, it will have locators to control the curve points.

    Args:
            knots(list): Curve knotes position.
                          Items can be tuples or pmc.PyNode() object.
            Selected transforms or vector data.
            degree(int): The curve type. By Default is it 1.
            {1:"linear", 3:"cubic"}
            locators(bool): Enable control locators.
            name(str): The curve name.
            visibility(bool): Curve visibility. True by default.

    Returns:
            Dict: {"curve":pmc.PyNode(), "locators":List}

    """
    locs = None
    temp = [
        knot.getMatrix(worldSpace=True).translate
        for knot in knots
        if isinstance(knot, pmc.nodetypes.Transform)
    ]
    if not temp:
        temp = knots

    curve = pmc.curve(d=degree, p=temp, n=name)
    curve.visibility.set(visibility)
    if locators:
        locs = rig_utils.locators_on_cv(
            curve.getShape(), connect=True, locatorScale=locatorScale
        )
        for count, node in enumerate(locs):
            node.rename("{}_{}_loc".format(name, str(count)))
    return {"curve": curve, "locators": locs}


def create_curve_from_transforms(
    selection, degree=1, cv_driver: str = "loc", name: str = "curve",
):
    """
    Create a curve based on selected transforms.
    By default, it will have locators to control the curve points.

    Args:
            selection(list): Selected transforms.
            degree(int): The curve type. By Default is it "linear"
            cv_driver(str): Enable control lacotors.
            name(str): The curve name.

    Returns:
            Tuple: (The created curve, list of locators or none)

    """
    _operations = {"loc": _cvs_as_locs,
                   "nodes": _cvs_as_matrices,
                   }

    knots = [node.getMatrix(worldSpace=True).translate for node in selection]
    curve = pmc.curve(d=degree, p=knots, n=name)

    # checks if the key is in _operations, the value is the function to execute
    func_ = _operations.get(cv_driver, False)

    if not func_:
        _LOGGER.error("Nothing choosen as curve drivers.")
        raise

    locs = func_(curve, name)

    return curve, locs


def _cvs_as_locs(curve, name):
    locs = rig_utils.locators_on_cv(curve.getShape(), connect=True)
    for count, node in enumerate(locs):
        node.rename("{}_{}_LOC".format(name, str(count)))

    return locs


def _cvs_as_matrices(curve, name):
    raise NotImplementedError("we need a way to create curve without locators. "
                              "the locators are useless if not used for further ops")


def get_curve_class_inst(snake_name):
    sub_classes = ControlCurves.__subclasses__()
    for sub_class in sub_classes:
        sub_name = sub_class.__name__
        sub_name = sub_name.replace('Control', '')
        sub_snake_name = string_utils.camel_to_snake(sub_name)

        if snake_name == sub_snake_name:
            return sub_class


def get_curve_snake_names():
    sub_classes = ControlCurves.__subclasses__()
    names = set()
    for sub_class in sub_classes:
        name = sub_class.__name__
        name = name.replace('Control', '')
        name = string_utils.camel_to_snake(name)
        names.add(name)

    name_list = list(names)
    name_list.sort()

    return name_list


def create_curve_by_snake_name(snake_name,
                               name="M_control_0_CON",
                               match=None,
                               scale=None,
                               color_index=17,
                               buffer_grp=True,
                               child=None,
                               lock_translate=False,
                               lock_rotate=False,
                               lock_scale=False,
                               lock_visibility=False,
                               move=None,
                               rotate=None):
    sub_class_inst = get_curve_class_inst(snake_name)()

    if match:
        match = pmc.PyNode(match)

    sub_class_inst.create_curve(name,
                                match,
                                scale,
                                color_index,
                                buffer_grp,
                                child,
                                lock_translate,
                                lock_rotate,
                                lock_scale,
                                lock_visibility,
                                move,
                                rotate)

    control = sub_class_inst.control
    buffer_grp = sub_class_inst.buffer_grp

    return control, buffer_grp


def replace_shapes_from_snake_name(snake_name, transform):
    pynodes = rig_utils.convert_to_pynode_list(transform)

    if not pynodes:
        return

    snake_control, buffer = create_curve_by_snake_name(snake_name, buffer_grp=False)

    pmc.delete(pynodes[0].getShapes())
    pmc.parent(snake_control.getShapes(), pynodes[0], r=True, s=True)
    pmc.delete(snake_control)

    shapes = pynodes[0].getShapes()
    for shape in shapes:
        shape.isHistoricallyInteresting.set(False)
        pmc.rename(shape, str(pynodes[0]) + "Shape")

    pmc.select(pynodes[0])


##########################################################
# CLASSES
##########################################################


class ControlCurves(object):
    """
    Create Control Curve class.
    """

    def __init__(self):
        self.control = None
        self.buffer_grp = None

    def create_curve(
            self,
            name="M_control_0_CON",
            match=None,
            scale=None,
            color_index=17,
            buffer_grp=True,
            child=None,
            lock_translate=False,
            lock_rotate=False,
            lock_scale=False,
            lock_visibility=False,
            move=None,
            rotate=None,
            tag=None,
            as_type=None,
            scale_display = False
    ):
        """
        Create curve method.

        Args:
            name(str): The control name.
            match(dagnode or matrix): The node for transform match.
            scale(list, tuple, None): The scale values.

            color_index(integer): The color of the test_single_control.
                                    Valid is:
                                     0:GREY,
                                     1:BLACK,
                                     2:DARKGREY,
                                     3:BRIGHTGREY,
                                     4:RED,
                                     5:DARKBLUE,
                                     6:BRIGHTBLUE,
                                     7:GREEN,
                                     8:DARKLILA,
                                     9:MAGENTA,
                                     10:BRIGHTBROWN,
                                     11:BROWN,
                                     12:DIRTRED,
                                     13:BRIGHTRED,
                                     14:BRIGHTGREEN,
                                     15:BLUE,
                                     16:WHITE,
                                     17:BRIGHTYELLOW,
                                     18:CYAN,
                                     19:TURQUOISE,
                                     20:LIGHTRED,
                                     21:LIGHTORANGE,
                                     22:LIGHTYELLOW,
                                     23:DIRTGREEN,
                                     24:LIGHTBROWN,
                                     25:DIRTYELLOW,
                                     26:LIGHTGREEN,
                                     27:LIGHTGREEN2,
                                     28:LIGHTBLUE

            buffer_grp(bool): Create buffer_grp for the test_single_control.
            child(dagnode): The child of the test_single_control.
            lock_translate(list, bool): Valid is ['tx','ty','tz']
            lock_rotate(list, bool): Valid is ['rx,'ry','rz']
            lock_scale(list, bool): Valid is ['sx','sy','sz']
            lock_visibility(bool): Lock/Hide the visibility channels.
            move(list, bool): Move the control curve shape.
            rotate(list, bool): Rotate the control curve shape.
            tag (): None.
            as_type (): None.


        """

        self.control = self.get_curve(name)
        shapes = self.control.getShapes()

        for shape in shapes:
            shape.isHistoricallyInteresting.set(False)
            pmc.rename(shape, f"{name}Shape")

        if scale:
            for shape_ in shapes:
                pmc.scale(shape_.cv[0:], scale)

        if scale_display:
            for shape_ in shapes:
                shape_.lineWidth.set(scale_display)

        if rotate:
            for shape_ in shapes:
                pmc.select(shape_.cv[0:])
                cmds.rotate(rotate[0], rotate[1], rotate[2], ws=True)
                # pmc.rotate was not working properly
                # pmc.rotate(rotate[0], rotate[1], rotate[2], ws=True)

                pmc.select(clear=True)

        if move:
            for shape__ in shapes:
                pmc.move(
                    shape__.cv[0:],
                    move,
                    r=True,
                    os=True,
                    wd=True,
                    xn=True,
                    xc="edge",
                )

        if match:
            # Normalize 'match' to a world-space 16-float matrix (strict in 2025)
            if isinstance(match, pmc.datatypes.Matrix):
                mm = match
            elif isinstance(match, (list, tuple)) and len(match) == 16:
                # Already a flat 16 list/tuple
                mm = pmc.datatypes.Matrix([match[0:4], match[4:8], match[8:12], match[12:16]])
            else:
                # Accept str or PyNode, ensure PyNode and grab its WS matrix
                tgt = pmc.PyNode(match)
                mm = tgt.getMatrix(worldSpace=True)

            m16 = [mm[i][j] for i in range(4) for j in range(4)]
            cmds.xform(self.control.name(), ws=True, m=m16)

        if color_index:
            for shape__ in shapes:
                shape__.overrideEnabled.set(1)
                shape__.overrideColor.set(color_index)

        if buffer_grp:
            self.buffer_grp = dag_utils.create_buffer_groups([self.control])[0]

        if child:
            self.control.addChild(child)

        if lock_translate:
            attributes_utils.lock_and_hide_attributes(
                self.control, attributes=lock_translate
            )

        if lock_rotate:
            attributes_utils.lock_and_hide_attributes(
                self.control, attributes=lock_rotate
            )

        if lock_scale:
            attributes_utils.lock_and_hide_attributes(
                self.control, attributes=lock_scale
            )

        if lock_visibility:
            attributes_utils.lock_and_hide_attributes(
                self.control, attributes="visibility"
            )

        if tag:
            self.control.addAttr(tag, at="message")

        if as_type != "operator":
            self.control.addAttr(constants.RIG_SYS_CONTROL_TAG, at="bool")
            pmc.addAttr(self.control.attr(constants.RIG_SYS_CONTROL_TAG), edit=True, dv=True)

            self.control.attr(constants.RIG_SYS_CONTROL_TAG).set(True, lock=True)

            ctrl_tag = pmc.createNode("controller", n=f"{name}_TAG")

        else:
            self.control.addAttr(constants.EWAW_OP_SUB_TAG, at="bool")
            pmc.addAttr(self.control.attr(constants.EWAW_OP_SUB_TAG), edit=True, dv=True)

            self.control.attr(constants.EWAW_OP_SUB_TAG).set(True, lock=True)

        self.control_name = name

        return name



    def get_curve(self, name):
        """
        Template method which has to implement in each derivation of this class.

        Args:
            name(str): The curve name.
        """

        raise pmc.PyNode(name)


class BoxControl(ControlCurves):
    """
    Create Box Control Curve.
    """

    def get_curve(self, name):
        return pmc.curve(
            degree=1,
            p=(
                (0.5, 0.5, 0.5),
                (0.5, 0.5, -0.5),
                (-0.5, 0.5, -0.5),
                (-0.5, -0.5, -0.5),
                (0.5, -0.5, -0.5),
                (0.5, 0.5, -0.5),
                (-0.5, 0.5, -0.5),
                (-0.5, 0.5, 0.5),
                (0.5, 0.5, 0.5),
                (0.5, -0.5, 0.5),
                (0.5, -0.5, -0.5),
                (-0.5, -0.5, -0.5),
                (-0.5, -0.5, 0.5),
                (0.5, -0.5, 0.5),
                (-0.5, -0.5, 0.5),
                (-0.5, 0.5, 0.5),
            ),
            k=(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15),
            n=name,
        )


class PyramideControl(ControlCurves):
    """
    Create Pyramide Control Curve.
    """

    def get_curve(self, name):
        return pmc.curve(
            degree=1,
            p=(
                (0, 2, 0),
                (1, 0, -1),
                (-1, 0, -1),
                (0, 2, 0),
                (-1, 0, 1),
                (1, 0, 1),
                (0, 2, 0),
                (1, 0, -1),
                (1, 0, 1),
                (-1, 0, 1),
                (-1, 0, -1),
            ),
            k=(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10),
            n=name,
        )


class QuaderControl(ControlCurves):
    """
    Create Quader Control Curve.
    """

    def get_curve(self, name):
        return pmc.curve(
            degree=1,
            p=(
                (0.5, 3.5, 0.5),
                (0.5, 3.5, -0.5),
                (-0.5, 3.5, -0.5),
                (-0.5, -3.5, -0.5),
                (0.5, -3.5, -0.5),
                (0.5, 3.5, -0.5),
                (-0.5, 3.5, -0.5),
                (-0.5, 3.5, 0.5),
                (0.5, 3.5, 0.5),
                (0.5, -3.5, 0.5),
                (0.5, -3.5, -0.5),
                (-0.5, -3.5, -0.5),
                (-0.5, -3.5, 0.5),
                (0.5, -3.5, 0.5),
                (-0.5, -3.5, 0.5),
                (-0.5, 3.5, 0.5),
            ),
            k=(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15),
            n=name,
        )


class SphereControl(ControlCurves):
    """
    Create Sphere Control Curve.
    """

    def get_curve(self, name):
        return pmc.curve(
            degree=1,
            p=(
                (0, 0, 1),
                (0, 0.5, 0.866025),
                (0, 0.866025, 0.5),
                (0, 1, 0),
                (0, 0.866025, -0.5),
                (0, 0.5, -0.866025),
                (0, 0, -1),
                (0, -0.5, -0.866025),
                (0, -0.866025, -0.5),
                (0, -1, 0),
                (0, -0.866025, 0.5),
                (0, -0.5, 0.866025),
                (0, 0, 1),
                (0.707107, 0, 0.707107),
                (1, 0, 0),
                (0.707107, 0, -0.707107),
                (0, 0, -1),
                (-0.707107, 0, -0.707107),
                (-1, 0, 0),
                (-0.866025, 0.5, 0),
                (-0.5, 0.866025, 0),
                (0, 1, 0),
                (0.5, 0.866025, 0),
                (0.866025, 0.5, 0),
                (1, 0, 0),
                (0.866025, -0.5, 0),
                (0.5, -0.866025, 0),
                (0, -1, 0),
                (-0.5, -0.866025, 0),
                (-0.866025, -0.5, 0),
                (-1, 0, 0),
                (-0.707107, 0, 0.707107),
                (0, 0, 1),
            ),
            k=(
                0,
                1,
                2,
                3,
                4,
                5,
                6,
                7,
                8,
                9,
                10,
                11,
                12,
                13,
                14,
                15,
                16,
                17,
                18,
                19,
                20,
                21,
                22,
                23,
                24,
                25,
                26,
                27,
                28,
                29,
                30,
                31,
                32,
            ),
            n=name,
        )


class SquareControl(ControlCurves):
    """
    Create Square Control Curve.
    """

    def get_curve(self, name):
        return pmc.curve(
            degree=1,
            p=((1, 0, -1), (-1, 0, -1), (-1, 0, 1), (1, 0, 1), (1, 0, -1)),
            k=(0, 1, 2, 3, 4),
            n=name,
        )


class CircleControl(ControlCurves):
    """
    Create Circle Control Curve.
    """

    def get_curve(self, name):
        return pmc.circle(
            c=(0, 0, 0),
            nr=(0, 1, 0),
            sw=360,
            r=1,
            d=3,
            ut=0,
            tol=0.01,
            s=8,
            ch=0,
            n=name,
        )[0]


class DoubleCircleControl(ControlCurves):
    """
    Create a Double Circle Control Curve.
    """

    def get_curve(self, name):
        circle0 = pmc.circle(
            c=(0, 0, 0),
            nr=(0, 1, 0),
            sw=360,
            r=1,
            d=3,
            ut=0,
            tol=0.01,
            s=8,
            ch=0,
            n=name,
        )[0]
        circle1 = pmc.circle(
            c=(0, 0, 0),
            nr=(0, 1, 0),
            sw=360,
            r=1,
            d=3,
            ut=0,
            tol=0.01,
            s=8,
            ch=0,
            n=name,
        )[0]
        for cv in range(8):
            circle1.getShape().controlPoints[cv].yValue.set(0.5)
        pmc.parent(circle1.getShape(), circle0, r=True, shape=True)
        pmc.delete(circle1)
        return circle0


class HexagonControl(ControlCurves):
    """
    Create a Hexagon Control Curve.
    """

    def get_curve(self, name):
        return pmc.curve(
            degree=1,
            p=(
                (-0.5, 1, 0.866025),
                (0.5, 1, 0.866025),
                (0.5, -1, 0.866025),
                (1, -1, 0),
                (1, 1, 0),
                (0.5, 1, -0.866025),
                (0.5, -1, -0.866025),
                (-0.5, -1, -0.866026),
                (-0.5, 1, -0.866026),
                (-1, 1, -1.5885e-007),
                (-1, -1, -1.5885e-007),
                (-0.5, -1, 0.866025),
                (-0.5, 1, 0.866025),
                (-1, 1, -1.5885e-007),
                (-0.5, 1, -0.866026),
                (0.5, 1, -0.866025),
                (1, 1, 0),
                (0.5, 1, 0.866025),
                (0.5, -1, 0.866025),
                (-0.5, -1, 0.866025),
                (-1, -1, -1.5885e-007),
                (-0.5, -1, -0.866026),
                (0.5, -1, -0.866025),
                (1, -1, 0),
            ),
            k=(
                0,
                1,
                2,
                3,
                4,
                5,
                6,
                7,
                8,
                9,
                10,
                11,
                12,
                13,
                14,
                15,
                16,
                17,
                18,
                19,
                20,
                21,
                22,
                23,
            ),
            n=name,
        )


class SingleArrowControl(ControlCurves):
    """
    Create Single Arrow Control Curve.
    """

    def get_curve(self, name):
        return pmc.curve(
            degree=1,
            p=(
                (0, 0, -1.32),
                (-0.99, 0, 0),
                (-0.33, 0, 0),
                (-0.33, 0, 0.99),
                (0.33, 0, 0.99),
                (0.33, 0, 0),
                (0.99, 0, 0),
                (0, 0, -1.32),
            ),
            k=(0, 1, 2, 3, 4, 5, 6, 7),
            n=name,
        )


class ArrowsOnBallControl(ControlCurves):
    """
    Create Arrows On Ball Control Curve.
    """

    def get_curve(self, name):
        return pmc.curve(
            degree=1,
            p=(
                (0, 0.35, -1.001567),
                (-0.336638, 0.677886, -0.751175),
                (-0.0959835, 0.677886, -0.751175),
                (-0.0959835, 0.850458, -0.500783),
                (-0.0959835, 0.954001, -0.0987656),
                (-0.500783, 0.850458, -0.0987656),
                (-0.751175, 0.677886, -0.0987656),
                (-0.751175, 0.677886, -0.336638),
                (-1.001567, 0.35, 0),
                (-0.751175, 0.677886, 0.336638),
                (-0.751175, 0.677886, 0.0987656),
                (-0.500783, 0.850458, 0.0987656),
                (-0.0959835, 0.954001, 0.0987656),
                (-0.0959835, 0.850458, 0.500783),
                (-0.0959835, 0.677886, 0.751175),
                (-0.336638, 0.677886, 0.751175),
                (0, 0.35, 1.001567),
                (0.336638, 0.677886, 0.751175),
                (0.0959835, 0.677886, 0.751175),
                (0.0959835, 0.850458, 0.500783),
                (0.0959835, 0.954001, 0.0987656),
                (0.500783, 0.850458, 0.0987656),
                (0.751175, 0.677886, 0.0987656),
                (0.751175, 0.677886, 0.336638),
                (1.001567, 0.35, 0),
                (0.751175, 0.677886, -0.336638),
                (0.751175, 0.677886, -0.0987656),
                (0.500783, 0.850458, -0.0987656),
                (0.0959835, 0.954001, -0.0987656),
                (0.0959835, 0.850458, -0.500783),
                (0.0959835, 0.677886, -0.751175),
                (0.336638, 0.677886, -0.751175),
                (0, 0.35, -1.001567),
            ),
            k=(
                0,
                1,
                2,
                3,
                4,
                5,
                6,
                7,
                8,
                9,
                10,
                11,
                12,
                13,
                14,
                15,
                16,
                17,
                18,
                19,
                20,
                21,
                22,
                23,
                24,
                25,
                26,
                27,
                28,
                29,
                30,
                31,
                32,
            ),
            n=name,
        )


class SingleArrowThinControl(ControlCurves):
    """
    Create a Single Arrow Thin Control Curve.
    """

    def get_curve(self, name):
        return pmc.curve(
            degree=1,
            p=((0, 0, 1), (0, 0, -1), (-1, 0, 0), (0, 0, -1), (1, 0, 0)),
            k=(0, 1, 2, 3, 4),
            n=name,
        )


class SingleArrowNormalControl(ControlCurves):
    """
    Create a Single Arrow Normal Control Curve.
    """

    def get_curve(self, name):
        return pmc.curve(
            degree=1,
            p=(
                (0, 0, -1.32),
                (-0.99, 0, 0),
                (-0.33, 0, 0),
                (-0.33, 0, 0.99),
                (0.33, 0, 0.99),
                (0.33, 0, 0),
                (0.99, 0, 0),
                (0, 0, -1.32),
            ),
            k=(0, 1, 2, 3, 4, 5, 6, 7),
            n=name,
        )


class SingleArrowFatControl(ControlCurves):
    """
    Create a Single Arrow Fat Control Curve.
    """

    def get_curve(self, name):
        return pmc.curve(
            degree=1,
            p=(
                (0, 0, -0.99),
                (-0.66, 0, 0),
                (-0.33, 0, 0),
                (-0.33, 0, 0.66),
                (0.33, 0, 0.66),
                (0.33, 0, 0),
                (0.66, 0, 0),
                (0, 0, -0.99),
            ),
            k=(0, 1, 2, 3, 4, 5, 6, 7),
            n=name,
        )


class DoubleArrowThinControl(ControlCurves):
    """
    Create a Double Arrow Thin Control Curve.
    """

    def get_curve(self, name):
        return pmc.curve(
            degree=1,
            p=(
                (1, 0, 1),
                (0, 0, 2),
                (-1, 0, 1),
                (0, 0, 2),
                (0, 0, -2),
                (-1, 0, -1),
                (0, 0, -2),
                (1, 0, -1),
            ),
            k=(0, 1, 2, 3, 4, 5, 6, 7),
            n=name,
        )


class DoubleArrowNormalControl(ControlCurves):
    """
    Create Double Arrow Normal Control Curve.
    """

    def get_curve(self, name):
        return pmc.curve(
            degree=1,
            p=(
                (0, 0, -2.31),
                (-0.99, 0, -0.99),
                (-0.33, 0, -0.99),
                (-0.33, 0, 0.99),
                (-0.99, 0, 0.99),
                (0, 0, 2.31),
                (0.99, 0, 0.99),
                (0.33, 0, 0.99),
                (0.33, 0, -0.99),
                (0.99, 0, -0.99),
                (0, 0, -2.31),
            ),
            k=(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10),
            n=name,
        )


class DoubleArrowFatControl(ControlCurves):
    """
    Create Double Arrow Fat Control Curve.
    """

    def get_curve(self, name):
        return pmc.curve(
            degree=1,
            p=(
                (0, 0, -1.35),
                (-0.66, 0, -0.36),
                (-0.33, 0, -0.36),
                (-0.33, 0, 0.36),
                (-0.66, 0, 0.36),
                (0, 0, 1.35),
                (0.66, 0, 0.36),
                (0.33, 0, 0.36),
                (0.33, 0, -0.36),
                (0.66, 0, -0.36),
                (0, 0, -1.35),
            ),
            k=(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10),
            n=name,
        )


class FourArrowThinControl(ControlCurves):
    """
    Create Four Arrow Thin Control Curve.
    """

    def get_curve(self, name):
        return pmc.curve(
            degree=1,
            p=(
                (1.25, 0, -0.5),
                (1.75, 0, 0),
                (1.25, 0, 0.5),
                (1.75, 0, 0),
                (-1.75, 0, 0),
                (-1.25, 0, -0.5),
                (-1.75, 0, 0),
                (-1.25, 0, 0.5),
                (-1.75, 0, 0),
                (0, 0, 0),
                (0, 0, 1.75),
                (-0.5, 0, 1.25),
                (0, 0, 1.75),
                (0.5, 0, 1.25),
                (0, 0, 1.75),
                (0, 0, -1.75),
                (0.5, 0, -1.25),
                (0, 0, -1.75),
                (-0.5, 0, -1.25),
                (0, 0, -1.75),
            ),
            k=(
                0,
                1,
                2,
                3,
                4,
                5,
                6,
                7,
                8,
                9,
                10,
                11,
                12,
                13,
                14,
                15,
                16,
                17,
                18,
                19,
            ),
            n=name,
        )


class FourArrowNormalControl(ControlCurves):
    """
    Create Four Arrow Normal Control Curve.
    """

    def get_curve(self, name):
        return pmc.curve(
            degree=1,
            p=(
                (0, 0, -1.98),
                (-0.495, 0, -1.32),
                (-0.165, 0, -1.32),
                (-0.165, 0, -0.165),
                (-1.32, 0, -0.165),
                (-1.32, 0, -0.495),
                (-1.98, 0, 0),
                (-1.32, 0, 0.495),
                (-1.32, 0, 0.165),
                (-0.165, 0, 0.165),
                (-0.165, 0, 1.32),
                (-0.495, 0, 1.32),
                (0, 0, 1.98),
                (0.495, 0, 1.32),
                (0.165, 0, 1.32),
                (0.165, 0, 0.165),
                (1.32, 0, 0.165),
                (1.32, 0, 0.495),
                (1.98, 0, 0),
                (1.32, 0, -0.495),
                (1.32, 0, -0.165),
                (0.165, 0, -0.165),
                (0.165, 0, -1.32),
                (0.495, 0, -1.32),
                (0, 0, -1.98),
            ),
            k=(
                0,
                1,
                2,
                3,
                4,
                5,
                6,
                7,
                8,
                9,
                10,
                11,
                12,
                13,
                14,
                15,
                16,
                17,
                18,
                19,
                20,
                21,
                22,
                23,
                24,
            ),
            n=name,
        )


class FourArrowFatControl(ControlCurves):
    """
    Create Four Arrow Fat Control Curve.
    """

    def get_curve(self, name):
        return pmc.curve(
            degree=1,
            p=(
                (0, 0, -1.98),
                (-0.495, 0, -1.32),
                (-0.165, 0, -1.32),
                (-0.165, 0, -0.165),
                (-1.32, 0, -0.165),
                (-1.32, 0, -0.495),
                (-1.98, 0, 0),
                (-1.32, 0, 0.495),
                (-1.32, 0, 0.165),
                (-0.165, 0, 0.165),
                (-0.165, 0, 1.32),
                (-0.495, 0, 1.32),
                (0, 0, 1.98),
                (0.495, 0, 1.32),
                (0.165, 0, 1.32),
                (0.165, 0, 0.165),
                (1.32, 0, 0.165),
                (1.32, 0, 0.495),
                (1.98, 0, 0),
                (1.32, 0, -0.495),
                (1.32, 0, -0.165),
                (0.165, 0, -0.165),
                (0.165, 0, -1.32),
                (0.495, 0, -1.32),
                (0, 0, -1.98),
            ),
            k=(
                0,
                1,
                2,
                3,
                4,
                5,
                6,
                7,
                8,
                9,
                10,
                11,
                12,
                13,
                14,
                15,
                16,
                17,
                18,
                19,
                20,
                21,
                22,
                23,
                24,
            ),
            n=name,
        )


class Rot180ArrowThinControl(ControlCurves):
    """
    Create Rotation 180 Arrow Thin Control Curve.
    """

    def get_curve(self, name):
        return pmc.curve(
            degree=1,
            p=(
                (-0.446514, 0, -1.351664),
                (0.0107043, 0, -1.001418),
                (-0.339542, 0, -0.5442),
                (0.0107043, 0, -1.001418),
                (-0.13006, 0, -1),
                (-0.393028, 0, -0.947932),
                (-0.725413, 0, -0.725516),
                (-0.947961, 0, -0.392646),
                (-1.026019, 0, 0),
                (-0.947961, 0, 0.392646),
                (-0.725413, 0, 0.725516),
                (-0.393028, 0, 0.947932),
                (-0.13006, 0, 1),
                (0, 0, 1),
                (-0.339542, 0, 0.5442),
                (0, 0, 1),
                (-0.446514, 0, 1.351664),
            ),
            k=(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16),
            n=name,
        )


class Rot180ArrowNormalControl(ControlCurves):
    """
    Create Rotation 180 Arrow Normal Control Curve.
    """

    def get_curve(self, name):
        return pmc.curve(
            degree=1,
            p=(
                (-0.251045, 0, -1.015808),
                (-0.761834, 0, -0.979696),
                (-0.486547, 0, -0.930468),
                (-0.570736, 0, -0.886448),
                (-0.72786, 0, -0.774834),
                (-0.909301, 0, -0.550655),
                (-1.023899, 0, -0.285854),
                (-1.063053, 0, 9.80765e-009),
                (-1.023899, 0, 0.285854),
                (-0.909301, 0, 0.550655),
                (-0.72786, 0, 0.774834),
                (-0.570736, 0, 0.886448),
                (-0.486547, 0, 0.930468),
                (-0.761834, 0, 0.979696),
                (-0.251045, 0, 1.015808),
                (-0.498915, 0, 0.567734),
                (-0.440202, 0, 0.841857),
                (-0.516355, 0, 0.802034),
                (-0.658578, 0, 0.701014),
                (-0.822676, 0, 0.498232),
                (-0.926399, 0, 0.258619),
                (-0.961797, 0, 8.87346e-009),
                (-0.926399, 0, -0.258619),
                (-0.822676, 0, -0.498232),
                (-0.658578, 0, -0.701014),
                (-0.516355, 0, -0.802034),
                (-0.440202, 0, -0.841857),
                (-0.498915, 0, -0.567734),
                (-0.251045, 0, -1.015808),
            ),
            k=(
                0,
                1,
                2,
                3,
                4,
                5,
                6,
                7,
                8,
                9,
                10,
                11,
                12,
                13,
                14,
                15,
                16,
                17,
                18,
                19,
                20,
                21,
                22,
                23,
                24,
                25,
                26,
                27,
                28,
            ),
            n=name,
        )


class Rot180ArrowFatControl(ControlCurves):
    """
    Create Rotation 180 Arrow Fat Control Curve.
    """

    def get_curve(self, name):
        return pmc.curve(
            degree=1,
            p=(
                (-0.124602, 0, -1.096506),
                (-0.975917, 0, -1.036319),
                (-0.559059, 0, -0.944259),
                (-0.798049, 0, -0.798033),
                (-1.042702, 0, -0.431934),
                (-1.128672, 0, 0),
                (-1.042702, 0, 0.431934),
                (-0.798049, 0, 0.798033),
                (-0.560906, 0, 0.946236),
                (-0.975917, 0, 1.036319),
                (-0.124602, 0, 1.096506),
                (-0.537718, 0, 0.349716),
                (-0.440781, 0, 0.788659),
                (-0.652776, 0, 0.652998),
                (-0.853221, 0, 0.353358),
                (-0.923366, 0, 0),
                (-0.853221, 0, -0.353358),
                (-0.652776, 0, -0.652998),
                (-0.439199, 0, -0.785581),
                (-0.537718, 0, -0.349716),
                (-0.124602, 0, -1.096506),
            ),
            k=(
                0,
                1,
                2,
                3,
                4,
                5,
                6,
                7,
                8,
                9,
                10,
                11,
                12,
                13,
                14,
                15,
                16,
                17,
                18,
                19,
                20,
            ),
            n=name,
        )


class ConeControl(ControlCurves):
    """
    Create Cone Control Curve.
    """

    def get_curve(self, name):
        return pmc.curve(
            degree=1,
            p=(
                (0.5, -1, 0.866025),
                (-0.5, -1, 0.866025),
                (0, 1, 0),
                (0.5, -1, 0.866025),
                (1, -1, 0),
                (0, 1, 0),
                (0.5, -1, -0.866025),
                (1, -1, 0),
                (0, 1, 0),
                (-0.5, -1, -0.866026),
                (0.5, -1, -0.866025),
                (0, 1, 0),
                (-1, -1, -1.5885e-007),
                (-0.5, -1, -0.866026),
                (0, 1, 0),
                (-0.5, -1, 0.866025),
                (-1, -1, -1.5885e-007),
            ),
            k=(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16),
            n=name,
        )


class EightArrowControl(ControlCurves):
    """
    Create Eight Arrow Control Curve.
    """

    def get_curve(self, name):
        return pmc.curve(
            degree=1,
            p=(
                (-1.8975, 0, 0),
                (-1.4025, 0, 0.37125),
                (-1.4025, 0, 0.12375),
                (-0.380966, 0, 0.157801),
                (-1.079222, 0, 0.904213),
                (-1.254231, 0, 0.729204),
                (-1.341735, 0, 1.341735),
                (-0.729204, 0, 1.254231),
                (-0.904213, 0, 1.079222),
                (-0.157801, 0, 0.380966),
                (-0.12375, 0, 1.4025),
                (-0.37125, 0, 1.4025),
                (0, 0, 1.8975),
                (0.37125, 0, 1.4025),
                (0.12375, 0, 1.4025),
                (0.157801, 0, 0.380966),
                (0.904213, 0, 1.079222),
                (0.729204, 0, 1.254231),
                (1.341735, 0, 1.341735),
                (1.254231, 0, 0.729204),
                (1.079222, 0, 0.904213),
                (0.380966, 0, 0.157801),
                (1.4025, 0, 0.12375),
                (1.4025, 0, 0.37125),
                (1.8975, 0, 0),
                (1.4025, 0, -0.37125),
                (1.4025, 0, -0.12375),
                (0.380966, 0, -0.157801),
                (1.079222, 0, -0.904213),
                (1.254231, 0, -0.729204),
                (1.341735, 0, -1.341735),
                (0.729204, 0, -1.254231),
                (0.904213, 0, -1.079222),
                (0.157801, 0, -0.380966),
                (0.12375, 0, -1.4025),
                (0.37125, 0, -1.4025),
                (0, 0, -1.8975),
                (-0.37125, 0, -1.4025),
                (-0.12375, 0, -1.4025),
                (-0.157801, 0, -0.380966),
                (-0.904213, 0, -1.079222),
                (-0.729204, 0, -1.254231),
                (-1.341735, 0, -1.341735),
                (-1.254231, 0, -0.729204),
                (-1.079222, 0, -0.904213),
                (-0.380966, 0, -0.157801),
                (-1.4025, 0, -0.12375),
                (-1.4025, 0, -0.37125),
                (-1.8975, 0, 0),
            ),
            k=(
                0,
                1,
                2,
                3,
                4,
                5,
                6,
                7,
                8,
                9,
                10,
                11,
                12,
                13,
                14,
                15,
                16,
                17,
                18,
                19,
                20,
                21,
                22,
                23,
                24,
                25,
                26,
                27,
                28,
                29,
                30,
                31,
                32,
                33,
                34,
                35,
                36,
                37,
                38,
                39,
                40,
                41,
                42,
                43,
                44,
                45,
                46,
                47,
                48,
            ),
            n=name,
        )


class SpiralControl(ControlCurves):
    """
    Create Spiral Control Curve.
    """

    def get_curve(self, name):
        return pmc.curve(
            degree=3,
            p=(
                (0.474561, 0, -1.241626),
                (0.171579, 0, -1.214307),
                (-0.434384, 0, -1.159672),
                (-1.124061, 0, -0.419971),
                (-1.169741, 0, 0.305922),
                (-0.792507, 0, 1.018176),
                (-0.0412486, 0, 1.262687),
                (0.915809, 0, 1.006098),
                (1.258635, 0, 0.364883),
                (1.032378, 0, -0.461231),
                (0.352527, 0, -0.810017),
                (-0.451954, 0, -0.43765),
                (-0.634527, 0, 0.208919),
                (-0.0751226, 0, 0.696326),
                (0.292338, 0, 0.414161),
                (0.476068, 0, 0.273078),
            ),
            k=(0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 13, 13),
            n=name,
        )


class CrossControl(ControlCurves):
    """
    Create Cross Control Curve.
    """

    def get_curve(self, name):
        return pmc.curve(
            degree=1,
            p=(
                (0.4, 0, -0.4),
                (0.4, 0, -2),
                (-0.4, 0, -2),
                (-0.4, 0, -0.4),
                (-2, 0, -0.4),
                (-2, 0, 0.4),
                (-0.4, 0, 0.4),
                (-0.4, 0, 2),
                (0.4, 0, 2),
                (0.4, 0, 0.4),
                (2, 0, 0.4),
                (2, 0, -0.4),
                (0.4, 0, -0.4),
            ),
            k=(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12),
            n=name,
        )


class FatCrossControl(ControlCurves):
    """
    Create Fat Cross Control Curve.
    """

    def get_curve(self, name):
        return pmc.curve(
            degree=1,
            p=(
                (2, 0, 1),
                (2, 0, -1),
                (1, 0, -1),
                (1, 0, -2),
                (-1, 0, -2),
                (-1, 0, -1),
                (-2, 0, -1),
                (-2, 0, 1),
                (-1, 0, 1),
                (-1, 0, 2),
                (1, 0, 2),
                (1, 0, 1),
                (2, 0, 1),
            ),
            k=(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12),
            n=name,
        )


class SpearControl(ControlCurves):
    """
    Create Spear Control Curve.
    """

    def get_curve(self, name):
        return pmc.curve(
            degree=1,
            p=(
                (0, 2, 0),
                (0, 0, 2),
                (0, 0, -2),
                (0, 2, 0),
                (-2, 0, 0),
                (2, 0, 0),
                (0, 2, 0),
            ),
            k=(0, 1, 2, 3, 4, 5, 6),
            n=name,
        )


class SpearControl1(ControlCurves):
    """
    Create Spear Variante Control Curve.
    """

    def get_curve(self, name):
        return pmc.curve(
            degree=1,
            p=(
                (0, 2, 0),
                (0, 0, 2),
                (0, -2, 0),
                (0, 0, -2),
                (0, 2, 0),
                (0, -2, 0),
                (0, 0, 0),
                (0, 0, 2),
                (0, 0, -2),
                (2, 0, 0),
                (0, 0, 2),
                (-2, 0, 0),
                (0, 0, -2),
                (0, 0, 2),
                (0, 0, 0),
                (-2, 0, 0),
                (2, 0, 0),
            ),
            k=(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16),
            n=name,
        )


class TransformControl(ControlCurves):
    """
    Create Transform Control Curve.
    """

    def get_curve(self, name):
        circle = pmc.circle(
            c=(0, 0, 0),
            nr=(0, 1, 0),
            sw=360,
            r=1.5,
            d=3,
            ut=0,
            tol=0.01,
            s=8,
            ch=0,
            n=name,
        )[0]
        arrow0 = pmc.curve(
            d=1,
            p=(
                (1.75625, 0, 0.115973),
                (1.75625, 0, -0.170979),
                (2.114939, 0, -0.170979),
                (2.114939, 0, -0.314454),
                (2.473628, 0, -0.0275029),
                (2.114939, 0, 0.259448),
                (2.114939, 0, 0.115973),
                (1.75625, 0, 0.115973),
            ),
            k=(0, 1, 2, 3, 4, 5, 6, 7),
            n=name,
        )
        arrow1 = pmc.curve(
            d=1,
            p=(
                (0.143476, 0, -1.783753),
                (0.143476, 0, -2.142442),
                (0.286951, 0, -2.142442),
                (0, 0, -2.501131),
                (-0.286951, 0, -2.142442),
                (-0.143476, 0, -2.142442),
                (-0.143476, 0, -1.783753),
                (0.143476, 0, -1.783753),
            ),
            k=(0, 1, 2, 3, 4, 5, 6, 7),
            n=name,
        )
        arrow2 = pmc.curve(
            d=1,
            p=(
                (-1.75625, 0, -0.170979),
                (-2.114939, 0, -0.170979),
                (-2.114939, 0, -0.314454),
                (-2.473628, 0, -0.0275029),
                (-2.114939, 0, 0.259448),
                (-2.114939, 0, 0.115973),
                (-1.75625, 0, 0.115973),
                (-1.75625, 0, -0.170979),
            ),
            k=(0, 1, 2, 3, 4, 5, 6, 7),
            n=name,
        )
        arrow3 = pmc.curve(
            d=1,
            p=(
                (-0.143476, 0, 1.728747),
                (-0.143476, 0, 2.087436),
                (-0.286951, 0, 2.087436),
                (0, 0, 2.446125),
                (0.286951, 0, 2.087436),
                (0.143476, 0, 2.087436),
                (0.143476, 0, 1.728747),
                (-0.143476, 0, 1.728747),
            ),
            k=(0, 1, 2, 3, 4, 5, 6, 7),
            n=name,
        )
        pmc.parent(arrow0.getShape(), circle, r=True, shape=True)
        pmc.parent(arrow1.getShape(), circle, r=True, shape=True)
        pmc.parent(arrow2.getShape(), circle, r=True, shape=True)
        pmc.parent(arrow3.getShape(), circle, r=True, shape=True)
        pmc.delete(arrow0, arrow1, arrow2, arrow3)
        return circle


class FootPrintControl(ControlCurves):
    """
    Create Foot Print Control Curve.
    """

    def get_curve(self, name):
        return pmc.curve(
            d=1,
            p=(
                (-0.081122, 0, -1.11758),
                (0.390719, 0, -0.921584),
                (0.514124, 0, -0.616704),
                (0.412496, 0, 0.0293557),
                (0.86256, 0, 0.552008),
                (0.920632, 0, 1.161772),
                (0.775452, 0, 1.669908),
                (0.38346, 0, 2.011088),
                (-0.131936, 0, 2.330484),
                (-0.552964, 0, 2.308708),
                (-0.654588, 0, 1.691688),
                (-0.57474, 0, 0.63912),
                (-0.364226, 0, 0.109206),
                (-0.531184, 0, -0.39893),
                (-0.465852, 0, -0.841736),
                (-0.081122, 0, -1.11758),
            ),
            k=(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15),
            n=name,
        )


class CurvedCircleControl(ControlCurves):
    """
    Create Curved Circle Control Curve.
    """

    def get_curve(self, name):
        values = [
            {"cv": 0, "value": [0.466, -0.235, -0.784]},
            {"cv": 1, "value": [0, 0.235, -1.108]},
            {"cv": 2, "value": [-0.466, -0.235, -0.784]},
            {"cv": 3, "value": [-1.108, 0.109, 0]},
            {"cv": 4, "value": [-0.466, -0.235, 0.784]},
            {"cv": 5, "value": [0, 0.235, 1.108]},
            {"cv": 6, "value": [0.466, -0.235, 0.784]},
            {"cv": 7, "value": [1.108, 0.109, 0]},
        ]
        circle = pmc.circle(
            c=(0, 0, 0),
            nr=(0, 1, 0),
            sw=360,
            r=1,
            d=3,
            ut=0,
            tol=0.01,
            s=8,
            ch=0,
            n=name,
        )[0]
        for v in values:
            circle.getShape().controlPoints[v["cv"]].xValue.set(v["value"][0])
            circle.getShape().controlPoints[v["cv"]].yValue.set(v["value"][1])
            circle.getShape().controlPoints[v["cv"]].zValue.set(v["value"][2])
        return circle


class DoubleCurvedCircleControl(ControlCurves):
    """
    Create Double Curved Circle Control Curve.
    """

    def get_curve(self, name):
        values0 = [
            {"cv": 0, "value": [0.466, -0.235, -0.784]},
            {"cv": 1, "value": [0, 0.235, -1.108]},
            {"cv": 2, "value": [-0.466, -0.235, -0.784]},
            {"cv": 3, "value": [-1.108, 0.109, 0]},
            {"cv": 4, "value": [-0.466, -0.235, 0.784]},
            {"cv": 5, "value": [0, 0.235, 1.108]},
            {"cv": 6, "value": [0.466, -0.235, 0.784]},
            {"cv": 7, "value": [1.108, 0.109, 0]},
        ]
        values1 = [
            {"cv": 0, "value": [0.466, -0.176, -0.784]},
            {"cv": 1, "value": [0, 0.294, -1.108]},
            {"cv": 2, "value": [-0.466, -0.176, -0.784]},
            {"cv": 3, "value": [-1.108, 0.168, 0]},
            {"cv": 4, "value": [-0.466, -0.176, 0.784]},
            {"cv": 5, "value": [0, 0.294, 1.108]},
            {"cv": 6, "value": [0.466, -0.176, 0.784]},
            {"cv": 7, "value": [1.108, 0.168, 0]},
        ]
        circle0 = pmc.circle(
            c=(0, 0, 0),
            nr=(0, 1, 0),
            sw=360,
            r=1,
            d=3,
            ut=0,
            tol=0.01,
            s=8,
            ch=0,
            n=name,
        )[0]
        circle1 = pmc.circle(
            c=(0, 0, 0),
            nr=(0, 1, 0),
            sw=360,
            r=1,
            d=3,
            ut=0,
            tol=0.01,
            s=8,
            ch=0,
            n=name,
        )[0]
        for v in values0:
            circle0.getShape().controlPoints[v["cv"]].xValue.set(v["value"][0])
            circle0.getShape().controlPoints[v["cv"]].yValue.set(v["value"][1])
            circle0.getShape().controlPoints[v["cv"]].zValue.set(v["value"][2])
        for v in values1:
            circle1.getShape().controlPoints[v["cv"]].xValue.set(v["value"][0])
            circle1.getShape().controlPoints[v["cv"]].yValue.set(v["value"][1])
            circle1.getShape().controlPoints[v["cv"]].zValue.set(v["value"][2])
        pmc.parent(circle1.getShape(), circle0, r=True, shape=True)
        pmc.delete(circle1)
        return circle0


class LocatorControl(ControlCurves):
    """
    Create Locator Control Curve.
    """

    def get_curve(self, name):
        line0 = pmc.curve(d=1, p=((5, 0, 0), (-5, 0, 0)), k=(0, 1), n=name)
        line1 = pmc.curve(d=1, p=((0, 5, 0), (0, -5, 0)), k=(0, 1), n=name)
        line2 = pmc.curve(d=1, p=((0, 0, 5), (0, 0, -5)), k=(0, 1), n=name)
        pmc.parent(line1.getShape(), line0, r=True, shape=True)
        pmc.parent(line2.getShape(), line0, r=True, shape=True)
        pmc.delete(line1, line2)
        return line0


class JointControl(ControlCurves):
    """
    Create Joint Control Curve.
    """

    def get_curve(self, name):
        line_0 = pmc.curve(
            d=1, p=((5, 0, 0), (-5, 0, 0)), k=(0, 1), n=name + "_tmp"
        )
        line_1 = pmc.curve(
            d=1, p=((0, 5, 0), (0, -5, 0)), k=(0, 1), n=name + "_tmp"
        )
        line_2 = pmc.curve(
            d=1, p=((0, 0, 5), (0, 0, -5)), k=(0, 1), n=name + "_tmp"
        )
        sphere_ctrl = pmc.curve(
            degree=1,
            p=(
                (0, 0, 1),
                (0, 0.5, 0.866025),
                (0, 0.866025, 0.5),
                (0, 1, 0),
                (0, 0.866025, -0.5),
                (0, 0.5, -0.866025),
                (0, 0, -1),
                (0, -0.5, -0.866025),
                (0, -0.866025, -0.5),
                (0, -1, 0),
                (0, -0.866025, 0.5),
                (0, -0.5, 0.866025),
                (0, 0, 1),
                (0.707107, 0, 0.707107),
                (1, 0, 0),
                (0.707107, 0, -0.707107),
                (0, 0, -1),
                (-0.707107, 0, -0.707107),
                (-1, 0, 0),
                (-0.866025, 0.5, 0),
                (-0.5, 0.866025, 0),
                (0, 1, 0),
                (0.5, 0.866025, 0),
                (0.866025, 0.5, 0),
                (1, 0, 0),
                (0.866025, -0.5, 0),
                (0.5, -0.866025, 0),
                (0, -1, 0),
                (-0.5, -0.866025, 0),
                (-0.866025, -0.5, 0),
                (-1, 0, 0),
                (-0.707107, 0, 0.707107),
                (0, 0, 1),
            ),
            k=(
                0,
                1,
                2,
                3,
                4,
                5,
                6,
                7,
                8,
                9,
                10,
                11,
                12,
                13,
                14,
                15,
                16,
                17,
                18,
                19,
                20,
                21,
                22,
                23,
                24,
                25,
                26,
                27,
                28,
                29,
                30,
                31,
                32,
            ),
            n=name,
        )
        pmc.parent(line_0.getShape(), sphere_ctrl, r=True, shape=True)
        pmc.parent(line_1.getShape(), sphere_ctrl, r=True, shape=True)
        pmc.parent(line_2.getShape(), sphere_ctrl, r=True, shape=True)
        pmc.delete([line_0, line_1, line_2])
        return sphere_ctrl


class LocalRotateAxesControl(ControlCurves):
    """
    Create a local rotate axes control.
    If color_index is None.
    The Y axes is green, X axes red and Z is blue.
    """

    def get_curve(self, name):
        arrow_0 = pmc.curve(
            degree=1,
            p=(
                [0, 0, 0],
                [3.804, 0, 0],
                [2.282, -0.761, 0],
                [3.804, 0, 0],
                [2.282, 0.761, 0],
            ),
            k=(0, 1, 2, 3, 4),
            n=name,
        )
        arrow_1 = pmc.curve(
            degree=1,
            p=(
                [0, 0, 0],
                [0, 0, 3.793],
                [0, -0.761, 2.271],
                [0, 0, 3.793],
                [0, 0.761, 2.271],
            ),
            k=(0, 1, 2, 3, 4),
            n=name,
        )
        arrow_2 = pmc.curve(
            degree=1,
            p=(
                [0, 0, 0],
                [0, 3.797, 0],
                [0.761, 2.275, 0],
                [0, 3.797, 0],
                [-0.761, 2.275, 0],
            ),
            k=(0, 1, 2, 3, 4),
            n=name,
        )
        pmc.parent(arrow_1.getShape(), arrow_0, r=True, shape=True)
        pmc.parent(arrow_2.getShape(), arrow_0, r=True, shape=True)
        pmc.delete(arrow_1, arrow_2)
        for color_index, shape in zip([13, 6, 14], arrow_0.getShapes()):
            shape.overrideEnabled.set(1)
            shape.overrideColor.set(color_index)
        return arrow_0


class DiamondControl(ControlCurves):
    """
    Create a diamond look like control.
    """

    def get_curve(self, name):
        spear_controls = [
            pmc.curve(
                degree=1,
                p=(
                    (0, 2, 0),
                    (0, 0, 2),
                    (0, -2, 0),
                    (0, 0, -2),
                    (0, 2, 0),
                    (0, -2, 0),
                    (0, 0, 0),
                    (0, 0, 2),
                    (0, 0, -2),
                    (2, 0, 0),
                    (0, 0, 2),
                    (-2, 0, 0),
                    (0, 0, -2),
                    (0, 0, 2),
                    (0, 0, 0),
                    (-2, 0, 0),
                    (2, 0, 0),
                ),
                k=(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16),
                n=name,
            )
            for x in range(3)
        ]
        pmc.rotate(spear_controls[1].cv[:], 0, 45, 0)
        pmc.rotate(spear_controls[2].cv[:], 0, -45, 0)
        spear_controls[0].addChild(
            spear_controls[1].getShape(), r=True, shape=True
        )
        spear_controls[0].addChild(
            spear_controls[2].getShape(), r=True, shape=True
        )
        pmc.delete(spear_controls[1:])
        return spear_controls[0]


class CirclePointControl(ControlCurves):
    def get_curve(self, name):
        curve = pmc.curve(
            degree=1,
            p=(
                (-0.2, 0, -0.6),
                (-0.2, 0, -0.7),
                (-0.3, 0, -0.7),
                (0, 0, -1),
                (0.3, 0, -0.7),
                (0.2, 0, -0.7),
                (0.2, 0, -0.6),
                (0.243049, 0, -0.586772),
                (0.352852, 0, -0.528081),
                (0.449096, 0, -0.449096),
                (0.528081, 0, -0.352852),
                (0.586772, 0, -0.243049),
                (0.6, 0, -0.2),
                (0.7, 0, -0.2),
                (0.7, 0, -0.3),
                (1, 0, 0),
                (0.7, 0, 0.3),
                (0.7, 0, 0.2),
                (0.6, 0, 0.2),
                (0.586772, 0, 0.243049),
                (0.528081, 0, 0.352852),
                (0.449096, 0, 0.449096),
                (0.352852, 0, 0.528081),
                (0.243049, 0, 0.586772),
                (0.2, 0, 0.6),
                (0.2, 0, 0.7),
                (0.3, 0, 0.7),
                (0, 0, 1),
                (-0.3, 0, 0.7),
                (-0.2, 0, 0.7),
                (-0.2, 0, 0.6),
                (-0.243049, 0, 0.586772),
                (-0.352852, 0, 0.528081),
                (-0.449096, 0, 0.449096),
                (-0.528081, 0, 0.352852),
                (-0.586772, 0, 0.243049),
                (-0.6, 0, 0.2),
                (-0.7, 0, 0.2),
                (-0.7, 0, 0.3),
                (-1, 0, 0),
                (-0.7, 0, -0.3),
                (-0.7, 0, -0.2),
                (-0.6, 0, -0.2),
                (-0.586772, 0, -0.243049),
                (-0.528081, 0, -0.352852),
                (-0.449096, 0, -0.449096),
                (-0.352852, 0, -0.528081),
                (-0.243049, 0, -0.586772),
                (-0.2, 0, -0.6),
            ),
            k=(
                0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
                10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
                20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
                30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
                40, 41, 42, 43, 44, 45, 46, 47, 48,
            ),
            n=name
        )

        return curve


class ThinCylinderControl(ControlCurves):
    def get_curve(self, name):
        curve = pmc.curve(
            degree=1,
            p=(
                (-1.63913e-07, -0.06136, 1),
                (-1.63913e-07, 0.06136, 1),
                (-0.19509, 0.06136, 0.980785),
                (-0.382683, 0.06136, 0.923879),
                (-0.55557, 0.06136, 0.831469),
                (-0.707107, 0.06136, 0.707106),
                (-0.831469, 0.06136, 0.55557),
                (-0.923879, 0.06136, 0.382683),
                (-0.980785, 0.06136, 0.19509),
                (-0.999999, 0.06136, -3.27826e-07),
                (-0.980785, 0.06136, -0.195091),
                (-0.923879, 0.06136, -0.382683),
                (-0.831469, 0.06136, -0.55557),
                (-0.707106, 0.06136, -0.707106),
                (-0.555569, 0.06136, -0.831469),
                (-0.382683, 0.06136, -0.923879),
                (-0.19509, 0.06136, -0.980784),
                (4.47035e-07, 0.06136, -0.999999),
                (0.195091, 0.06136, -0.980784),
                (0.382683, 0.06136, -0.923878),
                (0.55557, 0.06136, -0.831468),
                (0.707106, 0.06136, -0.707106),
                (0.831469, 0.06136, -0.555569),
                (0.923879, 0.06136, -0.382683),
                (0.980784, 0.06136, -0.19509),
                (1, 0.06136, 0),
                (0.980785, 0.06136, 0.19509),
                (0.923879, 0.06136, 0.382683),
                (0.831469, 0.06136, 0.55557),
                (0.707107, 0.06136, 0.707107),
                (0.55557, 0.06136, 0.83147),
                (0.382683, 0.06136, 0.923879),
                (0.19509, 0.06136, 0.980785),
                (-1.63913e-07, 0.06136, 1),
                (-1.63913e-07, -0.06136, 1),
                (0.19509, -0.06136, 0.980785),
                (0.382683, -0.06136, 0.923879),
                (0.55557, -0.06136, 0.83147),
                (0.707107, -0.06136, 0.707107),
                (0.831469, -0.06136, 0.55557),
                (0.923879, -0.06136, 0.382683),
                (0.980785, -0.06136, 0.19509),
                (1, -0.06136, 0),
                (1, 0.06136, 0),
                (1, -0.06136, 0),
                (0.980784, -0.06136, -0.19509),
                (0.923879, -0.06136, -0.382683),
                (0.831469, -0.06136, -0.555569),
                (0.707106, -0.06136, -0.707106),
                (0.55557, -0.06136, -0.831468),
                (0.382683, -0.06136, -0.923878),
                (0.195091, -0.06136, -0.980784),
                (4.47035e-07, -0.06136, -0.999999),
                (4.47035e-07, 0.06136, -0.999999),
                (4.47035e-07, -0.06136, -0.999999),
                (-0.19509, -0.06136, -0.980784),
                (-0.382683, -0.06136, -0.923879),
                (-0.555569, -0.06136, -0.831469),
                (-0.707106, -0.06136, -0.707106),
                (-0.831469, -0.06136, -0.55557),
                (-0.923879, -0.06136, -0.382683),
                (-0.980785, -0.06136, -0.195091),
                (-0.999999, -0.06136, -3.27826e-07),
                (-0.999999, 0.06136, -3.27826e-07),
                (-0.999999, -0.06136, -3.27826e-07),
                (-0.980785, -0.06136, 0.19509),
                (-0.923879, -0.06136, 0.382683),
                (-0.831469, -0.06136, 0.55557),
                (-0.707107, -0.06136, 0.707106),
                (-0.55557, -0.06136, 0.831469),
                (-0.382683, -0.06136, 0.923879),
                (-0.19509, -0.06136, 0.980785),
                (-1.63913e-07, -0.06136, 1),
            ),
            k=tuple(range(73)),
            n=name
        )

        return curve


class PrismControl(ControlCurves):
    def get_curve(self, name):
        curve = pmc.curve(
            degree=1,
            p=(
                (-0.353553, -0.000354052, -0.353553),
                (0.353553, -0.000354052, -0.353553),
                (0.353553, 0.000354052, 0.353553),
                (-0.353553, -0.000354052, 0.353553),
                (-0.353553, 0.000354052, -0.353553),
                (0, 0.5, 0),
                (0.353553, 0.000354052, 0.353553),
                (-0.353553, -0.000354052, 0.353553),
                (0, 0.5, 0),
                (0.353553, -0.000354052, -0.353553),
                (0, -0.5, 0),
                (-0.353553, -0.000354052, 0.353553),
                (0.353553, 0.000354052, 0.353553),
                (0, -0.5, 0),
                (-0.353553, -0.000354052, -0.353553),
            ),
            k=tuple(range(15)),
            n=name
        )

        return curve


class OctagonControl(ControlCurves):

    def get_curve(self, name):
        octagon_ctrl = pmc.curve(
            degree=1,
            p=(
                (-1, 0, 0),
                (-0.7, 0, -0.7),
                (0, 0, -1),
                (0.7, 0, -0.7),
                (1, 0, 0),
                (0.7, 0, 0.7),
                (0, 0, 1),
                (-0.7, 0, 0.7),
                (-1, 0, 0),
            ),
            k=tuple(range(9)),
            n=name
        )

        return octagon_ctrl


class AsteriskControl(ControlCurves):
    def get_curve(self, name):
        asterisk = pmc.curve(
            degree=1,
            p=(
                (-0.139133, 0, -0.335897),
                (-0.130526, 0, -0.991445),
                (0.130526, 0, -0.991445),
                (0.139133, 0, -0.335897),
                (0.608761, 0, -0.793353),
                (0.793353, 0, -0.608761),
                (0.335897, 0, -0.139133),
                (0.991445, 0, -0.130526),
                (0.991445, 0, 0.130526),
                (0.335897, 0, 0.139133),
                (0.793353, 0, 0.608761),
                (0.608761, 0, 0.793353),
                (0.139133, 0, 0.335897),
                (0.130526, 0, 0.991445),
                (-0.130526, 0, 0.991445),
                (-0.139133, 0, 0.335897),
                (-0.608761, 0, 0.793353),
                (-0.793353, 0, 0.608761),
                (-0.335897, 0, 0.139133),
                (-0.991445, 0, 0.130526),
                (-0.991445, 0, -0.130526),
                (-0.335897, 0, -0.139133),
                (-0.793353, 0, -0.608761),
                (-0.608761, 0, -0.793353),
                (-0.139133, 0, -0.335897),
            ),
            k=tuple(range(25)),
            n=name
        )
        return asterisk


class CircleArrowControl(ControlCurves):
    def get_curve(self, name):
        arrow_circle = pmc.curve(
            degree=1,
            p=(
                (0, 0.5, -0.2),
                (-0.0765367, 0.5, -0.184776),
                (-0.141421, 0.5, -0.141421),
                (-0.184776, 0.5, -0.0765367),
                (-0.2, 0.5, 0),
                (-0.184776, 0.5, 0.0765367),
                (-0.141421, 0.5, 0.141421),
                (-0.0765367, 0.5, 0.184776),
                (0, 0.5, 0.2),
                (0.0765367, 0.5, 0.184776),
                (0.141421, 0.5, 0.141421),
                (0.184776, 0.5, 0.0765367),
                (0.200004, 0.5, 0),
                (0.15, 0.5, 0),
                (0.2, 0.5, -0.1),
                (0.25, 0.5, 0),
                (0.200004, 0.5, 0),
            ),
            k=tuple(range(17)),
            n=name
        )
        return arrow_circle


class TargetControl(ControlCurves):
    def get_curve(self, name):
        target = pmc.curve(
            degree=1,
            p=[
                (0, 0, 0.325), (-0.0634045, 0, 0.318755), (-0.124372, 0, 0.300261), (-0.180561, 0, 0.270228),
                (-0.22981, 0, 0.22981), (-0.270228, 0, 0.180561), (-0.300261, 0, 0.124372), (-0.318755, 0, 0.0634045),
                (-0.325, 0, 0), (-0.318755, 0, -0.0634045), (-0.300261, 0, -0.124372), (-0.270228, 0, -0.180561),
                (-0.22981, 0, -0.22981), (-0.180561, 0, -0.270228), (-0.124372, 0, -0.300261),
                (-0.0634045, 0, -0.318755),
                (0, 0, -0.325), (0.0634045, 0, -0.318755), (0.124372, 0, -0.300261), (0.180561, 0, -0.270228),
                (0.22981, 0, -0.22981), (0.270228, 0, -0.180561), (0.300261, 0, -0.124372), (0.318755, 0, -0.0634045),
                (0.325, 0, 0), (0.318755, 0, 0.0634045), (0.300261, 0, 0.124372), (0.270228, 0, 0.180561),
                (0.22981, 0, 0.22981), (0.180561, 0, 0.270228), (0.124372, 0, 0.300261), (0.0634045, 0, 0.318755),
                (0, 0, 0.325), (0, 0, -0.325), (0, 0, -0.25), (-0.0487726, 0, -0.245197), (-0.095671, 0, -0.23097),
                (-0.138893, 0, -0.207868), (-0.176777, 0, -0.176777), (-0.207868, 0, -0.138893),
                (-0.23097, 0, -0.095671),
                (-0.245197, 0, -0.0487726), (-0.25, 0, 0), (-0.325, 0, 0), (0.325, 0, 0), (-0.25, 0, 0),
                (-0.245197, 0, 0.0487726), (-0.23097, 0, 0.095671), (-0.207868, 0, 0.138893), (-0.176777, 0, 0.176777),
                (-0.138893, 0, 0.207868), (-0.095671, 0, 0.23097), (-0.0487726, 0, 0.245197), (0, 0, 0.25),
                (0.0487726, 0, 0.245197), (0.095671, 0, 0.23097), (0.138893, 0, 0.207868), (0.176777, 0, 0.176777),
                (0.207868, 0, 0.138893), (0.23097, 0, 0.095671), (0.245197, 0, 0.0487726), (0.25, 0, 0),
                (0.245197, 0, -0.0487726), (0.23097, 0, -0.095671), (0.207868, 0, -0.138893), (0.176777, 0, -0.176777),
                (0.138893, 0, -0.207868), (0.095671, 0, -0.23097), (0.0487726, 0, -0.245197), (0, 0, -0.25),
            ],
            k=tuple(range(70)),
            n=name

        )
        return target


class RoundSquare(ControlCurves):
    def get_curve(self, name):
        curve = pmc.curve(
            degree=3,
            p=[
                (0, 0, 0.5),
                (-0.375, 0, 0.5),
                (-0.5, 0, 0.5),
                (-0.5, 0, 0.375),
                (-0.5, 0, -0.375),
                (-0.5, 0, -0.5),
                (-0.375, 0, -0.5),
                (0.375, 0, -0.5),
                (0.5, 0, -0.5),
                (0.5, 0, -0.375),
                (0.5, 0, 0.375),
                (0.5, 0, 0.5),
                (0.375, 0, 0.5),
                (0, 0, 0.5),
            ],
            k=[
                0, 0, 0,
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11,
                11, 11
            ],
            n=name
        )

        return curve


class RoundSquarePointControl(ControlCurves):
    def get_curve(self, name):
        ctrl_curve = pmc.curve(
            degree=3,
            p=[
                (0, 0, 0.5),
                (0.125, 0, 0.375),
                (0.125, 0, 0.375),
                (0.125, 0, 0.375),
                (0.25, 0, 0.375),
                (0.375, 0, 0.375),
                (0.375, 0, 0.25),
                (0.375, 0, -0.25),
                (0.375, 0, -0.375),
                (0.25, 0, -0.375),
                (-0.25, 0, -0.375),
                (-0.375, 0, -0.375),
                (-0.375, 0, -0.25),
                (-0.375, 0, 0.25),
                (-0.375, 0, 0.375),
                (-0.25, 0, 0.375),
                (-0.125, 0, 0.375),
                (-0.125, 0, 0.375),
                (-0.125, 0, 0.375),
                (0, 0, 0.5),
            ],
            k=[
                0, 0, 0,
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16,
                17, 17, 17
            ],
            n=name
        )
        return ctrl_curve


def linear_curve(
    name="M_linear_0_CRV",
    position=(),
    knots=(),
    driver_nodes=None,
    template=True,
):
    """
    Create a linear curve. If driverNodes specified
    it will create cvs in the range of the number
    of the nodes. And direct connect the nodes with the cvs.
    Args:
            name(str): The curves name.
            position(tuple): The worldspace position for each cv.
            knots(tuple): The amount of the knots(cvs).
            driver_nodes(list): Driver nodes for the curve cvs.
            The amount of the dirveNodes in the list
            specifie the amount of the curve cvs.
            template(bool): Enable the template model
            display type.
    Return:
            list: The new created curve.
    """
    data = {}
    data["degree"] = 1
    data["n"] = name
    if driver_nodes is None:
        data["p"] = position
        data["k"] = knots
    else:
        data["p"] = []
        data["k"] = []
        for x in range(len(driver_nodes)):
            data["p"].append((0, 0, 0))
            data["k"].append(x)
        data["p"] = tuple(data["p"])
        data["k"] = tuple(data["k"])
    result = pmc.curve(**data)
    attributes_utils.lock_and_hide_attributes(result)
    for y in range(len(driver_nodes)):
        decomp = pmc.createNode("decomposeMatrix")
        driver_nodes[y].worldMatrix[0].connect(decomp.inputMatrix)
        decomp.outputTranslate.connect(result.controlPoints[y])
    if template:
        result.overrideEnabled.set(1)
        result.overrideDisplayType.set(1)
    return result


class HostControl(ControlCurves):
    """
    Create a HOST Control Curve.
    """

    def get_curve(self, name):
        curve_trs = pmc.createNode("transform", name=name)
        curves = [
            self.h_curve(name),
            self.o_curve(name),
            self.o_curve(name),
            self.s_curve(name),
            self.t_curve(name),
            self.o_inner_curve(name),
        ]
        for crv in curves:
            shape = crv.getShape()
            pmc.parent(shape, curve_trs, s=True, r=True)
        pmc.delete(curves)
        return curve_trs

    def h_curve(self, name):
        pos = []
        pos.append((-17.0383954579, 8.65387986882, -0.000361074846968))
        pos.append((-21.539690555, 8.65387986882, -0.000361074846968))
        pos.append((-21.539690555, -8.65586309292, -0.000361074846968))
        pos.append((-17.0383954579, -8.65586309292, -0.000361074846968))
        pos.append((-17.0383954579, -1.38551652979, -0.000361074846968))
        pos.append((-15.6913138847, -1.38551652979, -0.000361074846968))
        pos.append((-15.6913138847, -8.65586309292, -0.000361074846968))
        pos.append((-11.1900187876, -8.65586309292, -0.000361074846968))
        pos.append((-11.1900187876, 8.65387986882, -0.000361074846968))
        pos.append((-15.6913138847, 8.65387986882, -0.000361074846968))
        pos.append((-15.6913138847, 2.4634773344, -0.000361074846968))
        pos.append((-17.0383954579, 2.4634773344, -0.000361074846968))
        pos.append(pos[0])
        new = pmc.curve(d=1, p=pos, n=name)
        return new

    def o_curve(self, name):
        pos = []
        pos.append((-4.89361362506, 9.01736458721, -0.000361074846968))
        pos.append((-5.6032852133, 8.98736686663, -0.000361074846968))
        pos.append((-6.26741074617, 8.89715195851, -0.000361074846968))
        pos.append((-6.88621033956, 8.74672312381, -0.000361074846968))
        pos.append((-7.45946387759, 8.53629558698, -0.000361074846968))
        pos.append((-7.98169944208, 8.26959501338, -0.000361074846968))
        pos.append((-8.44722173802, 7.95099763315, -0.000361074846968))
        pos.append((-8.85581391048, 7.58006810596, -0.000361074846968))
        pos.append((-9.20769281438, 7.15702491723, -0.000361074846968))
        pos.append((-9.49826128844, 6.69632071371, -0.000361074846968))
        pos.append((-9.72357844286, 6.21218313481, -0.000361074846968))
        pos.append((-9.88320486109, 5.70461870249, -0.000361074846968))
        pos.append((-9.97736065902, 5.17384590216, -0.000361074846968))
        pos.append((-10.0312262801, 4.53599568547, -0.000361074846968))
        pos.append((-10.0695451968, 3.70764494261, -0.000361074846968))
        pos.append((-10.0927560106, 2.68901215898, -0.000361074846968))
        pos.append((-10.1004193048, 1.47987884918, -0.000361074846968))
        pos.append((-10.1004193048, -1.48186207328, -0.000361074846968))
        pos.append((-10.0923174092, -2.71814749426, -0.000361074846968))
        pos.append((-10.0682318386, -3.75385882579, -0.000361074846968))
        pos.append((-10.0281609624, -4.58921659138, -0.000361074846968))
        pos.append((-9.97210478054, -5.22400067514, -0.000361074846968))
        pos.append((-9.87378960739, -5.74842516995, -0.000361074846968))
        pos.append((-9.70737465184, -6.25292408077, -0.000361074846968))
        pos.append((-9.47286154438, -6.73749720381, -0.000361074846968))
        pos.append((-9.170250285, -7.2019252384, -0.000361074846968))
        pos.append((-8.8063269653, -7.62781515751, -0.000361074846968))
        pos.append((-8.38832035439, -7.99699277615, -0.000361074846968))
        pos.append((-7.91622882179, -8.30945801791, -0.000361074846968))
        pos.append((-7.39005236749, -8.56499197702, -0.000361074846968))
        pos.append((-6.81898694453, -8.76359462799, -0.000361074846968))
        pos.append((-6.21266873776, -8.90570390975, -0.000361074846968))
        pos.append((-5.57087763127, -8.99088190886, -0.000361074846968))
        pos.append((-4.89361362506, -9.01934755655, -0.000361074846968))
        pos.append((-4.18394366732, -8.98913017865, -0.000361074846968))
        pos.append((-3.51959964904, -8.89891595839, -0.000361074846968))
        pos.append((-2.90080005564, -8.7487049085, -0.000361074846968))
        pos.append((-2.32754488713, -8.53827805953, -0.000361074846968))
        pos.append((-1.80530932264, -8.27179578026, -0.000361074846968))
        pos.append((-1.3397870267, -7.95298050058, -0.000361074846968))
        pos.append((-0.931194841502, -7.58205112625, -0.000361074846968))
        pos.append((-0.579315937604, -7.15922672864, -0.000361074846968))
        pos.append((-0.288748291524, -6.69830210351, -0.000361074846968))
        pos.append((-0.063431137104, -6.21416697035, -0.000361074846968))
        pos.append((0.0961952811236, -5.70682163487, -0.000361074846968))
        pos.append((0.190351079056, -5.17582790339, -0.000361074846968))
        pos.append((0.244217515344, -4.53797809433, -0.000361074846968))
        pos.append((0.282535616842, -3.70962775909, -0.000361074846968))
        pos.append((0.305745615345, -2.69099538309, -0.000361074846968))
        pos.append((0.313410540035, -1.48186207328, -0.000361074846968))
        pos.append((0.313410540035, 1.47987884918, -0.000361074846968))
        pos.append((0.305308644527, 2.71594537713, -0.000361074846968))
        pos.append((0.281221443411, 3.75187600931, -0.000361074846968))
        pos.append((0.241152197663, 4.58701528949, -0.000361074846968))
        pos.append((0.185096015819, 5.221798558, -0.000361074846968))
        pos.append((0.0867792121839, 5.74644235346, -0.000361074846968))
        pos.append((-0.0796349281209, 6.2509414681, -0.000361074846968))
        pos.append((-0.314148035583, 6.73551438733, -0.000361074846968))
        pos.append((-0.616758466977, 7.19994262573, -0.000361074846968))
        pos.append((-0.980681799416, 7.62583264674, -0.000361074846968))
        pos.append((-1.39868841032, 7.99501102968, -0.000361074846968))
        pos.append((-1.87077994293, 8.30747451357, -0.000361074846968))
        pos.append((-2.39695802772, 8.56300787398, -0.000361074846968))
        pos.append((-2.96802182019, 8.76183122681, -0.000361074846968))
        pos.append((-3.57434165745, 8.90393968058, -0.000361074846968))
        pos.append((-4.21635124935, 8.98911801088, -0.000361074846968))
        pos.append(pos[0])
        new = pmc.curve(d=1, p=pos, name=name)
        return new

    def s_curve(self, name):
        pos = []
        pos.append((5.95475458331, 9.01736458722, -0.000361074846968))
        pos.append((5.18224235213, 8.98495700518, -0.000361074846968))
        pos.append((4.46841138867, 8.88773588957, -0.000361074846968))
        pos.append((3.81370192475, 8.72570124038, -0.000361074846968))
        pos.append((3.21767372855, 8.49885142711, -0.000361074846968))
        pos.append((2.68996461541, 8.21463451956, -0.000361074846968))
        pos.append((2.24064611048, 7.88005346421, -0.000361074846968))
        pos.append((1.8694964674, 7.49554686238, -0.000361074846968))
        pos.append((1.57630046172, 7.06089785915, -0.000361074846968))
        pos.append((1.35426874088, 6.53428443403, -0.000361074846968))
        pos.append((1.19551789478, 5.87409979096, -0.000361074846968))
        pos.append((1.10026803931, 5.08012707504, -0.000361074846968))
        pos.append((1.06851754399, 4.15280407232, -0.000361074846968))
        pos.append((1.09085197037, 3.49393360269, -0.000361074846968))
        pos.append((1.1580753654, 2.89637437814, -0.000361074846968))
        pos.append((1.2699659827, 2.36056255424, -0.000361074846968))
        pos.append((1.42674719915, 1.88606197543, -0.000361074846968))
        pos.append((1.61746702598, 1.46652189043, -0.000361074846968))
        pos.append((1.83161533672, 1.09493609178, -0.000361074846968))
        pos.append((2.06919539235, 0.771522249618, -0.000361074846968))
        pos.append((2.33020230141, 0.496062693795, -0.000361074846968))
        pos.append((2.67354233898, 0.206808393165, -0.000361074846968))
        pos.append((3.15877234492, -0.158646770132, -0.000361074846968))
        pos.append((3.78567383382, -0.600522096748, -0.000361074846968))
        pos.append((4.55402832028, -1.11837817013, -0.000361074846968))
        pos.append((5.31515322237, -1.6294457062, -0.000361074846968))
        pos.append((5.9199404008, -2.06190414863, -0.000361074846968))
        pos.append((6.36838333359, -2.41531652661, -0.000361074846968))
        pos.append((6.66026679633, -2.68990051031, -0.000361074846968))
        pos.append((6.84266624224, -2.99141730453, -0.000361074846968))
        pos.append((6.9729520266, -3.42497102736, -0.000361074846968))
        pos.append((7.05112088844, -3.99099987249, -0.000361074846968))
        pos.append((7.0771793497, -4.68928372402, -0.000361074846968))
        pos.append((7.06360390555, -5.01554439845, -0.000361074846968))
        pos.append((7.02243734129, -5.29866806372, -0.000361074846968))
        pos.append((6.95390140332, -5.53931221416, -0.000361074846968))
        pos.append((6.85821131605, -5.73703906372, -0.000361074846968))
        pos.append((6.73405616705, -5.89141041872, -0.000361074846968))
        pos.append((6.58143921729, -6.00176960004, -0.000361074846968))
        pos.append((6.4001354594, -6.06789751086, -0.000361074846968))
        pos.append((6.18992640797, -6.09001304421, -0.000361074846968))
        pos.append((5.98234570341, -6.07249589501, -0.000361074846968))
        pos.append((5.80892372513, -6.02038182584, -0.000361074846968))
        pos.append((5.66966047313, -5.93367104051, -0.000361074846968))
        pos.append((5.56433746201, -5.81192554915, -0.000361074846968))
        pos.append((5.48726102722, -5.62952630705, -0.000361074846968))
        pos.append((5.43208204799, -5.3601975904, -0.000361074846968))
        pos.append((5.39901900973, -5.00415829223, -0.000361074846968))
        pos.append((5.38807191244, -4.56097001505, -0.000361074846968))
        pos.append((5.38807191244, -2.45473031613, -0.000361074846968))
        pos.append((1.20756068009, -2.45473031613, -0.000361074846968))
        pos.append((1.20756068009, -3.58810136458, -0.000361074846968))
        pos.append((1.23230496792, -4.50557132754, -0.000361074846968))
        pos.append((1.30653457044, -5.31224391549, -0.000361074846968))
        pos.append((1.43003100224, -6.00768154618, -0.000361074846968))
        pos.append((1.60301437921, -6.59254130633, -0.000361074846968))
        pos.append((1.85613950866, -7.09835398296, -0.000361074846968))
        pos.append((2.21918725623, -7.55730795938, -0.000361074846968))
        pos.append((2.69259296227, -7.96962197576, -0.000361074846968))
        pos.append((3.27635662677, -8.33529605756, -0.000361074846968))
        pos.append((3.94836393924, -8.6346233387, -0.000361074846968))
        pos.append((4.6862837343, -8.84811571871, -0.000361074846968))
        pos.append((5.49054809129, -8.97643012829, -0.000361074846968))
        pos.append((6.3609385248, -9.01934755655, -0.000361074846968))
        pos.append((7.15885376102, -8.98212325783, -0.000361074846968))
        pos.append((7.90596624814, -8.87088824961, -0.000361074846968))
        pos.append((8.60227924714, -8.68542357518, -0.000361074846968))
        pos.append((9.24779275803, -8.42616718621, -0.000361074846968))
        pos.append((9.81732552214, -8.11173124478, -0.000361074846968))
        pos.append((10.2861332517, -7.76182263293, -0.000361074846968))
        pos.append((10.6539974612, -7.37666047296, -0.000361074846968))
        pos.append((10.9209181507, -6.956025719, -0.000361074846968))
        pos.append((11.1103221736, -6.45678217713, -0.000361074846968))
        pos.append((11.2456461663, -5.83601193502, -0.000361074846968))
        pos.append((11.3268803458, -5.0937152984, -0.000361074846968))
        pos.append((11.3540344951, -4.22967317041, -0.000361074846968))
        pos.append((11.3052046366, -3.04484513951, -0.000361074846968))
        pos.append((11.1589335466, -2.03519063876, -0.000361074846968))
        pos.append((10.9150060007, -1.20049036751, -0.000361074846968))
        pos.append((10.5734187379, -0.540962811161, -0.000361074846968))
        pos.append((10.0441753354, 0.0710490601557, -0.000361074846968))
        pos.append((9.23662717533, 0.762983383291, -0.000361074846968))
        pos.append((8.15121122846, 1.53505864365, -0.000361074846968))
        pos.append((6.78748726301, 2.38683950092, -0.000361074846968))
        pos.append((6.31495549861, 2.68550905524, -0.000361074846968))
        pos.append((5.94534014486, 2.96140721237, -0.000361074846968))
        pos.append((5.67885642618, 3.21453234182, -0.000361074846968))
        pos.append((5.51550760355, 3.44532304488, -0.000361074846968))
        pos.append((5.41281293929, 3.69122266619, -0.000361074846968))
        pos.append((5.3396790248, 3.99076942313, -0.000361074846968))
        pos.append((5.29566562827, 4.34396168521, -0.000361074846968))
        pos.append((5.28099449609, 4.75036329687, -0.000361074846968))
        pos.append((5.29413296943, 5.06611302958, -0.000361074846968))
        pos.append((5.33311141862, 5.33894586903, -0.000361074846968))
        pos.append((5.39836029253, 5.56907948538, -0.000361074846968))
        pos.append((5.48967088868, 5.75629539322, -0.000361074846968))
        pos.append((5.60616274347, 5.90125230976, -0.000361074846968))
        pos.append((5.74739562513, 6.00504103155, -0.000361074846968))
        pos.append((5.91359128002, 6.06722947925, -0.000361074846968))
        pos.append((6.10430947637, 6.08781113089, -0.000361074846968))
        pos.append((6.27816842546, 6.072482912, -0.000361074846968))
        pos.append((6.42509497166, 6.02649988581, -0.000361074846968))
        pos.append((6.54530760037, 5.94964356691, -0.000361074846968))
        pos.append((6.639024797, 5.84191232483, -0.000361074846968))
        pos.append((6.70909665479, 5.67834501679, -0.000361074846968))
        pos.append((6.7592374257, 5.43310166696, -0.000361074846968))
        pos.append((6.78923840726, 5.10618390582, -0.000361074846968))
        pos.append((6.79930830194, 4.69803114991, -0.000361074846968))
        pos.append((6.79930830194, 3.41488672299, -0.000361074846968))
        pos.append((10.9798179038, 3.41488672299, -0.000361074846968))
        pos.append((10.9798179038, 4.09915775193, -0.000361074846968))
        pos.append((10.9546366451, 5.05582138852, -0.000361074846968))
        pos.append((10.879533101, 5.86205700565, -0.000361074846968))
        pos.append((10.7542855249, 6.5178621576, -0.000361074846968))
        pos.append((10.578890656, 7.02345532977, -0.000361074846968))
        pos.append((10.3262041279, 7.43533293581, -0.000361074846968))
        pos.append((9.96928701568, 7.81064032362, -0.000361074846968))
        pos.append((9.50836432675, 8.14916226877, -0.000361074846968))
        pos.append((8.94299256834, 8.45089714078, -0.000361074846968))
        pos.append((8.29309956634, 8.69876883748, -0.000361074846968))
        pos.append((7.57839140028, 8.87569310425, -0.000361074846968))
        pos.append((6.79887133112, 8.98211017291, -0.000361074846968))
        pos.append(pos[0])
        new = pmc.curve(d=1, p=pos, name=name)
        return new

    def t_curve(self, name):
        pos = []
        pos.append((21.540169765, 8.65387986882, -0.000361074846968))
        pos.append((11.7037503877, 8.65387986882, -0.000361074846968))
        pos.append((11.7037503877, 5.18982957728, -0.000361074846968))
        pos.append((14.3661654844, 5.18982957728, -0.000361074846968))
        pos.append((14.3661654844, -8.65586309292, -0.000361074846968))
        pos.append((18.8672420961, -8.65586309292, -0.000361074846968))
        pos.append((18.8672420961, 5.18982957728, -0.000361074846968))
        pos.append((21.540169765, 5.18982957728, -0.000361074846968))
        pos.append(pos[0])
        new = pmc.curve(d=1, p=pos, name=name)
        return new

    def o_inner_curve(self, name):
        pos = []
        pos.append((-4.87226238303, 6.05736665656, -0.000361074846968))
        pos.append((-4.68249639175, 6.03645075485, -0.000361074846968))
        pos.append((-4.52780709158, 5.97370468022, -0.000361074846968))
        pos.append((-4.40841296791, 5.86890831676, -0.000361074846968))
        pos.append((-4.32431402075, 5.72228014989, -0.000361074846968))
        pos.append((-4.2661430958, 5.50070333524, -0.000361074846968))
        pos.append((-4.22474663272, 5.17041209416, -0.000361074846968))
        pos.append((-4.19969255214, 4.73205373043, -0.000361074846968))
        pos.append((-4.19141293343, 4.18519534947, -0.000361074846968))
        pos.append((-4.19141293343, -3.72964852282, -0.000361074846968))
        pos.append((-4.19947406674, -4.42051976769, -0.000361074846968))
        pos.append((-4.22322212632, -4.97173522056, -0.000361074846968))
        pos.append((-4.26331093793, -5.3832946776, -0.000361074846968))
        pos.append((-4.31908504532, -5.65519875025, -0.000361074846968))
        pos.append((-4.40340247789, -5.83211038074, -0.000361074846968))
        pos.append((-4.52911474305, -5.95847606402, -0.000361074846968))
        pos.append((-4.6960033554, -6.03429539247, -0.000361074846968))
        pos.append((-4.90407157592, -6.05956856988, -0.000361074846968))
        pos.append((-5.10734616133, -6.03756350211, -0.000361074846968))
        pos.append((-5.26987810941, -5.97176637657, -0.000361074846968))
        pos.append((-5.39188590554, -5.86195891166, -0.000361074846968))
        pos.append((-5.47336954974, -5.70835918517, -0.000361074846968))
        pos.append((-5.52674847008, -5.46107487183, -0.000361074846968))
        pos.append((-5.56509428988, -5.0702130349, -0.000361074846968))
        pos.append((-5.58797003831, -4.53555600422, -0.000361074846968))
        pos.append((-5.59559583129, -3.85732144996, -0.000361074846968))
        pos.append((-5.59559583129, 4.18519534947, -0.000361074846968))
        pos.append((-5.58404871437, 4.78390651388, -0.000361074846968))
        pos.append((-5.54918887819, 5.25036960147, -0.000361074846968))
        pos.append((-5.49101795324, 5.58436694207, -0.000361074846968))
        pos.append((-5.40953430904, 5.78611702108, -0.000361074846968))
        pos.append((-5.30604396658, 5.90485731901, -0.000361074846968))
        pos.append((-5.18207632371, 5.98960846142, -0.000361074846968))
        pos.append((-5.03740963406, 6.04059056421, -0.000361074846968))
        pos.append((-4.87226238303, 6.05736665656, -0.000361074846968))
        pos.append(pos[0])
        new = pmc.curve(d=1, p=pos, name=name)
        return new


def cubic_curve(
    name="M_cubic_0_CRV", position=(), driver_nodes=None, template=True
):
    """
    Create a cubic curve. If driverNodes specified
    it will create cvs in the range of the number
    of the nodes. And direct connect the nodes with the cvs.
    Args:
            name(str): The curves name.
            position(tuple): The worldspace position for each cv.
            driver_nodes(list): Driver nodes for the curve cvs.
            The amount of the dirveNodes in the list
            specifie the amount of the curve cvs.
            template(bool): Enable the template model
            display type.
    Return:
            list: The new created curve.
    """
    data = {}
    data["n"] = name
    if driver_nodes is None:
        data["p"] = position
    else:
        data["p"] = []
        for x in range(len(driver_nodes)):
            data["p"].append((0, 0, 0))
        data["p"] = tuple(data["p"])
    result = pmc.curve(**data)
    attributes_utils.lock_and_hide_attributes(result)
    for y in range(len(driver_nodes)):
        decomp = pmc.createNode("decomposeMatrix")
        driver_nodes[y].worldMatrix[0].connect(decomp.inputMatrix)
        decomp.outputTranslate.connect(result.controlPoints[y])
    if template:
        result.overrideEnabled.set(1)
        result.overrideDisplayType.set(1)
    return result


# def mirror_curve(
#     curve=None, search="L_", replace="R_", buffer_grp=True, color_index=6
# ):
#     """
#     Mirror a curve from + X to - X. By default it search about 'L_' in
#     the name and replace it with 'R_'. It also creates a bufferGRP for
#     the duplicated curve. The mirrored curve will be BRIGHTBLUE.
#     Args:
#             curve(dagnode): The mirror curve.
#             search(str): The string to search for.
#             replace(str): The string to replace with.
#             buffer_grp(bool): Enable a buffer group for the
#             duplicated curve.
#             color_index(int): The color for the duplicated
#             curve.
#     Return:
#             list: The created curve and the buffer group.
#     """
#     result = []
#     if curve.getShape().nodeType() == "nurbsCurve":
#         dupl_curve = pmc.duplicate(curve, rr=True)[0]
#         children = utils.descendants(dupl_curve)
#         for node in children:
#             pmc.rename(node, name)
#         mirror_grp = pmc.createNode("transform", n="M_temp_mirror_0_GRP")
#         mirror_grp.addChild(dupl_curve)
#         mirror_grp.scaleX.set(-1)
#         pmc.makeIdentity(mirror_grp, a=True)
#         pmc.parent(dupl_curve, w=True)
#         pmc.delete(mirror_grp)
#         if buffer_grp:
#             buffer_ = rig_utils.create_buffer_groups(dupl_curve)[0]
#             result.append(buffer_)
#         for shape in dupl_curve.getShapes():
#             shape.overrideColor.set(color_index)
#         result.append(dupl_curve)
#     else:
#         _LOGGER.warning("Mirror only for nurbsCurves")
#     return result
