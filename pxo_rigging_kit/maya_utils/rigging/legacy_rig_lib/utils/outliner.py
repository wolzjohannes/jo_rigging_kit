"""
www.pixomondo.com
Date: 24 / 04 / 2022

outliner module
category : Rigging
subcategory : utils
author : Christof Puehringer / Junior Rigging TD
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


from future import standard_library
standard_library.install_aliases()
from builtins import range
import pymel.core as pmc

rgbValueDict = {'hidden': [1, .4, 0], 'joint': [0.9, 0.3, 0.5], 'ribbon': [0.1, 0.5, 0.7], 'joint':[1,0.3,.5]}

BASECOLORS = ['R', 'G', 'B']


def clause_check(input):
    """

    :param input:
    :return:
    """
    if isinstance(input, str) and input in list(rgbValueDict.keys()):
        return True
    else:
        return None


def color_outliner(function_in_scene, input=pmc.selected()):
    # this function takes the selected Items and recolors
    # them based on their function to the color values defined in rgbValueDict

    if clause_check(function_in_scene):

        for i in input:
            try:
                i.useOutlinerColor.set(True)

                for index, colorValue in enumerate(rgbValueDict[function_in_scene]):
                    i.attr('outlinerColor{color}'.format(color=BASECOLORS[index])).set(colorValue)

            except:
                pass


def decolor_outliner(input=pmc.selected()):
    """

    :param input:
    :return:
    """
    for i in input:
        try:
            i.useOutlinerColor.set(False)

            for index in range(0,3):
                i.attr('outlinerColor{color}'.format(color=BASECOLORS[index])).set(0)

        except:
            pass


def test_coloring():
    """

    :return:
    """

    color_outliner('hidden', input=pmc.selected())


def toggle_namespace(start=None):
    """this function searches all decendents of a node and toggles them in and out of a temporary namespace
    usage: when strings matter and you have a hierarchy that contains the same named objects

    :param start: string or pynode
    :return:True if namespace is on, False if namespace is off
    """
    if not start:
        sel = pmc.selected()
        if sel:
            start = sel[0]

    elif isinstance(start, str):
        start = pmc.PyNode(start)

    namespace_token = 'tempNamespace'
    all_hierarchy_nodes = pmc.listRelatives(start, allDescendents=True)
    all_hierarchy_nodes.append(start)

    space_check = pmc.namespace(exists=namespace_token)

    if not space_check:
        pmc.namespace(add=namespace_token)
        for x in all_hierarchy_nodes:
            pmc.rename(x, '{}:{}'.format(namespace_token, x.shortName()))
        return True

    else:
        for x in all_hierarchy_nodes:
            pmc.rename(x, '{}'.format(x.shortName().split(':')[-1]))

        pmc.namespace(rm=namespace_token)
        return False


def remove_namespace(start=None, namespace_token='tempNamespace'):
    """this function searches all decendents of a node and toggles them in and out of a temporary namespace
    usage: when strings matter and you have a hierarchy that contains the same named objects

    :param start: string or pynode
    :param namespace_token: string

    :return:True if namespace is on, False if namespace is off
    """
    if not start:
        sel = pmc.selected()
        if sel:
            start = sel[0]

    elif isinstance(start, str):
        start = pmc.PyNode(start)

    namespace_token = namespace_token
    all_hierarchy_nodes = pmc.listRelatives(start, allDescendents=True)
    all_hierarchy_nodes.append(start)

    space_check = pmc.namespace(exists=namespace_token)

    if space_check:
        for x in all_hierarchy_nodes:
            pmc.rename(x, '{}'.format(x.shortName().split(':')[-1]))

        pmc.namespace(rm=namespace_token)
        return False


def add_namespace(start=None, namespace_token='tempNamespace'):
    """this function searches all decendents of a node and toggles them in and out of a temporary namespace
    usage: when strings matter and you have a hierarchy that contains the same named objects

    :param start: string or pynode
    :param namespace_token: string
    :return:True if namespace is on, False if namespace is off
    """
    if not start:
        sel = pmc.selected()
        if sel:
            start = sel[0]

    elif isinstance(start, str):
        start = pmc.PyNode(start)

    namespace_token = namespace_token
    all_hierarchy_nodes = pmc.listRelatives(start, allDescendents=True)
    all_hierarchy_nodes.append(start)
    space_check = pmc.namespace(exists=namespace_token)

    if not space_check:
        pmc.namespace(add=namespace_token)
        for x in all_hierarchy_nodes:
            pmc.rename(x, '{}:{}'.format(namespace_token, x.shortName().split('|')[-1]))
        return True
