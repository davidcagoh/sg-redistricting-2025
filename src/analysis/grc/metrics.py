"""GRC-specific metrics for the variable-size ensemble (paper 2).

These metrics address the research questions specific to paper 2:
  - Does the actual GRC placement capture minority population at rates
    consistent with a neutral ensemble?
  - Are competitive subzones allocated to appropriately-sized districts?
  - Does the seat-size distribution across planning areas match random?

All functions are pure; they never mutate the graph or partition.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Sequence

import networkx as nx


def minority_capture_by_type(
    partition_parts: dict[int, list[int]],
    graph: nx.Graph,
    seat_counts: dict[int, int],
    minority_attr: str = "pct_minority",
) -> dict[str, float]:
    """Mean minority population share by district type.

    Returns a dict with keys 'smc_mean_minority', 'grc4_mean_minority',
    'grc5_mean_minority' (and similar for other seat counts encountered).

    Parameters
    ----------
    partition_parts:
        district_id → list of node IDs.
    graph:
        Nodes must carry pop_total and minority_attr attributes.
    seat_counts:
        district_id → seat_count (fixed for the chain lifetime).
    minority_attr:
        Node attribute name for minority population fraction (0-1).
        If attribute is missing on a node it is treated as 0.
    """
    by_type: dict[int, list[float]] = defaultdict(list)

    for district_id, nodes in partition_parts.items():
        seats = seat_counts.get(district_id, 1)
        total_pop = sum(graph.nodes[n].get("pop_total", 0) for n in nodes)
        minority_pop = sum(
            graph.nodes[n].get("pop_total", 0) * graph.nodes[n].get(minority_attr, 0.0)
            for n in nodes
        )
        pct = minority_pop / total_pop if total_pop > 0 else 0.0
        by_type[seats].append(pct)

    result: dict[str, float] = {}
    type_labels = {1: "smc", 4: "grc4", 5: "grc5"}
    for seats, pcts in by_type.items():
        label = type_labels.get(seats, f"grc{seats}")
        result[f"{label}_mean_minority"] = sum(pcts) / len(pcts) if pcts else 0.0
        result[f"{label}_n"] = float(len(pcts))

    return result


def seat_type_by_planning_area(
    partition_parts: dict[int, list[int]],
    graph: nx.Graph,
    seat_counts: dict[int, int],
) -> dict[str, float]:
    """Compute fraction of each planning area's population in GRC vs SMC.

    Returns:
        pln_area_grc_pop_frac: weighted mean fraction of population in GRC
                               districts, weighted by planning-area population.
    """
    # pln_area → {district_type: pop}
    area_type_pop: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for district_id, nodes in partition_parts.items():
        seats = seat_counts.get(district_id, 1)
        dtype = "grc" if seats > 1 else "smc"
        for node in nodes:
            pln_area = graph.nodes[node].get("pln_area", "UNKNOWN")
            pop = graph.nodes[node].get("pop_total", 0)
            area_type_pop[pln_area][dtype] += pop

    fracs: list[float] = []
    weights: list[float] = []
    for area, type_pops in area_type_pop.items():
        total = sum(type_pops.values())
        if total > 0:
            fracs.append(type_pops.get("grc", 0.0) / total)
            weights.append(total)

    if not weights:
        return {"pln_area_grc_pop_frac": 0.0}

    weighted_mean = sum(f * w for f, w in zip(fracs, weights)) / sum(weights)
    return {"pln_area_grc_pop_frac": weighted_mean}


def compute_grc_metrics(
    partition_parts: dict[int, list[int]],
    graph: nx.Graph,
    seat_counts: dict[int, int],
    minority_attr: str = "pct_minority",
) -> dict[str, float]:
    """Aggregate all GRC-specific metrics for one chain step."""
    result: dict[str, float] = {}
    result.update(
        minority_capture_by_type(partition_parts, graph, seat_counts, minority_attr)
    )
    result.update(seat_type_by_planning_area(partition_parts, graph, seat_counts))
    return result
