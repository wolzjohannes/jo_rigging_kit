# Import built-in modules
import os

# Import third-party modules
from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets
import pymel.core as pmc
from pixo_paths import normalize

# Import local modules
from pxo_rigging_kit.maya_utils.guis import SEP_SYTLE_SHEET
from pxo_rigging_kit.maya_utils.guis import STYLE_SHEET
from pxo_rigging_kit.maya_utils.guis import get_maya_window
import rig_fbx_export

#######################################################
# GLOBALS
#######################################################

WINDOW = None

#######################################################
# CLASSES
#######################################################

class FBXexporter(QtWidgets.QMainWindow):
    """
    FBX exporter.
    """
    TITEL = "FBX exporter"
    FIXED_WINDOW_SIZE = [400, 600]
    SEP_SIZE = FIXED_WINDOW_SIZE[0] - 20, 2
    PUSH_BUTTON_HIGHT = 25
    COMBO_BOX_MINIMAL_HIGHT = 25
    PUBLIS_SAFE_MODE = "Safe"
    PUBLISH_UNSAFE_MODE = "Unsafe"
    RIG_ICON = "pxoAsset_rig_icon.PNG"
    ICON_PATH = os.path.split(__file__)[0]

    def __init__(self, parent=None):
        super(FBXexporter, self).__init__()
        self.win = self
        self.win.setParent(parent)
        self.win.setWindowTitle(self.TITEL)
        self.win.setWindowFlags(QtCore.Qt.Window)
        self.win.setFixedSize(
            self.FIXED_WINDOW_SIZE[0], self.FIXED_WINDOW_SIZE[1]
        )
        self.setStyleSheet(self._format_general_style(STYLE_SHEET))
        self.QFrame = QtWidgets.QFrame(self.win)
        self.QFrame.setFixedSize(
            self.FIXED_WINDOW_SIZE[0], self.FIXED_WINDOW_SIZE[1]
        )
        self.QVBoxLayout = QtWidgets.QVBoxLayout()
        self.QLabel = QtWidgets.QLabel()
        self.QLabel.setText("Scene Rig assets")
        self.Qframe_sep_0 = QtWidgets.QFrame()
        self.Qframe_sep_0.setFixedSize(self.SEP_SIZE[0], self.SEP_SIZE[1])
        self.Qframe_sep_0.setFrameStyle(QtWidgets.QFrame.HLine)
        self.Qframe_sep_0.setStyleSheet(SEP_SYTLE_SHEET)
        self.Qframe_sep_1 = QtWidgets.QFrame()
        self.Qframe_sep_1.setFixedSize(self.SEP_SIZE[0], self.SEP_SIZE[1])
        self.Qframe_sep_1.setFrameStyle(QtWidgets.QFrame.HLine)
        self.Qframe_sep_1.setStyleSheet(SEP_SYTLE_SHEET)
        self.Qframe_sep_4 = QtWidgets.QFrame()
        self.Qframe_sep_4.setFixedSize(self.SEP_SIZE[0], self.SEP_SIZE[1])
        self.Qframe_sep_4.setFrameStyle(QtWidgets.QFrame.HLine)
        self.Qframe_sep_4.setStyleSheet(SEP_SYTLE_SHEET)
        self.QListWidget_0 = QtWidgets.QListWidget()
        self.QListWidget_0.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.QLabel_1 = QtWidgets.QLabel()
        self.QLabel_1.setText("Time range -- Start --")
        self.QLabel_2 = QtWidgets.QLabel()
        self.QLabel_2.setText("Time range -- End --")
        self.QLabel_3 = QtWidgets.QLabel()
        self.QLabel_3.setText("Export Mode")
        self.QSpinBox_0 = QtWidgets.QSpinBox()
        self.QSpinBox_0.setMinimumHeight(self.COMBO_BOX_MINIMAL_HIGHT)
        self.QSpinBox_0.setRange(0,100000)
        self.QSpinBox_1 = QtWidgets.QSpinBox()
        self.QSpinBox_1.setMinimumHeight(self.COMBO_BOX_MINIMAL_HIGHT)
        self.QSpinBox_1.setRange(0,100000)
        self.QComboBox_2 = QtWidgets.QComboBox()
        self.QComboBox_2.setMinimumHeight(self.COMBO_BOX_MINIMAL_HIGHT)
        self.QPushButton = QtWidgets.QPushButton()
        self.QPushButton.setText("Set from scene")
        self.QPushButton.setMinimumHeight(self.PUSH_BUTTON_HIGHT)
        self.QPushButton_0 = QtWidgets.QPushButton()
        self.QPushButton_0.setText(
            "Export"
        )
        self.QPushButton_0.setMinimumHeight(self.PUSH_BUTTON_HIGHT)
        self.QVBoxLayout.addWidget(self.QLabel)
        self.QVBoxLayout.addWidget(self.Qframe_sep_0)
        self.QVBoxLayout.addWidget(self.QListWidget_0)
        self.QVBoxLayout.addWidget(self.Qframe_sep_1)
        self.QVBoxLayout.addWidget(self.QLabel_1)
        self.QVBoxLayout.addWidget(self.QSpinBox_0)
        self.QVBoxLayout.addWidget(self.QLabel_2)
        self.QVBoxLayout.addWidget(self.QSpinBox_1)
        self.QVBoxLayout.addWidget(self.QPushButton)
        self.QVBoxLayout.addWidget(self.Qframe_sep_4)
        self.QVBoxLayout.addWidget(self.QLabel_3)
        self.QVBoxLayout.addWidget(self.QComboBox_2)
        self.QVBoxLayout.addWidget(self.QPushButton_0)
        self.QFrame.setLayout(self.QVBoxLayout)
        self._fill_scene_rigs_list()
        self._set_time_range_from_scene()
        self._fill_export_mode_combo_box()
        self.connect_signals()

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
        return style_string

    def _fill_scene_rigs_list(self):
        """
        Fill the scene rigs list view.

        Args:
            items_list(list):  List filled with strings.
        """
        item_icon_path = normalize(os.path.join(self.ICON_PATH, self.RIG_ICON))
        for item in [node.name() for node in rig_fbx_export.get_rig_assets()]:
            icon = QtGui.QIcon()
            icon.addFile(item_icon_path)
            item_widget = QtWidgets.QListWidgetItem()
            item_widget.setIcon(icon)
            item_widget.setText(item)
            item_widget.setSizeHint(QtCore.QSize(25, 25))
            self.QListWidget_0.addItem(item_widget)

    def _set_time_range_from_scene(self):
        """
        Will set the time range from the scene timeline in maya
        """
        self.QSpinBox_0.setValue(pmc.playbackOptions(query=True, min=True))
        self.QSpinBox_1.setValue(pmc.playbackOptions(query=True, max=True))

    def _fill_export_mode_combo_box(self):
        """
        Fill the export mode combox.
        Which defines if we publish the current guides in safe or unsafe mode
        """
        publish_modes = [self.PUBLIS_SAFE_MODE, self.PUBLISH_UNSAFE_MODE]
        self.QComboBox_2.addItems(publish_modes)
        self.QComboBox_2.setCurrentIndex(0)

    def _get_export_mode(self):
        """
        Get the publish mode from publish mode ComboBox.
        """
        if self.QComboBox_2.currentText() == "Safe":
            return True
        else:
            return False

    def connect_signals(self):
        """
        Connect all signals.
        """
        self.QPushButton.clicked.connect(self._set_time_range_from_scene)
        self.QPushButton_0.clicked.connect(self.export)

    def export(self):
        """
        Export the fbx data.
        """
        selected_list_items = [pmc.PyNode(item.text()) for item in self.QListWidget_0.selectedItems()]
        time_range = [int(self.QSpinBox_0.text()), int(self.QSpinBox_1.text())]
        publish_mode = self._get_export_mode()
        rig_fbx_export.execute_fbx_export(selected_list_items, time_range, publish_mode)

def show():
    global WINDOW
    maya_window = get_maya_window()
    if WINDOW:
        WINDOW.close()
    WINDOW = FBXexporter(maya_window)
    WINDOW.show()
