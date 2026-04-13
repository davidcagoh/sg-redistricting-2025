"""Tests for src/analysis/metrics/splitting.py.

TDD: tests written BEFORE implementation (RED phase).
All tests use in-memory synthetic graphs — no disk I/O.
"""
from __future__ import annotations

import math

import networkx as nx
import pytest

from src.analysis.metrics.splitting import (
    pln_area_splits,
    town_split_entropy,
    towns_split,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_graph(node_attrs: dict[int, dict]) -> nx.Graph:
    """Build a graph from a dict of {node_id: attr_dict}."""
    G = nx.Graph()
    for node_id, attrs in node_attrs.items():
        G.add_node(node_id, **attrs)
    return G


# ---------------------------------------------------------------------------
# towns_split
# ---------------------------------------------------------------------------


class TestTownsSplit:
    def test_all_same_town_one_district_no_splits(self) -> None:
        """2 nodes, same town, same district → 0 splits."""
        G = make_graph({
            0: {"hdb_town": "Tampines", "pln_area": "TAMPINES"},
            1: {"hdb_town": "Tampines", "pln_area": "TAMPINES"},
        })
        parts = {0: [0, 1]}
        assert towns_split(parts, G) == 0

    def test_all_same_town_two_districts_one_split(self) -> None:
        """1 town split across 2 districts → 1 split."""
        G = make_graph({
            0: {"hdb_town": "Tampines", "pln_area": "TAMPINES"},
            1: {"hdb_town": "Tampines", "pln_area": "TAMPINES"},
        })
        parts = {0: [0], 1: [1]}
        assert towns_split(parts, G) == 1

    def test_two_towns_each_confined_to_one_district(self) -> None:
        """2 towns each fully inside their own district → 0 splits."""
        G = make_graph({
            0: {"hdb_town": "Tampines", "pln_area": "TAMPINES"},
            1: {"hdb_town": "Bedok", "pln_area": "BEDOK"},
        })
        parts = {0: [0], 1: [1]}
        assert towns_split(parts, G) == 0

    def test_two_towns_each_split_across_two_districts(self) -> None:
        """2 towns, each split across 2 districts → 2 splits."""
        G = make_graph({
            0: {"hdb_town": "Tampines", "pln_area": "TAMPINES"},
            1: {"hdb_town": "Tampines", "pln_area": "TAMPINES"},
            2: {"hdb_town": "Bedok", "pln_area": "BEDOK"},
            3: {"hdb_town": "Bedok", "pln_area": "BEDOK"},
        })
        # District 0 gets node 0 (Tampines) and node 2 (Bedok)
        # District 1 gets node 1 (Tampines) and node 3 (Bedok)
        parts = {0: [0, 2], 1: [1, 3]}
        assert towns_split(parts, G) == 2

    def test_all_none_towns_returns_zero(self) -> None:
        """All hdb_town=None → exclude all, return 0."""
        G = make_graph({
            0: {"hdb_town": None, "pln_area": "TAMPINES"},
            1: {"hdb_town": None, "pln_area": "TAMPINES"},
        })
        parts = {0: [0], 1: [1]}
        assert towns_split(parts, G) == 0

    def test_mixed_none_and_real_town_split(self) -> None:
        """None-town nodes are excluded; only real-town nodes counted."""
        G = make_graph({
            0: {"hdb_town": "Tampines", "pln_area": "TAMPINES"},
            1: {"hdb_town": "Tampines", "pln_area": "TAMPINES"},
            2: {"hdb_town": None, "pln_area": "CENTRAL"},
        })
        # Node 0 (Tampines) in district 0, node 1 (Tampines) in district 1
        # Node 2 (None) ignored
        parts = {0: [0, 2], 1: [1]}
        assert towns_split(parts, G) == 1

    def test_three_districts_one_town_in_two_of_them(self) -> None:
        """1 town spread across 2 of 3 districts → 1 split."""
        G = make_graph({
            0: {"hdb_town": "Woodlands", "pln_area": "WOODLANDS"},
            1: {"hdb_town": "Woodlands", "pln_area": "WOODLANDS"},
            2: {"hdb_town": "Yishun", "pln_area": "YISHUN"},
        })
        # Town Woodlands spans districts 0 and 1
        # Town Yishun is fully in district 2
        parts = {0: [0], 1: [1], 2: [2]}
        assert towns_split(parts, G) == 1

    def test_return_type_is_int(self) -> None:
        G = make_graph({0: {"hdb_town": "Tampines", "pln_area": "TAMPINES"}})
        parts = {0: [0]}
        assert isinstance(towns_split(parts, G), int)

    def test_single_district_all_towns_confined(self) -> None:
        """With a single district, no town can be split → 0."""
        G = make_graph({
            0: {"hdb_town": "Jurong", "pln_area": "JURONG WEST"},
            1: {"hdb_town": "Tampines", "pln_area": "TAMPINES"},
        })
        parts = {0: [0, 1]}
        assert towns_split(parts, G) == 0

    def test_empty_partition_returns_zero(self) -> None:
        """Empty partition dict → 0 splits."""
        G = make_graph({0: {"hdb_town": "Tampines", "pln_area": "TAMPINES"}})
        parts: dict[int, list[int]] = {}
        assert towns_split(parts, G) == 0


# ---------------------------------------------------------------------------
# town_split_entropy
# ---------------------------------------------------------------------------


class TestTownSplitEntropy:
    def test_one_town_fully_in_one_district_entropy_zero(self) -> None:
        """All nodes of one town in same district → entropy 0.0."""
        G = make_graph({
            0: {"hdb_town": "Tampines", "pln_area": "TAMPINES"},
            1: {"hdb_town": "Tampines", "pln_area": "TAMPINES"},
        })
        parts = {0: [0, 1]}
        result = town_split_entropy(parts, G)
        assert result == pytest.approx(0.0, abs=1e-9)

    def test_one_town_split_fifty_fifty_entropy_one(self) -> None:
        """One town split 50/50 across 2 districts → entropy = 1.0."""
        G = make_graph({
            0: {"hdb_town": "Tampines", "pln_area": "TAMPINES"},
            1: {"hdb_town": "Tampines", "pln_area": "TAMPINES"},
        })
        parts = {0: [0], 1: [1]}
        result = town_split_entropy(parts, G)
        # entropy = -(0.5 * log2(0.5) + 0.5 * log2(0.5)) = 1.0
        assert result == pytest.approx(1.0, abs=1e-9)

    def test_one_town_split_one_third_two_thirds(self) -> None:
        """Town split 1/3 vs 2/3 → entropy = -(1/3*log2(1/3)+2/3*log2(2/3))."""
        G = make_graph({
            0: {"hdb_town": "Bedok", "pln_area": "BEDOK"},
            1: {"hdb_town": "Bedok", "pln_area": "BEDOK"},
            2: {"hdb_town": "Bedok", "pln_area": "BEDOK"},
        })
        # District 0: node 0 (1/3), District 1: nodes 1,2 (2/3)
        parts = {0: [0], 1: [1, 2]}
        p1, p2 = 1 / 3, 2 / 3
        expected = -(p1 * math.log2(p1) + p2 * math.log2(p2))
        result = town_split_entropy(parts, G)
        assert result == pytest.approx(expected, abs=1e-9)

    def test_none_town_nodes_excluded(self) -> None:
        """None-town nodes are excluded; result based only on real towns."""
        G = make_graph({
            0: {"hdb_town": "Tampines", "pln_area": "TAMPINES"},
            1: {"hdb_town": "Tampines", "pln_area": "TAMPINES"},
            2: {"hdb_town": None, "pln_area": "CENTRAL"},
            3: {"hdb_town": None, "pln_area": "CENTRAL"},
        })
        # Tampines perfectly confined in district 0; None nodes in district 1
        parts = {0: [0, 1], 1: [2, 3]}
        # Only Tampines matters → entropy = 0.0
        result = town_split_entropy(parts, G)
        assert result == pytest.approx(0.0, abs=1e-9)

    def test_no_towns_present_returns_zero(self) -> None:
        """If all hdb_town values are None → return 0.0."""
        G = make_graph({
            0: {"hdb_town": None, "pln_area": "CENTRAL"},
            1: {"hdb_town": None, "pln_area": "CENTRAL"},
        })
        parts = {0: [0], 1: [1]}
        result = town_split_entropy(parts, G)
        assert result == pytest.approx(0.0, abs=1e-9)

    def test_two_towns_mean_entropy(self) -> None:
        """Two towns: one confined (entropy 0), one split 50/50 (entropy 1) → mean 0.5."""
        G = make_graph({
            0: {"hdb_town": "Tampines", "pln_area": "TAMPINES"},
            1: {"hdb_town": "Tampines", "pln_area": "TAMPINES"},
            2: {"hdb_town": "Bedok", "pln_area": "BEDOK"},
            3: {"hdb_town": "Bedok", "pln_area": "BEDOK"},
        })
        # Tampines: both nodes in district 0 → entropy 0.0
        # Bedok: one node per district → entropy 1.0
        parts = {0: [0, 1, 2], 1: [3]}
        # Tampines: fully in district 0 → 0.0
        # Bedok: node 2 in district 0 (1/2), node 3 in district 1 (1/2) → entropy 1.0
        result = town_split_entropy(parts, G)
        assert result == pytest.approx(0.5, abs=1e-9)

    def test_return_type_is_float(self) -> None:
        G = make_graph({0: {"hdb_town": "Tampines", "pln_area": "TAMPINES"}})
        parts = {0: [0]}
        assert isinstance(town_split_entropy(parts, G), float)

    def test_single_node_single_district_entropy_zero(self) -> None:
        """One node, one district, one town → p=1.0, entropy = 0.0."""
        G = make_graph({0: {"hdb_town": "Jurong", "pln_area": "JURONG WEST"}})
        parts = {0: [0]}
        result = town_split_entropy(parts, G)
        assert result == pytest.approx(0.0, abs=1e-9)

    def test_empty_partition_returns_zero(self) -> None:
        """Empty partition → 0.0 (no towns to compute over)."""
        G = make_graph({0: {"hdb_town": "Tampines", "pln_area": "TAMPINES"}})
        parts: dict[int, list[int]] = {}
        result = town_split_entropy(parts, G)
        assert result == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# pln_area_splits
# ---------------------------------------------------------------------------


class TestPlnAreaSplits:
    def test_one_pln_area_one_district_no_splits(self) -> None:
        """All nodes in same pln_area in one district → 0 splits."""
        G = make_graph({
            0: {"hdb_town": None, "pln_area": "TAMPINES"},
            1: {"hdb_town": None, "pln_area": "TAMPINES"},
        })
        parts = {0: [0, 1]}
        assert pln_area_splits(parts, G) == 0

    def test_one_pln_area_split_across_two_districts(self) -> None:
        """1 planning area split across 2 districts → 1 split."""
        G = make_graph({
            0: {"hdb_town": None, "pln_area": "TAMPINES"},
            1: {"hdb_town": None, "pln_area": "TAMPINES"},
        })
        parts = {0: [0], 1: [1]}
        assert pln_area_splits(parts, G) == 1

    def test_two_pln_areas_each_confined(self) -> None:
        """2 planning areas each in their own district → 0 splits."""
        G = make_graph({
            0: {"hdb_town": None, "pln_area": "TAMPINES"},
            1: {"hdb_town": None, "pln_area": "BEDOK"},
        })
        parts = {0: [0], 1: [1]}
        assert pln_area_splits(parts, G) == 0

    def test_two_pln_areas_both_split(self) -> None:
        """2 planning areas each split across 2 districts → 2 splits."""
        G = make_graph({
            0: {"hdb_town": None, "pln_area": "TAMPINES"},
            1: {"hdb_town": None, "pln_area": "TAMPINES"},
            2: {"hdb_town": None, "pln_area": "BEDOK"},
            3: {"hdb_town": None, "pln_area": "BEDOK"},
        })
        parts = {0: [0, 2], 1: [1, 3]}
        assert pln_area_splits(parts, G) == 2

    def test_three_districts_one_pln_area_in_two(self) -> None:
        """1 pln_area spans 2 of 3 districts → 1 split."""
        G = make_graph({
            0: {"hdb_town": None, "pln_area": "WOODLANDS"},
            1: {"hdb_town": None, "pln_area": "WOODLANDS"},
            2: {"hdb_town": None, "pln_area": "YISHUN"},
        })
        parts = {0: [0], 1: [1], 2: [2]}
        assert pln_area_splits(parts, G) == 1

    def test_three_pln_areas_one_split(self) -> None:
        """3 planning areas, only 1 is split → 1 split."""
        G = make_graph({
            0: {"hdb_town": None, "pln_area": "TAMPINES"},
            1: {"hdb_town": None, "pln_area": "TAMPINES"},
            2: {"hdb_town": None, "pln_area": "BEDOK"},
            3: {"hdb_town": None, "pln_area": "JURONG WEST"},
        })
        # Tampines split across districts 0 and 1
        # Bedok confined to district 0
        # Jurong West confined to district 1
        parts = {0: [0, 2], 1: [1, 3]}
        assert pln_area_splits(parts, G) == 1

    def test_single_node_single_district_no_split(self) -> None:
        """Single node → pln_area in exactly one district → 0 splits."""
        G = make_graph({0: {"hdb_town": None, "pln_area": "CENTRAL"}})
        parts = {0: [0]}
        assert pln_area_splits(parts, G) == 0

    def test_return_type_is_int(self) -> None:
        G = make_graph({0: {"hdb_town": None, "pln_area": "TAMPINES"}})
        parts = {0: [0]}
        assert isinstance(pln_area_splits(parts, G), int)

    def test_empty_partition_returns_zero(self) -> None:
        """Empty partition → 0 splits."""
        G = make_graph({0: {"hdb_town": None, "pln_area": "TAMPINES"}})
        parts: dict[int, list[int]] = {}
        assert pln_area_splits(parts, G) == 0
