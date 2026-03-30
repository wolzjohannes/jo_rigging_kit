"""
BlendShape Manager - Unified backend for blendshape operations
Combines LayerManager, DeltaManager, and MeshBaker functionality
"""

import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om2
from collections import OrderedDict
import json
import os

# Import the classes from mt_blendshape_manager_utils
from .mt_blendshape_manager_utils import DeltaManager, MeshBaker, SimplifiedLayerManager


class BlendShapeManager:
    """Main backend controller for all blendshape operations."""

    def __init__(self, mesh=None):
        """Initialize manager with optional mesh.

        Args:
            mesh: Maya mesh node or None
        """
        self.mesh = mesh
        self.current_bs = None
        self.all_blendshapes = []
        self.layer_manager = None  # Will be initialized when blendshape is set
        self.delta_manager = DeltaManager(verbose=False)
        self.mesh_baker = MeshBaker()
        self.clipboard = {}  # For copy/paste operations
        self.target_cache = {}  # Cache target info for performance
        self._connections_cache = {}

        if mesh:
            self.set_mesh(mesh)

    def set_mesh(self, mesh):
        """Set current mesh and detect blendshapes.

        Args:
            mesh: Maya mesh node

        Returns:
            list: Found blendshape nodes
        """
        if not cmds.objExists(mesh):
            raise ValueError(f"Mesh '{mesh}' does not exist")

        self.mesh = mesh
        self.all_blendshapes = self._find_all_blendshapes()

        # Set first blendshape as current if available
        if self.all_blendshapes:
            self.set_blendshape(self.all_blendshapes[0])

        # Initialize SimplifiedLayerManager with new blendshape
        if mesh:
            self.layer_manager = SimplifiedLayerManager(mesh, mesh)

        return self.all_blendshapes

    def set_blendshape(self, blendshape):
        """Set current blendshape node.

        Args:
            blendshape: BlendShape node name
        """
        if not cmds.objExists(blendshape):
            raise ValueError(f"BlendShape '{blendshape}' does not exist")

        self.current_bs = blendshape
        self._refresh_target_cache()

        # Update SimplifiedLayerManager with new blendshape
        if self.mesh and blendshape:
            self.layer_manager = SimplifiedLayerManager(blendshape, self.mesh)

    def _find_all_blendshapes(self):
        """Find all blendshape nodes in mesh history.

        Returns:
            list: BlendShape node names
        """
        if not self.mesh:
            return []

        history = cmds.listHistory(self.mesh, pruneDagObjects=True) or []
        blendshapes = []

        for node in history:
            if cmds.nodeType(node) == 'blendShape':
                blendshapes.append(node)

        return blendshapes

    def _refresh_target_cache(self):
        """Refresh cached target information."""
        if not self.current_bs:
            return

        self.target_cache = {}
        targets = self.get_targets()

        for target_name, info in targets.items():
            self.target_cache[target_name] = info

    def get_target_info(self, target_name):
        """Get detailed information about a target.

        Args:
            target_name: Name of the target

        Returns:
            dict: Target information
        """
        targets = self.get_targets(include_layers=False)
        if target_name not in targets:
            return None

        info = targets[target_name].copy()

        # Add vertex count
        target_index = info['index']
        pt_attr = f"{self.current_bs}.inputTarget[0].inputTargetGroup[{target_index}].inputTargetItem[6000].inputPointsTarget"
        points = cmds.getAttr(pt_attr) or []
        info['vertex_count'] = len(points)

        return info

    def get_targets(self, include_layers=True):
        """Get all targets with their information.

        Args:
            include_layers: Include layer information

        Returns:
            OrderedDict: Target info by name
        """
        if not self.current_bs:
            return OrderedDict()

        targets = OrderedDict()
        aliases = cmds.aliasAttr(self.current_bs, query=True) or []

        for i in range(0, len(aliases), 2):
            target_name = aliases[i]
            weight_attr = aliases[i + 1]

            # Extract index from weight[n]
            index = int(weight_attr.split('[')[1].split(']')[0])

            # Get current weight value
            weight = cmds.getAttr(f"{self.current_bs}.{target_name}")

            # Check for connections
            connections = cmds.listConnections(
                f"{self.current_bs}.{target_name}",
                source=True, destination=False, plugs=True
            ) or []

            targets[target_name] = {
                'index': index,
                'weight': weight,
                'connected': len(connections) > 0,
                'connections': connections,
                'layers': []
            }

            # Layer information removed - will use empty targets instead

        return targets

    # =========================================================================
    # Layer Operations - NEW SIMPLIFIED APPROACH
    # =========================================================================

    def create_layer(self, target_name, layer_name=None):
        """Create layer using empty target in master blendshape.

        Args:
            target_name: Target to add layer to
            layer_name: Optional custom layer name

        Returns:
            str: Created layer name or None if failed
        """
        if not self.layer_manager:
            print("No layer manager initialized")
            return None

        # Verify target exists in current blendshape
        if self.current_bs:
            targets = self.get_targets(include_layers=False)
            if target_name not in targets:
                print(f"Error: Target '{target_name}' not found in blendshape '{self.current_bs}'")
                return None

        cmds.undoInfo(openChunk=True, chunkName=f'Create Layer: {target_name}')
        try:
            result = self.layer_manager.add_layer(target_name, layer_name)
            return result
        finally:
            cmds.undoInfo(closeChunk=True)

    def merge_layers(self, target_name, delete_after=True):
        """Merge all layers into target using simplified approach.

        Args:
            target_name: Target to merge layers into
            delete_after: Delete layers after merge

        Returns:
            bool: Success
        """
        if not self.layer_manager:
            print("No layer manager initialized")
            return False

        cmds.undoInfo(openChunk=True, chunkName=f'Merge Layers: {target_name}')
        try:
            # Get all layers for this target
            layers = self.layer_manager.list_layers(target_name)
            if not layers:
                print(f"No layers found for target '{target_name}'")
                return False

            # Merge each layer
            success = True
            for layer in layers:
                if not self.layer_manager.merge_layer(target_name, layer, delete_after):
                    success = False

            return success
        finally:
            cmds.undoInfo(closeChunk=True)

    def list_layers(self, target_name):
        """List all layers for a target.

        Args:
            target_name: Target name

        Returns:
            list: Layer names
        """
        if not self.layer_manager:
            return []

        return self.layer_manager.list_layers(target_name)

    # =========================================================================
    # Delta Operations (from DeltaManager)
    # =========================================================================

    def get_target_deltas_directly(self, target_name):
        """Get target deltas directly from blendshape node without modifying any weights.

        Args:
            target_name: Name of the target to get deltas from

        Returns:
            list: Delta tuples (vertex_index, x, y, z) or empty list
        """
        if not self.current_bs:
            return []

        targets = self.get_targets(include_layers=False)
        if target_name not in targets:
            print(f"Target '{target_name}' not found")
            return []

        target_index = targets[target_name]['index']

        # Get delta data directly from blendshape node
        pt_attr = f"{self.current_bs}.inputTarget[0].inputTargetGroup[{target_index}].inputTargetItem[6000].inputPointsTarget"
        ct_attr = f"{self.current_bs}.inputTarget[0].inputTargetGroup[{target_index}].inputTargetItem[6000].inputComponentsTarget"

        points = cmds.getAttr(pt_attr) or []
        components = cmds.getAttr(ct_attr) or []

        if not points or not components:
            return []

        # Decode vertex indices from components
        vertex_indices = []
        for comp in components:
            if 'vtx[' in comp:
                vertex_indices.extend(self._extract_vertex_indices(comp))

        # Build delta list with vertex index
        deltas = []
        for i, vtx_idx in enumerate(vertex_indices):
            if i < len(points):
                p = points[i]
                deltas.append((vtx_idx, p[0], p[1], p[2]))

        return deltas


    def copy_delta(self, target_name=None):
        """Copy delta of current mesh state or specific target.

        Args:
            target_name: Optional target to copy (if None, uses current mesh state)

        Returns:
            bool: Success
        """
        if not self.mesh:
            raise RuntimeError("No mesh set")

        # If copying a specific target, get its deltas directly
        if target_name and self.current_bs:
            deltas = self.get_target_deltas_directly(target_name)

            self.clipboard['current'] = deltas
            self.clipboard[target_name] = deltas

            print(f"Copied {len(deltas)} deltas from target '{target_name}'")
            return True

        # For current mesh state, calculate delta from origin
        else:
            from .mt_blendshape_manager_utils import get_origin_shape

            # Capture current state
            current_mesh = cmds.duplicate(self.mesh, name="temp_current")[0]

            # Get true base using origin shape
            try:
                orig_shape = get_origin_shape(self.mesh)
                base_mesh_shape = cmds.createNode('mesh', name='temp_base_shape')
                base_mesh = cmds.listRelatives(base_mesh_shape, parent=True)[0]
                cmds.connectAttr(f'{orig_shape}.outMesh', f'{base_mesh_shape}.inMesh', force=True)
                cmds.refresh()
                cmds.disconnectAttr(f'{orig_shape}.outMesh', f'{base_mesh_shape}.inMesh')
            except:
                # Fallback: duplicate with all deformers off
                base_mesh = cmds.duplicate(self.mesh, name="temp_base")[0]

            # Calculate deltas
            self.delta_manager.set_meshes(base_mesh, current_mesh)
            deltas = self.delta_manager.get_deltas()

            # Cleanup
            cmds.delete(current_mesh, base_mesh)

            self.clipboard['current'] = deltas
            print(f"Copied {len(deltas)} deltas from current mesh state")
            return True

    def paste_delta_replace(self, target_name, source_key=None):
        """Replace target with deltas from clipboard.

        Args:
            target_name: Target to replace
            source_key: Clipboard key (if None, uses 'current')

        Returns:
            bool: Success
        """
        if not source_key:
            source_key = 'current'

        if source_key not in self.clipboard:
            print(f"No deltas in clipboard (key '{source_key}' not found)")
            return False

        if not self.current_bs:
            raise RuntimeError("No blendshape selected")

        # Apply deltas directly to target
        self.delta_manager.deltas = self.clipboard[source_key]
        success = self.delta_manager.apply_to_blendshape_target(
            self.current_bs, target_name, self.mesh
        )

        if success:
            print(f"Replaced target '{target_name}' with {len(self.clipboard[source_key])} deltas")

        return success

    def paste_delta_add(self, target_name, source_key=None):
        """Add deltas from clipboard to existing target.

        Args:
            target_name: Target to add to
            source_key: Clipboard key (if None, uses 'current')

        Returns:
            bool: Success
        """
        if not source_key:
            source_key = 'current'

        if source_key not in self.clipboard:
            print(f"No deltas in clipboard (key '{source_key}' not found)")
            return False

        if not self.current_bs:
            raise RuntimeError("No blendshape selected")

        # Get existing target deltas directly
        existing_deltas = self.get_target_deltas_directly(target_name)

        # Convert to dict for easier combination
        delta_dict = {}
        for vtx, dx, dy, dz in existing_deltas:
            delta_dict[vtx] = [dx, dy, dz]

        # Add clipboard deltas
        for vtx, dx, dy, dz in self.clipboard[source_key]:
            if vtx in delta_dict:
                delta_dict[vtx][0] += dx
                delta_dict[vtx][1] += dy
                delta_dict[vtx][2] += dz
            else:
                delta_dict[vtx] = [dx, dy, dz]

        # Convert back to list format
        combined_deltas = []
        eps2 = self.delta_manager.eps2
        for vtx, (dx, dy, dz) in sorted(delta_dict.items()):
            # Only keep if movement is significant
            if dx*dx + dy*dy + dz*dz > eps2:
                combined_deltas.append((vtx, dx, dy, dz))

        # Apply combined deltas
        self.delta_manager.deltas = combined_deltas
        success = self.delta_manager.apply_to_blendshape_target(
            self.current_bs, target_name, self.mesh
        )

        if success:
            print(f"Added {len(self.clipboard[source_key])} deltas to '{target_name}'")

        return success

    def paste_delta_subtract(self, target_name, source_key=None):
        """Subtract deltas from clipboard from existing target.

        Args:
            target_name: Target to subtract from
            source_key: Clipboard key (if None, uses 'current')

        Returns:
            bool: Success
        """
        if not source_key:
            source_key = 'current'

        if source_key not in self.clipboard:
            print(f"No deltas in clipboard (key '{source_key}' not found)")
            return False

        if not self.current_bs:
            raise RuntimeError("No blendshape selected")

        # Get existing target deltas directly
        existing_deltas = self.get_target_deltas_directly(target_name)

        # Convert to dict for easier calculation
        delta_dict = {}
        for vtx, dx, dy, dz in existing_deltas:
            delta_dict[vtx] = [dx, dy, dz]

        # Subtract clipboard deltas
        for vtx, dx, dy, dz in self.clipboard[source_key]:
            if vtx in delta_dict:
                delta_dict[vtx][0] -= dx
                delta_dict[vtx][1] -= dy
                delta_dict[vtx][2] -= dz
            else:
                # Subtracting from zero
                delta_dict[vtx] = [-dx, -dy, -dz]

        # Convert back to list format
        result_deltas = []
        eps2 = self.delta_manager.eps2
        for vtx, (dx, dy, dz) in sorted(delta_dict.items()):
            # Only keep if movement is significant
            if dx*dx + dy*dy + dz*dz > eps2:
                result_deltas.append((vtx, dx, dy, dz))

        # Apply result deltas
        self.delta_manager.deltas = result_deltas
        success = self.delta_manager.apply_to_blendshape_target(
            self.current_bs, target_name, self.mesh
        )

        if success:
            print(f"Subtracted {len(self.clipboard[source_key])} deltas from '{target_name}'")

        return success

    # =========================================================================
    # Baking Operations
    # =========================================================================

    def bake_deformer(self, target_name, deformer_type=None, turn_off_deformers=True, preserve_blendshape_state=True, isolate_target=True, target_blendshape=None):
        """Bake deformer influence into target using single invertShape approach.

        Uses invertShape to calculate the pre-skin corrective that includes
        both the target and deformer contribution, then applies it to the target.

        Args:
            target_name: Name of target to bake into
            deformer_type: Type of deformer (unused)
            turn_off_deformers: Whether to turn off deformers during process
            preserve_blendshape_state: Preserve original blendshape weights after baking
            isolate_target: Set all other blendshape weights to 0 during baking
            target_blendshape: Optional blendshape node that contains the target (if different from current_bs)
        """
        cmds.undoInfo(openChunk=True, chunkName=f'Bake Deformer: {target_name}')
        try:
            # Use connection manager to handle connected attributes
            from .mt_blendshape_manager_utils import BlendShapeConnectionManager, BlendshapeStateManager

            # Get deformation history
            history = cmds.listHistory(self.mesh, pruneDagObjects=True) or []
            blendshapes = [node for node in history if cmds.nodeType(node) == 'blendShape']
            skin_clusters = [node for node in history if cmds.nodeType(node) == 'skinCluster']

            # Find deformers to bake
            deformers_to_bake = []
            layer_blendshapes_to_bake = []

            for node in history:
                node_type = cmds.nodeType(node)

                # Special handling for layer blendshapes when merging
                if node_type == 'blendShape' and not isolate_target and "_layers_bs" in node:
                    # Layer blendshapes need to be baked when merging!
                    layer_blendshapes_to_bake.append(node)
                    print(f"  Including layer blendshape for baking: {node}")
                elif (node_type != 'skinCluster' and
                      node_type != 'blendShape' and
                      cmds.attributeQuery('envelope', node=node, exists=True)):
                    deformers_to_bake.append(node)

            # Add layer blendshapes to the deformers list for merge operations
            if not isolate_target:
                deformers_to_bake.extend(layer_blendshapes_to_bake)

            if not skin_clusters:
                print("⚠️ Warning: No skinCluster found, baking may not work as expected")
                skin_cluster = None
            else:
                skin_cluster = skin_clusters[0]
                print(f"✅ Using skinCluster: {skin_cluster}")

            print(f"📦 Deformers to bake: {deformers_to_bake if deformers_to_bake else 'None'}")

            # Use context manager to preserve blendshape states during baking
            with BlendshapeStateManager(self.current_bs, preserve_blendshape_state) as state_manager:
                managers = []
                layer_connections_to_preserve = []

                # When not isolating (merge mode), find connections to layer blendshapes
                if not isolate_target:
                    # Find all layer blendshape nodes
                    layer_bs_nodes = [bs for bs in blendshapes if "_layers_bs" in bs]

                    # For each layer bs, find what connects to its envelope
                    for layer_bs in layer_bs_nodes:
                        envelope_connections = cmds.listConnections(
                            f"{layer_bs}.envelope",
                            source=True, destination=False, plugs=True
                        ) or []

                        if envelope_connections:
                            # Store the connection info
                            for src in envelope_connections:
                                layer_connections_to_preserve.append({
                                    'source': src,
                                    'destination': f"{layer_bs}.envelope"
                                })
                                print(f"  Will preserve connection: {src} -> {layer_bs}.envelope")

                for bs in blendshapes:
                    # Skip disconnecting layer blendshapes themselves
                    if not isolate_target and "_layers_bs" in bs:
                        print(f"  Preserving layer blendshape: {bs}")
                        continue
                    manager = BlendShapeConnectionManager(bs)
                    manager.store_state()
                    manager.disconnect_all()
                    managers.append(manager)

                # Restore critical layer connections that were just disconnected
                if not isolate_target:
                    for conn in layer_connections_to_preserve:
                        try:
                            cmds.connectAttr(conn['source'], conn['destination'], force=True)
                            print(f"  Restored connection: {conn['source']} -> {conn['destination']}")
                        except:
                            pass

                # Store original states
                deformer_states = {}
                for deformer in deformers_to_bake:
                    # Skip layer blendshapes - their state is controlled by connections
                    if "_layers_bs" in deformer:
                        continue
                    try:
                        deformer_states[deformer] = cmds.getAttr(f"{deformer}.envelope")
                    except:
                        pass  # May be connected/locked

                # STEP 1: Capture DESIRED result (target=1, deformers as user set them)
                print(f"\n📸 Step 1: Capturing desired result (target=1, deformers as currently set)")
                # Use target_blendshape if provided, otherwise use current_bs
                target_bs = target_blendshape if target_blendshape else self.current_bs
                cmds.setAttr(f"{target_bs}.{target_name}", 1)
                # Don't modify deformers - capture them as the user has set them

                desired_mesh = cmds.duplicate(self.mesh, name=f"{target_name}_desired")[0]

                # STEP 2: Setup live mesh for invertShape (target=0, deformers OFF, skin ON)
                print(f"🎯 Step 2: Setting up live mesh (target=0, deformers OFF, skin ON)")
                cmds.setAttr(f"{target_bs}.{target_name}", 0)
                for deformer in deformers_to_bake:
                    # Skip layer blendshapes - they're controlled by master connection
                    if "_layers_bs" in deformer:
                        print(f"  Skipping layer blendshape (controlled by master): {deformer}")
                        continue
                    try:
                        cmds.setAttr(f"{deformer}.envelope", 0)
                    except:
                        print(f"  Warning: Could not turn off {deformer} (may be connected)")
                if skin_cluster:
                    cmds.setAttr(f"{skin_cluster}.envelope", 1)  # Keep skin ON - crucial!

                # STEP 3: Calculate pre-skin solution using invertShape
                print(f"🔄 Step 3: Computing pre-skin corrective with invertShape")
                try:
                    import pymel.core as pm
                    inverted_shape = str(pm.invertShape(self.mesh, desired_mesh))
                    print(f"  ✅ InvertShape created: {inverted_shape}")
                except Exception as e:
                    print(f"  ❌ InvertShape failed: {e}")
                    cmds.delete(desired_mesh)
                    # Restore states
                    for deformer, value in deformer_states.items():
                        cmds.setAttr(f"{deformer}.envelope", value)
                    return False

                # STEP 4: Get pre-skin BASE reference (P) - no targets, no skin
                print(f"📐 Step 4: Getting pre-skin base reference (all targets OFF)")

                # Store current weights of other targets
                other_weights = {}
                targets = self.get_targets(include_layers=False)
                for name, info in targets.items():
                    if name != target_name:
                        other_weights[name] = info['weight']
                        cmds.setAttr(f"{self.current_bs}.{name}", 0)  # Turn OFF all others

                # Temporarily turn OFF skinCluster to get pure base mesh
                if skin_cluster:
                    cmds.setAttr(f"{skin_cluster}.envelope", 0)
                pre_skin_base = cmds.duplicate(self.mesh, name=f"{target_name}_preSkinBase")[0]

                # Restore skin and other target weights
                if skin_cluster:
                    cmds.setAttr(f"{skin_cluster}.envelope", 1)  # Turn back ON
                for name, weight in other_weights.items():
                    cmds.setAttr(f"{self.current_bs}.{name}", weight)  # Restore others

                # STEP 5: Calculate delta (S - P) and apply to target
                print(f"📝 Step 5: Calculating and applying delta to target")
                # Delta = inverted_shape - pre_skin_base (just base, no other targets)
                self.delta_manager.set_meshes(pre_skin_base, inverted_shape)
                final_delta = self.delta_manager.get_deltas()

                if final_delta:
                    print(f"  💾 Applying {len(final_delta)} deltas to target '{target_name}'")
                    self.delta_manager.deltas = final_delta
                    self.delta_manager.apply_to_blendshape_target(self.current_bs, target_name, self.mesh)
                else:
                    print(f"  ⚠️ No deltas calculated - target may already be correct")

                # STEP 6: Cleanup
                print(f"🧹 Cleaning up temporary meshes")
                cmds.delete(desired_mesh, pre_skin_base)
                if cmds.objExists(inverted_shape):
                    cmds.delete(inverted_shape)

                # Turn OFF deformers after successful bake (they're now baked into the target)
                print(f"🔌 Turning OFF baked deformers")
                for deformer in deformers_to_bake:
                    # Skip layer blendshapes - they should be deleted/handled separately
                    if "_layers_bs" in deformer:
                        print(f"  - Skipping layer blendshape (will be handled by merge): {deformer}")
                        continue
                    try:
                        cmds.setAttr(f"{deformer}.envelope", 0)
                        print(f"  - Deactivated: {deformer}")
                    except:
                        pass

                # Restore all connections
                for manager in managers:
                    manager.restore_all()

                print(f"\n✅ Successfully baked deformer into target '{target_name}'")
                return True

        finally:
            cmds.undoInfo(closeChunk=True)

    def rename_target(self, old_name, new_name):
        """Rename a blendshape target.

        Args:
            old_name: Current target name
            new_name: New target name

        Returns:
            bool: Success
        """
        if not self.current_bs:
            raise RuntimeError("No blendshape selected")

        cmds.undoInfo(openChunk=True, chunkName=f'Rename Target: {old_name} to {new_name}')
        try:
            targets = self.get_targets(include_layers=False)
            if old_name not in targets:
                print(f"Target '{old_name}' not found")
                return False

            target_index = targets[old_name]['index']

            # Remove old alias
            cmds.aliasAttr(f"{self.current_bs}.weight[{target_index}]", remove=True)

            # Set new alias
            cmds.aliasAttr(new_name, f"{self.current_bs}.weight[{target_index}]")

            # Refresh cache
            self._refresh_target_cache()

            print(f"Renamed '{old_name}' to '{new_name}'")
            return True
        finally:
            cmds.undoInfo(closeChunk=True)

    def extract_target(self, target_name):
        """Extract target as separate mesh.

        Args:
            target_name: Target to extract

        Returns:
            str: Extracted mesh name
        """
        if not self.current_bs or not self.mesh:
            raise RuntimeError("No blendshape or mesh selected")

        # Use connection manager to handle connected attributes
        from .mt_blendshape_manager_utils import BlendShapeConnectionManager
        manager = BlendShapeConnectionManager(self.current_bs)
        manager.store_state()
        manager.disconnect_all()

        # Store original weights
        targets = self.get_targets(include_layers=False)
        original_weights = {}
        for name, info in targets.items():
            original_weights[name] = info['weight']
            cmds.setAttr(f"{self.current_bs}.{name}", 0)

        # Activate target
        cmds.setAttr(f"{self.current_bs}.{target_name}", 1)

        # Duplicate mesh
        extracted = cmds.duplicate(self.mesh, name=f"{target_name}_extracted")[0]

        # Restore weights
        for name, weight in original_weights.items():
            cmds.setAttr(f"{self.current_bs}.{name}", weight)

        # Restore connections
        manager.restore_all()

        print(f"Extracted '{target_name}' as '{extracted}'")
        return extracted

    # =========================================================================
    # Weight Operations
    # =========================================================================

    def zero_all_deltas(self, target_name):
        """Remove all deltas from a target (set to zero).

        Args:
            target_name: Target to zero out

        Returns:
            bool: Success
        """
        if not self.current_bs:
            raise RuntimeError("No blendshape selected")

        cmds.undoInfo(openChunk=True, chunkName=f'Zero Deltas: {target_name}')
        try:
            targets = self.get_targets(include_layers=False)
            if target_name not in targets:
                print(f"Target '{target_name}' not found")
                return False

            target_index = targets[target_name]['index']

            # Clear point and component data (zeroes the deltas)
            pt = f"{self.current_bs}.inputTarget[0].inputTargetGroup[{target_index}].inputTargetItem[6000].inputPointsTarget"
            ct = f"{self.current_bs}.inputTarget[0].inputTargetGroup[{target_index}].inputTargetItem[6000].inputComponentsTarget"

            # Set to empty arrays - this zeros the deltas while keeping the target
            cmds.setAttr(pt, 0, type='pointArray')
            cmds.setAttr(ct, 0, type='componentList')

            print(f"Zeroed all deltas for target '{target_name}'")
            return True
        finally:
            cmds.undoInfo(closeChunk=True)

    def zero_all_weights(self):
        """Set all target weights to 0 (not deltas, just weights).

        Returns:
            dict: Previous weight values
        """
        if not self.current_bs:
            raise RuntimeError("No blendshape selected")

        # Use connection manager to handle connected attributes
        from .mt_blendshape_manager_utils import BlendShapeConnectionManager
        manager = BlendShapeConnectionManager(self.current_bs)
        manager.store_state()
        manager.disconnect_all()

        targets = self.get_targets(include_layers=False)
        previous = {}

        for name, info in targets.items():
            previous[name] = info['weight']
            cmds.setAttr(f"{self.current_bs}.{name}", 0)

        # Restore connections but not values (we want weights at 0)
        manager.restore_connections()

        print(f"Set {len(targets)} target weights to 0")
        return previous

    def solo_target(self, target_name):
        """Set solo target to 1, others to 0.

        Args:
            target_name: Target to solo

        Returns:
            dict: Previous weight values
        """
        if not self.current_bs:
            raise RuntimeError("No blendshape selected")

        # Use connection manager to handle connected attributes
        from .mt_blendshape_manager_utils import BlendShapeConnectionManager
        manager = BlendShapeConnectionManager(self.current_bs)
        manager.store_state()
        manager.disconnect_all()

        targets = self.get_targets(include_layers=False)
        previous = {}

        for name, info in targets.items():
            previous[name] = info['weight']
            value = 1.0 if name == target_name else 0.0
            cmds.setAttr(f"{self.current_bs}.{name}", value)

        # Restore connections but not values (we want our solo values)
        manager.restore_connections()

        print(f"Solo mode: '{target_name}'")
        return previous

    def restore_weights(self, weights):
        """Restore weight values.

        Args:
            weights: Dict of target_name: weight_value
        """
        if not self.current_bs:
            return

        for name, value in weights.items():
            if not self._is_connected(name):
                try:
                    cmds.setAttr(f"{self.current_bs}.{name}", value)
                except:
                    pass

    def _is_connected(self, target_name):
        """Check if target weight is connected.

        Args:
            target_name: Target to check

        Returns:
            bool: True if connected
        """
        connections = cmds.listConnections(
            f"{self.current_bs}.{target_name}",
            source=True, destination=False
        )
        return bool(connections)

    # =========================================================================
    # Advanced Operations (from mt_blendshape_tool)
    # =========================================================================

    def keep_selected_vertices(self, target_name):
        """Keep only selected vertices in target delta.
        Supports soft selection weighting.

        Args:
            target_name: Target to modify

        Returns:
            bool: Success
        """
        if not self.current_bs or not self.mesh:
            raise RuntimeError("No blendshape or mesh set")

        cmds.undoInfo(openChunk=True, chunkName=f'Keep Selected Vertices: {target_name}')

        targets = self.get_targets(include_layers=False)
        if target_name not in targets:
            print(f"Target '{target_name}' not found")
            return False

        target_index = targets[target_name]['index']

        # Get point and component attributes
        pt = f"{self.current_bs}.inputTarget[0].inputTargetGroup[{target_index}].inputTargetItem[6000].inputPointsTarget"
        ct = f"{self.current_bs}.inputTarget[0].inputTargetGroup[{target_index}].inputTargetItem[6000].inputComponentsTarget"

        pts = cmds.getAttr(pt) or []
        comps = cmds.getAttr(ct) or []

        if not pts or not comps:
            print(f"No delta data for target '{target_name}'")
            return False

        # Decode component list to vertex indices
        all_vertices = []
        for comp in comps:
            if 'vtx[' in comp:
                all_vertices.extend(self._extract_vertex_indices(comp))

        vertex_to_index = {v: i for i, v in enumerate(all_vertices)}

        # Check for soft selection
        soft_weights = self._get_soft_selection_weights()

        if soft_weights:
            # Apply soft selection weights
            new_pts = []
            kept_vertices = []

            for v in all_vertices:
                if v in soft_weights:
                    weight = soft_weights[v]
                    if weight > 0.0:
                        p = pts[vertex_to_index[v]]
                        new_pts.append([p[0] * weight, p[1] * weight, p[2] * weight])
                        kept_vertices.append(v)

            if not kept_vertices:
                cmds.setAttr(pt, 0, type='pointArray')
                cmds.setAttr(ct, 0, type='componentList')
                print(f"Cleared all deltas for '{target_name}'")
                return True

            new_comps = self._build_component_list(kept_vertices)
            cmds.setAttr(pt, len(new_pts), *new_pts, type='pointArray')
            cmds.setAttr(ct, len(new_comps), *new_comps, type='componentList')
            print(f"Applied soft selection to {len(kept_vertices)} vertices")
            cmds.undoInfo(closeChunk=True)
            return True
        else:
            # Hard selection
            sel = cmds.ls(sl=True, fl=True) or []
            mesh_name = self.mesh
            keep = set()

            for s in sel:
                if mesh_name in s and '.vtx[' in s:
                    try:
                        keep.add(int(s.split('.vtx[')[-1].rstrip(']')))
                    except:
                        pass

            kept = [v for v in all_vertices if v in keep]

            if not kept:
                cmds.setAttr(pt, 0, type='pointArray')
                cmds.setAttr(ct, 0, type='componentList')
                print(f"Cleared all deltas for '{target_name}'")
                return True

            new_pts = [pts[vertex_to_index[v]] for v in kept]
            new_comps = self._build_component_list(kept)
            cmds.setAttr(pt, len(new_pts), *new_pts, type='pointArray')
            cmds.setAttr(ct, len(new_comps), *new_comps, type='componentList')
            print(f"Kept {len(kept)} selected vertices")
            cmds.undoInfo(closeChunk=True)
            return True

    def mirror_target(self, source_name, dest_name=None, axis='x', tolerance=0.001):
        """Mirror target deltas to opposite side.
        Fast implementation using spatial hashing.

        Args:
            source_name: Source target name
            dest_name: Destination name (auto-generated if None)
            axis: Mirror axis ('x', 'y', or 'z')
            tolerance: Symmetry matching tolerance

        Returns:
            str: Destination target name if successful
        """
        if not self.current_bs or not self.mesh:
            raise RuntimeError("No blendshape or mesh set")

        cmds.undoInfo(openChunk=True, chunkName=f'Mirror Target: {source_name}')

        targets = self.get_targets(include_layers=False)
        if source_name not in targets:
            print(f"Source target '{source_name}' not found")
            return None

        source_index = targets[source_name]['index']

        # Auto-generate destination name
        if dest_name is None:
            dest_name = self._get_mirror_name(source_name)
            if dest_name == source_name:
                dest_name = f"{source_name}_mirror"

        # Get source delta data
        src_pt = f"{self.current_bs}.inputTarget[0].inputTargetGroup[{source_index}].inputTargetItem[6000].inputPointsTarget"
        src_ct = f"{self.current_bs}.inputTarget[0].inputTargetGroup[{source_index}].inputTargetItem[6000].inputComponentsTarget"

        points = cmds.getAttr(src_pt) or []
        components = cmds.getAttr(src_ct) or []

        if not points:
            print(f"No delta data for source target '{source_name}'")
            return None

        print(f"Mirroring {len(points)} vertices with deltas...")

        # Decode source vertices
        source_vertices = []
        for comp in components:
            if 'vtx[' in comp:
                source_vertices.extend(self._extract_vertex_indices(comp))

        # Get mesh vertex positions for spatial lookup
        vertex_count = cmds.polyEvaluate(self.mesh, vertex=True)

        # Build spatial hash for fast lookup
        axis_index = {'x': 0, 'y': 1, 'z': 2}[axis]
        vertex_map = {}

        for i in range(vertex_count):
            pos = cmds.xform(f"{self.mesh}.vtx[{i}]", q=True, ws=True, t=True)
            # Create key for mirrored position
            mirrored_pos = list(pos)
            mirrored_pos[axis_index] = -mirrored_pos[axis_index]
            key = tuple([round(p / tolerance) * tolerance for p in mirrored_pos])
            vertex_map[key] = i

        # Find mirror matches
        mirrored_deltas = []
        mirrored_vertices = []

        for i, vertex_index in enumerate(source_vertices):
            # Get source vertex position
            pos = cmds.xform(f"{self.mesh}.vtx[{vertex_index}]", q=True, ws=True, t=True)

            # Look up mirrored vertex
            key = tuple([round(p / tolerance) * tolerance for p in pos])
            if key in vertex_map:
                mirror_vertex = vertex_map[key]

                # Mirror the delta
                delta = points[i]
                mirrored_delta = list(delta)
                mirrored_delta[axis_index] = -mirrored_delta[axis_index]

                mirrored_deltas.append(mirrored_delta)
                mirrored_vertices.append(mirror_vertex)

        if not mirrored_deltas:
            print("No mirror matches found")
            return None

        # Check if destination target exists
        if dest_name in targets:
            dest_index = targets[dest_name]['index']
        else:
            # Create new target
            max_index = max([info['index'] for info in targets.values()]) if targets else -1
            dest_index = max_index + 1

            # Add empty target
            dup = cmds.duplicate(self.mesh, name=dest_name)[0]
            cmds.blendShape(self.current_bs, edit=True,
                           target=(self.mesh, dest_index, dup, 1.0))
            cmds.aliasAttr(dest_name, f"{self.current_bs}.weight[{dest_index}]")
            cmds.delete(dup)

        # Set mirrored deltas
        dest_pt = f"{self.current_bs}.inputTarget[0].inputTargetGroup[{dest_index}].inputTargetItem[6000].inputPointsTarget"
        dest_ct = f"{self.current_bs}.inputTarget[0].inputTargetGroup[{dest_index}].inputTargetItem[6000].inputComponentsTarget"

        dest_comps = self._build_component_list(mirrored_vertices)
        cmds.setAttr(dest_pt, len(mirrored_deltas), *mirrored_deltas, type='pointArray')
        cmds.setAttr(dest_ct, len(dest_comps), *dest_comps, type='componentList')

        print(f"Mirrored {len(mirrored_deltas)} vertices to '{dest_name}'")
        self._refresh_target_cache()
        cmds.undoInfo(closeChunk=True)

        return dest_name

    def _get_mirror_name(self, name):
        """Generate mirrored name (L_ <-> R_).

        Args:
            name: Original name

        Returns:
            str: Mirrored name
        """
        if name.startswith('L_'):
            return 'R_' + name[2:]
        elif name.startswith('R_'):
            return 'L_' + name[2:]
        elif name.startswith('l_'):
            return 'r_' + name[2:]
        elif name.startswith('r_'):
            return 'l_' + name[2:]
        elif '_L_' in name:
            return name.replace('_L_', '_R_')
        elif '_R_' in name:
            return name.replace('_R_', '_L_')
        elif '_l_' in name:
            return name.replace('_l_', '_r_')
        elif '_r_' in name:
            return name.replace('_r_', '_l_')
        else:
            return name

    def _extract_vertex_indices(self, comp_str):
        """Extract vertex indices from component string.

        Args:
            comp_str: Component string like 'vtx[0:5]'

        Returns:
            list: Vertex indices
        """
        if 'vtx[' not in comp_str:
            return []

        comp_str = comp_str.replace('vtx[', '').replace(']', '')

        if ':' in comp_str:
            parts = comp_str.split(':')
            if len(parts) == 2:
                try:
                    return list(range(int(parts[0]), int(parts[1]) + 1))
                except ValueError:
                    return []
        else:
            try:
                return [int(comp_str)]
            except ValueError:
                return []

    def _build_component_list(self, indices):
        """Build component list from vertex indices.

        Args:
            indices: List of vertex indices

        Returns:
            list: Component strings like ['vtx[0:5]', 'vtx[10]']
        """
        if not indices:
            return []

        indices = sorted(indices)
        components = []
        i = 0

        while i < len(indices):
            start = indices[i]
            end = start

            # Find consecutive range
            while i + 1 < len(indices) and indices[i + 1] == indices[i] + 1:
                i += 1
                end = indices[i]

            # Add component
            if start == end:
                components.append(f'vtx[{start}]')
            else:
                components.append(f'vtx[{start}:{end}]')

            i += 1

        return components

    def swap_mesh_to_target(self, target_name, source_mesh, use_undo=True):
        """Replace target geometry with selected mesh.

        Args:
            target_name: Name of target to replace
            source_mesh: Source mesh to use as new target shape
            use_undo: Whether to create undo chunk (False when called from bake_deformer)

        Returns:
            bool: Success
        """
        if not self.current_bs or not self.mesh:
            raise RuntimeError("No blendshape or mesh set")

        if use_undo:
            cmds.undoInfo(openChunk=True, chunkName=f'Swap Mesh to Target: {target_name}')

        # Use connection manager to handle connected attributes
        from .mt_blendshape_manager_utils import BlendShapeConnectionManager
        manager = BlendShapeConnectionManager(self.current_bs)
        manager.store_state()
        manager.disconnect_all()

        targets = self.get_targets(include_layers=False)
        if target_name not in targets:
            print(f"Target '{target_name}' not found")
            return False

        # Validate source mesh
        if not cmds.objExists(source_mesh):
            raise RuntimeError(f"Source mesh '{source_mesh}' does not exist")

        # Check topology
        source_vtx_count = cmds.polyEvaluate(source_mesh, vertex=True)
        mesh_vtx_count = cmds.polyEvaluate(self.mesh, vertex=True)

        if source_vtx_count != mesh_vtx_count:
            raise RuntimeError(f"Topology mismatch: source has {source_vtx_count} vertices, target has {mesh_vtx_count}")

        target_index = targets[target_name]['index']

        print(f"Swapping mesh to target: {target_name}")

        # Store current envelope
        original_envelope = cmds.getAttr(f"{self.current_bs}.envelope")

        # Disable blendshape temporarily
        cmds.setAttr(f"{self.current_bs}.envelope", 0)

        # Check if we need to invert (pre-skin vs post-skin)
        is_post_skin = self._is_post_skin_deformer()

        if is_post_skin:
            # Post-skin: use mesh directly as corrective
            print("  Post-skin workflow: using mesh directly")
            target_mesh = source_mesh
        else:
            # Pre-skin: need to invert shape
            print("  Pre-skin workflow: inverting shape")
            # Use Maya's invertShape if available, otherwise use our own method
            try:
                import pymel.core as pm
                base_shape = self.mesh
                source_shape = source_mesh

                # Get shape nodes
                if cmds.nodeType(base_shape) == 'transform':
                    base_shapes = cmds.listRelatives(base_shape, shapes=True, type='mesh')
                    base_shape = base_shapes[0] if base_shapes else base_shape

                if cmds.nodeType(source_shape) == 'transform':
                    source_shapes = cmds.listRelatives(source_shape, shapes=True, type='mesh')
                    source_shape = source_shapes[0] if source_shapes else source_shape

                # Use PyMel's invertShape
                inverted = pm.invertShape(base_shape, source_shape)
                target_mesh = str(inverted)
            except:
                # Fallback: use source directly
                print("  Warning: Could not invert shape, using source directly")
                target_mesh = source_mesh

        # Remove old target data
        pt = f"{self.current_bs}.inputTarget[0].inputTargetGroup[{target_index}].inputTargetItem[6000].inputPointsTarget"
        ct = f"{self.current_bs}.inputTarget[0].inputTargetGroup[{target_index}].inputTargetItem[6000].inputComponentsTarget"

        cmds.setAttr(pt, 0, type='pointArray')
        cmds.setAttr(ct, 0, type='componentList')

        # Add new target
        cmds.blendShape(self.current_bs, edit=True,
                       target=(self.mesh, target_index, target_mesh, 1.0),
                       topologyCheck=False)

        # Restore alias
        cmds.aliasAttr(target_name, f"{self.current_bs}.weight[{target_index}]")

        # Clean up inverted mesh if we created one
        if not is_post_skin and target_mesh != source_mesh and cmds.objExists(target_mesh):
            try:
                cmds.delete(target_mesh)
            except:
                pass

        # Restore envelope
        cmds.setAttr(f"{self.current_bs}.envelope", original_envelope)

        # Restore connections
        manager.restore_all()

        print(f"Successfully swapped mesh to target: {target_name}")
        if use_undo:
            cmds.undoInfo(closeChunk=True)
        return True

    def _is_post_skin_deformer(self):
        """Check if blendshape is post-skin (corrective) or pre-skin.

        Returns:
            bool: True if post-skin, False if pre-skin
        """
        if not self.mesh or not self.current_bs:
            return False

        history = cmds.listHistory(self.mesh, pruneDagObjects=True) or []

        # Find positions of blendshape and skinCluster
        bs_index = -1
        skin_index = -1

        for i, node in enumerate(history):
            node_type = cmds.nodeType(node)
            if node == self.current_bs:
                bs_index = i
            elif node_type == 'skinCluster':
                skin_index = i

        # If skin comes before blendshape in history, it's post-skin
        if skin_index >= 0 and bs_index >= 0:
            return skin_index < bs_index

        return False

    def _get_soft_selection_weights(self):
        """Get soft selection weights for current mesh.

        Returns:
            dict: Vertex index to weight mapping
        """
        if not cmds.softSelect(q=True, sse=True):
            return {}

        try:
            import maya.OpenMaya as om

            rich = om.MRichSelection()
            om.MGlobal.getRichSelection(rich)
            sel = om.MSelectionList()
            rich.getSelection(sel)

            if sel.length() == 0:
                return {}

            weights = {}
            dag = om.MDagPath()
            comp = om.MObject()

            it = om.MItSelectionList(sel, om.MFn.kMeshVertComponent)
            while not it.isDone():
                it.getDagPath(dag, comp)

                if comp.apiType() == om.MFn.kMeshVertComponent:
                    fnc = om.MFnSingleIndexedComponent(comp)
                    cnt = fnc.elementCount()

                    for i in range(cnt):
                        v = fnc.element(i)
                        w = fnc.weight(i).influence() if fnc.hasWeights() else 1.0
                        if w > 0.0:
                            weights[int(v)] = float(w)

                it.next()

            return weights
        except:
            return {}

    # =========================================================================
    # File Operations
    # =========================================================================

    def export_deltas(self, filepath, target_name=None):
        """Export deltas to file.

        Args:
            filepath: Output file path
            target_name: Specific target or None for all

        Returns:
            bool: Success
        """
        data = {}

        if target_name:
            # Export specific target
            self.copy_delta(target_name)
            data[target_name] = self.clipboard.get(target_name, [])
        else:
            # Export all targets
            targets = self.get_targets(include_layers=False)
            for name in targets:
                self.copy_delta(name)
                data[name] = self.clipboard.get(name, [])

        # Convert deltas to serializable format
        export_data = {}
        for name, deltas in data.items():
            export_data[name] = [
                [int(d[0]), float(d[1]), float(d[2]), float(d[3])]
                for d in deltas
            ]

        # Write to file
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)

        print(f"Exported deltas to: {filepath}")
        return True

    def import_deltas(self, filepath):
        """Import deltas from file.

        Args:
            filepath: Input file path

        Returns:
            bool: Success
        """
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            return False

        with open(filepath, 'r') as f:
            data = json.load(f)

        # Convert to delta format and store in clipboard
        for name, deltas in data.items():
            self.clipboard[name] = [
                (int(d[0]), float(d[1]), float(d[2]), float(d[3]))
                for d in deltas
            ]

        print(f"Imported {len(data)} targets from: {filepath}")
        return True


if __name__ == "__main__":
    show()