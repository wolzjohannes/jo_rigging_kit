"""
Usage:

from pxo_rigging_kit.maya_utils.guis import tool_skinio_gui
from importlib import reload

reload(tool_skinio_gui)

tool_skinio_gui.show_import_export_dialog()

"""



import logging
from dataclasses import dataclass
from typing import Callable, Type

import maya.OpenMayaUI as omui  # noqa: import error

from pxo_rigging_kit.maya_utils import decorators

import shiboken6  # noqa: import error
from PySide6 import QtCore, QtWidgets, QtGui  # noqa: import error
from PySide6.QtCore import Property, Qt, QSize, QPropertyAnimation, QEasingCurve, QRect, QPointF,QRectF,Signal  # noqa: import error
from PySide6.QtWidgets import QCheckBox, QSplashScreen  # noqa: import error
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QPixmap  # noqa: import error

from pxo_rigging_kit.maya_utils.deformers.handlers.deformer_handler import IOCallbacks, DeformerHandler

from pxo_rigging_kit.maya_utils.guis.custom_widgets import EscapeKeyFilter, GradientSplashScreen, ThemedLabel, \
    ThemedPushButton, ToggleSwitch, StatusProgressBar, IOListWidget, Theme, Flavour, SkinIOTheme

from pxo_rigging_kit.maya_utils.deformers.utilities.supply import get_external_skinclusters, get_internal_skinclusters


##########################################################
# GLOBALS
##########################################################


_LOGGER = logging.getLogger(f"{__name__}.py")
_LOGGER.setLevel(logging.INFO)

DECORATORS = decorators.Decorators()
DECORATORS.debug = True
DECORATORS.logger = _LOGGER

IO_WINDOW = None


@dataclass
class SkinIOFlavour(Flavour):
    title: str = "Skin I/O"
    deformer_type: str = "skin_cluster"
    external_fill_operation: Callable = get_external_skinclusters
    internal_fill_operation: Callable = get_internal_skinclusters
    theme: Type[Theme] = SkinIOTheme


#  main window TODO:most likely duplicate to somewhere, but idk what the best one is????


def maya_main_window():
    ptr = omui.MQtUtil.mainWindow()
    return shiboken6.wrapInstance(int(ptr), QtWidgets.QWidget)


###########################################
# Actual main ui
#########################################
class ImportExportDialog(QtWidgets.QDialog):
    def __init__(self,
                 flavour: Type[SkinIOFlavour],
                 handler: Type[DeformerHandler],
                 parent: QtWidgets.QWidget | None = None,
                 ):

        if not parent:
            parent = maya_main_window()

        super().__init__(parent)
        self.in_startup = True

        self.flavour = flavour()

        self.handler = handler  # we only create instances of this in the runner

        self.setWindowTitle(self.flavour.title)
        self.setMinimumWidth(900)
        self.setMinimumHeight(450)

        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowSystemMenuHint |
            QtCore.Qt.Window
        )

        self.driver = None
        self.old_pos = None

        self._create_widgets()
        self._create_layouts()
        self._attach_signals()

        self._esc_filter = EscapeKeyFilter()

        app = QtWidgets.QApplication.instance()
        app.installEventFilter(self._esc_filter)
        self.in_startup = False

    # WIDGETS
    def _create_widgets(self):
        # Title bar container
        self.title_bar_area = QtWidgets.QFrame()
        self.title_bar_area.setFixedHeight(32)
        self.title_bar_area.setStyleSheet(f""" {{ background-color: {SkinIOTheme.BACKGROUND_COLOR.name()}; }} """)

        self.window_title = ThemedLabel(self.windowTitle(), color=SkinIOTheme.PROGRESS_COLOR_LEFT)
        self.window_title.setStyleSheet("font-weight: bold; font-size: 30px;")

        self.close_btn = ThemedPushButton("X",
                                          text_color=SkinIOTheme.BACKGROUND_COLOR,
                                          base_color=SkinIOTheme.FAIL_COLOR_LEFT,
                                          hover_color=SkinIOTheme.FAIL_COLOR_LEFT.lighter(120),
                                          pressed_color=SkinIOTheme.FAIL_COLOR_LEFT.darker(110),
                                          )

        self.close_btn.setFixedSize(30, 30)

        # Size grip
        self.sizegrip = QtWidgets.QSizeGrip(self)

        # Lists
        self.import_list = IOListWidget(
            title="External Items",
            getter_operation=self.flavour.external_fill_operation
        )

        self.export_list = IOListWidget(
            title="Internal Items",
            getter_operation=self.flavour.internal_fill_operation
        )

        # Progress section
        self.main_progressbar = StatusProgressBar()
        self.main_progressbar.setRange(0, 100)

        self.sub_progressbar = StatusProgressBar()
        self.sub_progressbar.setRange(0, 100)
        self.sub_progressbar.setFixedHeight(10)

        self.annotation = ThemedLabel("Waiting...",
                                      color=SkinIOTheme.BACKGROUND_COLOR.lighter(400)
                                      )

        self.percentage = ThemedLabel("0%", )

        self.operation_name = ThemedLabel("Idle",
                                          color=SkinIOTheme.BACKGROUND_COLOR.lighter(400)
                                          )

        self.process_name = ThemedLabel("",
                                        color=SkinIOTheme.BACKGROUND_COLOR.lighter(400)
                                        )

        # Options THIS WILL NEED TO BE REDONE ONCE WE HAVE MULTIPLE FLAVOURS
        self.numpy_lbl = ThemedLabel("Numpy")
        self.numpy = ToggleSwitch(checkedText="query",
                                  uncheckedText="pass"
                                  )

        self.numpy.setChecked(True)

        self.json_lbl = ThemedLabel("JSon")
        self.json = ToggleSwitch(checkedText="query",
                                 uncheckedText="pass"
                                 )

        self.xml_lbl = ThemedLabel("Xml")
        self.xml = ToggleSwitch(checkedText="query",
                                uncheckedText="pass"
                                )

        self.ng_lbl = ThemedLabel("NG")
        self.ng = ToggleSwitch(checkedText="query",
                               uncheckedText="pass"
                               )


        # Buttons
        self.import_btn = ThemedPushButton("Import")
        self.export_btn = ThemedPushButton("Export")

        self.autorename_btn = ThemedPushButton("Rename By Transform Name")

        self.rebuild_pruned_btn = ThemedPushButton("Prune Internal Nodes")

        self.cancel_btn = ThemedPushButton("Cancel",
                                           hover_color=SkinIOTheme.FAIL_COLOR_LEFT,
                                           pressed_color=SkinIOTheme.FAIL_COLOR_LEFT.darker(110),
                                           )

    # LAYOUTS
    def _create_layouts(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Title bar layout
        title_layout = QtWidgets.QHBoxLayout(self.title_bar_area)
        title_layout.setContentsMargins(6, 0, 6, 0)
        title_layout.addWidget(self.window_title)
        title_layout.addStretch()
        title_layout.addWidget(self.close_btn)

        # Content layout
        content = QtWidgets.QVBoxLayout()
        content.setContentsMargins(10, 10, 10, 10)
        content.setSpacing(10)

        import_list_layout = QtWidgets.QVBoxLayout()
        import_list_layout.addWidget(self.import_list)
        import_list_layout.addWidget(self.import_btn)

        export_list_layout = QtWidgets.QVBoxLayout()
        export_list_layout.addWidget(self.export_list)

        btn_sub_layout = QtWidgets.QVBoxLayout()
        btn_sub_layout.addWidget(self.autorename_btn)
        btn_sub_layout.addWidget(self.rebuild_pruned_btn)
        btn_sub_layout.addWidget(self.export_btn)

        export_list_layout.addLayout(btn_sub_layout)

        # Lists
        lists_layout = QtWidgets.QHBoxLayout()
        lists_layout.addLayout(import_list_layout)
        lists_layout.addLayout(export_list_layout)
        content.addLayout(lists_layout)

        # Progress info
        info_layout = QtWidgets.QHBoxLayout()
        info_layout.addWidget(self.annotation)
        info_layout.addStretch()
        info_layout.addWidget(self.percentage)
        content.addLayout(info_layout)

        content.addWidget(QtWidgets.QLabel("Main Progress"))
        content.addWidget(self.main_progressbar)

        content.addWidget(QtWidgets.QLabel("Sub-Process Progress"))
        content.addWidget(self.sub_progressbar)

        subinfo_layout = QtWidgets.QHBoxLayout()
        subinfo_layout.addWidget(self.operation_name)
        subinfo_layout.addStretch()
        subinfo_layout.addWidget(self.process_name)
        content.addLayout(subinfo_layout)

        btn_layout = QtWidgets.QVBoxLayout()

        options_layout = QtWidgets.QGridLayout()
        options_layout.setHorizontalSpacing(30)
        options_layout.setVerticalSpacing(22)
        options_layout.setContentsMargins(50, 5, 50, 5)

        options_layout.addWidget(self.numpy_lbl, 0, 0, Qt.AlignRight)
        options_layout.addWidget(self.numpy, 0, 1, Qt.AlignLeft)

        options_layout.addWidget(self.json_lbl, 0, 2, Qt.AlignRight)
        options_layout.addWidget(self.json, 0, 3, Qt.AlignLeft)

        options_layout.addWidget(self.xml_lbl, 1, 0, Qt.AlignRight)
        options_layout.addWidget(self.xml, 1, 1, Qt.AlignLeft)

        options_layout.addWidget(self.ng_lbl, 1, 2, Qt.AlignRight)
        options_layout.addWidget(self.ng, 1, 3, Qt.AlignLeft)

        outer = QtWidgets.QHBoxLayout()
        outer.addStretch()
        outer.addLayout(options_layout)
        outer.addStretch()

        btn_layout.addLayout(outer)
        btn_layout.addWidget(self.cancel_btn)

        content.addLayout(btn_layout)

        # Add everything to main layout
        main_layout.addWidget(self.title_bar_area)
        main_layout.addLayout(content)

        # Size grip
        main_layout.addWidget(
            self.sizegrip,
            0,
            QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom
        )

    # SIGNALS
    def _attach_signals(self):
        self.close_btn.clicked.connect(self.close)
        self.cancel_btn.clicked.connect(self.cancel_operation)

        self.import_btn.clicked.connect(self.start_runner)

        self.export_btn.clicked.connect(self.start_runner)
        self.autorename_btn.clicked.connect(self.start_runner)
        self.rebuild_pruned_btn.clicked.connect(self.start_runner)

    # this starts the operation
    def start_runner(self):

        if self.driver is not None:
            self.annotation.setText("Operation already running...")
            return

        sender = self.sender()

        if sender == self.import_btn:
            items = self.import_list.get_enabled_items()
            operation = "import"

        elif sender == self.export_btn:
            items = self.export_list.get_enabled_items()
            operation = "export"

        elif sender == self.autorename_btn:
            items = sorted(self.export_list.get_enabled_items())
            operation = "rename"

        elif sender == self.rebuild_pruned_btn:
            items = sorted(self.export_list.get_enabled_items())
            operation = "prune"

        else:
            self.annotation.setText("Unknown operation.")
            return

        if not items:
            self.annotation.setText(f"No {operation} items selected.")
            return

        extra_params = self.collect_ui_settings()

        handler_ = self.handler(
            transforms=items,
            operation_type=operation,
            deformer_type=self.flavour.deformer_type,
            additional_arguments=extra_params,
        )

        self.driver = IOHandlerQtDriver(handler_)

        self.driver.main_progress.connect(self.update_main_progress)
        self.driver.sub_progress.connect(self.update_sub_progress)
        self.driver.message.connect(self.update_message)
        self.driver.cancelled.connect(self.on_cancelled)
        self.driver.error_occurred.connect(self.on_error)
        self.driver.step_finished.connect(self.on_step_finished)

        self.driver.finished.connect(self.on_finished)
        self.driver.finished.connect(self._cleanup_driver)

        self.driver.start()

    def cancel_operation(self):
        if self.driver:
            self.driver.handler.request_cancel()
            self.annotation.setText("Cancelling...")
            self._cleanup_driver()

    def _cleanup_driver(self):

        if not self.driver:
            return

        try:
            self.driver.main_progress.disconnect()
            self.driver.sub_progress.disconnect()
            self.driver.message.disconnect()
            self.driver.cancelled.disconnect()
            self.driver.error_occurred.disconnect()
            self.driver.step_finished.disconnect()
            self.driver.finished.disconnect()

        except:
            pass

        self.driver = None

    def collect_ui_settings(self):
        return {
            "numpy": self.numpy.isChecked(),
            "json": self.json.isChecked(),
            "xml": self.xml.isChecked(),
            "ng": self.ng.isChecked(),
        }

    # update slots
    def update_main_progress(self, value, text):
        self.main_progressbar.setValue(value)
        self.main_progressbar.setNormal()

        self.percentage.setText(f"{value}%")
        self.operation_name.setText(text)

    def update_sub_progress(self, value, text):
        self.sub_progressbar.setNormal()
        self.sub_progressbar.setValue(value)
        self.process_name.setText(text)

    def update_message(self, text):
        self.annotation.setText(text)

    def on_cancelled(self):
        self.main_progressbar.setCancelled()
        self.sub_progressbar.setCancelled()
        self.annotation.setText("Operation cancelled.")
        self.main_progressbar.setValue(0)

    def on_finished(self):
        self.main_progressbar.setSuccess(flash=False)
        self.sub_progressbar.setSuccess(flash=False)
        self.annotation.setText("Operation finished.")

    def on_error(self, msg):
        self.main_progressbar.setError()
        self.sub_progressbar.setError()
        self.annotation.setText(f"Error: {msg}")

    def on_step_finished(self, step_name):
        self.sub_progressbar.setSuccess()

    # EVENts
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            if self.title_bar_area.geometry().contains(event.position().toPoint()):
                self._drag_active = True
                self.old_pos = event.globalPosition().toPoint()
            else:
                self._drag_active = False

    def mouseMoveEvent(self, event):
        if getattr(self, "_drag_active", False):
            current = event.globalPosition().toPoint()
            delta = current - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = current

    def mouseReleaseEvent(self, event):
        self._drag_active = False

    def resizeEvent(self, event):
        self.sizegrip.move(
            self.width() - self.sizegrip.width(),
            self.height() - self.sizegrip.height()
        )
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        gradient = SkinIOTheme.BACKGROUND_COLOR
        painter.fillRect(self.rect(), gradient)


# We just want to fire signals here
class IOHandlerQtDriver(QtCore.QObject):
    main_progress = QtCore.Signal(int, str)
    sub_progress = QtCore.Signal(int, str)
    message = QtCore.Signal(str)
    finished = QtCore.Signal()
    cancelled = QtCore.Signal()
    error_occurred = QtCore.Signal(str)
    step_finished = QtCore.Signal(str)

    def __init__(self, handler):
        super().__init__()
        self.handler = handler

        self.callbacks = IOCallbacks(
            main_progress=lambda pct, msg: self.main_progress.emit(pct, msg),
            sub_progress=lambda pct, msg: self.sub_progress.emit(pct, msg),
            message=lambda msg: self.message.emit(msg),
            error=lambda msg: self.error_occurred.emit(msg),
            step_finished=lambda step: self.step_finished.emit(step),
            finished=lambda: self.finished.emit(),
            cancelled=lambda: self.cancelled.emit(),
        )

    def start(self):
        self._run_next_step()

    def _run_next_step(self):
        if self.handler.cancel_requested:
            self.cancelled.emit()
            return

        has_more = self.handler.run_step(self.callbacks)

        if has_more:
            QtCore.QTimer.singleShot(0, self._run_next_step)
        else:
            if self.handler.cancel_requested:
                self.cancelled.emit()
            else:
                self.finished.emit()


def show_skinio_window():
    global IO_WINDOW

    try:
        IO_WINDOW.close() # noqa
        IO_WINDOW.deleteLater() # noqa
    except: # noqa: bare except
        pass

    IO_WINDOW = None
    pix = QPixmap(r"X:\_pxm\logos\PXO_Logos\PNG\PXO_logo_black_4k.png")

    scaled_logo = pix.scaled(
        pix.width() * 0.05,
        pix.height() * 0.05,
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation)

    splash_screen = GradientSplashScreen(scaled_logo)

    splash_screen.start()
    QtWidgets.QApplication.processEvents()

    def load_main():
        global IO_WINDOW
        IO_WINDOW = ImportExportDialog(flavour=SkinIOFlavour, handler=DeformerHandler)
        splash_screen.fadeOut()
        splash_screen.finish(IO_WINDOW)
        IO_WINDOW.show()

    QtCore.QTimer.singleShot(50, load_main)   # 50ms is enough


def main():
    show_skinio_window()


if __name__ == "__main__":
    main()
