"""Variable-target ReCom proposal for the GRC/SMC ensemble.

Standard GerryChain ReCom assumes a single population target (ideal_pop)
shared by all districts. Here each district has a seat count, so its
target is seat_count × ideal_per_seat. When a pair of adjacent districts
is merged and re-split, each piece must satisfy its own per-district
tolerance constraint independently.

The proposal is a drop-in replacement for gerrychain.proposals.recom.
It has the same interface as GerryChain's proposal callables:

    proposal(partition) -> Partition
"""
from __future__ import annotations

import random
from functools import partial
from typing import Callable

import networkx as nx
from gerrychain import Partition
from gerrychain.tree import bipartition_tree

from src.analysis.grc.config import GRCConfig


def _pop(graph: nx.Graph, nodes, pop_col: str) -> float:
    return sum(graph.nodes[n][pop_col] for n in nodes)


def build_variable_recom_proposal(
    graph: nx.Graph,
    config: GRCConfig,
    seat_counts: dict[int, int],
    total_pop: float,
    pop_col: str = "pop_total",
) -> Callable[[Partition], Partition]:
    """Return a callable proposal for a GerryChain MarkovChain.

    Parameters
    ----------
    graph:
        The underlying NetworkX graph (same object passed to Partition).
    config:
        GRC ensemble config supplying recom_epsilon and max_attempts_per_step.
    seat_counts:
        Mapping district_id → seat_count, fixed for the lifetime of the chain.
    total_pop:
        Total population in the graph (used to compute ideal_per_seat).
    pop_col:
        Node attribute name for population.

    Returns
    -------
    callable
        Proposal function with signature (partition) -> Partition.
    """
    ideal_per_seat = total_pop / config.total_seats
    epsilon = config.recom_epsilon
    max_attempts = config.max_attempts_per_step

    bipartition_fn = partial(
        bipartition_tree,
        allow_pair_reselection=True,
        max_attempts=1000,
    )

    def _proposal(partition: Partition) -> Partition:
        crossing = list(partition.crossing_edges)
        if not crossing:
            return partition

        random.shuffle(crossing)

        for _ in range(max_attempts):
            edge = random.choice(crossing)
            u, v = edge
            d1 = partition.assignment[u]
            d2 = partition.assignment[v]

            if d1 == d2:
                continue

            s1 = seat_counts[d1]
            s2 = seat_counts[d2]
            target1 = s1 * ideal_per_seat
            target2 = s2 * ideal_per_seat

            merged_nodes = frozenset(partition.parts[d1]) | frozenset(partition.parts[d2])
            merged_subgraph = partition.graph.subgraph(merged_nodes)

            # Try both orientations: target1 for piece_1, then target2 for piece_1
            for target_a, target_b, da, db in [
                (target1, target2, d1, d2),
                (target2, target1, d2, d1),
            ]:
                try:
                    piece_a = bipartition_fn(
                        merged_subgraph,
                        pop_col=pop_col,
                        pop_target=target_a,
                        epsilon=epsilon,
                    )
                except Exception:
                    continue

                piece_b = merged_nodes - piece_a

                # Verify both pieces satisfy their respective tolerances
                pop_a = _pop(partition.graph, piece_a, pop_col)
                pop_b = _pop(partition.graph, piece_b, pop_col)

                ok_a = target_a > 0 and abs(pop_a - target_a) / target_a <= epsilon
                ok_b = target_b > 0 and abs(pop_b - target_b) / target_b <= epsilon

                if ok_a and ok_b:
                    flips = {n: da for n in piece_a}
                    flips.update({n: db for n in piece_b})
                    return partition.flip(flips)

        return partition  # All attempts failed: stay put (chain counts this as rejected)

    return _proposal


def build_grc_partition(
    graph: nx.Graph,
    assignment: dict[int, int],
    config: GRCConfig,
) -> Partition:
    """Build a GerryChain Partition from a GRC seed assignment.

    Wires a 'population' Tally updater for use in chain constraints and
    metric collection. The seat_count_by_district mapping is *not* stored
    in the Partition (it is external to GerryChain's state); callers must
    hold it separately.
    """
    from gerrychain import Graph as GCGraph
    from gerrychain.updaters import Tally

    gc_graph = GCGraph(graph)
    updaters = {"population": Tally("pop_total", alias="population")}
    return Partition(graph=gc_graph, assignment=assignment, updaters=updaters)
