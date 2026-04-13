"""Tests for src/analysis/metrics/compactness.py.

TDD: tests written BEFORE implementation (RED phase).
All tests use in-memory synthetic geometries — no disk I/O.
"""
from __future__ import annotations

import math

import networkx as nx
import pytest
from shapely.geometry import Point, box
from shapely.ops import unary_union

from src.analysis.metrics.compactness import (
    compute_compactness_metrics,
    cut_edges,
    district_geometries,
    mean_polsby_popper,
    min_polsby_popper,
    polsby_popper,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def circle_polygon(radius: float = 100.0, n_pts: int = 512) -> object:
    """Return a high-resolution circular polygon via Shapely buffer."""
    return Point(0.0, 0.0).buffer(radius, resolution=n_pts)


# ---------------------------------------------------------------------------
# polsby_popper
# ---------------------------------------------------------------------------


class TestPolsbyPopper:
    def test_circle_close_to_one(self) -> None:
        """A high-resolution circle should have PP very close to 1.0."""
        geom = circle_polygon(radius=100.0, n_pts=512)
        pp = polsby_popper(geom)
        assert 0.99 <= pp <= 1.0, f"Expected PP ~1.0 for circle, got {pp}"

    def test_thin_rectangle(self) -> None:
        """1000×1 rectangle: area=1000, perimeter≈2002, PP≈0.00313."""
        geom = box(0, 0, 1000, 1)
        expected = (4 * math.pi * 1000) / (2002 ** 2)
        pp = polsby_popper(geom)
        assert abs(pp - expected) < 1e-4, f"Expected PP≈{expected:.5f}, got {pp:.5f}"

    def test_square(self) -> None:
        """100×100 square: area=10000, perimeter=400, PP=4π*10000/160000≈0.7854."""
        geom = box(0, 0, 100, 100)
        expected = (4 * math.pi * 10_000) / (400 ** 2)
        pp = polsby_popper(geom)
        assert abs(pp - expected) < 1e-6, f"Expected PP≈{expected:.6f}, got {pp:.6f}"

    def test_pp_in_range(self) -> None:
        """PP must always lie in [0, 1]."""
        geom = box(0, 0, 50, 10)
        pp = polsby_popper(geom)
        assert 0.0 <= pp <= 1.0

    def test_degenerate_zero_area(self) -> None:
        """A line/degenerate geometry with zero area returns 0.0 (no division by zero)."""
        # A 'box' with zero height is a line — area=0, perimeter>0
        geom = box(0, 0, 100, 0)  # degenerate line
        pp = polsby_popper(geom)
        assert pp == 0.0

    def test_degenerate_zero_perimeter(self) -> None:
        """A point-like geometry with zero perimeter returns 0.0."""
        geom = Point(0.0, 0.0)  # single point: area=0, length=0
        pp = polsby_popper(geom)
        assert pp == 0.0

    def test_return_type_is_float(self) -> None:
        geom = box(0, 0, 10, 10)
        assert isinstance(polsby_popper(geom), float)


# ---------------------------------------------------------------------------
# district_geometries
# ---------------------------------------------------------------------------


class TestDistrictGeometries:
    def test_single_district_single_node(self) -> None:
        """One district with one node returns that node's geometry."""
        geom = box(0, 0, 10, 10)
        parts = {0: [42]}
        subzone_geoms = {42: geom}
        result = district_geometries(parts, subzone_geoms)
        assert 0 in result
        assert abs(result[0].area - geom.area) < 1e-9

    def test_single_district_two_nodes_union(self) -> None:
        """Two adjacent boxes in one district → union covers combined area."""
        box_a = box(0, 0, 10, 10)   # area 100
        box_b = box(10, 0, 20, 10)  # area 100, adjacent
        parts = {0: [1, 2]}
        subzone_geoms = {1: box_a, 2: box_b}
        result = district_geometries(parts, subzone_geoms)
        assert 0 in result
        assert abs(result[0].area - 200.0) < 1e-9

    def test_two_districts(self) -> None:
        """Two districts each with one node → two separate geometries."""
        box_a = box(0, 0, 10, 10)
        box_b = box(20, 0, 30, 10)
        parts = {0: [1], 1: [2]}
        subzone_geoms = {1: box_a, 2: box_b}
        result = district_geometries(parts, subzone_geoms)
        assert set(result.keys()) == {0, 1}
        assert abs(result[0].area - 100.0) < 1e-9
        assert abs(result[1].area - 100.0) < 1e-9

    def test_returns_dict(self) -> None:
        geom = box(0, 0, 5, 5)
        parts = {0: [0]}
        subzone_geoms = {0: geom}
        result = district_geometries(parts, subzone_geoms)
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# mean_polsby_popper
# ---------------------------------------------------------------------------


class TestMeanPolsbyPopper:
    def test_two_squares_mean(self) -> None:
        """Two identical squares → mean PP equals PP of one square."""
        sq = box(0, 0, 100, 100)
        expected_pp = polsby_popper(sq)
        parts = {0: [0], 1: [1]}
        subzone_geoms = {0: box(0, 0, 100, 100), 1: box(200, 0, 300, 100)}
        result = mean_polsby_popper(parts, subzone_geoms)
        assert abs(result - expected_pp) < 1e-6

    def test_mixed_districts(self) -> None:
        """Mean of a square (PP≈0.785) and thin rect (PP≈0.003) ~= 0.394."""
        sq = box(0, 0, 100, 100)
        thin = box(0, 0, 1000, 1)
        pp_sq = polsby_popper(sq)
        pp_thin = polsby_popper(thin)
        expected_mean = (pp_sq + pp_thin) / 2.0
        parts = {0: [0], 1: [1]}
        subzone_geoms = {0: sq, 1: thin}
        result = mean_polsby_popper(parts, subzone_geoms)
        assert abs(result - expected_mean) < 1e-6

    def test_return_type(self) -> None:
        parts = {0: [0]}
        subzone_geoms = {0: box(0, 0, 10, 10)}
        assert isinstance(mean_polsby_popper(parts, subzone_geoms), float)


# ---------------------------------------------------------------------------
# min_polsby_popper
# ---------------------------------------------------------------------------


class TestMinPolsbyPopper:
    def test_returns_minimum(self) -> None:
        """Min PP should be the smaller of the two district PPs."""
        sq = box(0, 0, 100, 100)
        thin = box(0, 0, 1000, 1)
        pp_sq = polsby_popper(sq)
        pp_thin = polsby_popper(thin)
        parts = {0: [0], 1: [1]}
        subzone_geoms = {0: sq, 1: thin}
        result = min_polsby_popper(parts, subzone_geoms)
        assert abs(result - min(pp_sq, pp_thin)) < 1e-6

    def test_single_district(self) -> None:
        sq = box(0, 0, 100, 100)
        parts = {0: [0]}
        subzone_geoms = {0: sq}
        result = min_polsby_popper(parts, subzone_geoms)
        assert abs(result - polsby_popper(sq)) < 1e-6

    def test_return_type(self) -> None:
        parts = {0: [0]}
        subzone_geoms = {0: box(0, 0, 10, 10)}
        assert isinstance(min_polsby_popper(parts, subzone_geoms), float)


# ---------------------------------------------------------------------------
# cut_edges
# ---------------------------------------------------------------------------


class TestCutEdges:
    def test_two_nodes_same_district_zero_cuts(self) -> None:
        """Edge between two nodes in the same district → 0 cut edges."""
        G = nx.Graph()
        G.add_edge(0, 1)
        assignment = {0: 0, 1: 0}
        assert cut_edges(G, assignment) == 0

    def test_two_nodes_different_districts_one_cut(self) -> None:
        """Edge between two nodes in different districts → 1 cut edge."""
        G = nx.Graph()
        G.add_edge(0, 1)
        assignment = {0: 0, 1: 1}
        assert cut_edges(G, assignment) == 1

    def test_four_nodes_mixed_assignment(self) -> None:
        """
        Nodes 0,1 in district 0; nodes 2,3 in district 1.
        Graph: 0-1, 1-2, 2-3. Cut edges: only 1-2 crosses.
        """
        G = nx.Graph()
        G.add_edges_from([(0, 1), (1, 2), (2, 3)])
        assignment = {0: 0, 1: 0, 2: 1, 3: 1}
        assert cut_edges(G, assignment) == 1

    def test_star_graph_all_different(self) -> None:
        """
        Star graph: center=0 connected to 1,2,3.
        All nodes in different districts → all 3 edges are cut.
        """
        G = nx.Graph()
        G.add_edges_from([(0, 1), (0, 2), (0, 3)])
        assignment = {0: 0, 1: 1, 2: 2, 3: 3}
        assert cut_edges(G, assignment) == 3

    def test_no_edges_zero_cuts(self) -> None:
        """Edgeless graph → 0 cut edges regardless of assignment."""
        G = nx.Graph()
        G.add_nodes_from([0, 1, 2])
        assignment = {0: 0, 1: 1, 2: 2}
        assert cut_edges(G, assignment) == 0

    def test_return_type_is_int(self) -> None:
        G = nx.Graph()
        G.add_edge(0, 1)
        assignment = {0: 0, 1: 1}
        assert isinstance(cut_edges(G, assignment), int)


# ---------------------------------------------------------------------------
# compute_compactness_metrics
# ---------------------------------------------------------------------------


class TestComputeCompactnessMetrics:
    def _make_inputs(self):
        """Two squares, two districts, one shared edge between nodes."""
        sq_a = box(0, 0, 100, 100)
        sq_b = box(100, 0, 200, 100)
        parts = {0: [0], 1: [1]}
        subzone_geoms = {0: sq_a, 1: sq_b}
        G = nx.Graph()
        G.add_edge(0, 1)
        assignment = {0: 0, 1: 1}
        return parts, subzone_geoms, G, assignment

    def test_returns_dict_with_expected_keys(self) -> None:
        parts, geoms, G, asgn = self._make_inputs()
        result = compute_compactness_metrics(parts, geoms, G, asgn)
        assert isinstance(result, dict)
        assert "mean_pp" in result
        assert "min_pp" in result
        assert "cut_edges" in result

    def test_mean_pp_value(self) -> None:
        parts, geoms, G, asgn = self._make_inputs()
        result = compute_compactness_metrics(parts, geoms, G, asgn)
        sq = box(0, 0, 100, 100)
        expected_pp = polsby_popper(sq)
        assert abs(result["mean_pp"] - expected_pp) < 1e-6

    def test_min_pp_value(self) -> None:
        parts, geoms, G, asgn = self._make_inputs()
        result = compute_compactness_metrics(parts, geoms, G, asgn)
        sq = box(0, 0, 100, 100)
        expected_pp = polsby_popper(sq)
        assert abs(result["min_pp"] - expected_pp) < 1e-6

    def test_cut_edges_value(self) -> None:
        parts, geoms, G, asgn = self._make_inputs()
        result = compute_compactness_metrics(parts, geoms, G, asgn)
        # Nodes 0 and 1 are in different districts → 1 cut edge
        assert result["cut_edges"] == 1

    def test_cut_edges_same_district(self) -> None:
        """If both nodes share a district, cut_edges must be 0."""
        sq_a = box(0, 0, 100, 100)
        sq_b = box(100, 0, 200, 100)
        parts = {0: [0, 1]}
        subzone_geoms = {0: sq_a, 1: sq_b}
        G = nx.Graph()
        G.add_edge(0, 1)
        assignment = {0: 0, 1: 0}
        result = compute_compactness_metrics(parts, subzone_geoms, G, assignment)
        assert result["cut_edges"] == 0

    def test_value_types(self) -> None:
        parts, geoms, G, asgn = self._make_inputs()
        result = compute_compactness_metrics(parts, geoms, G, asgn)
        assert isinstance(result["mean_pp"], float)
        assert isinstance(result["min_pp"], float)
        assert isinstance(result["cut_edges"], int)
