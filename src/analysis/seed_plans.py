"""Generate and validate seed partition plans for the MCMC ensemble pipeline.

A seed partition is an initial assignment of graph nodes (subzones) to districts
that satisfies population balance and contiguity constraints. It is passed to
GerryChain's MCMC chain as the starting state.

Two seeders are available (see wiki/seeding.md):
  1. recursive_tree_part (GerryChain default) — fails on Singapore's graph because
     ~36% of subzones have pop_total=0, making balanced spanning-tree cuts impossible
     in some recursion sub-graphs.
  2. _bfs_seed_partition (BFS fallback) — greedy BFS growth + local swap pass;
     always produces a valid seed on the Singapore graph.
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
# BFS seeder (fallback for Singapore's zero-population-heavy graph)
# ---------------------------------------------------------------------------


def _bfs_seed_partition(
    graph: nx.Graph,
    config: EnsembleConfig,
    rng: random.Random,
) -> dict[int, int]:
    """Greedy BFS growth seed partition.

    Grows k districts from randomly chosen non-zero-population seeds, always
    expanding the district with the smallest current population. After BFS
    growth, a local boundary swap pass drives all districts within pop_tolerance.

    This is the fallback used when recursive_tree_part cannot find a balanced
    spanning-tree cut (the typical failure mode on Singapore's graph, which has
    ~36% zero-population subzones creating contiguous uninhabited clusters).

    Parameters
    ----------
    graph:
        Subzone adjacency graph with 'pop_total' node attributes.
    config:
        Ensemble configuration (k_districts, pop_tolerance).
    rng:
        Random number generator (seeded externally for reproducibility).

    Returns
    -------
    dict[int, int]
        Mapping node_id → district_id. May not pass validate_partition if the
        graph topology prevents balance within tolerance; caller should validate.
    """
    k = config.k_districts

    # Pick k seeds from non-zero-population nodes
    nonzero_nodes = [n for n in graph.nodes if graph.nodes[n]["pop_total"] > 0]
    seed_pool = nonzero_nodes if len(nonzero_nodes) >= k else list(graph.nodes)
    seeds = rng.sample(seed_pool, k)

    assignment: dict[int, int] = {s: i for i, s in enumerate(seeds)}
    district_pops: list[int] = [graph.nodes[s]["pop_total"] for s in seeds]
    frontiers: list[set[int]] = [
        {nb for nb in graph.neighbors(s) if nb not in assignment}
        for s in seeds
    ]
    unassigned = set(graph.nodes) - set(assignment)

    # BFS growth: always expand the smallest-population district that has frontier
    while unassigned:
        candidates = [(district_pops[i], i) for i in range(k) if frontiers[i]]
        if not candidates:
            break
        _, best = min(candidates)
        frontier_list = sorted(frontiers[best])
        node = rng.choice(frontier_list)
        frontiers[best].discard(node)
        if node not in unassigned:
            continue
        assignment[node] = best
        district_pops[best] += graph.nodes[node]["pop_total"]
        unassigned.discard(node)
        for nb in graph.neighbors(node):
            if nb not in assignment:
                frontiers[best].add(nb)

    # Assign any remainder nodes (disconnected components not reached by BFS)
    for node in sorted(unassigned):
        neighbor_districts = [
            assignment[nb] for nb in graph.neighbors(node) if nb in assignment
        ]
        best = (
            min(neighbor_districts, key=lambda d: district_pops[d])
            if neighbor_districts
            else min(range(k), key=lambda d: district_pops[d])
        )
        assignment[node] = best
        district_pops[best] += graph.nodes[node]["pop_total"]

    return _local_swap_pass(graph, assignment, config, rng)


def _local_swap_pass(
    graph: nx.Graph,
    assignment: dict[int, int],
    config: EnsembleConfig,
    rng: random.Random,
    max_iters: int = 500,
) -> dict[int, int]:
    """Iterative boundary swap to drive districts within pop_tolerance.

    For each over-populated district, tries moving a boundary node to an
    adjacent under-populated district if the swap reduces total imbalance
    and preserves contiguity of the donor district.
    """
    total_pop = sum(graph.nodes[n]["pop_total"] for n in graph.nodes)
    ideal_pop = total_pop / config.k_districts
    if ideal_pop == 0:
        return dict(assignment)

    assignment = dict(assignment)

    for _ in range(max_iters):
        # Recompute district populations
        district_pops: dict[int, int] = {}
        for n, d in assignment.items():
            district_pops[d] = district_pops.get(d, 0) + graph.nodes[n]["pop_total"]

        over = [
            d for d, pop in district_pops.items()
            if abs(pop - ideal_pop) / ideal_pop > config.pop_tolerance
        ]
        if not over:
            break

        improved = False
        rng.shuffle(over)
        for d_from in over:
            pop_from = district_pops[d_from]
            d_from_nodes = [n for n, d in assignment.items() if d == d_from]
            rng.shuffle(d_from_nodes)
            for node in d_from_nodes:
                node_pop = graph.nodes[node]["pop_total"]
                adj_districts = {
                    assignment[nb] for nb in graph.neighbors(node)
                    if assignment[nb] != d_from
                }
                for d_to in adj_districts:
                    pop_to = district_pops[d_to]
                    new_from = pop_from - node_pop
                    new_to = pop_to + node_pop
                    if (abs(new_from - ideal_pop) + abs(new_to - ideal_pop) <
                            abs(pop_from - ideal_pop) + abs(pop_to - ideal_pop)):
                        # Verify donor district stays connected after removal
                        remaining = [n2 for n2, d in assignment.items()
                                     if d == d_from and n2 != node]
                        if not remaining or nx.is_connected(graph.subgraph(remaining)):
                            assignment[node] = d_to
                            district_pops[d_from] = new_from
                            district_pops[d_to] = new_to
                            pop_from = new_from
                            improved = True
                            break
                if improved:
                    break
            if improved:
                break
        if not improved:
            break

    return assignment


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

_BFS_ATTEMPTS = 10


def make_seed_partition(
    graph: nx.Graph,
    config: EnsembleConfig,
) -> dict[int, int]:
    """Generate a seed partition for the MCMC ensemble.

    Phase 1: tries GerryChain's recursive_tree_part up to
    config.max_attempts_per_step times.

    Phase 2: if all recursive_tree_part attempts fail (typically due to
    zero-population subzone clusters on the Singapore graph), falls back to
    _bfs_seed_partition with up to _BFS_ATTEMPTS different random seeds.

    Raises SeedPartitionError only if both phases fail.

    See wiki/seeding.md for the literature basis for this two-phase strategy.

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
        If all recursive_tree_part and BFS attempts fail.
    """
    total_pop = sum(graph.nodes[n]["pop_total"] for n in graph.nodes)
    ideal_pop = total_pop / config.k_districts

    random.seed(config.seed)
    gc_graph = GerryChainGraph(graph)

    _SEED_EPSILONS = [0.45, 0.40, 0.35, 0.30, 0.25, 0.20, config.pop_tolerance]

    last_exc: Exception | None = None

    # Phase 1: recursive_tree_part
    for attempt in range(config.max_attempts_per_step):
        epsilon = _SEED_EPSILONS[min(attempt, len(_SEED_EPSILONS) - 1)]
        try:
            assignment: dict[int, int] = recursive_tree_part(
                gc_graph,
                parts=range(config.k_districts),
                pop_target=ideal_pop,
                pop_col="pop_total",
                epsilon=epsilon,
            )
            validate_partition(graph, assignment, config)
            return assignment
        except Exception as exc:
            last_exc = exc

    # Phase 2: BFS fallback
    for bfs_attempt in range(_BFS_ATTEMPTS):
        bfs_rng = random.Random(config.seed + bfs_attempt * 31337)
        try:
            assignment = _bfs_seed_partition(graph, config, bfs_rng)
            validate_partition(graph, assignment, config)
            return assignment
        except Exception as exc:
            last_exc = exc

    raise SeedPartitionError(
        f"Failed to generate a valid seed partition after "
        f"{config.max_attempts_per_step} recursive_tree_part attempt(s) and "
        f"{_BFS_ATTEMPTS} BFS attempt(s). "
        f"Last error: {last_exc}"
    ) from last_exc
