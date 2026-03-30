import time

from PySide6 import QtCore, QtWidgets, QtGui
import maya.OpenMayaUI as omui
import shiboken6
import maya.cmds as cmds


from PySide6.QtCore import Property, Qt, QSize, QPropertyAnimation, QEasingCurve, QRect, QPointF
from PySide6.QtWidgets import QCheckBox
from PySide6.QtGui import QColor, QPainter, QPen, QBrush
from maya.api import OpenMaya as om2

BASE_GRADIENT_LEFT = QtGui.QColor(255, 255, 255, 18)
BASE_GRADIENT_RIGHT = QtGui.QColor(255, 255, 255, 0)

# Selection gradient
SELECTION_LEFT = QtGui.QColor(70, 120, 200, 180)
SELECTION_RIGHT = QtGui.QColor(70, 120, 200, 0)

# Hover overlay
HOVER_COLOR = QtGui.QColor(255, 255, 255, 20)

# Toggle colors
TOGGLE_OFF = QtGui.QColor(150, 150, 150)
TOGGLE_ON = QtGui.QColor(0, 176, 255)
TOGGLE_HANDLE = QtGui.QColor(255, 255, 255)

# Text
TEXT_COLOR = QtGui.QColor(220, 220, 220)



# ============================================================
#  MAYA MAIN WINDOW
# ============================================================

def maya_main_window():
    ptr = omui.MQtUtil.mainWindow()
    return shiboken6.wrapInstance(int(ptr), QtWidgets.QWidget)


# ============================================================
#  TOGGLE SWITCH WIDGET
# ============================================================

class ToggleSwitch(QCheckBox):
    _ANIMATION_DURATION = 200  # Time in ms.
    _HANDLE_REL_SIZE = 0.82
    _PREFERRED_HEIGHT = 10
    _TEXT_SIDE_PADDING = 4

    def __init__(self, checkedText="", uncheckedText="", checkedColor=TOGGLE_ON,
                 uncheckedColor=TOGGLE_OFF, fontHeightRatio=0.9, parent=None):
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
        painter.drawText(textRect, Qt.AlignCenter, currentText)
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


# ============================================================
#  MODEL
# ============================================================
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

    # ------------------------------------------------------------
    # Required Qt signatures
    # ------------------------------------------------------------
    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._items)

    def roleNames(self):
        return {
            self.NAME_ROLE: b"name",
            self.ENABLED_ROLE: b"enabled",
            self.SELECTED_ROLE: b"selected",
            self.ANIM_ROLE: b"anim",
        }

    # ------------------------------------------------------------
    # Data access
    # ------------------------------------------------------------
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

    # ------------------------------------------------------------
    # PUBLIC API (RESTORED)
    # ------------------------------------------------------------
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

    # ------------------------------------------------------------
    # Animation
    # ------------------------------------------------------------
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

# ============================================================
#  DELEGATE (ClickableFrame + ToggleSwitch merged)
# ============================================================
class IOItemDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._geom_cache = {}

    def sizeHint(self, option, index):
        # Increase this value to make items taller
        return QtCore.QSize(option.rect.width(), 34)

    # ------------------------------------------------------------
    # PAINT
    # ------------------------------------------------------------
    def paint(self, painter, option, index):
        painter.save()

        name = index.data(IOListModel.NAME_ROLE)
        selected = index.data(IOListModel.SELECTED_ROLE)
        anim = index.data(IOListModel.ANIM_ROLE)
        rect = option.rect

        # --------------------------------------------------------

        base_grad = QtGui.QLinearGradient(rect.left(), rect.top(), rect.right(), rect.top())
        base_grad.setColorAt(0.0, QtGui.QColor(255, 255, 255, 18))   # light at left
        base_grad.setColorAt(1.0, QtGui.QColor(255, 255, 255, 0))    # fade to transparent
        painter.fillRect(rect, base_grad)

        # --------------------------------------------------------
        # 2. SELECTION GRADIENT (your original)
        # --------------------------------------------------------
        if selected:
            sel_grad = QtGui.QLinearGradient(rect.left(), rect.top(), rect.right(), rect.top())
            sel_grad.setColorAt(0, QtGui.QColor(70, 120, 200, 180))
            sel_grad.setColorAt(1, QtGui.QColor(70, 120, 200, 0))
            painter.fillRect(rect, sel_grad)

        # --------------------------------------------------------
        # 3. HOVER HIGHLIGHT
        # --------------------------------------------------------
        if option.state & QtWidgets.QStyle.State_MouseOver:
            painter.fillRect(rect, QtGui.QColor(255, 255, 255, 20))

        # --------------------------------------------------------
        # 4. TEXT
        # --------------------------------------------------------
        text_rect = rect.adjusted(10, 0, -60, 0)
        painter.setPen(TEXT_COLOR)
        painter.drawText(text_rect, QtCore.Qt.AlignVCenter, name)

        # --------------------------------------------------------
        # 5. TOGGLE SWITCH
        # --------------------------------------------------------
        self._draw_toggle(painter, rect, anim)

        painter.restore()

    # ------------------------------------------------------------
    # SINGLE CLICK TOGGLE
    # ------------------------------------------------------------

    def editorEvent(self, event, model, option, index):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            if event.button() == QtCore.Qt.LeftButton:
                enabled = index.data(IOListModel.ENABLED_ROLE)
                model.setData(index, not enabled, IOListModel.ENABLED_ROLE)
                return True
        return False

    # ------------------------------------------------------------
    # TOGGLE DRAWING (unchanged)
    # ------------------------------------------------------------
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

        off_color = QtGui.QColor(150, 150, 150)
        on_color = QtGui.QColor(0, 176, 255)
        bg_color = self._interpolate_color(off_color, on_color, anim)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(bg_color)
        painter.drawRoundedRect(toggle_rect, radius, radius)

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

        painter.setBrush(QtGui.QColor(255, 255, 255))
        painter.drawEllipse(handle_rect)

    def _interpolate_color(self, c1, c2, t):
        return QtGui.QColor(
            int(c1.red() + (c2.red() - c1.red()) * t),
            int(c1.green() + (c2.green() - c1.green()) * t),
            int(c1.blue() + (c2.blue() - c1.blue()) * t),
            int(c1.alpha() + (c2.alpha() - c1.alpha()) * t),
        )

# ============================================================
#  VIEW
# ============================================================


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

    # ------------------------------------------------------------
    # Mouse click → emit item_clicked (left button only)
    # ------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            index = self.indexAt(event.position().toPoint())
            if index.isValid():
                name = index.data(IOListModel.NAME_ROLE)
                modifiers = event.modifiers()
                self.item_clicked.emit(index, event.modifiers())


        super().mousePressEvent(event)

    # ------------------------------------------------------------
    # Context menu
    # ------------------------------------------------------------
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
            print("yoooooooooooooooo")

        elif action == act_enable_all:
            self.request_enable_all.emit()

        elif action == act_disable_all:
            self.request_disable_all.emit()

        elif action == act_get_all_enabled:
            self.request_get_enabled.emit()

# ============================================================
#  WRAPPER WIDGET
# ============================================================

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

    # ------------------------------------------------------------
    # WIDGET SETUP
    # ------------------------------------------------------------
    def _create_widgets(self):

        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText("Search...")

    def _create_layout(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel(self.title))
        layout.addWidget(self.search)
        layout.addWidget(self.view)
        print("added layouts")

    def _create_signals(self):
        self.search.textChanged.connect(self.apply_filter)
        self.view.item_clicked.connect(self._on_item_clicked)

        self.view.request_clear.connect(self.clear)
        self.view.request_refresh.connect(self._on_refresh_requested)
        self.view.request_enable_all.connect(self.enable_all)
        self.view.request_disable_all.connect(self.disable_all)
        print("added signals")

    # ------------------------------------------------------------
    # MULTI-SELECTION LOGIC (fixed)
    # ------------------------------------------------------------
    def _on_item_clicked(self, proxy_index, modifiers):
        source_index = self.proxy.mapToSource(proxy_index)
        row = source_index.row()
        if row < 0:
            return

        # CTRL → toggle
        if modifiers & QtCore.Qt.ControlModifier:
            current = self.model.data(source_index, IOListModel.SELECTED_ROLE)
            self.model.setData(source_index, not current, IOListModel.SELECTED_ROLE)

        # SHIFT → range selection
        elif modifiers & QtCore.Qt.ShiftModifier and self._last_clicked_source_row is not None:
            start = min(self._last_clicked_source_row, row)
            end = max(self._last_clicked_source_row, row)
            names = [
                self.model.data(self.model.index(r), IOListModel.NAME_ROLE)
                for r in range(start, end + 1)
            ]
            self.model.set_selected_items(names)

        # No modifier → single selection
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

    # ------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------
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
        return self.model.get_enabled_items()

    def _on_refresh_requested(self):
        self.refresh(self.getter_operation())

# ============================================================
#  MAIN DIALOG (MAYA-FRIENDLY)
# ============================================================




class ImportExportDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):

        if not parent:
            parent = maya_main_window()

        super().__init__(parent)

        self.setWindowTitle("Import / Export Tool")
        self.setMinimumWidth(550)
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

    # ------------------------------------------------------------
    # WIDGETS
    # ------------------------------------------------------------
    def _create_widgets(self):
        # Title bar container
        self.title_bar_area = QtWidgets.QFrame()
        self.title_bar_area.setFixedHeight(32)
        self.title_bar_area.setStyleSheet("background-color: #2b2b2b;")

        self.window_title = QtWidgets.QLabel(self.windowTitle())
        self.window_title.setStyleSheet("font-weight: bold; font-size: 14px; color: white;")

        self.close_btn = QtWidgets.QPushButton("X")
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.setStyleSheet("color: white; background: #444; border: none;")

        # Size grip
        self.sizegrip = QtWidgets.QSizeGrip(self)

        # Lists
        self.import_list = IOListWidget(
            title="Import Items",
            getter_operation=_get_trs_test
        )

        self.export_list = IOListWidget(
            title="Export Items",
            getter_operation=_get_lol_test
        )

        # Progress section
        self.main_progressbar = QtWidgets.QProgressBar()
        self.main_progressbar.setRange(0, 100)

        self.sub_progressbar = QtWidgets.QProgressBar()
        self.sub_progressbar.setRange(0, 100)

        self.annotation = QtWidgets.QLabel("Waiting...")
        self.percentage = QtWidgets.QLabel("0%")
        self.operation_name = QtWidgets.QLabel("Idle")
        self.process_name = QtWidgets.QLabel("")

        # Options
        self.export_all_btn = ToggleSwitch(checkedText="export_all")
        self.import_all_btn = ToggleSwitch(checkedText="import_all")

        # Buttons
        self.import_btn = QtWidgets.QPushButton("Import")
        self.export_btn = QtWidgets.QPushButton("Export")
        self.cancel_btn = QtWidgets.QPushButton("Cancel")

    # ------------------------------------------------------------
    # LAYOUTS
    # ------------------------------------------------------------
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

        # Lists
        lists_layout = QtWidgets.QHBoxLayout()
        lists_layout.addWidget(self.import_list)
        lists_layout.addWidget(self.export_list)
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

        # Buttons
        btn_layout = QtWidgets.QVBoxLayout()

        options_layout = QtWidgets.QHBoxLayout()
        options_layout.addWidget(self.export_all_btn)
        options_layout.addWidget(self.import_all_btn)

        btn_sub_layout = QtWidgets.QHBoxLayout()
        btn_sub_layout.addWidget(self.import_btn)
        btn_sub_layout.addWidget(self.export_btn)

        btn_layout.addLayout(options_layout)
        btn_layout.addLayout(btn_sub_layout)
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

    # ------------------------------------------------------------
    # SIGNALS
    # ------------------------------------------------------------
    def _attach_signals(self):
        self.close_btn.clicked.connect(self.close)

        self.import_btn.clicked.connect(self.start_runner)
        self.export_btn.clicked.connect(self.start_runner)

        self.cancel_btn.clicked.connect(self.cancel_operation)

    # ------------------------------------------------------------
    # RUNNER LOGIC
    # ------------------------------------------------------------
    def start_runner(self):
        # Prevent multiple drivers
        if self.driver is not None:
            self.annotation.setText("Operation already running...")
            return

        sender = self.sender()
        if sender == self.import_btn:
            items = self.import_list.get_enabled_items()
            operation = "Import"
        elif sender == self.export_btn:
            items = self.export_list.get_enabled_items()
            operation = "Export"
        else:
            self.annotation.setText("Unknown operation.")
            return

        if not items:
            self.annotation.setText(f"No {operation.lower()} items selected.")
            return

        om2.MGlobal.displayInfo(f"{operation} runner started")

        handler = IOHandler(items)
        self.driver = IOHandlerQtDriver(handler)

        # Connect signals
        self.driver.main_progress.connect(self.update_main_progress)
        self.driver.sub_progress.connect(self.update_sub_progress)
        self.driver.message.connect(self.update_message)
        self.driver.cancelled.connect(self.on_cancelled)
        self.driver.finished.connect(self.on_finished)
        self.driver.finished.connect(self._cleanup_driver)

        self.driver.start()

    def cancel_operation(self):
        if self.driver:
            self.driver.handler.request_cancel()
            self.annotation.setText("Cancelling...")

    def _cleanup_driver(self):
        if not self.driver:
            return

        try:
            self.driver.main_progress.disconnect()
            self.driver.sub_progress.disconnect()
            self.driver.message.disconnect()
            self.driver.cancelled.disconnect()
            self.driver.finished.disconnect()
        except:
            pass

        self.driver = None

    # ------------------------------------------------------------
    # UI UPDATE SLOTS
    # ------------------------------------------------------------
    def update_main_progress(self, value, text):
        self.main_progressbar.setValue(value)
        self.percentage.setText(f"{value}%")
        self.operation_name.setText(text)

    def update_sub_progress(self, value, text):
        self.sub_progressbar.setValue(value)
        self.process_name.setText(text)

    def update_message(self, text):
        self.annotation.setText(text)

    def on_cancelled(self):
        self.annotation.setText("Operation cancelled.")
        self.main_progressbar.setValue(0)

    def on_finished(self):
        self.annotation.setText("Operation finished.")

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


# ============================================================
#  IO CALLBACKS
# ============================================================


class IOCallbacks:
    def __init__(self, main_progress=None, sub_progress=None, message=None):
        self.main_progress = main_progress
        self.sub_progress = sub_progress
        self.message = message


# ============================================================
#  IO HANDLER (PURE PYTHON, STEP-BASED, MAYA-SAFE)
# ============================================================


class IOHandler:
    """
    Replace the simulated work with real OpenMaya / cmds operations.
    """

    def __init__(self, items):
        self.items = items
        self.index = 0
        self.substep = 0
        self.cancel_requested = False

        self._assert_main_thread()

    def request_cancel(self):
        self.cancel_requested = True

    def has_more_work(self):
        return self.index < len(self.items)

    def run_step(self, callbacks: IOCallbacks):
        if self.cancel_requested:
            if callbacks.message:
                callbacks.message("Operation cancelled.")
            return False

        if not self.has_more_work():
            if callbacks.message:
                callbacks.message("All operations completed.")
            return False

        item = self.items[self.index]

        # Sub-step work
        if self.substep < 5:
            self._assert_main_thread()
            # Replace with real OpenMaya work
            time.sleep(0.05)

            sub_pct = int(((self.substep + 1) / 5) * 100)

            if callbacks.sub_progress:
                callbacks.sub_progress(sub_pct, f"{item}: step {self.substep + 1}/5")

            om2.MGlobal.displayInfo("hello from substep")
            self._test_mfnmesh_creation(f"{item}_step_{self.substep + 1}")
            QtWidgets.QApplication.processEvents()

            self.substep += 1
            return True

        # Move to next item
        self.index += 1
        self.substep = 0

        if callbacks.main_progress:
            main_pct = int((self.index / len(self.items)) * 100)
            callbacks.main_progress(main_pct, f"Processing {item}")

        return self.has_more_work()

    def _assert_main_thread(self):
        """
        This is the safest and most reliable main-thread check in Maya.
        If this function throws, you are NOT on the main thread.
        """
        try:
            # This is guaranteed main-thread only
            om2.MGlobal.getActiveSelectionList()
        except Exception as e:
            raise RuntimeError(
                "OpenMaya 2.0 call failed — importer is NOT running on the main thread.\n"
                "Error: {}".format(e)
            )

    def _test_mfnmesh_creation(self, item_name):
        """
        Safe, minimal MFnMesh creation.
        If this runs without crashing, we are on the main thread.
        """

        # Define 3 vertices
        points = [
            om2.MPoint(0, 0, 0),
            om2.MPoint(1, 0, 0),
            om2.MPoint(0, 1, 0)
        ]

        # One triangle face
        face_counts = [3]
        face_connects = [0, 1, 2]

        # Create the mesh
        mesh_fn = om2.MFnMesh()
        mesh_obj = mesh_fn.create(
            points,
            face_counts,
            face_connects
        )

        # Name it
        mesh_fn.setName("{}_testMesh".format(item_name))

        # Return something useful
        return mesh_fn.name()




class IOHandlerQtDriver(QtCore.QObject):

    main_progress = QtCore.Signal(int, str)
    sub_progress = QtCore.Signal(int, str)
    message = QtCore.Signal(str)
    finished = QtCore.Signal()
    cancelled = QtCore.Signal()

    def __init__(self, handler):
        super().__init__()
        self.handler = handler

        self.callbacks = IOCallbacks(
            main_progress=lambda pct, msg: self.main_progress.emit(pct, msg),
            sub_progress=lambda pct, msg: self.sub_progress.emit(pct, msg),
            message=lambda msg: self.message.emit(msg)
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


# ============================================================
#  ENTRY POINT FOR MAYA
# ============================================================

def _get_trs_test():
    return cmds.ls("name_*_trs*")


def _get_lol_test():
    return ["lol"]*10


def show_import_export_dialog():
    for w in QtWidgets.QApplication.topLevelWidgets():
        if isinstance(w, ImportExportDialog):
            w.close()

    dlg = ImportExportDialog()
    dlg.show()
    return dlg


def main():
    for x in range(20):
        cmds.createNode("transform", n=f"name_{x}_trs")

    show_import_export_dialog()


if __name__ == "__main__":
    main()
