"""Module manager view — enable, disable, uninstall and install modules."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.module_runtime.registry import ModuleRecord, ModuleRegistry
from core.services.module_service import ModuleService
from core.storage.models import ModuleRegistry as DBModuleRegistry
from core.storage.session import get_session
from core.utils.constants import ModuleState
from core.utils.helpers import safe_json_loads
from core.utils.logger import get_logger
from ui.widgets.page_header import PageHeader
from ui.widgets.status_badge import StatusBadge

_log = get_logger("iimp.ui.module_manager")


# ── Row widget ────────────────────────────────────────────────────────────────

class _ModuleRow(QFrame):
    """One row in the module manager list showing module info + action buttons."""

    enable_requested: Signal = Signal(str)
    disable_requested: Signal = Signal(str)
    uninstall_requested: Signal = Signal(str)

    def __init__(
        self,
        module_id: str,
        name: str,
        version: str,
        category: str,
        is_enabled: bool,
        is_builtin: bool,
        state_label: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._module_id = module_id
        self._is_enabled = is_enabled
        self._is_builtin = is_builtin
        self._setup(name, version, category, state_label)

    def _setup(self, name: str, version: str, category: str, state_label: str) -> None:
        self.setObjectName("managerModuleRow")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        info = QVBoxLayout()
        info.setSpacing(3)
        name_lbl = QLabel(name)
        name_lbl.setObjectName("moduleTitle")
        meta_lbl = QLabel(f"{category}  ·  v{version}")
        meta_lbl.setObjectName("moduleMeta")
        info.addWidget(name_lbl)
        info.addWidget(meta_lbl)
        layout.addLayout(info, stretch=1)

        _state_badges = {
            "activated": ("success", "Đang chạy"),
            "disabled": ("warning", "Đã tắt"),
            "error": ("danger", "Lỗi"),
            "incompatible": ("danger", "Không tương thích"),
        }
        badge_variant, badge_text = _state_badges.get(
            state_label, ("info", state_label.replace("_", " ").title())
        )
        badge = StatusBadge(badge_text, badge_variant)
        layout.addWidget(badge)

        if self._is_enabled:
            btn_toggle = QPushButton("Tắt")
            btn_toggle.setToolTip("Tắt module (sẽ unload nếu đang chạy)")
            btn_toggle.setProperty("role", "warning")
            btn_toggle.clicked.connect(lambda: self.disable_requested.emit(self._module_id))
        else:
            btn_toggle = QPushButton("Bật")
            btn_toggle.setToolTip("Bật module")
            btn_toggle.setProperty("role", "success")
            btn_toggle.clicked.connect(lambda: self.enable_requested.emit(self._module_id))

        layout.addWidget(btn_toggle)

        if not self._is_builtin:
            btn_remove = QPushButton("Gỡ")
            btn_remove.setToolTip("Gỡ cài đặt module")
            btn_remove.setProperty("role", "danger")
            btn_remove.clicked.connect(lambda: self.uninstall_requested.emit(self._module_id))
            layout.addWidget(btn_remove)


# ── Main view ─────────────────────────────────────────────────────────────────

class ModuleManagerView(QWidget):
    """Full module manager with enable/disable/uninstall/install-local flow."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._registry: ModuleRegistry | None = None
        self._module_service: ModuleService | None = None
        self._list_layout: QVBoxLayout | None = None
        self._setup_ui()

    # ── DI injection (called by MainWindow after services are wired) ──────────

    def set_services(self, registry: ModuleRegistry, module_service: ModuleService) -> None:
        self._registry = registry
        self._module_service = module_service
        self.refresh()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 20)
        outer.setSpacing(16)

        header = PageHeader(
            eyebrow="MODULE OPERATIONS",
            title="Quản lý vòng đời module",
            description="Bật, tắt, cài đặt và gỡ module trong khi vẫn giữ nguyên contract hiện tại của nền tảng.",
        )
        outer.addWidget(header)

        toolbar = QFrame()
        toolbar.setObjectName("managerToolbar")
        header_row = QHBoxLayout(toolbar)
        header_row.setContentsMargins(16, 14, 16, 14)
        header_row.setSpacing(10)

        helper = QLabel("Các thay đổi tại đây tác động trực tiếp đến khả năng tải và kích hoạt module trong shell.")
        helper.setObjectName("sectionMeta")
        header_row.addWidget(helper, stretch=1)

        btn_install = QPushButton("＋ Cài từ thư mục...")
        btn_install.setProperty("role", "secondary")
        btn_install.clicked.connect(self._on_install_local)
        header_row.addWidget(btn_install)

        btn_refresh = QPushButton("↻ Làm mới")
        btn_refresh.setProperty("role", "subtle")
        btn_refresh.clicked.connect(self.refresh)
        header_row.addWidget(btn_refresh)

        outer.addWidget(toolbar)

        # Scrollable module list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        self._list_layout = QVBoxLayout(container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(10)
        self._list_layout.addStretch()
        scroll.setWidget(container)
        outer.addWidget(scroll, stretch=1)

    # ── Public ────────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        if self._list_layout is None:
            return
        # Clear existing rows (except stretch)
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        rows = self._build_rows()
        if not rows:
            placeholder = QLabel("Chưa có module nào được cài đặt.")
            placeholder.setObjectName("mutedText")
            self._list_layout.insertWidget(0, placeholder)
            return

        for idx, row in enumerate(rows):
            row.enable_requested.connect(self._on_enable)
            row.disable_requested.connect(self._on_disable)
            row.uninstall_requested.connect(self._on_uninstall)
            self._list_layout.insertWidget(idx, row)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _build_rows(self) -> list[_ModuleRow]:
        rows: list[_ModuleRow] = []
        try:
            with get_session() as session:
                db_rows = session.query(DBModuleRegistry).order_by(DBModuleRegistry.name).all()
                entries = [
                    {
                        "id": r.module_id,
                        "name": r.name,
                        "version": r.version,
                        "category": r.category or "—",
                        "is_enabled": r.is_enabled,
                        "is_builtin": r.is_builtin,
                    }
                    for r in db_rows
                ]
        except Exception as exc:  # noqa: BLE001
            _log.error(f"ModuleManagerView: DB query failed: {exc}")
            entries = []

        for entry in entries:
            mid = entry["id"]
            state_label = "discovered"
            if self._registry:
                record = self._registry.get_record(mid)
                if record:
                    state_label = record.state.value

            if not entry["is_enabled"]:
                state_label = "disabled"

            rows.append(
                _ModuleRow(
                    module_id=mid,
                    name=entry["name"],
                    version=entry["version"],
                    category=entry["category"],
                    is_enabled=entry["is_enabled"],
                    is_builtin=entry["is_builtin"],
                    state_label=state_label,
                )
            )
        return rows

    def _on_enable(self, module_id: str) -> None:
        if self._module_service is None:
            return
        self._module_service.enable_module(module_id)
        self.refresh()

    def _on_disable(self, module_id: str) -> None:
        if self._module_service is None:
            return
        confirm = QMessageBox.question(
            self,
            "Xác nhận tắt module",
            f"Bạn có chắc muốn tắt module '{module_id}'?\n"
            "Module đang chạy sẽ bị unload.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self._module_service.disable_module(module_id)
            self.refresh()

    def _on_uninstall(self, module_id: str) -> None:
        if self._module_service is None:
            return
        confirm = QMessageBox.question(
            self,
            "Xác nhận gỡ module",
            f"Bạn có chắc muốn gỡ hoàn toàn module '{module_id}'?\n"
            "Thao tác này sẽ xóa toàn bộ settings và session lưu liên quan.\n"
            "File module trên ổ đĩa sẽ không bị xóa.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self._module_service.uninstall_module(module_id)
            self.refresh()

    def _on_install_local(self) -> None:
        if self._module_service is None:
            QMessageBox.warning(self, "Chưa sẵn sàng", "Module service chưa được khởi tạo.")
            return
        folder = QFileDialog.getExistingDirectory(
            self,
            "Chọn thư mục module",
            "",
            QFileDialog.Option.ShowDirsOnly,
        )
        if not folder:
            return
        source_dir = Path(folder)
        module_id = self._module_service.install_local_module(source_dir)
        if module_id:
            QMessageBox.information(
                self,
                "Cài đặt thành công",
                f"Module '{module_id}' đã được cài đặt thành công.",
            )
            self.refresh()
        else:
            QMessageBox.critical(
                self,
                "Cài đặt thất bại",
                f"Không thể cài module từ '{folder}'.\n"
                "Kiểm tra xem thư mục có chứa module.json hợp lệ không.",
            )
