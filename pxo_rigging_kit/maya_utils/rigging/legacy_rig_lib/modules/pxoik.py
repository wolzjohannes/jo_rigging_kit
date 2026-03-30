"""
www.pixomondo.com
Date: 20 / 05 / 2022

ik module
category : Rigging
subcategory : modules

author : Christof Puehringer / Rigging Junior TD
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
#   external libraries
from builtins import dict
from future import standard_library
standard_library.install_aliases()
from builtins import object
import pymel.core as pm


#   internal libraries
from ..base import module
from ..base import control

from ..utils import joint
from ..utils import name
from ..utils import constraints as pcons


class IkSystem(object):
    """

    """
    def __init__(self,
                 main_ctl_offset=False,
                 ik_base=None,
                 scale=1,
                 base_module=None,
                 component='ik',
                 stretch=False):

        local_args = locals()

        self._build(local_args)

    def _build(self, args):
        self.ik_base = args["ik_base"]
        self.scale = args["scale"]
        self.main_ctl_offset = args["main_ctl_offset"]
        self.base_module = args["base_module"]
        self.component = args["component"]
        self.stretch = args["stretch"]

        # making module
        self.module_base = module.Module(component=self.component,
                                         side=name.get_side(self.ik_base,
                                                            with_undescore=False),
                                         base_module=self.base_module)
        # create outputs
        self.ctl_objs = dict()
        self.ctrls = list()
        self.jnt_objs = dict()

        self.off = list()

        self.all_joints = joint.get_joint_chain(self.ik_base)

        # creation operations
        self.generate_controls()
        self.generate_rig()

        if self.stretch:
            self.generate_stretch()

    def generate_controls(self):
        """
        This function generates the controls for the ik


        Return:
            None
        """

        ik_base = self.ik_base
        side = name.get_side(self.ik_base, with_undescore=False)

        fk_base_control = control.Control(component='{}0'.format(self.component),
                                          side=side,
                                          description='control',
                                          subdefinition='default',
                                          shape='triangleX',
                                          scale=self.scale,
                                          move_to=ik_base,
                                          lock_hide=["s", "v"])

        if side == "L":
            fk_base_control.off.rx.set(fk_base_control.off.rx.get() + 180)

            # offsetting the control as needed
            fk_base_control.off.tx.set((fk_base_control.off.tx.get() + self.main_ctl_offset))

        else:
            fk_base_control.off.tx.set((fk_base_control.off.tx.get() - self.main_ctl_offset))

        self.ctl_objs['start'] = fk_base_control
        self.jnt_objs['start'] = ik_base

        ik_tip = self.all_joints[-1]
        side = name.get_side(ik_tip, with_undescore=False)

        ik_tip_control = control.Control(component='{}1'.format(self.component),
                                         side=side,
                                         description='control',
                                         subdefinition='default',
                                         shape='cube',
                                         scale=self.scale,
                                         move_to=ik_tip,
                                         lock_hide=["s", "v"])

        if side == "L":
            ik_tip_control.off.rx.set(ik_tip_control.off.rx.get() + 180)
            # offsetting the control as needed
            ik_tip_control.off.tx.set((ik_tip_control.off.tx.get() + self.main_ctl_offset))

        else:
            ik_tip_control.off.tx.set((ik_tip_control.off.tx.get() - self.main_ctl_offset))

        self.ctl_objs['end'] = ik_tip_control
        self.jnt_objs['end'] = ik_tip

        pm.parent(self.ctl_objs['end'].off, self.ctl_objs['start'].ctl)
        pm.parent(self.ctl_objs['start'].off, self.module_base.control_grp)

    def generate_rig(self):
        """
        This function generates and sets the control structure
        :return:
        """

        handle_name = name.change_suffix(self.ctl_objs['start'].ctl.name(), 'ikh')

        ikhandle = pm.ikHandle(n=handle_name, sj=self.jnt_objs['start'], ee=self.jnt_objs['end'])

        pm.rename(ikhandle[1], name.change_suffix(handle_name, 'eff'))
        pm.parent(ikhandle[0], self.module_base.noTransf_grp)

        polevec_target = pm.createNode('transform', n=name.change_suffix(handle_name, 'pos'))
        pm.matchTransform(polevec_target, self.ctl_objs['start'].ctl)
        pm.parent(polevec_target, self.ctl_objs['start'].ctl)

        polevec_target.tz.set(2)

        pcons.pxoparent(masters=self.ctl_objs['start'].ctl,
                        slaves=self.jnt_objs['start'],
                        maintainOffset=True,
                        native=True)

        pcons.pxoparent(masters=self.ctl_objs['end'].ctl,
                        slaves=ikhandle[0],
                        maintainOffset=True,
                        native=True)

        pm.poleVectorConstraint(polevec_target, ikhandle[0])

    def generate_stretch(self):

        compare_nde = pm.createNode('math_Compare', n='{}_compare'.format(self.component))
        compare_nde.operation.set(2, lock=True)

        select_nde = pm.createNode('math_Select', n='{}_select'.format(self.component))

        distance_nde = pm.createNode('math_DistanceTransforms', n='{}_distance'.format(self.component))

        divide_nde = pm.createNode('math_Divide', n='{}_divide'.format(self.component))

        self.ctl_objs['start'].ctl.worldMatrix.connect(distance_nde.input1)
        self.ctl_objs['end'].ctl.worldMatrix.connect(distance_nde.input2)

        distance_nde.output.connect(compare_nde.input1)
        distance_nde.output.connect(select_nde.input2)

        compare_nde.output.connect(select_nde.condition)

        select_nde.output.connect(divide_nde.input1)

        absolute_length = 0.0
        for jt in self.all_joints[1:]:
            multiply_nde = pm.createNode('math_Multiply', n='{}_scale'.format(jt))
            divide_nde.output.connect(multiply_nde.input1)

            joint_tx = jt.tx.get()
            multiply_nde.input2.set(joint_tx, lock=True)
            absolute_length += abs(joint_tx)

            multiply_nde.output.connect(jt.tx)

        compare_nde.input2.set(absolute_length, lock=True)
        select_nde.input1.set(absolute_length, lock=True)
        divide_nde.input2.set(absolute_length, lock=True)

    def calculate_pv_pos(self):
        pass
