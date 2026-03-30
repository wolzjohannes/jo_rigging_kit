# Import built-in modules
import os
import pathlib

# Import third-party modules
try:
    from PySide6 import QtCore
    from PySide6 import QtGui
    from PySide6 import QtWidgets
except ImportError:
    from PySide2 import QtCore
    from PySide2 import QtGui
    from PySide2 import QtWidgets
from mgear.shifter import io
import pymel.core as pmc

# Import local modules
from pxo_rigging_kit import constants
from pxo_rigging_kit.maya_utils.guis import SEP_SYTLE_SHEET
from pxo_rigging_kit.maya_utils.guis import STYLE_SHEET
from pxo_rigging_kit.maya_utils.guis import get_maya_window
from pxo_rigging_kit.maya_utils.mgear import guide_utils


#######################################################
# GLOBALS
#######################################################

WINDOW = None

#######################################################
# CLASSES
#######################################################


class GuidesManager(QtWidgets.QMainWindow):
    """
    Guides Template Manager.
    """

    ASSET_REF_NAME = "Current Asset Context"
    COMBO_BOX_MINIMAL_HEIGHT = 25
    FIXED_WINDOW_SIZE = [400, 600]
    MAYA_FILE_FORMAT_ICON = "guides_manager_maya_icon.png"
    MGEAR_FILE_FORMAT_ICON = "guides_manager_sgt_icon.png"
    PUSH_BUTTON_HEIGHT = 25
    REPO_REF_NAME = "Repository"
    PUBLISH_SAFE_MODE = "Safe"
    PUBLISH_UNSAFE_MODE = "Unsafe"
    SEP_SIZE = FIXED_WINDOW_SIZE[0] - 20, 2
    TITLE = "Guides Template Manager"

    def __init__(self, parent=None):
        super(GuidesManager, self).__init__()

        self.file_format = "sgt"
        self.source_type = self.REPO_REF_NAME
        self.publish_mode = True
        self.asset_name = None
        self.win = self
        self.win.setParent(parent)
        self.win.setWindowTitle(self.TITLE)
        self.win.setWindowFlags(QtCore.Qt.Window)
        self.win.setFixedSize(
            self.FIXED_WINDOW_SIZE[0], self.FIXED_WINDOW_SIZE[1]
        )

        self.QFrame = QtWidgets.QFrame(self.win)
        self.QFrame.setFixedSize(
            self.FIXED_WINDOW_SIZE[0], self.FIXED_WINDOW_SIZE[1]
        )
        self.QVBoxLayout = QtWidgets.QVBoxLayout()
        self.QLabel = QtWidgets.QLabel(text="Guides Templates List")

        self.seperator_0 = QtWidgets.QFrame()
        self.seperator_0.setFixedSize(self.SEP_SIZE[0], self.SEP_SIZE[1])
        self.seperator_0.setFrameStyle(QtWidgets.QFrame.HLine)
        self.seperator_0.setStyleSheet(SEP_SYTLE_SHEET)

        self.seperator_2 = QtWidgets.QFrame()
        self.seperator_2.setFixedSize(self.SEP_SIZE[0], self.SEP_SIZE[1])
        self.seperator_2.setFrameStyle(QtWidgets.QFrame.HLine)
        self.seperator_2.setStyleSheet(SEP_SYTLE_SHEET)

        self.Qframe_sep_4 = QtWidgets.QFrame()
        self.Qframe_sep_4.setFixedSize(self.SEP_SIZE[0], self.SEP_SIZE[1])
        self.Qframe_sep_4.setFrameStyle(QtWidgets.QFrame.HLine)
        self.Qframe_sep_4.setStyleSheet(SEP_SYTLE_SHEET)

        self.QListWidget_0 = QtWidgets.QListWidget()
        self.QLabel_1 = QtWidgets.QLabel(text="Guides source")

        self.QComboBox_0 = QtWidgets.QComboBox()
        self.QComboBox_0.setMinimumHeight(self.COMBO_BOX_MINIMAL_HEIGHT)

        self.QLabel_3 = QtWidgets.QLabel(text="Publish Mode")

        self.publish_type_choice = QtWidgets.QLabel(text="File Type")

        self.file_type_options = QtWidgets.QComboBox()
        self.file_type_options.setMinimumHeight(self.COMBO_BOX_MINIMAL_HEIGHT)

        self.QComboBox_2 = QtWidgets.QComboBox()
        self.QComboBox_2.setMinimumHeight(self.COMBO_BOX_MINIMAL_HEIGHT)

        self.QPushButton = QtWidgets.QPushButton(text="Import")

        self.QPushButton.setMinimumHeight(self.PUSH_BUTTON_HEIGHT)

        self.publish_button = QtWidgets.QPushButton(text="Publish scene guide to current asset context")

        self.publish_button.setMinimumHeight(self.PUSH_BUTTON_HEIGHT)

        self.QVBoxLayout.addWidget(self.publish_type_choice)

        self.QVBoxLayout.addWidget(self.file_type_options)
        self.QVBoxLayout.addWidget(self.QLabel)
        self.QVBoxLayout.addWidget(self.seperator_0)
        self.QVBoxLayout.addWidget(self.QListWidget_0)
        self.QVBoxLayout.addWidget(self.seperator_2)
        self.QVBoxLayout.addWidget(self.QLabel_1)
        self.QVBoxLayout.addWidget(self.QComboBox_0)
        self.QVBoxLayout.addWidget(self.QPushButton)
        self.QVBoxLayout.addWidget(self.Qframe_sep_4)
        self.QVBoxLayout.addWidget(self.QLabel_3)
        self.QVBoxLayout.addWidget(self.QComboBox_2)
        self.QVBoxLayout.addWidget(self.publish_button)

        self.QFrame.setLayout(self.QVBoxLayout)

        self.setStyleSheet(self._format_general_style(STYLE_SHEET))

        self.fill_guides_list()
        self._fill_source_combo_box()
        self._fill_file_type_combox_box()
        self._fill_publish_mode_combo_box()
        self.connect_signals()

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
        return style_string

    def _fill_guides_list(self, items_list):
        """
        Fill the guides list view.

        Args:
            items_list(list):  List filled with strings.
        """
        icon_file = self.MAYA_FILE_FORMAT_ICON
        if self.file_format == "sgt":
            icon_file = self.MGEAR_FILE_FORMAT_ICON
        item_icon_path = os.path.join(constants.ICONS_PATH, icon_file)
        for item in items_list:
            icon = QtGui.QIcon()
            icon.addFile(item_icon_path)

            item_widget = QtWidgets.QListWidgetItem()
            item_widget.setIcon(icon)
            item_widget.setText(item)
            item_widget.setSizeHint(QtCore.QSize(25, 25))
            self.QListWidget_0.addItem(item_widget)

    def _fill_guides_list_from_asset(self):
        """
        Fill guides list view with all found templates saved in current asset context.
        """
        guides_data_dict = guide_utils.get_guide_templates_from_asset_context(
            self.file_format
        )
        self._fill_guides_list(guides_data_dict.keys())

    def _fill_guides_list_from_repo(self):
        """
        Fill guides list view with templates saved and defined in the repository
        """
        guide_templates_data = guide_utils.get_guides_template_config()[0]
        templates = sorted(list(guide_templates_data.keys()))
        self._fill_guides_list(templates)

    def _fill_source_combo_box(self):
        """
        Fill the source combo box which defines from whoch source we pull the templates.
        """
        sources = [self.REPO_REF_NAME, self.ASSET_REF_NAME]
        self.QComboBox_0.addItems(sources)

    def _fill_file_type_combox_box(self):
        """
        Fill the file type combo box which defines which file type the templates has.
        """
        file_formats = guide_utils.get_guides_template_config()[1]
        self.file_type_options.addItems(file_formats)
        self.file_type_options.setCurrentIndex(0)

    def _fill_publish_mode_combo_box(self):
        """
        Fill the publishing mode combo box.
        Which defines if we publish the current guides in safe or unsafe mode
        """
        publish_modes = [self.PUBLISH_SAFE_MODE, self.PUBLISH_UNSAFE_MODE, ]
        self.QComboBox_2.addItems(publish_modes)
        self.QComboBox_2.setCurrentIndex(0)

    def fill_guides_list(self):
        """
        Fills the guides template view with all found guides.
        """

        self.QListWidget_0.clear()
        if self.source_type == self.REPO_REF_NAME:
            self._fill_guides_list_from_repo()
        else:
            self._fill_guides_list_from_asset()

    def _change_source_signal(self):
        """
        Signal if source combo box changes
        """
        self.source_type = self.QComboBox_0.currentText()
        self.fill_guides_list()

    def _get_file_type_option(self):
        return self.file_type_options.currentText()

    def _change_file_format_signal(self):
        """
        Signal if file format combo box changes.
        """
        self.file_format = self._get_file_type_option()
        self.fill_guides_list()

    def _get_template_from_list_view_signal(self):
        """
        Get the templates name for the selected item in the list view.
        """
        current_item = self.QListWidget_0.currentItem()
        if current_item:
            self.asset_name = current_item.text()

    def _get_publish_mode(self):
        """
        Get the publishing mode from publish mode ComboBox.
        """
        self.publish_mode = self.QComboBox_2.currentText()

        if self.publish_mode == self.PUBLISH_SAFE_MODE:
            self.publish_mode = True

        elif self.publish_mode == self.PUBLISH_UNSAFE_MODE:
            self.publish_mode = False

        else:
            raise ValueError("wrong publish")

    def connect_signals(self):
        """
        Connect all signals.
        """
        self.QComboBox_0.currentIndexChanged.connect(self._change_source_signal)

        self.file_type_options.currentIndexChanged.connect(
            self._change_file_format_signal
        )

        self.QComboBox_2.currentIndexChanged.connect(self._get_publish_mode)

        self.QListWidget_0.itemClicked.connect(
            self._get_template_from_list_view_signal
        )

        self.QPushButton.clicked.connect(self.import_signal)

        self.publish_button.clicked.connect(self.publish_scene_guide_template)

    def import_signal(self):
        """
        Import the selected template.
        """

        if self.source_type == self.REPO_REF_NAME:
            guide_utils.import_guide_template_with_custom_steps_from_repo(
                self.asset_name, self.file_format
            )
        else:
            guides_data_dict = (
                guide_utils.get_guide_templates_from_asset_context(
                    self.file_format
                )
            )
            guide_path = guides_data_dict[self.asset_name]

            if self.file_format == "sgt":
                io.import_guide_template(guide_path)

            else:
                guide_utils.import_cleaned(guide_path)

    def publish_scene_guide_template(self):
        """
        Publish the current scene guide.
        """

        guide_utils.publish_guides(self.publish_mode, self.file_format)

        self.fill_guides_list()


def show():
    global WINDOW
    maya_window = get_maya_window()
    if WINDOW:
        WINDOW.close()
    WINDOW = GuidesManager(maya_window)
    WINDOW.show()


if __name__ == "__main__":
    show()
