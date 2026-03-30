# Import built-in modules
from importlib import reload
import logging
from typing import Optional

# Import third-party modules
from future import standard_library

# Import local modules
from pxo_rigging_kit.maya_utils.EWAW_rs.base_constructs import data
from pxo_rigging_kit.maya_utils.EWAW_rs.base_constructs import operator


reload(operator)

##########################################################
# GLOBALS                                                #
##########################################################

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)

standard_library.install_aliases()

_DEFAULT_DIC = {
    "build_layer": 3,
    "is_operator": True,
    "is_module": False,
    "is_built": False,

    "comp_type": "singleton",
    "build_axis": "+z",
    "comp_index": 0,
    "comp_name": "defaultSingle",
    "comp_parent_name": "",
    "comp_host_name": None,
    "comp_spaces_names": None,
    "op_name": "C_defaultSingle_000_root",
    "comp_side": "C",
    "misc_info": None,
    "comp_root_name": "|C_defaultSingle_000_root|C_defaultSingle_000_main_OPRT",
    "comp_root_transforms": [0.0, 0.0, 1.0, 0.0,
                             0.0, 1.0, 0.0, 0.0,
                             -1.0,0.0, 0.0, 0.0,
                             0.0, 0.0, 0.0, 1.0],
    "comp_lra_names": 1,
    "comp_subplacement_names": 0,
    "comp_lra_transforms": [
        (
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0
        ),
    ],
    "comp_subplacement_transforms": None
}

##########################################################
# CLASSES                                                #
##########################################################


class Main(operator.Main):
    def __init__(self,
                 data_container: Optional[data.DataContainer] = None,
                 data_dict: Optional[dict] = None
                 ):

        if not data_dict:
            data_dict = _DEFAULT_DIC
            _LOGGER.warning("using default data dict as fallback")

        # Here we define static and fixed arguments for this component operator.
        super(Main, self).__init__(
                                   data_container=data_container,
                                   data_dict=data_dict
        )

    def post_build_process(self):
        """
        Here we adjust the operator template to the needs of this operator.
        """

        pass


