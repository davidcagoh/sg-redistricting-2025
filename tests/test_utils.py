"""
Unit tests for src/utils.py.

TDD: all tests are written before any implementation exists.
Run: pytest tests/test_utils.py
"""
import hashlib
import math
import tempfile
from pathlib import Path

import pytest

from src.utils import (
    ensure_crs,
    ensure_feature_ids,
    file_sha256,
    normalize_subzone_name,
)

# ---------------------------------------------------------------------------
# normalize_subzone_name
# ---------------------------------------------------------------------------


class TestNormalizeSubzoneName:
    def test_strips_and_uppercases(self):
        assert normalize_subzone_name("  bedok  north ") == "BEDOK NORTH"

    def test_already_normalized(self):
        assert normalize_subzone_name("ANG MO KIO") == "ANG MO KIO"

    def test_none_returns_empty_string(self):
        assert normalize_subzone_name(None) == ""

    def test_nan_returns_empty_string(self):
        assert normalize_subzone_name(float("nan")) == ""

    def test_non_string_integer_returns_empty_string(self):
        assert normalize_subzone_name(42) == ""

    def test_empty_string_returns_empty_string(self):
        assert normalize_subzone_name("") == ""


# ---------------------------------------------------------------------------
# ensure_crs
# ---------------------------------------------------------------------------

_WGS84_CRS84 = {
    "type": "name",
    "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
}


class TestEnsureCrs:
    def test_injects_crs_when_missing(self):
        result = ensure_crs({})
        assert "crs" in result
        assert result["crs"] == _WGS84_CRS84

    def test_preserves_existing_crs_unchanged(self):
        original_crs = {"type": "name", "properties": {"name": "EPSG:4326"}}
        fc = {"crs": original_crs}
        result = ensure_crs(fc)
        assert result["crs"] == original_crs

    def test_does_not_mutate_input(self):
        fc = {}
        ensure_crs(fc)
        assert fc == {}

    def test_returns_different_object_than_input(self):
        fc = {}
        result = ensure_crs(fc)
        assert result is not fc

    def test_returns_shallow_copy_with_existing_crs(self):
        fc = {"crs": _WGS84_CRS84, "type": "FeatureCollection"}
        result = ensure_crs(fc)
        assert result is not fc
        assert result["type"] == "FeatureCollection"


# ---------------------------------------------------------------------------
# ensure_feature_ids
# ---------------------------------------------------------------------------


class TestEnsureFeatureIds:
    def test_fills_missing_ids_avoiding_collisions(self):
        features = [
            {"_feature_id": 1},
            {"_feature_id": 3},
            {},
            {},
        ]
        result = ensure_feature_ids(features)

        assert len(result) == 4
        assert result[0]["_feature_id"] == 1
        assert result[1]["_feature_id"] == 3

        taken = {1, 3}
        assert result[2]["_feature_id"] not in taken
        assert result[3]["_feature_id"] not in taken
        assert result[2]["_feature_id"] != result[3]["_feature_id"]

    def test_all_features_already_have_ids(self):
        features = [
            {"_feature_id": 10, "name": "a"},
            {"_feature_id": 20, "name": "b"},
        ]
        result = ensure_feature_ids(features)
        assert result[0]["_feature_id"] == 10
        assert result[1]["_feature_id"] == 20

    def test_does_not_mutate_input_dicts(self):
        feat_with_id = {"_feature_id": 5, "data": "x"}
        feat_without_id = {"data": "y"}
        original_without_id_copy = dict(feat_without_id)

        ensure_feature_ids([feat_with_id, feat_without_id])

        # Original dicts must not be modified
        assert "_feature_id" not in feat_without_id
        assert feat_without_id == original_without_id_copy

    def test_gap_filling_assigns_next_available(self):
        """[{_feature_id:1}, {}] -> missing one should get id=2."""
        features = [{"_feature_id": 1}, {}]
        result = ensure_feature_ids(features)
        assert result[1]["_feature_id"] == 2

    def test_empty_list_returns_empty_list(self):
        assert ensure_feature_ids([]) == []


# ---------------------------------------------------------------------------
# file_sha256
# ---------------------------------------------------------------------------


class TestFileSha256:
    def test_returns_64_char_lowercase_hex(self, tmp_path):
        p = tmp_path / "sample.txt"
        p.write_text("hello world", encoding="utf-8")
        digest = file_sha256(p)
        assert len(digest) == 64
        assert digest == digest.lower()
        assert all(c in "0123456789abcdef" for c in digest)

    def test_deterministic_same_file(self, tmp_path):
        p = tmp_path / "data.bin"
        p.write_bytes(b"\x00\x01\x02\x03" * 1000)
        assert file_sha256(p) == file_sha256(p)

    def test_matches_hashlib_reference(self, tmp_path):
        content = b"Singapore electoral redistricting"
        p = tmp_path / "ref.bin"
        p.write_bytes(content)
        expected = hashlib.sha256(content).hexdigest()
        assert file_sha256(p) == expected

    def test_raises_file_not_found(self, tmp_path):
        missing = tmp_path / "does_not_exist.txt"
        with pytest.raises(FileNotFoundError):
            file_sha256(missing)
