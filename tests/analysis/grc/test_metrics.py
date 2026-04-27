"""Tests for src.analysis.grc.metrics."""
import networkx as nx

from src.analysis.grc.metrics import (
    compute_grc_metrics,
    minority_capture_by_type,
    seat_type_by_planning_area,
)


def _simple_graph() -> tuple[nx.Graph, dict[int, list[int]], dict[int, int]]:
    """4-node graph: 2 SMC districts (d0, d1), 1 four-seat GRC (d2)."""
    g = nx.path_graph(4)
    pops = [1000, 1000, 4000, 4000]
    pct_minority = [0.10, 0.20, 0.30, 0.40]
    for n in g.nodes:
        g.nodes[n]["pop_total"] = pops[n]
        g.nodes[n]["pct_minority"] = pct_minority[n]
        g.nodes[n]["pln_area"] = "A" if n < 2 else "B"
        g.nodes[n]["hdb_town"] = "TOWN_A"

    parts = {0: [0], 1: [1], 2: [2, 3]}
    seat_counts = {0: 1, 1: 1, 2: 4}
    return g, parts, seat_counts


class TestMinorityCaptureByType:
    def test_smc_mean(self):
        g, parts, seat_counts = _simple_graph()
        result = minority_capture_by_type(parts, g, seat_counts)
        # d0: 10%, d1: 20% → mean 15%
        assert abs(result["smc_mean_minority"] - 0.15) < 1e-6

    def test_grc4_mean(self):
        g, parts, seat_counts = _simple_graph()
        result = minority_capture_by_type(parts, g, seat_counts)
        # d2: nodes 2 (30%) and 3 (40%), pop 4000 each → mean (0.30+0.40)/2 = 35%
        assert abs(result["grc4_mean_minority"] - 0.35) < 1e-6

    def test_counts_present(self):
        g, parts, seat_counts = _simple_graph()
        result = minority_capture_by_type(parts, g, seat_counts)
        assert result["smc_n"] == 2.0
        assert result["grc4_n"] == 1.0


class TestSeatTypeByPlanningArea:
    def test_grc_fraction(self):
        g, parts, seat_counts = _simple_graph()
        result = seat_type_by_planning_area(parts, g, seat_counts)
        # Planning area A: 2000 pop total, 0 in GRC → frac 0.0
        # Planning area B: 8000 pop total, 8000 in GRC → frac 1.0
        # Weighted mean: (0*2000 + 1*8000) / 10000 = 0.8
        assert abs(result["pln_area_grc_pop_frac"] - 0.8) < 1e-6


class TestComputeGRCMetrics:
    def test_returns_expected_keys(self):
        g, parts, seat_counts = _simple_graph()
        result = compute_grc_metrics(parts, g, seat_counts)
        assert "smc_mean_minority" in result
        assert "grc4_mean_minority" in result
        assert "pln_area_grc_pop_frac" in result
