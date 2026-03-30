"""
www.pixomondo.com
Date: 03 / 02 / 2022

nodes module
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
from builtins import zip
from builtins import object
import pymel.core as pm
from . import name
from pxo_rigging_kit.maya_utils.rigging.legacy_rig_lib.utils import info_geo

def create_remap_val_node(input,
                       inputMin,
                       inputMax,
                       outputMin=0,
                       outputMax=1,
                       output=None,
                       name="remapValue"):
    """
    Create Set Range Node.

    Args:
        input(str, float): The object and the attribute we need
            to connect to the range node or a float value.
            Ex. 'cube.ty'
        inputMin(str,float): The object and the attribute we need
            to connect to the range node or a float value.
            Ex. 'cube.ty'
        inputMax(str,float): The object and the attribute we need
            to connect to the range node or a float value.
            Ex. 'cube.ty'
        outputMin(str,float): The object and the attribute we need
            to connect to the range node or a float value.
            Ex. 'cube.ty'
        outputMax(str,float): The object and the attribute we need
            to connect to the range node or a float value.
            Ex. 'cube.ty'
        output(str): The object and the attribute we need
            to connect to.
            Ex. 'cube.ty'
        name(str): The name of the range node.

    Return:
        pm.PyNode(): The range node name.

    """
    node = pm.createNode("remapValue", n=name)

    if not isinstance(input, list):
        input = [input]

    for item in input:
        if (isinstance(item, str)
                or isinstance(item, str)
                or isinstance(item, pm.Attribute)):
            pm.connectAttr(item, node + ".inputValue" )
        else:
            pm.setAttr(node + ".inputValue", item)

        if (isinstance(inputMin, str)
                or isinstance(inputMin, str)
                or isinstance(inputMin, pm.Attribute)):
            pm.connectAttr(inputMin, node + ".inputMin" )
        else:
            pm.setAttr(node + ".inputMin" , inputMin)

        if (isinstance(inputMax, str)
                or isinstance(inputMax, str)
                or isinstance(inputMax, pm.Attribute)):
            pm.connectAttr(inputMax, node + ".inputMax" )
        else:
            pm.setAttr(node + ".inputMax" , inputMax)

        if (isinstance(outputMin, str)
                or isinstance(outputMin, str)
                or isinstance(outputMin, pm.Attribute)):
            pm.connectAttr(outputMin, node + ".outputMin" )
        else:
            pm.setAttr(node + ".outputMin", outputMin)

        if (isinstance(outputMax, str)
                or isinstance(outputMax, str)
                or isinstance(outputMax, pm.Attribute)):
            pm.connectAttr(outputMax, node + ".outputMax" )
        else:
            pm.setAttr(node + ".outputMax" , outputMax)

    if output:
        if not isinstance(output, list):
            output = [output]
        for out in output:
            pm.connectAttr(node + ".outValue" , out, f=True)

    return node


###################
#Bifrost Nodes Wraps

#wrap of meshSpreadDef

class meshSpreadDefBifrost(object):
    def __init__(self,
                 node_name = None,
                 meshes = None,
                 parent_base = None,
                 replace = None
                 ):
        self.node_name = node_name
        self.meshes = meshes
        self.parent_base = parent_base
        self.replace = replace

        self.combine_and_connect()

    def combine_and_connect(self):
        combined_mesh  = info_geo.combine_meshes_list(meshes=self.meshes)
        self.connect_combined(combined_mesh, self.node_name)
        meshes_copy_grp = pm.group(n = 'baseMeshes_grp', em = 1, w = 1)
        print(self.meshes)
        copied_meshes = info_geo.copy_meshes_list(meshes=self.meshes,
                                                  searchReplace=self.replace,
                                                  parent = meshes_copy_grp)
        self.connect_geos_input_output(copied_meshes,
                                       self.meshes,
                                       self.node_name)
        self.set_vertices_relation(copied_meshes,combined_mesh,self.node_name)
    @staticmethod
    def connect_combined(mesh, bifrost_node):
        pm.connectAttr('{}.outMesh'.format(mesh), '{}.main_geo'.format(bifrost_node),f =1)
        print ("Combined mesh: {} connected to -----> Bifrost node: {}".format(
            mesh,
            bifrost_node))
    @staticmethod
    def connect_geos_input_output(in_geos, out_geos, bifrost_node):
        bifrost_to_maya = pm.createNode("bifrostGeoToMaya")
        pm.connectAttr( '{}.out_geometry'.format(bifrost_node),'{}.bifrostGeo'.format(bifrost_to_maya), f=1)
        for it, (in_g, out_g) in enumerate(zip(in_geos,out_geos)):
            pm.connectAttr('{}.outMesh'.format(in_g), '{}.children[{}]'.format(bifrost_node,it), f=1)
            pm.connectAttr('{}.mayaMesh[{}]'.format(bifrost_to_maya,it), '{}.inMesh'.format(out_g), f=1)

    @staticmethod
    def set_vertices_relation(base_meshes, combined_mesh, bifrost_node):
        geos_association_tuples = {}
        geo_order = []
        for geo in base_meshes:
            vert_associatiion_tuple = info_geo.getting_matching_verices(combined_mesh.name(), geo.name(), tollerance=0.01)
            geos_association_tuples[geo.name()] = vert_associatiion_tuple
            geo_order.append(geo.name())
        geos_association_tuples['geo_list'] = geo_order
        for main_it, key in enumerate(geos_association_tuples['geo_list']):
            for second_it, (main_id, child_id) in enumerate(geos_association_tuples[key]):
                pm.setAttr('{}.main_geo_IDs[{}].main_geo_IDs_A[{}]'.format(bifrost_node,
                                                                           main_it,
                                                                           second_it), main_id)