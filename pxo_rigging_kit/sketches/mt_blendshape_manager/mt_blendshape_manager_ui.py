"""
MT BlendShape Manager UI
Maya-native interface with hierarchical layer support
"""

import maya.cmds as cmds
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
try:
    from PySide6 import QtCore
    from PySide6 import QtGui
    from PySide6 import QtWidgets
except ImportError:
    from PySide2 import QtCore
    from PySide2 import QtGui
    from PySide2 import QtWidgets

import traceback
from .mt_blendshape_manager import BlendShapeManager


class BlendShapeManagerUI(MayaQWidgetDockableMixin, QtWidgets.QDialog):
    """Maya-native UI for BlendShape Manager."""

    WINDOW_NAME = "MTBlendShapeManagerWindow"
    WINDOW_TITLE = "MT BlendShape Manager"

    def __init__(self, parent=None):
        """Initialize the UI."""
        super(BlendShapeManagerUI, self).__init__(parent)

        # Core manager
        self.manager = BlendShapeManager()

        # UI state
        self.current_mesh = None
        self.current_bs = None

        # Auto-refresh timer
        self.refresh_timer = QtCore.QTimer()
        self.refresh_timer.timeout.connect(self.auto_refresh_weights)
        self.refresh_rate = 100  # Default 100ms refresh rate
        self.auto_refresh_enabled = False

        # Track last weight values to optimize refresh
        self.last_weight_values = {}

        # Setup UI
        self.setObjectName(self.WINDOW_NAME)
        self.setWindowTitle(self.WINDOW_TITLE)
        self.setMinimumWidth(500)
        self.setMinimumHeight(700)

        self.create_widgets()
        self.create_layout()
        self.create_connections()

        # Initial setup - auto-populate from selection
        self.refresh_from_selection()

        # If we have a mesh, auto-detect layers
        if self.current_mesh:
            self.refresh_all()

    def get_maya_icon(self, icon_name):
        """Get Maya's built-in icon."""
        import os

        # Try Maya's resource path
        if not icon_name.startswith(":"):
            icon_name = f":/{icon_name}"

        return QtGui.QIcon(icon_name)

    def create_widgets(self):
        """Create all UI widgets."""

        # === Mesh Selection (Selection-based only) ===
        self.mesh_label = QtWidgets.QLabel("Selected Mesh:")
        self.mesh_field = QtWidgets.QLineEdit()
        self.mesh_field.setReadOnly(True)
        self.mesh_field.setPlaceholderText("No mesh selected")

        self.get_mesh_btn = QtWidgets.QPushButton("Get From Selection")
        self.get_mesh_btn.setIcon(self.get_maya_icon("selectByObject.png"))

        self.refresh_btn = QtWidgets.QPushButton("Refresh")
        self.refresh_btn.setIcon(self.get_maya_icon("refresh.png"))

        # === BlendShape Selection ===
        self.bs_label = QtWidgets.QLabel("BlendShape:")
        self.bs_combo = QtWidgets.QComboBox()
        self.bs_create_btn = QtWidgets.QPushButton("Create New")
        self.bs_create_btn.setIcon(self.get_maya_icon("blendShape.png"))

        # === Search and Filter Bar ===
        self.search_field = QtWidgets.QLineEdit()
        self.search_field.setPlaceholderText("Search targets...")
        self.search_field.setClearButtonEnabled(True)

        self.show_active_cb = QtWidgets.QCheckBox("Active Only")
        self.show_active_cb.setToolTip("Show only targets with weight >= 0.01")

        # === Auto-Refresh Controls ===
        self.auto_refresh_cb = QtWidgets.QCheckBox("Auto-Refresh")
        self.auto_refresh_cb.setToolTip("Automatically refresh weights in real-time")

        self.refresh_rate_label = QtWidgets.QLabel("Rate (ms):")
        self.refresh_rate_spin = QtWidgets.QSpinBox()
        self.refresh_rate_spin.setMinimum(10)
        self.refresh_rate_spin.setMaximum(5000)
        self.refresh_rate_spin.setValue(100)
        self.refresh_rate_spin.setSuffix(" ms")
        self.refresh_rate_spin.setToolTip("Refresh interval in milliseconds")

        # === Target List with Sortable Columns ===
        self.target_tree = QtWidgets.QTreeWidget()
        self.target_tree.setHeaderLabels(["Name", "Weight"])
        self.target_tree.setSortingEnabled(False)  # We'll handle sorting manually
        self.target_tree.setAlternatingRowColors(True)
        self.target_tree.setRootIsDecorated(True)  # Allow tree expansion for layers
        self.target_tree.setSelectionMode(QtWidgets.QTreeWidget.ExtendedSelection)

        # Configure columns
        header = self.target_tree.header()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Interactive)  # Name column resizable
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        header.resizeSection(0, 200)  # Default width for Name
        header.resizeSection(1, 150)  # Width for Weight slider

        # Context menu
        self.target_tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        # === Operation Tabs ===
        self.operation_tabs = QtWidgets.QTabWidget()

        # Target Operations Tab
        self.target_ops_widget = QtWidgets.QWidget()
        target_ops_layout = QtWidgets.QGridLayout(self.target_ops_widget)
        target_ops_layout.setSpacing(2)

        self.add_target_btn = QtWidgets.QPushButton("Add Empty Layer")
        self.add_target_btn.setIcon(self.get_maya_icon("addClip.png"))
        self.delete_btn = QtWidgets.QPushButton("Delete")
        self.delete_btn.setIcon(self.get_maya_icon("delete.png"))
        self.rename_btn = QtWidgets.QPushButton("Rename")
        self.rename_btn.setIcon(self.get_maya_icon("renamePreset.png"))
        self.duplicate_btn = QtWidgets.QPushButton("Duplicate")
        self.duplicate_btn.setIcon(self.get_maya_icon("duplicatePreset.png"))
        self.extract_btn = QtWidgets.QPushButton("Extract")
        self.extract_btn.setIcon(self.get_maya_icon("polyDuplicateFacet.png"))

        target_ops_layout.addWidget(self.add_target_btn, 0, 0)
        target_ops_layout.addWidget(self.delete_btn, 0, 1)
        target_ops_layout.addWidget(self.rename_btn, 0, 2)
        target_ops_layout.addWidget(self.duplicate_btn, 1, 0)
        target_ops_layout.addWidget(self.extract_btn, 1, 1, 1, 2)

        self.operation_tabs.addTab(self.target_ops_widget, "Target")

        # Delta Operations Tab
        self.delta_ops_widget = QtWidgets.QWidget()
        delta_ops_layout = QtWidgets.QGridLayout(self.delta_ops_widget)
        delta_ops_layout.setSpacing(2)

        self.copy_delta_btn = QtWidgets.QPushButton("Copy Delta")
        self.copy_delta_btn.setIcon(self.get_maya_icon("polyCopyUV.png"))
        self.paste_replace_btn = QtWidgets.QPushButton("Paste Replace")
        self.paste_replace_btn.setIcon(self.get_maya_icon("polyPasteUV.png"))
        self.paste_add_btn = QtWidgets.QPushButton("Paste Add")
        self.paste_add_btn.setIcon(self.get_maya_icon("polyMapSewMove.png"))
        self.zero_deltas_btn = QtWidgets.QPushButton("Zero Deltas")
        self.zero_deltas_btn.setIcon(self.get_maya_icon("hyper_s_OFF.png"))
        self.keep_selected_btn = QtWidgets.QPushButton("Keep Selected")
        self.keep_selected_btn.setIcon(self.get_maya_icon("polySelectEditCtxt.png"))
        self.keep_selected_btn.setToolTip("Keep only selected vertices")

        delta_ops_layout.addWidget(self.copy_delta_btn, 0, 0)
        delta_ops_layout.addWidget(self.paste_replace_btn, 0, 1)
        delta_ops_layout.addWidget(self.paste_add_btn, 1, 0)
        delta_ops_layout.addWidget(self.zero_deltas_btn, 1, 1)
        delta_ops_layout.addWidget(self.keep_selected_btn, 2, 0, 1, 2)

        self.operation_tabs.addTab(self.delta_ops_widget, "Delta")

        # Weight Operations Tab
        self.weight_ops_widget = QtWidgets.QWidget()
        weight_ops_layout = QtWidgets.QGridLayout(self.weight_ops_widget)
        weight_ops_layout.setSpacing(2)

        self.zero_weights_btn = QtWidgets.QPushButton("Zero All Weights")
        self.zero_weights_btn.setIcon(self.get_maya_icon("hyper_s_OFF.png"))
        self.solo_btn = QtWidgets.QPushButton("Solo Target")
        self.solo_btn.setIcon(self.get_maya_icon("visible.png"))

        weight_ops_layout.addWidget(self.zero_weights_btn, 0, 0)
        weight_ops_layout.addWidget(self.solo_btn, 0, 1)

        self.operation_tabs.addTab(self.weight_ops_widget, "Weight")

        # Advanced Operations Tab
        self.advanced_ops_widget = QtWidgets.QWidget()
        advanced_ops_layout = QtWidgets.QGridLayout(self.advanced_ops_widget)
        advanced_ops_layout.setSpacing(2)

        self.mirror_target_btn = QtWidgets.QPushButton("Mirror Target")
        self.mirror_target_btn.setIcon(self.get_maya_icon("polyMirrorGeometry.png"))
        self.swap_mesh_btn = QtWidgets.QPushButton("Swap Mesh")
        self.swap_mesh_btn.setIcon(self.get_maya_icon("polySwapEdge.png"))
        self.bake_deformer_btn = QtWidgets.QPushButton("Bake Deformers")
        self.bake_deformer_btn.setIcon(self.get_maya_icon("bakeAnimation.png"))

        advanced_ops_layout.addWidget(self.mirror_target_btn, 0, 0)
        advanced_ops_layout.addWidget(self.swap_mesh_btn, 0, 1)
        advanced_ops_layout.addWidget(self.bake_deformer_btn, 1, 0, 1, 2)

        self.operation_tabs.addTab(self.advanced_ops_widget, "Advanced")

        # Layer Operations Tab - NEW SIMPLIFIED SYSTEM
        self.layer_ops_widget = QtWidgets.QWidget()
        layer_ops_layout = QtWidgets.QGridLayout(self.layer_ops_widget)
        layer_ops_layout.setSpacing(2)

        self.create_layer_btn = QtWidgets.QPushButton("Create Layer")
        self.create_layer_btn.setIcon(self.get_maya_icon("layerEditor.png"))
        self.create_layer_btn.setToolTip("Add empty target layer to selected target")

        self.merge_layers_btn = QtWidgets.QPushButton("Merge Layers")
        self.merge_layers_btn.setIcon(self.get_maya_icon("polyMergeToCenter.png"))
        self.merge_layers_btn.setToolTip("Merge all layers into master target")

        self.list_layers_btn = QtWidgets.QPushButton("List Layers")
        self.list_layers_btn.setIcon(self.get_maya_icon("list.png"))
        self.list_layers_btn.setToolTip("List all layers for selected target")

        layer_ops_layout.addWidget(self.create_layer_btn, 0, 0)
        layer_ops_layout.addWidget(self.merge_layers_btn, 0, 1)
        layer_ops_layout.addWidget(self.list_layers_btn, 1, 0, 1, 2)

        # Add info label
        info_label = QtWidgets.QLabel(
            "New simplified layer system uses empty targets directly in master blendshape.\n"
            "Layers are auto-activated when master target is activated."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("QLabel { color: #888; font-size: 10px; }")
        layer_ops_layout.addWidget(info_label, 2, 0, 1, 2)

        self.operation_tabs.addTab(self.layer_ops_widget, "Layers")

        # File Operations Tab
        self.file_ops_widget = QtWidgets.QWidget()
        file_ops_layout = QtWidgets.QGridLayout(self.file_ops_widget)
        file_ops_layout.setSpacing(2)

        self.export_btn = QtWidgets.QPushButton("Export Deltas")
        self.export_btn.setIcon(self.get_maya_icon("save.png"))
        self.import_btn = QtWidgets.QPushButton("Import Deltas")
        self.import_btn.setIcon(self.get_maya_icon("open.png"))

        file_ops_layout.addWidget(self.export_btn, 0, 0)
        file_ops_layout.addWidget(self.import_btn, 0, 1)

        self.operation_tabs.addTab(self.file_ops_widget, "File")

        # Status bar
        self.status_label = QtWidgets.QLabel("Ready")
        self.status_label.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Sunken)

    def create_layout(self):
        """Create the main UI layout."""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(4)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # === Mesh Selection Section ===
        mesh_layout = QtWidgets.QHBoxLayout()
        mesh_layout.addWidget(self.mesh_label)
        mesh_layout.addWidget(self.mesh_field, 1)
        mesh_layout.addWidget(self.get_mesh_btn)
        mesh_layout.addWidget(self.refresh_btn)
        main_layout.addLayout(mesh_layout)

        # === BlendShape Selection Section ===
        bs_layout = QtWidgets.QHBoxLayout()
        bs_layout.addWidget(self.bs_label)
        bs_layout.addWidget(self.bs_combo, 1)
        bs_layout.addWidget(self.bs_create_btn)
        main_layout.addLayout(bs_layout)

        # === Search and Filter Bar ===
        filter_layout = QtWidgets.QHBoxLayout()
        filter_layout.addWidget(QtWidgets.QLabel("Filter:"))
        filter_layout.addWidget(self.search_field, 1)
        filter_layout.addWidget(self.show_active_cb)

        # Add sort options
        self.sort_label = QtWidgets.QLabel("Sort:")
        self.sort_combo = QtWidgets.QComboBox()
        self.sort_combo.addItems(["Name ↑", "Name ↓", "Weight ↑", "Weight ↓"])
        self.sort_combo.setMaximumWidth(100)
        filter_layout.addWidget(self.sort_label)
        filter_layout.addWidget(self.sort_combo)

        main_layout.addLayout(filter_layout)

        # === Auto-Refresh Bar ===
        refresh_layout = QtWidgets.QHBoxLayout()
        refresh_layout.addWidget(self.auto_refresh_cb)
        refresh_layout.addWidget(self.refresh_rate_label)
        refresh_layout.addWidget(self.refresh_rate_spin)
        refresh_layout.addStretch()
        main_layout.addLayout(refresh_layout)

        # === Target List ===
        main_layout.addWidget(QtWidgets.QLabel("Targets:"))
        main_layout.addWidget(self.target_tree, 1)  # Stretch factor 1

        # === Operation Tabs ===
        main_layout.addWidget(self.operation_tabs)

        # === Status Bar ===
        main_layout.addWidget(self.status_label)

    def create_connections(self):
        """Create signal connections."""
        # Selection
        self.get_mesh_btn.clicked.connect(self.get_mesh_from_selection)
        self.refresh_btn.clicked.connect(self.refresh_all)
        self.bs_combo.currentTextChanged.connect(self.on_blendshape_changed)
        self.bs_create_btn.clicked.connect(self.create_blendshape)

        # Search and filter
        self.search_field.textChanged.connect(self.refresh_target_list)
        self.show_active_cb.stateChanged.connect(self.refresh_target_list)
        self.sort_combo.currentTextChanged.connect(self.refresh_target_list)

        # Auto-refresh connections
        self.auto_refresh_cb.stateChanged.connect(self.toggle_auto_refresh)
        self.refresh_rate_spin.valueChanged.connect(self.update_refresh_rate)

        # Target operations
        self.add_target_btn.clicked.connect(self.add_target)
        self.delete_btn.clicked.connect(self.delete_target)
        self.rename_btn.clicked.connect(self.rename_target)
        self.duplicate_btn.clicked.connect(self.duplicate_target)
        self.extract_btn.clicked.connect(self.extract_target)

        # Delta operations
        self.copy_delta_btn.clicked.connect(self.copy_delta)
        self.paste_replace_btn.clicked.connect(self.paste_replace)
        self.paste_add_btn.clicked.connect(self.paste_add)
        self.zero_deltas_btn.clicked.connect(self.zero_deltas)
        self.keep_selected_btn.clicked.connect(self.keep_selected_vertices)

        # Weight operations
        self.zero_weights_btn.clicked.connect(self.zero_all_weights)
        self.solo_btn.clicked.connect(self.solo_target)

        # Advanced operations
        self.mirror_target_btn.clicked.connect(self.mirror_target)
        self.swap_mesh_btn.clicked.connect(self.swap_mesh_to_target)
        self.bake_deformer_btn.clicked.connect(self.bake_deformer)

        # Layer operations
        self.create_layer_btn.clicked.connect(self.create_layer)
        self.merge_layers_btn.clicked.connect(self.merge_layers)
        self.list_layers_btn.clicked.connect(self.list_layers)

        # File operations
        self.export_btn.clicked.connect(self.export_deltas)
        self.import_btn.clicked.connect(self.import_deltas)

        # Target list
        self.target_tree.itemSelectionChanged.connect(self.on_target_selection_changed)
        self.target_tree.itemDoubleClicked.connect(self.on_target_double_clicked)
        self.target_tree.customContextMenuRequested.connect(self.show_context_menu)

    # === Helper Methods ===

    def set_status(self, message):
        """Update status bar."""
        self.status_label.setText(message)
        # Auto-clear after 5 seconds
        def clear_status():
            try:
                if self.status_label:
                    self.status_label.setText("Ready")
            except:
                pass
        QtCore.QTimer.singleShot(5000, clear_status)

    def get_selected_targets(self):
        """Get list of selected target names."""
        targets = []
        for item in self.target_tree.selectedItems():
            targets.append(item.text(0))
        return targets

    def refresh_from_selection(self):
        """Refresh UI from current selection."""
        selection = cmds.ls(selection=True, transforms=True)
        if selection:
            mesh = selection[0]
            shapes = cmds.listRelatives(mesh, shapes=True, type='mesh')
            if shapes:
                self.get_mesh_from_selection()

    def refresh_all(self):
        """Refresh all UI elements."""
        # Refresh blendshape list if mesh is set
        if self.current_mesh:
            self.refresh_blendshape_list()

        # Refresh target list if blendshape is set
        if self.current_bs:
            self.refresh_target_list()

        self.set_status("Refreshed")

    def get_mesh_from_selection(self):
        """Get mesh from current Maya selection."""
        selection = cmds.ls(selection=True, transforms=True)
        if not selection:
            self.set_status("Please select a mesh")
            return

        mesh = selection[0]

        # Verify it's a mesh
        shapes = cmds.listRelatives(mesh, shapes=True, type='mesh')
        if not shapes:
            self.set_status("Selected object is not a mesh")
            return

        self.current_mesh = mesh
        self.mesh_field.setText(mesh)

        # Update manager
        self.manager.set_mesh(mesh)

        # Refresh blendshapes
        self.refresh_blendshape_list()

        self.set_status(f"Mesh set to: {mesh}")

    def refresh_blendshape_list(self):
        """Refresh the blendshape combo box."""
        self.bs_combo.clear()

        if not self.current_mesh:
            return

        # Get blendshapes from history
        history = cmds.listHistory(self.current_mesh, pruneDagObjects=True) or []
        blendshapes = [node for node in history if cmds.nodeType(node) == 'blendShape']

        if blendshapes:
            self.bs_combo.addItems(blendshapes)
            self.current_bs = blendshapes[0]
            self.manager.set_blendshape(self.current_bs)
            self.refresh_target_list()

    def on_blendshape_changed(self, bs_name):
        """Handle blendshape selection change."""
        if bs_name:
            self.current_bs = bs_name
            self.manager.set_blendshape(bs_name)
            self.refresh_target_list()

    def detect_layer_relationships(self):
        """Detect parent-child relationships between targets and layers.

        Returns:
            dict: Map of blendshape to its layer blendshapes for each target
        """
        relationships = {}

        if not self.current_mesh:
            return relationships

        # Get all blendshapes in history
        history = cmds.listHistory(self.current_mesh, pruneDagObjects=True) or []
        all_blendshapes = [node for node in history if cmds.nodeType(node) == 'blendShape']

        # For each non-layer blendshape, find its layer blendshapes
        for bs in all_blendshapes:
            # Skip if this is itself a layer blendshape
            if bs.endswith('_layers_bs'):
                continue

            relationships[bs] = {}

            # Get targets in this blendshape
            try:
                targets = cmds.listAttr(f"{bs}.weight", multi=True) or []

                # For each target, look for its layer blendshape
                for target in targets:
                    layer_bs_name = f"{target}_layers_bs"
                    if layer_bs_name in all_blendshapes:
                        relationships[bs][target] = layer_bs_name
            except:
                pass

        return relationships

    def refresh_target_list(self):
        """Refresh the target list with layer hierarchy."""
        self.target_tree.clear()

        if not self.current_bs:
            return

        # Get filter settings
        search_text = self.search_field.text().lower()
        active_only = self.show_active_cb.isChecked()
        sort_option = self.sort_combo.currentText() if hasattr(self, 'sort_combo') else "Name ↑"

        # Get layer relationships
        layer_relationships = self.detect_layer_relationships()

        # Get targets from current blendshape
        targets = self.manager.get_targets(include_layers=False)

        # Convert to list for sorting
        target_list = []
        for name, info in targets.items():
            # Apply filters
            if search_text and search_text not in name.lower():
                continue

            if active_only and info['weight'] < 0.01:  # Changed to 0.01
                continue

            target_list.append((name, info))

        # Sort the list
        if "Name ↑" in sort_option:
            target_list.sort(key=lambda x: x[0].lower())
        elif "Name ↓" in sort_option:
            target_list.sort(key=lambda x: x[0].lower(), reverse=True)
        elif "Weight ↑" in sort_option:
            target_list.sort(key=lambda x: x[1]['weight'])
        elif "Weight ↓" in sort_option:
            target_list.sort(key=lambda x: x[1]['weight'], reverse=True)

        # Add sorted targets to tree
        for name, info in target_list:
            # Create main target item
            item = QtWidgets.QTreeWidgetItem()
            item.setText(0, name)
            # Store weight as data for proper sorting
            item.setData(1, QtCore.Qt.UserRole, info['weight'])

            # Add weight slider widget
            weight_widget = self.create_weight_widget(name, info['weight'], self.current_bs)

            self.target_tree.addTopLevelItem(item)
            self.target_tree.setItemWidget(item, 1, weight_widget)

            # Check if this target has a layer blendshape
            if (self.current_bs in layer_relationships and
                name in layer_relationships[self.current_bs]):
                layer_bs = layer_relationships[self.current_bs][name]
                # Add layer blendshape targets as children
                self.add_layer_children(item, layer_bs, name, search_text, active_only)

    def add_layer_children(self, parent_item, layer_bs, parent_target_name, search_text, active_only):
        """Add layer targets as children of the main target.

        Args:
            parent_item: Parent tree item
            layer_bs: Layer blendshape node
            parent_target_name: Name of parent target
            search_text: Search filter
            active_only: Show only active targets
        """
        # Get targets from layer blendshape
        try:
            layer_targets = cmds.listAttr(f"{layer_bs}.weight", multi=True) or []

            for layer_target in layer_targets:
                # Get weight
                weight = cmds.getAttr(f"{layer_bs}.{layer_target}")

                # Apply filters
                if search_text and search_text not in layer_target.lower():
                    continue

                if active_only and weight < 0.01:  # Changed to 0.01
                    continue

                # Get index
                index = cmds.getAttr(f"{layer_bs}.{layer_target}", multiIndices=True)
                if index:
                    index = index[0]
                else:
                    index = 0

                # Create child item
                child_item = QtWidgets.QTreeWidgetItem(parent_item)
                # Show layer name with "L" prefix for clarity
                display_name = f"L{layer_target}" if layer_target.isdigit() else layer_target
                child_item.setText(0, display_name)
                # Store weight as data
                child_item.setData(1, QtCore.Qt.UserRole, weight)

                # Add weight slider for layer
                weight_widget = self.create_weight_widget(layer_target, weight, layer_bs)
                self.target_tree.setItemWidget(child_item, 1, weight_widget)

        except Exception as e:
            print(f"Error adding layer children from {layer_bs}: {e}")

    def create_weight_widget(self, target_name, weight, blendshape_node):
        """Create weight slider widget.

        Args:
            target_name: Name of the target
            weight: Current weight value
            blendshape_node: BlendShape node name

        Returns:
            QWidget: Weight control widget
        """
        weight_widget = QtWidgets.QWidget()
        weight_layout = QtWidgets.QHBoxLayout(weight_widget)
        weight_layout.setContentsMargins(2, 0, 2, 0)

        # Weight value label
        weight_label = QtWidgets.QLabel(f"{weight:.3f}")
        weight_label.setMinimumWidth(45)

        # Weight slider
        slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        slider.setRange(0, 1000)
        slider.setValue(int(weight * 1000))
        slider.valueChanged.connect(
            lambda v, n=target_name, l=weight_label, bs=blendshape_node:
            self.on_weight_changed_for_bs(n, v, l, bs)
        )

        weight_layout.addWidget(weight_label)
        weight_layout.addWidget(slider)

        return weight_widget

    def on_weight_changed_for_bs(self, target_name, value, label, blendshape_node):
        """Handle weight slider change for specific blendshape.

        Args:
            target_name: Target name
            value: Slider value (0-1000)
            label: Label to update
            blendshape_node: BlendShape node
        """
        weight = value / 1000.0
        if blendshape_node:
            cmds.setAttr(f"{blendshape_node}.{target_name}", weight)
            label.setText(f"{weight:.3f}")

    def on_weight_changed(self, target_name, value, label):
        """Handle weight slider change."""
        weight = value / 1000.0
        if self.current_bs:
            cmds.setAttr(f"{self.current_bs}.{target_name}", weight)
            label.setText(f"{weight:.3f}")

    def on_target_selection_changed(self):
        """Handle target selection change."""
        pass  # Can be used for updating info display

    def on_target_double_clicked(self, item, column):
        """Handle double-click on target."""
        if column == 0:
            # Edit target name
            self.rename_target()
        elif column == 1:
            # Set weight to 1.0
            target_name = item.text(0)
            cmds.setAttr(f"{self.current_bs}.{target_name}", 1.0)
            self.refresh_target_list()

    def show_context_menu(self, position):
        """Show context menu for target list."""
        menu = QtWidgets.QMenu()

        # Add actions
        menu.addAction(self.get_maya_icon("visible.png"), "Solo", self.solo_target)
        menu.addAction(self.get_maya_icon("hyper_s_OFF.png"), "Zero Weight", self.zero_selected_weights)
        menu.addSeparator()
        menu.addAction(self.get_maya_icon("polyCopyUV.png"), "Copy Delta", self.copy_delta)
        menu.addAction(self.get_maya_icon("polyPasteUV.png"), "Paste Replace", self.paste_replace)
        menu.addSeparator()
        menu.addAction(self.get_maya_icon("delete.png"), "Delete", self.delete_target)

        menu.exec_(self.target_tree.mapToGlobal(position))

    # === Operation Methods ===

    def create_blendshape(self):
        """Create new blendshape."""
        if not self.current_mesh:
            self.set_status("Please select a mesh first")
            return

        name, ok = QtWidgets.QInputDialog.getText(
            self, "Create BlendShape", "Enter name:",
            text=f"{self.current_mesh}_blendShape"
        )

        if ok and name:
            bs = cmds.blendShape(self.current_mesh, name=name)[0]
            self.refresh_blendshape_list()
            self.bs_combo.setCurrentText(bs)
            self.set_status(f"Created blendshape: {bs}")

    def add_target(self):
        """Add empty target to current blendshape."""
        if not self.current_bs:
            self.set_status("No blendshape selected")
            return

        # Get selected targets to create empty layers for them
        selected_targets = self.get_selected_targets()
        if not selected_targets:
            self.set_status("Please select a target to add empty layer")
            return

        try:
            from mt_blendshape_manager.mt_blendshape_manager_utils import add_empty_target
        except ImportError:
            try:
                from pxo_rigging_kit.sketches.mt_blendshape_manager.mt_blendshape_manager_utils import add_empty_target
            except ImportError:
                from .mt_blendshape_manager_utils import add_empty_target

        cmds.undoInfo(openChunk=True, chunkName='Add Empty Target')
        try:
            for target_name in selected_targets:
                # Create layer name based on target
                layer_name = f"{target_name}_layer_1"

                # Check for existing layers and increment number
                existing_attrs = cmds.listAttr(f"{self.current_bs}.weight", multi=True) or []
                layer_num = 1
                while layer_name in existing_attrs:
                    layer_num += 1
                    layer_name = f"{target_name}_layer_{layer_num}"

                # Add empty target
                index = add_empty_target(self.current_bs, layer_name, self.manager.mesh)
                if index is not None:
                    self.set_status(f"Added empty layer: {layer_name}")
        except Exception as e:
            self.set_status(f"Error: {str(e)}")
        finally:
            cmds.undoInfo(closeChunk=True)

        self.refresh_target_list()

    def delete_target(self):
        """Delete selected targets."""
        targets = self.get_selected_targets()
        if not targets:
            self.set_status("No targets selected")
            return

        cmds.undoInfo(openChunk=True, chunkName='Delete Targets')
        try:
            for target in targets:
                self.manager.delete_target(target)
            self.set_status(f"Deleted {len(targets)} target(s)")
        finally:
            cmds.undoInfo(closeChunk=True)

        self.refresh_target_list()

    def rename_target(self):
        """Rename selected target."""
        targets = self.get_selected_targets()
        if not targets:
            self.set_status("No target selected")
            return

        old_name = targets[0]
        new_name, ok = QtWidgets.QInputDialog.getText(
            self, "Rename Target", "New name:", text=old_name
        )

        if ok and new_name and new_name != old_name:
            if self.manager.rename_target(old_name, new_name):
                self.refresh_target_list()
                self.set_status(f"Renamed '{old_name}' to '{new_name}'")

    def duplicate_target(self):
        """Duplicate selected targets."""
        targets = self.get_selected_targets()
        if not targets:
            self.set_status("No targets selected")
            return

        cmds.undoInfo(openChunk=True, chunkName='Duplicate Targets')
        try:
            for target in targets:
                new_name = self.manager.duplicate_target(target)
                if new_name:
                    self.set_status(f"Duplicated '{target}' as '{new_name}'")
        finally:
            cmds.undoInfo(closeChunk=True)

        self.refresh_target_list()

    def extract_target(self):
        """Extract selected targets as meshes."""
        targets = self.get_selected_targets()
        if not targets:
            self.set_status("No targets selected")
            return

        extracted = []
        for target in targets:
            mesh = self.manager.extract_target(target)
            if mesh:
                extracted.append(mesh)

        if extracted:
            cmds.select(extracted)
            self.set_status(f"Extracted {len(extracted)} target(s)")

    def copy_delta(self):
        """Copy deltas from selected target."""
        targets = self.get_selected_targets()
        if not targets:
            self.set_status("No target selected")
            return

        cmds.undoInfo(openChunk=True, chunkName='Copy Delta')
        try:
            self.manager.copy_delta(targets[0])
            self.set_status(f"Copied deltas from '{targets[0]}'")
        finally:
            cmds.undoInfo(closeChunk=True)

    def paste_replace(self):
        """Paste and replace target deltas."""
        targets = self.get_selected_targets()
        if not targets:
            self.set_status("No target selected")
            return

        cmds.undoInfo(openChunk=True, chunkName='Paste Replace')
        try:
            for target in targets:
                if self.manager.paste_delta_replace(target):
                    self.set_status(f"Replaced deltas for '{target}'")
        finally:
            cmds.undoInfo(closeChunk=True)

        self.refresh_target_list()

    def paste_add(self):
        """Paste and add to target deltas."""
        targets = self.get_selected_targets()
        if not targets:
            self.set_status("No target selected")
            return

        cmds.undoInfo(openChunk=True, chunkName='Paste Add')
        try:
            for target in targets:
                if self.manager.paste_delta_add(target):
                    self.set_status(f"Added deltas to '{target}'")
        finally:
            cmds.undoInfo(closeChunk=True)

        self.refresh_target_list()

    def zero_deltas(self):
        """Zero deltas for selected targets."""
        targets = self.get_selected_targets()
        if not targets:
            self.set_status("No targets selected")
            return

        cmds.undoInfo(openChunk=True, chunkName='Zero Deltas')
        try:
            for target in targets:
                self.manager.zero_all_deltas(target)
            self.set_status(f"Zeroed deltas for {len(targets)} target(s)")
        finally:
            cmds.undoInfo(closeChunk=True)

        self.refresh_target_list()

    def zero_all_weights(self):
        """Zero all target weights."""
        if not self.current_bs:
            self.set_status("No blendshape selected")
            return

        cmds.undoInfo(openChunk=True, chunkName='Zero All Weights')
        try:
            self.manager.zero_all_weights()
            self.refresh_target_list()
            self.set_status("Zeroed all weights")
        finally:
            cmds.undoInfo(closeChunk=True)

    def zero_selected_weights(self):
        """Zero weights for selected targets."""
        targets = self.get_selected_targets()
        if not targets:
            return

        cmds.undoInfo(openChunk=True, chunkName='Zero Selected Weights')
        try:
            for target in targets:
                cmds.setAttr(f"{self.current_bs}.{target}", 0)
            self.refresh_target_list()
        finally:
            cmds.undoInfo(closeChunk=True)

    def solo_target(self):
        """Solo selected target."""
        targets = self.get_selected_targets()
        if not targets:
            self.set_status("No target selected")
            return

        cmds.undoInfo(openChunk=True, chunkName='Solo Target')
        try:
            self.manager.solo_target(targets[0])
            self.refresh_target_list()
            self.set_status(f"Solo: {targets[0]}")
        finally:
            cmds.undoInfo(closeChunk=True)

    def keep_selected_vertices(self):
        """Keep only selected vertices in target."""
        targets = self.get_selected_targets()
        if not targets:
            self.set_status("No target selected")
            return

        cmds.undoInfo(openChunk=True, chunkName='Keep Selected Vertices')
        try:
            for target in targets:
                if self.manager.keep_selected_vertices(target):
                    self.set_status(f"Kept selected vertices for '{target}'")
        finally:
            cmds.undoInfo(closeChunk=True)

    def mirror_target(self):
        """Mirror selected target."""
        targets = self.get_selected_targets()
        if not targets:
            self.set_status("No target selected")
            return

        cmds.undoInfo(openChunk=True, chunkName='Mirror Target')
        try:
            for target in targets:
                new_target = self.manager.mirror_target(target)
                if new_target:
                    self.set_status(f"Mirrored '{target}' to '{new_target}'")
        finally:
            cmds.undoInfo(closeChunk=True)

        self.refresh_target_list()

    def swap_mesh_to_target(self):
        """Swap selected mesh to target."""
        targets = self.get_selected_targets()
        if not targets:
            self.set_status("No target selected")
            return

        selection = cmds.ls(selection=True, transforms=True)
        if not selection:
            self.set_status("Select a source mesh")
            return

        # Filter out the main mesh
        source_meshes = [m for m in selection if m != self.current_mesh]
        if not source_meshes:
            self.set_status("Select a source mesh different from the base mesh")
            return

        source_mesh = source_meshes[0]

        cmds.undoInfo(openChunk=True, chunkName='Swap Mesh to Target')
        try:
            for target in targets:
                if self.manager.swap_mesh_to_target(target, source_mesh):
                    self.set_status(f"Swapped mesh to '{target}'")
        finally:
            cmds.undoInfo(closeChunk=True)

    def bake_deformer(self):
        """Bake deformers to selected target."""
        targets = self.get_selected_targets()
        if not targets:
            self.set_status("No target selected")
            return

        cmds.undoInfo(openChunk=True, chunkName='Bake Deformers')
        try:
            for target in targets:
                if self.manager.bake_deformer(target):
                    self.set_status(f"Baked deformers to '{target}'")
        finally:
            cmds.undoInfo(closeChunk=True)

        self.refresh_target_list()

    def create_layer(self):
        """Create layer for selected target."""
        targets = self.get_selected_targets()
        if not targets:
            self.set_status("No target selected")
            return

        cmds.undoInfo(openChunk=True, chunkName='Create Layer')
        try:
            for target in targets:
                layer_name = self.manager.create_layer(target)
                if layer_name:
                    self.set_status(f"Created layer: {layer_name}")
        finally:
            cmds.undoInfo(closeChunk=True)

    def merge_layers(self):
        """Merge layers for selected target."""
        targets = self.get_selected_targets()
        if not targets:
            self.set_status("No target selected")
            return

        cmds.undoInfo(openChunk=True, chunkName='Merge Layers')
        try:
            for target in targets:
                if self.manager.merge_layers(target):
                    self.set_status(f"Merged layers for '{target}'")
        finally:
            cmds.undoInfo(closeChunk=True)

        self.refresh_target_list()

    def list_layers(self):
        """List layers for selected target."""
        targets = self.get_selected_targets()
        if not targets:
            self.set_status("No target selected")
            return

        for target in targets:
            layers = self.manager.list_layers(target)
            if layers:
                print(f"Layers for '{target}':")
                for layer in layers:
                    print(f"  - {layer}")
            else:
                print(f"No layers for '{target}'")

    def export_deltas(self):
        """Export deltas to file."""
        targets = self.get_selected_targets()

        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Deltas", "", "JSON Files (*.json)"
        )

        if not file_path:
            return

        # TODO: Implement export functionality
        self.set_status("Export functionality not yet implemented")

    def import_deltas(self):
        """Import deltas from file."""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Import Deltas", "", "JSON Files (*.json)"
        )

        if not file_path:
            return

        # TODO: Implement import functionality
        self.set_status("Import functionality not yet implemented")

    def toggle_auto_refresh(self, state):
        """Toggle auto-refresh on/off."""
        self.auto_refresh_enabled = state == QtCore.Qt.Checked

        if self.auto_refresh_enabled:
            self.refresh_timer.start(self.refresh_rate)
            self.set_status(f"Auto-refresh enabled ({self.refresh_rate}ms)")
        else:
            self.refresh_timer.stop()
            self.set_status("Auto-refresh disabled")

    def update_refresh_rate(self, value):
        """Update the refresh rate."""
        self.refresh_rate = value
        if self.auto_refresh_enabled:
            self.refresh_timer.stop()
            self.refresh_timer.start(self.refresh_rate)
            self.set_status(f"Refresh rate updated to {self.refresh_rate}ms")

    def auto_refresh_weights(self):
        """Auto-refresh only the weight values for performance."""
        if not self.current_bs:
            return

        try:
            # Get all visible items in the tree
            root = self.target_tree.invisibleRootItem()
            self.refresh_weight_items(root)

        except Exception as e:
            # If there's an error, stop auto-refresh to prevent spam
            self.auto_refresh_cb.setChecked(False)
            self.toggle_auto_refresh(QtCore.Qt.Unchecked)
            print(f"Auto-refresh error: {e}")

    def refresh_weight_items(self, parent_item):
        """Recursively refresh weight values for all items."""
        for i in range(parent_item.childCount()):
            item = parent_item.child(i)

            # Get the weight widget
            weight_widget = self.target_tree.itemWidget(item, 1)
            if weight_widget:
                # Find the slider and spinbox in the widget
                slider = weight_widget.findChild(QtWidgets.QSlider)
                spinbox = weight_widget.findChild(QtWidgets.QDoubleSpinBox)

                if slider and spinbox:
                    # Get target name from item
                    target_name = item.text(0)

                    # Determine if this is a layer target
                    if target_name.startswith("L"):
                        # This is a layer target, need to get parent and layer info
                        parent = item.parent()
                        if parent:
                            parent_name = parent.text(0)
                            # Get layer blendshape
                            layer_relationships = self.detect_layer_relationships()
                            if (self.current_bs in layer_relationships and
                                parent_name in layer_relationships[self.current_bs]):
                                layer_bs = layer_relationships[self.current_bs][parent_name]
                                # Get actual target name (remove "L" prefix if it's just a number)
                                actual_target = target_name[1:] if target_name[1:].isdigit() else target_name

                                # Get current weight from Maya
                                try:
                                    current_weight = cmds.getAttr(f"{layer_bs}.{actual_target}")

                                    # Only update if weight has changed
                                    if abs(current_weight - slider.value() / 1000.0) > 0.001:
                                        # Block signals to prevent feedback loop
                                        slider.blockSignals(True)
                                        spinbox.blockSignals(True)

                                        slider.setValue(int(current_weight * 1000))
                                        spinbox.setValue(current_weight)

                                        slider.blockSignals(False)
                                        spinbox.blockSignals(False)
                                except:
                                    pass  # Silently ignore errors for individual targets
                    else:
                        # Regular target
                        try:
                            current_weight = cmds.getAttr(f"{self.current_bs}.{target_name}")

                            # Only update if weight has changed
                            if abs(current_weight - slider.value() / 1000.0) > 0.001:
                                # Block signals to prevent feedback loop
                                slider.blockSignals(True)
                                spinbox.blockSignals(True)

                                slider.setValue(int(current_weight * 1000))
                                spinbox.setValue(current_weight)

                                slider.blockSignals(False)
                                spinbox.blockSignals(False)
                        except:
                            pass  # Silently ignore errors for individual targets

            # Recursively refresh children
            if item.childCount() > 0:
                self.refresh_weight_items(item)


def show():
    """Show the UI window."""
    global blendshape_manager_ui

    # Close existing window
    try:
        if blendshape_manager_ui:
            blendshape_manager_ui.close()
            blendshape_manager_ui.deleteLater()
    except:
        pass

    # Check for existing window
    if cmds.window(BlendShapeManagerUI.WINDOW_NAME, exists=True):
        cmds.deleteUI(BlendShapeManagerUI.WINDOW_NAME, window=True)

    # Check for existing workspace control
    workspace_control = BlendShapeManagerUI.WINDOW_NAME + 'WorkspaceControl'
    if cmds.workspaceControl(workspace_control, exists=True):
        cmds.deleteUI(workspace_control, control=True)

    # Create new window
    blendshape_manager_ui = BlendShapeManagerUI()
    blendshape_manager_ui.show(dockable=True)

    return blendshape_manager_ui