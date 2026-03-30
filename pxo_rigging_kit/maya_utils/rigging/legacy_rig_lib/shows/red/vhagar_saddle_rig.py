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

# internal libraries
from ...systems import saddleSystem
from ...modules import pxoik as pik
from ...modules import rivetControls
from ...modules import ribbon as rib

from ...utils import data
from ...utils import name
from ...utils import constraints as pcons
from ...utils import transform

standard_library.install_aliases()


class VhagarSaddleRig(saddleSystem.Saddle_system):

    STEERING_HANDLES = (("steeringHandle_L_0_bind_default_saddleJnt",
                        "steeringHandle_L_1_bind_default_saddleJnt"),
                        ("steeringHandle_R_0_bind_default_saddleJnt",
                        "steeringHandle_R_1_bind_default_saddleJnt"),
                        ("footrestHandle_L_0_bind_default_saddleJnt",
                        "footrestHandle_L_1_bind_default_saddleJnt"),
                        ("footrestHandle_R_0_bind_default_saddleJnt",
                        "footrestHandle_R_1_bind_default_saddleJnt"),
                        ('reign_L_0_bind_default_saddleJnt',
                         'reign_L_2_bind_default_saddleJnt'),
                        ('reign_R_0_bind_default_saddleJnt',
                         'reign_R_2_bind_default_saddleJnt'))

    SADDLE_TWEAKERS = []

    RIBBON_GEOMETRIES = (('backStrap_R_001_high_geo', 5), ('backStrap_L_001_high_geo', 5),
                         ('backStrapBack_R_002_high_geo', 5), ('backStrapBack_L_002_high_geo', 5),
                         ('frontBottomStrap_R_001_high_geo', 5), ('frontBottomStrap_L_001_high_geo', 5),
                         ('backBottomStrap_R_001_high_geo', 5), ('backBottomStrap_L_001_high_geo', 5),
                         ('frontLowerBackStrap_R_001_high_geo', 4), ('frontLowerBackStrap_L_001_high_geo', 4),
                         ('frontLowerFrontStrap_R_001_high_geo', 4), ('frontLowerFrontStrap_L_001_high_geo', 4),
                         ('frontInnerStrap_R_001_high_geo', 3), ('frontInnerStrap_L_001_high_geo', 3),
                         ('frontOutterStrap_R_001_high_geo', 3), ('frontOutterStrap_L_001_high_geo', 3),
                         ('sideRope_L_001_high_geo', 3), ('sideRope_R_001_high_geo', 3),
                         ('centerStrap_C_001_high_geo', 4), ('frontStrings_C_001_high_geo', 4),
                         ('sideStrings_R_001_high_geo', 4), ('sideStrings_L_001_high_geo', 4)
                         )

    RIBBON_MAIN_GEOMETRIES = (('backMaster_R_001_high_geo', 4), ('backMaster_L_001_high_geo', 4),
                              ('frontStrap_R_001_high_geo', 5), ('frontStrap_L_001_high_geo', 5),
                              ('backWing_R_001_high_geo', 5), ('backWing_L_001_high_geo', 5),
                              ('sideWing_L_001_high_geo', 4), ('sideWing_R_001_high_geo', 4),
                              ('frontMaster_R_001_high_geo', 6), ('frontMaster_L_001_high_geo', 6)
                              )

    REIGN_GEOMETRIES = [('reignToplevel_C_001_high_geo', 7)]
    REIGN_CONTROLS = ['reign_C_0_loc']

    REIGN_MID_GEOMETRIES = [('reignMidlevel_C_001_high_geo', 18)]

    REIGN_FIXED_GEOMETRIES = [('reignsFixedMain_C_001_high_geo', 18)]
    REIGN_FIXED_CONTROLS = ['reignFixed_C_0_loc']


    MODEL_PATH = r"X:\redgun_reg-6344\_library\assets\props\prp_saddleVhagar\mdl\_publish\reg_prp_saddleVhagar_mdl_v062_vat.mb"

    BUILD_FAKE_COLL = False

    def __init__(self):
        self.name = "saddleVhagar"

        rig_path = data.get_rigging_main_dir(type="prop")
        build_path = data.get_rigging_main_dir(type="prop")

        super(VhagarSaddleRig, self).__init__(prop_name=self.name,
                                              rig_data_path=rig_path,
                                              model_path=self.MODEL_PATH,
                                              builder_path=None,
                                              root_jnt="C_bnd_spine_0_2_jnt",
                                              head_jnt="C_bnd_saddle_0_0_jnt",
                                              scale=5,
                                              build_bs=True,
                                              load_deformers=False,
                                              go_to_T_pose=False,
                                              load_ctls=True,
                                              load_skin=True,
                                              pre_build=self.saddle_vhagar_pre_build,
                                              upgrade=self.saddle_vhagar_upgrade,
                                              post_build=self.saddle_vhagar_post_build)

        self.ribbon = None
        self.ribbon_prim_ctrl_offs = None

        self.ribbon_main = None

        self.reign = None
        self.reign_mid = None

        self.reign_fixed = None

        self.ik_tip_offsets = list()
        self.fk_base_offsets = list()
        self.ctls_objs_list = list()

    def saddle_vhagar_pre_build(self):

        if self.SADDLE_TWEAKERS:
            for element in self.SADDLE_TWEAKERS:
                element = pm.PyNode(element)
                element_dup = pm.duplicate(element,
                                           n=element.name().replace("_high_", "_local_"))[0]

                pm.parent([element_dup], self.base_module.no_transf_grp)

    def saddle_vhagar_upgrade(self):
        self.strap_rivet_build()
        self.steering_handles_build()

        #   ribbons build
        self.ribbon_build()
        self.ribbon_main_build()

        self.reign_build()
        self.reign_mid_build()

        self.reign_fixed_build()

    def saddle_vhagar_post_build(self):

        pcons.pxoparent(masters="saddleMainSaddle0_C_control_default_ctrl",
                        slaves=self.fk_base_offsets[:-2], maintainOffset=True, native=False)

        pcons.pxoparent(masters=self.reign_fixed.prim_ctls[0].ctl,
                        slaves=self.ik_tip_offsets[-2:], maintainOffset=True, native=False)

        pcons.pxoparent(masters="saddleMainSaddle0_C_control_default_ctrl",
                        slaves=self.reign.prim_offs, maintainOffset=True, native=False)

        reign_fixtures = ['strapStrap4_L_control_default_ctrl', 'strapStrap5_R_control_default_ctrl']
        for iteration, item in enumerate(reign_fixtures):
            pcons.pxoparent(masters=item,
                            slaves=self.fk_base_offsets[-2:][iteration], maintainOffset=True, native=False)

        pcons.pxoparent(masters="saddleMainSaddle0_C_control_default_ctrl",
                        slaves=self.reign_fixed.prim_offs, maintainOffset=True, native=False)

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

        fixed_modules = [pm.PyNode('reignreign_R_module_GRP'),
                         pm.PyNode('reignreign_L_module_GRP'),
                         pm.PyNode('reignFixed_C_module_GRP'),
                         pm.PyNode('saddleReinsLose_C_high_grp')]

        free_modules = [pm.PyNode('reign_C_module_GRP'),
                        pm.PyNode('reignMid_C_module_GRP'),
                        pm.PyNode('saddleReins_C_high_grp')]

        revnde = pm.createNode('reverse', n='visibilityReverse')

        for nde in fixed_modules:
            vis_control.reigns.connect(nde.visibility)

        vis_control.reigns.connect(revnde.inputX)

        for nde in free_modules:
            revnde.outputX.connect(nde.visibility)

        #   Turn off module vis
        modules_grp = pm.listRelatives('modules_GRP')

        for module in modules_grp:
            pm.setAttr('{}.extraElements_vis'.format(module), False)
            pm.setAttr('{}.noTransf_vis'.format(module), False)
            pm.setAttr('{}.joints_vis'.format(module), False)

        pm.setAttr("vis_C_control_default_ctrl.jointsVis", False)
        pm.delete('skeleton_grp')

        '''
        sel = pm.ls("*_local_geo", "*_tweaker_geo")
        for e in sel:
            connections_dest = pm.listConnections("{}.worldMesh[0]".format(e), d=1)
            for con in connections_dest:
                if pm.nodeType(con) == "blendShape":
                    pm.delete(con)

            if "_tweaker_" in e.name():
                high_shapes = pm.listRelatives(e.name().replace("_tweaker_", "_high_"), shapes=1)
            else:
                high_shapes = pm.listRelatives(e.name().replace("_local_", "_high_"), shapes=1)
            for sh in high_shapes:
                if sh.name().endswith("Orig"):
                    # finding the last shape node
                    local_shapes = pm.listRelatives(e.name(), shapes=1)
                    for loc_sh in local_shapes:
                        if pm.getAttr("{}.intermediateObject".format(loc_sh)) == 0:
                            mesh_to_connect = loc_sh

                    pm.connectAttr("{}.worldMesh[0]".format(mesh_to_connect),
                                   "{}.inMesh".format(sh))
       '''

    def steering_handles_build(self):
        self.ctls_objs_list = list()
        self.fk_base_offsets = list()
        self.ik_tip_offsets = list()

        if not self.STEERING_HANDLES:
            return None

        for jnt_list in self.STEERING_HANDLES:
            module_name = name.get_component(jnt_list[0], with_undescore=False)
            dumb_module_name = module_name * 2
            ik_build = pik.IkSystem(main_ctl_offset=False,
                                    ik_base=jnt_list[0],
                                    scale=1,
                                    base_module=self.base_module,
                                    component=dumb_module_name,
                                    stretch=True)

            start_and_end = (ik_build.ctl_objs['start'], ik_build.ctl_objs['end'])
            self.ctls_objs_list.append(start_and_end)
            self.fk_base_offsets.append(ik_build.ctl_objs['start'].off)
            self.ik_tip_offsets.append(ik_build.ctl_objs['end'].off)

    def strap_rivet_build(self):
        rivetControls.RivetControls(name="Strap",
                                    moving_mesh="strap_rivet_geo",
                                    dummies_rivet_grp="strap_rivet_grp",
                                    create_controls=True,
                                    seperate_hierarchy=True,
                                    base_module=self.base_module)

        geo_nde = pm.PyNode('strap_rivet_geo')
        pm.parent(geo_nde, self.base_module.no_transf_grp)

    def ribbon_build(self):
        """ wraps the ribbon module and class to create a ribbon from information stated in this module

        Returns:
            ribbon(cls): class containing the ribbon info
        """
        self.ribbon = rib.Ribbon(geometry_info=self.RIBBON_GEOMETRIES,
                                 placements=(),
                                 scale=self.scale,
                                 component_name='ribbonDetail',
                                 base_module=self.base_module
                                 )

        return self.ribbon

    def ribbon_main_build(self):
        """ wraps the ribbon module and class to create a ribbon from information stated in this module

        Returns:
            ribbon(cls): class containing the ribbon info
        """
        self.ribbon_main = rib.Ribbon(geometry_info=self.RIBBON_MAIN_GEOMETRIES,
                                      placements=(),
                                      component_name='ribbonMain',
                                      scale=self.scale,
                                      base_module=self.base_module
                                      )

        return self.ribbon_main

    def reign_build(self):
        """ wraps the ribbon module and class to create a ribbon from information stated in this module

        Returns:
            ribbon(cls): class containing the ribbon info
        """
        self.reign = rib.Ribbon(geometry_info=self.REIGN_GEOMETRIES,
                                placements=self.REIGN_CONTROLS,
                                component_name='reign',
                                scale=self.scale,
                                base_module=self.base_module
                                )

        return self.reign

    def reign_mid_build(self):
        """ wraps the ribbon module and class to create a ribbon from information stated in this module

        Returns:
            ribbon(cls): class containing the ribbon info
        """
        self.reign_mid = rib.Ribbon(geometry_info=self.REIGN_MID_GEOMETRIES,
                                    placements=(),
                                    component_name='reignMid',
                                    scale=self.scale,
                                    base_module=self.base_module
                                    )

        return self.reign_mid

    def reign_fixed_build(self):
        """ wraps the ribbon module and class to create a ribbon from information stated in this module

        Returns:
            ribbon(cls): class containing the ribbon info
        """
        self.reign_fixed = rib.Ribbon(geometry_info=self.REIGN_FIXED_GEOMETRIES,
                                      placements=self.REIGN_FIXED_CONTROLS,
                                      component_name='reignFixed',
                                      scale=self.scale,
                                      base_module=self.base_module
                                      )

        return self.reign_fixed

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

                else:
                    pm.pointConstraint(pm.PyNode(name_changed), jnt_nd, mo=True)

                if 'Collar' not in rvt.name():
                    tip_rvt = pm.PyNode(name_changed)
                    aim_constraint = pm.aimConstraint(tip_rvt,
                                                      jnt_nd,
                                                      weight=1,
                                                      aimVector=[1, 0, 0],
                                                      upVector=[0, 1, 0],
                                                      mo=True)  # worldUpObject = up_obj,worldUpType = "object"

        joints_grouped = pm.group(col_joints, n='fake_collision_jnts')
        pm.parent(joints_grouped, "no_transf_GRP")

        pm.parent('vectorCollision_GRP', "no_transf_GRP")
        pm.parent([locator_grouped, fols_grouped, joints_grouped],'vectorCollision_GRP')

        pm.delete("fake_collision_rivet_grp")


def fake_collision_setup(mesh_node, transforms_in, transforms_out=None):

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

        #   checking the dot product and applying the right position val
        condition = pm.createNode("condition")
        pm.connectAttr("{}.output".format(dot_node),
                       "{}.firstTerm".format(condition))
        pm.connectAttr("{}.output".format(translate_from_mat),
                       "{}.colorIfFalse".format(condition))
        pm.connectAttr("{}.position".format(cls_point),
                       "{}.colorIfTrue".format(condition))
        pm.setAttr("{}.operation".format(condition),4)

        if transforms_out:
            if len(transforms_in) == len(transforms_out):
                pm.connectAttr("{}.outColor".format(condition),
                               "{}.translate".format(transforms_out[it]))

            else:
                print('ERROR')


if __name__ == "__main__":
    import pymel.core as pm
    import importlib
    import rig_lib.shows.red.vhagar_saddle_rig as vhaSadRig

    importlib.reload(vhaSadRig)

    vhaSadRig.VhagarSaddleRig()
