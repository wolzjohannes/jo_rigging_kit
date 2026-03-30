
#www.pixomondo.com
#Date: 08 / 02 / 2022

#baseSystem module
#category : Rigging
#subcategory : systems
#author : Michele Trabona / Rigging TD





#basic class to make rigging system

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import object
import pymel.core as pm
import os

from ..base import baseModule
from ..utils import data
from ..utils import pixoSkin
from ..utils import shape
from ..utils import cleanup


class Base_system(object):
    def __init__(self,
                 character_name="new",
                 rig_data_path=None,
                 model_path=None,
                 builder_path=None,
                 root_jnt=None,
                 head_jnt=None,
                 scale=1.0,
                 load_skin=False,
                 load_deformers=False,
                 load_ctls=False,
                 go_to_T_pose=False,
                 type="body"):

        """
        It Is the starter class for the System builds.

        Args:
            character_name(str): The name we will insert
                on the base module name.
            model_path(str): Model path directory.
            builder_path(str):  Builder path directory.
            root_jnt(pm.PyNode(),str): The root joint
                that will be used for the skeleton connections.
            head_jnt(pm.PyNode(),str): The head joint
                that will be used to snap the visibility control.
            scale(float): The scale value which will be applied
                on all the modules.
            load_skin(bool): It lets the user to choose if the
                skin will or will not be loaded.
            load_deformers(bool):It lets the user to choose if the
                deformers will or will not be loaded.
            go_to_T_pose(bool):It lets the user to choose if the
                pose will or will not be applied before the
                control creation.
        Return:
            None.

        """
        self.character_name = character_name
        self.rig_data_path = rig_data_path
        self.model_path = model_path
        self.builder_path = builder_path
        self.root_jnt = root_jnt
        self.head_jnt = head_jnt
        self.scale = scale
        self.load_skin = load_skin
        self.load_deformers = load_deformers
        self.go_to_T_pose = go_to_T_pose
        self.type = type

        print('-- START BUILDING PROCESS--')
        start = pm.timerX()

        #   get the latest file version
        if builder_path is None:
            if rig_data_path:
                path_ext = "{}/{}".format(rig_data_path,
                                          "builder")
                file_name = data.get_all_latest_versions(path=path_ext)[-1]
                builder_path = "{}\{}".format(path_ext,
                                              file_name)
        if model_path is None:
                mdl_dir = data.get_model_dir()
                file_name = data.get_all_latest_versions(path=mdl_dir)[-1]
                model_path = "{}/{}".format(mdl_dir,
                                            file_name)

        # New Scene
        if builder_path:
            if os.path.isfile(builder_path):
                pm.newFile(force=True)

        # Import model
        if model_path:
            if os.path.isfile(builder_path):
                pm.importFile(model_path)

        # Import builder
        if builder_path:
            pm.importFile(builder_path)

        #   build the base module
        self.base_module = baseModule.Base_module(character_name=self.character_name,
                                                  scale=self.scale,
                                                  snap_ctls_element=self.head_jnt, type=self.type)

        #   setting the model version attributes

        file_version_num = data.get_file_version_number(model_path)

        pm.addAttr(self.base_module.top_group, ln="model_path", dataType="string")
        pm.setAttr("{}.model_path".format(self.base_module.top_group), model_path, type='string', l=1)

        pm.addAttr(self.base_module.top_group,
                   ln="model_version",
                   attributeType="long")

        pm.setAttr("{}.model_version".format(self.base_module.top_group),
                   file_version_num, l=1)

        #   parent all the elements under the right grps
        #   model                                          TO DO recognize low/mid/high
        character_model_grp = pm.PyNode("*_{}_mdl".format(character_name))

        pm.parent(character_model_grp, self.base_module.slow_model_grp)

        #   skeleton
        if self.root_jnt:
            pm.parent(self.root_jnt, self.base_module.skeleton_grp)

        self.pre_build()

        self.extra_joints()

        #   place pose
        self.upgrade()

        #   build rig
        self.rig_builder()

        #   load_skin                                          TO DO only for puppet ()
        if load_skin:
            if rig_data_path:
                path_ext = "{}/{}".format(rig_data_path,
                                          "data/skincluster")

                pixoSkin.pixo_import_skin(path_ext)

        #   control shapes load/change
        if load_ctls:
            shape.load_ctl_shapes(main_path=rig_data_path,
                                  specific_path=None,
                                  apply=1)

        self.post_build()

        #   cleaning everything
        cleanup.remove_unknowns()
        cleanup.remove_unused()



        #   fitting view
        pm.select(cl=True)
        pm.viewFit(all=True)

        totalTime = pm.timerX(startTime=start)
        print('-- BUILDING PROCESS END --')
        print(('Total time: ', totalTime))

    def pre_build(self):
        print("******* Pre-Build Executed *******")

    def upgrade(self):
        print("******* Upgrade Executed *******")

    def post_build(self):
        print("******* Post-Build Executed *******")

    def rig_builder(self):
        print("******* Rig-Builder Executed *******")

    def extra_joints(self):
        print("******* Extra-Joints Executed *******")
