"""PSO Logistics Map — Tối ưu hóa Giao hàng trên Bản đồ Thật v1.1.0

Split-panel layout:
  Left  (320px fixed)  : control panel (Bản đồ, PSO, Kết quả)
  Right (expanding)    : QTabWidget
      Tab 0 — Bản đồ Tuyến đường : _MapCanvas (road network + best route)
      Tab 1 — Đồ thị Hội tụ      : _ConvergenceCanvas

Luồng hoạt động:
  1. Module load → tự động bắt đầu LoadWorker (load graph từ cache hoặc parse .pbf)
  2. LoadWorker phát finished() → UI chuyển sang trạng thái READY
     (gồm demands + time_windows + service_times nếu là VRP/VRPTW)
  3. User bấm Chạy → SimulationWorker bắt đầu PSO cho TSP / VRP / VRPTW
  4. Mỗi iteration → progress_updated → cập nhật canvas + labels
  5. finished → hiển thị kết quả, bật nút Replay + Export

Phase 4: hỗ trợ 3 loại bài toán:
    tsp   — Travelling Salesman Problem (1 xe, không ràng buộc)
    vrp   — Capacitated VRP (nhiều xe, ràng buộc tải trọng)
    vrptw — VRP with Time Windows (nhiều xe, tải trọng + cửa sổ thời gian)
"""
from __future__ import annotations

import io
import random
from pathlib import Path
from typing import Any

import numpy as np

try:
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtWidgets import (
        QAbstractSpinBox,
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
    from PySide6.QtCore import QThread, Signal

    _QT = True
except ImportError:  # pragma: no cover — headless unit tests
    _QT = False

try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.collections import LineCollection
    from matplotlib.figure import Figure
    from matplotlib.patches import Circle

    _MPL = True
except ImportError:  # pragma: no cover
    _MPL = False

from core.module_runtime.base_module import BaseModule
from core.module_runtime.module_context import ModuleContext
from modules.logistics.pso_logistics_map.core.graph_builder import load_or_build
from modules.logistics.pso_logistics_map.core.distance_matrix import build_matrix
from modules.logistics.pso_logistics_map.models.config import MapLogisticsPSOConfig
from modules.logistics.pso_logistics_map.models.state import (
    STATE_VERSION,
    default_state,
)
from modules.logistics.pso_logistics_map.problems.tsp_problem import TSPProblem
from modules.logistics.pso_logistics_map.pso.discrete_swarm import DiscreteSwarm
from modules.logistics.pso_logistics_map.workers.simulation_worker import (
    SimulationWorker,
)
from modules.logistics.pso_logistics_map.core.pbf_loader import KNOWN_BBOXES, BBox

# ── Paths ─────────────────────────────────────────────────────────────────────
_MODULE_DIR = Path(__file__).parent
_PBF_FILE = _MODULE_DIR / "vietnam-260413.osm.pbf"
_CACHE_DIR = _MODULE_DIR / "cache"

# ── UI constants ──────────────────────────────────────────────────────────────
_CTRL_WIDTH: int = 320
_MONO_STYLE: str = "font-size: 11px; font-family: monospace;"
_MAX_HISTORY: int = 5000
_DEFAULT_DELAY_MS: int = 50
_DEFAULT_REPLAY_MS: int = 200

_COLOR_DEPOT = "#E74C3C"
_COLOR_CUSTOMER = "#2E86C1"
_COLOR_BEST_ROUTE = "#27AE60"
_COLOR_ROAD = "#C8D6E5"
_VRP_COLORS = [
    "#27AE60", "#E74C3C", "#8E44AD", "#F39C12",
    "#1ABC9C", "#2980B9", "#E67E22", "#16A085",
]

_WidgetBase = QWidget if _QT else object  # type: ignore[misc,assignment]


# ── Module-level giant-tour decoder (for UI display) ──────────────────────────

def _decode_giant_tour(
    perm: list[int],
    demands: np.ndarray,
    capacity: float,
) -> list[list[int]]:
    """Greedy capacity-split (mirrors VRPProblem.decode_giant_tour).

    Used by _MapView._on_iteration / replay to split a VRP/VRPTW giant-tour
    permutation into per-vehicle route index lists (0-based customer indices).
    """
    routes: list[list[int]] = []
    current: list[int] = []
    load = 0.0
    for idx in perm:
        d = float(demands[idx])
        if current and load + d > capacity:
            routes.append(current)
            current = [idx]
            load = d
        else:
            current.append(idx)
            load += d
    if current:
        routes.append(current)
    return routes


# ─── LoadWorker — graph loading + problem setup ───────────────────────────────

class _LoadWorker(QThread if _QT else object):  # type: ignore[misc]
    """Background thread: load/build graph, pick random nodes, build dist matrix."""

    status_update = Signal(str)
    graph_loaded = Signal(dict)   # keys: graph, dist_matrix, node_ids, coords, road_paths
    error_occurred = Signal(str)

    def __init__(
        self,
        bbox_name: str,
        n_customers: int,
        data_seed: int,
        network_type: str = "driving",
        problem_type: str = "tsp",
        n_vehicles: int = 3,
        vehicle_capacity: float = 50.0,
        demand_seed: int = 7,
        max_demand: float = 15.0,
        tw_seed: int = 13,
        tw_width_s: float = 1800.0,
        service_time_max_s: float = 300.0,
        vehicle_speed_kmph: float = 30.0,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._bbox_name = bbox_name
        self._n_customers = n_customers
        self._data_seed = data_seed
        self._network_type = network_type
        self._problem_type = problem_type
        self._n_vehicles = n_vehicles
        self._vehicle_capacity = vehicle_capacity
        self._demand_seed = demand_seed
        self._max_demand = max_demand
        self._tw_seed = tw_seed
        self._tw_width_s = tw_width_s
        self._service_time_max_s = service_time_max_s
        self._vehicle_speed_kmph = vehicle_speed_kmph

    def run(self) -> None:  # noqa: C901
        try:
            pbf_path = str(_PBF_FILE)
            bbox: BBox = KNOWN_BBOXES[self._bbox_name]
            cache_path = str(
                _CACHE_DIR / f"{self._bbox_name}_{self._network_type}.pkl"
            )
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)

            # Only require the large .pbf when the bbox cache doesn't exist yet
            if not Path(cache_path).exists() and not _PBF_FILE.exists():
                self.error_occurred.emit(
                    f"Không tìm thấy cache hoặc file .pbf:\n{_PBF_FILE}\n"
                    "Hãy đặt file vietnam-260413.osm.pbf vào thư mục module."
                )
                return

            self.status_update.emit(
                f"Đang tải đồ thị {self._bbox_name} ({self._network_type})…"
            )
            import networkx as nx  # noqa: PLC0415 — lazy import to keep startup fast
            graph: nx.DiGraph = load_or_build(
                pbf_path,
                cache_path,
                network_type=self._network_type,
                bbox=bbox,
            )

            n_nodes = graph.number_of_nodes()
            if n_nodes < self._n_customers + 1:
                self.error_occurred.emit(
                    f"Bbox '{self._bbox_name}' chỉ có {n_nodes} nodes — "
                    f"cần ít nhất {self._n_customers + 1}. "
                    "Hãy tăng bbox hoặc giảm số điểm giao."
                )
                return

            self.status_update.emit(
                f"Đồ thị: {n_nodes:,} nodes — đang chọn bố cục bài toán…"
            )

            # ── Restrict sampling to the largest SCC (ensures all-pairs directed reachability)
            import networkx as nx  # noqa: PLC0415 — already imported above, re-bind
            scc_nodes = max(nx.strongly_connected_components(graph), key=len)
            all_nodes = list(scc_nodes)
            n_scc = len(all_nodes)
            self.status_update.emit(
                f"SCC lớn nhất: {n_scc:,} nodes — đang chọn bố cục bài toán…"
            )
            if n_scc < self._n_customers + 1:
                self.error_occurred.emit(
                    f"SCC lớn nhất chỉ có {n_scc} nodes — "
                    f"cần ít nhất {self._n_customers + 1}. Giảm số điểm giao."
                )
                return

            # Pick depot + customers from SCC nodes using data_seed
            rng = random.Random(self._data_seed)
            chosen = rng.sample(all_nodes, self._n_customers + 1)
            # index 0 = depot, rest = customers
            node_ids = chosen

            self.status_update.emit(
                f"Đang tính ma trận khoảng cách "
                f"({self._n_customers + 1}×{self._n_customers + 1})…"
            )
            dist_matrix = build_matrix(graph, node_ids)

            # Collect (lon, lat) for each node (x=lon, y=lat)
            coords = [
                (graph.nodes[n]["x"], graph.nodes[n]["y"])
                for n in node_ids
            ]

            # Pre-compute road geometry for route visualisation (background thread, safe)
            # Use per-pair dijkstra_path (stops at target) — much cheaper than
            # single_source (which computes paths to all ~3k nodes per source).
            n_pts = len(node_ids)
            n_pairs = n_pts * (n_pts - 1)
            self.status_update.emit(f"Đang tính đường đi chi tiết ({n_pairs} cặp)…")
            road_paths: dict[tuple[int, int], list[tuple[float, float]]] = {}
            try:
                for _i in range(n_pts):
                    for _j in range(n_pts):
                        if _i == _j:
                            continue
                        try:
                            _path = nx.dijkstra_path(
                                graph, node_ids[_i], node_ids[_j], weight="weight"
                            )
                            road_paths[(_i, _j)] = [
                                (graph.nodes[_n]["x"], graph.nodes[_n]["y"])
                                for _n in _path
                            ]
                        except (nx.NetworkXNoPath, nx.NodeNotFound):
                            road_paths[(_i, _j)] = [coords[_i], coords[_j]]
            except Exception:  # noqa: BLE001
                road_paths = {}  # fallback to straight lines in canvas

            self.status_update.emit("Sẵn sàng.")
            # ── Generate demands / time windows if needed ─────────────────────
            demands: np.ndarray | None = None
            time_windows: np.ndarray | None = None
            service_times: np.ndarray | None = None

            if self._problem_type in ("vrp", "vrptw"):
                rng_dem = random.Random(self._demand_seed)
                demands = np.array(
                    [round(rng_dem.uniform(1.0, self._max_demand), 1)
                     for _ in range(self._n_customers)],
                    dtype=np.float64,
                )
                # Feasibility guard
                total_demand = float(demands.sum())
                min_cap = total_demand / max(1, self._n_vehicles)
                if self._vehicle_capacity < min_cap:
                    self._vehicle_capacity = float(np.ceil(min_cap))

            if self._problem_type == "vrptw":
                speed_mps = max(self._vehicle_speed_kmph / 3.6, 1e-9)
                rng_tw = random.Random(self._tw_seed)
                half = self._tw_width_s / 2.0
                time_windows = np.zeros((self._n_customers, 2), dtype=np.float64)
                service_times = np.zeros(self._n_customers, dtype=np.float64)
                for k in range(self._n_customers):
                    d_depot = float(dist_matrix[0, k + 1])
                    natural_s = d_depot / speed_mps if np.isfinite(d_depot) else 3600.0
                    time_windows[k, 0] = max(0.0, natural_s - half)
                    time_windows[k, 1] = natural_s + half
                    service_times[k] = round(rng_tw.uniform(0.0, self._service_time_max_s), 1)

            self.graph_loaded.emit(
                {
                    "graph": graph,
                    "dist_matrix": dist_matrix,
                    "node_ids": node_ids,
                    "coords": coords,  # list[(lon, lat)]
                    "road_paths": road_paths,
                    "demands": demands,
                    "time_windows": time_windows,
                    "service_times": service_times,
                    "vehicle_capacity": self._vehicle_capacity,
                }
            )

        except Exception as exc:  # noqa: BLE001
            self.error_occurred.emit(str(exc))


# ─── PlacementLoadWorker — load graph + SCC only (no node picking) ───────────

class _PlacementLoadWorker(QThread if _QT else object):  # type: ignore[misc]
    """Background thread: load graph and extract SCC info for manual node placement."""

    status_update = Signal(str)
    scc_ready = Signal(dict)   # graph, scc_osm_ids, scc_lonlats
    error_occurred = Signal(str)

    def __init__(
        self,
        bbox_name: str,
        network_type: str = "driving",
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._bbox_name = bbox_name
        self._network_type = network_type

    def run(self) -> None:
        try:
            pbf_path = str(_PBF_FILE)
            bbox: BBox = KNOWN_BBOXES[self._bbox_name]
            cache_path = str(
                _CACHE_DIR / f"{self._bbox_name}_{self._network_type}.pkl"
            )
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)

            if not Path(cache_path).exists() and not _PBF_FILE.exists():
                self.error_occurred.emit(
                    f"Không tìm thấy cache hoặc file .pbf:\n{_PBF_FILE}\n"
                    "Hãy đặt file vietnam-260413.osm.pbf vào thư mục module."
                )
                return

            self.status_update.emit(
                f"Đang tải đồ thị {self._bbox_name} ({self._network_type})…"
            )
            import networkx as nx  # noqa: PLC0415
            graph: nx.DiGraph = load_or_build(
                pbf_path, cache_path,
                network_type=self._network_type, bbox=bbox,
            )

            self.status_update.emit("Đang phân tích thành phần liên thông…")
            scc_nodes = max(nx.strongly_connected_components(graph), key=len)
            scc_osm_ids = list(scc_nodes)
            scc_lonlats = [
                (graph.nodes[n]["x"], graph.nodes[n]["y"])
                for n in scc_osm_ids
            ]
            n_scc = len(scc_osm_ids)
            self.status_update.emit(
                f"Sẵn sàng — {n_scc:,} điểm có thể chọn. Nhấp trên bản đồ để đặt điểm."
            )
            self.scc_ready.emit({
                "graph": graph,
                "scc_osm_ids": scc_osm_ids,
                "scc_lonlats": scc_lonlats,
            })
        except Exception as exc:  # noqa: BLE001
            self.error_occurred.emit(str(exc))


# ─── MatrixWorker — build dist_matrix + road_paths from manually chosen nodes ─

class _MatrixWorker(QThread if _QT else object):  # type: ignore[misc]
    """Background thread: compute dist_matrix + road_paths for a given node list."""

    status_update = Signal(str)
    graph_loaded = Signal(dict)   # same payload format as _LoadWorker
    error_occurred = Signal(str)

    def __init__(
        self,
        graph: Any,
        node_ids: list,
        problem_type: str = "tsp",
        n_vehicles: int = 3,
        vehicle_capacity: float = 50.0,
        demand_seed: int = 7,
        max_demand: float = 15.0,
        tw_seed: int = 13,
        tw_width_s: float = 1800.0,
        service_time_max_s: float = 300.0,
        vehicle_speed_kmph: float = 30.0,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._graph = graph
        self._node_ids = node_ids        # OSM IDs, index 0 = depot, rest = customers
        self._problem_type = problem_type
        self._n_vehicles = n_vehicles
        self._vehicle_capacity = vehicle_capacity
        self._demand_seed = demand_seed
        self._max_demand = max_demand
        self._tw_seed = tw_seed
        self._tw_width_s = tw_width_s
        self._service_time_max_s = service_time_max_s
        self._vehicle_speed_kmph = vehicle_speed_kmph

    def run(self) -> None:
        try:
            import networkx as nx  # noqa: PLC0415
            graph = self._graph
            node_ids = self._node_ids
            n_customers = len(node_ids) - 1

            self.status_update.emit(
                f"Đang tính ma trận khoảng cách ({n_customers + 1}×{n_customers + 1})…"
            )
            dist_matrix = build_matrix(graph, node_ids)

            coords = [
                (graph.nodes[n]["x"], graph.nodes[n]["y"])
                for n in node_ids
            ]

            n_pts = len(node_ids)
            n_pairs = n_pts * (n_pts - 1)
            self.status_update.emit(f"Đang tính đường đi chi tiết ({n_pairs} cặp)…")
            road_paths: dict[tuple[int, int], list[tuple[float, float]]] = {}
            try:
                for _i in range(n_pts):
                    for _j in range(n_pts):
                        if _i == _j:
                            continue
                        try:
                            _path = nx.dijkstra_path(
                                graph, node_ids[_i], node_ids[_j], weight="weight"
                            )
                            road_paths[(_i, _j)] = [
                                (graph.nodes[_n]["x"], graph.nodes[_n]["y"])
                                for _n in _path
                            ]
                        except (nx.NetworkXNoPath, nx.NodeNotFound):
                            road_paths[(_i, _j)] = [coords[_i], coords[_j]]
            except Exception:  # noqa: BLE001
                road_paths = {}

            # Generate demands / time windows
            demands: np.ndarray | None = None
            time_windows: np.ndarray | None = None
            service_times: np.ndarray | None = None

            if self._problem_type in ("vrp", "vrptw"):
                rng_dem = random.Random(self._demand_seed)
                demands = np.array(
                    [round(rng_dem.uniform(1.0, self._max_demand), 1)
                     for _ in range(n_customers)],
                    dtype=np.float64,
                )
                total_demand = float(demands.sum())
                min_cap = total_demand / max(1, self._n_vehicles)
                if self._vehicle_capacity < min_cap:
                    self._vehicle_capacity = float(np.ceil(min_cap))

            if self._problem_type == "vrptw":
                speed_mps = max(self._vehicle_speed_kmph / 3.6, 1e-9)
                rng_tw = random.Random(self._tw_seed)
                half = self._tw_width_s / 2.0
                time_windows = np.zeros((n_customers, 2), dtype=np.float64)
                service_times = np.zeros(n_customers, dtype=np.float64)
                for k in range(n_customers):
                    d_depot = float(dist_matrix[0, k + 1])
                    natural_s = d_depot / speed_mps if np.isfinite(d_depot) else 3600.0
                    time_windows[k, 0] = max(0.0, natural_s - half)
                    time_windows[k, 1] = natural_s + half
                    service_times[k] = round(rng_tw.uniform(0.0, self._service_time_max_s), 1)

            self.status_update.emit("Sẵn sàng.")
            self.graph_loaded.emit({
                "graph": graph,
                "dist_matrix": dist_matrix,
                "node_ids": node_ids,
                "coords": coords,
                "road_paths": road_paths,
                "demands": demands,
                "time_windows": time_windows,
                "service_times": service_times,
                "vehicle_capacity": self._vehicle_capacity,
            })
        except Exception as exc:  # noqa: BLE001
            self.error_occurred.emit(str(exc))


# ─── Canvas: road network + route map ────────────────────────────────────────

class _MapCanvas(_WidgetBase):  # type: ignore[valid-type]
    """Matplotlib canvas: draws road network edges + depot/customers + TSP route."""

    # Emitted on every click in placement mode
    placement_changed = Signal(object)  # {"depot_node_id": int|None, "customer_node_ids": [int,...]}

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        if not _QT:
            return
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if _MPL:
            self._fig = Figure(figsize=(8, 7), dpi=100)
            self._ax = self._fig.add_subplot(111)
            self._canvas = FigureCanvas(self._fig)
            self._canvas.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            layout.addWidget(self._canvas)
            self._route_artists: list = []
            self._depot_coord: tuple[float, float] | None = None
            self._customer_coords: list[tuple[float, float]] = []
            self._all_coords: list[tuple[float, float]] = []  # [depot] + customers
            self._road_paths: dict = {}
            self._ready: bool = False
            # ── Placement mode state ─────────────────────────────────────
            self._placement_mode: bool = False
            self._scc_lons: Any = None   # np.ndarray shape (N,)
            self._scc_lats: Any = None   # np.ndarray shape (N,)
            self._scc_osm_ids: list = []
            self._placed_depot_scc_idx: int | None = None    # index into _scc_osm_ids
            self._placed_customer_scc_idxs: list[int] = []  # indices into _scc_osm_ids
            self._placement_fg_artists: list = []            # depot + customer markers
            self._click_cid: int | None = None
        else:
            layout.addWidget(
                QLabel("⚠ matplotlib chưa cài. Chạy: pip install matplotlib")
            )

    def setup(
        self,
        graph: Any,
        depot_coord: tuple[float, float],
        customer_coords: list[tuple[float, float]],
        problem_type: str = "tsp",
        road_paths: dict | None = None,
    ) -> None:
        """Draw static background (road edges + depot + customers). UI thread only."""
        if not _MPL:
            return

        self._depot_coord = depot_coord
        self._customer_coords = customer_coords
        self._all_coords = [depot_coord] + list(customer_coords)  # 0=depot, 1..n=customers
        self._road_paths = road_paths or {}
        self._route_artists = []
        ax = self._ax
        ax.clear()

        # ── Road network edges via LineCollection ─────────────────────────────
        segs = []
        for u, v in graph.edges():
            try:
                x1, y1 = graph.nodes[u]["x"], graph.nodes[u]["y"]
                x2, y2 = graph.nodes[v]["x"], graph.nodes[v]["y"]
                segs.append([(x1, y1), (x2, y2)])
            except KeyError:
                continue
        if segs:
            lc = LineCollection(
                segs, colors=_COLOR_ROAD, linewidths=0.35, zorder=1, alpha=0.7
            )
            ax.add_collection(lc, autolim=False)  # prevent autoscale override

        # Compute bounds
        lons = [c[0] for c in customer_coords] + [depot_coord[0]]
        lats = [c[1] for c in customer_coords] + [depot_coord[1]]
        lon_min, lon_max = min(lons), max(lons)
        lat_min, lat_max = min(lats), max(lats)
        dlon = max((lon_max - lon_min) * 0.15, 0.003)
        dlat = max((lat_max - lat_min) * 0.15, 0.003)
        ax.set_xlim(lon_min - dlon, lon_max + dlon)
        ax.set_ylim(lat_min - dlat, lat_max + dlat)

        # ── Customer circles ────────────────────────────────────────────────
        r = max(dlon, dlat) * 0.06   # larger so circles are clearly visible
        for idx, (lon, lat) in enumerate(customer_coords):
            circ = Circle(
                (lon, lat), radius=r,
                facecolor=_COLOR_CUSTOMER, edgecolor="white",
                linewidth=0.8, zorder=5,
            )
            ax.add_patch(circ)
            ax.text(
                lon, lat, str(idx + 1),
                ha="center", va="center",
                fontsize=7, fontweight="bold", color="white", zorder=6,
            )

        # ── Depot square (Rectangle, no pad so it stays data-sized) ────────
        dr = r * 1.4
        from matplotlib.patches import Rectangle as _Rect  # noqa: PLC0415
        depot_patch = _Rect(
            (depot_coord[0] - dr, depot_coord[1] - dr), 2 * dr, 2 * dr,
            facecolor=_COLOR_DEPOT, edgecolor="white",
            linewidth=1.5, zorder=6,
        )
        ax.add_patch(depot_patch)
        ax.text(
            depot_coord[0], depot_coord[1], "D",
            ha="center", va="center",
            fontsize=8, fontweight="bold", color="white", zorder=7,
        )

        ax.set_xlabel("Kinh độ", fontsize=9)
        ax.set_ylabel("Vĩ độ", fontsize=9)
        _titles = {"tsp": "Bản đồ tuyến đường TSP", "vrp": "Bản đồ tuyến đường VRP",
                   "vrptw": "Bản đồ tuyến đường VRPTW"}
        ax.set_title(_titles.get(problem_type, "Bản đồ tuyến đường"), fontsize=10)
        ax.set_facecolor("#F4F6F8")
        self._fig.patch.set_facecolor("#F4F6F8")
        self._fig.tight_layout(pad=0.8)
        self._canvas.draw()
        self._ready = True

    def update_route(
        self,
        perm: list[int],
        gbest_fitness: float,
        iteration: int,
    ) -> None:
        """Refresh TSP tour polyline. Uses draw_idle() for low overhead."""
        if not _MPL or not self._ready:
            return

        for a in self._route_artists:
            try:
                a.remove()
            except Exception:  # noqa: BLE001
                pass
        self._route_artists = []

        if perm and self._depot_coord:
            # Build road-following polyline: index 0=depot, i+1=customer i (0-based)
            seq = [0] + [i + 1 for i in perm] + [0]
            xs: list[float] = []
            ys: list[float] = []
            for k in range(len(seq) - 1):
                a, b = seq[k], seq[k + 1]
                seg = self._road_paths.get((a, b))
                if seg:
                    xs.extend(c[0] for c in seg)
                    ys.extend(c[1] for c in seg)
                else:
                    xs.extend([self._all_coords[a][0], self._all_coords[b][0]])
                    ys.extend([self._all_coords[a][1], self._all_coords[b][1]])
            (line,) = self._ax.plot(
                xs, ys,
                color=_COLOR_BEST_ROUTE, lw=1.8, alpha=0.9, zorder=4,
                solid_capstyle="round", solid_joinstyle="round",
            )
            self._route_artists.append(line)

        km = gbest_fitness / 1000.0
        self._ax.set_title(
            f"TSP — Vòng {iteration}  |  gBest = {km:.3f} km",
            fontsize=10,
        )
        self._canvas.draw_idle()

    def update_vrp_route(
        self,
        routes: list[list[int]],
        gbest_fitness: float,
        iteration: int,
        problem_type: str = "vrp",
        n_vehicles_cfg: int = 0,
    ) -> None:
        """Refresh multi-vehicle route polylines (VRP / VRPTW). draw_idle() for low overhead."""
        if not _MPL or not self._ready:
            return

        for a in self._route_artists:
            try:
                a.remove()
            except Exception:  # noqa: BLE001
                pass
        self._route_artists = []

        if self._depot_coord:
            for v_idx, route in enumerate(routes):
                if not route:
                    continue
                color = _VRP_COLORS[v_idx % len(_VRP_COLORS)]
                seq = [0] + [i + 1 for i in route] + [0]
                xs: list[float] = []
                ys: list[float] = []
                for k in range(len(seq) - 1):
                    a, b = seq[k], seq[k + 1]
                    seg = self._road_paths.get((a, b))
                    if seg:
                        xs.extend(c[0] for c in seg)
                        ys.extend(c[1] for c in seg)
                    else:
                        xs.extend([self._all_coords[a][0], self._all_coords[b][0]])
                        ys.extend([self._all_coords[a][1], self._all_coords[b][1]])
                (line,) = self._ax.plot(
                    xs, ys,
                    color=color, lw=1.6, alpha=0.85, zorder=4,
                    solid_capstyle="round", solid_joinstyle="round",
                )
                self._route_artists.append(line)

        lbl = problem_type.upper()
        km = gbest_fitness / 1000.0
        n_v = len(routes)
        over = n_vehicles_cfg > 0 and n_v > n_vehicles_cfg
        xe_str = f"{n_v} xe"
        if over:
            xe_str = f"⚠ {n_v} xe (vượt {n_vehicles_cfg} cấu hình)"
        self._ax.set_title(
            f"{lbl} — Vòng {iteration}  |  gBest = {km:.3f} km  ({xe_str})",
            fontsize=10,
        )
        self._canvas.draw_idle()

    # ── Placement mode ────────────────────────────────────────────────────────

    def setup_road_only(
        self,
        graph: Any,
        scc_lonlats: list[tuple[float, float]],
        scc_osm_ids: list,
    ) -> None:
        """Draw road network + all SCC nodes as clickable dots. Enters placement mode."""
        if not _MPL or not _QT:
            return

        # Reset placement state
        self._placed_depot_scc_idx = None
        self._placed_customer_scc_idxs = []
        self._placement_fg_artists = []
        self._scc_osm_ids = scc_osm_ids

        # Build numpy arrays for fast nearest-neighbour lookup
        lons = [c[0] for c in scc_lonlats]
        lats = [c[1] for c in scc_lonlats]
        self._scc_lons = np.array(lons)
        self._scc_lats = np.array(lats)

        ax = self._ax
        ax.clear()
        self._route_artists = []
        self._ready = False

        # Road edges
        segs = []
        for u, v in graph.edges():
            try:
                segs.append([(graph.nodes[u]["x"], graph.nodes[u]["y"]),
                              (graph.nodes[v]["x"], graph.nodes[v]["y"])])
            except KeyError:
                continue
        if segs:
            from matplotlib.collections import LineCollection as _LC  # noqa: PLC0415
            lc = _LC(segs, colors=_COLOR_ROAD, linewidths=0.35, zorder=1, alpha=0.7)
            ax.add_collection(lc, autolim=False)

        # SCC nodes as tiny interactive dots (drawn once, never redrawn on click)
        ax.scatter(
            lons, lats,
            s=4, c="#A0AEC0", alpha=0.5, zorder=2, linewidths=0,
        )

        # Axis limits from SCC extent
        dlon = max((max(lons) - min(lons)) * 0.05, 0.003)
        dlat = max((max(lats) - min(lats)) * 0.05, 0.003)
        ax.set_xlim(min(lons) - dlon, max(lons) + dlon)
        ax.set_ylim(min(lats) - dlat, max(lats) + dlat)

        ax.set_xlabel("Kinh độ", fontsize=9)
        ax.set_ylabel("Vĩ độ", fontsize=9)
        ax.set_title(
            "Chế độ thủ công — Nhấp trái: Điểm giao | Nhấp phải: Depot",
            fontsize=10,
        )
        ax.set_facecolor("#F4F6F8")
        self._fig.patch.set_facecolor("#F4F6F8")
        self._fig.tight_layout(pad=0.8)
        self._canvas.draw()

        # Connect click event
        if self._click_cid is not None:
            self._canvas.mpl_disconnect(self._click_cid)
        self._click_cid = self._canvas.mpl_connect(
            "button_press_event", self._on_mpl_click
        )
        self._placement_mode = True

    def _on_mpl_click(self, event: Any) -> None:  # noqa: C901
        """Handle matplotlib click in placement mode."""
        if not self._placement_mode:
            return
        if event.inaxes != self._ax:
            return
        if event.xdata is None or event.ydata is None:
            return

        # Find nearest SCC node
        d2 = (self._scc_lons - event.xdata) ** 2 + (self._scc_lats - event.ydata) ** 2
        nearest = int(np.argmin(d2))

        if event.button == 3:  # Right-click → set/move depot
            if self._placed_depot_scc_idx == nearest:
                # Deselect depot
                self._placed_depot_scc_idx = None
            else:
                # If this node was a customer, remove it first
                if nearest in self._placed_customer_scc_idxs:
                    self._placed_customer_scc_idxs.remove(nearest)
                self._placed_depot_scc_idx = nearest

        else:  # Left-click → toggle customer / set depot if none
            if nearest == self._placed_depot_scc_idx:
                self._placed_depot_scc_idx = None  # deselect depot
            elif nearest in self._placed_customer_scc_idxs:
                self._placed_customer_scc_idxs.remove(nearest)  # deselect customer
            else:
                if self._placed_depot_scc_idx is None:
                    # No depot yet — first click becomes depot
                    self._placed_depot_scc_idx = nearest
                else:
                    self._placed_customer_scc_idxs.append(nearest)

        self._redraw_placement_markers()
        self.placement_changed.emit(self.get_placement_state())

    def _redraw_placement_markers(self) -> None:
        """Remove and redraw depot + customer markers (fast, no road redraw)."""
        if not _MPL:
            return
        for a in self._placement_fg_artists:
            try:
                a.remove()
            except Exception:  # noqa: BLE001
                pass
        self._placement_fg_artists = []

        ax = self._ax
        # Draw customers
        for seq_idx, scc_idx in enumerate(self._placed_customer_scc_idxs):
            lon = float(self._scc_lons[scc_idx])
            lat = float(self._scc_lats[scc_idx])
            from matplotlib.patches import Circle as _C  # noqa: PLC0415
            circ = _C(
                (lon, lat), radius=0.0003,
                facecolor=_COLOR_CUSTOMER, edgecolor="white",
                linewidth=0.8, zorder=6,
            )
            ax.add_patch(circ)
            txt = ax.text(
                lon, lat, str(seq_idx + 1),
                ha="center", va="center",
                fontsize=7, fontweight="bold", color="white", zorder=7,
            )
            self._placement_fg_artists.extend([circ, txt])

        # Draw depot
        if self._placed_depot_scc_idx is not None:
            lon = float(self._scc_lons[self._placed_depot_scc_idx])
            lat = float(self._scc_lats[self._placed_depot_scc_idx])
            from matplotlib.patches import Rectangle as _Rect  # noqa: PLC0415
            dr = 0.0004
            rect = _Rect(
                (lon - dr, lat - dr), 2 * dr, 2 * dr,
                facecolor=_COLOR_DEPOT, edgecolor="white",
                linewidth=1.5, zorder=6,
            )
            ax.add_patch(rect)
            txt = ax.text(
                lon, lat, "D",
                ha="center", va="center",
                fontsize=8, fontweight="bold", color="white", zorder=7,
            )
            self._placement_fg_artists.extend([rect, txt])

        self._canvas.draw_idle()

    def clear_placement(self) -> None:
        """Reset all placed nodes (keep road background)."""
        self._placed_depot_scc_idx = None
        self._placed_customer_scc_idxs = []
        self._redraw_placement_markers()
        self.placement_changed.emit(self.get_placement_state())

    def get_placement_state(self) -> dict:
        """Return current placement as {depot_node_id, customer_node_ids}."""
        depot_id = (
            self._scc_osm_ids[self._placed_depot_scc_idx]
            if self._placed_depot_scc_idx is not None
            else None
        )
        customer_ids = [self._scc_osm_ids[i] for i in self._placed_customer_scc_idxs]
        return {"depot_node_id": depot_id, "customer_node_ids": customer_ids}

    def exit_placement_mode(self) -> None:
        """Disconnect click handler and clear placement visuals."""
        if self._click_cid is not None:
            try:
                self._canvas.mpl_disconnect(self._click_cid)
            except Exception:  # noqa: BLE001
                pass
            self._click_cid = None
        self._placement_mode = False
        self._placed_depot_scc_idx = None
        self._placed_customer_scc_idxs = []
        self._placement_fg_artists = []
        if _MPL and self._ax is not None:
            self._ax.clear()
            self._ax.set_title("Bản đồ Tuyến đường", fontsize=10)
            self._ax.set_facecolor("#F4F6F8")
            self._canvas.draw_idle()

    # ─────────────────────────────────────────────────────────────────────────

    def get_figure_bytes(self) -> bytes:
        if not _MPL:
            return b""
        buf = io.BytesIO()
        self._fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
        return buf.getvalue()


# ─── Canvas: convergence chart ────────────────────────────────────────────────

class _ConvergenceCanvas(_WidgetBase):  # type: ignore[valid-type]

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
                QLabel("⚠ matplotlib chưa cài. Chạy: pip install matplotlib")
            )

    def reset(self, problem_type: str = "tsp") -> None:
        if not _MPL:
            return
        self._history = []
        self._problem_type = problem_type
        self._ax.clear()
        self._ax.set_xlabel("Vòng lặp", fontsize=9)
        self._ax.set_ylabel("gBest (m)", fontsize=9)
        self._ax.set_title(f"Đồ thị hội tụ PSO — {problem_type.upper()}", fontsize=10)
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
        if not _MPL:
            return
        pt = getattr(self, "_problem_type", "tsp")
        self._ax.clear()
        if self._history:
            x = list(range(len(self._history)))
            self._ax.plot(x, self._history, color="#2471A3", lw=1.6)
            self._ax.fill_between(x, self._history, alpha=0.10, color="#2471A3")
            self._ax.set_title(
                f"Hội tụ PSO ({pt.upper()})  |  gBest = {self._history[-1]/1000:.3f} km",
                fontsize=10,
            )
        else:
            self._ax.set_title(f"Đồ thị hội tụ PSO — {pt.upper()}", fontsize=10)
        self._ax.set_xlabel("Vòng lặp", fontsize=9)
        self._ax.set_ylabel("gBest (m)", fontsize=9)
        self._ax.grid(True, alpha=0.3)
        self._fig.tight_layout(pad=1.0)
        self._canvas.draw_idle()

    def get_figure_bytes(self) -> bytes:
        if not _MPL:
            return b""
        buf = io.BytesIO()
        self._fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
        return buf.getvalue()


# ─── Main view widget ─────────────────────────────────────────────────────────

class _MapView(_WidgetBase):  # type: ignore[valid-type]
    """Root QWidget for the PSO Logistics Map module."""

    def __init__(self, module: "PSOLogisticsMapModule") -> None:
        super().__init__()
        if not _QT:
            return
        self._module = module
        self._worker: SimulationWorker | None = None
        self._load_worker: _LoadWorker | None = None
        self._placement_worker: _PlacementLoadWorker | None = None
        self._matrix_worker: _MatrixWorker | None = None
        self._scc_graph: Any = None  # graph held between scc_ready and confirm
        self._scc_graph_osm_ids: list = []  # full SCC node list (kept for reference)
        self._sim_running: bool = False
        self._graph_ready: bool = False
        # Loaded graph data
        self._graph: Any = None
        self._dist_matrix: np.ndarray | None = None
        self._node_ids: list = []
        self._coords: list[tuple[float, float]] = []  # [(lon, lat)]
        # VRP/VRPTW data (None for TSP)
        self._demands: np.ndarray | None = None
        self._time_windows: np.ndarray | None = None
        self._service_times: np.ndarray | None = None
        self._loaded_vehicle_capacity: float = 50.0
        # Current problem type (tracked for canvas update branching)
        self._current_problem_type: str = "tsp"
        self._current_vehicle_capacity: float = 50.0
        # History
        self._best_route_history: list[dict] = []
        self._last_result: dict | None = None
        self._total_iters: int = 100
        # Replay
        self._replay_idx: int = 0
        self._replay_timer = QTimer()
        self._replay_timer.timeout.connect(self._on_replay_tick)
        # Canvas refs
        self._map_canvas: _MapCanvas | None = None
        self._convergence_canvas: _ConvergenceCanvas | None = None
        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(8)

        _CSS_NO_ARROWS = (
            "QSpinBox::up-button, QSpinBox::down-button,"
            "QDoubleSpinBox::up-button, QDoubleSpinBox::down-button"
            "{ width:0;height:0;border:none;image:none; }"
            "QSpinBox, QDoubleSpinBox { padding-right:3px; }"
        )

        left_widget = QWidget()
        left_widget.setFixedWidth(_CTRL_WIDTH)
        left_widget.setStyleSheet(_CSS_NO_ARROWS)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.setSpacing(4)

        self._ctrl_tabs = QTabWidget()
        self._ctrl_tabs.setDocumentMode(True)
        _tab_map = QWidget()
        _tab_pso = QWidget()
        _tl_map = QVBoxLayout(_tab_map)
        _tl_map.setContentsMargins(4, 4, 4, 4)
        _tl_map.setSpacing(4)
        _tl_pso = QVBoxLayout(_tab_pso)
        _tl_pso.setContentsMargins(4, 4, 4, 4)
        _tl_pso.setSpacing(4)
        self._ctrl_tabs.addTab(_tab_map, "Bản đồ")
        self._ctrl_tabs.addTab(_tab_pso, "PSO")
        left_layout.addWidget(self._ctrl_tabs)

        def _lrow(lbl: str, w: QWidget, lbl_w: int = 130) -> QHBoxLayout:
            row = QHBoxLayout()
            lb = QLabel(lbl)
            lb.setMinimumWidth(lbl_w)
            row.addWidget(lb)
            row.addWidget(w)
            return row

        # ── Group: Bản đồ / Vùng ─────────────────────────────────────────────
        grp_map = QGroupBox("Vùng bản đồ")
        gm = QVBoxLayout(grp_map)
        gm.setSpacing(4)

        self._combo_bbox = QComboBox()
        for name in KNOWN_BBOXES:
            self._combo_bbox.addItem(name, name)
        gm.addLayout(_lrow("Khu vực:", self._combo_bbox))

        self._combo_net_type = QComboBox()
        self._combo_net_type.addItem("Lái xe (driving)", "driving")
        self._combo_net_type.addItem("Đi bộ (walking)", "walking")
        self._combo_net_type.addItem("Xe đạp (cycling)", "cycling")
        gm.addLayout(_lrow("Loại đường:", self._combo_net_type))

        self._btn_load_graph = QPushButton("↺  Tải lại đồ thị")
        self._btn_load_graph.setToolTip(
            "Tải lại đồ thị từ file .pbf với vùng và loại đường đã chọn"
        )
        gm.addWidget(self._btn_load_graph)

        _tl_map.addWidget(grp_map)

        # ── Group: Bài toán ────────────────────────────────────────────────────
        grp_prob = QGroupBox("Bài toán")
        gp = QVBoxLayout(grp_prob)
        gp.setSpacing(4)

        self._combo_problem_type = QComboBox()
        self._combo_problem_type.addItem("TSP — 1 xe, không ràng buộc", "tsp")
        self._combo_problem_type.addItem("VRP — Nhiều xe, tải trọng", "vrp")
        self._combo_problem_type.addItem("VRPTW — VRP + Cửa sổ thời gian", "vrptw")
        gp.addLayout(_lrow("Loại bài toán:", self._combo_problem_type, lbl_w=110))

        self._spin_n_cust = QSpinBox()
        self._spin_n_cust.setRange(3, 50)
        self._spin_n_cust.setValue(10)
        self._spin_n_cust.setToolTip(
            "Số điểm giao (không tính depot). Thay đổi seed dữ liệu sẽ tạo bố cục khác."
        )
        gp.addLayout(_lrow("Số điểm giao:", self._spin_n_cust))

        # ── Input-mode selector (seed vs manual) ──────────────────────────────
        self._combo_input_mode = QComboBox()
        self._combo_input_mode.addItem("🎲 Ngẫu nhiên (Seed)", "seed")
        self._combo_input_mode.addItem("📍 Thủ công (Click bản đồ)", "manual")
        gp.addLayout(_lrow("Chế độ nhập:", self._combo_input_mode, lbl_w=110))

        # ── Seed row (hidden in manual mode) ──────────────────────────────────
        self._row_seed = QWidget()
        _seed_row_layout = QHBoxLayout(self._row_seed)
        _seed_row_layout.setContentsMargins(0, 0, 0, 0)
        _seed_lbl = QLabel("Seed dữ liệu:")
        _seed_lbl.setMinimumWidth(130)
        self._spin_data_seed = QSpinBox()
        self._spin_data_seed.setRange(1, 99999)
        self._spin_data_seed.setValue(42)
        self._spin_data_seed.setToolTip("Seed chọn ngẫu nhiên vị trí depot và điểm giao")
        _seed_row_layout.addWidget(_seed_lbl)
        _seed_row_layout.addWidget(self._spin_data_seed)
        gp.addWidget(self._row_seed)

        # ── Manual placement group (hidden until SCC loaded) ──────────────────
        self._grp_manual = QGroupBox("Chế độ Thủ công")
        _gm2 = QVBoxLayout(self._grp_manual)
        _gm2.setSpacing(4)
        self._lbl_placement_hint = QLabel(
            "Chuột trái: thêm điểm giao\n"
            "Chuột phải: đặt depot\n"
            "Click lại node đã chọn: bỏ chọn"
        )
        self._lbl_placement_hint.setWordWrap(True)
        _gm2.addWidget(self._lbl_placement_hint)
        self._lbl_placement_count = QLabel("Đã chọn: 0 depot, 0/0 điểm giao")
        _gm2.addWidget(self._lbl_placement_count)
        _manual_btn_row = QHBoxLayout()
        self._btn_manual_clear = QPushButton("✕ Xóa tất cả")
        self._btn_manual_clear.setEnabled(False)
        self._btn_manual_confirm = QPushButton("✓ Xác nhận")
        self._btn_manual_confirm.setEnabled(False)
        _manual_btn_row.addWidget(self._btn_manual_clear)
        _manual_btn_row.addWidget(self._btn_manual_confirm)
        _gm2.addLayout(_manual_btn_row)
        self._grp_manual.setVisible(False)
        gp.addWidget(self._grp_manual)

        _tl_map.addWidget(grp_prob)

        # ── Group: VRP (hiện khi vrp / vrptw) ─────────────────────────────────
        self._grp_vrp = QGroupBox("Xe & Tải trọng (VRP)")
        gv = QVBoxLayout(self._grp_vrp)
        gv.setSpacing(4)

        self._spin_n_vehicles = QSpinBox()
        self._spin_n_vehicles.setRange(1, 20)
        self._spin_n_vehicles.setValue(3)
        gv.addLayout(_lrow("Số xe:", self._spin_n_vehicles))

        self._spin_vehicle_cap = QDoubleSpinBox()
        self._spin_vehicle_cap.setRange(1.0, 9999.0)
        self._spin_vehicle_cap.setValue(50.0)
        self._spin_vehicle_cap.setDecimals(1)
        self._spin_vehicle_cap.setToolTip("Tải trọng tối đa mỗi xe (đơn vị demand)")
        gv.addLayout(_lrow("Tải trọng xe:", self._spin_vehicle_cap))

        self._spin_demand_seed = QSpinBox()
        self._spin_demand_seed.setRange(1, 99999)
        self._spin_demand_seed.setValue(7)
        gv.addLayout(_lrow("Seed demand:", self._spin_demand_seed))

        self._spin_max_demand = QDoubleSpinBox()
        self._spin_max_demand.setRange(0.1, 100.0)
        self._spin_max_demand.setValue(15.0)
        self._spin_max_demand.setDecimals(1)
        gv.addLayout(_lrow("Demand tối đa:", self._spin_max_demand))

        self._grp_vrp.setVisible(False)
        _tl_map.addWidget(self._grp_vrp)

        # ── Group: VRPTW (hiện khi vrptw only) ────────────────────────────────
        self._grp_vrptw = QGroupBox("Cửa sổ thời gian (VRPTW)")
        gt = QVBoxLayout(self._grp_vrptw)
        gt.setSpacing(4)

        self._spin_speed_kmph = QDoubleSpinBox()
        self._spin_speed_kmph.setRange(1.0, 200.0)
        self._spin_speed_kmph.setValue(30.0)
        self._spin_speed_kmph.setDecimals(1)
        self._spin_speed_kmph.setSuffix(" km/h")
        gt.addLayout(_lrow("Tốc độ xe:", self._spin_speed_kmph))

        self._spin_tw_seed = QSpinBox()
        self._spin_tw_seed.setRange(1, 99999)
        self._spin_tw_seed.setValue(13)
        gt.addLayout(_lrow("Seed TW:", self._spin_tw_seed))

        self._spin_tw_width_s = QDoubleSpinBox()
        self._spin_tw_width_s.setRange(60.0, 43200.0)
        self._spin_tw_width_s.setValue(1800.0)
        self._spin_tw_width_s.setDecimals(0)
        self._spin_tw_width_s.setSuffix(" s")
        self._spin_tw_width_s.setToolTip("Độ rộng cửa sổ thời gian (giây)")
        gt.addLayout(_lrow("Độ rộng TW:", self._spin_tw_width_s))

        self._spin_svc_time_s = QDoubleSpinBox()
        self._spin_svc_time_s.setRange(0.0, 3600.0)
        self._spin_svc_time_s.setValue(300.0)
        self._spin_svc_time_s.setDecimals(0)
        self._spin_svc_time_s.setSuffix(" s")
        self._spin_svc_time_s.setToolTip("Thời gian phục vụ tối đa mỗi điểm (giây)")
        gt.addLayout(_lrow("Svc time tối đa:", self._spin_svc_time_s))

        self._spin_tw_penalty = QDoubleSpinBox()
        self._spin_tw_penalty.setRange(0.01, 10000.0)
        self._spin_tw_penalty.setValue(10.0)
        self._spin_tw_penalty.setDecimals(2)
        self._spin_tw_penalty.setToolTip("Penalty mỗi giây đến muộn")
        gt.addLayout(_lrow("Penalty TW:", self._spin_tw_penalty))

        self._grp_vrptw.setVisible(False)
        _tl_map.addWidget(self._grp_vrptw)

        _tl_map.addStretch()

        # Wire: bbox / ncust / seed change → reload graph if already loaded
        self._combo_input_mode.currentIndexChanged.connect(self._on_input_mode_changed)
        self._combo_bbox.currentIndexChanged.connect(self._on_map_setting_changed)
        self._combo_net_type.currentIndexChanged.connect(self._on_map_setting_changed)
        self._combo_problem_type.currentIndexChanged.connect(self._on_problem_type_changed)
        self._spin_n_cust.valueChanged.connect(self._on_map_setting_changed)
        self._spin_data_seed.valueChanged.connect(self._on_map_setting_changed)
        self._spin_n_vehicles.valueChanged.connect(self._on_map_setting_changed)
        self._spin_vehicle_cap.valueChanged.connect(self._on_map_setting_changed)
        self._spin_demand_seed.valueChanged.connect(self._on_map_setting_changed)
        self._spin_max_demand.valueChanged.connect(self._on_map_setting_changed)
        self._spin_tw_seed.valueChanged.connect(self._on_map_setting_changed)
        self._spin_tw_width_s.valueChanged.connect(self._on_map_setting_changed)
        self._spin_svc_time_s.valueChanged.connect(self._on_map_setting_changed)
        self._spin_speed_kmph.valueChanged.connect(self._on_map_setting_changed)
        self._btn_load_graph.clicked.connect(self._on_load_graph)

        # Manual placement buttons
        self._btn_manual_clear.clicked.connect(self._on_manual_clear)
        self._btn_manual_confirm.clicked.connect(self._on_manual_confirm)

        # ── Group: PSO ────────────────────────────────────────────────────────
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
        g2.addLayout(_lrow("n_ops tối đa:", self._spin_ops))

        self._combo_topo = QComboBox()
        self._combo_topo.addItem("Star (toàn cục)", "star")
        self._combo_topo.addItem("Ring (láng giềng)", "ring")
        g2.addLayout(_lrow("Topology:", self._combo_topo))

        self._spin_pso_seed = QSpinBox()
        self._spin_pso_seed.setRange(0, 99999)
        self._spin_pso_seed.setValue(42)
        self._spin_pso_seed.setSpecialValueText("ngẫu nhiên")
        g2.addLayout(_lrow("Seed PSO:", self._spin_pso_seed))

        self._spin_delay = QSpinBox()
        self._spin_delay.setRange(0, 2000)
        self._spin_delay.setValue(_DEFAULT_DELAY_MS)
        self._spin_delay.setSingleStep(10)
        self._spin_delay.setSuffix(" ms")
        g2.addLayout(_lrow("Trễ / bước:", self._spin_delay))

        _tl_pso.addWidget(grp_pso)
        _tl_pso.addStretch()

        # ── Run / Stop ────────────────────────────────────────────────────────
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
        _btn_style_green = (
            "QPushButton{background:#27AE60;color:white;font-weight:bold;"
            "padding:4px 8px;border-radius:4px;}"
            "QPushButton:hover{background:#1E8449;}"
            "QPushButton:disabled{background:#BDC3C7;color:#7F8C8D;}"
        )

        btn_row = QHBoxLayout()
        self._btn_run = QPushButton("▶  Chạy")
        self._btn_run.setStyleSheet(_btn_style_run)
        self._btn_run.setEnabled(False)
        self._btn_stop = QPushButton("■  Dừng")
        self._btn_stop.setStyleSheet(_btn_style_stop)
        self._btn_stop.setEnabled(False)
        btn_row.addWidget(self._btn_run)
        btn_row.addWidget(self._btn_stop)
        left_layout.addLayout(btn_row)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        left_layout.addWidget(self._progress)

        # ── Replay ────────────────────────────────────────────────────────────
        replay_row = QHBoxLayout()
        self._btn_replay = QPushButton("⏯  Phát lại")
        self._btn_replay.setStyleSheet(_btn_style_green)
        self._btn_replay.setEnabled(False)
        self._btn_replay_stop = QPushButton("■")
        self._btn_replay_stop.setStyleSheet(_btn_style_stop)
        self._btn_replay_stop.setEnabled(False)
        self._btn_replay_stop.setMaximumWidth(32)
        self._spin_replay_speed = QSpinBox()
        self._spin_replay_speed.setRange(50, 2000)
        self._spin_replay_speed.setValue(_DEFAULT_REPLAY_MS)
        self._spin_replay_speed.setSingleStep(50)
        self._spin_replay_speed.setSuffix(" ms")
        self._spin_replay_speed.setMaximumWidth(80)
        replay_row.addWidget(self._btn_replay)
        replay_row.addWidget(self._btn_replay_stop)
        replay_row.addWidget(self._spin_replay_speed)
        left_layout.addLayout(replay_row)

        # ── Export ────────────────────────────────────────────────────────────
        export_row = QHBoxLayout()
        self._btn_export_map = QPushButton("📷 Bản đồ")
        self._btn_export_map.setEnabled(False)
        self._btn_export_conv = QPushButton("📷 Hội tụ")
        self._btn_export_conv.setEnabled(False)
        self._btn_export_route = QPushButton("📋 Tuyến")
        self._btn_export_route.setEnabled(False)
        self._btn_export_route.setToolTip("Xuất tuyến đường tối ưu ra file CSV")
        export_row.addWidget(self._btn_export_map)
        export_row.addWidget(self._btn_export_conv)
        export_row.addWidget(self._btn_export_route)
        left_layout.addLayout(export_row)

        # ── Result panel ────────────────────────────────────────────────────
        grp_res = QGroupBox("Kết quả")
        gr = QVBoxLayout(grp_res)
        gr.setSpacing(3)

        self._lbl_status = QLabel("Trạng thái: Chờ tải đồ thị")
        self._lbl_status.setStyleSheet(_MONO_STYLE + " color:#7F8C8D;")
        self._lbl_status.setWordWrap(True)

        self._lbl_fitness = QLabel("gBest quãng đường: —")
        self._lbl_fitness.setStyleSheet(_MONO_STYLE)

        self._lbl_route = QLabel("Tuyến tốt nhất: —")
        self._lbl_route.setStyleSheet(_MONO_STYLE)
        self._lbl_route.setWordWrap(True)
        self._lbl_route.setTextFormat(Qt.TextFormat.RichText)

        self._lbl_iters = QLabel("Vòng lặp: —")
        self._lbl_iters.setStyleSheet(_MONO_STYLE)

        for w in (self._lbl_status, self._lbl_fitness, self._lbl_route, self._lbl_iters):
            gr.addWidget(w)

        left_layout.addWidget(grp_res, stretch=1)

        # Remove spinbox arrows
        for _sb in left_widget.findChildren(QAbstractSpinBox):
            _sb.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)

        root_layout.addWidget(left_widget)

        # ── Right: tabs ───────────────────────────────────────────────────────
        self._tabs = QTabWidget()
        self._tabs.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._map_canvas = _MapCanvas()
        self._tabs.addTab(self._map_canvas, "Bản đồ Tuyến đường")

        self._convergence_canvas = _ConvergenceCanvas()
        self._convergence_canvas.reset()
        self._tabs.addTab(self._convergence_canvas, "Đồ thị Hội tụ")

        root_layout.addWidget(self._tabs, stretch=1)

        # ── Wire signals ──────────────────────────────────────────────────────
        self._btn_run.clicked.connect(self._on_run)
        self._btn_stop.clicked.connect(self._on_stop)
        self._btn_replay.clicked.connect(self._on_replay_start)
        self._btn_replay_stop.clicked.connect(self._on_replay_stop)
        self._btn_export_map.clicked.connect(self._on_export_map)
        self._btn_export_conv.clicked.connect(self._on_export_convergence)
        self._btn_export_route.clicked.connect(self._on_export_route)

        # Connect placement_changed after canvas is created
        self._map_canvas.placement_changed.connect(self._on_placement_changed)

    # ── Graph loading ─────────────────────────────────────────────────────────

    def start_load_graph(self) -> None:  # noqa: C901
        """Launch the appropriate worker based on input mode."""
        if self._sim_running:
            return
        if self._load_worker is not None and self._load_worker.isRunning():
            return
        if self._placement_worker is not None and self._placement_worker.isRunning():
            return
        if self._matrix_worker is not None and self._matrix_worker.isRunning():
            return

        manual_mode = self._combo_input_mode.currentData() == "manual"

        self._graph_ready = False
        self._btn_run.setEnabled(False)
        self._set_status("Đang tải đồ thị…", color="#E67E22")

        if manual_mode:
            # Clean up any previous placement state
            self._map_canvas.exit_placement_mode()
            self._grp_manual.setVisible(False)
            self._placement_worker = _PlacementLoadWorker(
                bbox_name=self._combo_bbox.currentData(),
                network_type=self._combo_net_type.currentData(),
            )
            self._placement_worker.status_update.connect(
                lambda msg: self._set_status(msg, color="#E67E22")
            )
            self._placement_worker.scc_ready.connect(self._on_scc_ready)
            self._placement_worker.error_occurred.connect(self._on_load_error)
            self._placement_worker.start()
        else:
            pt = self._combo_problem_type.currentData()
            self._load_worker = _LoadWorker(
                bbox_name=self._combo_bbox.currentData(),
                n_customers=self._spin_n_cust.value(),
                data_seed=self._spin_data_seed.value(),
                network_type=self._combo_net_type.currentData(),
                problem_type=pt,
                n_vehicles=self._spin_n_vehicles.value(),
                vehicle_capacity=self._spin_vehicle_cap.value(),
                demand_seed=self._spin_demand_seed.value(),
                max_demand=self._spin_max_demand.value(),
                tw_seed=self._spin_tw_seed.value(),
                tw_width_s=self._spin_tw_width_s.value(),
                service_time_max_s=self._spin_svc_time_s.value(),
                vehicle_speed_kmph=self._spin_speed_kmph.value(),
            )
            self._load_worker.status_update.connect(
                lambda msg: self._set_status(msg, color="#E67E22")
            )
            self._load_worker.graph_loaded.connect(self._on_graph_loaded)
            self._load_worker.error_occurred.connect(self._on_load_error)
            self._load_worker.start()

    def _on_load_graph(self) -> None:
        """Handler for the 'Tải lại đồ thị' button."""
        self.start_load_graph()

    def _on_input_mode_changed(self) -> None:
        """Show/hide seed row vs manual placement group on mode switch."""
        manual = self._combo_input_mode.currentData() == "manual"
        self._row_seed.setVisible(not manual)
        if not manual:
            # Switching to seed mode — discard any in-progress placement
            self._map_canvas.exit_placement_mode()
            self._grp_manual.setVisible(False)
            self._scc_graph = None
        # Mark graph stale so user presses Reload
        self._graph_ready = False
        self._btn_run.setEnabled(False)
        self._set_status(
            "Thay đổi chế độ — nhấn 'Tải lại đồ thị' để bắt đầu.", color="#7F8C8D"
        )

    def _on_scc_ready(self, payload: dict) -> None:
        """Graph loaded in manual mode — enter placement mode."""
        self._scc_graph = payload["graph"]
        self._scc_graph_osm_ids = payload["scc_osm_ids"]
        self._map_canvas.setup_road_only(
            payload["graph"],
            payload["scc_lonlats"],
            payload["scc_osm_ids"],
        )
        n_target = self._spin_n_cust.value()
        self._lbl_placement_count.setText(
            f"Đã chọn: 0 depot, 0/{n_target} điểm giao"
        )
        self._btn_manual_clear.setEnabled(False)
        self._btn_manual_confirm.setEnabled(False)
        self._grp_manual.setVisible(True)

    def _on_placement_changed(self, state: dict) -> None:
        """Update manual placement counter and enable/disable Confirm."""
        if self._combo_input_mode.currentData() != "manual":
            return
        depot_id = state.get("depot_node_id")
        customers = state.get("customer_node_ids", [])
        n_target = self._spin_n_cust.value()
        n_depot = 1 if depot_id is not None else 0
        n_cust = len(customers)
        self._lbl_placement_count.setText(
            f"Đã chọn: {n_depot} depot, {n_cust}/{n_target} điểm giao"
        )
        can_confirm = depot_id is not None and n_cust >= 1
        self._btn_manual_confirm.setEnabled(can_confirm)
        self._btn_manual_clear.setEnabled(n_depot > 0 or n_cust > 0)

    def _on_manual_clear(self) -> None:
        """Clear all manually placed nodes."""
        self._map_canvas.clear_placement()

    def _on_manual_confirm(self) -> None:
        """Compute dist_matrix + road_paths for the manually placed nodes."""
        if self._scc_graph is None:
            return
        state = self._map_canvas.get_placement_state()
        depot_id = state.get("depot_node_id")
        customers = state.get("customer_node_ids", [])
        if depot_id is None or not customers:
            return

        node_ids = [depot_id] + customers
        pt = self._combo_problem_type.currentData()
        self._matrix_worker = _MatrixWorker(
            graph=self._scc_graph,
            node_ids=node_ids,
            problem_type=pt,
            n_vehicles=self._spin_n_vehicles.value(),
            vehicle_capacity=self._spin_vehicle_cap.value(),
            demand_seed=self._spin_demand_seed.value(),
            max_demand=self._spin_max_demand.value(),
            tw_seed=self._spin_tw_seed.value(),
            tw_width_s=self._spin_tw_width_s.value(),
            service_time_max_s=self._spin_svc_time_s.value(),
            vehicle_speed_kmph=self._spin_speed_kmph.value(),
        )
        self._matrix_worker.status_update.connect(
            lambda msg: self._set_status(msg, color="#E67E22")
        )
        self._matrix_worker.graph_loaded.connect(self._on_graph_loaded)
        self._matrix_worker.error_occurred.connect(self._on_load_error)
        self._btn_manual_confirm.setEnabled(False)
        self._btn_manual_clear.setEnabled(False)
        self._set_status("Đang tính ma trận…", color="#E67E22")
        self._matrix_worker.start()

    def _on_map_setting_changed(self) -> None:
        """Mark graph as stale when bbox/ncust/seed changes."""
        if self._graph_ready:
            self._graph_ready = False
            self._btn_run.setEnabled(False)
            self._set_status("Thay đổi cấu hình — nhấn 'Tải lại đồ thị' để áp dụng.", color="#7F8C8D")

    def _on_problem_type_changed(self) -> None:
        """Show/hide VRP and VRPTW groups, mark graph stale."""
        pt = self._combo_problem_type.currentData()
        self._grp_vrp.setVisible(pt in ("vrp", "vrptw"))
        self._grp_vrptw.setVisible(pt == "vrptw")
        if self._graph_ready:
            self._graph_ready = False
            self._btn_run.setEnabled(False)
            self._set_status("Thay đổi loại bài toán — nhấn 'Tải lại đồ thị' để tạo lại dữ liệu.", color="#7F8C8D")

    def _on_graph_loaded(self, payload: dict) -> None:
        self._graph = payload["graph"]
        self._dist_matrix = payload["dist_matrix"]
        self._node_ids = payload["node_ids"]
        self._coords = payload["coords"]
        self._demands = payload.get("demands")
        self._time_windows = payload.get("time_windows")
        self._service_times = payload.get("service_times")
        self._loaded_vehicle_capacity = float(payload.get("vehicle_capacity", self._spin_vehicle_cap.value()))
        self._graph_ready = True
        n_nodes = self._graph.number_of_nodes()
        n_cust = len(self._coords) - 1
        # Keep spinner in sync with actual data (important for manual placement mode)
        if self._spin_n_cust.value() != n_cust:
            self._spin_n_cust.blockSignals(True)
            self._spin_n_cust.setValue(n_cust)
            self._spin_n_cust.blockSignals(False)
        pt = self._combo_problem_type.currentData()
        extra = ""
        if self._demands is not None:
            extra = f"  |  tổng demand = {self._demands.sum():.1f}"
        self._set_status(
            f"✓ Sẵn sàng — {n_nodes:,} nodes  |  {n_cust} điểm giao{extra}",
            color="#27AE60",
        )
        self._btn_run.setEnabled(True)
        # Draw static background on map canvas
        depot_coord = self._coords[0]
        customer_coords = self._coords[1:]
        road_paths = payload.get("road_paths", {})
        self._map_canvas.setup(self._graph, depot_coord, customer_coords,
                               problem_type=pt, road_paths=road_paths)
        self._convergence_canvas.reset(problem_type=pt)
        self._progress.setValue(0)

    def _on_load_error(self, msg: str) -> None:
        self._set_status(f"Lỗi tải đồ thị: {msg}", color="#E74C3C")
        self._module._logger.error(f"[pso_logistics_map] load error: {msg}")

    # ── Simulation control ────────────────────────────────────────────────────

    def _build_config(self) -> MapLogisticsPSOConfig:
        seed_val = self._spin_pso_seed.value()
        return MapLogisticsPSOConfig(
            n_customers=self._spin_n_cust.value(),
            data_seed=self._spin_data_seed.value(),
            problem_type=self._combo_problem_type.currentData(),
            n_vehicles=self._spin_n_vehicles.value(),
            vehicle_capacity=self._loaded_vehicle_capacity,
            demand_seed=self._spin_demand_seed.value(),
            max_demand=self._spin_max_demand.value(),
            vehicle_speed_kmph=self._spin_speed_kmph.value(),
            tw_seed=self._spin_tw_seed.value(),
            tw_width_s=self._spin_tw_width_s.value(),
            service_time_max_s=self._spin_svc_time_s.value(),
            tw_penalty=self._spin_tw_penalty.value(),
            n_particles=self._spin_npart.value(),
            n_iterations=self._spin_niter.value(),
            w=self._spin_w.value(),
            c1=self._spin_c1.value(),
            c2=self._spin_c2.value(),
            n_ops_max=self._spin_ops.value(),
            topology=self._combo_topo.currentData(),
            pso_seed=seed_val if seed_val > 0 else None,
            step_delay_ms=self._spin_delay.value(),
        )

    def _on_run(self) -> None:
        if self._sim_running or not self._graph_ready or self._dist_matrix is None:
            return

        config = self._build_config()
        self._total_iters = config.n_iterations
        self._best_route_history = []
        # Store problem context for canvas decode
        self._current_problem_type = config.problem_type
        self._current_vehicle_capacity = self._loaded_vehicle_capacity
        self._current_n_vehicles = config.n_vehicles

        self._convergence_canvas.reset(problem_type=config.problem_type)
        self._progress.setValue(0)
        self._set_status("Đang chạy PSO…", color="#27AE60")
        self._btn_run.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._btn_replay.setEnabled(False)
        self._btn_replay_stop.setEnabled(False)
        self._btn_export_map.setEnabled(False)
        self._btn_export_conv.setEnabled(False)

        self._worker = SimulationWorker(
            config, self._dist_matrix,
            demands=self._demands,
            time_windows=self._time_windows,
            service_times=self._service_times,
        )
        self._worker.progress_updated.connect(self._on_iteration)
        self._worker.result_ready.connect(self._on_done)
        self._worker.error_occurred.connect(self._on_sim_error)
        self._worker.result_ready.connect(lambda _: self._on_worker_finished())
        self._sim_running = True
        self._worker.start()

    def _on_stop(self) -> None:
        if self._worker is not None:
            self._worker.stop()
        self._set_status("Đang dừng…", color="#E67E22")

    def _on_iteration(
        self, iteration: int, gbest_fitness: float, gbest_position: list
    ) -> None:
        # Accumulate history
        self._best_route_history.append(
            {"iteration": iteration, "fitness": gbest_fitness, "perm": gbest_position}
        )
        if len(self._best_route_history) > _MAX_HISTORY:
            self._best_route_history = self._best_route_history[-_MAX_HISTORY:]

        pct = int(100 * iteration / max(1, self._total_iters))
        self._progress.setValue(pct)
        self._convergence_canvas.append(gbest_fitness)

        # Update map canvas (TSP vs VRP/VRPTW)
        pt = self._current_problem_type
        if pt in ("vrp", "vrptw") and self._demands is not None:
            routes = _decode_giant_tour(gbest_position, self._demands, self._current_vehicle_capacity)
            self._map_canvas.update_vrp_route(routes, gbest_fitness, iteration, pt,
                                              n_vehicles_cfg=self._current_n_vehicles)
            n_v = len(routes)
            _over = n_v > self._current_n_vehicles
            xe_lbl = f"⚠ {n_v} xe (vượt {self._current_n_vehicles})" if _over else f"{n_v} xe"
            self._lbl_fitness.setText(f"gBest: {gbest_fitness/1000:.3f} km  ({xe_lbl})")
            _parts_iter = []
            for _vi, _r in enumerate(routes[:4]):
                _c = _VRP_COLORS[_vi % len(_VRP_COLORS)]
                _stops = ','.join(str(i + 1) for i in _r[:3])
                _ellip = '…' if len(_r) > 3 else ''
                _parts_iter.append(
                    f'<span style="color:{_c};">&#9632;</span>'
                    f'V{_vi+1}:[{_stops}{_ellip}]'
                )
            self._lbl_route.setText(' | '.join(_parts_iter))
        else:
            self._map_canvas.update_route(gbest_position, gbest_fitness, iteration)
            self._lbl_fitness.setText(f"gBest: {gbest_fitness/1000:.3f} km")
            route_str = " → ".join(str(i + 1) for i in gbest_position[:7])
            if len(gbest_position) > 7:
                route_str += " → …"
            self._lbl_route.setText(f"D → {route_str} → D")

        self._lbl_iters.setText(f"Vòng lặp: {iteration}/{self._total_iters}")

    def _on_done(self, result: dict) -> None:
        self._last_result = result
        self._module._last_result = result
        fitness = float(result["gbest_fitness"])
        iters = int(result["iterations_done"])
        perm: list[int] = result.get("gbest_position", [])
        self._progress.setValue(100)
        self._set_status(f"Hoàn thành — {iters} vòng", color="#2471A3")
        pt = self._current_problem_type
        if pt in ("vrp", "vrptw") and self._demands is not None and perm:
            routes = _decode_giant_tour(perm, self._demands, self._current_vehicle_capacity)
            n_v = len(routes)
            _over = n_v > self._current_n_vehicles
            xe_lbl = f"⚠ {n_v} xe (vượt {self._current_n_vehicles} cấu hình)" if _over else f"{n_v} xe"
            self._lbl_fitness.setText(f"gBest: {fitness/1000:.3f} km  ({xe_lbl})")  # type: ignore[possibly-undefined]
            parts = []
            for v_idx, route in enumerate(routes):
                color = _VRP_COLORS[v_idx % len(_VRP_COLORS)]
                load = sum(float(self._demands[i]) for i in route)
                warn = ' ⚠' if _over and v_idx >= self._current_n_vehicles else ''
                parts.append(
                    f'<span style="color:{color}; font-size:14px;">&#9632;</span>'
                    f' V{v_idx + 1}{warn}: {len(route)} kh&nbsp;&nbsp;tải={load:.0f}'
                )
            self._lbl_route.setText('<br>'.join(parts))
        else:
            self._lbl_fitness.setText(
                f"gBest: {fitness/1000:.3f} km  ({fitness:.0f} m)"
            )
        self._lbl_iters.setText(f"Vòng lặp: {iters}/{self._total_iters}")

    def _on_sim_error(self, msg: str) -> None:
        self._set_status(f"Lỗi PSO: {msg}", color="#E74C3C")
        self._module._logger.error(f"[pso_logistics_map] simulation error: {msg}")
        # Re-enable Run so the user can retry after an error
        self._sim_running = False
        self._btn_run.setEnabled(self._graph_ready)
        self._btn_stop.setEnabled(False)
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None

    def _on_worker_finished(self) -> None:
        self._sim_running = False
        self._btn_run.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._btn_export_map.setEnabled(True)
        self._btn_export_conv.setEnabled(True)
        self._btn_export_route.setEnabled(True)
        if self._best_route_history:
            self._btn_replay.setEnabled(True)
        if self._worker is not None:
            self._worker.deleteLater()
        self._worker = None

    # ── Replay ────────────────────────────────────────────────────────────────

    def _on_replay_start(self) -> None:
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
        pt = self._current_problem_type
        if pt in ("vrp", "vrptw") and self._demands is not None:
            routes = _decode_giant_tour(frame["perm"], self._demands, self._current_vehicle_capacity)
            self._map_canvas.update_vrp_route(routes, frame["fitness"], frame["iteration"], pt,
                                              n_vehicles_cfg=self._current_n_vehicles)
        else:
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
                default_name="pso_map_route.png",
                file_filter="PNG Image (*.png);;All Files (*)",
            )
            if path:
                self._module._export_svc.write_bytes(path, data)
                self._module._activity_svc.log(
                    "EXPORT_COMPLETED",
                    "PSO Map: map exported",
                    module_id=PSOLogisticsMapModule.MODULE_ID,
                )
        except Exception as exc:  # noqa: BLE001
            self._module._logger.warning(f"[pso_logistics_map] export: {exc}")

    def _on_export_convergence(self) -> None:
        try:
            data = self._convergence_canvas.get_figure_bytes()
            if not data:
                return
            path = self._module._export_svc.ask_save_path(
                self,
                title="Xuất Đồ thị Hội tụ",
                default_name="pso_map_convergence.png",
                file_filter="PNG Image (*.png);;All Files (*)",
            )
            if path:
                self._module._export_svc.write_bytes(path, data)
                self._module._activity_svc.log(
                    "EXPORT_COMPLETED",
                    "PSO Map: convergence exported",
                    module_id=PSOLogisticsMapModule.MODULE_ID,
                )
        except Exception as exc:  # noqa: BLE001
            self._module._logger.warning(f"[pso_logistics_map] export conv: {exc}")

    def _on_export_route(self) -> None:
        """Xuất tuyến đường tối ưu cuối cùng ra file CSV."""
        try:
            if self._last_result is None or not self._coords:
                return
            perm: list[int] = self._last_result.get("gbest_position", [])
            if not perm:
                return
            fitness = float(self._last_result.get("gbest_fitness", 0.0))
            pt = self._current_problem_type
            depot_lon, depot_lat = self._coords[0]
            customer_coords = self._coords[1:]
            lines: list[str] = [f"# PSO {pt.upper()} — gBest = {fitness / 1000:.3f} km\n"]
            if pt in ("vrp", "vrptw") and self._demands is not None:
                lines.append("vehicle_id,stop,customer_label,lon,lat,demand,cumulative_load\n")
                routes = _decode_giant_tour(perm, self._demands, self._current_vehicle_capacity)
                for v_idx, route in enumerate(routes):
                    vid = f"V{v_idx + 1}"
                    cum = 0.0
                    lines.append(f"{vid},0,Depot,{depot_lon:.6f},{depot_lat:.6f},0.0,0.0\n")
                    for stop, cust_idx in enumerate(route, start=1):
                        lon, lat = customer_coords[cust_idx]
                        d = float(self._demands[cust_idx])
                        cum += d
                        lines.append(
                            f"{vid},{stop},C{cust_idx + 1},{lon:.6f},{lat:.6f},{d:.1f},{cum:.1f}\n"
                        )
                    lines.append(
                        f"{vid},{len(route) + 1},Depot,{depot_lon:.6f},{depot_lat:.6f},0.0,{cum:.1f}\n"
                    )
            else:
                lines.append("stop,customer_label,lon,lat\n")
                lines.append(f"0,Depot,{depot_lon:.6f},{depot_lat:.6f}\n")
                for stop, cust_idx in enumerate(perm, start=1):
                    lon, lat = customer_coords[cust_idx]
                    lines.append(f"{stop},C{cust_idx + 1},{lon:.6f},{lat:.6f}\n")
                lines.append(f"{len(perm) + 1},Depot,{depot_lon:.6f},{depot_lat:.6f}\n")
            data = "".join(lines).encode("utf-8-sig")  # BOM cho Excel
            path = self._module._export_svc.ask_save_path(
                self,
                title=f"Xuất Tuyến đường {pt.upper()}",
                default_name=f"pso_{pt}_routes.csv",
                file_filter="CSV (*.csv);;Văn bản (*.txt);;Tất cả (*)",
            )
            if path:
                self._module._export_svc.write_bytes(path, data)
                self._module._activity_svc.log(
                    "EXPORT_COMPLETED",
                    f"PSO Map: {pt.upper()} route CSV exported",
                    module_id=PSOLogisticsMapModule.MODULE_ID,
                )
        except Exception as exc:  # noqa: BLE001
            self._module._logger.warning(f"[pso_logistics_map] export route: {exc}")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _set_status(self, text: str, color: str = "#7F8C8D") -> None:
        self._lbl_status.setText(f"Trạng thái: {text}")
        self._lbl_status.setStyleSheet(_MONO_STYLE + f" color:{color};")

    def stop_all(self) -> None:
        """Stop all running background threads. Called from on_unload."""
        if self._worker is not None:
            self._worker.stop()
            self._worker.wait(3000)
        if self._load_worker is not None and self._load_worker.isRunning():
            self._load_worker.terminate()
            self._load_worker.wait(2000)
        self._replay_timer.stop()

    # ── State helpers ─────────────────────────────────────────────────────────

    def get_ui_state(self) -> dict[str, Any]:
        return {
            "bbox_name": self._combo_bbox.currentData(),
            "network_type": self._combo_net_type.currentData(),
            "problem_type": self._combo_problem_type.currentData(),
            "n_customers": self._spin_n_cust.value(),
            "data_seed": self._spin_data_seed.value(),
            # VRP
            "n_vehicles": self._spin_n_vehicles.value(),
            "vehicle_capacity": self._spin_vehicle_cap.value(),
            "demand_seed": self._spin_demand_seed.value(),
            "max_demand": self._spin_max_demand.value(),
            # VRPTW
            "vehicle_speed_kmph": self._spin_speed_kmph.value(),
            "tw_seed": self._spin_tw_seed.value(),
            "tw_width_s": self._spin_tw_width_s.value(),
            "service_time_max_s": self._spin_svc_time_s.value(),
            "tw_penalty": self._spin_tw_penalty.value(),
            # PSO
            "n_particles": self._spin_npart.value(),
            "n_iterations": self._spin_niter.value(),
            "w": self._spin_w.value(),
            "c1": self._spin_c1.value(),
            "c2": self._spin_c2.value(),
            "n_ops_max": self._spin_ops.value(),
            "topology": self._combo_topo.currentData(),
            "pso_seed": self._spin_pso_seed.value(),
            "step_delay_ms": self._spin_delay.value(),
            "replay_speed_ms": self._spin_replay_speed.value(),
            "active_tab": self._tabs.currentIndex(),
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

        _set_combo(self._combo_bbox, "bbox_name")
        _set_combo(self._combo_net_type, "network_type")
        _set_combo(self._combo_problem_type, "problem_type")
        self._spin_n_cust.setValue(state.get("n_customers", 10))
        self._spin_data_seed.setValue(state.get("data_seed", 42))
        self._spin_n_vehicles.setValue(state.get("n_vehicles", 3))
        self._spin_vehicle_cap.setValue(state.get("vehicle_capacity", 50.0))
        self._spin_demand_seed.setValue(state.get("demand_seed", 7))
        self._spin_max_demand.setValue(state.get("max_demand", 15.0))
        self._spin_speed_kmph.setValue(state.get("vehicle_speed_kmph", 30.0))
        self._spin_tw_seed.setValue(state.get("tw_seed", 13))
        self._spin_tw_width_s.setValue(state.get("tw_width_s", 1800.0))
        self._spin_svc_time_s.setValue(state.get("service_time_max_s", 300.0))
        self._spin_tw_penalty.setValue(state.get("tw_penalty", 10.0))
        self._spin_npart.setValue(state.get("n_particles", 30))
        self._spin_niter.setValue(state.get("n_iterations", 100))
        self._spin_w.setValue(state.get("w", 0.5))
        self._spin_c1.setValue(state.get("c1", 1.5))
        self._spin_c2.setValue(state.get("c2", 1.5))
        self._spin_ops.setValue(state.get("n_ops_max", 3))
        _set_combo(self._combo_topo, "topology")
        self._spin_pso_seed.setValue(state.get("pso_seed", 42))
        self._spin_delay.setValue(state.get("step_delay_ms", _DEFAULT_DELAY_MS))
        self._spin_replay_speed.setValue(state.get("replay_speed_ms", _DEFAULT_REPLAY_MS))
        self._tabs.setCurrentIndex(state.get("active_tab", 0))


# ─── BaseModule implementation ────────────────────────────────────────────────

class PSOLogisticsMapModule(BaseModule):
    """IIMP module — PSO Logistics Map v1.1.0 (TSP / VRP / VRPTW trên bản đồ thật).

    Hosts discrete PSO simulation for TSP, CVRP, and VRPTW problems on a real
    road network loaded from an offline OSM .pbf file via pyosmium + networkx.
    """

    MODULE_ID = "pso_logistics_map"
    MODULE_NAME = "PSO — Giao hàng trên Bản đồ Thật"
    MODULE_VERSION = "1.1.0"

    def __init__(self, manifest: dict, context: ModuleContext) -> None:
        super().__init__(manifest=manifest, context=context)
        self._logger = context.logger
        self._export_svc = context.export_service
        self._activity_svc = context.activity_service
        self._view: _MapView | None = None
        self._last_result: dict | None = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def on_load(self) -> None:
        self._logger.info(f"[{self.MODULE_ID}] on_load")

    def build_view(self) -> Any:  # QWidget
        if self._view is None:
            self._view = _MapView(self)
            # Kick off graph loading automatically on first build
            self._view.start_load_graph()
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
        if self._view is not None:
            self._view.stop_all()
        self._logger.info(f"[{self.MODULE_ID}] on_unload")

    # ── State persistence ─────────────────────────────────────────────────────

    def get_state(self) -> dict[str, Any]:
        state = default_state()
        if self._view is not None:
            state.update(self._view.get_ui_state())
        state["_state_version"] = STATE_VERSION
        if self._last_result:
            state["last_gbest_fitness"] = self._last_result.get("gbest_fitness")
            state["last_gbest_position"] = self._last_result.get("gbest_position")
            state["last_convergence"] = self._last_result.get("convergence_history", [])
            state["last_n_iterations"] = self._last_result.get("iterations_done")
        return state

    def restore_state(self, state: dict[str, Any]) -> None:
        if self._view is None:
            return
        self._view.apply_ui_state(state)

        conv: list[float] = state.get("last_convergence", [])
        if conv:
            self._view._convergence_canvas.set_history(conv)

        fitness = state.get("last_gbest_fitness")
        n_iters = state.get("last_n_iterations")
        if fitness is not None:
            self._view._lbl_fitness.setText(
                f"gBest: {fitness/1000:.3f} km  ({fitness:.0f} m)"
            )
        if n_iters is not None:
            total = state.get("n_iterations", n_iters)
            self._view._lbl_iters.setText(f"Vòng lặp: {n_iters}/{total}")
