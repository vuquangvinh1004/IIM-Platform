"""PSO Logistics — Tối ưu hóa Giao hàng v1.0.0

Split-panel layout:
  Left  (fixed 300px) : scrollable control panel
  Right (expanding)   : QTabWidget
      Tab 0 — Bản đồ Tuyến đường : RouteMapCanvas (depot + customers + best route)
      Tab 1 — Đồ thị Hội tụ       : ConvergenceCanvas (gbest fitness vs iteration)

v1.0 scope : TSP (single vehicle, visit all customers exactly once)
v1.1 planned: VRP (multi-vehicle, capacity constraints)
v1.2 planned: VRPTW (multi-vehicle, time windows)

Threading strategy:
  - Simulation runs in SimulationWorker (QThread); signals carry only plain Python types.
  - PSO iteration animation: _on_iteration() slot updates route canvas via draw_idle().
  - Replay animation: separate QTimer reads _best_route_history after simulation ends.
    These two animations NEVER run concurrently.
  - on_unload() stops worker with request_stop() + wait(3000ms).

Problem generation (D5):
  - TSPProblem.generate() called in UI thread for canvas setup AND in worker thread
    for swarm creation.  Both use the same data_seed → identical problem layouts.
    No mutable problem object crosses the thread boundary.
"""
from __future__ import annotations

import io
import math
from typing import Any

import numpy as np

try:
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtWidgets import (
        QAbstractSpinBox,
        QCheckBox,
        QComboBox,
        QDoubleSpinBox,
        QFrame,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QProgressBar,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QSpinBox,
        QTabWidget,
        QVBoxLayout,
        QWidget,
    )
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False

try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    from matplotlib.patches import Circle, FancyBboxPatch
    _MPL = True
except ImportError:  # pragma: no cover
    _MPL = False

from core.module_runtime.base_module import BaseModule
from core.module_runtime.module_context import ModuleContext
from modules.logistics.pso_logistics.models.config import LogisticsPSOConfig
from modules.logistics.pso_logistics.models.state import (
    STATE_VERSION,
    default_state,
)
from modules.logistics.pso_logistics.problems.tsp_problem import TSPProblem
from modules.logistics.pso_logistics.problems.vrp_problem import VRPProblem
from modules.logistics.pso_logistics.problems.vrptw_problem import VRPTWProblem

try:
    from shiboken6 import isValid as _qt_is_valid
except ImportError:  # pragma: no cover
    def _qt_is_valid(_obj: object) -> bool:
        return True

_WidgetBase = QWidget if _QT else object  # type: ignore[misc,assignment]

# ── UI constants ──────────────────────────────────────────────────────────────
_CTRL_WIDTH: int = 340
_MONO_STYLE: str = "font-size: 11px; font-family: monospace;"
_MAX_HISTORY: int = 5000      # cap on stored replay frames
_DEFAULT_DELAY_MS: int = 50   # default simulation step delay
_DEFAULT_REPLAY_MS: int = 200  # default replay timer interval

# Colours used in all route maps
_COLOR_DEPOT = "#E74C3C"
_COLOR_CUSTOMER = "#2E86C1"
_COLOR_BEST_ROUTE = "#27AE60"
_COLOR_ALL_ROUTES = "#95A5A6"
# Per-vehicle colours for VRP (cycles if more vehicles than colours)
_VRP_COLORS = [
    "#27AE60", "#E74C3C", "#8E44AD", "#F39C12",
    "#1ABC9C", "#2980B9", "#E67E22", "#16A085",
]


# ─── Canvas: 2D route map ─────────────────────────────────────────────────────

class _RouteMapCanvas(_WidgetBase):  # type: ignore[valid-type]
    """Matplotlib canvas: depot + customers + best-route polyline.

    Call setup() once to draw the static background (depot and customers).
    Call update_route() every iteration to refresh the best-route overlay.
    Static elements (depot marker, customer scatter, labels) are drawn once
    in setup() and never redrawn — only the route lines are replaced.
    """

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        if not _QT:
            return
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if _MPL:
            self._fig = Figure(figsize=(7, 6), dpi=100)
            self._ax = self._fig.add_subplot(111)
            self._canvas = FigureCanvas(self._fig)
            self._canvas.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            layout.addWidget(self._canvas)
            self._route_artists: list = []
            self._particle_artists: list = []
            self._depot: Any = None
            self._customers: list = []
            self._road_network: Any = None
            self._road_node_indices: Any = None
            self._vrp_problem: Any = None   # set for VRP mode
            self._customer_patches: list = []  # for VRP node recoloring
            self._ready: bool = False
        else:
            layout.addWidget(
                QLabel("⚠ matplotlib chưa được cài. Chạy: pip install matplotlib")
            )

    def setup(
        self,
        depot: Any,
        customers: list,
        coord_range: float,
        road_network: Any = None,
        road_node_indices: Any = None,
        vrp_problem: Any = None,
    ) -> None:
        """Draw static background (nodes + optional road grid). UI thread only."""
        if not _MPL:
            return
        self._ax.clear()
        self._depot = depot
        self._customers = customers
        self._road_network = road_network
        self._road_node_indices = road_node_indices
        self._vrp_problem = vrp_problem
        self._route_artists = []
        self._particle_artists = []
        self._customer_patches = []

        n = len(customers)
        node_r = coord_range * 0.022   # ~2% of range — visible at any scale
        fs = 8 if n <= 15 else (7 if n <= 40 else 6)

        pad = coord_range * 0.06
        self._ax.set_xlim(-pad, coord_range + pad)
        self._ax.set_ylim(-pad, coord_range + pad)
        # No set_aspect — axes fills canvas fully at any coord_range

        # ── Background: road grid or plain ───────────────────────────────────
        if road_network is not None:
            self._ax.set_facecolor("#F0F3F4")
            road_network.draw_background(self._ax)
            self._ax.grid(False)
        else:
            self._ax.set_facecolor("white")
            self._ax.grid(True, alpha=0.18)

        # ── Customer circles with ID labels ───────────────────────────────────
        for c in customers:
            circ = Circle(
                (c.x, c.y), radius=node_r,
                facecolor=_COLOR_CUSTOMER, edgecolor="white",
                linewidth=1.2, zorder=5,
            )
            self._ax.add_patch(circ)
            self._customer_patches.append(circ)
            self._ax.text(
                c.x, c.y, str(c.id),
                ha="center", va="center",
                fontsize=fs, fontweight="bold", color="white", zorder=6,
            )

        # ── Depot: rounded square with "D" label ─────────────────────────────
        dr = node_r * 1.4
        depot_patch = FancyBboxPatch(
            (depot.x - dr, depot.y - dr), 2 * dr, 2 * dr,
            boxstyle="round,pad=0.15",
            facecolor=_COLOR_DEPOT, edgecolor="white",
            linewidth=1.5, zorder=6,
        )
        self._ax.add_patch(depot_patch)
        self._ax.text(
            depot.x, depot.y, "D",
            ha="center", va="center",
            fontsize=fs + 1, fontweight="bold", color="white", zorder=7,
        )

        self._ax.set_xlabel("x", fontsize=9)
        self._ax.set_ylabel("y", fontsize=9)
        map_title = "Bản đồ tuyến đường VRP" if vrp_problem else "Bản đồ tuyến đường TSP"
        self._ax.set_title(map_title, fontsize=10)
        self._fig.tight_layout(pad=1.0)
        self._canvas.draw()
        self._ready = True

    def update_route(
        self,
        perm: list[int],
        gbest_fitness: float,
        iteration: int,
        all_perms: list[list[int]] | None = None,
        show_all: bool = False,
    ) -> None:
        """Refresh best-route polyline (and optionally faded particle routes).

        Uses draw_idle() for minimal overhead.
        """
        if not _MPL or not self._ready:
            return

        # Remove previous dynamic artists
        for a in self._route_artists + self._particle_artists:
            try:
                a.remove()
            except Exception:  # noqa: BLE001
                pass
        self._route_artists = []
        self._particle_artists = []

        # Faded particle routes (Euclidean mode only — road paths are expensive to draw per-particle)
        if show_all and all_perms and self._road_network is None:
            for p_perm in all_perms[:30]:  # cap at 30 for performance
                xs, ys = self._perm_to_xy(p_perm)
                (line,) = self._ax.plot(
                    xs, ys,
                    color=_COLOR_ALL_ROUTES, alpha=0.12, lw=0.6, zorder=2,
                )
                self._particle_artists.append(line)

        # Best route polyline (follows roads when road network is active)
        if perm:
            if self._vrp_problem is not None:
                # VRP: draw one coloured line per vehicle route
                routes = self._vrp_problem.decode_giant_tour(perm)
                # Recolor customer nodes by vehicle assignment
                for _cp in self._customer_patches:
                    _cp.set_facecolor(_COLOR_CUSTOMER)
                for _vi, _rt in enumerate(routes):
                    _nc = _VRP_COLORS[_vi % len(_VRP_COLORS)]
                    for _ci in _rt:
                        if _ci < len(self._customer_patches):
                            self._customer_patches[_ci].set_facecolor(_nc)
                for v_idx, route in enumerate(routes):
                    xs, ys = self._route_to_xy(route)
                    color = _VRP_COLORS[v_idx % len(_VRP_COLORS)]
                    (line,) = self._ax.plot(
                        xs, ys,
                        color=color, lw=2.0, alpha=0.9, zorder=4,
                        solid_capstyle="round", solid_joinstyle="round",
                    )
                    self._route_artists.append(line)
                n_used = len(routes)
                n_max = self._vrp_problem.n_vehicles
                self._ax.set_title(
                    f"VRP — Vòng {iteration}  |  gBest = {gbest_fitness:.2f}"
                    f"  |  {n_used}/{n_max} xe",
                    fontsize=10,
                )
            else:
                # TSP: single green route
                xs, ys = self._get_tour_coords(perm)
                (line,) = self._ax.plot(
                    xs, ys,
                    color=_COLOR_BEST_ROUTE, lw=2.0, alpha=0.9, zorder=4,
                    solid_capstyle="round", solid_joinstyle="round",
                )
                self._route_artists.append(line)
                self._ax.set_title(
                    f"TSP — Vòng {iteration}  |  gBest = {gbest_fitness:.2f}",
                    fontsize=10,
                )
        self._canvas.draw_idle()

    def _get_tour_coords(self, perm: list[int]) -> tuple[list[float], list[float]]:
        """Road-following coordinates when road network active; straight lines otherwise."""
        if self._road_network is not None and self._road_node_indices is not None:
            coords = self._road_network.tour_coords(self._road_node_indices, perm)
            return [p[0] for p in coords], [p[1] for p in coords]
        return self._perm_to_xy(perm)

    def _route_to_xy(self, customer_indices: list[int]) -> tuple[list[float], list[float]]:
        """Straight-line coords for a single VRP vehicle route (depot→customers→depot)."""
        xs: list[float] = [self._depot.x]
        ys: list[float] = [self._depot.y]
        for idx in customer_indices:
            xs.append(self._customers[idx].x)
            ys.append(self._customers[idx].y)
        xs.append(self._depot.x)
        ys.append(self._depot.y)
        return xs, ys

    def _perm_to_xy(self, perm: list[int]) -> tuple[list[float], list[float]]:
        """Convert customer-index permutation to (xs, ys) including depot endpoints."""
        xs: list[float] = [self._depot.x]
        ys: list[float] = [self._depot.y]
        for idx in perm:
            xs.append(self._customers[idx].x)
            ys.append(self._customers[idx].y)
        xs.append(self._depot.x)
        ys.append(self._depot.y)
        return xs, ys

    def get_figure_bytes(self) -> bytes:
        if not _MPL:
            return b""
        buf = io.BytesIO()
        self._fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
        return buf.getvalue()


# ─── Canvas: convergence chart ────────────────────────────────────────────────

class _ConvergenceCanvas(_WidgetBase):  # type: ignore[valid-type]
    """Matplotlib canvas: gbest fitness vs iteration number."""

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        if not _QT:
            return
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if _MPL:
            self._fig = Figure(figsize=(6, 5), dpi=100)
            self._ax = self._fig.add_subplot(111)
            self._canvas = FigureCanvas(self._fig)
            self._canvas.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            layout.addWidget(self._canvas)
            self._history: list[float] = []
        else:
            layout.addWidget(
                QLabel("⚠ matplotlib chưa được cài. Chạy: pip install matplotlib")
            )

    def reset(self, problem_type: str = "tsp") -> None:
        if not _MPL:
            return
        self._history = []
        self._problem_type = problem_type
        self._ax.clear()
        self._ax.set_xlabel("Vòng lặp", fontsize=9)
        self._ax.set_ylabel("gBest Distance", fontsize=9)
        label = "TSP" if problem_type == "tsp" else ("VRPTW" if problem_type == "vrptw" else "VRP")
        self._ax.set_title(f"Đồ thị hội tụ PSO — {label}", fontsize=10)
        self._ax.grid(True, alpha=0.3)
        self._canvas.draw()

    def append(self, fitness: float) -> None:
        if not _MPL:
            return
        self._history.append(fitness)
        self._redraw()

    def set_history(self, history: list[float]) -> None:
        if not _MPL:
            return
        self._history = list(history)
        self._redraw()

    def _redraw(self) -> None:
        self._ax.clear()
        _pt = getattr(self, "_problem_type", "tsp")
        label = "TSP" if _pt == "tsp" else ("VRPTW" if _pt == "vrptw" else "VRP")
        if self._history:
            x = list(range(len(self._history)))
            self._ax.plot(x, self._history, color="#2471A3", lw=1.6)
            self._ax.fill_between(x, self._history, alpha=0.10, color="#2471A3")
            self._ax.set_title(
                f"Hội tụ PSO — {label}  |  gBest = {self._history[-1]:.2f}",
                fontsize=10,
            )
        else:
            self._ax.set_title(f"Đồ thị hội tụ PSO — {label}", fontsize=10)
        self._ax.set_xlabel("Vòng lặp", fontsize=9)
        self._ax.set_ylabel("gBest Distance", fontsize=9)
        self._ax.grid(True, alpha=0.3)
        self._fig.tight_layout(pad=1.0)
        self._canvas.draw_idle()

    def get_figure_bytes(self) -> bytes:
        if not _MPL:
            return b""
        buf = io.BytesIO()
        self._fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
        return buf.getvalue()


# ─── Canvas: swarm view (N sub-plots, one per particle) ───────────────────────

_SWARM_MAX_DISPLAY: int = 12   # cap displayed particles to avoid perf issues
_COLOR_GBEST_FRAME = "#E74C3C"
_COLOR_PARTICLE_ROUTE = "#7F8C8D"
_COLOR_GBEST_ROUTE = "#E74C3C"


class _SwarmViewCanvas(_WidgetBase):  # type: ignore[valid-type]
    """Matplotlib canvas: grid of sub-plots, one per particle.

    Each subplot shows that particle's current route on the same node layout.
    The gbest owner's subplot gets a red border and red route; all others
    use grey routes.

    Call setup() once after the problem is generated (UI thread).
    Call update() every iteration to refresh all subplots.
    Only call update() when the tab is visible — caller must throttle if needed.
    """

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        if not _QT:
            return
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if _MPL:
            self._fig = Figure(dpi=90)
            self._canvas = FigureCanvas(self._fig)
            self._canvas.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            layout.addWidget(self._canvas)
            self._axes: list = []
            self._route_artists: list[list] = []   # per-subplot dynamic artists
            self._depot: Any = None
            self._customers: list = []
            self._coord_range: float = 100.0
            self._n_display: int = 0
            self._ready: bool = False
        else:
            layout.addWidget(
                QLabel("⚠ matplotlib chưa được cài. Chạy: pip install matplotlib")
            )

    # ── Layout helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _grid_dims(n: int) -> tuple[int, int]:
        """Return (rows, cols) for a near-square grid of n cells."""
        import math
        cols = math.ceil(math.sqrt(n))
        rows = math.ceil(n / cols)
        return rows, cols

    def _node_labels(self) -> list[str]:
        """A-E for ≤5 customers, numeric ID otherwise."""
        n = len(self._customers)
        if n <= 5:
            return [chr(ord("A") + i) for i in range(n)]
        return [str(c.id) for c in self._customers]

    # ── Public API ────────────────────────────────────────────────────────────

    def setup(
        self,
        depot: Any,
        customers: list,
        coord_range: float,
        n_particles: int,
    ) -> None:
        """Create the subplot grid and draw static nodes.  UI thread only."""
        if not _MPL:
            return
        self._depot = depot
        self._customers = customers
        self._coord_range = coord_range
        self._n_display = min(n_particles, _SWARM_MAX_DISPLAY)

        rows, cols = self._grid_dims(self._n_display)
        self._fig.clear()
        self._axes = []
        self._route_artists = []

        labels = self._node_labels()
        n_cust = len(customers)
        node_r = coord_range * 0.04
        pad = coord_range * 0.08
        fs = 7

        for idx in range(self._n_display):
            ax = self._fig.add_subplot(rows, cols, idx + 1)
            ax.set_xlim(-pad, coord_range + pad)
            ax.set_ylim(-pad, coord_range + pad)
            ax.set_aspect("equal", adjustable="box")
            ax.set_facecolor("white")
            ax.axis("off")

            # Static: customer dots
            for i, c in enumerate(customers):
                circ = __import__("matplotlib.patches", fromlist=["Circle"]).Circle(
                    (c.x, c.y), radius=node_r,
                    facecolor=_COLOR_CUSTOMER, edgecolor="white",
                    linewidth=0.8, zorder=5,
                )
                ax.add_patch(circ)
                lbl = labels[i] if i < len(labels) else str(c.id)
                ax.text(c.x, c.y, lbl,
                        ha="center", va="center",
                        fontsize=fs, fontweight="bold", color="white", zorder=6)

            # Static: depot square
            dr = node_r * 1.3
            depot_patch = __import__(
                "matplotlib.patches", fromlist=["FancyBboxPatch"]
            ).FancyBboxPatch(
                (depot.x - dr, depot.y - dr), 2 * dr, 2 * dr,
                boxstyle="round,pad=0.1",
                facecolor=_COLOR_DEPOT, edgecolor="white",
                linewidth=0.8, zorder=6,
            )
            ax.add_patch(depot_patch)
            ax.text(depot.x, depot.y, "D",
                    ha="center", va="center",
                    fontsize=fs, fontweight="bold", color="white", zorder=7)

            ax.set_title(f"Hạt {idx + 1}", fontsize=7, pad=2)
            self._axes.append(ax)
            self._route_artists.append([])

        self._fig.tight_layout(pad=0.4, h_pad=0.6, w_pad=0.4)
        self._canvas.draw()
        self._ready = True

    def update(
        self,
        positions: list[list[int]],
        gbest_position: list[int],
        customers: list,
        depot: Any,
        iteration: int,
    ) -> None:
        """Refresh all subplots with current particle routes.  UI thread only."""
        if not _MPL or not self._ready:
            return

        n_show = min(len(positions), self._n_display)
        gbest_set = set(gbest_position)

        for idx in range(n_show):
            ax = self._axes[idx]
            perm = positions[idx]

            # Remove previous route artists for this subplot
            for a in self._route_artists[idx]:
                try:
                    a.remove()
                except Exception:  # noqa: BLE001
                    pass
            self._route_artists[idx] = []

            # Determine if this particle owns gbest
            is_gbest = (list(perm) == list(gbest_position))
            route_color = _COLOR_GBEST_ROUTE if is_gbest else _COLOR_PARTICLE_ROUTE
            lw = 1.4 if is_gbest else 0.7
            alpha = 0.9 if is_gbest else 0.55

            # Draw route: depot → customers in perm order → depot
            xs = [depot.x]
            ys = [depot.y]
            for ci in perm:
                if ci < len(customers):
                    xs.append(customers[ci].x)
                    ys.append(customers[ci].y)
            xs.append(depot.x)
            ys.append(depot.y)
            (line,) = ax.plot(xs, ys, color=route_color, lw=lw, alpha=alpha, zorder=3)
            self._route_artists[idx].append(line)

            # Update title with distance label
            dist_str = f"d: {self._customers[0].id if customers else '?'}"
            try:
                import math
                d = sum(
                    math.hypot(
                        customers[perm[k]].x - customers[perm[k - 1]].x,
                        customers[perm[k]].y - customers[perm[k - 1]].y,
                    )
                    for k in range(1, len(perm))
                )
                d += math.hypot(
                    customers[perm[0]].x - depot.x,
                    customers[perm[0]].y - depot.y,
                ) if perm else 0.0
                d += math.hypot(
                    customers[perm[-1]].x - depot.x,
                    customers[perm[-1]].y - depot.y,
                ) if perm else 0.0
                dist_str = f"{d:.1f}"
            except Exception:  # noqa: BLE001
                pass

            title_color = _COLOR_GBEST_FRAME if is_gbest else "#2C3E50"
            title_fw = "bold" if is_gbest else "normal"
            ax.set_title(
                f"Hạt {idx + 1} — {dist_str}",
                fontsize=7, pad=2, color=title_color, fontweight=title_fw,
            )

            # Frame colour: red border for gbest owner
            for spine in ax.spines.values():
                spine.set_visible(True)
                spine.set_linewidth(1.5 if is_gbest else 0.5)
                spine.set_edgecolor(_COLOR_GBEST_FRAME if is_gbest else "#D5D8DC")

        # Super-title
        if self._n_display < len(positions):
            extra = f"  (hiện {self._n_display}/{len(positions)} hạt)"
        else:
            extra = ""
        self._fig.suptitle(
            f"Bầy đàn — Vòng {iteration}{extra}",
            fontsize=9, y=0.99,
        )
        self._canvas.draw_idle()

    def reset(self) -> None:
        """Clear canvas when a new run starts."""
        if not _MPL:
            return
        self._ready = False
        self._fig.clear()
        self._axes = []
        self._route_artists = []
        self._canvas.draw()

    def get_figure_bytes(self) -> bytes:
        if not _MPL:
            return b""
        buf = io.BytesIO()
        self._fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        return buf.getvalue()


# ─── Main view widget ─────────────────────────────────────────────────────────

class _LogisticsView(_WidgetBase):  # type: ignore[valid-type]
    """Root QWidget for the PSO Logistics module."""

    def __init__(self, module: "PSOLogisticsModule") -> None:
        super().__init__()
        if not _QT:
            return
        self._module = module
        self._worker = None
        self._sim_running: bool = False
        self._total_iters: int = 100
        self._current_problem: TSPProblem | VRPProblem | None = None
        self._best_route_history: list[dict] = []  # {iteration, fitness, perm}
        self._last_result: dict | None = None
        # Replay state
        self._replay_idx: int = 0
        self._replay_timer: QTimer = QTimer()
        self._replay_timer.timeout.connect(self._on_replay_tick)
        # Canvas refs
        self._map_canvas: _RouteMapCanvas | None = None
        self._convergence_canvas: _ConvergenceCanvas | None = None
        self._swarm_canvas: _SwarmViewCanvas | None = None
        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(8)

        # ── Left: tabbed control panel ────────────────────────────────────────
        _CSS_NO_ARROWS = (
            "QSpinBox::up-button, QSpinBox::down-button,"
            "QDoubleSpinBox::up-button, QDoubleSpinBox::down-button"
            "{ width: 0px; height: 0px; border: none; image: none; }"
            "QSpinBox, QDoubleSpinBox { padding-right: 3px; }"
        )
        left_widget = QWidget()
        left_widget.setFixedWidth(_CTRL_WIDTH)
        left_widget.setStyleSheet(_CSS_NO_ARROWS)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.setSpacing(4)
        # Parameter tabs
        self._ctrl_tabs = QTabWidget()
        self._ctrl_tabs.setDocumentMode(True)
        _tab_problem = QWidget()
        _tab_pso = QWidget()
        _tab_disp = QWidget()
        _tl_problem = QVBoxLayout(_tab_problem)
        _tl_problem.setContentsMargins(4, 4, 4, 4)
        _tl_problem.setSpacing(4)
        _tl_pso = QVBoxLayout(_tab_pso)
        _tl_pso.setContentsMargins(4, 4, 4, 4)
        _tl_pso.setSpacing(4)
        _tl_disp = QVBoxLayout(_tab_disp)
        _tl_disp.setContentsMargins(4, 4, 4, 4)
        _tl_disp.setSpacing(4)
        self._ctrl_tabs.addTab(_tab_problem, 'Bài toán')
        self._ctrl_tabs.addTab(_tab_pso, 'PSO')
        self._ctrl_tabs.addTab(_tab_disp, 'Hiển thị')
        left_layout.addWidget(self._ctrl_tabs)

        def _lrow(lbl_text: str, widget: QWidget, lbl_w: int = 140) -> QHBoxLayout:
            row = QHBoxLayout()
            lbl = QLabel(lbl_text)
            lbl.setMinimumWidth(lbl_w)
            row.addWidget(lbl)
            row.addWidget(widget)
            return row

        # ── Group: Problem ────────────────────────────────────────────────────
        grp_prob = QGroupBox("Bài toán")
        g1 = QVBoxLayout(grp_prob)
        g1.setSpacing(4)

        self._combo_problem_type = QComboBox()
        self._combo_problem_type.addItem("TSP — 1 xe", "tsp")
        self._combo_problem_type.addItem("VRP — Tải trọng", "vrp")
        self._combo_problem_type.addItem("VRPTW — Thời gian", "vrptw")
        g1.addLayout(_lrow("Loại bài toán:", self._combo_problem_type))

        self._spin_n_cust = QSpinBox()
        self._spin_n_cust.setRange(3, 80)
        self._spin_n_cust.setValue(10)
        g1.addLayout(_lrow("Số điểm giao:", self._spin_n_cust))

        self._spin_range = QDoubleSpinBox()
        self._spin_range.setRange(10.0, 1000.0)
        self._spin_range.setValue(100.0)
        self._spin_range.setDecimals(0)
        self._spin_range.setSingleStep(10.0)
        g1.addLayout(_lrow("Phạm vi tọa độ:", self._spin_range))

        self._spin_data_seed = QSpinBox()
        self._spin_data_seed.setRange(1, 99999)
        self._spin_data_seed.setValue(42)
        self._spin_data_seed.setToolTip("Seed tạo vị trí khách hàng")
        g1.addLayout(_lrow("Seed dữ liệu:", self._spin_data_seed))

        _tl_problem.addWidget(grp_prob)

        # ── Group: VRP settings ───────────────────────────────────────────────
        self._grp_vrp = QGroupBox("VRP — Xe & Tải trọng")
        gv = QVBoxLayout(self._grp_vrp)
        gv.setSpacing(4)

        self._spin_n_vehicles = QSpinBox()
        self._spin_n_vehicles.setRange(2, 20)
        self._spin_n_vehicles.setValue(3)
        self._spin_n_vehicles.setToolTip("Số xe tối đa được phép dùng")
        gv.addLayout(_lrow("Số xe tối đa:", self._spin_n_vehicles))

        self._spin_capacity = QDoubleSpinBox()
        self._spin_capacity.setRange(5.0, 9999.0)
        self._spin_capacity.setValue(50.0)
        self._spin_capacity.setDecimals(1)
        self._spin_capacity.setSingleStep(5.0)
        self._spin_capacity.setToolTip("Tải trọng tối đa mỗi xe")
        gv.addLayout(_lrow("Tải trọng xe:", self._spin_capacity))

        self._spin_demand_seed = QSpinBox()
        self._spin_demand_seed.setRange(1, 99999)
        self._spin_demand_seed.setValue(7)
        self._spin_demand_seed.setToolTip("Seed tạo cầu (demand) của khách hàng")
        gv.addLayout(_lrow("Seed cầu:", self._spin_demand_seed))

        self._spin_max_demand = QDoubleSpinBox()
        self._spin_max_demand.setRange(1.0, 200.0)
        self._spin_max_demand.setValue(15.0)
        self._spin_max_demand.setDecimals(1)
        self._spin_max_demand.setSingleStep(1.0)
        self._spin_max_demand.setToolTip("Cầu tối đa mỗi khách hàng (U[1, max_demand])")
        gv.addLayout(_lrow("Cầu tối đa:", self._spin_max_demand))

        self._grp_vrp.setEnabled(False)   # disabled until VRP mode selected
        _tl_problem.addWidget(self._grp_vrp)

        # ── Group: VRPTW settings ─────────────────────────────────────────────
        self._grp_vrptw = QGroupBox("VRPTW — Cửa sổ thời gian")
        gvt = QVBoxLayout(self._grp_vrptw)
        gvt.setSpacing(4)

        self._spin_speed = QDoubleSpinBox()
        self._spin_speed.setRange(0.1, 999.0)
        self._spin_speed.setValue(1.0)
        self._spin_speed.setDecimals(2)
        self._spin_speed.setSingleStep(0.1)
        self._spin_speed.setToolTip("Tốc độ xe (đơn vị khoảng cách / đơn vị thời gian)")
        gvt.addLayout(_lrow("Tốc độ xe:", self._spin_speed))

        self._spin_tw_width = QDoubleSpinBox()
        self._spin_tw_width.setRange(1.0, 9999.0)
        self._spin_tw_width.setValue(30.0)
        self._spin_tw_width.setDecimals(1)
        self._spin_tw_width.setSingleStep(5.0)
        self._spin_tw_width.setToolTip("Độ rộng cửa sổ thời gian mỗi khách hàng")
        gvt.addLayout(_lrow("Độ rộng TW:", self._spin_tw_width))

        self._spin_svc_max = QDoubleSpinBox()
        self._spin_svc_max.setRange(0.0, 999.0)
        self._spin_svc_max.setValue(5.0)
        self._spin_svc_max.setDecimals(1)
        self._spin_svc_max.setSingleStep(1.0)
        self._spin_svc_max.setToolTip("Thời gian phục vụ tối đa tại mỗi khách hàng U[0, max]")
        gvt.addLayout(_lrow("Thời gian PV max:", self._spin_svc_max))

        self._spin_tw_penalty = QDoubleSpinBox()
        self._spin_tw_penalty.setRange(0.0, 9999.0)
        self._spin_tw_penalty.setValue(10.0)
        self._spin_tw_penalty.setDecimals(1)
        self._spin_tw_penalty.setSingleStep(5.0)
        self._spin_tw_penalty.setToolTip("Hình phạt / đơn vị trễ hạn (soft time windows)")
        gvt.addLayout(_lrow("Hình phạt TW:", self._spin_tw_penalty))

        self._spin_tw_seed = QSpinBox()
        self._spin_tw_seed.setRange(1, 99999)
        self._spin_tw_seed.setValue(13)
        self._spin_tw_seed.setToolTip("Seed sinh cửa sổ thời gian và thời gian phục vụ")
        gvt.addLayout(_lrow("Seed TW:", self._spin_tw_seed))

        self._grp_vrptw.setEnabled(False)   # disabled until VRPTW mode selected
        _tl_problem.addWidget(self._grp_vrptw)
        _tl_problem.addStretch()

        # Wire problem type switch
        self._combo_problem_type.currentIndexChanged.connect(self._on_problem_type_changed)

        # ── Group: PSO parameters ─────────────────────────────────────────────
        grp_pso = QGroupBox("Tham số PSO")
        g2 = QVBoxLayout(grp_pso)
        g2.setSpacing(4)

        self._spin_npart = QSpinBox()
        self._spin_npart.setRange(5, 200)
        self._spin_npart.setValue(30)
        g2.addLayout(_lrow("Số hạt:", self._spin_npart))

        self._spin_niter = QSpinBox()
        self._spin_niter.setRange(10, 2000)
        self._spin_niter.setValue(100)
        g2.addLayout(_lrow("Số vòng lặp:", self._spin_niter))

        self._spin_w = QDoubleSpinBox()
        self._spin_w.setRange(0.0, 1.0)
        self._spin_w.setValue(0.5)
        self._spin_w.setSingleStep(0.05)
        self._spin_w.setDecimals(2)
        self._spin_w.setToolTip("Quán tính — quyết định số operator ngẫu nhiên")
        g2.addLayout(_lrow("w (quán tính):", self._spin_w))

        self._spin_c1 = QDoubleSpinBox()
        self._spin_c1.setRange(0.0, 4.0)
        self._spin_c1.setValue(1.5)
        self._spin_c1.setSingleStep(0.1)
        self._spin_c1.setDecimals(2)
        g2.addLayout(_lrow("c₁ (cá nhân):", self._spin_c1))

        self._spin_c2 = QDoubleSpinBox()
        self._spin_c2.setRange(0.0, 4.0)
        self._spin_c2.setValue(1.5)
        self._spin_c2.setSingleStep(0.1)
        self._spin_c2.setDecimals(2)
        g2.addLayout(_lrow("c₂ (xã hội):", self._spin_c2))

        self._spin_ops = QSpinBox()
        self._spin_ops.setRange(1, 10)
        self._spin_ops.setValue(3)
        self._spin_ops.setToolTip("Số operator tối đa mỗi bước / thành phần PSO")
        g2.addLayout(_lrow("n_ops tối đa:", self._spin_ops))

        self._combo_topo = QComboBox()
        self._combo_topo.addItem("Star (toàn cục)", "star")
        self._combo_topo.addItem("Ring (láng giềng)", "ring")
        g2.addLayout(_lrow("Topology:", self._combo_topo))

        self._spin_pso_seed = QSpinBox()
        self._spin_pso_seed.setRange(0, 99999)
        self._spin_pso_seed.setValue(42)
        self._spin_pso_seed.setSpecialValueText("ngẫu nhiên")
        self._spin_pso_seed.setToolTip("0 = seed ngẫu nhiên mỗi lần chạy")
        g2.addLayout(_lrow("Seed PSO:", self._spin_pso_seed))

        self._spin_mutation = QDoubleSpinBox()
        self._spin_mutation.setRange(0.0, 0.5)
        self._spin_mutation.setValue(0.05)
        self._spin_mutation.setDecimals(2)
        self._spin_mutation.setSingleStep(0.01)
        self._spin_mutation.setToolTip(
            "Xác suất đột biến ngẫu nhiên mỗi hạt/bước — tránh bẫy tối ưu cục bộ (0 = tắt)"
        )
        g2.addLayout(_lrow("Tỷ lệ đột biến:", self._spin_mutation))

        _tl_pso.addWidget(grp_pso)
        _tl_pso.addStretch()

        # ── Group: Display ────────────────────────────────────────────────────
        grp_disp = QGroupBox("Hiển thị & Tốc độ")
        g3 = QVBoxLayout(grp_disp)
        g3.setSpacing(4)

        self._spin_delay = QSpinBox()
        self._spin_delay.setRange(0, 2000)
        self._spin_delay.setValue(_DEFAULT_DELAY_MS)
        self._spin_delay.setSingleStep(10)
        self._spin_delay.setSuffix(" ms")
        self._spin_delay.setToolTip("Thời gian chờ giữa các bước (0 = nhanh nhất)")
        g3.addLayout(_lrow("Trễ / bước:", self._spin_delay))

        self._chk_show_all = QCheckBox("Hiện tất cả nghiệm (mờ)")
        self._chk_show_all.setChecked(False)
        self._chk_show_all.setToolTip(
            "Hiển thị route của tất cả hạt ở màu xám mờ; chỉ tác dụng khi đang chạy"
        )
        g3.addWidget(self._chk_show_all)

        self._chk_road_mode = QCheckBox("Chế độ lưới đường phố")
        self._chk_road_mode.setChecked(False)
        self._chk_road_mode.setToolTip(
            "Bật: xe di chuyển theo lưới đường phố (khoảng cách thực tế, không phải đường thẳng)"
        )
        g3.addWidget(self._chk_road_mode)

        replay_row = QHBoxLayout()
        lbl_rs = QLabel("Tốc độ phát lại:")
        lbl_rs.setMinimumWidth(140)
        self._spin_replay_speed = QSpinBox()
        self._spin_replay_speed.setRange(50, 2000)
        self._spin_replay_speed.setValue(_DEFAULT_REPLAY_MS)
        self._spin_replay_speed.setSingleStep(50)
        self._spin_replay_speed.setSuffix(" ms/frame")
        replay_row.addWidget(lbl_rs)
        replay_row.addWidget(self._spin_replay_speed)
        g3.addLayout(replay_row)

        _tl_disp.addWidget(grp_disp)
        _tl_disp.addStretch()

        # ── Run / Stop ────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        _btn_style_run = (
            "QPushButton{background:#2471A3;color:white;font-weight:bold;"
            "padding:5px 8px;border-radius:4px;}"
            "QPushButton:hover{background:#1A5276;}"
            "QPushButton:disabled{background:#BDC3C7;color:#7F8C8D;}"
        )
        _btn_style_stop = (
            "QPushButton{background:#C0392B;color:white;font-weight:bold;"
            "padding:5px 8px;border-radius:4px;}"
            "QPushButton:disabled{background:#BDC3C7;color:#7F8C8D;}"
        )
        self._btn_run = QPushButton("▶  Chạy")
        self._btn_run.setStyleSheet(_btn_style_run)
        self._btn_stop = QPushButton("■  Dừng")
        self._btn_stop.setEnabled(False)
        self._btn_stop.setStyleSheet(_btn_style_stop)
        btn_row.addWidget(self._btn_run)
        btn_row.addWidget(self._btn_stop)
        left_layout.addLayout(btn_row)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        left_layout.addWidget(self._progress)

        # ── Replay ────────────────────────────────────────────────────────────
        replay_btn_row = QHBoxLayout()
        _btn_style_replay = (
            "QPushButton{background:#27AE60;color:white;font-weight:bold;"
            "padding:4px 8px;border-radius:4px;}"
            "QPushButton:hover{background:#1E8449;}"
            "QPushButton:disabled{background:#BDC3C7;color:#7F8C8D;}"
        )
        self._btn_replay = QPushButton("⏯  Phát lại")
        self._btn_replay.setStyleSheet(_btn_style_replay)
        self._btn_replay.setEnabled(False)
        self._btn_replay.setToolTip("Phát lại quá trình PSO từ đầu trên bản đồ")
        self._btn_replay_stop = QPushButton("■")
        self._btn_replay_stop.setEnabled(False)
        self._btn_replay_stop.setMaximumWidth(32)
        self._btn_replay_stop.setStyleSheet(_btn_style_stop)
        replay_btn_row.addWidget(self._btn_replay)
        replay_btn_row.addWidget(self._btn_replay_stop)
        left_layout.addLayout(replay_btn_row)

        # ── Export buttons (compact: one row) ────────────────────────────────
        self._btn_export_map = QPushButton("📷 Bản đồ")
        self._btn_export_map.setEnabled(False)
        self._btn_export_conv = QPushButton("📷 Hội tụ")
        self._btn_export_conv.setEnabled(False)
        _export_row = QHBoxLayout()
        _export_row.addWidget(self._btn_export_map)
        _export_row.addWidget(self._btn_export_conv)
        left_layout.addLayout(_export_row)

        # ── Result panel ──────────────────────────────────────────────────────
        grp_res = QGroupBox("Kết quả")
        g4 = QVBoxLayout(grp_res)
        g4.setSpacing(3)

        self._lbl_fitness = QLabel("gBest quãng đường: —")
        self._lbl_fitness.setStyleSheet(_MONO_STYLE)
        self._lbl_fitness.setWordWrap(True)

        self._lbl_route = QLabel("Tuyến tốt nhất: —")
        self._lbl_route.setStyleSheet(_MONO_STYLE)
        self._lbl_route.setWordWrap(True)
        self._lbl_route.setTextFormat(Qt.TextFormat.RichText)

        self._lbl_iters = QLabel("Vòng lặp: —")
        self._lbl_iters.setStyleSheet(_MONO_STYLE)

        self._lbl_status = QLabel("Trạng thái: Chờ")
        self._lbl_status.setStyleSheet(_MONO_STYLE + " color:#7F8C8D;")

        for w in (self._lbl_fitness, self._lbl_route, self._lbl_iters, self._lbl_status):
            g4.addWidget(w)

        left_layout.addWidget(grp_res, stretch=1)

        # Remove up/down arrows from all spinboxes
        if _QT:
            for _sb in left_widget.findChildren(QAbstractSpinBox):
                _sb.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)

        root_layout.addWidget(left_widget)

        # ── Right: tabs ───────────────────────────────────────────────────────
        self._tabs = QTabWidget()
        self._tabs.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self._map_canvas = _RouteMapCanvas()
        self._tabs.addTab(self._map_canvas, "Bản đồ Tuyến đường")

        self._convergence_canvas = _ConvergenceCanvas()
        self._convergence_canvas.reset()
        self._tabs.addTab(self._convergence_canvas, "Đồ thị Hội tụ")

        self._swarm_canvas = _SwarmViewCanvas()
        self._tabs.addTab(self._swarm_canvas, "Bầy đàn")

        root_layout.addWidget(self._tabs, stretch=1)

        # ── Wire signals ──────────────────────────────────────────────────────
        self._btn_run.clicked.connect(self._on_run)
        self._btn_stop.clicked.connect(self._on_stop)
        self._btn_replay.clicked.connect(self._on_replay_start)
        self._btn_replay_stop.clicked.connect(self._on_replay_stop)
        self._btn_export_map.clicked.connect(self._on_export_map)
        self._btn_export_conv.clicked.connect(self._on_export_convergence)

    # ── Simulation control ────────────────────────────────────────────────────

    def _build_config(self) -> LogisticsPSOConfig:
        seed_val = self._spin_pso_seed.value()
        return LogisticsPSOConfig(
            n_customers=self._spin_n_cust.value(),
            coord_range=float(self._spin_range.value()),
            data_seed=self._spin_data_seed.value(),
            n_particles=self._spin_npart.value(),
            n_iterations=self._spin_niter.value(),
            w=self._spin_w.value(),
            c1=self._spin_c1.value(),
            c2=self._spin_c2.value(),
            n_ops_max=self._spin_ops.value(),
            topology=self._combo_topo.currentData(),
            pso_seed=seed_val if seed_val > 0 else None,
            step_delay_ms=self._spin_delay.value(),
            road_mode=self._chk_road_mode.isChecked(),
            problem_type=self._combo_problem_type.currentData(),
            n_vehicles=self._spin_n_vehicles.value(),
            vehicle_capacity=float(self._spin_capacity.value()),
            demand_seed=self._spin_demand_seed.value(),
            max_demand=float(self._spin_max_demand.value()),
            vehicle_speed=float(self._spin_speed.value()),
            tw_seed=self._spin_tw_seed.value(),
            tw_width=float(self._spin_tw_width.value()),
            service_time_max=float(self._spin_svc_max.value()),
            tw_penalty=float(self._spin_tw_penalty.value()),
            mutation_rate=self._spin_mutation.value(),
        )

    def _on_run(self) -> None:
        if self._sim_running:
            return

        from modules.logistics.pso_logistics.workers.simulation_worker import (
            SimulationWorker,
        )

        config = self._build_config()
        self._total_iters = config.n_iterations
        self._best_route_history = []

        # Generate problem in UI thread for canvas setup (D5)
        if config.problem_type == "vrptw":
            self._current_problem = VRPTWProblem.generate(
                config.n_customers, config.coord_range,
                config.data_seed, config.demand_seed,
                config.n_vehicles, config.vehicle_capacity,
                config.max_demand, config.vehicle_speed,
                config.tw_seed, config.tw_width,
                config.service_time_max, config.tw_penalty,
            )
            vrp_p = self._current_problem
            road_net = None
            road_ni = None
        elif config.problem_type == "vrp":
            self._current_problem = VRPProblem.generate(
                config.n_customers, config.coord_range,
                config.data_seed, config.demand_seed,
                config.n_vehicles, config.vehicle_capacity,
                config.max_demand,
            )
            vrp_p = self._current_problem
            road_net = None
            road_ni = None
        else:
            self._current_problem = TSPProblem.generate(
                config.n_customers, config.coord_range, config.data_seed,
                road_mode=config.road_mode,
            )
            vrp_p = None
            road_net = self._current_problem.road_network
            road_ni = self._current_problem.road_node_indices

        # Reset canvases
        self._convergence_canvas.reset(config.problem_type)
        self._map_canvas.setup(
            self._current_problem.depot,
            self._current_problem.customers,
            config.coord_range,
            road_network=road_net,
            road_node_indices=road_ni,
            vrp_problem=vrp_p,
        )
        self._swarm_canvas.reset()
        self._swarm_canvas.setup(
            self._current_problem.depot,
            self._current_problem.customers,
            config.coord_range,
            config.n_particles,
        )

        # Reset UI state
        self._progress.setValue(0)
        self._lbl_status.setText("Trạng thái: Đang chạy…")
        self._lbl_status.setStyleSheet(_MONO_STYLE + " color:#27AE60;")
        self._btn_run.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._btn_replay.setEnabled(False)
        self._btn_replay_stop.setEnabled(False)
        self._btn_export_map.setEnabled(False)
        self._btn_export_conv.setEnabled(False)

        # Create and start worker (re-generates identical problem from data_seed)
        self._worker = SimulationWorker(config)
        self._worker.iteration_done.connect(self._on_iteration)
        self._worker.simulation_done.connect(self._on_done)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.finished.connect(self._on_worker_finished)
        self._sim_running = True
        self._worker.start()

    def _on_stop(self) -> None:
        if self._worker is not None:
            self._worker.request_stop()
        self._lbl_status.setText("Trạng thái: Đang dừng…")

    def _on_problem_type_changed(self) -> None:
        """Enable/disable VRP/VRPTW groups and road mode based on problem type."""
        ptype = self._combo_problem_type.currentData()
        self._grp_vrp.setEnabled(ptype in ("vrp", "vrptw"))
        self._grp_vrptw.setEnabled(ptype == "vrptw")
        # Road mode only meaningful for TSP
        self._chk_road_mode.setEnabled(ptype == "tsp")

    def _on_iteration(
        self,
        iteration: int,
        gbest_fitness: float,
        gbest_perm: list,
        all_perms: list,
    ) -> None:
        """UI-thread slot: update canvas, labels and accumulate history."""
        # Accumulate replay history (cap at _MAX_HISTORY)
        self._best_route_history.append(
            {"iteration": iteration, "fitness": gbest_fitness, "perm": gbest_perm}
        )
        if len(self._best_route_history) > _MAX_HISTORY:
            self._best_route_history = self._best_route_history[-_MAX_HISTORY:]

        # Update progress
        pct = int(100 * iteration / max(1, self._total_iters))
        self._progress.setValue(pct)

        # Update convergence chart every iteration
        self._convergence_canvas.append(gbest_fitness)

        # Update route map every iteration (draw_idle is cheap)
        show_all = self._chk_show_all.isChecked()
        self._map_canvas.update_route(
            gbest_perm, gbest_fitness, iteration, all_perms, show_all
        )

        # Update swarm view only when tab is active (performance throttle)
        if self._tabs.currentIndex() == 2 and self._current_problem is not None:
            self._swarm_canvas.update(
                positions=all_perms,
                gbest_position=gbest_perm,
                customers=self._current_problem.customers,
                depot=self._current_problem.depot,
                iteration=iteration,
            )

        # Update result labels
        self._lbl_fitness.setText(f"gBest: {gbest_fitness:.4f}")
        self._lbl_iters.setText(f"Vòng lặp: {iteration}/{self._total_iters}")
        if self._current_problem and gbest_perm:
            if isinstance(self._current_problem, (VRPProblem, VRPTWProblem)):
                routes = self._current_problem.decode_routes(gbest_perm)
                html_rows = []
                _show = min(len(routes), 10)
                for r in routes[:_show]:
                    color = _VRP_COLORS[(r.vehicle_id - 1) % len(_VRP_COLORS)]
                    ids_str = "→".join(str(i) for i in r.customer_ids[:5])
                    if len(r.customer_ids) > 5:
                        ids_str += "→…"
                    swatch = f'<span style="color:{color}; font-size:13px;">&#9632;</span>'
                    if isinstance(self._current_problem, VRPTWProblem):
                        total_late = sum(r.lateness_times) if r.lateness_times else 0.0
                        extra = f" [{r.load:.0f}] trễ:{total_late:.1f}"
                    else:
                        extra = f" [{r.load:.0f}]"
                    html_rows.append(
                        f'{swatch} <b>Xe{r.vehicle_id}</b>: 0→{ids_str}→0{extra}'
                    )
                if len(routes) > _show:
                    html_rows.append(f'<span style="color:#888;">  … +{len(routes)-_show} xe nữa</span>')
                self._lbl_route.setText("<br>".join(html_rows))
            else:
                ids = self._current_problem.decode_route_ids(gbest_perm)
                short = ids[:7]
                route_str = " → ".join(str(i) for i in short)
                if len(ids) > 7:
                    route_str += " → …"
                self._lbl_route.setText(f"0 → {route_str} → 0")

    def _on_done(self, result: dict) -> None:
        self._last_result = result
        fitness = float(result["gbest_fitness"])
        iters = int(result["iterations_done"])
        stopped = bool(result.get("stopped_early", False))

        self._progress.setValue(100 if not stopped else self._progress.value())

        status = "Hoàn thành" if not stopped else "Đã dừng"
        self._lbl_status.setText(f"Trạng thái: {status}")
        self._lbl_status.setStyleSheet(
            _MONO_STYLE + " color:#2471A3; font-weight:bold;"
        )
        self._lbl_fitness.setText(f"gBest: {fitness:.4f}")
        self._lbl_iters.setText(f"Vòng lặp: {iters}/{self._total_iters}")

        self._module._last_result = result

    def _on_error(self, msg: str) -> None:
        self._lbl_status.setText(f"Lỗi: {msg}")
        self._lbl_status.setStyleSheet(_MONO_STYLE + " color:#E74C3C;")
        self._module._logger.error(f"[pso_logistics] simulation error: {msg}")

    def _on_worker_finished(self) -> None:
        self._sim_running = False
        self._btn_run.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._btn_export_map.setEnabled(True)
        self._btn_export_conv.setEnabled(True)
        if self._best_route_history:
            self._btn_replay.setEnabled(True)
        self._worker = None

    # ── Replay animation (D3: separate from simulation worker) ────────────────

    def _on_replay_start(self) -> None:
        """Start frame-by-frame playback of best_route_history via QTimer."""
        if not self._best_route_history or self._sim_running:
            return
        self._replay_idx = 0
        self._replay_timer.start(self._spin_replay_speed.value())
        self._btn_replay.setEnabled(False)
        self._btn_replay_stop.setEnabled(True)

    def _on_replay_stop(self) -> None:
        self._replay_timer.stop()
        self._btn_replay.setEnabled(bool(self._best_route_history))
        self._btn_replay_stop.setEnabled(False)

    def _on_replay_tick(self) -> None:
        if self._replay_idx >= len(self._best_route_history):
            self._replay_timer.stop()
            self._btn_replay.setEnabled(True)
            self._btn_replay_stop.setEnabled(False)
            return
        frame = self._best_route_history[self._replay_idx]
        self._map_canvas.update_route(
            frame["perm"], frame["fitness"], frame["iteration"]
        )
        self._lbl_iters.setText(
            f"Phát lại: {frame['iteration']}/{self._total_iters}"
        )
        self._replay_idx += 1

    # ── Export ────────────────────────────────────────────────────────────────

    def _on_export_map(self) -> None:
        try:
            data = self._map_canvas.get_figure_bytes()
            if not data:
                return
            path = self._module._export_svc.ask_save_path(
                self,
                title="Xuất Bản đồ Tuyến đường",
                default_name="pso_logistics_map.png",
                file_filter="PNG Image (*.png);;All Files (*)",
            )
            if path:
                self._module._export_svc.write_bytes(path, data)
                self._module._activity_svc.log(
                    "EXPORT_COMPLETED",
                    "PSO Logistics: map exported",
                    module_id=PSOLogisticsModule.MODULE_ID,
                )
        except Exception as exc:  # noqa: BLE001
            self._module._logger.warning(f"[pso_logistics] export map failed: {exc}")

    def _on_export_convergence(self) -> None:
        try:
            data = self._convergence_canvas.get_figure_bytes()
            if not data:
                return
            path = self._module._export_svc.ask_save_path(
                self,
                title="Xuất Đồ thị Hội tụ",
                default_name="pso_logistics_convergence.png",
                file_filter="PNG Image (*.png);;All Files (*)",
            )
            if path:
                self._module._export_svc.write_bytes(path, data)
                self._module._activity_svc.log(
                    "EXPORT_COMPLETED",
                    "PSO Logistics: convergence exported",
                    module_id=PSOLogisticsModule.MODULE_ID,
                )
        except Exception as exc:  # noqa: BLE001
            self._module._logger.warning(
                f"[pso_logistics] export convergence failed: {exc}"
            )

    # ── State helpers ─────────────────────────────────────────────────────────

    def get_ui_state(self) -> dict[str, Any]:
        def _combo_data(c: QComboBox) -> str:
            return c.currentData()

        return {
            "n_customers": self._spin_n_cust.value(),
            "coord_range": self._spin_range.value(),
            "data_seed": self._spin_data_seed.value(),
            "n_particles": self._spin_npart.value(),
            "n_iterations": self._spin_niter.value(),
            "w": self._spin_w.value(),
            "c1": self._spin_c1.value(),
            "c2": self._spin_c2.value(),
            "n_ops_max": self._spin_ops.value(),
            "topology": _combo_data(self._combo_topo),
            "pso_seed": self._spin_pso_seed.value(),
            "step_delay_ms": self._spin_delay.value(),
            "show_all_particles": self._chk_show_all.isChecked(),
            "replay_speed_ms": self._spin_replay_speed.value(),
            "active_tab": self._tabs.currentIndex(),
            "road_mode": self._chk_road_mode.isChecked(),
            "problem_type": _combo_data(self._combo_problem_type),
            "n_vehicles": self._spin_n_vehicles.value(),
            "vehicle_capacity": self._spin_capacity.value(),
            "demand_seed": self._spin_demand_seed.value(),
            "max_demand": self._spin_max_demand.value(),
            "vehicle_speed": self._spin_speed.value(),
            "tw_seed": self._spin_tw_seed.value(),
            "tw_width": self._spin_tw_width.value(),
            "service_time_max": self._spin_svc_max.value(),
            "tw_penalty": self._spin_tw_penalty.value(),
            "mutation_rate": self._spin_mutation.value(),
        }

    def apply_ui_state(self, state: dict[str, Any]) -> None:
        def _set_combo(combo: QComboBox, key: str) -> None:
            val = state.get(key)
            if val is None:
                return
            for i in range(combo.count()):
                if combo.itemData(i) == val:
                    combo.setCurrentIndex(i)
                    return

        self._spin_n_cust.setValue(state.get("n_customers", 10))
        self._spin_range.setValue(state.get("coord_range", 100.0))
        self._spin_data_seed.setValue(state.get("data_seed", 42))
        self._spin_npart.setValue(state.get("n_particles", 30))
        self._spin_niter.setValue(state.get("n_iterations", 100))
        self._spin_w.setValue(state.get("w", 0.5))
        self._spin_c1.setValue(state.get("c1", 1.5))
        self._spin_c2.setValue(state.get("c2", 1.5))
        self._spin_ops.setValue(state.get("n_ops_max", 3))
        _set_combo(self._combo_topo, "topology")
        self._spin_pso_seed.setValue(state.get("pso_seed", 42))
        self._spin_delay.setValue(state.get("step_delay_ms", _DEFAULT_DELAY_MS))
        self._chk_show_all.setChecked(state.get("show_all_particles", False))
        self._spin_replay_speed.setValue(state.get("replay_speed_ms", _DEFAULT_REPLAY_MS))
        self._tabs.setCurrentIndex(state.get("active_tab", 0))
        self._chk_road_mode.setChecked(state.get("road_mode", False))
        _set_combo(self._combo_problem_type, "problem_type")
        self._spin_n_vehicles.setValue(state.get("n_vehicles", 3))
        self._spin_capacity.setValue(state.get("vehicle_capacity", 50.0))
        self._spin_demand_seed.setValue(state.get("demand_seed", 7))
        self._spin_max_demand.setValue(state.get("max_demand", 15.0))
        self._spin_speed.setValue(state.get("vehicle_speed", 1.0))
        self._spin_tw_seed.setValue(state.get("tw_seed", 13))
        self._spin_tw_width.setValue(state.get("tw_width", 30.0))
        self._spin_svc_max.setValue(state.get("service_time_max", 5.0))
        self._spin_tw_penalty.setValue(state.get("tw_penalty", 10.0))
        self._spin_mutation.setValue(state.get("mutation_rate", 0.05))
        self._on_problem_type_changed()


# ─── BaseModule implementation ────────────────────────────────────────────────

class PSOLogisticsModule(BaseModule):
    """IIMP module — PSO Logistics v1.2.0 (TSP + VRP + VRPTW).

    Hosts discrete PSO simulation for routing problems.
    Simulation runs in SimulationWorker (QThread) to keep shell responsive.
    """

    MODULE_ID = "pso_logistics"
    MODULE_NAME = "PSO — Tối ưu hóa Giao hàng"
    MODULE_VERSION = "1.2.0"

    def __init__(self, manifest: dict, context: ModuleContext) -> None:
        super().__init__(manifest=manifest, context=context)
        self._logger = context.logger
        self._export_svc = context.export_service
        self._settings_svc = context.settings_service
        self._activity_svc = context.activity_service
        self._view: _LogisticsView | None = None
        self._last_result: dict | None = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def on_load(self) -> None:
        self._logger.info(f"[{self.MODULE_ID}] on_load")

    def build_view(self) -> Any:  # QWidget
        if self._view is None or not _qt_is_valid(self._view):
            self._view = _LogisticsView(self)
        return self._view

    def on_activate(self) -> None:
        self._logger.info(f"[{self.MODULE_ID}] on_activate")
        self._activity_svc.log(
            "MODULE_ACTIVATE",
            f"{self.MODULE_ID} activated",
            module_id=self.MODULE_ID,
        )

    def on_deactivate(self) -> None:
        self._logger.info(f"[{self.MODULE_ID}] on_deactivate")

    def on_unload(self) -> None:
        """Stop any running simulation before module is unloaded (D5)."""
        if self._view is not None and self._view._worker is not None:
            self._view._worker.request_stop()
            self._view._worker.wait(3000)
        if self._view is not None:
            self._view._replay_timer.stop()
        self._logger.info(f"[{self.MODULE_ID}] on_unload")

    # ── State persistence (BUG-03 compliant) ─────────────────────────────────

    def get_state(self) -> dict[str, Any]:
        state = default_state()
        if self._view is not None:
            state.update(self._view.get_ui_state())
        state["_state_version"] = STATE_VERSION
        if self._last_result:
            state["last_gbest_fitness"] = self._last_result.get("gbest_fitness")
            state["last_gbest_perm"] = self._last_result.get("gbest_perm")
            state["last_convergence"] = self._last_result.get("convergence_history", [])
            state["last_n_iterations"] = self._last_result.get("iterations_done")
        return state

    def restore_state(self, state: dict[str, Any]) -> None:
        if self._view is None:
            return
        self._view.apply_ui_state(state)

        # Restore convergence chart
        conv: list[float] = state.get("last_convergence", [])
        if conv:
            self._view._convergence_canvas.set_history(conv)

        # Restore result labels
        fitness = state.get("last_gbest_fitness")
        n_iters = state.get("last_n_iterations")
        if fitness is not None:
            self._view._lbl_fitness.setText(f"gBest: {fitness:.4f}")
        if n_iters is not None:
            self._view._lbl_iters.setText(f"Vòng lặp: {n_iters}")
            self._view._lbl_status.setText("Trạng thái: Đã khôi phục")
            self._view._lbl_status.setStyleSheet(_MONO_STYLE + " color:#7F8C8D;")

        self._logger.debug(f"[{self.MODULE_ID}] restore_state done")
