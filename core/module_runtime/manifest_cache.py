"""Manifest discovery cache — avoids re-parsing unchanged module.json files.

On each startup the discovery pipeline calls ``get_cached_manifest()`` for
every module directory.  If the ``module.json`` has not been modified since the
last scan (based on ``mtime``), the previously-parsed manifest is returned
instantly, skipping JSON I/O and Pydantic validation.

The cache is stored as a single JSON file under ``data/cache/``.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from config.paths import CACHE_DIR
from core.utils.logger import get_logger

if TYPE_CHECKING:
    from core.module_runtime.manifest_schema import ModuleManifest

_log = get_logger("iimp.manifest_cache")

CACHE_FILE: Path = CACHE_DIR / "manifest_cache.json"
MANIFEST_FILENAME = "module.json"


class ManifestCache:
    """In-memory + on-disk cache for parsed module manifests."""

    def __init__(self, cache_file: Path = CACHE_FILE) -> None:
        self._cache_file = cache_file
        self._entries: dict[str, dict] = {}  # dir_path_str → {mtime, data}
        self._load()

    # ── Public API ────────────────────────────────────────────────────────────

    def get_cached_manifest(
        self,
        module_dir: Path,
    ) -> "ModuleManifest | None":
        """Return the cached manifest if the file hasn't changed, else None."""
        manifest_path = module_dir / MANIFEST_FILENAME
        if not manifest_path.exists():
            return None

        dir_key = str(module_dir.resolve())
        current_mtime = manifest_path.stat().st_mtime

        entry = self._entries.get(dir_key)
        if entry is not None and entry.get("mtime") == current_mtime:
            # Cache hit — reconstruct ModuleManifest from stored data
            try:
                from core.module_runtime.manifest_schema import ModuleManifest
                return ModuleManifest.model_validate(entry["data"])
            except Exception:
                _log.debug(f"Cache entry invalid for {dir_key}, will re-parse.")
                self._entries.pop(dir_key, None)

        return None

    def put(self, module_dir: Path, manifest: "ModuleManifest") -> None:
        """Store a freshly-parsed manifest in the cache."""
        manifest_path = module_dir / MANIFEST_FILENAME
        if not manifest_path.exists():
            return

        dir_key = str(module_dir.resolve())
        self._entries[dir_key] = {
            "mtime": manifest_path.stat().st_mtime,
            "data": manifest.model_dump(mode="json"),
        }

    def save(self) -> None:
        """Persist the cache to disk."""
        try:
            self._cache_file.parent.mkdir(parents=True, exist_ok=True)
            self._cache_file.write_text(
                json.dumps(self._entries, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            _log.warning(f"Could not write manifest cache: {exc}")

    def invalidate(self, module_dir: Path) -> None:
        """Remove a single entry from the cache."""
        dir_key = str(module_dir.resolve())
        self._entries.pop(dir_key, None)

    def clear(self) -> None:
        """Clear the entire cache."""
        self._entries.clear()
        if self._cache_file.exists():
            try:
                self._cache_file.unlink()
            except OSError:
                pass

    # ── Internal ──────────────────────────────────────────────────────────────

    def _load(self) -> None:
        """Load cache from disk if available."""
        if not self._cache_file.exists():
            return
        try:
            raw = json.loads(self._cache_file.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                self._entries = raw
                _log.debug(f"Manifest cache loaded: {len(self._entries)} entries.")
        except (json.JSONDecodeError, OSError) as exc:
            _log.warning(f"Could not read manifest cache: {exc}")
            self._entries = {}
