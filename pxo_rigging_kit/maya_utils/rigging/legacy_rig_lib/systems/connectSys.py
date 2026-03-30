
"""
www.pixomondo.com
Date: 19 / 02 / 2022

connectSys module
category : Rigging
subcategory : systems
author : Michele Trabona / Rigging TD

"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from future import standard_library

standard_library.install_aliases()
from builtins import object
from pymel.core import datatypes

from ..utils import data
from ..utils import joint
from ..utils import constraints
from ..utils import transform
import pymel.core as pm
import os


class SystemsConnection(object):
    def __init__(self,
                 rig_lod = None,
                 body_rig_path = None,
                 face_rig_path = None):
        print('-- START BUILDING PROCESS--')
        start = pm.timerX()

        if face_rig_path == None:
            face_main_rig_dir = data.get_rigging_main_dir()
            face_main_rig_dir = "{}/{}".format(face_main_rig_dir,
                                               "work_scenes")
            file_name = data.get_all_latest_versions(path=face_main_rig_dir)[-1]
            face_rig_path = "{}/{}".format(face_main_rig_dir,
                                               file_name)
        if body_rig_path == None:
            rig_two_dir = data.get_rigging_main_dir(type ="lod2")
            file_name = data.get_all_latest_versions(path=rig_two_dir)[-1]
            body_rig_path = "{}/{}".format(rig_two_dir,
                                           file_name
                                           )

        # New Scene
        if body_rig_path:
            if os.path.isfile(body_rig_path):
                pm.newFile(force=True)

        # Import face rig
        if face_rig_path:
            if os.path.isfile(body_rig_path):
                pm.importFile(face_rig_path)

        # Import body version two
        if body_rig_path:
            pm.importFile(body_rig_path)

        if rig_lod == 3:
            # delete all the useless ctrls (Johanness script)
            # delete model
            SystemsConnection.connect_rigs(rig_lod)
        elif rig_lod == 4:
            # connect bs and skeleton
            SystemsConnection.connect_rigs(rig_lod)


        totalTime = pm.timerX(startTime=start)
        print('-- BUILDING PROCESS END --')
        print(('Total time: ', totalTime))

    @staticmethod
    def connect_rigs(rig_lod,root_jnt = "C_bnd_neck_0_0_faceJnt"):

        main_rig_grp = pm.ls("*_*_rig")[0]
        char_name = main_rig_grp.name().split("_")[1]
        face_rig_grp = pm.PyNode("{}_faceRig_GRP".format(char_name))
        main_face_rig_ctl = None
        second_face_rig_ctl = None
        slow_model_grp = None
        connection_list = pm.listConnections(
                            "{}.message".format(face_rig_grp),
                            d=1)
        for nd in connection_list:
            if "global" in nd.name().split("|")[-1]:
                main_face_rig_ctl = nd
            elif "main" in nd.name().split("|")[-1]:
                second_face_rig_ctl = nd
            elif "slow_model" in nd.name().split("|")[-1]:
                slow_model_grp = nd
        main_rig_ctl = pm.PyNode("global_0_default_ctrl")
        # hiding the groups and connecting the scale
        for ctl in [main_face_rig_ctl,second_face_rig_ctl]:
            shapes_list = pm.listRelatives(ctl,s = 1)
            for sh in shapes_list:
                pm.setAttr("{}.v".format(sh),0)
        pm.connectAttr("{}.main_scale".format(main_rig_ctl),
                       "{}.sx".format(main_face_rig_ctl))
        # parenting the main grp
        face_rig_parent = None
        if pm.objExists("xtra_rig_components_grp"):
            face_rig_parent = pm.PyNode("xtra_rig_components_grp")
        else:
            face_rig_parent = pm.group(n = "xtra_rig_components_grp",
                                       em = 1,parent= main_rig_grp)
        pm.parent(face_rig_grp,face_rig_parent)
        #connecting the face to main rig
        joints_list = joint.get_joint_chain(root_jnt)
        constraints.connect_by_tag(joints_list)

        if rig_lod in [3, 4]:
            """
            local_face_nd = pm.PyNode("face_local_geo")
            global_body_nd = pm.ls("{}Body*_geo".format(char_name))[0]
            pm.blendShape([local_face_nd],global_body_nd,
                          frontOfChain =1,tc = 0,
                          weight=(0, 1), n = "faceRig_def_bs")
            pm.setAttr("vis_C_control_default_ctrl.modelVis",0)
            """
            #head_geo_node = pm.ls("{}Head*_geo".format(char_name))[0]
            if rig_lod == 4:
                pm.hide(slow_model_grp)
            # connecting geos with bsConnection tag

            all_model_transf = pm.listRelatives(
                "geo_grp",
                ad=1,
                type="transform"
            )
            constraints.connect_by_tag(all_model_transf)

        #adding ctrls to set
        hierarchy = pm.listRelatives(face_rig_grp, ad=1, type="transform")
        ctls = []
        for obj in hierarchy:
            if hasattr(obj, 'rig_ctrl'):
                ctls.append(obj)
        pm.sets("controllers_set", add=ctls)
        #removing extra delete set
        sets_list = pm.ls(sets=1)
        for s in sets_list:
            if "delete_on_publish" in s.name() and "_rig_face" in s.name():
                pm.delete(s)


    @staticmethod
    def get_facial_ctls():

        face_main_rig_dir = data.get_rigging_main_dir()
        face_main_rig_dir = "{}/{}".format(face_main_rig_dir,
                                           "controlShapes")
        file_name = data.get_all_latest_versions(path=face_main_rig_dir)[-1]
        ctls_rig_path = "{}/{}".format(face_main_rig_dir,
                                           file_name)

        # Import face rig
        if os.path.isfile(ctls_rig_path):
            pm.importFile(ctls_rig_path)

        main_rig_grp = pm.ls("*_*_rig")[0]
        #parenting the main grp
        face_rig_parent = None
        if pm.objExists("xtra_rig_components_grp"):
            face_rig_parent = pm.PyNode("xtra_rig_components_grp")
        else:
            face_rig_parent = pm.group(n = "xtra_rig_components_grp",
                                       em = 1,parent= main_rig_grp)

        ctrl_shapes_grp = pm.PyNode("control_shapes_grp")
        ctl_shapes = pm.listRelatives(ctrl_shapes_grp,
                                      c = 1,
                                      type = "transform")
        for ctl_shape in ctl_shapes:
            pm.rename(ctl_shape,
                      ctl_shape.name().replace("shape_",
                                               ""))
            transform.make_extra_buffer(ctl_shape,
                                      "zeroTransf",
                                        buffer_number=1,
                                        move_to=1)
            for at in ["t", "s", "r"]:
                for spec_at in ["x", "y", "z"]:
                    at_name = at + spec_at
                    pm.setAttr("{}.{}".format(ctl_shape.name(), at_name),
                               k=1, l=0, cb=1)
                    pm.setAttr("{}.{}".format(ctl_shape.name(), at_name),
                               k=1)
        pm.rename(ctrl_shapes_grp, "facial_rig_ctls_grp")
        pm.parent(ctrl_shapes_grp,face_rig_parent)


class SystemsGenericConnection(object):
    def __init__(self,
                 rig_lod = None,
                 main_rig_path = None,
                 second_rig_path = None,
                 second_rig_element = None,
                 json_file = ""):
        print('-- START BUILDING PROCESS--')
        start = pm.timerX()

        if second_rig_path == None:
            face_main_rig_dir = data.get_rigging_main_dir()
            face_main_rig_dir = "{}/{}".format(face_main_rig_dir,
                                               "work_scenes")
            file_name = data.get_all_latest_versions(path=face_main_rig_dir)[-1]
            face_rig_path = "{}/{}".format(face_main_rig_dir,
                                               file_name)
        if main_rig_path == None:
            rig_two_dir = data.get_rigging_main_dir(type ="lod2")
            file_name = data.get_all_latest_versions(path=rig_two_dir)[-1]
            main_rig_path = "{}/{}".format(rig_two_dir,
                                               file_name)

        # New Scene
        if main_rig_path:
            if os.path.isfile(main_rig_path):
                pm.newFile(force=True)

        # Import face rig
        if face_rig_path:
            if os.path.isfile(body_rig_path):
                pm.importFile(face_rig_path)

        # Import body version two
        if main_rig_path:
            pm.importFile(main_rig_path)

        if rig_lod == 3:
            #delete all the useless ctrls (Johanness script)
            #delete model
            SystemsConnection.connect_rigs(rig_lod, second_rig_element)
        elif rig_lod == 4:
            #connect bs and skeleton
            SystemsConnection.connect_rigs(rig_lod, second_rig_element)


        totalTime = pm.timerX(startTime=start)
        print('-- BUILDING PROCESS END --')
        print(('Total time: ', totalTime))

    @staticmethod
    def connect_rigs(second_rig_element,rig_lod = None,root_jnt = "C_bnd_neck_0_0_faceJnt"):

        main_rig_grp = pm.ls("rig_root_grp")[0]
        char_name = pm.ls("crt_*_rig")[0].name().split("_")[1]
        gen_rig_grp = pm.PyNode("::*{}*_{}_GRP".format(char_name[:1].upper(),
                                                    second_rig_element))
        main_face_rig_ctl = None
        #main_face_rig_ctl = pm.PyNode("global_C_control_default_ctrl")
        second_face_rig_ctl = None
        connection_list = pm.listConnections(
                            "{}.message".format(gen_rig_grp),
                            d=1)
        for nd in connection_list:
            if "global" in nd.name().split("|")[-1]:
                main_face_rig_ctl = nd
            elif "main" in nd.name().split("|")[-1]:
                second_face_rig_ctl = nd
        main_rig_ctl = pm.PyNode("global_0_default_ctrl")
        #hiding the groups and connecting the scale
        for ctl in [main_face_rig_ctl,second_face_rig_ctl]:
            shapes_list = pm.listRelatives(ctl,s = 1)
            for sh in shapes_list:
                pm.setAttr("{}.v".format(sh),0)
        pm.connectAttr("{}.sx".format(main_rig_ctl),
                       "{}.sx".format(main_face_rig_ctl), f =1)
        #parenting the main grp
        face_rig_parent = None
        if pm.objExists("xtra_rig_components_grp"):
            face_rig_parent = pm.PyNode("xtra_rig_components_grp")
        else:
            face_rig_parent = pm.group(n = "xtra_rig_components_grp",
                                       em = 1,parent= main_rig_grp)
        pm.parent(gen_rig_grp,face_rig_parent)
        #connecting the face to main rig
        joints_list = joint.get_joint_chain(root_jnt)
        constraints.connect_by_tag(joints_list)

        #adding ctrls to set
        hierarchy = pm.listRelatives(gen_rig_grp, ad=1, type="transform")
        ctls = []
        for obj in hierarchy:
            if hasattr(obj, 'rig_ctrl'):
                ctls.append(obj)
        try:
            pm.sets("controllers_set", add=ctls)
        except:
            pass
        #removing extra delete set
        sets_list = pm.ls(sets=1)
        for s in sets_list:
            if "delete_on_publish" in s.name() and second_rig_element in s.name():
                pm.delete(s)


    @staticmethod
    def get_gen_ctls(second_rig_path,second_rig_element):

        second_rig_path = data.get_rigging_main_dir()
        second_rig_path = "{}/{}".format(face_main_rig_dir,
                                           "controlShapesLOD")
        file_name = data.get_all_latest_versions(path=second_rig_path)[-1]
        ctls_rig_path = "{}/{}".format(second_rig_path,
                                           file_name)

        # Import face rig
        if os.path.isfile(ctls_rig_path):
            pm.importFile(ctls_rig_path)

        main_rig_grp = pm.ls("*_*_rig")[0]
        #parenting the main grp
        gen_rig_parent = None
        if pm.objExists("xtra_rig_components_grp"):
            gen_rig_parent = pm.PyNode("xtra_rig_components_grp")
        else:
            gen_rig_parent = pm.group(n = "xtra_rig_components_grp",
                                       em = 1,parent= main_rig_grp)

        ctrl_shapes_grp = pm.PyNode("control_shapes_grp")
        ctl_shapes = pm.listRelatives(ctrl_shapes_grp,
                                      c = 1,
                                      type = "transform")
        for ctl_shape in ctl_shapes:
            pm.rename(ctl_shape,
                      ctl_shape.name().replace("shape_",
                                               ""))
            transform.make_extra_buffer(ctl_shape,
                                      "zeroTransf",
                                        buffer_number=1,
                                        move_to=1)
            for at in ["t", "s", "r"]:
                for spec_at in ["x", "y", "z"]:
                    at_name = at + spec_at
                    pm.setAttr("{}.{}".format(ctl_shape.name(), at_name),
                               k=1, l=0, cb=1)
                    pm.setAttr("{}.{}".format(ctl_shape.name(), at_name),
                               k=1)
        pm.rename(ctrl_shapes_grp, "{}_ctls_grp".format(second_rig_element))
        pm.parent(ctrl_shapes_grp,gen_rig_parent)

"""
import legacy_rig_lib.systems.connectSys as cns
reload(cns)


cns.Systems_generic_connection.connect_rigs("propRig", root_jnt = "C_bnd_spine_0_0_saddleJnt")
cns.Systems_connection.connect_rigs(rig_lod = 4)

"""