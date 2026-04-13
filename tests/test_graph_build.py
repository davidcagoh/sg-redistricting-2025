"""Tests for src/analysis/graph_build.py.

TDD: tests written before implementation. All tests here use in-memory
synthetic GeoDataFrames — no disk I/O for unit tests. The @pytest.mark.slow
test at the bottom exercises real processed data.
"""
from __future__ import annotations

import pandas as pd
import pytest
import geopandas as gpd
import networkx as nx
from shapely.geometry import box

from src.analysis.graph_build import build_subzone_graph, identify_islands, filter_for_mcmc


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def make_grid_gdf(
    rows: int,
    cols: int,
    cell_size: float = 1000.0,
    origin: tuple[float, float] = (100_000, 100_000),
) -> gpd.GeoDataFrame:
    """Create a rows×cols grid of squares as a GeoDataFrame in EPSG:3414.

    Node index is row-major: cell (r, c) → index r*cols + c.
    Layout for 2×2 (rows=2, cols=2):
        row 0: sq0=(0,0)-(1,1)  sq1=(1,0)-(2,1)   (bottom row)
        row 1: sq2=(0,1)-(1,2)  sq3=(1,1)-(2,2)   (top row)
    Rook adjacency edges: 0-1, 0-2, 1-3, 2-3 (NOT 0-3 diagonal, NOT 1-2 diagonal)
    """
    geoms, names, pops, pln, fids = [], [], [], [], []
    for r in range(rows):
        for c in range(cols):
            x0 = origin[0] + c * cell_size
            y0 = origin[1] + r * cell_size
            geoms.append(box(x0, y0, x0 + cell_size, y0 + cell_size))
            idx = r * cols + c
            names.append(f"SZ_{idx:02d}")
            pops.append(100 * (idx + 1))
            pln.append(f"PA_{r}")
            fids.append(idx)
    gdf = gpd.GeoDataFrame(
        {
            "subzone_name_norm": names,
            "PLN_AREA_N": pln,
            "pop_total": pops,
            "_feature_id": fids,
        },
        geometry=geoms,
        crs="EPSG:3414",
    )
    return gdf


@pytest.fixture
def grid_2x2() -> gpd.GeoDataFrame:
    return make_grid_gdf(2, 2)


@pytest.fixture
def grid_3x3() -> gpd.GeoDataFrame:
    return make_grid_gdf(3, 3)


@pytest.fixture
def grid_with_island() -> gpd.GeoDataFrame:
    """3×3 grid plus one isolated square far away (pop=0)."""
    main = make_grid_gdf(3, 3)
    island = gpd.GeoDataFrame(
        {
            "subzone_name_norm": ["ISLAND"],
            "PLN_AREA_N": ["OFFSHORE"],
            "pop_total": [0],
            "_feature_id": [99],
        },
        geometry=[box(500_000, 500_000, 501_000, 501_000)],
        crs="EPSG:3414",
    )
    combined = gpd.GeoDataFrame(
        pd.concat([main, island], ignore_index=True),
        crs="EPSG:3414",
    )
    return combined


# ---------------------------------------------------------------------------
# TestBuildSubzoneGraph
# ---------------------------------------------------------------------------


class TestBuildSubzoneGraph:
    def test_2x2_node_count(self, grid_2x2: gpd.GeoDataFrame) -> None:
        G = build_subzone_graph(grid_2x2)
        assert G.number_of_nodes() == 4

    def test_2x2_edge_count(self, grid_2x2: gpd.GeoDataFrame) -> None:
        # Rook adjacency: 4 shared edges in a 2×2 grid
        G = build_subzone_graph(grid_2x2)
        assert G.number_of_edges() == 4

    def test_2x2_no_diagonal_edges(self, grid_2x2: gpd.GeoDataFrame) -> None:
        G = build_subzone_graph(grid_2x2)
        # Nodes 0 and 3 are diagonal — must NOT be adjacent
        assert not G.has_edge(0, 3)
        # Nodes 1 and 2 are diagonal — must NOT be adjacent
        assert not G.has_edge(1, 2)

    def test_2x2_expected_edges_present(self, grid_2x2: gpd.GeoDataFrame) -> None:
        G = build_subzone_graph(grid_2x2)
        # In row-major 2×2: 0-1 (same row), 2-3 (same row), 0-2 (same col), 1-3 (same col)
        for u, v in [(0, 1), (2, 3), (0, 2), (1, 3)]:
            assert G.has_edge(u, v), f"Expected edge ({u},{v}) missing"

    def test_3x3_centre_node_degree_4(self, grid_3x3: gpd.GeoDataFrame) -> None:
        G = build_subzone_graph(grid_3x3)
        # Centre node index 4 in row-major 3×3
        assert G.degree(4) == 4

    def test_3x3_corner_node_degree_2(self, grid_3x3: gpd.GeoDataFrame) -> None:
        G = build_subzone_graph(grid_3x3)
        for corner in [0, 2, 6, 8]:
            assert G.degree(corner) == 2, f"Corner {corner} has wrong degree"

    def test_3x3_edge_node_degree_3(self, grid_3x3: gpd.GeoDataFrame) -> None:
        G = build_subzone_graph(grid_3x3)
        # Edge (non-corner) nodes: 1, 3, 5, 7
        for edge_node in [1, 3, 5, 7]:
            assert G.degree(edge_node) == 3, f"Edge node {edge_node} has wrong degree"

    def test_3x3_total_edges(self, grid_3x3: gpd.GeoDataFrame) -> None:
        # 3×3 grid has 12 rook-adjacency edges (3 rows × 2 + 2 cols × 3 = 12)
        G = build_subzone_graph(grid_3x3)
        assert G.number_of_edges() == 12

    def test_node_attrs_populated(self, grid_2x2: gpd.GeoDataFrame) -> None:
        G = build_subzone_graph(grid_2x2)
        for _node, data in G.nodes(data=True):
            assert "subzone_name_norm" in data
            assert "pop_total" in data
            assert "pln_area" in data
            assert "area_m2" in data
            assert "_feature_id" in data
            assert data["pop_total"] >= 0
            assert data["area_m2"] > 0

    def test_node_attrs_values_correct(self, grid_2x2: gpd.GeoDataFrame) -> None:
        G = build_subzone_graph(grid_2x2)
        # Node 0: subzone_name_norm="SZ_00", pop_total=100, area_m2=1_000_000 (1km²)
        n0 = G.nodes[0]
        assert n0["subzone_name_norm"] == "SZ_00"
        assert n0["pop_total"] == 100
        assert abs(n0["area_m2"] - 1_000_000.0) < 1.0  # 1 km² cell
        assert n0["_feature_id"] == 0

    def test_edge_shared_perimeter_positive(self, grid_2x2: gpd.GeoDataFrame) -> None:
        G = build_subzone_graph(grid_2x2)
        for _u, _v, data in G.edges(data=True):
            assert "shared_perimeter_m" in data
            assert data["shared_perimeter_m"] > 0

    def test_edge_shared_perimeter_correct(self, grid_2x2: gpd.GeoDataFrame) -> None:
        G = build_subzone_graph(grid_2x2)
        # In a 2×2 grid with cell_size=1000, every shared edge is exactly 1000 m
        for _u, _v, data in G.edges(data=True):
            assert abs(data["shared_perimeter_m"] - 1000.0) < 1.0, (
                f"Expected shared_perimeter_m ≈ 1000, got {data['shared_perimeter_m']}"
            )

    def test_node_ids_match_gdf_index(self, grid_2x2: gpd.GeoDataFrame) -> None:
        G = build_subzone_graph(grid_2x2)
        assert set(G.nodes()) == set(grid_2x2.index)

    def test_returns_networkx_graph(self, grid_2x2: gpd.GeoDataFrame) -> None:
        G = build_subzone_graph(grid_2x2)
        assert isinstance(G, nx.Graph)

    def test_tolerance_excludes_point_touches(self) -> None:
        # Two squares that only share a single corner point (no shared edge)
        # should NOT be adjacent under default tolerance
        sq_a = box(0, 0, 1000, 1000)
        sq_b = box(1000, 1000, 2000, 2000)  # touches only at corner (1000,1000)
        gdf = gpd.GeoDataFrame(
            {
                "subzone_name_norm": ["A", "B"],
                "PLN_AREA_N": ["PA", "PA"],
                "pop_total": [100, 200],
                "_feature_id": [0, 1],
            },
            geometry=[sq_a, sq_b],
            crs="EPSG:3414",
        )
        G = build_subzone_graph(gdf, tolerance_m=1.0)
        assert G.number_of_edges() == 0

    def test_custom_tolerance(self, grid_2x2: gpd.GeoDataFrame) -> None:
        # With a very large tolerance (> 1000 m), shared 1000 m edges should
        # still be included. With tolerance > 1001 m they should be excluded.
        G_normal = build_subzone_graph(grid_2x2, tolerance_m=999.0)
        G_too_strict = build_subzone_graph(grid_2x2, tolerance_m=1001.0)
        assert G_normal.number_of_edges() == 4
        assert G_too_strict.number_of_edges() == 0

    def test_projected_crs(self, grid_2x2: gpd.GeoDataFrame) -> None:
        # Input must be in EPSG:3414; verify fixture is correct
        assert grid_2x2.crs.to_epsg() == 3414

    def test_fid_column_fallback(self) -> None:
        # If GeoDataFrame has 'FID' instead of '_feature_id', still works
        gdf = make_grid_gdf(2, 2)
        gdf = gdf.rename(columns={"_feature_id": "FID"})
        G = build_subzone_graph(gdf)
        for _node, data in G.nodes(data=True):
            assert "_feature_id" in data  # stored under canonical name

    def test_graph_is_undirected(self, grid_2x2: gpd.GeoDataFrame) -> None:
        G = build_subzone_graph(grid_2x2)
        assert not G.is_directed()

    def test_single_node_no_edges(self) -> None:
        gdf = make_grid_gdf(1, 1)
        G = build_subzone_graph(gdf)
        assert G.number_of_nodes() == 1
        assert G.number_of_edges() == 0

    def test_input_gdf_not_mutated(self, grid_2x2: gpd.GeoDataFrame) -> None:
        cols_before = list(grid_2x2.columns)
        _ = build_subzone_graph(grid_2x2)
        assert list(grid_2x2.columns) == cols_before


# ---------------------------------------------------------------------------
# TestIdentifyIslands
# ---------------------------------------------------------------------------


class TestIdentifyIslands:
    def test_connected_graph_returns_empty(self, grid_3x3: gpd.GeoDataFrame) -> None:
        G = build_subzone_graph(grid_3x3)
        islands = identify_islands(G)
        assert islands == []

    def test_isolated_node_is_island(self, grid_3x3: gpd.GeoDataFrame) -> None:
        G = build_subzone_graph(grid_3x3)
        G.add_node(
            99,
            subzone_name_norm="ISLAND",
            pop_total=0,
            pln_area="X",
            area_m2=1e6,
            _feature_id=99,
        )
        islands = identify_islands(G)
        assert any(99 in comp for comp in islands)

    def test_mainland_not_in_islands(self, grid_3x3: gpd.GeoDataFrame) -> None:
        G = build_subzone_graph(grid_3x3)
        G.add_node(
            99,
            subzone_name_norm="ISLAND",
            pop_total=0,
            pln_area="X",
            area_m2=1e6,
            _feature_id=99,
        )
        islands = identify_islands(G)
        mainland_nodes = set(range(9))
        for comp in islands:
            assert not any(n in mainland_nodes for n in comp)

    def test_two_islands_returned(self, grid_3x3: gpd.GeoDataFrame) -> None:
        G = build_subzone_graph(grid_3x3)
        G.add_node(
            99,
            subzone_name_norm="ISLAND_A",
            pop_total=0,
            pln_area="X",
            area_m2=1e6,
            _feature_id=99,
        )
        G.add_node(
            100,
            subzone_name_norm="ISLAND_B",
            pop_total=0,
            pln_area="Y",
            area_m2=1e6,
            _feature_id=100,
        )
        islands = identify_islands(G)
        # Both isolated nodes should appear in separate components
        assert len(islands) == 2

    def test_returns_list_of_lists(self, grid_3x3: gpd.GeoDataFrame) -> None:
        G = build_subzone_graph(grid_3x3)
        G.add_node(
            99,
            subzone_name_norm="ISLAND",
            pop_total=0,
            pln_area="X",
            area_m2=1e6,
            _feature_id=99,
        )
        islands = identify_islands(G)
        assert isinstance(islands, list)
        for comp in islands:
            assert isinstance(comp, list)

    def test_single_node_graph_has_no_mainland_vs_island(self) -> None:
        G = nx.Graph()
        G.add_node(0, subzone_name_norm="ONLY", pop_total=100, pln_area="X", area_m2=1e6, _feature_id=0)
        # Single component: that IS the mainland, so no islands
        islands = identify_islands(G)
        assert islands == []


# ---------------------------------------------------------------------------
# TestFilterForMcmc
# ---------------------------------------------------------------------------


class TestFilterForMcmc:
    def test_removes_zero_pop_islands(self, grid_3x3: gpd.GeoDataFrame) -> None:
        G = build_subzone_graph(grid_3x3)
        G.add_node(
            99,
            subzone_name_norm="ISLAND",
            pop_total=0,
            pln_area="X",
            area_m2=1e6,
            _feature_id=99,
        )
        filtered, excluded = filter_for_mcmc(G)
        assert 99 in excluded
        assert 99 not in filtered.nodes

    def test_keeps_populated_islands(self, grid_3x3: gpd.GeoDataFrame) -> None:
        G = build_subzone_graph(grid_3x3)
        G.add_node(
            99,
            subzone_name_norm="POP_ISLAND",
            pop_total=500,
            pln_area="X",
            area_m2=1e6,
            _feature_id=99,
        )
        filtered, excluded = filter_for_mcmc(G)
        assert 99 not in excluded
        assert 99 in filtered.nodes

    def test_input_graph_not_mutated(self, grid_3x3: gpd.GeoDataFrame) -> None:
        G = build_subzone_graph(grid_3x3)
        G.add_node(
            99,
            subzone_name_norm="ISLAND",
            pop_total=0,
            pln_area="X",
            area_m2=1e6,
            _feature_id=99,
        )
        n_before = G.number_of_nodes()
        filter_for_mcmc(G)
        assert G.number_of_nodes() == n_before  # input unchanged

    def test_no_isolated_components_in_result(self, grid_3x3: gpd.GeoDataFrame) -> None:
        G = build_subzone_graph(grid_3x3)
        G.add_node(
            99,
            subzone_name_norm="ISLAND",
            pop_total=0,
            pln_area="X",
            area_m2=1e6,
            _feature_id=99,
        )
        filtered, _ = filter_for_mcmc(G)
        components = list(nx.connected_components(filtered))
        assert len(components) == 1

    def test_returns_tuple_graph_and_list(self, grid_3x3: gpd.GeoDataFrame) -> None:
        G = build_subzone_graph(grid_3x3)
        result = filter_for_mcmc(G)
        assert isinstance(result, tuple)
        assert len(result) == 2
        filtered, excluded = result
        assert isinstance(filtered, nx.Graph)
        assert isinstance(excluded, list)

    def test_fully_connected_graph_returns_empty_excluded(self, grid_3x3: gpd.GeoDataFrame) -> None:
        G = build_subzone_graph(grid_3x3)
        filtered, excluded = filter_for_mcmc(G)
        assert excluded == []
        assert filtered.number_of_nodes() == G.number_of_nodes()

    def test_custom_min_pop_threshold(self, grid_3x3: gpd.GeoDataFrame) -> None:
        G = build_subzone_graph(grid_3x3)
        # Island with pop=50 — below min_pop=100 → should be excluded
        G.add_node(
            99,
            subzone_name_norm="SMALL_ISLAND",
            pop_total=50,
            pln_area="X",
            area_m2=1e6,
            _feature_id=99,
        )
        _, excluded_default = filter_for_mcmc(G, min_pop=1)
        # With min_pop=1, pop=50 island is kept (50 >= 1)
        assert 99 not in excluded_default

        _, excluded_100 = filter_for_mcmc(G, min_pop=100)
        # With min_pop=100, pop=50 island is excluded (50 < 100)
        assert 99 in excluded_100

    def test_filtered_graph_preserves_mainland_edges(self, grid_3x3: gpd.GeoDataFrame) -> None:
        G = build_subzone_graph(grid_3x3)
        G.add_node(
            99,
            subzone_name_norm="ISLAND",
            pop_total=0,
            pln_area="X",
            area_m2=1e6,
            _feature_id=99,
        )
        original_edges = G.number_of_edges()
        filtered, _ = filter_for_mcmc(G)
        # No mainland edges should be lost
        assert filtered.number_of_edges() == original_edges

    def test_filtered_graph_is_new_object(self, grid_3x3: gpd.GeoDataFrame) -> None:
        G = build_subzone_graph(grid_3x3)
        filtered, _ = filter_for_mcmc(G)
        assert filtered is not G


# ---------------------------------------------------------------------------
# Slow / integration tests — require processed data files
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_real_subzone_graph_smoke() -> None:
    """Smoke test on real Singapore subzone data."""
    from src.analysis.io_layer import load_subzones_with_population

    layer = load_subzones_with_population()
    G = build_subzone_graph(layer.svy21)

    # Singapore has ~320 subzones in the URA Master Plan
    assert 280 <= G.number_of_nodes() <= 350, (
        f"Unexpected node count: {G.number_of_nodes()}"
    )

    # Mainland should encompass the vast majority of subzones
    largest = max(nx.connected_components(G), key=len)
    assert len(largest) >= 250, (
        f"Largest component only has {len(largest)} nodes"
    )

    filtered, excluded = filter_for_mcmc(G)

    # After filtering, should be well-connected (at most a handful of components)
    n_components = len(list(nx.connected_components(filtered)))
    assert n_components <= 5, (
        f"Too many components after filtering: {n_components}"
    )

    # Report excluded islands for the task report
    excluded_names = [G.nodes[n].get("subzone_name_norm", str(n)) for n in excluded]
    print(f"\nReal data: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    print(f"Excluded island subzones ({len(excluded)}): {excluded_names}")
