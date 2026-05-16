"""SQLAlchemy ORM models matching the official DB schema in IIMP_ARCHITECTURE.md §8.

Rules:
- Models are thin data containers — no business logic here.
- All JSON fields are stored as TEXT and serialized/deserialized by service layer.
- Foreign key relationships use ON DELETE CASCADE for child tables.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.database import Base


class ModuleRegistry(Base):
    """Tracks all discovered/installed modules."""

    __tablename__ = "module_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    module_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str | None] = mapped_column(String)
    version: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    entry_point: Mapped[str] = mapped_column(String, nullable=False)
    install_path: Mapped[str] = mapped_column(String, nullable=False)
    icon_path: Mapped[str | None] = mapped_column(String)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    permissions: Mapped[str | None] = mapped_column(Text)  # JSON array
    tags: Mapped[str | None] = mapped_column(Text)  # JSON array
    min_platform_version: Mapped[str | None] = mapped_column(String)
    installed_at: Mapped[datetime] = mapped_column(default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.now, onupdate=datetime.now)

    settings: Mapped[list[ModuleSettings]] = relationship(
        "ModuleSettings", back_populates="registry", cascade="all, delete-orphan"
    )
    sessions: Mapped[list[ModuleSession]] = relationship(
        "ModuleSession", back_populates="registry", cascade="all, delete-orphan"
    )
    workspace_items: Mapped[list[WorkspaceItem]] = relationship(
        "WorkspaceItem", back_populates="registry", cascade="all, delete-orphan"
    )


class ModuleSettings(Base):
    """Per-module key-value configuration store."""

    __tablename__ = "module_settings"
    __table_args__ = (UniqueConstraint("module_id", "setting_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    module_id: Mapped[str] = mapped_column(
        String, ForeignKey("module_registry.module_id", ondelete="CASCADE"), nullable=False
    )
    setting_key: Mapped[str] = mapped_column(String, nullable=False)
    setting_value: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.now, onupdate=datetime.now)

    registry: Mapped[ModuleRegistry] = relationship("ModuleRegistry", back_populates="settings")


class ModuleSession(Base):
    """Persisted session state for each module."""

    __tablename__ = "module_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    module_id: Mapped[str] = mapped_column(
        String, ForeignKey("module_registry.module_id", ondelete="CASCADE"), nullable=False
    )
    session_name: Mapped[str | None] = mapped_column(String)
    session_state: Mapped[str | None] = mapped_column(Text)  # JSON dict
    is_last_active: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.now, onupdate=datetime.now)

    registry: Mapped[ModuleRegistry] = relationship("ModuleRegistry", back_populates="sessions")


class WorkspaceItem(Base):
    """Pinned / quick-launch items in the workspace view."""

    __tablename__ = "workspace_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    module_id: Mapped[str] = mapped_column(
        String, ForeignKey("module_registry.module_id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(String)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.now, onupdate=datetime.now)

    registry: Mapped[ModuleRegistry] = relationship(
        "ModuleRegistry", back_populates="workspace_items"
    )


class AppSettings(Base):
    """Global application settings key-value store."""

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    setting_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    setting_value: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.now, onupdate=datetime.now)


class ActivityLog(Base):
    """Audit log for significant application events."""

    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    module_id: Mapped[str | None] = mapped_column(String)
    activity_type: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)


class InstalledArtifact(Base):
    """Records every installed artifact (module, template, asset)."""

    __tablename__ = "installed_artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    artifact_type: Mapped[str] = mapped_column(String, nullable=False)  # MODULE|TEMPLATE|ASSET
    artifact_name: Mapped[str] = mapped_column(String, nullable=False)
    artifact_version: Mapped[str | None] = mapped_column(String)
    artifact_path: Mapped[str] = mapped_column(String, nullable=False)
    checksum: Mapped[str | None] = mapped_column(String)
    installed_at: Mapped[datetime] = mapped_column(default=datetime.now)


class LibraryFolder(Base):
    """User-created folder in the module library view."""

    __tablename__ = "library_folders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.now, onupdate=datetime.now)

    items: Mapped[list["LibraryFolderItem"]] = relationship(
        "LibraryFolderItem", back_populates="folder", cascade="all, delete-orphan"
    )


class LibraryFolderItem(Base):
    """Shortcut linking a module to a user-created library folder."""

    __tablename__ = "library_folder_items"
    __table_args__ = (UniqueConstraint("folder_id", "module_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    folder_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("library_folders.id", ondelete="CASCADE"), nullable=False
    )
    module_id: Mapped[str] = mapped_column(String, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)

    folder: Mapped[LibraryFolder] = relationship("LibraryFolder", back_populates="items")
