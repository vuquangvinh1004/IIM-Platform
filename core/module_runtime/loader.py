"""Module loader for IIMP.

Responsibilities:
- Load a module.json, validate it, import the entry point class.
- Instantiate the module with manifest + context.
- Raise typed exceptions on failure so callers can show fallback UI.

This is the only place where ``importlib`` is used for module loading.
"""
from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ValidationError

from core.module_runtime.base_module import BaseModule
from core.module_runtime.manifest_schema import ModuleManifest
from core.utils.exceptions import (
    DependencyMissingError,
    ManifestNotFoundError,
    ManifestValidationError,
    ModuleLoadError,
    ModuleNotFoundError,
)
from core.utils.imports import check_dependencies
from core.utils.logger import get_logger

if TYPE_CHECKING:
    from core.module_runtime.module_context import ModuleContext

_log = get_logger("iimp.loader")

MANIFEST_FILENAME = "module.json"


def load_manifest(module_dir: Path) -> ModuleManifest:
    """Read and validate the manifest from *module_dir*.

    Raises:
        ManifestNotFoundError: if module.json is absent.
        ManifestValidationError: if the manifest fails schema validation.
    """
    manifest_path = module_dir / MANIFEST_FILENAME
    if not manifest_path.exists():
        raise ManifestNotFoundError(str(module_dir))

    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ManifestValidationError(str(module_dir), f"JSON parse error: {exc}") from exc

    try:
        return ModuleManifest.model_validate(raw)
    except ValidationError as exc:
        raise ManifestValidationError(str(module_dir), str(exc)) from exc


def check_optional_dependencies(manifest: ModuleManifest) -> list[str]:
    """Return list of missing optional dependencies declared in *manifest*.

    If the list is non-empty the caller should decide whether to block
    loading or show a degraded-mode warning.
    """
    deps = manifest.optional_dependencies
    if not deps:
        return []
    missing = check_dependencies(deps)
    if missing:
        _log.warning(
            "Module '%s' is missing optional dependencies: %s",
            manifest.id,
            ", ".join(missing),
        )
    return missing


def load_module_class(manifest: ModuleManifest) -> type[BaseModule]:
    """Import and return the module class named in *manifest.entry_point*.

    Raises:
        ModuleNotFoundError: if the import or attribute lookup fails.
    """
    module_path, _, class_name = manifest.entry_point.partition(":")
    try:
        py_module = importlib.import_module(module_path)
    except ImportError as exc:
        raise ModuleNotFoundError(
            manifest.id,
            f"Cannot import '{module_path}': {exc}",
        ) from exc

    cls = getattr(py_module, class_name, None)
    if cls is None:
        raise ModuleNotFoundError(
            manifest.id,
            f"Class '{class_name}' not found in '{module_path}'",
        )
    if not (isinstance(cls, type) and issubclass(cls, BaseModule)):
        raise ModuleLoadError(
            manifest.id,
            f"'{class_name}' is not a subclass of BaseModule",
        )
    return cls


def instantiate_module(
    module_dir: Path,
    context: "ModuleContext",
) -> BaseModule:
    """Full load pipeline: manifest → validate → import → instantiate.

    Raises typed exceptions on any failure step.
    """
    manifest = load_manifest(module_dir)

    # Pre-check optional dependencies before importing module code
    missing = check_optional_dependencies(manifest)
    if missing:
        raise DependencyMissingError(manifest.id, missing)

    cls = load_module_class(manifest)
    try:
        instance = cls(manifest=manifest.model_dump(), context=context)
        instance.on_load()
        _log.info(f"Module loaded: {manifest.id} v{manifest.version}")
        return instance
    except Exception as exc:
        raise ModuleLoadError(manifest.id, f"Instantiation failed: {exc}") from exc
