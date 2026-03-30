import math
from abc import ABC
from dataclasses import dataclass
from typing import Type, Callable

try:
    import shiboken6  # noqa: import error
    from PySide6 import QtCore, QtWidgets, QtGui  # noqa: import error
    from PySide6.QtCore import Property, Qt, QSize, QPropertyAnimation, QEasingCurve, QRect, QPointF, QRectF, \
        Signal  # noqa: import error
    from PySide6.QtWidgets import QCheckBox, QSplashScreen  # noqa: import error
    from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QPixmap  # noqa: import error

except ImportError:
    from PySide2 import QtCore
    from PySide2 import QtGui
    from PySide2 import QtWidgets

import maya.cmds as cmds

import numpy as np
from pxo_rigging_kit.maya_utils.guis import scale_dpi


#######################################################
# CLASSES
#######################################################




class Theme:
    pass



class SkinIOTheme(Theme):
    BASE_GRADIENT_LEFT = QtGui.QColor(255, 255, 255, 18)
    BASE_GRADIENT_RIGHT = QtGui.QColor(0, 0, 0, 3)

    SELECTION_LEFT = QtGui.QColor(70, 120, 200, 180)
    SELECTION_RIGHT = QtGui.QColor(70, 120, 200, 0)

    HOVER_COLOR = QtGui.QColor(255, 255, 255, 20)

    TOGGLE_OFF = QtGui.QColor(150, 150, 150)
    TOGGLE_ON = QtGui.QColor(0, 176, 255)
    TOGGLE_HANDLE = QtGui.QColor(255, 255, 255)

    TEXT_COLOR = QtGui.QColor(220, 220, 220)

    SUCCESS_COLOR_LEFT = QtGui.QColor(100,240,160)
    PROGRESS_COLOR_LEFT = QtGui.QColor(0, 176, 255)
    CANCEL_COLOR_LEFT = QtGui.QColor(255, 210,50)
    FAIL_COLOR_LEFT = QtGui.QColor(255, 100, 50)

    SUCCESS_COLOR_RIGHT = QtGui.QColor(100,240,160)
    PROGRESS_COLOR_RIGHT = QtGui.QColor(5, 160, 255)
    CANCEL_COLOR_RIGHT = QtGui.QColor(255, 210,50)
    FAIL_COLOR_RIGHT = QtGui.QColor(255, 100, 50)

    BACKGROUND_COLOR = QtGui.QColor("#1c1c1c")

    @staticmethod
    def PROGRESS_GRADIENT():
        """Blue gradient used for loading / in-progress states."""
        g = QtGui.QLinearGradient(QPointF(0, 1), QPointF(0, 0))  # bottom → top
        g.setCoordinateMode(QtGui.QLinearGradient.ObjectBoundingMode)
        g.setColorAt(0.0, QColor("#7AADF0"))
        g.setColorAt(1.0, QColor("#629BD8"))
        return g

    @staticmethod
    def SUCCESS_GRADIENT():
        """Green gradient used for success states."""
        g = QtGui.QLinearGradient(QPointF(0, 1), QPointF(0, 0))
        g.setCoordinateMode(QtGui.QLinearGradient.ObjectBoundingMode)
        g.setColorAt(0.0, QColor("#73DB7C"))
        g.setColorAt(1.0, QColor("#63C565"))
        return g

    @staticmethod
    def ERROR_GRADIENT():
        """Red gradient used for failure states."""
        g = QtGui.QLinearGradient(QPointF(0, 1), QPointF(0, 0))
        g.setCoordinateMode(QtGui.QLinearGradient.ObjectBoundingMode)
        g.setColorAt(0.0, QColor("#C7611A"))
        g.setColorAt(1.0, QColor("#C7421A"))
        return g

    @staticmethod
    def IDLE_GRADIENT():
        """Subtle dark gradient for idle states."""
        g = QtGui.QLinearGradient(QPointF(0, 1), QPointF(0, 0))
        g.setCoordinateMode(QtGui.QLinearGradient.ObjectBoundingMode)
        g.setColorAt(0.0, QColor("#2a2a2a"))
        g.setColorAt(1.0, QColor("#3a3a3a"))
        return g






class ClickSeparator(QtWidgets.QFrame):
    clicked = QtCore.Signal()

    def __init__(self, parent=None):
        super(ClickSeparator, self).__init__(parent)

        self.setFrameStyle(QtWidgets.QFrame.HLine)

        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()
        return True


class ClickLabel(QtWidgets.QLabel):
    clicked = QtCore.Signal()

    def __init__(self, parent=None):
        super(ClickLabel, self).__init__(parent)
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()
        return True


class TextEntryWidget(QtWidgets.QWidget):

    def __init__(self, title=None):
        super(TextEntryWidget, self).__init__()

        layout = QtWidgets.QHBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignTop)
        layout.setContentsMargins(1, 1, 1, 1)
        self.setLayout(layout)
        self.main_layout = layout

        if title:
            title_widget = QtWidgets.QLabel(title)
            layout.addWidget(title_widget)

        self.text_entry = QtWidgets.QLineEdit()
        self.button = QtWidgets.QPushButton('<')

        self.button.clicked.connect(self._button_fill_text)

        layout.addWidget(self.text_entry)
        layout.addWidget(self.button)

    def _button_fill_text(self):
        selection = cmds.ls(sl=True)
        if selection:
            self.text_entry.setText(selection[0])
        else:
            self.text_entry.clear()

    def set_text(self, text):
        self.text_entry.setText(text)

    def text(self):
        return self.text_entry.text()

    def hide_button(self, bool_value):
        if bool_value:
            self.button.hide()
        else:
            self.button.show()


class CollapsableSeparator(QtWidgets.QWidget):
    clicked = QtCore.Signal()

    def __init__(self, title, parent=None):
        super(CollapsableSeparator, self).__init__(parent)

        self.title = title

        self.setMouseTracking(True)

        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setAlignment(QtCore.Qt.AlignTop)
        self.setLayout(self.main_layout)

        self.clicked.connect(self._toggle_collapse)

        self._collapse_state = True

        self._build_widgets()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)

        pos = event.pos()
        if pos.y() > 40:
            return True

        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()
        return True

    def _build_widgets(self):
        separator = ClickSeparator()
        label = ClickLabel(self.title)

        self.main_layout.addWidget(separator)
        self.main_layout.addWidget(label)

        self.collapse_widget = QtWidgets.QWidget()
        self.collapse_layout = QtWidgets.QVBoxLayout()
        self.collapse_widget.setLayout(self.collapse_layout)

        self.main_layout.addWidget(self.collapse_widget)

        self._collapse_state = True

    def _toggle_collapse(self):

        self.set_collapsed(self._collapse_state)

    def add_widget(self, widget_inst):
        self.collapse_layout.addWidget(widget_inst)

    def add_layout(self, layout_inst):
        self.collapse_layout.addLayout(layout_inst)

    def set_collapsed(self, bool_value):
        if bool_value:
            self.collapse_widget.hide()
        else:
            self.collapse_widget.show()

        self._collapse_state = not self._collapse_state


class ResetSlider(QtWidgets.QWidget):
    value_changed = QtCore.Signal(object)
    pressed = QtCore.Signal()
    released = QtCore.Signal()

    def __init__(self, title, parent=None):
        super(ResetSlider, self).__init__(parent)
        self.title = title

        self.setMouseTracking(True)

        self.main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.main_layout)

        self.main_layout.setContentsMargins(2, 1, 1, 1)
        self.main_layout.setSpacing(1)

        self._emit_value_change = True

        self._build_widgets()

    def wheelEvent(self, event):
        event.ignore()

    def _build_widgets(self):
        label = QtWidgets.QLabel(self.title)
        self.slider = QtWidgets.QSlider()

        self.slider.setMinimum(-10)
        self.slider.setMaximum(10)
        self.slider.setValue(0)
        self.slider.setOrientation(QtCore.Qt.Horizontal)

        self.main_layout.addWidget(label)
        self.main_layout.addWidget(self.slider)

        self.slider.sliderReleased.connect(self._slider_released)
        self.slider.sliderPressed.connect(self._slider_pressed)
        self.slider.valueChanged.connect(self._slider_value_changed)

    def _slider_value_changed(self, value):
        if not self._emit_value_change:
            return

        self.value_changed.emit(value)

    def _slider_pressed(self):
        self.pressed.emit()

    def _slider_released(self):
        self._emit_value_change = False
        self.slider.setValue(0)
        self._emit_value_change = True
        self.released.emit()


class ThreeDoubleWidget(QtWidgets.QWidget):
    value_changed = QtCore.Signal(object, object, object)

    def __init__(self, title, parent=None):
        super(ThreeDoubleWidget, self).__init__(parent)

        self.title = title

        self.main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.main_layout)

        self.main_layout.setContentsMargins(5, 1, 1, 1)
        self.main_layout.setSpacing(1)

        self._build_widgets()

    def _build_widgets(self):
        label = QtWidgets.QLabel(self.title)
        self.double1, layout1 = self._add_double_value('X')
        self.double2, layout2 = self._add_double_value('Y')
        self.double3, layout3 = self._add_double_value('Z')

        self.main_layout.addWidget(label)
        self.main_layout.addLayout(layout1)
        self.main_layout.addLayout(layout2)
        self.main_layout.addLayout(layout3)

    def _get_values(self):
        value1 = self.double1.value()
        value2 = self.double2.value()
        value3 = self.double3.value()

        return value1, value2, value3

    def _value_changed(self):
        values = self._get_values()

        self.value_changed.emit(*values)

    def _add_double_value(self, name, value=0):
        label = QtWidgets.QLabel(name)

        double_widget = QtWidgets.QDoubleSpinBox()
        double_widget.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        double_widget.setStyleSheet("QDoubleSpinBox { border: none; }")
        double_widget.setMinimum(-1000)
        double_widget.setMaximum(1000)
        double_widget.setValue(value)
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(label, alignment=QtCore.Qt.AlignRight)
        layout.addWidget(double_widget)
        layout.setContentsMargins(5, 1, 0, 0)
        layout.setSpacing(3)

        double_widget.valueChanged.connect(self._value_changed)

        return double_widget, layout

    def set_all_values(self, value):
        self.double1.setValue(value)
        self.double2.setValue(value)
        self.double3.setValue(value)

    def get_value(self):
        values = self._get_values()

        return values


class MayaColorIndices(QtWidgets.QWidget):
    clicked = QtCore.Signal(object)

    def __init__(self, parent=None):
        super(MayaColorIndices, self).__init__(parent)

        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(1, 1, 1, 1)
        self.setLayout(self.main_layout)

        self._build_widgets()

    def _build_widgets(self):
        indexed_colors = [cmds.colorIndex(i, query=True) for i in range(1, 32)]

        h_layout = QtWidgets.QHBoxLayout()
        grid_layout = QtWidgets.QGridLayout()

        color_widget = ColorWidget(QtGui.QColor(0, 0, 0, 0))
        color_widget.set_click_emit_value(0)
        color_widget.clicked.connect(self.color_clicked)

        grid_layout.addWidget(color_widget, 0, 0)

        column = 1
        row = 0
        inc = 0
        for color in indexed_colors:
            color = QtGui.QColor(*(int(channel * 255) for channel in color))

            color_widget = ColorWidget(color)
            color_widget.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
            color_widget.set_click_emit_value(inc + 1)
            color_widget.clicked.connect(self.color_clicked)

            grid_layout.addWidget(color_widget, row, column)

            inc += 1
            column += 1

            if column == 8:
                column = 0
                row += 1

        h_layout.addStretch()
        h_layout.addLayout(grid_layout)
        h_layout.addStretch()
        self.main_layout.addLayout(h_layout)

    def color_clicked(self, value):
        self.clicked.emit(value)


class ColorWidget(QtWidgets.QLabel):
    clicked = QtCore.Signal(object)

    def __init__(self, color: QtGui.QColor, parent=None):
        super(ColorWidget, self).__init__(parent)

        self.setMouseTracking(True)

        self.color = color
        self.set_color(color)

        self._emit_value = None

    def mousePressEvent(self, event):
        super().mousePressEvent(event)

        emit_value = self.color
        if self._emit_value is not None:
            emit_value = self._emit_value

        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit(emit_value)
        return True

    def set_click_emit_value(self, value):
        self._emit_value = value

    def set_color(self, color: QtGui.QColor):
        self.color = color
        pixmap = create_color_icon(self.color)
        self.setPixmap(pixmap)


class GradientWidget(QtWidgets.QWidget):
    clicked = QtCore.Signal(object)
    dragged = QtCore.Signal(object)

    def __init__(self):
        super().__init__()
        self.setMinimumSize(scale_dpi(50), scale_dpi(70))
        self._mouse_pressed = False
        self.image = None

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self._mouse_pressed = True
        if event.button() == QtCore.Qt.LeftButton:
            pos = event.pos()
            if self.image.rect().contains(pos):
                color = self.image.pixelColor(pos)
                self.clicked.emit(color)
        return True

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)

        if not self._mouse_pressed:
            return True

        pos = event.pos()
        if self.image.rect().contains(pos):
            color = self.image.pixelColor(pos)
            self.dragged.emit(color)
        return True

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)

        self._mouse_pressed = False
        return True

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        self.image = QtGui.QImage(QtCore.QSize(self.width(), self.height()), QtGui.QImage.Format_RGB32)

        for y in range(self.height()):
            v = y / (self.height() - 1.0)

            value = 1 - v ** 4
            saturation = 1 - (1 - v) ** 4

            saturation = min(np.interp(saturation, [0, 1], [0, 1.1]), 1.0)
            value = min(np.interp(value, [0, 1], [0, 1.1]), 1.0)

            for x in range(self.width()):
                u = x / (self.width() - 1)
                hue = u * 360.0
                color = QtGui.QColor.fromHsvF(hue / 360.0, saturation, value)
                self.image.setPixelColor(x, y, color)

        # Draw the image
        painter.drawImage(self.rect(), self.image)



class GetColor(QtWidgets.QWidget):
    clicked = QtCore.Signal(object)

    def __init__(self, parent=None):
        super(GetColor, self).__init__(parent)

        self.main_layout = QtWidgets.QHBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.setLayout(self.main_layout)

        self._mouse_pressed = False
        self._orig_color = None

        self._build_widgets()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == QtCore.Qt.LeftButton:
            self._mouse_pressed = True
            self._orig_color = self.color.color

        return True

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)

        if self._mouse_pressed:
            color = get_color_under_mouse()
            self.color.set_color(color)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self._mouse_pressed = False
        if self._orig_color == self.color.color:
            self.clicked.emit(self.color.color)
        self._orig_color = None

        return True

    def _build_widgets(self):
        self.color = ColorWidget(QtGui.QColor(100, 100, 100, 255))
        self.load = QtWidgets.QPushButton('Load')
        self.load.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        self.main_layout.addWidget(self.color)
        self.main_layout.addWidget(self.load)


class HideShowWidget(QtWidgets.QWidget):
    clicked = QtCore.Signal(object, object)

    def __init__(self, name, parent=None):
        super(HideShowWidget, self).__init__(parent)

        self.title = name

        self.main_layout = QtWidgets.QHBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(5)
        self.setLayout(self.main_layout)

        self._build_widgets()

    def _build_widgets(self):
        label = QtWidgets.QLabel(self.title)
        label.setFixedWidth(170)
        hide = QtWidgets.QPushButton('Hide')
        show = QtWidgets.QPushButton('Show')

        hide.clicked.connect(self._emit_off)
        show.clicked.connect(self._emit_on)

        self.main_layout.addWidget(label)

        self.main_layout.addWidget(hide)
        self.main_layout.addWidget(show)
        self.main_layout.addStretch()

    def _emit_off(self):
        self.clicked.emit(False, self.title)

    def _emit_on(self):
        self.clicked.emit(True, self.title)

class HashRenameWidget(QtWidgets.QWidget):

    rename_clicked = QtCore.Signal(object, object)

    EXAMPLE_INC_STRING = 'example: A or a'
    EXAMPLE_INC_NUMBER = 'example: 1'

    def __init__(self, parent=None):
        super(HashRenameWidget, self).__init__(parent)

        self.main_layout = QtWidgets.QHBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(5)
        self.setLayout(self.main_layout)

        self._build_widgets()

    def _build_widgets(self):
        rename_layout = QtWidgets.QHBoxLayout()

        rename_inc_type = QtWidgets.QComboBox()
        rename_inc_type.addItems(['Start Number', 'Start Letter'])
        rename_inc_type.setMinimumWidth(100)
        rename_inc_type.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                                            QtWidgets.QSizePolicy.Preferred))
        rename_inc_type.currentIndexChanged.connect(self._current_inc_type_changed)

        self.rename_inc_type = rename_inc_type

        inc_string = QtWidgets.QLineEdit()
        inc_string.setPlaceholderText(self.EXAMPLE_INC_NUMBER)
        inc_string.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                                       QtWidgets.QSizePolicy.Preferred))

        self.inc_string = inc_string

        rename_button = QtWidgets.QPushButton('Rename')
        rename_button.setSizePolicy(
            QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                  QtWidgets.QSizePolicy.Preferred))

        rename_layout.addWidget(rename_inc_type)
        rename_layout.addWidget(inc_string)
        rename_layout.addWidget(rename_button)

        self.main_layout.addLayout(rename_layout)

        rename_button.clicked.connect(self._rename_clicked)

    def _rename_clicked(self):
        index = self.rename_inc_type.currentIndex()
        start_number_letter = str(self.inc_string.text())

        self.rename_clicked.emit(index, start_number_letter)

    def _current_inc_type_changed(self, index):
        self.inc_string.setText('')
        if index == 0:
            self.inc_string.setPlaceholderText(self.EXAMPLE_INC_NUMBER)
        if index == 1:
            self.inc_string.setPlaceholderText(self.EXAMPLE_INC_STRING)



def get_color_under_mouse():
    # Get mouse global position
    pos = QtGui.QCursor.pos()

    screen = QtGui.QGuiApplication.screenAt(pos)
    if screen is None:
        return None

    screenshot = screen.grabWindow(0, pos.x(), pos.y(), 1, 1)
    if screenshot.isNull():
        return None

    image = screenshot.toImage()
    color = image.pixelColor(0, 0)
    return color


def create_color_icon(color: QtGui.QColor,
                      size: QtCore.QSize = QtCore.QSize(scale_dpi(20),
                                                        scale_dpi(20))
                      ) -> QtGui.QPixmap:
    pixmap = QtGui.QPixmap(size)
    pixmap.fill(QtCore.Qt.transparent)

    painter = QtGui.QPainter(pixmap)
    painter.fillRect(0, 0, size.width(), size.height(), color)
    painter.end()

    return pixmap


def create_signal(*args):
    return QtCore.Signal(*args)


class EscapeKeyFilter(QtCore.QObject):
    def __init__(self):
        super().__init__()
        self.escape_pressed = False

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.KeyPress:
            if event.key() == Qt.Key_Escape:
                self.escape_pressed = True

        elif event.type() == QtCore.QEvent.KeyRelease:
            if event.key() == Qt.Key_Escape:
                self.escape_pressed = False

        return False


class GradientSplashScreen(QSplashScreen):
    finished = Signal()
    fadeFinished = Signal()
    fillChanged = Signal()

    def __init__(self, pix: Type[QPixmap], parent=None):
        super().__init__(pix, Qt.WindowStaysOnTopHint | Qt.Tool)

        self._fill = 0.0

        self.setMask(pix.mask())
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setWindowOpacity(1.0)


        self._anim = QPropertyAnimation(self, b"fill", self)
        self._anim.setDuration(400)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.InOutQuad)
        self._anim.finished.connect(self.finished)


    @Property(float, notify=fillChanged)
    def fill(self):
        return self._fill

    @fill.setter
    def fill(self, value):
        self._fill = value
        self.fillChanged.emit()
        self.update()

    # Start animation
    def start(self):
        self.show()
        QtCore.QTimer.singleShot(0, self._anim.start)

    def fadeOut(self, duration=600):
        fade = QPropertyAnimation(self, b"windowOpacity", self)
        fade.setDuration(duration)
        fade.setStartValue(1.0)
        fade.setEndValue(0.0)
        fade.setEasingCurve(QEasingCurve.InOutQuad)
        fade.finished.connect(self.fadeFinished)
        fade.start()

    def _drawShadow(self, painter, pix, offset=QPointF(3, 3), blur=50):
        shadow = QtGui.QImage(pix.size(), QtGui.QImage.Format_ARGB32_Premultiplied)
        shadow.fill(Qt.transparent)

        sp = QPainter(shadow)
        sp.drawPixmap(0, 0, pix)
        sp.end()

        # Convert to black silhouette
        for y in range(shadow.height()):
            scan = shadow.scanLine(y)
            ptr = memoryview(scan)
            for x in range(shadow.width()):
                a = ptr[x*4 + 3]
                ptr[x*4 + 0] = 0
                ptr[x*4 + 1] = 0
                ptr[x*4 + 2] = 0
                ptr[x*4 + 3] = a

        blurred = shadow.scaled(
            shadow.width() + blur,
            shadow.height() + blur,
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation
        )

        painter.drawImage(offset, blurred)

    # Paint event
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), Qt.black)

        pix = self.pixmap()
        w, h = pix.width(), pix.height()

        painter.drawPixmap(0, 0, pix)

        grad = SkinIOTheme.SUCCESS_GRADIENT()

        # Clip to the logo's alpha mask (but NOT the window mask)
        mask_region = QtGui.QRegion(pix.mask())
        painter.setClipRegion(mask_region)

        fill_rect = QRectF(0, h * (1 - self._fill), w, h * self._fill)
        painter.setClipRect(fill_rect, Qt.IntersectClip)
        painter.fillRect(fill_rect, grad)


class ThemedLabel(QtWidgets.QLabel):
    def __init__(self, text="", parent=None, color=None):
        super().__init__(text, parent)

        # Default to theme text color
        self._color = color or SkinIOTheme.TEXT_COLOR
        self.updateStyle()

    def setColor(self, color):
        self._color = color
        self.updateStyle()

    def updateStyle(self):
        self.setStyleSheet(f"color: {self._color.name()};")


class ThemedPushButton(QtWidgets.QPushButton):
    """
    A QPushButton that draws itself using the global Theme colors.
    Supports custom hover colors (e.g. error, cancel, success).
    """

    def __init__(self, text="", parent=None,
                 hover_color: QtGui.QColor | None = None,
                 pressed_color: QtGui.QColor | None = None,
                 base_color: QtGui.QColor | None = None,
                 text_color: QtGui.QColor | None = None):

        super().__init__(text, parent)

        # Default colors follow your theme
        self._baseColor = base_color or SkinIOTheme.BACKGROUND_COLOR.lighter(140)
        self._hoverColor = hover_color or SkinIOTheme.PROGRESS_COLOR_RIGHT
        self._pressedColor = pressed_color or SkinIOTheme.PROGRESS_COLOR_RIGHT.darker(140)
        self._textColor = text_color or SkinIOTheme.TEXT_COLOR

        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.setFlat(True)  # Removes native borders

        # Track hover state
        self._hover = False
        self._pressed = False

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._pressed = True
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._pressed = False
        self.update()
        super().mouseReleaseEvent(event)


    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        rect = self.rect()
        radius = rect.height() * 0.05

        # Choose color based on state
        if not self.isEnabled():
            bg = SkinIOTheme.BACKGROUND_COLOR.darker(180)
            fg = SkinIOTheme.TEXT_COLOR.darker(150)

        elif self._pressed:
            bg = self._pressedColor
            fg = SkinIOTheme.BACKGROUND_COLOR

        elif self._hover:
            bg = self._hoverColor
            fg = SkinIOTheme.BACKGROUND_COLOR

        else:
            bg = self._baseColor
            fg = self._textColor

        # Draw background
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(rect, radius, radius)

        # Draw text
        painter.setPen(fg)
        painter.drawText(rect, QtCore.Qt.AlignCenter, self.text())


class ToggleSwitch(QCheckBox):
    _ANIMATION_DURATION = 200  # Time in ms.
    _HANDLE_REL_SIZE = 0.82
    _PREFERRED_HEIGHT = 16
    _TEXT_SIDE_PADDING = 4

    def __init__(self,
                 checkedText="",
                 uncheckedText="",
                 checkedColor=SkinIOTheme.TOGGLE_ON,
                 uncheckedColor=SkinIOTheme.TOGGLE_OFF,
                 fontHeightRatio=0.9,
                 parent=None
                 ):

        super().__init__(parent=parent)
        assert (0 < fontHeightRatio <= 1)
        self.setMinimumWidth(30)
        self.setMaximumWidth(60)

        self._checkedText = checkedText
        self._uncheckedText = uncheckedText
        self._fontHeightRatio = fontHeightRatio

        self.setCheckedColor(checkedColor)
        self.setUncheckedColor(uncheckedColor)

        self._handlePositionMultiplier = 0

        self._animation = QPropertyAnimation(self, b"handlePositionMultiplier")
        self._animation.setEasingCurve(QEasingCurve.InOutCubic)
        self._animation.setDuration(self._ANIMATION_DURATION)

        self.stateChanged.connect(self._onStateChanged)
        self.setCursor(Qt.PointingHandCursor)
        self._updateText()
        self.setChecked(False)

    def _updateText(self):
        self.setText(self._checkedText if self.isChecked() else self._uncheckedText)

    @Property(float)
    def handlePositionMultiplier(self):
        return self._handlePositionMultiplier

    @handlePositionMultiplier.setter
    def handlePositionMultiplier(self, handlePositionMultiplier):
        self._handlePositionMultiplier = handlePositionMultiplier
        self.update()

    def resizeEvent(self, event):
        font = self.font()
        font.setBold(True)
        font.setPixelSize(event.size().height() * self._fontHeightRatio)
        self.setFont(font)

    def sizeHint(self):
        maxTextWidth = float("-inf")
        for text in [self._checkedText, self._uncheckedText]:
            textSize = self.fontMetrics().size(Qt.TextSingleLine, text)
            maxTextWidth = max(maxTextWidth, textSize.width())

        # We use _PREFERRED_HEIGHT to prevent users from shooting themselves in the foot (visually).
        preferredHeight = max(self.minimumHeight(), self._PREFERRED_HEIGHT)

        # The 1.2 is a magic number creating some padding for the text so
        # that big letters do not overflow the rounded corners.
        return QSize(preferredHeight + maxTextWidth * 1.2 + self._TEXT_SIDE_PADDING, preferredHeight)

    def hitButton(self, pos):
        """ Define the clickable area of the checkbox.
        """
        return self.contentsRect().contains(pos)

    def _onStateChanged(self, state):
        self._animation.stop()
        if bool(state):
            self._animation.setEndValue(1)
        else:
            self._animation.setEndValue(0)
        self._animation.start()

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        contRect = self.contentsRect()
        diameter = contRect.height()
        radius = diameter / 2

        # Determine current text based on handle position
        # during the animation - switch it right in the middle.
        if self._handlePositionMultiplier > 0.5:
            currentText = self._checkedText
        else:
            currentText = self._uncheckedText

        # Determine used brushes based on check state.
        if self.isChecked():
            bodyBrush = self._checkedBodyBrush
            handleBrush = self._checkedHandleBrush

        else:
            bodyBrush = self._uncheckedBodyBrush
            handleBrush = self._uncheckedHandleBrush

        # Draw the toggle's body.
        painter.setPen(Qt.NoPen)
        painter.setBrush(bodyBrush)
        painter.drawRoundedRect(contRect, radius, radius)

        painter.setPen(QPen(handleBrush.color().darker(110)))
        painter.setBrush(handleBrush)

        # Draw the text.
        painter.save()

        textPosMultiplier = (1.0 - self._handlePositionMultiplier)
        textRectX = diameter * textPosMultiplier + self._TEXT_SIDE_PADDING * self._handlePositionMultiplier
        textRectWidth = contRect.width() - diameter - self._TEXT_SIDE_PADDING
        textRect = QRect(textRectX, 0, textRectWidth, contRect.height())

        if self.isEnabled():
            # Trick for fading the text through the handle during transition.
            textOpacity = abs(0.5 - self._handlePositionMultiplier) * 2
        else:
            # Override text opacity for disabled toggle.
            textOpacity = 0.5

        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor.fromRgbF(0, 0, 0, textOpacity)))
        painter.drawText(textRect, Qt.AlignCenter, str(currentText))
        painter.restore()

        # Adjust the handle drawing brush if the toggle is not enabled.
        if not self.isEnabled():
            newColor = painter.brush().color()
            newColor.setAlphaF(0.5)
            painter.setBrush(QBrush(newColor))

        # Draw the handle.
        travelDistance = contRect.width() - diameter
        handlePosX = contRect.x() + radius + travelDistance * self._handlePositionMultiplier
        handleRadius = self._HANDLE_REL_SIZE * radius
        painter.drawEllipse(QPointF(handlePosX, contRect.center().y() + 1), handleRadius, handleRadius)

        painter.restore()

    def setChecked(self, checked):
        super().setChecked(checked)
        # Ensure we are in the finished animation state if there are signals blocked from the outside!
        if self.signalsBlocked():
            self._handlePositionMultiplier = 1 if checked else 0
            # Ensure the toggle is updated visually even though it seems this is not necessary.
            self.update()
        self._updateText()

    def setCheckedNoAnim(self, checked):
        self._animation.setDuration(0)
        self.setChecked(checked)
        self._animation.setDuration(self._ANIMATION_DURATION)

    def setCheckedColor(self, color):
        self._checkedHandleBrush = QBrush(color)
        self._checkedBodyBrush = QBrush(color.lighter(170))

    def setUncheckedColor(self, color):
        self._uncheckedHandleBrush = QBrush(color)
        self._uncheckedBodyBrush = QBrush(color.lighter(170))


class StatusProgressBar(QtWidgets.QProgressBar):
    NORMAL = "normal"
    ERROR = "error"
    SUCCESS = "success"
    CANCELLED = "cancelled"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = self.NORMAL
        self.setTextVisible(True)
        self.setMinimum(0)
        self.setMaximum(100)

    # set the states

    def setNormal(self):
        self._state = self.NORMAL
        self.update()

    def setError(self):
        self._state = self.ERROR
        self.update()

    def setSuccess(self, flash=True):
        self._state = self.SUCCESS
        self.update()

        if flash:
            QtCore.QTimer.singleShot(400, self.setNormal)

    def setCancelled(self):
        self._state = self.CANCELLED
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        rect = self.rect()

        # Background
        painter.fillRect(rect, SkinIOTheme.BACKGROUND_COLOR)

        # Compute progress
        progress = (self.value() - self.minimum()) / (self.maximum() - self.minimum())
        progress_rect = QtCore.QRect(
            rect.x(),
            rect.y(),
            int(rect.width() * progress),
            rect.height()
        )

        if progress <= 0.1:
            painter.fillRect(rect, SkinIOTheme.BACKGROUND_COLOR.darker(200))
            painter.setPen(SkinIOTheme.TEXT_COLOR)
            painter.drawText(rect, QtCore.Qt.AlignCenter, self.text())
            return

        # Choose gradient based on state
        if self._state == self.NORMAL:
            left = SkinIOTheme.PROGRESS_COLOR_LEFT
            right = SkinIOTheme.PROGRESS_COLOR_RIGHT
            text = SkinIOTheme.TEXT_COLOR

        elif self._state == self.ERROR:
            left = SkinIOTheme.FAIL_COLOR_LEFT
            right = SkinIOTheme.FAIL_COLOR_RIGHT
            text = SkinIOTheme.BACKGROUND_COLOR

        elif self._state == self.SUCCESS:
            left = SkinIOTheme.SUCCESS_COLOR_LEFT
            right = SkinIOTheme.SUCCESS_COLOR_RIGHT
            text = SkinIOTheme.BACKGROUND_COLOR

        elif self._state == self.CANCELLED:
            left = SkinIOTheme.CANCEL_COLOR_LEFT
            right = SkinIOTheme.CANCEL_COLOR_RIGHT
            text = SkinIOTheme.BACKGROUND_COLOR

        else:
            left = SkinIOTheme.PROGRESS_COLOR_LEFT
            right = SkinIOTheme.PROGRESS_COLOR_RIGHT
            text = SkinIOTheme.TEXT_COLOR

        # Draw gradient chunk
        gradient = QtGui.QLinearGradient(rect.topLeft(), rect.topRight())
        gradient.setColorAt(0, left)
        gradient.setColorAt(1, right)
        painter.fillRect(progress_rect, gradient)

        # Draw text
        painter.setPen(text)
        painter.drawText(rect, QtCore.Qt.AlignCenter, self.text())


class IOListModel(QtCore.QAbstractListModel):
    NAME_ROLE = QtCore.Qt.UserRole + 1
    ENABLED_ROLE = QtCore.Qt.UserRole + 2
    SELECTED_ROLE = QtCore.Qt.UserRole + 3
    ANIM_ROLE = QtCore.Qt.UserRole + 4

    ANIM_DURATION = 200  # ms

    def __init__(self):
        super().__init__()
        self._items = []  # each: {"name": str, "enabled": bool, "selected": bool, "anim": float}
        self._animations = {}  # row → (start_time, start_value, end_value)

        self._timer = QtCore.QTimer()
        self._timer.timeout.connect(self._update_animations)

    # Required Qt signatures
    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._items)

    def roleNames(self):
        return {
            self.NAME_ROLE: b"name",
            self.ENABLED_ROLE: b"enabled",
            self.SELECTED_ROLE: b"selected",
            self.ANIM_ROLE: b"anim",
        }

    # Data access
    def data(self, index, role):
        if not index.isValid():
            return None

        item = self._items[index.row()]

        if role == self.NAME_ROLE:
            return item["name"]
        if role == self.ENABLED_ROLE:
            return item["enabled"]
        if role == self.SELECTED_ROLE:
            return item["selected"]
        if role == self.ANIM_ROLE:
            return item["anim"]

        return None

    def setData(self, index, value, role):
        if not index.isValid():
            return False

        row = index.row()
        item = self._items[row]

        if role == self.ENABLED_ROLE:
            item["enabled"] = value
            self._start_animation(index, value)

        elif role == self.SELECTED_ROLE:
            item["selected"] = value

        elif role == self.ANIM_ROLE:
            item["anim"] = value

        else:
            return False

        self.dataChanged.emit(index, index, [role])
        return True

    def flags(self, index):
        return (
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsSelectable
        )

    # the actual model operataions
    def addItem(self, name):
        """Add a single item."""
        self.beginInsertRows(QtCore.QModelIndex(), len(self._items), len(self._items))
        self._items.append({
            "name": name,
            "enabled": False,
            "selected": False,
            "anim": 0.0
        })
        self.endInsertRows()

    def clear(self):
        """Clear all items."""
        self.beginResetModel()
        self._items = []
        self._animations = {}
        self.endResetModel()

    def enable_all(self):
        """Enable all items and animate them to ON."""
        for row in range(len(self._items)):
            index = self.index(row)
            self.setData(index, True, self.ENABLED_ROLE)
            self.setData(index, 1.0, self.ANIM_ROLE)

    def disable_all(self):
        """Disable all items and animate them to OFF."""
        for row in range(len(self._items)):
            index = self.index(row)
            self.setData(index, False, self.ENABLED_ROLE)
            self.setData(index, 0.0, self.ANIM_ROLE)

    def get_enabled_items(self):
        """Return list of names where enabled=True."""
        return [item["name"] for item in self._items if item["enabled"]]

    def clear_selection(self):
        changed = []
        for row, item in enumerate(self._items):
            if item["selected"]:
                item["selected"] = False
                changed.append(row)

        for row in changed:
            index = self.index(row)
            self.dataChanged.emit(index, index, [self.SELECTED_ROLE])

    def set_selected_items(self, names):
        changed = []
        name_set = set(names)

        for row, item in enumerate(self._items):
            new_state = item["name"] in name_set
            if item["selected"] != new_state:
                item["selected"] = new_state
                changed.append(row)

        for row in changed:
            index = self.index(row)
            self.dataChanged.emit(index, index, [self.SELECTED_ROLE])

    # Animation for the toggöe pm
    def _start_animation(self, index, enabled):
        row = index.row()
        now = QtCore.QTime.currentTime().msecsSinceStartOfDay()

        start = self._items[row]["anim"]
        end = 1.0 if enabled else 0.0

        self._animations[row] = (now, start, end)

        if not self._timer.isActive():
            self._timer.start(16)

    def _update_animations(self):
        if not self._animations:
            self._timer.stop()
            return

        now = QtCore.QTime.currentTime().msecsSinceStartOfDay()
        finished = []

        for row, (start_time, start, end) in list(self._animations.items()):
            t = (now - start_time) / self.ANIM_DURATION
            if t >= 1.0:
                t = 1.0
                finished.append(row)

            value = start + (end - start) * t
            self._items[row]["anim"] = value

            index = self.index(row)
            self.dataChanged.emit(index, index, [self.ANIM_ROLE])

        for row in finished:
            self._animations.pop(row, None)


class IOItemDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._geom_cache = {}

    def sizeHint(self, option, index):
        # Increase this value to make items taller
        return QtCore.QSize(option.rect.width(), 34)


    def paint(self, painter, option, index):
        painter.save()

        name = index.data(IOListModel.NAME_ROLE)
        selected = index.data(IOListModel.SELECTED_ROLE)
        anim = index.data(IOListModel.ANIM_ROLE)
        rect = option.rect

        base_grad = QtGui.QLinearGradient(rect.left(), rect.top(), rect.right(), rect.top())
        base_grad.setColorAt(0, SkinIOTheme.BASE_GRADIENT_LEFT)  # light at left
        base_grad.setColorAt(1, SkinIOTheme.BASE_GRADIENT_RIGHT)  # fade to transparent
        painter.fillRect(rect, base_grad)

        if selected:
            sel_grad = QtGui.QLinearGradient(rect.left(), rect.top(), rect.right(), rect.top())
            sel_grad.setColorAt(0, SkinIOTheme.TOGGLE_ON)
            sel_grad.setColorAt(1, SkinIOTheme.SELECTION_RIGHT)
            painter.fillRect(rect, sel_grad)

        if option.state & QtWidgets.QStyle.State_MouseOver:
            painter.fillRect(rect, SkinIOTheme.HOVER_COLOR)


        text_rect = rect.adjusted(10, 0, -60, 0)
        painter.setPen(SkinIOTheme.BACKGROUND_COLOR if selected else SkinIOTheme.TEXT_COLOR)
        painter.drawText(text_rect, QtCore.Qt.AlignVCenter, str(name))

        self._draw_toggle(painter, rect, anim)

        painter.restore()

    def editorEvent(self, event, model, option, index):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            if event.button() == QtCore.Qt.LeftButton:
                enabled = index.data(IOListModel.ENABLED_ROLE)
                model.setData(index, not enabled, IOListModel.ENABLED_ROLE)
                return True
        return False

    # TOGGLE DRAWING (unchanged)
    def _draw_toggle(self, painter, rect, anim):
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)

        h = rect.height()

        if h not in self._geom_cache:
            toggle_h = int(h * 0.55)
            toggle_w = int(toggle_h * 1.8)
            margin = int(h * 0.20)
            self._geom_cache[h] = (toggle_w, toggle_h, margin)

        toggle_w, toggle_h, margin = self._geom_cache[h]

        toggle_rect = QtCore.QRect(
            rect.right() - toggle_w - margin,
            rect.center().y() - toggle_h // 2,
            toggle_w,
            toggle_h
        )

        radius = toggle_h // 2

        off_handle = SkinIOTheme.TOGGLE_OFF
        on_handle = SkinIOTheme.TOGGLE_ON

        # Interpolated handle color
        handle_color = self._interpolate_color(off_handle, on_handle, anim)

        # Background is lighter version of handle color
        body_color = handle_color.lighter(170)

        # Draw body
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(body_color)
        painter.drawRoundedRect(toggle_rect, radius, radius)

        # Draw handle (same geometry as before)
        handle_diam = toggle_h - int(toggle_h * 0.25)
        travel = toggle_w - handle_diam - int(toggle_h * 0.15)

        handle_x = toggle_rect.left() + int(toggle_h * 0.075) + travel * anim
        handle_y = toggle_rect.center().y() - handle_diam // 2

        handle_rect = QtCore.QRect(
            int(handle_x),
            int(handle_y),
            handle_diam,
            handle_diam
        )

        painter.setBrush(handle_color)
        painter.drawEllipse(handle_rect)

    def _interpolate_color(self, c1, c2, t):
        return QtGui.QColor(
            int(c1.red() + (c2.red() - c1.red()) * t),
            int(c1.green() + (c2.green() - c1.green()) * t),
            int(c1.blue() + (c2.blue() - c1.blue()) * t),
            int(c1.alpha() + (c2.alpha() - c1.alpha()) * t),
        )


class IOListView(QtWidgets.QListView):
    item_clicked = QtCore.Signal(QtCore.QModelIndex, QtCore.Qt.KeyboardModifiers)
    request_clear = QtCore.Signal()
    request_refresh = QtCore.Signal()
    request_enable_all = QtCore.Signal()
    request_disable_all = QtCore.Signal()
    request_get_enabled = QtCore.Signal()

    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.setUniformItemSizes(True)
        self.setFocusPolicy(QtCore.Qt.NoFocus)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._open_menu)

    # emit item_clicked
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            index = self.indexAt(event.position().toPoint())
            if index.isValid():
                name = index.data(IOListModel.NAME_ROLE)
                modifiers = event.modifiers()
                self.item_clicked.emit(index, event.modifiers())

        super().mousePressEvent(event)

    # Context menu
    def _open_menu(self, pos):
        menu = QtWidgets.QMenu(self)

        act_get_all_enabled = menu.addAction("Get Enabled")
        menu.addSeparator()

        act_enable_all = menu.addAction("Enable All")
        act_disable_all = menu.addAction("Disable All")

        menu.addSeparator()
        act_clear = menu.addAction("Clear List")
        act_refresh = menu.addAction("Refresh List")

        # Disable actions if list is empty
        model = self.model()

        has_items = model is not None and model.rowCount() > 0

        act_get_all_enabled.setEnabled(has_items)
        act_enable_all.setEnabled(has_items)
        act_disable_all.setEnabled(has_items)

        action = menu.exec(self.mapToGlobal(pos))

        if action == act_clear:
            self.request_clear.emit()

        elif action == act_refresh:
            self.request_refresh.emit()

        elif action == act_enable_all:
            self.request_enable_all.emit()

        elif action == act_disable_all:
            self.request_disable_all.emit()

        elif action == act_get_all_enabled:
            self.request_get_enabled.emit()


class IOListWidget(QtWidgets.QWidget):
    item_selected = QtCore.Signal(list)

    def __init__(self, title, getter_operation, parent=None):
        super().__init__(parent)
        self.title = title

        self.model = IOListModel()

        self.proxy = QtCore.QSortFilterProxyModel()
        self.proxy.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.proxy.setSourceModel(self.model)

        self.view = IOListView()
        self.view.setModel(self.proxy)
        self.view.setItemDelegate(IOItemDelegate(self.view))

        self.getter_operation = getter_operation

        self._last_clicked_source_row = None

        self._create_widgets()
        self._create_layout()
        self._create_signals()

        self.refresh(self.getter_operation())

    def _create_widgets(self):

        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText("Searching...")

    def _create_layout(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(ThemedLabel(self.title))
        layout.addWidget(self.search)
        layout.addWidget(self.view)

    def _create_signals(self):
        self.search.textChanged.connect(self.apply_filter)
        self.view.item_clicked.connect(self._on_item_clicked)

        self.view.request_clear.connect(self.clear)
        self.view.request_refresh.connect(self._on_refresh_requested)
        self.view.request_enable_all.connect(self.enable_all)
        self.view.request_disable_all.connect(self.disable_all)

    def _on_item_clicked(self, proxy_index, modifiers):
        source_index = self.proxy.mapToSource(proxy_index)
        row = source_index.row()
        if row < 0:
            return

        #toggle
        if modifiers & QtCore.Qt.ControlModifier:
            current = self.model.data(source_index, IOListModel.SELECTED_ROLE)
            self.model.setData(source_index, not current, IOListModel.SELECTED_ROLE)

        #range selection
        elif modifiers & QtCore.Qt.ShiftModifier and self._last_clicked_source_row is not None:
            start = min(self._last_clicked_source_row, row)
            end = max(self._last_clicked_source_row, row)
            names = [
                self.model.data(self.model.index(r), IOListModel.NAME_ROLE)
                for r in range(start, end + 1)
            ]
            self.model.set_selected_items(names)

        #      single selection
        else:
            self.model.clear_selection()
            self.model.setData(source_index, True, IOListModel.SELECTED_ROLE)

        self._last_clicked_source_row = row

        # Emit selected names
        selected = [
            self.model.data(self.model.index(r), IOListModel.NAME_ROLE)
            for r in range(self.model.rowCount())
            if self.model.data(self.model.index(r), IOListModel.SELECTED_ROLE)
        ]
        self.item_selected.emit(selected)

    # exposed items
    def add_item(self, name):
        self.model.addItem(name)

    def add_list(self, names):
        for n in names:
            self.model.addItem(n)

    def clear(self):
        self.model.clear()

    def apply_filter(self, text):
        self.proxy.setFilterFixedString(text)

    def refresh(self, new_items):
        self.model.clear()
        for name in new_items:
            self.model.addItem(name)

    def enable_all(self):
        self.model.enable_all()

    def disable_all(self):
        self.model.disable_all()

    def get_enabled_items(self):
        enabled_items = self.model.get_enabled_items()
        return enabled_items

    def _on_refresh_requested(self):
        self.refresh(self.getter_operation())


@dataclass
class Flavour(ABC):
    title: str
    deformer_type: str
    external_fill_operation: Callable
    internal_fill_operation: Callable
    theme: Type[Theme]

