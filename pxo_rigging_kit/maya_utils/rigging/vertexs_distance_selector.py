"""
Vertex Distance Selector for Maya
==================================
A tool for selecting mesh vertices or curve CVs within a specified distance from another object.

Supports:
- Mesh to Mesh: selects vertices of source mesh near target mesh
- Mesh to Curve: selects vertices of source mesh near target curve
- Curve to Mesh: selects CVs of source curve near target mesh
- Curve to Curve: selects CVs of source curve near target curve

Author: Assistant
Version: 1.0
Maya Version: 2020+
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om2


class VertexDistanceSelector:
    """
    Core class for distance-based component selection.

    Usage:
        selector = VertexDistanceSelector()
        components = selector.select_by_distance(distance=2.0)
    """

    def __init__(self):
        """Initialize the selector with empty result cache."""
        self.last_result = []

    def detect_type(self, obj):
        """
        Detect if object is mesh or curve.

        Args:
            obj (str): Name of the Maya object

        Returns:
            str: 'mesh', 'curve', or None if neither
        """
        shapes = cmds.listRelatives(obj, shapes=True, fullPath=True) or []

        for shape in shapes:
            node_type = cmds.nodeType(shape)
            if node_type == 'mesh':
                return 'mesh'
            elif node_type == 'nurbsCurve':
                return 'curve'

        return None

    def select_by_distance(self, source=None, target=None, distance=1.0):
        """
        Main method to select components within specified distance.

        Args:
            source (str): Source object name. If None, uses first selected object
            target (str): Target object name. If None, uses second selected object
            distance (float): Maximum distance threshold for selection

        Returns:
            list: Names of selected components (e.g., ['pSphere1.vtx[0]', 'pSphere1.vtx[1]'])

        Example:
            # Using current selection
            selector = VertexDistanceSelector()
            result = selector.select_by_distance(distance=2.5)

            # Using specific objects
            result = selector.select_by_distance('pSphere1', 'pCube1', distance=3.0)
        """
        # Get objects from selection if not provided
        if not source or not target:
            selection = cmds.ls(sl=True, type='transform')
            if len(selection) < 2:
                cmds.warning("Please select two objects (mesh or curve)")
                return []
            source = selection[0]
            target = selection[1]

        # Detect object types
        source_type = self.detect_type(source)
        target_type = self.detect_type(target)

        if not source_type or not target_type:
            cmds.warning("Invalid object types")
            return []

        # Route to appropriate method based on object types
        result = []
        if source_type == 'mesh' and target_type == 'mesh':
            result = self._mesh_to_mesh(source, target, distance)
        elif source_type == 'mesh' and target_type == 'curve':
            result = self._mesh_to_curve(source, target, distance)
        elif source_type == 'curve' and target_type == 'mesh':
            result = self._curve_to_mesh(source, target, distance)
        elif source_type == 'curve' and target_type == 'curve':
            result = self._curve_to_curve(source, target, distance)

        # Store and select result
        self.last_result = result

        if result:
            cmds.select(result, r=True)
        else:
            cmds.select(clear=True)

        return result

    def _get_bbox_candidates(self, points, target_bbox, distance):
        """
        Pre-filter points using bounding box check for performance.
        Only points within expanded bounding box are considered.

        Args:
            points: List of MPoint objects
            target_bbox: MBoundingBox of target object
            distance: Distance to expand bounding box

        Returns:
            set: Indices of points within expanded bounding box
        """
        bbox_min = target_bbox.min
        bbox_max = target_bbox.max

        candidates = []
        for i, point in enumerate(points):
            # Check if point is within expanded bounding box
            if (point.x >= bbox_min.x - distance and point.x <= bbox_max.x + distance and
                    point.y >= bbox_min.y - distance and point.y <= bbox_max.y + distance and
                    point.z >= bbox_min.z - distance and point.z <= bbox_max.z + distance):
                candidates.append(i)

        return set(candidates)

    def _mesh_to_mesh(self, source_mesh, target_mesh, distance):
        """
        Select vertices of source mesh within distance from target mesh.
        Uses bounding box pre-filtering for performance.
        Shows progress bar for meshes with >1000 vertices.
        """
        components = []

        try:
            # Get target mesh function set
            sel = om2.MSelectionList()
            sel.add(target_mesh)
            target_dag = sel.getDagPath(0)
            target_dag.extendToShape()
            target_fn = om2.MFnMesh(target_dag)

            # Get source mesh function set
            sel.clear()
            sel.add(source_mesh)
            source_dag = sel.getDagPath(0)
            source_dag.extendToShape()
            source_fn = om2.MFnMesh(source_dag)

            # Get all vertex positions at once for performance
            all_points = source_fn.getPoints(om2.MSpace.kWorld)
            target_bbox = target_fn.boundingBox

            # Pre-filter vertices using bounding box
            valid_indices = self._get_bbox_candidates(all_points, target_bbox, distance)

            # Show progress bar for large operations
            total = len(valid_indices)
            show_progress = total > 1000

            if show_progress:
                cmds.progressWindow(title='Processing',
                                    progress=0,
                                    status=f'Checking {total} vertices...',
                                    isInterruptable=True)

            try:
                # Process only vertices that passed bbox filter
                for i, idx in enumerate(valid_indices):
                    point = all_points[idx]
                    # Find closest point on target mesh
                    closest_point = target_fn.getClosestPoint(point, space=om2.MSpace.kWorld)[0]

                    # Check actual distance
                    if point.distanceTo(closest_point) <= distance:
                        components.append(f'{source_mesh}.vtx[{idx}]')

                    # Update progress bar
                    if show_progress and i % 100 == 0:
                        if cmds.progressWindow(query=True, isCancelled=True):
                            break
                        progress = int((i / total) * 100)
                        cmds.progressWindow(edit=True, progress=progress)

            finally:
                if show_progress:
                    cmds.progressWindow(endProgress=1)

        except Exception as e:
            cmds.warning(f"Error: {str(e)}")

        return components

    def _mesh_to_curve(self, source_mesh, target_curve, distance):
        """
        Select vertices of source mesh within distance from target curve.
        Uses bounding box pre-filtering for performance.
        """
        components = []

        try:
            # Get curve function set
            sel = om2.MSelectionList()
            sel.add(target_curve)
            curve_dag = sel.getDagPath(0)
            curve_dag.extendToShape()
            curve_fn = om2.MFnNurbsCurve(curve_dag)

            # Get mesh function set
            sel.clear()
            sel.add(source_mesh)
            source_dag = sel.getDagPath(0)
            source_dag.extendToShape()
            source_fn = om2.MFnMesh(source_dag)

            # Get all vertex positions
            all_points = source_fn.getPoints(om2.MSpace.kWorld)
            curve_bbox = curve_fn.boundingBox

            # Pre-filter with bounding box
            valid_indices = self._get_bbox_candidates(all_points, curve_bbox, distance)

            # Show progress for large operations
            total = len(valid_indices)
            show_progress = total > 1000

            if show_progress:
                cmds.progressWindow(title='Processing',
                                    progress=0,
                                    status=f'Checking {total} vertices...',
                                    isInterruptable=True)

            try:
                # Process filtered vertices
                for i, idx in enumerate(valid_indices):
                    point = all_points[idx]
                    # Find closest point on curve
                    closest_point, param = curve_fn.closestPoint(point, space=om2.MSpace.kWorld)

                    if point.distanceTo(closest_point) <= distance:
                        components.append(f'{source_mesh}.vtx[{idx}]')

                    # Update progress
                    if show_progress and i % 100 == 0:
                        if cmds.progressWindow(query=True, isCancelled=True):
                            break
                        progress = int((i / total) * 100)
                        cmds.progressWindow(edit=True, progress=progress)

            finally:
                if show_progress:
                    cmds.progressWindow(endProgress=1)

        except Exception as e:
            cmds.warning(f"Error: {str(e)}")

        return components

    def _curve_to_mesh(self, source_curve, target_mesh, distance):
        """
        Select CVs of source curve within distance from target mesh.
        """
        components = []

        try:
            # Get mesh function set
            sel = om2.MSelectionList()
            sel.add(target_mesh)
            mesh_dag = sel.getDagPath(0)
            mesh_dag.extendToShape()
            mesh_fn = om2.MFnMesh(mesh_dag)

            # Get curve function set
            sel.clear()
            sel.add(source_curve)
            curve_dag = sel.getDagPath(0)
            curve_dag.extendToShape()
            curve_fn = om2.MFnNurbsCurve(curve_dag)

            # Get all CV positions
            cv_positions = curve_fn.cvPositions(om2.MSpace.kWorld)
            mesh_bbox = mesh_fn.boundingBox

            # Pre-filter CVs with bounding box
            valid_indices = self._get_bbox_candidates(cv_positions, mesh_bbox, distance)

            # Process filtered CVs
            for idx in valid_indices:
                cv_pos = cv_positions[idx]
                # Find closest point on mesh
                closest_point = mesh_fn.getClosestPoint(cv_pos, space=om2.MSpace.kWorld)[0]

                if cv_pos.distanceTo(closest_point) <= distance:
                    components.append(f'{source_curve}.cv[{idx}]')

        except Exception as e:
            cmds.warning(f"Error: {str(e)}")

        return components

    def _curve_to_curve(self, source_curve, target_curve, distance):
        """
        Select CVs of source curve within distance from target curve.
        """
        components = []

        try:
            # Get target curve function set
            sel = om2.MSelectionList()
            sel.add(target_curve)
            target_dag = sel.getDagPath(0)
            target_dag.extendToShape()
            target_fn = om2.MFnNurbsCurve(target_dag)

            # Get source curve function set
            sel.clear()
            sel.add(source_curve)
            source_dag = sel.getDagPath(0)
            source_dag.extendToShape()
            source_fn = om2.MFnNurbsCurve(source_dag)

            # Get CV positions
            cv_positions = source_fn.cvPositions(om2.MSpace.kWorld)
            target_bbox = target_fn.boundingBox

            # Pre-filter with bounding box
            valid_indices = self._get_bbox_candidates(cv_positions, target_bbox, distance)

            # Process filtered CVs
            for idx in valid_indices:
                cv_pos = cv_positions[idx]
                # Find closest point on target curve
                closest_point, param = target_fn.closestPoint(cv_pos, space=om2.MSpace.kWorld)

                if cv_pos.distanceTo(closest_point) <= distance:
                    components.append(f'{source_curve}.cv[{idx}]')

        except Exception as e:
            cmds.warning(f"Error: {str(e)}")

        return components


class VertexDistanceSelectorUI:
    """
    User Interface for the Vertex Distance Selector.
    Simple window with integrated distance slider.

    Usage:
        ui = VertexDistanceSelectorUI()
        ui.show()
    """

    def __init__(self):
        """Initialize UI with default values."""
        self.window_name = "vertexDistanceSelectorWin"
        self.selector = VertexDistanceSelector()
        self.distance_value = 2.0

    def show(self):
        """
        Create and display the UI window.
        Window contains:
        - Distance slider (0.1 to 50 units)
        - Numeric field for precise input
        - Max value field to adjust slider range
        - Select button to execute operation
        """
        # Delete existing window if it exists
        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name)

        # Create new window
        window = cmds.window(
            self.window_name,
            title="Distance Selector",
            width=400,
            height=140,
            sizeable=False
        )

        # Main layout with padding
        cmds.columnLayout(adjustableColumn=True, rowSpacing=10, columnAttach=('both', 10))

        cmds.separator(height=10, style='none')

        # Distance controls row
        cmds.rowLayout(numberOfColumns=4,
                       columnWidth4=(60, 220, 60, 50),
                       columnAlign=(1, 'right'),
                       columnAttach=[(1, 'both', 5), (2, 'both', 5), (3, 'both', 5), (4, 'both', 5)])

        cmds.text(label="Distance:")

        # Distance slider
        self.distance_slider = cmds.floatSlider(
            min=0.1,
            max=50.0,
            value=self.distance_value,
            step=0.1,
            dragCommand=self.update_distance,
            changeCommand=self.update_distance
        )

        # Distance value field
        self.distance_field = cmds.floatField(
            value=self.distance_value,
            precision=2,
            width=50,
            enterCommand=self.update_from_field,
            changeCommand=self.update_from_field
        )

        # Max value field for slider range
        self.max_field = cmds.floatField(
            value=50.0,
            precision=1,
            width=40,
            enterCommand=self.update_slider_range,
            annotation="Slider max value"
        )

        cmds.setParent('..')

        cmds.separator(height=15, style='none')

        # Select button
        cmds.button(
            label="Select Close",
            height=35,
            backgroundColor=(0.3, 0.5, 0.3),
            command=self.execute_selection
        )

        # Info text for feedback
        cmds.separator(height=10, style='none')
        self.info_text = cmds.text(
            label="Select two objects and click 'Select Close'",
            height=20
        )

        cmds.setParent('..')

        # Display window
        cmds.showWindow(window)

    def update_distance(self, value):
        """Update distance value from slider movement."""
        self.distance_value = value
        cmds.floatField(self.distance_field, edit=True, value=value)

    def update_from_field(self, *args):
        """Update slider position from field value."""
        value = cmds.floatField(self.distance_field, query=True, value=True)
        self.distance_value = value

        # Expand slider range if needed
        slider_max = cmds.floatSlider(self.distance_slider, query=True, max=True)
        if value > slider_max:
            cmds.floatSlider(self.distance_slider, edit=True, max=value)

        cmds.floatSlider(self.distance_slider, edit=True, value=value)

    def update_slider_range(self, *args):
        """Update slider maximum range from max field."""
        max_value = cmds.floatField(self.max_field, query=True, value=True)
        cmds.floatSlider(self.distance_slider, edit=True, max=max_value)

    def execute_selection(self, *args):
        """
        Execute the selection operation with undo support.
        Validates selection and provides user feedback.
        """
        # Create undo chunk for the operation
        cmds.undoInfo(openChunk=True, chunkName="Distance Selection")

        try:
            # Validate selection
            selection = cmds.ls(sl=True, type='transform')

            if len(selection) < 2:
                cmds.text(self.info_text, edit=True,
                          label="Error: Select two objects first")
                return

            # Execute selection
            result = self.selector.select_by_distance(distance=self.distance_value)

            # Update feedback text
            if result:
                source_type = self.selector.detect_type(selection[0])
                target_type = self.selector.detect_type(selection[1])
                cmds.text(self.info_text, edit=True,
                          label=f"Selected {len(result)} components ({source_type} → {target_type})")
            else:
                cmds.text(self.info_text, edit=True,
                          label="No components found within distance")

        finally:
            # Close undo chunk
            cmds.undoInfo(closeChunk=True)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def show():
    """
    Show the UI window.

    Example:
        import vertex_distance_selector as vds
        vds.show()
    """
    ui = VertexDistanceSelectorUI()
    ui.show()


def select_near(distance=2.0):
    """
    Direct selection function for script use.
    Uses current selection as source and target.

    Args:
        distance (float): Maximum distance for selection

    Returns:
        list: Selected component names

    Example:
        # Select vertices within 3 units
        result = select_near(distance=3.0)
        print(f"Selected {len(result)} components")
    """
    selector = VertexDistanceSelector()
    return selector.select_by_distance(distance=distance)





# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    """
    Main execution when script is run directly.
    Shows the UI window.
    """
    show()
