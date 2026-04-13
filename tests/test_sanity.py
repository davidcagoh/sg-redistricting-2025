"""
Task 0.2 — Sanity tests for processed data files.

Ported from sanity.py with three fixes:
1. Uses PROCESSED from src.utils (absolute path) instead of relative paths.
2. Checks for unique polygon IDs under either _feature_id or FID (whichever is
   present), because electoral GeoJSON files use FID, not _feature_id.
3. All checks are pytest assertions — no bare print statements.
"""

import json

import pandas as pd
import pytest

from src.utils import PROCESSED


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def load_features(filename: str) -> list[dict]:
    path = PROCESSED / filename
    with open(path) as f:
        fc = json.load(f)
    return fc["features"]


# ---------------------------------------------------------------------------
# master_population_subzone.csv
# ---------------------------------------------------------------------------


def test_csv_exists():
    assert (PROCESSED / "master_population_subzone.csv").exists()


def test_csv_required_columns():
    df = pd.read_csv(PROCESSED / "master_population_subzone.csv")
    for col in ["subzone_id", "Number", "pop_total"]:
        assert col in df.columns, f"Missing column: {col}"


def test_csv_no_duplicate_subzone_ids():
    df = pd.read_csv(PROCESSED / "master_population_subzone.csv")
    assert df["subzone_id"].is_unique, "Duplicate subzone_id values found"


def test_csv_pop_total_non_negative():
    df = pd.read_csv(PROCESSED / "master_population_subzone.csv")
    assert (df["pop_total"] >= 0).all(), "Negative pop_total values found"


# ---------------------------------------------------------------------------
# subzone_with_population.geojson
# ---------------------------------------------------------------------------


def test_subzone_geojson_exists():
    assert (PROCESSED / "subzone_with_population.geojson").exists()


def test_subzone_geojson_crs():
    path = PROCESSED / "subzone_with_population.geojson"
    with open(path) as f:
        fc = json.load(f)
    crs_name = fc.get("crs", {}).get("properties", {}).get("name", "")
    assert "CRS84" in crs_name or "4326" in crs_name, f"Unexpected CRS: {crs_name}"


def test_subzone_geojson_has_features():
    features = load_features("subzone_with_population.geojson")
    assert len(features) > 0


def test_subzone_geojson_unique_feature_ids():
    features = load_features("subzone_with_population.geojson")
    ids = []
    for f in features:
        props = f.get("properties", {})
        # Use explicit None checks so that a legitimate ID value of 0 is not
        # treated as falsy and silently dropped.
        if "_feature_id" in props:
            fid = props["_feature_id"]
        else:
            fid = props.get("FID")
        assert fid is not None, f"Feature missing both _feature_id and FID: {props}"
        ids.append(fid)
    assert len(ids) == len(set(ids)), "Duplicate feature IDs found in subzone GeoJSON"


def test_subzone_geojson_has_pop_total():
    features = load_features("subzone_with_population.geojson")
    for f in features:
        assert "pop_total" in f.get("properties", {}), "Feature missing pop_total"


def test_subzone_geojson_subzone_n_present():
    features = load_features("subzone_with_population.geojson")
    for f in features:
        assert "SUBZONE_N" in f.get("properties", {}), "Feature missing SUBZONE_N"


# ---------------------------------------------------------------------------
# electoral_boundaries_2020.geojson
# ---------------------------------------------------------------------------


def test_electoral_2020_exists():
    assert (PROCESSED / "electoral_boundaries_2020.geojson").exists()


def test_electoral_2020_has_features():
    features = load_features("electoral_boundaries_2020.geojson")
    assert len(features) > 0


def test_electoral_2020_unique_ids():
    features = load_features("electoral_boundaries_2020.geojson")
    ids = []
    for f in features:
        props = f.get("properties", {})
        # Use explicit None checks: FID=0 is a valid ID and must not be discarded
        # by a falsy test.
        fid = props["FID"] if "FID" in props else props.get("_feature_id")
        assert fid is not None, f"Electoral 2020 feature missing FID/_feature_id: {props}"
        ids.append(fid)
    assert len(ids) == len(set(ids)), "Duplicate IDs in electoral_boundaries_2020.geojson"


def test_electoral_2020_has_ed_name():
    features = load_features("electoral_boundaries_2020.geojson")
    for f in features:
        props = f.get("properties", {})
        assert "ED_DESC" in props or "Name" in props, (
            f"Feature missing ED name field: {props}"
        )


# ---------------------------------------------------------------------------
# electoral_boundaries_2025.geojson
# ---------------------------------------------------------------------------


def test_electoral_2025_exists():
    assert (PROCESSED / "electoral_boundaries_2025.geojson").exists()


def test_electoral_2025_has_features():
    features = load_features("electoral_boundaries_2025.geojson")
    assert len(features) > 0


def test_electoral_2025_unique_ids():
    features = load_features("electoral_boundaries_2025.geojson")
    ids = []
    for f in features:
        props = f.get("properties", {})
        # Use explicit None checks: FID=0 is a valid ID and must not be discarded
        # by a falsy test.
        fid = props["FID"] if "FID" in props else props.get("_feature_id")
        assert fid is not None, f"Electoral 2025 feature missing FID/_feature_id: {props}"
        ids.append(fid)
    assert len(ids) == len(set(ids)), "Duplicate IDs in electoral_boundaries_2025.geojson"


def test_electoral_2025_has_ed_name():
    features = load_features("electoral_boundaries_2025.geojson")
    for f in features:
        props = f.get("properties", {})
        assert "ED_DESC" in props or "Name" in props, (
            f"Feature missing ED name field: {props}"
        )


def test_electoral_2025_has_33_divisions():
    """GE2025 should have 33 electoral divisions per EBRC 2025 report."""
    features = load_features("electoral_boundaries_2025.geojson")
    assert len(features) == 33, f"Expected 33 divisions for GE2025, got {len(features)}"
