"""Tests for src/analysis/io_layer.py.

Integration tests (marked @pytest.mark.integration) require the actual
processed data files to be present on disk. Unit-style error-path tests
use monkeypatching and do not require real files.
"""
import pytest
import pandas as pd

from src.analysis.io_layer import (
    SubzoneLayer,
    load_subzones_with_population,
    load_electoral_boundaries,
    load_hdb_buildings,
    load_hdb_property_table,
)


# ---------------------------------------------------------------------------
# SubzoneLayer — integration tests (real data files)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_load_subzones_returns_subzone_layer():
    layer = load_subzones_with_population()
    assert isinstance(layer, SubzoneLayer)


@pytest.mark.integration
def test_load_subzones_wgs84_crs():
    layer = load_subzones_with_population()
    epsg = layer.wgs84.crs.to_epsg()
    crs_str = str(layer.wgs84.crs)
    assert epsg in (4326, 4269) or "CRS84" in crs_str


@pytest.mark.integration
def test_load_subzones_svy21_crs():
    layer = load_subzones_with_population()
    assert layer.svy21.crs.to_epsg() == 3414


@pytest.mark.integration
def test_load_subzones_required_columns():
    layer = load_subzones_with_population()
    for col in ["SUBZONE_N", "PLN_AREA_N", "pop_total", "subzone_name_norm", "geometry"]:
        assert col in layer.wgs84.columns, f"Missing column: {col}"


@pytest.mark.integration
def test_load_subzones_name_norm_is_uppercase():
    layer = load_subzones_with_population()
    assert (
        layer.wgs84["subzone_name_norm"] == layer.wgs84["subzone_name_norm"].str.upper()
    ).all()


@pytest.mark.integration
def test_load_subzones_unique_ids():
    layer = load_subzones_with_population()
    df = layer.wgs84
    id_col = "_feature_id" if "_feature_id" in df.columns else "FID"
    assert df[id_col].is_unique


@pytest.mark.integration
def test_load_subzones_nonempty():
    layer = load_subzones_with_population()
    assert len(layer.wgs84) >= 200


@pytest.mark.integration
def test_load_subzones_wgs84_and_svy21_same_row_count():
    layer = load_subzones_with_population()
    assert len(layer.wgs84) == len(layer.svy21)


@pytest.mark.integration
def test_load_subzones_does_not_mutate_between_calls():
    """Each call returns an independent object; adding a column to one does not affect the other."""
    layer1 = load_subzones_with_population()
    layer2 = load_subzones_with_population()
    # They should be equal in length but be different objects
    assert layer1.wgs84 is not layer2.wgs84


# ---------------------------------------------------------------------------
# Electoral boundaries — integration tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_load_electoral_2020():
    gdf = load_electoral_boundaries(2020)
    assert len(gdf) > 0
    assert "geometry" in gdf.columns


@pytest.mark.integration
def test_load_electoral_2020_count():
    gdf = load_electoral_boundaries(2020)
    assert len(gdf) == 31


@pytest.mark.integration
def test_load_electoral_2025():
    gdf = load_electoral_boundaries(2025)
    assert len(gdf) == 33


@pytest.mark.integration
def test_load_electoral_has_ed_name():
    gdf = load_electoral_boundaries(2020)
    assert "ED_DESC" in gdf.columns or "Name" in gdf.columns


@pytest.mark.integration
def test_load_electoral_2025_has_ed_name():
    gdf = load_electoral_boundaries(2025)
    assert "ED_DESC" in gdf.columns or "Name" in gdf.columns


@pytest.mark.integration
def test_load_electoral_unique_ids():
    for year in (2020, 2025):
        gdf = load_electoral_boundaries(year)
        id_col = "_feature_id" if "_feature_id" in gdf.columns else "FID"
        assert gdf[id_col].is_unique, f"Duplicate IDs in {year} electoral boundaries"


# ---------------------------------------------------------------------------
# Electoral boundaries — error-path (unit) tests
# ---------------------------------------------------------------------------


def test_load_electoral_invalid_year():
    with pytest.raises(ValueError, match="2020 or 2025"):
        load_electoral_boundaries(2019)


def test_load_electoral_invalid_year_future():
    with pytest.raises(ValueError, match="2020 or 2025"):
        load_electoral_boundaries(2030)


def test_load_subzones_missing_file(tmp_path, monkeypatch):
    import src.analysis.io_layer as io
    monkeypatch.setattr(io, "PROCESSED", tmp_path)
    with pytest.raises(FileNotFoundError, match="merge_census_and_geospatial"):
        io.load_subzones_with_population()


def test_load_electoral_missing_file(tmp_path, monkeypatch):
    import src.analysis.io_layer as io
    monkeypatch.setattr(io, "PROCESSED", tmp_path)
    with pytest.raises(FileNotFoundError, match="validate_and_copy_geospatial"):
        io.load_electoral_boundaries(2020)


# ---------------------------------------------------------------------------
# HDB buildings — integration tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_load_hdb_buildings_nonempty():
    gdf = load_hdb_buildings()
    assert len(gdf) > 0
    assert "geometry" in gdf.columns


@pytest.mark.integration
def test_load_hdb_buildings_has_crs():
    gdf = load_hdb_buildings()
    assert gdf.crs is not None


# ---------------------------------------------------------------------------
# HDB property table — integration tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_load_hdb_property_table_columns():
    df = load_hdb_property_table()
    for col in ["blk_no", "street", "bldg_contract_town"]:
        assert col in df.columns, f"Missing column: {col}"


@pytest.mark.integration
def test_load_hdb_property_table_returns_dataframe():
    df = load_hdb_property_table()
    assert isinstance(df, pd.DataFrame)


@pytest.mark.integration
def test_load_hdb_property_town_is_uppercase():
    df = load_hdb_property_table()
    non_null = df["bldg_contract_town"].dropna()
    assert (non_null == non_null.str.upper()).all()


@pytest.mark.integration
def test_load_hdb_property_town_is_stripped():
    df = load_hdb_property_table()
    non_null = df["bldg_contract_town"].dropna()
    assert (non_null == non_null.str.strip()).all()


@pytest.mark.integration
def test_load_hdb_property_table_nonempty():
    df = load_hdb_property_table()
    assert len(df) > 0


# ---------------------------------------------------------------------------
# HDB error paths
# ---------------------------------------------------------------------------


def test_load_hdb_buildings_missing_file(tmp_path, monkeypatch):
    import src.analysis.io_layer as io
    monkeypatch.setattr(io, "RAW", tmp_path)
    with pytest.raises(FileNotFoundError):
        io.load_hdb_buildings()


def test_load_hdb_property_table_missing_file(tmp_path, monkeypatch):
    import src.analysis.io_layer as io
    monkeypatch.setattr(io, "RAW", tmp_path)
    with pytest.raises(FileNotFoundError):
        io.load_hdb_property_table()
