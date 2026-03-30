"""
www.pixomondo.com
Date: 21 / 02 / 2022

tweaker module
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
from builtins import object
import pymel.core as pm
from ..base import module
from ..base import control
from ..utils import name
from ..utils import transform
from ..utils import joint
from ..utils import constraints
from pxo_rigging_kit.maya_utils.rigging.legacy_rig_lib.utils import info_geo
import mgear.core.node as node
import mgear.core.transform as mtrs


class Tweakers(object):
    def __init__(self,
                 name="New",
                 scale=10.0,
                 mesh=None,
                 moving_mesh=None,
                 dummies_locs_grp=None,
                 base_module=None,
                 connectionType='blendShape'
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

    def _build(self, args):
        self.name = args["name"]
        self.scale = args["scale"]
        self.mesh = args["mesh"]
        self.moving_mesh = args["moving_mesh"]
        self.dummies_locs_grp = args["dummies_locs_grp"]
        self.base_module = args["base_module"]
        self.connectionType = args['connectionType']
        self.moving_mesh = pm.PyNode(self.moving_mesh)

        #   making the basic module
        self.module_base = module.Module(component="tweakers{}".format(self.name),
                                         side="C",
                                         base_module=self.base_module)
        #   copy the facial mesh
        tweaker_mesh = None
        if "_local_" in self.mesh:
            tweaker_mesh = pm.duplicate(self.mesh,
                                        n=self.mesh.replace("_local_",
                                                            "_tweaker_"))[0]
        elif "_high_" in self.mesh:
            tweaker_mesh = pm.duplicate(self.mesh,
                                        n=self.mesh.replace("_high_",
                                                            "_tweaker_"))[0]
            pm.parent(tweaker_mesh, self.module_base.noTransf_grp)

        #   check if the face mesh exists
        if pm.objExists("connect_BS"):
            pm.blendShape("connect_BS",
                          e=1, t=(self.mesh, 1, tweaker_mesh, 1))

            pm.setAttr("{}.{}".format("connect_BS",
                                      tweaker_mesh.name()), 1)

        elif pm.objExists("facialBS_geo"):
            facial_bs = pm.blendShape("facialBS_geo",
                                      self.mesh,
                                      n="connect_BS")[0]

            pm.setAttr("{}.{}".format(facial_bs.name(),
                                      tweaker_mesh.name()), 1)
        else:
            if self.connectionType == 'blendShape':
                facial_bs = pm.blendShape([tweaker_mesh],
                                          self.mesh,
                                          n="{}connect_BS".format(self.name))[0]

                pm.setAttr("{}.{}".format(facial_bs.name(),
                                          tweaker_mesh.name()), 1)

            elif self.connectionType == 'direct':
                info_geo.connect_meshes_inOut(tweaker_mesh,self.mesh)

        self._controls_builder()

    def _controls_builder(self):
        all_dummies_list = pm.listRelatives(self.dummies_locs_grp,
                                            c=1,
                                            type="transform")

        twk_jnts_static_grp = pm.group(n="{}twk_static_jnts_grp".format(self.name),
                                       em=1,
                                       p=self.module_base.noTransf_grp)

        twk_fol_static_grp = pm.group(n="{}twk_static_fol_grp".format(self.name),
                                      em=1,
                                      p=self.module_base.noTransf_grp)

        for dummy_loc in all_dummies_list:

            side = name.get_side(dummy_loc,
                                 with_undescore=False)

            component = name.get_component(dummy_loc,
                                           with_undescore=False)

            rivet_node = self.rivet_on_face(dummy_loc,
                                            side,
                                            component)

            pm.parent(rivet_node, twk_fol_static_grp)
            fc_ctl = self.tweaker_ctl_maker(component, side, dummy_loc)

            pm.delete(pm.parentConstraint(dummy_loc,
                                          fc_ctl.off,
                                          mo=0))

            constraints.pxoparent(masters=rivet_node,
                                  slaves=fc_ctl.off,
                                  maintainOffset=True,
                                  native=False
                                  )

            face_tweak_jnt = joint.make_joint_on_element(fc_ctl.ctl,
                                                         suffix="jnt",
                                                         connect=0)
            #   freezing to avoid the flip
            pm.makeIdentity(face_tweak_jnt,
                            apply=1, t=1,
                            r=1, s=0, n=0,
                            pn=1)

            extra_buf = transform.make_extra_buffer(face_tweak_jnt,
                                                    "maintainPos",
                                                    buffer_number=1,
                                                    move_to=1)[0]

            pm.parent(extra_buf,twk_jnts_static_grp)
            constraints.connection_tag(face_tweak_jnt,
                                       "tConnection,rConnection",
                                       fc_ctl.ctl)

            constraints.connect_by_tag(face_tweak_jnt)

    def rivet_on_face(self, ctl_dummy, component, side):
        position = ctl_dummy.getTranslation(w=1)
        shape = self.moving_mesh.getShape()

        if shape.nodeType() == 'nurbsSurface':
            pos, u, v = self.moving_mesh.closestPoint(position)
            fol = transform.createFollicle(shape, uPos=u, vPos=v)
            #   geo, uPos = 0.0, vPos = 0.0, name = False

        elif shape.nodeType() == 'mesh':
            face_id = self.moving_mesh.getClosestPoint(position)[1]
            pm.select(self.moving_mesh.name() + '.f[' + str(face_id) + ']')
            fol = transform.attachToGeo()
            fol.v.set(0)

        else:
            raise ValueError

        fol_transform = pm.listRelatives(fol, p=1)
        pm.rename(fol_transform, '{}_{}_fol'.format(component, side))
        return fol_transform

    def tweaker_ctl_maker(self, component, side, dummy_loc):
        ind = name.get_index(dummy_loc, with_undescore=False)
        twk_ctl = control.Control(component="{}{}".format(component,
                                                          ind),
                                  side=side,
                                  description="control",
                                  subdefinition="default",
                                  shape="simpleSphere",
                                  scale=self.scale,
                                  color_name="secondary",
                                  move_to=dummy_loc,
                                  lock_hide=["s",  "v"],
                                  parent=self.module_base.get_grps()["prim"])

        extra_buf = transform.make_extra_buffer(twk_ctl.ctl,
                                                "reversePos",
                                                buffer_number=1,
                                                move_to=1)[0]

        mult_div_rev_ctl = node.createMulDivNode("{}.t".format(twk_ctl.ctl),
                                                 [-1, -1, -1],
                                                 operation=1,
                                                 output=None)

        pm.connectAttr("{}.output".format(mult_div_rev_ctl),
                       "{}.t".format(extra_buf), f=1)

        pm.rename(mult_div_rev_ctl, "{}RevPos{}MPD".format(component, side))
        return twk_ctl

    @staticmethod
    def mirror_loc_dummies(loc_list):
        for loc in loc_list:
            side = name.get_side(loc, with_undescore=False)
            opposite_side = name.get_opposite(side)
            opposite_side_ctl = name.flip_side(loc)
            if not pm.objExists(opposite_side_ctl):
                opposite_side_ctl = pm.duplicate(loc,
                                                 n=opposite_side_ctl)[0]
            else:
                opposite_side_ctl = pm.PyNode(opposite_side_ctl)
            t_mat = loc.getMatrix()
            flip = False
            if opposite_side == "R":
                flip = True
            mat_flipped = mtrs.getSymmetricalTransform(t_mat, axis="yz", fNegScale=True)
            opposite_side_ctl.setMatrix(mat_flipped)
            # pm.setAttr("{}.rz".format(opposite_side_ctl),0)


