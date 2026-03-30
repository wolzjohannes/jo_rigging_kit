"""
www.pixomondo.com
Date: 09 / 05 / 2022

saddleSystem module
category : Rigging
subcategory : systems
author : Christof Puehringer / Junior Rigging TD

"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


# external libraries
from builtins import super
from future import standard_library
standard_library.install_aliases()
from builtins import range
import pymel.core as pm

# internal libraries
from ...systems import saddleSystem

from ...modules import freeControls
from ...modules import rivetControls

from ...modules import ribbon as rib

from ...utils import data
from ...utils import name
from ...utils import constraints as pcons
from ...utils import transform


class SyraxSaddleRig(saddleSystem.Saddle_system):

    STEERING_HANDLES = (("steeringHandle_L_0_bind_default_saddleJnt",
                        "steeringHandle_L_1_bind_default_saddleJnt"),
                        ("steeringHandle_R_0_bind_default_saddleJnt",
                        "steeringHandle_R_1_bind_default_saddleJnt"),
                        ("footrestHandle_L_0_bind_default_saddleJnt",
                        "footrestHandle_L_1_bind_default_saddleJnt"),
                        ("footrestHandle_R_0_bind_default_saddleJnt",
                        "footrestHandle_R_1_bind_default_saddleJnt"))

    SADDLE_TWEAKERS = ['saddleWing_C_001_high_geo', 'saddleStrap_C_001_high_geo',
                       'saddleBolt_C_002_high_geo', 'saddleMetalPieces_C_001_high_geo',
                       'saddleBolt_C_001_high_geo', 'saddleRings_C_001_high_geo',
                       'saddleBlanket_C_004_high_geo', 'saddleBlankets_C_001_high_geo',
                       'saddleDecotriangles_C_001_high_geo', 'collarMain_R_001_high_geo',
                       'collarMain_L_001_high_geo', 'saddleFrontStrapNrb_R_001_high_geo',
                       'saddleBackStrapNrb_R_001_high_geo', 'saddleFrontStrapNrb_L_001_high_geo',
                       'saddleBackStrapNrb_L_001_high_geo', 'saddleBacklayer_C_001_high_geo'
                       ]

    TWEAKER_UPGRADE = ('collarMain_R_001_high_geo', 'collarMain_L_001_high_geo',
                       'saddleFrontStrapNrb_R_001_high_geo', 'saddleBackStrapNrb_R_001_high_geo',
                       'saddleFrontStrapNrb_L_001_high_geo', 'saddleBackStrapNrb_L_001_high_geo',
                       'saddleWing_C_001_high_geo', 'saddleBlankets_C_001_high_geo',
                       'saddleMetalPieces_C_001_high_geo'
                       )

    RIBBON_GEOMETRIES = (('strapNrb_R_001_high_geo', 4), ('strapNrb_L_001_high_geo', 4),
                         ('saddleFrontStrapNrb_R_001_high_geo', 5), ('saddleBackStrapNrb_R_001_high_geo', 5),
                         ('saddleFrontStrapNrb_L_001_high_geo', 5), ('saddleBackStrapNrb_L_001_high_geo', 5)
                         )

    COLLAR_SECONDARY_GEOMETRIES = (('saddleBaseNrb_R_001_high_geo', 16), ('saddleBaseNrb_L_001_high_geo', 16))

    REIGN_GEOMETRIES = (('reignFixedNrb_R_001_high_geo', 8), ('reignFixedNrb_L_001_high_geo', 8))
    REIGN_CONTROLS = ('reignFixed_R_0_default_loc', 'reignFixed_L_0_default_loc')

    REIGN_FREE_GEOMETRIES = ('reignsNrb_R_001_high_geo', 5), ('reignsNrb_L_001_high_geo', 5)
    REIGN_FREE_CONTROLS = ('reign_R_0_default_loc', 'reign_L_0_default_loc')

    COLLAR_GEOMETRIES = (('collarMain_R_001_high_geo', 5), ('collarMain_L_001_high_geo', 5))

    COLLAR_SPACES = ['C_bnd_chest_0_0_saddleJnt',
                     'C_bnd_neck_0_0_saddleJnt',
                     'saddleChestplateSaddle0_C_control_default_ctrl'
                     ]

    RIVET_SPACES = ['C_bnd_chest_0_0_saddleJnt', 'C_bnd_neck_0_0_saddleJnt']

    MODEL_PATH = r"X:\redgun_reg-6344\_library\assets\props\prp_saddleSyrax\mdl\_publish\reg_prp_saddleSyrax_mdl_v100_thz.mb"

    BUILD_FAKE_COLL = True

    def __init__(self):
        self.name = "saddleSyrax"

        self.ribbon = None
        self.straps = None
        self.collar = None
        self.reigns = None
        self.collar_secondaries = None

        self.ctls_objs_list = list()

        rig_path = data.get_rigging_main_dir(type="prop")

        super(SyraxSaddleRig, self).__init__(prop_name=self.name,
                                             rig_data_path=rig_path,
                                             model_path=self.MODEL_PATH,
                                             builder_path=None,
                                             root_jnt="C_bnd_spine_0_0_jnt",
                                             head_jnt="C_bnd_saddle_0_0_jnt",
                                             scale=5,
                                             build_bs=True,
                                             load_deformers=False,
                                             go_to_T_pose=False,
                                             load_ctls=True,
                                             load_skin=True,
                                             pre_build=self.saddle_syrax_pre_build,
                                             upgrade=self.saddle_syrax_upgrade,
                                             post_build=self.saddle_syrax_post_build
                                             )

    def saddle_syrax_pre_build(self):

        self.local_geos = []

        if self.SADDLE_TWEAKERS:
            tweakers = pm.createNode('transform', n='blendTargetsLocal_C_001_GRP')
            pm.parent(tweakers, self.base_module.no_transf_grp)

            for element in self.SADDLE_TWEAKERS:
                element = pm.PyNode(element)
                element_dup = pm.duplicate(element,
                                           n=element.name().replace("_high_", "_local_"))[0]

                pm.parent([element_dup], tweakers)
                pm.blendShape([element_dup], element, frontOfChain=True, weight=(0, 1))
                self.local_geos.append(element_dup)

        if self.TWEAKER_UPGRADE:

            self.upgraded_node = pm.duplicate('saddleBlankets_C_003_high_geo', n='masterTweaker_C_001_high_geo')[0]
            box_control_group = pm.createNode('transform', n='blendTargetsBox_C_001_GRP')
            pm.parent(self.upgraded_node, box_control_group)

            for element in self.TWEAKER_UPGRADE:
                element = pm.PyNode(element.replace("_high_", "_local_"))
                upgraded_name = element.replace("_local_", "_intermediate_")

                element_dup = pm.duplicate(element,
                                           n=upgraded_name)[0]

                pm.parent([element_dup],box_control_group)
                pm.blendShape([element_dup], element, frontOfChain=True, weight=(0, 1))

            pm.parent(box_control_group, self.base_module.no_transf_grp)

    def saddle_syrax_upgrade(self):

        #   builds the rivet
        self.strap_rivet_build()
        self.chestplate_rivet_build()

        #   builds the steering handles right now not in modular form yet
        self.steering_handles_build()

        #   builds the ribbons as multiple modules
        self.ribbon_build()
        self.straps_build()
        self.collar_build()
        self.collar_secondary_build()
        self.reigns_build()

        #   build the fake collisions
        self.fake_collision_build()

    def saddle_syrax_post_build(self):

        if self.TWEAKER_UPGRADE:
            object_master = self.upgraded_node
            object_slave = pm.PyNode('saddleBlankets_C_003_tweaker_geo')

            pm.blendShape(object_master,
                          object_slave,
                          frontOfChain=True,
                          weight=(0, 1)
                          )

            pcons.pxoparent(masters="saddleMainSaddle0_C_control_default_ctrl",
                            slaves=object_master,
                            maintainOffset=True,
                            native=False)

            self.dirtiest_collision_tweak_fix()

        # parenting the handles with the rivet joint
        for i in range(0, len(self.STEERING_HANDLES)):

            pcons.pxoparent(masters="saddleMainSaddle0_C_control_default_ctrl",
                            slaves=self.ctls_objs_list[i][0].off,
                            maintainOffset=True,
                            native=False)

        # parenting the handles with the rivet joint
        for i in self.reigns.prim_offs:
            pcons.pxoparent(masters="saddleMainSaddle0_C_control_default_ctrl",
                            slaves=i,
                            maintainOffset=True,
                            native=False
                            )

        reversed_handles = tuple(reversed(self.STEERING_HANDLES))

        for iteration, i in enumerate(self.straps.prim_offs):
            pcons.pxoparent(masters=reversed_handles[iteration+2][0],
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

        revnde = pm.createNode('reverse', n='visibilityReverse')

        vis_control.reigns.connect(fixed.visibility)
        vis_control.reigns.connect(fixed_module.visibility)

        vis_control.reigns.connect(revnde.inputX)

        revnde.outputX.connect(free.visibility)
        revnde.outputX.connect(free_module.visibility)

        pm.delete('skeleton_grp')



        #   setting visibilities on all elements in group
        modules_grp = pm.listRelatives('modules_GRP')

        for module in modules_grp:
            pm.setAttr('{}.extraElements_vis'.format(module), False)
            pm.setAttr('{}.noTransf_vis'.format(module), False)
            pm.setAttr('{}.joints_vis'.format(module), False)

    def steering_handles_build(self):
        """

        Returns:

        """
        self.ctls_objs_list = list()

        for jnt_list in self.STEERING_HANDLES:

            side = name.get_side(jnt_list[0], with_undescore=False)
            component = name.get_component(jnt_list[0], with_undescore=False)

            free_ctls_on = freeControls.FreeControls(name=component,
                                                     scale=5,
                                                     elements_list=jnt_list,
                                                     create_controls=True,
                                                     side=side,
                                                     make_jnt=False,
                                                     seperate_hierarchy=False,
                                                     base_module=self.base_module)

            ctls_objs = free_ctls_on.ctls_list
            handle_name = name.change_suffix(ctls_objs[0].ctl.name(), 'ikh')

            # creates an ik handle renames and re-parents it into the no-trans group
            ik_handle = pm.ikHandle(n=handle_name, sj=jnt_list[0], ee=jnt_list[-1])
            pm.rename(ik_handle[1], name.change_suffix(handle_name, 'eff'))
            pm.parent(ik_handle[0], free_ctls_on.module_base.noTransf_grp)

            # creates a pole-vector constraint, matches it with offset to the control so it works like single chain
            pole_vec_target = pm.createNode('transform', n=name.change_suffix(handle_name, 'pos'))
            pm.matchTransform(pole_vec_target, ctls_objs[0].ctl)
            pm.parent(pole_vec_target, ctls_objs[0].ctl)

            pole_vec_target.tz.set(2)

            # constraints the joint base and ik handle to the controls
            pcons.pxoparent(masters=ctls_objs[0].ctl, slaves=jnt_list[0])
            pcons.pxoparent(ctls_objs[-1].ctl, slaves=ik_handle[0])

            pm.poleVectorConstraint(pole_vec_target, ik_handle[0])

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

    def chestplate_rivet_build(self):
        vis_control = pm.PyNode('vis_C_control_default_ctrl')
        rivet = rivetControls.RivetControls(name="Chestplate",
                                            moving_mesh="chestplate_rivet_geo",
                                            dummies_rivet_grp="chestplate_rivet_grp",
                                            create_controls=True,
                                            seperate_hierarchy=True,
                                            base_module=self.base_module,
                                            controller_spaces=self.RIVET_SPACES,
                                            host=vis_control
                                            )
        for i in rivet.joint_output:
            dummy_name = i.name().replace('ChestplateChestplate',
                                          'ChestplateSaddle'
                                          )

            pm.rename(i, dummy_name)

        dummy_name = rivet.jointParent.name().replace('ChestplateChestplate',
                                                      'ChestplateSaddle'
                                                      )

        pm.rename(rivet.jointParent, dummy_name)

        geo_nde = pm.PyNode('chestplate_rivet_geo')
        pm.parent(geo_nde, self.base_module.no_transf_grp)
        #   asdf

    def ribbon_build(self):
        """ wraps the ribbon module and class to create a ribbon from information stated in this module

        Returns:
            ribbon(cls): class containing the ribbon info
        """
        self.ribbon = rib.Ribbon(geometry_info=self.RIBBON_GEOMETRIES,
                                 placements=(),
                                 component_name='ribbon',
                                 scale=self.scale,
                                 base_module=self.base_module
                                 )

        return self.ribbon

    def straps_build(self):
        """ wraps the ribbon module and class to create a ribbon from information stated in this module

        Returns:
            ribbon(cls): class containing the ribbon info
        """
        self.straps = rib.Ribbon(geometry_info=self.REIGN_GEOMETRIES,
                                 placements=self.REIGN_CONTROLS,
                                 component_name='reignFixed',
                                 scale=self.scale,
                                 base_module=self.base_module
                                 )

        return self.straps

    def collar_build(self):
        """ wraps the ribbon module and class to create a ribbon from information stated in this module

        Returns:
            ribbon(cls): class containing the ribbon info
        """
        vis_control = pm.PyNode('vis_C_control_default_ctrl')
        self.collar = rib.Ribbon(geometry_info=self.COLLAR_GEOMETRIES,
                                 placements=(),
                                 component_name='collar',
                                 scale=self.scale,
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
        self.reigns = rib.Ribbon(geometry_info=self.REIGN_FREE_GEOMETRIES,
                                 placements=self.REIGN_FREE_CONTROLS,
                                 component_name='reignFree',
                                 scale=self.scale,
                                 base_module=self.base_module
                                 )

        return self.reigns

    def collar_secondary_build(self):
        """ wraps the ribbon module and class to create a ribbon from information stated in this module

        Returns:
            ribbon(cls): class containing the ribbon info
        """
        self.collar_secondaries = rib.Ribbon(geometry_info=self.COLLAR_SECONDARY_GEOMETRIES,
                                             placements=(),
                                             component_name='collarSecondary',
                                             scale=self.scale,
                                             base_module=self.base_module
                                             )

        return self.collar_secondaries

    def fake_collision_build(self):
        """
        rivet_mod = rivetControls.RivetControls(
                                     name="frontPlate",
                                     scale=10.0,
                                     moving_mesh="fakeCollisionSupport_geo",
                                     dummies_rivet_grp="fake_collision_rivet_grp",
                                     create_controls=0,
                                     seperate_hierarchy=0,
                                     make_jnt=0,
                                     base_module=self.base_module
                                     )


        riv_nodes = rivet_mod.rivet_nodes
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
                                                      "_saddleJnt")
                                   )

                col_joints.append(jnt_nd)
                name_changed = rvt.name().replace("_start_default_rivFol", "_end_default_loc")

                if 'Collar' not in rvt.name():
                    pm.pointConstraint(rvt, jnt_nd, mo=True)
                    up_object = pm.createNode('transform', n='{}_upVec'.format(rvt.name()))
                    pm.matchTransform(up_object, rvt)

                    pm.parent(up_object, rvt)

                    up_object.translateX.set(1)

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
                                        mo=True
                                        )

        joints_grouped = pm.group(col_joints, n='fake_collision_jnts')
        pm.parent(joints_grouped, "skeleton_GRP")

        pm.parent('vectorCollision_GRP', "no_transf_GRP")
        pm.parent([fols_grouped], 'vectorCollision_GRP')

        pm.delete("fake_collision_rivet_grp")

    def dirtiest_collision_tweak_fix(self):
        """ this method removes the typical constraint that is created for tweaker nodes
        and appends the tweaker to the collision system to get faux dynamical collision follow

        Returns:
            True(Bool)
        """
        pm.delete('L_saddleEdgeMaster_folTOsaddleEdgeMaster0_L_control_default_offsetCtrl_prc')
        pcons.pxoparent(masters='fakeColl_L_1_start_default_saddleJnt',
                        slaves='saddleEdgeMaster0_L_control_default_offsetCtrl',
                        maintainOffset=True,
                        native=False
                        )

        pm.delete('R_saddleEdgeMaster_folTOsaddleEdgeMaster0_R_control_default_offsetCtrl_prc')
        pcons.pxoparent(masters='fakeColl_R_1_start_default_saddleJnt',
                        slaves='saddleEdgeMaster0_R_control_default_offsetCtrl',
                        maintainOffset=True,
                        native=False
                        )
        return True


def fake_collision_setup(mesh_node, transforms_in, transforms_out=None):
    """

    :param mesh_node:
    :param transforms_in:
    :param transforms_out:
    :return:
    """
    collision_master = pm.createNode('transform', n='collisionMaster_GRP')
    pm.parent(collision_master, "vectorCollision_GRP")

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


