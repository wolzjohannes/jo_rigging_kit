
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from future import standard_library

# Import built-in modules
from builtins import str

# Import python standard import
import logging
import numpy  # noqa: import error
import six
from functools import wraps

# Import third-party modules
from maya import cmds as cmds  # noqa: import error
from pymel import core as pmc  # noqa: import error

from maya.api import OpenMayaAnim as oma2  # noqa: import error
from maya.api import OpenMaya as om2  # noqa: import error
from maya import OpenMaya  # noqa: import error

from pxo_rigging_kit.maya_utils import openmaya_utils
from pxo_rigging_kit.maya_utils.openmaya_utils import get_mobject_om2, get_dag_path_om2, get_mfn_deformer

# Import local modules
try:
    # Import third-party modules
    import ngSkinTools2  # noqa: import error
    from ngSkinTools2.api import InfluenceMappingConfig  # noqa: import error
    from ngSkinTools2.api import VertexTransferMode  # noqa: import error
    from ngSkinTools2.api import import_export  # noqa: import error
    from ngSkinTools2.api import layers  # noqa: import error
    from ngSkinTools2.operations import removeLayerData  # noqa: import error
    from ngSkinTools2.ui import mainwindow as ng_main_window  # noqa: import error

except ModuleNotFoundError:
    pmc.warning("Unable to import ngSkinTools2")

# Import local modules
from pxo_rigging_kit import constants

from pxo_rigging_kit.maya_utils import decorators
from pxo_rigging_kit.maya_utils import exceptions
from pxo_rigging_kit.maya_utils import mesh_utils
from pxo_rigging_kit.io_version_control import version_io


##########################################################
# GLOBALS
##########################################################

standard_library.install_aliases()

_LOGGER = logging.getLogger(f"{__name__}.py")
_LOGGER.setLevel(logging.DEBUG)

DECORATORS = decorators.Decorators()
DECORATORS.debug = False
DECORATORS.logger = _LOGGER


##########################################################
# IMPORT EXPORT FUNCTIONS
##########################################################

def merge_two_dicts(first, second):
    """
    Merges two dictionaries together.

    Args:
        first (dict): Dictionary to merge into.
        second (dict): Dictionary to be merged.

    Returns:
        Dict (result): Resulting dictionary.
    """

    result = first.copy()       # start with keys and values of x
    result.update(second)       # modifies z with keys and values of y
    return result


@DECORATORS.x_timer
def set_attr_preparation(func):
    @wraps(func)
    def wrapper(cls):

        if cls.deformer_name and pmc.objExists(cls.deformer_name):
            pmc.delete(cls.deformer_name)

        influence_strings = [str(x) for x in cls.influence_names.tolist()]

        cmds.skinCluster(
                influence_strings,
                cls.transform_name,
                name=cls.deformer_name,
                toSelectedBones=True,
                bindMethod=0,
                skinMethod=0,
                normalizeWeights=0,
                removeUnusedInfluence=False,
                multi=True,
        )

        cls.get_deformer_info()

        # gather information about existing geometry, shape and skin cluster
        # we need to fix thisss
        if cmds.getAttr(f"{cls.deformer_name}.normalizeWeights"):
            cmds.setAttr(f"{cls.deformer_name}.normalizeWeights", False)

        cmds.skinPercent(cls.deformer_name,
                         cls.transform_name,
                         prw=100,
                         normalize=False,
                         )

        # run the actual set weight function :)
        func(cls)

        cmds.skinCluster(cls.deformer_name,
                         edit=True,
                         forceNormalizeWeights=True,
                         )

        cls.set_deformer_attr_data()

        if not cmds.getAttr(f"{cls.deformer_name}.normalizeWeights"):
            cmds.setAttr(f"{cls.deformer_name}.normalizeWeights", True)

        # help out the logging but only in debug mode
        _LOGGER.debug(f"{func.__name__} called")
        _LOGGER.debug(f"{func.__name__} returned: {pmc.PyNode(cls.deformer_name)}")

        # help out the logging but only in debug mode
        return pmc.PyNode(cls.deformer_name)

    return wrapper


@DECORATORS.x_timer
def transfer_option(func):
    """

    Args:
        func(functioncall): There are multiple operations that can apply skinweights, one of them has to go in here.

    Returns:

    """
    @wraps(func)
    def wrapper(cls):
        """

        Args:
            cls:

        Returns:

        """
        if cls.transfer_needed:

            # switch around the imported and target meshes
            transfer_transform_node = cls.transform_node_import
            transfer_shape_node = cls.shape_node_import

            transfer_transform_name = str(transfer_transform_node.shortName())
            transfer_shape_name = str(transfer_shape_node.shortName())

            transform_node = cls.transform_node
            shape_node = cls.shape_node

            transform_name = cls.transform_name
            shape_name = cls.shape_name

            cls.transform_node = transfer_transform_node
            cls.shape_node = transfer_shape_node

            cls.transform_name = transfer_transform_name
            cls.shape_name = transfer_shape_name

            # run operations in here
            func(cls)

            # transfer the deformers
            cls.transfer_deformer(mesh_list=[transform_name])

            # switch back to original
            cls.transform_node = transform_node
            cls.shape_node = shape_node

            cls.transform_name = transform_name
            cls.shape_name = shape_name

        else:
            # run the operation here without transferring
            func(cls)

        # update the deformer info
        cls.get_deformer_info()

        # help out the logging but only in debug mode
        _LOGGER.debug(f"{func.__name__} called")
        _LOGGER.debug(f"{func.__name__} returned: {pmc.PyNode(cls.deformer_name)}")

        # give back the deformer node
        return pmc.PyNode(cls.deformer_name)

    return wrapper


class DeformerOperator(object):
    EXPORT_FOLDER_NAME = constants.PXO_FILEPATH_DFRM

    ALLOWED_OBJECT_TYPES: list | None   = None
    DEFORMER_TYPE_NAME: str | None      = None
    DEFORMER_SUFFIX_NAME: str | None    = "DEF"
    DEFORMER_SETTINGS: dict | None      = None

    FILE_NAMES = {"vertex_pos": "verts_ws_positions",
                  "vertex_id": "poly_vertex_id",
                  "mesh_data": "mesh_data",
                  "deformer_data": "deformer_data",
                  }

    def __init__(self, input_dag_node: str):
        if not cmds.objExists(input_dag_node):
            raise exceptions.MayaNodeNotFound("the node does not exist with this name in the scene")

        self.io_manager = version_io.ImportExport(abstraction_layers=2)

        self.deformer_operator_name = input_dag_node

        self.has_deformer: bool = False

        self.is_already_rebuilt = False

        self.allowed_node_type = False

        self.transfer_needed: bool = False

        self.deformer_node_data = None

        # build the deformer setting dictionary from the pattern in DeformerOperator class
        self.deformer_settings: dict | None = self.DEFORMER_SETTINGS

        self.transform_node = None
        self.transform_name = None
        self.transform_mfn = None
        self.transform_mdagpath = None
        self.transform_node_import = None

        self.shape_node = None
        self.shape_name = None
        self.shape_mfn = None
        self.shape_mdagpath = None
        self.shape_node_import = None

        self.mesh_data = None

        self.deformer_node = None
        self.deformer_name = None
        self.deformer_mfn = None

        # deformer general information
        self.transfer_check = None
        self.envelope_attr = None
        self.use_components_attr = None

        self.vertex_pos_np = None
        self.poly_vertex_ids_np = None

        self.vert_count = None
        self.geometry_points = None

        self.operating_node = self.get_operating_node(input_dag_node)
        self.deformer_data = self.DEFORMER_SETTINGS

    def gather_scene_external_data(self, **kwargs):
        """
        Queries first the scene for Transform, Shape and Component Information.
        Then tries to get the Deformer Information.
        Finally searches the directories for exported data, imports and processes it for further operations.

        Returns:

        """

        if not self.allowed_node_type:
            raise exceptions.MeshError("the geometry is not part of the allowed nurbs or mesh nodes")

        self.get_transform_info()

        self.get_shape_info()

        self.get_geo_info()

        # this needs to be checked
        try:
            self.get_deformer_info()

        except exceptions.DeformerNotFoundError:
            _LOGGER.warning("the deformer was not found, but for now there is nothing to be done. So it will just pass")
            pass

        # load vertex positions
        self.vertex_pos_np = self.io_manager.load(object_name=self.transform_name,
                                                  data_type="npy",
                                                  receiver_node=self.operating_node,
                                                  data_category=self.EXPORT_FOLDER_NAME,
                                                  data_file_name=self.FILE_NAMES["vertex_pos"],
                                                  version=-1,
                                                  )

        # load the vertex ids
        self.poly_vertex_ids_np = self.io_manager.load(object_name=self.transform_name,
                                                       data_type="npy",
                                                       receiver_node=self.operating_node,
                                                       data_category=self.EXPORT_FOLDER_NAME,
                                                       data_file_name=self.FILE_NAMES["vertex_id"],
                                                       version=-1,
                                                       )

        # load the mesh data
        self.mesh_data = self.io_manager.load(object_name=self.transform_name,
                                              data_type=constants.JSON,
                                              receiver_node=self.operating_node,
                                              data_category=self.EXPORT_FOLDER_NAME,
                                              data_file_name=self.FILE_NAMES["mesh_data"],
                                              version=-1,
                                              )

        # load the deformer node data
        self.deformer_node_data = self.io_manager.load(object_name=self.transform_name,
                                                       data_type=constants.JSON,
                                                       receiver_node=self.operating_node,
                                                       data_category=self.EXPORT_FOLDER_NAME,
                                                       data_file_name=self.FILE_NAMES["deformer_data"],
                                                       version=-1,
                                                       )

        # brings the deformer node data in a format that is further processable
        self.unpack_node_data()

        # import in the reference geometry for comparison reasons
        import_name_ = self.transform_name.replace(constants.NAMESPACE,
                                                   constants.SEPARATOR
                                                   )

        # IF WE PLUG IN HERE; IT WILL BE GOODER
        (self.transform_node_import,
         self.shape_node_import) = self.io_manager.load(object_name=self.transform_name,
                                                        data_type="mb",
                                                        receiver_node=self.operating_node,
                                                        data_category=self.EXPORT_FOLDER_NAME,
                                                        data_file_name=import_name_,
                                                        version=-1,
                                                        )

        return True

    def gather_scene_internal_data(self, **kwargs):

        if not self.allowed_node_type:
            raise exceptions.MeshError("the geometry is not part of the allowed nurbs or mesh nodes")

        self.get_transform_info()

        self.get_shape_info()

        self.get_geo_info()

        self.get_deformer_info()

        self.has_deformer = True

        self.get_deformer_attr_data()

        self.pack_node_data()

    def pack_node_data(self):

        """
        Creates a dict with all the needed information of the deformer that is not array data.

        """

        # write a dict with generalized information
        info = {"name_transform"        : self.transform_name,
                "name_shape"            : self.shape_name,
                "name_deformer"     : self.deformer_name,
                }

        # get rid of the maya objects because they can not be json serialized
        self.deformer_node_data = {key_: value_[0:3:2] for (key_, value_) in self.deformer_data.items()}

        # merge the two dicts to get one for export
        self.deformer_node_data = merge_two_dicts(self.deformer_node_data, info)

        # check if something majorly wrong occured and there are no values
        if not all(self.deformer_node_data.values()):
            raise exceptions.DeformerGeneralizedError("[compile_node_data] operation has not all data")

    def unpack_node_data(self):
        """
        Creates a dict with all the needed information of the deformer that is not array data.

        """

        # extract transform name
        self.transform_name = self.deformer_node_data.pop("name_transform", None)

        # extract shape name
        self.shape_name = self.deformer_node_data.pop("name_shape", None)

        # extract deformer name
        self.deformer_name = self.deformer_node_data.pop("name_deformer", None)

        # extract deformer data
        self.deformer_data = {key_: [value_[0], (self.deformer_name, key_), value_[1]]
                              for (key_, value_)
                              in self.deformer_node_data.items()
                              }

    def get_operating_node(self, input_dag_node):
        """
        Gives you the in point of all needed nodes for skin cluster operations.
        Still needs a way to find out what the input node is, so for now its dag transform or shape

        Args:
            input_dag_node(str, pmc.PyNode(), list): Object of which you want to gather the information from.

        Returns:
            Tuple: (transform_info, shape_info, skin_cluster_info)
        """

        if not input_dag_node:
            raise ValueError(f"input_dag_node is {input_dag_node}. "
                             f"Please give a proper node input!"
                             )

        if isinstance(input_dag_node, list):
            input_dag_node = input_dag_node[0]

        if isinstance(input_dag_node, six.string_types):
            input_dag_node = pmc.PyNode(input_dag_node)

        node_type = get_mobject_om2(input_dag_node.longName())

        if node_type.hasFn(om2.MFn.kTransform):

            self.operating_node = input_dag_node

        elif any((node_type.hasFn(om2.MFn.kMesh),
                  node_type.hasFn(om2.MFn.kNurbsSurface),
                  node_type.hasFn(om2.MFn.kNurbsCurve)
                  )
                 ):

            self.operating_node = input_dag_node.getParent()

        else:
            raise ValueError("Please select either a Shape or a Transform")

        self.allowed_node_checking()

        return self.operating_node

    def allowed_node_checking(self):
        # check if a node is valid for operations
        shape_node = self.operating_node.getChildren()[0]
        shape_node_type = get_mobject_om2(shape_node.longName())

        if any((shape_node_type.hasFn(om2.MFn.kMesh),
                shape_node_type.hasFn(om2.MFn.kNurbsSurface),
                shape_node_type.hasFn(om2.MFn.kNurbsCurve),
                      )):

            self.allowed_node_type = True

    def get_transform_info(self):
        """
        Converts first item of list or string into pmc.PyNode.
        Returns all the OpenMaya handles for the Dag Transform node.

        """
        if not self.operating_node:
            raise exceptions.SkinclusterError("no operating node was found.")

        self.transform_node = self.operating_node

        self.transform_name = str(self.transform_node.shortName())

        self.transform_mfn = get_mobject_om2(self.transform_name)
        self.transform_mdagpath = get_dag_path_om2(self.transform_name)

    def get_shape_info(self):
        """
        Returns all the OpenMaya handles for the Dag Shape node.

        """
        input_dag_name = str(self.operating_node.shortName())
        self.shape_node = self.operating_node.getShape(noIntermediate=True)

        if not self.shape_node:
            raise exceptions.DeformerGeneralizedError(
                    f"[{input_dag_name}] has no shape attached"
            )

        self.shape_name = str(self.shape_node.longName())
        self.shape_mfn = get_mobject_om2(self.shape_name)
        self.shape_mdagpath = get_dag_path_om2(self.shape_name)

        self.comp_ids, self.comp_count = openmaya_utils.get_complete_components_om2(self.shape_mfn)

    def get_deformer_info(self):
        """
        Returns all the OpenMaya handles for the skin cluster node.

        """

        self.deformer_node, self.deformer_position = self.get_specific_deformer_type()

        _LOGGER.debug(f"deformer_node: {self.deformer_node}")
        _LOGGER.debug(f"deformer_position: {self.deformer_position}")

        if not self.deformer_node:
            raise exceptions.DeformerNotFoundError(
                    f"[{self.transform_name}] has no deformer "
                    f"of type [{self.DEFORMER_TYPE_NAME}] attached."
            )

        self.deformer_name = str(self.deformer_node.longName())
        self.deformer_mfn = get_mfn_deformer(self.deformer_name)

    @DECORATORS.x_timer
    def get_geo_info(self):
        """
        Function takes the OpenMaya.MfnMesh and returns the point positions for the mesh in numpy array plus vertex count.

        """

        self.mesh_data = mesh_utils.get_mesh_data(self.shape_mdagpath)

        # convert vertex positions into np array
        self.vertex_pos_np = numpy.asarray(self.mesh_data["verts_ws_pos_list"],
                                           dtype=numpy.float64,
                                           )

        # convert vertex ids to np array
        self.poly_vertex_ids_np = numpy.asarray(self.mesh_data["poly_vertex_id_list"],
                                                dtype=numpy.int32,
                                                )

        # assign new values for the dict to find the right files
        self.mesh_data["verts_ws_pos_list"] = f"{self.deformer_name}_verts_ws_positions.npy"
        self.mesh_data["poly_vertex_id_list"] = f"{self.deformer_name}_poly_vertex_id.npy"
        self.mesh_data["mesh_shape"] = self.shape_name

    # write applications
    @DECORATORS.x_timer
    def export_data(self, **kwargs):
        """
        This will be extended by the subclass that is dedicated to a specific deformer.

        """
        if not self.has_deformer:
            raise exceptions.DeformerGeneralizedError("there was no deformer of the right type on the node.")

        if not self.transform_name:
            raise exceptions.DeformerGeneralizedError("no transform name was given.")

        if not self.deformer_node_data:
            raise exceptions.DeformerGeneralizedError("Deformer Data was insufficient for the export.")

        if not self.mesh_data:
            raise exceptions.DeformerGeneralizedError("Mesh Data was insufficient for the export.")

        if self.vertex_pos_np is None:
            raise exceptions.DeformerGeneralizedError("Vertex Position Data was insufficient for the export.")

        if self.poly_vertex_ids_np is None:
            raise exceptions.DeformerGeneralizedError("Vertex Ids Data was insufficient for the export.")

        # write vertex positions
        self.io_manager.write(
                object_name=self.transform_name,
                data_to_write=self.vertex_pos_np,
                data_file_name=self.FILE_NAMES["vertex_pos"],
                data_type="npy",
        )

        # write the vertex ids
        self.io_manager.write(
                object_name=self.transform_name,
                data_to_write=self.poly_vertex_ids_np,
                data_file_name=self.FILE_NAMES["vertex_id"],
                data_type="npy",
        )

        # write the mesh data
        self.io_manager.write(
                object_name=self.transform_name,
                data_to_write=self.mesh_data,
                data_file_name=self.FILE_NAMES["mesh_data"],
                data_type=constants.JSON,
        )

        # write the deformer node data
        self.io_manager.write(
                object_name=self.transform_name,
                data_to_write=self.deformer_node_data,
                data_file_name=self.FILE_NAMES["deformer_data"],
                data_type=constants.JSON,
        )

        # export the object
        self.io_manager.write(
                object_name=self.transform_name,
                data_file_name=self.transform_name.replace(constants.NAMESPACE, constants.SEPARATOR),
                data_type="mb",
        )

    @DECORATORS.x_timer
    def import_data(self, **kwargs):
        """
        This will be filled by the subclass of this class that is dedicated to a specific deformer.

        """

        if mesh_utils.check_mesh_data(self.shape_node_import,
                                      self.shape_node,
                                      diff_poly_vertex_id=False,
                                      diff_poly_vertex_id_color_on_mesh=False,
                                      diff_vertx_ws_pos=False,
                                      diff_vertx_ws_color_on_mesh=False,
                                      verts_ws_pos_tolerance=mesh_utils.VERTS_WS_POS_TOLERANCE,
                                      ):

            self.transfer_needed = False
            pmc.delete(self.shape_node_import)
            pmc.delete(self.transform_node_import)
            _LOGGER.info("killed transfer mesh since [mesh_utils.check_mesh_data] states no transfer was needed.")

        else:
            self.transfer_needed = True
            _LOGGER.info("set transfer_needed to True since [mesh_utils.check_mesh_data] states transfer is needed.")

    @DECORATORS.x_timer
    def set_deformer_attr_data(self, deformer_mfn=None, deformer_settings=None):
        """
        Sets the attributes of the OpenMaya.MfnSkinCluster for node specific information.

        Args:
            deformer_mfn(OpenMaya.MfnDeformer): The OpenMaya.MfnDeformer Class to be queried for node information.

        Returns:
            Bool: True if operation is finished.
        """

        _deformer_mfn = deformer_mfn or self.deformer_mfn
        _deformer_settings = deformer_settings or self.deformer_data

        if not _deformer_settings:
            raise exceptions.SkinclusterError("the dictionary for DEFORMER_SETTINGS settings for this subclass have not been specified")

        for plug_name, plug_value in _deformer_settings.items():
            defomer_plug = _deformer_mfn.findPlug(plug_name, 0)

            if plug_value[0] == "as_float":
                defomer_plug.setFloat(plug_value[2])

            if plug_value[0] == "as_int":
                defomer_plug.setInt(plug_value[2])

            if plug_value[0] == "as_bool":
                defomer_plug.setBool(plug_value[2])

    @DECORATORS.x_timer
    def get_deformer_attr_data(self, deformer_mfn=None):
        """
        Queries the attributes of the OpenMaya.MfnSkinCluster for node specific information.

        Args:
            deformer_mfn(OpenMaya.MfnDeformer): The OpenMaya.MfnDeformer Class to be queried for node information.

        Returns:
            tuple:(envelope_attr,
                   skin_method_attr,
                   node_state_attr,
                   normalize_weights_attr,
                   weight_dist_attr,
                   max_influences_attr,
                   maintain_max_attr,
                   use_components_attr
                   )
        """
        _deformer_mfn = deformer_mfn or self.deformer_mfn

        for plug_name, plug_value in self.deformer_data.items():

            deformer_plug = _deformer_mfn.findPlug(plug_name, 0)
            plug_value[1] = deformer_plug

            if plug_value[0] == "as_float":
                plug_value[2] = deformer_plug.asFloat()
                continue

            elif plug_value[0] == "as_int":
                plug_value[2] = deformer_plug.asInt()
                continue

            elif plug_value[0] == "as_bool":
                plug_value[2] = deformer_plug.asBool()
                continue

            elif plug_value[0] == "as_input_connection":
                src = deformer_plug.connectedTo(False, True)

                if not src:
                    plug_value[2] = None
                    continue

                connected_plug = src[0]
                connected_node = connected_plug.node()
                connected_mfn = om2.MFnDependencyNode(connected_node)

                plug_value[2] = f"{connected_mfn.uniqueName()}.{connected_plug.partialName()}"

            elif plug_value[0] == "as_output_connections":
                dst = deformer_plug.connectedTo(True, False)

                if not dst:
                    plug_value[2] = None
                    continue

                destinations = []
                for destination in dst:
                    connected_node = destination.node()
                    connected_mfn = om2.MFnDependencyNode(connected_node)

                    destination_name = f"{connected_mfn.uniqueName()}.{destination.partialName()}"
                    destinations.append(destination_name)

                plug_value[2] = destinations
                continue

        return self.deformer_data

    @DECORATORS.x_timer
    def rebuild_pruned(self, **kwargs):
        raise NotImplementedError("deformer will be rebuilt as a pruned deformer")

    @DECORATORS.x_timer
    def transfer_deformer(self, mesh_list=None, **kwargs):

        if not mesh_list:
            raise exceptions.DeformerGeneralizedError("the mesh list was not defined or empty")

        self.get_transform_info()
        self.get_deformer_info()

    @DECORATORS.x_timer
    def rename_deformer(self, update_data=False, **kwargs):
        """
        Renames the deformer based on the transform name.

        """

        self.get_transform_info()
        self.get_shape_info()
        self.get_deformer_info()
        self.get_deformer_attr_data()
        self.pack_node_data()

        if not all((self.transform_node,
                   self.transform_name,
                   self.deformer_name,
                   self.deformer_node)
                   ):
            raise exceptions.SkinclusterError("there was either no transform node import or no transform node")

        if "_" in self.transform_name:
            transform_name_decomposed = self.transform_name.split("_")[0:-1]
        else:
            transform_name_decomposed = self.transform_name.split("_")[::]

        transform_name_decomposed.append(self.DEFORMER_SUFFIX_NAME)

        deform_name_new = "_".join(transform_name_decomposed)
        deform_name_new = deform_name_new.replace(":",
                                                  constants.SEPARATOR
                                                  )

        self.deformer_node.rename(deform_name_new)

        self.deformer_name = deform_name_new
        self.deformer_node_data["name_deformer"] = deform_name_new

        if update_data:
            self.gather_scene_internal_data(**kwargs)

    # i think this should be shifted into the deformer handler
    def get_deformers_for_shape(self):
        """
        Get the deformers from an object's history that only
        effect that particular mesh, and not inputs from other
        meshes (IE, meshes driving blendshapes).

        Returns:
            List: Filled with pmc.PyNode() for each found deformer.

        """
        deformers = []

        shape_deformed = self.get_deform_shape()

        history = pmc.listHistory(shape_deformed,
                                  pruneDagObjects=True,
                                  )

        for node in history:
            if "geometryFilter" not in node.nodeType(inherited=True):
                continue

            sel = om2.MGlobal.getSelectionListByName(node.longName())
            mobj = sel.getDependNode(0)

            deformer_ = oma2.MFnGeometryFilter(mobj)
            outputs_ = deformer_.getOutputGeometry()

            outputs = [pmc.PyNode(om2.MFnDependencyNode(o).uniqueName()) for o in outputs_]

            if shape_deformed in outputs:
                deformers.append(node)

        return deformers

    def get_deform_shape(self):
        """
        Gets the visible geometry shape regardless of whether
        the object is deformed or not.

        Returns:
            pymel.core.PyNode(): The object's deform shape.

        """

        deformed_object = pmc.PyNode(self.transform_node)

        if deformed_object.type() in self.ALLOWED_OBJECT_TYPES:
            deformed_object = deformed_object.getParent()

        shapes = deformed_object.getShapes(noIntermediate=True)

        if not shapes:
            raise ValueError(f"{deformed_object} has no visible shape")

        if len(shapes) > 1:
            raise ValueError(f"{deformed_object} has more than one visible shape")

        return shapes[0]


    # i think this should be shifted into the deformer handler?
    def get_specific_deformer_type(self):
        """
        Get the skincluster form

        Returns:
            pmc.PyNode(): The skin cluster node.

        """

        deformers = self.get_deformers_for_shape()

        if not deformers:
            raise exceptions.DeformerNotFoundError(f"Given Shape: {self.shape_name} of "
                                                   f"Transform: {self.transform_name} has no Deformers.")

        typed_deformers = list(filter(lambda x: x.type() == self.DEFORMER_TYPE_NAME, deformers))

        if not typed_deformers:
            raise exceptions.DeformerNotFoundError(f"Given Shape: {self.shape_name} "
                                                   f"has no Deformers of type: {self.DEFORMER_TYPE_NAME}.")

        if len(typed_deformers) > 2:
            _LOGGER.warning(f"Multiple Deformers of type {self.DEFORMER_TYPE_NAME} found, "
                            f"will be using the first in stack.")

        skin = typed_deformers[0] if typed_deformers else None

        if skin:
            skin.weightDistribution.set(1)

        return skin, deformers.index(skin)

    def absolutize_deformer(self, **kwargs):
        """
        Used to simplify the deformer by only letting one input effect one vertex, this is used to sanatize the deformer.

        """
        if not self.deformer_node:
            raise exceptions.DeformerNotFoundError()

    def kill_deformer(self, **kwargs):
        """
        Removes the deformer.

        """
        if not self.deformer_node:
            raise exceptions.DeformerNotFoundError()

    def rebuild_deformer(self, **kwargs):
        """
        Rebuilds the deformer.

        """

        if not self.deformer_node:
            raise exceptions.DeformerNotFoundError()

    def get_inputs(self):
        """
        Gives back all the inputs to the deformer.

        """
        if not self.deformer_node:
            raise exceptions.DeformerNotFoundError()


