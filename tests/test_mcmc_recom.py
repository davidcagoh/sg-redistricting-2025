"""Tests for src/analysis/mcmc/recom.py — written FIRST (TDD RED phase).

Synthetic graph: 6 nodes arranged in a 2x3 grid, each with pop_total.
Two districts: nodes 0,1,2 → district 0; nodes 3,4,5 → district 1.

     0 — 1 — 2
     |   |   |
     3 — 4 — 5
"""
from __future__ import annotations

import functools

import networkx as nx
import pytest

import gerrychain
import gerrychain.accept
from gerrychain import MarkovChain, Partition
from gerrychain.constraints import within_percent_of_ideal_population

from src.analysis.config import EnsembleConfig
from src.analysis.mcmc.recom import build_chain, build_initial_partition


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tiny_graph() -> nx.Graph:
    """6-node grid graph with pop_total attributes (100 each → total 600)."""
    g = nx.grid_2d_graph(2, 3)
    # Relabel to integer nodes 0..5 for simpler assignment dicts
    mapping = {node: i for i, node in enumerate(sorted(g.nodes()))}
    g = nx.relabel_nodes(g, mapping)
    for node in g.nodes():
        g.nodes[node]["pop_total"] = 100
    return g


@pytest.fixture()
def two_district_assignment() -> dict[int, int]:
    """Simple valid 2-district assignment for the 6-node grid.

    District 0: nodes 0, 1, 2 (row 0)
    District 1: nodes 3, 4, 5 (row 1)
    Both rows are connected in the grid so each district is contiguous.
    """
    return {0: 0, 1: 0, 2: 0, 3: 1, 4: 1, 5: 1}


@pytest.fixture()
def two_district_config() -> EnsembleConfig:
    """Minimal EnsembleConfig for a 2-district run."""
    return EnsembleConfig(
        k_districts=2,
        pop_tolerance=0.10,
        n_steps=5,
        recom_epsilon=0.05,
        recom_node_repeats=1,
    )


@pytest.fixture()
def initial_partition(
    tiny_graph: nx.Graph,
    two_district_assignment: dict[int, int],
    two_district_config: EnsembleConfig,
) -> Partition:
    return build_initial_partition(tiny_graph, two_district_assignment, two_district_config)


# ---------------------------------------------------------------------------
# build_initial_partition tests
# ---------------------------------------------------------------------------


class TestBuildInitialPartition:
    def test_returns_gerrychain_partition(
        self,
        tiny_graph: nx.Graph,
        two_district_assignment: dict[int, int],
        two_district_config: EnsembleConfig,
    ) -> None:
        """Return value must be a gerrychain.Partition instance."""
        result = build_initial_partition(
            tiny_graph, two_district_assignment, two_district_config
        )
        assert isinstance(result, Partition)

    def test_has_population_updater(
        self,
        initial_partition: Partition,
    ) -> None:
        """Partition must carry a 'population' updater key."""
        assert "population" in initial_partition.updaters

    def test_population_updater_returns_dict(
        self,
        initial_partition: Partition,
    ) -> None:
        """Accessing partition['population'] must return a dict keyed by district."""
        pop = initial_partition["population"]
        assert isinstance(pop, dict)

    def test_population_values_match_node_attrs(
        self,
        initial_partition: Partition,
        two_district_assignment: dict[int, int],
        tiny_graph: nx.Graph,
    ) -> None:
        """Each district's population must equal the sum of its nodes' pop_total."""
        pop = initial_partition["population"]
        # District 0: nodes 0,1,2 → 300 each
        assert pop[0] == 300
        assert pop[1] == 300

    def test_assignment_matches_input(
        self,
        initial_partition: Partition,
        two_district_assignment: dict[int, int],
    ) -> None:
        """partition.assignment must reflect the input assignment dict."""
        for node, district in two_district_assignment.items():
            assert initial_partition.assignment[node] == district

    def test_correct_number_of_districts(
        self,
        initial_partition: Partition,
        two_district_config: EnsembleConfig,
    ) -> None:
        """Number of parts in the partition must equal config.k_districts."""
        assert len(initial_partition.parts) == two_district_config.k_districts

    def test_accepts_plain_nx_graph(
        self,
        tiny_graph: nx.Graph,
        two_district_assignment: dict[int, int],
        two_district_config: EnsembleConfig,
    ) -> None:
        """build_initial_partition must accept a plain nx.Graph without raising."""
        # nx.Graph (not GCGraph) is deliberately passed; the function must wrap it.
        assert isinstance(tiny_graph, nx.Graph)
        result = build_initial_partition(
            tiny_graph, two_district_assignment, two_district_config
        )
        assert isinstance(result, Partition)


# ---------------------------------------------------------------------------
# build_chain tests
# ---------------------------------------------------------------------------


class TestBuildChain:
    @pytest.fixture()
    def chain(self, initial_partition: Partition, two_district_config: EnsembleConfig):
        constraint = within_percent_of_ideal_population(
            initial_partition, two_district_config.pop_tolerance
        )
        acceptance = gerrychain.accept.always_accept
        return build_chain(
            initial_partition,
            two_district_config,
            [constraint],
            acceptance,
        )

    def test_returns_markov_chain(self, chain) -> None:
        """Return value must be a gerrychain.MarkovChain instance."""
        assert isinstance(chain, MarkovChain)

    def test_total_steps_matches_config(
        self, chain, two_district_config: EnsembleConfig
    ) -> None:
        """MarkovChain.total_steps must equal config.n_steps."""
        assert chain.total_steps == two_district_config.n_steps

    def test_chain_is_iterable(self, chain) -> None:
        """Chain must be iterable (has __iter__)."""
        assert hasattr(chain, "__iter__")

    def test_chain_yields_partitions(
        self,
        initial_partition: Partition,
        two_district_config: EnsembleConfig,
    ) -> None:
        """Each step yielded by iterating the chain must be a Partition."""
        constraint = within_percent_of_ideal_population(
            initial_partition, two_district_config.pop_tolerance
        )
        acceptance = gerrychain.accept.always_accept
        chain = build_chain(
            initial_partition,
            two_district_config,
            [constraint],
            acceptance,
        )
        steps = list(chain)
        assert len(steps) == two_district_config.n_steps
        for step in steps:
            assert isinstance(step, Partition)

    def test_chain_initial_state_is_partition(self, chain) -> None:
        """chain.state must be the initial Partition."""
        assert isinstance(chain.state, Partition)

    def test_proposal_uses_allow_pair_reselection(
        self,
        initial_partition: Partition,
        two_district_config: EnsembleConfig,
    ) -> None:
        """The ReCom proposal must pass allow_pair_reselection=True to bipartition_tree.

        This prevents the chain from freezing on Singapore's ~36% zero-population
        subzones, which otherwise cause every bipartition attempt to fail.
        """
        import functools

        constraint = within_percent_of_ideal_population(
            initial_partition, two_district_config.pop_tolerance
        )
        acceptance = gerrychain.accept.always_accept
        chain = build_chain(
            initial_partition,
            two_district_config,
            [constraint],
            acceptance,
        )
        method = chain.proposal.keywords.get("method")
        assert method is not None, "proposal must supply a 'method' kwarg"
        assert isinstance(method, functools.partial), "method must be a functools.partial"
        assert method.keywords.get("allow_pair_reselection") is True
        # max_attempts must be low so failing pairs give up quickly and reselect
        assert method.keywords.get("max_attempts", 100_000) <= 1_000
