"""
www.pixomondo.com
Date: 26 / 01 / 2022

joint module
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
import pymel.core as pm
import maya.cmds as mc

from . import name
from . import attributes
from . import constraints as cns

def get_joint_chain (start_jnt):
    """
    Get the joint chain from the specified start joint.

    Args:
        start_jnt(pm.PyNode(),str): The start joint which
        will be considered as the first joint of the chain.

    Return:
        pm.PyNode(),list: The list of joints under the
            hierarchy

    """
    if isinstance(start_jnt, str):
        start_jnt = pm.PyNode(start_jnt)

    joints_list = pm.listRelatives(start_jnt, ad = 1, type = "joint")
    joints_list.append(start_jnt)
    joints_list.reverse()

    return joints_list


def make_joint_on_element(element,suffix,connect = 0):
    if isinstance(element,str):
        element = pm.PyNode(element)
    joint_name = "{}{}".format(
        name.remove_suffix(element.name()),
        suffix)

    jnt = pm.joint(n = joint_name)
    pm.delete(pm.parentConstraint(element,
                                  jnt,
                                  mo = 0))
    jnt_output = jnt
    if connect == 1:
        cns.pxoparent(masters= element,slaves= jnt,maintainOffset= True)
    return jnt_output


def get_upmost_joint(hierarchy_start= None):
    """
    under a selected starting point it will list all the joints which have no joint as parent
    and therefore should be considered as start of the chain in world

    Args:
        hierarchy_start(pm.PyNode(),str, None): the beginning of the investigation, if None, scene is checked

    Return:
        uppermost_joints(list): list of all rootJoints as PyNodes

    """
    uppermost_joints= list()

    if not hierarchy_start:
        joints_to_check= pm.ls(type='joint')

    else:
        if isinstance(hierarchy_start, str):
            start_jnt = pm.PyNode(hierarchy_start)

        else:
            start_jnt= hierarchy_start

        joints_to_check= pm.listRelatives(start_jnt, ad = 1, type = "joint")

    for jt in joints_to_check:
        if jt.getParent().nodeType() == 'transform':
            uppermost_joints.append(jt)

    return uppermost_joints


def create_clean_hierarchy(hierarchy_start=None):
    """
    duplicates, cleans and formats all selected joints, and re-parents them under a new fileStructure

    WARNING:// THIS IS NOT YET CLEANED UP NICELY, IT JUST WORKS WITH HIERARCHY START AS INPUT!

    Args:
        hierarchy_start(pm.PyNode(),str, None): The object we want to clean

    Return:
        resulting_structure(dict): one dictionary containing the master, sub and all rootJoints

    """
    all_joints_affected= get_upmost_joint(hierarchy_start=hierarchy_start)


    # create new rootNodes to parent under
    master = pm.createNode('transform', n='jnt_org')
    sub = pm.createNode('transform', n='local_C0_jnt_org')
    pm.parent(sub, master)

    # create list for output
    joint_duplicates = []

    # loop over all rootJoints
    for jt in all_joints_affected:
        print (jt)
        joint_copied= pm.duplicate(jt)[0]

        pm.parent(joint_copied, sub)

        remaining_string= name.renamer_fix_suffix(joint_copied)

        joint_copied.rename(remaining_string)
        joint_duplicates.append(joint_copied)

    # get new object structure
    all_joints_general= get_joint_chain(sub)

    # loop over new object structure and prune its custom attrs
    for jt in all_joints_general:
        attributes.remove_custom_attrs(jt)

    resulting_structure = {master: {sub: joint_duplicates}}
    return resulting_structure


def unlock_all_joints():
    for s in mc.ls(type='joint'):
        try:
            mc.setAttr('{0}.liw'.format(s), 0)
        except:
            continue


def get_all_joints_with_under_selected():
    import pymel.core as pmc
    import itertools

    sel_start = pmc.selected()

    all_children = list(itertools.chain.from_iterable([x.listRelatives(allDescendents=True) for x in sel_start]))
    all_children.extend(sel_start)

    all_children_unique = list(set(all_children))

    all_children_joints = [x for x in all_children_unique if x.nodeType() == 'joint']

    pmc.select(all_children_joints)
    return all_children_joints
