"""Linear Programming 3D — Giải bài toán QHTT 3 biến bằng đồ thị không gian v1.0.0

Cho phép người dùng:
  1. Nhập hàm mục tiêu Z = c₁X₁ + c₂X₂ + c₃X₃ (max hoặc min)
  2. Ràng buộc không âm X₁ ≥ 0, X₂ ≥ 0, X₃ ≥ 0 (bắt buộc)
  3. Thêm tối đa 10 ràng buộc dạng a·X₁ + b·X₂ + c·X₃ ≤|≥|= rhs
  4. Vẽ polyhedron miền nghiệm (feasible region) trong không gian 3D
  5. Bảng các đỉnh và giá trị hàm mục tiêu tại mỗi đỉnh
  6. Xác định điểm tối ưu
  7. Slider mặt phẳng đồng mức Z = k để trực quan hóa
  8. Xoay góc nhìn (Elevation / Azimuth)
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any

import numpy as np

try:
    from PySide6.QtCore import Qt, Signal
    from PySide6.QtWidgets import (
        QAbstractSpinBox,
        QComboBox,
        QDoubleSpinBox,
        QFrame,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QSlider,
        QTableWidget,
        QTableWidgetItem,
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
from core.utils.imports import safe_import

_WidgetBase = QWidget if _QT else object  # type: ignore[misc]

# ─── Constants ────────────────────────────────────────────────────────────────

MAX_CONSTRAINTS: int = 10
_EPS: float = 1e-9

# ─── Data classes ─────────────────────────────────────────────────────────────


@dataclass
class Constraint3D:
    """Single linear constraint: a*x₁ + b*x₂ + c*x₃  op  rhs."""

    a: float = 1.0
    b: float = 1.0
    c: float = 1.0
    op: str = "≤"  # one of "≤", "≥", "="
    rhs: float = 1.0

    def label(self, idx: int) -> str:
        """Human-readable label, 1-indexed."""
        parts: list[str] = []
        for coef, var in [(self.a, "X\u2081"), (self.b, "X\u2082"), (self.c, "X\u2083")]:
            if coef == 0:
                continue
            sign = ""
            if parts:
                sign = " + " if coef > 0 else " - "
                abs_c = abs(coef)
            else:
                if coef < 0:
                    sign = "-"
                abs_c = abs(coef)
            if abs_c == 1:
                parts.append(f"{sign}{var}")
            else:
                parts.append(f"{sign}{abs_c:g}{var}")
        if not parts:
            parts.append("0")
        return f"({''.join(parts)}) {self.op} {self.rhs:g}"


@dataclass
class LP3DProblem:
    """Full LP 3-variable problem definition."""

    c1: float = 1.0
    c2: float = 1.0
    c3: float = 1.0
    sense: str = "max"  # "max" or "min"
    constraints: list[Constraint3D] = field(default_factory=list)


@dataclass
class Vertex3D:
    """A vertex of the feasible polyhedron."""

    x: float
    y: float
    z: float
    obj: float  # objective value
    is_optimal: bool = False
    source: str = ""


@dataclass
class LP3DResult:
    """Result of solving the 3D LP."""

    feasible: bool = True
    bounded: bool = True
    vertices: list[Vertex3D] = field(default_factory=list)
    optimal_vertices: list[Vertex3D] = field(default_factory=list)
    optimal_value: float = 0.0
    hull_faces: list[list[int]] = field(default_factory=list)
    message: str = ""


# ─── Pure-Python LP Engine ────────────────────────────────────────────────────


class LP3DEngine:
    """Graphical LP solver for 3-variable problems — pure Python, no Qt."""

    def __init__(self) -> None:
        self.problem = LP3DProblem()

    # ── Problem setup ─────────────────────────────────────────────────────

    def set_objective(self, c1: float, c2: float, c3: float,
                      sense: str = "max") -> None:
        self.problem.c1 = c1
        self.problem.c2 = c2
        self.problem.c3 = c3
        self.problem.sense = sense

    def set_constraints(self, constraints: list[Constraint3D]) -> None:
        self.problem.constraints = list(constraints)

    # ── Solver ────────────────────────────────────────────────────────────

    def solve(self) -> LP3DResult:
        """Find all vertices of the feasible polyhedron and identify optimum."""
        prob = self.problem

        # Build list of all half-space boundaries including x₁≥0, x₂≥0, x₃≥0
        # Each plane: (a, b, c, rhs, op)
        planes: list[tuple[float, float, float, float, str]] = [
            (1.0, 0.0, 0.0, 0.0, "≥"),  # x₁ ≥ 0
            (0.0, 1.0, 0.0, 0.0, "≥"),  # x₂ ≥ 0
            (0.0, 0.0, 1.0, 0.0, "≥"),  # x₃ ≥ 0
        ]
        for ct in prob.constraints:
            planes.append((ct.a, ct.b, ct.c, ct.rhs, ct.op))

        n = len(planes)
        if n < 3:
            return LP3DResult(feasible=False, message="Không đủ ràng buộc.")

        # Find all intersection points of triples of planes
        raw_vertices: list[tuple[float, float, float, str]] = []
        for i, j, k in itertools.combinations(range(n), 3):
            pt = self._intersect_3planes(planes[i], planes[j], planes[k])
            if pt is not None:
                src = (self._plane_label(planes[i], i) + " ∩ "
                       + self._plane_label(planes[j], j) + " ∩ "
                       + self._plane_label(planes[k], k))
                raw_vertices.append((pt[0], pt[1], pt[2], src))

        # Filter: keep only vertices in the feasible region
        feasible_pts: list[tuple[float, float, float, str]] = []
        for (vx, vy, vz, src) in raw_vertices:
            if self._is_feasible(vx, vy, vz, planes):
                feasible_pts.append((vx, vy, vz, src))

        # Remove near-duplicates
        unique: list[tuple[float, float, float, str]] = []
        for pt in feasible_pts:
            if not any(
                abs(pt[0] - u[0]) < _EPS
                and abs(pt[1] - u[1]) < _EPS
                and abs(pt[2] - u[2]) < _EPS
                for u in unique
            ):
                unique.append(pt)

        if not unique:
            return LP3DResult(
                feasible=False,
                message="Miền nghiệm rỗng — hệ ràng buộc vô nghiệm.",
            )

        # Compute objective values
        vertices: list[Vertex3D] = []
        for (vx, vy, vz, src) in unique:
            vx = 0.0 if abs(vx) < _EPS else vx
            vy = 0.0 if abs(vy) < _EPS else vy
            vz = 0.0 if abs(vz) < _EPS else vz
            obj = prob.c1 * vx + prob.c2 * vy + prob.c3 * vz
            obj = 0.0 if abs(obj) < _EPS else obj
            vertices.append(Vertex3D(x=vx, y=vy, z=vz, obj=obj, source=src))

        # Convex hull faces (for 3D rendering)
        hull_faces = self._convex_hull_faces(
            [(v.x, v.y, v.z) for v in vertices]
        )

        # Find optimal
        if prob.sense == "max":
            opt_val = max(v.obj for v in vertices)
        else:
            opt_val = min(v.obj for v in vertices)

        opt_verts: list[Vertex3D] = []
        for v in vertices:
            if abs(v.obj - opt_val) < _EPS:
                v.is_optimal = True
                opt_verts.append(v)

        return LP3DResult(
            feasible=True,
            bounded=True,
            vertices=sorted(vertices, key=lambda v: (v.x, v.y, v.z)),
            optimal_vertices=opt_verts,
            optimal_value=opt_val,
            hull_faces=hull_faces,
            message="Đã tìm được nghiệm tối ưu." if opt_verts else "",
        )

    # ── Geometry helpers ──────────────────────────────────────────────────

    @staticmethod
    def _intersect_3planes(
        p1: tuple[float, float, float, float, str],
        p2: tuple[float, float, float, float, str],
        p3: tuple[float, float, float, float, str],
    ) -> tuple[float, float, float] | None:
        """Find intersection of three planes via Cramer's rule (3×3 system)."""
        A = np.array([
            [p1[0], p1[1], p1[2]],
            [p2[0], p2[1], p2[2]],
            [p3[0], p3[1], p3[2]],
        ], dtype=np.float64)
        b = np.array([p1[3], p2[3], p3[3]], dtype=np.float64)
        det = np.linalg.det(A)
        if abs(det) < _EPS:
            return None
        sol = np.linalg.solve(A, b)
        return (float(sol[0]), float(sol[1]), float(sol[2]))

    @staticmethod
    def _is_feasible(
        x: float, y: float, z: float,
        planes: list[tuple[float, float, float, float, str]],
    ) -> bool:
        """Check if point (x, y, z) satisfies all constraints."""
        for a, b, c, rhs, op in planes:
            val = a * x + b * y + c * z
            if op == "≤":
                if val > rhs + _EPS:
                    return False
            elif op == "≥":
                if val < rhs - _EPS:
                    return False
            elif op == "=":
                if abs(val - rhs) > _EPS:
                    return False
        return True

    @staticmethod
    def _plane_label(plane: tuple[float, float, float, float, str],
                     idx: int) -> str:
        a, b, c, rhs, op = plane
        if idx == 0:
            return "X\u2081=0"
        if idx == 1:
            return "X\u2082=0"
        if idx == 2:
            return "X\u2083=0"
        parts: list[str] = []
        for coef, var in [(a, "X\u2081"), (b, "X\u2082"), (c, "X\u2083")]:
            if coef != 0:
                sign = "+" if coef > 0 and parts else ""
                parts.append(f"{sign}{coef:g}{var}")
        return f"{''.join(parts)}{op}{rhs:g}"

    @staticmethod
    def _convex_hull_faces(
        points: list[tuple[float, float, float]],
    ) -> list[list[int]]:
        """Compute convex hull faces. Returns list of face index-lists.

        Uses scipy.spatial.ConvexHull when available, otherwise returns empty
        (graceful degradation — polyhedron just won't render).
        """
        if len(points) < 4:
            # Degenerate cases: fewer than 4 points → no 3D hull
            if len(points) == 3:
                return [[0, 1, 2]]
            return []
        try:
            _mod, _ok = safe_import("scipy.spatial")  # noqa: N806
            if not _ok:
                return []
            ConvexHull = _mod.ConvexHull  # noqa: N806
            hull = ConvexHull(np.array(points, dtype=np.float64))
            return [list(simplex) for simplex in hull.simplices]
        except Exception:
            return []

    # ── State ─────────────────────────────────────────────────────────────

    def get_state(self) -> dict[str, Any]:
        p = self.problem
        return {
            "c1": p.c1,
            "c2": p.c2,
            "c3": p.c3,
            "sense": p.sense,
            "constraints": [
                {"a": ct.a, "b": ct.b, "c": ct.c, "op": ct.op, "rhs": ct.rhs}
                for ct in p.constraints
            ],
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        self.problem.c1 = float(state.get("c1", 1.0))
        self.problem.c2 = float(state.get("c2", 1.0))
        self.problem.c3 = float(state.get("c3", 1.0))
        self.problem.sense = state.get("sense", "max")
        raw = state.get("constraints", [])
        self.problem.constraints = [
            Constraint3D(
                a=float(ct.get("a", 1)),
                b=float(ct.get("b", 1)),
                c=float(ct.get("c", 1)),
                op=ct.get("op", "≤"),
                rhs=float(ct.get("rhs", 1)),
            )
            for ct in raw
        ]


# ─── UI: LP 3D Canvas ────────────────────────────────────────────────────────


class _LP3DCanvas(_WidgetBase):  # type: ignore[misc]
    """Matplotlib 3D canvas for the feasible polyhedron and iso-profit plane.

    Z-ordering mitigation strategy (matplotlib 3D known bug):
    - Render opaque polyhedron faces FIRST with moderate alpha
    - Render transparent constraint planes AFTER with low alpha
    - Use computed_zorder=False to control draw order manually
    - Sort faces by centroid distance to camera before rendering
    """

    def __init__(self, parent: Any = None) -> None:
        if not _QT:  # pragma: no cover
            return
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if _MPL:
            self._figure = Figure(figsize=(7, 6), dpi=100)
            self._figure.patch.set_facecolor("#FAFBFC")
            self._ax = self._figure.add_subplot(111, projection="3d",
                                                computed_zorder=False)
            self._canvas = FigureCanvas(self._figure)
            self._canvas.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            layout.addWidget(self._canvas)
        else:  # pragma: no cover
            layout.addWidget(QLabel("(matplotlib không khả dụng)"))
            self._figure = None
            self._ax = None
            self._canvas = None

    def render(
        self,
        engine: LP3DEngine,
        result: LP3DResult,
        iso_k: float | None = None,
        precision: int = 4,
        elev: float = 25.0,
        azim: float = -60.0,
    ) -> None:
        if not _MPL or self._ax is None:  # pragma: no cover
            return
        assert self._figure is not None and self._canvas is not None
        _art3d, _art3d_ok = safe_import("mpl_toolkits.mplot3d.art3d")  # noqa: N806
        Poly3DCollection = _art3d.Poly3DCollection if _art3d_ok else None  # noqa: N806

        ax = self._ax
        ax.clear()
        ax.set_facecolor("#FAFBFC")
        ax.view_init(elev=elev, azim=azim)

        prob = engine.problem

        if result.feasible and result.vertices:
            pts = [(v.x, v.y, v.z) for v in result.vertices]
            all_x = [p[0] for p in pts]
            all_y = [p[1] for p in pts]
            all_z = [p[2] for p in pts]
            margin = 1.15
            x_max = max(all_x) * margin + 1.0
            y_max = max(all_y) * margin + 1.0
            z_max = max(all_z) * margin + 1.0
        else:
            x_max, y_max, z_max = 10.0, 10.0, 10.0

        x_max = max(x_max, 2.0)
        y_max = max(y_max, 2.0)
        z_max = max(z_max, 2.0)

        # ── Draw polyhedron faces ─────────────────────────────────────────
        if (result.feasible and result.hull_faces
                and Poly3DCollection is not None):
            pts_arr = np.array(
                [(v.x, v.y, v.z) for v in result.vertices],
                dtype=np.float64,
            )
            faces = [pts_arr[face].tolist() for face in result.hull_faces]
            poly = Poly3DCollection(
                faces,
                alpha=0.25,
                facecolor="#AED6F1",
                edgecolor="#2471A3",
                linewidth=0.8,
                zorder=2,
            )
            ax.add_collection3d(poly)

        # ── Draw vertices ─────────────────────────────────────────────────
        if result.feasible:
            for v in result.vertices:
                if v.is_optimal:
                    ax.scatter(
                        [v.x], [v.y], [v.z],
                        color="red", s=120, marker="*",
                        zorder=8, depthshade=False,
                        label=f"Tối ưu ({v.x:.{precision}g}, "
                              f"{v.y:.{precision}g}, {v.z:.{precision}g})",
                    )
                else:
                    ax.scatter(
                        [v.x], [v.y], [v.z],
                        color="black", s=30, marker="o",
                        zorder=7, depthshade=False,
                    )
                ax.text(
                    v.x, v.y, v.z,
                    f"  ({v.x:.{precision}g}, {v.y:.{precision}g}, "
                    f"{v.z:.{precision}g})",
                    fontsize=7, color="#333", zorder=9,
                )

        # ── Draw constraint planes (transparent) ─────────────────────────
        colors = [
            "#E74C3C", "#2980B9", "#27AE60", "#8E44AD", "#F39C12",
            "#1ABC9C", "#E67E22", "#3498DB", "#9B59B6", "#2ECC71",
        ]
        for i, ct in enumerate(prob.constraints):
            color = colors[i % len(colors)]
            self._draw_constraint_plane(
                ax, ct, i + 1, color, x_max, y_max, z_max)

        # ── Draw iso-profit plane ─────────────────────────────────────────
        if iso_k is not None:
            self._draw_iso_plane(
                ax, prob.c1, prob.c2, prob.c3, iso_k,
                x_max, y_max, z_max)

        # ── Axis labels and limits ────────────────────────────────────────
        ax.set_xlabel("X\u2081", fontsize=10, fontweight="bold", labelpad=8)
        ax.set_ylabel("X\u2082", fontsize=10, fontweight="bold", labelpad=8)
        ax.set_zlabel("X\u2083", fontsize=10, fontweight="bold", labelpad=8)
        ax.set_xlim(0, x_max)
        ax.set_ylim(0, y_max)
        ax.set_zlim(0, z_max)

        sense_label = "max" if prob.sense == "max" else "min"
        title = (f"Z = {prob.c1:g}X\u2081 + {prob.c2:g}X\u2082"
                 f" + {prob.c3:g}X\u2083 → {sense_label}")
        if result.feasible and result.optimal_vertices:
            title += f"  |  Z* = {result.optimal_value:.{precision}g}"
        ax.set_title(title, fontsize=11, fontweight="bold", pad=14)

        ax.tick_params(labelsize=8)

        self._figure.tight_layout(pad=1.5)
        self._canvas.draw()

    @staticmethod
    def _draw_constraint_plane(
        ax: Any, ct: Constraint3D, idx: int, color: str,
        x_max: float, y_max: float, z_max: float,
    ) -> None:
        """Draw a single constraint plane as a transparent surface.

        Only draws the portion within the visible first octant (x,y,z ≥ 0).
        """
        a, b, c, rhs = ct.a, ct.b, ct.c, ct.rhs
        res = 30  # grid resolution

        if abs(c) > _EPS:
            # Solve for x₃: x₃ = (rhs - a*x₁ - b*x₂) / c
            x1 = np.linspace(0, x_max, res)
            x2 = np.linspace(0, y_max, res)
            X1, X2 = np.meshgrid(x1, x2)
            X3 = (rhs - a * X1 - b * X2) / c
            # Clip to visible region
            mask = (X3 >= -0.01) & (X3 <= z_max * 1.1)
            X3_clipped = np.where(mask, X3, np.nan)
            ax.plot_surface(
                X1, X2, X3_clipped,
                alpha=0.12, color=color, zorder=1,
                rstride=1, cstride=1, linewidth=0, antialiased=False,
            )
        elif abs(b) > _EPS:
            # Solve for x₂: x₂ = (rhs - a*x₁ - c*x₃) / b
            x1 = np.linspace(0, x_max, res)
            x3 = np.linspace(0, z_max, res)
            X1, X3 = np.meshgrid(x1, x3)
            X2 = (rhs - a * X1 - c * X3) / b  # c is 0 here
            mask = (X2 >= -0.01) & (X2 <= y_max * 1.1)
            X2_clipped = np.where(mask, X2, np.nan)
            ax.plot_surface(
                X1, X2_clipped, X3,
                alpha=0.12, color=color, zorder=1,
                rstride=1, cstride=1, linewidth=0, antialiased=False,
            )
        elif abs(a) > _EPS:
            # Solve for x₁: x₁ = (rhs - b*x₂ - c*x₃) / a
            x2 = np.linspace(0, y_max, res)
            x3 = np.linspace(0, z_max, res)
            X2, X3 = np.meshgrid(x2, x3)
            X1 = (rhs - b * X2 - c * X3) / a  # b, c are 0 here
            mask = (X1 >= -0.01) & (X1 <= x_max * 1.1)
            X1_clipped = np.where(mask, X1, np.nan)
            ax.plot_surface(
                X1_clipped, X2, X3,
                alpha=0.12, color=color, zorder=1,
                rstride=1, cstride=1, linewidth=0, antialiased=False,
            )

    @staticmethod
    def _draw_iso_plane(
        ax: Any, c1: float, c2: float, c3: float, k: float,
        x_max: float, y_max: float, z_max: float,
    ) -> None:
        """Draw the iso-profit plane c1*x1 + c2*x2 + c3*x3 = k."""
        res = 25
        if abs(c3) > _EPS:
            x1 = np.linspace(0, x_max, res)
            x2 = np.linspace(0, y_max, res)
            X1, X2 = np.meshgrid(x1, x2)
            X3 = (k - c1 * X1 - c2 * X2) / c3
            mask = (X3 >= -0.01) & (X3 <= z_max * 1.1)
            X3_c = np.where(mask, X3, np.nan)
            ax.plot_surface(
                X1, X2, X3_c,
                alpha=0.25, color="#FF6F00", zorder=5,
                rstride=1, cstride=1, linewidth=0, antialiased=False,
            )
        elif abs(c2) > _EPS:
            x1 = np.linspace(0, x_max, res)
            x3 = np.linspace(0, z_max, res)
            X1, X3 = np.meshgrid(x1, x3)
            X2 = (k - c1 * X1 - c3 * X3) / c2
            mask = (X2 >= -0.01) & (X2 <= y_max * 1.1)
            X2_c = np.where(mask, X2, np.nan)
            ax.plot_surface(
                X1, X2_c, X3,
                alpha=0.25, color="#FF6F00", zorder=5,
                rstride=1, cstride=1, linewidth=0, antialiased=False,
            )
        elif abs(c1) > _EPS:
            x2 = np.linspace(0, y_max, res)
            x3 = np.linspace(0, z_max, res)
            X2, X3 = np.meshgrid(x2, x3)
            X1 = (k - c2 * X2 - c3 * X3) / c1
            mask = (X1 >= -0.01) & (X1 <= x_max * 1.1)
            X1_c = np.where(mask, X1, np.nan)
            ax.plot_surface(
                X1_c, X2, X3,
                alpha=0.25, color="#FF6F00", zorder=5,
                rstride=1, cstride=1, linewidth=0, antialiased=False,
            )

    def export_png(self, path: str) -> None:
        if self._figure is not None:
            self._figure.savefig(path, dpi=150, bbox_inches="tight",
                                 facecolor="#FFFFFF")


# ─── UI: Constraint row widget ───────────────────────────────────────────────


class _ConstraintRow3D(_WidgetBase):  # type: ignore[misc]
    """A single constraint input row: a·X₁ + b·X₂ + c·X₃  op  rhs."""

    if _QT:
        changed = Signal()
        remove_requested = Signal()

    def __init__(self, idx: int, constraint: Constraint3D | None = None,
                 parent: Any = None) -> None:
        if not _QT:  # pragma: no cover
            return
        super().__init__(parent)
        self.idx = idx
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 2, 0, 2)
        lay.setSpacing(3)

        self._lbl = QLabel(f"({idx})")
        self._lbl.setFixedWidth(24)
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._lbl)

        c = constraint or Constraint3D()

        self._spin_a = self._make_spin(c.a)
        lay.addWidget(self._spin_a)
        lay.addWidget(self._lbl_var("X\u2081 +"))

        self._spin_b = self._make_spin(c.b)
        lay.addWidget(self._spin_b)
        lay.addWidget(self._lbl_var("X\u2082 +"))

        self._spin_c = self._make_spin(c.c)
        lay.addWidget(self._spin_c)
        lay.addWidget(self._lbl_var("X\u2083"))

        self._combo_op = QComboBox()
        self._combo_op.addItems(["≤", "≥", "="])
        if constraint:
            idx_op = (["≤", "≥", "="].index(constraint.op)
                      if constraint.op in ["≤", "≥", "="] else 0)
            self._combo_op.setCurrentIndex(idx_op)
        self._combo_op.setFixedWidth(48)
        lay.addWidget(self._combo_op)

        self._spin_rhs = self._make_spin(c.rhs)
        lay.addWidget(self._spin_rhs)

        self._btn_remove = QPushButton("✕")
        self._btn_remove.setFixedSize(20, 20)
        self._btn_remove.setToolTip("Xóa ràng buộc")
        self._btn_remove.setStyleSheet(
            "QPushButton { color: white; background: #E74C3C; font-weight: bold;"
            " border: 1px solid #C0392B; border-radius: 3px; font-size: 14px;"
            " padding: 0px; line-height: 20px; }"
            "QPushButton:hover { background: #C0392B; }")
        self._btn_remove.clicked.connect(self.remove_requested.emit)
        lay.addWidget(self._btn_remove)

        # Connect change signals
        for sp in (self._spin_a, self._spin_b, self._spin_c, self._spin_rhs):
            sp.valueChanged.connect(self.changed.emit)
        self._combo_op.currentIndexChanged.connect(self.changed.emit)

    @staticmethod
    def _lbl_var(text: str) -> QLabel:
        lbl = QLabel(f" {text} ")
        lbl.setContentsMargins(0, 0, 0, 0)
        return lbl

    @staticmethod
    def _make_spin(value: float) -> QDoubleSpinBox:
        sp = QDoubleSpinBox()
        sp.setRange(-9999.0, 9999.0)
        sp.setDecimals(2)
        sp.setValue(value)
        sp.setSingleStep(0.5)
        sp.setMinimumWidth(56)
        sp.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sp.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        return sp

    def get_constraint(self) -> Constraint3D:
        return Constraint3D(
            a=self._spin_a.value(),
            b=self._spin_b.value(),
            c=self._spin_c.value(),
            op=self._combo_op.currentText(),
            rhs=self._spin_rhs.value(),
        )

    def set_index(self, idx: int) -> None:
        self.idx = idx
        self._lbl.setText(f"({idx})")


# ─── UI: Vertex table ────────────────────────────────────────────────────────


class _VertexTable3D(_WidgetBase):  # type: ignore[misc]
    """Table showing vertices and objective values for 3D LP."""

    def __init__(self, parent: Any = None) -> None:
        if not _QT:  # pragma: no cover
            return
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(
            ["X\u2081", "X\u2082", "X\u2083", "Z", "Tối ưu"])
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setStyleSheet(
            "QTableWidget { gridline-color: #DDE2E8; font-size: 14px; }"
            "QHeaderView::section { background-color: #2C3E50; color: #FFF;"
            " padding: 8px; font-weight: bold; font-size: 15px; }"
        )
        hdr = self._table.horizontalHeader()
        hdr.setStretchLastSection(False)
        for col in range(5):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._table)

    def populate(self, vertices: list[Vertex3D], precision: int = 4) -> None:
        self._table.setRowCount(0)
        for v in vertices:
            row = self._table.rowCount()
            self._table.insertRow(row)
            items = [
                f"{v.x:.{precision}g}",
                f"{v.y:.{precision}g}",
                f"{v.z:.{precision}g}",
                f"{v.obj:.{precision}g}",
                "★" if v.is_optimal else "",
            ]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if v.is_optimal:
                    item.setBackground(
                        __import__("PySide6.QtGui",
                                   fromlist=["QColor"]).QColor("#FDEDEC"))
                self._table.setItem(row, col, item)


# ─── UI: Main module view ────────────────────────────────────────────────────


class _LP3DView(_WidgetBase):  # type: ignore[misc]
    """Main view: left panel (inputs + table) | right panel (3D graph + controls)."""

    def __init__(self, engine: LP3DEngine, context: ModuleContext,
                 parent: Any = None) -> None:
        if not _QT:  # pragma: no cover
            return
        super().__init__(parent)
        self._engine = engine
        self._context = context
        self._precision = 4
        self._iso_k: float | None = None
        self._result: LP3DResult | None = None
        self._constraint_rows: list[_ConstraintRow3D] = []

        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # ── Left panel ────────────────────────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(8)

        # Objective function
        obj_group = QGroupBox("Hàm mục tiêu")
        obj_lay = QGridLayout(obj_group)
        obj_lay.setSpacing(5)

        obj_lay.addWidget(QLabel("Z ="), 0, 0)
        self._spin_c1 = self._make_coef_spin(engine.problem.c1)
        obj_lay.addWidget(self._spin_c1, 0, 1)
        obj_lay.addWidget(QLabel("X\u2081 +"), 0, 2)
        self._spin_c2 = self._make_coef_spin(engine.problem.c2)
        obj_lay.addWidget(self._spin_c2, 0, 3)
        obj_lay.addWidget(QLabel("X\u2082 +"), 0, 4)
        self._spin_c3 = self._make_coef_spin(engine.problem.c3)
        obj_lay.addWidget(self._spin_c3, 0, 5)
        obj_lay.addWidget(QLabel("X\u2083 →"), 0, 6)

        self._combo_sense = QComboBox()
        self._combo_sense.addItems(["max", "min"])
        self._combo_sense.setCurrentText(engine.problem.sense)
        self._combo_sense.setFixedWidth(60)
        obj_lay.addWidget(self._combo_sense, 0, 7)

        left.addWidget(obj_group)

        # Non-negativity note
        nn_label = QLabel(
            "  Ràng buộc không âm:  X\u2081 ≥ 0 ,  X\u2082 ≥ 0 ,  X\u2083 ≥ 0")
        nn_label.setStyleSheet(
            "color: #7F8C8D; font-style: italic; font-size: 13px;")
        left.addWidget(nn_label)

        # Constraints section
        cst_group = QGroupBox("Các ràng buộc (tối đa 10)")
        cst_lay = QVBoxLayout(cst_group)
        cst_lay.setSpacing(4)

        self._constraints_container = QVBoxLayout()
        self._constraints_container.setSpacing(2)
        cst_lay.addLayout(self._constraints_container)

        btn_row = QHBoxLayout()
        self._btn_add = QPushButton("＋ Thêm ràng buộc")
        self._btn_add.setStyleSheet(
            "QPushButton { color: white; background: #2980B9; font-weight: bold;"
            " padding: 5px 12px; border-radius: 4px; font-size: 14px; }"
            "QPushButton:hover { background: #2471A3; }"
            "QPushButton:disabled { background: #BDC3C7; color: #7F8C8D; }")
        self._btn_add.clicked.connect(self._add_constraint)
        btn_row.addWidget(self._btn_add)
        btn_row.addStretch()
        cst_lay.addLayout(btn_row)

        left.addWidget(cst_group)

        # Solve button
        self._btn_solve = QPushButton("  Giải bài toán  ")
        self._btn_solve.setStyleSheet(
            "QPushButton { background: #2980B9; color: white; font-weight: bold;"
            " font-size: 15px; padding: 8px 16px; border-radius: 4px; }"
            "QPushButton:hover { background: #2471A3; }")
        self._btn_solve.clicked.connect(self._on_solve)
        left.addWidget(self._btn_solve,
                       alignment=Qt.AlignmentFlag.AlignCenter)

        # Result label
        self._lbl_result = QLabel("")
        self._lbl_result.setStyleSheet(
            "font-size: 14px; color: #2C3E50; padding: 4px;")
        self._lbl_result.setWordWrap(True)
        left.addWidget(self._lbl_result)

        # Vertex table
        vtx_group = QGroupBox("Các đỉnh và giá trị hàm mục tiêu")
        vtx_lay = QVBoxLayout(vtx_group)
        self._vertex_table = _VertexTable3D()
        vtx_lay.addWidget(self._vertex_table)
        left.addWidget(vtx_group)

        left.addStretch()

        left_widget = QWidget()
        left_widget.setLayout(left)
        left_widget.setMinimumWidth(480)
        left_widget.setMaximumWidth(600)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(left_widget)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(500)
        scroll.setMaximumWidth(620)
        root.addWidget(scroll)

        # ── Right panel ───────────────────────────────────────────────────
        right = QVBoxLayout()
        right.setSpacing(6)

        self._canvas = _LP3DCanvas()
        right.addWidget(self._canvas, stretch=1)

        # Controls row: view angle + iso-plane slider
        ctrl_group = QGroupBox("Điều khiển")
        ctrl_outer = QVBoxLayout(ctrl_group)
        ctrl_outer.setSpacing(6)

        # View angle row
        angle_row = QHBoxLayout()
        angle_row.setSpacing(8)

        angle_row.addWidget(QLabel("Elevation:"))
        self._spin_elev = QDoubleSpinBox()
        self._spin_elev.setRange(-90.0, 90.0)
        self._spin_elev.setValue(25.0)
        self._spin_elev.setSingleStep(5.0)
        self._spin_elev.setDecimals(0)
        self._spin_elev.setSuffix("°")
        self._spin_elev.setFixedWidth(80)
        self._spin_elev.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self._spin_elev.valueChanged.connect(self._on_view_changed)
        angle_row.addWidget(self._spin_elev)

        angle_row.addSpacing(12)
        angle_row.addWidget(QLabel("Azimuth:"))
        self._spin_azim = QDoubleSpinBox()
        self._spin_azim.setRange(-180.0, 180.0)
        self._spin_azim.setValue(-60.0)
        self._spin_azim.setSingleStep(10.0)
        self._spin_azim.setDecimals(0)
        self._spin_azim.setSuffix("°")
        self._spin_azim.setFixedWidth(80)
        self._spin_azim.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self._spin_azim.valueChanged.connect(self._on_view_changed)
        angle_row.addWidget(self._spin_azim)
        angle_row.addStretch()
        ctrl_outer.addLayout(angle_row)

        # Iso-plane slider row
        iso_row = QHBoxLayout()
        iso_row.setSpacing(8)

        self._lbl_k = QLabel("k = 0.00")
        self._lbl_k.setFixedWidth(100)
        self._lbl_k.setStyleSheet("font-weight: bold; font-size: 14px;")
        iso_row.addWidget(self._lbl_k)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 1000)
        self._slider.setValue(0)
        self._slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._slider.setTickInterval(100)
        self._slider.valueChanged.connect(self._on_slider_changed)
        iso_row.addWidget(self._slider, stretch=1)

        self._chk_show_iso = QPushButton("Mặt phẳng Z = k")
        self._chk_show_iso.setCheckable(True)
        self._chk_show_iso.setChecked(False)
        self._chk_show_iso.clicked.connect(self._on_slider_changed)
        iso_row.addWidget(self._chk_show_iso)

        ctrl_outer.addLayout(iso_row)
        right.addWidget(ctrl_group)

        right_widget = QWidget()
        right_widget.setLayout(right)
        root.addWidget(right_widget, stretch=1)

        # Initialize with existing constraints
        for ct in engine.problem.constraints:
            self._add_constraint_row(ct)

        # Connect auto-update signals
        self._spin_c1.valueChanged.connect(self._on_input_changed)
        self._spin_c2.valueChanged.connect(self._on_input_changed)
        self._spin_c3.valueChanged.connect(self._on_input_changed)
        self._combo_sense.currentIndexChanged.connect(self._on_input_changed)

    @staticmethod
    def _make_coef_spin(value: float) -> QDoubleSpinBox:
        sp = QDoubleSpinBox()
        sp.setRange(-9999.0, 9999.0)
        sp.setDecimals(2)
        sp.setValue(value)
        sp.setSingleStep(0.5)
        sp.setFixedWidth(64)
        sp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sp.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        return sp

    # ── Constraint management ─────────────────────────────────────────────

    def _add_constraint(self) -> None:
        if len(self._constraint_rows) >= MAX_CONSTRAINTS:
            return
        self._add_constraint_row(Constraint3D())

    def _add_constraint_row(self, c: Constraint3D) -> None:
        idx = len(self._constraint_rows) + 1
        row = _ConstraintRow3D(idx, c)
        row.changed.connect(self._on_input_changed)
        row.remove_requested.connect(lambda r=row: self._remove_constraint(r))
        self._constraint_rows.append(row)
        self._constraints_container.addWidget(row)
        self._update_add_button()

    def _remove_constraint(self, row: _ConstraintRow3D) -> None:
        if row in self._constraint_rows:
            self._constraint_rows.remove(row)
            self._constraints_container.removeWidget(row)
            row.deleteLater()
            for i, r in enumerate(self._constraint_rows):
                r.set_index(i + 1)
            self._update_add_button()
            self._on_input_changed()

    def _update_add_button(self) -> None:
        self._btn_add.setEnabled(
            len(self._constraint_rows) < MAX_CONSTRAINTS)

    def _collect_constraints(self) -> list[Constraint3D]:
        return [r.get_constraint() for r in self._constraint_rows]

    # ── Solve & render ────────────────────────────────────────────────────

    def _on_input_changed(self) -> None:
        self._sync_engine()

    def _sync_engine(self) -> None:
        self._engine.set_objective(
            self._spin_c1.value(),
            self._spin_c2.value(),
            self._spin_c3.value(),
            self._combo_sense.currentText(),
        )
        self._engine.set_constraints(self._collect_constraints())

    def _on_solve(self) -> None:
        self._sync_engine()
        result = self._engine.solve()
        self._result = result

        # Update slider range
        if result.feasible and result.vertices:
            z_vals = [v.obj for v in result.vertices]
            z_min = min(z_vals)
            z_max = max(z_vals)
            margin = max(abs(z_max - z_min) * 0.3, 1.0)
            self._slider_z_min = z_min - margin
            self._slider_z_max = z_max + margin
            self._slider.setValue(500)
        else:
            self._slider_z_min = 0.0
            self._slider_z_max = 10.0

        # Update result label
        if not result.feasible:
            self._lbl_result.setText(f"⚠ {result.message}")
            self._lbl_result.setStyleSheet(
                "font-size: 14px; color: #E74C3C; padding: 4px;"
                " font-weight: bold;")
        else:
            opt = result.optimal_vertices
            if opt:
                pts = ", ".join(
                    f"({v.x:.{self._precision}g}, {v.y:.{self._precision}g}, "
                    f"{v.z:.{self._precision}g})"
                    for v in opt
                )
                msg = (
                    f"✓ Giá trị tối ưu: Z* = "
                    f"{result.optimal_value:.{self._precision}g}\n"
                    f"  Tại đỉnh: {pts}"
                )
                if len(opt) > 1:
                    msg += ("\n  (Nghiệm tối ưu trên cạnh/mặt"
                            " nối các đỉnh trên)")
            else:
                msg = "Miền nghiệm rỗng."
            self._lbl_result.setText(msg)
            self._lbl_result.setStyleSheet(
                "font-size: 14px; color: #27AE60; padding: 4px;"
                " font-weight: bold;")

        # Update vertex table
        self._vertex_table.populate(result.vertices, self._precision)

        # Render graph
        self._render_canvas()

    def _on_slider_changed(self) -> None:
        if self._result is None:
            return
        iso_k = self._current_iso_k() if self._chk_show_iso.isChecked() else None
        if iso_k is not None:
            self._lbl_k.setText(f"k = {iso_k:.2f}")
        else:
            self._lbl_k.setText("k = —")
        self._render_canvas()

    def _on_view_changed(self) -> None:
        if self._result is None:
            return
        self._render_canvas()

    def _render_canvas(self) -> None:
        if self._result is None:
            return
        iso_k = (self._current_iso_k()
                 if self._chk_show_iso.isChecked() else None)
        self._canvas.render(
            self._engine, self._result, iso_k, self._precision,
            elev=self._spin_elev.value(),
            azim=self._spin_azim.value(),
        )

    def _current_iso_k(self) -> float:
        t = self._slider.value() / 1000.0
        z_min = getattr(self, "_slider_z_min", 0.0)
        z_max = getattr(self, "_slider_z_max", 10.0)
        return z_min + t * (z_max - z_min)

    # ── State ─────────────────────────────────────────────────────────────

    def get_view_state(self) -> dict[str, Any]:
        return {
            "slider_pos": self._slider.value(),
            "show_iso": self._chk_show_iso.isChecked(),
            "elev": self._spin_elev.value(),
            "azim": self._spin_azim.value(),
        }

    def restore_view_state(self, state: dict[str, Any]) -> None:
        self._slider.setValue(state.get("slider_pos", 0))
        self._chk_show_iso.setChecked(state.get("show_iso", False))
        self._spin_elev.setValue(state.get("elev", 25.0))
        self._spin_azim.setValue(state.get("azim", -60.0))


# ─── Module class ─────────────────────────────────────────────────────────────


class LinearProgramming3DModule(BaseModule):
    """IIMP module: Graphical LP solver for 3-variable problems."""

    def __init__(self, manifest: dict, context: Any) -> None:
        super().__init__(manifest, context)
        self._engine = LP3DEngine()
        self._view: _LP3DView | None = None

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def on_load(self) -> None:
        self.context.logger.info("LinearProgramming3DModule loaded.")

    def build_view(self) -> QWidget:
        self._view = _LP3DView(self._engine, self.context)
        return self._view  # type: ignore[return-value]

    def on_activate(self) -> None:
        self.context.logger.info("LinearProgramming3DModule activated.")

    def on_deactivate(self) -> None:
        self.context.logger.info("LinearProgramming3DModule deactivated.")

    def on_unload(self) -> None:
        self._view = None
        self.context.logger.info("LinearProgramming3DModule unloaded.")

    # ── State ─────────────────────────────────────────────────────────────

    def get_state(self) -> dict:
        state = self._engine.get_state()
        if self._view is not None:
            state["view"] = self._view.get_view_state()
        return state

    def restore_state(self, state: dict) -> None:
        self._engine.restore_state(state)
        if self._view is not None:
            for ct in self._engine.problem.constraints:
                self._view._add_constraint_row(ct)
            view_state = state.get("view", {})
            self._view.restore_view_state(view_state)

    # ── Export ────────────────────────────────────────────────────────────

    def export(self, target_path: str, export_type: str = "default") -> None:
        if self._view is not None:
            self._view._canvas.export_png(target_path)
            self.context.logger.info(f"Exported LP 3D graph to {target_path}")
