"""
www.pixomondo.com
Date: 09 / 06 / 2022

attributes module
category : Rigging
subcategory : utils
author : Christof Puehringer / Rigging TD

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from future import standard_library
standard_library.install_aliases()
import logging as log

import maya.cmds as cmds
import maya.mel as mel

log.basicConfig(level=log.INFO)


def clean_scene():
    remove_unknowns()
    remove_unused()


def remove_unknowns():
    """ function to clean out all the unknowns

    Return:
        deleted_objects(dict): returns all plugins and nodes which are eliminated
    """
    nodes_formatted = 'ZERO'
    plugins_formatted = 'ZERO'

    #   gets and removes all

    plugins_deleted = remove_unknown_plugins()
    nodes_deleted = remove_unknown_nodes()

    #   format for output
    if nodes_deleted:
        nodes_formatted = '\n'.join(nodes_deleted)

    if plugins_deleted:
        plugins_formatted = '\n'.join(plugins_deleted)

    #   give out-liner output
    log.info('\n\n\nDELETED ITEMS:\n\n*** Nodes:\n{}\n\n*** PlugIns:\n{}\n\n\n'.format(nodes_formatted,
                                                                                       plugins_formatted))

    #   give function output
    outputs = {'nodes': nodes_deleted, 'plugins': plugins_deleted}
    return outputs


def remove_unused():
    """

    :return:
    """
    mel.eval('MLdeleteUnused;')


def remove_unknown_plugins():

    # unknown plugins deletion
    plugins_unknown = cmds.unknownPlugin(query=1, list=1)
    plugins_deleted=list()
    #   check and delete

    if not plugins_unknown:
        return

    for plg in plugins_unknown:
        try:
            cmds.unknownPlugin(plg, remove=True)
            plugins_deleted.append(plg)
        except RuntimeError as error:
            log.warning("Unknown plugin cannot be removed due to ERROR: {}".format(error))
    return plugins_deleted


def remove_unknown_nodes():
    nodes_unknown = cmds.ls(type="unknown")
    nodes_deleted = list()

    #   check and delete
    if not nodes_unknown:
        return

    for nde in nodes_unknown:
        cmds.lockNode(nde, lock=False)
        cmds.delete(nde)
        nodes_deleted.append(nde)

    return nodes_deleted


if __name__ == "__main":
    clean_scene()