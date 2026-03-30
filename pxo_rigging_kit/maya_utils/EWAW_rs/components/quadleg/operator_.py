# Import built-in modules
import logging

from importlib import reload
from typing import Optional

# Import third-party modules
from future import standard_library

# Import local modules
from pxo_rigging_kit.maya_utils.EWAW_rs.base_constructs import operator
from pxo_rigging_kit.maya_utils.EWAW_rs.base_constructs import data


reload(operator)

##########################################################
# GLOBALS
##########################################################

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)
standard_library.install_aliases()

_DEFAULT_DIC = {
    "build_layer": 0,
    "is_operator": True,
    "is_module": False,
    "is_built": False,
    "comp_type": "quadleg",
    "build_axis": "-y",
    "comp_index": 0,
    "comp_name": "quadlegDefault",
    "comp_parent_name": "",
    "comp_host_name": None,
    "comp_spaces_names": "",
    "op_name": "C_quadlegDefault_000_root",
    "comp_side": "C",
    "misc_info": None,
    "comp_root_name": "|C_quadlegDefault_000_root|C_quadlegDefault_000_main_OPRT",
    "comp_root_transforms": [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 45.819447648300084, 0.0, 1.0
    ],
    "comp_lra_names": (
        "|C_quadlegDefault_000_root|C_quadlegDefault_000_main_OPRT|C_quadlegDefault_000_main_LRA",
        "|C_quadlegDefault_000_root|C_quadlegDefault_000_main_OPRT|C_quadlegDefault_000_sub000_opr|C_quadlegDefault_000_sub000_lra",
        "|C_quadlegDefault_000_root|C_quadlegDefault_000_main_OPRT|C_quadlegDefault_000_sub000_opr|C_quadlegDefault_000_sub001_opr|C_quadlegDefault_000_sub001_lra",
        "|C_quadlegDefault_000_root|C_quadlegDefault_000_main_OPRT|C_quadlegDefault_000_sub000_opr|C_quadlegDefault_000_sub001_opr|C_quadlegDefault_000_sub002_opr|C_quadlegDefault_000_sub002_lra",
        "|C_quadlegDefault_000_root|C_quadlegDefault_000_main_OPRT|C_quadlegDefault_000_sub000_opr|C_quadlegDefault_000_sub001_opr|C_quadlegDefault_000_sub002_opr|C_quadlegDefault_000_sub003_opr|C_quadlegDefault_000_sub003_lra",
        "|C_quadlegDefault_000_root|C_quadlegDefault_000_main_OPRT|C_quadlegDefault_000_sub000_opr|C_quadlegDefault_000_sub001_opr|C_quadlegDefault_000_sub002_opr|C_quadlegDefault_000_sub003_opr|C_quadlegDefault_000_sub004_opr|C_quadlegDefault_000_sub004_lra",
        "|C_quadlegDefault_000_root|C_quadlegDefault_000_main_OPRT|C_quadlegDefault_000_sub000_opr|C_quadlegDefault_000_sub001_opr|C_quadlegDefault_000_sub002_opr|C_quadlegDefault_000_sub003_opr|C_quadlegDefault_000_sub004_opr|C_quadlegDefault_000_sub005_opr|C_quadlegDefault_000_sub005_lra",
        "|C_quadlegDefault_000_root|C_quadlegDefault_000_main_OPRT|C_quadlegDefault_000_sub000_opr|C_quadlegDefault_000_sub001_opr|C_quadlegDefault_000_sub002_opr|C_quadlegDefault_000_sub003_opr|C_quadlegDefault_000_sub004_opr|C_quadlegDefault_000_sub005_opr|C_quadlegDefault_000_sub006_opr|C_quadlegDefault_000_sub006_lra",
        "|C_quadlegDefault_000_root|C_quadlegDefault_000_main_OPRT|C_quadlegDefault_000_sub000_opr|C_quadlegDefault_000_sub001_opr|C_quadlegDefault_000_sub002_opr|C_quadlegDefault_000_sub003_opr|C_quadlegDefault_000_sub004_opr|C_quadlegDefault_000_sub005_opr|C_quadlegDefault_000_sub006_opr|C_quadlegDefault_000_sub007_opr|C_quadlegDefault_000_sub007_lra",
        "|C_quadlegDefault_000_root|C_quadlegDefault_000_main_OPRT|C_quadlegDefault_000_sub000_opr|C_quadlegDefault_000_sub001_opr|C_quadlegDefault_000_sub002_opr|C_quadlegDefault_000_sub003_opr|C_quadlegDefault_000_sub004_opr|C_quadlegDefault_000_sub005_opr|C_quadlegDefault_000_sub006_opr|C_quadlegDefault_000_sub007_opr|C_quadlegDefault_000_sub008_opr|C_quadlegDefault_000_sub008_lra"
    ),
    "comp_subplacement_names": (
        "|C_quadlegDefault_000_root|C_quadlegDefault_000_main_OPRT|C_quadlegDefault_000_sub000_opr",
        "|C_quadlegDefault_000_root|C_quadlegDefault_000_main_OPRT|C_quadlegDefault_000_sub000_opr|C_quadlegDefault_000_sub001_opr",
        "|C_quadlegDefault_000_root|C_quadlegDefault_000_main_OPRT|C_quadlegDefault_000_sub000_opr|C_quadlegDefault_000_sub001_opr|C_quadlegDefault_000_sub002_opr",
        "|C_quadlegDefault_000_root|C_quadlegDefault_000_main_OPRT|C_quadlegDefault_000_sub000_opr|C_quadlegDefault_000_sub001_opr|C_quadlegDefault_000_sub002_opr|C_quadlegDefault_000_sub003_opr",
        "|C_quadlegDefault_000_root|C_quadlegDefault_000_main_OPRT|C_quadlegDefault_000_sub000_opr|C_quadlegDefault_000_sub001_opr|C_quadlegDefault_000_sub002_opr|C_quadlegDefault_000_sub003_opr|C_quadlegDefault_000_sub004_opr",
        "|C_quadlegDefault_000_root|C_quadlegDefault_000_main_OPRT|C_quadlegDefault_000_sub000_opr|C_quadlegDefault_000_sub001_opr|C_quadlegDefault_000_sub002_opr|C_quadlegDefault_000_sub003_opr|C_quadlegDefault_000_sub004_opr|C_quadlegDefault_000_sub005_opr",
        "|C_quadlegDefault_000_root|C_quadlegDefault_000_main_OPRT|C_quadlegDefault_000_sub000_opr|C_quadlegDefault_000_sub001_opr|C_quadlegDefault_000_sub002_opr|C_quadlegDefault_000_sub003_opr|C_quadlegDefault_000_sub004_opr|C_quadlegDefault_000_sub005_opr|C_quadlegDefault_000_sub006_opr",
        "|C_quadlegDefault_000_root|C_quadlegDefault_000_main_OPRT|C_quadlegDefault_000_sub000_opr|C_quadlegDefault_000_sub001_opr|C_quadlegDefault_000_sub002_opr|C_quadlegDefault_000_sub003_opr|C_quadlegDefault_000_sub004_opr|C_quadlegDefault_000_sub005_opr|C_quadlegDefault_000_sub006_opr|C_quadlegDefault_000_sub007_opr",
        "|C_quadlegDefault_000_root|C_quadlegDefault_000_main_OPRT|C_quadlegDefault_000_sub000_opr|C_quadlegDefault_000_sub001_opr|C_quadlegDefault_000_sub002_opr|C_quadlegDefault_000_sub003_opr|C_quadlegDefault_000_sub004_opr|C_quadlegDefault_000_sub005_opr|C_quadlegDefault_000_sub006_opr|C_quadlegDefault_000_sub007_opr|C_quadlegDefault_000_sub008_opr"
    ),
    "comp_lra_transforms": [
        (
            0.0, -1.0, 0.0, 0.0,
            1.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 45.819447648300084, 0.0, 1.0
        ),
        (
            0.0, -0.8674624771227475, 0.49750261384646666, 0.0,
            2.775557561562891e-16, 0.49750261384646677, 0.8674624771227475, 0.0,
            -0.9999999999999998, 2.775557561562891e-16, 2.220446049250313e-16, 0.0,
            0.0, 44.714357179312856, 0.0, 1.0
        ),
        (
            0.0, -0.6157509039341869, -0.7879408761475899, 0.0,
            -1.5509107624155381e-16, -0.7879408761475899, 0.6157509039341869, 0.0,
            -1.0, 7.003852650462277e-17, -1.4663686756752218e-16, 0.0,
            0.0, 28.49410539894538, 9.30255529293489, 1.0
        ),
        (
            1.1102230246251565e-16, -0.8979042955785301, 0.44019072682375243, 0.0,
            -5.551115123125783e-17, 0.4401907268237525, 0.8979042955785301, 0.0,
            -1.0, -5.551115123125783e-17, 0.0, 0.0,
            0.0, 16.176440409199003, -6.459649329261833, 1.0
        ),
        (
            0.0, -0.2425356250363329, 0.9701425001453319, 0.0,
            -6.938893903907227e-17, 0.9701425001453319, 0.2425356250363329, 0.0,
            -1.0, -6.938893903907227e-17, 0.0, 0.0,
            0.0, 3.0, 0.0, 1.0
        ),
        (
            0.0, -0.7071067811865476, 0.7071067811865476, 0.0,
            -1.1102230246251565e-16, 0.7071067811865475, 0.7071067811865476, 0.0,
            -1.0, -1.1102230246251565e-16, -2.220446049250313e-16, 0.0,
            0.0, 2.0, 4.0, 1.0
        ),
        (
            0.0, 0.0, -1.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            1.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 6.0, 1.0
        ),
        (
            -0.0006099719918605806, 0.0, 0.9999998139670674, 0.0,
            0.0, 1.0, 0.0, 0.0,
            -0.9999998139670674, 0.0, -0.0006099719918605806, 0.0,
            0.0, 0.0, -2.0, 1.0
        ),
        (
            -1.0, 0.0, -1.2246467991473532e-16, 0.0,
            0.0, 1.0, 0.0, 0.0,
            1.2246467991473532e-16, 0.0, -1.0, 0.0,
            2.0, 0.0, 2.0, 1.0
        ),
        (
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            -2.0, 0.0, 2.0, 1.0
        )
    ],
    "comp_subplacement_transforms": [
        (
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 44.714357179312856, 0.0, 1.0
        ),
        (
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 28.49410539894538, 9.30255529293489, 1.0
        ),
        (
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 16.176440409199003, -6.459649329261833, 1.0
        ),
        (
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 3.0, 0.0, 1.0
        ),
        (
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 2.0, 4.0, 1.0
        ),
        (
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 6.0, 1.0
        ),
        (
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, -2.0, 1.0
        ),
        (
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            2.0, 0.0, 2.0, 1.0
        ),
        (
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            -2.0, 0.0, 2.0, 1.0
        )
    ]
}

##########################################################
# FUNCTIONS
##########################################################


class Main(operator.Main):
    def __init__(self,
                 data_container: Optional[data.DataContainer] = None,
                 data_dict: Optional[dict] = None,
                 ):

        if not data_dict:
            data_dict = _DEFAULT_DIC
            _LOGGER.warning("using default data dict as fallback")

        # Here we define static and fixed arguments for this component operator.
        super(Main, self).__init__(
                data_container=data_container,
                data_dict=data_dict,
        )

    def post_build_process(self):
        """
        Here we adjust the operator template to the needs of this operator.
        """

        # Rename the sub ctrls and lra nodes
        # Be aware that the lra nodes count == sub_ctrl_count + 1
        # Because of the diamond main control.
        # That why we pop out the first lra node from the lra nodes.
        # We just want to rename the lra nodes under sub ctrls.

        # Pre pose the sub_ctrl
        """
        self.main_opr_node.setMatrix((1.0, 0.0, 0.0, 0.0,
                                      0.0, 1.0, 0.0, 0.0,
                                      0.0, 0.0, 1.0, 0.0,
                                      3., 88, -44, 1.0
                                      ), ws=True
                                     )

        self.sub_opr_nodes[0].setMatrix((1.0, 0.0, 0.0, 0.0,
                                         0.0, 1.0, 0.0, 0.0,
                                         0.0, 0.0, 1.0, 0.0,
                                         11.8, 88, -44, 1.0
                                         ), ws=True
                                        )

        self.sub_opr_nodes[1].setMatrix((1.0, 0.0, 0.0, 0.0,
                                         0.0, 1.0, 0.0, 0.0,
                                         0.0, 0.0, 1.0, 0.0,
                                         11.8, 52.4, -47.8, 1.0
                                         ), ws=True
                                        )

        self.sub_opr_nodes[2].setMatrix((1.0, 0.0, 0.0, 0.0,
                                         0.0, 1.0, 0.0, 0.0,
                                         0.0, 0.0, 1.0, 0.0,
                                         11.8, 27.7, -61.7, 1.0
                                         ), ws=True
                                        )

        self.sub_opr_nodes[3].setMatrix((1.0, 0.0, 0.0, 0.0,
                                         0.0, 1.0, 0.0, 0.0,
                                         0.0, 0.0, 1.0, 0.0,
                                         11.8, 6, -58.2, 1.0
                                         ), ws=True
                                        )

        """
        pass
