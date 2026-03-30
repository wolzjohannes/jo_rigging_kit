# Import built-in modules
from importlib import reload
import logging
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

##########################################################
# FUNCTIONS
##########################################################


class Main(operator.Main):
    def __init__(self, comp_side: str = "C",
                 comp_name: str="fkChain",
                 build_axis: str = "+z",
                 build_axes_mult_factor: int = 10,
                 data_container: Optional[data.DataContainer] = None
                 ):

        # Here we define static and fixed arguments for this component operator.
        super(Main, self).__init__(
            comp_name=comp_name,
            comp_side=comp_side,
            comp_type="test_fk_chain",
            build_axis=build_axis,
            build_axis_mult_factor=build_axes_mult_factor,
            sub_opr_count=4,
            lra_ctrl=True,
                data_container=data_container,
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

        self.sub_opr_nodes[0].translateZ.set(2)

        self.sub_opr_nodes[1].translateZ.set(4)

        self.sub_opr_nodes[2].translateZ.set(6)

        self.sub_opr_nodes[3].translateZ.set(8)

