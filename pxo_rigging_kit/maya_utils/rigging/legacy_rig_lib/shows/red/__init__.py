from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from . import vhagar_face_rig
from . import syrax_face_rig
from . import arrax_face_rig
from . import arrax_saddle_rig
from . import syrax_saddle_rig
from pxo_rigging_kit.maya_utils.rigging import legacy_rig_lib


# """
# Example:
#
# >>>    #shape_transfer
# >>>    import pymel.core as pm
# >>>    #pm.select(cl = 1)
# >>>    char_name = "vhagar"
# >>>    bs_geo = pm.PyNode("facialBS_geo")
# >>>    new_shape = pm.PyNode("{}Head_C_001_high_geo".format(char_name))
# >>>    bs = pm.PyNode("facial_BS")
# >>>    targets_array = pm.listAttr(bs.w,m=1)
# >>>    for t in targets_array:
# >>>        pm.setAttr("{}.{}".format(bs,t),0)
# >>>    #turn off bs to get the real node shape
# >>>    #pm.setAttr("{}.e".format(bs),0)
# >>>    extract_geo = pm.duplicate(bs_geo,n = "toExtract_geo")
# >>>    pm.parent(extract_geo, w = 1)
# >>>    #pm.setAttr("{}.e".format(bs),1)
# >>>    blend_shape_nd = pm.blendShape([new_shape,bs_geo], extract_geo, frontOfChain=True, weight=((0, 1),(1,1)))
# >>>    targets_array = pm.listAttr(bs.w,m=1)
# >>>    shapes_grp = pm.group(n = 'shapes_grp', em = 1)
# >>>    for i in range(len(targets_array)):
# >>>        pm.setAttr(bs.name() + "." + targets_array[i],1)
# >>>        dup = pm.duplicate(extract_geo, n = targets_array[i])
# >>>        pm.setAttr(bs.name() + "." + targets_array[i],0)
# >>>        pm.parent(dup,shapes_grp)
#
# >>>    #useful functions
# >>>    import pymel.core as pm
# >>>    import legacy_rig_lib.utils.data as dt
# >>>    reload(dt)
# >>>    #getting mainpath for saving purpouse
# >>>    main_path = dt.get_rigging_main_dir(type = "face")
# >>>    #create folder
# >>>    assets_path = r"X:\redgun_reg-6344\_library\assets\creature"
# >>>    asset_name = "crt_vermithor"
# >>>    dt.set_asset_folders(assets_path, asset_name,specific = "face" )
# >>>    import legacy_rig_lib.utils.joint as jnt
# >>>    jnts_list = jnt.get_joint_chain("C_bnd_spine_0_0_saddleJnt")
# >>>    import legacy_rig_lib.utils.constraints as const
# >>>    reload(const)
# >>>    const.connect_by_tag(jnts_list)
# >>>    import legacy_rig_lib.utils.tags as tags
# >>>    tags.tag_element(pm.selected(),"bodyRig")
# >>>    #place joints guides
# >>>    import legacy_rig_lib.modules.eye as eye
# >>>    eye.Eye.build_cage()
# >>>    eye.Eye.extract_joints("eye_L_cage_grp")
# >>>    import legacy_rig_lib.modules.eyelid as eyelid
# >>>    eyelid.Eyelid.build_cage()
# >>>    eyelid.Eyelid.extract_joints("eyelid_L_cage_grp")
# >>>    import legacy_rig_lib.modules.nose as nose
# >>>    nose.Nose.build_cage()
# >>>    nose.Nose.extract_joints("nose_C_cage_grp")
# >>>    #mirror bs dummies
# >>>    import legacy_rig_lib.modules.facialBS as fbs
# >>>    reload(fbs)
# >>>    fbs.FacialBS.mirror_ctl_dummies(pm.selected())
# >>>    fbs.FacialBS.fix_ctls_dummies()
# >>>    #mirror tweaker locators
# >>>    import legacy_rig_lib.modules.tweakers as twk
# >>>    twk.Tweakers.mirror_loc_dummies(pm.selected())
# >>>    #CTLS EXTRACT AND APPLY
# >>>    import legacy_rig_lib.utils.shape as sh
# >>>    reload(sh)
# >>>    #Extract
# >>>    sh.extract_ctrl_shapes()
# >>>    #extract for lod
# >>>    sh.extract_ctrl_shapes_for_LOD()
# >>>    #save ctrls for lod
# >>>    sh.save_ctl_shapes(main_path = main_path,
# >>>                        specific_path = None,
# >>>                        type = 'LOD')
# >>>    #load ctl shapes for lod
# >>>    sh.load_ctl_shapes(main_path = main_path,
# >>>                        type = 'LOD')
# >>>    #Mirror ctl shapes
# >>>    sh.mirror_ctl_shapes()
# >>>    #extract shapes
# >>>    sh.extract_ctrl_shapes()
# >>>    #apply
# >>>    sh.apply_ctrl_shapes()
# >>>    #save ctl shapes
# >>>    sh.save_ctl_shapes(main_path = main_path,
# >>>                        specific_path = None)
# >>>    #load ctl shapes
# >>>    sh.load_ctl_shapes(main_path = main_path,
# >>>                        specific_path = None,
# >>>                        apply = 0)
# >>>    import legacy_rig_lib.utils.pixoSkin as pSkin
# >>>    reload(pSkin)
# >>>    path = r"{}/data/skincluster".format(main_path)
# >>>    pSkin.pixo_export_skin (path = path,objects = pm.selected())
# >>>    sel = pm.selected()
# >>>    for e in sel[1:]:
# >>>        pSkin.ngSkin2_transfer_weights(sel[0], e)
# >>>    pSkin.pixo_export_skin (path = "C:\Users\michele.trabona\Desktop\New Folder",objects = pm.selected())
# >>>    pSkin.pixo_import_skin("X:/redgun_reg-6344/_library/assets/creature/crt_vhagar/rig_face\\data\\skincluster")
#
# """
