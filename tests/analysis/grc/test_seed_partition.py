"""Tests for src.analysis.grc.seed_partition."""
import networkx as nx
import pytest

from src.analysis.grc.config import GRCConfig, DistrictType
from src.analysis.grc.seed_partition import (
    GRCSeedError,
    make_grc_seed_partition,
    validate_grc_partition,
)


def _make_grid_graph(rows: int = 6, cols: int = 6, pop_per_node: int = 1000) -> nx.Graph:
    """Build a simple grid graph with uniform population."""
    g = nx.grid_2d_graph(rows, cols)
    g = nx.convert_node_labels_to_integers(g)
    for n in g.nodes:
        g.nodes[n]["pop_total"] = pop_per_node
        g.nodes[n]["pln_area"] = f"PLN_{n % 4}"
        g.nodes[n]["hdb_town"] = f"TOWN_{n % 3}"
    return g


def _small_config() -> GRCConfig:
    """3 districts: 1×(1-seat) + 1×(2-seat) + 1×(3-seat), total 6 seats."""
    return GRCConfig(
        district_types=(
            DistrictType(seat_count=1, num_districts=1),
            DistrictType(seat_count=2, num_districts=1),
            DistrictType(seat_count=3, num_districts=1),
        ),
        pop_tolerance=0.40,
        n_steps=10,
        burn_in=0,
        seed=42,
    )


class TestValidateGRCPartition:
    def test_wrong_district_count(self):
        g = _make_grid_graph(2, 3, 100)
        cfg = _small_config()
        bad = {n: 0 for n in g.nodes}  # only 1 district
        with pytest.raises(ValueError, match="Expected 3 districts"):
            validate_grc_partition(g, bad, cfg)

    def test_missing_nodes(self):
        g = _make_grid_graph(2, 3, 100)
        cfg = _small_config()
        # 3 districts but only 4 of 6 nodes assigned → missing check fires
        partial = {0: 0, 1: 1, 2: 2, 3: 0}
        with pytest.raises(ValueError, match="missing"):
            validate_grc_partition(g, partial, cfg)


class TestMakeGRCSeedPartition:
    def test_produces_valid_partition(self):
        g = _make_grid_graph(6, 6, 1000)
        cfg = GRCConfig(
            district_types=(
                DistrictType(seat_count=1, num_districts=4),
                DistrictType(seat_count=2, num_districts=2),
            ),
            pop_tolerance=0.40,
            seed=42,
        )
        assignment = make_grc_seed_partition(g, cfg)
        # Should not raise
        validate_grc_partition(g, assignment, cfg)

    def test_all_nodes_assigned(self):
        g = _make_grid_graph(4, 4, 500)
        cfg = GRCConfig(
            district_types=(
                DistrictType(seat_count=1, num_districts=3),
                DistrictType(seat_count=3, num_districts=1),
            ),
            pop_tolerance=0.50,
            seed=7,
        )
        assignment = make_grc_seed_partition(g, cfg)
        assert set(assignment.keys()) == set(g.nodes)

    def test_correct_district_count(self):
        g = _make_grid_graph(4, 4, 500)
        cfg = GRCConfig(
            district_types=(
                DistrictType(seat_count=1, num_districts=3),
                DistrictType(seat_count=3, num_districts=1),
            ),
            pop_tolerance=0.50,
            seed=7,
        )
        assignment = make_grc_seed_partition(g, cfg)
        assert len(set(assignment.values())) == cfg.k_districts
