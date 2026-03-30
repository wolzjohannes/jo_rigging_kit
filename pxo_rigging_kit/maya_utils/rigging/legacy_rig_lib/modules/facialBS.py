"""
www.pixomondo.com
Date: 15 / 02 / 2022

jaw module
category : Rigging
subcategory : modules
author : Michele Trabona / Rigging TD

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import range
from builtins import object
import pymel.core as pm
from ..base import module
from ..base import control
from ..base import controlShapes
from ..utils import name
from ..utils import transform
from ..utils import shape
import mgear.core.node as node
import mgear.core.transform as mtrs
import maya.api.OpenMaya as om


class FacialBS(object):
    def __init__(self,
                 scale = 1.0,
                 bs_mesh = None,
                 moving_mesh = None,
                 dummies_ctl_grp = None,
                 base_module = None,
                 ctl_t_mult = 10
                 ):
        """
        It builds the jaw module.

        Args:

            scale(float):  The scale which will be applied to
                the module creation.
            bs_mesh(pyNode,str): The name of the mesh.
            base_module(instance): The instance of the main module
                class. It is used to connect the nose module to
                the main.
        Return:
            None.

        """
        local_args = locals()

        self._build(local_args)

    def _build(self,
               args):
        self.scale = args["scale"]
        self.bs_mesh = args["bs_mesh"]
        self.moving_mesh = args["moving_mesh"]
        self.dummies_ctl_grp = args["dummies_ctl_grp"]
        self.base_module = args["base_module"]
        self.ctl_t_mult =  args["ctl_t_mult"]
        if isinstance(self.moving_mesh,str):
            self.moving_mesh = pm.PyNode(self.moving_mesh)

        #making the basic module
        self.module_base = module.Module(component="facialBS",
                                         side="C",
                                         base_module=self.base_module)
        self._controls_builder()

    def _controls_builder(self):
        all_dummies_list = pm.listRelatives(self.dummies_ctl_grp,
                                            c = 1,
                                            type = "transform")
        bs_node = pm.listConnections("{}.inMesh".format(self.bs_mesh),
                                     d=1,
                                     type="blendShape")[0]
        for dummy_ctl in all_dummies_list:

            side = name.get_side(dummy_ctl,
                                 with_undescore=0)
            component = name.get_component(dummy_ctl,
                                           with_undescore=0)
            rivet_node = self.rivet_on_face(dummy_ctl,
                                            side,
                                            component)
            pm.parent(rivet_node,self.module_base.noTransf_grp)
            fc_ctl = self.face_ctl_maker(component,side,dummy_ctl)

            pm.delete(pm.parentConstraint(dummy_ctl,
                                          fc_ctl.off,
                                          mo =0))

            pm.parentConstraint(rivet_node,fc_ctl.off,mo =1)                     #TO DO WITH MATRIX
            t_name = "{}_{}".format(side,component)
            if self.ctl_t_mult:
                pm.connectAttr("{}.outputX".format(self.mult_div_resize.name()),
                               "{}.{}".format(bs_node,t_name),
                               f=1)
            else:
                pm.connectAttr("{}.tx".format(fc_ctl.ctl),
                               "{}.{}".format(bs_node,t_name))



    def face_ctl_maker(self,component,side,dummy_ctl):
        face_ctl = control.Control(component=component,
                                   side=side,
                                   description="control",
                                   subdefinition="default",
                                   shape="drop",
                                   scale=self.scale,
                                   #move_to=dummy_ctl,
                                   lock_hide=["s", "r", "v", "ty","tz"],
                                   parent = self.module_base.control_grp)
        extra_buf = transform.make_extra_buffer(face_ctl.ctl,
                                              "noMove",
                                                buffer_number=1,
                                                move_to=1)[0]

        pm.makeIdentity(dummy_ctl, apply = 1, t = 0,
                        r= 0, s = 1,
                        n = 0, pn = 1)
        shape.copy_shape(dummy_ctl,
                         face_ctl.ctl,
                         mode = "blendShape")
        max_val = 1
        if self.ctl_t_mult:
            max_val = self.ctl_t_mult
        pm.transformLimits(face_ctl.ctl.name(), tx=[0, max_val], etx=[1, 1])
        dup = pm.duplicate(face_ctl.ctl)[0]
        dup.sx.unlock()
        dup.sy.unlock()
        dup.sz.unlock()
        dup.s.set(0, 0, 0)
        nurbs_name = "{}_{}_growing_nrb".format(component,side)
        growing_mesh = pm.loft(face_ctl.ctl, dup,
                               ch=1, u=1,
                               c=0, ar=1,
                               d=3, ss=1,
                               rn=0, po=0,
                               rsn=1, n=nurbs_name)[0]
        if side == "R":
            pm.reverseSurface (growing_mesh, d = 0,
                               ch = 1,rpo = 1)
        pm.delete(growing_mesh, ch=1)
        pm.delete(dup)
        #assign material to nurb
        set_name = "nurbCtl_shader"
        if not pm.objExists(set_name):
            white_mat = pm.shadingNode("blinn", asShader=True, name="ctl_growing")
            pm.setAttr("{}.color".format(white_mat), 1.0, 1.0, 1.0)
            # Create Surface Shader
            set_name = pm.sets(renderable=True, noSurfaceShader=True, empty=True, name="nurbCtl_shader")

            # Connect material to shader
            pm.connectAttr("ctl_growing.outColor", "nurbCtl_shader.surfaceShader")

        pm.sets(set_name, edit=True, forceElement=growing_mesh)

        pm.parent(growing_mesh, extra_buf)
        pm.setAttr("{}.overrideEnabled".format(growing_mesh.name()), 1)
        pm.setAttr("{}.overrideDisplayType".format(growing_mesh.name()), 2)

        mult_div_rev_ctl= node.createMulDivNode("{}.tx".format(face_ctl.ctl),
                                                   -1,
                                                   operation=1,
                                                output = "{}.tx".format(extra_buf))
        pm.rename(mult_div_rev_ctl, "{}Rev{}MPD".format(component, side))
        pm.connectAttr("{}.tx".format(face_ctl.ctl),
                       "{}.sx".format(growing_mesh),
                       f = 1 )
        pm.connectAttr("{}.tx".format(face_ctl.ctl),
                       "{}.sy".format(growing_mesh),
                       f = 1 )
        pm.connectAttr("{}.tx".format(face_ctl.ctl),
                       "{}.sz".format(growing_mesh),
                       f = 1 )
        pm.connectAttr("{}.t".format(face_ctl.ctl),
                       "{}.t".format(growing_mesh),
                       f = 1 )
        if self.ctl_t_mult:
            self.mult_div_resize = node.createMulDivNode("{}.tx".format(face_ctl.ctl),
                                                     max_val,
                                                     operation=2,
                                                     output="{}.sx".format(growing_mesh))
            pm.connectAttr("{}.outputX".format(self.mult_div_resize.name()),
                           "{}.sy".format(growing_mesh),
                           f=1)
            pm.connectAttr("{}.outputX".format(self.mult_div_resize.name()),
                           "{}.sz".format(growing_mesh),
                           f=1)
            pm.rename(self.mult_div_resize, "{}Resize{}MPD".format(component, side))
        return face_ctl

    def rivet_on_face(self,ctl_dummy,component,side):
        position = ctl_dummy.getTranslation(w=1)
        face_id = self.moving_mesh.getClosestPoint(position)[1]
        pm.select(self.moving_mesh.name() + '.f[' + str(face_id) + ']')
        fol = transform.attachToGeo()
        fol.v.set(0)
        fol_transform = pm.listRelatives(fol, p=1)
        pm.rename(fol_transform, '{}_{}_face_fol'.format(component,side))
        return fol_transform

    @staticmethod
    def build_ctl_dummies(bs_mesh):
        bs_node = pm.listConnections("{}.inMesh".format(bs_mesh), d=1, type="blendShape")[0]
        targets_array = pm.listAttr(bs_node.w, m=1)
        shapes_grp = pm.group(n='dummie_shapes_grp')
        for i in range(len(targets_array)):
            side,component = targets_array[i].split("_")
            shape = controlShapes.drop()
            pm.rename(shape,"{}_{}_dummyCtl".format(component,side))
            pm.parent(shape,shapes_grp)

    @staticmethod
    def mirror_ctl_dummies(ctl_list):
        for ctld in ctl_list:
            opposite_side_ctl = name.flip_side(ctld)
            if not pm.objExists(opposite_side_ctl):
                opposite_side_ctl = pm.duplicate(ctld,
                                                 n=opposite_side_ctl)[0]
            else:
                opposite_side_ctl = pm.PyNode(opposite_side_ctl)
            t_mat = ctld.getMatrix()
            mat_flipped = mtrs.getSymmetricalTransform(t_mat, axis="yz", fNegScale=False)
            opposite_side_ctl.setMatrix(mat_flipped)

    @staticmethod
    def fix_ctls_dummies ():
        sel = pm.ls("*dummyCtl")
        for e in sel:
            center = pm.objectCenter(e, gl=True)
            pm.xform(e, worldSpace=True, scalePivot=center)
            pm.xform(e, worldSpace=True, rotatePivot=center)

            dup = pm.duplicate(e)[0]

            t_main = om.MVector(e.t.get())
            r_main = e.r.get()
            dup.r.set(0, 0, 0)
            dup.t.set(0, 0, 0)

            vector_test = om.MVector(pm.xform(dup, query=True, worldSpace=True, scalePivot=True))
            vector_om = vector_test * -1

            cvs = pm.ls("{}.cv[:]".format(dup), fl=1)

            for cv in cvs:
                curve_cv_vec = om.MVector(pm.xform(cv, q=1, t=1, ws=1))
                new_cv_pos = curve_cv_vec + vector_om
                pm.xform(cv, t=new_cv_pos, ws=1)
            pm.xform(dup, worldSpace=True, scalePivot=(0, 0, 0))
            pm.xform(dup, worldSpace=True, rotatePivot=(0, 0, 0))

            pm.xform(dup, r=True, translation=t_main + (vector_test))
            pm.xform(dup, r=True, rotation=r_main)
            pm.delete(e)
            pm.rename(dup, e.name())