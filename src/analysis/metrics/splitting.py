"""Community-splitting metrics for Singapore electoral redistricting analysis.

Each function measures how much a proposed partition fragments geographic
communities — HDB towns and URA planning areas — across electoral districts.

All functions are pure: they never mutate the graph or the partition.
"""
from __future__ import annotations

import math
from collections import defaultdict

import networkx as nx


def towns_split(
    partition_parts: dict[int, list[int]],
    graph: nx.Graph,
) -> int:
    """Count HDB towns appearing in more than one district.

    Parameters
    ----------
    partition_parts:
        Mapping of district_id → list of node IDs in that district.
    graph:
        NetworkX graph whose nodes carry an ``hdb_town`` attribute.
        Nodes with ``hdb_town=None`` are excluded from consideration.

    Returns
    -------
    int
        Number of distinct HDB towns that span more than one district.
        Returns 0 if no nodes have a non-None ``hdb_town``.
    """
    # town → set of district IDs that contain at least one node from that town
    town_districts: dict[str, set[int]] = defaultdict(set)

    for district_id, node_ids in partition_parts.items():
        for node_id in node_ids:
            town = graph.nodes[node_id].get("hdb_town")
            if town is None:
                continue
            town_districts[town].add(district_id)

    return sum(1 for districts in town_districts.values() if len(districts) > 1)


def town_split_entropy(
    partition_parts: dict[int, list[int]],
    graph: nx.Graph,
) -> float:
    """Shannon entropy of district assignments per HDB town.

    For each town, computes the distribution of its nodes across districts,
    then calculates the Shannon entropy of that distribution. The metric is
    the mean entropy across all towns (None-town nodes are excluded entirely).

    Parameters
    ----------
    partition_parts:
        Mapping of district_id → list of node IDs in that district.
    graph:
        NetworkX graph whose nodes carry an ``hdb_town`` attribute.

    Returns
    -------
    float
        Mean Shannon entropy (log base-2) across all towns.
        Returns 0.0 if no towns are present (all ``hdb_town`` are None).
    """
    # town → {district_id: count_of_nodes}
    town_district_counts: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))

    for district_id, node_ids in partition_parts.items():
        for node_id in node_ids:
            town = graph.nodes[node_id].get("hdb_town")
            if town is None:
                continue
            town_district_counts[town][district_id] += 1

    if not town_district_counts:
        return 0.0

    entropies: list[float] = []
    for district_counts in town_district_counts.values():
        total = sum(district_counts.values())
        entropy = 0.0
        for count in district_counts.values():
            p = count / total
            if p > 0.0:
                entropy -= p * math.log2(p)
        entropies.append(entropy)

    return sum(entropies) / len(entropies)


def pln_area_splits(
    partition_parts: dict[int, list[int]],
    graph: nx.Graph,
) -> int:
    """Count planning areas appearing in more than one district.

    Parameters
    ----------
    partition_parts:
        Mapping of district_id → list of node IDs in that district.
    graph:
        NetworkX graph whose nodes carry a ``pln_area`` attribute.
        This attribute is always set (never None).

    Returns
    -------
    int
        Number of distinct planning areas that span more than one district.
    """
    # pln_area → set of district IDs that contain at least one node from that area
    area_districts: dict[str, set[int]] = defaultdict(set)

    for district_id, node_ids in partition_parts.items():
        for node_id in node_ids:
            pln_area = graph.nodes[node_id]["pln_area"]
            area_districts[pln_area].add(district_id)

    return sum(1 for districts in area_districts.values() if len(districts) > 1)
