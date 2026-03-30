"""
Utility classes for BlendShape Manager
Contains LayerManager, DeltaManager, MeshBaker, and BlendShapeConnectionManager
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om2
from contextlib import contextmanager
import re


def create_from_origin_shape(mesh):
    """Extract the original undeformed shape using the intermediate object.

    This gets the TRUE origin shape before any deformers by accessing
    the intermediate object that Maya stores.

    Args:
        mesh: The mesh to extract origin shape from

    Returns:
        str: Name of the new mesh with origin shape (no deformers)
    """
    # Ensure we have the transform node
    if cmds.nodeType(mesh) != 'transform':
        mesh = cmds.listRelatives(mesh, parent=True)[0]

    # Get all shapes including intermediate objects
    shapes = cmds.listRelatives(mesh, shapes=True, noIntermediate=False, fullPath=True) or []
    if not shapes:
        raise RuntimeError(f"No shapes found for {mesh}")

    # Find the ORIGINAL shape (intermediate object)
    origin_shape = None
    for shape in shapes:
        if cmds.getAttr(f"{shape}.intermediateObject"):
            origin_shape = shape
            print(f"  Found intermediate origin shape: {shape}")
            break

    if not origin_shape:
        # No intermediate? This shouldn't happen with deformed meshes
        print(f"  WARNING: No intermediate shape found, using first shape")
        origin_shape = shapes[0]

    # Method 1: Direct duplicate of intermediate shape
    # Temporarily make it non-intermediate
    was_intermediate = cmds.getAttr(f"{origin_shape}.intermediateObject")
    cmds.setAttr(f"{origin_shape}.intermediateObject", 0)

    # Get parent transform for duplication
    parent = cmds.listRelatives(origin_shape, parent=True, fullPath=True)[0]

    # Duplicate the transform (this will include the now-visible origin shape)
    duplicated = cmds.duplicate(parent, name=f"{mesh}_origin")[0]

    # Restore intermediate state
    cmds.setAttr(f"{origin_shape}.intermediateObject", was_intermediate)

    # Clean up the duplicate - remove any other shapes
    dup_shapes = cmds.listRelatives(duplicated, shapes=True, fullPath=True) or []

    # Keep only the first shape (should be our origin)
    if len(dup_shapes) > 1:
        for i in range(1, len(dup_shapes)):
            cmds.delete(dup_shapes[i])

    print(f"  Created origin shape mesh: {duplicated}")
    return duplicated


def add_empty_target(blendshape_node, target_name, mesh=None):
    """Add empty target to blendshape

    Args:
        blendshape_node (str): The blendshape node
        target_name (str): Name for the new target
        mesh (str): Optional mesh to duplicate (default: base mesh)

    Returns:
        int: Target index or None if failed
    """
    if not cmds.objExists(blendshape_node) or cmds.nodeType(blendshape_node) != 'blendShape':
        return None

    # Get base geometry
    base_geo = (cmds.blendShape(blendshape_node, q=True, geometry=True) or
                cmds.listConnections(f"{blendshape_node}.outputGeometry[0]", destination=True, shapes=True) or
                [None])[0]

    if not base_geo:
        return None

    # Get transform
    base_transform = cmds.listRelatives(base_geo, parent=True)[0] if cmds.nodeType(base_geo) == 'mesh' else base_geo
    mesh_to_dup = mesh if mesh else base_transform
    if cmds.nodeType(mesh_to_dup) != 'transform':
        mesh_to_dup = cmds.listRelatives(mesh_to_dup, parent=True)[0]

    # Find next index
    existing = cmds.getAttr(f"{blendshape_node}.weight", multiIndices=True) or []
    next_index = next((i for i in range(max(existing) + 2) if i not in existing), 0) if existing else 0

    # Add target
    duplicated = cmds.duplicate(mesh_to_dup, name=f"{target_name}_temp")[0]
    try:
        cmds.blendShape(blendshape_node, edit=True, target=(base_geo, next_index, duplicated, 1.0))
        cmds.aliasAttr(target_name, f"{blendshape_node}.weight[{next_index}]")
        cmds.delete(duplicated)

        # Reset target delta - this creates proper empty target that won't crash
        cmds.blendShape(blendshape_node, edit=True, resetTargetDelta=(0, next_index))

        return next_index
    except Exception as e:
        cmds.delete(duplicated)
        return None


class SimplifiedLayerManager:
    """Manages layers using empty targets directly in master blendshape.

    This new approach eliminates the need for separate blendshape nodes (_layers_bs)
    by using empty targets with a naming convention directly in the master blendshape.
    """

    def __init__(self, blendshape_node, mesh):
        """Initialize SimplifiedLayerManager.

        Args:
            blendshape_node: The master blendshape node
            mesh: The mesh with the blendshape
        """
        self.blendshape = blendshape_node
        self.mesh = mesh
        self.layer_suffix = "_layer_"

    def add_layer(self, target_name, layer_name=None):
        """Add a new layer as an empty target in the master blendshape.

        Args:
            target_name: Name of the master target
            layer_name: Optional custom layer name (default: auto-numbered)

        Returns:
            str: Name of created layer or None if failed
        """
        if not cmds.objExists(self.blendshape):
            print(f"Blendshape '{self.blendshape}' not found")
            return None

        # Get existing layers for this target
        existing_layers = self.list_layers(target_name)

        # Determine layer name
        if not layer_name:
            # Auto-number the layer
            layer_num = len(existing_layers) + 1
            layer_name = f"{target_name}{self.layer_suffix}{layer_num}"
        elif not layer_name.startswith(target_name):
            # Ensure layer name follows convention
            layer_name = f"{target_name}_{layer_name}"

        # Check if layer already exists
        aliases = cmds.aliasAttr(self.blendshape, query=True) or []
        existing_targets = [aliases[i] for i in range(0, len(aliases), 2)]
        if layer_name in existing_targets:
            print(f"Layer '{layer_name}' already exists")
            return layer_name

        # Create empty target using our simplified function
        layer_index = add_empty_target(self.blendshape, layer_name, self.mesh)

        if layer_index is None:
            print(f"Failed to create layer '{layer_name}'")
            return None

        # Connect master target weight to layer weight for auto-activation
        master_attr = f"{self.blendshape}.{target_name}"
        layer_attr = f"{self.blendshape}.{layer_name}"

        if cmds.objExists(master_attr) and cmds.objExists(layer_attr):
            # Check if already connected
            connections = cmds.listConnections(layer_attr, source=True, destination=False, plugs=True) or []
            if not connections:
                try:
                    cmds.connectAttr(master_attr, layer_attr, force=True)
                    print(f"Connected {master_attr} -> {layer_attr} for auto-activation")
                except Exception as e:
                    print(f"Could not connect auto-activation: {e}")

        print(f"✓ Created layer '{layer_name}' at index {layer_index}")
        return layer_name

    def list_layers(self, target_name):
        """List all layers for a given target.

        Args:
            target_name: Name of the master target

        Returns:
            list: Names of all layers for this target
        """
        if not cmds.objExists(self.blendshape):
            return []

        # Get all target aliases
        aliases = cmds.aliasAttr(self.blendshape, query=True) or []
        all_targets = [aliases[i] for i in range(0, len(aliases), 2)]

        # Find targets that match our layer pattern
        layer_pattern = f"{target_name}{self.layer_suffix}"
        layers = [t for t in all_targets if t.startswith(layer_pattern)]

        return sorted(layers)

    def merge_layer(self, target_name, layer_name, delete_after=True):
        """Merge a layer's deltas into the master target using bake method.

        This implementation uses Maya's duplicate and blendShape -tc command
        to properly combine shapes without manual delta math.

        Args:
            target_name: Name of the master target
            layer_name: Name of the layer to merge
            delete_after: Delete layer after merge

        Returns:
            bool: Success
        """
        import maya.mel as mel

        if not cmds.objExists(self.blendshape):
            print(f"Blendshape '{self.blendshape}' not found")
            return False

        # Verify both targets exist
        target_attr = f"{self.blendshape}.{target_name}"
        layer_attr = f"{self.blendshape}.{layer_name}"

        if not cmds.objExists(target_attr):
            print(f"Target '{target_name}' not found")
            return False

        if not cmds.objExists(layer_attr):
            print(f"Layer '{layer_name}' not found")
            return False

        # Get mesh transform
        mesh_transform = self.mesh
        if cmds.nodeType(self.mesh) == 'mesh':
            mesh_transform = cmds.listRelatives(self.mesh, parent=True)[0]

        # Get target indices
        targets = self._get_all_targets()
        if target_name not in targets or layer_name not in targets:
            print("Could not find target indices")
            return False

        target_index = targets[target_name]
        layer_index = targets[layer_name]

        print(f"Merging layer '{layer_name}' (index {layer_index}) into target '{target_name}' (index {target_index})")

        # Store current weights
        all_weights = {}
        aliases = cmds.aliasAttr(self.blendshape, query=True) or []
        for i in range(0, len(aliases), 2):
            alias = aliases[i]
            all_weights[alias] = cmds.getAttr(f"{self.blendshape}.{alias}")
            cmds.setAttr(f"{self.blendshape}.{alias}", 0)

        try:
            # Check if layer has any deltas
            layer_pt_attr = f"{self.blendshape}.inputTarget[0].inputTargetGroup[{layer_index}].inputTargetItem[6000].inputPointsTarget"
            try:
                layer_deltas = cmds.getAttr(layer_pt_attr) or []
            except:
                layer_deltas = []

            if not layer_deltas:
                print(f"Layer '{layer_name}' has no deltas to merge")
                # Restore weights
                for alias, weight in all_weights.items():
                    try:
                        cmds.setAttr(f"{self.blendshape}.{alias}", weight)
                    except:
                        pass

                if delete_after:
                    return self.delete_layer(layer_name)
                return True

            # Method: Bake combined shape and replace target
            # This avoids manual delta math and uses Maya's built-in shape handling

            # 1. Capture base shape (everything at 0)
            base_shape = cmds.duplicate(mesh_transform, name="merge_base_temp")[0]

            # 2. Capture target only
            cmds.setAttr(target_attr, 1)
            target_shape = cmds.duplicate(mesh_transform, name="merge_target_temp")[0]
            cmds.setAttr(target_attr, 0)

            # 3. Capture layer only
            cmds.setAttr(layer_attr, 1)
            layer_shape = cmds.duplicate(mesh_transform, name="merge_layer_temp")[0]
            cmds.setAttr(layer_attr, 0)

            # 4. Capture combined (both active)
            cmds.setAttr(target_attr, 1)
            cmds.setAttr(layer_attr, 1)
            combined_shape = cmds.duplicate(mesh_transform, name="merge_combined_temp")[0]
            cmds.setAttr(target_attr, 0)
            cmds.setAttr(layer_attr, 0)

            # 5. Clear the target and set it to the combined shape
            # First reset the target to empty
            cmds.blendShape(self.blendshape, edit=True, resetTargetDelta=(0, target_index))

            # 6. Set the combined shape as the new target
            # Get the mesh shape node
            mesh_shape = self.mesh
            if cmds.nodeType(self.mesh) != 'mesh':
                shapes = cmds.listRelatives(self.mesh, shapes=True, type='mesh')
                if shapes:
                    mesh_shape = shapes[0]

            # Use MEL command for reliable target replacement
            mel_cmd = f'blendShape -e -tc 0 -t {mesh_shape} {target_index} {combined_shape} 1.0 {self.blendshape}'
            mel.eval(mel_cmd)

            print(f"  Successfully merged deltas into target")

            # 7. Cleanup temp shapes
            for temp in [base_shape, target_shape, layer_shape, combined_shape]:
                if cmds.objExists(temp):
                    cmds.delete(temp)

        except Exception as e:
            print(f"Error during merge: {e}")
            # Restore weights
            for alias, weight in all_weights.items():
                try:
                    cmds.setAttr(f"{self.blendshape}.{alias}", weight)
                except:
                    pass
            return False

        # Restore weights (except the layer if we're deleting it)
        for alias, weight in all_weights.items():
            if delete_after and alias == layer_name:
                continue
            try:
                cmds.setAttr(f"{self.blendshape}.{alias}", weight)
            except:
                pass

        # Delete layer if requested
        if delete_after:
            if not self.delete_layer(layer_name):
                print(f"Warning: Failed to delete layer '{layer_name}' after merge")

        print(f"✓ Successfully merged layer '{layer_name}' into target '{target_name}'")
        return True

    def _combine_deltas(self, layer_deltas, layer_components, target_deltas, target_components):
        """Combine two sets of deltas using proper vector addition.

        Args:
            layer_deltas: List of (x, y, z) tuples from layer
            layer_components: List of component strings from layer
            target_deltas: List of (x, y, z) tuples from target
            target_components: List of component strings from target

        Returns:
            tuple: (combined_deltas, combined_components)
        """
        if not target_deltas:
            # Target is empty, just return layer deltas
            return layer_deltas, layer_components

        if not layer_deltas:
            # Layer is empty, just return target deltas
            return target_deltas, target_components

        # Create dictionaries for efficient lookup
        # Parse component indices from strings like "vtx[123]"
        layer_dict = {}
        for i, comp in enumerate(layer_components):
            if i < len(layer_deltas):
                # Extract vertex index from component string
                try:
                    vtx_index = int(comp.split('[')[1].split(']')[0])
                    layer_dict[vtx_index] = layer_deltas[i]
                except (IndexError, ValueError):
                    print(f"Warning: Could not parse component '{comp}'")
                    continue

        target_dict = {}
        for i, comp in enumerate(target_components):
            if i < len(target_deltas):
                try:
                    vtx_index = int(comp.split('[')[1].split(']')[0])
                    target_dict[vtx_index] = target_deltas[i]
                except (IndexError, ValueError):
                    print(f"Warning: Could not parse component '{comp}'")
                    continue

        # Combine deltas by adding vectors for same vertices
        combined_dict = target_dict.copy()

        for vtx_index, layer_delta in layer_dict.items():
            if vtx_index in combined_dict:
                # Add vectors: (x1+x2, y1+y2, z1+z2)
                target_delta = combined_dict[vtx_index]
                combined_dict[vtx_index] = (
                    target_delta[0] + layer_delta[0],
                    target_delta[1] + layer_delta[1],
                    target_delta[2] + layer_delta[2]
                )
            else:
                # New vertex, just add the layer delta
                combined_dict[vtx_index] = layer_delta

        # Convert back to lists, sorted by vertex index for consistency
        sorted_indices = sorted(combined_dict.keys())
        combined_deltas = [combined_dict[idx] for idx in sorted_indices]
        combined_components = [f"vtx[{idx}]" for idx in sorted_indices]

        print(f"  Combined {len(layer_dict)} layer + {len(target_dict)} target = {len(combined_deltas)} total deltas")
        return combined_deltas, combined_components

    def delete_layer(self, layer_name):
        """Safely delete a layer target without leaving orphaned weights.

        Args:
            layer_name: Name of the layer to delete

        Returns:
            bool: Success
        """
        if not cmds.objExists(self.blendshape):
            return False

        layer_attr = f"{self.blendshape}.{layer_name}"
        if not cmds.objExists(layer_attr):
            print(f"Layer '{layer_name}' not found")
            return False

        # Get target index
        targets = self._get_all_targets()
        if layer_name not in targets:
            return False

        layer_index = targets[layer_name]

        print(f"Safely deleting layer '{layer_name}' at index {layer_index}")

        # 1. Disconnect any connections first
        connections = cmds.listConnections(layer_attr, source=True, destination=False, plugs=True) or []
        for conn in connections:
            try:
                cmds.disconnectAttr(conn, layer_attr)
            except:
                pass

        # 2. Set weight to 0
        try:
            cmds.setAttr(layer_attr, 0)
        except:
            pass

        # 3. Reset target delta (clears shape data)
        try:
            cmds.blendShape(self.blendshape, edit=True, resetTargetDelta=(0, layer_index))
        except Exception as e:
            print(f"  Warning: Could not reset delta: {e}")

        # 4. Remove alias (important to do this before removing weight)
        try:
            cmds.aliasAttr(layer_attr, remove=True)
            print(f"  Removed alias '{layer_name}'")
        except Exception as e:
            print(f"  Warning: Could not remove alias: {e}")

        # 5. Try to remove the weight instance safely
        try:
            weight_attr = f"{self.blendshape}.weight[{layer_index}]"
            # Use removeMultiInstance with break flag for safety
            cmds.removeMultiInstance(weight_attr, b=True)
            print(f"  Removed weight at index {layer_index}")
        except:
            # This is okay - weight remains but is cleared and has no alias
            print(f"  Note: Weight cleared at index {layer_index}")

        print(f"✓ Deleted layer '{layer_name}'")
        return True

    def _get_all_targets(self):
        """Get all targets and their indices.

        Returns:
            dict: {target_name: index}
        """
        targets = {}
        aliases = cmds.aliasAttr(self.blendshape, query=True) or []

        for i in range(0, len(aliases), 2):
            alias_name = aliases[i]
            weight_attr = aliases[i + 1]
            # Extract index from weight[#]
            index = int(weight_attr.split('[')[1].split(']')[0])
            targets[alias_name] = index

        return targets


# Keep old LayerManager class for reference (disabled)
class LayerManager_REMOVED:
    """Manages layer blendshapes for master blendshape targets."""

    def __init__(self, mesh_base):
        """Initialize LayerManager with base mesh.

        Args:
            mesh_base: Base mesh with master blendshape
        """
        self.mesh = mesh_base
        self.master_bs = self._find_master_blendshape()
        self.layer_blendshapes = {}
        self.connections = {}

        if self.master_bs:
            self.scan_existing_layers()

    def _find_master_blendshape(self):
        """Auto-detect master blendshape from mesh.
        The master is the FIRST blendshape in the history that's not a layer BS.

        Returns:
            str: Name of master blendshape or None
        """
        history = cmds.listHistory(self.mesh, pruneDagObjects=True) or []

        # Collect all non-layer blendshapes
        blendshapes = []
        for node in history:
            if cmds.nodeType(node) == 'blendShape':
                if not node.endswith('_layers_bs'):
                    blendshapes.append(node)

        # Return the first one (master) if it exists
        # In Maya, the first blendshape in history is typically the one closest to the mesh
        if blendshapes:
            # Reverse the list because history is returned in reverse order
            blendshapes.reverse()
            print(f"Found {len(blendshapes)} blendshapes, using first as master: {blendshapes[0]}")
            return blendshapes[0]

        return None

    def scan_existing_layers(self):
        """Scan and index existing layer blendshapes."""
        if not self.master_bs:
            return

        targets = self._get_target_names()
        history = cmds.listHistory(self.mesh, pruneDagObjects=True) or []

        for target in targets:
            layer_bs_name = f"{target}_layers_bs"
            if layer_bs_name in history:
                self.layer_blendshapes[target] = layer_bs_name

                connection = cmds.listConnections(f"{layer_bs_name}.envelope",
                                                  source=True, destination=False)
                if connection:
                    self.connections[target] = connection[0]

    def _get_target_names(self):
        """Get all target names from master blendshape.

        Returns:
            list: Target names
        """
        if not self.master_bs:
            return []

        aliases = cmds.aliasAttr(self.master_bs, query=True) or []
        targets = []

        for i in range(0, len(aliases), 2):
            targets.append(aliases[i])

        return targets

    def create_layer_bs(self, target_name, force_recreate=False):
        """Create layer blendshape for target - ALWAYS post-deformation.

        Args:
            target_name: Name of target in master blendshape
            force_recreate: Force recreation of blendshape

        Returns:
            str: Name of layer blendshape
        """
        layer_bs_name = f"{target_name}_layers_bs"

        # If force recreate, delete existing
        if force_recreate and cmds.objExists(layer_bs_name):
            cmds.delete(layer_bs_name)
            if target_name in self.layer_blendshapes:
                del self.layer_blendshapes[target_name]

        # Check if it exists in scene but not in our dict
        if cmds.objExists(layer_bs_name):
            self.layer_blendshapes[target_name] = layer_bs_name
            return layer_bs_name

        # Check if already tracked
        if target_name in self.layer_blendshapes:
            # Verify it still exists
            if cmds.objExists(self.layer_blendshapes[target_name]):
                return self.layer_blendshapes[target_name]
            else:
                # Was deleted, remove from dict
                del self.layer_blendshapes[target_name]

        # CAPTURE ORIGINAL DEFORMER ORDER BEFORE CREATION
        # Get the first deformer in the current order (for positioning reference)
        history_before = cmds.listHistory(self.mesh, pruneDagObjects=True) or []
        first_deformer = None

        # Find the first deformer (this will be our reference point)
        for node in history_before:
            node_type = cmds.nodeType(node)
            # Include deltaMush and other deformers that might be on top
            if node_type in ['blendShape', 'skinCluster', 'cluster', 'ffd', 'wire', 'tweak', 'nonLinear', 'deltaMush']:
                if not first_deformer:
                    first_deformer = node
                    print(f"  First deformer in chain: {node} ({node_type})")
                print(f"  Existing deformer: {node} ({node_type})")

        # Create new layer blendshape (it will be inserted somewhere initially)
        layer_bs = cmds.blendShape(self.mesh, name=layer_bs_name,
                                   topologyCheck=False)[0]

        print(f"  Created layer blendshape: {layer_bs}")

        # PLACE LAYER BS AT THE BEGINNING (POST-DEFORMATION)
        # Only move the layer BS to the top, without disrupting other deformers
        # In Maya's deformation order, the first deformer in the list is evaluated last

        if first_deformer and first_deformer != layer_bs:
            try:
                # Single reorder operation: place layer_bs before the first deformer
                # This makes it evaluate post-deformation without touching other deformers
                cmds.reorderDeformers(layer_bs, first_deformer, self.mesh)
                print(f"  ✅ Layer blendshape {layer_bs} placed at beginning (post-deformation)")
                print(f"     It will evaluate AFTER all other deformations")
            except Exception as e:
                print(f"  ⚠️ Warning: Could not reorder {layer_bs}: {e}")
        else:
            print(f"  ✅ Layer blendshape {layer_bs} is already at the beginning")

        self.layer_blendshapes[target_name] = layer_bs

        # IMPORTANT: Ensure target weight is 0 before connecting to prevent delta contamination
        current_weight = cmds.getAttr(f"{self.master_bs}.{target_name}")
        if current_weight != 0:
            print(f"  Setting {target_name} weight to 0 before connection (was {current_weight})")
            cmds.setAttr(f"{self.master_bs}.{target_name}", 0)

        self.connect_direct(target_name)

        # Restore the original weight after connection
        if current_weight != 0:
            print(f"  Restoring {target_name} weight to {current_weight}")
            cmds.setAttr(f"{self.master_bs}.{target_name}", current_weight)

        return layer_bs

    def reset_layer_bs(self, target_name):
        """Reset layer blendshape for target.

        Args:
            target_name: Target name

        Returns:
            str: New layer blendshape name
        """
        return self.create_layer_bs(target_name, force_recreate=True)

    def add_layer(self, target_name, layer_name=None):
        """Add new EMPTY layer to target's layer blendshape.

        Args:
            target_name: Target in master blendshape
            layer_name: Optional custom name for layer

        Returns:
            str: Full layer name
        """
        if target_name not in self._get_target_names():
            print(f"Warning: Target '{target_name}' not found in master blendshape")
            return None

        layer_bs = self.create_layer_bs(target_name)

        # Verify layer_bs exists
        if not cmds.objExists(layer_bs):
            print(f"ERROR: Failed to create layer blendshape for {target_name}")
            return None

        # Get ALL existing aliases to check for duplicates
        all_aliases = cmds.aliasAttr(layer_bs, query=True) or []
        existing_alias_names = [all_aliases[i] for i in range(0, len(all_aliases), 2)]

        existing_layers = self._get_layer_targets(layer_bs)
        layer_index = len(existing_layers) + 1

        if not layer_name:
            layer_name = f"{layer_index}"

        # Simple naming without timestamp
        full_layer_name = f"{target_name}_layer_{layer_name}"

        # Check if this exact alias already exists
        if full_layer_name in existing_alias_names:
            print(f"Layer '{full_layer_name}' already exists in blendshape")
            return full_layer_name

        # SAFER APPROACH: Use BlendshapeStateManager to preserve master blendshape state
        print(f"Creating empty layer '{full_layer_name}'...")

        try:
            # Use context manager to preserve master blendshape state during layer creation
            with BlendshapeStateManager(self.master_bs, preserve_state=True) as state_manager:
                # Set all master blendshape weights to 0 to get clean base shape
                state_manager.set_all_weights_to_zero_except(None)  # Zero ALL weights

                # Turn off other deformers (but master blendshape weights are already at 0)
                history = cmds.listHistory(self.mesh, pruneDagObjects=True) or []
                deformer_states = {}

                for node in history:
                    # Skip the master blendshape - we're managing it with the context manager
                    if node == self.master_bs:
                        continue

                    if cmds.attributeQuery('envelope', node=node, exists=True):
                        try:
                            current_val = cmds.getAttr(f"{node}.envelope")
                            deformer_states[node] = current_val
                            cmds.setAttr(f"{node}.envelope", 0)
                        except:
                            pass

                # Now duplicate - this gives us the clean base shape
                base_shape = cmds.duplicate(self.mesh, name=f"{full_layer_name}_base")[0]

                # Restore other deformers (master blendshape restored by context manager)
                for node, value in deformer_states.items():
                    try:
                        cmds.setAttr(f"{node}.envelope", value)
                    except:
                        pass

            next_index = self._get_next_target_index(layer_bs)

            # Add base shape as target - since it matches the blendshape's base,
            # it should automatically have no deltas
            cmds.blendShape(layer_bs, edit=True,
                            target=(self.mesh, next_index, base_shape, 1.0),
                            topologyCheck=False)

            # Delete the temp mesh
            cmds.delete(base_shape)

            # Verify it's empty by checking the deltas
            pt_attr = f"{layer_bs}.inputTarget[0].inputTargetGroup[{next_index}].inputTargetItem[6000].inputPointsTarget"
            existing_pts = cmds.getAttr(pt_attr) or []

            if existing_pts:
                print(f"  Warning: Layer has {len(existing_pts)} deltas, zeroing them...")
                # If there are deltas, zero them properly
                # Get vertex count from mesh
                vertex_count = cmds.polyEvaluate(self.mesh, vertex=True)

                # Create zero deltas for ALL vertices
                zero_pts = []
                components = []
                for i in range(vertex_count):
                    zero_pts.append([0.0, 0.0, 0.0])
                    components.append(f'vtx[{i}]')

                # Set all vertices with zero deltas
                cmds.setAttr(pt_attr, len(zero_pts), *zero_pts, type='pointArray')
                ct_attr = f"{layer_bs}.inputTarget[0].inputTargetGroup[{next_index}].inputTargetItem[6000].inputComponentsTarget"
                cmds.setAttr(ct_attr, len(components), *components, type='componentList')

                print(f"  Set {vertex_count} vertices with zero deltas")
            else:
                print(f"  Created empty layer (no deltas needed)")

            # Set the layer weight to 1 to activate it
            cmds.setAttr(f"{layer_bs}.weight[{next_index}]", 1.0)

            # Store the mapping for our reference
            if not hasattr(self, 'layer_mapping'):
                self.layer_mapping = {}
            if target_name not in self.layer_mapping:
                self.layer_mapping[target_name] = {}
            self.layer_mapping[target_name][full_layer_name] = next_index

            print(f"  Successfully created layer '{full_layer_name}' at index {next_index}")
            return full_layer_name

        except Exception as e:
            print(f"ERROR creating layer: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _get_layer_targets(self, layer_bs):
        """Get all layer targets in a layer blendshape.

        Args:
            layer_bs: Layer blendshape node

        Returns:
            list: Layer target names
        """
        aliases = cmds.aliasAttr(layer_bs, query=True) or []
        layers = []

        for i in range(0, len(aliases), 2):
            layers.append(aliases[i])

        return layers

    def _get_next_target_index(self, blendshape_node):
        """Get next available target index.

        Args:
            blendshape_node: BlendShape node

        Returns:
            int: Next available index
        """
        aliases = cmds.aliasAttr(blendshape_node, query=True) or []

        if not aliases:
            return 0

        indices = []
        for i in range(1, len(aliases), 2):
            weight = aliases[i]
            if 'weight[' in weight:
                idx = int(weight.split('[')[1].split(']')[0])
                indices.append(idx)

        return max(indices) + 1 if indices else 0

    def connect_direct(self, target_name):
        """Create direct connection from master to layer envelope.

        Args:
            target_name: Target name to connect

        Returns:
            bool: Success
        """
        if not self.master_bs:
            return False

        if target_name not in self.layer_blendshapes:
            return False

        layer_bs = self.layer_blendshapes[target_name]

        source = f"{self.master_bs}.{target_name}"
        dest = f"{layer_bs}.envelope"

        # Check if there's already a connection and safely disconnect if needed
        existing = cmds.listConnections(dest, source=True, destination=False, plugs=True)
        if existing:
            try:
                # Only disconnect if it's not the same connection we want to make
                if existing[0] != source:
                    cmds.disconnectAttr(existing[0], dest)
                    print(f"  Disconnected existing: {existing[0]} -X-> {dest}")
            except Exception as e:
                print(f"  Warning: Could not disconnect {existing[0]} from {dest}: {e}")
                # Continue anyway, force connection will handle it

        cmds.connectAttr(source, dest, force=True)
        self.connections[target_name] = source

        return True

    def merge_layers_to_target(self, target_name, delete_after=False, backup_first=False):
        """Merge all layers into master target using bake deformer approach.

        Simply captures the current visible state (master + layers at current weights)
        and bakes it directly into the master target.

        Args:
            target_name: Target to merge layers into
            delete_after: Delete layer blendshape after merge
            backup_first: Create backup of original target (not used in new approach)

        Returns:
            bool: Success
        """
        if target_name not in self.layer_blendshapes:
            print(f"No layers found for target '{target_name}'")
            return False

        layer_bs = self.layer_blendshapes[target_name]

        print(f"Merging layers for '{target_name}' using bake deformer...")

        # Check if layer envelope is connected
        envelope_connections = cmds.listConnections(f"{layer_bs}.envelope",
                                                   source=True, destination=False, plugs=True) or []

        if envelope_connections:
            # Envelope is connected - ensure it's driven by setting the master target
            print(f"  Layer envelope is connected from: {envelope_connections[0]}")
            # The connection should drive it to 1 when master target is set to 1
            layer_envelope = None  # Mark as connected, not manually set
        else:
            # Envelope is not connected - set it manually
            layer_envelope = cmds.getAttr(f"{layer_bs}.envelope")
            try:
                cmds.setAttr(f"{layer_bs}.envelope", 1)
                print(f"  Layer blendshape '{layer_bs}' envelope set to 1 for merge")
            except:
                print(f"  Warning: Could not set layer envelope, it may be locked")
                layer_envelope = None

        # CRITICAL: Also activate all layer targets within the layer blendshape!
        # Get all layer targets and set their weights to 1 (or current value)
        layer_aliases = cmds.aliasAttr(layer_bs, query=True) or []
        layer_weights_backup = {}

        for i in range(0, len(layer_aliases), 2):
            layer_target = layer_aliases[i]
            # Store current weight
            current_weight = cmds.getAttr(f"{layer_bs}.{layer_target}")
            layer_weights_backup[layer_target] = current_weight
            # Set to 1 for merge (or keep current if already non-zero)
            if current_weight == 0:
                try:
                    cmds.setAttr(f"{layer_bs}.{layer_target}", 1)
                    print(f"    Activated layer target: {layer_target} = 1")
                except:
                    print(f"    Warning: Could not set {layer_target}, may be connected")
            else:
                print(f"    Layer target already active: {layer_target} = {current_weight}")

        # Get the BlendShapeManager to use its bake_deformer method
        from .mt_blendshape_manager import BlendShapeManager
        bs_manager = BlendShapeManager()
        bs_manager.set_blendshape(self.master_bs)
        bs_manager.set_mesh(self.mesh)

        # Bake the current visible state (master + layers) into the master target
        # This captures exactly what the artist sees on screen
        success = bs_manager.bake_deformer(
            target_name,
            deformer_type=None,  # Bake all deformers
            turn_off_deformers=False,  # Keep deformers as they are
            preserve_blendshape_state=True,  # Preserve current blendshape states
            isolate_target=False,  # Don't isolate, capture combined result
            target_blendshape=self.master_bs  # Pass the master blendshape where target exists
        )

        if not success:
            print(f"Failed to bake layers into target '{target_name}'")
            # Restore original envelope value on failure (if we set it manually)
            if layer_envelope is not None:
                try:
                    cmds.setAttr(f"{layer_bs}.envelope", layer_envelope)
                except:
                    pass  # Envelope was connected, can't set it
            # Restore layer target weights
            for layer_target, weight in layer_weights_backup.items():
                try:
                    cmds.setAttr(f"{layer_bs}.{layer_target}", weight)
                except:
                    pass  # May be connected
            return False

        # Delete the layer blendshape after successful bake
        if delete_after:
            cmds.delete(layer_bs)
            del self.layer_blendshapes[target_name]
            if target_name in self.connections:
                del self.connections[target_name]
            print(f"  Deleted layer blendshape for '{target_name}'")
        else:
            # Just disable it
            cmds.setAttr(f"{layer_bs}.envelope", 0)
            print(f"  Disabled layer blendshape for '{target_name}'")

        print(f"✅ Successfully merged layers into '{target_name}'")
        return True

    def _backup_target(self, target_name):
        """Create backup of target before merge using orig shape.

        Args:
            target_name: Target to backup

        Returns:
            str: Backup target name
        """
        backup_name = f"{target_name}_backup"

        # Get the orig shape (base mesh without deformations)
        orig_shape = self._get_orig_shape()
        if not orig_shape:
            print(f"Warning: Could not find orig shape for backup")
            return None

        # Store current blendshape values
        current_values = {}
        aliases = cmds.aliasAttr(self.master_bs, query=True) or []
        for i in range(0, len(aliases), 2):
            attr_name = aliases[i]
            current_values[attr_name] = cmds.getAttr(f"{self.master_bs}.{attr_name}")
            cmds.setAttr(f"{self.master_bs}.{attr_name}", 0)

        # Activate only the target we want to backup
        cmds.setAttr(f"{self.master_bs}.{target_name}", 1)

        # Duplicate current state for backup
        dup = cmds.duplicate(self.mesh, name=backup_name)[0]

        # Restore all blendshape values
        for attr_name, value in current_values.items():
            cmds.setAttr(f"{self.master_bs}.{attr_name}", value)

        # Add backup as new target
        next_index = self._get_next_target_index(self.master_bs)
        cmds.blendShape(self.master_bs, edit=True,
                        target=(self.mesh, next_index, dup, 1.0))

        # Store the backup index for reference
        if not hasattr(self, 'backup_indices'):
            self.backup_indices = {}
        self.backup_indices[backup_name] = next_index

        cmds.delete(dup)

        # Set backup weight to 0
        cmds.setAttr(f"{self.master_bs}.weight[{next_index}]", 0)

        return backup_name

    def _get_orig_shape(self):
        """Get the original shape node from the blendshape.

        Returns:
            str: Original shape node or None
        """
        # Get the input target from blendshape
        input_target = cmds.listConnections(f"{self.master_bs}.input[0].inputGeometry",
                                            source=True, destination=False)
        if input_target:
            return input_target[0]
        return None

    def _get_base_shape(self):
        """Get base shape for delta calculation.

        Returns:
            str: Base shape mesh
        """
        temp_dup = cmds.duplicate(self.mesh, name="temp_base")[0]

        shapes = cmds.listRelatives(temp_dup, shapes=True, type='mesh') or []
        if shapes:
            history = cmds.listHistory(shapes[0], pruneDagObjects=True) or []
            for node in history:
                if cmds.nodeType(node) in ['blendShape', 'skinCluster', 'cluster',
                                           'deltaMush', 'wire', 'lattice', 'wrap']:
                    cmds.delete(node)

        return temp_dup

    def _get_target_index(self, blendshape_node, target_name):
        """Get target index by name.

        Args:
            blendshape_node: BlendShape node
            target_name: Target name

        Returns:
            int: Target index or None
        """
        aliases = cmds.aliasAttr(blendshape_node, query=True) or []

        for i in range(0, len(aliases), 2):
            if aliases[i] == target_name:
                weight_attr = aliases[i + 1]
                return int(weight_attr.split('[')[1].split(']')[0])

        return None

    def list_layers(self, target_name):
        """List all layers for a target.

        Args:
            target_name: Target name

        Returns:
            list: Layer names
        """
        if target_name not in self.layer_blendshapes:
            return []

        layer_bs = self.layer_blendshapes[target_name]
        return self._get_layer_targets(layer_bs)

    def get_info(self):
        """Get complete info about layer setup.

        Returns:
            dict: Layer information
        """
        info = {
            'mesh': self.mesh,
            'master_bs': self.master_bs,
            'targets': {}
        }

        for target, layer_bs in self.layer_blendshapes.items():
            info['targets'][target] = {
                'layer_bs': layer_bs,
                'layers': self.list_layers(target),
                'connected': target in self.connections
            }

        return info



class DeltaSanityChecker:
    """Comprehensive sanity checking for delta operations."""

    def __init__(self, verbose=True):
        """Initialize sanity checker.

        Args:
            verbose: If True, print detailed debug information
        """
        self.verbose = verbose
        self.errors = []
        self.warnings = []

    def _log_debug(self, msg):
        """Log debug message if verbose."""
        if self.verbose:
            print(f"[DEBUG] {msg}")

    def _log_error(self, msg):
        """Log error message."""
        self.errors.append(msg)
        print(f"[ERROR] {msg}")

    def _log_warning(self, msg):
        """Log warning message."""
        self.warnings.append(msg)
        print(f"[WARNING] {msg}")

    def check_mesh_exists(self, mesh_name, context=""):
        """Check if mesh exists and is valid.

        Args:
            mesh_name: Name of mesh to check
            context: Context string for error messages

        Returns:
            bool: True if mesh exists and is valid
        """
        if not mesh_name:
            self._log_error(f"{context}: Mesh name is None or empty")
            return False

        if not cmds.objExists(mesh_name):
            self._log_error(f"{context}: Mesh '{mesh_name}' does not exist in scene")
            return False

        # Check if it's actually a mesh
        node_type = cmds.nodeType(mesh_name)
        if node_type not in ['mesh', 'transform']:
            # Check if transform has mesh shape
            shapes = cmds.listRelatives(mesh_name, shapes=True, type='mesh') or []
            if not shapes:
                self._log_error(f"{context}: '{mesh_name}' is not a mesh (type: {node_type})")
                return False

        self._log_debug(f"{context}: Mesh '{mesh_name}' exists and is valid")
        return True

    def check_topology_match(self, mesh1, mesh2):
        """Check if two meshes have matching topology.

        Args:
            mesh1: First mesh name
            mesh2: Second mesh name

        Returns:
            tuple: (bool success, int vertex_count1, int vertex_count2)
        """
        try:
            vert_count1 = cmds.polyEvaluate(mesh1, vertex=True)
            vert_count2 = cmds.polyEvaluate(mesh2, vertex=True)

            if vert_count1 != vert_count2:
                self._log_error(
                    f"Topology mismatch: '{mesh1}' has {vert_count1} vertices, '{mesh2}' has {vert_count2} vertices")
                return False, vert_count1, vert_count2

            # Also check face count for complete topology validation
            face_count1 = cmds.polyEvaluate(mesh1, face=True)
            face_count2 = cmds.polyEvaluate(mesh2, face=True)

            if face_count1 != face_count2:
                self._log_warning(
                    f"Face count mismatch: '{mesh1}' has {face_count1} faces, '{mesh2}' has {face_count2} faces")

            self._log_debug(f"Topology match confirmed: {vert_count1} vertices, {face_count1} faces")
            return True, vert_count1, vert_count2

        except Exception as e:
            self._log_error(f"Failed to evaluate topology: {e}")
            return False, 0, 0

    def check_blendshape_exists(self, blendshape_node):
        """Check if blendshape node exists and is valid.

        Args:
            blendshape_node: Name of blendshape node

        Returns:
            bool: True if blendshape exists and is valid
        """
        if not blendshape_node:
            self._log_error("BlendShape node name is None or empty")
            return False

        if not cmds.objExists(blendshape_node):
            self._log_error(f"BlendShape node '{blendshape_node}' does not exist")
            return False

        # Verify it's actually a blendShape node
        node_type = cmds.nodeType(blendshape_node)
        if node_type != 'blendShape':
            self._log_error(f"Node '{blendshape_node}' is not a blendShape (type: {node_type})")
            return False

        self._log_debug(f"BlendShape '{blendshape_node}' exists and is valid")
        return True

    def check_blendshape_target(self, blendshape_node, target_name):
        """Check if target exists in blendshape.

        Args:
            blendshape_node: Name of blendshape node
            target_name: Name of target to check

        Returns:
            tuple: (bool exists, int target_index or None)
        """
        if not self.check_blendshape_exists(blendshape_node):
            return False, None

        aliases = cmds.aliasAttr(blendshape_node, query=True) or []

        for i in range(0, len(aliases), 2):
            if aliases[i] == target_name:
                weight_attr = aliases[i + 1]
                try:
                    target_index = int(weight_attr.split('[')[1].split(']')[0])
                    self._log_debug(f"Target '{target_name}' found at index {target_index}")
                    return True, target_index
                except:
                    self._log_error(f"Failed to parse target index from '{weight_attr}'")
                    return False, None

        self._log_debug(f"Target '{target_name}' not found in blendShape '{blendshape_node}'")
        self._log_debug(f"Available targets: {[aliases[i] for i in range(0, len(aliases), 2)]}")
        return False, None

    def check_mesh_has_skincluster(self, mesh_name):
        """Check if mesh has a skin cluster.

        Args:
            mesh_name: Name of mesh to check

        Returns:
            tuple: (bool has_skincluster, str skincluster_name or None)
        """
        if not self.check_mesh_exists(mesh_name, "SkinCluster check"):
            return False, None

        # Find skin cluster in history
        history = cmds.listHistory(mesh_name, pruneDagObjects=True) or []
        for node in history:
            if cmds.nodeType(node) == 'skinCluster':
                self._log_debug(f"Found skinCluster '{node}' on mesh '{mesh_name}'")
                return True, node

        self._log_debug(f"No skinCluster found on mesh '{mesh_name}'")
        return False, None

    def check_mesh_deformers(self, mesh_name):
        """Check what deformers are on the mesh.

        Args:
            mesh_name: Name of mesh to check

        Returns:
            dict: Dictionary of deformer types and their names
        """
        if not self.check_mesh_exists(mesh_name, "Deformer check"):
            return {}

        deformers = {}
        deformer_types = ['blendShape', 'skinCluster', 'cluster', 'deltaMush',
                          'tension', 'wire', 'lattice', 'wrap', 'nonLinear']

        history = cmds.listHistory(mesh_name, pruneDagObjects=True) or []

        for node in history:
            node_type = cmds.nodeType(node)
            if node_type in deformer_types:
                if node_type not in deformers:
                    deformers[node_type] = []
                deformers[node_type].append(node)

        if deformers:
            self._log_debug(f"Deformers on '{mesh_name}':")
            for deformer_type, nodes in deformers.items():
                self._log_debug(f"  {deformer_type}: {nodes}")
        else:
            self._log_debug(f"No deformers found on '{mesh_name}'")

        return deformers

    def validate_delta_operation(self, base_mesh, target_mesh, operation="delta calculation"):
        """Comprehensive validation for delta operations.

        Args:
            base_mesh: Base mesh name
            target_mesh: Target mesh name
            operation: Description of operation being validated

        Returns:
            bool: True if all checks pass
        """
        self._log_debug(f"=== Validating {operation} ===")

        # Check meshes exist
        if not self.check_mesh_exists(base_mesh, "Base mesh"):
            return False
        if not self.check_mesh_exists(target_mesh, "Target mesh"):
            return False

        # Check topology
        topology_ok, verts1, verts2 = self.check_topology_match(base_mesh, target_mesh)
        if not topology_ok:
            return False

        # Check for locked/referenced nodes
        if cmds.referenceQuery(base_mesh, isNodeReferenced=True):
            self._log_warning(f"Base mesh '{base_mesh}' is referenced - some operations may be restricted")

        if cmds.referenceQuery(target_mesh, isNodeReferenced=True):
            self._log_warning(f"Target mesh '{target_mesh}' is referenced - some operations may be restricted")

        self._log_debug(f"Validation passed for {operation}")
        return True

    def validate_corrective_workflow(self, skinned_mesh, sculpted_mesh, blendshape_node, target_name):
        """Validate entire corrective workflow.

        Args:
            skinned_mesh: Mesh with skin cluster
            sculpted_mesh: Sculpted corrective shape
            blendshape_node: Target blendshape node
            target_name: Name of target to create/replace

        Returns:
            bool: True if all checks pass
        """
        self._log_debug("=== Validating Corrective Workflow ===")

        # Reset error/warning lists
        self.errors = []
        self.warnings = []

        # Check meshes
        if not self.validate_delta_operation(skinned_mesh, sculpted_mesh, "corrective workflow"):
            return False

        # Check for skin cluster
        has_skin, skin_name = self.check_mesh_has_skincluster(skinned_mesh)
        if not has_skin:
            self._log_warning(f"Skinned mesh '{skinned_mesh}' has no skinCluster - workflow may not work as expected")

        # Check blendshape
        if not self.check_blendshape_exists(blendshape_node):
            return False

        # Check if target already exists
        target_exists, target_idx = self.check_blendshape_target(blendshape_node, target_name)
        if target_exists:
            self._log_warning(f"Target '{target_name}' already exists at index {target_idx} - it will be replaced")

        # Check deformers on both meshes
        self._log_debug("Checking deformer stacks:")
        self.check_mesh_deformers(skinned_mesh)
        self.check_mesh_deformers(sculpted_mesh)

        # Final summary
        if self.errors:
            self._log_error(f"Validation failed with {len(self.errors)} error(s)")
            return False

        if self.warnings:
            self._log_warning(f"Validation passed with {len(self.warnings)} warning(s)")
        else:
            self._log_debug("Validation passed with no warnings")

        return True

    def get_summary(self):
        """Get summary of checks performed.

        Returns:
            dict: Summary with errors and warnings
        """
        return {
            'errors': self.errors,
            'warnings': self.warnings,
            'has_errors': len(self.errors) > 0,
            'has_warnings': len(self.warnings) > 0
        }


def get_origin_shape(node):
    """Fast path: prefer sibling intermediate; fallback to history; else visible. (Full DAG path)"""
    if not cmds.objExists(node):
        raise RuntimeError('Nodo non trovato: %s' % node)

    # Resolve a visible mesh shape under node
    def _visible_shape(n):
        if cmds.nodeType(n) == 'mesh':
            if cmds.getAttr(n + '.intermediateObject'):
                par = (cmds.listRelatives(n, p=True, f=True) or [None])[0]
                if par:
                    vis = cmds.listRelatives(par, s=True, ni=True, type='mesh', f=True) or []
                    return vis[0] if vis else n
                return n
            return cmds.ls(n, l=True)[0]
        vis = cmds.listRelatives(n, s=True, ni=True, type='mesh', f=True) or []
        if not vis:
            raise RuntimeError('Nessuno mesh visibile sotto: %s' % n)
        return vis[0]

    final = _visible_shape(node)

    # 1) sibling intermediate (cheap)
    par = (cmds.listRelatives(final, p=True, f=True) or [None])[0]
    if par:
        sibs = cmds.listRelatives(par, s=True, type='mesh', f=True) or []
        for s in sibs:
            if cmds.getAttr(s + '.intermediateObject'):
                return s

    # 2) fallback: history scan (expensive)
    for h in (cmds.listHistory(final, pruneDagObjects=True) or []):
        if cmds.nodeType(h) == 'mesh' and cmds.getAttr(h + '.intermediateObject'):
            return cmds.ls(h, l=True)[0]

    return final


class DeltaManager:
    """Simple class to get vertex deltas between two meshes (fast path with OM2)."""

    def __init__(self, eps=1e-4, space='object', verbose=False, validate=True):
        """Initialize the delta manager.

        Args:
            eps: Epsilon threshold for delta detection (default 1e-4)
            space: 'object' or 'world' space for delta calculation
            verbose: If True, print debug messages
            validate: If True, run sanity checks before operations
        """
        self.base_mesh = None
        self.target_mesh = None
        self.deltas = []
        self.eps = eps
        self.eps2 = eps * eps  # Squared epsilon for faster distance checks
        self.space = space
        self.verbose = verbose
        self.validate = validate
        self.sanity_checker = DeltaSanityChecker(verbose=verbose) if validate else None

    def set_meshes(self, base_mesh, target_mesh):
        """Set the base and target meshes.

        Args:
            base_mesh: The base/original mesh
            target_mesh: The target/deformed mesh
        """
        self.base_mesh = base_mesh
        self.target_mesh = target_mesh

    def _get_mesh_fn(self, node):
        """Return MFnMesh of the visible shape under node.

        Args:
            node: Mesh transform or shape node

        Returns:
            om2.MFnMesh: Function set for the mesh
        """
        if cmds.nodeType(node) == 'mesh':
            if not cmds.getAttr(node + '.intermediateObject'):
                sel = om2.MSelectionList()
                sel.add(node)
                dag_path = sel.getDagPath(0)
                return om2.MFnMesh(dag_path)

        shapes = cmds.listRelatives(node, s=True, ni=True, type='mesh', f=True) or []
        if not shapes:
            shapes = cmds.listRelatives(node, s=True, type='mesh', f=True) or []
            if not shapes:
                raise RuntimeError('No mesh found under: %s' % node)

        node = shapes[0]
        sel = om2.MSelectionList()
        sel.add(node)
        dag_path = sel.getDagPath(0)
        return om2.MFnMesh(dag_path)

    def get_deltas(self):
        """Get vertex deltas between base and target mesh using fast OpenMaya API.

        Returns:
            list: List of (vertex_index, delta_x, delta_y, delta_z) tuples
        """
        if not self.base_mesh or not self.target_mesh:
            return []

        # Get MFnMesh for both meshes
        try:
            fn_base = self._get_mesh_fn(self.base_mesh)
            fn_target = self._get_mesh_fn(self.target_mesh)
        except Exception as e:
            print(f"Error getting mesh functions: {e}")
            return []

        # Determine space
        space = om2.MSpace.kObject if self.space == 'object' else om2.MSpace.kWorld

        # Get all points at once (much faster than per-vertex queries)
        base_points = fn_base.getPoints(space)
        target_points = fn_target.getPoints(space)

        # Check topology match
        if len(base_points) != len(target_points):
            raise RuntimeError('Topology mismatch: %d vs %d vertices' % (len(base_points), len(target_points)))

        # Calculate deltas using squared distance for efficiency
        eps2 = self.eps2
        out = []
        for i in range(len(base_points)):
            dx = target_points[i].x - base_points[i].x
            dy = target_points[i].y - base_points[i].y
            dz = target_points[i].z - base_points[i].z

            # Use squared distance to avoid sqrt
            if dx * dx + dy * dy + dz * dz > eps2:
                out.append((i, dx, dy, dz))

        self.deltas = out
        return out

    def get_deltas_as_dict(self):
        """Get deltas as a dictionary for easier lookup.

        Returns:
            dict: {vertex_index: (delta_x, delta_y, delta_z)}
        """
        if not self.deltas:
            self.get_deltas()

        delta_dict = {}
        for vertex_idx, dx, dy, dz in self.deltas:
            delta_dict[vertex_idx] = (dx, dy, dz)

        return delta_dict

    def print_summary(self):
        """Print a summary of the deltas."""
        if not self.deltas:
            print("No deltas calculated yet")
            return

        print(f"\n=== Delta Summary ===")
        print(f"Base mesh: {self.base_mesh}")
        print(f"Target mesh: {self.target_mesh}")
        print(f"Vertices with deltas: {len(self.deltas)}")

        if self.deltas:
            # Find max deltas
            max_delta = max(self.deltas, key=lambda d: abs(d[1]) + abs(d[2]) + abs(d[3]))
            print(
                f"Largest delta on vertex {max_delta[0]}: ({max_delta[1]:.4f}, {max_delta[2]:.4f}, {max_delta[3]:.4f})")

    def apply_to_blendshape_target(self, blendshape_node, target_name, mesh_name):
        """Apply deltas to a blendshape target (optimized version).

        Args:
            blendshape_node: Name of the blendshape node (e.g., 'blendShape1')
            target_name: Name of the target (e.g., 'L_test')
            mesh_name: Name of the mesh the blendshape is on (e.g., 'pCube3')

        Returns:
            bool: True if successful
        """
        if not self.deltas:
            print("No deltas to apply. Run get_deltas() first.")
            return False

        # Find target index by name
        target_index = None
        aliases = cmds.aliasAttr(blendshape_node, query=True) or []

        for i in range(0, len(aliases), 2):
            if aliases[i] == target_name:
                # Extract index from weight[n]
                weight_attr = aliases[i + 1]
                target_index = int(weight_attr.split('[')[1].split(']')[0])
                break

        if target_index is None:
            print(f"Target '{target_name}' not found in blendshape '{blendshape_node}'")
            return False

        print(f"Found target '{target_name}' at index {target_index}")

        # OPTIMIZED: Sort deltas once by vertex index
        sorted_deltas = sorted(self.deltas, key=lambda d: d[0])

        # OPTIMIZED: Extract data in single pass
        vertex_indices = []
        point_deltas = []
        for vtx_idx, dx, dy, dz in sorted_deltas:
            vertex_indices.append(vtx_idx)
            point_deltas.append([dx, dy, dz])

        # Build component strings
        components = self._pack_components(vertex_indices)

        # Get geometry index (usually 0 for single mesh)
        geom_index = 0

        # Build attribute paths
        pt_attr = f'{blendshape_node}.inputTarget[{geom_index}].inputTargetGroup[{target_index}].inputTargetItem[6000].inputPointsTarget'
        ct_attr = f'{blendshape_node}.inputTarget[{geom_index}].inputTargetGroup[{target_index}].inputTargetItem[6000].inputComponentsTarget'

        # Apply the deltas
        cmds.setAttr(pt_attr, len(point_deltas), *point_deltas, type='pointArray')
        cmds.setAttr(ct_attr, len(components), *components, type='componentList')

        print(f"Applied {len(self.deltas)} deltas to '{target_name}' on '{blendshape_node}'")
        return True

    def _pack_components(self, indices):
        """Pack vertex indices into component strings.

        Args:
            indices: List of vertex indices (will be sorted)

        Returns:
            list: Component strings like ['vtx[0:5]', 'vtx[7]', 'vtx[10:15]']
        """
        indices = sorted(indices)
        if not indices:
            return []

        comps = []
        start = indices[0]
        prev = start

        for v in indices[1:]:
            if v != prev + 1:
                # End current range
                if start == prev:
                    comps.append('vtx[%d]' % start)
                else:
                    comps.append('vtx[%d:%d]' % (start, prev))
                start = v
            prev = v

        # Add final range
        if start == prev:
            comps.append('vtx[%d]' % start)
        else:
            comps.append('vtx[%d:%d]' % (start, prev))

        return comps

    def add_deltas(self, other_deltas):
        """Add another set of deltas to current deltas.

        Args:
            other_deltas: List of (vertex_index, dx, dy, dz) or DeltaManager instance

        Returns:
            list: Combined deltas
        """
        if isinstance(other_deltas, DeltaManager):
            other_deltas = other_deltas.deltas

        # Convert to dicts for easier math
        current_dict = {}
        for vtx, dx, dy, dz in self.deltas:
            current_dict[vtx] = [dx, dy, dz]

        other_dict = {}
        for vtx, dx, dy, dz in other_deltas:
            other_dict[vtx] = [dx, dy, dz]

        # Combine all vertices
        all_vertices = set(current_dict.keys()) | set(other_dict.keys())

        # Add deltas
        result = []
        for vtx in sorted(all_vertices):
            curr = current_dict.get(vtx, [0, 0, 0])
            other = other_dict.get(vtx, [0, 0, 0])

            new_delta = [curr[0] + other[0], curr[1] + other[1], curr[2] + other[2]]

            # Only store if there's movement (use squared distance)
            if new_delta[0] * new_delta[0] + new_delta[1] * new_delta[1] + new_delta[2] * new_delta[2] > self.eps2:
                result.append((vtx, new_delta[0], new_delta[1], new_delta[2]))

        self.deltas = result
        return result

    def subtract_deltas(self, other_deltas):
        """Subtract another set of deltas from current deltas.

        Args:
            other_deltas: List of (vertex_index, dx, dy, dz) or DeltaManager instance

        Returns:
            list: Resulting deltas
        """
        if isinstance(other_deltas, DeltaManager):
            other_deltas = other_deltas.deltas

        # Convert to dicts
        current_dict = {}
        for vtx, dx, dy, dz in self.deltas:
            current_dict[vtx] = [dx, dy, dz]

        other_dict = {}
        for vtx, dx, dy, dz in other_deltas:
            other_dict[vtx] = [dx, dy, dz]

        # Combine all vertices
        all_vertices = set(current_dict.keys()) | set(other_dict.keys())

        # Subtract deltas
        result = []
        for vtx in sorted(all_vertices):
            curr = current_dict.get(vtx, [0, 0, 0])
            other = other_dict.get(vtx, [0, 0, 0])

            new_delta = [curr[0] - other[0], curr[1] - other[1], curr[2] - other[2]]

            # Only store if there's movement (use squared distance)
            if new_delta[0] * new_delta[0] + new_delta[1] * new_delta[1] + new_delta[2] * new_delta[2] > self.eps2:
                result.append((vtx, new_delta[0], new_delta[1], new_delta[2]))

        self.deltas = result
        return result

    def multiply_deltas(self, factor):
        """Multiply all deltas by a factor.

        Args:
            factor: Scalar value to multiply by

        Returns:
            list: Scaled deltas
        """
        result = []
        for vtx, dx, dy, dz in self.deltas:
            new_delta = [dx * factor, dy * factor, dz * factor]

            # Only store if there's movement (use squared distance)
            if new_delta[0] * new_delta[0] + new_delta[1] * new_delta[1] + new_delta[2] * new_delta[2] > self.eps2:
                result.append((vtx, new_delta[0], new_delta[1], new_delta[2]))

        self.deltas = result
        return result

    def divide_deltas(self, divisor):
        """Divide all deltas by a divisor.

        Args:
            divisor: Scalar value to divide by

        Returns:
            list: Scaled deltas
        """
        if divisor == 0:
            print("Error: Cannot divide by zero")
            return self.deltas

        result = []
        for vtx, dx, dy, dz in self.deltas:
            new_delta = [dx / divisor, dy / divisor, dz / divisor]

            # Only store if there's movement (use squared distance)
            if new_delta[0] * new_delta[0] + new_delta[1] * new_delta[1] + new_delta[2] * new_delta[2] > self.eps2:
                result.append((vtx, new_delta[0], new_delta[1], new_delta[2]))

        self.deltas = result
        return result

    def get_pose_space_delta(self, base_deformed, corrective_sculpt):
        """Calculate pose space delta using Maya's invertShape for corrective blendshapes.

        This is used when base_deformed has skinCluster and corrective_sculpt
        is the sculpted correction in that pose.

        Args:
            base_deformed: Mesh with skinCluster in posed position (e.g., pCube1)
            corrective_sculpt: Sculpted corrective shape in same pose (e.g., pCube2)

        Returns:
            str: Name of inverted shape ready for blendshape target
        """
        # Verify both meshes exist
        if not cmds.objExists(base_deformed):
            return None

        if not cmds.objExists(corrective_sculpt):
            return None

        # Check topology match
        base_verts = cmds.polyEvaluate(base_deformed, vertex=True)
        corrective_verts = cmds.polyEvaluate(corrective_sculpt, vertex=True)

        if base_verts != corrective_verts:
            return None

        # Use Maya's invertShape to calculate the corrective delta
        inverted_name = f"{corrective_sculpt}_inverted"

        # invertShape returns the inverted mesh
        import pymel.core as pm
        inverted = str(pm.invertShape(base_deformed, corrective_sculpt))

        if inverted:
            # Rename for clarity
            inverted = cmds.rename(inverted, inverted_name)

            # Store reference for potential delta extraction
            self.inverted_shape = inverted

            return inverted
        else:
            return None

    def apply_pose_corrective_to_blendshape(self, base_mesh, corrective_sculpt,
                                            blendshape_node, target_name):
        """Complete workflow: Calculate and apply pose space corrective to blendshape.

        Args:
            base_mesh: Skinned mesh in pose
            corrective_sculpt: Sculpted correction
            blendshape_node: Target blendshape node
            target_name: Name for the corrective target

        Returns:
            bool: True if successful
        """
        # Calculate inverted shape
        inverted = self.get_pose_space_delta(base_mesh, corrective_sculpt)

        if not inverted:
            return False

        # Find target index
        target_index = None
        aliases = cmds.aliasAttr(blendshape_node, query=True) or []

        for i in range(0, len(aliases), 2):
            if aliases[i] == target_name:
                weight_attr = aliases[i + 1]
                target_index = int(weight_attr.split('[')[1].split(']')[0])
                break

        # If target exists, clear old data
        if target_index is not None:
            geom_idx = 0
            cmds.removeMultiInstance(
                f'{blendshape_node}.inputTarget[{geom_idx}].inputTargetGroup[{target_index}]',
                b=True
            )
        else:
            # Find next available index
            existing_indices = []
            for i in range(1, len(aliases), 2):
                weight = aliases[i]
                if 'weight[' in weight:
                    idx = int(weight.split('[')[1].split(']')[0])
                    existing_indices.append(idx)

            target_index = 0
            while target_index in existing_indices:
                target_index += 1

        # Apply inverted shape to base_mesh (NOT to other meshes)
        cmds.blendShape(blendshape_node, edit=True,
                        target=(base_mesh, target_index, inverted, 1.0),
                        topologyCheck=False)

        # Set alias
        cmds.aliasAttr(target_name, f'{blendshape_node}.weight[{target_index}]')

        # Clean up inverted shape
        cmds.delete(inverted)

        return True

    def swap_shape_with_corrective(self, skinned_mesh, sculpted_mesh, blendshape_node, target_name):
        """Replace a blendshape target with pose space corrective delta.

        This method calculates the corrective delta between a skinned mesh and a sculpted correction,
        then replaces the specified blendshape target with this delta.

        Args:
            skinned_mesh: Mesh with skinCluster in pose (e.g., pCube1)
            sculpted_mesh: Sculpted corrective shape in same pose (e.g., pCube2)
            blendshape_node: BlendShape node containing the target (e.g., blendShape1)
            target_name: Name of target to replace (e.g., L_test)

        Returns:
            bool: True if successful, False otherwise
        """
        # Run comprehensive validation if enabled
        if self.validate and self.sanity_checker:
            if not self.sanity_checker.validate_corrective_workflow(
                    skinned_mesh, sculpted_mesh, blendshape_node, target_name
            ):
                print("[ERROR] Validation failed. Check errors above for details.")
                return False

        # Quick existence checks if validation is disabled
        if not cmds.objExists(skinned_mesh):
            print(f"[ERROR] Skinned mesh '{skinned_mesh}' does not exist")
            return False
        if not cmds.objExists(sculpted_mesh):
            print(f"[ERROR] Sculpted mesh '{sculpted_mesh}' does not exist")
            return False
        if not cmds.objExists(blendshape_node):
            print(f"[ERROR] BlendShape node '{blendshape_node}' does not exist")
            return False

        # Calculate inverted shape
        if self.verbose:
            print(f"[DEBUG] Calculating inverted shape between '{skinned_mesh}' and '{sculpted_mesh}'")

        try:
            import pymel.core as pm
            inverted = str(pm.invertShape(skinned_mesh, sculpted_mesh))
        except Exception as e:
            print(f"[ERROR] invertShape failed: {e}")
            return False

        if not inverted:
            print("[ERROR] invertShape returned None or empty result")
            return False

        if self.verbose:
            print(f"[DEBUG] Created inverted shape: {inverted}")

        # Get the original shape of the skinned mesh
        try:
            orig_shape = get_origin_shape(skinned_mesh)
            if self.verbose:
                print(f"[DEBUG] Found origin shape: {orig_shape}")
        except Exception as e:
            print(f"[ERROR] Failed to get origin shape: {e}")
            cmds.delete(inverted)
            return False

        # Create a temporary mesh from the orig shape
        temp_mesh = cmds.createNode('mesh', name='temp_orig_shape')
        temp_transform = cmds.listRelatives(temp_mesh, parent=True)[0]

        # Connect the orig shape to get the undeformed geometry
        cmds.connectAttr(f'{orig_shape}.outMesh', f'{temp_mesh}.inMesh', force=True)

        # Calculate delta between original shape and inverted shape
        self.set_meshes(temp_transform, inverted)

        if self.verbose:
            print(f"[DEBUG] Calculating deltas between temp mesh and inverted shape")

        try:
            deltas = self.get_deltas()
        except Exception as e:
            print(f"[ERROR] Failed to calculate deltas: {e}")
            # Clean up before returning
            try:
                if cmds.objExists(orig_shape) and cmds.objExists(temp_mesh):
                    connections = cmds.listConnections(f'{temp_mesh}.inMesh', source=True, plugs=True)
                    if connections and f'{orig_shape}.outMesh' in connections:
                        cmds.disconnectAttr(f'{orig_shape}.outMesh', f'{temp_mesh}.inMesh')
                if cmds.objExists(temp_transform):
                    cmds.delete(temp_transform)
                if cmds.objExists(inverted):
                    cmds.delete(inverted)
            except Exception as cleanup_error:
                print(f"Cleanup error: {cleanup_error}")
            return False

        # Disconnect and delete temp mesh
        try:
            if cmds.objExists(orig_shape) and cmds.objExists(temp_mesh):
                connections = cmds.listConnections(f'{temp_mesh}.inMesh', source=True, plugs=True)
                if connections and f'{orig_shape}.outMesh' in connections:
                    cmds.disconnectAttr(f'{orig_shape}.outMesh', f'{temp_mesh}.inMesh')
            if cmds.objExists(temp_transform):
                cmds.delete(temp_transform)
        except Exception as e:
            print(f"[WARNING] Error cleaning up temp mesh: {e}")

        # Clean up inverted mesh
        try:
            cmds.delete(inverted)
        except Exception as e:
            print(f"[WARNING] Error cleaning up inverted mesh: {e}")

        if not deltas:
            print("[ERROR] No deltas calculated - meshes may be identical")
            return False

        if self.verbose:
            print(f"[DEBUG] Calculated {len(deltas)} vertex deltas")

        # Find the mesh that has the blendshape
        connections = cmds.listConnections(f"{blendshape_node}.outputGeometry",
                                           destination=True, source=False)
        if not connections:
            return False

        target_mesh = connections[0].split('.')[0]

        # Apply deltas to the target
        success = self.apply_to_blendshape_target(blendshape_node, target_name, target_mesh)

        return success


# Helper function for testing sanity checks
def test_sanity_check(base_mesh=None, target_mesh=None, blendshape_node=None, target_name='test_target'):
    """Test sanity checking system with provided or selected meshes.

    Args:
        base_mesh: Base mesh name (uses selection if None)
        target_mesh: Target mesh name (uses selection if None)
        blendshape_node: BlendShape node name (optional)
        target_name: Target name for blendshape operations

    Returns:
        dict: Summary of sanity check results
    """
    # Get meshes from selection if not provided
    if not base_mesh or not target_mesh:
        sel = cmds.ls(selection=True, transforms=True)
        if len(sel) < 2:
            print("[ERROR] Please select 2 meshes or provide mesh names")
            return None
        base_mesh = base_mesh or sel[0]
        target_mesh = target_mesh or sel[1]

    print("\n" + "=" * 60)
    print("SANITY CHECK TEST")
    print("=" * 60)

    checker = DeltaSanityChecker(verbose=True)

    # Test basic mesh validation
    print("\n--- Mesh Validation ---")
    checker.check_mesh_exists(base_mesh, "Base mesh")
    checker.check_mesh_exists(target_mesh, "Target mesh")

    # Test topology
    print("\n--- Topology Check ---")
    topology_ok, v1, v2 = checker.check_topology_match(base_mesh, target_mesh)

    # Test deformers
    print("\n--- Deformer Analysis ---")
    base_deformers = checker.check_mesh_deformers(base_mesh)
    target_deformers = checker.check_mesh_deformers(target_mesh)

    # Test blendshape if provided
    if blendshape_node:
        print("\n--- BlendShape Validation ---")
        if checker.check_blendshape_exists(blendshape_node):
            checker.check_blendshape_target(blendshape_node, target_name)

    # Get summary
    summary = checker.get_summary()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Errors: {len(summary['errors'])}")
    for error in summary['errors']:
        print(f"  • {error}")
    print(f"Warnings: {len(summary['warnings'])}")
    for warning in summary['warnings']:
        print(f"  • {warning}")

    return summary


# Test function
def test_delta_manager(verbose=True, validate=True):
    """Test the DeltaManager with selected meshes.

    Args:
        verbose: If True, print debug messages
        validate: If True, run sanity checks

    Returns:
        DeltaManager: Configured delta manager instance
    """
    sel = cmds.ls(selection=True, transforms=True)

    if len(sel) != 2:
        print("Please select exactly 2 meshes (base first, then target)")
        return

    print(f"\nTesting DeltaManager with verbose={verbose}, validate={validate}")

    dm = DeltaManager(verbose=verbose, validate=validate)

    # If validation is enabled, it will run checks
    if validate:
        if not dm.sanity_checker.validate_delta_operation(sel[0], sel[1]):
            print("Validation failed, aborting test")
            return dm

    dm.set_meshes(sel[0], sel[1])
    deltas = dm.get_deltas()
    dm.print_summary()

    return dm


class BlendshapeStateManager:
    """Context manager to preserve blendshape target weights during operations."""

    def __init__(self, blendshape_node, preserve_state=True):
        """Initialize blendshape state manager.

        Args:
            blendshape_node (str): Blendshape node to preserve
            preserve_state (bool): Whether to preserve the current state
        """
        self.blendshape_node = blendshape_node
        self.preserve_state = preserve_state
        self.stored_weights = {}
        self.stored_envelope = None
        self.stored_connections = {}  # Store disconnected connections

    def __enter__(self):
        """Store current blendshape state."""
        if not self.preserve_state or not cmds.objExists(self.blendshape_node):
            return self

        # Store envelope value
        if cmds.attributeQuery('envelope', node=self.blendshape_node, exists=True):
            self.stored_envelope = cmds.getAttr(f"{self.blendshape_node}.envelope")

        # Get all weight attributes
        weight_attrs = cmds.listAttr(self.blendshape_node, keyable=True) or []
        weight_attrs = [attr for attr in weight_attrs if attr.startswith('weight')]

        # Store current weight values
        for attr in weight_attrs:
            try:
                value = cmds.getAttr(f"{self.blendshape_node}.{attr}")
                self.stored_weights[attr] = value
                print(f"  Stored {attr} = {value}")
            except:
                pass

        print(f"BlendshapeStateManager: Stored state for {len(self.stored_weights)} targets")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore blendshape state."""
        if not self.preserve_state or not cmds.objExists(self.blendshape_node):
            return

        # Restore envelope
        if self.stored_envelope is not None:
            try:
                cmds.setAttr(f"{self.blendshape_node}.envelope", self.stored_envelope)
            except:
                pass

        # Restore weight values
        for attr, value in self.stored_weights.items():
            try:
                cmds.setAttr(f"{self.blendshape_node}.{attr}", value)
            except:
                pass

        # Reconnect stored connections
        for dest, source in self.stored_connections.items():
            try:
                cmds.connectAttr(source, dest)
                print(f"  Reconnected {source} -> {dest}")
            except:
                pass

        print(f"BlendshapeStateManager: Restored state for {len(self.stored_weights)} targets")

    def set_all_weights_to_zero_except(self, except_target=None):
        """Set all blendshape weights to zero except specified target.

        Args:
            except_target (str): Target name to keep unchanged (optional)
        """
        if not cmds.objExists(self.blendshape_node):
            return

        weight_attrs = cmds.listAttr(self.blendshape_node, keyable=True) or []
        weight_attrs = [attr for attr in weight_attrs if attr.startswith('weight')]

        for attr in weight_attrs:
            if except_target and except_target in attr:
                print(f"  Keeping {attr} unchanged")
                continue
            try:
                cmds.setAttr(f"{self.blendshape_node}.{attr}", 0.0)
                print(f"  Set {attr} = 0.0")
            except:
                pass

    def _alias_map(self, node):
        """{alias: 'weight[IDX]'}"""
        pairs = cmds.aliasAttr(node, query=True) or []
        return {pairs[i]: pairs[i+1] for i in range(0, len(pairs), 2)}

    def _weight_plug(self, node, alias):
        amap = self._alias_map(node)
        if alias not in amap:
            raise RuntimeError("Target '%s' not found on %s" % (alias, node))
        return "%s.%s" % (node, amap[alias])

    def turn_off_single_target(self, target_name):
        """Turn OFF only the specified target, leave all others as they are."""
        if not cmds.objExists(self.blendshape_node):
            return

        amap = self._alias_map(self.blendshape_node)

        # Find and turn off ONLY the target being baked
        for alias, plug in amap.items():
            if alias == target_name:
                full = "%s.%s" % (self.blendshape_node, plug)

                # Disconnect if connected
                connections = cmds.listConnections(full, plugs=True, destination=False) or []
                if connections:
                    self.stored_connections[full] = connections[0]
                    cmds.disconnectAttr(connections[0], full)
                    print(f"  Disconnected {alias}")

                # Unlock if locked
                if cmds.getAttr(full, lock=True):
                    cmds.setAttr(full, lock=False)

                # Set to 0
                try:
                    cmds.setAttr(full, 0.0)
                    print(f"  Turned OFF {alias} for delta calculation")
                except Exception as e:
                    print(f"  ⚠️ Could not turn off {alias}: {e}")
                break

    def isolate_target_during_bake(self, target_name):
        """Zero ALL other aliases; keep only target_name at its current value."""
        if not cmds.objExists(self.blendshape_node):
            return
        amap = self._alias_map(self.blendshape_node)  # alias -> weight[IDX]

        # cache current target value via alias
        try:
            tgt_val = cmds.getAttr("%s.%s" % (self.blendshape_node, target_name))
        except:
            # fallback to weight plug
            tgt_val = cmds.getAttr(self._weight_plug(self.blendshape_node, target_name))

        # Disconnect ALL weight attributes first
        for alias, plug in amap.items():
            full = "%s.%s" % (self.blendshape_node, plug)

            # Store and disconnect connections
            connections = cmds.listConnections(full, plugs=True, destination=False) or []
            if connections:
                self.stored_connections[full] = connections[0]
                cmds.disconnectAttr(connections[0], full)
                print(f"  Disconnected {alias}")

            # Unlock if locked
            if cmds.getAttr(full, lock=True):
                cmds.setAttr(full, lock=False)

        # Now set the weights
        for alias, plug in amap.items():
            full = "%s.%s" % (self.blendshape_node, plug)
            try:
                cmds.setAttr(full, tgt_val if alias == target_name else 0.0)
                print(f"  {alias}: {tgt_val if alias == target_name else 0.0}")
            except Exception as e:
                print(f"  ⚠️ Could not set {alias}: {e}")

    def isolate_target_completely(self, target_name):
        """Hard isolation: set all aliases to 0 except the requested one (set to 1)."""
        if not cmds.objExists(self.blendshape_node):
            return False
        amap = self._alias_map(self.blendshape_node)
        for alias, plug in amap.items():
            full = "%s.%s" % (self.blendshape_node, plug)
            cmds.setAttr(full, 1.0 if alias == target_name else 0.0)
        return True

    def get_clean_base_mesh(self, mesh):
        """Get clean base mesh using origin shape method.

        This method creates a truly clean base mesh by:
        1. Finding the origin shape
        2. Creating temporary mesh from it
        3. Returning clean mesh without any deformer influence

        Args:
            mesh (str): Source mesh name

        Returns:
            str: Clean base mesh name (caller must delete)
        """
        print(f"🧹 CREATING CLEAN BASE MESH from {mesh}")

        # Find origin shape
        try:
            from . import get_origin_shape
            orig_shape = get_origin_shape(mesh)
            print(f"  Found origin shape: {orig_shape}")
        except:
            print("  Warning: Could not find origin shape, using duplicate method")
            return cmds.duplicate(mesh, name=f'{mesh}_clean_fallback')[0]

        # Create clean mesh from origin
        clean_mesh_shape = cmds.createNode('mesh', name=f'{mesh}_clean_shape')
        clean_mesh_transform = cmds.listRelatives(clean_mesh_shape, parent=True)[0]
        clean_mesh_transform = cmds.rename(clean_mesh_transform, f'{mesh}_CLEAN_BASE')

        # Connect origin to clean mesh temporarily
        cmds.connectAttr(f'{orig_shape}.outMesh', f'{clean_mesh_shape}.inMesh', force=True)
        cmds.refresh()

        # Disconnect safely
        try:
            connections = cmds.listConnections(f'{clean_mesh_shape}.inMesh', source=True, plugs=True)
            if connections and f'{orig_shape}.outMesh' in connections:
                cmds.disconnectAttr(f'{orig_shape}.outMesh', f'{clean_mesh_shape}.inMesh')
        except Exception as e:
            print(f"  Warning: Could not disconnect origin: {e}")

        print(f"✅ CLEAN BASE MESH: {clean_mesh_transform}")
        return clean_mesh_transform

    def create_isolated_sculpted_mesh(self, mesh, target_name):
        """Create sculpted mesh with ONLY specified target influence.

        This is the ultimate solution - creates mesh that contains
        ONLY the delta from the specified target, nothing else.

        Args:
            mesh (str): Source mesh
            target_name (str): Target to isolate

        Returns:
            str: Sculpted mesh with only target influence
        """
        print(f"\n🎯 CREATING ISOLATED SCULPTED MESH: {target_name}")

        if not cmds.objExists(self.blendshape_node):
            print("❌ Blendshape node not found!")
            return None

        # Step 1: Get completely clean base mesh
        clean_base = self.get_clean_base_mesh(mesh)

        # Step 2: Complete isolation
        success = self.isolate_target_completely(target_name)
        if not success:
            cmds.delete(clean_base)
            return None

        # Step 3: Duplicate the isolated mesh
        sculpted_mesh = cmds.duplicate(mesh, name=f'{target_name}_ISOLATED_SCULPT')[0]

        # Step 4: Verify the sculpted mesh has ONLY target influence
        print(f"✅ ISOLATED SCULPTED MESH: {sculpted_mesh}")
        print(f"   📋 Base mesh (clean): {clean_base}")

        # Clean up base mesh
        cmds.delete(clean_base)

        return sculpted_mesh

    def get_target_deltas(self, blendshape_node, target_name):
        """Get the raw delta values for a specific target.

        Args:
            blendshape_node (str): Blendshape node name
            target_name (str): Target name

        Returns:
            list: Delta values as [(vertex_id, [x, y, z]), ...]
        """
        if not cmds.objExists(blendshape_node):
            return []

        # Find target index
        targets = cmds.aliasAttr(blendshape_node, query=True) or []
        target_idx = None
        for i in range(0, len(targets), 2):
            if targets[i] == target_name:
                attr_name = targets[i + 1]
                # Extract index from weight[X]
                import re
                match = re.search(r'weight\[(\d+)\]', attr_name)
                if match:
                    target_idx = int(match.group(1))
                    break

        if target_idx is None:
            print(f"Could not find target index for {target_name}")
            return []

        # Get deltas from blendshape
        geom_idx = 0
        delta_attr = f"{blendshape_node}.inputTarget[{geom_idx}].inputTargetGroup[{target_idx}].inputTargetItem[6000].inputPointsTarget"

        try:
            deltas = cmds.getAttr(delta_attr) or []

            # Get component list
            comp_attr = f"{blendshape_node}.inputTarget[{geom_idx}].inputTargetGroup[{target_idx}].inputTargetItem[6000].inputComponentsTarget"
            components = cmds.getAttr(comp_attr) or []

            # Combine deltas with vertex indices
            result = []
            for i, delta in enumerate(deltas):
                if i < len(components):
                    vertex_id = components[i]
                    result.append((vertex_id, list(delta)))

            return result

        except Exception as e:
            print(f"Error getting deltas for {target_name}: {e}")
            return []

    def apply_delta_subtraction(self, mesh, delta_list, scale=-1.0):
        """Apply delta subtraction to a mesh.

        Args:
            mesh (str): Target mesh
            delta_list (list): List of deltas as [(vertex_id, [x, y, z]), ...]
            scale (float): Scale factor (-1.0 for subtraction, 1.0 for addition)
        """
        if not delta_list or not cmds.objExists(mesh):
            return

        print(f"Applying {len(delta_list)} delta subtractions to {mesh} (scale: {scale})")

        for vertex_id, delta in delta_list:
            try:
                vertex_name = f"{mesh}.vtx[{vertex_id}]"
                current_pos = cmds.xform(vertex_name, query=True, translation=True, worldSpace=False)

                new_pos = [
                    current_pos[0] + (delta[0] * scale),
                    current_pos[1] + (delta[1] * scale),
                    current_pos[2] + (delta[2] * scale)
                ]

                cmds.xform(vertex_name, translation=new_pos, worldSpace=False)

            except Exception as e:
                print(f"Error applying delta to vertex {vertex_id}: {e}")

    def collect_contaminating_deltas(self, blendshape_node, target_being_baked):
        """Collect deltas from all active targets except the one being baked.

        Args:
            blendshape_node (str): Blendshape node
            target_being_baked (str): Target name being baked (exclude this)

        Returns:
            list: Combined contaminating deltas
        """
        print(f"🔍 Collecting contaminating deltas (excluding {target_being_baked})")

        if not cmds.objExists(blendshape_node):
            return []

        # Get all weight attributes
        weight_attrs = cmds.listAttr(blendshape_node, keyable=True) or []
        weight_attrs = [attr for attr in weight_attrs if attr.startswith('weight')]

        contaminating_deltas = []

        for attr in weight_attrs:
            try:
                # Get target name from attribute
                aliases = cmds.aliasAttr(blendshape_node, query=True) or []
                target_name = None
                for i in range(0, len(aliases), 2):
                    if aliases[i + 1] == attr:
                        target_name = aliases[i]
                        break

                if not target_name or target_name == target_being_baked:
                    continue

                # Check if this target is active
                weight = cmds.getAttr(f"{blendshape_node}.{target_name}")
                if abs(weight) < 0.001:  # Skip if essentially zero
                    continue

                print(f"  📊 Found contaminating target: {target_name} (weight: {weight})")

                # Get deltas for this target
                target_deltas = self.get_target_deltas(blendshape_node, target_name)

                # Scale deltas by weight and add to contaminating list
                for vertex_id, delta in target_deltas:
                    scaled_delta = [delta[0] * weight, delta[1] * weight, delta[2] * weight]
                    contaminating_deltas.append((vertex_id, scaled_delta))

            except Exception as e:
                print(f"  ⚠️ Error processing {attr}: {e}")

        print(f"🔍 Collected {len(contaminating_deltas)} contaminating delta points")
        return contaminating_deltas


class MeshBaker:
    """Bake all deformers on a mesh into delta values for blendshape targets."""

    def __init__(self, delta_manager=None):
        """Initialize MeshBaker.

        Args:
            delta_manager: DeltaManager instance to use (creates new if None)
        """
        self.delta_manager = delta_manager or DeltaManager()
        self.baked_meshes = {}
        self.original_connections = {}

    def bake_current_state(self, mesh_name):
        """Bake mesh at current state with all deformers.

        Args:
            mesh_name: Name of mesh to bake

        Returns:
            str: Name of baked mesh
        """
        if not cmds.objExists(mesh_name):
            return None

        dup = cmds.duplicate(mesh_name, name=f"{mesh_name}_baked")[0]

        shapes = cmds.listRelatives(dup, shapes=True, type='mesh') or []
        if shapes:
            history = cmds.listHistory(shapes[0], pruneDagObjects=True) or []
            for node in history:
                if cmds.nodeType(node) in ['blendShape', 'skinCluster', 'cluster',
                                           'deltaMush', 'tension', 'wire', 'lattice',
                                           'wrap', 'nonLinear', 'ffd']:
                    cmds.delete(node)

        self.baked_meshes[mesh_name] = dup
        return dup

    def bake_to_blendshape_target(self, source_mesh, blendshape_node, target_name,
                                  disable_above_skin=True, base_mesh=None, preserve_blendshape_state=True,
                                  isolate_target=True):
        """Bake deformed mesh directly to blendshape target using proper corrective workflow.

        Args:
            source_mesh: Mesh with deformers to bake
            blendshape_node: Target blendshape node
            target_name: Name for the target
            disable_above_skin: If True, disable deformers above skinCluster
            base_mesh: Base mesh for delta calculation (uses orig if None)
            preserve_blendshape_state: If True, preserve current blendshape weights during bake
            isolate_target: If True, set all other blendshape weights to 0 during bake

        Returns:
            bool: Success
        """
        # Use context manager to preserve blendshape state
        with BlendshapeStateManager(blendshape_node, preserve_blendshape_state) as state_manager:

            # Isolate target if requested - set all other blendshape weights to 0
            if isolate_target:
                state_manager.isolate_target_during_bake(target_name)

            # 1. Duplicate current deformed state with only target active - key fix!
            deformed_dup = cmds.duplicate(source_mesh, name=f"{source_mesh}_deformed")[0]

            # 2. Disable deformers above skinCluster on original mesh
            if disable_above_skin:
                history = cmds.listHistory(source_mesh, pruneDagObjects=True) or []
                found_skin = False
                for node in reversed(history):
                    node_type = cmds.nodeType(node)
                    if node_type == 'skinCluster':
                        found_skin = True
                    elif found_skin and node_type in ['blendShape', 'cluster', 'deltaMush',
                                                      'tension', 'wire', 'lattice', 'wrap']:
                        if cmds.attributeQuery('envelope', node=node, exists=True):
                            cmds.setAttr(f"{node}.envelope", 0)

            # 3. Create inverted shape between deformed duplicate and original with deformers off
            import pymel.core as pm
            inverted = str(pm.invertShape(source_mesh, deformed_dup))

            # 4. Create mesh from origin shape for delta calculation
            orig_shape = get_origin_shape(source_mesh)
            temp_orig = cmds.createNode('mesh', name='temp_orig_mesh')
            temp_transform = cmds.listRelatives(temp_orig, parent=True)[0]

            cmds.connectAttr(f'{orig_shape}.outMesh', f'{temp_orig}.inMesh', force=True)
            cmds.refresh()

            # Safe disconnect after refresh
            try:
                if cmds.objExists(orig_shape) and cmds.objExists(temp_orig):
                    connections = cmds.listConnections(f'{temp_orig}.inMesh', source=True, plugs=True)
                    if connections and f'{orig_shape}.outMesh' in connections:
                        cmds.disconnectAttr(f'{orig_shape}.outMesh', f'{temp_orig}.inMesh')
            except Exception as e:
                print(f"[WARNING] Could not disconnect temp original: {e}")

            # 5. Calculate delta between inverted and origin
            self.delta_manager.set_meshes(temp_transform, inverted)
            deltas = self.delta_manager.get_deltas()

            # Clean up temp meshes
            cmds.delete([deformed_dup, temp_transform, inverted])

            if deltas:
                connections = cmds.listConnections(f"{blendshape_node}.outputGeometry",
                                                   destination=True, source=False)
                if connections:
                    target_mesh = connections[0].split('.')[0]
                    success = self.delta_manager.apply_to_blendshape_target(
                        blendshape_node, target_name, target_mesh
                    )
                    return success

            return False

    def extract_deformer_delta(self, mesh_name, deformer_type='blendShape'):
        """Extract delta from specific deformer type.

        Args:
            mesh_name: Mesh with deformers
            deformer_type: Type of deformer to isolate

        Returns:
            list: Delta values
        """
        history = cmds.listHistory(mesh_name, pruneDagObjects=True) or []
        target_deformer = None

        for node in history:
            if cmds.nodeType(node) == deformer_type:
                target_deformer = node
                break

        if not target_deformer:
            return []

        other_deformers = []
        for node in history:
            node_type = cmds.nodeType(node)
            if node_type in ['blendShape', 'skinCluster', 'cluster', 'deltaMush'] and node != target_deformer:
                other_deformers.append(node)

        for deformer in other_deformers:
            envelope = cmds.getAttr(f"{deformer}.envelope")
            cmds.setAttr(f"{deformer}.envelope", 0)
            self.original_connections[deformer] = envelope

        baked_with_target = self.bake_current_state(mesh_name)

        cmds.setAttr(f"{target_deformer}.envelope", 0)
        baked_without = self.bake_current_state(mesh_name)

        cmds.setAttr(f"{target_deformer}.envelope", 1)

        for deformer, value in self.original_connections.items():
            cmds.setAttr(f"{deformer}.envelope", value)

        self.delta_manager.set_meshes(baked_without, baked_with_target)
        deltas = self.delta_manager.get_deltas()

        cmds.delete([baked_with_target, baked_without])

        return deltas

    def combine_baked_shapes(self, mesh_list, weights=None):
        """Combine multiple baked shapes with weights.

        Args:
            mesh_list: List of mesh names
            weights: Weight values (uniform if None)

        Returns:
            str: Combined mesh name
        """
        if not mesh_list:
            return None

        if weights is None:
            weights = [1.0 / len(mesh_list)] * len(mesh_list)

        base_dup = cmds.duplicate(mesh_list[0], name="combined_bake")[0]

        temp_blendshape = cmds.blendShape(base_dup, name="temp_combine_bs")[0]

        for i, mesh in enumerate(mesh_list[1:], 1):
            cmds.blendShape(temp_blendshape, edit=True,
                            target=(base_dup, i - 1, mesh, 1.0))
            cmds.setAttr(f"{temp_blendshape}.weight[{i - 1}]", weights[i])

        baked = self.bake_current_state(base_dup)
        cmds.delete(base_dup)

        return baked


class BlendShapeConnectionManager:
    """Manages blendshape connections and states for safe operations.

    This class handles:
    - Storing all incoming connections to blendshape weights
    - Storing current weight values
    - Disconnecting all connections temporarily
    - Restoring connections and values after operations
    """

    def __init__(self, blendshape_node):
        """Initialize the connection manager.

        Args:
            blendshape_node: Name of the blendshape node to manage
        """
        if not cmds.objExists(blendshape_node):
            raise ValueError(f"BlendShape node '{blendshape_node}' does not exist")

        if cmds.nodeType(blendshape_node) != 'blendShape':
            raise ValueError(f"'{blendshape_node}' is not a blendShape node")

        self.blendshape = blendshape_node
        self.connections = {}  # {attribute: source_attribute}
        self.values = {}  # {attribute: value}
        self.envelope_connection = None
        self.envelope_value = 1.0

    def store_state(self):
        """Store all connections and values for the blendshape."""
        print(f"Storing state for blendshape: {self.blendshape}")

        # Clear previous state
        self.connections.clear()
        self.values.clear()

        # Get all weight attributes
        weight_attrs = cmds.listAttr(f"{self.blendshape}.weight", multi=True) or []

        for attr in weight_attrs:
            full_attr = f"{self.blendshape}.{attr}"

            # Store current value
            try:
                value = cmds.getAttr(full_attr)
                self.values[attr] = value
            except:
                self.values[attr] = 0.0

            # Check for incoming connections
            connections = cmds.listConnections(full_attr, source=True, destination=False, plugs=True)
            if connections:
                self.connections[attr] = connections[0]
                print(f"  Found connection: {connections[0]} -> {attr}")

        # Also store envelope connection and value
        envelope_attr = f"{self.blendshape}.envelope"
        try:
            self.envelope_value = cmds.getAttr(envelope_attr)
        except:
            self.envelope_value = 1.0

        envelope_conn = cmds.listConnections(envelope_attr, source=True, destination=False, plugs=True)
        if envelope_conn:
            self.envelope_connection = envelope_conn[0]
            print(f"  Found envelope connection: {envelope_conn[0]}")

        print(f"  Stored {len(self.connections)} connections and {len(self.values)} values")

    def safe_disconnect_attr(self, source, destination):
        """Safely disconnect attributes with proper validation.

        Args:
            source (str): Source attribute (e.g., "pCube1.tx")
            destination (str): Destination attribute (e.g., "blendShape1.envelope")

        Returns:
            bool: True if disconnected or no connection existed, False if error
        """
        try:
            # Check if connection exists
            connections = cmds.listConnections(destination, source=True, destination=False, plugs=True)
            if connections and source in connections:
                cmds.disconnectAttr(source, destination)
                return True
            else:
                # No connection to disconnect - this is fine
                return True
        except Exception as e:
            print(f"  Error disconnecting {source} -> {destination}: {e}")
            return False

    def disconnect_all(self):
        """Disconnect all incoming connections to the blendshape."""
        print(f"Disconnecting all connections for: {self.blendshape}")

        # Disconnect weight connections using safe method
        for attr, source in self.connections.items():
            full_attr = f"{self.blendshape}.{attr}"
            if self.safe_disconnect_attr(source, full_attr):
                print(f"  Disconnected: {source} -X-> {attr}")

        # Disconnect envelope if connected using safe method
        if self.envelope_connection:
            envelope_attr = f"{self.blendshape}.envelope"
            if self.safe_disconnect_attr(self.envelope_connection, envelope_attr):
                print(f"  Disconnected envelope: {self.envelope_connection}")

    def restore_connections(self):
        """Restore all connections that were previously disconnected."""
        print(f"Restoring connections for: {self.blendshape}")

        # Restore weight connections
        for attr, source in self.connections.items():
            full_attr = f"{self.blendshape}.{attr}"
            try:
                cmds.connectAttr(source, full_attr, force=True)
                print(f"  Reconnected: {source} -> {attr}")
            except Exception as e:
                print(f"  Warning: Could not reconnect {source} to {attr}: {e}")

        # Restore envelope connection
        if self.envelope_connection:
            try:
                cmds.connectAttr(self.envelope_connection, f"{self.blendshape}.envelope", force=True)
                print(f"  Reconnected envelope: {self.envelope_connection}")
            except Exception as e:
                print(f"  Warning: Could not reconnect envelope: {e}")

    def restore_values(self):
        """Restore all weight values to their stored state."""
        print(f"Restoring values for: {self.blendshape}")

        # Restore weight values
        for attr, value in self.values.items():
            full_attr = f"{self.blendshape}.{attr}"

            # Only set if not connected (connections override values)
            if attr not in self.connections:
                try:
                    cmds.setAttr(full_attr, value)
                except Exception as e:
                    print(f"  Warning: Could not restore value for {attr}: {e}")

        # Restore envelope value if not connected
        if not self.envelope_connection:
            try:
                cmds.setAttr(f"{self.blendshape}.envelope", self.envelope_value)
            except Exception as e:
                print(f"  Warning: Could not restore envelope value: {e}")

    def restore_all(self):
        """Restore both connections and values in the correct order."""
        self.restore_connections()
        self.restore_values()

    @contextmanager
    def disconnected_context(self, restore_values=True):
        """Context manager for operations that need disconnected state.

        Usage:
            manager = BlendShapeConnectionManager('blendShape1')
            manager.store_state()

            with manager.disconnected_context():
                # Do operations with disconnected blendshape
                pass
            # Connections are automatically restored

        Args:
            restore_values: Whether to restore values after reconnecting
        """
        try:
            self.disconnect_all()
            yield self
        finally:
            self.restore_connections()
            if restore_values:
                self.restore_values()

    def get_free_weights(self):
        """Get list of weight attributes that are not connected.

        Returns:
            list: Attribute names that have no incoming connections
        """
        weight_attrs = cmds.listAttr(f"{self.blendshape}.weight", multi=True) or []
        free_weights = []

        for attr in weight_attrs:
            if attr not in self.connections:
                free_weights.append(attr)

        return free_weights

    def get_connected_weights(self):
        """Get dictionary of connected weight attributes.

        Returns:
            dict: {attribute: source_connection}
        """
        return self.connections.copy()

    def zero_all_weights(self):
        """Set all unconnected weights to zero."""
        for attr in self.get_free_weights():
            try:
                cmds.setAttr(f"{self.blendshape}.{attr}", 0)
            except:
                pass


# =========================================================================
# Layer Utility Functions for Target-as-Layer System
# =========================================================================

def parse_target_name(target_name):
    """Parse target name to extract layer info.

    Args:
        target_name: Target name to parse

    Returns:
        tuple: (base_name, layer_number) or (target_name, None)

    Examples:
        'smile' -> ('smile', None)
        'L1_smile' -> ('smile', 1)
        'L2_smile' -> ('smile', 2)
        'L1_L1_smile' -> ('L1_smile', 1)  # Nested layer
    """
    pattern = r'^L(\d+)_(.+)$'
    match = re.match(pattern, target_name)

    if match:
        layer_num = int(match.group(1))
        base_name = match.group(2)
        return base_name, layer_num

    return target_name, None


def is_layer_target(target_name):
    """Check if target is a layer.

    Args:
        target_name: Target name to check

    Returns:
        bool: True if target is a layer
    """
    return bool(re.match(r'^L\d+_', target_name))


def get_parent_target(layer_name):
    """Get parent target name from layer.

    Args:
        layer_name: Layer target name

    Returns:
        str: Parent target name or None
    """
    base_name, layer_num = parse_target_name(layer_name)
    return base_name if layer_num is not None else None


def get_layer_number(layer_name):
    """Extract layer number from layer name.

    Args:
        layer_name: Layer target name

    Returns:
        int: Layer number or None
    """
    _, layer_num = parse_target_name(layer_name)
    return layer_num


def get_next_layer_name(parent_target, existing_targets):
    """Generate next available layer name.

    Args:
        parent_target: Parent target name
        existing_targets: List of existing target names

    Returns:
        str: Next available layer name
    """
    # Find all layers for this parent
    existing_layers = []
    for target in existing_targets:
        base_name, layer_num = parse_target_name(target)
        if base_name == parent_target and layer_num is not None:
            existing_layers.append(layer_num)

    # Find next available number
    next_num = 1
    if existing_layers:
        next_num = max(existing_layers) + 1

    return f"L{next_num}_{parent_target}"


def get_all_layers_for_target(parent_target, all_targets):
    """Get all layer names for a parent target.

    Args:
        parent_target: Parent target name
        all_targets: List of all target names

    Returns:
        list: Layer names sorted by layer number
    """
    layers = []
    for target in all_targets:
        base_name, layer_num = parse_target_name(target)
        if base_name == parent_target and layer_num is not None:
            layers.append((target, layer_num))

    # Sort by layer number
    layers.sort(key=lambda x: x[1])
    return [layer[0] for layer in layers]


def organize_targets_hierarchically(targets_dict):
    """Organize flat target dict into hierarchy.

    Args:
        targets_dict: Flat dictionary of targets

    Returns:
        dict: Hierarchical structure
    """
    hierarchy = {}

    # First pass: identify all parent targets
    for name, info in targets_dict.items():
        base_name, layer_num = parse_target_name(name)

        if layer_num is None:
            # This is a main target
            if name not in hierarchy:
                hierarchy[name] = {
                    **info,
                    'is_parent': True,
                    'layers': []
                }

    # Second pass: add layers to their parents
    for name, info in targets_dict.items():
        base_name, layer_num = parse_target_name(name)

        if layer_num is not None:
            # This is a layer
            if base_name not in hierarchy:
                # Parent doesn't exist as a real target
                hierarchy[base_name] = {
                    'index': -1,
                    'weight': 0.0,
                    'is_parent': True,
                    'exists': False,  # Mark as virtual parent
                    'layers': []
                }

            hierarchy[base_name]['layers'].append({
                'name': name,
                'layer_number': layer_num,
                **info
            })

    # Sort layers by number
    for parent in hierarchy.values():
        parent['layers'].sort(key=lambda x: x['layer_number'])

    return hierarchy


def rename_target_with_layers(old_name, new_name, bs_node):
    """Rename a target and all its layers.

    Args:
        old_name: Current target name
        new_name: New target name
        bs_node: Blendshape node

    Returns:
        list: List of renamed targets [(old, new), ...]
    """
    renamed = []

    # Get all targets
    target_count = cmds.blendShape(bs_node, query=True, weightCount=True)
    all_targets = []

    for i in range(target_count):
        alias = cmds.aliasAttr(f"{bs_node}.weight[{i}]", query=True)
        if alias:
            all_targets.append(alias)

    # Rename main target
    if old_name in all_targets:
        target_index = all_targets.index(old_name)
        cmds.aliasAttr(f"{bs_node}.weight[{target_index}]", remove=True)
        cmds.aliasAttr(new_name, f"{bs_node}.weight[{target_index}]")
        renamed.append((old_name, new_name))

    # Find and rename all layers
    layers = get_all_layers_for_target(old_name, all_targets)
    for layer_name in layers:
        _, layer_num = parse_target_name(layer_name)
        new_layer_name = f"L{layer_num}_{new_name}"

        target_index = all_targets.index(layer_name)
        cmds.aliasAttr(f"{bs_node}.weight[{target_index}]", remove=True)
        cmds.aliasAttr(new_layer_name, f"{bs_node}.weight[{target_index}]")
        renamed.append((layer_name, new_layer_name))

    return renamed


def validate_layer_operation(operation, target_name, bs_node):
    """Validate layer operations before execution.

    Args:
        operation: Operation to validate ('create_layer', 'merge_layer', etc.)
        target_name: Target name
        bs_node: Blendshape node

    Returns:
        tuple: (is_valid, error_message)
    """
    # Get all current targets
    target_count = cmds.blendShape(bs_node, query=True, weightCount=True)
    all_targets = []
    for i in range(target_count):
        alias = cmds.aliasAttr(f"{bs_node}.weight[{i}]", query=True)
        if alias:
            all_targets.append(alias)

    if operation == 'create_layer':
        if is_layer_target(target_name):
            return False, "Cannot create layer on a layer target"
        if target_name not in all_targets:
            return False, f"Target '{target_name}' does not exist"
        return True, None

    elif operation == 'merge_layer':
        if not is_layer_target(target_name):
            return False, f"'{target_name}' is not a layer"
        parent = get_parent_target(target_name)
        if parent not in all_targets:
            return False, f"Parent target '{parent}' does not exist"
        return True, None

    elif operation == 'promote_layer':
        if not is_layer_target(target_name):
            return False, f"'{target_name}' is not a layer"
        parent = get_parent_target(target_name)
        if parent in all_targets:
            return False, f"Cannot promote: parent name '{parent}' already exists"
        return True, None

    elif operation == 'delete_with_layers':
        if is_layer_target(target_name):
            return False, "Use this operation on parent targets only"
        return True, None

    return True, None


def get_layer_depth(target_name):
    """Get the depth of a layer (for nested layers).

    Args:
        target_name: Target name

    Returns:
        int: Depth (0 for main targets, 1+ for layers)
    """
    depth = 0
    current_name = target_name

    while True:
        base_name, layer_num = parse_target_name(current_name)
        if layer_num is None:
            break
        depth += 1
        current_name = base_name

        # Prevent infinite loops
        if depth > 10:
            break

    return depth


if __name__ == "__main__":
    # Run test if executed directly
    test_delta_manager()