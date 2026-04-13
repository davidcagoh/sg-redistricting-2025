"""Compactness metrics for electoral redistricting analysis.

All functions are pure (no side effects). Geometries are Shapely objects.
"""
from __future__ import annotations

import math

import networkx as nx
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union


def polsby_popper(geometry: BaseGeometry) -> float:
    """Compute the Polsby-Popper compactness score for a geometry.

    Formula: 4π·Area / Perimeter²

    Returns a value in [0, 1] where 1 is a perfect circle.
    Returns 0.0 for degenerate geometries (zero area or zero perimeter).

    Parameters
    ----------
    geometry:
        A Shapely geometry (Polygon or MultiPolygon).

    Returns
    -------
    float
        Polsby-Popper score in [0.0, 1.0].
    """
    area: float = geometry.area
    perimeter: float = geometry.length

    if perimeter == 0.0 or area == 0.0:
        return 0.0

    return (4.0 * math.pi * area) / (perimeter ** 2)


def district_geometries(
    parts: dict[int, list[int]],
    subzone_geoms: dict[int, BaseGeometry],
) -> dict[int, BaseGeometry]:
    """Compute the dissolved geometry for each district.

    Takes a partition mapping (district_id → list of node ids) and a
    per-node geometry mapping, returning the unary_union of all node
    geometries for each district.

    Parameters
    ----------
    parts:
        Mapping from district id to list of node ids belonging to that district.
    subzone_geoms:
        Mapping from node id to Shapely geometry.

    Returns
    -------
    dict[int, BaseGeometry]
        Mapping from district id to the dissolved geometry of that district.
    """
    return {
        district_id: unary_union([subzone_geoms[node_id] for node_id in node_ids])
        for district_id, node_ids in parts.items()
    }


def mean_polsby_popper(
    parts: dict[int, list[int]],
    subzone_geoms: dict[int, BaseGeometry],
) -> float:
    """Compute the mean Polsby-Popper score across all districts.

    Parameters
    ----------
    parts:
        Partition mapping (district_id → list of node ids).
    subzone_geoms:
        Per-node geometry mapping (node_id → Shapely geometry).

    Returns
    -------
    float
        Arithmetic mean of per-district PP scores.
    """
    geoms = district_geometries(parts, subzone_geoms)
    scores = [polsby_popper(geom) for geom in geoms.values()]
    return sum(scores) / len(scores)


def min_polsby_popper(
    parts: dict[int, list[int]],
    subzone_geoms: dict[int, BaseGeometry],
) -> float:
    """Compute the minimum Polsby-Popper score across all districts.

    Parameters
    ----------
    parts:
        Partition mapping (district_id → list of node ids).
    subzone_geoms:
        Per-node geometry mapping (node_id → Shapely geometry).

    Returns
    -------
    float
        Minimum per-district PP score.
    """
    geoms = district_geometries(parts, subzone_geoms)
    scores = [polsby_popper(geom) for geom in geoms.values()]
    return min(scores)


def cut_edges(graph: nx.Graph, assignment: dict[int, int]) -> int:
    """Count the number of edges whose endpoints belong to different districts.

    Parameters
    ----------
    graph:
        NetworkX graph where nodes correspond to subzones.
    assignment:
        Mapping from node id to district id.

    Returns
    -------
    int
        Number of edges that cross a district boundary.
    """
    return sum(
        1
        for u, v in graph.edges()
        if assignment[u] != assignment[v]
    )


def compute_compactness_metrics(
    parts: dict[int, list[int]],
    subzone_geoms: dict[int, BaseGeometry],
    graph: nx.Graph,
    assignment: dict[int, int],
) -> dict:
    """Compute a summary of compactness metrics for a redistricting plan.

    Parameters
    ----------
    parts:
        Partition mapping (district_id → list of node ids).
    subzone_geoms:
        Per-node geometry mapping (node_id → Shapely geometry).
    graph:
        NetworkX graph where nodes correspond to subzones.
    assignment:
        Mapping from node id to district id.

    Returns
    -------
    dict
        Dictionary with keys:
        - ``"mean_pp"``: mean Polsby-Popper score across districts (float)
        - ``"min_pp"``: minimum Polsby-Popper score across districts (float)
        - ``"cut_edges"``: number of edges crossing district boundaries (int)
    """
    return {
        "mean_pp": mean_polsby_popper(parts, subzone_geoms),
        "min_pp": min_polsby_popper(parts, subzone_geoms),
        "cut_edges": cut_edges(graph, assignment),
    }
