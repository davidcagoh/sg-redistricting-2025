"""Variable-size BFS seed partition for the GRC/SMC ensemble.

Extends the equal-population BFS seeder from src/analysis/seed_plans.py
to handle districts with heterogeneous population targets (each district's
target is seat_count × ideal_per_seat).

The seeder grows k districts by BFS, always expanding the district most
below its population target. A local swap pass then drives all districts
within pop_tolerance of their individual targets.
"""
from __future__ import annotations

import random

import networkx as nx

from src.analysis.grc.config import GRCConfig


class GRCSeedError(Exception):
    """Raised when a valid variable-size seed partition cannot be found."""


def _per_district_targets(graph: nx.Graph, config: GRCConfig) -> dict[int, float]:
    """Compute per-district population target from total graph population."""
    total_pop = sum(graph.nodes[n]["pop_total"] for n in graph.nodes)
    ideal_per_seat = total_pop / config.total_seats
    return {
        district_id: seats * ideal_per_seat
        for district_id, seats in config.seat_counts_by_id().items()
    }


def validate_grc_partition(
    graph: nx.Graph,
    assignment: dict[int, int],
    config: GRCConfig,
    *,
    pop_tolerance: float | None = None,
) -> None:
    """Validate that assignment satisfies variable-size population constraints.

    Checks: correct k, all nodes assigned, each district contiguous,
    each district within pop_tolerance of its per-type target.

    Parameters
    ----------
    pop_tolerance:
        Override the tolerance from config.  Pass ``config.seed_pop_tolerance``
        when validating seed partitions; omit (or pass None) to use
        ``config.pop_tolerance`` for chain-time validation.
    """
    actual = set(assignment.values())
    if len(actual) != config.k_districts:
        raise ValueError(
            f"Expected {config.k_districts} districts, got {len(actual)}"
        )

    missing = set(graph.nodes) - set(assignment.keys())
    if missing:
        raise ValueError(f"Assignment missing {len(missing)} node(s): {sorted(missing)}")

    districts_to_nodes: dict[int, list[int]] = {}
    for node, d in assignment.items():
        districts_to_nodes.setdefault(d, []).append(node)

    targets = _per_district_targets(graph, config)
    tol = config.pop_tolerance if pop_tolerance is None else pop_tolerance

    for d, nodes in districts_to_nodes.items():
        subgraph = graph.subgraph(nodes)
        if not nx.is_connected(subgraph):
            raise ValueError(f"District {d} is not contiguous")

        pop = sum(graph.nodes[n]["pop_total"] for n in nodes)
        target = targets[d]
        if target > 0:
            dev = abs(pop - target) / target
            if dev > tol:
                raise ValueError(
                    f"District {d} pop {pop} deviates {dev:.1%} from target "
                    f"{target:.1f} (tolerance {tol:.1%})"
                )


def _bfs_grc_seed(
    graph: nx.Graph,
    config: GRCConfig,
    rng: random.Random,
) -> dict[int, int]:
    """Variable-size BFS seed with absolute-deficit priority.

    All districts grow simultaneously.  At each step, the district with the
    largest *absolute* population deficit (target − current_pop) expands by
    one frontier node.  This naturally prioritises GRC5 (deficit ~208k) over
    GRC4 (~167k) over SMC (~42k), so large districts claim territory before
    small ones box them in.

    Seeds GRC5 districts from the highest-population subzones and SMC districts
    from smaller subzones to give GRC districts a head start.

    Finishes with a swap pass to correct residual imbalance.
    """
    seat_counts = config.seat_counts_by_id()
    total_pop = sum(graph.nodes[n]["pop_total"] for n in graph.nodes)
    ideal_per_seat = total_pop / config.total_seats
    targets = {d: seats * ideal_per_seat for d, seats in seat_counts.items()}

    # Stratified seeds: GRC5 from largest subzones, SMC from small ones
    grc5_ids = sorted([d for d, s in seat_counts.items() if s == 5])
    grc4_ids = sorted([d for d, s in seat_counts.items() if s == 4])
    smc_ids = sorted([d for d, s in seat_counts.items() if s == 1])

    nonzero_sorted_by_pop = sorted(
        [n for n in graph.nodes if graph.nodes[n]["pop_total"] > 0],
        key=lambda n: -graph.nodes[n]["pop_total"],
    )
    n_nodes = len(nonzero_sorted_by_pop)

    # GRC5 seeds: top n_grc5 nodes by population
    grc5_seeds = rng.sample(nonzero_sorted_by_pop[: len(grc5_ids) * 2], len(grc5_ids))
    used = set(grc5_seeds)
    # GRC4 seeds: next tier
    grc4_pool = [n for n in nonzero_sorted_by_pop if n not in used][: len(grc4_ids) * 3]
    if len(grc4_pool) < len(grc4_ids):
        grc4_pool = [n for n in nonzero_sorted_by_pop if n not in used]
    grc4_seeds = rng.sample(grc4_pool, len(grc4_ids))
    used |= set(grc4_seeds)
    # SMC seeds: from the rest
    smc_pool = [n for n in nonzero_sorted_by_pop if n not in used]
    if len(smc_pool) < len(smc_ids):
        smc_pool = [n for n in graph.nodes if n not in used]
    smc_seeds = rng.sample(smc_pool, len(smc_ids))

    all_district_ids = grc5_ids + grc4_ids + smc_ids
    seeds_ordered = grc5_seeds + grc4_seeds + smc_seeds

    assignment: dict[int, int] = {s: d for d, s in zip(all_district_ids, seeds_ordered)}
    district_pops: dict[int, float] = {
        d: float(graph.nodes[s]["pop_total"])
        for d, s in zip(all_district_ids, seeds_ordered)
    }
    frontiers: dict[int, set[int]] = {
        d: {nb for nb in graph.neighbors(s) if nb not in assignment}
        for d, s in zip(all_district_ids, seeds_ordered)
    }
    unassigned = set(graph.nodes) - set(assignment)

    while unassigned:
        # Expand the district with largest absolute deficit
        candidates = [
            (targets[d] - district_pops[d], d)
            for d in all_district_ids
            if frontiers[d]
        ]
        if not candidates:
            break
        _, best = max(candidates)  # most under-filled
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

    # Assign disconnected remainder
    for node in sorted(unassigned):
        neighbor_districts = [
            assignment[nb] for nb in graph.neighbors(node) if nb in assignment
        ]
        best = (
            max(neighbor_districts, key=lambda d: targets[d] - district_pops[d])
            if neighbor_districts
            else max(all_district_ids, key=lambda d: targets[d] - district_pops[d])
        )
        assignment[node] = best
        district_pops[best] += graph.nodes[node]["pop_total"]

    return _grc_swap_pass(graph, assignment, config, rng, targets)


def _grc_swap_pass(
    graph: nx.Graph,
    assignment: dict[int, int],
    config: GRCConfig,
    rng: random.Random,
    targets: dict[int, float],
    max_iters: int = 5000,
) -> dict[int, int]:
    """Boundary swap pass with per-district population targets.

    Iterates full boundary sweeps until no improving swap is found or
    max_iters is reached.  Never empties a district.
    """
    assignment = dict(assignment)

    for _ in range(max_iters):
        district_pops: dict[int, float] = {}
        for n, d in assignment.items():
            district_pops[d] = district_pops.get(d, 0.0) + graph.nodes[n]["pop_total"]

        over = [
            d for d, pop in district_pops.items()
            if targets[d] > 0 and abs(pop - targets[d]) / targets[d] > config.pop_tolerance
        ]
        if not over:
            break

        # Collect all boundary nodes for over-tolerance districts
        boundary_moves: list[tuple[int, int, float]] = []  # (node, d_to, delta_err)
        rng.shuffle(over)
        for d_from in over:
            pop_from = district_pops[d_from]
            tgt_from = targets[d_from]
            d_from_nodes = [n for n, d in assignment.items() if d == d_from]
            for node in d_from_nodes:
                node_pop = graph.nodes[node]["pop_total"]
                adj_districts = {
                    assignment[nb]
                    for nb in graph.neighbors(node)
                    if assignment[nb] != d_from
                }
                for d_to in adj_districts:
                    pop_to = district_pops[d_to]
                    tgt_to = targets[d_to]
                    new_from = pop_from - node_pop
                    new_to = pop_to + node_pop
                    old_err = (
                        abs(pop_from - tgt_from) / tgt_from
                        + abs(pop_to - tgt_to) / tgt_to
                    ) if tgt_from > 0 and tgt_to > 0 else 0.0
                    new_err = (
                        abs(new_from - tgt_from) / tgt_from
                        + abs(new_to - tgt_to) / tgt_to
                    ) if tgt_from > 0 and tgt_to > 0 else 0.0
                    if new_err < old_err:
                        boundary_moves.append((node, d_to, old_err - new_err))

        if not boundary_moves:
            break

        # Apply the single best improving swap this iteration
        boundary_moves.sort(key=lambda x: -x[2])
        applied = False
        for node, d_to, _ in boundary_moves:
            d_from = assignment[node]
            remaining = [
                n2 for n2, d in assignment.items()
                if d == d_from and n2 != node
            ]
            if remaining and nx.is_connected(graph.subgraph(remaining)):
                assignment[node] = d_to
                applied = True
                break

        if not applied:
            break

    return assignment


def _unit_merge_grc_seed(
    graph: nx.Graph,
    config: GRCConfig,
    rng: random.Random,
) -> dict[int, int]:
    """Two-stage GRC seed using paper-1 BFS as a unit generator.

    Stage 1 — unit partition: reuse paper-1's ``_bfs_seed_partition`` with
    ``k = config.total_seats`` (97) to produce one equal-population unit per
    seat.  Each unit has ~ideal_per_seat people.

    Stage 2 — unit merging: build a unit-adjacency meta-graph (97 nodes), then
    run a greedy BFS on the meta-graph to merge units into districts, largest
    districts first (GRC5 = 5 units, GRC4 = 4 units, SMC = 1 unit).

    Because the meta-graph has equal-weight nodes and only 97 of them, the BFS
    converges reliably regardless of Singapore's zero-population topology.

    District IDs are assigned to match ``config.seat_counts_by_id()``:
    GRC5 districts first (IDs for seats=5), then GRC4 (seats=4), then SMC (seats=1).
    """
    from src.analysis.config import EnsembleConfig
    from src.analysis.seed_plans import _bfs_seed_partition

    total_seats = config.total_seats
    seat_counts = config.seat_counts_by_id()

    # Stage 1: equal-pop unit partition using the paper-1 BFS seeder
    unit_cfg = EnsembleConfig(
        k_districts=total_seats,
        pop_tolerance=0.50,  # loose: zero-pop subzones make tight balance hard
        seed=rng.randint(0, 2**31),
    )
    unit_assignment: dict[int, int] = _bfs_seed_partition(graph, unit_cfg, rng)

    # Build unit adjacency meta-graph
    meta: nx.Graph = nx.Graph()
    meta.add_nodes_from(range(total_seats))
    for n1, n2 in graph.edges():
        u1 = unit_assignment.get(n1)
        u2 = unit_assignment.get(n2)
        if u1 is not None and u2 is not None and u1 != u2:
            meta.add_edge(u1, u2)

    # Stage 2: BFS on meta-graph to merge units into districts
    # Order: largest seat-count first so GRC5 claims territory before SMC
    by_seats = sorted(set(seat_counts.values()), reverse=True)
    district_groups: dict[int, int] = {}  # unit_id → district_id
    used_units: set[int] = set()
    district_id = 0

    # Assign district IDs in the order defined by seat_counts_by_id
    # (0..k-1), grouped by type so GRC5 get IDs 23-32, etc.
    seat_to_district_ids: dict[int, list[int]] = {}
    for d, s in seat_counts.items():
        seat_to_district_ids.setdefault(s, []).append(d)

    for seats in by_seats:
        d_ids = sorted(seat_to_district_ids.get(seats, []))
        for d in d_ids:
            # Seed: any unused meta-node adjacent to already-used territory, else any unused
            unused = [u for u in meta.nodes if u not in used_units]
            if not unused:
                break
            adjacent = [u for u in unused if any(nb in used_units for nb in meta.neighbors(u))]
            seed_unit = rng.choice(adjacent if adjacent else unused)

            collected: set[int] = {seed_unit}
            frontier: set[int] = set(meta.neighbors(seed_unit)) - used_units

            while len(collected) < seats and frontier:
                nxt = rng.choice(sorted(frontier - collected - used_units) or sorted(frontier))
                collected.add(nxt)
                frontier |= set(meta.neighbors(nxt))
                frontier -= collected | used_units

            for u in collected:
                district_groups[u] = d
            used_units |= collected

    # Any units not merged (shouldn't happen) → assign to nearest district
    for u in range(total_seats):
        if u not in district_groups:
            neighbors_assigned = [district_groups[nb] for nb in meta.neighbors(u) if nb in district_groups]
            district_groups[u] = neighbors_assigned[0] if neighbors_assigned else 0

    # Map original graph nodes → district IDs via unit assignment
    return {n: district_groups[unit_assignment[n]] for n in graph.nodes}


_BFS_ATTEMPTS = 50


def make_grc_seed_partition(
    graph: nx.Graph,
    config: GRCConfig,
) -> dict[int, int]:
    """Generate a variable-size seed partition for the GRC/SMC ensemble.

    Strategy (two-phase, mirroring paper-1's make_seed_partition):

    Phase 1 — unit-merge seeder: uses paper-1's ``_bfs_seed_partition`` to
    produce k=total_seats equal-population units, then merges adjacent units
    on a meta-graph into GRC5/GRC4/SMC districts.  This reuses the proven
    Singapore-graph seeder and avoids the boxing-in problem of simultaneous BFS.

    Phase 2 — fallback: if the unit-merge seeder fails validation (unlikely
    but possible due to topology), falls back to ``_bfs_grc_seed`` with up to
    _BFS_ATTEMPTS different random seeds.

    Validation for seeding uses ``config.seed_pop_tolerance`` (default 20%),
    which is relaxed compared to the chain's runtime ``pop_tolerance`` (10%).
    """
    last_exc: Exception | None = None

    # Phase 1: unit-merge approach
    for attempt in range(20):
        rng = random.Random(config.seed + attempt * 7919)
        try:
            assignment = _unit_merge_grc_seed(graph, config, rng)
            validate_grc_partition(
                graph, assignment, config,
                pop_tolerance=config.seed_pop_tolerance,
            )
            return assignment
        except Exception as exc:
            last_exc = exc

    # Phase 2: fallback BFS
    for attempt in range(_BFS_ATTEMPTS):
        bfs_rng = random.Random(config.seed + attempt * 31337)
        try:
            assignment = _bfs_grc_seed(graph, config, bfs_rng)
            validate_grc_partition(
                graph, assignment, config,
                pop_tolerance=config.seed_pop_tolerance,
            )
            return assignment
        except Exception as exc:
            last_exc = exc

    raise GRCSeedError(
        f"Failed to generate a valid GRC seed after unit-merge and BFS fallback. "
        f"Last error: {last_exc}"
    ) from last_exc
