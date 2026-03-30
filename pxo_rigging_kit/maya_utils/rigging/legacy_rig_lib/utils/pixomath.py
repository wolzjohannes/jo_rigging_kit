"""
www.pixomondo.com
Date: 26 / 01 / 2022

pixomath module
category : Rigging
subcategory : utils
author : Michele Trabona / Rigging TD

"""
from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from builtins import int
from future import standard_library
standard_library.install_aliases()
from builtins import range
import math
import maya.api.OpenMaya as om
import pymel.core as pm

def angle_between(base,elementA,elementB):
    """
    It gets the angle between two elements.

    Args:
        base(pm.PyNode(),str): The base point of the vectors.
        elementA(pm.PyNode(),str): The element which defines toward
            what will point the first vector.
        elementB(pm.PyNode(),str): The element which defines toward
            what will point the second vector.
    Return:
        float: The angle in degrees.

    """
    if isinstance(base, str):
        base = pm.PyNode(base)
    if isinstance(elementA, str):
        elementA = pm.PyNode(elementA)
    if isinstance(elementB, str):
        elementB = pm.PyNode(elementB)
    base_vector = om.MVector(base.getTranslation(ws=1))
    elementA_vector = om.MVector(elementA.getTranslation(ws=1))
    elementB_vector = om.MVector(elementB.getTranslation(ws=1))

    vec_A = (elementA_vector - base_vector).normal()
    vec_B = (elementB_vector - base_vector).normal()

    angle_degrees = math.degrees(math.acos(vec_A * vec_B))

    return angle_degrees

def vector_between(elementA,
                   elementB,
                   normalize = 0,
                   reverse = 0):
    """
    It gets the vector that goes from A to B or reversed.

    Args:
        elementA(pm.PyNode(),str): The element which defines the
            point A of the vector.
        elementB(pm.PyNode(),str): The element which defines the
            point B of the vector.
        normalize(bool): It defines if the vector should or
            should not be normalized.
        reverse(bool): It defines if the vector should or
            should not be having the reverse direction.
    Return:
        MVector: vector from A to B

    """

    if isinstance(elementA, str):
        elementA = pm.PyNode(elementA)
    if isinstance(elementB, str):
        elementB = pm.PyNode(elementB)

    elementA_vector = om.MVector(elementA.getTranslation(ws=1))
    elementB_vector = om.MVector(elementB.getTranslation(ws=1))

    vector_AB = None

    if reverse:
        vector_AB = elementA_vector - elementB_vector
    else:
        vector_AB = elementB_vector - elementA_vector

    if normalize:
        vector_AB = vector_AB.normal()

    return vector_AB


def convert_PyMat_to_list (PyMat):
    list_mat = (PyMat[0][0], PyMat[0][1], PyMat[0][2], PyMat[0][3],
                 PyMat[1][0], PyMat[1][1], PyMat[1][2], PyMat[1][3],
                 PyMat[2][0], PyMat[2][1], PyMat[2][2], PyMat[2][3],
                 PyMat[3][0], PyMat[3][1], PyMat[3][2], PyMat[3][3])
    return list_mat


def lerp_zero_one(amount):
    """
    lerps amount times between zero and one.

    Args:
         amount(integer):
    Return:
        lerped_output(list): list of float values from zero to one
    """

    try:
        amount = int(amount)

    except:
        raise ValueError('input must be of type integer')

    lerped_output = list()

    for i in range(0, amount):
        lerped_output.append(float((1.0 / (amount - 1)) * i))

    return lerped_output
