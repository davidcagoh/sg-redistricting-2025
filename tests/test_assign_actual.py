"""Tests for src/analysis/assign_actual.py.

TDD: tests written BEFORE implementation (RED phase).
All tests use in-memory synthetic GeoDataFrames in EPSG:3414 — no disk I/O.

Functions under test:
    assign_subzones_to_eds(subzones, electoral) -> pd.DataFrame
    assign_actual_plan(year, graph, subzones_svy21, electoral) -> dict[int, str]
"""
from __future__ import annotations

import pandas as pd
import pytest
import geopandas as gpd
import networkx as nx
from shapely.geometry import box

from src.analysis.assign_actual import assign_subzones_to_eds, assign_actual_plan


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def make_subzones(specs: list[dict]) -> gpd.GeoDataFrame:
    """Build a minimal subzone GeoDataFrame in EPSG:3414.

    Each spec dict must have keys: fid, name, geometry (a Shapely geometry).
    pop_total and PLN_AREA_N are filled with defaults.
    """
    return gpd.GeoDataFrame(
        {
            "_feature_id": [s["fid"] for s in specs],
            "subzone_name_norm": [s["name"] for s in specs],
            "PLN_AREA_N": [s.get("pln_area", "PA_DEFAULT") for s in specs],
            "pop_total": [s.get("pop_total", 100) for s in specs],
        },
        geometry=[s["geometry"] for s in specs],
        crs="EPSG:3414",
    )


def make_electoral(specs: list[dict]) -> gpd.GeoDataFrame:
    """Build a minimal electoral GeoDataFrame in EPSG:3414 with ED_DESC column."""
    return gpd.GeoDataFrame(
        {
            "ED_DESC": [s["ed_name"] for s in specs],
        },
        geometry=[s["geometry"] for s in specs],
        crs="EPSG:3414",
    )


def make_graph_from_subzones(subzones: gpd.GeoDataFrame) -> nx.Graph:
    """Build a trivial graph (no edges needed) from a subzone GeoDataFrame.

    Node IDs are integer row indices, matching build_subzone_graph convention.
    """
    G = nx.Graph()
    for idx, row in subzones.iterrows():
        G.add_node(
            idx,
            subzone_name_norm=row["subzone_name_norm"],
            pln_area=row["PLN_AREA_N"],
            pop_total=int(row["pop_total"]),
            area_m2=float(row.geometry.area),
            _feature_id=row["_feature_id"],
        )
    return G


# ---------------------------------------------------------------------------
# SVY21 coordinate ranges used in fixtures
# Easting: ~100 000 – 50 000 m relative; Northing: ~0 – 50 000 m relative
# We use small boxes starting at (10_000, 10_000) for simplicity.
# ---------------------------------------------------------------------------

ORIGIN_X = 10_000.0
ORIGIN_Y = 10_000.0
CELL = 1_000.0  # 1 km cells


# ---------------------------------------------------------------------------
# TestAssignSubzonesToEds
# ---------------------------------------------------------------------------


class TestAssignSubzonesToEds:
    """Unit tests for assign_subzones_to_eds."""

    def test_subzone_entirely_inside_one_ed(self) -> None:
        """A subzone wholly within ED1 must be assigned to ED1."""
        # Subzone: small box inside ED1
        sz_geom = box(ORIGIN_X, ORIGIN_Y, ORIGIN_X + CELL, ORIGIN_Y + CELL)
        # ED1: large box that fully contains the subzone
        ed1_geom = box(ORIGIN_X - CELL, ORIGIN_Y - CELL, ORIGIN_X + 2 * CELL, ORIGIN_Y + 2 * CELL)
        # ED2: far away, no overlap
        ed2_geom = box(ORIGIN_X + 5 * CELL, ORIGIN_Y + 5 * CELL, ORIGIN_X + 7 * CELL, ORIGIN_Y + 7 * CELL)

        subzones = make_subzones([{"fid": 0, "name": "SZ_INSIDE", "geometry": sz_geom}])
        electoral = make_electoral([
            {"ed_name": "ED_ONE", "geometry": ed1_geom},
            {"ed_name": "ED_TWO", "geometry": ed2_geom},
        ])

        result = assign_subzones_to_eds(subzones, electoral)

        assert len(result) == 1
        row = result.iloc[0]
        assert row["ed_name"] == "ED_ONE"

    def test_subzone_majority_overlap_wins(self) -> None:
        """When a subzone straddles two EDs, the one with greater overlap wins."""
        # Subzone spans x = [10_000, 12_000], so it covers 2 km
        sz_geom = box(ORIGIN_X, ORIGIN_Y, ORIGIN_X + 2 * CELL, ORIGIN_Y + CELL)
        # ED_BIG covers 75% of the subzone (x = [9_000, 11_500])
        ed_big_geom = box(ORIGIN_X - CELL, ORIGIN_Y - CELL, ORIGIN_X + 1.5 * CELL, ORIGIN_Y + 2 * CELL)
        # ED_SMALL covers 25% (x = [11_500, 13_000])
        ed_small_geom = box(ORIGIN_X + 1.5 * CELL, ORIGIN_Y - CELL, ORIGIN_X + 3 * CELL, ORIGIN_Y + 2 * CELL)

        subzones = make_subzones([{"fid": 1, "name": "SZ_SPLIT", "geometry": sz_geom}])
        electoral = make_electoral([
            {"ed_name": "ED_BIG", "geometry": ed_big_geom},
            {"ed_name": "ED_SMALL", "geometry": ed_small_geom},
        ])

        result = assign_subzones_to_eds(subzones, electoral)

        assert len(result) == 1
        assert result.iloc[0]["ed_name"] == "ED_BIG"

    def test_subzone_no_overlap_returns_none(self) -> None:
        """A subzone with no overlap with any ED gets ed_name=None."""
        # Subzone far from any ED
        sz_geom = box(ORIGIN_X + 20 * CELL, ORIGIN_Y + 20 * CELL,
                      ORIGIN_X + 21 * CELL, ORIGIN_Y + 21 * CELL)
        ed_geom = box(ORIGIN_X, ORIGIN_Y, ORIGIN_X + CELL, ORIGIN_Y + CELL)

        subzones = make_subzones([{"fid": 2, "name": "SZ_ORPHAN", "geometry": sz_geom}])
        electoral = make_electoral([{"ed_name": "ED_SOMEWHERE", "geometry": ed_geom}])

        result = assign_subzones_to_eds(subzones, electoral)

        assert len(result) == 1
        assert result.iloc[0]["ed_name"] is None

    def test_returns_dataframe_with_required_columns(self) -> None:
        """Result must contain: _feature_id, subzone_name_norm, ed_name, overlap_area_m2, assignment_method."""
        sz_geom = box(ORIGIN_X, ORIGIN_Y, ORIGIN_X + CELL, ORIGIN_Y + CELL)
        ed_geom = box(ORIGIN_X - CELL, ORIGIN_Y - CELL, ORIGIN_X + 2 * CELL, ORIGIN_Y + 2 * CELL)

        subzones = make_subzones([{"fid": 3, "name": "SZ_COLS", "geometry": sz_geom}])
        electoral = make_electoral([{"ed_name": "ED_COLS", "geometry": ed_geom}])

        result = assign_subzones_to_eds(subzones, electoral)

        required_cols = {"_feature_id", "subzone_name_norm", "ed_name", "overlap_area_m2", "assignment_method"}
        assert required_cols.issubset(set(result.columns)), (
            f"Missing columns: {required_cols - set(result.columns)}"
        )

    def test_assignment_method_is_areal_majority(self) -> None:
        """assignment_method must be 'areal_majority' for all matched rows."""
        sz_geom = box(ORIGIN_X, ORIGIN_Y, ORIGIN_X + CELL, ORIGIN_Y + CELL)
        ed_geom = box(ORIGIN_X - CELL, ORIGIN_Y - CELL, ORIGIN_X + 2 * CELL, ORIGIN_Y + 2 * CELL)

        subzones = make_subzones([{"fid": 4, "name": "SZ_METHOD", "geometry": sz_geom}])
        electoral = make_electoral([{"ed_name": "ED_METHOD", "geometry": ed_geom}])

        result = assign_subzones_to_eds(subzones, electoral)

        matched = result[result["ed_name"].notna()]
        assert (matched["assignment_method"] == "areal_majority").all()

    def test_returns_one_row_per_subzone(self) -> None:
        """Result has exactly one row per input subzone."""
        geoms = [
            box(ORIGIN_X + i * CELL, ORIGIN_Y, ORIGIN_X + (i + 1) * CELL, ORIGIN_Y + CELL)
            for i in range(3)
        ]
        # Single large ED covers all subzones
        ed_geom = box(ORIGIN_X - CELL, ORIGIN_Y - CELL, ORIGIN_X + 4 * CELL, ORIGIN_Y + 2 * CELL)

        subzones = make_subzones([
            {"fid": i, "name": f"SZ_{i:02d}", "geometry": g}
            for i, g in enumerate(geoms)
        ])
        electoral = make_electoral([{"ed_name": "ED_BIG", "geometry": ed_geom}])

        result = assign_subzones_to_eds(subzones, electoral)

        assert len(result) == 3

    def test_uses_epsg3414_coords(self) -> None:
        """Inputs in EPSG:3414 are handled correctly (no CRS error raised)."""
        sz_geom = box(ORIGIN_X, ORIGIN_Y, ORIGIN_X + CELL, ORIGIN_Y + CELL)
        ed_geom = box(ORIGIN_X - CELL, ORIGIN_Y - CELL, ORIGIN_X + 2 * CELL, ORIGIN_Y + 2 * CELL)

        subzones = make_subzones([{"fid": 5, "name": "SZ_CRS", "geometry": sz_geom}])
        electoral = make_electoral([{"ed_name": "ED_CRS", "geometry": ed_geom}])

        # Must not raise even though values are in SVY21 numeric range
        result = assign_subzones_to_eds(subzones, electoral)
        assert isinstance(result, pd.DataFrame)

    def test_feature_id_propagated(self) -> None:
        """_feature_id in result matches the input subzone's _feature_id."""
        sz_geom = box(ORIGIN_X, ORIGIN_Y, ORIGIN_X + CELL, ORIGIN_Y + CELL)
        ed_geom = box(ORIGIN_X - CELL, ORIGIN_Y - CELL, ORIGIN_X + 2 * CELL, ORIGIN_Y + 2 * CELL)

        subzones = make_subzones([{"fid": 42, "name": "SZ_FID", "geometry": sz_geom}])
        electoral = make_electoral([{"ed_name": "ED_FID", "geometry": ed_geom}])

        result = assign_subzones_to_eds(subzones, electoral)
        assert result.iloc[0]["_feature_id"] == 42

    def test_subzone_name_norm_propagated(self) -> None:
        """subzone_name_norm in result matches the input subzone's name."""
        sz_geom = box(ORIGIN_X, ORIGIN_Y, ORIGIN_X + CELL, ORIGIN_Y + CELL)
        ed_geom = box(ORIGIN_X - CELL, ORIGIN_Y - CELL, ORIGIN_X + 2 * CELL, ORIGIN_Y + 2 * CELL)

        subzones = make_subzones([{"fid": 6, "name": "BISHAN EAST", "geometry": sz_geom}])
        electoral = make_electoral([{"ed_name": "ED_BISHAN", "geometry": ed_geom}])

        result = assign_subzones_to_eds(subzones, electoral)
        assert result.iloc[0]["subzone_name_norm"] == "BISHAN EAST"

    def test_overlap_area_m2_positive_when_matched(self) -> None:
        """overlap_area_m2 must be > 0 for successfully assigned subzones."""
        sz_geom = box(ORIGIN_X, ORIGIN_Y, ORIGIN_X + CELL, ORIGIN_Y + CELL)
        ed_geom = box(ORIGIN_X - CELL, ORIGIN_Y - CELL, ORIGIN_X + 2 * CELL, ORIGIN_Y + 2 * CELL)

        subzones = make_subzones([{"fid": 7, "name": "SZ_AREA", "geometry": sz_geom}])
        electoral = make_electoral([{"ed_name": "ED_AREA", "geometry": ed_geom}])

        result = assign_subzones_to_eds(subzones, electoral)
        matched = result[result["ed_name"].notna()]
        assert (matched["overlap_area_m2"] > 0).all()

    def test_multiple_subzones_multiple_eds(self) -> None:
        """Multiple subzones each dominated by different EDs are assigned correctly."""
        # Two subzones side-by-side; two EDs each covering one subzone
        sz0_geom = box(ORIGIN_X, ORIGIN_Y, ORIGIN_X + CELL, ORIGIN_Y + CELL)
        sz1_geom = box(ORIGIN_X + 2 * CELL, ORIGIN_Y, ORIGIN_X + 3 * CELL, ORIGIN_Y + CELL)

        ed0_geom = box(ORIGIN_X - CELL, ORIGIN_Y - CELL, ORIGIN_X + 1.5 * CELL, ORIGIN_Y + 2 * CELL)
        ed1_geom = box(ORIGIN_X + 1.5 * CELL, ORIGIN_Y - CELL, ORIGIN_X + 4 * CELL, ORIGIN_Y + 2 * CELL)

        subzones = make_subzones([
            {"fid": 0, "name": "SZ_LEFT", "geometry": sz0_geom},
            {"fid": 1, "name": "SZ_RIGHT", "geometry": sz1_geom},
        ])
        electoral = make_electoral([
            {"ed_name": "ED_LEFT", "geometry": ed0_geom},
            {"ed_name": "ED_RIGHT", "geometry": ed1_geom},
        ])

        result = assign_subzones_to_eds(subzones, electoral)
        result_map = dict(zip(result["subzone_name_norm"], result["ed_name"]))

        assert result_map["SZ_LEFT"] == "ED_LEFT"
        assert result_map["SZ_RIGHT"] == "ED_RIGHT"

    def test_empty_subzones_returns_empty_dataframe(self) -> None:
        """Empty subzone input returns empty DataFrame with correct columns."""
        subzones = make_subzones([])
        ed_geom = box(ORIGIN_X, ORIGIN_Y, ORIGIN_X + CELL, ORIGIN_Y + CELL)
        electoral = make_electoral([{"ed_name": "ED_ONE", "geometry": ed_geom}])

        result = assign_subzones_to_eds(subzones, electoral)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
        required_cols = {"_feature_id", "subzone_name_norm", "ed_name", "overlap_area_m2", "assignment_method"}
        assert required_cols.issubset(set(result.columns))

    def test_result_is_dataframe_not_geodataframe(self) -> None:
        """Return type must be plain pd.DataFrame, not GeoDataFrame."""
        sz_geom = box(ORIGIN_X, ORIGIN_Y, ORIGIN_X + CELL, ORIGIN_Y + CELL)
        ed_geom = box(ORIGIN_X - CELL, ORIGIN_Y - CELL, ORIGIN_X + 2 * CELL, ORIGIN_Y + 2 * CELL)

        subzones = make_subzones([{"fid": 8, "name": "SZ_TYPE", "geometry": sz_geom}])
        electoral = make_electoral([{"ed_name": "ED_TYPE", "geometry": ed_geom}])

        result = assign_subzones_to_eds(subzones, electoral)

        # Must be DataFrame; GeoDataFrame is a subclass so check exact type
        assert type(result) is pd.DataFrame

    def test_electoral_with_name_column_fallback(self) -> None:
        """Electoral GeoDataFrame with 'Name' column (not 'ED_DESC') is accepted."""
        sz_geom = box(ORIGIN_X, ORIGIN_Y, ORIGIN_X + CELL, ORIGIN_Y + CELL)
        ed_geom = box(ORIGIN_X - CELL, ORIGIN_Y - CELL, ORIGIN_X + 2 * CELL, ORIGIN_Y + 2 * CELL)

        subzones = make_subzones([{"fid": 9, "name": "SZ_FALLBACK", "geometry": sz_geom}])
        # Use 'Name' column instead of 'ED_DESC'
        electoral = gpd.GeoDataFrame(
            {"Name": ["ED_NAME_COL"]},
            geometry=[ed_geom],
            crs="EPSG:3414",
        )

        result = assign_subzones_to_eds(subzones, electoral)

        assert len(result) == 1
        assert result.iloc[0]["ed_name"] == "ED_NAME_COL"

    def test_electoral_missing_both_name_columns_raises(self) -> None:
        """ValueError raised when electoral has neither 'ED_DESC' nor 'Name'."""
        sz_geom = box(ORIGIN_X, ORIGIN_Y, ORIGIN_X + CELL, ORIGIN_Y + CELL)
        ed_geom = box(ORIGIN_X - CELL, ORIGIN_Y - CELL, ORIGIN_X + 2 * CELL, ORIGIN_Y + 2 * CELL)

        subzones = make_subzones([{"fid": 10, "name": "SZ_ERR", "geometry": sz_geom}])
        electoral = gpd.GeoDataFrame(
            {"WRONG_COL": ["ED_UNKNOWN"]},
            geometry=[ed_geom],
            crs="EPSG:3414",
        )

        with pytest.raises(ValueError, match="neither"):
            assign_subzones_to_eds(subzones, electoral)

    def test_reprojection_from_wgs84_works(self) -> None:
        """Inputs in WGS84 are auto-reprojected to EPSG:3414 without error."""
        # Singapore bounding box in WGS84 degrees
        sz_geom = box(103.8, 1.3, 103.81, 1.31)
        ed_geom = box(103.79, 1.29, 103.82, 1.32)

        subzones = gpd.GeoDataFrame(
            {
                "_feature_id": [0],
                "subzone_name_norm": ["SZ_WGS"],
                "PLN_AREA_N": ["PA"],
                "pop_total": [100],
            },
            geometry=[sz_geom],
            crs="EPSG:4326",
        )
        electoral = gpd.GeoDataFrame(
            {"ED_DESC": ["ED_WGS"]},
            geometry=[ed_geom],
            crs="EPSG:4326",
        )

        result = assign_subzones_to_eds(subzones, electoral)

        assert len(result) == 1
        assert result.iloc[0]["ed_name"] == "ED_WGS"

    def test_empty_electoral_returns_none_for_all_subzones(self) -> None:
        """When electoral GeoDataFrame is empty, all subzones get ed_name=None."""
        sz_geom = box(ORIGIN_X, ORIGIN_Y, ORIGIN_X + CELL, ORIGIN_Y + CELL)
        subzones = make_subzones([{"fid": 11, "name": "SZ_NOELEC", "geometry": sz_geom}])
        # Empty electoral GDF — must have the column but zero rows
        electoral = gpd.GeoDataFrame(
            {"ED_DESC": pd.Series([], dtype=str)},
            geometry=gpd.GeoSeries([], dtype="geometry"),
            crs="EPSG:3414",
        )

        result = assign_subzones_to_eds(subzones, electoral)

        assert len(result) == 1
        assert result.iloc[0]["ed_name"] is None


# ---------------------------------------------------------------------------
# TestAssignActualPlan
# ---------------------------------------------------------------------------


class TestAssignActualPlan:
    """Unit tests for assign_actual_plan."""

    def _build_scenario(self) -> tuple[nx.Graph, gpd.GeoDataFrame, gpd.GeoDataFrame]:
        """Return (graph, subzones_svy21, electoral) for a simple 3-subzone scenario."""
        sz_geoms = [
            box(ORIGIN_X + i * CELL, ORIGIN_Y, ORIGIN_X + (i + 1) * CELL, ORIGIN_Y + CELL)
            for i in range(3)
        ]
        subzones = make_subzones([
            {"fid": i, "name": f"SZ_{i:02d}", "geometry": g}
            for i, g in enumerate(sz_geoms)
        ])
        # One large ED covers all three subzones
        ed_geom = box(ORIGIN_X - CELL, ORIGIN_Y - CELL, ORIGIN_X + 4 * CELL, ORIGIN_Y + 2 * CELL)
        electoral = make_electoral([{"ed_name": "ED_ALL", "geometry": ed_geom}])
        graph = make_graph_from_subzones(subzones)
        return graph, subzones, electoral

    def test_returns_dict(self) -> None:
        """assign_actual_plan must return a dict."""
        graph, subzones, electoral = self._build_scenario()
        result = assign_actual_plan(2020, graph, subzones, electoral)
        assert isinstance(result, dict)

    def test_all_graph_nodes_in_result(self) -> None:
        """Every node in the graph must have an entry in the result dict."""
        graph, subzones, electoral = self._build_scenario()
        result = assign_actual_plan(2020, graph, subzones, electoral)
        assert set(result.keys()) == set(graph.nodes())

    def test_node_ids_match_graph_node_ids(self) -> None:
        """Keys of result dict match graph node IDs exactly."""
        graph, subzones, electoral = self._build_scenario()
        result = assign_actual_plan(2025, graph, subzones, electoral)
        assert set(result.keys()) == set(graph.nodes())

    def test_matched_nodes_get_ed_name(self) -> None:
        """Nodes whose subzone overlaps an ED receive the correct ed_name string."""
        graph, subzones, electoral = self._build_scenario()
        result = assign_actual_plan(2020, graph, subzones, electoral)
        for _node_id, ed_name in result.items():
            assert ed_name == "ED_ALL", f"Expected 'ED_ALL', got {ed_name!r}"

    def test_unmatched_nodes_get_none(self) -> None:
        """Nodes with no electoral overlap receive None."""
        # Subzone far from any ED
        sz_far_geom = box(ORIGIN_X + 50 * CELL, ORIGIN_Y + 50 * CELL,
                          ORIGIN_X + 51 * CELL, ORIGIN_Y + 51 * CELL)
        subzones = make_subzones([{"fid": 99, "name": "SZ_FAR", "geometry": sz_far_geom}])
        ed_geom = box(ORIGIN_X, ORIGIN_Y, ORIGIN_X + CELL, ORIGIN_Y + CELL)
        electoral = make_electoral([{"ed_name": "ED_NEAR", "geometry": ed_geom}])
        graph = make_graph_from_subzones(subzones)

        result = assign_actual_plan(2020, graph, subzones, electoral)

        assert result[0] is None

    def test_year_argument_accepted_2020(self) -> None:
        """year=2020 is accepted without error."""
        graph, subzones, electoral = self._build_scenario()
        result = assign_actual_plan(2020, graph, subzones, electoral)
        assert result is not None

    def test_year_argument_accepted_2025(self) -> None:
        """year=2025 is accepted without error."""
        graph, subzones, electoral = self._build_scenario()
        result = assign_actual_plan(2025, graph, subzones, electoral)
        assert result is not None

    def test_empty_graph_returns_empty_dict(self) -> None:
        """An empty graph returns an empty dict."""
        subzones = make_subzones([])
        ed_geom = box(ORIGIN_X, ORIGIN_Y, ORIGIN_X + CELL, ORIGIN_Y + CELL)
        electoral = make_electoral([{"ed_name": "ED_ONLY", "geometry": ed_geom}])
        graph = nx.Graph()

        result = assign_actual_plan(2020, graph, subzones, electoral)

        assert result == {}

    def test_result_values_are_strings_or_none(self) -> None:
        """All values in the result dict are either str or None."""
        graph, subzones, electoral = self._build_scenario()
        result = assign_actual_plan(2020, graph, subzones, electoral)
        for node_id, ed_name in result.items():
            assert ed_name is None or isinstance(ed_name, str), (
                f"Node {node_id} has unexpected value type: {type(ed_name)}"
            )

    def test_input_subzones_not_mutated(self) -> None:
        """The subzones GeoDataFrame is not mutated by the function."""
        graph, subzones, electoral = self._build_scenario()
        cols_before = list(subzones.columns)
        crs_before = subzones.crs

        assign_actual_plan(2020, graph, subzones, electoral)

        assert list(subzones.columns) == cols_before
        assert subzones.crs == crs_before

    def test_input_electoral_not_mutated(self) -> None:
        """The electoral GeoDataFrame is not mutated by the function."""
        graph, subzones, electoral = self._build_scenario()
        cols_before = list(electoral.columns)

        assign_actual_plan(2020, graph, subzones, electoral)

        assert list(electoral.columns) == cols_before
