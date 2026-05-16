"""Smoke tests for LinearProgramming3DModule UI — skips gracefully without PySide6."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

try:
    from PySide6.QtWidgets import QApplication, QWidget

    _QT = True
except ImportError:
    _QT = False

_STUB_MANIFEST = {
    "id": "linear_programming_3d",
    "name": "Quy hoạch Tuyến tính 3D",
    "version": "1.0.0",
    "sdk_version": "1.0.0",
    "min_platform_version": "1.0.0",
    "entry_point": "modules.quantitative_methods.linear_programming_3d.entry:LinearProgramming3DModule",
    "category": "quantitative_methods",
    "author": "IIMP Team",
    "permissions": ["storage.read", "storage.write", "export.file",
                     "settings.read", "settings.write"],
}


def _make_context() -> MagicMock:
    ctx = MagicMock()
    ctx.logger = MagicMock()
    ctx.export_service = MagicMock()
    ctx.settings_service = MagicMock()
    ctx.settings_service.get_module_setting.return_value = None
    ctx.activity_service = MagicMock()
    return ctx


def _make_module():
    from modules.quantitative_methods.linear_programming_3d.module import LinearProgramming3DModule
    return LinearProgramming3DModule(manifest=_STUB_MANIFEST, context=_make_context())


@pytest.fixture(scope="module")
def qapp():
    if not _QT:
        pytest.skip("PySide6 not available")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ─── Tests ────────────────────────────────────────────────────────────────────


@pytest.mark.skipif(not _QT, reason="PySide6 not available")
class TestSmokeUI:
    """Basic UI smoke tests."""

    def test_on_load(self, qapp) -> None:
        mod = _make_module()
        mod.on_load()

    def test_build_view_returns_widget(self, qapp) -> None:
        mod = _make_module()
        mod.on_load()
        view = mod.build_view()
        assert isinstance(view, QWidget)

    def test_lifecycle_activate_deactivate(self, qapp) -> None:
        mod = _make_module()
        mod.on_load()
        mod.build_view()
        mod.on_activate()
        mod.on_deactivate()
        mod.on_unload()

    def test_get_state_returns_dict(self, qapp) -> None:
        mod = _make_module()
        mod.on_load()
        mod.build_view()
        state = mod.get_state()
        assert isinstance(state, dict)
        assert "c1" in state
        assert "c2" in state
        assert "c3" in state
        assert "sense" in state

    def test_restore_state(self, qapp) -> None:
        mod = _make_module()
        mod.on_load()
        mod.build_view()
        state = {
            "c1": 5.0, "c2": 3.0, "c3": 2.0, "sense": "max",
            "constraints": [{"a": 1, "b": 1, "c": 1, "op": "≤", "rhs": 6}],
        }
        mod.restore_state(state)
        new_state = mod.get_state()
        assert new_state["c1"] == 5.0
        assert new_state["c3"] == 2.0
        assert len(new_state["constraints"]) == 1

    def test_add_constraint_via_button(self, qapp) -> None:
        mod = _make_module()
        mod.on_load()
        view = mod.build_view()
        from modules.quantitative_methods.linear_programming_3d.module import _LP3DView
        assert isinstance(view, _LP3DView)
        initial = len(view._constraint_rows)
        view._add_constraint()
        assert len(view._constraint_rows) == initial + 1

    def test_max_constraints_limit(self, qapp) -> None:
        mod = _make_module()
        mod.on_load()
        view = mod.build_view()
        from modules.quantitative_methods.linear_programming_3d.module import MAX_CONSTRAINTS, _LP3DView
        assert isinstance(view, _LP3DView)
        for _ in range(MAX_CONSTRAINTS + 5):
            view._add_constraint()
        assert len(view._constraint_rows) <= MAX_CONSTRAINTS

    def test_solve_with_constraints(self, qapp) -> None:
        mod = _make_module()
        mod.on_load()
        view = mod.build_view()
        from modules.quantitative_methods.linear_programming_3d.module import Constraint3D, _LP3DView
        assert isinstance(view, _LP3DView)
        view._add_constraint_row(Constraint3D(1, 1, 1, "≤", 6))
        view._on_solve()
        assert view._result is not None
        assert view._result.feasible

    def test_solve_updates_vertex_table(self, qapp) -> None:
        mod = _make_module()
        mod.on_load()
        view = mod.build_view()
        from modules.quantitative_methods.linear_programming_3d.module import Constraint3D, _LP3DView
        assert isinstance(view, _LP3DView)
        view._add_constraint_row(Constraint3D(1, 1, 1, "≤", 6))
        view._on_solve()
        assert view._vertex_table._table.rowCount() > 0

    def test_remove_constraint(self, qapp) -> None:
        mod = _make_module()
        mod.on_load()
        view = mod.build_view()
        from modules.quantitative_methods.linear_programming_3d.module import _LP3DView
        assert isinstance(view, _LP3DView)
        view._add_constraint()
        view._add_constraint()
        count = len(view._constraint_rows)
        assert count == 2
        view._remove_constraint(view._constraint_rows[0])
        assert len(view._constraint_rows) == 1

    def test_iso_plane_toggle(self, qapp) -> None:
        mod = _make_module()
        mod.on_load()
        view = mod.build_view()
        from modules.quantitative_methods.linear_programming_3d.module import Constraint3D, _LP3DView
        assert isinstance(view, _LP3DView)
        view._add_constraint_row(Constraint3D(1, 1, 1, "≤", 6))
        view._on_solve()
        view._chk_show_iso.setChecked(True)
        view._on_slider_changed()

    def test_slider_movement(self, qapp) -> None:
        mod = _make_module()
        mod.on_load()
        view = mod.build_view()
        from modules.quantitative_methods.linear_programming_3d.module import Constraint3D, _LP3DView
        assert isinstance(view, _LP3DView)
        view._add_constraint_row(Constraint3D(1, 1, 1, "≤", 6))
        view._on_solve()
        view._chk_show_iso.setChecked(True)
        view._slider.setValue(200)
        view._slider.setValue(800)

    def test_elevation_azimuth_controls(self, qapp) -> None:
        mod = _make_module()
        mod.on_load()
        view = mod.build_view()
        from modules.quantitative_methods.linear_programming_3d.module import Constraint3D, _LP3DView
        assert isinstance(view, _LP3DView)
        view._add_constraint_row(Constraint3D(1, 1, 1, "≤", 6))
        view._on_solve()
        view._spin_elev.setValue(45)
        view._spin_azim.setValue(-60)
        view._render_canvas()

    def test_infeasible_solve(self, qapp) -> None:
        mod = _make_module()
        mod.on_load()
        view = mod.build_view()
        from modules.quantitative_methods.linear_programming_3d.module import Constraint3D, _LP3DView
        assert isinstance(view, _LP3DView)
        view._add_constraint_row(Constraint3D(1, 0, 0, "≥", 10))
        view._add_constraint_row(Constraint3D(1, 0, 0, "≤", 2))
        view._on_solve()
        assert view._result is not None
        assert not view._result.feasible

    def test_view_state_roundtrip(self, qapp) -> None:
        mod = _make_module()
        mod.on_load()
        view = mod.build_view()
        from modules.quantitative_methods.linear_programming_3d.module import Constraint3D, _LP3DView
        assert isinstance(view, _LP3DView)
        view._add_constraint_row(Constraint3D(1, 1, 1, "≤", 6))
        view._on_solve()
        state = view.get_view_state()
        assert "slider_pos" in state
        assert "show_iso" in state
        assert "elev" in state
        assert "azim" in state

    def test_export_png(self, qapp, tmp_path) -> None:
        mod = _make_module()
        mod.on_load()
        view = mod.build_view()
        from modules.quantitative_methods.linear_programming_3d.module import Constraint3D, _LP3DView
        assert isinstance(view, _LP3DView)
        view._add_constraint_row(Constraint3D(1, 1, 1, "≤", 6))
        view._on_solve()
        out = tmp_path / "lp3d.png"
        view._canvas.export_png(str(out))
        assert out.exists()
        assert out.stat().st_size > 0
