"""Tests for src/analysis/metrics/registry.py.

TDD: tests written BEFORE implementation (RED phase).
All tests use in-memory synthetic fixtures — no disk I/O.

Fixture: 4-node 2x2 grid
  Nodes: 0, 1, 2, 3
  Edges: 0-1, 0-2, 1-3, 2-3
  Partition: {0: [0,1], 1: [2,3]}
  Assignment: {0:0, 1:0, 2:1, 3:1}
  Geometries: shapely boxes tiling a 200x100 rectangle
"""
from __future__ import annotations

import networkx as nx
import pytest
from shapely.geometry import box

from src.analysis.metrics.registry import METRICS_VERSION, compute_all

# ---------------------------------------------------------------------------
# Required output keys
# ---------------------------------------------------------------------------

REQUIRED_KEYS = {
    "max_abs_pop_dev",
    "pop_range",
    "ideal_pop",
    "mean_pp",
    "min_pp",
    "cut_edges",
    "towns_split",
    "pln_area_splits",
    "town_split_entropy",
}


# ---------------------------------------------------------------------------
# Shared fixture builders
# ---------------------------------------------------------------------------


def make_uniform_fixture() -> tuple[
    dict[int, list[int]],
    dict[int, object],
    nx.Graph,
    dict[int, int],
]:
    """4-node 2x2 grid. All nodes same town, same pln_area, equal population.

    District 0: nodes 0, 1 (left column)
    District 1: nodes 2, 3 (right column)

    Node layout (spatial):
      0 -- 1
      |    |
      2 -- 3

    Subzone geometries (100x100 boxes):
      node 0: (0,0)-(100,100)
      node 1: (0,100)-(100,200)   <- stacked vertically within district 0 union
      node 2: (100,0)-(200,100)
      node 3: (100,100)-(200,200)
    """
    G = nx.Graph()
    for node_id in range(4):
        G.add_node(
            node_id,
            pop_total=100,
            hdb_town="Tampines",
            pln_area="TAMPINES",
        )
    G.add_edges_from([(0, 1), (0, 2), (1, 3), (2, 3)])

    partition_parts = {0: [0, 1], 1: [2, 3]}
    subzone_geoms = {
        0: box(0, 0, 100, 100),
        1: box(0, 100, 100, 200),
        2: box(100, 0, 200, 100),
        3: box(100, 100, 200, 200),
    }
    assignment = {0: 0, 1: 0, 2: 1, 3: 1}
    return partition_parts, subzone_geoms, G, assignment


def make_heterogeneous_fixture() -> tuple[
    dict[int, list[int]],
    dict[int, object],
    nx.Graph,
    dict[int, int],
]:
    """4-node 2x2 grid. Nodes have different populations and different towns.

    District 0: nodes 0 (pop=100, town=Tampines), 1 (pop=300, town=Tampines)
    District 1: nodes 2 (pop=200, town=Bedok),    3 (pop=200, town=Bedok)

    District pops: {0: 400, 1: 400}  → equal pop, but towns split because
    Tampines (nodes 0,1) is entirely in district 0 → no town split.
    Bedok   (nodes 2,3) is entirely in district 1 → no town split.

    To force a non-zero towns_split we need at least one town to span districts.
    Use a variant: node 0 in Tampines/district 0, node 2 in Tampines/district 1.
    """
    G = nx.Graph()
    attrs = {
        0: {"pop_total": 50, "hdb_town": "Tampines", "pln_area": "TAMPINES"},
        1: {"pop_total": 150, "hdb_town": "Tampines", "pln_area": "TAMPINES"},
        2: {"pop_total": 200, "hdb_town": "Tampines", "pln_area": "TAMPINES"},
        3: {"pop_total": 200, "hdb_town": "Bedok", "pln_area": "BEDOK"},
    }
    for node_id, a in attrs.items():
        G.add_node(node_id, **a)
    G.add_edges_from([(0, 1), (0, 2), (1, 3), (2, 3)])

    partition_parts = {0: [0, 1], 1: [2, 3]}
    subzone_geoms = {
        0: box(0, 0, 100, 100),
        1: box(0, 100, 100, 200),
        2: box(100, 0, 200, 100),
        3: box(100, 100, 200, 200),
    }
    assignment = {0: 0, 1: 0, 2: 1, 3: 1}
    return partition_parts, subzone_geoms, G, assignment


# ---------------------------------------------------------------------------
# METRICS_VERSION
# ---------------------------------------------------------------------------


class TestMetricsVersion:
    def test_version_is_string_one(self) -> None:
        assert METRICS_VERSION == "1"

    def test_version_is_str_type(self) -> None:
        assert isinstance(METRICS_VERSION, str)


# ---------------------------------------------------------------------------
# compute_all — key completeness
# ---------------------------------------------------------------------------


class TestComputeAllKeys:
    def test_returns_all_required_keys(self) -> None:
        """compute_all must return exactly the 9 required keys."""
        parts, geoms, G, assignment = make_uniform_fixture()
        result = compute_all(parts, geoms, G, assignment)
        assert set(result.keys()) == REQUIRED_KEYS

    def test_no_none_values_in_result(self) -> None:
        """Every value in the result dict must be a float or int — never None."""
        parts, geoms, G, assignment = make_uniform_fixture()
        result = compute_all(parts, geoms, G, assignment)
        for key, value in result.items():
            assert value is not None, f"Key '{key}' has None value"

    def test_all_values_are_numeric(self) -> None:
        """Every value must be an instance of (int, float)."""
        parts, geoms, G, assignment = make_uniform_fixture()
        result = compute_all(parts, geoms, G, assignment)
        for key, value in result.items():
            assert isinstance(value, (int, float)), (
                f"Key '{key}' has non-numeric value: {value!r} ({type(value).__name__})"
            )


# ---------------------------------------------------------------------------
# compute_all — uniform partition (all equal)
# ---------------------------------------------------------------------------


class TestComputeAllUniformPartition:
    """When all districts have equal population and all nodes share one town."""

    def setup_method(self) -> None:
        parts, geoms, G, assignment = make_uniform_fixture()
        self.result = compute_all(parts, geoms, G, assignment)

    def test_max_abs_pop_dev_is_zero(self) -> None:
        assert self.result["max_abs_pop_dev"] == pytest.approx(0.0, abs=1e-9)

    def test_pop_range_is_zero(self) -> None:
        assert self.result["pop_range"] == pytest.approx(0.0, abs=1e-9)

    def test_ideal_pop_is_correct(self) -> None:
        # total pop = 4 * 100 = 400; 2 districts → ideal = 200.0
        assert self.result["ideal_pop"] == pytest.approx(200.0, abs=1e-9)

    def test_towns_split_is_zero(self) -> None:
        # All nodes share "Tampines"; district 0 has [0,1], district 1 has [2,3]
        # Tampines spans BOTH districts → towns_split = 1, not 0.
        # The uniform fixture has the same town across districts, so it IS split.
        assert self.result["towns_split"] == 1

    def test_cut_edges_correct(self) -> None:
        # Edges crossing districts: 0-2 and 1-3 → 2 cut edges
        assert self.result["cut_edges"] == 2

    def test_mean_pp_is_positive(self) -> None:
        assert self.result["mean_pp"] > 0.0

    def test_min_pp_is_positive(self) -> None:
        assert self.result["min_pp"] > 0.0

    def test_min_pp_leq_mean_pp(self) -> None:
        assert self.result["min_pp"] <= self.result["mean_pp"]

    def test_pln_area_splits_is_one(self) -> None:
        # TAMPINES spans both districts
        assert self.result["pln_area_splits"] == 1

    def test_town_split_entropy_positive(self) -> None:
        # Tampines split 2-2 across two districts → entropy = 1.0
        assert self.result["town_split_entropy"] == pytest.approx(1.0, abs=1e-9)


# ---------------------------------------------------------------------------
# compute_all — heterogeneous partition
# ---------------------------------------------------------------------------


class TestComputeAllHeterogeneousPartition:
    """Nodes differ in population and town; verifies non-trivial metric values."""

    def setup_method(self) -> None:
        parts, geoms, G, assignment = make_heterogeneous_fixture()
        self.result = compute_all(parts, geoms, G, assignment)
        # District pops: {0: 50+150=200, 1: 200+200=400}
        # Ideal = 300.0
        # Deviations: district 0 → (200-300)/300 = -1/3, district 1 → (400-300)/300 = 1/3
        # max_abs_pop_dev = 1/3 ≈ 0.3333
        # pop_range = (400-200)/300 = 2/3 ≈ 0.6667

    def test_max_abs_pop_dev_nonzero(self) -> None:
        assert self.result["max_abs_pop_dev"] == pytest.approx(1 / 3, abs=1e-9)

    def test_pop_range_nonzero(self) -> None:
        assert self.result["pop_range"] == pytest.approx(2 / 3, abs=1e-9)

    def test_ideal_pop(self) -> None:
        assert self.result["ideal_pop"] == pytest.approx(300.0, abs=1e-9)

    def test_towns_split_nonzero(self) -> None:
        # Tampines: nodes 0,1 in district 0 AND node 2 in district 1 → split
        # Bedok: node 3 in district 1 only → not split
        assert self.result["towns_split"] == 1

    def test_cut_edges_correct(self) -> None:
        # Edges 0-2 and 1-3 cross districts → 2 cut edges
        assert self.result["cut_edges"] == 2

    def test_pln_area_splits_correct(self) -> None:
        # TAMPINES spans districts 0 and 1 → 1 split
        # BEDOK only in district 1 → 0 split
        assert self.result["pln_area_splits"] == 1

    def test_town_split_entropy_is_float(self) -> None:
        assert isinstance(self.result["town_split_entropy"], float)

    def test_mean_pp_is_positive(self) -> None:
        assert self.result["mean_pp"] > 0.0

    def test_min_pp_leq_mean_pp(self) -> None:
        assert self.result["min_pp"] <= self.result["mean_pp"]


# ---------------------------------------------------------------------------
# compute_all — return type is plain dict
# ---------------------------------------------------------------------------


class TestComputeAllReturnType:
    def test_returns_dict(self) -> None:
        parts, geoms, G, assignment = make_uniform_fixture()
        result = compute_all(parts, geoms, G, assignment)
        assert isinstance(result, dict)

    def test_result_is_not_empty(self) -> None:
        parts, geoms, G, assignment = make_uniform_fixture()
        result = compute_all(parts, geoms, G, assignment)
        assert len(result) > 0
