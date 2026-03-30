import maya.OpenMayaUI as omui
import maya.cmds as cmds

try:
    from shiboken2 import wrapInstance
except ModuleNotFoundError:
    from shiboken6 import wrapInstance
import sys
import re
try:
    from PySide2 import QtWidgets
except:
    from PySide6 import QtWidgets

current_dpi = cmds.mayaDpiSetting(rsv=True, q=True)


def scale_dpi(float_value):
    scale = current_dpi
    return float_value * scale


def scale_px_values(stylesheet: str, scale: float = current_dpi) -> str:
    def replacer(match):
        number = float(match.group(1))
        scaled = round(number, 4)
        return f"{scaled}px"

    return re.sub(r'(\d+\.?\d*)px', replacer, stylesheet)


STYLE_SHEET = [
    r"QWidget{",
    r"background: #223040; ",
    r"font: 9pt Verdana; }",
    r"QListWidget{",
    r"font: 9pt Helvetcia;",
    r"background: black;",
    r"alternate-background-color: grey; }",
    r"QListWidget::item {image: url(ITEM_ICON);}",
    r"QListWidget::item:selected {background: solid #223040;}",
    r"QListWidget::item:selected:!active {background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,stop: 0 #ABAFE5, stop: 1 #8588B2); color: black;}",
    r"QListWidget::item:selected:active {background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,stop: 0 #6a6ea9, stop: 1 #888dd9); color: black;}",
    r"QListWidget::item:hover {background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,stop: 0 #FAFBFE, stop: 1 #DCDEF1); color: #2E2E2E;}",
    r"QListWidget QScrollBar:vertical {",
    r"    background: black; }",
    r"QListWidget QScrollBar:horizontal {",
    r"    background: black; }",
    r"QComboBox{",
    r"background: #312036; ",
    r"border: 1px solid gray; }",
    r"QPushButton{",
    r"background: #312036; ",
    r"border: 1px solid gray;",
    r"border-radius: 1px; }",
    r"QPushButton:pressed {background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,stop: 0 #dadbde, stop: 1 #f6f7fa);}",
    r"QPushButton:hover {background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,stop: 0 #ABAFE5, stop: 1 #8588B2);}",
    r"QGroupBox {",
    r"    border: 1px solid #556070;",
    r"    margin-top: 12px;",
    r"    background-color: #1b2835;",
    r"    border-radius: 4px;",
    r"    font: bold 9pt Verdana;",
    r"    color: #D3D7CF; }",
    r"QGroupBox::title {",
    r"    subcontrol-origin: margin;",
    r"    subcontrol-position: top left;",
    rf"    top: -1px;",
    r"    padding: 0px 3px;",
    r"    color: #AFC0D0;",
    r"    background-color: transparent; }",
    r"TextEntryWidget QLabel {",
    r"    color: #D3D7CF;",
    r"    font: 9pt Verdana;",
    r"    padding: 2px 0px;",
    r"    background-color: transparent; }",
    r"QLineEdit {",
    r"    background-color: #1F1423;",
    r"    color: #F0F0F0;",
    r"    border: 1px solid gray;",
    r"    border-radius: 2px;",
    r"    padding: 2px 4px;",
    r"    font: 7pt Verdana; }",
    r"QLineEdit:focus {",
    r"    border: 2px solid #888dd9;",
    r"    background-color: #1F1423; }",
    r"QSpinBox {",
    r"    background-color: #312036;",
    r"    color: #F0F0F0;",
    r"    border: 1px solid gray;",
    r"    border-radius: 2px;",
    r"    padding: 2px 4px;",
    r"    font: 7pt Verdana; }",
    r"QSpinBox:focus {",
    r"    border: 2px solid #888dd9;",
    r"    background-color: #3A2A41; }",
    r"QCheckBox::indicator {",
    r"    background-color: #1F1423;",
    r"    border: 1px solid gray;",
    r"    border-radius: 4px;",
    r"    width: 20px;",
    r"    height: 20px;}",
    r"QCheckBox::indicator:checked {",
    r"    image: url(CHECK_ICON); }",
    r"QCheckBox::indicator:disabled {",
    r"    background-color: darkgray;",
    r"    border: 1px solid gray;",
    r"}",
    r"QCheckBox:disabled {",
    r"    color: darkgray;",
    r"}",
    r"QSlider::groove:horizontal {",
    r"    background-color: #1a1f2a;  ",
    r"    height: 7px;               ",
    r"    border: 1px solid #556070; ",
    r"    border-radius: 4px;        ",
    r"}",
    r"QSlider::handle:horizontal {",
    r"    background: #312036;       ",
    r"    width: 24px;               ",
    r"    height: 12px;              ",
    r"    border: 1px solid #AFC0D0; ",
    r"    margin: -4px 0;"
    r"    border-radius: 12px 16px;  ",
    r"}",
    r"QSlider::handle:horizontal:hover {",
    r"    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #ABAFE5, stop: 1 #8588B2); ",
    r"}",
    r"QRadioButton {",
    r"color: #D3D7CF;",
    r"font: 9pt Verdana;",
    r"background-color: transparent;",
    r"}",
    r"QRadioButton::indicator {",
    r"width: 14px;",
    r"height: 14px;",
    r"border-radius: 9px;",
    r"background-color: #312036;",
    r"border: 3px solid gray;",
    r"}",
    r"QRadioButton::indicator:checked {",
    r"background-color: #F0F0F0;",
    r"border: 3px solid #AFC0D0;",
    r"}",
    r"QRadioButton::indicator:hover {",
    r"border: 3px solid #888dd9;",
    r"}",
    r"QScrollArea {",
    r"    border: none;",
    r"}",
    r"QScrollBar:vertical {",
    r"    background: #223040;",
    r"    width: 9px;",
    r"    margin: 0px 0px 0px 0px;",
    r"    border: none;",
    r"}",
    r"QScrollBar::handle:vertical {",
    r"    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #312036, stop:1 #312036);",
    r"    min-height: 20px;",
    r"    border-radius: 4px;",
    r"}",
    r"QScrollBar::handle:vertical:hover {",
    r"    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #888dd9, stop:1 #6a6ea9);",
    r"}",
    r"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {",
    r"    height: 0px;",
    r"}",
    r"QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {",
    r"    background: none;",
    r"}",
    r"QScrollBar:horizontal {",
    r"    background: #223040;",
    r"    height: 10px;",
    r"    margin: 0px 0px 0px 0px;",
    r"    border: none;",
    r"}",
    r"QScrollBar::handle:horizontal {",
    r"    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #312036, stop:1 #312036);",
    r"    min-width: 20px;",
    r"    border-radius: 4px;",
    r"}",
    r"QScrollBar::handle:horizontal:hover {",
    r"    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #888dd9, stop:1 #6a6ea9);",
    r"}",
    r"QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {",
    r"    width: 0px;",
    r"}",
    r"QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {",
    r"    background: none;",
    r"}",
    r"ClickSeparator{border: 2px solid grey;}",
    r" QAbstractScrollArea::corner {background: #272A2B;}",
    r"QDoubleSpinBox {",
    r"    background-color: #1F1423;",
    r"    color: #F0F0F0;",
    r"    border: 1px solid gray;",
    r"    border-radius: 2px;",
    r"    padding: 2px 4px;",
    r"    font: 7pt Verdana; }",
    r"QDoubleSpinBox:focus {",
    r"    border: 2px solid #888dd9;",
    r"    background-color: #1F1423; }",
    r"QTabWidget::pane {border: 1px solid #2F455A; top: -1px; background: #162029;}",
    r"QTabBar::tab {background: #1A2530; color: #70777D; padding: 6px 12px; border-top: 1px solid #101820; border-left: 1px solid #101820; border-right: 1px solid #101820; border-bottom: 1px solid #2F455A;}",  # darker border, no bottom
    r"QTabBar::tab:selected {background: #223040; color: white; border-top: 1px solid #2F455A; border-left: 1px solid #2F455A; border-right: 1px solid #2F455A; border-bottom: 1px solid #223040;}",  # bottom blends with pane
    #r"QTabBar::tab:hover {background: #2A3B4C; color: #D0D6DB; border-top: 1px solid #1C2833; border-left: 1px solid #1C2833; border-right: 1px solid #1C2833; border-bottom: none;}",  # no bottom on hover too
    r"QTabBar::tab:!selected {margin-top: 2px;}"

]

SEP_SYTLE_SHEET = r"QFrame{border: 1px solid grey; border-radius: 1px;}"


def get_maya_window():
    """
    Return the Maya main window widget as a Python object
    """

    main_window_ptr = omui.MQtUtil.mainWindow()
    if main_window_ptr is not None:
        if sys.version_info.major >= 3:
            return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)
        else:
            return wrapInstance(long(main_window_ptr), QtWidgets.QWidget)
