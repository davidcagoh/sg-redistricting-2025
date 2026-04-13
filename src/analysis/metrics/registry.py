"""Registry: aggregate all redistricting metric functions into a single call.

All constituent functions are pure (no side effects). This module only
orchestrates them and merges their results.
"""
from __future__ import annotations

import networkx as nx
from shapely.geometry.base import BaseGeometry

from src.analysis.metrics.compactness import compute_compactness_metrics
from src.analysis.metrics.population import compute_population_metrics
from src.analysis.metrics.splitting import (
    pln_area_splits,
    town_split_entropy,
    towns_split,
)

METRICS_VERSION = "1"


def compute_all(
    partition_parts: dict[int, list[int]],
    subzone_geoms: dict[int, BaseGeometry],
    graph: nx.Graph,
    assignment: dict[int, int],
) -> dict[str, float]:
    """Compute all redistricting metrics for one partition step.

    Parameters
    ----------
    partition_parts:
        Mapping of district_id → list of node IDs in that district.
    subzone_geoms:
        Mapping of node_id → Shapely geometry for each subzone.
    graph:
        NetworkX graph whose nodes carry ``pop_total``, ``hdb_town``,
        and ``pln_area`` attributes.
    assignment:
        Mapping of node_id → district_id (inverse of partition_parts).

    Returns
    -------
    dict[str, float]
        Dictionary with keys:
        ``max_abs_pop_dev``, ``pop_range``, ``ideal_pop``,
        ``mean_pp``, ``min_pp``, ``cut_edges``,
        ``towns_split``, ``pln_area_splits``, ``town_split_entropy``.
    """
    parts_pop: dict[int, int] = {
        district: sum(graph.nodes[node]["pop_total"] for node in nodes)
        for district, nodes in partition_parts.items()
    }

    pop_metrics = compute_population_metrics(parts_pop)
    compactness_metrics = compute_compactness_metrics(
        partition_parts, subzone_geoms, graph, assignment
    )
    splitting_metrics = {
        "towns_split": towns_split(partition_parts, graph),
        "pln_area_splits": pln_area_splits(partition_parts, graph),
        "town_split_entropy": town_split_entropy(partition_parts, graph),
    }

    return {**pop_metrics, **compactness_metrics, **splitting_metrics}
