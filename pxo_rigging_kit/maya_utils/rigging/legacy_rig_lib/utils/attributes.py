"""
www.pixomondo.com
Date: 31 / 01 / 2022

attributes module
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


def add_section(object, at_name = "settings"):
    """
    It will add a section attribute on the
    specified object.

    Args:
        object(pm.PyNode(),str): The object on
            which we want to add the attribute.
        at_name(str): The name of the tag.

    Return:
        None.

    """
    if isinstance(object,str):
        object = pm.PyNode(object)

    pm.addAttr(object,
               ln = at_name,
               at = "enum",
               shortName=at_name,
               niceName=at_name,
               enumName = "########",
               k =0)
    pm.setAttr("{}.{}".format(object, at_name), cb = 1, l =1)


def remove_custom_attrs(object):
    """
    removes all custom attributes from the specified object

    Args:
        object(pm.PyNode(),str): The object we want to clean

    Return:
        None.

    """

    if isinstance(object,str):
        object = pm.PyNode(object)

    all_custom_attrs= object.listAttr(userDefined= True)

    if all_custom_attrs:
        for cat in all_custom_attrs:
                pm.deleteAttr('{attr}'.format(attr= cat))
