"""Smoke tests for LinearProgramming2DModule UI — skips gracefully without PySide6."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

try:
    from PySide6.QtWidgets import QApplication, QWidget

    _QT = True
except ImportError:
    _QT = False

_STUB_MANIFEST = {
    "id": "linear_programming_2d",
    "name": "Quy hoạch Tuyến tính 2D",
    "version": "1.0.0",
    "sdk_version": "1.0.0",
    "min_platform_version": "1.0.0",
    "entry_point": "modules.quantitative_methods.linear_programming_2d.entry:LinearProgramming2DModule",
    "category": "statistics",
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
    from modules.quantitative_methods.linear_programming_2d.module import LinearProgramming2DModule
    return LinearProgramming2DModule(manifest=_STUB_MANIFEST, context=_make_context())


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
        assert "sense" in state

    def test_restore_state(self, qapp) -> None:
        mod = _make_module()
        mod.on_load()
        mod.build_view()
        state = {
            "c1": 5.0, "c2": 3.0, "sense": "max",
            "constraints": [{"a": 1, "b": 1, "op": "≤", "rhs": 4}],
        }
        mod.restore_state(state)
        new_state = mod.get_state()
        assert new_state["c1"] == 5.0
        assert len(new_state["constraints"]) == 1

    def test_add_constraint_via_button(self, qapp) -> None:
        mod = _make_module()
        mod.on_load()
        view = mod.build_view()
        from modules.quantitative_methods.linear_programming_2d.module import _LP2DView
        assert isinstance(view, _LP2DView)
        initial = len(view._constraint_rows)
        view._add_constraint()
        assert len(view._constraint_rows) == initial + 1

    def test_max_constraints_limit(self, qapp) -> None:
        mod = _make_module()
        mod.on_load()
        view = mod.build_view()
        from modules.quantitative_methods.linear_programming_2d.module import MAX_CONSTRAINTS, _LP2DView
        assert isinstance(view, _LP2DView)
        for _ in range(MAX_CONSTRAINTS + 5):
            view._add_constraint()
        assert len(view._constraint_rows) <= MAX_CONSTRAINTS

    def test_solve_with_constraints(self, qapp) -> None:
        mod = _make_module()
        mod.on_load()
        view = mod.build_view()
        from modules.quantitative_methods.linear_programming_2d.module import Constraint, _LP2DView
        assert isinstance(view, _LP2DView)
        view._add_constraint_row(Constraint(1, 1, "≤", 4))
        view._on_solve()
        assert view._result is not None
        assert view._result.feasible

    def test_solve_updates_vertex_table(self, qapp) -> None:
        mod = _make_module()
        mod.on_load()
        view = mod.build_view()
        from modules.quantitative_methods.linear_programming_2d.module import Constraint, _LP2DView
        assert isinstance(view, _LP2DView)
        view._add_constraint_row(Constraint(1, 1, "≤", 4))
        view._on_solve()
        assert view._vertex_table._table.rowCount() > 0

    def test_remove_constraint(self, qapp) -> None:
        mod = _make_module()
        mod.on_load()
        view = mod.build_view()
        from modules.quantitative_methods.linear_programming_2d.module import _LP2DView
        assert isinstance(view, _LP2DView)
        view._add_constraint()
        view._add_constraint()
        count = len(view._constraint_rows)
        assert count == 2
        view._remove_constraint(view._constraint_rows[0])
        assert len(view._constraint_rows) == 1

    def test_iso_line_toggle(self, qapp) -> None:
        mod = _make_module()
        mod.on_load()
        view = mod.build_view()
        from modules.quantitative_methods.linear_programming_2d.module import Constraint, _LP2DView
        assert isinstance(view, _LP2DView)
        view._add_constraint_row(Constraint(1, 1, "≤", 4))
        view._on_solve()
        view._chk_show_iso.setChecked(True)
        view._on_slider_changed()

    def test_slider_movement(self, qapp) -> None:
        mod = _make_module()
        mod.on_load()
        view = mod.build_view()
        from modules.quantitative_methods.linear_programming_2d.module import Constraint, _LP2DView
        assert isinstance(view, _LP2DView)
        view._add_constraint_row(Constraint(1, 1, "≤", 4))
        view._on_solve()
        view._chk_show_iso.setChecked(True)
        view._slider.setValue(200)
        view._slider.setValue(800)
