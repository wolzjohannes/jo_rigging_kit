from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from builtins import dict
from future import standard_library
standard_library.install_aliases()
def adapt_controls():
    axis = ['X', 'Y', 'Z']
    # Organise top node
    asset_geo_roots = [x for x in pm.ls(transforms=True) if pm.objExists('{}.PXM_asset_geo_root'.format(x))]
    if not asset_geo_roots or len(asset_geo_roots) > 1:
        raise ValueError

    asset_geo_root = asset_geo_roots[0]
    asset_name = asset_geo_root.split('_')[-2]
    asset_type = asset_geo_root.split('_')[0].split(':')[-1]

    rig_group = pm.PyNode('mgear_rig_grp')
    global_control = pm.PyNode('global_0_default_ctrl')
    vis_control = pm.PyNode('visibility_C_0_control_default_ctrl')

    asset_group = pm.group(n='{}_{}_rig'.format(asset_type, asset_name), em=True)
    pm.parent(rig_group, asset_group)
    pm.parent(asset_geo_root, asset_group)

    # Global ctrl main scale attribute and lock & hide scale channels
    global_control.addAttr('main_scale',
                           at='double',
                           min=0.001,
                           hnv=True,
                           dv=1,
                           k=True)

    for x in axis:
        global_control.main_scale.connect(global_control.attr('scale{}'.format(x)))
        global_control.attr('scale{}'.format(x)).set(lock=True,
                                                     k=False,
                                                     channelBox=False)

    # Connect attributes for geo, ctl and joint visibility
    for x in axis:
        vis_control.attr('translate{}'.format(x)).set(lock=True, keyable=False)
        vis_control.attr('rotate{}'.format(x)).set(lock=True, keyable=False)
        vis_control.attr('scale{}'.format(x)).set(lock=True, keyable=False)
    vis_control.rotateOrder.set(lock=True, keyable=False)

    vis_control.addAttr('model_display_type', at='enum', dv=2, enumName='normal:template:reference')
    vis_control.model_display_type.set(cb=True)

    vis_control.addAttr('mgear_jnt_vis', at='bool', keyable=False)
    vis_control.mgear_jnt_vis.set(False, cb=True)
    vis_control.addAttr('mgear_ctl_vis', at='bool', keyable=False)
    vis_control.mgear_ctl_vis.set(True, cb=True)
    vis_control.addAttr('mgear_ctl_vis_on_playback', at='bool', keyable=False)
    vis_control.mgear_ctl_vis_on_playback.set(False, cb=True)
    vis_control.addAttr('mgear_ctl_x_ray', at='bool', keyable=False)
    vis_control.mgear_ctl_x_ray.set(False, cb=True)

    vis_control.mgear_jnt_vis.connect(rig_group.jnt_vis)
    vis_control.mgear_ctl_vis.connect(rig_group.ctl_vis)
    vis_control.mgear_ctl_vis_on_playback.connect(rig_group.ctl_vis_on_playback)
    vis_control.mgear_ctl_x_ray.connect(rig_group.ctl_x_ray)

    asset_geo_root.overrideEnabled.set(True)
    vis_control.model_display_type.connect(asset_geo_root.drawOverride.overrideDisplayType)

    # connect geos
    complexity_groups = asset_geo_root.getChildren()
    naming_decomposition = dict()

    complexity_levels = [x.getChildren()[0] for x in complexity_groups]
    for i in complexity_levels:
        geometry_groups = [(x.shortName().split(':')[-1], x) for x in i.getChildren()]
        naming_decomposition[i.shortName().split(':')[-1]] = geometry_groups
    for key, value in list(naming_decomposition.items()):
        vis_control.addAttr(key, at='enum', enumName='xxxxxxxxxxxx', keyable=False)
        vis_control.attr(key).set(lock=True, cb=True)
        for v in value:
            vis_control.addAttr(v[0], at='bool', dv=True, keyable=False)
            vis_control.attr(v[0]).set(True, cb=True)
            vis_control.attr(v[0]).connect(v[1].visibility)

    # Rename sets
    pm.rename('mgear_rig_grp_sets_grp', 'pxm_rig_root_set')
    pm.rename('mgear_rig_grp_componentsRoots_grp', 'components_root_set')
    pm.rename('mgear_rig_grp_controllers_grp', 'controllers_set')
    pm.rename('mgear_rig_grp_deformers_grp', 'deformers_set')

    pm.select(cl=True)
    pm.viewFit()