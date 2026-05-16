"""Module discovery — scans the modules directory for valid module packages.

A valid package must contain a ``module.json`` at the top level of each
leaf directory. Nested category directories (e.g. ``modules/statistics/``)
are traversed recursively.

Performance: a manifest cache (ManifestCache) avoids re-parsing unchanged
``module.json`` files on repeated startups.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from config.paths import MODULES_DIR
from core.module_runtime.loader import load_manifest
from core.module_runtime.manifest_cache import ManifestCache
from core.module_runtime.manifest_schema import ModuleManifest
from core.module_runtime.registry import ModuleRegistry
from core.utils.constants import ModuleState
from core.utils.exceptions import ManifestError
from core.utils.logger import get_logger

_log = get_logger("iimp.discovery")

MANIFEST_FILENAME = "module.json"

# Module-level cache instance (created once per process)
_manifest_cache = ManifestCache()


def discover_modules(
    registry: ModuleRegistry,
    modules_dir: Path | None = None,
    *,
    on_progress: Callable[[int, int, str], None] | None = None,
) -> tuple[int, int]:
    """Scan *modules_dir* for module packages and register valid ones.

    Args:
        registry: The runtime module registry.
        modules_dir: Override for the default modules directory.
        on_progress: Optional callback ``(current, total, module_name)``
            invoked after each manifest is processed.  Used by the splash
            screen to report startup progress.

    Returns:
        (found, failed) counts.
    """
    scan_dir = modules_dir or MODULES_DIR
    if not scan_dir.exists():
        _log.warning(f"Modules directory does not exist: {scan_dir}")
        return 0, 0

    _log.info(f"Scanning for modules in: {scan_dir}")

    manifest_paths = sorted(scan_dir.rglob(MANIFEST_FILENAME))
    total = len(manifest_paths)
    found = 0
    failed = 0

    for idx, manifest_path in enumerate(manifest_paths, start=1):
        module_dir = manifest_path.parent
        try:
            # Try cache first
            manifest: ModuleManifest | None = _manifest_cache.get_cached_manifest(module_dir)
            if manifest is None:
                manifest = load_manifest(module_dir)
                _manifest_cache.put(module_dir, manifest)

            if registry.is_registered(manifest.id):
                _log.debug(f"Skipping duplicate: {manifest.id}")
                if on_progress:
                    on_progress(idx, total, manifest.name)
                continue

            registry.register(manifest, module_dir)
            registry.set_state(manifest.id, ModuleState.VALIDATED)
            found += 1
            _log.info(f"Discovered module: {manifest.id} v{manifest.version} @ {module_dir}")
        except ManifestError as exc:
            _log.error(f"Manifest error in '{module_dir}': {exc}")
            failed += 1

        if on_progress:
            name = manifest.name if manifest else module_dir.name
            on_progress(idx, total, name)

    # Persist cache to disk after full scan
    _manifest_cache.save()

    _log.info(f"Discovery complete. Found: {found}, Failed: {failed}")
    return found, failed
