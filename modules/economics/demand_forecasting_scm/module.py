"""DemandForecastingModule — IIMP module shell.

Kế thừa BaseModule, implement đầy đủ 5 lifecycle methods + get_state/restore_state/export.
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from core.module_runtime.base_module import BaseModule

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget
    from .ui.main_view import MainView


class DemandForecastingModule(BaseModule):
    """Module dự báo nhu cầu chuỗi cung ứng — Phase 1.

    Lifecycle:
        on_load()        → load settings từ SettingsService, không render UI
        build_view()     → tạo và trả về MainView QWidget
        on_activate()    → (no-op nếu không có background task)
        on_deactivate()  → (no-op)
        on_unload()      → dọn dẹp: không còn resource nặng ở module này
    """

    def __init__(self, manifest: dict, context: Any) -> None:
        super().__init__(manifest, context)
        self._view: MainView | None = None
        self._logger = context.logger.bind(module=self.module_id) if context else None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_load(self) -> None:
        """Nạp settings đã lưu từ SettingsService."""
        if self._logger:
            self._logger.info(f"[{self.module_id}] on_load() — v{self.module_version}")

        # Nạp config đã lưu (nếu có); sẽ dùng trong build_view
        self._saved_config: dict = {}
        try:
            config = self.context.settings_service.get(
                f"{self.module_id}.config", default=None
            )
            if isinstance(config, dict):
                self._saved_config = config
        except Exception:  # noqa: BLE001
            pass

    def build_view(self) -> "QWidget":
        """Tạo mới và trả về MainView cho mỗi lần host yêu cầu render."""
        self._dispose_view()

        from .ui.main_view import MainView  # noqa: PLC0415

        self._view = MainView(context=self.context)

        # Áp dụng config đã lưu (nếu có)
        if self._saved_config:
            self._view._apply_config(self._saved_config)

        if self._logger:
            self._logger.debug(f"[{self.module_id}] build_view() — view created")

        return self._view

    def on_activate(self) -> None:
        """Gọi khi module được đưa vào workspace và hiển thị."""
        if self._logger:
            self._logger.debug(f"[{self.module_id}] on_activate()")

    def on_deactivate(self) -> None:
        """Gọi khi module mất focus."""
        if self._logger:
            self._logger.debug(f"[{self.module_id}] on_deactivate()")

    def on_unload(self) -> None:
        """Dọn dẹp resources."""
        if self._logger:
            self._logger.info(f"[{self.module_id}] on_unload() — releasing resources")

        self._dispose_view()

    def _dispose_view(self) -> None:
        """Stop timers and safely release current view instance if present."""
        if self._view is None:
            return

        # Dừng tất cả QTimer đang chạy trong MethodViews (nếu có).
        try:
            if self._view._stationary_tab is not None:
                for mv in self._view._stationary_tab._method_views.values():
                    mv._recalc_timer.stop()
            if self._view._trend_tab is not None:
                for mv in self._view._trend_tab._method_views.values():
                    mv._recalc_timer.stop()
        except Exception:  # noqa: BLE001
            pass

        try:
            self._view.setParent(None)  # type: ignore[call-arg]
            self._view.deleteLater()  # type: ignore[call-arg]
        except Exception:  # noqa: BLE001
            pass
        self._view = None

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def get_state(self) -> dict:
        """Trả về state hiện tại dưới dạng JSON-serializable dict."""
        if self._view is None:
            return {}
        try:
            state = self._view.get_state()
            state_dict = state.to_dict()
            state_dict["_state_version"] = self.manifest.get("data_contract_version", "1.0.0")
            return state_dict
        except Exception as exc:  # noqa: BLE001
            if self._logger:
                self._logger.warning(f"[{self.module_id}] get_state() error: {exc}")
            return {}

    def restore_state(self, state: dict) -> None:
        """Phục hồi state đã lưu vào view."""
        if self._view is None or not state:
            return

        try:
            from .models.state import DemandForecastingState  # noqa: PLC0415
            restored = DemandForecastingState.from_dict(state)
            self._view.restore_state(restored)
        except Exception as exc:  # noqa: BLE001
            if self._logger:
                self._logger.warning(f"[{self.module_id}] restore_state() error: {exc}")

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export(self, target_path: str, export_type: str = "default") -> None:
        """Export chart PNG hoặc data CSV.

        Supported export_type values:
            "chart_png"  — xuất biểu đồ Yt hiện tại
            "default"    — tương đương "chart_png"
        """
        if self._view is None:
            raise RuntimeError("Module chưa được khởi tạo view.")

        dataset = self._view._dataset
        if dataset is None:
            raise RuntimeError("Chưa có dữ liệu để export.")

        if export_type in ("chart_png", "default"):
            self._export_chart_png(target_path, dataset)
        else:
            raise NotImplementedError(f"export_type='{export_type}' chưa được hỗ trợ.")

    def _export_chart_png(self, target_path: str, dataset) -> None:  # type: ignore[type-arg]
        from .services.chart_builder import build_yt_chart  # noqa: PLC0415
        t_vals = [p.t for p in dataset.points]
        y_vals = [p.y for p in dataset.points]
        fig = build_yt_chart(t_vals, y_vals)
        os.makedirs(os.path.dirname(target_path) or ".", exist_ok=True)
        fig.savefig(target_path, dpi=150, bbox_inches="tight")
        import matplotlib.pyplot as plt  # noqa: PLC0415
        plt.close(fig)
        if self._logger:
            self._logger.info(f"[{self.module_id}] Exported chart → {target_path}")

    # ------------------------------------------------------------------
    # Settings schema
    # ------------------------------------------------------------------

    def get_settings_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "benchmark": {
                    "type": "string",
                    "enum": ["naive", "ma2", "ma3"],
                    "default": "naive",
                    "description": "Phương pháp benchmark cho FVA",
                },
                "ts_threshold": {
                    "type": "number",
                    "minimum": 1.0,
                    "maximum": 10.0,
                    "default": 4.0,
                    "description": "Ngưỡng Tracking Signal (±)",
                },
            },
        }
