"""
www.pixomondo.com
Date: 03 / 06 / 2022

shader module
category : Rigging
subcategory : utils
author : Christof Puehringer / Junior Rigging TD


''' to run it in scene:
assign_to_meshes_random()

clear_generated_materials()
'''




"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
#   external libraries
from builtins import round
from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import range
import pymel.core as pm
import random as random

# the use case for this module is to assign utility shaders for specific rigging tasks


def assign_shader(object_to_shade=None, material_name='', material_type='lambert', material_color=(0.5, 0.5, 0.5)):
    """ function to apply a shader and material to an object

    Args:
        object_to_shade(pm.PyNode): object to be shaded
        material_name(string): name of the material
        material_type(string): type of material assigned
        material_color(tuple): the color of the material

    Returns:
         material(pm.PyNode): the created maya material
    """

    if not object_to_shade:
        return None

    if material_name == '':
        material_name = 'default_{object}_msMat'.format(object=object_to_shade.shortName())

    #   Create Material
    material = pm.shadingNode(material_type, asShader=True, name=material_name)
    material.color.set(material_color)
    material.addAttr('scriptGenerated', dt='string')

    #   Create Surface Shader
    shader_name = "{}SurfaceShader".format(material_name)
    shader = pm.sets(renderable=True, noSurfaceShader=True, empty=True, name=shader_name)
    shader.addAttr('scriptGenerated', dt='string')

    #   Connect material to shader
    material.outColor.connect(shader.surfaceShader)

    #   Assign shader to objects
    pm.sets(shader, edit=True, forceElement=object_to_shade)

    return material


def catch_all_meshes():
    """ gets all polygonal meshes

    Returns:
        List: list of poly meshes as pm.PyNodes
    """
    return pm.ls(type='mesh')


def random_color(rounding_factor=4):
    """ generates a random tuple of values from 0-1
    Args:
        rounding_factor(int): the diget to which it will be rounded upon

    Returns:
        (tuple): tuple of random rounded numbers
    """
    return round(random.random(), rounding_factor), round(random.random(), rounding_factor), round(random.random(), rounding_factor)


def assign_to_meshes_random(poly_objects=catch_all_meshes()):
    """ assigns shader to list of pm.PyNodes

    Args:
        poly_objects(list): the objects to which materials will be applied to

    Returns:
        objects_changed(list): the objects that have been changed
    """
    #   check if input
    if not poly_objects:
        return None

    #   get rid of previous clowns
    clear_generated_materials()

    #   apply material and shader
    objects_changed = list()
    for obj in poly_objects:
        assign_shader(object_to_shade=obj, material_color=random_color())
        objects_changed.append(obj)

    return objects_changed


def clear_generated_materials():
    """ removes all module generated shaders and materials, and replaces them with lambert1

    Returns:
        effected_meshes(list): list of all meshes that were changed
    """
    #   get all shaders
    all_shaders = pm.ls(type='shadingEngine')

    #   sort for script-generated shaders
    generated_shaders = [x for x in all_shaders if x.hasAttr('scriptGenerated')]

    #   check if there are any
    if not generated_shaders:
        return None

    #   get script-generated materials
    generated_materials = [pm.listConnections(x.surfaceShader, d=False, s=True)[0] for x in generated_shaders]

    #   get all meshes and store them for deletion and reassignment
    effected_meshes = list()
    for shd in generated_shaders:
        index_amount = pm.getAttr(shd.dagSetMembers, multiIndices=True)

        if not index_amount:
            continue

        for i in range(0, len(index_amount)):
            attr_name = 'dagSetMembers[{}]'.format(str(i))

            connections = pm.listConnections(shd.attr(attr_name), d=False, s=True)
            if connections:
                effected_meshes.append(connections[0])

    #   apply lambert1 to meshes
    for nde in effected_meshes:
        print(nde)
        try:
            pm.sets('initialShadingGroup', edit=True, forceElement=nde)

        except:
            pass

    #   delete custom nodes
    pm.delete(generated_shaders, generated_materials)

    return effected_meshes


