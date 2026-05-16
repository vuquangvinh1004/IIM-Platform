"""Unit tests for helpers and validators."""
from __future__ import annotations

import pytest

from core.utils.helpers import (
    parse_version,
    safe_json_dumps,
    safe_json_loads,
    truncate,
    version_satisfies,
)
from core.utils.validators import (
    validate_entry_point,
    validate_module_id,
    validate_permissions,
    validate_semver,
)


class TestParseVersion:
    def test_simple(self):
        assert parse_version("1.2.3") == (1, 2, 3)

    def test_two_parts(self):
        assert parse_version("1.0") == (1, 0)

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_version("abc")

    def test_all_separators_raises(self):
        """An input with only dots/dashes produces an empty tuple → ValueError."""
        with pytest.raises(ValueError):
            parse_version("...")


class TestVersionSatisfies:
    def test_equal(self):
        assert version_satisfies("1.0.0", "1.0.0") is True

    def test_newer(self):
        assert version_satisfies("2.0.0", "1.0.0") is True

    def test_older(self):
        assert version_satisfies("0.9.0", "1.0.0") is False

    def test_bad_versions_return_false(self):
        assert version_satisfies("bad", "1.0.0") is False


class TestSafeJson:
    def test_loads_valid(self):
        assert safe_json_loads('{"a": 1}') == {"a": 1}

    def test_loads_invalid_returns_fallback(self):
        assert safe_json_loads("not json", fallback={}) == {}

    def test_dumps_valid(self):
        assert safe_json_dumps({"x": 1}) == '{"x": 1}'

    def test_dumps_invalid_returns_fallback(self):
        class Bad:
            pass
        assert safe_json_dumps(Bad()) == "{}"


class TestTruncate:
    def test_short_string_unchanged(self):
        assert truncate("hello", 80) == "hello"

    def test_long_string_truncated(self):
        text = "x" * 100
        result = truncate(text, 10)
        assert len(result) == 10
        assert result.endswith("…")

    def test_exact_length_unchanged(self):
        text = "abc"
        assert truncate(text, 3) == "abc"


class TestValidators:
    def test_valid_id(self):
        assert validate_module_id("my_module-01") == "my_module-01"

    def test_id_with_spaces_raises(self):
        with pytest.raises(ValueError):
            validate_module_id("bad id")

    def test_id_empty_raises(self):
        with pytest.raises(ValueError):
            validate_module_id("")

    def test_id_none_raises(self):
        with pytest.raises(ValueError):
            validate_module_id(None)

    def test_valid_semver(self):
        assert validate_semver("1.2.3") == "1.2.3"

    def test_semver_empty_raises(self):
        with pytest.raises(ValueError):
            validate_semver("")

    def test_semver_invalid_raises(self):
        with pytest.raises(ValueError):
            validate_semver("not.a.version.abc")

    def test_valid_entry_point(self):
        assert validate_entry_point("a.b.c:Class") == "a.b.c:Class"

    def test_entry_point_without_colon_raises(self):
        with pytest.raises(ValueError):
            validate_entry_point("a.b.c.Class")

    def test_entry_point_empty_raises(self):
        with pytest.raises(ValueError):
            validate_entry_point("")

    def test_permissions_valid(self):
        result = validate_permissions(["storage.read", "export.file"])
        assert result == ["storage.read", "export.file"]

    def test_permissions_not_list_raises(self):
        with pytest.raises(ValueError):
            validate_permissions("storage.read")

    def test_permissions_non_string_item_raises(self):
        with pytest.raises(ValueError):
            validate_permissions([1, 2, 3])

