# Import built-in modules
import os

import logging

# Import third-party modules
try:
    from PySide6 import QtCore
    from PySide6 import QtGui
    from PySide6 import QtWidgets
except ImportError:
    from PySide2 import QtCore
    from PySide2 import QtGui
    from PySide2 import QtWidgets

# Import local modules
from pxo_rigging_kit import constants
from pxo_rigging_kit.maya_utils.guis import STYLE_SHEET
from pxo_rigging_kit.maya_utils.guis import SEP_SYTLE_SHEET
from pxo_rigging_kit.maya_utils.guis import get_maya_window
from pxo_rigging_kit.maya_utils.guis import scale_px_values
from pxo_rigging_kit.maya_utils.guis import scale_dpi
from pxo_rigging_kit.maya_utils.guis import custom_widgets
from pxo_rigging_kit.maya_utils.mgear import guide_utils

#######################################################
# GLOBALS
#######################################################

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)
_UI_LOGGER = logging.getLogger()
_UI_LOGGER.setLevel(logging.INFO)
ui_interesting = {'ui': 'interesting'}
WINDOW = None


#######################################################
# CLASSES
#######################################################


class TransferGuides(QtWidgets.QMainWindow):
    """
    Guides Template Manager.
    """
    TITLE = "Transfer Guides"
    FIXED_WINDOW_SIZE = [450, 650]
    SEP_SIZE = FIXED_WINDOW_SIZE[0] - 20, 2
    MAYA_CHECK_ICON = 'check_inv.png'

    def __init__(self, parent=None):
        super(TransferGuides, self).__init__()

        self.win = self
        self.win.setParent(parent)
        self.win.setWindowTitle(self.TITLE)
        self.win.setWindowFlags(QtCore.Qt.Window)
        self.win.setFixedSize(
            self.FIXED_WINDOW_SIZE[0], self.FIXED_WINDOW_SIZE[1]
        )

        self.log_handler = RuntimeLog()
        _UI_LOGGER.addHandler(self.log_handler)

        self.log_handler.log_signal.signal.connect(self._handle_log)

        self.setStyleSheet(self._format_general_style(STYLE_SHEET))

        self.QFrame = QtWidgets.QFrame(self.win)
        self.QFrame.setFixedSize(
            self.FIXED_WINDOW_SIZE[0], self.FIXED_WINDOW_SIZE[1]
        )

        self.main_widget = QtWidgets.QFrame(self.win)
        self.main_widget.setFixedSize(
            self.FIXED_WINDOW_SIZE[0], self.FIXED_WINDOW_SIZE[1]
        )

        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setAlignment(QtCore.Qt.AlignCenter)

        self.main_widget.setLayout(self.main_layout)

        self.setCentralWidget(self.main_widget)

        self._build_widgets()
        self._connect_signals()

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

        icon_file = TransferGuides.MAYA_CHECK_ICON
        icon_path = os.path.join(constants.ICONS_PATH, icon_file)
        icon_path = icon_path.replace("\\", "/")

        style_string = style_string.replace('CHECK_ICON', icon_path)

        return style_string

    def _build_widgets(self):
        title_label = QtWidgets.QLabel('Transfer Guides')

        self.main_layout.addWidget(title_label)
        self._add_separator()

        self.tabs = QtWidgets.QTabWidget()

        generic_transfer_widget = QtWidgets.QWidget()
        generic_transfer_layout = QtWidgets.QVBoxLayout()
        generic_transfer_widget.setLayout(generic_transfer_layout)

        generic_hint_label = QtWidgets.QLabel()
        generic_hint_label.setText("Source workfile topo must match.\n"
                                   "Before Transfer:\n"
                                   "Reference target asset model and save.")




        asset_name = os.environ['PXO_ASSET']
        source_label = QtWidgets.QLabel(f'Source Asset Path:')
        current_asset_label = QtWidgets.QLabel(f'Current Target: {asset_name}')
        #generic_transfer_layout.addWidget(current_asset_label)

        generic_text = guide_utils.get_generic()

        self.source_text = custom_widgets.TextEntryWidget()
        self.source_text.set_text(generic_text)
        self.source_text.hide_button(True)

        source_dir_button = QtWidgets.QPushButton('Dir')
        source_dir_button.clicked.connect(self.get_path)

        self.source_text.main_layout.addWidget(source_dir_button)

        generic_transfer_layout.addWidget(generic_hint_label)
        self._add_separator(generic_transfer_layout)
        generic_transfer_layout.addWidget(source_label)
        generic_transfer_layout.addWidget(self.source_text)
        generic_transfer_layout.addWidget(current_asset_label)


        self.generic_target_guide_entry, self.generic_target_mesh_entry, target_combo = self._add_combo('TARGET', generic_transfer_layout)
        self.generic_target_guide_entry.text_entry.setPlaceholderText('Optional')
        self.generic_target_mesh_entry.text_entry.setPlaceholderText('Optional')

        source_target_widget = QtWidgets.QWidget()
        source_target_layout = QtWidgets.QVBoxLayout()
        source_target_widget.setLayout(source_target_layout)

        hint_label = QtWidgets.QLabel()
        hint_label.setText("Provide Source and Target guide group.\nSource/Target topology must match.")

        source_target_layout.addWidget(hint_label)
        self._add_separator(source_target_layout)

        self.source_guide_entry, self.source_mesh_entry, source_combo = self._add_combo('SOURCE', source_target_layout)
        self.target_guide_entry, self.target_mesh_entry, target_combo = self._add_combo('TARGET', source_target_layout)

        tool_widget = self._create_tool_widget()

        self.tabs.addTab(generic_transfer_widget, 'Generic')
        self.tabs.addTab(source_target_widget, 'Source Target')
        self.tabs.addTab(tool_widget, 'Tools')

        self.main_layout.addWidget(self.tabs)

        self.alignment_fix_checkbox = QtWidgets.QCheckBox('Alignment Fixes')
        self.alignment_fix_checkbox.setChecked(True)

        delta_layout = QtWidgets.QHBoxLayout()
        self.delta_mush_fix_checkbox = QtWidgets.QCheckBox('Delta Mush Fix')
        self.delta_mush_fix_checkbox.setChecked(False)

        delta_label = QtWidgets.QLabel('Iterations')

        self.delta_mush_iterations = QtWidgets.QSpinBox()
        self.delta_mush_iterations.setMinimum(100)
        self.delta_mush_iterations.setMaximum(5000)
        self.delta_mush_iterations.setValue(1000)
        self.delta_mush_iterations.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)

        delta_layout.addWidget(self.delta_mush_fix_checkbox)
        delta_layout.addWidget(self.delta_mush_iterations)
        delta_layout.addWidget(delta_label)

        self.transfer_button = QtWidgets.QPushButton('Transfer')

        self._add_separator()

        self.transfer_widget = QtWidgets.QWidget()
        transfer_layout = QtWidgets.QVBoxLayout()
        self.transfer_widget.setLayout(transfer_layout)

        transfer_layout.addWidget(self.alignment_fix_checkbox)
        transfer_layout.addLayout(delta_layout)

        transfer_layout.addWidget(self.transfer_button)

        self.main_layout.addWidget(self.transfer_widget)

        self.log_text = QtWidgets.QListWidget()

        self.main_layout.addWidget(self.log_text)

    def _reset_log_list(self):
        self.log_text.clear()
        self.repaint()

    def _connect_signals(self):
        self.transfer_button.clicked.connect(self._transfer)
        self.tabs.currentChanged.connect(self._tab_changed)

    def _tab_changed(self):
        if self.tabs.currentIndex() == 2:
            self.transfer_widget.hide()
        else:
            self.transfer_widget.show()

    def _create_tool_widget(self):

        tool_widget = QtWidgets.QWidget()
        tool_layout = QtWidgets.QVBoxLayout()

        tool_widget.setLayout(tool_layout)

        align_selected = QtWidgets.QPushButton('Align Selected')
        align_body = QtWidgets.QPushButton('Align Body')
        self._add_separator()
        remove_facial = QtWidgets.QPushButton('Remove Facial Extras')

        tool_layout.addStretch()
        tool_layout.addWidget(align_selected)
        tool_layout.addWidget(align_body)
        tool_layout.addSpacing(10)
        tool_layout.addWidget(remove_facial)
        tool_layout.addStretch()

        align_selected.clicked.connect(self._align_selected)
        align_body.clicked.connect(self._align_body)
        remove_facial.clicked.connect(self._remove_facial)

        return tool_widget


    def _add_combo(self, title, parent):
        group = QtWidgets.QGroupBox(title)
        group_layout = QtWidgets.QVBoxLayout()
        group_layout.setAlignment(QtCore.Qt.AlignCenter)
        group.setLayout(group_layout)

        guide_entry = custom_widgets.TextEntryWidget('Guide\t')
        mesh_entry = custom_widgets.TextEntryWidget('Mesh\t')

        group_layout.addWidget(guide_entry, alignment=QtCore.Qt.AlignTop)
        group_layout.addWidget(mesh_entry, alignment=QtCore.Qt.AlignTop)

        parent.addWidget(group)

        return guide_entry, mesh_entry, group

    def _add_separator(self, parent = None):
        separator = QtWidgets.QFrame()
        separator.setFixedSize(self.SEP_SIZE[0], self.SEP_SIZE[1])
        separator.setFrameStyle(QtWidgets.QFrame.HLine)
        separator.setStyleSheet(SEP_SYTLE_SHEET)

        if not parent:
            parent = self.main_layout

        parent.addWidget(separator)

    def _transfer(self):
        tab_index = self.tabs.currentIndex()
        self._reset_log_list()

        if tab_index == 0:
            self._transfer_generic()
        if tab_index == 1:
            self._transfer_source_target()

    def _transfer_generic(self):
        target_mesh = self.generic_target_mesh_entry.text()
        target_guide = self.generic_target_guide_entry.text()

        alignment_fix = self.alignment_fix_checkbox.isChecked()
        delta_mush_fix = self.delta_mush_fix_checkbox.isChecked()
        delta_mush_iterations = self.delta_mush_iterations.value()

        source_path = self.source_text.text()

        guide_utils.transfer_generic(source_path, target_mesh, target_guide, alignment_fix, delta_mush_fix, delta_mush_iterations)

    def _transfer_source_target(self):
        source_guide = self.source_guide_entry.text()
        source_mesh = self.source_mesh_entry.text()
        target_guide = self.target_guide_entry.text()
        target_mesh = self.target_mesh_entry.text()

        alignment_fix = self.alignment_fix_checkbox.isChecked()
        delta_mush_fix = self.delta_mush_fix_checkbox.isChecked()
        delta_mush_iterations = self.delta_mush_iterations.value()

        transfer_inst = guide_utils.TransferGuides()
        transfer_inst.set_source(source_guide, source_mesh)
        transfer_inst.set_target(target_guide, target_mesh)
        transfer_inst.set_delta_mush_fix(delta_mush_fix, delta_mush_iterations)
        transfer_inst.set_alignment_fix(alignment_fix)
        transfer_inst.transfer()

    def _align_selected(self):
        self._reset_log_list()

        roots = guide_utils.find_mgear_roots_from_selection()

        if roots:
            guide_utils.align_components(roots)
        else:
            _LOGGER.warning('No guides selected.', extra=ui_interesting)


    def _align_body(self):
        self._reset_log_list()

        guide_utils.align_body()

    def _remove_facial(self):
        self._reset_log_list()

        guide_utils.remove_facial()

    def _handle_log(self, message):
        item = QtWidgets.QListWidgetItem(message)
        self.log_text.addItem(item)
        self.log_text.scrollToItem(item)
        self.repaint()

    def get_path(self):
        current_path = self.source_text.text()
        filepath = QtWidgets.QFileDialog.getOpenFileName(self, 'Maya File', current_path, 'Maya File (*.ma *.mb)')
        if filepath:
            self.source_text.set_text(filepath[0])

class SignalLog(QtCore.QObject):
    signal = QtCore.Signal(object)

class RuntimeLog(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []  # store LogRecord objects
        self.log_signal = SignalLog()

    def emit(self, record):
        level_name = record.levelname
        print('level name', level_name)
        if hasattr(record, 'ui'):
            ui_interesting = getattr(record, 'ui')
            if ui_interesting:

                log_message = self.format(record)
                if level_name == 'WARNING':
                    log_message = 'WARNING! ' + log_message

                self.records.append(log_message)  # store formatted message
                self.log_signal.signal.emit(self.records[-1])


def show():
    global WINDOW
    maya_window = get_maya_window()
    if WINDOW:
        WINDOW.close()
    WINDOW = TransferGuides(maya_window)
    WINDOW.show()
