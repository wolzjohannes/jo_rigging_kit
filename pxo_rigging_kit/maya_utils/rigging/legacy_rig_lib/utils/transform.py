"""
www.pixomondo.com
Date: 04 / 02 / 2022

transform module
category : Rigging
subcategory : utils
author : Michele Trabona / Rigging TD

"""
from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import range
from past.utils import old_div
import pymel.core as pm
from pymel.core import datatypes
from . import name
import maya.api.OpenMaya as om




def make_extra_buffer (element,
                       extra_name,
                       buffer_number = 1,
                       translate_to= 0,
                       move_to = 1):
    """
    It makes as many buffer groups as we specify with the
    specified buffer name.

    Args:
        element(pm.PyNode(), str): The element on which we
            want to make the buffer on.
        extra_name(str): The name of the extra buffer group.
        buffer_number(int): The number of buffer groups.

    Return:
        list: The extra buffer groups' list.

    """


    if isinstance(element, str):
        element = pm.PyNode(element)
    buffers_list = []
    for it in range(buffer_number):
        buffer_name = "{}{}{}_{}_default_GRP".format(name.get_component(element.name(),
                                                                        with_undescore=False),
                                                     name.get_side(element.name()),
                                                     it,
                                                     extra_name)
        buff_grp = pm.group(n = buffer_name,em = 1, w = 1)
        parent = pm.listRelatives(element,p = 1)
        if len(parent) > 0 :
            parent = parent[0]
        else:
            parent = None

        if translate_to:
            pm.delete(pm.pointConstraint(element, buff_grp, mo=0))
            pm.parent(buff_grp,parent)
            pm.parent(element,buff_grp)
        if move_to:
            pm.delete(pm.parentConstraint(element,buff_grp,mo=0))
            pm.parent(buff_grp,parent)
            pm.parent(element,buff_grp)

        buffers_list.append(buff_grp)

        return buffers_list


def elements_position(elements):
    positions_list = []
    for e in elements:
        pos = pm.xform(e, q=1, t=1, ws=1)
        positions_list.append(pos)
    return positions_list


def get_cv_position(curve, output = 1):
    cvs_number = pm.ls(curve.cv[:], fl = 1)
    cv_pos_list = []
    for cv in cvs_number:
        cv_pos = pm.xform(cv,q = 1,t =1,ws = 1)
        if output == 1:
            cv_pos = datatypes.Vector(cv_pos)
        cv_pos_list.append(cv_pos)

    return cv_pos_list


def elements_matrices(elements):
    if not isinstance(elements,list):
        elements = [elements]
    matrices_list = []
    for e in elements:
        if isinstance(e,str):
            e = pm.PyNode(e)
        matrix = e.getMatrix(ws = 1)
        matrices_list.append(matrix)
    return matrices_list


def createFollicle(geo, uPos=0.0, vPos=0.0, name=False):
    if not name:
        prefix = geo.name().strip('Shape')
        number = len(pm.ls(prefix + '*_flcShape', type='follicle'))
        number_spaced = str(number).zfill(3)
        name = '{}_{}_flc'.format(prefix, number_spaced)

    flcl = pm.createNode('follicle', name=name + 'Shape')

    try:
        geo.local.connect(flcl.inputSurface)

    except AttributeError:
        geo.outMesh.connect(flcl.inputMesh)

    geo.worldMatrix[0].connect(flcl.inputWorldMatrix)

    flcl.outRotate.connect(flcl.getParent().rotate)
    flcl.outTranslate.connect(flcl.getParent().translate)

    flcl.parameterU.set(uPos)
    flcl.parameterV.set(vPos)
    flcl.getParent().t.lock()
    flcl.getParent().r.lock()
    flcl.getParent().rename(name)

    return flcl


def attachToGeo(*args, **kwargs):
    selected = pm.selected()

    if not args:
        args = selected

    if len(args):
        remaining = []

        for node in args:
            sel = [x for x in node if isinstance(x, pm.MeshFace)]
            faces = [x for sublist in sel for x in sublist]

            if len(faces):
                geo = pm.PyNode(node.name().split('.')[0])

                if geo.type() == 'transform':
                    geo = geo.getShape()

                cp = pm.shadingNode("closestPointOnMesh",
                                    asUtility=True,
                                    n="cpom")

                geo.outMesh.connect(cp.inMesh)
                geo.worldMatrix.connect(cp.inputMatrix)

                for face in faces:
                    pm.select(face, r=True)

                    # Get face's bounding box.
                    pev = pm.polyEvaluate(bc=True)

                    # Get the centre of the face
                    minX, maxX = pev[0]
                    minY, maxY = pev[1]
                    minZ, maxZ = pev[2]

                    faceCentre = ((
                        (old_div((minX + maxX), 2)),
                        (old_div((minY + maxY), 2)),
                        (old_div((minZ + maxZ), 2))
                    ))

                    cp.inPosition.set(faceCentre)
                    flcl = createFollicle(geo,
                                          cp.u.get(),
                                          cp.v.get())

                pm.delete(cp)

            else:
                remaining.append(node)

        if len(remaining) > 1:

            geo = remaining[-1]
            nodes = remaining[:-1]
            nodePos = []

            for node in nodes:
                nodePos.append(node.getTranslation(space='world'))

            if geo.type() == 'transform':
                geo = geo.getShape()

            if geo.type() == 'nurbsSurface':
                cp = pm.createNode('closestPointOnSurface',
                                   n='_'.join((geo.name(), 'cpos')))

                geo.worldSpace >> cp.inputSurface

                for i in range(0, len(nodes)):
                    cp.inPosition.set(nodePos[i])
                    flcl = createFollicle(geo,
                                          cp.parameterU.get(),
                                          cp.parameterV.get(),
                                          name=nodes[i].name())

                    pm.parent(nodes[i], flcl.getParent())

                pm.delete(cp)
                pm.select(selected)

            elif geo.type() == 'mesh':
                cp = pm.shadingNode("closestPointOnMesh",
                                    asUtility=True,
                                    n="cpom")

                geo.outMesh.connect(cp.inMesh)
                geo.worldMatrix.connect(cp.inputMatrix)

                for i in range(0, len(nodes)):
                    cp.inPosition.set(nodePos[i])
                    flcl = createFollicle(geo,
                                          cp.u.get(),
                                          cp.v.get(),
                                          name=nodes[i].name())

                    pm.parent(nodes[i], flcl.getParent())
                pm.delete(cp)
                pm.select(selected)

    return flcl


def getSymmetricalTransform(t, axis="yz", fNegScale=False):
    """Get the symmetrical tranformation

    Get the symmetrical tranformation matrix from a define 2 axis mirror
    plane. exp:"yz".

    Arguments:
        t (matrix): The transformation matrix to mirror.
        axis (str): The mirror plane.
        fNegScale(bool):  This function is not yet implemented.

    Returns:
        matrix: The symmetrical tranformation matrix.
    """

    if axis == "yz":
        mirror = datatypes.TransformationMatrix(-1, 0, 0, 0,
                                                0, 1, 0, 0,
                                                0, 0, 1, 0,
                                                0, 0, 0, 1)

    elif axis == "xy":
        mirror = datatypes.TransformationMatrix(1, 0, 0, 0,
                                                0, 1, 0, 0,
                                                0, 0, -1, 0,
                                                0, 0, 0, 1)
    elif axis == "zx":
        mirror = datatypes.TransformationMatrix(1, 0, 0, 0,
                                                0, -1, 0, 0,
                                                0, 0, 1, 0,
                                                0, 0, 0, 1)
    else:
        mirror= datatypes.TransformationMatrix(1, 0, 0, 0,
                                                0, 1, 0, 0,
                                                0, 0, 1, 0,
                                                0, 0, 0, 1)

    t *= mirror

    matrix = om.MMatrix(t)

    return t

def rivet_on_face(mesh, dummy):
    """ uses pymel to get the uv position of closest faceCenter and then applies a nFollicle to it

    Args:

        dummy(PyNode): the object where the control will be snapped to
        side(str): extracted from the for loop
        component(str): extracted from the for loop
        index(str): extracted from the for loop

    Return:
        fol_transform(PyNode): transform node of the created Follicle
    """
    if isinstance(mesh,str):
        mesh = pm.PyNode(mesh)

    if isinstance(dummy,str):
        dummy = pm.PyNode(dummy)

    position = dummy.getTranslation(w =1)

    face_id_ah = mesh.getShape().getClosestPoint(position, space= 'world')[1]

    pm.select(mesh.name() + '.f[' + str(face_id_ah) + ']')

    fol = attachToGeo()
    fol.v.set(1)
    fol_transform = pm.listRelatives(fol, p= 1)
    pm.rename(fol_transform, dummy.name().replace("_loc","_rivFol"))
    return fol_transform