"""Module library view — browse, search and open modules with folder organization.

Layout:
    ┌──────────────────────────────────────────────────────────┐
    │  Search box                                              │
    ├────────────────┬─────────────────────────────────────────┤
    │  Folder panel  │  Module cards for selected folder       │
    │  ─ All Modules │                                         │
    │  ─ Custom 1    │                                         │
    │  ─ Custom 2    │                                         │
    │  + New folder  │                                         │
    └────────────────┴─────────────────────────────────────────┘
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from core.module_runtime.registry import ModuleRecord
from ui.widgets.module_card import ModuleCard
from ui.widgets.page_header import PageHeader
from ui.widgets.empty_state import EmptyState

if TYPE_CHECKING:
    from core.services.folder_service import FolderService

_ALL_MODULES_ID = -1  # sentinel for the virtual "All Modules" folder


class ModuleLibraryView(QWidget):
    """Displays modules organized in folders with shortcut support."""

    open_module = Signal(str)  # module_id

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cards: list[ModuleCard] = []
        self._records: list[ModuleRecord] = []
        self._folder_service: FolderService | None = None
        self._selected_folder_id: int = _ALL_MODULES_ID
        self._selected_folder_name = "Tất cả module"
        self._setup_ui()

    # ── Public API ────────────────────────────────────────────────────────────

    def set_folder_service(self, svc: FolderService) -> None:
        self._folder_service = svc

    def populate(self, records: list[ModuleRecord]) -> None:
        """Rebuild entire view from *records*."""
        self._records = [r for r in records if r.manifest.category != "template"]
        self._refresh_folders()
        self._show_folder(_ALL_MODULES_ID)

    # ── UI construction ───────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 20)
        outer.setSpacing(16)

        header_frame = PageHeader(
            eyebrow="MODULE LIBRARY",
            title="Khám phá công cụ học thuật",
            description="Duyệt, nhóm và mở các module tương tác trong cùng một workspace thống nhất.",
        )
        self._module_count_pill = QLabel("0 module")
        self._module_count_pill.setObjectName("metricPill")

        header_layout = header_frame.layout()
        header_layout.addWidget(self._module_count_pill, alignment=Qt.AlignmentFlag.AlignLeft)
        outer.addWidget(header_frame)

        toolbar_frame = QFrame()
        toolbar_frame.setObjectName("libraryToolbar")
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(16, 14, 16, 14)
        toolbar_layout.setSpacing(12)

        self._search_box = QLineEdit()
        self._search_box.setObjectName("librarySearch")
        self._search_box.setPlaceholderText("Tìm theo tên, danh mục, phiên bản hoặc mô tả...")
        self._search_box.textChanged.connect(self._filter)
        toolbar_layout.addWidget(self._search_box, stretch=1)
        outer.addWidget(toolbar_frame)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        folder_panel = QFrame()
        folder_panel.setObjectName("folder_panel")
        fp_layout = QVBoxLayout(folder_panel)
        fp_layout.setContentsMargins(14, 14, 14, 14)
        fp_layout.setSpacing(8)

        folder_header = QLabel("Thư mục")
        folder_header.setObjectName("folderHeader")
        fp_layout.addWidget(folder_header)

        folder_hint = QLabel("Tạo các nhóm truy cập nhanh cho module bạn dùng thường xuyên.")
        folder_hint.setObjectName("folderHint")
        folder_hint.setWordWrap(True)
        fp_layout.addWidget(folder_hint)

        self._folder_list = QListWidget()
        self._folder_list.setObjectName("folder_list")
        self._folder_list.currentRowChanged.connect(self._on_folder_selected)
        self._folder_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._folder_list.customContextMenuRequested.connect(self._folder_context_menu)
        fp_layout.addWidget(self._folder_list, stretch=1)

        add_folder_btn = QPushButton("Tạo thư mục")
        add_folder_btn.setProperty("role", "ghost")
        add_folder_btn.clicked.connect(self._create_folder)
        fp_layout.addWidget(add_folder_btn)

        folder_panel.setMinimumWidth(160)
        folder_panel.setMaximumWidth(260)
        splitter.addWidget(folder_panel)

        card_frame = QFrame()
        card_frame.setObjectName("libraryChrome")
        card_layout = QVBoxLayout(card_frame)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(12)

        header_shell = QFrame()
        header_shell.setObjectName("librarySectionHeader")
        header_shell_layout = QHBoxLayout(header_shell)
        header_shell_layout.setContentsMargins(16, 14, 16, 14)
        header_shell_layout.setSpacing(12)

        text_shell = QVBoxLayout()
        text_shell.setSpacing(3)
        self._results_title = QLabel("Tất cả module")
        self._results_title.setObjectName("sectionTitle")
        self._results_meta = QLabel("0 kết quả")
        self._results_meta.setObjectName("sectionMeta")
        text_shell.addWidget(self._results_title)
        text_shell.addWidget(self._results_meta)

        self._add_module_btn = QPushButton("Thêm vào thư mục")
        self._add_module_btn.setProperty("role", "secondary")
        self._add_module_btn.clicked.connect(self._open_add_module_dialog)
        self._add_module_btn.setVisible(False)
        header_shell_layout.addLayout(text_shell, stretch=1)
        header_shell_layout.addWidget(self._add_module_btn)
        card_layout.addWidget(header_shell)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        self._container = QWidget()
        self._cards_layout = QVBoxLayout(self._container)
        self._cards_layout.setContentsMargins(16, 4, 16, 16)
        self._cards_layout.setSpacing(12)

        self._empty_state = self._build_empty_state()
        self._cards_layout.addWidget(self._empty_state)
        self._cards_layout.addStretch()

        scroll.setWidget(self._container)
        card_layout.addWidget(scroll, stretch=1)

        splitter.addWidget(card_frame)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([190, 600])

        outer.addWidget(splitter, stretch=1)

    def _build_empty_state(self) -> QWidget:
        return EmptyState(
            kicker="DISCOVERY",
            title="Chưa có module phù hợp",
            message="Thử đổi từ khóa tìm kiếm hoặc chọn một thư mục khác để tiếp tục khám phá module.",
        )

    # ── Folder management ─────────────────────────────────────────────────────

    def _refresh_folders(self) -> None:
        """Rebuild the folder list from DB + virtual 'All Modules'."""
        self._folder_list.blockSignals(True)
        self._folder_list.clear()

        all_item = QListWidgetItem(f"Tất cả module ({len(self._records)})")
        all_item.setData(Qt.ItemDataRole.UserRole, _ALL_MODULES_ID)
        self._folder_list.addItem(all_item)

        if self._folder_service:
            for folder in self._folder_service.list_folders():
                count = len(folder.items)
                item = QListWidgetItem(f"{folder.name} ({count})")
                item.setData(Qt.ItemDataRole.UserRole, folder.id)
                self._folder_list.addItem(item)

        self._select_folder_in_list(self._selected_folder_id)
        self._folder_list.blockSignals(False)

    def _select_folder_in_list(self, folder_id: int) -> None:
        for i in range(self._folder_list.count()):
            item = self._folder_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == folder_id:
                self._folder_list.setCurrentRow(i)
                return
        # Fallback to All Modules
        self._folder_list.setCurrentRow(0)

    def _on_folder_selected(self, row: int) -> None:
        item = self._folder_list.item(row)
        if item is None:
            return
        folder_id = item.data(Qt.ItemDataRole.UserRole)
        self._selected_folder_name = item.text().rsplit("(", 1)[0].strip()
        self._show_folder(folder_id)

    def _show_folder(self, folder_id: int) -> None:
        """Display module cards for the selected folder."""
        self._selected_folder_id = folder_id

        self._add_module_btn.setVisible(folder_id != _ALL_MODULES_ID)

        for card in self._cards:
            self._cards_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()

        if folder_id == _ALL_MODULES_ID:
            self._selected_folder_name = "Tất cả module"
            visible_records = self._records
        elif self._folder_service:
            module_ids = set(self._folder_service.get_folder_module_ids(folder_id))
            visible_records = [r for r in self._records if r.manifest.id in module_ids]
        else:
            visible_records = []

        for record in visible_records:
            m = record.manifest
            card = ModuleCard(
                module_id=m.id,
                name=m.name,
                category=m.category,
                version=m.version,
                description=m.description,
            )
            card.open_requested.connect(self.open_module)
            card.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            card.customContextMenuRequested.connect(
                lambda pos, c=card: self._card_context_menu(c, pos)
            )
            self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)
            self._cards.append(card)

        self._filter(self._search_box.text())

    # ── Folder context menu ───────────────────────────────────────────────────

    def _folder_context_menu(self, pos) -> None:
        item = self._folder_list.itemAt(pos)
        if item is None:
            return
        folder_id = item.data(Qt.ItemDataRole.UserRole)
        if folder_id == _ALL_MODULES_ID:
            return  # no context menu for All Modules

        menu = QMenu(self)
        rename_action = menu.addAction("Rename")
        delete_action = menu.addAction("Delete")

        action = menu.exec(self._folder_list.mapToGlobal(pos))
        if action == rename_action:
            self._rename_folder(folder_id)
        elif action == delete_action:
            self._delete_folder(folder_id)

    def _create_folder(self) -> None:
        if not self._folder_service:
            return
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if not ok or not name.strip():
            return
        folder = self._folder_service.create_folder(name.strip())
        if folder is None:
            QMessageBox.warning(self, "Error", f"Folder '{name.strip()}' already exists.")
            return
        self._refresh_folders()
        self._select_folder_in_list(folder.id)

    def _rename_folder(self, folder_id: int) -> None:
        if not self._folder_service:
            return
        name, ok = QInputDialog.getText(self, "Rename Folder", "New name:")
        if not ok or not name.strip():
            return
        success = self._folder_service.rename_folder(folder_id, name.strip())
        if not success:
            QMessageBox.warning(self, "Error", f"Cannot rename to '{name.strip()}'.")
            return
        self._refresh_folders()

    def _delete_folder(self, folder_id: int) -> None:
        if not self._folder_service:
            return
        reply = QMessageBox.question(
            self,
            "Delete Folder",
            "Delete this folder? Module shortcuts inside will be removed.\n"
            "The modules themselves will NOT be deleted.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._folder_service.delete_folder(folder_id)
        self._selected_folder_id = _ALL_MODULES_ID
        self._refresh_folders()
        self._show_folder(_ALL_MODULES_ID)

    # ── Card context menu ─────────────────────────────────────────────────────

    def _card_context_menu(self, card: ModuleCard, pos) -> None:
        if not self._folder_service:
            return
        menu = QMenu(self)

        if self._selected_folder_id == _ALL_MODULES_ID:
            # In All Modules: offer "Add to folder…"
            folders = self._folder_service.list_folders()
            if folders:
                add_menu = menu.addMenu("Add to folder…")
                for f in folders:
                    act = add_menu.addAction(f.name)
                    act.setData(f.id)
            else:
                no_act = menu.addAction("No custom folders yet")
                no_act.setEnabled(False)
        else:
            # In a custom folder: offer "Remove from this folder"
            menu.addAction("Remove from this folder")

        action = menu.exec(card.mapToGlobal(pos))
        if action is None:
            return

        if self._selected_folder_id == _ALL_MODULES_ID:
            target_folder_id = action.data()
            if target_folder_id is not None:
                added = self._folder_service.add_module_to_folder(
                    target_folder_id, card._module_id
                )
                if added:
                    self._refresh_folders()
                else:
                    QMessageBox.information(
                        self, "Info", "Module is already in that folder."
                    )
        else:
            self._folder_service.remove_module_from_folder(
                self._selected_folder_id, card._module_id
            )
            self._refresh_folders()
            self._show_folder(self._selected_folder_id)

    # ── Add module dialog ─────────────────────────────────────────────────────

    def _open_add_module_dialog(self) -> None:
        if not self._folder_service or self._selected_folder_id == _ALL_MODULES_ID:
            return
        existing_ids = set(
            self._folder_service.get_folder_module_ids(self._selected_folder_id)
        )
        available = [
            r for r in self._records if r.manifest.id not in existing_ids
        ]
        if not available:
            QMessageBox.information(
                self, "Info", "All modules are already in this folder."
            )
            return
        dlg = _AddModuleDialog(available, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            selected = dlg.selected_module_ids()
            for mid in selected:
                self._folder_service.add_module_to_folder(
                    self._selected_folder_id, mid
                )
            if selected:
                self._refresh_folders()
                self._show_folder(self._selected_folder_id)

    # ── Search filter ─────────────────────────────────────────────────────────

    def _filter(self, text: str) -> None:
        query = text.lower().strip()
        visible_count = 0
        for card in self._cards:
            visible = card.matches_query(query)
            card.setVisible(visible)
            if visible:
                visible_count += 1

        total_count = len(self._cards)
        self._module_count_pill.setText(f"{len(self._records)} module")
        self._results_title.setText(self._selected_folder_name)
        if query:
            self._results_meta.setText(f"{visible_count}/{total_count} kết quả cho '{query}'")
        else:
            self._results_meta.setText(f"{visible_count} module sẵn sàng để mở")

        self._empty_state.setVisible(visible_count == 0)


# ── Add-module picker dialog ──────────────────────────────────────────────────


class _AddModuleDialog(QDialog):
    """Modal dialog to pick modules from All Modules to add to a folder."""

    def __init__(
        self, records: list[ModuleRecord], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Modules to Folder")
        self.setMinimumSize(420, 360)
        self._checkboxes: list[tuple[QCheckBox, str]] = []
        self._setup_ui(records)

    def _setup_ui(self, records: list[ModuleRecord]) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        hint = QLabel("Select modules to add as shortcuts:")
        layout.addWidget(hint)

        # Filter box
        self._dlg_filter = QLineEdit()
        self._dlg_filter.setPlaceholderText("Filter…")
        self._dlg_filter.textChanged.connect(self._apply_filter)
        layout.addWidget(self._dlg_filter)

        # Scrollable checkbox list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        container = QWidget()
        self._cb_layout = QVBoxLayout(container)
        self._cb_layout.setSpacing(4)

        for record in records:
            m = record.manifest
            cb = QCheckBox(f"{m.name}  ({m.category} • v{m.version})")
            cb.setProperty("module_id", m.id)
            self._cb_layout.addWidget(cb)
            self._checkboxes.append((cb, m.id))

        self._cb_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll, stretch=1)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_module_ids(self) -> list[str]:
        return [mid for cb, mid in self._checkboxes if cb.isChecked()]

    def _apply_filter(self, text: str) -> None:
        q = text.lower().strip()
        for cb, mid in self._checkboxes:
            cb.setVisible(not q or q in cb.text().lower() or q in mid.lower())
