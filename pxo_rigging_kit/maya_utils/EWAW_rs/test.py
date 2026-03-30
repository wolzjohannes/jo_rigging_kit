# testing the operator
from importlib import reload
from pxo_rigging_kit.maya_utils.EWAW_rs.base_constructs import data
from pxo_rigging_kit.maya_utils.EWAW_rs.components.quadleg import operator_
from pxo_rigging_kit.maya_utils.EWAW_rs.components.test_fk_chain import module_

reload(data)
reload(operator_)
reload(module_)

# init the front leg guide
FrontLeg = operator_.Main()

# init the back leg guide
BackLeg = operator_.Main()

# build the guides
FrontLeg.build()
BackLeg.build()

# build the guides
front_leg_data = FrontLeg.__dict__()
back_leg_data = BackLeg.__dict__()

# intermediary bullshit still needed to feed data from dict to dataclass
front_leg_info = data.DataContainer()
back_leg_info = data.DataContainer()

# update the dict
front_leg_info.dict_to_data(front_leg_data)
back_leg_info.dict_to_data(back_leg_data)

# init the front module
front_leg_module = module_.Main(DataContainer=front_leg_info)

# init the back module
back_leg_module = module_.Main(DataContainer=back_leg_info)

# build the module
front_leg_module.build()
back_leg_module.build()
