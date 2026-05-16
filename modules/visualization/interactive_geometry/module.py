"""Interactive Geometry Explorer — v1.0.0

Visualises five 3D surface / parametric shapes interactively:
  - Sine Wave 2D   — Z = sin(√(X²+Y²)) / √(X²+Y²)   (cardinal sine surface)
  - Paraboloid     — Z = X² + Y²
  - Saddle         — Z = X² − Y²
  - Sphere         — parametric (θ, φ)
  - Torus          — parametric (θ, φ), R=3, r=1

Controls available via the side panel:
  - Shape selector (radio buttons)
  - Elevation and Azimuth angle inputs
  - Resolution selector (low / medium / high)
  - Colour map selector
  - Export PNG button

All heavy geometry computation is pure numpy — no Qt dependency.
Qt and Matplotlib imports are guarded so the module can be imported
in headless test environments without PySide6.
"""
from __future__ import annotations

import io
from typing import Any

import numpy as np

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QButtonGroup,
        QComboBox,
        QDoubleSpinBox,
        QFrame,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QRadioButton,
        QSizePolicy,
        QSpinBox,
        QVBoxLayout,
        QWidget,
    )

    _QT = True
except ImportError:  # pragma: no cover
    _QT = False

try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure

    _MPL = True
except ImportError:  # pragma: no cover
    _MPL = False

from core.module_runtime.base_module import BaseModule
from core.module_runtime.module_context import ModuleContext

_CanvasBase: type = QWidget if _QT else object  # type: ignore[misc]
_ModuleWidgetBase: type = QWidget if _QT else object  # type: ignore[misc]

# ---------------------------------------------------------------------------
# Geometry core — pure numpy, no Qt dependency
# ---------------------------------------------------------------------------

SHAPES = ("sine_2d", "paraboloid", "saddle", "sphere", "torus")
RESOLUTION = {"low": 30, "medium": 60, "high": 100}
COLORMAPS = ("viridis", "plasma", "inferno", "coolwarm", "RdBu", "Spectral", "copper")


def compute_surface(shape: str, n: int = 60) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (X, Y, Z) ndarrays for a 3-D surface or parametric shape.

    Parameters
    ----------
    shape:
        One of ``"sine_2d"``, ``"paraboloid"``, ``"saddle"``, ``"sphere"``,
        ``"torus"``.
    n:
        Grid resolution (n × n).

    Returns
    -------
    X, Y, Z — each shape ``(n, n)`` for surface plots or ``(n,)`` for
    parametric wire-frames.  Caller is responsible for choosing the right
    ``plot_surface`` / ``plot_wireframe`` axes method.
    """
    if shape == "sine_2d":
        return _surface_sinc(n)
    if shape == "paraboloid":
        return _surface_paraboloid(n)
    if shape == "saddle":
        return _surface_saddle(n)
    if shape == "sphere":
        return _surface_sphere(n)
    if shape == "torus":
        return _surface_torus(n)
    raise ValueError(f"Unknown shape: {shape!r}")


def _surface_sinc(n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    lin = np.linspace(-6.0, 6.0, n)
    X, Y = np.meshgrid(lin, lin)
    R = np.sqrt(X**2 + Y**2)
    with np.errstate(invalid="ignore", divide="ignore"):
        Z = np.where(R == 0, 1.0, np.sin(R) / R)
    return X, Y, Z


def _surface_paraboloid(n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    lin = np.linspace(-3.0, 3.0, n)
    X, Y = np.meshgrid(lin, lin)
    Z = X**2 + Y**2
    return X, Y, Z


def _surface_saddle(n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    lin = np.linspace(-3.0, 3.0, n)
    X, Y = np.meshgrid(lin, lin)
    Z = X**2 - Y**2
    return X, Y, Z


def _surface_sphere(n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    theta = np.linspace(0, np.pi, n)
    phi = np.linspace(0, 2 * np.pi, n)
    THETA, PHI = np.meshgrid(theta, phi)
    X = np.sin(THETA) * np.cos(PHI)
    Y = np.sin(THETA) * np.sin(PHI)
    Z = np.cos(THETA)
    return X, Y, Z


def _surface_torus(n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    R, r = 3.0, 1.0
    theta = np.linspace(0, 2 * np.pi, n)
    phi = np.linspace(0, 2 * np.pi, n)
    THETA, PHI = np.meshgrid(theta, phi)
    X = (R + r * np.cos(PHI)) * np.cos(THETA)
    Y = (R + r * np.cos(PHI)) * np.sin(THETA)
    Z = r * np.sin(PHI)
    return X, Y, Z


def surface_stats(X: np.ndarray, Y: np.ndarray, Z: np.ndarray) -> dict[str, float]:
    """Return descriptive statistics for a computed surface Z array."""
    return {
        "z_min": float(np.min(Z)),
        "z_max": float(np.max(Z)),
        "z_mean": float(np.mean(Z)),
        "z_std": float(np.std(Z)),
        "x_range": float(np.ptp(X)),
        "y_range": float(np.ptp(Y)),
    }


# ---------------------------------------------------------------------------
# Qt Canvas (only instantiated when _QT and _MPL are True)
# ---------------------------------------------------------------------------


class _GeometryCanvas(_CanvasBase):  # type: ignore[valid-type,misc]
    """Matplotlib 3D canvas embedded in a QWidget."""

    def __init__(self, parent: Any = None) -> None:  # pragma: no cover
        if not (_QT and _MPL):
            return
        super().__init__(parent)
        self.figure = Figure(figsize=(6, 5), tight_layout=True)
        self._canvas = FigureCanvas(self.figure)
        self._canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas)
        self.ax = self.figure.add_subplot(111, projection="3d")

    def render(
        self,
        shape: str,
        n: int,
        colormap: str,
        elev: float,
        azim: float,
    ) -> None:  # pragma: no cover
        self.ax.cla()
        X, Y, Z = compute_surface(shape, n)
        self.ax.plot_surface(X, Y, Z, cmap=colormap, linewidth=0, antialiased=True, alpha=0.9)
        self.ax.view_init(elev=elev, azim=azim)
        self.ax.set_xlabel("X")
        self.ax.set_ylabel("Y")
        self.ax.set_zlabel("Z")  # type: ignore[attr-defined]
        title = shape.replace("_", " ").title()
        self.ax.set_title(title, fontsize=11, pad=10)
        self._canvas.draw()

    def to_png_bytes(self) -> bytes:  # pragma: no cover
        buf = io.BytesIO()
        self.figure.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        buf.seek(0)
        return buf.read()


# ---------------------------------------------------------------------------
# Main module widget
# ---------------------------------------------------------------------------


class _InteractiveGeometryWidget(_ModuleWidgetBase):  # type: ignore[valid-type,misc]
    """Host widget — side-panel controls + 3D canvas."""

    def __init__(self, context: Any, manifest: dict) -> None:  # pragma: no cover
        if not _QT:
            return
        super().__init__()
        self._ctx = context
        self._manifest = manifest
        defaults = manifest.get("default_settings", {})
        self._shape: str = defaults.get("default_shape", "sine_2d")
        self._colormap: str = defaults.get("default_colormap", "viridis")
        self._elev: float = float(defaults.get("default_elevation", 30))
        self._azim: float = float(defaults.get("default_azimuth", -60))
        self._resolution: str = "medium"
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:  # pragma: no cover
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(8)

        # ── Left: 3D canvas ────────────────────────────────────────────────
        self._canvas = _GeometryCanvas()
        root_layout.addWidget(self._canvas, stretch=1)

        # ── Right: Controls panel ──────────────────────────────────────────
        panel = QFrame()
        panel.setFixedWidth(220)
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(8, 8, 8, 8)
        panel_layout.setSpacing(10)

        # Shape group
        shape_group = QGroupBox("Hình dạng")
        shape_v = QVBoxLayout(shape_group)
        self._shape_btn_group = QButtonGroup(self)
        _shape_labels = {
            "sine_2d": "Sine 2D (Sinc)",
            "paraboloid": "Paraboloid",
            "saddle": "Yên ngựa (Saddle)",
            "sphere": "Hình cầu",
            "torus": "Hình xuyến (Torus)",
        }
        for s, label in _shape_labels.items():
            rb = QRadioButton(label)
            rb.setObjectName(f"rb_{s}")
            rb.setChecked(s == self._shape)
            rb.toggled.connect(lambda checked, _s=s: self._on_shape(checked, _s))
            self._shape_btn_group.addButton(rb)
            shape_v.addWidget(rb)
        panel_layout.addWidget(shape_group)

        # View angles
        angles_group = QGroupBox("Góc nhìn")
        angles_v = QVBoxLayout(angles_group)
        angles_v.addWidget(QLabel("Elevation (°):"))
        self._elev_spin = QDoubleSpinBox()
        self._elev_spin.setRange(-90.0, 90.0)
        self._elev_spin.setValue(self._elev)
        self._elev_spin.setSingleStep(5.0)
        self._elev_spin.valueChanged.connect(self._on_elev)
        angles_v.addWidget(self._elev_spin)
        angles_v.addWidget(QLabel("Azimuth (°):"))
        self._azim_spin = QDoubleSpinBox()
        self._azim_spin.setRange(-180.0, 180.0)
        self._azim_spin.setValue(self._azim)
        self._azim_spin.setSingleStep(10.0)
        self._azim_spin.valueChanged.connect(self._on_azim)
        angles_v.addWidget(self._azim_spin)
        panel_layout.addWidget(angles_group)

        # Resolution
        res_group = QGroupBox("Độ phân giải")
        res_v = QVBoxLayout(res_group)
        self._res_combo = QComboBox()
        for r in ("low", "medium", "high"):
            self._res_combo.addItem(r.capitalize(), r)
        self._res_combo.setCurrentIndex(1)
        self._res_combo.currentIndexChanged.connect(self._on_resolution)
        res_v.addWidget(self._res_combo)
        panel_layout.addWidget(res_group)

        # Colormap
        cmap_group = QGroupBox("Bảng màu")
        cmap_v = QVBoxLayout(cmap_group)
        self._cmap_combo = QComboBox()
        for c in COLORMAPS:
            self._cmap_combo.addItem(c)
        idx = COLORMAPS.index(self._colormap) if self._colormap in COLORMAPS else 0
        self._cmap_combo.setCurrentIndex(idx)
        self._cmap_combo.currentIndexChanged.connect(self._on_cmap)
        cmap_v.addWidget(self._cmap_combo)
        panel_layout.addWidget(cmap_group)

        # Stats label
        self._stats_label = QLabel("")
        self._stats_label.setWordWrap(True)
        self._stats_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        panel_layout.addWidget(self._stats_label)

        panel_layout.addStretch()

        # Export button
        self._export_btn = QPushButton("Xuất ảnh PNG")
        self._export_btn.clicked.connect(self._on_export)
        panel_layout.addWidget(self._export_btn)

        root_layout.addWidget(panel)

    # ── Slots ──────────────────────────────────────────────────────────────

    def _on_shape(self, checked: bool, shape: str) -> None:  # pragma: no cover
        if checked:
            self._shape = shape
            self._refresh()

    def _on_elev(self, value: float) -> None:  # pragma: no cover
        self._elev = value
        self._refresh()

    def _on_azim(self, value: float) -> None:  # pragma: no cover
        self._azim = value
        self._refresh()

    def _on_resolution(self) -> None:  # pragma: no cover
        self._resolution = self._res_combo.currentData()
        self._refresh()

    def _on_cmap(self) -> None:  # pragma: no cover
        self._colormap = self._cmap_combo.currentText()
        self._refresh()

    def _refresh(self) -> None:  # pragma: no cover
        n = RESOLUTION[self._resolution]
        self._canvas.render(self._shape, n, self._colormap, self._elev, self._azim)
        X, Y, Z = compute_surface(self._shape, n)
        stats = surface_stats(X, Y, Z)
        self._stats_label.setText(
            f"Z min: {stats['z_min']:.4f}\n"
            f"Z max: {stats['z_max']:.4f}\n"
            f"Z mean: {stats['z_mean']:.4f}\n"
            f"Z std: {stats['z_std']:.4f}"
        )

    def _on_export(self) -> None:  # pragma: no cover
        png_bytes = self._canvas.to_png_bytes()
        self._ctx.export_service.export_bytes(
            data=png_bytes,
            filename=f"geometry_{self._shape}.png",
            mime_type="image/png",
        )
        self._ctx.activity_service.log(
            event_type="MODULE_EXPORT",
            detail=f"Exported geometry shape: {self._shape}",
        )

    def get_state(self) -> dict[str, Any]:  # pragma: no cover
        return {
            "shape": self._shape,
            "colormap": self._colormap,
            "elevation": self._elev,
            "azimuth": self._azim,
            "resolution": self._resolution,
        }

    def restore_state(self, state: dict[str, Any]) -> None:  # pragma: no cover
        self._shape = state.get("shape", self._shape)
        self._colormap = state.get("colormap", self._colormap)
        self._elev = float(state.get("elevation", self._elev))
        self._azim = float(state.get("azimuth", self._azim))
        self._resolution = state.get("resolution", self._resolution)
        # Sync widgets to restored values
        self._elev_spin.setValue(self._elev)
        self._azim_spin.setValue(self._azim)
        idx_res = list(RESOLUTION.keys()).index(self._resolution)
        self._res_combo.setCurrentIndex(idx_res)
        idx_cmap = COLORMAPS.index(self._colormap) if self._colormap in COLORMAPS else 0
        self._cmap_combo.setCurrentIndex(idx_cmap)
        for btn in self._shape_btn_group.buttons():
            if btn.objectName() == f"rb_{self._shape}":
                btn.setChecked(True)
        self._refresh()


# ---------------------------------------------------------------------------
# Module entry — BaseModule subclass
# ---------------------------------------------------------------------------


class InteractiveGeometryModule(BaseModule):
    """IIMP module: Interactive Geometry Explorer.

    Demonstrates matplotlib 3D surface visualisation inside the IIMP shell.
    All geometry computation is dependency-free (pure numpy); Qt is only
    required when ``build_view()`` is called by the host.
    """

    def on_load(self) -> None:
        self.context.logger.info("[InteractiveGeometry] on_load")

    def on_activate(self) -> None:
        self.context.logger.info("[InteractiveGeometry] on_activate")

    def on_deactivate(self) -> None:
        self.context.logger.info("[InteractiveGeometry] on_deactivate")

    def on_unload(self) -> None:
        self.context.logger.info("[InteractiveGeometry] on_unload")

    def build_view(self) -> Any:  # returns QWidget at runtime
        """Construct and return the module's root Qt widget."""
        return _InteractiveGeometryWidget(context=self.context, manifest=self.manifest)

    def get_state(self) -> dict[str, Any]:
        if hasattr(self, "_widget") and self._widget is not None:
            return self._widget.get_state()
        return {}

    def restore_state(self, state: dict[str, Any]) -> None:
        if hasattr(self, "_widget") and self._widget is not None:
            self._widget.restore_state(state)

    # Convenience metadata properties
    @property
    def module_id(self) -> str:
        return self.manifest["id"]

    @property
    def module_name(self) -> str:
        return self.manifest["name"]

    @property
    def module_version(self) -> str:
        return self.manifest["version"]
