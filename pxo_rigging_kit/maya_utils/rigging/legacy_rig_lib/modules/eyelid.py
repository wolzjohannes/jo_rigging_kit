"""
www.pixomondo.com
Date: 04 / 02 / 2022

eyelid module
category : Rigging
subcategory : modules
author : Michele Trabona / Rigging TD

"""
from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from future import standard_library
from builtins import range
from builtins import object
from importlib import reload
import pymel.core as pmc
from pymel.core import datatypes
from ..base import module
from ..base import control
from ..utils import joint
from ..utils import name
from ..utils import pixomath as pmath
from ..utils import nodes as pnodes
from ..utils import shape
from ..utils import constraints
import mgear.core.node as node
from ..base import cageCore
from pxo_rigging_kit.maya_utils.rigging import rig_utils
from maya import cmds

standard_library.install_aliases()
reload(constraints)
#   note!!! the first joint should be the upper one and the second the lower


#   eye_jnt = "eye_R_0_start_default_JNT"
class Eyelid(object):
    def __init__(self,
                 eyelid_starts,
                 eye_jnt,
                 head_jnts,
                 main_ctl_offset=10,
                 scale=1,
                 fleshy_eyelids=0,
                 vert_ranges=None,
                 oriz_ranges=None,
                 ribbon=0,
                 ribbon_curves=None,
                 base_module=None,
                 side=None,
                 eye_lid_ribbon_push_vec_axes="X",
                 scaling_control=None):

        local_args = locals()

        self._build(local_args)

    def _build(self, args):
        self.eyelid_starts = args["eyelid_starts"]
        self.eye_jnt = args["eye_jnt"]
        self.head_jnts = args["head_jnts"]
        self.main_ctl_offset = args["main_ctl_offset"]
        self.scale = args["scale"]
        fleshy_eyelids = args["fleshy_eyelids"]
        ribbon = args["ribbon"]

        self.ribbon_curves = args["ribbon_curves"]
        self.vert_ranges = args["vert_ranges"]
        self.oriz_ranges = args["oriz_ranges"]
        self.base_module = args["base_module"]
        self.side = args["side"]

        self.eye_lid_ribbon_push_vec_axes = args["eye_lid_ribbon_push_vec_axes"]
        self.scaling_control = args["scaling_control"]

        if not self.side:
            self.side = name.get_side(self.eyelid_starts[0], with_undescore=False)

        # making module
        self.module_base = module.Module(component="eyelid",
                                         side=self.side,
                                         base_module=self.base_module)

        eye_ctls = self.eyelid_controls_builder()

        self._add_control_attrs(eye_ctls[0])

        self.lid_standard_functionality(eye_ctls[0], eye_ctls[1], eye_ctls[2])

        self.fleshy_eyelids(main_ctl=eye_ctls[0])
        self.lid_ribbon()

    def eyelid_controls_builder(self):

        eyelid_ctl_objs_list = []
        eyelid_snap_tip = joint.get_joint_chain(self.eyelid_starts[0])[-1]

        if not self.side:
            self.side = name.get_side(self.eyelid_starts[0], with_undescore=False)

        eyelid_main_ctl_obj = control.Control(component="eyelid",
                                              side=self.side,
                                              description="control",
                                              subdefinition="default",
                                              shape="triangleX",
                                              scale=self.scale * 0.3,
                                              translate_to=eyelid_snap_tip,
                                              rotate_to= self.eye_jnt,
                                              lock_hide=["s", "r", "v", "tx", "tz"])

        if self.side == "L":                                                         # TO DO orientation with matrix
            eyelid_main_ctl_obj.off.rx.set(eyelid_main_ctl_obj.off.rx.get() + 180)

            # offsetting the control as needed
            eyelid_main_ctl_obj.off.tx.set((eyelid_main_ctl_obj.off.tx.get() + self.main_ctl_offset))

        else:
            eyelid_main_ctl_obj.off.tx.set((eyelid_main_ctl_obj.off.tx.get() - self.main_ctl_offset))

        # limiting the control movement from 0 to 1
        pmc.transformLimits(eyelid_main_ctl_obj.ctl.name(), ty=[0, 1], ety=[1, 1])
        eyelid_ctl_objs_list.append(eyelid_main_ctl_obj)

        for e in self.eyelid_starts:
            eyelid_chain = joint.get_joint_chain(e)

            eyelid_tip = eyelid_chain[-1]

            component = name.get_component(eyelid_tip,
                                           with_undescore=False
                                           )

            eyelid_ctl_obj = control.Control(component=component,
                                             side=self.side,
                                             description="control",
                                             subdefinition="default",
                                             shape="doubleArrowMX",
                                             scale=self.scale * 0.3,
                                             translate_to=eyelid_tip,
                                             rotate_to=self.eye_jnt
                                             )
            #   TO DO orientation with matrix
            # lock_hide = ["s","r","v","tx","tz"])
            # turning the ctrl offset of the upper lid upside down
            # fixing the ctls orientation                                                #TO DO orientation with matrix

            if self.side == "R":
                if "Lower" in eyelid_ctl_obj.off.name():
                    eyelid_ctl_obj.off.rx.set(0)

            if self.side == "L":
                if "Upper" in eyelid_ctl_obj.off.name():
                    eyelid_ctl_obj.off.rx.set(eyelid_ctl_obj.off.rx.get() +180)

            #   limiting the controls movement from - 1 to 1
            pmc.transformLimits(eyelid_ctl_obj.ctl.name(), ty=[-1, 1], ety= [True, True])
            eyelid_ctl_objs_list.append(eyelid_ctl_obj)
            #   parenting the controls under the primary grp
            if pmc.objExists(self.module_base.control_grp):
                for ctl in eyelid_ctl_objs_list:
                    pmc.parent(ctl.off, self.module_base.control_grp)

        return eyelid_ctl_objs_list

    def lid_standard_functionality(self,
                                   main_ctl,
                                   upper_ctl,
                                   lower_ctl,
                                   ):

        #   getting the angle between the joints
        angle_range = pmath.angle_between(self.eyelid_starts[0],
                                          joint.get_joint_chain(self.eyelid_starts[0])[-1],
                                          joint.get_joint_chain(self.eyelid_starts[1])[-1]
                                          )

        #   setting up upper and lower lid range of motion
        if not self.side:
            self.side = name.get_side(self.eyelid_starts[0], with_undescore=True)

        #   remapVal Up
        range_remap_up =pnodes.create_remap_val_node(input="{}.ty".format(upper_ctl.ctl.name()),
                                                     inputMin=-1,
                                                     inputMax=1,
                                                     outputMin=angle_range,
                                                     outputMax=-angle_range,
                                                     output=None,
                                                     name="{}Upper{}RMV".format("range", self.side)
                                                     )

        #   remapVal Low
        range_remap_low = pnodes.create_remap_val_node(input="{}.ty".format(lower_ctl.ctl.name()),
                                                       inputMin=-1,
                                                       inputMax=1,
                                                       outputMin=-angle_range,
                                                       outputMax=angle_range,
                                                       output=None,
                                                       name="{}Lower{}RMV".format("range", self.side)
                                                       )

        #   prepare the insertion of fleshy eyelids rotation
        #   plusMin up (sum)
        self.plus_min_ins_up = node.createPlusMinusAverage1D(
                        ["{}.outValue".format(range_remap_up.name())],
                        operation=1)
        pmc.rename(self.plus_min_ins_up, "{}Upper{}PMA".format("fleshyIns", self.side))
        #   plusMin low (sum)
        self.plus_min_ins_low = node.createPlusMinusAverage1D(
                        ["{}.outValue".format(range_remap_low.name())],
                        operation=1)
        pmc.rename(self.plus_min_ins_low, "{}Lower{}PMA".format("fleshyIns", self.side))
        #   getting the difference between lowe and upper lid rotation for  EYEBLINK
        #   plusMin(sub)
        plus_min_dif_rot = node.createPlusMinusAverage1D(
                        ["{}.output1D".format(self.plus_min_ins_up.name()),
                         "{}.output1D".format(self.plus_min_ins_low.name()),
                         -angle_range],
                        operation=2)
        pmc.rename(plus_min_dif_rot, "{}Eyeblink{}PMA".format("rotDiff", self.side))
        #   multiplyDiv turn on and off the blink (to connect with the ty of the main eye control)
        multi_div_switcher = node.createMulDivNode("{}.output1D".format(plus_min_dif_rot.name()),
                                                   "{}.ty".format(main_ctl.ctl.name()),
                                                   operation=1)

        pmc.rename(multi_div_switcher, "{}Eyeblink{}MLD".format("switcher", self.side))
        #   revert the upper lid value
        multi_div_rev_up_rot = node.createMulDivNode("{}.outputX".format(multi_div_switcher.name()),
                                                     -1,
                                                     operation=1)

        pmc.rename(multi_div_rev_up_rot, "{}EyeblinkUpInv{}MLD".format("switcher", self.side))
        #   getting the  line shifter
        #   blendColor up color 1
        blend_up_line_shift = node.createBlendNode("{}.outputX".format(multi_div_rev_up_rot),
                                                  0,
                                                  blender="{}.blinkPosition".format(main_ctl.ctl.name())
                                                  )

        pmc.rename(blend_up_line_shift, "{}EyeblinkUpper{}CLB".format("blend", self.side))
        # blendColor low color 2
        blend_low_line_shift = node.createBlendNode(0,
                                                    "{}.outputX".format(multi_div_switcher),
                                                    blender="{}.blinkPosition".format(main_ctl.ctl.name()))

        pmc.rename(blend_low_line_shift, "{}EyeblinkLower{}CLB".format("blend", self.side))
        #   adding the blink function to the overall rotation
        #   plusMin up (sum)
        plus_min_add_blink_up = node.createPlusMinusAverage1D(
                        ["{}.output1D".format(self.plus_min_ins_up.name()),
                         "{}.outputR".format(blend_up_line_shift.name())],
                        operation=1)
        pmc.rename(plus_min_add_blink_up, "{}UpperAdd{}PMA".format("eyeblink", self.side))

        #   plusMin low (sum)
        plus_min_add_blink_low = node.createPlusMinusAverage1D(
                        ["{}.output1D".format(self.plus_min_ins_low.name()),
                         "{}.outputR".format(blend_low_line_shift.name())],
                        operation=1,
                        output="{}.rz".format(self.eyelid_starts[1]))

        pmc.rename(plus_min_add_blink_low, "{}LowerAdd{}PMA".format("eyeblink", self.side))

        #   ONLY FOR THE UPPER
        #   plusminus (range of motion - lower lid rotation)
        plus_min_angleRange_push_up = node.createPlusMinusAverage1D(
                        [angle_range,
                         "{}.outValue".format(range_remap_low.name())],
                        operation=2)

        pmc.rename(plus_min_angleRange_push_up, "{}UpperPush{}PMA".format("angleRange", self.side))

        #   invert for upper lid
        mult_div_lower_inverse_push = node.createMulDivNode("{}.output1D".format(plus_min_angleRange_push_up.name()),
                                                   -1,
                                                   operation=1)

        pmc.rename(mult_div_lower_inverse_push, "{}UpperRev{}MPD".format("angleRange", self.side))
        #   clamp (max is the upper plus minus)
        clump_lower_push = node.createClampNode("{}.output1D".format(plus_min_add_blink_up.name()),
                                                "{}.outputX".format(mult_div_lower_inverse_push.name()),
                                        angle_range
                                       )

        pmc.rename(clump_lower_push, "{}UpperPush{}CLP".format("angleRange", self.side))
        print(type(clump_lower_push))
        print(type(self.eyelid_starts[0]))
        print("ERROR HERE")
        cmds.connectAttr(f"{clump_lower_push}.outputR",
                         f"{self.eyelid_starts[0]}.rz")

        print("NOT HERE")

    def fleshy_eyelids(self,
                       main_ctl,
                       up_down_axes="rz"
                       ):
        if not self.side:
            self.side = name.get_side(self.eyelid_starts[0], with_undescore=False)
        #   multiply to switch on and off the follow
        mult_div_eye_vert_follow = node.createMulDivNode("{}.{}".format(self.eye_jnt, up_down_axes),
                                                         "{}.eyeFollow".format(main_ctl.ctl.name()),
                                                         operation=1
                                                         )

        pmc.rename(mult_div_eye_vert_follow, "{}Switcher{}MPD".format("fleshyVert", self.side))
        #   remap value for upper follow up/low
        range_remap_vert_up = pnodes.create_remap_val_node(input="{}.outputX".format(mult_div_eye_vert_follow.name()),
                                                           inputMin=self.vert_ranges[0][0][0],
                                                           inputMax=self.vert_ranges[0][0][1],
                                                           outputMin=self.vert_ranges[0][1][0],
                                                           outputMax=self.vert_ranges[0][1][1],
                                                           output="{}.input1D[1]".format(self.plus_min_ins_up.name()),
                                                           name="{}FleshyUp{}RMV".format("vert", self.side))

        #   remap value for lower follow up/low
        range_remap_vert_low = pnodes.create_remap_val_node(input="{}.outputX".format(mult_div_eye_vert_follow.name()),
                                                            inputMin=self.vert_ranges [1][0][0],
                                                            inputMax=self.vert_ranges [1][0][1],
                                                            outputMin=self.vert_ranges [1][1][0],
                                                            outputMax=self.vert_ranges [1][1][1],
                                                            output="{}.input1D[1]".format(self.plus_min_ins_low.name()),
                                                            name="{}FleshyLow{}RMV".format("vert", self.side))
        #   setting up the ramp value
        range_remap_vert_low.value[2].value_FloatValue.set(0.5)
        range_remap_vert_low.value[2].value_Position.set(0.5)
        range_remap_vert_low.value[2].value_Interp.set(1)
        range_remap_vert_low.value[1].value_FloatValue.set(0.64)

        # remap value for upper follow right/left
        mult_div_eye_oriz_follow = node.createMulDivNode("{}.ry".format(self.eye_jnt ),
                                                         "{}.eyeFollow".format(main_ctl.ctl.name()),
                                                         operation=1
                                                         )

        pmc.rename(mult_div_eye_oriz_follow, "{}Switcher{}MPD".format("fleshyOriz", self.side))
        range_remap_oriz_up = pnodes.create_remap_val_node(input="{}.outputX".format(mult_div_eye_oriz_follow.name()),
                                                           inputMin=self.oriz_ranges[0][0][0],
                                                           inputMax=self.oriz_ranges[0][0][1],
                                                           outputMin=self.oriz_ranges[0][1][0],
                                                           outputMax=self.oriz_ranges[0][1][1],
                                                           output="{}.ry".format(self.eyelid_starts[0]),
                                                           name="{}FleshyUp{}RMV".format("oriz", self.side)
                                                           )
        # remap value for lower follow right/left
        range_remap_oriz_up = pnodes.create_remap_val_node(input="{}.outputX".format(mult_div_eye_oriz_follow.name()),
                                                           inputMin=self.oriz_ranges[1][0][0],
                                                           inputMax=self.oriz_ranges[1][0][1],
                                                           outputMin=self.oriz_ranges[1][1][0],
                                                           outputMax=self.oriz_ranges[1][1][1],
                                                           output="{}.ry".format(self.eyelid_starts[1]),
                                                           name="{}FleshyLow{}RMV".format("oriz", self.side)
                                                           )

    def _add_control_attrs(self, main_ctl):
        pmc.addAttr(main_ctl.ctl, ln="blinkPosition", type="float", dv=0.7, min=0.0, max=1.0, k=1)
        pmc.addAttr(main_ctl.ctl, ln="eyeFollow", type="float", dv=1.0, min=0.0, max=1.0, k=1)

    def lid_ribbon(self):
        controls_number = 5
        #   making the eyelid ribbon setup
        eye_jnts = joint.get_joint_chain(self.eye_jnt)
        eye_jnt_offset = pmc.duplicate(eye_jnts[0])[0]

        offset_joints = joint.get_joint_chain(eye_jnt_offset)
        [offset_joint.rename("{0}_lidRibbon_jnt".format(str(offset_joint.shortName())))
         for offset_joint
         in offset_joints
         ]

        pmc.parent(eye_jnt_offset, eye_jnts[0])
        eye_jnt_offset.attr("translate{}".format(self.eye_lid_ribbon_push_vec_axes)).set(.5)
        vector_push = (pmath.vector_between(eye_jnts[0], eye_jnt_offset, normalize=True) * 0.05)
        # get side
        if not self.side:
            self.side = name.get_side(self.eye_jnt, with_undescore=False)

        local_eyelid_grp = pmc.group(n="eyelidLocalDef{}_grp".format(self.side),
                                     em=1)
        if self.base_module:
            pmc.parent(local_eyelid_grp, self.base_module.no_transf_grp)

        for curve in self.ribbon_curves:
            pmc.rebuildCurve(curve,
                             ch=1, rpo=1, rt=0,
                             end=1, kr=0, kcp=0,
                             kep=1, kt=0, s=4,
                             d=3, tol=0.01)
            pmc.delete(curve, ch=1)

            eyelid_nurb = shape.build_nurb_from_curve_vector(curve, vector_push)
            #   building the local eyelid_nurb
            eyelid_component = name.get_component(eyelid_nurb.name(), str_index=1)
            local_eyelid_name = eyelid_nurb.name().replace(eyelid_component,
                                                           "local{}".format(eyelid_component))
            local_eyelid = pmc.duplicate(eyelid_nurb, n = local_eyelid_name)[0]
            pmc.parent(local_eyelid, local_eyelid_grp)
            pmc.parent(eyelid_nurb, self.module_base.extraElements_grp)
            nurb_comp = eyelid_nurb.name().split('_')[0]
            u_value_base = 1.0/(controls_number+1)

            for it in range(controls_number+1)[1:]:
                u_val = u_value_base*it

                rivet_node = constraints.create_transform_on_surbsurface(eyelid_nurb,
                                                                         component="{}Tweak".format(nurb_comp),
                                                                         index=it,
                                                                         u_value=u_val,
                                                                         v_value=0.5,
                                                                         turn_on_percentage=True)

                eyelid_tweak_ctl = control.Control(component="{}Tweak{}".format(nurb_comp, it),
                                                   side=self.side,
                                                   description="control",
                                                   subdefinition="default",
                                                   shape="circleZ",
                                                   scale=self.scale * 0.3,
                                                   color_name="secondary",
                                                   move_to=rivet_node,
                                                   parent= self.module_base.secondary_grp,
                                                   lock_hide=["s", "v"])

                local_rivet_node = constraints.create_transform_on_surbsurface(local_eyelid,
                                                                               component="{}LocalTweak".format(nurb_comp),
                                                                               index=it,
                                                                               u_value=u_val,
                                                                               v_value=0.5,
                                                                               turn_on_percentage=True
                                                                               )


                pmc.parent(local_rivet_node, local_eyelid_grp)

                eyelid_tweak_jnt = joint.make_joint_on_element(eyelid_tweak_ctl.ctl,
                                                               suffix="faceJnt",
                                                               connect=0)

                # create offset joints

                base_eyelid_deformation_jnt = joint.make_joint_on_element(eyelid_tweak_ctl.off,
                                                                          suffix="faceOffsetJnt",
                                                                          connect=False)

                pmc.parent(eyelid_tweak_jnt, rivet_node)
                pmc.parent(base_eyelid_deformation_jnt, rivet_node)

                constraints.connection_tag(eyelid_tweak_jnt,
                                           "tConnection,rConnection",
                                           eyelid_tweak_ctl.ctl)

                if self.scaling_control:

                    self.scaling_control.attr("scale").connect(eyelid_tweak_jnt.attr("scale"))

                    constraints.connection_tag(eyelid_tweak_ctl.ctl,
                                               "sConnection",
                                               self.scaling_control)

                    constraints.connect_by_tag(eyelid_tweak_ctl.ctl)

                constraints.connect_by_tag(eyelid_tweak_jnt)
                #   make local version
                eyelid_tweak_local_jnt = joint.make_joint_on_element(eyelid_tweak_ctl.ctl,
                                                                     suffix="localJnt",
                                                                     connect=0)
                constraints.connection_tag(eyelid_tweak_local_jnt,
                                           "tConnection,rConnection,sConnection",
                                           eyelid_tweak_jnt)

                constraints.connect_by_tag(eyelid_tweak_local_jnt)
                #   local_eye = name.change_suffix(self.eye_jnt,"localJnt")
                pmc.parent(eyelid_tweak_local_jnt, local_rivet_node)

                rig_utils.pxo_constraining(masters=rivet_node,
                                           slaves=eyelid_tweak_ctl.off,
                                           maintainOffset=True,
                                           name=None,
                                           skipRotate=None,
                                           skipTranslate=None,
                                           skipScale=("x", "y", "z"),
                                           native=False,
                                           space_switch=False,
                                           host=None,
                                           )




                pmc.parent(rivet_node, self.module_base.joints_grp)


    @staticmethod
    def build_cage():
        eyelid_cage_dic ={'main_name': 'eyelid_L_',
 'name_list': [ ['eyelid_L_0_main_default_faceJnt'],
                ['eyelidLower_L_0_start_default_faceJnt eyelidLower_L_0_end_default_faceJnt'],
               ['eyelidUpper_L_0_start_default_faceJnt eyelidUpper_L_0_end_default_faceJnt']],
 'parents_name': ['unknown',
                   'eyelid0_L_cageCtl_default_ctrl',
                   'eyelid0_L_cageCtl_default_ctrl'],
 'positions_list': [[(2.220446049250313e-16,0.0,1.0,0.0,
                         0.0,1.0,0.0,0.0,
                         -1.0,0.0,2.220446049250313e-16,0.0,
                         0.0,0.0,0.0,1.0)],

                        [(0.0,-0.5735764363510462,0.8191520442889919,0.0,
                      -5.551115123125784e-17,0.8191520442889918,0.5735764363510462,0.0,
                      -1.0,-5.551115123125784e-17,0.0,0.0,
                      0.0,0.0,0.0,1.0),
                     (0.0,-0.5735764363510462,0.8191520442889919,0.0,
                      -5.551115123125784e-17,0.8191520442889918,0.5735764363510462,0.0,
                      -1.0,-5.551115123125784e-17,0.0,0.0,
                      -4.440892098500627e-16,-2.2943057454041833,3.2766081771559668,1.0)],
                    [(0.0,0.5735764363510462,0.8191520442889919,0.0,
                      5.551115123125784e-17,0.8191520442889918,-0.5735764363510462,0.0,
                      -1.0,5.551115123125784e-17, 0.0,0.0,
                      0.0,0.0,0.0,1.0),
                     (0.0,0.5735764363510462,0.8191520442889919,0.0,
                      5.551115123125784e-17,0.8191520442889918,-0.5735764363510462,0.0,
                      -1.0,5.551115123125784e-17,0.0,0.0,
                      4.4408920985006257e-16,2.2943057454041833,3.2766081771559668,1.0)]]}
        cageCore.Cage.build_cage_from_dict(eyelid_cage_dic)


    @staticmethod
    def extract_joints(cage_name):
        joints_chain = cageCore.Cage.joints_maker(cage_name)
        for chain in joints_chain:
            if "Lower" in chain[0].name():
                r_val = 180
                if "R" in chain[0].name():
                    r_val = r_val*-1
                pmc.setAttr("{}.rx".format(chain[0]), r_val)
                pmc.makeIdentity(chain[0], apply=1,
                                 t=1, r=1, s=1,
                                 n=0, pn=1)
        pmc.parent(joints_chain[1][0], joints_chain[2][0], joints_chain[0][0])

