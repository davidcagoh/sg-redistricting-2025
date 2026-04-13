"""Generate and validate seed partition plans for the MCMC ensemble pipeline.

A seed partition is an initial assignment of graph nodes (subzones) to districts
that satisfies population balance and contiguity constraints. It is passed to
GerryChain's MCMC chain as the starting state.
"""
from __future__ import annotations

import random

import networkx as nx

from gerrychain import Graph as GerryChainGraph
from gerrychain.tree import recursive_tree_part

from src.analysis.config import EnsembleConfig


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SeedPartitionError(Exception):
    """Raised when a valid seed partition cannot be found within max_attempts."""


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_partition(
    graph: nx.Graph,
    assignment: dict[int, int],
    config: EnsembleConfig,
) -> None:
    """Validate a partition assignment.

    Checks (in order):
    1. Correct number of districts (== config.k_districts)
    2. All nodes assigned (all graph nodes appear in assignment)
    3. Each district is contiguous (nx.is_connected on the district subgraph)
    4. Population balance: each district within config.pop_tolerance of ideal

    Parameters
    ----------
    graph:
        The adjacency graph produced by build_subzone_graph.
    assignment:
        Mapping of node_id → district_id.
    config:
        Ensemble configuration supplying k_districts and pop_tolerance.

    Raises
    ------
    ValueError
        With a descriptive message on the first check that fails.
    """
    # --- Check 1: correct number of districts ---
    actual_districts = set(assignment.values())
    if len(actual_districts) != config.k_districts:
        raise ValueError(
            f"Expected {config.k_districts} district(s), "
            f"but assignment uses {len(actual_districts)} district(s): {sorted(actual_districts)}"
        )

    # --- Check 2: all nodes assigned ---
    graph_nodes = set(graph.nodes)
    assigned_nodes = set(assignment.keys())
    missing = graph_nodes - assigned_nodes
    if missing:
        raise ValueError(
            f"Assignment is missing {len(missing)} node(s): {sorted(missing)}"
        )

    # --- Check 3: contiguity of each district ---
    districts_to_nodes: dict[int, list[int]] = {}
    for node, district in assignment.items():
        districts_to_nodes.setdefault(district, []).append(node)

    for district_id, nodes in districts_to_nodes.items():
        subgraph = graph.subgraph(nodes)
        if not nx.is_connected(subgraph):
            raise ValueError(
                f"District {district_id} is not contiguous (not connected). "
                f"Nodes in district: {sorted(nodes)}"
            )

    # --- Check 4: population balance ---
    total_pop = sum(graph.nodes[n]["pop_total"] for n in graph.nodes)
    ideal_pop = total_pop / config.k_districts

    for district_id, nodes in districts_to_nodes.items():
        district_pop = sum(graph.nodes[n]["pop_total"] for n in nodes)
        if ideal_pop > 0:
            deviation = abs(district_pop - ideal_pop) / ideal_pop
        else:
            deviation = 0.0

        if deviation > config.pop_tolerance:
            raise ValueError(
                f"District {district_id} population {district_pop} deviates "
                f"{deviation:.1%} from ideal {ideal_pop:.1f}, "
                f"exceeding tolerance {config.pop_tolerance:.1%}"
            )


# ---------------------------------------------------------------------------
# Seed generation
# ---------------------------------------------------------------------------


def make_seed_partition(
    graph: nx.Graph,
    config: EnsembleConfig,
) -> dict[int, int]:
    """Generate a seed partition using GerryChain's recursive_tree_part.

    The partition divides the graph into config.k_districts contiguous,
    population-balanced districts. The function retries up to
    config.max_attempts_per_step times before raising SeedPartitionError.

    Parameters
    ----------
    graph:
        The adjacency graph produced by build_subzone_graph.
    config:
        Ensemble configuration supplying k_districts, pop_tolerance, seed,
        and max_attempts_per_step.

    Returns
    -------
    dict[int, int]
        Mapping of node_id → district_id.

    Raises
    ------
    SeedPartitionError
        If all max_attempts_per_step attempts fail to produce a valid partition.
    """
    total_pop = sum(graph.nodes[n]["pop_total"] for n in graph.nodes)
    ideal_pop = total_pop / config.k_districts

    random.seed(config.seed)

    # GerryChain's recursive_tree_part requires a GerryChain Graph object,
    # not a plain nx.Graph. Convert once before the retry loop.
    gc_graph = GerryChainGraph(graph)

    last_exc: Exception | None = None
    for attempt in range(config.max_attempts_per_step):
        try:
            assignment: dict[int, int] = recursive_tree_part(
                gc_graph,
                parts=range(config.k_districts),
                pop_target=ideal_pop,
                pop_col="pop_total",
                epsilon=config.pop_tolerance,
            )
            return assignment
        except Exception as exc:
            last_exc = exc

    raise SeedPartitionError(
        f"Failed to generate a valid seed partition after "
        f"{config.max_attempts_per_step} attempt(s). "
        f"Last error: {last_exc}"
    ) from last_exc
