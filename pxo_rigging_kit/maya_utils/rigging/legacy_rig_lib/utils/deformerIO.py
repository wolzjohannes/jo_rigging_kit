from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from builtins import int
from future import standard_library
standard_library.install_aliases()
from builtins import range
import maya.OpenMaya as om
import maya.OpenMayaAnim as oma


# poly mesh and skinCluster name
shapeName = 'pSphere1'
clusterName = 'skinCluster1'

# get the MFnSkinCluster for clusterName
selList = om.MSelectionList()
selList.add(clusterName)
clusterNode = om.MObject()
selList.getDependNode(0, clusterNode)
skinFn = oma.MFnSkinCluster(clusterNode)

# get the MDagPath for all influence
infDags = om.MDagPathArray()
skinFn.influenceObjects(infDags)

# create a dictionary whose key is the MPlug indice id and
# whose value is the influence list id
infIds = {}
infs = []
for x in range(infDags.length()):
    infPath = infDags[x].fullPathName()
    infId = int(skinFn.indexForInfluenceObject(infDags[x]))
    infIds[infId] = x
    infs.append(infPath)

# get the MPlug for the weightList and weights attributes
wlPlug = skinFn.findPlug('weightList')
wPlug = skinFn.findPlug('weights')
wlAttr = wlPlug.attribute()
wAttr = wPlug.attribute()
wInfIds = om.MIntArray()

# the weights are stored in dictionary, the key is the vertId,
# the value is another dictionary whose key is the influence id and
# value is the weight for that influence
weights = {}
for vId in range(wlPlug.numElements()):
    vWeights = {}
    # tell the weights attribute which vertex id it represents
    wPlug.selectAncestorLogicalIndex(vId, wlAttr)

    # get the indice of all non-zero weights for this vert
    wPlug.getExistingArrayAttributeIndices(wInfIds)

    # create a copy of the current wPlug
    infPlug = om.MPlug(wPlug)
    for infId in wInfIds:
        # tell the infPlug it represents the current influence id
        infPlug.selectAncestorLogicalIndex(infId, wAttr)

        # add this influence and its weight to this verts weights
        try:
            vWeights[infIds[infId]] = infPlug.asDouble()
        except KeyError:
            # assumes a removed influence
            pass
    weights[vId] = vWeights