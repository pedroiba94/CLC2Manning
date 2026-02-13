# -*- coding: utf-8 -*-
import os
from pathlib import Path

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QFileDialog
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtGui import QDesktopServices, QIcon

from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsWkbTypes,
    QgsProviderRegistry,
)

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "Mod1_dialog_base.ui")
)

CNIG_URL = "https://centrodedescargas.cnig.es/CentroDescargas/corine-land-cover"


class Mod1Dialog(QDialog, FORM_CLASS):
    """
    Paso 1: Seleccionar CORINE (GPKG) y opcionalmente cargarlo al proyecto
    Paso 2: Usar selección nativa de QGIS (flecha) para capturar AOI (polígono)
    """

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setupUi(self)

        # Icono del diálogo (mismo icon.png)
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
            self.setWindowIcon(QIcon(icon_path))
        except Exception:
            pass

        # Estado
        self.corine_gpkg_path = None
        self.corine_layer = None
        self.aoi_geom = None

        # AOI selector state (2 pasos)
        self._aoi_select_armed = False

        # Paso 1
        self.rbTengoCorine.toggled.connect(self._update_ui_state)
        self.rbNoTengoCorine.toggled.connect(self._update_ui_state)
        self.btnAbrirCNIG.clicked.connect(self._open_cnig)
        self.btnSeleccionarArchivo.clicked.connect(self._select_gpkg)

        # Paso 2
        self.btnPickAoi.clicked.connect(self._on_btn_pick_aoi)
        self.btnLimpiarAoi.clicked.connect(self._clear_aoi)

        # OK/Cancel
        self.buttonBox.accepted.connect(self._on_accept)
        self.buttonBox.rejected.connect(self.reject)

        # init
        self._update_ui_state()
        self._set_status_corine(False, "Pendiente")
        self._set_status_aoi(False, "Pendiente")

    def _update_ui_state(self):
        self.btnAbrirCNIG.setEnabled(self.rbNoTengoCorine.isChecked())

    def _open_cnig(self):
        QDesktopServices.openUrl(QUrl(CNIG_URL))

    def _set_status_corine(self, ok: bool, msg: str):
        self.lblEstado.setText(f"Status: {msg}")
        self.lblEstado.setStyleSheet("color: green;" if ok else "color: red;")

    def _set_status_aoi(self, ok: bool, msg: str):
        self.lblAoiEstado.setText(f"AOI: {msg}")
        self.lblAoiEstado.setStyleSheet("color: green;" if ok else "color: red;")

    def _clear_aoi(self):
        self.aoi_geom = None
        self._aoi_select_armed = False
        self._set_status_aoi(False, "Pendiente")

    # -------------------------
    # Paso 1: seleccionar GPKG
    # -------------------------
    def _select_gpkg(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select CORINE 2018 (GPKG)",
            "",
            "GeoPackage (*.gpkg)"
        )
        if not path:
            return

        self.txtRutaCorine.setText(path)

        try:
            gpkg_path = str(Path(path))
            if not Path(gpkg_path).exists():
                raise Exception("GPKG not found.")

            lyr = self._find_corine_layer_in_gpkg(gpkg_path)
            if lyr is None or not lyr.isValid():
                raise Exception("No polygon layer with CODE_18 found inside the selected GPKG.")

            self.corine_gpkg_path = gpkg_path

            if hasattr(self, "chkCargarCorine") and self.chkCargarCorine.isChecked():
                existing = self._find_existing_layer_by_source(gpkg_path, lyr.name())
                if existing is None:
                    QgsProject.instance().addMapLayer(lyr)
                    self.corine_layer = lyr
                else:
                    self.corine_layer = existing
            else:
                self.corine_layer = lyr

            self._set_status_corine(True, "CORINE OK (GPKG válido)")
            self._clear_aoi()

        except Exception as e:
            self.corine_gpkg_path = None
            self.corine_layer = None
            self._set_status_corine(False, str(e))

    def _find_existing_layer_by_source(self, gpkg_path: str, layername: str):
        for lyr in QgsProject.instance().mapLayers().values():
            if not isinstance(lyr, QgsVectorLayer) or not lyr.isValid():
                continue
            src = lyr.source()
            if gpkg_path in src and (f"layername={layername}" in src or lyr.name() == layername):
                return lyr
        return None

    def _find_corine_layer_in_gpkg(self, gpkg_path: str) -> QgsVectorLayer:
        md = QgsProviderRegistry.instance().providerMetadata("ogr")
        conn = md.createConnection(gpkg_path, {})
        tables = conn.tables()
        if not tables:
            return None

        for t in tables:
            layer_name = t.tableName() if hasattr(t, "tableName") else t.name()
            uri = f"{gpkg_path}|layername={layer_name}"
            vlayer = QgsVectorLayer(uri, layer_name, "ogr")
            if not vlayer.isValid():
                continue
            if vlayer.geometryType() != QgsWkbTypes.PolygonGeometry:
                continue
            if "CODE_18" in [f.name() for f in vlayer.fields()]:
                return vlayer

        return None

    # -------------------------
    # Paso 2: Selección nativa de QGIS (flecha)
    # -------------------------
    def _on_btn_pick_aoi(self):
        if not self.corine_gpkg_path:
            self._set_status_aoi(False, "Seleccione CORINE primero (Paso 1).")
            return

        if not self._aoi_select_armed:
            self._aoi_select_armed = True
            try:
                self.iface.actionSelect().trigger()
            except Exception:
                pass
            self._set_status_aoi(False, "Seleccione UN polígono con la flecha de QGIS, luego haga clic en este botón nuevamente.")
            return

        self._capture_selected_polygon_as_aoi()
        self._aoi_select_armed = False

    def _capture_selected_polygon_as_aoi(self):
        try:
            layers = self.iface.mapCanvas().layers()
            for lyr in layers:
                if not isinstance(lyr, QgsVectorLayer) or not lyr.isValid():
                    continue
                if lyr.geometryType() != QgsWkbTypes.PolygonGeometry:
                    continue
                if lyr.selectedFeatureCount() < 1:
                    continue

                feats = lyr.selectedFeatures()
                if not feats:
                    continue

                geom = feats[0].geometry()
                if geom is None or geom.isEmpty():
                    continue

                self.aoi_geom = geom
                self._set_status_aoi(True, f"OK (selected from: {lyr.name()})")
                return

            self.aoi_geom = None
            self._set_status_aoi(False, "No se encontraron polígonos seleccionados. Seleccione un polígono y vuelva a intentarlo.")

        except Exception as e:
            self.aoi_geom = None
            self._set_status_aoi(False, str(e))

    # -------------------------
    # OK
    # -------------------------
    def _on_accept(self):
        if not self.corine_gpkg_path or not Path(self.corine_gpkg_path).exists():
            self._set_status_corine(False, "Selecciona un archivo.gpkg de CORINE válido primero.")
            return

        if self.aoi_geom is None or self.aoi_geom.isEmpty():
            self._set_status_aoi(False, "Select an AOI first (Step 2).")
            return

        self.accept()

    # -------------------------
    # Heredar estilo
    # -------------------------
    def apply_corine_style_to(self, target_layer: QgsVectorLayer):
        try:
            if not hasattr(self, "chkHeredarEstilo"):
                return
            if not self.chkHeredarEstilo.isChecked():
                return
            if self.corine_layer is None or not self.corine_layer.isValid():
                return
            if target_layer is None or not target_layer.isValid():
                return

            target_layer.setRenderer(self.corine_layer.renderer().clone())
            target_layer.triggerRepaint()
        except Exception:
            pass

