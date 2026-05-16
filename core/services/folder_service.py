"""Library folder service — CRUD for user-created module folders.

Folders organise module shortcuts in the library view.  The built-in
"All Modules" folder is virtual (not persisted); only custom folders
and their module shortcuts are stored in the database.
"""
from __future__ import annotations

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from core.storage.models import LibraryFolder, LibraryFolderItem
from core.storage.session import get_session
from core.utils.logger import get_logger

_log = get_logger("iimp.services.folder")


class FolderService:
    """Manages library folders and module shortcuts."""

    # ── Folder CRUD ───────────────────────────────────────────────────────────

    def list_folders(self) -> list[LibraryFolder]:
        with get_session() as session:
            rows = session.execute(
                select(LibraryFolder).order_by(LibraryFolder.sort_order, LibraryFolder.name)
            ).scalars().all()
            # Eagerly load items so they survive session close
            for row in rows:
                _ = row.items
            session.expunge_all()
            return list(rows)

    def create_folder(self, name: str) -> LibraryFolder | None:
        name = name.strip()
        if not name:
            return None
        with get_session() as session:
            try:
                folder = LibraryFolder(name=name)
                session.add(folder)
                session.flush()
                session.expunge(folder)
                _log.info(f"Created library folder: '{name}'")
                return folder
            except IntegrityError:
                session.rollback()
                _log.warning(f"Folder '{name}' already exists.")
                return None

    def rename_folder(self, folder_id: int, new_name: str) -> bool:
        new_name = new_name.strip()
        if not new_name:
            return False
        with get_session() as session:
            folder = session.get(LibraryFolder, folder_id)
            if folder is None:
                return False
            try:
                folder.name = new_name
                session.flush()
                _log.info(f"Renamed folder {folder_id} to '{new_name}'")
                return True
            except IntegrityError:
                session.rollback()
                _log.warning(f"Cannot rename: folder '{new_name}' already exists.")
                return False

    def delete_folder(self, folder_id: int) -> bool:
        with get_session() as session:
            folder = session.get(LibraryFolder, folder_id)
            if folder is None:
                return False
            name = folder.name
            session.delete(folder)
            _log.info(f"Deleted library folder: '{name}'")
            return True

    # ── Folder items (shortcuts) ──────────────────────────────────────────────

    def get_folder_module_ids(self, folder_id: int) -> list[str]:
        with get_session() as session:
            rows = session.execute(
                select(LibraryFolderItem.module_id)
                .where(LibraryFolderItem.folder_id == folder_id)
                .order_by(LibraryFolderItem.sort_order)
            ).scalars().all()
            return list(rows)

    def add_module_to_folder(self, folder_id: int, module_id: str) -> bool:
        with get_session() as session:
            try:
                item = LibraryFolderItem(folder_id=folder_id, module_id=module_id)
                session.add(item)
                session.flush()
                _log.info(f"Added shortcut '{module_id}' to folder {folder_id}")
                return True
            except IntegrityError:
                session.rollback()
                _log.debug(f"Module '{module_id}' already in folder {folder_id}")
                return False

    def remove_module_from_folder(self, folder_id: int, module_id: str) -> bool:
        with get_session() as session:
            item = session.execute(
                select(LibraryFolderItem).where(
                    LibraryFolderItem.folder_id == folder_id,
                    LibraryFolderItem.module_id == module_id,
                )
            ).scalar_one_or_none()
            if item is None:
                return False
            session.delete(item)
            _log.info(f"Removed shortcut '{module_id}' from folder {folder_id}")
            return True
