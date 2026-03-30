"""
Custom script to add extra joints on any joint chain and use them as interpolation
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import built-in modules
from builtins import range
import logging
from importlib import reload
from pprint import pprint

# Import third-party modules
from future import standard_library
import pymel.core as pmc

from pxo_rigging_kit import constants
# Import local modules
from pxo_rigging_kit.maya_utils.exceptions import MayaNodeNotFound
from pxo_rigging_kit.maya_utils.rigging import rig_utils
from pxo_rigging_kit.maya_utils import decorators
reload(rig_utils)

#######################################################
# GLOBALS
#######################################################

logging.basicConfig(level=logging)
_LOGGER = logging.getLogger(__name__ + ".py")
standard_library.install_aliases()
DECORATORS = decorators.Decorators()

#######################################################
# CLASSES
#######################################################


class InterpolationSetup(object):
    JNT_NUM = 15
    PROJECTION_DIRECTION = "Y"
    GLOBAL_CTRL = "global_0_*_ctrl"
    LOCAL_JNT = "*_bnd_local_*_jnt"

    def __init__(self):
        self.name = "pxo_interpolationJoints_setup"
        self.component_name = None
        self.new_joint_bnd_list = []
        self.tail_joint_list = []
        self.joint_pos_list = []
        self.numb_of_jnt = []
        self.deformer_set = None

    def create(self):
        """
        Creates the setup.
        """
        global_con = pmc.ls(self.GLOBAL_CTRL)[0]
        par_factor = 1 / float(self.JNT_NUM - 1)
        self._add_extra_jnt(self.tail_joint_list)
        curve_on_jnt, tail_loft_sur, tail_curve_grp = self._curve_setup(
            self.component_name, self.tail_joint_list
        )

        new_joints = self._create_joint_setup(
            self.component_name,
            self.JNT_NUM,
            par_factor,
            curve_on_jnt,
            tail_loft_sur,
        )

        self._cleanup_and_scale(
            self.component_name, tail_curve_grp, new_joints, global_con
        )

    def _curve_setup(self, comp_str, tail_joint_list):
        """
        Create four curves. Two of them will be skinned to the current joints and the
        other two will be wired deformed with the first two.
        The two high definition curves will be used for the loft
        The two low def will be used to follow 1:1 the current joints with a skin cluster

        Args:
            comp_str(str): The component name.
            tail_joint_list(list): The existing tail system joints.

        Returns:
            Tuple: curve_on_jnt, tail_loft_sur, tail_curve_grp

        """
        # create a list of the position of the current tail joints
        joint_pos_list = list()
        for jnt in tail_joint_list:
            translate = pmc.xform(jnt, q=1, ws=1, rp=1)
            joint_pos_list.append(translate)

        # build two curves: one is for the position of the new joints and the other is for the aiming system
        low_res_curve_on_jnt = pmc.curve(
            name="{0}_lowRes_bend_crv".format(comp_str),
            p=joint_pos_list,
            degree=1,
        )
        low_res_curve_target = pmc.curve(
            name="{0}_lowRes_target_bend_crv".format(comp_str),
            p=joint_pos_list,
            degree=1,
        )
        low_res_curve_target.attr(
            "translate{0}".format(self.PROJECTION_DIRECTION)
        ).set(10)
        pmc.makeIdentity(low_res_curve_target, apply=True, t=1, r=1, s=1, n=0)
        pmc.delete(low_res_curve_target, constructionHistory=True)

        curve_on_jnt = pmc.curve(
            name="{0}_highRes_bend_crv".format(comp_str),
            p=joint_pos_list,
            degree=3,
        )
        curve_target = pmc.curve(
            name="{0}_highRes_bend_target_crv".format(comp_str),
            p=joint_pos_list,
            degree=3,
        )
        tail_curve_grp = pmc.group(
            curve_on_jnt,
            curve_target,
            low_res_curve_on_jnt,
            low_res_curve_target,
            name="{0}_curve_grp".format(comp_str),
        )
        curve_target.attr("translate{0}".format(self.PROJECTION_DIRECTION)).set(
            10
        )
        pmc.makeIdentity(curve_target, apply=True, t=1, r=1, s=1, n=0)
        pmc.delete(curve_target, constructionHistory=True)
        sk_on_jnt = pmc.skinCluster(
            tail_joint_list, low_res_curve_on_jnt, maximumInfluences=1
        )

        sk_target = pmc.skinCluster(
            tail_joint_list,
            low_res_curve_target,
            toSelectedBones=True,
            maximumInfluences=1,
        )

        pmc.rebuildCurve(
            curve_on_jnt,
            ch=1,
            rpo=1,
            rt=0,
            end=1,
            kr=0,
            kcp=0,
            kep=1,
            kt=0,
            s=(len(tail_joint_list) - 1),
            d=3,
            tol=0.01,
        )
        pmc.rebuildCurve(
            curve_target,
            ch=1,
            rpo=1,
            rt=0,
            end=1,
            kr=0,
            kcp=0,
            kep=1,
            kt=0,
            s=(len(tail_joint_list) - 1),
            d=3,
            tol=0.01,
        )

        for jnt in tail_joint_list:
            pmc.skinPercent(
                sk_on_jnt,
                low_res_curve_on_jnt.cv[tail_joint_list.index(jnt)],
                tv=(jnt, 1),
            )
            pmc.skinPercent(
                sk_target,
                low_res_curve_target.cv[tail_joint_list.index(jnt)],
                tv=(jnt, 1),
            )

        wire_curve_jnt = pmc.wire(
            curve_on_jnt,
            w=low_res_curve_on_jnt,
            name="{0}_jointWire_crv".format(comp_str),
            gw=False,
            en=1.000000,
            ce=0.000000,
            li=0.000000,
        )[0]
        wire_curve_jnt.attr("dropoffDistance[0]").set(100000)

        wire_target_curve_jnt = pmc.wire(
            curve_target,
            w=low_res_curve_target,
            name="{0}_jointTargetWire_crv".format(comp_str),
            gw=False,
            en=1.000000,
            ce=0.000000,
            li=0.000000,
        )[0]
        wire_target_curve_jnt.attr("dropoffDistance[0]").set(100000)

        tail_loft_sur = pmc.loft(
            curve_on_jnt,
            curve_target,
            name="{0}_jointRibbon_nrb".format(comp_str),
            ch=1,
            u=1,
            c=0,
            ar=1,
            d=3,
            ss=1,
            rn=0,
            po=0,
            rsn=True,
        )[0]
        pmc.parent(tail_loft_sur, tail_curve_grp)

        return curve_on_jnt, tail_loft_sur, tail_curve_grp

    @DECORATORS.requires_plugins(["maya-math-nodes"])
    def _create_joint_setup(
        self,
        comp_str,
        numb_of_jnt,
        par_factor,
        curve_on_jnt,
        tail_loft_sur,
    ):
        """
        Creates the actually new interpolated bind joints and connect it on the ribbon nurbs surface.

        Args:
            comp_str(str): The component name.
            numb_of_jnt(int): The number of joints for the creation.
            par_factor(int): The interpolation factor.
            curve_on_jnt(pmc.PyNode): The driver nurbs curve.
            tail_loft_sur(pmc.PyNode): The driver nurbs surface.

        Returns:
            List: The newly created bind joints.

        """
        new_joint_bnd_list = list()
        try:
            local_jnt = pmc.ls(self.LOCAL_JNT)[0]
        except:
            raise MayaNodeNotFound(f"{self.LOCAL_JNT} not existing")
        for new_bnd_jnt in range(0, numb_of_jnt):
            # find parameter and delete node
            par = par_factor * new_bnd_jnt

            main_point_on_curve = pmc.createNode(
                "pointOnCurveInfo",
                name="{0}_main_point_on_curve_{1}_poc".format(
                    comp_str, new_bnd_jnt
                ),
            )

            curve_on_jnt.worldSpace.connect(main_point_on_curve.inputCurve)
            main_point_on_curve.parameter.set(par)
            main_point_on_curve.turnOnPercentage.set(1)

            closest = pmc.createNode("closestPointOnSurface")

            tail_loft_sur.getShape().worldSpace.connect(closest.inputSurface)

            pos = main_point_on_curve.position.get()

            # print main_point_on_curve.positionX
            closest.inPositionX.set(pos[0], l=True)
            closest.inPositionY.set(pos[1], l=True)
            closest.inPositionZ.set(pos[2], l=True)

            u_param = pmc.getAttr("{0}.result.parameterU".format(closest))
            v_param = pmc.getAttr("{0}.result.parameterV".format(closest))

            pmc.delete(main_point_on_curve, closest)

            transform_on_nurbs = rig_utils.create_transform_on_nurbs_surface(
                tail_loft_sur, v_param, u_param, decompose_name="translateAndRotateOnly", reuse_uv_pin=True
            )

            bnd_jnt = pmc.joint(
                name="C_bnd_interpolate{0}_0_{1}_jnt".format(
                    comp_str.capitalize(),
                    new_bnd_jnt,
                )
            )
            for connection_ in transform_on_nurbs.decompose_matrix_connections[:-3]:
                transform_on_nurbs.decompose_matrix.attr(connection_[0]).connect(bnd_jnt.attr(connection_[1]))
                mult_matrix_nd = pmc.createNode("math_MultiplyMatrix")
                transform_on_nurbs.world_matrix_attr.connect(mult_matrix_nd.input1)
                local_jnt.worldInverseMatrix.connect(mult_matrix_nd.input2)
                mult_matrix_nd.output.connect(transform_on_nurbs.decompose_matrix.inputMatrix, force=True)

            new_joint_bnd_list.append(bnd_jnt)

            if self.deformer_set:
                pmc.sets(self.deformer_set,
                         addElement=[bnd_jnt]
                         )

            pmc.parent(bnd_jnt, local_jnt)
            # bnd_jnt.inheritsTransform.set(False, lock=True)

        return new_joint_bnd_list

    @staticmethod
    def _cleanup_and_scale(comp_str, tail_curve_grp, new_joint_bnd_list, global_con):
        """
        Cleans some groups and connect the main scale to the new system.

        Args:
            comp_str(str): The component string.
            tail_curve_grp(pmc.PyNode): The tail curve group.
            new_joint_bnd_list(list): List filled with the newly created bind joints.
            global_con(pmc.PyNode): The global control.

        """
        # cleanup with main group
        tail_setup_nde = pmc.group(
            name="interpolate{0}_setup_grp".format(comp_str.capitalize()), em=True
        )
        tail_setup_nde.visibility.set(0)
        pmc.parent(tail_curve_grp, tail_setup_nde)
        for jnt in new_joint_bnd_list:
            jnt.inverseScale.disconnect()

        # connect scale of the main control to the joint
        # for jnt in new_joint_bnd_list:
        #     for axe in "XYZ":
        #         global_con.attr("scale{0}".format(axe)).connect(
        #             jnt.attr("scale{0}".format(axe))
        #         )

        pmc.parent(tail_setup_nde, pmc.PyNode("setup"))

    @staticmethod
    def _add_extra_jnt(tail_joint_list):
        """
        Add an extra joint at the end of the tail.
        This is very specific for arrax we might not need it for other characters.

        Args:
            tail_joint_list(list): The newly created joint list.

        Returns:
            List: The newly tail joint list plus the extra joint.

        """
        # add extra jnt for a smoother tail
        last_jnt = pmc.duplicate(
            tail_joint_list[-1],
            name=tail_joint_list[-1]
            .name()
            .replace(
                "_{0}_jnt".format(len(tail_joint_list) - 1),
                "_{0}_jnt".format(len(tail_joint_list)),
            ),
            parentOnly=True,
        )[0]
        translate = pmc.xform(last_jnt, q=True, t=True, r=True)
        pmc.parent(last_jnt, tail_joint_list[-1])

        last_jnt.translate.set(translate)
        tail_joint_list.append(last_jnt)
        return tail_joint_list
