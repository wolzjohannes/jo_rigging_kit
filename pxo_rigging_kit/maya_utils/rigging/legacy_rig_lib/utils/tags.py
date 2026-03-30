"""
www.pixomondo.com
Date: 01 / 02 / 2022

tags module
category : Rigging
subcategory : utils
author : Michele Trabona / Rigging TD

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from future import standard_library
standard_library.install_aliases()
import pymel.core as pm

TAG = 'ObjTag'


def tag_element(elements, tag_name):
    """
    It is used to tag any element which need the tag
    in order to obtain different kind of behaviour
    for different tags.

    Args:
        elements(pm.PyNode(),str,list): The elements
            on which we want to add the tag.
        tag_name(str): The name of the tag.

    Return:
        None.

    """

    if not isinstance(elements, list):
        elements = [elements]

    for e in elements:
        if isinstance(e, str):
            e = pm.PyNode(e)

        pm.addAttr(e, ln=TAG, dt="string")

        # setting up the attribute
        pm.setAttr("{element}.{tag}".format(element=e, tag=TAG),
                   tag_name,
                   type="string",
                   l=True)


def relation_tag_element(elements, at_name, tag_name):
    """
    It is used to tag any element which need the tag
    in order to specify a connection between elements.

    Args:
        elements(pm.PyNode(),str,list): The elements
            on which we want to add the tag.
        at_name(str): The name of the tag attribute.
        tag_name(str): The name of the tag.

    Return:
        None.

    """

    if not isinstance(elements, list):
        elements = [elements]

    for e in elements:
        if isinstance(e, str):
            e = pm.PyNode(e)

        pm.addAttr(e,ln = at_name, dt = "string")
        # setting up the attribute
        pm.setAttr("{}.{}".format(e,at_name),
                   tag_name,
                   type = "string",
                   l = 1)


def detag_elements(elements=pm.selected()):
    """loops over list and removes the ObjTag attr(or the attr specified on top of the tags module)

    Args:
        elements(list): if nothing chosen takes active selection, else list of PyNodes
    Return:
        changed_elements(list): returns all the elements that were de-tagged
    """

    changed_elements = list()

    for i in elements:
        try:
            i.ObjTag.set(lock=False)
            i.deleteAttr(TAG)
            changed_elements.append(i)

        except:
            pass

    return changed_elements



