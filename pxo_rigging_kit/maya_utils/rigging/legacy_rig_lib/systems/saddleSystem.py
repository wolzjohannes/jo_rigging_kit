"""

www.pixomondo.com
Date: 22 / 03 / 2022

saddleSystem module
category : Rigging
subcategory : systems
author : Michele Trabona / Rigging TD

"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from builtins import super
from future import standard_library
standard_library.install_aliases()
import pymel.core as pm
from ..utils import name
from ..utils import joint
from ..utils import constraints
from ..modules import tweakers
#reload(tweakers)

from ..modules import rivetControls
from . import baseSystem

"""
    Saddle System setup

"""


class Saddle_system(baseSystem.Base_system):

    def __init__(self,
                 prop_name="new",
                 rig_data_path=None,
                 model_path=None,
                 builder_path=None,
                 root_jnt=None,
                 head_jnt=None,
                 scale=1.0,
                 build_bs=1,
                 load_skin=1,
                 load_deformers=0,
                 load_ctls=1,
                 go_to_T_pose=0,
                 pre_build=None,
                 upgrade=None,
                 post_build=None
                 ):

        """
        It will build the facial rig system.

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

        self.prop_name = prop_name
        self.rig_data_path = rig_data_path
        self.model_path = model_path
        self.builder_path = builder_path
        self.root_jnt = root_jnt
        self.head_jnt = head_jnt
        self.scale = scale
        self.build_bs = build_bs
        self.load_skin = load_skin
        self.load_deformers = load_deformers
        self.go_to_T_pose = go_to_T_pose
        self.custom_pre_build = pre_build
        self.custom_upgrade = upgrade
        self.custom_post_build = post_build

        super(Saddle_system, self).__init__(prop_name,
                                            rig_data_path,
                                            model_path,
                                            builder_path,
                                            root_jnt,
                                            head_jnt,
                                            scale,
                                            load_skin,
                                            load_deformers,
                                            load_ctls,
                                            go_to_T_pose,
                                            type="prop")

    def pre_build(self):
        """
        It is a instance class and it will be executed
        after the load of all the files needed and
        after the base module creation.

        """
        # tagging joints to connect them with the body afterwards
        joint_hierarchy = joint.get_joint_chain(self.root_jnt)
        for jnt in joint_hierarchy:
            if jnt.hasAttr("ObjTag"):
                if jnt.ObjTag.get() == "bodyRig":
                    if jnt.hasAttr("connection_tag"):
                        constraints.remove_connection_tag(jnt)

                    constraints.connection_tag(jnt, "pConstraint", jnt)

        name.renamer_change_suffix(joint_hierarchy, "saddleJnt")
        pm.parent("saddleRigProxy_geo",
                  self.base_module.no_transf_grp)
        pm.parent("saddle_rivet_geo",
                  self.base_module.no_transf_grp)
        # deleting the low poly mesh
        pm.delete("low")

        if self.custom_pre_build is not None:
            self.custom_pre_build()

    def upgrade(self):
        if self.custom_upgrade is not None:
            self.custom_upgrade()

    def post_build(self):
        if self.custom_post_build is not None:
            self.custom_post_build()



    def rig_builder(self):
        """
        tweakers.Tweakers(moving_mesh=self.face_geo,
                          mesh = "face_local_geo",
                    dummies_locs_grp="dummies_tweaker_grp",
                          scale=self.scale,
                          base_module = self.base_module)
        """
        # Implementing the saddle main_rivet control
        rivetControls.RivetControls(name="Saddle",
                                    moving_mesh="saddle_rivet_geo",
                                    dummies_rivet_grp="saddle_rivet_grp",
                                    create_controls=True,
                                    seperate_hierarchy=True,
                                    base_module=self.base_module)
        # MAKING TWEAKER SETUP

        # dummie joint
        dummie_jnt = pm.joint(n="dummieTweaker_jnt")
        pm.parent(dummie_jnt, self.base_module.no_transf_grp)
        if pm.objExists("tweakers_grp"):
            list_rel = pm.listRelatives("tweakers_grp",
                                        ad=True,
                                        type="transform")
            rivet_grps = []
            for child in list_rel:
                if child.endswith("_tweakers_grp"):
                    rivet_grps.append(child)

            for grp in rivet_grps:
                # getting the geo we want to snap to name
                geo = pm.ls("{}*_geo".format(grp.name()[:-12]))[0]

                geo_dup = pm.duplicate(geo, n=geo.name().replace("_high_",
                                                                 "_local_"))[0]
                pm.blendShape([geo_dup],
                              geo,
                              frontOfChain=True,
                              weight=(0, 1))

                pm.parent(geo_dup, self.base_module.no_transf_grp)
                tweakers.Tweakers(name=grp.name()[:-13],
                                  moving_mesh=geo.name(),
                                  mesh=geo.name(),
                                  dummies_locs_grp=grp,
                                  scale=self.scale,
                                  connectionType='blendShape',
                                  base_module=self.base_module)

        print("******* Rig-Builder Executed *******")
