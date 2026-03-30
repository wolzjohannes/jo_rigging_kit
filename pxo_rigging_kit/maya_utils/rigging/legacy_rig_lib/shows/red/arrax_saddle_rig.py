"""
www.pixomondo.com
Date: 22 / 03 / 2022

saddleSystem module
category : Rigging
subcategory : systems
author : Christos Orfanidis / Junior Rigging TD

"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from builtins import super
from future import standard_library
standard_library.install_aliases()
from builtins import range
import pymel.core as pm

from ...systems import saddleSystem

from ...modules import freeControls
from ...modules import rivetControls
from ...modules import ribbon as rib

from ...utils import data
from ...utils import name
from ...utils import transform
from ...utils import constraints as pcons


class ArraxSaddleRig(saddleSystem.Saddle_system):

    STEERING_HANDLES = (("steeringHandle_L_0_bind_default_saddleJnt",
                        "steeringHandle_L_1_bind_default_saddleJnt"),
                        ("steeringHandle_R_0_bind_default_saddleJnt",
                        "steeringHandle_R_1_bind_default_saddleJnt")
                        )

    BUILD_FAKE_COLL = True

    SADDLE_TWEAKERS = ['saddleStraps_C_001_high_geo', 'saddleStrapsMetal_C_001_high_geo',
                       'saddleBolt_C_001_high_geo', 'saddleBlankets_C_008_high_geo',
                       'saddleBlankets_C_002_high_geo', 'saddleBlankets_C_003_high_geo',
                       'saddleLeatherPads_C_002_high_geo', 'saddleLeatherPads_C_003_high_geo',
                       'saddleMetalPieces_C_001_high_geo', 'saddleBlanket_C_001_high_geo',
                       'saddleDisks_C_003_high_geo', 'saddleDisks_C_004_high_geo',
                       'saddlePlate_C_001_high_geo', 'longRope_L_001_high_geo',
                       'sideFrontStrap_L_001_high_geo', 'sideBackStrap_L_001_high_geo',
                       'shoulderPatch_R_001_high_geo', 'shoulderPatch_L_001_high_geo',
                       'saddleBlanket_C_002_high_geo', 'saddlePad_C_002_high_geo',
                       'saddleBase_C_001_high_geo', 'strapBaseNrb_R_001_high_geo',
                       'strapBaseNrb_L_001_high_geo'
                       ]

    RIBBON_GEOMETRIES = [('strapBaseNrb_R_001_high_geo', 7), ('strapBaseNrb_L_001_high_geo', 7),
                         ('shoulderOutterStrap_R_001_high_geo', 4), ('shoulderOutterStrap_L_001_high_geo', 4),
                         ('shoulderInnerStrap_R_001_high_geo', 4), ('shoulderInnerStrap_L_001_high_geo', 4),
                         ('shoulderMiddleStrap_R_001_high_geo', 4), ('shoulderMiddleStrap_L_001_high_geo', 4),
                         ('frontCenterStrap_R_001_high_geo', 4), ('frontCenterStrap_L_001_high_geo', 4),
                         ('upperForkStrap_R_001_high_geo', 4), ('upperForkStrap_L_001_high_geo', 4),
                         ('lowerForkStrap_R_001_high_geo', 4), ('lowerForkStrap_L_001_high_geo', 4),
                         ('sideFrontStrap_L_001_high_geo', 4), ('sideBackStrap_L_001_high_geo', 4),
                         ('longRope_L_001_high_geo', 12)
                         ]

    COLLAR_GEOMETRIES = [('saddleBaseNrb_C_001_high_geo', 17)]
    COLLAR_SPACES = ['C_bnd_chest_0_0_saddleJnt',
                     'C_bnd_neck_0_0_saddleJnt'
                     ]

    SHOULDER_GEOMETRIES = [('shoulderPatch_R_001_high_geo', 5), ('shoulderPatch_L_001_high_geo', 5)]
    SHOULDER_SPACES = ['C_bnd_chest_0_0_saddleJnt',
                       'C_bnd_neck_0_0_saddleJnt'
                       ]
    REIGN_FREE_GEOMETRIES = (('reignFreeMain_R_001_high_geo', 3), ('reignFreeMain_L_001_high_geo', 3))
    REIGN_FREE_CONTROLS = ('reignFreeMaster_R_0_default_loc', 'reignFreeMaster_L_0_default_loc')

    REIGN_GEOMETRIES = ('reignFixedMain_R_001_high_geo', 3), ('reignFixedMain_L_001_high_geo', 3)
    REIGN_CONTROLS = ('reignFixedMaster_R_0_default_loc', 'reignFixedMaster_L_0_default_loc')

    REIGN_SECONDARY_GEOMETRIES = (('reignFixedSecondary_R_001_high_geo', 5),
                                  ('reignFixedSecondary_L_001_high_geo', 5)
                                  )

    REIGN_SECONDARY_FREE_GEOMETRIES = (('reignFreeSecondary_R_001_high_geo', 5),
                                       ('reignFreeSecondary_L_001_high_geo', 5)
                                       )

    def __init__(self):
        self.name = "saddleArrax"
        rig_path = data.get_rigging_main_dir(type="prop")
        model_path = r"X:\redgun_reg-6344\_library\assets\props\prp_saddleArrax\mdl\_publish\reg_prp_saddleArrax_mdl_v055_vat.mb"

        super(ArraxSaddleRig, self).__init__(prop_name=self.name,
                                             rig_data_path=rig_path,
                                             model_path=model_path,
                                             builder_path=None,
                                             root_jnt="C_bnd_spine_0_hip_jnt",
                                             head_jnt="C_bnd_saddle_0_0_jnt",
                                             scale=10,
                                             build_bs=True,
                                             load_deformers=False,
                                             go_to_T_pose=False,
                                             load_ctls=True,
                                             load_skin=True,
                                             pre_build=self.saddle_arrax_pre_build,
                                             upgrade=self.saddle_arrax_upgrade,
                                             post_build=self.saddle_arrax_post_build)

        self.ribbon = None

        self.reigns_free = None
        self.reigns = None
        self.reigns_free_secondary = None
        self.reigns_fixed_secondary = None

        self.collar = None
        self.shoulder = None
        self.handle_rivet_parents = None

    def saddle_arrax_pre_build(self):
        if self.SADDLE_TWEAKERS:
            #   create group to keep order in no_transform
            tweakers = pm.createNode('transform', n='blendTargetsLocal_C_001_GRP')
            pm.parent(tweakers, self.base_module.no_transf_grp)

            for element in self.SADDLE_TWEAKERS:
                element = pm.PyNode(element)
                element_dup = pm.duplicate(element,
                                           n=element.name().replace("_high_",
                                                                    "_local_"))[0]

                pm.parent([element_dup], tweakers)

                pm.blendShape([element_dup],
                              element,
                              frontOfChain=True,
                              weight=(0, 1))

    def saddle_arrax_upgrade(self):
        self.steering_handles_build()

        #   rivets build
        self.strap_rivet_build()
        self.handle_rivet_build()

        #   ribbons build
        self.ribbon_build()
        self.shoulder_build()
        self.collar_build()

        self.reigns_free_build()
        self.reigns_build()
        self.reigns_free_secondary_build()
        self.reigns_fixed_secondary_build()

        self.fake_collision_build()

    def saddle_arrax_post_build(self):
        # parenting the handles with the rivet joint

        for i in range(0, len(self.STEERING_HANDLES)):

            pcons.pxoparent(masters='saddleMainSaddle0_C_control_default_ctrl',
                            slaves=self.ctls_objs_list[i][0].off, maintainOffset=True, native=False)

        # parenting the handles with the rivet joint
        for i in self.reigns_free.prim_offs:
            pcons.pxoparent(masters="saddleMainSaddle0_C_control_default_ctrl",
                            slaves=i,
                            maintainOffset=True,
                            native=False
                            )

        reversed_handles = tuple(reversed(self.STEERING_HANDLES))

        for iteration, i in enumerate(self.reigns.prim_offs):
            pcons.pxoparent(masters=reversed_handles[iteration][0],
                            slaves=i,
                            maintainOffset=True,
                            native=False
                            )

        vis_control = pm.PyNode('vis_C_control_default_ctrl')
        vis_control.jointsVis.set(False)

        vis_control.addAttr('reigns',
                            at='enum',
                            enumName='free:fixed',
                            k=False,
                            dv=True
                            )

        vis_control.reigns.set(0)
        vis_control.reigns.set(cb=True)

        fixed = pm.PyNode('saddleReinsWrapped_C_001_high_grp')
        free = pm.PyNode('saddleReins_C_001_high_grp')

        fixed_module = pm.PyNode('reignFixed_C_module_GRP')
        free_module = pm.PyNode('reignFree_C_module_GRP')

        fixed_secondary_module = pm.PyNode('reignFixedSecondary_C_module_GRP')
        free_secondary_module = pm.PyNode('reignFreeSecondary_C_module_GRP')

        revnde = pm.createNode('reverse', n='visibilityReverse')

        vis_control.reigns.connect(fixed.visibility)
        vis_control.reigns.connect(fixed_module.visibility)
        vis_control.reigns.connect(fixed_secondary_module.visibility)

        vis_control.reigns.connect(revnde.inputX)

        revnde.outputX.connect(free.visibility)
        revnde.outputX.connect(free_module.visibility)
        revnde.outputX.connect(free_secondary_module.visibility)

        # Turn off module vis
        modules_grp = pm.listRelatives('modules_GRP')

        for module in modules_grp:
            pm.setAttr('{}.extraElements_vis'.format(module), False)
            pm.setAttr('{}.noTransf_vis'.format(module), False)
            pm.setAttr('{}.joints_vis'.format(module), False)

        pm.setAttr("vis_C_control_default_ctrl.jointsVis", False)
        pm.delete('skeleton_grp')

    def steering_handles_build(self):
        self.ctls_objs_list = []
        for jnt_list in self.STEERING_HANDLES:
            side = name.get_side(jnt_list[0], with_undescore=False)
            free_controls_mod = freeControls.FreeControls(name="Handles",
                                                          scale=10.0,
                                                          elements_list=jnt_list,
                                                          create_controls=True,
                                                          side=side,
                                                          make_jnt=0,
                                                          seperate_hierarchy=False,
                                                          base_module=self.base_module
                                                          )

            ctls_objs = free_controls_mod.ctls_list

            handle_name = name.change_suffix(ctls_objs[0].ctl.name(), 'ikh')

            ikhandle = pm.ikHandle(n=handle_name, sj=jnt_list[0], ee=jnt_list[-1])

            pm.rename(ikhandle[1], name.change_suffix(handle_name, 'eff'))
            pm.parent(ikhandle[0], free_controls_mod.module_base.noTransf_grp)

            polevec_target = pm.createNode('transform', n=name.change_suffix(handle_name, 'pos'))
            pm.matchTransform(polevec_target, ctls_objs[0].ctl)
            pm.parent(polevec_target, ctls_objs[0].ctl)

            polevec_target.tz.set(2)

            pm.parentConstraint(ctls_objs[0].ctl, jnt_list[0])
            pm.parentConstraint(ctls_objs[-1].ctl, ikhandle[0])
            pm.poleVectorConstraint(polevec_target, ikhandle[0])

            pm.parent(ctls_objs[-1].off, ctls_objs[0].ctl)
            self.ctls_objs_list.append(ctls_objs)

    def strap_rivet_build(self):
        rivetControls.RivetControls(name="Strap",
                                    moving_mesh="strap_rivet_geo",
                                    dummies_rivet_grp="strap_rivet_grp",
                                    create_controls=True,
                                    seperate_hierarchy=True,
                                    base_module=self.base_module
                                    )

        geo_nde = pm.PyNode('strap_rivet_geo')
        pm.parent(geo_nde, self.base_module.no_transf_grp)

    def handle_rivet_build(self):
        handle_rivets = rivetControls.RivetControls(name="Handle",
                                                    moving_mesh="handles_rivet_geo",
                                                    dummies_rivet_grp="handles_rivet_grp",
                                                    create_controls=False,
                                                    seperate_hierarchy=True,
                                                    base_module=self.base_module
                                                    )

        self.handle_rivet_parents = handle_rivets.joint_output[::-1]
        geo_nde = pm.PyNode('handles_rivet_geo')
        pm.parent(geo_nde, self.base_module.no_transf_grp)

    def ribbon_build(self):
        """ wraps the ribbon module and class to create a ribbon from information stated in this module

        Returns:f
            ribbon(cls): class containing the ribbon info
        """
        self.ribbon = rib.Ribbon(geometry_info=self.RIBBON_GEOMETRIES,
                                 placements=(),
                                 scale=self.scale,
                                 component_name='ribbon',
                                 base_module=self.base_module
                                 )

        return self.ribbon

    def collar_build(self):
        """ wraps the ribbon module and class to create a ribbon from information stated in this module

        Returns:
            ribbon(cls): class containing the ribbon info
        """

        vis_control = pm.PyNode('vis_C_control_default_ctrl')
        self.collar = rib.Ribbon(geometry_info=self.COLLAR_GEOMETRIES,
                                 placements=(),
                                 scale=self.scale,
                                 component_name='collar',
                                 base_module=self.base_module,
                                 controller_spaces=self.COLLAR_SPACES,
                                 host=vis_control
                                 )

        return self.collar

    def reigns_build(self):
        """ wraps the ribbon module and class to create a ribbon from information stated in this module

        Returns:
            ribbon(cls): class containing the ribbon info
        """
        self.reigns = rib.Ribbon(geometry_info=self.REIGN_GEOMETRIES,
                                 placements=self.REIGN_CONTROLS,
                                 component_name='reignFixed',
                                 scale=self.scale,
                                 base_module=self.base_module
                                 )

        return self.reigns

    def reigns_free_build(self):
        """ wraps the ribbon module and class to create a ribbon from information stated in this module

        Returns:
            ribbon(cls): class containing the ribbon info
        """

        self.reigns_free = rib.Ribbon(geometry_info=self.REIGN_FREE_GEOMETRIES,
                                      placements=self.REIGN_FREE_CONTROLS,
                                      component_name='reignFree',
                                      scale=self.scale,
                                      base_module=self.base_module
                                      )

        return self.reigns_free

    def reigns_free_secondary_build(self):
        """ wraps the ribbon module and class to create a ribbon from information stated in this module

        Returns:
            ribbon(cls): class containing the ribbon info
        """

        self.reigns_free_secondary = rib.Ribbon(geometry_info=self.REIGN_SECONDARY_FREE_GEOMETRIES,
                                                component_name='reignFreeSecondary',
                                                scale=self.scale,
                                                base_module=self.base_module
                                                )

        return self.reigns_free_secondary

    def reigns_fixed_secondary_build(self):
        """ wraps the ribbon module and class to create a ribbon from information stated in this module

        Returns:
            ribbon(cls): class containing the ribbon info
        """

        self.reigns_fixed_secondary = rib.Ribbon(geometry_info=self.REIGN_SECONDARY_GEOMETRIES,
                                                 component_name='reignFixedSecondary',
                                                 scale=self.scale,
                                                 base_module=self.base_module
                                                 )

        return self.reigns_fixed_secondary

    def shoulder_build(self):
        """ wraps the ribbon module and class to create a ribbon from information stated in this module

        Returns:
            ribbon(cls): class containing the ribbon info
        """

        self.shoulder = rib.Ribbon(geometry_info=self.SHOULDER_GEOMETRIES,
                                   placements=(),
                                   scale=self.scale,
                                   component_name='shoulderPads',
                                   base_module=self.base_module
                                   )

        return self.shoulder

    def fake_collision_build(self):
        """
        rivet_mod = rivetControls.RivetControls(name="frontPlate",
                                                scale=10.0,
                                                moving_mesh="fakeCollisionSupport_geo",
                                                dummies_rivet_grp="fake_collision_rivet_grp",
                                                create_controls=0,
                                                seperate_hierarchy=0,
                                                make_jnt=0,
                                                base_module=self.base_module
                                                )


        riv_nodes = rivet_mod.rivet_nodes
        print riv_nodes
        """

        # SETUP FOR THE SADDLE
        saddle_locators = pm.listRelatives("fake_collision_rivet_grp")
        collar_locators = pm.listRelatives("C_fakeCollisionCollarLocs_GRP")

        dummies = saddle_locators + collar_locators

        rvt_list = []
        for dummy in dummies:
            rvt = transform.rivet_on_face(mesh="fakeCollisionSupport_geo",
                                          dummy=dummy)[0]

            pm.parent(rvt, self.base_module.no_transf_grp)

            rvt_list.append(rvt)

        fols_grouped = pm.group(rvt_list, n='fake_collision_fols')

        if self.BUILD_FAKE_COLL:
            end_locators = [x for x in dummies if 'end' in x.name()]
            end_rivets = [x for x in rvt_list if 'end' in x.name()]

            fake_collision_setup('fakeCollisionCollider_geo',
                                 end_rivets, transforms_out=end_locators)

            locator_grouped = pm.group(end_locators, n='fake_collision_locs')

        col_joints = list()
        for rvt in rvt_list:
            if "start" in rvt.name():
                jnt_nd = pm.PyNode(rvt.name().replace("_rivFol",
                                                      "_saddleJnt"))
                col_joints.append(jnt_nd)
                name_changed = rvt.name().replace("_start_default_rivFol", "_end_default_loc")

                if 'Collar' not in rvt.name():
                    pm.pointConstraint(rvt, jnt_nd, mo=True)
                    up_object = pm.createNode('transform', n='{}_upVec'.format(rvt.name()))
                    pm.matchTransform(up_object, rvt)

                    pm.parent(up_object, rvt)

                    pm.xform(up_object, t=(0, 1, 0), absolute=True, ws=True)

                    tip_rvt = pm.PyNode(name_changed)

                    aim_constraint = pm.aimConstraint(tip_rvt,
                                                      jnt_nd,
                                                      weight=1,
                                                      aimVector=[1, 0, 0],
                                                      upVector=[0, 1, 0],
                                                      mo=True,
                                                      worldUpType=1,
                                                      worldUpObject=up_object
                                                      )

                else:
                    pm.pointConstraint(pm.PyNode(name_changed), jnt_nd, mo=False)
                    pm.orientConstraint(rvt,
                                        jnt_nd,
                                        weight=1,
                                        mo=True)

        joints_grouped = pm.group(col_joints, n='fake_collision_jnts')
        pm.parent(joints_grouped, "skeleton_GRP")

        pm.parent('vectorCollision_GRP', "no_transf_GRP")
        pm.parent([fols_grouped], 'vectorCollision_GRP')

        pm.delete("fake_collision_rivet_grp")


def fake_collision_setup(mesh_node, transforms_in, transforms_out=None):
    collision_master = pm.createNode('transform', n='collisionMaster')
    pm.parent(collision_master, "no_transf_GRP")

    for it, trnsf in enumerate(transforms_in):

        #   getting the translate from the transform WM
        translate_from_mat = pm.createNode("math_TranslationFromMatrix")

        pm.connectAttr("{}.worldMatrix[0]".format(trnsf),
                       "{}.input".format(translate_from_mat))

        #   getting the closest point on mesh
        cls_point = pm.createNode("closestPointOnMesh")
        pm.connectAttr("{}.worldMatrix[0]".format(mesh_node),
                       "{}.inputMatrix".format(cls_point))
        pm.connectAttr("{}.outMesh".format(mesh_node),
                       "{}.inMesh".format(cls_point))

        #   connect the locator translation to the cls point
        pm.connectAttr("{}.output".format(translate_from_mat),
                       "{}.inPosition".format(cls_point))

        #   finding the vector from the transf to the nearest point
        diff_vector = pm.createNode("math_SubtractVector")
        pm.connectAttr("{}.output".format(translate_from_mat),
                       "{}.input1".format(diff_vector))
        pm.connectAttr("{}.position".format(cls_point),
                       "{}.input2".format(diff_vector))

        #   normalizing the diff_vec
        normal_vec = pm.createNode("math_NormalizeVector")

        pm.connectAttr("{}.output".format(diff_vector),
                       "{}.input".format(normal_vec))

        #   dot product between diff vector and geo normal
        dot_node = pm.createNode("math_DotProduct")
        pm.connectAttr("{}.normal".format(cls_point),
                       "{}.input1".format(dot_node))
        pm.connectAttr("{}.output".format(normal_vec),
                       "{}.input2".format(dot_node))

        #   checking the dot product and generating bool if less then zero
        compare = pm.createNode("math_Compare")
        pm.setAttr("{}.operation".format(compare), 1)
        pm.connectAttr("{}.output".format(dot_node),
                       "{}.input1".format(compare))

        #   feeding the bool in a selection
        selector = pm.createNode("math_SelectVector")
        pm.connectAttr("{}.output".format(compare),
                       "{}.condition".format(selector))
        pm.connectAttr("{}.output".format(translate_from_mat),
                       "{}.input1".format(selector))
        pm.connectAttr("{}.position".format(cls_point),
                       "{}.input2".format(selector))

        #   make a pinning option
        pinning_choice = pm.createNode('math_SelectVector')
        pinning_choice.condition.set(1)
        pm.connectAttr("{}.position".format(cls_point),
                       "{}.input1".format(pinning_choice))
        pm.connectAttr("{}.output".format(selector),
                       "{}.input2".format(pinning_choice))

        #   generating an output for the transform
        if transforms_out:
            if len(transforms_in) == len(transforms_out):
                pm.connectAttr("{}.output".format(pinning_choice),
                               "{}.translate".format(transforms_out[it]))

            else:
                print('did not connect the calculation to a transform, since no output was given')

        collision_switch_name = trnsf.shortName()
        collision_master.addAttr('{}'.format(collision_switch_name), at='bool', keyable=True)
        collision_master.attr(collision_switch_name).connect(pinning_choice.condition)
        collision_master.attr(collision_switch_name).set(1)
