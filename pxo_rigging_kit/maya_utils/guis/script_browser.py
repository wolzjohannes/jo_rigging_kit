#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Maya Script Browser - Professional Script Management Tool for Maya
Version: 1.0
Author: Maya Script Browser Team
Description: A comprehensive script browser with customizable categories, user colors, and icons
Matteo Turrisi - turrisimatteo@gmail.com 06/2025
"""

import os
import json
import glob
import datetime
import traceback
import hashlib
import getpass
from collections import defaultdict
from functools import partial

import maya.cmds as cmds
from maya import OpenMayaUI as omui
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
import maya.mel as mel

try:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtCore import Qt, QTimer, Signal
    from shiboken2 import wrapInstance

except ImportError:
    from PySide6 import QtWidgets, QtCore, QtGui
    from PySide6.QtCore import Qt, QTimer, Signal
    from shiboken6 import wrapInstance

# =============================================================================
# GLOBAL DEFAULT SETTINGS - All default configurations in one place
# =============================================================================

# File paths
USER_SCRIPTS_DIR = cmds.internalVar(userScriptDir=True)
SCRIPT_DIR = r"X:\_staff_Folders\_departments\rigging\scripts"

DEFAULT_BROWSER_FOLDER = os.path.join(SCRIPT_DIR, 'maya_script_browser')
SETTINGS_FILE = os.path.join(SCRIPT_DIR, "maya_script_browser", 'maya_script_browser_settings.json')

# Default categories with their colors and icons
DEFAULT_CATEGORIES = ['Uncategorized',
                      'Rigging',
                      'Animation',
                      'Modeling',
                      'FX',
                      'Pipeline',
                      'Utilities'
                      ]

DEFAULT_CATEGORY_COLORS = {
    'Rigging': '#e74c3c',
    'Animation': '#3498db',
    'Modeling': '#2ecc71',
    'FX': '#9b59b6',
    'Pipeline': '#f39c12',
    'Utilities': '#34495e',
    'Uncategorized': '#7f8c8d'
}

DEFAULT_CATEGORY_ICONS = {
    'Rigging': '🦴',
    'Animation': '🎬',
    'Modeling': '🎨',
    'FX': '✨',
    'Pipeline': '⚙️',
    'Utilities': '🔧',
    'Uncategorized': '📄'
}

# User color generation palette - Used to assign unique colors to users
USER_COLOR_PALETTE = [
    '#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6',
    '#1abc9c', '#34495e', '#e67e22', '#16a085', '#8e44ad',
    '#2c3e50', '#d35400', '#c0392b', '#7f8c8d', '#27ae60'
]

# Available icon suggestions for users
AVAILABLE_ICONS = [
    '📄', '📁', '🎬', '🎨', '✨', '⚙️', '🔧', '🦴', '🎭', '🎪',
    '🎯', '🚀', '💡', '🔥', '⭐', '🏆', '💎', '🌟', '🎮', '🎸',
    '🎵', '🎧', '📷', '🎥', '🖌️', '🖍️', '✏️', '📐', '📏', '🔨',
    '🔩', '⚡', '💫', '🌈', '🎪', '🎭', '🎨', '🖼️', '🛠️', '📊'
]

# Application settings defaults
DEFAULT_SETTINGS = {
    'browser_folder': DEFAULT_BROWSER_FOLDER,
    'favorites': [],
    'sort_order': 'name',
    'include_subfolders': True,
    'categories': DEFAULT_CATEGORIES,
    'auto_save': True,
    'search_in_content': False,
    'recent_scripts': [],
    'max_recent': 10,
    'preview_font_size': 10,
    'category_colors': DEFAULT_CATEGORY_COLORS,
    'category_icons': DEFAULT_CATEGORY_ICONS,
    'user_colors': {},  # Stores custom colors for each user
    'show_user_colors': True,  # Toggle to show/hide user colors
    'window_geometry': None,  # Stores window size and position
    'preview_visible': False  # Remember preview panel state
}

# UI Theme colors
THEME_COLORS = {
    'background': '#2b2b2b',
    'background_light': '#363636',
    'background_dark': '#1e1e1e',
    'border': '#555',
    'border_light': '#666',
    'text': '#EEE',
    'text_dim': '#999',
    'accent': '#5a9fd4',
    'accent_hover': '#7fbff4',
    'success': '#4CAF50',
    'error': '#F44336',
    'warning': '#FF9800'
}


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def maya_main_window():
    """Get Maya main window as Qt widget"""
    try:
        ptr = omui.MQtUtil.mainWindow()
        return wrapInstance(int(ptr), QtWidgets.QMainWindow) if ptr else None
    except:
        return None


def maya_api_version():
    """Get Maya API version for compatibility checks"""
    try:
        return int(cmds.about(api=True))
    except:
        return 201700  # Default to Maya 2017


def is_single_emoji(text):
    """
    Check if the text is a single emoji character
    This is a simple check that works for most common emojis
    """
    if not text or len(text) > 4:  # Most emojis are 1-4 characters
        return False

    # Check if it's in our approved emoji list
    if text in AVAILABLE_ICONS:
        return True

    # Basic check for emoji ranges (simplified)
    try:
        # Check if it's likely an emoji by trying to encode it
        text.encode('ascii')
        return False  # If it encodes to ASCII, it's not an emoji
    except UnicodeEncodeError:
        # If it can't be encoded to ASCII, it might be an emoji
        # This is a simplified check - in production you might want to use regex
        return len(text) <= 2  # Most emojis are 1-2 characters in Python


def generate_user_color(username):
    """
    Generate a consistent color for a username
    Uses hash to ensure same user always gets same color
    """
    if not username:
        return '#999999'

    # Create hash from username
    hash_value = hash(username) % len(USER_COLOR_PALETTE)
    return USER_COLOR_PALETTE[hash_value]


# =============================================================================
# SETTINGS MANAGER
# =============================================================================

class SettingsManager(object):
    """
    Manages application settings with automatic saving and caching
    Handles both user preferences and script metadata cache
    """

    def __init__(self):
        self._settings = self._load_settings()
        self.browser_folder = self._settings.get('browser_folder', DEFAULT_BROWSER_FOLDER)
        self.cache_folder = os.path.join(self.browser_folder, '.cache')
        self.cache_file = os.path.join(self.cache_folder, 'metadata_cache.json')
        self._create_directories()
        self._cache = self._load_cache()

    def _create_directories(self):
        """Create necessary directories for browser and cache"""
        for folder in [self.browser_folder, self.cache_folder]:
            try:
                if not os.path.exists(folder):
                    os.makedirs(folder)
            except:
                pass

    def _load_settings(self):
        """Load settings from JSON file, merge with defaults"""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    settings = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    for key, value in DEFAULT_SETTINGS.items():
                        settings.setdefault(key, value)
                    return settings
        except:
            pass
        return dict(DEFAULT_SETTINGS)

    def _load_cache(self):
        """Load metadata cache for faster script loading"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
        except:
            pass
        return {}

    def save_settings(self):
        """Save current settings to JSON file"""
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(self._settings, f, indent=2)
        except Exception as e:
            print("Failed to save settings: {}".format(e))

    def save_cache(self):
        """Save metadata cache to improve loading performance"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self._cache, f, indent=2)
        except:
            pass

    def get(self, key, default=None):
        """Get a setting value with optional default"""
        return self._settings.get(key, default)

    def set(self, key, value):
        """Set a setting value and auto-save if enabled"""
        self._settings[key] = value
        if key == 'browser_folder':
            self.browser_folder = value
            self.cache_folder = os.path.join(value, '.cache')
            self.cache_file = os.path.join(self.cache_folder, 'metadata_cache.json')
            self._create_directories()
        if self.get('auto_save', True):
            self.save_settings()

    def get_cache(self, file_path):
        """Get cached metadata for a file"""
        file_hash = self._get_file_hash(file_path)
        return self._cache.get(file_hash) if file_hash else None

    def set_cache(self, file_path, metadata):
        """Cache metadata for a file"""
        file_hash = self._get_file_hash(file_path)
        if file_hash:
            self._cache[file_hash] = metadata

    def _get_file_hash(self, file_path):
        """Generate hash based on file path and modification time"""
        try:
            mtime = os.path.getmtime(file_path)
            return hashlib.md5("{}_{:.6f}".format(file_path, mtime).encode('utf-8')).hexdigest()
        except:
            return None

    def get_user_color(self, username):
        """Get custom color for a user, generate if not exists"""
        if not username:
            return '#999999'

        user_colors = self.get('user_colors', {})
        if username not in user_colors:
            # Generate and store a color for this user
            user_colors[username] = generate_user_color(username)
            self.set('user_colors', user_colors)

        return user_colors[username]


# Global settings instance
SETTINGS = SettingsManager()


# =============================================================================
# THEME MANAGER
# =============================================================================

class ThemeManager(object):
    """Manages UI themes and styling"""

    @staticmethod
    def get_main_style():
        """Get main application stylesheet"""
        return """
            QMainWindow, QWidget {{
                background: {bg};
                color: {text};
                font-family: 'Segoe UI', Arial, sans-serif;
            }}

            /* Search container */
            #searchContainer {{
                background: {bg_light};
                border-bottom: 2px solid {border};
                padding: 15px;
            }}

            /* Search bar */
            #searchBar {{
                background: #3a3a3a;
                border: 2px solid {border};
                border-radius: 20px;
                padding: 10px 20px;
                font-size: 14px;
                color: {text};
                min-height: 36px;
            }}
            #searchBar:focus {{
                border-color: {accent};
                background: #404040;
            }}

            /* Filter container */
            #filterContainer {{
                background: #303030;
                border-bottom: 1px solid #444;
                padding: 10px 15px;
            }}

            /* Buttons */
            QPushButton {{
                background: #444;
                color: {text};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 5px 10px;
                font-weight: bold;
                font-size: 11px;
                min-height: 26px;
            }}
            QPushButton:hover {{
                background: {border};
                border-color: {accent};
            }}
            QPushButton:checked {{
                background: {accent};
                border-color: {accent_hover};
            }}

            /* ComboBox */
            QComboBox {{
                background: #3a3a3a;
                border: 1px solid {border};
                border-radius: 4px;
                padding: 4px 8px;
                color: {text};
                font-size: 11px;
                min-height: 24px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid {text_dim};
                margin-right: 6px;
            }}

            /* List widget */
            QListWidget {{
                background: {bg};
                border: none;
                padding: 5px;
            }}
            QListWidget::item {{
                background: transparent;
                border: none;
                margin-bottom: 3px;
            }}

            /* Scrollbar */
            QScrollBar:vertical {{
                background: {bg};
                width: 10px;
            }}
            QScrollBar::handle:vertical {{
                background: {border};
                border-radius: 5px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {border_light};
            }}
        """.format(
            bg=THEME_COLORS['background'],
            bg_light=THEME_COLORS['background_light'],
            bg_dark=THEME_COLORS['background_dark'],
            border=THEME_COLORS['border'],
            border_light=THEME_COLORS['border_light'],
            text=THEME_COLORS['text'],
            text_dim=THEME_COLORS['text_dim'],
            accent=THEME_COLORS['accent'],
            accent_hover=THEME_COLORS['accent_hover']
        )

    @staticmethod
    def get_card_style(selected=False, hovered=False):
        """Get style for script cards based on state"""
        if selected:
            return "background: {}; border: 1px solid {}; border-radius: 4px; color: white;".format(
                THEME_COLORS['accent'], THEME_COLORS['accent_hover']
            )
        elif hovered:
            return "background: #3a3a3a; border: 1px solid {}; border-radius: 4px;".format(
                THEME_COLORS['accent']
            )
        else:
            return "background: #333333; border: 1px solid #444444; border-radius: 4px;"


# =============================================================================
# SCRIPT METADATA
# =============================================================================

class ScriptMetadata(object):
    """Handles extraction and parsing of script metadata from file headers"""

    @staticmethod
    def extract(file_path):
        """
        Extract metadata from a Python script file
        Looks for special comment headers at the top of the file
        """
        name = os.path.splitext(os.path.basename(file_path))[0]
        try:
            modified_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
            file_size = os.path.getsize(file_path)
        except:
            modified_time = datetime.datetime.now()
            file_size = 0

        metadata = {
            'name': name,
            'path': file_path,
            'description': '',
            'tags': [],
            'category': 'Uncategorized',
            'user': '',
            'content': '',
            'modified': modified_time,
            'size': file_size
        }

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                metadata['content'] = content

                # Parse header comments for metadata
                for line in content.splitlines()[:20]:  # Check first 20 lines
                    if line.startswith('#'):
                        ScriptMetadata._parse_header_line(line, metadata)
                    elif line.strip() and not line.startswith('#'):
                        break  # Stop at first non-comment line
        except Exception as e:
            print("Error reading {}: {}".format(file_path, e))

        return metadata

    @staticmethod
    def _parse_header_line(line, metadata):
        """Parse a comment line for metadata information"""
        line = line.lstrip('#').strip()
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip().lower()
            value = value.strip()

            if key == 'description':
                metadata['description'] = value
            elif key == 'category' and value in SETTINGS.get('categories', []):
                metadata['category'] = value
            elif key == 'tags':
                metadata['tags'] = [t.strip() for t in value.split(',') if t.strip()]
            elif key == 'user':
                metadata['user'] = value


# =============================================================================
# SCRIPT CARD WIDGET
# =============================================================================

class ScriptCard(QtWidgets.QWidget):
    """
    Visual card representation of a script
    Shows icon, name, description, category, user, and tags
    """
    clicked = Signal(object)
    doubleClicked = Signal(object)

    def __init__(self, metadata, parent=None):
        super(ScriptCard, self).__init__(parent)
        self.metadata = metadata
        self._selected = False
        self._hovered = False
        self.setFixedHeight(90)
        self.setCursor(Qt.PointingHandCursor)
        self._setup_ui()
        self._update_style()

    def _setup_ui(self):
        """Setup card UI with icon, text, and badges"""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Top row: Icon + Name + Badges
        top_layout = QtWidgets.QHBoxLayout()
        top_layout.setSpacing(10)

        # Category icon with background color
        icon_widget = QtWidgets.QLabel()
        icon_text = SETTINGS.get('category_icons', {}).get(self.metadata['category'], '📄')
        icon_widget.setText(icon_text)
        icon_widget.setStyleSheet("""
            QLabel {
                font-size: 20px;
                min-width: 32px;
                max-width: 32px;
                min-height: 32px;
                max-height: 32px;
                background: %s;
                border-radius: 16px;
                qproperty-alignment: AlignCenter;
            }
        """ % self._get_category_color())
        top_layout.addWidget(icon_widget)

        # Name and description
        text_layout = QtWidgets.QVBoxLayout()
        text_layout.setSpacing(2)

        self.name_label = QtWidgets.QLabel(self.metadata['name'])
        self.name_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #EEE;")
        text_layout.addWidget(self.name_label)

        if self.metadata['description']:
            desc_label = QtWidgets.QLabel(self.metadata['description'])
            desc_label.setStyleSheet("color: #BBB; font-size: 10px;")
            desc_label.setWordWrap(True)
            desc_label.setMaximumHeight(20)
            text_layout.addWidget(desc_label)

        top_layout.addLayout(text_layout, 1)

        # Right side: User + Category badges + Favorite
        badges_layout = QtWidgets.QHBoxLayout()
        badges_layout.setSpacing(5)

        # User badge with custom color
        if self.metadata.get('user'):
            user_label = QtWidgets.QLabel(self.metadata['user'])
            user_color = SETTINGS.get_user_color(self.metadata['user'])
            user_label.setStyleSheet("""
                background: {}; color: white; padding: 2px 8px;
                border-radius: 10px; font-size: 9px; font-weight: bold;
            """.format(user_color))
            badges_layout.addWidget(user_label)

        # Category badge
        category_label = QtWidgets.QLabel(self.metadata['category'])
        category_label.setStyleSheet("""
            background: %s; color: white; padding: 2px 8px;
            border-radius: 10px; font-size: 9px; font-weight: bold;
        """ % self._get_category_color())
        badges_layout.addWidget(category_label)

        # Favorite button
        self.fav_button = QtWidgets.QPushButton()
        self.fav_button.setFixedSize(24, 24)
        self.fav_button.setFlat(True)
        self.fav_button.clicked.connect(self._toggle_favorite)
        self._update_favorite_button()
        badges_layout.addWidget(self.fav_button)

        top_layout.addLayout(badges_layout)
        layout.addLayout(top_layout)

        # Bottom row: Tags + Date
        if self.metadata['tags']:
            bottom_layout = QtWidgets.QHBoxLayout()
            bottom_layout.setContentsMargins(44, 0, 0, 0)

            tags_text = " ".join(["#{}".format(tag) for tag in self.metadata['tags'][:3]])
            tags_label = QtWidgets.QLabel(tags_text)
            tags_label.setStyleSheet("color: #88B0D3; font-size: 9px; font-style: italic;")
            bottom_layout.addWidget(tags_label)

            bottom_layout.addStretch()

            date_label = QtWidgets.QLabel(self.metadata['modified'].strftime("%m/%d"))
            date_label.setStyleSheet("color: #777; font-size: 9px;")
            bottom_layout.addWidget(date_label)

            layout.addLayout(bottom_layout)

    def _get_category_color(self):
        """Get the color assigned to this category"""
        colors = SETTINGS.get('category_colors', DEFAULT_CATEGORY_COLORS)
        return colors.get(self.metadata['category'], '#7f8c8d')

    def _update_favorite_button(self):
        """Update favorite button appearance based on state"""
        is_fav = self.metadata['name'] in SETTINGS.get('favorites', [])
        self.fav_button.setText('★' if is_fav else '☆')
        self.fav_button.setStyleSheet(
            'font-size: 16px; color: #FFD700; background: transparent; border: none;' if is_fav else
            'font-size: 16px; color: #666; background: transparent; border: none;'
        )

    def _toggle_favorite(self):
        """Toggle favorite status of this script"""
        favorites = SETTINGS.get('favorites', [])
        if self.metadata['name'] in favorites:
            favorites.remove(self.metadata['name'])
        else:
            favorites.append(self.metadata['name'])
        SETTINGS.set('favorites', favorites)
        self._update_favorite_button()

    def set_selected(self, selected):
        """Set selection state of the card"""
        self._selected = selected
        self._update_style()

    def _update_style(self):
        """Update card appearance based on state"""
        self.setStyleSheet(ThemeManager.get_card_style(self._selected, self._hovered))

    def enterEvent(self, event):
        """Handle mouse enter - show hover state"""
        self._hovered = True
        if not self._selected:
            self._update_style()

    def leaveEvent(self, event):
        """Handle mouse leave - remove hover state"""
        self._hovered = False
        if not self._selected:
            self._update_style()

    def mousePressEvent(self, event):
        """Handle mouse click"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self)

    def mouseDoubleClickEvent(self, event):
        """Handle double click - execute script"""
        if event.button() == Qt.LeftButton:
            self.doubleClicked.emit(self)


# =============================================================================
# CODE PREVIEW WIDGET
# =============================================================================

class CodePreview(QtWidgets.QPlainTextEdit):
    """Code preview widget with adjustable font size"""

    def __init__(self, parent=None):
        super(CodePreview, self).__init__(parent)
        self.setReadOnly(True)
        self._update_font_size()

    def _update_font_size(self):
        """Update font based on saved preference"""
        font_size = SETTINGS.get('preview_font_size', 10)
        font = QtGui.QFont('Consolas', font_size)
        font.setStyleHint(QtGui.QFont.Monospace)
        self.setFont(font)

    def change_font_size(self, delta):
        """Change font size by delta amount"""
        current = SETTINGS.get('preview_font_size', 10)
        new_size = max(8, min(16, current + delta))
        SETTINGS.set('preview_font_size', new_size)
        self._update_font_size()


# =============================================================================
# SCRIPT LOADER THREAD
# =============================================================================

class ScriptLoader(QtCore.QThread):
    """Background thread for loading scripts without blocking UI"""
    scriptsLoaded = Signal(list)
    progressUpdate = Signal(str)

    def run(self):
        """Load all Python scripts from the browser folder"""
        self.progressUpdate.emit("Scanning for scripts...")
        scripts = []
        browser_folder = SETTINGS.browser_folder
        pattern = '**/*.py' if SETTINGS.get('include_subfolders', True) else '*.py'

        try:
            files = glob.glob(os.path.join(browser_folder, pattern),
                              recursive=SETTINGS.get('include_subfolders', True))

            for i, file_path in enumerate(files):
                if i % 10 == 0:
                    self.progressUpdate.emit("Loading scripts... {}/{}".format(i + 1, len(files)))

                # Check cache first for faster loading
                cached = SETTINGS.get_cache(file_path)
                if cached:
                    scripts.append(cached)
                else:
                    # Extract metadata and cache it
                    metadata = ScriptMetadata.extract(file_path)
                    SETTINGS.set_cache(file_path, metadata)
                    scripts.append(metadata)

            SETTINGS.save_cache()
            self.progressUpdate.emit("Loaded {} scripts".format(len(scripts)))
        except Exception as e:
            self.progressUpdate.emit("Error loading scripts: {}".format(e))

        self.scriptsLoaded.emit(scripts)


# =============================================================================
# SCRIPT FILTER
# =============================================================================

class ScriptFilter(object):
    """Handles filtering of scripts based on various criteria"""

    @staticmethod
    def filter_scripts(scripts, search_text="", category="All Categories", user="All Users",
                       show_favorites_only=False, search_in_content=False):
        """
        Filter scripts based on search criteria
        Returns list of scripts matching all criteria
        """
        filtered = []
        favorites = SETTINGS.get('favorites', [])
        search_lower = search_text.lower()

        for script in scripts:
            # Check favorites filter
            if show_favorites_only and script['name'] not in favorites:
                continue

            # Check category filter
            if category != "All Categories" and script['category'] != category:
                continue

            # Check user filter
            if user != "All Users" and script.get('user', '') != user:
                continue

            # Check search text
            if search_text:
                found = any(search_lower in str(script.get(field, '')).lower()
                            for field in ['name', 'description', 'category', 'user'])

                # Search in tags
                if not found:
                    found = any(search_lower in tag.lower() for tag in script.get('tags', []))

                # Search in content if enabled
                if not found and search_in_content:
                    found = search_lower in script.get('content', '').lower()

                if not found:
                    continue

            filtered.append(script)

        return filtered


# =============================================================================
# MAIN SCRIPT BROWSER WINDOW
# =============================================================================

class MayaScriptBrowser(MayaQWidgetDockableMixin, QtWidgets.QMainWindow):
    """
    Main Script Browser Window
    Provides a dockable interface for managing and executing Maya scripts
    """
    WINDOW_NAME = "MayaScriptBrowser"
    WORKSPACE_CONTROL_NAME = WINDOW_NAME + "WorkspaceControl"

    def __init__(self, parent=None):
        self.deleteInstances()
        super(MayaScriptBrowser, self).__init__(parent=parent)

        # Window setup
        self.setObjectName(self.WINDOW_NAME)
        self.setWindowTitle('Maya Script Browser v1.0')
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        # Restore window geometry if saved
        geometry = SETTINGS.get('window_geometry')
        if geometry:
            self.restoreGeometry(QtCore.QByteArray.fromBase64(geometry))
        else:
            self.resize(1000, 700)

        # Data storage
        self.scripts = []
        self.script_cards = {}
        self.current_selection = None
        self._selected_script_name = None

        # Setup UI
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)

        self._setup_ui()
        self._apply_theme()
        self._setup_shortcuts()
        self._load_scripts()

    def deleteInstances(self):
        """Clean up any existing instances to prevent duplicates"""
        try:
            if cmds.workspaceControl(self.WORKSPACE_CONTROL_NAME, query=True, exists=True):
                cmds.workspaceControl(self.WORKSPACE_CONTROL_NAME, edit=True, close=True)
                cmds.deleteUI(self.WORKSPACE_CONTROL_NAME, control=True)
        except:
            pass

        # Clean up old window instances
        maya_main = maya_main_window()
        if maya_main:
            for obj in maya_main.children():
                if hasattr(obj, 'objectName') and obj.objectName() == self.WINDOW_NAME and obj != self:
                    try:
                        obj.setParent(None)
                        obj.deleteLater()
                    except:
                        pass

    def _setup_ui(self):
        """Setup main UI layout"""
        main_layout = QtWidgets.QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Search container at the top
        search_container = self._create_search_container()
        main_layout.addWidget(search_container)

        # Filter container below search
        filter_container = self._create_filter_container()
        main_layout.addWidget(filter_container)

        # Content area with splitter
        self.content_splitter = QtWidgets.QSplitter(Qt.Horizontal)

        # Left panel - script list
        left_panel = self._create_left_panel()
        self.content_splitter.addWidget(left_panel)

        # Right panel - preview
        self.preview_panel = self._create_preview_panel()
        self.content_splitter.addWidget(self.preview_panel)

        # Restore preview visibility
        preview_visible = SETTINGS.get('preview_visible', False)
        self.preview_panel.setVisible(preview_visible)
        self.toggle_preview_btn.setChecked(preview_visible)
        self.content_splitter.setSizes([600, 400] if preview_visible else [1, 0])

        main_layout.addWidget(self.content_splitter)

    def _create_search_container(self):
        """Create search bar container"""
        container = QtWidgets.QWidget()
        container.setObjectName("searchContainer")
        container.setFixedHeight(70)
        layout = QtWidgets.QHBoxLayout(container)
        layout.setSpacing(10)

        # Search bar
        self.search_bar = QtWidgets.QLineEdit()
        self.search_bar.setObjectName("searchBar")
        self.search_bar.setPlaceholderText("🔍 Search scripts... (Enter to run)")
        self.search_bar.textChanged.connect(self._on_search_changed)
        self.search_bar.returnPressed.connect(self._on_search_enter)
        layout.addWidget(self.search_bar)

        # Preview toggle button
        self.toggle_preview_btn = QtWidgets.QPushButton("👁")
        self.toggle_preview_btn.setCheckable(True)
        self.toggle_preview_btn.setFixedSize(40, 36)
        self.toggle_preview_btn.setToolTip("Toggle preview panel")
        self.toggle_preview_btn.toggled.connect(self._toggle_preview_panel)
        layout.addWidget(self.toggle_preview_btn)

        return container

    def _create_filter_container(self):
        """Create filter controls container"""
        container = QtWidgets.QWidget()
        container.setObjectName("filterContainer")
        container.setFixedHeight(50)
        layout = QtWidgets.QHBoxLayout(container)
        layout.setSpacing(15)

        # Category filter
        self.category_combo = QtWidgets.QComboBox()
        self.category_combo.addItem("All Categories")
        self.category_combo.addItems(SETTINGS.get('categories', []))
        self.category_combo.currentTextChanged.connect(self._apply_filters)
        self.category_combo.setMinimumWidth(120)
        layout.addWidget(QtWidgets.QLabel("Category:"))
        layout.addWidget(self.category_combo)

        # User filter
        self.user_combo = QtWidgets.QComboBox()
        self.user_combo.addItem("All Users")
        self.user_combo.currentTextChanged.connect(self._apply_filters)
        self.user_combo.setMinimumWidth(100)
        layout.addWidget(QtWidgets.QLabel("User:"))
        layout.addWidget(self.user_combo)

        # Favorites toggle
        self.favorites_btn = QtWidgets.QPushButton("★")
        self.favorites_btn.setCheckable(True)
        self.favorites_btn.toggled.connect(self._apply_filters)
        self.favorites_btn.setFixedSize(32, 26)
        self.favorites_btn.setToolTip("Show favorites only")
        layout.addWidget(self.favorites_btn)

        layout.addStretch()

        # Action buttons
        for text, slot, tip in [
            ("+", self._new_script, "New Script"),
            ("↻", self._load_scripts, "Refresh"),
            ("⚙", self._show_settings, "Settings")
        ]:
            btn = QtWidgets.QPushButton(text)
            btn.setFixedSize(32, 26)
            btn.setToolTip(tip)
            btn.clicked.connect(slot)
            layout.addWidget(btn)

        return container

    def _create_left_panel(self):
        """Create left panel with script list"""
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Sort controls
        sort_widget = QtWidgets.QWidget()
        sort_layout = QtWidgets.QHBoxLayout(sort_widget)
        sort_layout.setContentsMargins(5, 0, 5, 0)

        sort_layout.addWidget(QtWidgets.QLabel("Sort:"))

        self.sort_combo = QtWidgets.QComboBox()
        self.sort_combo.addItems(["Name", "Date", "Category"])
        self.sort_combo.setCurrentText(SETTINGS.get('sort_order', 'name').title())
        self.sort_combo.currentTextChanged.connect(self._on_sort_changed)
        sort_layout.addWidget(self.sort_combo)

        sort_layout.addStretch()

        self.results_label = QtWidgets.QLabel("0")
        self.results_label.setStyleSheet("color: #999; font-weight: bold;")
        sort_layout.addWidget(self.results_label)

        layout.addWidget(sort_widget)

        # Script list
        self.script_list = QtWidgets.QListWidget()
        self.script_list.setSpacing(2)
        self.script_list.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.script_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.script_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.script_list.customContextMenuRequested.connect(self._show_context_menu)
        self.script_list.currentItemChanged.connect(self._on_list_selection_changed)
        layout.addWidget(self.script_list)

        return panel

    def _create_preview_panel(self):
        """Create preview panel for code display"""
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)

        # Header with title and font controls
        header_layout = QtWidgets.QHBoxLayout()
        self.preview_title = QtWidgets.QLabel("Select a script to preview")
        self.preview_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        header_layout.addWidget(self.preview_title)
        header_layout.addStretch()

        # Font size controls
        for text, delta in [("-", -1), ("+", 1)]:
            btn = QtWidgets.QPushButton(text)
            btn.setFixedSize(25, 25)
            btn.delta_value = delta
            btn.clicked.connect(self._on_font_size_click)
            header_layout.addWidget(btn)

        layout.addLayout(header_layout)

        # Script info widget
        self.info_widget = QtWidgets.QWidget()
        self.info_widget.setStyleSheet("background: #3a3a3a; border-radius: 4px; padding: 8px;")
        self.info_widget.setVisible(False)

        info_layout = QtWidgets.QVBoxLayout(self.info_widget)
        self.info_label = QtWidgets.QLabel()
        self.info_label.setWordWrap(True)
        info_layout.addWidget(self.info_label)

        layout.addWidget(self.info_widget)

        # Code preview
        self.code_preview = CodePreview()
        self.code_preview.setStyleSheet("""
            QPlainTextEdit {
                background: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #444;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.code_preview, 1)

        # Instructions
        layout.addWidget(QtWidgets.QLabel("💡 Right-click scripts for actions • Enter to run"))

        return panel

    def _on_font_size_click(self):
        """Handle font size button click"""
        sender = self.sender()
        if hasattr(sender, 'delta_value') and hasattr(self, 'code_preview'):
            self.code_preview.change_font_size(sender.delta_value)

    def _toggle_preview_panel(self, visible):
        """Toggle preview panel visibility"""
        self.preview_panel.setVisible(visible)
        self.content_splitter.setSizes([600, 400] if visible else [1, 0])
        self.toggle_preview_btn.setStyleSheet(
            "background: #5a9fd4;" if visible else "background: #444;"
        )
        # Save preference
        SETTINGS.set('preview_visible', visible)

    def _load_scripts(self):
        """Load scripts in background thread"""
        self._show_message("Loading scripts...")

        # Store current selection
        if self.current_selection:
            self._selected_script_name = self.current_selection.metadata['name']

        # Clear current data
        self.scripts = []
        self.script_cards = {}
        self.script_list.clear()

        # Start loader thread
        self.script_loader = ScriptLoader()
        self.script_loader.scriptsLoaded.connect(self._on_scripts_loaded)
        self.script_loader.progressUpdate.connect(self._show_message)
        self.script_loader.start()

    def _on_scripts_loaded(self, scripts):
        """Handle loaded scripts"""
        self.scripts = scripts
        self._update_user_combo()
        self._sort_scripts()
        self._populate_script_list()
        self._show_message("Loaded {} scripts".format(len(scripts)))
        self._restore_selection()

    def _update_user_combo(self):
        """Update user combo with unique users"""
        users = set(script.get('user', '') for script in self.scripts if script.get('user', ''))
        current = self.user_combo.currentText()
        self.user_combo.clear()
        self.user_combo.addItem("All Users")
        for user in sorted(users):
            self.user_combo.addItem(user)
        if current in users:
            self.user_combo.setCurrentText(current)

    def _sort_scripts(self):
        """Sort scripts based on current setting"""
        sort_order = SETTINGS.get('sort_order', 'name').lower()
        if sort_order == 'name':
            self.scripts.sort(key=lambda x: x['name'].lower())
        elif sort_order == 'date':
            self.scripts.sort(key=lambda x: x['modified'], reverse=True)
        elif sort_order == 'category':
            self.scripts.sort(key=lambda x: (x['category'], x['name'].lower()))

    def _populate_script_list(self):
        """Populate script list with filtered results"""
        # Clear existing
        self.script_list.clear()
        old_cards = self.script_cards
        self.script_cards = {}

        # Clean up old cards
        for _, (_, card) in old_cards.items():
            try:
                if card and hasattr(card, 'deleteLater'):
                    card.deleteLater()
            except:
                pass

        # Get filtered scripts
        filtered_scripts = self._get_filtered_scripts()

        # Add cards for each script
        for script in filtered_scripts:
            try:
                self._add_script_card(script)
            except Exception as e:
                print("Warning adding script card: {}".format(e))

        self._update_results_count(len(filtered_scripts))

        # Auto-select first item
        if filtered_scripts and self.script_cards:
            try:
                first_name = list(self.script_cards.keys())[0]
                first_item, first_card = self.script_cards[first_name]
                self.script_list.setCurrentItem(first_item)
                self._on_card_clicked(first_card)
            except:
                pass

    def _add_script_card(self, script_metadata):
        """Add a script card to the list"""
        card = ScriptCard(script_metadata)
        card.clicked.connect(self._on_card_clicked)
        card.doubleClicked.connect(self._on_card_double_clicked)

        item = QtWidgets.QListWidgetItem()
        item.setSizeHint(QtCore.QSize(0, card.height()))

        self.script_list.addItem(item)
        self.script_list.setItemWidget(item, card)
        self.script_cards[script_metadata['name']] = (item, card)

    def _get_filtered_scripts(self):
        """Get filtered scripts based on current criteria"""
        return ScriptFilter.filter_scripts(
            self.scripts,
            self.search_bar.text(),
            self.category_combo.currentText(),
            self.user_combo.currentText(),
            self.favorites_btn.isChecked(),
            SETTINGS.get('search_in_content', False)
        )

    def _apply_filters(self):
        """Apply filters and refresh display"""
        if self.current_selection:
            self._selected_script_name = self.current_selection.metadata['name']
        self._populate_script_list()
        self._restore_selection()

    def _restore_selection(self):
        """Restore previous selection after refresh"""
        if not self._selected_script_name:
            return
        for name, (item, card) in self.script_cards.items():
            if name == self._selected_script_name:
                self._on_card_clicked(card)
                self.script_list.scrollToItem(item)
                self.script_list.setCurrentItem(item)
                break

    def _on_card_clicked(self, card):
        """Handle card selection"""
        if not card or not hasattr(card, 'metadata'):
            return

        try:
            # Deselect previous
            if self.current_selection and hasattr(self.current_selection, 'set_selected'):
                try:
                    self.current_selection.set_selected(False)
                except:
                    pass

            # Select new
            card.set_selected(True)
            self.current_selection = card

            # Sync with list widget
            for name, (item, script_card) in self.script_cards.items():
                if script_card == card:
                    try:
                        self.script_list.setCurrentItem(item)
                    except:
                        pass
                    break

            # Update preview
            self._update_preview(card.metadata)
        except Exception as e:
            print("Warning in _on_card_clicked: {}".format(e))

    def _on_card_double_clicked(self, card):
        """Handle card double click - run script"""
        self._run_script_by_metadata(card.metadata)

    def _update_preview(self, metadata):
        """Update preview panel with script info"""
        self.preview_title.setText("📄 {}".format(metadata['name']))

        # Build info text
        info_parts = []
        if metadata['description']:
            info_parts.append("<b>Description:</b> {}".format(metadata['description']))
        if metadata.get('user'):
            info_parts.append("<b>User:</b> {}".format(metadata['user']))
        info_parts.extend([
            "<b>Category:</b> {}".format(metadata['category']),
            "<b>Modified:</b> {}".format(metadata['modified'].strftime('%Y-%m-%d %H:%M')),
            "<b>Size:</b> {:.1f} KB".format(metadata['size'] / 1024)
        ])
        if metadata['tags']:
            info_parts.append("<b>Tags:</b> {}".format(', '.join(metadata['tags'])))

        self.info_label.setText('<br>'.join(info_parts))
        self.info_widget.setVisible(True)

        # Update code preview
        self.code_preview.setPlainText(metadata['content'])

        # Update recent scripts
        self._update_recent_scripts(metadata['name'])

    def _update_recent_scripts(self, script_name):
        """Add script to recent list"""
        recent = SETTINGS.get('recent_scripts', [])
        if script_name in recent:
            recent.remove(script_name)
        recent.insert(0, script_name)
        recent = recent[:SETTINGS.get('max_recent', 10)]
        SETTINGS.set('recent_scripts', recent)

    def _update_results_count(self, count):
        """Update results count display"""
        total = len(self.scripts)
        self.results_label.setText("{}/{}".format(count, total) if count != total else str(total))

    def _run_script_by_metadata(self, metadata):
        """Execute a script"""
        try:
            exec(metadata['content'], {'__name__': '__main__'})
            self._show_notification("✓ '{}' executed successfully".format(metadata['name']), "success")
            self._update_recent_scripts(metadata['name'])
        except Exception as e:
            self._show_notification("✗ Error executing '{}': {}".format(metadata['name'], str(e)), "error")
            print("Script execution failed: {}".format(traceback.format_exc()))

    def _show_notification(self, message, msg_type="info"):
        """Show notification in Maya viewport"""
        colors = {
            'success': THEME_COLORS['success'],
            'error': THEME_COLORS['error'],
            'info': THEME_COLORS['accent']
        }
        try:
            cmds.inViewMessage(
                amg="<span style='color:{}'>{}</span>".format(colors.get(msg_type, colors['info']), message),
                pos='topCenter', fade=True
            )
        except:
            print(message)

    def _show_message(self, message):
        """Show message in console"""
        print("Maya Script Browser: {}".format(message))

    def _on_search_changed(self):
        """Handle search text change with debouncing"""
        if hasattr(self, '_search_timer'):
            self._search_timer.stop()
        else:
            self._search_timer = QTimer()
            self._search_timer.timeout.connect(self._apply_filters)
            self._search_timer.setSingleShot(True)
        self._search_timer.start(300)

    def _on_search_enter(self):
        """Handle Enter key in search - run first/selected script"""
        if self.current_selection:
            self._run_script_by_metadata(self.current_selection.metadata)
        elif self.script_cards:
            first_name = list(self.script_cards.keys())[0]
            _, first_card = self.script_cards[first_name]
            self._run_script_by_metadata(first_card.metadata)

    def _on_sort_changed(self, order):
        """Handle sort order change"""
        SETTINGS.set('sort_order', order.lower())
        self._sort_scripts()
        self._populate_script_list()

    def _on_list_selection_changed(self, current, previous):
        """Handle list selection change"""
        if current:
            for name, (item, card) in self.script_cards.items():
                if item == current:
                    if not self.current_selection or self.current_selection.metadata['name'] != name:
                        self._on_card_clicked(card)
                    break

    def keyPressEvent(self, event):
        """Handle keyboard navigation"""
        if self.search_bar.hasFocus():
            super(MayaScriptBrowser, self).keyPressEvent(event)
            return

        if event.key() == QtCore.Qt.Key_Up:
            self._navigate_list(-1)
        elif event.key() == QtCore.Qt.Key_Down:
            self._navigate_list(1)
        elif event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            if self.current_selection:
                self._run_script_by_metadata(self.current_selection.metadata)
        elif event.key() == QtCore.Qt.Key_Delete:
            if self.current_selection:
                self._delete_script()
        elif event.key() == QtCore.Qt.Key_F and event.modifiers() == QtCore.Qt.ControlModifier:
            self.search_bar.setFocus()
            self.search_bar.selectAll()
        else:
            super(MayaScriptBrowser, self).keyPressEvent(event)

    def _navigate_list(self, direction):
        """Navigate through list with keyboard"""
        if not self.script_cards:
            return

        names = list(self.script_cards.keys())
        current_index = -1

        if self.current_selection:
            try:
                current_index = names.index(self.current_selection.metadata['name'])
            except:
                current_index = -1

        new_index = (current_index + direction) % len(names)
        name = names[new_index]
        item, card = self.script_cards[name]

        self.script_list.setCurrentItem(item)
        self._on_card_clicked(card)
        self.script_list.scrollToItem(item)

    def _show_context_menu(self, position):
        """Show right-click context menu"""
        if not self.script_list.itemAt(position) or not self.current_selection:
            return

        menu = QtWidgets.QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #3a3a3a; color: #EEE; border: 1px solid #555; }
            QMenu::item { padding: 8px 16px; }
            QMenu::item:selected { background: #5a9fd4; }
        """)

        actions = [
            ("▶ Run Script", self._run_script),
            (None, None),
            ("✎ Edit Metadata", self._edit_script),
            ("↗ Open in Charcoal", self._open_external),
            (None, None),
            ("✕ Delete Script", self._delete_script)
        ]

        for text, slot in actions:
            if text:
                menu.addAction(text).triggered.connect(slot)
            else:
                menu.addSeparator()

        menu.exec_(self.script_list.mapToGlobal(position))

    def _run_script(self):
        """Run selected script"""
        if self.current_selection:
            self._run_script_by_metadata(self.current_selection.metadata)

    def _edit_script(self):
        """Edit script metadata"""
        if not self.current_selection:
            return
        dialog = ScriptEditDialog(self.current_selection.metadata, self)
        if dialog.exec_():
            self._load_scripts()

    def _open_external(self):
        """Open script in external editor"""
        if not self.current_selection:
            return
        file_path = self.current_selection.metadata['path']
        try:
            file_path = file_path.replace('\\', '/')
            mel.eval(f'charcoalEditor2 -of "{file_path}";')
        except Exception as e:
            self._show_notification("✗ Failed to open: {}".format(e), "error")

    def _delete_script(self):
        """Delete selected script with confirmation"""
        if not self.current_selection:
            return

        name = self.current_selection.metadata['name']
        path = self.current_selection.metadata['path']

        reply = QtWidgets.QMessageBox.question(
            self, "Delete Script",
            "Delete '{}'?\n\nThis cannot be undone.".format(name),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes:
            try:
                os.remove(path)
                # Remove from favorites if present
                favorites = SETTINGS.get('favorites', [])
                if name in favorites:
                    favorites.remove(name)
                    SETTINGS.set('favorites', favorites)
                # Clear cache
                SETTINGS.set_cache(path, None)
                SETTINGS.save_cache()
                self.current_selection = None
                self._load_scripts()
                self._show_notification("✓ Script deleted", "success")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", "Failed to delete: {}".format(e))

    def _new_script(self):
        """Create new script"""
        dialog = NewScriptDialog(self)
        if dialog.exec_():
            self._load_scripts()

    def _show_settings(self):
        """Show settings dialog"""
        dialog = SettingsDialog(self)
        if dialog.exec_():
            self._apply_theme()
            self._load_scripts()

    def _setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        shortcuts = [
            ("Ctrl+R", self._run_script),
            ("Ctrl+N", self._new_script),
            ("Ctrl+F", lambda: self.search_bar.setFocus()),
            ("Ctrl+,", self._show_settings)
        ]

        for key, slot in shortcuts:
            try:
                shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(key), self)
            except:
                shortcut = QtGui.QShortcut(QtGui.QKeySequence(key), self)

            shortcut.activated.connect(slot)

    def _apply_theme(self):
        """Apply application theme"""
        self.setStyleSheet(ThemeManager.get_main_style())

    def closeEvent(self, event):
        """Handle window close - save settings"""
        try:
            # Save window geometry
            SETTINGS.set('window_geometry', self.saveGeometry().toBase64().data())
            SETTINGS.save_settings()
            SETTINGS.save_cache()
        except:
            pass
        event.accept()

    def run_docked(self):
        """Show as docked window in Maya"""
        self.setObjectName(self.WINDOW_NAME)

        # Clean up existing workspace control
        try:
            if cmds.workspaceControl(self.WORKSPACE_CONTROL_NAME, query=True, exists=True):
                cmds.workspaceControl(self.WORKSPACE_CONTROL_NAME, edit=True, close=True)
                cmds.deleteUI(self.WORKSPACE_CONTROL_NAME, control=True)
        except:
            pass

        # Show dockable
        self.show(dockable=True, area='right', floating=False)

        # Try to dock next to Attribute Editor
        try:
            cmds.workspaceControl(self.WORKSPACE_CONTROL_NAME,
                                  edit=True,
                                  tabToControl=["AttributeEditor", -1],
                                  widthProperty="preferred",
                                  minimumWidth=400)
        except:
            pass

        self.setDockableParameters(width=450, height=700)
        self.raise_()
        return self


# =============================================================================
# DIALOG CLASSES
# =============================================================================

class ScriptEditDialog(QtWidgets.QDialog):
    """Dialog for editing script metadata"""

    def __init__(self, metadata, parent=None):
        super(ScriptEditDialog, self).__init__(parent)
        self.metadata = metadata
        self.setWindowTitle("Edit Script: {}".format(metadata['name']))
        self.setFixedSize(450, 400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QtWidgets.QFormLayout(self)
        layout.setSpacing(15)

        self.description_edit = QtWidgets.QLineEdit(self.metadata.get('description', ''))
        self.user_edit = QtWidgets.QLineEdit(self.metadata.get('user', ''))

        self.category_combo = QtWidgets.QComboBox()
        self.category_combo.addItems(SETTINGS.get('categories', []))
        self.category_combo.setCurrentText(self.metadata.get('category', 'Uncategorized'))

        self.tags_edit = QtWidgets.QLineEdit(', '.join(self.metadata.get('tags', [])))

        layout.addRow("Description:", self.description_edit)
        layout.addRow("User:", self.user_edit)
        layout.addRow("Category:", self.category_combo)
        layout.addRow("Tags:", self.tags_edit)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self._save_changes)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _save_changes(self):
        """Save metadata changes to script file"""
        try:
            file_path = self.metadata['path']
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Find where content starts
            content_start = 0
            for i, line in enumerate(lines):
                if line.strip() and not line.startswith('#'):
                    content_start = i
                    break

            # Build new headers
            headers = []
            if self.description_edit.text():
                headers.append("# description: {}\n".format(self.description_edit.text()))
            if self.user_edit.text():
                headers.append("# user: {}\n".format(self.user_edit.text()))
            headers.append("# category: {}\n".format(self.category_combo.currentText()))
            if self.tags_edit.text():
                headers.append("# tags: {}\n".format(self.tags_edit.text()))
            headers.append("\n")

            # Write updated file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(headers + lines[content_start:])

            # Clear cache
            SETTINGS.set_cache(file_path, None)
            SETTINGS.save_cache()
            self.accept()

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", "Failed to save: {}".format(e))


class NewScriptDialog(QtWidgets.QDialog):
    """Dialog for creating new scripts"""

    def __init__(self, parent=None):
        super(NewScriptDialog, self).__init__(parent)
        self.setWindowTitle("Create New Script")
        self.resize(600, 500)
        self._setup_ui()

    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        form = QtWidgets.QFormLayout()
        self.name_edit = QtWidgets.QLineEdit()
        self.description_edit = QtWidgets.QLineEdit()
        self.user_edit = QtWidgets.QLineEdit(getpass.getuser())

        self.category_combo = QtWidgets.QComboBox()
        self.category_combo.addItems(SETTINGS.get('categories', []))

        self.tags_edit = QtWidgets.QLineEdit()

        form.addRow("Name:", self.name_edit)
        form.addRow("Description:", self.description_edit)
        form.addRow("User:", self.user_edit)
        form.addRow("Category:", self.category_combo)
        form.addRow("Tags:", self.tags_edit)

        layout.addLayout(form)

        # Template code
        self.code_edit = QtWidgets.QPlainTextEdit()
        self.code_edit.setPlainText("""import maya.cmds as cmds

def main():
    \"\"\"Main function - Add your code here\"\"\"
    print("Hello from Maya Script Browser!")

    # Your code here
    pass

if __name__ == "__main__":
    main()
""")
        layout.addWidget(QtWidgets.QLabel("Code:"))
        layout.addWidget(self.code_edit)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self._create_script)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _create_script(self):
        """Create the script file"""
        name = self.name_edit.text().strip()
        if not name:
            QtWidgets.QMessageBox.warning(self, "Error", "Please enter a script name.")
            return

        if name.endswith('.py'):
            name = name[:-3]

        file_path = os.path.join(SETTINGS.browser_folder, "{}.py".format(name))
        if os.path.exists(file_path):
            reply = QtWidgets.QMessageBox.question(
                self, "File Exists", "Overwrite '{}.py'?".format(name),
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            if reply != QtWidgets.QMessageBox.Yes:
                return

        try:
            # Build file content
            headers = []
            if self.description_edit.text():
                headers.append("# description: {}\n".format(self.description_edit.text()))
            if self.user_edit.text():
                headers.append("# user: {}\n".format(self.user_edit.text()))
            headers.append("# category: {}\n".format(self.category_combo.currentText()))
            if self.tags_edit.text():
                headers.append("# tags: {}\n".format(self.tags_edit.text()))
            headers.append("\n")

            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(headers)
                f.write(self.code_edit.toPlainText())

            self.accept()

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", "Failed to create: {}".format(e))


class SettingsDialog(QtWidgets.QDialog):
    """Comprehensive settings dialog"""

    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)
        self.setWindowTitle("Maya Script Browser Settings")
        self.setFixedSize(700, 600)
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        """Setup settings UI with tabs"""
        layout = QtWidgets.QVBoxLayout(self)

        tabs = QtWidgets.QTabWidget()
        layout.addWidget(tabs)

        # Create tabs
        tabs.addTab(self._create_general_tab(), "General")
        tabs.addTab(self._create_categories_tab(), "Categories")
        tabs.addTab(self._create_appearance_tab(), "Appearance")
        tabs.addTab(self._create_users_tab(), "Users")

        # Buttons
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self._save_settings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _create_general_tab(self):
        """Create general settings tab"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        # Script folder
        folder_group = QtWidgets.QGroupBox("Script Folder")
        folder_layout = QtWidgets.QHBoxLayout(folder_group)
        self.folder_label = QtWidgets.QLabel()
        folder_layout.addWidget(self.folder_label)
        browse_btn = QtWidgets.QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_folder)
        folder_layout.addWidget(browse_btn)
        layout.addWidget(folder_group)

        # Options
        self.auto_save_cb = QtWidgets.QCheckBox("Auto-save settings")
        self.include_subfolders_cb = QtWidgets.QCheckBox("Include subfolders when scanning")
        self.search_content_cb = QtWidgets.QCheckBox("Search in script content (slower)")
        self.show_user_colors_cb = QtWidgets.QCheckBox("Show user colors in cards")

        layout.addWidget(self.auto_save_cb)
        layout.addWidget(self.include_subfolders_cb)
        layout.addWidget(self.search_content_cb)
        layout.addWidget(self.show_user_colors_cb)
        layout.addStretch()

        return tab

    def _create_categories_tab(self):
        """Create categories management tab"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(tab)

        # List
        self.cat_list = QtWidgets.QListWidget()
        layout.addWidget(self.cat_list)

        # Buttons
        btn_layout = QtWidgets.QVBoxLayout()
        for text, slot in [
            ("Add", self._add_category),
            ("Rename", self._rename_category),
            ("Remove", self._remove_category),
            ("Move Up", self._move_up),
            ("Move Down", self._move_down)
        ]:
            btn = QtWidgets.QPushButton(text)
            btn.clicked.connect(slot)
            btn_layout.addWidget(btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return tab

    def _create_appearance_tab(self):
        """Create appearance customization tab"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        # Instructions
        info = QtWidgets.QLabel(
            "Customize icons and colors for each category.\n"
            "Click icon buttons to change icons, color buttons to change colors."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        # Custom icon input
        custom_group = QtWidgets.QGroupBox("Custom Icon")
        custom_layout = QtWidgets.QHBoxLayout(custom_group)

        custom_layout.addWidget(QtWidgets.QLabel("Enter custom icon:"))
        self.custom_icon_input = QtWidgets.QLineEdit()
        self.custom_icon_input.setMaxLength(4)
        self.custom_icon_input.setPlaceholderText("🎯")
        custom_layout.addWidget(self.custom_icon_input)

        self.add_custom_icon_btn = QtWidgets.QPushButton("Add to Selected Category")
        self.add_custom_icon_btn.clicked.connect(self._add_custom_icon)
        custom_layout.addWidget(self.add_custom_icon_btn)

        layout.addWidget(custom_group)

        # Category appearance list
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QtWidgets.QWidget()
        scroll_layout = QtWidgets.QVBoxLayout(scroll_widget)

        self.appearance_widgets = {}
        self.selected_category = None

        categories = SETTINGS.get('categories', [])
        colors = SETTINGS.get('category_colors', {})
        icons = SETTINGS.get('category_icons', {})

        for cat in categories:
            frame = QtWidgets.QFrame()
            frame.setStyleSheet("QFrame { background: #3a3a3a; border-radius: 4px; padding: 10px; }")
            frame_layout = QtWidgets.QHBoxLayout(frame)

            # Category name (clickable)
            cat_btn = QtWidgets.QPushButton(cat)
            cat_btn.setCheckable(True)
            cat_btn.clicked.connect(partial(self._select_category, cat))
            frame_layout.addWidget(cat_btn)
            self.appearance_widgets[cat + '_btn'] = cat_btn

            # Icon selector
            icon_btn = QtWidgets.QPushButton(icons.get(cat, '📄'))
            icon_btn.setFixedSize(40, 30)
            icon_btn.clicked.connect(partial(self._choose_icon, cat))
            self.appearance_widgets[cat + '_icon'] = icon_btn
            frame_layout.addWidget(icon_btn)

            # Color selector
            color = colors.get(cat, '#7f8c8d')
            color_btn = QtWidgets.QPushButton()
            color_btn.setFixedSize(60, 30)
            color_btn.setStyleSheet("background: {}; border: 2px solid #555;".format(color))
            color_btn.clicked.connect(partial(self._choose_color, cat))
            self.appearance_widgets[cat + '_color'] = color_btn
            frame_layout.addWidget(color_btn)

            frame_layout.addWidget(QtWidgets.QLabel(color))
            frame_layout.addStretch()

            scroll_layout.addWidget(frame)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        return tab

    def _create_users_tab(self):
        """Create user color customization tab"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        info = QtWidgets.QLabel(
            "Customize colors for each user. Colors are automatically assigned "
            "but you can override them here."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        # User colors list
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QtWidgets.QWidget()
        scroll_layout = QtWidgets.QVBoxLayout(scroll_widget)

        self.user_color_widgets = {}

        # Get all unique users
        users = set()
        for script in self.parent().scripts if hasattr(self.parent(), 'scripts') else []:
            if script.get('user'):
                users.add(script['user'])

        # Get saved user colors
        user_colors = SETTINGS.get('user_colors', {})

        for user in sorted(users):
            frame = QtWidgets.QFrame()
            frame.setStyleSheet("QFrame { background: #3a3a3a; border-radius: 4px; padding: 10px; }")
            frame_layout = QtWidgets.QHBoxLayout(frame)

            # User name
            frame_layout.addWidget(QtWidgets.QLabel(user))

            # Color selector
            color = user_colors.get(user, generate_user_color(user))
            color_btn = QtWidgets.QPushButton()
            color_btn.setFixedSize(60, 30)
            color_btn.setStyleSheet("background: {}; border: 2px solid #555;".format(color))
            color_btn.clicked.connect(partial(self._choose_user_color, user))
            self.user_color_widgets[user] = color_btn
            frame_layout.addWidget(color_btn)

            frame_layout.addWidget(QtWidgets.QLabel(color))
            frame_layout.addStretch()

            # Reset button
            reset_btn = QtWidgets.QPushButton("Reset")
            reset_btn.clicked.connect(partial(self._reset_user_color, user))
            frame_layout.addWidget(reset_btn)

            scroll_layout.addWidget(frame)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        return tab

    def _select_category(self, category):
        """Select a category for custom icon"""
        # Uncheck all other category buttons
        for cat in SETTINGS.get('categories', []):
            btn_key = cat + '_btn'
            if btn_key in self.appearance_widgets and cat != category:
                self.appearance_widgets[btn_key].setChecked(False)

        self.selected_category = category

    def _add_custom_icon(self):
        """Add custom icon to selected category"""
        if not self.selected_category:
            QtWidgets.QMessageBox.warning(
                self, "Warning", "Please select a category first by clicking on its name."
            )
            return

        icon_text = self.custom_icon_input.text().strip()
        if not icon_text:
            QtWidgets.QMessageBox.warning(
                self, "Warning", "Please enter an icon."
            )
            return

        # Validate it's an emoji/icon
        if not is_single_emoji(icon_text):
            QtWidgets.QMessageBox.warning(
                self, "Warning",
                "Please enter a single emoji icon.\n"
                "Examples: 🎯 🚀 💡 🔥 ⭐"
            )
            return

        # Update icon
        icons = SETTINGS.get('category_icons', {})
        icons[self.selected_category] = icon_text
        SETTINGS.set('category_icons', icons)

        # Update UI
        icon_btn_key = self.selected_category + '_icon'
        if icon_btn_key in self.appearance_widgets:
            self.appearance_widgets[icon_btn_key].setText(icon_text)

        # Clear input
        self.custom_icon_input.clear()

        QtWidgets.QMessageBox.information(
            self, "Success",
            "Icon updated for '{}'!".format(self.selected_category)
        )

    def _load_settings(self):
        """Load current settings into UI"""
        self.folder_label.setText(SETTINGS.get('browser_folder', ''))
        self.auto_save_cb.setChecked(SETTINGS.get('auto_save', True))
        self.include_subfolders_cb.setChecked(SETTINGS.get('include_subfolders', True))
        self.search_content_cb.setChecked(SETTINGS.get('search_in_content', False))
        self.show_user_colors_cb.setChecked(SETTINGS.get('show_user_colors', True))
        self._load_categories()

    def _load_categories(self):
        """Load categories into list"""
        self.cat_list.clear()
        self.cat_list.addItems(SETTINGS.get('categories', []))

    def _browse_folder(self):
        """Browse for script folder"""
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select Folder", self.folder_label.text()
        )
        if folder:
            self.folder_label.setText(folder)

    def _add_category(self):
        """Add new category"""
        text, ok = QtWidgets.QInputDialog.getText(
            self, "Add Category", "Category name:"
        )
        if ok and text:
            categories = SETTINGS.get('categories', [])
            if text not in categories:
                categories.append(text)
                SETTINGS.set('categories', categories)
                self._load_categories()

    def _rename_category(self):
        """Rename selected category"""
        item = self.cat_list.currentItem()
        if item and item.text() != "Uncategorized":
            text, ok = QtWidgets.QInputDialog.getText(
                self, "Rename", "New name:", text=item.text()
            )
            if ok and text:
                categories = SETTINGS.get('categories', [])
                idx = categories.index(item.text())
                categories[idx] = text
                SETTINGS.set('categories', categories)
                self._load_categories()

    def _remove_category(self):
        """Remove selected category"""
        item = self.cat_list.currentItem()
        if item and item.text() != "Uncategorized":
            categories = SETTINGS.get('categories', [])
            categories.remove(item.text())
            SETTINGS.set('categories', categories)
            self._load_categories()

    def _move_up(self):
        """Move category up in list"""
        row = self.cat_list.currentRow()
        if row > 0:
            categories = SETTINGS.get('categories', [])
            categories[row], categories[row - 1] = categories[row - 1], categories[row]
            SETTINGS.set('categories', categories)
            self._load_categories()
            self.cat_list.setCurrentRow(row - 1)

    def _move_down(self):
        """Move category down in list"""
        row = self.cat_list.currentRow()
        categories = SETTINGS.get('categories', [])
        if 0 <= row < len(categories) - 1:
            categories[row], categories[row + 1] = categories[row + 1], categories[row]
            SETTINGS.set('categories', categories)
            self._load_categories()
            self.cat_list.setCurrentRow(row + 1)

    def _choose_icon(self, category):
        """Choose icon for category"""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Choose Icon for {}".format(category))
        dialog.setFixedSize(400, 300)

        layout = QtWidgets.QVBoxLayout(dialog)

        # Icon grid
        grid = QtWidgets.QGridLayout()
        for i, icon in enumerate(AVAILABLE_ICONS):
            btn = QtWidgets.QPushButton(icon)
            btn.setFixedSize(40, 40)
            btn.clicked.connect(partial(self._set_icon, category, icon, dialog))
            grid.addWidget(btn, i // 8, i % 8)

        layout.addLayout(grid)
        dialog.exec_()

    def _set_icon(self, category, icon, dialog):
        """Set icon for category"""
        icons = SETTINGS.get('category_icons', {})
        icons[category] = icon
        SETTINGS.set('category_icons', icons)

        if category + '_icon' in self.appearance_widgets:
            self.appearance_widgets[category + '_icon'].setText(icon)

        dialog.accept()

    def _choose_color(self, category):
        """Choose color for category"""
        current_colors = SETTINGS.get('category_colors', {})
        current = current_colors.get(category, '#7f8c8d')

        color = QtWidgets.QColorDialog.getColor(
            QtGui.QColor(current), self, "Choose color"
        )
        if color.isValid():
            hex_color = color.name()
            current_colors[category] = hex_color
            SETTINGS.set('category_colors', current_colors)

            if category + '_color' in self.appearance_widgets:
                self.appearance_widgets[category + '_color'].setStyleSheet(
                    "background: {}; border: 2px solid #555;".format(hex_color)
                )

    def _choose_user_color(self, user):
        """Choose color for user"""
        user_colors = SETTINGS.get('user_colors', {})
        current = user_colors.get(user, generate_user_color(user))

        color = QtWidgets.QColorDialog.getColor(
            QtGui.QColor(current), self, "Choose color for {}".format(user)
        )
        if color.isValid():
            hex_color = color.name()
            user_colors[user] = hex_color
            SETTINGS.set('user_colors', user_colors)

            if user in self.user_color_widgets:
                self.user_color_widgets[user].setStyleSheet(
                    "background: {}; border: 2px solid #555;".format(hex_color)
                )

    def _reset_user_color(self, user):
        """Reset user color to auto-generated"""
        user_colors = SETTINGS.get('user_colors', {})
        if user in user_colors:
            del user_colors[user]
            SETTINGS.set('user_colors', user_colors)

        # Update UI
        default_color = generate_user_color(user)
        if user in self.user_color_widgets:
            self.user_color_widgets[user].setStyleSheet(
                "background: {}; border: 2px solid #555;".format(default_color)
            )

    def _save_settings(self):
        """Save all settings"""
        SETTINGS.set('browser_folder', self.folder_label.text())
        SETTINGS.set('auto_save', self.auto_save_cb.isChecked())
        SETTINGS.set('include_subfolders', self.include_subfolders_cb.isChecked())
        SETTINGS.set('search_in_content', self.search_content_cb.isChecked())
        SETTINGS.set('show_user_colors', self.show_user_colors_cb.isChecked())
        SETTINGS.save_settings()
        self.accept()


# =============================================================================
# MAIN FUNCTIONS
# =============================================================================
_maya_script_browser_instance = None
def show_maya_script_browser(dockable=False):
    """
    Show Maya Script Browser

    Args:
        dockable (bool): Whether to show as dockable window

    Returns:
        MayaScriptBrowser: The browser instance
    """
    global _maya_script_browser_instance

    try:
        # Clean up existing instance
        if _maya_script_browser_instance:
            try:
                _maya_script_browser_instance.close()
                _maya_script_browser_instance.deleteLater()
            except:
                pass
            _maya_script_browser_instance = None

        # Create new instance
        _maya_script_browser_instance = MayaScriptBrowser()

        if dockable:
            _maya_script_browser_instance.run_docked()
        else:
            _maya_script_browser_instance.show()

        return _maya_script_browser_instance

    except Exception as e:
        cmds.error("Failed to show Maya Script Browser: {}".format(e))
        return None


### USAGE

# from pxo_rigging_kit.maya_utils import script_browser
# import importlib
# importlib.reload(script_browser)
# script_browser.show_maya_script_browser(True)