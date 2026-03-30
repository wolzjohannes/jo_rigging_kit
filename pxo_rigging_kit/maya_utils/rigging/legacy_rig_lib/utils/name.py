"""
www.pixomondo.com
Date: 25 / 01 / 2022

name module
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
import re
import pymel.core as pm

"""
    naming convention order = component}_{side}_{index}_{description}_{subdefinition}_{extension}

"""


def get_component(name_string, with_undescore=True, str_index=0):
    """
    Args:
        name_string(str): The name from which we want to get the
            component name.
        with_undescore(bool): It defines if the output should be
            with or without namespace.

    Return:
        str: The component name.

    """
    if "_" not in name_string:
        return ""
    else:
        component = name_string.split(":")[-1].split("_")[str_index]
        if with_undescore:
            component = "{}_".format(component)
        return component


def get_side(name_string, with_undescore=True):
    """
    Args:
        name_string(str): The name from which we want to get the
            side name.
        with_undescore(bool): It defines if the output should be
            with or without namespace.

    Return:
        str: The side name.

    """
    sides = ["C", "L", "R"]
    if "_" not in name_string:
        return ""
    else:
        for side_ in sides:
            if "{}_".format(side_) in name_string:
                side = side_
            else:
                side = name_string.split(":")[-1].split("_")[1]
        if with_undescore:
            side = "_{}_".format(side)
        return side


def get_opposite(side):
    """
    Args:
        side(str): The name from which we want to get the
            opposite side.

    Return:
        str: The side name.

    """
    if side == "R":
        opposite = "L"
        return opposite
    elif side == "_R_":
        opposite = "_L_"
        return opposite
    elif side == "L":
        opposite = "R"
        return opposite

    elif side == "_L_":
        opposite = "_R_"
        return opposite


def flip_side(name_string):
    side = get_side(name_string)
    op_side = get_opposite(side)
    new_name = name_string.replace(side,op_side)
    return new_name


def get_extension(name_string, with_undescore=True):
    """
    Args:
        name_string(str): The name from which we want to get the
            extension name.
        with_undescore(bool): It defines if the output should be
            with or without namespace.

    Return:
        str: The extesion name.

    """
    if not "_" in name_string:
        return ""
    else:
        extension = name_string.split("_")[-1]
        if with_undescore:
            extension = "_{}".format(extension)
        return extension


def get_index(name_string, with_undescore=True):
    """
    Args:
        name_string(str): The name from which we want to get the
            index.
        with_undescore(bool): It defines if the output should be
            with or without namespace.

    Return:
        str: The index.

    """
    if not "_" in name_string:
        return ""
    else:
        index = name_string.split("_")[2]
        if with_undescore:
            index = "_{}_".format(index)
        return index


def get_subdefinition(name_string, with_undescore=1):
    """
    Args:
        name_string(str): The name from which we want to get the
            subdefinition name.
        with_undescore(bool): It defines if the output should be
            with or without namespace.

    Return:
        str: The subdefinition name.

    """
    if not "_" in name_string:
        return ""
    else:
        subdefinition = name_string.split("_")[-2]
        if with_undescore:
            subdefinition = "_{}_".format(subdefinition)
        return subdefinition


def get_description(name_string, with_undescore=1):
    """
    Args:
        name_string(str): The name from which we want to get the
            description name.
        with_undescore(bool): It defines if the output should be
            with or without namespace.

    Return:
        str: The description component name.

    """
    if not "_" in name_string:
        return ""
    else:
        description = name_string.split("_")[-3]
        if with_undescore:
            description = "_{}_".format(description)
        return description


def remove_suffix(name_string, with_undescore=1):
    """
    Args:
        name_string(str): The name from which we want to remove
            the suffix.
        with_undescore(bool): It defines if the output should be
            with or without namespace.

    Return:
        str: The name without suffix.

    """

    if not "_" in name_string:
        return ""
    else:
        pattern = re.compile(r"_")
        matches = pattern.finditer(name_string)
        indices = []
        for match in matches:
            indices.append(match.start())
        if with_undescore:
            name_string = name_string[:indices[-1]+1]
        else:
            name_string = name_string[:indices[-1] ]
        return name_string


def change_suffix (name_string, new_suffix):
    """
    Args:
        name_string(str): The name from which we want to change
            the suffix.
        new_suffix(bool): The new suffix.

    Return:
        str: The name with the new suffix.

    """
    new_name = None
    if not "_" in name_string:
        return ""
    else:
        new_name = "{}{}".format(remove_suffix(name_string,
                                               with_undescore=1),
                                 new_suffix)
    return new_name


def renamer_change_suffix(objects, new_suffix):
    """
    It changes all the names of all the objects specified in the
    objects list.
    Args:
        objecte(str,pm.PyNode(),list): The object or objects
        from which we want to change the suffix.
        new_suffix(bool): The new suffix.

    Return:
        None.

    """

    if not isinstance(objects,list):
        objects = [objects]

    for obj in objects:
        new_name = change_suffix(obj.name(),
                                 new_suffix)
        pm.rename(obj,new_name)


def renamer_fix_suffix(object):
    """
    checks if the last character in the object name is a numeric, if yes, it gets pruned

    Args:
        objecte(str,pm.PyNode()): The object or objects
        from which we want to change the suffix.
        new_suffix(bool): The new suffix.

    Return:
        None.

    """

    if isinstance(object, str):
        object = pm.PyNode(object)

    obj_name= object.name()

    if obj_name[-1].isnumeric():
        return obj_name.rstrip(obj_name[-1])

    else:
        return obj_name