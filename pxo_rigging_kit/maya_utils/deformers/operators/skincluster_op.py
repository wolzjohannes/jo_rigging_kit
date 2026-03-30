# Author:     Christof Puehringer / Rigging TD

"""
Utils code for skincluster management. Import, export and transfer.


Examples:

    - Renaming a skincluster to the transform it deforms:
    >>> from importlib import reload
    >>> from pxo_rigging_kit.maya_utils.deformers.operators import skincluster_op
    >>> reload(skincluster_op)
    >>> skin_operator = skincluster_op.SkinClusterOperator("MESH_NAME")
    >>> skin_operator.gather_scene_internal_data()
    >>> skin_operator.rename_deformer()


    - Exporting a skincluster:
    >>> from importlib import reload
    >>> from pxo_rigging_kit.maya_utils.deformers.operators import skincluster_op
    >>> reload(skincluster_op)
    >>> skin_operator = skincluster_op.SkinClusterOperator("MESH_NAME")
    >>> skin_operator.gather_scene_internal_data()
    >>> skin_operator.export_data()


    - Importing a skincluster:
    >>> from importlib import reload
    >>> from pxo_rigging_kit.maya_utils.deformers.operators import skincluster_op
    >>> reload(skincluster_op)
    >>> skin_operator = skincluster_op.SkinClusterOperator("MESH_NAME")
    >>> skin_operator.gather_scene_external_data()
    >>> skin_operator.import_data(numpy=True,
    >>>                           json=False,
    >>>                           xml=False,
    >>>                           ng=False,
    >>>                           )


   - Transferring a skincluster:
    >>> from importlib import reload
    >>> from pxo_rigging_kit.maya_utils.deformers.operators import skincluster_op
    >>> reload(skincluster_op)
    >>> skin_operator = skincluster_op.SkinClusterOperator("MESH_NAME")
    >>> skin_operator.transfer_deformer(mesh_list=["TO_NAME_ONE",
    >>>                                            "TO_NAME_TWO",
    >>>                                            "TO_NAME_THREE",
    >>>                                            "TO_NAME_FOUR",
    >>>                                            "TO_NAME_FIVE"
    >>>                                            ]
    >>>                                            )

The skin cluster export directory looks like this:

_DATA_LOCATION_FOLDER_NAME
    DATE
        TIME
            skincluster1(source skin cluster node name):
                - influence_matrices.npy:
                - influence_names.npy:

                - skin_cluster_data.json:

                - skincluster1_mesh_data.json:
                - skincluster1_poly_vertex_id.npy:
                - skincluster1_verts_ws_positions:

                - vertex_positions.npy:
                - weight_array.npy:
                - weight_legend.npy:
            data_lookup.json:


TOD0:
    Translate the NG and XML data into a faster format

"""

# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from future import standard_library
from typing import Tuple, List

# Import built-in modules
from builtins import dict
from builtins import int
from builtins import range
from builtins import str

# Import python standard import
import logging

# Import third-party modules
import numpy as np  # noqa: import error

from maya import cmds as cmds  # noqa: import error
from pymel import core as pmc  # noqa: import error
from maya.api import OpenMaya as om2  # noqa: import error
from maya.api import OpenMayaAnim as oma2  # noqa: import error

# Import local modules

from pxo_rigging_kit import constants
from pxo_rigging_kit.maya_utils import decorators
from pxo_rigging_kit.maya_utils import exceptions
from pxo_rigging_kit.maya_utils.deformers.operators.deformer_op_base import (DeformerOperator,
                                                                             transfer_option,
                                                                             set_attr_preparation)

##########################################################
# GLOBALS
##########################################################

standard_library.install_aliases()

_LOGGER = logging.getLogger(f"{__name__}.py")
_LOGGER.setLevel(logging.INFO)

DECORATORS = decorators.Decorators()
DECORATORS.debug = True
DECORATORS.logger = _LOGGER

##########################################################
# CLASSES
##########################################################


class SkinClusterOperator(DeformerOperator):
    """
    The SkinClusterOperator is a class that is meant to unify all the skin-cluster operations.
    It inherits the core functionality from the deformer operator that has generalized deformer methods.

    Take Care: Both are written with OM1. THIS NEEDS TO BE CHANGED.

    """
    EXPORT_FOLDER_NAME: str         = constants.PXO_FILEPATH_SKIN

    ALLOWED_OBJECT_TYPES: list      = ["mesh", "nurbsSurface", "nurbsCurve"]
    DEFORMER_TYPE_NAME: str         = "skinCluster"
    DEFORMER_SUFFIX_NAME: str       = "SKC"

    DEFORMER_SETTINGS: dict         = {"envelope"               : ["as_float", None, None],
                                       "skinningMethod"         : ["as_int", None, None],
                                       "nodeState"              : ["as_int", None, None],
                                       "normalizeWeights"       : ["as_int", None, None],
                                       "weightDistribution"     : ["as_int", None, None],
                                       "maxInfluences"          : ["as_int", None, None],
                                       "maintainMaxInfluences"  : ["as_bool", None, None],
                                       "dqsSupportNonRigid"     : ["as_bool", None, None],
                                       "dqsScale"              : ["as_input_connection", None, None],
                                       "dqsScaleX"              : ["as_float", None, None],
                                       "dqsScaleY"              : ["as_float", None, None],
                                       "dqsScaleZ"              : ["as_float", None, None],
                                       "relativeSpaceMode"      : ["as_int", None, None],
                                       "deformUserNormals"      : ["as_float", None, None],
                                       "relativeSpaceMatrix"    : ["as_float", None, None],
                                       }

    def __init__(self, input_dag_node: str) -> None:
        super(SkinClusterOperator, self).__init__(input_dag_node)

        # file name construction
        self.FILE_NAMES["deformer_data"]                = "skin_node_data"
        self.FILE_NAMES["compressed_legend"]            = "compressed_legend"
        self.FILE_NAMES["compressed_weights"]           = "compressed_weights"

        self.FILE_NAMES["ng2_data"]                     = "ng2_data"
        self.FILE_NAMES["deformer_command"]             = "skin_weights"
        self.FILE_NAMES["uncompressed_weights"]         = "skin_weights"

        self.FILE_NAMES["influence_matrices"]           = "influence_matrices"
        self.FILE_NAMES["influence_names"]              = "influence_names"
        self.FILE_NAMES["blend_weights"]                = "dq_weights"

        # operational data
        self.build_nonexisting                              = True
        self.abort_operation_on_joint_error                 = False

        # deformer specific datas
        self.inf_dagpaths: List[om2.MDagPath] | None        = None
        self.inf_dagpath_count                              = None

        self.maximum_weights: int | None                    = None
        self.maintain_max_influences_enabled: bool | None   = None

        self.influence_names: np.ndarray | None             = None
        self.influence_matrices: np.ndarray | None          = None

        self.compressed_weights: np.ndarray | None          = None
        self.compressed_legend: np.ndarray | None           = None
        self.blend_weights:  np.ndarray | None              = None
        self.uncompressed_weights: np.ndarray | None        = None

    @DECORATORS.x_timer
    def get_influence_info_np(self) -> None:
        """Gather influence names and matrices in export order.

        Export order is the order returned by `MFnSkinCluster.influenceObjects()`.
        This order defines the export index space [0..N-1].
        """
        if self.deformer_mfn is None:
            raise RuntimeError("deformer_mfn is not set.")

        inf_dagpaths: List[om2.MDagPath] = self.deformer_mfn.influenceObjects()
        inf_count: int = len(inf_dagpaths)

        self.influence_names = np.array(
            [str(d.fullPathName()) for d in inf_dagpaths],
            dtype="unicode",
        )

        self.influence_matrices = np.array(
            [d.inclusiveMatrix() for d in inf_dagpaths],
            dtype=np.float64,
        )

        assert self.influence_names.shape[0] == inf_count
        assert self.influence_matrices.shape[0] == inf_count

    @DECORATORS.x_timer
    def get_component_weights_np(self) -> Tuple[np.ndarray, int]:
        """Read full weight table from the skinCluster.

        Returns:
            Tuple[np.ndarray, int]: A tuple containing:
                - weights_2d: Array of shape (num_verts, num_influences).
                - influence_count: Number of influences in the skinCluster.
        """
        if self.deformer_mfn is None or self.shape_mdagpath is None or self.comp_ids is None:
            raise RuntimeError("deformer_mfn, shape_mdagpath, or comp_ids is not set.")

        weights_mda, influence_count = self.deformer_mfn.getWeights(
            self.shape_mdagpath,
            self.comp_ids,
        )

        weights_np = np.asarray(weights_mda, dtype=np.float64)

        assert weights_np.size == self.comp_count * influence_count

        weights_2d = weights_np.reshape((self.comp_count, influence_count))

        return weights_2d, influence_count

    @DECORATORS.x_timer
    def get_blend_weights_np(self) -> Tuple[np.ndarray, int]:
        """Read full weight table from the skinCluster.

        Returns:
            Tuple[np.ndarray, int]: A tuple containing:
                - weights_2d: Array of shape (num_verts, num_influences).
                - influence_count: Number of influences in the skinCluster.
        """
        if self.deformer_mfn is None or self.shape_mdagpath is None or self.comp_ids is None:
            raise RuntimeError("deformer_mfn, shape_mdagpath, or comp_ids is not set.")

        blend_mda = self.deformer_mfn.getBlendWeights(self.shape_mdagpath,
                                                      self.comp_ids,
                                                      )

        blends = np.asarray(blend_mda, dtype=np.float64)

        assert blends.size == self.comp_count

        return blends

    @staticmethod
    @DECORATORS.x_timer
    def prune_weights_topk(
            weights_2d: np.ndarray,
            max_influences: int,
            near_zero: float = 1e-6,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Prune weights to top-K influences per vertex.

        Args:
            weights_2d: Full weight table, shape (num_verts, num_influences).
            max_influences: Maximum influences to keep per vertex.
            near_zero: Threshold below which weights are treated as zero.

        Returns:
            Tuple[np.ndarray, np.ndarray]:
                - pruned_weights: (num_verts, K)
                - pruned_indices: (num_verts, K)
        """
        num_verts, num_infl = weights_2d.shape
        max_influences = min(max_influences, num_infl)

        # Remove tiny weights
        weights = np.where(weights_2d < near_zero, 0.0, weights_2d)
        inf_ids = np.arange(num_infl, dtype=np.int32)

        # Top-K indices per vertex
        topk_idx = np.argpartition(weights, -max_influences, axis=1)[:, -max_influences:]

        row_indices = np.arange(num_verts)[:, None]
        topk_sorted = np.argsort(weights[row_indices, topk_idx], axis=1)[:, ::-1]
        topk_idx = topk_idx[row_indices, topk_sorted]

        pruned_weights = weights[row_indices, topk_idx]
        pruned_indices = inf_ids[topk_idx]

        # Normalize
        sums = pruned_weights.sum(axis=1, keepdims=True)
        pruned_weights = np.divide(
            pruned_weights,
            sums,
            out=np.zeros_like(pruned_weights),
            where=sums != 0,
        )

        return pruned_weights, pruned_indices

    @staticmethod
    @DECORATORS.x_timer
    def build_compressed_from_pruned(
        pruned_weights: np.ndarray,
        pruned_indices: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Build compressed weights and legend from pruned arrays.

        Args:
            pruned_weights: Array of shape (num_verts, K).
            pruned_indices: Array of shape (num_verts, K).

        Returns:
            Tuple[np.ndarray, np.ndarray]:
                - compressed_weights: Structured array with fields
                  ('influence_index', int32), ('influence_weight', float64).
                - compressed_legend: int32 array of length num_verts with K per vertex.
        """
        num_verts, k = pruned_weights.shape

        flat_weights = pruned_weights.reshape(-1)
        flat_indices = pruned_indices.reshape(-1)

        compressed_weights = np.empty(
            flat_weights.shape[0],
            dtype=[("influence_index", np.int32), ("influence_weight", np.float64)],
        )
        compressed_weights["influence_index"] = flat_indices
        compressed_weights["influence_weight"] = flat_weights

        compressed_legend = np.full(num_verts, k, dtype=np.int32)

        return compressed_weights, compressed_legend

    @staticmethod
    @DECORATORS.x_timer
    def prune_unused_influences(
        compressed_weights: np.ndarray,
        influence_names: np.ndarray,
        influence_matrices: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Prune influences that have no non-zero weights and remap indices.

        Args:
            compressed_weights: Structured array with fields
                'influence_index' and 'influence_weight'.
            influence_names: Array of influence names in export order.
            influence_matrices: Array of influence matrices in export order.

        Returns:
            Tuple[np.ndarray, np.ndarray, np.ndarray]:
                - new_compressed_weights: Same shape, remapped indices.
                - new_influence_names: Pruned names in new export order.
                - new_influence_matrices: Pruned matrices in new export order.
        """

        indices = compressed_weights["influence_index"]
        weights = compressed_weights["influence_weight"]

        used_mask = weights != 0.0
        used_indices = np.unique(indices[used_mask])

        new_influence_names = influence_names[used_indices]
        new_influence_matrices = influence_matrices[used_indices]

        # Build a lookup table for remapping
        max_index = indices.max()
        lut = np.full(max_index + 1, -1, dtype=np.int32)
        lut[used_indices] = np.arange(len(used_indices), dtype=np.int32)

        # Vectorized remap (pure NumPy)
        remapped_indices = lut[indices]

        new_compressed_weights = compressed_weights.copy()
        new_compressed_weights["influence_index"] = remapped_indices

        return new_compressed_weights, new_influence_names, new_influence_matrices

    @staticmethod
    @DECORATORS.x_timer
    def compressed_to_full(
        compressed_weights: np.ndarray,
        compressed_legend: np.ndarray,
        influence_count: int,
    ) -> np.ndarray:
        """Rebuild full weight table from compressed representation.

        Args:
            compressed_weights: Structured array with fields
                'influence_index' and 'influence_weight'.
            compressed_legend: Per-vertex influence counts.
            influence_count: Number of influences (columns) in export space.

        Returns:
            np.ndarray: Full weight table of shape (num_verts, influence_count).
        """
        num_verts = compressed_legend.shape[0]
        full = np.zeros((num_verts, influence_count), dtype=np.float64)

        offset = 0
        for v in range(num_verts):
            count = int(compressed_legend[v])
            sl = compressed_weights[offset : offset + count]
            full[v, sl["influence_index"]] = sl["influence_weight"]
            offset += count

        return full

    @staticmethod
    @DECORATORS.x_timer
    def numpy_to_maya_arrays(
        full_weights: np.ndarray,
    ) -> Tuple[om2.MDoubleArray, om2.MIntArray]:
        """Convert full weight table to Maya API 2.0 arrays.

        Args:
            full_weights: Full weight table, shape (num_verts, num_influences).

        Returns:
            Tuple[om2.MDoubleArray, om2.MIntArray]:
                - mweights: Flattened weights in row-major order.
                - inf_ids: Influence indices [0..num_influences-1].
        """

        flat = np.asarray(full_weights, dtype=np.float64).ravel().tolist()

        mweights = om2.MDoubleArray(flat)

        inf_ids = om2.MIntArray([idx for idx in range(full_weights.shape[1])])

        return mweights, inf_ids

    @staticmethod
    @DECORATORS.x_timer
    def set_weights_on_new_skincluster(
        new_deformer_mfn: oma2.MFnSkinCluster,
        shape_mdagpath: om2.MDagPath,
        comp_ids: om2.MObject,
        full_weights: np.ndarray,
    ) -> None:
        """Apply weights to a newly created skinCluster.

        Assumes the new skinCluster's influences are added in the same
        order as the exported influence_names (export index space).

        Args:
            new_deformer_mfn: Function set for the new skinCluster.
            shape_mdagpath: Geometry path.
            comp_ids: Component object (vertices).
            full_weights: Full weight table in export index order.
        """
        mweights, inf_ids = SkinClusterOperator.numpy_to_maya_arrays(full_weights)

        new_deformer_mfn.setWeights(
            shape_mdagpath,
            comp_ids,
            inf_ids,
            mweights,
            False,  # already normalized
        )

    @staticmethod
    def compute_dynamic_max_influences(
            weights_2d: np.ndarray,
            near_zero: float = 1e-6,
    ) -> int:
        """Compute the maximum number of meaningful (non-zero) influences per vertex.

        Args:
            weights_2d: Full weight table, shape (num_verts, num_influences).
            near_zero: Threshold below which weights are treated as zero.

        Returns:
            int: Maximum number of influences used by any vertex.
        """
        # Remove noise
        cleaned = np.where(weights_2d < near_zero, 0.0, weights_2d)

        # Count non-zero influences per vertex
        per_vertex_counts = (cleaned > 0.0).sum(axis=1)

        return int(per_vertex_counts.max())

    @staticmethod
    @DECORATORS.x_timer
    def resolve_prune_k(
            weights_2d: np.ndarray,
            prune_target: int,
            enforce_prune_target: bool,
            near_zero: float = 1e-6,
    ) -> int:
        """Determine the final prune K value using best-practice logic.

        Args:
            weights_2d: Full weight table, shape (num_verts, num_influences).
            prune_target: User-requested pruning number.
            enforce_prune_target: If True, force prune_target as the max influences.
            near_zero: Threshold below which weights are treated as zero.

        Returns:
            int: Final K value to use for pruning.
        """
        dynamic_k = SkinClusterOperator.compute_dynamic_max_influences(weights_2d, near_zero)

        if enforce_prune_target:
            # User forces a hard limit
            return min(prune_target, dynamic_k)

        # Otherwise: best practice → preserve all meaningful influences
        return dynamic_k

    @DECORATORS.x_timer
    def set_bind_pre_matrices(
            self,
            new_deformer_mfn: oma2.MFnSkinCluster,
            influence_matrices: np.ndarray,
    ) -> None:

        """Apply exported bindPreMatrix values to a newly created skinCluster.

        Args:
            new_deformer_mfn: MFnSkinCluster for the new skinCluster.
            influence_paths: List of MDagPaths for the influences added to the new skinCluster.
                             Must be in the same order as self.influence_names.
        """

        if influence_matrices is None:
            raise RuntimeError("influence_matrices not loaded.")

        influence_matrices_ = influence_matrices.tolist()

        bpm_plug = new_deformer_mfn.findPlug("bindPreMatrix", False)

        for idx_, mtx in enumerate(influence_matrices_):
            # Exported inclusive matrix
            m = om2.MMatrix(mtx)

            inv = m.inverse()

            elem = bpm_plug.elementByLogicalIndex(idx_)

            # Set the matrix
            elem.setMObject(om2.MFnMatrixData().create(inv))

    @DECORATORS.x_timer
    def gather_scene_internal_data(self, prune_enforce=False, **kwargs):
        """High-level export pipeline.

            Steps:
                1. Gather influences.
                2. Read full weights.
                3. Prune per-vertex to top-K.
                4. Compress.
                5. Prune unused influences globally and remap.

            The resulting data members:
                - self.compressed_weights
                - self.compressed_legend
                - self.influence_names
                - self.influence_matrices
            are ready to be saved to disk.

        """

        super(SkinClusterOperator, self).gather_scene_internal_data(**kwargs)

        if prune_enforce and isinstance(prune_enforce, int):
            self.maximum_weights = prune_enforce
            self.maintain_max_influences_enabled = True
        else:
            self.maximum_weights = self.deformer_data.get("maxInfluences")[-1] or 30
            self.maintain_max_influences_enabled = self.deformer_data.get("maintainMaxInfluences")[-1]

        if not self.has_deformer:
            raise exceptions.SkinclusterError("the deformer was not found: gathering operation was stopped")

        self.get_influence_info_np()

        weights_2d, _ = self.get_component_weights_np()
        blend_weights = self.get_blend_weights_np()

        # NEW: Best-practice pruning logic
        dynamic_prune_k = self.resolve_prune_k(weights_2d,
                                               prune_target=self.maximum_weights,
                                               enforce_prune_target=self.maintain_max_influences_enabled,
                                               )

        pruned_w, pruned_idx = self.prune_weights_topk(
            weights_2d,
            max_influences=dynamic_prune_k,
        )

        compressed_weights, compressed_legend = self.build_compressed_from_pruned(
            pruned_w,
            pruned_idx,
        )

        compressed_weights, influence_names, influence_matrices = self.prune_unused_influences(
            compressed_weights,
            self.influence_names,
            self.influence_matrices,
        )

        self.compressed_weights = compressed_weights
        self.compressed_legend = compressed_legend
        self.influence_names = influence_names
        self.influence_matrices = influence_matrices

        # converts skin weights into readable format
        assert self.influence_matrices.shape[0] == self.influence_names.shape[0]

        influence_count = self.influence_names.shape[0]

        self.uncompressed_weights = self.compressed_to_full(
            self.compressed_weights,
            self.compressed_legend,
            influence_count,
        )

        self.blend_weights = blend_weights

    @set_attr_preparation
    def _om_set_weights(
            self,
        ) -> None:
            """
            Assumes:
                - self.compressed_weights, self.compressed_legend,
                  self.influence_names, self.influence_matrices
                  have been loaded from disk.
                - The new skinCluster has influences added in the same
                  order as self.influence_names.
            """

            if self.compressed_weights is None:
                raise RuntimeError("compressed_weights is not set.")

            if self.compressed_legend is None:
                raise RuntimeError("compressed_legend is not set.")

            if self.influence_names is None:
                raise RuntimeError("influence_names is not set.")

            if self.influence_matrices is None:
                raise RuntimeError("influence_matrices is not set.")

            self.set_bind_pre_matrices(self.deformer_mfn, self.influence_matrices)

            self.set_weights_on_new_skincluster(
                self.deformer_mfn,
                self.shape_mdagpath,
                self.comp_ids,
                self.uncompressed_weights,
            )


    @DECORATORS.x_timer
    def gather_scene_external_data(self,
                                   **kwargs
                                   ):

        super(SkinClusterOperator, self).gather_scene_external_data(**kwargs)

        # loads the numpy compressed weights
        self.compressed_weights = self.io_manager.load(object_name=self.operating_node,
                                                       data_type="npy",
                                                       data_file_name=self.FILE_NAMES["compressed_weights"],
                                                       data_category=self.EXPORT_FOLDER_NAME,
                                                       )

        # loads the numpy compressed legend
        self.compressed_legend = self.io_manager.load(object_name=self.operating_node,
                                                      data_type="npy",
                                                      data_file_name=self.FILE_NAMES["compressed_legend"],
                                                      data_category=self.EXPORT_FOLDER_NAME,
                                                      )

        # loads the numpy influence names
        self.influence_names = self.io_manager.load(object_name=self.operating_node,
                                                    data_type="npy",
                                                    data_file_name=self.FILE_NAMES["influence_names"],
                                                    data_category=self.EXPORT_FOLDER_NAME,
                                                    )

        # loads the numpy influence matrices
        self.influence_matrices = self.io_manager.load(object_name=self.operating_node,
                                                       data_type="npy",
                                                       data_file_name=self.FILE_NAMES["influence_matrices"],
                                                       data_category=self.EXPORT_FOLDER_NAME,
                                                       )

        # converts skin weights into readable format
        assert self.influence_matrices.shape[0] == self.influence_names.shape[0]

        influence_count = self.influence_names.shape[0]

        self.uncompressed_weights = self.compressed_to_full(
            self.compressed_weights,
            self.compressed_legend,
            influence_count,
        )


    @DECORATORS.x_timer
    def import_data(self,
                    numpy=True,
                    json=False,
                    xml=False,
                    ng=False,
                    **kwargs):
        """
        asfasdfasdfsadf.

        Args:
            numpy (bool): Flag to import the data as two compressed Numpy files.
            json (bool): Flag to import the data as a Json Dict.
            xml (bool): Flag to import the data as the Maya Export Deformer Weights Command.
            ng (bool): Flag to import the data as the NG2 Export Skinlayers Command.

        """

        super(SkinClusterOperator, self).import_data(**kwargs)

        # corrects the import data (by adding joints where none are in the scene)
        self.correct_import_data()

        # exports that are optional but at least one of them has to be exportable.
        if numpy:
            self._import_np()

        if json:
            self._import_json()

        if xml:
            self._import_xml()

        if ng:
            self._import_ng()

        self.set_deformer_attr_data()

        if pmc.objExists(self.transform_node_import):
            pmc.delete(self.transform_node_import)

        cmds.select(cl=True)

    @DECORATORS.x_timer
    @transfer_option
    def _import_np(self, ):
        """
        Sets the weights by set weights commands

        """

        self._om_set_weights()

    @DECORATORS.x_timer
    @transfer_option
    def _import_json(self, ):
        """
        Sets the weights by set weights commands.

        """

        self._set_weights()

    @DECORATORS.x_timer
    @set_attr_preparation
    def _import_ng(self, ):
        """
        sdfgsdfgsdfg

        """

        self.io_manager.load(object_name=self.transform_name,
                             data_file_name=self.FILE_NAMES["ng2_data"],
                             data_type="ng",
                             data_category=self.EXPORT_FOLDER_NAME,
                             )

    @DECORATORS.x_timer
    @set_attr_preparation
    def _import_xml(self, ):
        """
        Sets the weights with the maya.pymel.core.deformerWeights command.

            Returns:
               pymel.core.PyNode: The created skin cluster.
        """

        self.io_manager.load(object_name=self.operating_node,
                             data_type="deformer_weights",
                             receiver_node=self.deformer_name,
                             data_file_name=self.FILE_NAMES["deformer_command"],
                             version=-1,
                             as_path=False,
                             )


    @DECORATORS.x_timer
    def export_data(self,
                    numpy=True,
                    json=False,
                    xml=False,
                    ng=False,
                    **kwargs
                    ):
        """
        Exports the data after the gather scene internal data has been run through-

        Args:
            numpy (bool): Flag to export the data as two compressed Numpy files.
            json (bool): Flag to export the data as a Json Dict.
            xml (bool): Flag to export the data as the Maya Export Deformer Weights Command.
            ng (bool): Flag to export the data as the NG2 Export Skinlayers Command.

        """

        super(SkinClusterOperator, self).export_data(**kwargs)

        # check if there are export methods specified.
        if not any((numpy, json, xml, ng)):
            raise exceptions.SkinclusterError("No export method was specified")

        if self.influence_matrices is None:
            raise exceptions.SkinclusterError("Skincluster Matrice Data was insufficient for the export.")

        if self.influence_names is None:
            raise exceptions.SkinclusterError("Skincluster Names was insufficient for the export.")

        self.io_manager.write(
                object_name=self.operating_node,
                data_to_write=self.influence_matrices,
                data_file_name=self.FILE_NAMES["influence_matrices"],
                data_type="npy",
                data_category=self.EXPORT_FOLDER_NAME,
        )

        self.io_manager.write(
                object_name=self.operating_node,
                data_to_write=self.influence_names,
                data_file_name=self.FILE_NAMES["influence_names"],
                data_type="npy",
                data_category=self.EXPORT_FOLDER_NAME,
        )

        # exports that are optional but at least one of them has to be exportable.
        if numpy:
            self._export_np()

        if json:
            self._export_json()

        if xml:
            self._export_xml()

        if ng and self.shape_mfn.hasFn(om2.MFn.kMesh):
            self._export_ng()

        self.is_already_rebuilt = False

    @DECORATORS.x_timer
    def _export_np(self, ):
        """
        Writes the compressed weight and legend file.

        """

        self.io_manager.write(
                object_name=self.operating_node,
                data_to_write=self.compressed_weights,
                data_file_name=self.FILE_NAMES["compressed_weights"],
                data_type=constants.NPY,
                data_category=self.EXPORT_FOLDER_NAME,
        )

        self.io_manager.write(
                object_name=self.operating_node,
                data_to_write=self.compressed_legend,
                data_file_name=self.FILE_NAMES["compressed_legend"],
                data_type=constants.NPY,
                data_category=self.EXPORT_FOLDER_NAME,
        )
        '''
        self.io_manager.write(
            object_name=self.operating_node,
            data_to_write=self.uncompressed_weights,
            data_file_name=self.FILE_NAMES["uncompressed_weights"],
            data_type=constants.NPY,
            data_category=self.EXPORT_FOLDER_NAME,
        )
        '''
        self.io_manager.write(
            object_name=self.operating_node,
            data_to_write=self.blend_weights,
            data_file_name=self.FILE_NAMES["blend_weights"],
            data_type=constants.NPY,
            data_category=self.EXPORT_FOLDER_NAME,
        )



    @DECORATORS.x_timer
    def _export_json(self, ):
        """
        Writes the json file in an uncompressed way.

        Returns:

        """
        # write the skin weight json data
        pass

    @DECORATORS.x_timer
    def _export_ng(self, ):
        if not self.is_already_rebuilt:
            _LOGGER.warning("rebuild needed for the data of externally created tools "
                            "since they do not prune like we do")

            self.rebuild_pruned()
            self.is_already_rebuilt = True

        _LOGGER.error("building NG")
        self.io_manager.write(object_name=self.operating_node,
                              data_file_name=self.FILE_NAMES["ng2_data"],
                              data_type="ng",
                              data_category=self.EXPORT_FOLDER_NAME,
                              )

    @DECORATORS.x_timer
    def _export_xml(self, ):
        if not self.is_already_rebuilt:
            _LOGGER.warning("rebuild needed for the data of externally created tools "
                            "since they do not prune like we do")

            self.rebuild_pruned()
            self.is_already_rebuilt = True

        self.io_manager.write(object_name=self.operating_node,
                              data_file_name=self.FILE_NAMES["deformer_command"],
                              node_to_export=self.deformer_node,
                              data_type="deformer_weights",
                              data_category=self.EXPORT_FOLDER_NAME,
                              )

    @DECORATORS.x_timer
    def correct_import_data(self, ):
        """
        Function to fix skin data before importing, will adjust joints in scene.

        """

        # double check if transform name stayed the same

        if not self.transform_name == self.transform_node_import.shortName().replace("_IMPORT", ""):
            raise exceptions.SkinclusterError(
                    f"the transform node seems to have changed from {self.transform_node_import} to {self.transform_name}."
            )
        '''
        print("shape_node_import", self.shape_node_import)
        print("shape_name", self.shape_name)
        print("shape_name_corrected", self.shape_name.split("|")[-1])
        print("shape_node_import_corrected", self.shape_node_import.longName().replace("_IMPORT", ""))

        # double check if shape name stayed the same
        if not self.shape_name.split("|")[-1] == self.shape_node_import.longName().replace("_IMPORT", ""):
            raise exceptions.SkinclusterError(
                    f"the shape node seems to have changed from {self.shape_node_import} to {self.shape_name}."
            )
        '''
        # check for skin cluster, if already there, unbind

        # remove skin cluster if there is one on it
        if self.deformer_node:
            pmc.skinCluster(self.deformer_node, edit=True, unbind=True)

        # sort out long names vs shortnames and if they exist in the scene
        nonexisting_joints = list()

        for indexed_pos_, inf_name in enumerate(self.influence_names):
            inf_name = str(inf_name)

            if cmds.objExists(inf_name):
                pass

            elif cmds.objExists(inf_name.split("|")[-1]):
                self.influence_names[indexed_pos_] = inf_name.split("|")[-1]

            else:
                nonexisting_joints.append((inf_name, indexed_pos_))

        # check if there are joints in the scene that do not exist, and will try to rebuild them
        if nonexisting_joints:

            if not self.build_nonexisting:

                # strong abort, will kick back an error that kills the whole script
                if self.abort_operation_on_joint_error:
                    raise exceptions.SkinclusterError(
                            f"Operation Aborted: "
                            f"There were influences in the data set of {self.operating_node}"
                            f" that are not in the scene. Discontinued processes."
                    )

                # soft abort, will return None but allows for further iterations when running as batch operation
                _LOGGER.warning(f"Operation Aborted on {self.operating_node}: "
                                f"This is due to a Skin Cluster error. "
                                f"Continuing processes.")
                return

            # operation happening if the non - existing joints options are not erroring out before
            _LOGGER.warning(f"Building the non existing joints on {self.operating_node} from file")

            for joint_long_name, indexed_pos_ in nonexisting_joints:
                self.recreate_non_existing_joint(indexed_pos_,
                                                 joint_long_name
                                                 )

        # set all joint lock influence weight to zero
        for inf in self.influence_names:
            if not cmds.attributeQuery("liw",
                                       node=inf,
                                       exists=True,
                                       ):
                continue

            cmds.setAttr(f"{inf}.liw", 0)

        return True

    def recreate_non_existing_joint(self, indexed_pos_, joint_long_name):
        # here is where ADJUSTMENTS
        joint_short_name = joint_long_name.split("|")[-1]

        joint_node = cmds.createNode("joint",
                                     n=joint_short_name,
                                     )

        cmds.setAttr(f"{joint_node}.useOutlinerColor", True)
        cmds.setAttr(f"{joint_node}.outlinerColor", 1, 0.2, 0.1)

        cmds.addAttr(
            joint_node,
            longName="isContinuityBuilt",
            at="bool",
            dv=True,
        )

        cmds.xform(
                joint_node, matrix=tuple(self.influence_matrices[0][indexed_pos_]), worldSpace=True
        )

        self.influence_names[indexed_pos_] = joint_node

        # check if newly created joints can be parented under an existing structure
        if (
                len(cmds.ls(joint_short_name)) == 1
                and len(joint_long_name.split("|")) >= 2
                and cmds.objExists(joint_long_name.split("|")[-2])
        ):
            pass

        return joint_node, joint_short_name


    @DECORATORS.x_timer
    def transfer_deformer(self, mesh_list=None, **kwargs):
        super(SkinClusterOperator, self).transfer_deformer(mesh_list=mesh_list,
                                                           )

        geo_names = [str(nde.shortName()) if isinstance(nde, pmc.PyNode)
                     else nde for nde
                     in mesh_list
                     ]

        from_skin_cluster_node, from_skincluster_position = self.get_specific_deformer_type()

        if not from_skin_cluster_node:
            _LOGGER.warning(f" cluster not found on {self.transform_name}")
            return

        from_influences = from_skin_cluster_node.getInfluence(q=True)
        from_influence_names = [str(nde.shortName()) for nde in from_influences]

        transferred_items = set()

        for geo_name in geo_names:
            to_skin_cluster_name = f"{geo_name.split(':')[-1].split('|')[-1]}_{self.DEFORMER_SUFFIX_NAME}"

            to_skin_cluster_node = get_skin_cluster(pmc.PyNode(geo_name))

            if to_skin_cluster_node:
                to_skin_cluster_name = str(to_skin_cluster_node.shortName())

            else:
                cmds.skinCluster(
                        from_influence_names,
                        geo_name,
                        maximumInfluences=30,
                        dropoffRate=4,
                        name=to_skin_cluster_name,
                        removeUnusedInfluence=False,
                )
                to_skin_cluster_node = pmc.PyNode(to_skin_cluster_name)

            to_influences = to_skin_cluster_node.getInfluence(q=True)
            to_influence_names = [str(nde.shortName()) for nde in to_influences]

            from_influences_set = set(from_influence_names)
            to_influences_set = set(to_influence_names)

            if not to_influences_set == from_influences_set:
                not_found_joints = list(from_influences_set - to_influences_set)

                if not_found_joints:
                    cmds.skinCluster(
                            to_skin_cluster_name, edit=True, ai=not_found_joints
                    )

            cmds.copySkinWeights(
                    self.transform_name,
                    geo_name,
                    surfaceAssociation="closestPoint",
                    influenceAssociation=[
                        "label",
                        "oneToOne",
                        "closestJoint",
                        "closestBone",
                    ],
                    noMirror=True,
            )

            transferred_items.add((geo_name, to_skin_cluster_name, SkinClusterOperator(geo_name)))

        return transferred_items

    def absolutize_deformer(self, **kwargs) -> dict[int, tuple[int, str]]:
        """Return the highest-weight influence per vertex.

                This method assumes the export pipeline has already run and produced:
                    - self.compressed_weights
                    - self.compressed_legend
                    - self.influence_names

                Returns:
                    dict[int, tuple[int, str]]:
                        Mapping:
                            vertex_id -> (influence_index, influence_name)
                """

        self.gather_scene_internal_data()

        if self.compressed_weights is None:
            raise RuntimeError("compressed_weights is not available. Run gather first.")
        if self.compressed_legend is None:
            raise RuntimeError("compressed_legend is not available. Run gather first.")
        if self.influence_names is None:
            raise RuntimeError("influence_names is not available. Run gather first.")

        # Reconstruct full table in export index space
        influence_count = self.influence_names.shape[0]

        full = self.compressed_to_full(
            self.compressed_weights,
            self.compressed_legend,
            influence_count,
        )

        # Compute top influence per vertex
        top_indices = full.argmax(axis=1)  # shape (num_verts,)

        # Build result dictionary
        result = {
            v: (int(idx), str(self.influence_names[idx]))
            for v, idx in enumerate(top_indices)
        }

        return result

    def kill_deformer(self, **kwargs):
        pmc.skinCluster(self.deformer_node, edit=True, unbind=True)

    def rebuild_deformer(self, **kwargs):
        self._om_set_weights()

    @DECORATORS.x_timer
    @set_attr_preparation
    def _set_weights(self, ):
        """
        Uses maya.cmds.setAttr() to set the weights according to the weights list.

        Returns:
            Bool: True if done.
        """
        if not self.uncompressed_weights:
            raise exceptions.SkinclusterError("no uncompressed weights were found to set")

        if not self.deformer_name:
            raise exceptions.SkinclusterError("no deformer name were found at ")

        for vert_id, weight_data in enumerate(self.uncompressed_weights):
            for inf_id, inf_value in list(weight_data.items()):
                weight_attr = f"{self.deformer_name}.weightList[{str(vert_id)}].weights[{str(inf_id)}]"
                cmds.setAttr(weight_attr, inf_value)

        return True

    def rename_deformer(self, **kwargs):
        """
        Renames the skin cluster in the scene or from given mesh shape match the names of the geometry.

        Args:
            mesh_list(list): Will use logic on given mesh shapes.
                             If None will find all mesh shapes in the scene.

        Returns:
            Bool: True if operation finished.

        """
        super(SkinClusterOperator, self).rename_deformer(update_data=False, **kwargs)


    @DECORATORS.x_timer
    def rebuild_pruned(self, **kwargs):
        """
        Rebuilds the skincluster as is, with the pruned information.

        Returns:

        """
        self.gather_scene_internal_data()
        self.rebuild_deformer()
        self.gather_scene_internal_data()



@DECORATORS.x_timer
def get_skin_cluster(geo):
    """
    Gets the skin cluster as a pmc.PyNode.

    Args:
        geo(pmc.PyNode):  the Transform you want to query

    Returns:
        pymel.core.PyNode: If geo has a skin cluster.
        None: If geo has no skin cluster.
    """

    skin_cluster_str = f'findRelatedSkinCluster("{geo.longName()}")'
    skin_cluster = str(pmc.mel.eval(skin_cluster_str))

    if skin_cluster:
        return pmc.PyNode(skin_cluster)

    return None
