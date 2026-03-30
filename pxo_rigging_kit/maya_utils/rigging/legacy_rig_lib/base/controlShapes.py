"""
www.pixomondo.com
Date: 24 / 01 / 2022

controlShapes module
category : Rigging
subcategory : base
author : Michele Trabona / Rigging TD

"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from future import standard_library
standard_library.install_aliases()
import pymel.core as pm
import maya.OpenMaya as om

def _printControlCVsPositionsForFunctions(curve_obj):
    cvs = pm.ls("{}.cv[*]".format(curve_obj.name()),fl = 1)
    pos_list = []
    for cv in cvs:
         pos = pm.xform(cv,q = 1, t = 1, ws =1)
         pos_list.append(pos)
         print("    pos.append(({},{},{}))".format(pos[0],pos[1],pos[2]))

         #return pos_list

def printFunction_control_selection (curve_obj, function_name):
    print ("""def {} (scale = [1,1,1]):
    pos = []""".format(function_name))
    _printControlCVsPositionsForFunctions(curve_obj)
    print("""    new = pm.curve(d = 1, p = pos)
    components_list = "{}.cv[*]".format(new)
    pm.scaleComponents(scale[0],scale[1],scale[2], components_list, pivot = [0,0,0], rotation = [0,0,0])
    return new""")

def circle(normal = "x",scale = [1,1,1], degree = 3):

    normalID = {"x":[1,0,0],"y":[0,1,0],"z":[0,0,1]}
    new = pm.circle(nr = normalID[normal], ch = 0, r = 1.0, d = degree)[0]

    components_list = "{}.cv[*]".format(new)
    pm.scaleComponents(scale[0],scale[1],scale[2], components_list, pivot = [0,0,0], rotation = [0,0,0])
    return new

def square(normal = "x",scale = [1,1,1]):

    normalID = {"x":[1,0,0],"y":[0,1,0],"z":[0,0,1]}

    a = 1
    pos = []
    pos.append((a, 0, a))
    pos.append((a, 0, -a))
    pos.append((-a, 0, -a))
    pos.append((-a, 0, a))
    pos.append((a, 0, a))

    new = pm.curve(d = 1, p = pos)
    up_vector = [1,0,0]
    normal_in = normalID[normal]
    if normal_in[0] >normal_in[1] and normal_in[0] > normal_in [2]:
        up_vector = [0,1,0]
    ref_obj = pm.joint(n = "controlShapeAimRef_JNT", p = normal_in)
    pm.delete(pm.aimConstraint(ref_obj, new, aim = [0,1,0],u = up_vector, wu = [1,0,0],wut ="scene"))
    pm.delete(ref_obj)
    pm.makeIdentity (new, a = 1,r = 1)
    components_list = "{}.cv[*]".format(new)
    pm.scaleComponents(scale[0],scale[1],scale[2], components_list, pivot = [0,0,0], rotation = [0,0,0])
    return new

def locator(scale = [1,1,1]):
    a = 1
    pos = []
    pos.append((-a,0,0))
    pos.append((a,0,0))
    pos.append((0,0,0))
    pos.append((0,0,a))
    pos.append((0,0,-a))
    pos.append((0,0,0))
    pos.append((0,a,0))
    pos.append((0,-a,0))

    new = pm.curve(d = 1, p = pos)
    components_list = "{}.cv[*]".format(new)
    pm.scaleComponents(scale[0],scale[1],scale[2], components_list, pivot = [0,0,0], rotation = [0,0,0])
    return new


def exagon (scale = [1,1,1]):
    pos = []
    pos.append((0.499999970198,0.0,0.866025447845))
    pos.append((1.0,0.0,0.0))
    pos.append((0.500000238419,0.0,-0.866025328636))
    pos.append((-0.499999850988,0.0,-0.86602550745))
    pos.append((-1.0,0.0,-1.49011611938e-07))
    pos.append((-0.500000119209,0.0,0.866025388241))
    pos.append((0.499999970198,0.0,0.866025447845))
    new = pm.curve(d = 1, p = pos)
    components_list = "{}.cv[*]".format(new)
    pm.scaleComponents(scale[0],scale[1],scale[2], components_list, pivot = [0,0,0], rotation = [0,0,0])
    return new


def triangleZ (scale = [1,1,1]):
    pos = []
    pos.append((1.0,-0.65816622209,0.0))
    pos.append((-1.0,-0.65816622209,0.0))
    pos.append((-4.71812777032e-28,1.34183377791,0.0))
    pos.append((1.0,-0.65816622209,0.0))
    new = pm.curve(d = 1, p = pos)
    components_list = "{}.cv[*]".format(new)
    pm.scaleComponents(scale[0],scale[1],scale[2], components_list, pivot = [0,0,0], rotation = [0,0,0])
    return new


def triangleX (scale = [1,1,1]):
    pos = []
    pos.append((2.22044604925e-16,-0.65816622209,-1.0))
    pos.append((-2.22044604925e-16,-0.65816622209,1.0))
    pos.append((-1.04763481675e-43,1.34183377791,4.71812777032e-28))
    pos.append((2.22044604925e-16,-0.65816622209,-1.0))
    new = pm.curve(d = 1, p = pos)
    components_list = "{}.cv[*]".format(new)
    pm.scaleComponents(scale[0],scale[1],scale[2], components_list, pivot = [0,0,0], rotation = [0,0,0])
    return new

def cube (scale = [1,1,1]):
    pos = []
    pos.append((-1.0,-1.0,-1.0))
    pos.append((-1.0,-1.0,1.0))
    pos.append((1.0,-1.0,1.0))
    pos.append((1.0,-1.0,-1.0))
    pos.append((-1.0,-1.0,-1.0))
    pos.append((-1.0,1.0,-1.0))
    pos.append((1.0,1.0,-1.0))
    pos.append((1.0,-1.0,-1.0))
    pos.append((1.0,-1.0,1.0))
    pos.append((1.0,1.0,1.0))
    pos.append((1.0,1.0,-1.0))
    pos.append((1.0,1.0,1.0))
    pos.append((-1.0,1.0,1.0))
    pos.append((-1.0,-1.0,1.0))
    pos.append((-1.0,-1.0,-1.0))
    pos.append((-1.0,1.0,-1.0))
    pos.append((-1.0,1.0,1.0))
    new = pm.curve(d = 1, p = pos)
    components_list = "{}.cv[*]".format(new)
    pm.scaleComponents(scale[0],scale[1],scale[2], components_list, pivot = [0,0,0], rotation = [0,0,0])
    return new

def double_arrow_minimalX (scale = [1,1,1]):
    pos = []
    pos.append((0.0,-0.5,0.5))
    pos.append((0.0,0.5,0.5))
    pos.append((0.0,1.0,0.0))
    pos.append((0.0,0.5,-0.5))
    pos.append((0.0,-0.5,-0.5))
    pos.append((0.0,-1.0,0.0))
    pos.append((0.0,-0.5,0.5))
    new = pm.curve(d = 1, p = pos)
    components_list = "{}.cv[*]".format(new)
    pm.scaleComponents(scale[0],scale[1],scale[2], components_list, pivot = [0,0,0], rotation = [0,0,0])
    return new

def double_arrow_minimalZ (scale = [1,1,1]):
    pos = []
    pos.append((0.5,-0.5,1.11022302463e-16))
    pos.append((0.5,0.5,1.11022302463e-16))
    pos.append((0.0,1.0,0.0))
    pos.append((-0.5,0.5,-1.11022302463e-16))
    pos.append((-0.5,-0.5,-1.11022302463e-16))
    pos.append((0.0,-1.0,0.0))
    pos.append((0.5,-0.5,1.11022302463e-16))
    new = pm.curve(d = 1, p = pos)
    components_list = "{}.cv[*]".format(new)
    pm.scaleComponents(scale[0],scale[1],scale[2], components_list, pivot = [0,0,0], rotation = [0,0,0])
    return new

def V (scale = [1,1,1]):
    pos = []
    pos.append((-0.00473854064941,0.0466345310211,0.135740356445))
    pos.append((-0.00473854064941,1.95777526855,0.857591552734))
    pos.append((-0.00473854064941,1.95777526855,0.58701965332))
    pos.append((-0.00473854064941,0.393107261658,-0.00392242431641))
    pos.append((-0.00473854064941,1.95777526855,-0.575744018555))
    pos.append((-0.00473854064941,1.95777526855,-0.813390197754))
    pos.append((-0.00473854064941,0.0466345310211,-0.119942321777))
    pos.append((-0.00473854064941,0.0466345310211,0.135740356445))
    new = pm.curve(d = 1, p = pos)
    components_list = "{}.cv[*]".format(new)
    pm.scaleComponents(scale[0],scale[1],scale[2], components_list, pivot = [0,0,0], rotation = [0,0,0])
    return new

def S (scale = [1,1,1]):
    pos = []
    pos.append((-0.00473854064941,0.351375045776,0.56472240448))
    pos.append((-0.00473854064941,0.239031257629,0.270295944214))
    pos.append((-0.00473854064941,0.2015832901,0.0326760864258))
    pos.append((-0.00473854064941,0.222713890076,-0.110821380615))
    pos.append((-0.00473854064941,0.286158485413,-0.223641281128))
    pos.append((-0.00473854064941,0.383507270813,-0.296765213013))
    pos.append((-0.00473854064941,0.506323776245,-0.321122283936))
    pos.append((-0.00473854064941,0.610284156799,-0.305148696899))
    pos.append((-0.00473854064941,0.697451095581,-0.25720161438))
    pos.append((-0.00473854064941,0.780730438232,-0.166332168579))
    pos.append((-0.00473854064941,0.873080825806,-0.021538772583))
    pos.append((-0.00473854064941,1.01797996521,0.223195114136))
    pos.append((-0.00473854064941,1.14936515808,0.395281066895))
    pos.append((-0.00473854064941,1.27617500305,0.498077774048))
    pos.append((-0.00473854064941,1.41917007446,0.548140602112))
    pos.append((-0.00473854064941,1.60416183472,0.544385223389))
    pos.append((-0.00473854064941,1.78656173706,0.464305877686))
    pos.append((-0.00473854064941,1.92529907227,0.308722419739))
    pos.append((-0.00473854064941,1.99665100098,0.104689331055))
    pos.append((-0.00473854064941,2.00096191406,-0.1257371521))
    pos.append((-0.00473854064941,1.93196350098,-0.479958648682))
    pos.append((-0.00473854064941,1.68402954102,-0.479958648682))
    pos.append((-0.00473854064941,1.77312713623,-0.216209869385))
    pos.append((-0.00473854064941,1.8028263855,-0.0292874908447))
    pos.append((-0.00473854064941,1.78410247803,0.0991884994507))
    pos.append((-0.00473854064941,1.72793045044,0.203148841858))
    pos.append((-0.00473854064941,1.64332885742,0.271909179688))
    pos.append((-0.00473854064941,1.53939498901,0.294838104248))
    pos.append((-0.00473854064941,1.44931884766,0.278044700623))
    pos.append((-0.00473854064941,1.3702180481,0.227690963745))
    pos.append((-0.00473854064941,1.28953048706,0.132775306702))
    pos.append((-0.00473854064941,1.19461471558,-0.0176776123047))
    pos.append((-0.00473854064941,1.04773200989,-0.269155349731))
    pos.append((-0.00473854064941,0.914707260132,-0.44219329834))
    pos.append((-0.00473854064941,0.785332107544,-0.543561935425))
    pos.append((-0.00473854064941,0.63490562439,-0.592646179199))
    pos.append((-0.00473854064941,0.431745262146,-0.587304077148))
    pos.append((-0.00473854064941,0.231599845886,-0.495614852905))
    pos.append((-0.00473854064941,0.0838179969788,-0.316203231812))
    pos.append((-0.00473854064941,0.00831386566162,-0.0727916717529))
    pos.append((-0.00473854064941,0.00410891056061,0.174904174805))
    pos.append((-0.00473854064941,0.0827865982056,0.56472240448))
    pos.append((-0.00473854064941,0.351375045776,0.56472240448))
    new = pm.curve(d = 1, p = pos)
    components_list = "{}.cv[*]".format(new)
    pm.scaleComponents(scale[0],scale[1],scale[2], components_list, pivot = [0,0,0], rotation = [0,0,0])
    return new

def drop (scale = [1,1,1]):
    pos = []
    pos.append((-1.0,-6.12323426293e-17,1.57421433236e-15))
    pos.append((-0.946237325668,-5.79403292274e-17,0.320102125406))
    pos.append((-0.794029891491,-4.86203099035e-17,0.607293188572))
    pos.append((-0.557690560818,-3.41486990601e-17,0.829120695591))
    pos.append((-0.261294454336,-1.59996715151e-17,0.932576417923))
    pos.append((0.0620052181184,3.79156224942e-18,0.888724148273))
    pos.append((1.68220233917,-2.98023223877e-08,-1.98976783543e-09))
    pos.append((0.0620052181184,3.79156224942e-18,-0.888724148273))
    pos.append((-0.261294454336,-1.59996715151e-17,-0.932576417923))
    pos.append((-0.557690560818,-3.41486990601e-17,-0.829120695591))
    pos.append((-0.794029891491,-4.86203099035e-17,-0.607293188572))
    pos.append((-0.946237325668,-5.79403292274e-17,-0.320102125406))
    pos.append((-1.0,-6.12323426293e-17,1.57421433236e-15))
    new = pm.curve(d = 1, p = pos)
    components_list = "{}.cv[*]".format(new)
    pm.scaleComponents(scale[0],scale[1],scale[2], components_list, pivot = [0,0,0], rotation = [0,0,0])
    return new

def simpleSphere (scale = [1,1,1]):
    pos = []
    pos.append((0.0,1.0,0.0))
    pos.append((-0.433883756399,0.900968849659,-3.79313220833e-08))
    pos.append((-0.781831502914,0.623489797115,-6.83498839749e-08))
    pos.append((-0.974927902222,0.222520858049,-8.52309014476e-08))
    pos.append((-0.974927902222,-0.222520858049,-8.52309014476e-08))
    pos.append((-0.781831502914,-0.623489797115,-6.83498839749e-08))
    pos.append((-0.433883756399,-0.900968849659,-3.79313220833e-08))
    pos.append((0.0,-1.0,0.0))
    pos.append((0.433883756399,-0.900968849659,0.0))
    pos.append((0.781831502914,-0.623489797115,0.0))
    pos.append((0.974927902222,-0.222520858049,0.0))
    pos.append((0.974927902222,0.222520858049,0.0))
    pos.append((0.781831502914,0.623489797115,0.0))
    pos.append((0.433883756399,0.900968849659,0.0))
    pos.append((0.0,1.0,0.0))
    pos.append((5.68969795722e-08,0.900968849659,-0.433883756399))
    pos.append((1.02524815304e-07,0.623489797115,-0.781831502914))
    pos.append((1.27846348619e-07,0.222520858049,-0.974927902222))
    pos.append((1.27846348619e-07,-0.222520858049,-0.974927902222))
    pos.append((1.02524815304e-07,-0.623489797115,-0.781831502914))
    pos.append((5.68969795722e-08,-0.900968849659,-0.433883756399))
    pos.append((0.0,-1.0,0.0))
    pos.append((-1.89656610416e-08,-0.900968849659,0.433883756399))
    pos.append((-3.41749419874e-08,-0.623489797115,0.781831502914))
    pos.append((-4.26154507238e-08,-0.222520858049,0.974927902222))
    pos.append((-4.26154507238e-08,0.222520858049,0.974927902222))
    pos.append((-3.41749419874e-08,0.623489797115,0.781831502914))
    pos.append((-1.89656610416e-08,0.900968849659,0.433883756399))
    pos.append((0.0,1.0,0.0))
    new = pm.curve(d = 1, p = pos)
    components_list = "{}.cv[*]".format(new)
    pm.scaleComponents(scale[0],scale[1],scale[2], components_list, pivot = [0,0,0], rotation = [0,0,0])
    return new



