# -*- coding: windows-1252 -*-
"""
blazing_skin_compact.py - Complete SkinCluster I/O Tool with UI
============================================================
Fast, stable skinCluster weight export/import with comprehensive UI and batch operations.
"""

import os
import sys
import struct
import time
import numpy as np
from contextlib import contextmanager

# Maya imports
import maya.cmds as cmds
import maya.api.OpenMaya as om2
import maya.api.OpenMayaAnim as oma2
import pymel.core as pm

# Qt imports with fallback
try:
    from PySide6.QtWidgets import *
    from PySide6.QtCore import *
    from PySide6.QtGui import *
except ImportError:
    from PySide2.QtWidgets import *
    from PySide2.QtCore import *
    from PySide2.QtGui import *

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

# Constants
FLAG_FP32 = 1 << 0
FLAG_MESHNAME = 1 << 1
DEFAULT_CHUNK_SIZE = 200000


@contextmanager
def _timer(label, store, verbose):
    if not verbose:
        yield
        return
    t0 = time.perf_counter()
    yield
    store[label] = time.perf_counter() - t0
    om2.MGlobal.displayInfo(f"  {label:<12} {store[label]:.4f}s")


@contextmanager
def _disable_undo():
    state = cmds.undoInfo(q=True, state=True)
    cmds.undoInfo(state=False)
    try:
        yield
    finally:
        cmds.undoInfo(state=state)


@contextmanager
def _suspend_scene():
    """Suspend Maya evaluation and viewport refresh"""
    try:
        ui_state = cmds.refresh(q=True, suspend=True)
    except:
        ui_state = False

    try:
        eval_mode = cmds.evaluationManager(q=True, mode=True)[0]
    except:
        eval_mode = None

    cmds.refresh(suspend=True)
    try:
        cmds.evaluationManager(mode='serial')
    except:
        pass

    try:
        yield
    finally:
        if eval_mode:
            try:
                cmds.evaluationManager(mode=eval_mode)
            except:
                pass
        cmds.refresh(suspend=ui_state)


class SkinIO:
    """Fast skinCluster weight export/import with caching, auto-binding and batch operations"""

    def __init__(self, mesh=None):
        self.mesh = mesh
        self._skin_fn = None
        self._dag_path = None
        self._influences = None
        self._component = None
        self._vertex_count = None

    def _get_dag_path(self):
        if not self._dag_path:
            if not self.mesh:
                raise RuntimeError("Mesh name not set")
            sel = om2.MSelectionList()
            sel.add(self.mesh)
            self._dag_path = sel.getDagPath(0)
        return self._dag_path

    def _get_component_info(self):
        if not self._component:
            dag = self._get_dag_path()

            if dag.hasFn(om2.MFn.kMesh):
                vtx_count, comp_type = om2.MFnMesh(dag).numVertices, om2.MFn.kMeshVertComponent
            elif dag.hasFn(om2.MFn.kNurbsCurve):
                vtx_count, comp_type = om2.MFnNurbsCurve(dag).numCVs, om2.MFn.kCurveCVComponent
            else:
                raise RuntimeError(f"Object {self.mesh} is neither mesh nor curve")

            fn = om2.MFnSingleIndexedComponent()
            self._component = fn.create(comp_type)
            fn.addElements(range(vtx_count))
            self._vertex_count = vtx_count
        return self._component, self._vertex_count

    def _create_skin_api(self, influence_names, verbose=False):
        """Create skinCluster using API"""
        if verbose:
            om2.MGlobal.displayInfo(f"Creating skinCluster with {len(influence_names)} influences...")

        skin_cluster = cmds.skinCluster(influence_names, self.mesh, tsb=True, mi=4, dr=4.0,
                                        name=f'{self.mesh}_skinCluster')[0]
        self._skin_fn = None
        self._influences = None
        return self._get_skin_fn()

    def _find_skin_cluster(self, influence_names=None, verbose=False):
        """Find existing skinCluster or create one"""
        if self._skin_fn:
            try:
                skin_name = self._skin_fn.name()
                if cmds.objExists(skin_name) and cmds.nodeType(skin_name) == 'skinCluster':
                    return skin_name
            except:
                if verbose:
                    om2.MGlobal.displayWarning("Cached skinCluster no longer valid, clearing cache")
                self.clear_cache()

        existing = next((n for n in cmds.listHistory(self.mesh, pdo=True) or []
                         if cmds.nodeType(n) == 'skinCluster'), None)
        if existing:
            self._skin_fn = None
            return existing

        if influence_names:
            if verbose:
                om2.MGlobal.displayInfo(f"No skinCluster found on {self.mesh}. Creating one...")
            with _timer('createSkinAPI', {}, verbose), _suspend_scene():
                self._create_skin_api(influence_names, verbose)
                return self._skin_fn.name()

        raise RuntimeError(f'No skinCluster on {self.mesh} and no influence names provided')

    def _get_skin_fn(self, influence_names=None, verbose=False):
        """Get cached skinCluster function set"""
        if not self._skin_fn:
            skin = self._find_skin_cluster(influence_names, verbose)
            try:
                skin_obj = om2.MSelectionList().add(skin).getDependNode(0)
                self._skin_fn = oma2.MFnSkinCluster(skin_obj)
                self._skin_fn.influenceObjects()  # Validate
            except Exception as e:
                if verbose:
                    om2.MGlobal.displayWarning(f"SkinCluster creation failed: {str(e)}")
                self.clear_cache()
                skin = self._find_skin_cluster(influence_names, verbose)
                skin_obj = om2.MSelectionList().add(skin).getDependNode(0)
                self._skin_fn = oma2.MFnSkinCluster(skin_obj)
        return self._skin_fn

    def _get_influences(self, force_refresh=False, verbose=False):
        if not self._influences or force_refresh:
            try:
                self._influences = self._get_skin_fn().influenceObjects()
            except RuntimeError as e:
                if verbose:
                    om2.MGlobal.displayWarning(f"Cache corrupted, retrying: {e}")
                self.clear_cache()
                self._influences = self._get_skin_fn().influenceObjects()
        return self._influences

    def export_weights(self, path, *, fp32=False, verbose=False) -> dict:
        """Export skinCluster weights to binary file"""
        t0 = time.perf_counter()
        flags = (FLAG_FP32 if fp32 else 0) | FLAG_MESHNAME
        T = {}

        with _timer('findSkin', T, verbose):
            fn = self._get_skin_fn(None, verbose)

        dag = self._get_dag_path()
        with _timer('buildComp', T, verbose):
            comp, vtx = self._get_component_info()

        with _timer('getInfluences', T, verbose):
            inf_objects = self._get_influences(verbose=verbose)
            n_inf = len(inf_objects)
            inf_names = [p.partialPathName() for p in inf_objects]

        with _timer('getWeights', T, verbose):
            w_arr, _ = fn.getWeights(dag, comp)

        with _timer('bufferPrep', T, verbose):
            np_buf = np.asarray(w_arr, dtype=np.float32 if fp32 else np.float64)

        with _timer('fileWrite', T, verbose):
            with open(path, 'wb') as f:
                f.write(struct.pack('IIB', n_inf, vtx, flags))

                if flags & FLAG_MESHNAME:
                    mesh_bytes = self.mesh.encode()
                    f.write(struct.pack('I', len(mesh_bytes)) + mesh_bytes)

                for name in inf_names:
                    name_bytes = name.encode()
                    f.write(struct.pack('I', len(name_bytes)) + name_bytes)

                np_buf.tofile(f)

        size_mb = np_buf.nbytes / 1048576
        om2.MGlobal.displayInfo(
            f"[Export] {n_inf} inf | {vtx} vtx -> {path} ({size_mb:.1f} MB) [{time.perf_counter() - t0:.2f}s]")
        return T

    def import_weights(self, path, *, chunk=None, verbose=False, clean_existing=True,
                       create_missing_joints=True) -> dict:
        """Import skinCluster weights from binary file"""
        t0 = time.perf_counter()
        T = {}
        chunk = chunk or DEFAULT_CHUNK_SIZE

        with _timer('fileRead', T, verbose):
            with open(path, 'rb') as f:
                n_inf, file_vtx, flags = struct.unpack('IIB', f.read(9))

                saved_mesh = None
                if flags & FLAG_MESHNAME:
                    mesh_len = struct.unpack('I', f.read(4))[0]
                    saved_mesh = f.read(mesh_len).decode()
                    if not self.mesh:
                        self.mesh = saved_mesh
                        if verbose:
                            om2.MGlobal.displayInfo(f"Using saved mesh name: {saved_mesh}")

                names = []
                for _ in range(n_inf):
                    name_len = struct.unpack('I', f.read(4))[0]
                    names.append(f.read(name_len).decode())

                if create_missing_joints:
                    for name in names:
                        if not cmds.objExists(name):
                            if verbose:
                                om2.MGlobal.displayInfo(f"Creating missing joint: {name}")
                            cmds.select(clear=True)
                            cmds.joint(name=name, position=(0, 0, 0))

            with open(path, 'rb') as f:
                f.seek(9)
                if flags & FLAG_MESHNAME:
                    mesh_len = struct.unpack('I', f.read(4))[0]
                    f.read(mesh_len)
                for _ in range(n_inf):
                    name_len = struct.unpack('I', f.read(4))[0]
                    f.read(name_len)

                dtype = np.float32 if (flags & FLAG_FP32) else np.float64
                buf = np.fromfile(f, dtype=dtype, count=n_inf * file_vtx)
                if dtype == np.float32:
                    buf = buf.astype(np.float64)

        if clean_existing:
            with _timer('cleanSkin', T, verbose):
                self._clean_existing_skinclusters(verbose)

        with _timer('findSkin', T, verbose):
            existing_skin = next((n for n in cmds.listHistory(self.mesh, pdo=True) or []
                                  if cmds.nodeType(n) == 'skinCluster'), None)

            if existing_skin:
                self._skin_fn = None
                fn = self._get_skin_fn(None, verbose)
            else:
                fn = self._create_skin_api(names, verbose)

        dag = self._get_dag_path()
        comp, vtx = self._get_component_info()

        if file_vtx != vtx:
            raise RuntimeError(f'Vertex-count mismatch: file {path} has {file_vtx}, mesh has {vtx}')

        curr = [p.partialPathName() for p in self._get_influences(force_refresh=True, verbose=verbose)]
        ids = om2.MIntArray([curr.index(n) for n in names])

        with _timer('setWeights', T, verbose):
            optimal_chunk = min(chunk, vtx)
            cmds.setAttr(f"{fn.name()}.normalizeWeights", 1)

            with _disable_undo(), _suspend_scene():
                if optimal_chunk < vtx:
                    dag = self._get_dag_path()
                    comp_type = om2.MFn.kMeshVertComponent if dag.hasFn(om2.MFn.kMesh) else om2.MFn.kCurveCVComponent

                    for start in range(0, vtx, optimal_chunk):
                        end = min(start + optimal_chunk, vtx)
                        weights = om2.MDoubleArray(buf[start * n_inf:end * n_inf].tolist())

                        sub = om2.MFnSingleIndexedComponent()
                        sub_comp = sub.create(comp_type)
                        sub.addElements(range(start, end))

                        fn.setWeights(dag, sub_comp, ids, weights, True)
                else:
                    fn.setWeights(dag, comp, ids, om2.MDoubleArray(buf.tolist()), True)

        om2.MGlobal.displayInfo(f"[Import] {n_inf} inf | {vtx} vtx -> {path} [{time.perf_counter() - t0:.2f}s]")
        return T

    def get_info(self) -> dict:
        """Get information about the current skinCluster"""
        try:
            fn, influences = self._get_skin_fn(), self._get_influences()
            _, vtx_count = self._get_component_info()
            return {
                'mesh': self.mesh, 'skinCluster': fn.name(),
                'influences': [inf.partialPathName() for inf in influences],
                'influenceCount': len(influences), 'vertexCount': vtx_count
            }
        except:
            return {'mesh': self.mesh, 'skinCluster': None, 'influences': [], 'influenceCount': 0, 'vertexCount': 0}

    def clear_cache(self) -> None:
        """Clear all cached data"""
        self._skin_fn = self._dag_path = self._influences = self._component = self._vertex_count = None

    def _clean_existing_skinclusters(self, verbose=False):
        """Remove all existing skinClusters from the mesh/curve"""
        existing = [n for n in cmds.listHistory(self.mesh, pdo=True) or [] if cmds.nodeType(n) == 'skinCluster']
        if existing:
            if verbose:
                om2.MGlobal.displayInfo(f"Removing {len(existing)} existing skinCluster(s)")
            [cmds.delete(skin) for skin in existing if cmds.objExists(skin)]
            self.clear_cache()

    @classmethod
    def _ensure_data_folder(cls):
        """Create blazingSkin folder in project data directory"""
        data_folder = os.path.join(cmds.workspace(q=True, rd=True), 'data', 'blazingSkin')
        if not os.path.exists(data_folder):
            os.makedirs(data_folder)
        return data_folder

    @classmethod
    def _get_all_skin_clusters(cls):
        """Get all skinClusters in scene organized by mesh/curve"""
        mesh_skin_map = {}
        for skin in cmds.ls(type='skinCluster') or []:
            for geo in cmds.skinCluster(skin, q=True, geometry=True) or []:
                transform = (cmds.listRelatives(geo, parent=True) or [geo])[0]
                mesh_skin_map.setdefault(transform, []).append(skin)
        return mesh_skin_map

    @classmethod
    def batch_export_all(cls, meshes=None, fp32=True, verbose=False, rename_skin_clusters=True) -> dict:
        """Export skin weights for multiple meshes/curves"""
        t0 = time.perf_counter()
        om2.MGlobal.displayInfo("=== BATCH EXPORT START ===")

        data_folder = cls._ensure_data_folder()
        mesh_skin_map = cls._get_all_skin_clusters()

        exported, skipped, failed = [], [], []

        for mesh, skins in mesh_skin_map.items():
            if meshes and mesh not in meshes:
                continue

            if len(skins) > 1:
                skipped.append((mesh, len(skins)))
                if verbose:
                    om2.MGlobal.displayWarning(f"Skipping {mesh}: has {len(skins)} skinClusters")
                continue

            try:
                skin_cluster = skins[0]
                safe_name = skin_cluster.replace(':', '_')
                file_path = os.path.join(data_folder, f"{safe_name}.bin")

                sio = cls(mesh)
                sio.export_weights(file_path, fp32=fp32, verbose=verbose)

                exported.append({'mesh': mesh, 'skinCluster': skin_cluster,
                                 'file': f"{safe_name}.bin", 'safe_name': safe_name})
            except Exception as e:
                failed.append({'mesh': mesh, 'skinCluster': skins[0] if skins else 'unknown', 'error': str(e)})
                om2.MGlobal.displayError(f"Failed to export {mesh}: {e}")

        om2.MGlobal.displayInfo(
            f"Exported: {len(exported)}, Skipped: {len(skipped)}, Failed: {len(failed)} [{time.perf_counter() - t0:.2f}s total]")
        return {'exported': exported, 'skipped': skipped, 'failed': failed}

    @classmethod
    def batch_export_selected(cls, **kwargs) -> dict:
        """Export weights for selected meshes/curves"""
        selection = cmds.ls(sl=True, transforms=True)
        return cls.batch_export_all(meshes=selection, **kwargs) if selection else \
            (om2.MGlobal.displayWarning("No meshes/curves selected") or {'exported': [], 'skipped': [], 'failed': []})

    @classmethod
    def batch_import_all(cls, files=None, chunk=None, verbose=False,
                         clean_existing=True, create_missing_joints=True) -> dict:
        """Import skin weights from multiple files"""
        t0 = time.perf_counter()
        om2.MGlobal.displayInfo("=== BATCH IMPORT START ===")

        data_folder = cls._ensure_data_folder()
        if files is None:
            files = [f for f in os.listdir(data_folder) if f.endswith('.bin')]

        imported, skipped, failed = [], [], []

        for file_name in files:
            file_path = os.path.join(data_folder, file_name)

            if not os.path.exists(file_path):
                if verbose:
                    om2.MGlobal.displayWarning(f"File not found: {file_path}")
                continue

            try:
                info = SkinFileInfo(file_path)
                if not info.mesh_name:
                    if verbose:
                        om2.MGlobal.displayWarning(f"No mesh name in file: {file_name}")
                    continue

                if not cmds.objExists(info.mesh_name):
                    skipped.append({'file': file_name, 'mesh': info.mesh_name, 'reason': 'Mesh not in scene'})
                    continue

                sio = cls(info.mesh_name)
                sio.import_weights(file_path, chunk=chunk, verbose=verbose,
                                   clean_existing=clean_existing, create_missing_joints=create_missing_joints)

                imported.append({'file': file_name, 'mesh': info.mesh_name,
                                 'skinCluster': sio._skin_fn.name() if sio._skin_fn else None})
            except Exception as e:
                failed.append({'file': file_name, 'error': str(e)})
                om2.MGlobal.displayError(f"Failed to import {file_name}: {e}")

        om2.MGlobal.displayInfo(
            f"Imported: {len(imported)}, Skipped: {len(skipped)}, Failed: {len(failed)} [{time.perf_counter() - t0:.2f}s total]")
        return {'imported': imported, 'skipped': skipped, 'failed': failed}

    @classmethod
    def batch_import_selected(cls, **kwargs) -> dict:
        """Import weights for selected meshes/curves if files exist"""
        selection = cmds.ls(sl=True, transforms=True)
        if not selection:
            om2.MGlobal.displayWarning("No meshes/curves selected")
            return {'imported': [], 'skipped': [], 'failed': []}

        data_folder, mesh_skin_map = cls._ensure_data_folder(), cls._get_all_skin_clusters()
        files_to_import = [f"{skin.replace(':', '_')}.bin" for mesh in selection
                           for skin in mesh_skin_map.get(mesh, [])
                           if os.path.exists(os.path.join(data_folder, f"{skin.replace(':', '_')}.bin"))]

        return cls.batch_import_all(files=files_to_import, **kwargs) if files_to_import else \
            (om2.MGlobal.displayWarning("No matching files found for selection") or {'imported': [], 'skipped': [],
                                                                                     'failed': []})

    @classmethod
    def list_saved_weights(cls) -> list:
        """List all saved weight files with info"""
        data_folder = cls._ensure_data_folder()
        files = [f for f in os.listdir(data_folder) if f.endswith('.bin')]

        file_info = []
        for file_name in files:
            try:
                info = SkinFileInfo(os.path.join(data_folder, file_name))
                file_info.append({
                    'file': file_name, 'mesh': info.mesh_name,
                    'vertices': info.vertex_count, 'influences': info.n_influences,
                    'size_mb': info.file_size_mb
                })
            except:
                file_info.append({'file': file_name, 'error': 'Could not read file'})

        return file_info


class SkinFileInfo:
    """Read skin file information without importing weights"""

    def __init__(self, path):
        self.path = path
        self._read_info()

    def _read_info(self):
        """Read file header and influence names"""
        with open(self.path, 'rb') as f:
            self.n_influences, self.vertex_count, flags = struct.unpack('IIB', f.read(9))

            self.is_fp32 = bool(flags & FLAG_FP32)
            self.is_compressed = False
            self.has_mesh_name = bool(flags & FLAG_MESHNAME)

            self.mesh_name = None
            if self.has_mesh_name:
                mesh_len = struct.unpack('I', f.read(4))[0]
                self.mesh_name = f.read(mesh_len).decode()

            self.influences = []
            for _ in range(self.n_influences):
                name_len = struct.unpack('I', f.read(4))[0]
                self.influences.append(f.read(name_len).decode())

            f.seek(0, 2)
            self.file_size = f.tell()
            self.file_size_mb = self.file_size / 1048576

    def get_info(self) -> dict:
        """Return dictionary with all file information"""
        return {
            'path': self.path, 'mesh_name': self.mesh_name,
            'vertex_count': self.vertex_count, 'influence_count': self.n_influences,
            'influences': self.influences, 'is_fp32': self.is_fp32,
            'is_compressed': self.is_compressed, 'file_size_mb': self.file_size_mb
        }

    def check_missing_influences(self) -> list:
        """Return list of influences that don't exist in scene"""
        return [inf for inf in self.influences if not cmds.objExists(inf)]


class SkinIOUI(MayaQWidgetDockableMixin, QMainWindow):
    WINDOW_TITLE = "Blazing Skin Compact"
    WINDOW_OBJECT = "BlazingSkinCompactWindow"

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.deleteControl(self.WINDOW_OBJECT + "WorkspaceControl")
        self.setObjectName(self.WINDOW_OBJECT)
        self.setWindowTitle(self.WINDOW_TITLE)
        self.setMinimumSize(450, 600)
        self.resize(450, 600)

        self._create_ui()
        self._apply_maya_styling()
        self._connect_signals()
        self._update_mesh_selection()

    @staticmethod
    def deleteControl(control):
        if cmds.workspaceControl(control, query=True, exists=True):
            cmds.deleteUI(control, control=True)

    def _create_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # Create tab widget with proper styling
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        self.tab_widget.setDocumentMode(False)
        self.tab_widget.setTabsClosable(False)
        self.tab_widget.setMovable(False)

        # Make tabs more prominent with Maya-compatible styling
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #666666;
                background-color: #393939;
            }
            QTabBar::tab {
                background: #4A4A4A;
                border: 1px solid #666666;
                color: #CCCCCC;
                padding: 8px 16px;
                margin-right: 1px;
                min-width: 60px;
            }
            QTabBar::tab:selected {
                background: #5A5A5A;
                border-bottom-color: #393939;
                color: #FFFFFF;
            }
            QTabBar::tab:hover {
                background: #555555;
                color: #FFFFFF;
            }
        """)

        main_layout.addWidget(self.tab_widget)

        # Create tabs
        self._create_export_tab()
        self._create_import_tab()
        self._create_advanced_tab()

        # Add status bar at bottom
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet(
            "QLabel { background-color: #2B2B2B; color: #CCCCCC; padding: 4px; border: 1px solid #555555; }")
        main_layout.addWidget(self.status_label)

        # Connect tab change signal
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

    def _apply_maya_styling(self):
        """Apply Maya-compatible dark theme styling"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #393939;
                color: #CCCCCC;
            }
            QWidget {
                background-color: #393939;
                color: #CCCCCC;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #555555;
                border-radius: 3px;
                margin-top: 8px;
                padding-top: 4px;
                color: #DDDDDD;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
            }
            QPushButton {
                background-color: #4A4A4A;
                border: 1px solid #666666;
                border-radius: 3px;
                padding: 6px 12px;
                color: #CCCCCC;
            }
            QPushButton:hover {
                background-color: #555555;
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: #333333;
            }
            QLineEdit {
                background-color: #2B2B2B;
                border: 1px solid #555555;
                border-radius: 2px;
                padding: 4px;
                color: #CCCCCC;
            }
            QTextEdit {
                background-color: #2B2B2B;
                border: 1px solid #555555;
                color: #CCCCCC;
            }
            QListWidget {
                background-color: #2B2B2B;
                border: 1px solid #555555;
                color: #CCCCCC;
            }
            QCheckBox {
                color: #CCCCCC;
            }
            QLabel {
                color: #CCCCCC;
            }
        """)

    def _create_export_tab(self):
        tab = QWidget()
        self.tab_widget.addTab(tab, "Export")
        layout = QVBoxLayout(tab)

        # Mesh selection
        mesh_group = QGroupBox("Mesh Selection")
        mesh_layout = QHBoxLayout(mesh_group)

        self.mesh_line = QLineEdit()
        self.mesh_line.setPlaceholderText("Select mesh or enter name")
        mesh_btn = QPushButton("Get Selected")
        mesh_btn.clicked.connect(self._get_selected_mesh)

        mesh_layout.addWidget(QLabel("Mesh:"))
        mesh_layout.addWidget(self.mesh_line)
        mesh_layout.addWidget(mesh_btn)
        layout.addWidget(mesh_group)

        # Export options
        options_group = QGroupBox("Export Options")
        options_layout = QVBoxLayout(options_group)

        # Single export options
        single_options = QHBoxLayout()
        self.fp32_check = QCheckBox("32-bit Precision")
        self.verbose_check = QCheckBox("Verbose")
        single_options.addWidget(self.fp32_check)
        single_options.addWidget(self.verbose_check)
        options_layout.addLayout(single_options)

        # Single export button
        self.export_btn = QPushButton("Export Current Mesh")
        self.export_btn.clicked.connect(self._export_weights)
        options_layout.addWidget(self.export_btn)

        layout.addWidget(options_group)

        # Batch export section
        batch_group = QGroupBox("Batch Export")
        batch_layout = QVBoxLayout(batch_group)

        # Batch export options
        batch_options = QHBoxLayout()
        self.batch_fp32_check = QCheckBox("32-bit Precision")
        self.batch_fp32_check.setChecked(True)
        self.batch_verbose_check = QCheckBox("Verbose")
        batch_options.addWidget(self.batch_fp32_check)
        batch_options.addWidget(self.batch_verbose_check)
        batch_layout.addLayout(batch_options)

        # Batch export buttons
        batch_buttons = QHBoxLayout()
        self.export_all_btn = QPushButton("Export All Meshes")
        self.export_selected_btn = QPushButton("Export Selected Meshes")

        self.export_all_btn.clicked.connect(self._export_all)
        self.export_selected_btn.clicked.connect(self._export_selected)

        batch_buttons.addWidget(self.export_all_btn)
        batch_buttons.addWidget(self.export_selected_btn)
        batch_layout.addLayout(batch_buttons)

        layout.addWidget(batch_group)

        # Mesh info display
        info_group = QGroupBox("Mesh Information")
        info_layout = QVBoxLayout(info_group)

        self.info_text = QTextEdit()
        self.info_text.setMaximumHeight(120)
        self.info_text.setReadOnly(True)
        info_layout.addWidget(self.info_text)

        refresh_info_btn = QPushButton("Refresh Info")
        refresh_info_btn.clicked.connect(self._refresh_mesh_info)
        info_layout.addWidget(refresh_info_btn)

        layout.addWidget(info_group)
        layout.addStretch()

    def _create_import_tab(self):
        tab = QWidget()
        self.tab_widget.addTab(tab, "Import")
        layout = QVBoxLayout(tab)

        # Mesh selection (shared with export)
        mesh_group = QGroupBox("Target Mesh")
        mesh_layout = QHBoxLayout(mesh_group)

        # Reference to the same mesh line from export tab
        mesh_layout.addWidget(QLabel("Mesh:"))
        self.import_mesh_label = QLabel("(Use mesh selection from Export tab)")
        self.import_mesh_label.setStyleSheet("color: gray; font-style: italic;")
        mesh_layout.addWidget(self.import_mesh_label)
        layout.addWidget(mesh_group)

        # Import options
        options_group = QGroupBox("Import Options")
        options_layout = QVBoxLayout(options_group)

        # Single import options
        self.clean_existing_check = QCheckBox("Clean Existing skinCluster")
        self.clean_existing_check.setChecked(True)
        self.create_joints_check = QCheckBox("Create Missing Joints")
        self.create_joints_check.setChecked(True)
        self.verbose_import_check = QCheckBox("Verbose")

        options_layout.addWidget(self.clean_existing_check)
        options_layout.addWidget(self.create_joints_check)
        options_layout.addWidget(self.verbose_import_check)

        # Single import button
        self.import_btn = QPushButton("Import Current Mesh")
        self.import_btn.clicked.connect(self._import_weights)
        options_layout.addWidget(self.import_btn)

        layout.addWidget(options_group)

        # Batch import section
        batch_import_group = QGroupBox("Batch Import")
        batch_import_layout = QVBoxLayout(batch_import_group)

        # Batch import options
        self.batch_clean_check = QCheckBox("Clean Existing skinClusters")
        self.batch_clean_check.setChecked(True)
        self.batch_create_joints_check = QCheckBox("Create Missing Joints")
        self.batch_create_joints_check.setChecked(True)
        self.batch_verbose_import_check = QCheckBox("Verbose")

        batch_import_layout.addWidget(self.batch_clean_check)
        batch_import_layout.addWidget(self.batch_create_joints_check)
        batch_import_layout.addWidget(self.batch_verbose_import_check)

        # Batch import buttons
        batch_import_buttons = QHBoxLayout()
        self.import_all_btn = QPushButton("Import All Files")
        self.import_selected_btn = QPushButton("Import Selected Meshes")

        self.import_all_btn.clicked.connect(self._import_all)
        self.import_selected_btn.clicked.connect(self._import_selected)

        batch_import_buttons.addWidget(self.import_all_btn)
        batch_import_buttons.addWidget(self.import_selected_btn)
        batch_import_layout.addLayout(batch_import_buttons)

        layout.addWidget(batch_import_group)
        layout.addStretch()

    def _create_advanced_tab(self):
        tab = QWidget()
        self.tab_widget.addTab(tab, "Advanced")
        layout = QVBoxLayout(tab)

        # File management section
        files_group = QGroupBox("Weight File Management")
        files_layout = QVBoxLayout(files_group)

        self.files_list = QListWidget()
        self.files_list.setMaximumHeight(200)
        files_layout.addWidget(self.files_list)

        files_buttons = QHBoxLayout()
        refresh_files_btn = QPushButton("Refresh Files")
        self.delete_file_btn = QPushButton("Delete Selected")
        self.delete_file_btn.setEnabled(False)

        refresh_files_btn.clicked.connect(self._refresh_file_list)
        self.delete_file_btn.clicked.connect(self._delete_selected_file)
        self.files_list.itemSelectionChanged.connect(self._on_file_selected)

        files_buttons.addWidget(refresh_files_btn)
        files_buttons.addWidget(self.delete_file_btn)
        files_buttons.addStretch()
        files_layout.addLayout(files_buttons)

        layout.addWidget(files_group)

        # Utilities section
        utilities_group = QGroupBox("Utilities")
        utilities_layout = QVBoxLayout(utilities_group)

        # Data folder info
        data_info = QHBoxLayout()
        data_info.addWidget(QLabel("Data folder:"))
        self.data_folder_btn = QPushButton("Open Data Folder")
        self.data_folder_btn.clicked.connect(self._open_data_folder)
        data_info.addWidget(self.data_folder_btn)
        data_info.addStretch()
        utilities_layout.addLayout(data_info)

        # Scene utilities
        scene_utils = QHBoxLayout()
        self.cleanup_scene_btn = QPushButton("List All SkinClusters")
        self.cleanup_scene_btn.clicked.connect(self._list_scene_skinclusters)
        scene_utils.addWidget(self.cleanup_scene_btn)
        scene_utils.addStretch()
        utilities_layout.addLayout(scene_utils)

        layout.addWidget(utilities_group)

        # Log/Results section
        log_group = QGroupBox("Operation Log")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)

        log_buttons = QHBoxLayout()
        clear_log_btn = QPushButton("Clear Log")
        clear_log_btn.clicked.connect(self.log_text.clear)
        log_buttons.addWidget(clear_log_btn)
        log_buttons.addStretch()
        log_layout.addLayout(log_buttons)

        layout.addWidget(log_group)
        layout.addStretch()

        # Initialize file list after UI is ready
        QTimer.singleShot(0, self._refresh_file_list)

    def _on_tab_changed(self, index):
        """Handle tab change events"""
        tab_names = ["Export", "Import", "Advanced"]
        if index < len(tab_names):
            self._show_message(f"Switched to {tab_names[index]} tab")

            # Update mesh info when switching to Export tab
            if index == 0 and hasattr(self, 'mesh_line'):  # Export tab
                self._refresh_mesh_info()

    def _connect_signals(self):
        try:
            if hasattr(cmds, 'scriptJob'):
                cmds.scriptJob(event=["SelectionChanged", self._update_mesh_selection],
                               parent=self.objectName(), killWithScene=False)
        except Exception as e:
            print(f"Warning: Could not create scriptJob: {e}")

    def _get_selected_mesh(self):
        selection = cmds.ls(selection=True, transforms=True)
        if selection:
            self.mesh_line.setText(selection[0])
            self._refresh_mesh_info()
        else:
            self._show_message("No mesh selected")

    def _update_mesh_selection(self):
        if hasattr(self, 'mesh_line'):
            selection = cmds.ls(selection=True, transforms=True)
            if selection and len(selection) == 1:
                self.mesh_line.setText(selection[0])

    def _get_skin_cluster(self, mesh):
        """Helper method to get skinCluster from mesh"""
        try:
            for node in cmds.listHistory(mesh, pdo=True) or []:
                if cmds.nodeType(node) == 'skinCluster':
                    return node
        except:
            pass
        return None

    def _export_weights(self):
        mesh = self.mesh_line.text().strip()

        if not mesh:
            self._show_message("Please select a mesh")
            return

        if not cmds.objExists(mesh):
            self._show_message(f"Mesh '{mesh}' does not exist")
            return

        try:
            skin_cluster = self._get_skin_cluster(mesh)

            if not skin_cluster:
                self._show_message(f"No skinCluster found on {mesh}")
                return

            safe_name = skin_cluster.replace(':', '_')

            data_folder = SkinIO._ensure_data_folder()
            file_path = os.path.join(data_folder, f"{safe_name}.bin")

            sio = SkinIO(mesh)
            result = sio.export_weights(
                file_path,
                fp32=self.fp32_check.isChecked(),
                verbose=self.verbose_check.isChecked()
            )

            self._show_message(f"Export successful: {safe_name}.bin")

        except Exception as e:
            self._show_message(f"Export failed: {str(e)}")

    def _import_weights(self):
        mesh = self.mesh_line.text().strip()

        if not mesh:
            self._show_message("Please select a mesh")
            return

        try:
            data_folder = SkinIO._ensure_data_folder()
            files = [f for f in os.listdir(data_folder) if f.endswith('.bin')]

            target_file = None
            mesh_clean = mesh.replace(':', '_')

            for file_name in files:
                base_name = file_name.replace('.bin', '')
                if mesh_clean in base_name or base_name in mesh_clean:
                    target_file = file_name
                    break

            if not target_file:
                if files:
                    file_list = ', '.join(files)
                    self._show_message(f"No matching file found. Available: {file_list}")
                else:
                    self._show_message("No weight files found in data folder")
                return

            file_path = os.path.join(data_folder, target_file)

            sio = SkinIO(mesh)
            result = sio.import_weights(
                file_path,
                verbose=self.verbose_import_check.isChecked(),
                clean_existing=self.clean_existing_check.isChecked(),
                create_missing_joints=self.create_joints_check.isChecked()
            )

            self._show_message(f"Import successful: {target_file}")

        except Exception as e:
            self._show_message(f"Import failed: {str(e)}")

    def _export_selected(self):
        try:
            result = SkinIO.batch_export_selected(
                fp32=self.batch_fp32_check.isChecked(),
                verbose=self.batch_verbose_check.isChecked()
            )
            exported_count = len(result.get('exported', []))
            self._show_message(f"Exported {exported_count} selected meshes")
            QTimer.singleShot(500, self._refresh_file_list)
        except Exception as e:
            self._show_message(f"Export selected failed: {str(e)}")

    def _export_all(self):
        try:
            result = SkinIO.batch_export_all(
                fp32=self.batch_fp32_check.isChecked(),
                verbose=self.batch_verbose_check.isChecked()
            )
            exported_count = len(result.get('exported', []))
            self._show_message(f"Exported {exported_count} meshes from scene")
            QTimer.singleShot(500, self._refresh_file_list)
        except Exception as e:
            self._show_message(f"Export all failed: {str(e)}")

    def _import_selected(self):
        try:
            result = SkinIO.batch_import_selected(
                verbose=self.batch_verbose_import_check.isChecked(),
                clean_existing=self.batch_clean_check.isChecked(),
                create_missing_joints=self.batch_create_joints_check.isChecked()
            )
            imported_count = len(result.get('imported', []))
            self._show_message(f"Imported {imported_count} selected meshes")
        except Exception as e:
            self._show_message(f"Import selected failed: {str(e)}")

    def _import_all(self):
        try:
            result = SkinIO.batch_import_all(
                verbose=self.batch_verbose_import_check.isChecked(),
                clean_existing=self.batch_clean_check.isChecked(),
                create_missing_joints=self.batch_create_joints_check.isChecked()
            )
            imported_count = len(result.get('imported', []))
            self._show_message(f"Imported {imported_count} files")
        except Exception as e:
            self._show_message(f"Import all failed: {str(e)}")

    def _refresh_file_list(self):
        self.files_list.clear()

        try:
            files = SkinIO.list_saved_weights()

            for file_info in files:
                if 'error' in file_info:
                    item_text = f"{file_info['file']} - ERROR"
                else:
                    item_text = f"{file_info['file']} - {file_info['mesh']} ({file_info['vertices']} verts, {file_info['influences']} infs, {file_info['size_mb']:.1f}MB)"

                self.files_list.addItem(item_text)

        except Exception as e:
            self._show_message(f"Error refreshing file list: {str(e)}")

    def _on_file_selected(self):
        selected = self.files_list.selectedItems()
        self.delete_file_btn.setEnabled(len(selected) > 0)

    def _delete_selected_file(self):
        selected = self.files_list.selectedItems()
        if not selected:
            return

        item_text = selected[0].text()
        filename = item_text.split(' - ')[0]

        reply = QMessageBox.question(
            self, "Delete File",
            f"Are you sure you want to delete '{filename}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                data_folder = SkinIO._ensure_data_folder()
                file_path = os.path.join(data_folder, filename)

                if os.path.exists(file_path):
                    os.remove(file_path)
                    self._refresh_file_list()
                    self._show_message(f"Deleted: {filename}")
                else:
                    self._show_message(f"File not found: {filename}")

            except Exception as e:
                self._show_message(f"Error deleting file: {str(e)}")

    def _open_data_folder(self):
        """Open the data folder in file explorer"""
        try:
            data_folder = SkinIO._ensure_data_folder()
            if os.path.exists(data_folder):
                import subprocess
                import platform

                if platform.system() == "Windows":
                    subprocess.Popen(f'explorer "{data_folder}"')
                elif platform.system() == "Darwin":  # macOS
                    subprocess.Popen(["open", data_folder])
                else:  # Linux
                    subprocess.Popen(["xdg-open", data_folder])

                self._show_message(f"Opened: {data_folder}")
            else:
                self._show_message("Data folder does not exist")
        except Exception as e:
            self._show_message(f"Error opening data folder: {str(e)}")

    def _list_scene_skinclusters(self):
        """List all skinClusters in the scene"""
        try:
            skin_clusters = cmds.ls(type='skinCluster') or []
            if not skin_clusters:
                self._log_message("No skinClusters found in scene")
                return

            self._log_message(f"Found {len(skin_clusters)} skinClusters:")
            for sc in skin_clusters:
                try:
                    geometry = cmds.skinCluster(sc, q=True, geometry=True)
                    geo_names = []
                    for geo in geometry or []:
                        transform = (cmds.listRelatives(geo, parent=True) or [geo])[0]
                        geo_names.append(transform)

                    influences = cmds.skinCluster(sc, q=True, influence=True) or []
                    self._log_message(f"  {sc}: {', '.join(geo_names)} ({len(influences)} influences)")
                except:
                    self._log_message(f"  {sc}: [Error getting info]")

        except Exception as e:
            self._show_message(f"Error listing skinClusters: {str(e)}")

    def _log_message(self, message):
        """Add message to the log in Advanced tab"""
        if hasattr(self, 'log_text'):
            self.log_text.append(message)
        print(f"BlazingSkin: {message}")

    def _refresh_mesh_info(self):
        mesh = self.mesh_line.text().strip()
        if not mesh:
            self.info_text.clear()
            return

        try:
            sio = SkinIO(mesh)
            info = sio.get_info()

            info_text = f"Mesh: {info['mesh']}\n"
            info_text += f"SkinCluster: {info['skinCluster']}\n"
            info_text += f"Vertex Count: {info['vertexCount']}\n"
            info_text += f"Influence Count: {info['influenceCount']}\n"
            info_text += f"Influences: {', '.join(info['influences'][:5])}"
            if len(info['influences']) > 5:
                info_text += f"... (+{len(info['influences']) - 5} more)"

            self.info_text.setText(info_text)

        except Exception as e:
            self.info_text.setText(f"Error getting mesh info: {str(e)}")

    def _show_message(self, message):
        if hasattr(self, 'status_label'):
            self.status_label.setText(message)
        print(f"BlazingSkin: {message}")


def show_blazing_skin_compact():
    """Show the compact SkinIO UI"""
    global blazing_skin_window

    try:
        blazing_skin_window.close()
        blazing_skin_window.deleteLater()
    except:
        pass

    blazing_skin_window = SkinIOUI()
    blazing_skin_window.show(dockable=True)

    return blazing_skin_window


# External API Functions for Scripting
def batch_export(meshes=None, selected_only=False, export_all=False, fp32=True, verbose=False,
                 rename_skin_clusters=True):
    """
    External batch export function for scripting use.

    Args:
        meshes (list): Specific mesh names to export. If None, uses other parameters.
        selected_only (bool): Export only selected meshes in scene.
        export_all (bool): Export all meshes with skinClusters in scene.
        fp32 (bool): Use 32-bit precision for smaller files.
        verbose (bool): Print detailed progress information.
        rename_skin_clusters (bool): Rename skinClusters to match geometry names.

    Returns:
        dict: Results with 'exported', 'skipped', and 'failed' lists.

    Examples:
        # Export specific meshes
        result = batch_export(meshes=['character_body', 'character_head'])

        # Export all selected meshes
        result = batch_export(selected_only=True, verbose=True)

        # Export all meshes in scene
        result = batch_export(export_all=True, fp32=False)
    """
    try:
        if meshes:
            # Export specific meshes
            return SkinIO.batch_export_all(
                meshes=meshes,
                fp32=fp32,
                verbose=verbose,
                rename_skin_clusters=rename_skin_clusters
            )
        elif selected_only:
            # Export selected meshes
            return SkinIO.batch_export_selected(
                fp32=fp32,
                verbose=verbose,
                rename_skin_clusters=rename_skin_clusters
            )
        elif export_all:
            # Export all meshes
            return SkinIO.batch_export_all(
                fp32=fp32,
                verbose=verbose,
                rename_skin_clusters=rename_skin_clusters
            )
        else:
            om2.MGlobal.displayWarning(
                "No export mode specified. Use meshes=[], selected_only=True, or export_all=True")
            return {'exported': [], 'skipped': [], 'failed': []}

    except Exception as e:
        om2.MGlobal.displayError(f"Batch export failed: {str(e)}")
        return {'exported': [], 'skipped': [], 'failed': [{'error': str(e)}]}


def batch_import(files=None, meshes=None, selected_only=False, import_all=False,
                 chunk=None, verbose=False, clean_existing=True, create_missing_joints=True):
    """
    External batch import function for scripting use.

    Args:
        files (list): Specific file names to import from data folder.
        meshes (list): Specific mesh names to find matching files for.
        selected_only (bool): Import files matching selected meshes in scene.
        import_all (bool): Import all available weight files.
        chunk (int): Chunk size for large imports (default: 200000).
        verbose (bool): Print detailed progress information.
        clean_existing (bool): Remove existing skinClusters before import.
        create_missing_joints (bool): Create joints that don't exist in scene.

    Returns:
        dict: Results with 'imported', 'skipped', and 'failed' lists.

    Examples:
        # Import specific files
        result = batch_import(files=['character_body_SKC.bin', 'character_head_SKC.bin'])

        # Import for specific meshes (auto-find matching files)
        result = batch_import(meshes=['character_body', 'character_head'], verbose=True)

        # Import for selected meshes
        result = batch_import(selected_only=True, clean_existing=False)

        # Import all available files
        result = batch_import(import_all=True, chunk=100000)
    """
    try:
        if files:
            # Import specific files
            return SkinIO.batch_import_all(
                files=files,
                chunk=chunk,
                verbose=verbose,
                clean_existing=clean_existing,
                create_missing_joints=create_missing_joints
            )
        elif meshes:
            # Import for specific meshes - find matching files
            data_folder = SkinIO._ensure_data_folder()
            mesh_skin_map = SkinIO._get_all_skin_clusters()

            files_to_import = []
            for mesh in meshes:
                # Try to find matching file for this mesh
                skins = mesh_skin_map.get(mesh, [])
                for skin in skins:
                    safe_name = skin.replace(':', '_')
                    file_path = os.path.join(data_folder, f"{safe_name}.bin")
                    if os.path.exists(file_path):
                        files_to_import.append(f"{safe_name}.bin")
                        break
                else:
                    # No skinCluster found, try mesh name directly
                    mesh_safe = mesh.replace(':', '_')
                    file_path = os.path.join(data_folder, f"{mesh_safe}.bin")
                    if os.path.exists(file_path):
                        files_to_import.append(f"{mesh_safe}.bin")

            if files_to_import:
                return SkinIO.batch_import_all(
                    files=files_to_import,
                    chunk=chunk,
                    verbose=verbose,
                    clean_existing=clean_existing,
                    create_missing_joints=create_missing_joints
                )
            else:
                om2.MGlobal.displayWarning(f"No matching files found for meshes: {meshes}")
                return {'imported': [], 'skipped': [], 'failed': []}

        elif selected_only:
            # Import for selected meshes
            return SkinIO.batch_import_selected(
                chunk=chunk,
                verbose=verbose,
                clean_existing=clean_existing,
                create_missing_joints=create_missing_joints
            )
        elif import_all:
            # Import all available files
            return SkinIO.batch_import_all(
                chunk=chunk,
                verbose=verbose,
                clean_existing=clean_existing,
                create_missing_joints=create_missing_joints
            )
        else:
            om2.MGlobal.displayWarning(
                "No import mode specified. Use files=[], meshes=[], selected_only=True, or import_all=True")
            return {'imported': [], 'skipped': [], 'failed': []}

    except Exception as e:
        om2.MGlobal.displayError(f"Batch import failed: {str(e)}")
        return {'imported': [], 'skipped': [], 'failed': [{'error': str(e)}]}


# Convenience wrapper functions
def export_selected(fp32=True, verbose=False):
    """Quick export of selected meshes"""
    return batch_export(selected_only=True, fp32=fp32, verbose=verbose)


def export_all(fp32=True, verbose=False):
    """Quick export of all meshes in scene"""
    return batch_export(export_all=True, fp32=fp32, verbose=verbose)


def import_selected(verbose=False, clean_existing=True):
    """Quick import for selected meshes"""
    return batch_import(selected_only=True, verbose=verbose, clean_existing=clean_existing)


def import_all(verbose=False, clean_existing=True):
    """Quick import of all available files"""
    return batch_import(import_all=True, verbose=verbose, clean_existing=clean_existing)


def export_mesh(mesh_name, fp32=True, verbose=False):
    """Export a single specific mesh"""
    return batch_export(meshes=[mesh_name], fp32=fp32, verbose=verbose)


def import_mesh(mesh_name, verbose=False, clean_existing=True):
    """Import weights for a single specific mesh"""
    return batch_import(meshes=[mesh_name], verbose=verbose, clean_existing=clean_existing)


def list_weight_files():
    """List all saved weight files with information"""
    return SkinIO.list_saved_weights()


def get_data_folder():
    """Get the path to the blazingSkin data folder"""
    return SkinIO._ensure_data_folder()


# For testing/shelf button
if __name__ == "__main__":
    show_blazing_skin_compact()