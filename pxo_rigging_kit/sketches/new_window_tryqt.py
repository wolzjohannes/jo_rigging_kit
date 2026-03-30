# Import built-in modules
import random
import sys
import time

# Import third-party modules
try:
    from PySide6 import QtCore
    from PySide6 import QtWidgets
    from PySide6.QtGui import QFont
    from PySide6.QtGui import QIcon
    from PySide6.QtGui import QImage
    from PySide6.QtGui import QPixmap

except ImportError:
    from PySide2 import QtCore
    from PySide2 import QtWidgets
    from PySide2.QtGui import QFont
    from PySide2.QtGui import QIcon
    from PySide2.QtGui import QImage
    from PySide2.QtGui import QPixmap

import maya.OpenMayaUI as omui

try:
    from shiboken2 import wrapInstance
except ModuleNotFoundError:
    from shiboken6 import wrapInstance

_ERROR_COLOR = ("ERROR_COLOR", r"QLinearGradient( x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 #C7611A, stop: 1 #C7421A)")
_SUCCESS_COLOR = ("SUCCESS_COLOR", r"QLinearGradient( x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 #73DB7C, stop: 1 #63C565)")
_PROGRESS_COLOR = ("PROGRESS_COLOR", r"QLinearGradient( x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 #7AADF0, stop: 1 #629BD8)")

_BACKGROUND_COLOR = r"1c1c1c"

sheet = [r"QWidget{",
         r"background: #212026; ",
         r"font: 9pt Verdana; }",

         r"QFrame#separator_line{",
         r"background: #C7C1C1;}",

         r"QProgressBar {",
         r"background-color: #1c1c1c;",
         r"color: #bfbae0;",
         r"border-style: inlay;",
         r"border-width: 1px;",
         r"border-color: #74c8ff;",
         r"border-radius: 0px;",
         r"border-bottom-right-radius: 7px;"
         r"text-align: center; ",
         r"text-height: 15px; ",
         r"min-height: 4px; ",
         r"max-height: 4px; ",
         r"height: 4px; }",

         r"QProgressBar::chunk {",
         r"min-height: 2px; ",
         r"background: PROGRESS_COLOR}",

         r"QLabel[small_type_tag=true]{",
         r"background: #212026; ",
         r"font: 7pt Verdana italic; }",

         r"QLabel#window_title_label{",
         r"background: #212026; ",
         r"font: 20pt Verdana bold; }",

         r"QCheckBox {",
         r"spacing: 5px;",
         r"}",

         r"QCheckBox::indicator {",
         r"width: 13px;",
         r"height: 13px;",
         r"}",

         r"QCheckBox::indicator:unchecked {",
         r"image: url(:/images/checkbox_unchecked.png);",
         r"}",

         r"QCheckBox::indicator:unchecked:hover {",
         r"image: url(:/images/checkbox_unchecked_hover.png);",
         r"}",

         r"QCheckBox::indicator:unchecked:pressed {",
         r"image: url(:/images/checkbox_unchecked_pressed.png);",
         r"}",

         r"QCheckBox::indicator:checked {",
         r"image: url(:/images/checkbox_checked.png);",
         r"}",

         r"QCheckBox::indicator:checked:hover {",
         r"image: url(:/images/checkbox_checked_hover.png);",
         r"}",

         r"QCheckBox::indicator:checked:pressed {",
         r"image: url(:/images/checkbox_checked_pressed.png);",
         r"}",

         r"QCheckBox::indicator:indeterminate:hover {",
         r"image: url(:/images/checkbox_indeterminate_hover.png);",
         r"}",

         r"QCheckBox::indicator:indeterminate:pressed {",
         r"image: url(:/images/checkbox_indeterminate_pressed.png);",
         r"}",

         r"QPushButton[close_btn=true]::hover {",
         r"color: #1c1c1c;",
         r"background: QLinearGradient( x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 #C7611A, stop: 1 #C7421A);",
         r"border: QLinearGradient( x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 #C7611A, stop: 1 #C7421A);",
         r"}",

         r"QPushButton[close_btn=true]{",
         r"border:none;",
         r"font: 20pt Verdana bold;",
         r"}",

         r"QPushButton[negative_btn=true]::hover {",
         r"color: #1c1c1c;",
         r"background: QLinearGradient( x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 #C7611A, stop: 1 #C7421A);",
         r"border: QLinearGradient( x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 #C7611A, stop: 1 #C7421A);",
         r"}",

         r"QPushButton[open_btn=true]::hover {",
         r"color: #1c1c1c;",
         r"background: QLinearGradient( x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 #73DB7C, stop: 1 #63C565);",

         r"border: QLinearGradient( x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 #73DB7C, stop: 1 #63C565);",

         r"}",

         ]


class QHLine(QtWidgets.QFrame):
    def __init__(self, object_name="separator_line"):
        super(QHLine, self).__init__()
        self.setMinimumWidth(1)
        self.setFixedHeight(1)

        self.setFrameShape(QtWidgets.QFrame.HLine)
        self.setFrameShadow(QtWidgets.QFrame.Raised)

        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)
        self.setObjectName(object_name)


class QVLine(QtWidgets.QFrame):
    def __init__(self, object_name="separator_line"):
        super(QVLine, self).__init__()
        self.setMinimumHeight(1)
        self.setFixedWidth(1)

        self.setFrameShape(QtWidgets.QFrame.VLine)
        self.setFrameShadow(QtWidgets.QFrame.Raised)

        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)
        self.setObjectName(object_name)


def maya_main_window():
    """
    Return the Maya main window widget as a Python object
    """
    main_window_ptr = omui.MQtUtil.mainWindow()
    if sys.version_info.major >= 3:
        return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)
    else:
        return wrapInstance(long(main_window_ptr), QtWidgets.QWidget)


class TestDialog(QtWidgets.QDialog):
    def __init__(self, parent=maya_main_window()):
        super(TestDialog, self).__init__(parent)

        self.setWindowTitle("Test Dialog")
        self.setMinimumWidth(200)
        self.setWindowFlags(self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint | QtCore.Qt.FramelessWindowHint)

        self.setStyleSheet(TestDialog._format_general_style(sheet).replace(_PROGRESS_COLOR[0], _PROGRESS_COLOR[1]))
        self.create_widgets()
        self.create_layouts()

        self.attatch_signals()

    def create_widgets(self):
        self.sizegrip = QtWidgets.QSizeGrip(self)

        self.window_title = QtWidgets.QLabel(str(self.windowTitle()))
        self.window_title.setObjectName("window_title_label")
        self.window_title.setAlignment(QtCore.Qt.AlignLeft)

        self.close_btn = QtWidgets.QPushButton("X")
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.setFixedSize(30, 30)

        self.close_btn.setProperty("close_btn", True)

        self.line_seperator = QHLine()

        self.lineedit = QtWidgets.QLineEdit()
        self.checkbox1 = QtWidgets.QCheckBox("Checkbox1")

        self.progressbar = QtWidgets.QProgressBar()
        self.progressbar.setValue(0)
        self.progressbar.setTextVisible(False)

        self.annotation = QtWidgets.QLabel("bruh")
        self.annotation.setAlignment(QtCore.Qt.AlignLeft)
        self.percentage = QtWidgets.QLabel("0%")
        self.percentage.setAlignment(QtCore.Qt.AlignRight)

        self.operation_name = QtWidgets.QLabel("initializing operations")
        self.operation_name.setProperty("small_type_tag", True)

        self.process_name = QtWidgets.QLabel("process")
        self.process_name.setProperty("small_type_tag", True)
        self.process_name.setAlignment(QtCore.Qt.AlignRight)

        self.button1 = QtWidgets.QPushButton("add")
        self.button1.setProperty("open_btn", True)

        self.button2 = QtWidgets.QPushButton("subtract")
        self.button2.setProperty("negative_btn", True)

    def create_layouts(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        sub_layout = QtWidgets.QVBoxLayout(self)
        sub_layout.setSpacing(0)
        sub_layout.setContentsMargins(5, 5, 5, 5)

        main_layout.addLayout(sub_layout)

        # adding window title
        window_frame_layout = QtWidgets.QHBoxLayout(self)
        window_frame_layout.addWidget(self.window_title, 1)
        window_frame_layout.addWidget(self.close_btn, alignment=QtCore.Qt.AlignRight)

        # format stretching
        window_frame_layout.addStretch()
        window_frame_layout.insertSpacing(0, 5)

        sub_layout.addLayout(window_frame_layout)

        sub_layout.addWidget(self.line_seperator)

        sub_layout.insertSpacing(1, 2)
        sub_layout.insertSpacing(2, 1)
        sub_layout.insertSpacing(4, 16)

        sub_layout.addWidget(self.lineedit)
        sub_layout.addWidget(self.checkbox1)
        sub_layout.addStretch()

        progressbar_layout = QtWidgets.QVBoxLayout(self)
        progressbar_layout.insertSpacing(0, 16)

        progressbar_info_layout = QtWidgets.QHBoxLayout(self)
        progressbar_info_layout.addWidget(self.annotation)
        progressbar_info_layout.addWidget(self.percentage)
        progressbar_layout.addLayout(progressbar_info_layout)

        progressbar_layout.insertSpacing(5, 4)
        progressbar_layout.addWidget(self.progressbar)

        progressbar_subinfo_layout = QtWidgets.QHBoxLayout(self)
        progressbar_subinfo_layout.addWidget(self.operation_name)
        progressbar_subinfo_layout.addWidget(self.process_name)
        progressbar_layout.addLayout(progressbar_subinfo_layout)

        progressbar_layout.insertSpacing(6, 16)

        sub_layout.addLayout(progressbar_layout)
        sub_layout.addStretch()

        add_button_layout = QtWidgets.QVBoxLayout(self)

        add_button_layout.addWidget(self.button1)
        add_button_layout.addWidget(self.button2)
        sub_layout.addLayout(add_button_layout)

        main_layout.addWidget(self.sizegrip, 1, QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom)


    def attatch_signals(self):
        self.button1.clicked.connect(self.add_progress_value)
        self.button2.clicked.connect(self.subtract_progress_value)

        self.progressbar.valueChanged.connect(self.set_success_color)
        self.progressbar.valueChanged.connect(self.update_percentage)
        self.progressbar.valueChanged.connect(self.update_annotation)
        self.progressbar.valueChanged.connect(self.update_operation_name)

        self.close_btn.clicked.connect(self.close)
        self.checkbox1.stateChanged.connect(self.set_error_color)

    def add_progress_value(self):
        self.progressbar.setValue(self.progressbar.value() + 10)

    def subtract_progress_value(self):
        self.progressbar.setValue(self.progressbar.value() - 10)

    def set_success_color(self):
        if self.progressbar.value() == 100:
            self.progressbar.setStyleSheet(
                    TestDialog._format_general_style(sheet).replace(_PROGRESS_COLOR[0], _SUCCESS_COLOR[1]))

        else:
            self.progressbar.setStyleSheet(
                    TestDialog._format_general_style(sheet).replace(_PROGRESS_COLOR[0], _PROGRESS_COLOR[1]))

    def set_error_color(self):
        if self.checkbox1.isChecked():
            self.progressbar.setStyleSheet(
                    TestDialog._format_general_style(sheet).replace(_PROGRESS_COLOR[0], _ERROR_COLOR[1]))

        else:
            self.progressbar.setStyleSheet(
                    TestDialog._format_general_style(sheet).replace(_PROGRESS_COLOR[0], _PROGRESS_COLOR[1]))

    @staticmethod
    def _format_general_style(style_list, **kwargs):
        style_string = ''.join(style_list)

        return style_string

    def update_annotation(self):
        text_name = str(random.choice(["apple", "banana", "cherry"]))
        self.annotation.setText(text_name)

    def update_percentage(self):
        text_name = str(self.progressbar.value())
        self.percentage.setText("{0} %".format(text_name))

    def update_operation_name(self):
        text_name = str(self.annotation.text())

        if self.progressbar.value() == 0:
            self.operation_name.setText("initializing operations on: {0}".format(text_name))
        else:
            self.operation_name.setText("running operation: 1 at: {0}".format(text_name))

    # action #1
    def mousePressEvent(self, event):
        self.oldPosition = event.globalPos()

    # action #2
    def mouseMoveEvent(self, event):
        delta = QtCore.QPoint(event.globalPos() - self.oldPosition)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPosition = event.globalPos()


if __name__ == "__main__":

    d = TestDialog()
    d.show()







