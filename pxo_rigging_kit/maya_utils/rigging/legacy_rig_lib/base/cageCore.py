"""
www.pixomondo.com
Date: 10 / 02 / 2022

cageCore module
category : Rigging
subcategory : base
author : Michele Trabona / Rigging TD

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from future import standard_library
standard_library.install_aliases()
from builtins import map
from builtins import object
import pymel.core as pm
from pymel.core import datatypes
from ..utils import name
from ..utils import pixomath as pmath
from ..utils import joint
from ..utils import transform
from ..utils import tags
from . import control
from mgear.core import node
import mgear.core.transform as MGtransf
import mgear.core.vector as MGVector


class Cage(object):
    def __init__(self,
                 cage_name,
                points_lists = None,
                 parents_list = None,
                 hook = None,
                 scale = 1.0,
                 joints_starters = None,
                 name_list = None,
                 connect_sub_parents = 1
                ):
        self.cage_name = cage_name
        self.point_lists = points_lists
        self.parents_list = parents_list
        self.scale = scale
        self.joints_starters = joints_starters
        self.name_list = name_list
        self.connect_sub_parents = connect_sub_parents
        self.side = name.get_side(cage_name,
                                  with_undescore=0)
        self.component = name.get_component(cage_name,
                                            with_undescore=0)
        self.ctl_side = self.side
        self.ctl_component = self.component


        if not self.joints_starters == None:
            self.joints_structure_reader()
            self.list_jnts = None

        self.groups_structure()
        self.cage_tags()
        self.multi_cage_chain()


    def groups_structure(self):
        #main_grp
        self.top_grp = pm.group(n = "{}_{}_cage_grp".format(self.component,
                                                            self.side),
                                em = 1)
        self.control_grp = pm.group(n = "{}_{}_ctrl_grp".format(self.component,
                                                                self.side),
                                    em = 1,
                                    p = self.top_grp)
        self.curve_grp = pm.group(n = "{}_{}_curve_grp".format(self.component,
                                                               self.side),
                                    em = 1,
                                    p = self.top_grp)
        pm.setAttr(self.curve_grp.inheritsTransform, 0)


    def cage_tags(self):

        tags.relation_tag_element(self.top_grp,
                                  "main_name",
                                  "{}_{}".format(self.component,
                                                 self.side))
        tags.tag_element([self.curve_grp,
                          self.control_grp],
                         self.top_grp.name())
        tags.relation_tag_element(self.top_grp,
                                  "control",
                                  self.control_grp.name())
        tags.relation_tag_element(self.top_grp,
                                  "curve",
                                  self.curve_grp.name())



    def curve_maker(self):
        #make curve
        pos = []
        for ctl in self.ctls_list:
            ctl_pos = pm.xform(ctl.ctl,q = 1, t=1, ws = 1)
            pos.append((ctl_pos[0], ctl_pos[1], ctl_pos[2]))
        curve_name = "{}{}0_cageCrv_default_{}".format(
                                            self.ctl_component,
                                           self.ctl_side,
                                            "crv")
        self.crv = pm.curve(n = curve_name,d=1, p=pos)
        #giving it the names
        names_string = None
        if self.name_list != None:
            names_string = " ".join(map(str,self.names))

        else:
            names_string = " ".join(map(str, self.list_jnts))
        tags.relation_tag_element(self.crv,
                                  "joints_name",
                                  names_string)
        if self.parent_e:
            parent_name = self.parent_e
        else:
            parent_name = "unknown"
        tags.relation_tag_element(self.crv,
                                  "parent_name",
                                  parent_name)

        #connect curve with ctls
        it = 0
        for ctl_con in self.ctls_list:
            d_m = node.createDecomposeMatrixNode("{}.worldMatrix[0]".format(ctl_con.ctl))
            pm.connectAttr("{}.outputTranslate".format(d_m),
                           "{}.controlPoints[{}]".format(self.crv,it),
                           f = 1)
            tags.relation_tag_element(self.crv,
                                      "ctl_name{}".format(it),
                                      ctl_con.ctl)

            it +=1
        #ctls attr
        pm.setAttr(self.crv.overrideEnabled, 1)
        pm.setAttr(self.crv.overrideDisplayType,2)
        pm.setAttr(self.crv.ovc, 25)
        pm.parent(self.crv,self.curve_grp)


    def cage_chain(self,position_list):
        it = 0
        self.ctls_list = []
        for pos in position_list:
            cage_ctl = control.Control(component="{}{}".format(
                                                self.ctl_component,
                                                               it),
                                      side=self.ctl_side,
                                      description="cageCtl",
                                      subdefinition="default",
                                      shape="simpleSphere",
                                      scale=self.scale,
                                      lock_hide=["s","v"])
            cage_ctl.off.setMatrix(pos,ws = 1)

            if len(self.ctls_list)>0:
                pm.parent(cage_ctl.off,self.ctls_list[-1].ctl)
            self.ctls_list.append(cage_ctl)

            it += 1
        pm.parent(self.ctls_list[0].off,self.control_grp)
        if self.connect_sub_parents:
            if self.parent_e:
                if not self.parent_e == "unknown":
                    pm.parentConstraint(self.parent_e,
                                        self.ctls_list[0].off,
                                        mo = 1)

    def joints_structure_reader(self):
        self.point_lists =[]
        for jnt in self.joints_starters:
            list_jnts = joint.get_joint_chain(jnt)
            positions_list = transform.elements_matrices(list_jnts)
            self.point_lists.append(positions_list)


    def multi_cage_chain(self):
        it = 0
        self.names = None
        for p_list in self.point_lists:
            if not self.joints_starters == None :
                self.ctl_side = name.get_side(
                                    self.joints_starters[it],
                                          with_undescore=0)
                self.ctl_component = name.get_component(
                                            self.joints_starters[it],
                                                    with_undescore=0)
                self.list_jnts = joint.get_joint_chain(self.joints_starters[it])
            if not self.name_list == None:
                self.ctl_side = name.get_side(
                        self.name_list[it][0],
                        with_undescore=0)
                self.ctl_component = name.get_component(
                                            self.name_list[it][0],
                                                    with_undescore=0)
                self.names = self.name_list[it]
            if self.parents_list:
                self.parent_e = self.parents_list[it]
            else:
                self.parent_e = None
            self.cage_chain(p_list)
            self.curve_maker()
            it +=1
    @staticmethod
    def connect_parents(cage):
        crvs_grp = pm.getAttr("{}.curve".format(cage))
        crvs_list = pm.listRelatives(crvs_grp,c=1,type = "transform")
        for crv in crvs_list:
            parent_name = pm.getAttr(crv.parent_name)
            if not parent_name == "unknown":
                children_ctl = pm.getAttr(crv.ctl_name0)
                pm.parentConstraint(
                    parent_name,
                    children_ctl,
                    mo = 1
                )


    @staticmethod
    def joints_maker(top_grp):
        side = name.get_side(top_grp, with_undescore=0)
        crvs_grp = pm.getAttr("{}.curve".format(top_grp))
        crvs_list = pm.listRelatives(crvs_grp,c=1,type = "transform")
        joints_chains = []
        for crv in crvs_list:
            crvs_pos = transform.get_cv_position(crv)
            matrix_list = None
            up_vector = None
            if len(crvs_pos) > 2:
                up_vector = MGVector.getPlaneNormal(crvs_pos[0],
                                                    crvs_pos[1],
                                                    crvs_pos[2])
            elif len(crvs_pos) == 1:
                ctl_name = pm.getAttr("{}.ctl_name0".format(crv))
                ctl_0 = pm.PyNode(ctl_name)
                matrix_list = [ctl_0.getMatrix(ws = 1)]
            else:
                ctl_name = pm.getAttr("{}.ctl_name0".format(crv))
                ctl_0 = pm.PyNode(ctl_name)

                mat = ctl_0.getMatrix()
                z_vec = datatypes.Vector(mat[2][0],
                                         mat[2][1],
                                         mat[2][2])
                z_vec = z_vec.normal()
                x_vec = crvs_pos[1] - crvs_pos[0]
                x_vec = x_vec.normal()

                up_vector = z_vec^x_vec
            if not len(crvs_pos) == 1:
                # joints orientation
                negate = 0
                if side == "R":
                    negate = True
                matrix_list = MGtransf.getChainTransform2(crvs_pos,
                                                          up_vector,
                                                          negate=negate)
            chain_list = []
            pm.select(cl = 1)
            names_list = pm.getAttr("{}.joints_name".format(crv)).split(" ")

            for it_, m in enumerate(matrix_list):
                joint = pm.joint(n=names_list[it_])
                joint.setMatrix(m,
                                ws=1
                                )
                pm.select(cl=1)

                if len(chain_list) > 0:
                    pm.parent(joint, chain_list[-1])

                chain_list.append(joint)

            print(chain_list)
            pm.makeIdentity(chain_list[0],
                            apply=1,
                            t=1,
                            r=1,
                            s=1,
                            n=0,
                            pn=1
                            )

            pm.select(cl=1)

            joints_chains.append(chain_list)

        print(joints_chains)
        return joints_chains

    @staticmethod
    def cage_exporter():
        pass


    @staticmethod
    def cage_importer():
        pass


    @staticmethod
    def cage_dict_maker (cage):
        """
        if not isinstance(cage,str):
            cage = cage.name()
            """
        main_name = pm.getAttr("{}.main_name".format(cage))
        if not main_name.endswith("_"):
            main_name = main_name + "_"
        #getting crvs points and names
        crvs_grp = pm.getAttr("{}.curve".format(cage))
        crvs_list = pm.listRelatives(crvs_grp,c=1,type = "transform")
        joints_name_list = []
        ctls_matrices_list = []
        parents_name = []
        for crv in crvs_list:
            joints_name = pm.getAttr("{}.joints_name".format(crv))
            joints_name_list.append([joints_name])
            matrix_list = []
            #get ctls list
            at_list = pm.listAttr(crv, locked=1, )
            ctl_list = []
            for at in at_list:
                if "ctl_name" in at:
                    ctl_list.append(at)
            for at in ctl_list:
                ctl_nd = pm.PyNode(pm.getAttr(
                "{}.{}".format(crv,at)
                ))
                mat = pmath.convert_PyMat_to_list(
                    ctl_nd.getMatrix(ws=1)
                )
                matrix_list.append(mat)
            ctls_matrices_list.append(matrix_list)
            # get parent
            parent = pm.getAttr(crv.parent_name)
            parents_name.append(parent)
        cage_dic = {"main_name" : main_name,
                    "positions_list" : ctls_matrices_list,
                    "parents_name":parents_name,
                    "name_list": joints_name_list}
        return cage_dic


    @staticmethod
    def build_cage_from_dict(cage_dict,
                             connect_sub_parents=1
                             ):

        cage_main_grp = "{0}_cage_grp".format(cage_dict["main_name"])

        if pm.objExists(cage_main_grp):
            pm.delete(cage_main_grp)

        cage = Cage(cage_name=cage_dict["main_name"],
                    points_lists=cage_dict["positions_list"],
                    parents_list=cage_dict["parents_name"],
                    name_list=cage_dict["name_list"],
                    connect_sub_parents =connect_sub_parents
                    )

        return cage


    @staticmethod
    def mirror_cage(cage):
        if isinstance(cage,str):
            cage = pm.PyNode(cage)
        opposite = name.flip_side(cage)
        if not pm.objExists(opposite):
            cage_dic = Cage.cage_dict_maker(cage)
            cage_dic ["main_name"] = name.flip_side(
                                    cage_dic ["main_name"])
            new_name_list = []
            for list_name in cage_dic["name_list"]:
                temp_nm_list = []
                for nm in list_name:
                    temp_nm_list.append(name.flip_side(nm))
                new_name_list.append(temp_nm_list)

            cage_dic["name_list"] = new_name_list
            new_parents_name = []
            for prnt in cage_dic["parents_name"]:
                if "unknown" in prnt:
                  new_parents_name.append(prnt)
                else:
                    new_parents_name.append(
                        name.flip_side(prnt)
                    )
            cage_dic["parents_name"] = new_parents_name

            Cage.build_cage_from_dict(cage_dic,
                                      connect_sub_parents = 0)
        ctl_grp_name = pm.getAttr("{}.control".format(cage))
        ctl_list = pm.listRelatives(ctl_grp_name,
                                    ad = 1,
                                    type = "transform" )
        ctl_list.reverse()
        flip_ctl_list = []
        for e in ctl_list:
            if e.name().endswith("_ctrl"):
                flip_ctl_list.append(e)
        #mirror cage
        for ctl in flip_ctl_list:
            side = name.get_side(ctl, with_undescore=0)
            opposite_side = name.get_opposite(side)
            opposite_side_ctl = pm.PyNode(name.flip_side(ctl))

            t_mat = ctl.getMatrix(ws = 1)
            flip = False
            if opposite_side == "R":
                flip = True
            mat_flipped = MGtransf.getSymmetricalTransform(t_mat, axis="yz", fNegScale=flip)
            get_offset = pm.listRelatives(opposite_side_ctl,
                                          p = 1,
                                          type = "transform")[0]
            get_offset.setMatrix(mat_flipped, ws =1)

        Cage.connect_parents(opposite)

    """
import pymel.core as pm

joint_a = pm.PyNode("main")

joint_tree_dic = {}
main_list = pm.listRelatives(joint_a,ad =1, type= "joint")
main_list.append(joint_a)
run = 0
elements_list = [joint_a]
run_in = 0
while run == 0:
    it = 0
    chain_list =[] 
    for element in elements_list:
        while run_in == 0:
            main_list.remove(element)
            list_rel = pm.listRelatives(element,c = 1, type = "joint")
            chain_list.append(element)
            if len(list_rel)==1:
                chain_list.append(list_rel[0])
                main_list.remove(list_rel[0])
                elements_list = [list_rel[0]]
            if len(list_rel)>1:
                chain_list = [element]+list_rel
                elements_list = list_rel
            if len(list_rel)==0:
                run_in += 1
        joint_tree_dic[chain_list[0]] = chain_list        
    it+=1
    if len(main_list)==0:
        print main_list
        run = 1
    if it == 500:
        print it
        run = 1
    

    
    """