"""Linear Programming 2D — Giải bài toán QHTT 2 biến bằng đồ thị v1.0.0

Cho phép người dùng:
  1. Nhập hàm mục tiêu Z = c₁X₁ + c₂X₂ (max hoặc min)
  2. Ràng buộc không âm X₁ ≥ 0, X₂ ≥ 0 (bắt buộc)
  3. Thêm tối đa 10 ràng buộc dạng a·X₁ + b·X₂ ≤|≥|= rhs
  4. Vẽ miền nghiệm (feasible region)
  5. Bảng các đỉnh và giá trị hàm mục tiêu tại mỗi đỉnh
  6. Xác định điểm tối ưu
  7. Slider kéo đường đồng mức Z = k để trực quan hóa
"""
from __future__ import annotations

import io
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
        QSpinBox,
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
    from matplotlib.patches import Polygon as MplPolygon

    _MPL = True
except ImportError:  # pragma: no cover
    _MPL = False

from core.module_runtime.base_module import BaseModule
from core.module_runtime.module_context import ModuleContext

_WidgetBase = QWidget if _QT else object  # type: ignore[misc]

# ─── Constants ────────────────────────────────────────────────────────────────

MAX_CONSTRAINTS: int = 10
_BIG: float = 1e6  # clipping bound for unbounded regions
_EPS: float = 1e-9

# ─── Data classes ─────────────────────────────────────────────────────────────


@dataclass
class Constraint:
    """Single linear constraint: a*x + b*y  op  rhs."""

    a: float = 1.0
    b: float = 1.0
    op: str = "≤"  # one of "≤", "≥", "="
    rhs: float = 1.0

    def label(self, idx: int) -> str:
        """Human-readable label, 1-indexed."""
        parts: list[str] = []
        if self.a != 0:
            if self.a == 1:
                parts.append("X\u2081")
            elif self.a == -1:
                parts.append("-X\u2081")
            else:
                parts.append(f"{self.a:g}X\u2081")
        if self.b != 0:
            sign = " + " if self.b > 0 and parts else (" - " if self.b < 0 and parts else "")
            abs_b = abs(self.b)
            if not parts and self.b < 0:
                sign = "-"
            if abs_b == 1:
                parts.append(f"{sign}X\u2082")
            else:
                parts.append(f"{sign}{abs_b:g}X\u2082")
        if not parts:
            parts.append("0")
        return f"({''.join(parts)}) {self.op} {self.rhs:g}"


@dataclass
class LPProblem:
    """Full LP problem definition."""

    c1: float = 1.0
    c2: float = 1.0
    sense: str = "max"  # "max" or "min"
    constraints: list[Constraint] = field(default_factory=list)


@dataclass
class Vertex:
    """A vertex of the feasible region."""

    x: float
    y: float
    z: float  # objective value
    is_optimal: bool = False
    source: str = ""  # which constraints form this vertex


@dataclass
class LPResult:
    """Result of solving the LP."""

    feasible: bool = True
    bounded: bool = True
    vertices: list[Vertex] = field(default_factory=list)
    optimal_vertices: list[Vertex] = field(default_factory=list)
    optimal_value: float = 0.0
    polygon: list[tuple[float, float]] = field(default_factory=list)
    message: str = ""


# ─── Pure-Python LP Engine ────────────────────────────────────────────────────


class LPEngine:
    """Graphical LP solver for 2-variable problems — pure Python, no Qt."""

    def __init__(self) -> None:
        self.problem = LPProblem()

    # ── Problem setup ─────────────────────────────────────────────────────

    def set_objective(self, c1: float, c2: float, sense: str = "max") -> None:
        self.problem.c1 = c1
        self.problem.c2 = c2
        self.problem.sense = sense

    def set_constraints(self, constraints: list[Constraint]) -> None:
        self.problem.constraints = list(constraints)

    # ── Solver ────────────────────────────────────────────────────────────

    def solve(self) -> LPResult:
        """Find all vertices of the feasible region and identify the optimum."""
        prob = self.problem

        # Build list of all half-plane boundaries including x≥0, y≥0
        # Each line stored as (a, b, rhs, op) in standard form a*x + b*y op rhs
        lines: list[tuple[float, float, float, str]] = [
            (1.0, 0.0, 0.0, "≥"),  # x ≥ 0
            (0.0, 1.0, 0.0, "≥"),  # y ≥ 0
        ]
        for c in prob.constraints:
            lines.append((c.a, c.b, c.rhs, c.op))

        n = len(lines)
        if n < 2:
            return LPResult(feasible=False, message="Không đủ ràng buộc.")

        # Find all intersection points of pairs of lines
        raw_vertices: list[tuple[float, float, str]] = []
        for i, j in itertools.combinations(range(n), 2):
            pt = self._intersect(lines[i], lines[j])
            if pt is not None:
                src = self._line_label(lines[i], i) + " ∩ " + self._line_label(lines[j], j)
                raw_vertices.append((pt[0], pt[1], src))

        # Filter: keep only vertices in the feasible region
        feasible_pts: list[tuple[float, float, str]] = []
        for (vx, vy, src) in raw_vertices:
            if self._is_feasible(vx, vy, lines):
                feasible_pts.append((vx, vy, src))

        # Remove near-duplicates
        unique: list[tuple[float, float, str]] = []
        for pt in feasible_pts:
            if not any(abs(pt[0] - u[0]) < _EPS and abs(pt[1] - u[1]) < _EPS for u in unique):
                unique.append(pt)

        if not unique:
            return LPResult(feasible=False, message="Miền nghiệm rỗng — hệ ràng buộc vô nghiệm.")

        # Compute objective values
        vertices: list[Vertex] = []
        for (vx, vy, src) in unique:
            # Clamp -0.0 to 0.0 for clean display (X, Y are non-negative)
            vx = 0.0 if abs(vx) < _EPS else vx
            vy = 0.0 if abs(vy) < _EPS else vy
            z = prob.c1 * vx + prob.c2 * vy
            z = 0.0 if abs(z) < _EPS else z
            vertices.append(Vertex(x=vx, y=vy, z=z, source=src))

        # Convex hull ordering (for polygon drawing)
        polygon = self._convex_hull([(v.x, v.y) for v in vertices])

        # Find optimal
        if prob.sense == "max":
            opt_val = max(v.z for v in vertices)
        else:
            opt_val = min(v.z for v in vertices)

        opt_verts: list[Vertex] = []
        for v in vertices:
            if abs(v.z - opt_val) < _EPS:
                v.is_optimal = True
                opt_verts.append(v)

        return LPResult(
            feasible=True,
            bounded=True,
            vertices=sorted(vertices, key=lambda v: (v.x, v.y)),
            optimal_vertices=opt_verts,
            optimal_value=opt_val,
            polygon=polygon,
            message="Đã tìm được nghiệm tối ưu." if opt_verts else "",
        )

    # ── Geometry helpers ──────────────────────────────────────────────────

    @staticmethod
    def _intersect(
        l1: tuple[float, float, float, str],
        l2: tuple[float, float, float, str],
    ) -> tuple[float, float] | None:
        """Find intersection of two lines a₁x+b₁y=rhs₁ and a₂x+b₂y=rhs₂."""
        a1, b1, r1, _ = l1
        a2, b2, r2, _ = l2
        det = a1 * b2 - a2 * b1
        if abs(det) < _EPS:
            return None
        x = (r1 * b2 - r2 * b1) / det
        y = (a1 * r2 - a2 * r1) / det
        return (x, y)

    @staticmethod
    def _is_feasible(x: float, y: float, lines: list[tuple[float, float, float, str]]) -> bool:
        """Check if point (x, y) satisfies all constraints."""
        for a, b, rhs, op in lines:
            val = a * x + b * y
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
    def _line_label(line: tuple[float, float, float, str], idx: int) -> str:
        a, b, rhs, op = line
        if idx == 0:
            return "X\u2081=0"
        if idx == 1:
            return "X\u2082=0"
        parts: list[str] = []
        if a != 0:
            parts.append(f"{a:g}X\u2081")
        if b != 0:
            sign = "+" if b > 0 and parts else ""
            parts.append(f"{sign}{b:g}X\u2082")
        return f"{''.join(parts)}{op}{rhs:g}"

    @staticmethod
    def _convex_hull(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
        """Compute convex hull of 2D points (Andrew's monotone chain)."""
        pts = sorted(set(points))
        if len(pts) <= 1:
            return pts

        def cross(o: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
            return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

        lower: list[tuple[float, float]] = []
        for p in pts:
            while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
                lower.pop()
            lower.append(p)
        upper: list[tuple[float, float]] = []
        for p in reversed(pts):
            while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
                upper.pop()
            upper.append(p)
        return lower[:-1] + upper[:-1]

    # ── State ─────────────────────────────────────────────────────────────

    def get_state(self) -> dict[str, Any]:
        p = self.problem
        return {
            "c1": p.c1,
            "c2": p.c2,
            "sense": p.sense,
            "constraints": [
                {"a": c.a, "b": c.b, "op": c.op, "rhs": c.rhs}
                for c in p.constraints
            ],
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        self.problem.c1 = float(state.get("c1", 1.0))
        self.problem.c2 = float(state.get("c2", 1.0))
        self.problem.sense = state.get("sense", "max")
        raw = state.get("constraints", [])
        self.problem.constraints = [
            Constraint(
                a=float(c.get("a", 1)),
                b=float(c.get("b", 1)),
                op=c.get("op", "≤"),
                rhs=float(c.get("rhs", 1)),
            )
            for c in raw
        ]


# ─── UI: LP Graph Canvas ─────────────────────────────────────────────────────


class _LPCanvas(_WidgetBase):  # type: ignore[misc]
    """Matplotlib canvas for the feasible region, constraint lines, and iso-profit."""

    def __init__(self, parent: Any = None) -> None:
        if not _QT:  # pragma: no cover
            return
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if _MPL:
            self._figure = Figure(figsize=(8, 6), dpi=100)
            self._figure.patch.set_facecolor("#FAFBFC")
            self._ax = self._figure.add_subplot(111)
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
        engine: LPEngine,
        result: LPResult,
        iso_k: float | None = None,
        precision: int = 4,
    ) -> None:
        if not _MPL or self._ax is None:  # pragma: no cover
            return
        assert self._figure is not None and self._canvas is not None

        ax = self._ax
        ax.clear()
        ax.set_facecolor("#FAFBFC")

        prob = engine.problem

        # Determine plot bounds — include all constraint-line axis intercepts
        # so that every line is fully visible within the chart frame.
        intercept_x: list[float] = []
        intercept_y: list[float] = []
        for c in prob.constraints:
            # X-intercept: c.b == 0 → x = rhs/a;  else y=0 → x = rhs/a
            if abs(c.a) > _EPS:
                xi = c.rhs / c.a
                if xi >= 0:
                    intercept_x.append(xi)
            # Y-intercept: c.a == 0 → y = rhs/b;  else x=0 → y = rhs/b
            if abs(c.b) > _EPS:
                yi = c.rhs / c.b
                if yi >= 0:
                    intercept_y.append(yi)

        if result.feasible and result.polygon:
            all_x = [p[0] for p in result.polygon] + intercept_x
            all_y = [p[1] for p in result.polygon] + intercept_y
            x_max = max(all_x) * 1.15 + 1.0
            y_max = max(all_y) * 1.15 + 1.0
        elif intercept_x or intercept_y:
            x_max = max(intercept_x, default=10.0) * 1.15 + 1.0
            y_max = max(intercept_y, default=10.0) * 1.15 + 1.0
        else:
            x_max, y_max = 10.0, 10.0

        x_max = max(x_max, 2.0)
        y_max = max(y_max, 2.0)

        # Draw axes (the axes themselves represent X≥0, Y≥0 constraints)
        ax.spines["left"].set_position("zero")
        ax.spines["bottom"].set_position("zero")
        ax.spines["right"].set_visible(False)
        ax.spines["top"].set_visible(False)
        ax.spines["left"].set_color("#333")
        ax.spines["bottom"].set_color("#333")
        ax.spines["left"].set_linewidth(1.2)
        ax.spines["bottom"].set_linewidth(1.2)

        # Color palette for constraint lines
        colors = [
            "#E74C3C", "#2980B9", "#27AE60", "#8E44AD", "#F39C12",
            "#1ABC9C", "#E67E22", "#3498DB", "#9B59B6", "#2ECC71",
        ]

        # Draw each constraint line
        for i, c in enumerate(prob.constraints):
            color = colors[i % len(colors)]
            self._draw_constraint_line(ax, c, i + 1, color, x_max, y_max)

        # Draw feasible region polygon
        if result.feasible and result.polygon and len(result.polygon) >= 3:
            poly = MplPolygon(
                result.polygon,
                closed=True,
                facecolor="#AED6F1",
                edgecolor="#2471A3",
                alpha=0.35,
                lw=1.5,
                zorder=3,
                label="Miền nghiệm",
            )
            ax.add_patch(poly)

        # Draw vertices
        if result.feasible:
            for v in result.vertices:
                if v.is_optimal:
                    ax.plot(v.x, v.y, "r*", markersize=16, zorder=8,
                            label=f"Tối ưu ({v.x:.{precision}g}, {v.y:.{precision}g})")
                else:
                    ax.plot(v.x, v.y, "ko", markersize=6, zorder=7)
                ax.annotate(
                    f"({v.x:.{precision}g}, {v.y:.{precision}g})",
                    (v.x, v.y),
                    textcoords="offset points",
                    xytext=(8, 8),
                    fontsize=8,
                    color="#333",
                    zorder=9,
                )

        # Draw iso-profit/cost line
        if iso_k is not None and (abs(prob.c1) > _EPS or abs(prob.c2) > _EPS):
            self._draw_iso_line(ax, prob.c1, prob.c2, iso_k, x_max, y_max)

        # Axis labels and grid
        ax.set_xlabel("X\u2081", fontsize=11, fontweight="bold")
        ax.set_ylabel("X\u2082", fontsize=11, fontweight="bold", rotation=0)
        ax.xaxis.set_label_coords(1.02, -0.02)
        ax.yaxis.set_label_coords(-0.02, 1.02)
        ax.set_xlim(0, x_max)
        ax.set_ylim(0, y_max)
        ax.grid(False)

        sense_label = "max" if prob.sense == "max" else "min"
        title = f"Z = {prob.c1:g}X\u2081 + {prob.c2:g}X\u2082 → {sense_label}"
        if result.feasible and result.optimal_vertices:
            title += f"  |  Z* = {result.optimal_value:.{precision}g}"
        ax.set_title(title, fontsize=12, fontweight="bold", pad=10)

        ax.legend(fontsize=8, loc="upper right", framealpha=0.9)
        self._figure.tight_layout(pad=1.5)
        self._canvas.draw()

    @staticmethod
    def _draw_constraint_line(
        ax: Any, c: Constraint, idx: int, color: str,
        x_max: float, y_max: float,
    ) -> None:
        """Draw a single constraint line across the visible range."""
        a, b, rhs = c.a, c.b, c.rhs
        lbl = c.label(idx)

        if abs(b) > _EPS and abs(a) > _EPS:
            # General case: y = (rhs - a*x) / b
            x_pts = np.linspace(0, x_max, 400)
            y_pts = (rhs - a * x_pts) / b
            mask = (y_pts >= 0) & (y_pts <= y_max * 1.2) & (x_pts >= 0)
            ax.plot(x_pts[mask], y_pts[mask], color=color, lw=1.8, zorder=5, label=lbl)
        elif abs(b) < _EPS and abs(a) > _EPS:
            # Vertical line: x = rhs / a
            x_val = rhs / a
            if 0 <= x_val <= x_max:
                ax.axvline(x_val, color=color, lw=1.8, zorder=5, label=lbl)
        elif abs(a) < _EPS and abs(b) > _EPS:
            # Horizontal line: y = rhs / b
            y_val = rhs / b
            if 0 <= y_val <= y_max:
                ax.axhline(y_val, color=color, lw=1.8, zorder=5, label=lbl)

    @staticmethod
    def _draw_iso_line(
        ax: Any, c1: float, c2: float, k: float,
        x_max: float, y_max: float,
    ) -> None:
        """Draw the iso-profit/cost line c1*x + c2*y = k."""
        if abs(c2) > _EPS and abs(c1) > _EPS:
            x_pts = np.linspace(0, x_max, 400)
            y_pts = (k - c1 * x_pts) / c2
            mask = (y_pts >= 0) & (y_pts <= y_max * 1.2) & (x_pts >= 0)
            ax.plot(x_pts[mask], y_pts[mask], color="#FF6F00", lw=2.2,
                    linestyle="--", zorder=6, alpha=0.85,
                    label=f"Z = {k:.2f}")
        elif abs(c2) < _EPS and abs(c1) > _EPS:
            x_val = k / c1
            if x_val >= 0:
                ax.axvline(x_val, color="#FF6F00", lw=2.2, linestyle="--",
                           zorder=6, alpha=0.85, label=f"Z = {k:.2f}")
        elif abs(c1) < _EPS and abs(c2) > _EPS:
            y_val = k / c2
            if y_val >= 0:
                ax.axhline(y_val, color="#FF6F00", lw=2.2, linestyle="--",
                           zorder=6, alpha=0.85, label=f"Z = {k:.2f}")

    def export_png(self, path: str) -> None:
        if self._figure is not None:
            self._figure.savefig(path, dpi=150, bbox_inches="tight",
                                 facecolor="#FFFFFF")


# ─── UI: Constraint row widget ───────────────────────────────────────────────


class _ConstraintRow(_WidgetBase):  # type: ignore[misc]
    """A single constraint input row: a·x + b·y  op  rhs."""

    if _QT:
        changed = Signal()
        remove_requested = Signal()

    def __init__(self, idx: int, constraint: Constraint | None = None, parent: Any = None) -> None:
        if not _QT:  # pragma: no cover
            return
        super().__init__(parent)
        self.idx = idx
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 2, 0, 2)
        lay.setSpacing(4)

        self._lbl = QLabel(f"({idx})")
        self._lbl.setFixedWidth(26)
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._lbl)

        self._spin_a = self._make_spin(constraint.a if constraint else 1.0)
        lay.addWidget(self._spin_a)
        lbl_x = QLabel(" X\u2081 + ")
        lbl_x.setContentsMargins(2, 0, 2, 0)
        lay.addWidget(lbl_x)

        self._spin_b = self._make_spin(constraint.b if constraint else 1.0)
        lay.addWidget(self._spin_b)
        lbl_y = QLabel(" X\u2082 ")
        lbl_y.setContentsMargins(2, 0, 2, 0)
        lay.addWidget(lbl_y)

        self._combo_op = QComboBox()
        self._combo_op.addItems(["≤", "≥", "="])
        if constraint:
            idx_op = ["≤", "≥", "="].index(constraint.op) if constraint.op in ["≤", "≥", "="] else 0
            self._combo_op.setCurrentIndex(idx_op)
        self._combo_op.setFixedWidth(50)
        lay.addWidget(self._combo_op)

        self._spin_rhs = self._make_spin(constraint.rhs if constraint else 1.0)
        lay.addWidget(self._spin_rhs)

        lay.addSpacing(2)

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
        self._spin_a.valueChanged.connect(self.changed.emit)
        self._spin_b.valueChanged.connect(self.changed.emit)
        self._spin_rhs.valueChanged.connect(self.changed.emit)
        self._combo_op.currentIndexChanged.connect(self.changed.emit)

    @staticmethod
    def _make_spin(value: float) -> QDoubleSpinBox:
        sp = QDoubleSpinBox()
        sp.setRange(-9999.0, 9999.0)
        sp.setDecimals(2)
        sp.setValue(value)
        sp.setSingleStep(0.5)
        sp.setMinimumWidth(64)
        sp.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sp.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        return sp

    def get_constraint(self) -> Constraint:
        return Constraint(
            a=self._spin_a.value(),
            b=self._spin_b.value(),
            op=self._combo_op.currentText(),
            rhs=self._spin_rhs.value(),
        )

    def set_index(self, idx: int) -> None:
        self.idx = idx
        self._lbl.setText(f"({idx})")


# ─── UI: Vertex table ────────────────────────────────────────────────────────


class _VertexTable(_WidgetBase):  # type: ignore[misc]
    """Table showing vertices of the feasible region and objective values."""

    def __init__(self, parent: Any = None) -> None:
        if not _QT:  # pragma: no cover
            return
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["X\u2081", "X\u2082", "Z", "Tối ưu"])
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setStyleSheet(
            "QTableWidget { gridline-color: #DDE2E8; font-size: 14px; }"
            "QHeaderView::section { background-color: #2C3E50; color: #FFF;"
            " padding: 8px; font-weight: bold; font-size: 15px; }"
        )
        hdr = self._table.horizontalHeader()
        hdr.setStretchLastSection(False)
        for col in range(4):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._table)

    def populate(self, vertices: list[Vertex], precision: int = 4) -> None:
        self._table.setRowCount(0)
        for v in vertices:
            row = self._table.rowCount()
            self._table.insertRow(row)
            items = [
                f"{v.x:.{precision}g}",
                f"{v.y:.{precision}g}",
                f"{v.z:.{precision}g}",
                "★" if v.is_optimal else "",
            ]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if v.is_optimal:
                    item.setBackground(
                        __import__("PySide6.QtGui", fromlist=["QColor"]).QColor("#FDEDEC"))
                self._table.setItem(row, col, item)


# ─── UI: Main module view ────────────────────────────────────────────────────


class _LP2DView(_WidgetBase):  # type: ignore[misc]
    """Main view: left panel (inputs + vertex table) | right panel (graph + slider)."""

    def __init__(self, engine: LPEngine, context: ModuleContext, parent: Any = None) -> None:
        if not _QT:  # pragma: no cover
            return
        super().__init__(parent)
        self._engine = engine
        self._context = context
        self._precision = 4
        self._iso_k: float | None = None
        self._result: LPResult | None = None
        self._constraint_rows: list[_ConstraintRow] = []

        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # ── Left panel ────────────────────────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(8)

        # Objective function
        obj_group = QGroupBox("Hàm mục tiêu")
        obj_lay = QGridLayout(obj_group)
        obj_lay.setSpacing(6)

        obj_lay.addWidget(QLabel("Z ="), 0, 0)
        self._spin_c1 = self._make_coef_spin(engine.problem.c1)
        obj_lay.addWidget(self._spin_c1, 0, 1)
        obj_lay.addWidget(QLabel(" X\u2081 + "), 0, 2)
        self._spin_c2 = self._make_coef_spin(engine.problem.c2)
        obj_lay.addWidget(self._spin_c2, 0, 3)
        obj_lay.addWidget(QLabel(" X\u2082  →"), 0, 4)

        self._combo_sense = QComboBox()
        self._combo_sense.addItems(["max", "min"])
        self._combo_sense.setCurrentText(engine.problem.sense)
        self._combo_sense.setFixedWidth(60)
        obj_lay.addWidget(self._combo_sense, 0, 5)

        left.addWidget(obj_group)

        # Non-negativity note
        nn_label = QLabel("  Ràng buộc không âm:  X\u2081 ≥ 0 ,  X\u2082 ≥ 0")
        nn_label.setStyleSheet("color: #7F8C8D; font-style: italic; font-size: 13px;")
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
        left.addWidget(self._btn_solve, alignment=Qt.AlignmentFlag.AlignCenter)

        # Result label
        self._lbl_result = QLabel("")
        self._lbl_result.setStyleSheet("font-size: 14px; color: #2C3E50; padding: 4px;")
        self._lbl_result.setWordWrap(True)
        left.addWidget(self._lbl_result)

        # Vertex table
        vtx_group = QGroupBox("Các điểm góc và giá trị hàm mục tiêu")
        vtx_lay = QVBoxLayout(vtx_group)
        self._vertex_table = _VertexTable()
        vtx_lay.addWidget(self._vertex_table)
        left.addWidget(vtx_group)

        left.addStretch()

        left_widget = QWidget()
        left_widget.setLayout(left)
        left_widget.setMinimumWidth(440)
        left_widget.setMaximumWidth(540)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(left_widget)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(460)
        scroll.setMaximumWidth(560)
        root.addWidget(scroll)

        # ── Right panel ───────────────────────────────────────────────────
        right = QVBoxLayout()
        right.setSpacing(6)

        self._canvas = _LPCanvas()
        right.addWidget(self._canvas, stretch=1)

        # Iso-line slider
        slider_group = QGroupBox("Đường đồng mức Z = k")
        slider_lay = QHBoxLayout(slider_group)
        slider_lay.setSpacing(8)

        self._lbl_k = QLabel("k = 0.00")
        self._lbl_k.setFixedWidth(100)
        self._lbl_k.setStyleSheet("font-weight: bold; font-size: 14px;")
        slider_lay.addWidget(self._lbl_k)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 1000)
        self._slider.setValue(0)
        self._slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._slider.setTickInterval(100)
        self._slider.valueChanged.connect(self._on_slider_changed)
        slider_lay.addWidget(self._slider, stretch=1)

        self._chk_show_iso = QPushButton("Hiện đường đồng mức")
        self._chk_show_iso.setCheckable(True)
        self._chk_show_iso.setChecked(False)
        self._chk_show_iso.clicked.connect(self._on_slider_changed)
        slider_lay.addWidget(self._chk_show_iso)

        right.addWidget(slider_group)

        right_widget = QWidget()
        right_widget.setLayout(right)
        root.addWidget(right_widget, stretch=1)

        # Initialize with default constraints if engine has some
        for c in engine.problem.constraints:
            self._add_constraint_row(c)

        # Connect signals for auto-update
        self._spin_c1.valueChanged.connect(self._on_input_changed)
        self._spin_c2.valueChanged.connect(self._on_input_changed)
        self._combo_sense.currentIndexChanged.connect(self._on_input_changed)

    @staticmethod
    def _make_coef_spin(value: float) -> QDoubleSpinBox:
        sp = QDoubleSpinBox()
        sp.setRange(-9999.0, 9999.0)
        sp.setDecimals(2)
        sp.setValue(value)
        sp.setSingleStep(0.5)
        sp.setFixedWidth(72)
        sp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sp.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        return sp

    # ── Constraint management ─────────────────────────────────────────────

    def _add_constraint(self) -> None:
        if len(self._constraint_rows) >= MAX_CONSTRAINTS:
            return
        self._add_constraint_row(Constraint())

    def _add_constraint_row(self, c: Constraint) -> None:
        idx = len(self._constraint_rows) + 1
        row = _ConstraintRow(idx, c)
        row.changed.connect(self._on_input_changed)
        row.remove_requested.connect(lambda r=row: self._remove_constraint(r))
        self._constraint_rows.append(row)
        self._constraints_container.addWidget(row)
        self._update_add_button()

    def _remove_constraint(self, row: _ConstraintRow) -> None:
        if row in self._constraint_rows:
            self._constraint_rows.remove(row)
            self._constraints_container.removeWidget(row)
            row.deleteLater()
            # Re-index
            for i, r in enumerate(self._constraint_rows):
                r.set_index(i + 1)
            self._update_add_button()
            self._on_input_changed()

    def _update_add_button(self) -> None:
        self._btn_add.setEnabled(len(self._constraint_rows) < MAX_CONSTRAINTS)

    def _collect_constraints(self) -> list[Constraint]:
        return [r.get_constraint() for r in self._constraint_rows]

    # ── Solve & render ────────────────────────────────────────────────────

    def _on_input_changed(self) -> None:
        """Auto re-solve when inputs change."""
        self._sync_engine()

    def _sync_engine(self) -> None:
        self._engine.set_objective(
            self._spin_c1.value(),
            self._spin_c2.value(),
            self._combo_sense.currentText(),
        )
        self._engine.set_constraints(self._collect_constraints())

    def _on_solve(self) -> None:
        self._sync_engine()
        result = self._engine.solve()
        self._result = result

        # Update slider range based on vertex Z values
        if result.feasible and result.vertices:
            z_vals = [v.z for v in result.vertices]
            z_min = min(z_vals)
            z_max = max(z_vals)
            margin = max(abs(z_max - z_min) * 0.3, 1.0)
            self._slider_z_min = z_min - margin
            self._slider_z_max = z_max + margin
            self._slider.setValue(500)  # middle
        else:
            self._slider_z_min = 0.0
            self._slider_z_max = 10.0

        # Update result label
        if not result.feasible:
            self._lbl_result.setText(f"⚠ {result.message}")
            self._lbl_result.setStyleSheet(
                "font-size: 14px; color: #E74C3C; padding: 4px; font-weight: bold;")
        else:
            opt = result.optimal_vertices
            if opt:
                pts = ", ".join(f"({v.x:.{self._precision}g}, {v.y:.{self._precision}g})" for v in opt)
                msg = (f"✓ Giá trị tối ưu: Z* = {result.optimal_value:.{self._precision}g}\n"
                       f"  Tại đỉnh: {pts}")
                if len(opt) > 1:
                    msg += "\n  (Nghiệm tối ưu trên cạnh nối các đỉnh trên)"
            else:
                msg = "Miền nghiệm rỗng."
            self._lbl_result.setText(msg)
            self._lbl_result.setStyleSheet(
                "font-size: 14px; color: #27AE60; padding: 4px; font-weight: bold;")

        # Update vertex table
        self._vertex_table.populate(result.vertices, self._precision)

        # Render graph
        iso_k = self._current_iso_k() if self._chk_show_iso.isChecked() else None
        self._canvas.render(self._engine, result, iso_k, self._precision)

    def _on_slider_changed(self) -> None:
        if self._result is None:
            return
        iso_k = self._current_iso_k() if self._chk_show_iso.isChecked() else None
        if iso_k is not None:
            self._lbl_k.setText(f"k = {iso_k:.2f}")
        else:
            self._lbl_k.setText("k = —")
        self._canvas.render(self._engine, self._result, iso_k, self._precision)

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
        }

    def restore_view_state(self, state: dict[str, Any]) -> None:
        self._slider.setValue(state.get("slider_pos", 0))
        self._chk_show_iso.setChecked(state.get("show_iso", False))


# ─── Module class ─────────────────────────────────────────────────────────────


class LinearProgramming2DModule(BaseModule):
    """IIMP module: Graphical LP solver for 2-variable problems."""

    def __init__(self, manifest: dict, context: Any) -> None:
        super().__init__(manifest, context)
        self._engine = LPEngine()
        self._view: _LP2DView | None = None

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def on_load(self) -> None:
        self.context.logger.info("LinearProgramming2DModule loaded.")

    def build_view(self) -> QWidget:
        self._view = _LP2DView(self._engine, self.context)
        return self._view  # type: ignore[return-value]

    def on_activate(self) -> None:
        self.context.logger.info("LinearProgramming2DModule activated.")

    def on_deactivate(self) -> None:
        self.context.logger.info("LinearProgramming2DModule deactivated.")

    def on_unload(self) -> None:
        self._view = None
        self.context.logger.info("LinearProgramming2DModule unloaded.")

    # ── State ─────────────────────────────────────────────────────────────

    def get_state(self) -> dict:
        state = self._engine.get_state()
        if self._view is not None:
            state["view"] = self._view.get_view_state()
        return state

    def restore_state(self, state: dict) -> None:
        self._engine.restore_state(state)
        if self._view is not None:
            # Rebuild constraint rows from engine state
            for c in self._engine.problem.constraints:
                self._view._add_constraint_row(c)
            view_state = state.get("view", {})
            self._view.restore_view_state(view_state)

    # ── Export ────────────────────────────────────────────────────────────

    def export(self, target_path: str, export_type: str = "default") -> None:
        if self._view is not None:
            self._view._canvas.export_png(target_path)
            self.context.logger.info(f"Exported LP graph to {target_path}")
