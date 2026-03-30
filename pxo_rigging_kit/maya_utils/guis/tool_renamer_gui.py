# =======================================================================
# INFO (__doc__)
# =======================================================================


# =======================================================================
# IMPORT
# =======================================================================
import os
from functools import partial
import re

try:
    from PySide6 import QtCore
    from PySide6 import QtGui
    from PySide6 import QtWidgets

except ImportError:
    from PySide2 import QtCore
    from PySide2 import QtGui
    from PySide2 import QtWidgets

import maya.cmds as cmds
import pymel.core as pm
from mgear.shifter.component import guide

from pxo_rigging_kit import constants
from pxo_rigging_kit.maya_utils.rigging import curves_utils
from pxo_rigging_kit.maya_utils.rigging import rig_utils
from pxo_rigging_kit.maya_utils.guis import custom_widgets
from pxo_rigging_kit.maya_utils.guis import scale_dpi
from pxo_rigging_kit.maya_utils.guis import scale_px_values
from pxo_rigging_kit.maya_utils import decorators
from pxo_rigging_kit.maya_utils.mgear import guide_utils

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

class ToolRenamer(QtWidgets.QMainWindow):
    """
    Tool Renamer.
    """
    TITLE = "Rename Tool"
    WINDOW_SIZE = [scale_dpi(370), scale_dpi(450)]
    SEP_SIZE = WINDOW_SIZE[0] - 30, 2
    PUSH_BUTTON_HIGHT = 25
    COMBO_BOX_MINIMAL_HIGHT = 25
    MAYA_CHECK_ICON = 'check_inv.png'
    EXAMPLE_INC_STRING = 'example: A or a'
    EXAMPLE_INC_NUMBER = 'example: 1'

    def __init__(self, parent=None):
        super(ToolRenamer, self).__init__()

        self.win = self
        self.win.setParent(parent)
        self.win.setWindowTitle(self.TITLE)
        self.win.setWindowFlags(QtCore.Qt.Window)

        self.main_widget = QtWidgets.QWidget()
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.main_widget)

        self.main_layout.setAlignment(QtCore.Qt.AlignTop)

        self.shape_list = sorted(curves_utils.get_curve_snake_names())

        self._build_widgets()

        self.setStyleSheet(self._format_general_style(STYLE_SHEET))

        self._cache_scale_position = []
        self._cache_cvs = []
        self._update_check = True
        self._recent_controls = []

    def sizeHint(self):
        return QtCore.QSize(*ToolRenamer.WINDOW_SIZE)

    @staticmethod
    def _format_general_style(style_list):
        """
        Format the the style sheet list to a string which can be used as style sheet for QT.

        Args:
            style_list: LIst filled with stylesheet strings.

        Returns:
            String: The style sheet string.
        """

        style_string = "".join(style_list)
        style_string = scale_px_values(style_string)
        icon_file = ToolRenamer.MAYA_CHECK_ICON

        icon_path = os.path.join(constants.ICONS_PATH, icon_file)
        icon_path = icon_path.replace("\\", "/")

        style_string = style_string.replace('CHECK_ICON', icon_path)

        return style_string

    def _build_widgets(self):
        label = QtWidgets.QLabel('Renamer Tool')
        self.main_layout.addWidget(label)
        self._add_separator()

        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        section_widget = QtWidgets.QWidget()
        scroll_area.setWidget(section_widget)
        self.section_layout = QtWidgets.QVBoxLayout()
        self.section_layout.setContentsMargins(1, 1, 1, 1)
        self.section_layout.setSpacing(1)
        section_widget.setLayout(self.section_layout)

        self.section_layout.setAlignment(QtCore.Qt.AlignTop)

        self.main_layout.addWidget(scroll_area)

        self._build_select()
        self._build_hash_rename()
        self._build_mgear_rename()
        self._build_search_and_replace()
        self._build_prefix_suffix()
        self._unique_rename()

    def _build_select(self):
        collapse_widget = custom_widgets.CollapsableSeparator('Select')
        collapse_widget.set_collapsed(True)

        collapse_widget.collapse_layout.setContentsMargins(2, 2, 2, 2)
        collapse_widget.collapse_layout.setSpacing(1)

        self.section_layout.addWidget(collapse_widget)

        self.search_widget = custom_widgets.TextEntryWidget('Search\t')
        self.search_widget.text_entry.returnPressed.connect(self._run_search)

        self.filter_widget = custom_widgets.TextEntryWidget('Filter\t')
        self.filter_widget.text_entry.returnPressed.connect(self._run_search)

        grid_layout = QtWidgets.QGridLayout()
        grid_layout.setSpacing(1)
        types = ['transform', 'joint', 'locator', 'mesh', 'curve', 'surface']
        column = 0
        row = 0

        for type_name in types:
            title = type_name.capitalize()
            button = QtWidgets.QPushButton(title)
            grid_layout.addWidget(button, row, column)
            button.clicked.connect(partial(self._set_filter, type_name))
            column += 1

        collapse_widget.add_widget(self.search_widget)
        collapse_widget.add_widget(self.filter_widget)
        collapse_widget.add_layout(grid_layout)

        button_layout = QtWidgets.QHBoxLayout()

        select = QtWidgets.QPushButton('Select')
        select.setMinimumHeight(40)

        hier = QtWidgets.QPushButton('Select Hierarchy')
        hier.setMinimumHeight(40)

        button_layout.addWidget(select)
        button_layout.addWidget(hier)

        select.clicked.connect(self._run_search)
        hier.clicked.connect(self._select_hier)


        collapse_widget.collapse_layout.addSpacing(5)
        collapse_widget.add_layout(button_layout)

    def _build_hash_rename(self):
        collapse_widget = custom_widgets.CollapsableSeparator('Hash Rename')
        collapse_widget.set_collapsed(True)

        collapse_widget.collapse_layout.setContentsMargins(2, 2, 2, 2)
        collapse_widget.collapse_layout.setSpacing(1)

        self.section_layout.addWidget(collapse_widget)

        self.rename_text = QtWidgets.QLineEdit()
        self.rename_text.setPlaceholderText('example: arm_##_joint')

        rename_widget = custom_widgets.HashRenameWidget()

        collapse_widget.add_widget(self.rename_text)
        collapse_widget.add_widget(rename_widget)

        rename_widget.rename_clicked.connect(self._rename)

    def _build_mgear_rename(self):
        collapse_widget = custom_widgets.CollapsableSeparator('mGear Guide Rename')
        collapse_widget.set_collapsed(True)

        collapse_widget.collapse_layout.setContentsMargins(2, 2, 2, 2)
        collapse_widget.collapse_layout.setSpacing(1)

        self.section_layout.addWidget(collapse_widget)

        mgear_load = QtWidgets.QPushButton('Load')
        mgear_load.setMinimumWidth(custom_widgets.scale_dpi(100))

        mgear_layout = QtWidgets.QHBoxLayout()

        left_layout = QtWidgets.QVBoxLayout()
        left_layout.setAlignment(QtCore.Qt.AlignRight)

        right_layout = QtWidgets.QVBoxLayout()
        right_layout.setAlignment(QtCore.Qt.AlignLeft)

        name_label = QtWidgets.QLabel('Name:')
        side_label = QtWidgets.QLabel('Side:')
        comp_label = QtWidgets.QLabel('Component Index:')

        left_layout.addWidget(name_label, alignment=QtCore.Qt.AlignRight)
        left_layout.addWidget(side_label, alignment=QtCore.Qt.AlignRight)
        left_layout.addWidget(comp_label, alignment=QtCore.Qt.AlignRight)

        self.inc_checkbox = QtWidgets.QCheckBox('Increment Component')

        self.mgear_name = QtWidgets.QLineEdit()
        self.mgear_side = QtWidgets.QComboBox()
        self.mgear_side.addItem('Center')
        self.mgear_side.addItem('Left')
        self.mgear_side.addItem('Right')
        self.mgear_component_index = QtWidgets.QSpinBox()
        self.mgear_component_index.setMinimum(0)
        self.mgear_component_index.setMaximum(1000)

        right_layout.addWidget(self.mgear_name)
        right_layout.addWidget(self.mgear_side)
        right_layout.addWidget(self.mgear_component_index)

        mgear_layout.addLayout(left_layout)
        mgear_layout.addLayout(right_layout)

        rename_widget = custom_widgets.HashRenameWidget()

        collapse_widget.collapse_layout.addWidget(mgear_load, alignment = QtCore.Qt.AlignCenter)
        collapse_widget.collapse_layout.addSpacing(10)
        collapse_widget.add_layout(mgear_layout)
        collapse_widget.collapse_layout.addSpacing(10)
        collapse_widget.add_widget(self.inc_checkbox)
        collapse_widget.add_widget(rename_widget)

        mgear_load.clicked.connect(self._load_mgear)
        rename_widget.rename_clicked.connect(self._rename_mgear)

    def _build_search_and_replace(self):
        collapse_widget = custom_widgets.CollapsableSeparator('Search and Replace')
        collapse_widget.set_collapsed(True)

        collapse_widget.collapse_layout.setContentsMargins(2, 2, 2, 2)
        collapse_widget.collapse_layout.setSpacing(1)

        self.section_layout.addWidget(collapse_widget)

        self.string_search = custom_widgets.TextEntryWidget('Search\t')
        self.string_search.hide_button(True)

        self.string_replace = custom_widgets.TextEntryWidget('Replace\t')
        self.string_replace.hide_button(True)

        button_layout = QtWidgets.QHBoxLayout()
        replace_first = QtWidgets.QPushButton('Replace First')
        replace_start = QtWidgets.QPushButton('Replace at Start')
        replace_end = QtWidgets.QPushButton('Replace at End')

        button_layout.addWidget(replace_first)
        button_layout.addWidget(replace_start)
        button_layout.addWidget(replace_end)

        replace_first.clicked.connect(self._replace_first)
        replace_start.clicked.connect(self._replace_start)
        replace_end.clicked.connect(self._replace_end)

        collapse_widget.add_widget(self.string_search)
        collapse_widget.add_widget(self.string_replace)
        collapse_widget.add_layout(button_layout)

    def _build_prefix_suffix(self):
        collapse_widget = custom_widgets.CollapsableSeparator('Prefix and Suffix')
        collapse_widget.set_collapsed(True)

        collapse_widget.collapse_layout.setContentsMargins(2, 2, 2, 2)
        collapse_widget.collapse_layout.setSpacing(1)

        self.section_layout.addWidget(collapse_widget)

        self.string_prefix = custom_widgets.TextEntryWidget('Prefix\t')
        self.string_prefix.hide_button(True)

        self.string_suffix = custom_widgets.TextEntryWidget('Suffix\t')
        self.string_suffix.hide_button(True)

        button_layout = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton('Add Prefix/Suffix')
        button_layout.addWidget(add_button)

        add_button.clicked.connect(self._prefix)
        add_button.clicked.connect(self._suffix)

        collapse_widget.add_widget(self.string_prefix)
        collapse_widget.add_widget(self.string_suffix)
        collapse_widget.add_layout(button_layout)

    def _unique_rename(self):
        collapse_widget = custom_widgets.CollapsableSeparator('Unique Rename')
        collapse_widget.set_collapsed(True)

        collapse_widget.collapse_layout.setContentsMargins(2, 2, 2, 2)
        collapse_widget.collapse_layout.setSpacing(1)

        self.section_layout.addWidget(collapse_widget)

        select_nonunique = QtWidgets.QPushButton('Select Non-Unique')
        name_unique = QtWidgets.QPushButton('Name Unique')

        select_nonunique.clicked.connect(self._select_nonunique)
        name_unique.clicked.connect(self._name_unique)

        collapse_widget.add_widget(select_nonunique)
        collapse_widget.add_widget(name_unique)

    def _add_hash_rename_widget(self):
        rename_layout = QtWidgets.QHBoxLayout()

        rename_inc_type = QtWidgets.QComboBox()
        rename_inc_type.addItems(['Start Number', 'Start Letter'])
        rename_inc_type.setMinimumWidth(100)
        rename_inc_type.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                                                 QtWidgets.QSizePolicy.Preferred))
        rename_inc_type.currentIndexChanged.connect(self._current_inc_type_changed)

        inc_string = QtWidgets.QLineEdit()
        inc_string.setPlaceholderText(self.EXAMPLE_INC_NUMBER)
        inc_string.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                                            QtWidgets.QSizePolicy.Preferred))

        rename_button = QtWidgets.QPushButton('Rename')
        rename_button.setSizePolicy(
            QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                  QtWidgets.QSizePolicy.Preferred))

        rename_layout.addWidget(rename_inc_type)
        rename_layout.addWidget(inc_string)
        rename_layout.addWidget(rename_button)

        return rename_button, rename_inc_type, inc_string, rename_layout

    def _set_filter(self, filter_type):
        if filter_type == 'curve':
            filter_type = 'nurbsCurve'
        if filter_type == 'surface':
            filter_type = 'nurbsSurface'
        self.filter_widget.text_entry.setText(filter_type)
        self._run_search()

    def _run_search(self):
        """
        Search selection or all nodes based on the filters in the UI.
        """
        selection = cmds.ls(sl=True)

        search_text = self.search_widget.text()
        filter_text = self.filter_widget.text()

        start_command = 'result = cmds.ls('
        end_command = ')'
        search_command = ''
        alt_search_command = ''
        filter_command = ''
        selection_command = ''

        if search_text:
            search_command = f'"{search_text}",'
            alt_search_command = f'"*{search_text}*",'
        if filter_text:
            filter_command = f'type = "{filter_text}",'
        if selection:
            selection_command = 'sl = True'

        command = f'{start_command}{search_command}{filter_command}{selection_command}{end_command}'
        result = self._run_command(command)
        if not result and alt_search_command:
            command2 = f'{start_command}{alt_search_command}{filter_command}{selection_command}{end_command}'
            result = self._run_command(command2)
        if not result and selection_command:
            command3 = f'{start_command}{alt_search_command}{filter_command}{end_command}'
            result = self._run_command(command3)

        if result:
            cmds.select(result)
        else:
            cmds.select(cl=True)

    def _run_command(self, command):
        result = []
        env = {'cmds': cmds}
        try:
            exec(command, env)
        except:
            pass
        if 'result' in env:
            result = env['result']

        return result

    @DECORATORS.undo
    def _rename(self, current_inc_type, inc_string):
        """
        Rename selected nodes based on hash char

        """
        rename_text = self.rename_text.text()
        new_name, index_value, new_current_inc_type = self._handle_rename(rename_text, current_inc_type, inc_string)
        self._rename_selection(new_name, rename_text, index_value, new_current_inc_type)

    def _rename_mgear(self, current_inc_type, inc_string):

        inc_component = self.inc_checkbox.isChecked()

        name = self.mgear_name.text()
        if not name:
            return

        if name.find('#') < 0:
            name += '#'

        side = self.mgear_side.currentText()
        side = side[0]
        component_value = self.mgear_component_index.value()

        new_name, index_value, inc_type = self._handle_rename(name, current_inc_type, inc_string)
        mgear_name = f'{new_name}_{side}{component_value}_root'

        comp_inst = guide.ComponentGuide()
        roots = guide_utils.find_mgear_roots_from_selection()

        pm_roots = []
        for root in roots:
            root_node = pm.PyNode(root)
            result = comp_inst.rename(root_node, new_name, side, 999)
            pm_roots.append(root_node)

        for root_node in pm_roots:
            if not inc_component:
                new_name = self._convert_hash_character_to_index(name, index_value, inc_type)

                inc = 0
                while cmds.objExists(mgear_name):
                    index_value += 1
                    new_name = self._convert_hash_character_to_index(name, index_value, inc_type)
                    mgear_name = f'{new_name}_{side}{component_value}_root'
                    if inc > 5000:
                        break

            comp_inst.rename(root_node, new_name, side, component_value)

    def _handle_rename(self, rename_text, current_inc_type, inc_string):

        index_value = 1

        if not rename_text.find('#') > -1:
            return None,None,None

        if current_inc_type == 0:
            if not inc_string:
                inc_string = '1'

            if inc_string.isdigit():
                index_value = int(inc_string)
            else:
                index_value = self.letters_to_number(inc_string)

        if current_inc_type == 1:
            if not inc_string:
                inc_string = 'A'

            if inc_string.isupper():
                current_inc_type = 2

            hash_count = rename_text.count('#')
            string_count = len(inc_string)

            index_value = self.letters_to_number(inc_string)
            orig_index_value = index_value

            start_index = sum(26 ** i for i in range(1, hash_count))
            if index_value >= start_index:
                index_value = index_value - start_index

            if hash_count != string_count:
                if string_count > 1 and string_count < hash_count:
                    index_value -= sum(26 ** i for i in range(1, string_count))

        new_name = self._convert_hash_character_to_index(rename_text, index_value, current_inc_type)
        return new_name, index_value, current_inc_type

    def _rename_selection(self, new_name, rename_text, index_value, current_inc_type):
        selection = cmds.ls(sl=True, uuid=True)

        for uuid in selection:
            long_name = cmds.ls(uuid, l=True)
            cmds.rename(long_name, uuid) #rename to uuid for uniqness before renaming again

        for uuid in selection:

            while cmds.objExists(new_name):
                index_value += 1

                new_name = self._convert_hash_character_to_index(rename_text, index_value, current_inc_type)

                if index_value > 5000:
                    break
            long_name = cmds.ls(uuid, l=True)
            cmds.rename(long_name, new_name)

    def _convert_hash_character_to_index(self, name, index_value, increment_type=0):
        """
        Converts # to character represented by index value.
        increment_type 0 = unsigned integer
        increment_type 1 = lowercase base-26 alphabet
        increment_type 2 = uppercase base-26 alphabet
        Args:
            name: The name to reformat
            index_value: The index to reformat with
            increment_type: the increment type, determines what type of alphanumeric to increment.

        Returns:

        """

        new_name = name

        if increment_type == 0:
            new_name = re.sub(r'#+', lambda m: f"{index_value:0{len(m.group())}d}", name)
        elif increment_type == 1:
            new_name = re.sub(r'#+', lambda m: self.number_to_letters(index_value, len(m.group()), capital=False), name)
        elif increment_type == 2:
            new_name = re.sub(r'#+', lambda m: self.number_to_letters(index_value, len(m.group()), capital=True), name)

        return new_name

    def _load_mgear(self):

        found = guide_utils.find_mgear_roots_from_selection()

        if not found:
            return

        sides = {'C':0,'L':1, 'R':2}

        mgear_root = found[0]
        mgear_name =  cmds.getAttr(f'{mgear_root}.comp_name')
        mgear_side = cmds.getAttr(f'{mgear_root}.comp_side')
        mgear_index = cmds.getAttr(f'{mgear_root}.comp_index')

        mgear_side = sides.get(mgear_side, 0)

        self.mgear_name.setText(mgear_name)
        self.mgear_side.setCurrentIndex(mgear_side)
        self.mgear_component_index.setValue(mgear_index)


    def number_to_letters(self, index, length, capital=True):
        """
        Converts a number to base-26 Excel-style letters and pads to desired length.
        """
        result = ""

        char_base = ord('A') if capital else ord('a')

        offset = sum(26 ** i for i in range(1, length))
        n = index + offset

        while n >= 0:
            result = chr(n % 26 + char_base) + result
            n = n // 26 - 1

        if len(result) < length:
            result = result.rjust(length, chr(char_base))
        return result

    def letters_to_number(self, letters):
        """
        Converts a base-26 Excel-style lowercase letter string to a zero-based integer.
        For example:
            'a'  -> 0
            'z'  -> 25
            'aa' -> 26
            'ab' -> 27
        """
        letters = letters.lower()
        value = 0
        for char in letters:
            value = value * 26 + (ord(char) - ord('a') + 1)
        return value - 1  # Convert to zero-based

    def _select_hier(self):
        filter_text = self.filter_widget.text()
        if filter_text:
            selection = cmds.ls(sl=True, type=filter_text)
        else:
            selection = cmds.ls(sl=True)
        if not selection:
            return

        cmds.select(selection, hi=True)

        if filter_text:
            filter_selection = cmds.ls(sl=True, type=filter_text)
            cmds.select(filter_selection)

    def _current_inc_type_changed(self, index):
        self.inc_string.setText('')
        if index == 0:
            self.inc_string.setPlaceholderText(self.EXAMPLE_INC_NUMBER)
        if index == 1:
            self.inc_string.setPlaceholderText(self.EXAMPLE_INC_STRING)

    @DECORATORS.undo
    def _replace_first(self):

        nodes_uuid = cmds.ls(sl=True, uuid=True)

        if not nodes_uuid:
            return

        search = str(self.string_search.text())
        replace = str(self.string_replace.text())

        if not any([search, replace]):
            return

        new_name_dict = {}

        for uuid in nodes_uuid:
            long_name = cmds.ls(uuid, uuid=True)[0]
            short_name = long_name.split('|')[-1]

            if short_name.find(search) > -1:
                short_name = short_name.replace(search, replace, 1)
            else:
                continue

            new_name_dict[uuid] = short_name
            cmds.rename(long_name, rig_utils.get_unique_name(short_name))

    @DECORATORS.undo
    def _replace_start(self):

        nodes_uuid = cmds.ls(sl=True, uuid=True)

        if not nodes_uuid:
            return

        search = str(self.string_search.text())
        replace = str(self.string_replace.text())

        if not any([search, replace]):
            return

        new_name_dict = {}

        for uuid in nodes_uuid:
            long_name = cmds.ls(uuid, uuid=True)[0]
            short_name = long_name.split('|')[-1]

            if short_name.startswith(search):
                short_name = short_name.replace(search, replace, 1)
            else:
                continue

            new_name_dict[uuid] = short_name
            cmds.rename(long_name, rig_utils.get_unique_name(short_name))

    @DECORATORS.undo
    def _replace_end(self):
        nodes_uuid = cmds.ls(sl=True, uuid=True)

        if not nodes_uuid:
            return

        search = str(self.string_search.text())
        replace = str(self.string_replace.text())

        if not any([search, replace]):
            return

        new_name_dict = {}

        for uuid in nodes_uuid:
            long_name = cmds.ls(uuid, uuid=True)[0]
            short_name = long_name.split('|')[-1]

            if short_name.endswith(search):
                short_name = short_name[:-len(search)] + replace
            else:
                continue

            new_name_dict[uuid] = short_name
            cmds.rename(long_name, rig_utils.get_unique_name(short_name))

    @DECORATORS.undo
    def _prefix(self):
        nodes_uuid = cmds.ls(sl=True, uuid=True)

        if not nodes_uuid:
            return

        prefix = str(self.string_prefix.text())

        if not prefix:
            return

        new_name_dict = {}

        for uuid in nodes_uuid:
            long_name = cmds.ls(uuid, uuid=True)[0]
            short_name = long_name.split('|')[-1]

            if not short_name.startswith(prefix):
                short_name = prefix + short_name
            else:
                continue

            new_name_dict[uuid] = short_name
            cmds.rename(long_name, rig_utils.get_unique_name(short_name))

    @DECORATORS.undo
    def _suffix(self):
        nodes_uuid = cmds.ls(sl=True, uuid=True)

        if not nodes_uuid:
            return

        suffix = str(self.string_suffix.text())

        if not suffix:
            return

        new_name_dict = {}

        for uuid in nodes_uuid:
            long_name = cmds.ls(uuid, uuid=True)[0]
            short_name = long_name.split('|')[-1]

            if not short_name.endswith(suffix):
                short_name = short_name + suffix
            else:
                continue

            new_name_dict[uuid] = short_name
            cmds.rename(long_name, rig_utils.get_unique_name(short_name))

    def _select_nonunique(self):
        transforms = cmds.ls(type='transform')

        non_unique = []

        if transforms:
            for transform in transforms:
                if transform.find("|") > -1:
                    non_unique.append(transform)
        else:
            cmds.warning("No Object in Selection")

        cmds.select(non_unique)

    @DECORATORS.undo
    def _name_unique(self):
        nodes_uuid = cmds.ls(sl=True, uuid=True, type='transform')

        if not nodes_uuid:
            return

        for uuid in nodes_uuid:
            long_name = cmds.ls(uuid, uuid=True)[0]
            short_name = long_name.split('|')[-1]
            long_name = cmds.rename(long_name, 'temp1341234')

            cmds.rename(long_name, rig_utils.get_unique_name(short_name))

    def _add_separator(self):
        separator = QtWidgets.QFrame()
        separator.setFixedSize(self.SEP_SIZE[0], self.SEP_SIZE[1])
        separator.setFrameStyle(QtWidgets.QFrame.HLine)
        separator.setStyleSheet(SEP_SYTLE_SHEET)
        self.main_layout.addWidget(separator)


def show():
    global WINDOW
    maya_window = get_maya_window()
    if WINDOW:
        WINDOW.close()
    WINDOW = ToolRenamer(maya_window)
    WINDOW.show()
