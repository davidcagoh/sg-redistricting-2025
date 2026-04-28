"""Tests for src.analysis.grc.option_a."""
from __future__ import annotations

import numpy as np
import pandas as pd
import networkx as nx
import pytest

from src.analysis.grc.option_a import (
    ActualCapture,
    build_node_arrays,
    compute_actual_capture,
    compute_district_stats,
    compute_percentile_rank,
    run_null_distribution,
    N_GRC,
    N_SMC,
    N_DISTRICTS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_graph(n_nodes: int = 6) -> nx.Graph:
    """Simple path graph with pop_total and pct_minority on each node."""
    g = nx.path_graph(n_nodes)
    for i in g.nodes:
        g.nodes[i]["pop_total"] = 1000 * (i + 1)
        g.nodes[i]["pct_minority"] = 0.10 * (i + 1)  # 0.1, 0.2, ... 0.6
    return g


def _make_assignments(n_steps: int = 3, n_nodes: int = 6, n_districts: int = 3) -> pd.DataFrame:
    """Assignments DataFrame: n_steps steps, n_nodes nodes, n_districts districts."""
    rows = []
    for step in range(n_steps):
        for node in range(n_nodes):
            district = node % n_districts
            rows.append({"step_index": step, "node_id": node, "district_id": district})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# build_node_arrays
# ---------------------------------------------------------------------------


class TestBuildNodeArrays:
    def test_shape(self):
        g = _make_graph(4)
        pop, min_pop, max_id = build_node_arrays(g)
        assert max_id == 3
        assert len(pop) == 4
        assert len(min_pop) == 4

    def test_pop_values(self):
        g = _make_graph(3)
        pop, _, _ = build_node_arrays(g)
        assert pop[0] == 1000
        assert pop[1] == 2000
        assert pop[2] == 3000

    def test_minority_pop_values(self):
        g = _make_graph(3)
        _, min_pop, _ = build_node_arrays(g)
        # node 0: 1000 * 0.1 = 100
        assert abs(min_pop[0] - 100.0) < 1e-6
        # node 2: 3000 * 0.3 = 900
        assert abs(min_pop[2] - 900.0) < 1e-6

    def test_missing_pct_minority_defaults_zero(self):
        g = nx.path_graph(2)
        g.nodes[0]["pop_total"] = 1000
        g.nodes[1]["pop_total"] = 2000
        # no pct_minority attribute
        _, min_pop, _ = build_node_arrays(g)
        assert min_pop[0] == 0.0
        assert min_pop[1] == 0.0


# ---------------------------------------------------------------------------
# compute_district_stats
# ---------------------------------------------------------------------------


class TestComputeDistrictStats:
    def test_output_shape(self):
        g = _make_graph(6)
        pop, min_pop, _ = build_node_arrays(g)
        df = _make_assignments(n_steps=2, n_nodes=6, n_districts=3)
        stats = compute_district_stats(df, pop, min_pop)
        # 2 steps × 3 districts = 6 rows
        assert len(stats) == 6
        assert set(stats.columns) >= {"step_index", "district_id", "total_pop", "minority_pop"}

    def test_population_sums(self):
        g = _make_graph(6)
        pop, min_pop, _ = build_node_arrays(g)
        df = _make_assignments(n_steps=1, n_nodes=6, n_districts=3)
        stats = compute_district_stats(df, pop, min_pop)

        # district 0 has nodes 0, 3 → pops 1000, 4000 → total 5000
        d0 = stats[(stats["step_index"] == 0) & (stats["district_id"] == 0)].iloc[0]
        assert d0["total_pop"] == 5000.0

    def test_minority_pop_sums(self):
        g = _make_graph(6)
        pop, min_pop, _ = build_node_arrays(g)
        df = _make_assignments(n_steps=1, n_nodes=6, n_districts=3)
        stats = compute_district_stats(df, pop, min_pop)

        # district 0 nodes 0,3: min_pop = 100 + 1600 = 1700
        d0 = stats[(stats["step_index"] == 0) & (stats["district_id"] == 0)].iloc[0]
        assert abs(d0["minority_pop"] - 1700.0) < 1e-6


# ---------------------------------------------------------------------------
# run_null_distribution
# ---------------------------------------------------------------------------


class TestRunNullDistribution:
    def _make_stats(self, n_steps: int = 5, n_districts: int = 4) -> pd.DataFrame:
        """Create synthetic district_stats with deterministic values."""
        rows = []
        for s in range(n_steps):
            for d in range(n_districts):
                rows.append({
                    "step_index": s,
                    "district_id": d,
                    "total_pop": float(1000 * (d + 1)),
                    "minority_pop": float(100 * (d + 1)),
                })
        return pd.DataFrame(rows)

    def test_output_length(self):
        stats = self._make_stats(n_steps=5, n_districts=4)
        scores = run_null_distribution(stats, n_grc=2, n_districts=4, n_perms=10, seed=0)
        assert len(scores) == 50  # 5 steps × 10 perms

    def test_scores_in_valid_range(self):
        stats = self._make_stats(n_steps=3, n_districts=4)
        scores = run_null_distribution(stats, n_grc=2, n_districts=4, n_perms=20, seed=42)
        assert np.all(scores >= 0.0)
        assert np.all(scores <= 1.0)

    def test_deterministic_with_same_seed(self):
        stats = self._make_stats(n_steps=4, n_districts=4)
        s1 = run_null_distribution(stats, n_grc=2, n_districts=4, n_perms=10, seed=7)
        s2 = run_null_distribution(stats, n_grc=2, n_districts=4, n_perms=10, seed=7)
        np.testing.assert_array_equal(s1, s2)

    def test_different_seeds_differ(self):
        # Districts with distinct minority rates so permutations vary
        rows = []
        for s in range(4):
            for d in range(4):
                rows.append({
                    "step_index": s,
                    "district_id": d,
                    "total_pop": 1000.0,
                    "minority_pop": float(100 * (d + 1)),  # 10%, 20%, 30%, 40%
                })
        stats = pd.DataFrame(rows)
        s1 = run_null_distribution(stats, n_grc=2, n_districts=4, n_perms=10, seed=1)
        s2 = run_null_distribution(stats, n_grc=2, n_districts=4, n_perms=10, seed=2)
        assert not np.allclose(s1, s2)

    def test_uniform_pct_minority_constant_score(self):
        """If all districts have identical minority share, all permutations score the same."""
        rows = []
        for s in range(3):
            for d in range(6):
                rows.append({
                    "step_index": s,
                    "district_id": d,
                    "total_pop": 1000.0,
                    "minority_pop": 300.0,  # 30% everywhere
                })
        stats = pd.DataFrame(rows)
        scores = run_null_distribution(stats, n_grc=3, n_districts=6, n_perms=50, seed=0)
        np.testing.assert_allclose(scores, 0.3, rtol=1e-6)


# ---------------------------------------------------------------------------
# compute_actual_capture
# ---------------------------------------------------------------------------


class TestComputeActualCapture:
    def _setup(self):
        # 4 nodes: 0,1 → SMC; 2,3 → GRC
        g = nx.path_graph(4)
        pops = [1000, 2000, 3000, 4000]
        pct_mins = [0.10, 0.20, 0.30, 0.40]
        for n in g.nodes:
            g.nodes[n]["pop_total"] = pops[n]
            g.nodes[n]["pct_minority"] = pct_mins[n]
        pop, min_pop, _ = build_node_arrays(g)

        node_to_ed = {0: "HOUGANG", 1: "POTONG PASIR", 2: "ANG MO KIO", 3: "SENGKANG"}
        grc_names = {"ANG MO KIO", "SENGKANG"}
        return pop, min_pop, node_to_ed, grc_names

    def test_returns_actual_capture(self):
        pop, min_pop, n2e, grcs = self._setup()
        result = compute_actual_capture(n2e, pop, min_pop, grcs)
        assert isinstance(result, ActualCapture)

    def test_grc_minority_pct(self):
        pop, min_pop, n2e, grcs = self._setup()
        result = compute_actual_capture(n2e, pop, min_pop, grcs)
        # GRC nodes 2,3: minority_pop = 3000*0.30 + 4000*0.40 = 900 + 1600 = 2500
        # GRC total_pop = 7000
        expected_grc = 2500 / 7000
        assert abs(result.grc_minority_pct - expected_grc) < 1e-6

    def test_smc_minority_pct(self):
        pop, min_pop, n2e, grcs = self._setup()
        result = compute_actual_capture(n2e, pop, min_pop, grcs)
        # SMC nodes 0,1: minority_pop = 1000*0.10 + 2000*0.20 = 100 + 400 = 500
        # SMC total_pop = 3000
        expected_smc = 500 / 3000
        assert abs(result.smc_minority_pct - expected_smc) < 1e-6

    def test_node_counts(self):
        pop, min_pop, n2e, grcs = self._setup()
        result = compute_actual_capture(n2e, pop, min_pop, grcs)
        assert result.n_grc_nodes == 2
        assert result.n_smc_nodes == 2
        assert result.n_unmatched_nodes == 0

    def test_unmatched_nodes_excluded(self):
        pop, min_pop, n2e, grcs = self._setup()
        n2e_with_none = dict(n2e)
        n2e_with_none[0] = None  # node 0 unmatched
        result = compute_actual_capture(n2e_with_none, pop, min_pop, grcs)
        assert result.n_unmatched_nodes == 1
        assert result.n_smc_nodes == 1

    def test_case_insensitive_grc_lookup(self):
        pop, min_pop, n2e, _ = self._setup()
        # Lower-case in node_to_ed, upper-case in grc_names
        n2e_lower = {0: "hougang", 1: "potong pasir", 2: "ang mo kio", 3: "sengkang"}
        grcs_upper = {"ANG MO KIO", "SENGKANG"}
        result = compute_actual_capture(n2e_lower, pop, min_pop, grcs_upper)
        assert result.n_grc_nodes == 2


# ---------------------------------------------------------------------------
# compute_percentile_rank
# ---------------------------------------------------------------------------


class TestComputePercentileRank:
    def test_at_median(self):
        null = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        rank = compute_percentile_rank(3.0, null)
        assert abs(rank - 40.0) < 1e-6  # 2 out of 5 strictly below

    def test_below_all(self):
        null = np.array([2.0, 3.0, 4.0])
        rank = compute_percentile_rank(1.0, null)
        assert rank == 0.0

    def test_above_all(self):
        null = np.array([1.0, 2.0, 3.0])
        rank = compute_percentile_rank(5.0, null)
        assert rank == 100.0


# ---------------------------------------------------------------------------
# Module-level constants sanity
# ---------------------------------------------------------------------------


def test_sg2025_district_counts():
    assert N_GRC == 18
    assert N_SMC == 15
    assert N_DISTRICTS == N_GRC + N_SMC
