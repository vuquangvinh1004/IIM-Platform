"""Settings view — app-level configuration with real DB persistence."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from config.paths import DATA_DIR, EXPORTS_DIR, LOGS_DIR, MODULES_DIR
from config.settings import APP_NAME, APP_VERSION, PLATFORM_VERSION, SDK_VERSION
from core.services.settings_service import SettingsService
from core.utils.logger import get_logger
from ui.widgets.page_header import PageHeader

_log = get_logger("iimp.ui.settings")

# Setting keys stored in app_settings DB table
_KEY_THEME = "app.theme"
_KEY_LOG_LEVEL = "app.log_level"
_KEY_MAX_RECENT = "app.max_recent_items"
_KEY_RESTORE_STATE = "app.restore_module_state"


def _section(title: str) -> QGroupBox:
    g = QGroupBox(title)
    g.setObjectName("settingsSection")
    return g


class SettingsView(QWidget):
    """Full settings view with app preferences and platform info."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings_service: SettingsService | None = None
        # Widget refs
        self._theme_combo: QComboBox | None = None
        self._log_level_combo: QComboBox | None = None
        self._max_recent_spin: QSpinBox | None = None
        self._restore_state_cb: QCheckBox | None = None
        self._setup_ui()

    # ── DI ────────────────────────────────────────────────────────────────────

    def set_settings_service(self, svc: SettingsService) -> None:
        self._settings_service = svc
        self._load_values()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        outer = QVBoxLayout(container)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(16)

        header = PageHeader(
            eyebrow="APP PREFERENCES",
            title="Thiết lập nền tảng",
            description="Quản lý theme, logging, phục hồi trạng thái và các đường dẫn vận hành cục bộ của IIMP.",
        )
        outer.addWidget(header)

        intro = QFrame()
        intro.setObjectName("settingsIntroPanel")
        intro_layout = QHBoxLayout(intro)
        intro_layout.setContentsMargins(16, 14, 16, 14)
        intro_layout.setSpacing(12)
        intro_text = QLabel("Các thay đổi ở đây được lưu cục bộ và áp dụng cho toàn bộ shell.")
        intro_text.setObjectName("sectionMeta")
        intro_layout.addWidget(intro_text)
        outer.addWidget(intro)

        # ── Appearance ──
        appear_group = _section("Giao diện")
        appear_form = QFormLayout(appear_group)
        appear_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        appear_form.setSpacing(10)

        theme_combo = QComboBox()
        theme_combo.addItem("Light (mặc định)", "light")
        theme_combo.addItem("Dark (sắp hỗ trợ)", "dark")
        appear_form.addRow("Giao diện:", theme_combo)
        self._theme_combo = theme_combo
        outer.addWidget(appear_group)

        # ── Logging ──
        log_group = _section("Logging")
        log_form = QFormLayout(log_group)
        log_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        log_form.setSpacing(10)

        log_level_combo = QComboBox()
        for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            log_level_combo.addItem(level, level)
        log_form.addRow("Mức log:", log_level_combo)
        self._log_level_combo = log_level_combo
        outer.addWidget(log_group)

        # ── Module behaviour ──
        mod_group = _section("Hành vi module")
        mod_form = QFormLayout(mod_group)
        mod_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        mod_form.setSpacing(10)

        max_recent_spin = QSpinBox()
        max_recent_spin.setRange(0, 50)
        max_recent_spin.setValue(10)
        mod_form.addRow("Số mục gần đây:", max_recent_spin)
        self._max_recent_spin = max_recent_spin

        restore_cb = QCheckBox("Tự động phục hồi trạng thái module khi mở lại")
        restore_cb.setChecked(True)
        mod_form.addRow("", restore_cb)
        self._restore_state_cb = restore_cb
        outer.addWidget(mod_group)

        # ── Paths info ──
        paths_group = _section("Đường dẫn dữ liệu")
        paths_form = QFormLayout(paths_group)
        paths_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        paths_form.setSpacing(6)
        for label, path in [
            ("Data root:", DATA_DIR),
            ("Modules:", MODULES_DIR),
            ("Exports:", EXPORTS_DIR),
            ("Logs:", LOGS_DIR),
        ]:
            path_edit = QLineEdit(str(path))
            path_edit.setReadOnly(True)
            path_edit.setProperty("readonlyField", "true")
            paths_form.addRow(label, path_edit)
        outer.addWidget(paths_group)

        # ── About ──
        about_group = _section("Thông tin nền tảng")
        about_form = QFormLayout(about_group)
        about_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        about_form.setSpacing(6)
        for label, value in [
            ("Ứng dụng:", f"{APP_NAME} v{APP_VERSION}"),
            ("Platform:", f"v{PLATFORM_VERSION}"),
            ("SDK:", f"v{SDK_VERSION}"),
        ]:
            val_lbl = QLabel(value)
            val_lbl.setObjectName("sectionMeta")
            about_form.addRow(label, val_lbl)
        outer.addWidget(about_group)

        # ── Save button ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_save = QPushButton("Lưu cài đặt")
        btn_save.setProperty("role", "secondary")
        btn_save.clicked.connect(self._save)
        btn_row.addWidget(btn_save)
        outer.addLayout(btn_row)
        outer.addStretch()

        scroll.setWidget(container)

        # Outer layout just holds the scroll
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(scroll)

    # ── Private ───────────────────────────────────────────────────────────────

    def _load_values(self) -> None:
        if self._settings_service is None:
            return
        svc = self._settings_service
        if self._theme_combo:
            theme = str(svc.get_app_setting(_KEY_THEME, "light"))
            idx = self._theme_combo.findData(theme)
            if idx >= 0:
                self._theme_combo.setCurrentIndex(idx)
        if self._log_level_combo:
            level = str(svc.get_app_setting(_KEY_LOG_LEVEL, "INFO"))
            idx = self._log_level_combo.findData(level)
            if idx >= 0:
                self._log_level_combo.setCurrentIndex(idx)
        if self._max_recent_spin:
            val = svc.get_app_setting(_KEY_MAX_RECENT, 10)
            self._max_recent_spin.setValue(int(val))  # type: ignore[arg-type]
        if self._restore_state_cb:
            val = svc.get_app_setting(_KEY_RESTORE_STATE, True)
            self._restore_state_cb.setChecked(bool(val))

    def _save(self) -> None:
        if self._settings_service is None:
            QMessageBox.warning(self, "Chưa sẵn sàng", "Settings service chưa được khởi tạo.")
            return
        svc = self._settings_service
        if self._theme_combo:
            svc.set_app_setting(_KEY_THEME, self._theme_combo.currentData())
        if self._log_level_combo:
            svc.set_app_setting(_KEY_LOG_LEVEL, self._log_level_combo.currentData())
        if self._max_recent_spin:
            svc.set_app_setting(_KEY_MAX_RECENT, self._max_recent_spin.value())
        if self._restore_state_cb:
            svc.set_app_setting(_KEY_RESTORE_STATE, self._restore_state_cb.isChecked())
        QMessageBox.information(self, "Đã lưu", "Cài đặt đã được lưu thành công.")
        _log.info("App settings saved.")
