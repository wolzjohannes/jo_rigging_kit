"""
www.pixomondo.com
Date: 26 / 01 / 2022

shape module
category : Rigging
subcategory : utils
author : Michele Trabona / Rigging TD

"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from future import standard_library
standard_library.install_aliases()
from builtins import str
import pymel.core as pm
import os
import maya.api.OpenMaya as om
from . import name
from . import data
import mgear.core.transform as mtr


def build_nurb_from_curve_vector(curve, pushing_vector):
    """
    Create a transform on a nurbsSurface.

    Args:
        curve(pm.PyNode(),str): The curve from which we will
            make the nurb.
        pushing_vector(vector): The vector that will
            push the curve's CVs to make the loft.

    Return:
        pm.PyNode(): The nurb transform node.

    """
    if isinstance(curve, str):
        curve = pm.PyNode(curve)
    #   construction curve placement
    constr_curve = pm.duplicate(curve, n="{}{}".format(curve.name(),"_ribbon_constr"))[0]
    cvs_number = pm.ls(constr_curve.cv[:], fl=1)
    for cv in cvs_number:
        curve_cv_vec = om.MVector(pm.xform(cv, q=1,  t=1, ws=1))
        new_cv_pos = curve_cv_vec + pushing_vector
        pm.xform(cv,  t=new_cv_pos, ws=1)

    c_comp = curve.name().split('_')[0]
    c_side = name.get_side(curve.name(), with_undescore=1)
    c_description = name.get_description(curve.name(), with_undescore=1)
    c_subdefinition = name.get_subdefinition(curve.name(), with_undescore=False)
    nurb_name = "{}{}0{}{}_{}".format(c_comp,c_side,c_description,c_subdefinition,"nrb")
    curve_nrb = pm.loft(curve, constr_curve,
                         ch = 1, u = 1,
                         c = 0, ar = 1,
                         d = 3, ss = 1,
                         rn = 0, po = 0,
                         rsn = 1, n = nurb_name)[0]
    pm.delete(constr_curve)
    pm.delete(curve_nrb, ch =1)

    return curve_nrb



def copy_shape(source, destination,mode = ""):

    """
    Copy Shape from source to destination transform

    Args:
        source(pm.PyNode(),str): The object from which
            we want to copy the shape.
        destination(pm.PyNode(),str): The object under which
            the shape will be copied.
        mode(pm.PyNode(),str): The mode with which we want to
        apply the ctl transformation

    Return:
        None.

    """
    if mode == 'blendShape':
        blend_shape_nd = pm.blendShape([source], destination, frontOfChain=True, weight=(0, 1))
        pm.delete(destination, ch=True)
    else:
        source_shapes = pm.ls(source)[0].getShapes()
        destination_shapes = pm.ls(destination)[0].getShapes()
        pm.delete(destination_shapes)

        pm.parent(source_shapes, destination, r=True, s=True)
        pm.delete(source)


def extract_ctrl_shapes():
    control_shape_grp = pm.group(n='control_shapes_grp', em=True)
    ctrl_list = pm.ls('*_ctrl')
    for ctrl in ctrl_list:
        ctrl_shape = pm.duplicate(ctrl, rr=True)[0]
        for at in ["t","s","r"]:
            for spec_at in  ["x","y","z"]:
                at_name = at + spec_at
                pm.setAttr("{}.{}".format(ctrl_shape.name(),at_name),
                           k =1, l =0, cb =1)

        delete_list = pm.listRelatives(ctrl_shape, c=True, type='transform')
        pm.delete(delete_list)
        pm.parent(ctrl_shape, control_shape_grp)
        new_name = str(ctrl_shape.name()).replace('_ctrl1', '_shape_ctrl')
        pm.rename(ctrl_shape, new_name)
    return control_shape_grp


def extract_ctrl_shapes_for_LOD():
    control_shape_grp = pm.group(n='control_shapesLOD_grp', em=True)
    ctrl_list = pm.ls('*_ctrl')
    for ctrl in ctrl_list:
        ctrl_shape = pm.duplicate(ctrl, rr=True)[0]
        delete_list = pm.listRelatives(ctrl_shape, c=True, type='transform')
        pm.delete(delete_list)
        pm.parent(ctrl_shape, control_shape_grp)
        new_name = str(ctrl_shape.name()).replace('_ctrl1', '_LOD_ctrl')
        pm.rename(ctrl_shape, new_name)
        #resetting the values
        attrs_list = pm.listAttr(ctrl,keyable = 1)
        for at in attrs_list:

            at_val = pm.getAttr("{}.{}".format(ctrl.name(),at))
            pm.setAttr("{}.{}".format(ctrl_shape.name(), at),at_val)
    return control_shape_grp

def apply_ctrl_shapes ():
    if pm.objExists('control_shapes_grp'):
        control_shape_list = pm.ls('*_shape_ctrl*')
        control_list = [cv for cv in pm.ls('*_ctrl', '*_ctrl?') if cv not in control_shape_list]
        for ctrl in control_list:
            for ctrl_shape in control_shape_list:
                if str(ctrl_shape.name()).replace('_shape_ctrl', '_ctrl') == str(ctrl.name()):
                    print(('Transfering Shape: ', str(ctrl_shape.name()), ' <-----> ', str(ctrl.name())))
                    copy_shape(ctrl_shape, ctrl)
        #check if there are elements under the shape group
        if len(pm.listRelatives("control_shapes_grp",ad = 1)) == 0:
            pm.delete('control_shapes_grp')


def save_ctl_shapes(main_path = None,
                    specific_path = None,
                    type = None):
    if not type:
        type = ""
    if specific_path == None:
        if main_path:
            specific_path = "{}/{}".format(main_path,
                                      "controlShapes{}".format(type))
    if specific_path:
        if os.path.isdir(specific_path):
            control_shape_grp = "control_shapes{}_grp".format(type)
            if not pm.objExists(control_shape_grp):
                control_shape_grp = extract_ctrl_shapes()
            data.export_maya_file(specific_path,
                                  "controlShapes{}".format(type),
                                  control_shape_grp,
                                  ext="mb")



def load_ctl_shapes(main_path = None,
                    specific_path = None,
                    apply = 0,
                    type = None):
    if not type:
        type = ""

    if specific_path == None:
        if main_path:
            path_ext = "{}\{}".format(main_path,
                                      "controlShapes{}".format(type))
            file_name = data.get_all_latest_versions(path=path_ext)[0]
            specific_path = "{}\{}".format(path_ext,
                                      file_name)
    if specific_path:
        if os.path.isfile(specific_path):
            pm.importFile(specific_path)
            if apply:
                apply_ctrl_shapes()


def mirror_ctl_shapes():

    sel = pm.selected()
    for ctl in sel:
        opposite = pm.PyNode(name.flip_side(ctl.name()))
        t_mat = ctl.getMatrix()
        mat_flipped = mtr.getSymmetricalTransform(t_mat, axis="yz", fNegScale=False)
        new_ctl = pm.duplicate(ctl)[0]
        new_ctl.setMatrix(mat_flipped)
        opposite_side = name.get_side(opposite.name(), with_undescore=0)
        shape = pm.listRelatives(new_ctl, shapes = 1)[0]
        color_ind = pm.getAttr("{}.ovc".format(shape))
        new_color = None
        if opposite_side == "L":
            if color_ind == 13:
                new_color = 6
            else:
                new_color = 18
        elif opposite_side == "R":
            if color_ind == 6:
                new_color = 13
            else:
                new_color = 20
        pm.setAttr("{}.ovc".format(shape), new_color)
        copy_shape(new_ctl, opposite, mode="")


"""

import pymel.core as pm
import legacy_rig_lib.utils.name as nm
ctrl_list = pm.ls('*_ctrl')
ctrl_list = [ ctrl for ctrl in ctrl_list if not "_LOD_" in ctrl.name()]
extracted_LOD = pm.listRelatives("control_shapesLOD_grp")
missing_lod_ctls = []
diff_attrs_ctls = []
diffVal_attrs_ctls = []
for ctrl in ctrl_list:
    lod_name = str(ctrl.name()).replace('_ctrl', '_LOD_ctrl')
    if lod_name in extracted_LOD:
       attrs_lod =  pm.listAttr(lod_name,k =1)
       attrs_ctrl = pm.listAttr(ctrl, k = 1)
       #checking if the attrs are the same
       if len(set(attrs_lod).symmetric_difference(set(attrs_ctrl)))>0:
           diff_attrs_ctls.append(ctrl)
       else:
           for at in attrs_lod:
               ctrl_val = pm.getAttr("{}.{}".format(ctrl,at))
               lod_val = pm.getAttr("{}.{}".format(lod_name,at))
               if ctrl_val != lod_val:
                   diffVal_attrs_ctls.append(ctrl)          
    else:
        missing_lod_ctls.append(ctrl)
diffVal_attrs_ctls = list(set(diffVal_attrs_ctls))
lists_sum = len(missing_lod_ctls)+len(diff_attrs_ctls)+len(diffVal_attrs_ctls)
if lists_sum:
    print ("\nControls which are not in the LOD :")
    print (missing_lod_ctls)
    print ("\n"+"#"*80)
    print ("\nControls which don't share the same attributes in LOD:")
    print (diff_attrs_ctls)
    print ("\n"+"#"*80)
    print ("\nControls which don't share the same attributes' value in LOD:")
    print (diffVal_attrs_ctls)
    print ("\n"+"#"*80)
"""