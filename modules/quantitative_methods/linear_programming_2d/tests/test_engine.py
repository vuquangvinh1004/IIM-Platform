"""Unit tests for LPEngine — pure Python, no Qt dependency."""
from __future__ import annotations

import pytest

from modules.quantitative_methods.linear_programming_2d.module import (
    Constraint,
    LPEngine,
    LPResult,
    Vertex,
)

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _engine_with(
    c1: float, c2: float, sense: str, constraints: list[Constraint],
) -> tuple[LPEngine, LPResult]:
    eng = LPEngine()
    eng.set_objective(c1, c2, sense)
    eng.set_constraints(constraints)
    result = eng.solve()
    return eng, result


# ─── Basic feasibility ───────────────────────────────────────────────────────


class TestFeasibility:
    """Tests for feasible / infeasible detection."""

    def test_simple_feasible(self) -> None:
        """x + y ≤ 4, x ≥ 0, y ≥ 0 → feasible."""
        _, r = _engine_with(1, 1, "max", [Constraint(1, 1, "≤", 4)])
        assert r.feasible

    def test_contradictory_infeasible(self) -> None:
        """x ≥ 5  and  x ≤ 2  (with y ≥ 0) → infeasible."""
        _, r = _engine_with(1, 0, "max", [
            Constraint(1, 0, "≥", 5),
            Constraint(1, 0, "≤", 2),
        ])
        assert not r.feasible

    def test_no_constraints_feasible(self) -> None:
        """Only non-negativity → still feasible (the origin is feasible)."""
        _, r = _engine_with(1, 1, "max", [])
        # With only x≥0 and y≥0, the only vertex is (0,0)
        assert r.feasible
        assert len(r.vertices) == 1
        assert abs(r.vertices[0].x) < 1e-9
        assert abs(r.vertices[0].y) < 1e-9


# ─── Classic LP problems ─────────────────────────────────────────────────────


class TestClassicProblems:
    """Well-known textbook LP problems."""

    def test_max_simple_triangle(self) -> None:
        """max Z = x + y  s.t.  x + y ≤ 4, x ≥ 0, y ≥ 0.
        Feasible region is triangle (0,0), (4,0), (0,4).
        Optimal at Z* = 4 at (4,0) or (0,4)."""
        _, r = _engine_with(1, 1, "max", [Constraint(1, 1, "≤", 4)])
        assert r.feasible
        assert abs(r.optimal_value - 4.0) < 1e-6
        assert len(r.vertices) == 3

    def test_max_two_constraints(self) -> None:
        """max Z = 5x + 3y  s.t.  x + y ≤ 4, 5x + 3y ≤ 15, x ≥ 0, y ≥ 0.
        From the user's reference image: vertices (0,0), (3,0), (1.5,2.5), (0,4).
        Optimal: Z* = 15 at (3, 0)."""
        _, r = _engine_with(5, 3, "max", [
            Constraint(1, 1, "≤", 4),
            Constraint(5, 3, "≤", 15),
        ])
        assert r.feasible
        assert abs(r.optimal_value - 15.0) < 1e-6
        # Check (3, 0) is among optimal vertices
        opt_pts = [(v.x, v.y) for v in r.optimal_vertices]
        assert any(abs(x - 3) < 1e-6 and abs(y) < 1e-6 for x, y in opt_pts)

    def test_min_problem(self) -> None:
        """min Z = 2x + 3y  s.t.  x + y ≤ 6, x ≤ 4, y ≤ 5, x ≥ 0, y ≥ 0.
        Minimum at (0, 0) → Z* = 0."""
        _, r = _engine_with(2, 3, "min", [
            Constraint(1, 1, "≤", 6),
            Constraint(1, 0, "≤", 4),
            Constraint(0, 1, "≤", 5),
        ])
        assert r.feasible
        assert abs(r.optimal_value) < 1e-6
        opt_pts = [(v.x, v.y) for v in r.optimal_vertices]
        assert any(abs(x) < 1e-6 and abs(y) < 1e-6 for x, y in opt_pts)

    def test_multiple_optimal_vertices(self) -> None:
        """max Z = x + y  s.t.  x + y ≤ 4, x ≥ 0, y ≥ 0.
        Optimal at (4,0) AND (0,4) → both with Z* = 4."""
        _, r = _engine_with(1, 1, "max", [Constraint(1, 1, "≤", 4)])
        assert r.feasible
        assert len(r.optimal_vertices) == 2

    def test_single_optimal_vertex(self) -> None:
        """max Z = 3x + 2y  s.t.  x + y ≤ 4, x ≤ 3, y ≤ 3, x ≥ 0, y ≥ 0.
        Optimal at (3, 1) → Z* = 11."""
        _, r = _engine_with(3, 2, "max", [
            Constraint(1, 1, "≤", 4),
            Constraint(1, 0, "≤", 3),
            Constraint(0, 1, "≤", 3),
        ])
        assert r.feasible
        assert abs(r.optimal_value - 11.0) < 1e-6
        assert len(r.optimal_vertices) == 1
        v = r.optimal_vertices[0]
        assert abs(v.x - 3.0) < 1e-6
        assert abs(v.y - 1.0) < 1e-6


# ─── Vertex counting ─────────────────────────────────────────────────────────


class TestVertices:
    """Tests for vertex enumeration."""

    def test_triangle_has_3_vertices(self) -> None:
        _, r = _engine_with(1, 1, "max", [Constraint(1, 1, "≤", 4)])
        assert len(r.vertices) == 3

    def test_quadrilateral_has_4_vertices(self) -> None:
        """x + y ≤ 4, x ≤ 3 → polygon (0,0), (3,0), (3,1), (0,4)."""
        _, r = _engine_with(1, 1, "max", [
            Constraint(1, 1, "≤", 4),
            Constraint(1, 0, "≤", 3),
        ])
        assert r.feasible
        assert len(r.vertices) == 4

    def test_pentagon(self) -> None:
        """x ≤ 3, y ≤ 3, x + y ≤ 5 → 5 vertices."""
        _, r = _engine_with(1, 1, "max", [
            Constraint(1, 0, "≤", 3),
            Constraint(0, 1, "≤", 3),
            Constraint(1, 1, "≤", 5),
        ])
        assert r.feasible
        assert len(r.vertices) == 5

    def test_vertex_coordinates(self) -> None:
        """x + y ≤ 4 → vertices at (0,0), (4,0), (0,4)."""
        _, r = _engine_with(1, 1, "max", [Constraint(1, 1, "≤", 4)])
        pts = sorted([(v.x, v.y) for v in r.vertices])
        assert abs(pts[0][0]) < 1e-6 and abs(pts[0][1]) < 1e-6
        assert abs(pts[1][0]) < 1e-6 and abs(pts[1][1] - 4.0) < 1e-6
        assert abs(pts[2][0] - 4.0) < 1e-6 and abs(pts[2][1]) < 1e-6


# ─── Convex hull ──────────────────────────────────────────────────────────────


class TestConvexHull:
    """Tests for the convex hull output."""

    def test_polygon_not_empty(self) -> None:
        _, r = _engine_with(1, 1, "max", [Constraint(1, 1, "≤", 4)])
        assert len(r.polygon) >= 3

    def test_polygon_vertices_match(self) -> None:
        """All polygon points should be feasible vertices."""
        _, r = _engine_with(1, 1, "max", [Constraint(1, 1, "≤", 4)])
        vert_set = {(round(v.x, 8), round(v.y, 8)) for v in r.vertices}
        for px, py in r.polygon:
            assert (round(px, 8), round(py, 8)) in vert_set


# ─── Constraint types ────────────────────────────────────────────────────────


class TestConstraintTypes:
    """Tests for ≤, ≥, = operators."""

    def test_ge_constraint(self) -> None:
        """min Z = x + y  s.t.  x + y ≥ 2, x ≤ 5, y ≤ 5."""
        _, r = _engine_with(1, 1, "min", [
            Constraint(1, 1, "≥", 2),
            Constraint(1, 0, "≤", 5),
            Constraint(0, 1, "≤", 5),
        ])
        assert r.feasible
        assert abs(r.optimal_value - 2.0) < 1e-6

    def test_eq_constraint(self) -> None:
        """max Z = x + y  s.t.  x + y = 4, x ≥ 0, y ≥ 0.
        Only two feasible vertices: (4,0) and (0,4)."""
        _, r = _engine_with(1, 1, "max", [Constraint(1, 1, "=", 4)])
        assert r.feasible
        assert len(r.vertices) == 2
        assert abs(r.optimal_value - 4.0) < 1e-6

    def test_mixed_operators(self) -> None:
        """x + y ≤ 6, x ≥ 1, y ≥ 1."""
        _, r = _engine_with(1, 1, "max", [
            Constraint(1, 1, "≤", 6),
            Constraint(1, 0, "≥", 1),
            Constraint(0, 1, "≥", 1),
        ])
        assert r.feasible
        assert abs(r.optimal_value - 6.0) < 1e-6


# ─── State persistence ───────────────────────────────────────────────────────


class TestState:
    """Tests for get_state / restore_state."""

    def test_round_trip(self) -> None:
        eng = LPEngine()
        eng.set_objective(3, 5, "min")
        eng.set_constraints([
            Constraint(2, 1, "≤", 10),
            Constraint(1, 3, "≥", 6),
        ])
        state = eng.get_state()

        eng2 = LPEngine()
        eng2.restore_state(state)
        assert eng2.problem.c1 == 3.0
        assert eng2.problem.c2 == 5.0
        assert eng2.problem.sense == "min"
        assert len(eng2.problem.constraints) == 2
        assert eng2.problem.constraints[0].a == 2.0
        assert eng2.problem.constraints[1].op == "≥"

    def test_restore_empty_state(self) -> None:
        eng = LPEngine()
        eng.restore_state({})
        assert eng.problem.c1 == 1.0
        assert eng.problem.sense == "max"


# ─── Constraint label ────────────────────────────────────────────────────────


class TestConstraintLabel:
    """Tests for human-readable constraint labels."""

    def test_standard_label(self) -> None:
        c = Constraint(5, 3, "≤", 15)
        lbl = c.label(1)
        assert "5X₁" in lbl
        assert "3X₂" in lbl
        assert "≤" in lbl
        assert "15" in lbl

    def test_negative_coefficient(self) -> None:
        c = Constraint(1, -2, "≥", 3)
        lbl = c.label(1)
        assert "X₁" in lbl
        assert "2X₂" in lbl
        assert "≥" in lbl

    def test_unit_coefficients(self) -> None:
        c = Constraint(1, 1, "≤", 4)
        lbl = c.label(1)
        assert "X₁" in lbl
        assert "X₂" in lbl

    def test_zero_coefficient(self) -> None:
        c = Constraint(0, 3, "≤", 9)
        lbl = c.label(1)
        assert "3X₂" in lbl
        assert "X₁" not in lbl


# ─── Edge cases ───────────────────────────────────────────────────────────────


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_single_point_feasible(self) -> None:
        """x = 2, y = 3 → single point."""
        _, r = _engine_with(1, 1, "max", [
            Constraint(1, 0, "=", 2),
            Constraint(0, 1, "=", 3),
        ])
        assert r.feasible
        assert len(r.vertices) == 1
        assert abs(r.vertices[0].x - 2.0) < 1e-6
        assert abs(r.vertices[0].y - 3.0) < 1e-6

    def test_objective_zero_coefficients(self) -> None:
        """Z = 0·x + 0·y → all vertices have Z = 0."""
        _, r = _engine_with(0, 0, "max", [Constraint(1, 1, "≤", 4)])
        assert r.feasible
        assert abs(r.optimal_value) < 1e-6

    def test_vertical_constraint_line(self) -> None:
        """x ≤ 3 → vertical boundary."""
        _, r = _engine_with(1, 0, "max", [
            Constraint(1, 0, "≤", 3),
            Constraint(0, 1, "≤", 5),
        ])
        assert r.feasible
        assert abs(r.optimal_value - 3.0) < 1e-6

    def test_horizontal_constraint_line(self) -> None:
        """y ≤ 4 → horizontal boundary."""
        _, r = _engine_with(0, 1, "max", [
            Constraint(0, 1, "≤", 4),
            Constraint(1, 0, "≤", 5),
        ])
        assert r.feasible
        assert abs(r.optimal_value - 4.0) < 1e-6

    def test_many_constraints(self) -> None:
        """10 constraints — the maximum allowed."""
        constraints = [Constraint(1, 0, "≤", float(i + 1)) for i in range(10)]
        _, r = _engine_with(1, 1, "max", constraints)
        assert r.feasible
