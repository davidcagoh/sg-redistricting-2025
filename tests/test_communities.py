"""Tests for src/analysis/communities.py — attach_hdb_towns.

TDD: tests written before implementation.
Unit tests use fully synthetic in-memory fixtures.
@pytest.mark.slow test exercises real data from disk.
"""
from __future__ import annotations

import logging

import geopandas as gpd
import networkx as nx
import pandas as pd
import pytest
from shapely.geometry import Point, box

from src.analysis.communities import attach_hdb_towns


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def make_two_subzone_graph() -> nx.Graph:
    """2 adjacent subzones as a minimal graph."""
    G = nx.Graph()
    G.add_node(
        0,
        subzone_name_norm="SUBZONE_A",
        pln_area="PA1",
        pop_total=1000,
        area_m2=1e6,
        _feature_id=0,
    )
    G.add_node(
        1,
        subzone_name_norm="SUBZONE_B",
        pln_area="PA1",
        pop_total=800,
        area_m2=1e6,
        _feature_id=1,
    )
    G.add_edge(0, 1, shared_perimeter_m=1000)
    return G


def make_two_subzone_gdf() -> gpd.GeoDataFrame:
    """Matching GeoDataFrame for the 2-subzone graph, in EPSG:3414."""
    return gpd.GeoDataFrame(
        {
            "subzone_name_norm": ["SUBZONE_A", "SUBZONE_B"],
            "PLN_AREA_N": ["PA1", "PA1"],
            "pop_total": [1000, 800],
            "_feature_id": [0, 1],
        },
        geometry=[box(0, 0, 1000, 1000), box(1000, 0, 2000, 1000)],
        crs="EPSG:3414",
    )


def make_buildings(points_with_towns: list[tuple[float, float, str]]) -> gpd.GeoDataFrame:
    """Build a buildings GeoDataFrame from (x, y, town_code) tuples."""
    geoms, blk_nos, streets = [], [], []
    for i, (x, y, _) in enumerate(points_with_towns):
        geoms.append(Point(x, y))
        blk_nos.append(str(i + 1))
        streets.append(f"FAKE ST {i + 1}")
    return gpd.GeoDataFrame(
        {"blk_no": blk_nos, "street": streets},
        geometry=geoms,
        crs="EPSG:3414",
    )


def make_properties(points_with_towns: list[tuple[float, float, str]]) -> pd.DataFrame:
    """Build a matching property DataFrame from (x, y, town_code) tuples."""
    rows = []
    for i, (_, _, town) in enumerate(points_with_towns):
        rows.append(
            {
                "blk_no": str(i + 1),
                "street": f"FAKE ST {i + 1}",
                "bldg_contract_town": town,
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


class TestAttachHdbTowns:
    def test_returns_new_graph(self) -> None:
        """Result must be a new graph object, not the same reference."""
        G = make_two_subzone_graph()
        buildings = make_buildings([(500, 500, "BD"), (1500, 500, "AK")])
        props = make_properties([(500, 500, "BD"), (1500, 500, "AK")])
        result = attach_hdb_towns(G, make_two_subzone_gdf(), buildings, props)
        assert result is not G

    def test_majority_town_correct(self) -> None:
        """Majority-vote town label and purity are computed correctly per subzone.

        Subzone A (x 0-1000): 3 BD buildings, 1 AK building → majority BD, purity 0.75
        Subzone B (x 1000-2000): 4 AK buildings → majority AK, purity 1.0
        """
        pts = [
            (100, 100, "BD"),
            (200, 200, "BD"),
            (300, 300, "BD"),
            (400, 400, "AK"),
            (1100, 100, "AK"),
            (1200, 200, "AK"),
            (1300, 300, "AK"),
            (1400, 400, "AK"),
        ]
        G = make_two_subzone_graph()
        buildings = make_buildings(pts)
        props = make_properties(pts)
        result = attach_hdb_towns(G, make_two_subzone_gdf(), buildings, props)

        assert result.nodes[0]["hdb_town"] == "BD"
        assert result.nodes[1]["hdb_town"] == "AK"
        assert abs(result.nodes[0]["hdb_town_purity"] - 0.75) < 0.01
        assert abs(result.nodes[1]["hdb_town_purity"] - 1.0) < 0.01

    def test_no_buildings_in_subzone(self) -> None:
        """Subzone with zero buildings gets hdb_town=None and hdb_town_purity=0.0."""
        pts = [(100, 100, "BD"), (200, 200, "BD")]
        G = make_two_subzone_graph()
        buildings = make_buildings(pts)
        props = make_properties(pts)
        result = attach_hdb_towns(G, make_two_subzone_gdf(), buildings, props)

        assert result.nodes[0]["hdb_town"] == "BD"
        assert result.nodes[1]["hdb_town"] is None
        assert result.nodes[1]["hdb_town_purity"] == 0.0

    def test_input_graph_not_mutated(self) -> None:
        """The original graph must not be modified after the call."""
        G = make_two_subzone_graph()
        assert "hdb_town" not in G.nodes[0]
        buildings = make_buildings([(500, 500, "BD")])
        props = make_properties([(500, 500, "BD")])
        attach_hdb_towns(G, make_two_subzone_gdf(), buildings, props)
        assert "hdb_town" not in G.nodes[0]

    def test_all_nodes_get_hdb_town_attr(self) -> None:
        """Every node in the result must carry both hdb_town and hdb_town_purity."""
        pts = [(500, 500, "BD"), (1500, 500, "AK")]
        G = make_two_subzone_graph()
        buildings = make_buildings(pts)
        props = make_properties(pts)
        result = attach_hdb_towns(G, make_two_subzone_gdf(), buildings, props)
        for n in result.nodes:
            assert "hdb_town" in result.nodes[n]
            assert "hdb_town_purity" in result.nodes[n]

    def test_low_join_rate_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """A WARNING is emitted when the building-property join rate is below 80%."""
        # Buildings with no matching property rows → join rate = 0%
        buildings = make_buildings([(500, 500, "BD")])
        props = pd.DataFrame(
            [{"blk_no": "999", "street": "NOWHERE", "bldg_contract_town": "BD"}]
        )
        G = make_two_subzone_graph()
        with caplog.at_level(logging.WARNING):
            attach_hdb_towns(G, make_two_subzone_gdf(), buildings, props)
        assert any(
            "join rate" in msg.lower() or "join" in msg.lower()
            for msg in caplog.messages
        )

    def test_purity_warning_logged_for_mixed_subzone(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A WARNING is logged for subzones where purity < 0.7."""
        # Subzone A: 3 BD, 3 AK → purity = 0.5, below threshold
        pts = [
            (100, 100, "BD"),
            (200, 200, "BD"),
            (300, 300, "BD"),
            (400, 400, "AK"),
            (500, 500, "AK"),
            (600, 600, "AK"),
        ]
        G = make_two_subzone_graph()
        buildings = make_buildings(pts)
        props = make_properties(pts)
        with caplog.at_level(logging.WARNING):
            attach_hdb_towns(G, make_two_subzone_gdf(), buildings, props)
        assert any("purity" in msg.lower() for msg in caplog.messages)

    def test_buildings_reprojected_from_wgs84(self) -> None:
        """Buildings in WGS84 are reprojected to EPSG:3414 before the spatial join."""
        # Point(103.82, 1.35) is roughly in Singapore, near subzone A coords when reprojected
        # We use actual SVY21 coords converted to WGS84 for a reliable test.
        # SVY21 (500, 500) → approximate WGS84 via pyproj
        from pyproj import Transformer

        transformer = Transformer.from_crs("EPSG:3414", "EPSG:4326", always_xy=True)
        lon, lat = transformer.transform(500, 500)

        buildings_wgs84 = gpd.GeoDataFrame(
            {"blk_no": ["1"], "street": ["FAKE ST 1"]},
            geometry=[Point(lon, lat)],
            crs="EPSG:4326",
        )
        props = pd.DataFrame([{"blk_no": "1", "street": "FAKE ST 1", "bldg_contract_town": "BD"}])
        G = make_two_subzone_graph()
        result = attach_hdb_towns(G, make_two_subzone_gdf(), buildings_wgs84, props)
        # Should land in subzone 0 (0-1000 x 0-1000 in SVY21)
        assert result.nodes[0]["hdb_town"] == "BD"

    def test_tie_broken_deterministically(self) -> None:
        """When two towns tie in a subzone the result is a string (not None or error)."""
        # 1 BD, 1 AK in subzone 0 — pandas mode returns the first alphabetically
        pts = [(100, 100, "AK"), (200, 200, "BD")]
        G = make_two_subzone_graph()
        buildings = make_buildings(pts)
        props = make_properties(pts)
        result = attach_hdb_towns(G, make_two_subzone_gdf(), buildings, props)
        town = result.nodes[0]["hdb_town"]
        assert isinstance(town, str)
        assert town in {"AK", "BD"}

    def test_graph_edges_preserved(self) -> None:
        """Edges from the input graph must be present unchanged in the result."""
        pts = [(500, 500, "BD"), (1500, 500, "AK")]
        G = make_two_subzone_graph()
        buildings = make_buildings(pts)
        props = make_properties(pts)
        result = attach_hdb_towns(G, make_two_subzone_gdf(), buildings, props)
        assert result.has_edge(0, 1)
        assert result.edges[0, 1]["shared_perimeter_m"] == 1000

    def test_case_insensitive_join_key_normalization(self) -> None:
        """Buildings and properties are joined after strip+upper normalization."""
        buildings = gpd.GeoDataFrame(
            {"blk_no": ["  1a  "], "street": ["  clementi ave 1  "]},
            geometry=[Point(500, 500)],
            crs="EPSG:3414",
        )
        props = pd.DataFrame(
            [
                {
                    "blk_no": "1A",
                    "street": "CLEMENTI AVE 1",
                    "bldg_contract_town": "CT",
                }
            ]
        )
        G = make_two_subzone_graph()
        result = attach_hdb_towns(G, make_two_subzone_gdf(), buildings, props)
        assert result.nodes[0]["hdb_town"] == "CT"

    def test_four_node_graph_all_labeled(self) -> None:
        """A 2x2 grid graph: all four subzones receive town labels."""
        # Four subzones in a 2×2 grid
        gdf = gpd.GeoDataFrame(
            {
                "subzone_name_norm": ["A", "B", "C", "D"],
                "PLN_AREA_N": ["P1", "P1", "P1", "P1"],
                "pop_total": [100, 100, 100, 100],
                "_feature_id": [0, 1, 2, 3],
            },
            geometry=[
                box(0, 0, 1000, 1000),
                box(1000, 0, 2000, 1000),
                box(0, 1000, 1000, 2000),
                box(1000, 1000, 2000, 2000),
            ],
            crs="EPSG:3414",
        )
        G = nx.Graph()
        for i in range(4):
            G.add_node(i, subzone_name_norm=gdf.iloc[i]["subzone_name_norm"],
                       pln_area="P1", pop_total=100, area_m2=1e6, _feature_id=i)
        G.add_edge(0, 1)
        G.add_edge(0, 2)
        G.add_edge(1, 3)
        G.add_edge(2, 3)

        pts = [
            (500, 500, "BD"),   # node 0
            (1500, 500, "AK"),  # node 1
            (500, 1500, "CT"),  # node 2
            (1500, 1500, "WL"), # node 3
        ]
        buildings = make_buildings(pts)
        props = make_properties(pts)
        result = attach_hdb_towns(G, gdf, buildings, props)

        for n in [0, 1, 2, 3]:
            assert result.nodes[n]["hdb_town"] is not None
            assert result.nodes[n]["hdb_town_purity"] == 1.0


# ---------------------------------------------------------------------------
# Slow integration test against real data
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_attach_hdb_towns_real_data() -> None:
    """Smoke test: most nodes get a non-None hdb_town on real processed data.

    Prints top-10 town code distribution and join rate.
    """
    from src.analysis.graph_build import build_subzone_graph
    from src.analysis.io_layer import (
        load_hdb_buildings,
        load_hdb_property_table,
        load_subzones_with_population,
    )

    layer = load_subzones_with_population()
    subzones = layer.svy21

    hdb_buildings = load_hdb_buildings()
    hdb_props = load_hdb_property_table()

    G = build_subzone_graph(subzones)

    result = attach_hdb_towns(G, subzones, hdb_buildings, hdb_props)

    # Collect stats
    towns = [
        result.nodes[n]["hdb_town"]
        for n in result.nodes
        if result.nodes[n]["hdb_town"] is not None
    ]
    none_count = sum(
        1 for n in result.nodes if result.nodes[n]["hdb_town"] is None
    )
    total = result.number_of_nodes()

    labeled_pct = len(towns) / total * 100
    print(f"\nTotal nodes: {total}")
    print(f"Labeled (non-None): {len(towns)} ({labeled_pct:.1f}%)")
    print(f"Unlabeled (None):   {none_count}")

    # Top-10 distribution
    from collections import Counter
    dist = Counter(towns).most_common(10)
    print("\nTop-10 town codes by subzone count:")
    for town, count in dist:
        print(f"  {town}: {count}")

    # Most nodes should be labeled (residential Singapore is largely HDB)
    assert labeled_pct >= 40.0, (
        f"Expected at least 40% of nodes to be labeled, got {labeled_pct:.1f}%"
    )
