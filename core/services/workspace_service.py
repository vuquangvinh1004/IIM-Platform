"""Workspace service — active module tracking and workspace_items CRUD.

workspace_items store pinned / quick-launch shortcuts for modules the user
wants to keep visible in the workspace view.  Each item is linked to a
module_registry row via module_id.
"""
from __future__ import annotations

from dataclasses import dataclass

from core.storage.models import WorkspaceItem
from core.storage.session import get_session
from core.utils.logger import get_logger

_log = get_logger("iimp.services.workspace")


@dataclass
class WorkspaceItemData:
    """Plain data class returned by WorkspaceService — no ORM objects leaked."""

    id: int
    module_id: str
    title: str | None
    pinned: bool
    sort_order: int


class WorkspaceService:
    """Manages workspace state and workspace_items persistence."""

    def __init__(self) -> None:
        self._active_module_id: str | None = None

    # ── Active module tracking ────────────────────────────────────────────────

    @property
    def active_module_id(self) -> str | None:
        return self._active_module_id

    def set_active(self, module_id: str | None) -> None:
        self._active_module_id = module_id
        _log.debug(f"Active module: {module_id}")

    # ── workspace_items CRUD ─────────────────────────────────────────────────

    def get_all_items(self) -> list[WorkspaceItemData]:
        """Return all workspace items ordered by sort_order ascending."""
        with get_session() as session:
            rows = (
                session.query(WorkspaceItem)
                .order_by(WorkspaceItem.sort_order.asc())
                .all()
            )
            return [_to_data(r) for r in rows]

    def get_pinned_items(self) -> list[WorkspaceItemData]:
        """Return only pinned workspace items ordered by sort_order."""
        with get_session() as session:
            rows = (
                session.query(WorkspaceItem)
                .filter_by(pinned=True)
                .order_by(WorkspaceItem.sort_order.asc())
                .all()
            )
            return [_to_data(r) for r in rows]

    def add_item(self, module_id: str, title: str | None = None) -> WorkspaceItemData:
        """Add *module_id* to workspace items.  No-op if already present.

        Returns the existing or newly created item data.
        """
        with get_session() as session:
            existing = session.query(WorkspaceItem).filter_by(module_id=module_id).first()
            if existing:
                return _to_data(existing)
            max_order = session.query(WorkspaceItem).count()
            item = WorkspaceItem(
                module_id=module_id,
                title=title,
                pinned=False,
                sort_order=max_order,
            )
            session.add(item)
            session.flush()
            _log.info(f"WorkspaceItem added: {module_id}")
            return _to_data(item)

    def remove_item(self, module_id: str) -> bool:
        """Remove *module_id* from workspace items.

        Returns True if the item existed and was removed, False otherwise.
        """
        with get_session() as session:
            item = session.query(WorkspaceItem).filter_by(module_id=module_id).first()
            if item is None:
                return False
            session.delete(item)
            _log.info(f"WorkspaceItem removed: {module_id}")
            return True

    def set_pinned(self, module_id: str, pinned: bool = True) -> bool:
        """Pin or unpin a workspace item.

        Creates the workspace item if it does not exist yet.
        Returns True if the item is now in the requested pin state.
        """
        with get_session() as session:
            item = session.query(WorkspaceItem).filter_by(module_id=module_id).first()
            if item is None:
                max_order = session.query(WorkspaceItem).count()
                item = WorkspaceItem(
                    module_id=module_id,
                    pinned=pinned,
                    sort_order=max_order,
                )
                session.add(item)
            else:
                item.pinned = pinned
            _log.info(f"WorkspaceItem pin={pinned}: {module_id}")
            return True

    def reorder(self, ordered_module_ids: list[str]) -> None:
        """Update sort_order to match the given list order.

        Module IDs not present in the list are left unchanged at higher
        sort_order values.
        """
        with get_session() as session:
            for pos, module_id in enumerate(ordered_module_ids):
                item = session.query(WorkspaceItem).filter_by(module_id=module_id).first()
                if item is not None:
                    item.sort_order = pos
        _log.debug(f"WorkspaceItem reordered: {ordered_module_ids}")

    def is_pinned(self, module_id: str) -> bool:
        """Return True if *module_id* has a pinned workspace item."""
        with get_session() as session:
            item = session.query(WorkspaceItem).filter_by(module_id=module_id).first()
            return item is not None and bool(item.pinned)


def _to_data(item: WorkspaceItem) -> WorkspaceItemData:
    return WorkspaceItemData(
        id=item.id,
        module_id=item.module_id,
        title=item.title,
        pinned=bool(item.pinned),
        sort_order=item.sort_order,
    )
