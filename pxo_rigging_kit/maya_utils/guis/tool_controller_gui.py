# =======================================================================
# INFO (__doc__)
# =======================================================================


# =======================================================================
# IMPORT
# =======================================================================
import os

try:
    from PySide6 import QtCore
    from PySide6 import QtGui
    from PySide6 import QtWidgets

except ImportError:
    from PySide2 import QtCore
    from PySide2 import QtGui
    from PySide2 import QtWidgets

import maya.cmds as cmds

from pxo_rigging_kit import constants
from pxo_rigging_kit import string_utils
from pxo_rigging_kit.maya_utils import dag_utils
from pxo_rigging_kit.maya_utils.rigging import curves_utils
from pxo_rigging_kit.maya_utils.rigging import rig_utils
from pxo_rigging_kit.maya_utils.guis import custom_widgets
from pxo_rigging_kit.maya_utils.guis import scale_px_values
from pxo_rigging_kit.maya_utils.guis import scale_dpi
from pxo_rigging_kit.maya_utils import decorators

# =======================================================================
# MAIN()
# =======================================================================

from pxo_rigging_kit.maya_utils.guis import SEP_SYTLE_SHEET
from pxo_rigging_kit.maya_utils.guis import STYLE_SHEET
from pxo_rigging_kit.maya_utils.guis import get_maya_window

#######################################################
# GLOBALS
#######################################################

WINDOW = None
DECORATORS = decorators.Decorators()


#######################################################
# CLASSES
#######################################################

class ToolController(QtWidgets.QMainWindow):
    """
    Tool Controller.
    """
    TITLE = "Controller Tool"
    WINDOW_SIZE = [scale_dpi(400), scale_dpi(500)]
    SEP_SIZE = WINDOW_SIZE[0] - 30, 2
    MAYA_CHECK_ICON = 'check_inv.png'

    def __init__(self, parent=None):
        super(ToolController, self).__init__()

        self.win = self
        self.win.setParent(parent)
        self.win.setWindowTitle(self.TITLE)
        self.win.setWindowFlags(QtCore.Qt.Window)

        self.main_widget = QtWidgets.QWidget()
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_widget.setLayout(self.main_layout)

        self.setCentralWidget(self.main_widget)

        self.shape_list = sorted(curves_utils.get_curve_snake_names())

        self._build_widgets()

        self.setStyleSheet(self._format_general_style(STYLE_SHEET))

        self._cache_scale_position = []
        self._cache_cvs = []
        self._update_check = True
        self._recent_controls = []

    def sizeHint(self):
        return QtCore.QSize(*ToolController.WINDOW_SIZE)

    @staticmethod
    def _format_general_style(style_list):
        """
        Format the style sheet list to a string which can be used as style sheet for QT.

        Args:
            style_list: LIst filled with stylesheet strings.

        Returns:
            String: The style sheet string.
        """
        style_string = "".join(style_list)
        style_string = scale_px_values(style_string)

        icon_file = ToolController.MAYA_CHECK_ICON
        icon_path = os.path.join(constants.ICONS_PATH, icon_file)
        icon_path = icon_path.replace("\\", "/")

        style_string = style_string.replace('CHECK_ICON', icon_path)

        return style_string

    def _build_widgets(self):
        label = QtWidgets.QLabel('Controller Tool')
        self.main_layout.addWidget(label)

        self._add_separator()

        self.main_layout.setAlignment(QtCore.Qt.AlignTop)

        self.shape_list_widget = QtWidgets.QListWidget()
        for shape_name in self.shape_list:
            self.shape_list_widget.addItem(shape_name)

        self.shape_list_widget.setCurrentRow(3)

        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        section_widget = QtWidgets.QWidget()
        scroll_area.setWidget(section_widget)
        self.section_layout = QtWidgets.QVBoxLayout()
        section_widget.setLayout(self.section_layout)

        splitter = QtWidgets.QSplitter()
        splitter.addWidget(self.shape_list_widget)
        splitter.addWidget(scroll_area)
        splitter.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.MinimumExpanding)

        splitter.setSizes([1, 3])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        self.main_layout.addWidget(splitter)

        self._build_section_control()
        self._build_section_shape()
        self._build_section_color()
        self._build_section_channels()
        self.section_layout.addStretch()

    def _build_section_control(self):

        collapse_widget = custom_widgets.CollapsableSeparator('Control')
        collapse_widget.set_collapsed(True)
        collapse_widget.collapse_layout.setContentsMargins(1, 1, 1, 1)
        self.section_layout.addWidget(collapse_widget)
        self.section_layout.setContentsMargins(1, 1, 1, 1)
        self.section_layout.setSpacing(0)

        grid_layout = QtWidgets.QGridLayout()
        grid_layout.setHorizontalSpacing(2)
        grid_layout.setVerticalSpacing(2)

        suffix_label = QtWidgets.QLabel('Suffix')
        self.suffix = QtWidgets.QLineEdit()
        self.suffix.setText('ctrl')

        grid_layout.addWidget(suffix_label, 0, 0)
        grid_layout.addWidget(self.suffix, 0, 1)

        self.offset_checkbox, offset_checkbox_layout = self._add_checkbox('Offset Node')
        self.offset_checkbox.setCheckState(QtCore.Qt.Checked)
        self.offset_text = QtWidgets.QLineEdit()
        self.offset_text.setText('buffer_grp')
        offset_add = QtWidgets.QPushButton('Add')
        offset_add.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)

        offset_layout = QtWidgets.QHBoxLayout()
        offset_layout.addWidget(self.offset_text)
        offset_layout.addWidget(offset_add)

        grid_layout.addLayout(offset_checkbox_layout, 1, 0)
        grid_layout.addLayout(offset_layout, 1, 1)

        offset_add.clicked.connect(self._add_offset)

        self.shape_node_checkbox, shape_node_layout = self._add_checkbox('Shape Node')
        self.shape_node_checkbox.setCheckState(QtCore.Qt.Checked)

        self.shape_axis_combo = QtWidgets.QComboBox()
        combo_entries = ('+X', '+Y', '+Z', '-X', '-Y', '-Z')
        for entry in combo_entries:
            self.shape_axis_combo.addItem(entry)
        self.shape_axis_combo.setCurrentIndex(0)

        grid_layout.addLayout(shape_node_layout, 2, 0)
        grid_layout.addWidget(self.shape_axis_combo, 2, 1)

        self.create_joint_checkbox, joint_checkbox_layout = self._add_checkbox('Create Joint')
        radio_layout = QtWidgets.QVBoxLayout()
        self.each_object_radio = QtWidgets.QRadioButton('Each Object')
        self.each_object_radio.setChecked(True)
        self.all_objects_radio = QtWidgets.QRadioButton('All Objects')
        radio_layout.addWidget(self.each_object_radio)
        radio_layout.addWidget(self.all_objects_radio)
        radio_group = QtWidgets.QButtonGroup(self)
        radio_group.addButton(self.each_object_radio)
        radio_group.addButton(self.all_objects_radio)
        radio_group.setExclusive(True)

        grid_layout.addLayout(joint_checkbox_layout, 3, 0, alignment=QtCore.Qt.AlignTop)
        grid_layout.addLayout(radio_layout, 3, 1)

        parent_label = QtWidgets.QLabel('Parent')
        radio_layout2 = QtWidgets.QVBoxLayout()
        self.parent_world_radio = QtWidgets.QRadioButton('World')
        self.parent_world_radio.setChecked(True)
        self.selection_order_radio = QtWidgets.QRadioButton('Selection Order')
        radio_layout2.addWidget(self.parent_world_radio)
        radio_layout2.addWidget(self.selection_order_radio)
        radio_group2 = QtWidgets.QButtonGroup(self)
        radio_group2.addButton(self.parent_world_radio)
        radio_group2.addButton(self.selection_order_radio)
        radio_group2.setExclusive(True)

        grid_layout.addWidget(parent_label, 4, 0, alignment=QtCore.Qt.AlignTop)
        grid_layout.addLayout(radio_layout2, 4, 1)

        constraint_type_label = QtWidgets.QLabel('Constraint Type')

        self.constraint_type_combo = QtWidgets.QComboBox()
        combo_entries = ('None', 'Point Orient', 'Parent', 'Matrix')
        for entry in combo_entries:
            self.constraint_type_combo.addItem(entry)
        self.constraint_type_combo.setCurrentIndex(3)

        grid_layout.addWidget(constraint_type_label, 5, 0)
        grid_layout.addWidget(self.constraint_type_combo, 5, 1)

        constrain_label = QtWidgets.QLabel('Constrain')
        constraint_layout = QtWidgets.QVBoxLayout()
        constraint_layout.setAlignment(QtCore.Qt.AlignLeft)

        self.translate_check, translate_layout = self._add_checkbox('Translate')
        self.rotate_check, rotate_layout = self._add_checkbox('Rotate')
        self.scale_check, scale_layout = self._add_checkbox('Scale')
        self.translate_check.setCheckState(QtCore.Qt.Checked)
        self.rotate_check.setCheckState(QtCore.Qt.Checked)
        self.scale_check.setCheckState(QtCore.Qt.Checked)

        translate_layout.setAlignment(QtCore.Qt.AlignLeft)
        constraint_layout.addLayout(translate_layout,)
        constraint_layout.addLayout(rotate_layout)
        constraint_layout.addLayout(scale_layout)

        grid_layout.addWidget(constrain_label, 6, 0, alignment=QtCore.Qt.AlignTop)
        grid_layout.addLayout(constraint_layout, 6, 1)

        create_controls = QtWidgets.QPushButton('Create Controls')
        create_controls.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)
        create_sub_control = QtWidgets.QPushButton('Create Sub Control')
        create_sub_control.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)
        create_pivot_control = QtWidgets.QPushButton('Create Pivot Control')

        sub_control_layout = QtWidgets.QVBoxLayout()
        sub_control_layout.addWidget(create_sub_control)
        sub_control_layout.addWidget(create_pivot_control)

        grid_layout.addWidget(create_controls, 7, 0)
        grid_layout.addLayout(sub_control_layout, 7, 1)

        collapse_widget.add_layout(grid_layout)

        self.constraint_type_combo.currentIndexChanged.connect(self._constraint_type_changed)

        create_controls.clicked.connect(self._create_controls)
        create_sub_control.clicked.connect(self._create_sub_control)
        create_pivot_control.clicked.connect(self._create_pivot_control)

    def _build_section_shape(self):
        collapse_widget = custom_widgets.CollapsableSeparator('Edit Shape')
        collapse_widget.set_collapsed(True)
        collapse_widget.collapse_layout.setContentsMargins(1, 1, 1, 1)
        self.section_layout.addWidget(collapse_widget)

        replace_shape = QtWidgets.QPushButton('Replace Shape')

        collapse_widget.add_widget(replace_shape)

        collapse_widget.collapse_layout.addSpacing(0)

        self.scale_slider = custom_widgets.ResetSlider('Tweak Size')

        collapse_widget.add_widget(self.scale_slider)

        grid_layout = QtWidgets.QGridLayout()
        grid_layout.setContentsMargins(1, 1, 1, 1)
        grid_layout.setSpacing(2)

        self.translate = custom_widgets.ThreeDoubleWidget('Translate')
        self.rotate = custom_widgets.ThreeDoubleWidget('Rotate')
        self.scale = custom_widgets.ThreeDoubleWidget('Scale')
        self.scale.set_all_values(1)

        apply_translate = QtWidgets.QPushButton('Apply')
        apply_rotate = QtWidgets.QPushButton('Apply')
        apply_scale = QtWidgets.QPushButton('Apply')

        grid_layout.addWidget(self.translate, 0, 0)
        grid_layout.addWidget(apply_translate, 1, 0)

        grid_layout.addWidget(self.rotate, 0, 1)
        grid_layout.addWidget(apply_rotate, 1, 1)

        grid_layout.addWidget(self.scale, 0, 2)
        grid_layout.addWidget(apply_scale, 1, 2)

        collapse_widget.add_layout(grid_layout)

        replace_shape.clicked.connect(self._replace_shape)
        apply_translate.clicked.connect(self._apply_translate)
        apply_rotate.clicked.connect(self._apply_rotate)
        apply_scale.clicked.connect(self._apply_scale)

        self.scale_slider.value_changed.connect(self._scale_slider_value_change)
        self.scale_slider.pressed.connect(self._scale_slider_pressed)
        self.scale_slider.released.connect(self._scale_slider_released)

    def _build_section_color(self):
        collapse_widget = custom_widgets.CollapsableSeparator('Edit Color')
        collapse_widget.set_collapsed(True)

        collapse_widget.collapse_layout.setContentsMargins(1, 1, 1, 1)

        self.section_layout.addWidget(collapse_widget)

        color_widget = custom_widgets.MayaColorIndices()
        color_picker_widget = custom_widgets.GradientWidget()
        collapse_widget.add_widget(color_widget)
        collapse_widget.add_widget(color_picker_widget)

        custom_color_layout = QtWidgets.QHBoxLayout()

        self.color1 = custom_widgets.GetColor()
        self.color2 = custom_widgets.GetColor()

        gradiant = QtWidgets.QPushButton('Gradiant Selected')

        custom_color_layout.addWidget(self.color1)
        custom_color_layout.addStretch()
        custom_color_layout.addWidget(self.color2)

        collapse_widget.add_layout(custom_color_layout)
        collapse_widget.add_widget(gradiant)

        selection_highlight = custom_widgets.HideShowWidget('Selection Highlight')
        collapse_widget.add_widget(selection_highlight)

        color_widget.clicked.connect(self._set_color_index)
        color_picker_widget.clicked.connect(self._set_color_rgb)
        color_picker_widget.dragged.connect(self._set_color_rgb)

        self.color1.clicked.connect(self._set_color_rgb)
        self.color2.clicked.connect(self._set_color_rgb)
        self.color1.load.clicked.connect(self._load_color1)
        self.color2.load.clicked.connect(self._load_color2)
        gradiant.clicked.connect(self._gradiant_selected)

        selection_highlight.clicked.connect(self._selection_highlight)

    def _build_section_channels(self):
        collapse_widget = custom_widgets.CollapsableSeparator('Edit Channels')
        collapse_widget.set_collapsed(True)
        collapse_widget.collapse_layout.setContentsMargins(1, 1, 1, 1)
        self.section_layout.addWidget(collapse_widget)

        translate_widget = custom_widgets.HideShowWidget('Translate')
        translate_widget.clicked.connect(self._hide_show)

        rotate_widget = custom_widgets.HideShowWidget('Rotate')
        rotate_widget.clicked.connect(self._hide_show)

        scale_widget = custom_widgets.HideShowWidget('Scale')
        scale_widget.clicked.connect(self._hide_show)

        vis_widget = custom_widgets.HideShowWidget('Visibility')
        vis_widget.clicked.connect(self._hide_show)

        collapse_widget.add_widget(translate_widget)
        collapse_widget.add_widget(rotate_widget)
        collapse_widget.add_widget(scale_widget)
        collapse_widget.add_widget(vis_widget)

    def _add_separator(self):
        separator = QtWidgets.QFrame()
        separator.setFixedSize(self.SEP_SIZE[0], self.SEP_SIZE[1])
        separator.setFrameStyle(QtWidgets.QFrame.HLine)
        separator.setStyleSheet(SEP_SYTLE_SHEET)

        self.main_layout.addWidget(separator)

    def _add_double_value(self, name, value=0):
        label = QtWidgets.QLabel(name)
        label.setStyleSheet("font-size: 7pt;")

        double_widget = QtWidgets.QDoubleSpinBox()
        double_widget.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        double_widget.setStyleSheet("QDoubleSpinBox { border: none; }")
        double_widget.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)
        double_widget.setValue(value)
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(label, alignment=QtCore.Qt.AlignRight)
        layout.addWidget(double_widget)
        layout.setContentsMargins(10, 1, 1, 1)
        layout.setSpacing(1)
        return double_widget, layout

    def _add_checkbox(self, name):
        label = QtWidgets.QLabel(name)
        checkbox = QtWidgets.QCheckBox()

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(checkbox)
        layout.addWidget(label, alignment=QtCore.Qt.AlignLeft)
        layout.addStretch()
        layout.setSpacing(0)

        return checkbox, layout

    def _create_joint(self, objects):
        """
        This will create a single joint at the middle of objects.
        If the objects are geometry a skin cluster is also created with the created joint as influence.

        Args:
            objects: unique name of transforms in Maya

        Returns:
            the joint created
        """
        cmds.select(clear=True)

        short_name = objects[0].split('|')[-1]

        joint = cmds.joint(name=f"{short_name}_joint")

        clr = None
        try:
            clr = cmds.cluster(objects)[1]
        except RuntimeError:
            pass

        if clr:
            cmds.delete(cmds.parentConstraint(clr, joint, mo=False))
            cmds.delete(clr)
        else:
            if len(objects) > 1:
                center = rig_utils.get_avg_object_center(objects)
                rotation = [0, 0, 0]
            else:
                center = cmds.xform(objects, q=True, ws=True, t=True)
                rotation = cmds.xform(objects, q=True, ws=True, ro=True)

            cmds.xform(joint, ws=True, t=center, ro=rotation)

        if clr:
            for object in objects:
                cmds.skinCluster(joint, object, tsb=True)

        return joint

    def _create_joints(self, selection):
        """
        Will either create a single joint per transform selection or a multiple joints per transform selection.
        If the selection is a geometry a skin cluster will also be created with the new joint as an influence.

        Args:
            selection:  Use selection of transform to guide joint creation.

        Returns:
            list: the joints created
        """

        create_joint = self.create_joint_checkbox.isChecked()
        joint_group = self.all_objects_radio.isChecked()

        joints = []
        if create_joint:
            if joint_group:
                joint = self._create_joint(selection)
                joints.append(joint)
            else:
                for thing in selection:
                    joint = self._create_joint([thing])
                    joints.append(joint)

        return joints

    def _get_shape(self):
        """
        Convenience for getting the current shape in the shape list.

        Returns:
            str: Current shape name selected. If nothing selected then 'circle'

        """
        shape_item = self.shape_list_widget.currentItem()
        if shape_item:
            shape_name = str(shape_item.text())
        else:
            shape_name = 'circle'

        return shape_name

    def _align_curve(self, control):
        """
        Aligns the control to the current axis.

        Args:
            control: The name of the control to edit the shape node.
        """
        rotations = {'+X': [0, 0, 90],
                     '-X': [0, 0, -90],
                     '+Y': [0, 0, 0],
                     '-Y': [0, 180, 0],
                     '+Z': [90, 0, 0],
                     '-Z': [-90, 0, 0],
                     }

        rotate = None

        current_axis = str(self.shape_axis_combo.currentText())

        if current_axis in rotations:
            rotate = rotations[current_axis]
        if not rotate:
            return

        cvs = self.get_cvs(control)

        cmds.rotate(*rotate, cvs, os=True)

    def _rename_buffer_group(self, buffer_grp):
        """
        Rename the buffer group above a control.
        This uses the offset text defined in the UI.

        Args:
            buffer_grp: The buffer group transform name to rename

        Returns:
            str: The new buffer group name

        """
        offset_text = str(self.offset_text.text())
        if offset_text and offset_text != 'buffer_grp':
            new_buffer_name = buffer_grp.replace('buffer_grp', offset_text)
            buffer_grp = cmds.rename(buffer_grp, new_buffer_name)

        return buffer_grp

    @DECORATORS.undo
    def _add_offset(self):
        """
        Adds an offset group to any transform selected in the scene.
        """
        offset_text = str(self.offset_text.text())
        selected = cmds.ls(sl=True, l=True)

        uuids = cmds.ls(selected,
                        uuid=True
                        )

        buffers = dag_utils.create_buffer_groups(rig_utils.convert_to_pynode_list(selected), offset_text)

        buffers = rig_utils.convert_any_pynodes(buffers)

        cmds.select(cmds.ls(uuids))

        return buffers

    def _create_control(self, transform=None):
        """
        Create a control with the same transformation as the given transform.

        Args:
            transform: Name of a transform to use as example.

        Returns:
            [control, buffer_grp]:  The new control and buffer_grp names.
        """

        ctrl_suffix = str(self.suffix.text())

        if transform and transform.endswith(ctrl_suffix):
            sub_controls = self._create_sub_control(transform)

            if sub_controls:
                self._recent_controls.append(sub_controls[0])
                return [sub_controls[0], None]
            else:
                return [None, None]

        shape_name = self._get_shape()
        create_shape = self.shape_node_checkbox.isChecked()

        offset_group = self.offset_checkbox.isChecked()

        name = f'control_0_{ctrl_suffix}'
        name = rig_utils.get_unique_name(name)

        rotations = {'+X': [0, 0, 90],
                     '-X': [0, 0, -90],
                     '+Y': [0, 0, 0],
                     '-Y': [0, 180, 0],
                     '+Z': [90, 0, 0],
                     '-Z': [-90, 0, 0],
                     }

        current_axis = str(self.shape_axis_combo.currentText())

        rotation = rotations['+Y']

        if current_axis in rotations:
            rotation = rotations[current_axis]

        match = transform
        scale = None
        color_index = 17
        do_buffer_grp = offset_group
        child = None
        lock_translate = False
        lock_rotate = False
        lock_scale = False
        lock_visibility = False
        move = None
        rotate = rotation

        control, buffer_grp = curves_utils.create_curve_by_snake_name(shape_name,
                                                                      name,
                                                                      match,
                                                                      scale,
                                                                      color_index,
                                                                      do_buffer_grp,
                                                                      child,
                                                                      lock_translate,
                                                                      lock_rotate,
                                                                      lock_scale,
                                                                      lock_visibility,
                                                                      move,
                                                                      rotate)

        control = control.name()
        if buffer_grp:
            buffer_grp = buffer_grp.name()
            buffer_grp = self._rename_buffer_group(buffer_grp)

        cmds.setAttr(f'{control}.visibility', k=False, l=True)

        new_name = control + '_hitch'

        hitch = cmds.createNode('transform', n=new_name)
        cmds.matchTransform(hitch, control, position=True, rotation=True)
        cmds.parent(hitch, control)

        if not cmds.objExists(f'{control}.hitch'):
            cmds.addAttr(control, ln='hitch', at="message")
        cmds.connectAttr(f'{hitch}.message', f'{control}.hitch')

        self._constrain(hitch, transform)
        self._recent_controls.append(control)

        if not create_shape:
            cmds.delete(self._get_child_shapes(control))
        cmds.controller(control)

        return control, buffer_grp

    @DECORATORS.undo
    def _create_sub_control(self, transform=None):
        """
        Given a control add a sub control. Behavior changes based on what transform is passed.
        control:  creates a sub controls
        sub control: creates another sub control. If main control has 2 sub controls no more are added.
        pivot control: no sub control created.

        Args:
            transform: The name of the control to add sub control to.
                        If no transform supplied command works on selection.

        Returns:
            list: The names of the sub controls created.
        """
        if transform:
            selected = [transform]
        else:
            selected = cmds.ls(sl=True, l=True)

        scale = 0.8

        subs = []

        selected_uuids = cmds.ls(selected, uuid=True)

        for uuid in selected_uuids:
            node = cmds.ls(uuid)[0]
            node_name = node.split('|')[-1]

            if node_name.find('_piv_') > -1:
                continue

            suffix = str(self.suffix.text())
            new_suffix = f"sub_{suffix}"
            shape_name = self._get_shape()

            if not node.endswith(suffix):
                continue
            main_node = None

            if node.endswith(f'sub2_{suffix}'):
                continue

            if node.endswith(f'sub_{suffix}'):
                shapes = self._get_child_shapes(node)
                main_node = cmds.listConnections(f'{shapes[0]}.visibility')[0]
                scale = 0.6

                orig_new_suffix = new_suffix
                new_suffix = f"sub2_{suffix}"
                suffix = orig_new_suffix

            sub = cmds.group(empty=True, name=node_name.replace(suffix, new_suffix))
            curves_utils.replace_shapes_from_snake_name(shape_name, sub)
            cvs = self.get_cvs(sub)
            cmds.scale(scale, scale, scale, cvs, a=True)

            self._align_curve(sub)

            cmds.setAttr(f'{sub}.visibility', k=False, l=True)

            children = cmds.listRelatives(node, f=True, type='transform')
            if children:
                children = [child for child in children if not child.endswith(f'piv_{suffix}')]

            cmds.parent(sub, node, r=True)

            if children:
                cmds.parent(children, sub)

            if not main_node:
                main_node = node

            self._sub_control_visibility(main_node, sub)

            if cmds.objExists(f'{main_node}.endCtrl'):
                cmds.connectAttr(f'{sub}.message', f'{main_node}.endCtrl')

            color = self._get_color_rgb(node)
            darker = self._darken_color(color)
            self._set_color_rgb(darker, [sub])

            cmds.controller(sub)
            cmds.controller(sub, node, e=True, p=True)
            cmds.addAttr(sub, ln="isCtl", at="bool", dv=True)
            subs.append(sub)

        if subs:
            cmds.select(subs)

        return subs

    @DECORATORS.undo
    def _create_pivot_control(self):
        """
        Creates a pivot control per selection.

        Returns:
            list: The names of the pivot controls created.

        """
        suffix = str(self.suffix.text())
        selected = cmds.ls(sl=True)

        pivot_controls = []

        for node in selected:
            if not cmds.objExists(f'{node}.displayPivotOffset'):
                cmds.addAttr(node, longName='displayPivotOffset', attributeType="bool", k=True, dv=1)

            existing_pivot_ctrl = cmds.listConnections(f'{node}.rotatePivotX')
            if existing_pivot_ctrl:
                return
            if node.endswith(f'_piv_{suffix}'):
                return

            pivot_ctrl = cmds.spaceLocator(name='%s' % node.replace(suffix, f'piv_{suffix}'))[0]
            self._replace_shape([pivot_ctrl], 'locator')
            cmds.parent(pivot_ctrl, node, r=True)

            cmds.connectAttr(f'{pivot_ctrl}.translateX', f'{node}.rotatePivotX')
            cmds.connectAttr(f'{pivot_ctrl}.translateY', f'{node}.rotatePivotY')
            cmds.connectAttr(f'{pivot_ctrl}.translateZ', f'{node}.rotatePivotZ')
            cmds.connectAttr(f'{pivot_ctrl}.translateX', f'{node}.scalePivotX')
            cmds.connectAttr(f'{pivot_ctrl}.translateY', f'{node}.scalePivotY')
            cmds.connectAttr(f'{pivot_ctrl}.translateZ', f'{node}.scalePivotZ')

            pivot_controls.append(pivot_ctrl)

        cmds.select(pivot_controls)
        return pivot_controls

    def _is_sub_control(self, node):
        """
        Checks if the node name given is a sub control.
        Args:
            node: The name of a node to test

        Returns:
            bool: True if it is a sub control.
        """
        suffix = str(self.suffix.text())
        if node.endswith(f'sub2_{suffix}'):
            return True

        if node.endswith(f'sub_{suffix}'):
            return True

    def _constrain(self, control, transform):
        """
        control constrains transform using the setting defined in the UI.
        constrain_type 0 = None
        constrain_type 1 = point and orient
        constrain_type 2 = parent
        constrain_type 3 = matrix

        Args:
            control: The name of a control
            transform: The name of a transform

        """
        if not transform:
            return

        control = str(control)
        transform = str(transform)

        translate = self.translate_check.isChecked()
        rotate = self.rotate_check.isChecked()
        scale = self.scale_check.isChecked()

        constrain_type = self.constraint_type_combo.currentIndex()

        if not translate and not rotate and not scale:
            return

        if constrain_type == 0:
            return

        if constrain_type == 1:
            if translate:
                cmds.pointConstraint(control, transform, mo=True)
            if rotate:
                cmds.orientConstraint(control, transform, mo=True)
        if constrain_type == 2:
            if translate or rotate:
                if not translate:
                    cmds.parentConstraint(control, transform, mo=True, skipTranslate=['x', 'y', 'z'])
                elif not rotate:
                    cmds.parentConstraint(control, transform, mo=True, skipRotate=['x', 'y', 'z'])
                else:
                    cmds.parentConstraint(control, transform, mo=True)

        if constrain_type < 3:
            if scale:
                cmds.scaleConstraint(control, transform)

        if constrain_type == 3:
            rig_utils.constrain_matrix(control, transform, translate, rotate, scale)

    def _constraint_type_changed(self, index):

        if index == 0:
            self.translate_check.setEnabled(False)
            self.rotate_check.setEnabled(False)
            self.scale_check.setEnabled(False)
        else:
            self.translate_check.setEnabled(True)
            self.rotate_check.setEnabled(True)
            self.scale_check.setEnabled(True)

    @DECORATORS.undo
    def _create_controls(self):
        """
        Creates controls on the selected transforms.
        If selected transform is a control then add sub control.

        """
        selected = cmds.ls(sl=True, l=True)
        hierarchy = self.selection_order_radio.isChecked()
        joints = self._create_joints(selected)

        self._recent_controls = []

        if joints:
            scope = joints
        else:
            scope = selected

        if scope:

            uuid_scope = cmds.ls(scope, uuid=True)

            last_control = None
            for uuid_name in uuid_scope:
                thing = cmds.ls(uuid_name)[0]
                control, buffer = self._create_control(thing)
                if hierarchy and last_control:
                    if buffer:
                        child = buffer
                    else:
                        child = control

                    if not self._is_sub_control(child):
                        last_control = cmds.ls(last_control, l=True)
                        cmds.parent(child, last_control)

                last_control = cmds.ls(control, uuid=True)
        else:
            self._create_control()

        if self._recent_controls:
            cmds.select(self._recent_controls)

    @DECORATORS.undo
    def _replace_shape(self, transforms=None, shape_name=None):
        """
        Replaces the shape of the transforms given. If no transforms than works on selection.

        Args:
            transforms: The names of transforms to work on. If no transforms given than work on selection.
            shape_name: The name of the shape to replace current with.  Shape name must correspond to library.
        """
        if not shape_name:
            shape_name = self._get_shape()

        if not transforms:
            transforms = cmds.ls(sl=True, l=True)
        if not transforms:
            transforms = self._recent_controls
        if not transforms:
            return

        scale = 1
        sub = False
        main_control = None
        for thing in transforms:
            control = thing

            if control.find('_sub_') > -1:
                scale = .8
                sub = True
            if control.find('_sub2_') > -1:
                scale = .6
                sub = True
            if sub:
                shapes = self._get_child_shapes(control)
                main_control = cmds.listConnections(f'{shapes[0]}.visibility')[0]

            rgb_value = self._get_color_rgb(control)

            curves_utils.replace_shapes_from_snake_name(shape_name, control)

            if main_control:
                self._sub_control_visibility(main_control, control)

            self._set_color_rgb(rgb_value, [control])

            self._align_curve(thing)
            cvs = self.get_cvs(thing)
            cmds.scale(scale, scale, scale, cvs, a=True)

        cmds.select(transforms)

    @DECORATORS.undo
    def _scale_slider_value_change(self, value):
        """
        Scales the geometry cvs.

        Args:
            value: The scale amount.
        """
        value = self._remap(abs(value), 0, 10, 1, 0.1 if value < 0 else 2)

        cvs = self._cache_cvs
        positions = self._cache_scale_position

        for position, cv in zip(positions, cvs):
            cmds.xform(cv, ws=True, t=position)
        cmds.scale(value, value, value, cvs, absolute=True)

    def _scale_slider_pressed(self):

        scope = cmds.ls(sl=True, type='transform')
        if not scope:
            return
        self._cache_cvs = [cv for thing in scope for cv in self.get_cvs(thing) or []]
        self._cache_scale_position = [cmds.xform(cv, q=True, ws=True, t=True) for cv in self._cache_cvs]

    def _scale_slider_released(self):
        self._cache_cvs = []
        self._cache_scale_position = []

    @DECORATORS.undo
    def _apply_translate(self):
        """
        Translate selected cvs
        """
        translate = self.translate.get_value()
        selected = cmds.ls(sl=True, l=True)
        for thing in selected:
            cvs = self.get_cvs(thing)
            if cvs:
                cmds.move(*translate, cvs, relative=True, os=True)

    @DECORATORS.undo
    def _apply_rotate(self):
        """
        Rotate selected cvs
        """
        rotate = self.rotate.get_value()
        selected = cmds.ls(sl=True, l=True)
        for thing in selected:
            cvs = self.get_cvs(thing)
            if cvs:
                cmds.rotate(*rotate, cvs, relative=True, os=True)

    @DECORATORS.undo
    def _apply_scale(self):
        """
        Scale selected cvs
        """
        scale = self.scale.get_value()
        selected = cmds.ls(sl=True, l=True)
        for thing in selected:
            cvs = self.get_cvs(thing)
            if cvs:
                cmds.scale(*scale, cvs, absolute=True)

    def _sub_control_visibility(self, main_control, sub_control):
        """
        Adds an attribute to show/hide the sub control under a main control
        Args:
            main_control: name of main control, parent to sub_control
            sub_control: name of a sub_control that sits under main_control
        """
        if not cmds.objExists(f'{main_control}.sub_control'):
            cmds.addAttr(main_control, ln='sub_control', at='long', min=0, max=1, dv=1, k=False)
            cmds.setAttr(f'{main_control}.sub_control', cb=True)

        shapes = self._get_child_shapes(sub_control)

        for shape in shapes:
            cmds.connectAttr(f'{main_control}.sub_control', f'{shape}.visibility')

    def get_cvs(self, transform):
        """
        Get all CVs of shape nodes under the given transform node.

        Args:
            transform (str): Name of the transform node.

        Returns:
            list: List of CVs for all shape nodes under the transform.
        """
        # Ensure the transform exists
        if not cmds.objExists(transform):
            raise ValueError(f"Transform node '{transform}' does not exist.")

        shapes = self._get_child_shapes(transform)

        all_cvs = []
        for shape in shapes:

            try:
                cvs = cmds.filterExpand(f"{shape}.cv[*]", selectionMask=28) or []
            except RuntimeError:
                cvs = []
            if cvs and type(cvs) == list:
                all_cvs.extend(cvs)

        return all_cvs

    def _get_color_rgb(self, transform):
        """
        Get the rgb color or index color from the shape node of a transform.
        Args:
            transform: The name of a transform.

        Returns:
            tuple: the rgb values (0,0,0)

        """
        shapes = self._get_child_shapes(transform)
        if not shapes:
            raise ValueError(f"{transform} has no shapes associated with it!")

        shape_ = shapes[0]

        rgb_on = cmds.getAttr(f'{shape_}.overrideRGBColors')
        color = []

        if rgb_on:
            color = cmds.getAttr(f'{shape_}.overrideColorRGB')[0]
        else:
            color_index = cmds.getAttr(f'{shape_}.overrideColor')
            if color_index > 0:
                color = cmds.colorIndex(color_index, query=True)

        return color

    def _darken_shape_color(self, transform):
        color = self._get_color_rgb(transform)
        if color:
            new_color = self._darken_color(color)
            self._set_color_rgb(new_color, [transform])

    def _set_color_index(self, index_value):

        for thing in cmds.ls(sl=True, l=True):
            shapes = self._get_child_shapes(thing)
            for shape in shapes:
                cmds.setAttr(f'{shape}.overrideEnabled', 1)
                cmds.setAttr(f'{shape}.overrideRGBColors', 0)
                cmds.setAttr(f'{shape}.overrideColor', index_value)

    def _set_color_rgb(self, rgb_value, transforms=None):

        if type(rgb_value) == QtGui.QColor:
            rgb_value = rgb_value.getRgbF()

        if not transforms:
            transforms = cmds.ls(sl=True, l=True)

        for thing in transforms:
            shapes = self._get_child_shapes(thing)
            for shape in shapes:
                cmds.setAttr(f'{shape}.overrideEnabled', 1)
                cmds.setAttr(f'{shape}.overrideRGBColors', 1)
                cmds.setAttr(f'{shape}.overrideColorRGB', *rgb_value)

    def _load_color1(self):
        selection = cmds.ls(sl=True, type='transform')
        if not selection:
            return

        color = self._get_color_rgb(selection[0])

        q_color = QtGui.QColor()
        q_color.setRgbF(*color)

        self.color1.color.set_color(q_color)

    def _load_color2(self):
        selection = cmds.ls(sl=True, type='transform')
        if not selection:
            return

        color = self._get_color_rgb(selection[0])

        q_color = QtGui.QColor()
        q_color.setRgbF(*color)

        self.color2.color.set_color(q_color)

    def _gradiant_selected(self):
        """
        Given 2 colors supplied through the UI, apply gradient to selection by selection order.
        """
        selection = cmds.ls(sl=True, type='transform')
        if not selection:
            return

        selection.sort(key=string_utils.extract_integer)

        color1 = self.color1.color.color
        color2 = self.color2.color.color

        count = len(selection)
        for i, obj in enumerate(selection):
            t = float(i) / (count - 1) if count > 1 else 0.0
            interp_color = self._interpolate_qcolor(color1, color2, t)

            self._set_color_rgb(interp_color.getRgbF(), [obj])

    def _hide_show(self, bool_value, title):
        """Show/hide the channel box channels """
        xyz = ['translate', 'rotate', 'scale']
        for thing in cmds.ls(sl=True, type='transform', l=True):
            attribute = title.lower()
            self.lock_and_hide(thing, attribute, not bool_value)

            if attribute in xyz:
                for axis in 'XYZ':
                    sub_attribute = f"{attribute}{axis}"
                    self.lock_and_hide(thing, sub_attribute, not bool_value)

    @staticmethod
    def _get_child_shapes(transform):
        shape_nodes = cmds.listRelatives(transform, shapes=True, fullPath=True) or []

        return shape_nodes

    @staticmethod
    def _darken_color(rgb_f, factor=0.7):
        r, g, b = rgb_f
        r = max(0.0, min(1.0, r * factor))
        g = max(0.0, min(1.0, g * factor))
        b = max(0.0, min(1.0, b * factor))
        return [r, g, b]

    @staticmethod
    def _remap(value, from_min, from_max, to_min, to_max):
        """
        Remaps value from min,max to min,max
        """
        return to_min + (value - from_min) * (to_max - to_min) / (from_max - from_min)

    @staticmethod
    def _interpolate_qcolor(c1: QtGui.QColor, c2: QtGui.QColor, t: float) -> QtGui.QColor:
        """Linearly interpolates between two QColor instances."""
        r = c1.redF() + (c2.redF() - c1.redF()) * t
        g = c1.greenF() + (c2.greenF() - c1.greenF()) * t
        b = c1.blueF() + (c2.blueF() - c1.blueF()) * t
        return QtGui.QColor.fromRgbF(r, g, b)

    @staticmethod
    def _selection_highlight(bool_value):
        """Show/hide the selection highlight in the model panels."""
        model_panels = cmds.getPanel(type='modelPanel')
        for panel in model_panels:
            cmds.modelEditor(panel, edit=True, sel=bool_value)

    @staticmethod
    def lock_and_hide(node, attribute, bool_value):
        if bool_value:
            cmds.setAttr(f'{node}.{attribute}', l=True)
            cmds.setAttr(f'{node}.{attribute}', k=False)
            cmds.setAttr(f'{node}.{attribute}', cb=False)

        else:
            cmds.setAttr(f'{node}.{attribute}', l=False)
            cmds.setAttr(f'{node}.{attribute}', k=True)


def show():
    global WINDOW
    maya_window = get_maya_window()
    if WINDOW:
        WINDOW.close()
    WINDOW = ToolController(maya_window)
    WINDOW.show()
