# Import built-in modules
from importlib import reload

# Import third-party modules
import pymel.core as pmc

# Import local modules
from pxo_rigging_kit.maya_utils import attributes_utils
from pxo_rigging_kit.maya_utils import dag_utils
from pxo_rigging_kit.maya_utils.rigging import rig_utils

reload(rig_utils)

def create_fleshy_eye_fake(eye_lid_fk_control, side, fleshy_eye_root_list):
    root_buffer_groups = [(root, rig_utils.create_transfrom_on_position(eye_lid_fk_control)) for root in fleshy_eye_root_list]
    attributes_utils.add_pxo_separator_attr(eye_lid_fk_control, "{}_fleshy_eye_attributes".format(side))
    for index, root_tuple in enumerate(root_buffer_groups):
        trs = root_tuple[1]
        root = root_tuple[0]
        buffer_grp = dag_utils.create_buffer_groups([trs])[0]
        parent_nd = root.getParent()
        parent_nd.addChild(buffer_grp)
        trs.addChild(root)
        attr_name = "fleshy_eye_mult_{}".format(index)
        eye_lid_fk_control.addAttr(attr_name, type="float", min=0.0, max=1.0, dv=1.0, keyable=True)
        angle_mult = pmc.createNode("animBlendNodeAdditiveRotation")
        eye_lid_fk_control.rotate.connect(angle_mult.inputA)
        eye_lid_fk_control.attr(attr_name).connect(angle_mult.weightA)
        angle_mult.output.connect(trs.rotate)

fleshy_eye_root_list = pmc.ls("fleshyEye_L*_root")
create_fleshy_eye_fake(pmc.PyNode("eye_L_0_fk_ctl"), "L", fleshy_eye_root_list)
