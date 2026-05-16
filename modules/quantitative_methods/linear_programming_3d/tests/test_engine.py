"""Unit tests for LP3DEngine — pure Python, no Qt dependency."""
from __future__ import annotations

import pytest

from modules.quantitative_methods.linear_programming_3d.module import (
    Constraint3D,
    LP3DEngine,
    LP3DResult,
    Vertex3D,
)

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _engine_with(
    c1: float, c2: float, c3: float, sense: str,
    constraints: list[Constraint3D],
) -> tuple[LP3DEngine, LP3DResult]:
    eng = LP3DEngine()
    eng.set_objective(c1, c2, c3, sense)
    eng.set_constraints(constraints)
    result = eng.solve()
    return eng, result


# ─── Basic feasibility ───────────────────────────────────────────────────────


class TestFeasibility:
    """Tests for feasible / infeasible detection."""

    def test_simple_feasible(self) -> None:
        """x₁ + x₂ + x₃ ≤ 6, all ≥ 0 → feasible."""
        _, r = _engine_with(1, 1, 1, "max", [
            Constraint3D(1, 1, 1, "≤", 6),
        ])
        assert r.feasible

    def test_contradictory_infeasible(self) -> None:
        """x₁ ≥ 10 and x₁ ≤ 2 → infeasible."""
        _, r = _engine_with(1, 0, 0, "max", [
            Constraint3D(1, 0, 0, "≥", 10),
            Constraint3D(1, 0, 0, "≤", 2),
        ])
        assert not r.feasible

    def test_no_constraints_feasible(self) -> None:
        """Only non-negativity → origin is the only vertex."""
        _, r = _engine_with(1, 1, 1, "max", [])
        assert r.feasible
        assert len(r.vertices) == 1
        v = r.vertices[0]
        assert abs(v.x) < 1e-9 and abs(v.y) < 1e-9 and abs(v.z) < 1e-9

    def test_infeasible_message(self) -> None:
        _, r = _engine_with(1, 0, 0, "max", [
            Constraint3D(1, 0, 0, "≥", 10),
            Constraint3D(1, 0, 0, "≤", 2),
        ])
        assert "rỗng" in r.message


# ─── Classic LP problems ─────────────────────────────────────────────────────


class TestClassicProblems:
    """Well-known textbook LP problems in 3 variables."""

    def test_max_tetrahedron(self) -> None:
        """max Z = x₁ + x₂ + x₃  s.t.  x₁ + x₂ + x₃ ≤ 6, all ≥ 0.
        Tetrahedron with 4 vertices. Optimal Z* = 6 at one of (6,0,0),
        (0,6,0), (0,0,6)."""
        _, r = _engine_with(1, 1, 1, "max", [
            Constraint3D(1, 1, 1, "≤", 6),
        ])
        assert r.feasible
        assert abs(r.optimal_value - 6.0) < 1e-6
        assert len(r.vertices) == 4

    def test_max_box(self) -> None:
        """max Z = x₁ + x₂ + x₃  s.t.  x₁ ≤ 2, x₂ ≤ 3, x₃ ≤ 4, all ≥ 0.
        Box with 8 vertices. Optimal at (2, 3, 4) → Z* = 9."""
        _, r = _engine_with(1, 1, 1, "max", [
            Constraint3D(1, 0, 0, "≤", 2),
            Constraint3D(0, 1, 0, "≤", 3),
            Constraint3D(0, 0, 1, "≤", 4),
        ])
        assert r.feasible
        assert abs(r.optimal_value - 9.0) < 1e-6
        assert len(r.vertices) == 8

    def test_min_at_origin(self) -> None:
        """min Z = x₁ + x₂ + x₃  s.t.  x₁ ≤ 5, x₂ ≤ 5, x₃ ≤ 5.
        Minimum at (0,0,0) → Z* = 0."""
        _, r = _engine_with(1, 1, 1, "min", [
            Constraint3D(1, 0, 0, "≤", 5),
            Constraint3D(0, 1, 0, "≤", 5),
            Constraint3D(0, 0, 1, "≤", 5),
        ])
        assert r.feasible
        assert abs(r.optimal_value) < 1e-6

    def test_multiple_optimal_vertices(self) -> None:
        """max Z = x₁ + x₂ + x₃  s.t.  x₁ + x₂ + x₃ ≤ 6, all ≥ 0.
        Optimal at (6,0,0), (0,6,0), (0,0,6) → all Z* = 6."""
        _, r = _engine_with(1, 1, 1, "max", [
            Constraint3D(1, 1, 1, "≤", 6),
        ])
        assert r.feasible
        assert len(r.optimal_vertices) == 3

    def test_single_optimal_vertex(self) -> None:
        """max Z = 3x₁ + 2x₂ + x₃  s.t.  x₁ ≤ 4, x₂ ≤ 3, x₃ ≤ 2.
        Optimal at (4, 3, 2) → Z* = 20."""
        _, r = _engine_with(3, 2, 1, "max", [
            Constraint3D(1, 0, 0, "≤", 4),
            Constraint3D(0, 1, 0, "≤", 3),
            Constraint3D(0, 0, 1, "≤", 2),
        ])
        assert r.feasible
        assert abs(r.optimal_value - 20.0) < 1e-6
        assert len(r.optimal_vertices) == 1
        v = r.optimal_vertices[0]
        assert abs(v.x - 4.0) < 1e-6
        assert abs(v.y - 3.0) < 1e-6
        assert abs(v.z - 2.0) < 1e-6

    def test_mixed_constraints(self) -> None:
        """max Z = 2x₁ + 3x₂ + x₃  s.t.
        x₁ + x₂ + x₃ ≤ 10, x₁ + 2x₂ ≤ 12, x₃ ≤ 4."""
        _, r = _engine_with(2, 3, 1, "max", [
            Constraint3D(1, 1, 1, "≤", 10),
            Constraint3D(1, 2, 0, "≤", 12),
            Constraint3D(0, 0, 1, "≤", 4),
        ])
        assert r.feasible
        assert r.optimal_value > 0


# ─── Vertex counting ─────────────────────────────────────────────────────────


class TestVertices:
    """Tests for vertex enumeration."""

    def test_tetrahedron_has_4_vertices(self) -> None:
        _, r = _engine_with(1, 1, 1, "max", [
            Constraint3D(1, 1, 1, "≤", 6),
        ])
        assert len(r.vertices) == 4

    def test_box_has_8_vertices(self) -> None:
        _, r = _engine_with(1, 1, 1, "max", [
            Constraint3D(1, 0, 0, "≤", 3),
            Constraint3D(0, 1, 0, "≤", 3),
            Constraint3D(0, 0, 1, "≤", 3),
        ])
        assert len(r.vertices) == 8

    def test_vertex_coordinates_tetrahedron(self) -> None:
        """x₁ + x₂ + x₃ ≤ 6 → vertices at (0,0,0), (6,0,0), (0,6,0), (0,0,6)."""
        _, r = _engine_with(1, 1, 1, "max", [
            Constraint3D(1, 1, 1, "≤", 6),
        ])
        pts = sorted([(v.x, v.y, v.z) for v in r.vertices])
        expected = sorted([(0, 0, 0), (6, 0, 0), (0, 6, 0), (0, 0, 6)])
        for p, e in zip(pts, expected):
            assert abs(p[0] - e[0]) < 1e-6
            assert abs(p[1] - e[1]) < 1e-6
            assert abs(p[2] - e[2]) < 1e-6

    def test_prism_vertices(self) -> None:
        """x₁ + x₂ ≤ 4, x₃ ≤ 3 → 6 vertices (triangular prism)."""
        _, r = _engine_with(1, 1, 1, "max", [
            Constraint3D(1, 1, 0, "≤", 4),
            Constraint3D(0, 0, 1, "≤", 3),
        ])
        assert r.feasible
        assert len(r.vertices) == 6


# ─── Convex hull ──────────────────────────────────────────────────────────────


class TestConvexHull:
    """Tests for the convex hull faces output."""

    def test_hull_faces_exist(self) -> None:
        _, r = _engine_with(1, 1, 1, "max", [
            Constraint3D(1, 1, 1, "≤", 6),
        ])
        assert len(r.hull_faces) >= 1

    def test_hull_faces_tetrahedron(self) -> None:
        """A tetrahedron should have 4 faces."""
        _, r = _engine_with(1, 1, 1, "max", [
            Constraint3D(1, 1, 1, "≤", 6),
        ])
        assert len(r.hull_faces) == 4

    def test_hull_face_indices_valid(self) -> None:
        _, r = _engine_with(1, 1, 1, "max", [
            Constraint3D(1, 1, 1, "≤", 6),
        ])
        n = len(r.vertices)
        for face in r.hull_faces:
            for idx in face:
                assert 0 <= idx < n


# ─── Constraint types ────────────────────────────────────────────────────────


class TestConstraintTypes:
    def test_ge_constraint(self) -> None:
        """min Z = x₁ + x₂ + x₃  s.t.  x₁ + x₂ + x₃ ≥ 3, x₁ ≤ 5, x₂ ≤ 5, x₃ ≤ 5."""
        _, r = _engine_with(1, 1, 1, "min", [
            Constraint3D(1, 1, 1, "≥", 3),
            Constraint3D(1, 0, 0, "≤", 5),
            Constraint3D(0, 1, 0, "≤", 5),
            Constraint3D(0, 0, 1, "≤", 5),
        ])
        assert r.feasible
        assert abs(r.optimal_value - 3.0) < 1e-6

    def test_eq_constraint(self) -> None:
        """max Z = x₁ + x₂ + x₃  s.t.  x₁ + x₂ + x₃ = 6.
        Only vertices on the plane x₁+x₂+x₃=6 in first octant."""
        _, r = _engine_with(1, 1, 1, "max", [
            Constraint3D(1, 1, 1, "=", 6),
        ])
        assert r.feasible
        # All vertices satisfy x₁+x₂+x₃ = 6
        for v in r.vertices:
            assert abs(v.x + v.y + v.z - 6.0) < 1e-6
        assert abs(r.optimal_value - 6.0) < 1e-6

    def test_mixed_operators(self) -> None:
        """x₁ + x₂ + x₃ ≤ 10, x₁ ≥ 1, x₂ ≥ 1, x₃ ≥ 1."""
        _, r = _engine_with(1, 1, 1, "max", [
            Constraint3D(1, 1, 1, "≤", 10),
            Constraint3D(1, 0, 0, "≥", 1),
            Constraint3D(0, 1, 0, "≥", 1),
            Constraint3D(0, 0, 1, "≥", 1),
        ])
        assert r.feasible
        assert abs(r.optimal_value - 10.0) < 1e-6
        # All vertices satisfy x₁ ≥ 1, x₂ ≥ 1, x₃ ≥ 1
        for v in r.vertices:
            assert v.x >= 1.0 - 1e-6
            assert v.y >= 1.0 - 1e-6
            assert v.z >= 1.0 - 1e-6


# ─── Constraint label ────────────────────────────────────────────────────────


class TestConstraintLabel:
    def test_basic_label(self) -> None:
        c = Constraint3D(2, 3, 1, "≤", 6)
        lbl = c.label(1)
        assert "2" in lbl
        assert "3" in lbl
        assert "X\u2081" in lbl
        assert "X\u2082" in lbl
        assert "X\u2083" in lbl
        assert "≤" in lbl
        assert "6" in lbl

    def test_negative_coeff(self) -> None:
        c = Constraint3D(1, -2, 3, "≤", 5)
        lbl = c.label(1)
        assert "X\u2081" in lbl
        assert "2" in lbl
        assert "-" in lbl

    def test_zero_coeff_omitted(self) -> None:
        c = Constraint3D(0, 0, 1, "≤", 3)
        lbl = c.label(1)
        assert "X\u2083" in lbl
        # X₁ and X₂ should not appear
        assert "X\u2081" not in lbl
        assert "X\u2082" not in lbl

    def test_unit_coeff(self) -> None:
        c = Constraint3D(1, 1, 1, "≤", 10)
        lbl = c.label(1)
        assert "X\u2081" in lbl
        assert "X\u2082" in lbl
        assert "X\u2083" in lbl

    def test_all_zero_coeffs(self) -> None:
        c = Constraint3D(0, 0, 0, "≤", 0)
        lbl = c.label(1)
        assert "0" in lbl


# ─── Intersect 3 planes ──────────────────────────────────────────────────────


class TestIntersect3Planes:
    def test_coordinate_planes(self) -> None:
        """Intersection of x₁=0, x₂=0, x₃=0 is the origin."""
        p1 = (1.0, 0.0, 0.0, 0.0, "=")
        p2 = (0.0, 1.0, 0.0, 0.0, "=")
        p3 = (0.0, 0.0, 1.0, 0.0, "=")
        pt = LP3DEngine._intersect_3planes(p1, p2, p3)
        assert pt is not None
        assert abs(pt[0]) < 1e-9
        assert abs(pt[1]) < 1e-9
        assert abs(pt[2]) < 1e-9

    def test_parallel_planes_no_intersection(self) -> None:
        """Two parallel planes → no unique intersection."""
        p1 = (1.0, 0.0, 0.0, 1.0, "=")
        p2 = (1.0, 0.0, 0.0, 2.0, "=")
        p3 = (0.0, 1.0, 0.0, 0.0, "=")
        pt = LP3DEngine._intersect_3planes(p1, p2, p3)
        assert pt is None

    def test_known_intersection(self) -> None:
        """x₁ = 2, x₂ = 3, x₃ = 4 → (2, 3, 4)."""
        p1 = (1.0, 0.0, 0.0, 2.0, "=")
        p2 = (0.0, 1.0, 0.0, 3.0, "=")
        p3 = (0.0, 0.0, 1.0, 4.0, "=")
        pt = LP3DEngine._intersect_3planes(p1, p2, p3)
        assert pt is not None
        assert abs(pt[0] - 2.0) < 1e-9
        assert abs(pt[1] - 3.0) < 1e-9
        assert abs(pt[2] - 4.0) < 1e-9

    def test_general_planes(self) -> None:
        """x₁ + x₂ + x₃ = 6, x₁ = 0, x₂ = 0 → (0, 0, 6)."""
        p1 = (1.0, 1.0, 1.0, 6.0, "=")
        p2 = (1.0, 0.0, 0.0, 0.0, "=")
        p3 = (0.0, 1.0, 0.0, 0.0, "=")
        pt = LP3DEngine._intersect_3planes(p1, p2, p3)
        assert pt is not None
        assert abs(pt[0]) < 1e-9
        assert abs(pt[1]) < 1e-9
        assert abs(pt[2] - 6.0) < 1e-9


# ─── State persistence ───────────────────────────────────────────────────────


class TestStatePersistence:
    def test_get_state(self) -> None:
        eng = LP3DEngine()
        eng.set_objective(2, 3, 1, "min")
        eng.set_constraints([Constraint3D(1, 2, 3, "≤", 10)])
        state = eng.get_state()
        assert state["c1"] == 2
        assert state["c2"] == 3
        assert state["c3"] == 1
        assert state["sense"] == "min"
        assert len(state["constraints"]) == 1
        assert state["constraints"][0]["a"] == 1

    def test_restore_state(self) -> None:
        eng = LP3DEngine()
        state = {
            "c1": 5, "c2": 3, "c3": 2, "sense": "max",
            "constraints": [
                {"a": 1, "b": 1, "c": 1, "op": "≤", "rhs": 10},
            ],
        }
        eng.restore_state(state)
        assert eng.problem.c1 == 5
        assert eng.problem.c3 == 2
        assert eng.problem.sense == "max"
        assert len(eng.problem.constraints) == 1

    def test_roundtrip_state(self) -> None:
        eng1 = LP3DEngine()
        eng1.set_objective(7, 2, 4, "min")
        eng1.set_constraints([
            Constraint3D(1, 0, 0, "≤", 5),
            Constraint3D(0, 1, 1, "≥", 2),
        ])
        state = eng1.get_state()

        eng2 = LP3DEngine()
        eng2.restore_state(state)
        assert eng2.problem.c1 == 7
        assert eng2.problem.c3 == 4
        assert eng2.problem.sense == "min"
        assert len(eng2.problem.constraints) == 2
        assert eng2.problem.constraints[1].op == "≥"
        assert eng2.problem.constraints[1].rhs == 2

    def test_restore_defaults(self) -> None:
        eng = LP3DEngine()
        eng.restore_state({})
        assert eng.problem.c1 == 1.0
        assert eng.problem.sense == "max"
        assert eng.problem.constraints == []


# ─── Objective value ──────────────────────────────────────────────────────────


class TestObjectiveValue:
    def test_z_value_at_origin(self) -> None:
        _, r = _engine_with(5, 3, 2, "max", [
            Constraint3D(1, 1, 1, "≤", 6),
        ])
        origin = [v for v in r.vertices
                  if abs(v.x) < 1e-6 and abs(v.y) < 1e-6 and abs(v.z) < 1e-6]
        assert len(origin) == 1
        assert abs(origin[0].obj) < 1e-6

    def test_z_value_computed(self) -> None:
        """Z = 5x₁ + 3x₂ + 2x₃ at (6, 0, 0) → 30."""
        _, r = _engine_with(5, 3, 2, "max", [
            Constraint3D(1, 1, 1, "≤", 6),
        ])
        v6 = [v for v in r.vertices if abs(v.x - 6) < 1e-6]
        assert len(v6) == 1
        assert abs(v6[0].obj - 30.0) < 1e-6

    def test_optimal_is_max(self) -> None:
        """max Z = 5x₁ + 3x₂ + 2x₃  s.t.  x₁+x₂+x₃ ≤ 6
        → max at (6,0,0) with Z* = 30."""
        _, r = _engine_with(5, 3, 2, "max", [
            Constraint3D(1, 1, 1, "≤", 6),
        ])
        assert abs(r.optimal_value - 30.0) < 1e-6

    def test_optimal_is_min(self) -> None:
        """min Z = 5x₁ + 3x₂ + 2x₃  s.t.  x₁+x₂+x₃ ≤ 6
        → min at (0,0,0) with Z* = 0."""
        _, r = _engine_with(5, 3, 2, "min", [
            Constraint3D(1, 1, 1, "≤", 6),
        ])
        assert abs(r.optimal_value) < 1e-6


# ─── Edge cases ──────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_single_point_feasible(self) -> None:
        """x₁ = 2, x₂ = 3, x₃ = 1 → single vertex."""
        _, r = _engine_with(1, 1, 1, "max", [
            Constraint3D(1, 0, 0, "=", 2),
            Constraint3D(0, 1, 0, "=", 3),
            Constraint3D(0, 0, 1, "=", 1),
        ])
        assert r.feasible
        assert len(r.vertices) == 1
        v = r.vertices[0]
        assert abs(v.x - 2) < 1e-6
        assert abs(v.y - 3) < 1e-6
        assert abs(v.z - 1) < 1e-6

    def test_degenerate_zero_coefficients(self) -> None:
        """Constraint 0·x₁ + 0·x₂ + 0·x₃ ≤ 5 → always true, origin feasible."""
        _, r = _engine_with(1, 1, 1, "max", [
            Constraint3D(0, 0, 0, "≤", 5),
        ])
        assert r.feasible

    def test_negative_rhs_infeasible(self) -> None:
        """x₁ + x₂ + x₃ ≤ -1, with non-negativity → infeasible."""
        _, r = _engine_with(1, 1, 1, "max", [
            Constraint3D(1, 1, 1, "≤", -1),
        ])
        assert not r.feasible

    def test_negative_0_clamped(self) -> None:
        """Vertices with tiny negative values should be clamped to 0."""
        _, r = _engine_with(1, 1, 1, "max", [
            Constraint3D(1, 1, 1, "≤", 6),
        ])
        for v in r.vertices:
            # No negative coordinates after clamping
            assert v.x >= 0.0
            assert v.y >= 0.0
            assert v.z >= 0.0


# ─── Plane label ──────────────────────────────────────────────────────────────


class TestPlaneLabel:
    def test_coordinate_plane_labels(self) -> None:
        lbl0 = LP3DEngine._plane_label((1, 0, 0, 0, "≥"), 0)
        assert lbl0 == "X\u2081=0"
        lbl1 = LP3DEngine._plane_label((0, 1, 0, 0, "≥"), 1)
        assert lbl1 == "X\u2082=0"
        lbl2 = LP3DEngine._plane_label((0, 0, 1, 0, "≥"), 2)
        assert lbl2 == "X\u2083=0"

    def test_general_plane_label(self) -> None:
        lbl = LP3DEngine._plane_label((2, 3, 1, 10, "≤"), 5)
        assert "2" in lbl
        assert "3" in lbl
        assert "10" in lbl
        assert "≤" in lbl
