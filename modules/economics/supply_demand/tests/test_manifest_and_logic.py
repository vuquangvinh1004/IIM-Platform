"""Smoke tests for supply_demand module manifest and logic."""
import json
import pathlib

MODULE_DIR = pathlib.Path(__file__).parent.parent


def test_manifest_exists():
    assert (MODULE_DIR / "module.json").exists()


def test_manifest_required_fields():
    manifest = json.loads((MODULE_DIR / "module.json").read_text(encoding="utf-8"))
    required = [
        "id", "name", "version", "sdk_version", "min_platform_version",
        "entry_point", "description", "category", "author",
        "permissions", "tags", "supports_state_restore", "supports_export",
    ]
    for field in required:
        assert field in manifest, f"Missing required field: {field}"


def test_manifest_entry_point():
    manifest = json.loads((MODULE_DIR / "module.json").read_text(encoding="utf-8"))
    ep = manifest["entry_point"]
    assert "supply_demand" in ep
    assert ep.endswith("SupplyDemandModule")


def test_equilibrium_calculation():
    """Pure logic test — no Qt dependency."""
    import sys
    sys.path.insert(0, str(MODULE_DIR.parent.parent.parent))
    # Import only constants (no Qt needed)
    from modules.economics.supply_demand.module import (
        _equilibrium, BASE_S_INTERCEPT, BASE_S_SLOPE,
        BASE_D_INTERCEPT, BASE_D_SLOPE,
    )
    p_eq, q_eq = _equilibrium(
        BASE_S_INTERCEPT, BASE_S_SLOPE, BASE_D_INTERCEPT, BASE_D_SLOPE
    )
    assert abs(p_eq - 16.0) < 0.1, f"Expected P*=16, got {p_eq}"
    assert abs(q_eq - 38.0) < 0.5, f"Expected Q*=38, got {q_eq}"


def test_shift_moves_equilibrium():
    """Shifting supply should change equilibrium."""
    import sys
    sys.path.insert(0, str(MODULE_DIR.parent.parent.parent))
    from modules.economics.supply_demand.module import (
        _equilibrium, BASE_S_SLOPE, BASE_D_INTERCEPT, BASE_D_SLOPE,
    )
    # Shift supply right (increase intercept by 10)
    p_eq_new, q_eq_new = _equilibrium(
        -10.0 + 10.0, BASE_S_SLOPE, BASE_D_INTERCEPT, BASE_D_SLOPE
    )
    # More supply -> lower price, higher quantity
    assert p_eq_new < 16.0
    assert q_eq_new > 38.0
