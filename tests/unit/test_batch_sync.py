"""Tests for batch DB sync optimisation — Phương án C."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.module_runtime.manifest_schema import ModuleManifest
from core.module_runtime.registry import ModuleRecord, ModuleRegistry
from core.services.app_services import AppServices
from core.services.module_service import ModuleService
from core.utils.constants import ModuleState


def _manifest(mod_id: str) -> ModuleManifest:
    return ModuleManifest.model_validate({
        "id": mod_id,
        "name": f"Module {mod_id}",
        "version": "1.0.0",
        "sdk_version": "1.0.0",
        "min_platform_version": "1.0.0",
        "entry_point": f"modules.{mod_id}.entry:Mod",
        "description": f"Test module {mod_id}",
        "category": "test",
        "author": "Tests",
        "permissions": [],
        "tags": [],
        "supports_state_restore": False,
        "supports_export": False,
    })


class TestBatchSync:
    """Verify _sync_registry_to_db uses batch query."""

    def test_sync_uses_single_query_for_existing(self, tmp_path: Path):
        """Ensure only one .all() query is issued, not N filter_by() queries."""
        registry = ModuleRegistry()
        for i in range(5):
            mid = f"mod_{i}"
            m = _manifest(mid)
            registry.register(m, tmp_path / mid)
            registry.set_state(mid, ModuleState.VALIDATED)

        svc = ModuleService(
            registry=registry,
            services=AppServices(
                event_bus=MagicMock(),
                settings=MagicMock(),
                activity=MagicMock(),
                paths=MagicMock(),
                export=MagicMock(),
                dialogs=MagicMock(),
                theme=MagicMock(),
            ),
        )

        # Patch get_session to track queries
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.all.return_value = []  # No existing rows

        from contextlib import contextmanager

        @contextmanager
        def fake_session():
            yield mock_session

        with patch("core.services.module_service.get_session", fake_session):
            svc._sync_registry_to_db()

        # Should call .all() once for batch load — not filter_by() per module
        mock_query.all.assert_called_once()
        # Should NOT have called filter_by at all
        mock_query.filter_by.assert_not_called()
        # Should have added 5 new records
        assert mock_session.add.call_count == 5
