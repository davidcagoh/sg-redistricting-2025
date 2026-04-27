"""Build a NetworkX adjacency graph from URA subzone polygons.

This module constructs the rook-adjacency dual graph that GerryChain's MCMC
redistricting chain operates on. Two subzones are adjacent iff their shared
boundary has length > tolerance_m (eliminating point-only contacts).

Algorithm: STRtree spatial index → O(n log n) instead of O(n²).
"""
from __future__ import annotations

from typing import Any

import geopandas as gpd
import networkx as nx
from shapely.strtree import STRtree


def build_subzone_graph(
    subzones: gpd.GeoDataFrame,
    *,
    tolerance_m: float = 1.0,
) -> nx.Graph:
    """Build the rook-adjacency dual graph from subzone polygons.

    Parameters
    ----------
    subzones:
        GeoDataFrame in a projected CRS (use SVY21 / EPSG:3414, not WGS84).
        Required columns: subzone_name_norm, PLN_AREA_N, pop_total.
        Either ``_feature_id`` or ``FID`` must be present.
    tolerance_m:
        Minimum shared boundary length (metres) to count as adjacent.
        Filters out point-only touches between diagonal squares.

    Returns
    -------
    nx.Graph
        Undirected graph. Node IDs are integer row indices of the input
        GeoDataFrame (matching GerryChain's expectation).

        Node attributes:
            subzone_name_norm, pln_area, pop_total, area_m2, _feature_id

        Edge attributes:
            shared_perimeter_m
    """
    if subzones.crs is None or subzones.crs.is_geographic:
        raise ValueError(
            "subzones must be in a projected CRS (e.g. EPSG:3414 SVY21), "
            f"got: {subzones.crs}"
        )

    G: nx.Graph = nx.Graph()

    # Determine feature-id column (prefer _feature_id, fall back to FID)
    fid_col = "_feature_id" if "_feature_id" in subzones.columns else "FID"

    # Add nodes — one per GeoDataFrame row
    for idx, row in subzones.iterrows():
        G.add_node(
            idx,
            subzone_name_norm=row["subzone_name_norm"],
            pln_area=row["PLN_AREA_N"],
            pop_total=int(row["pop_total"]),
            area_m2=float(row.geometry.area),
            _feature_id=row[fid_col],
        )

    # Precompute boundaries (list preserves alignment with index list)
    indices = list(subzones.index)
    geometries = list(subzones.geometry)
    boundaries = [geom.boundary for geom in geometries]

    # STRtree built on boundaries for fast bounding-box queries
    tree = STRtree(boundaries)

    for pos_i, idx_i in enumerate(indices):
        boundary_i = boundaries[pos_i]

        # Query returns positions of candidates whose bbox intersects boundary_i's bbox
        candidate_positions = tree.query(boundary_i)

        for pos_j in candidate_positions:
            if pos_j <= pos_i:
                # Only process each pair once; skip self
                continue

            shared = boundary_i.intersection(boundaries[pos_j])
            shared_len = shared.length

            if shared_len > tolerance_m:
                idx_j = indices[pos_j]
                G.add_edge(idx_i, idx_j, shared_perimeter_m=float(shared_len))

    return G


def attach_pct_minority(
    graph: nx.Graph,
    pct_minority_lookup: dict[str, float],
    *,
    default: float = 0.0,
) -> nx.Graph:
    """Attach ``pct_minority`` to every node in *graph* (mutates in place).

    Parameters
    ----------
    graph:
        Graph produced by ``build_subzone_graph``.  Each node must have a
        ``subzone_name_norm`` attribute.
    pct_minority_lookup:
        Mapping from normalized subzone name → minority share, as returned
        by ``io_layer.load_ethnic_data()``.
    default:
        Value assigned to nodes whose name is absent from the lookup
        (e.g. non-residential subzones with no Census row).

    Returns
    -------
    nx.Graph
        The same *graph* object with ``pct_minority`` set on every node.
    """
    for node, attrs in graph.nodes(data=True):
        name = attrs.get("subzone_name_norm", "")
        graph.nodes[node]["pct_minority"] = pct_minority_lookup.get(name, default)
    return graph


def identify_islands(graph: nx.Graph) -> list[list[Any]]:
    """Return non-mainland connected components as lists of node IDs.

    The 'mainland' is defined as the largest connected component. All other
    components are returned as lists of node IDs sorted for determinism.

    Parameters
    ----------
    graph:
        Undirected NetworkX graph produced by build_subzone_graph.

    Returns
    -------
    list[list[Any]]
        Empty list if the graph is fully connected.
        Each inner list contains the node IDs of one non-mainland component.
    """
    components = list(nx.connected_components(graph))

    if len(components) <= 1:
        return []

    # Largest component = mainland
    mainland = max(components, key=len)

    return [sorted(comp) for comp in components if comp is not mainland]


def filter_for_mcmc(
    graph: nx.Graph,
    *,
    min_pop: float = float("inf"),
) -> tuple[nx.Graph, list[Any]]:
    """Remove non-mainland components from the graph.

    A component is excluded when:
    1. It belongs to a non-mainland component (per identify_islands), AND
    2. The total pop_total across its component is < min_pop.

    With the default min_pop=inf, ALL non-mainland components are excluded
    regardless of population.  This is required for MCMC: GerryChain's ReCom
    cannot form contiguous districts from isolated sub-graphs, so any non-mainland
    node (even one with non-zero population, e.g. Singapore node 317) must be
    removed before seeding.

    Pass an explicit min_pop value to preserve high-population non-mainland
    components (e.g. min_pop=1 keeps components with any residents).

    The input graph is never mutated.

    Parameters
    ----------
    graph:
        Undirected NetworkX graph produced by build_subzone_graph.
    min_pop:
        Population threshold below which a non-mainland component is removed.
        Default is ``float("inf")``, which removes all non-mainland components.

    Returns
    -------
    (filtered_graph, excluded_node_ids)
        filtered_graph is a new Graph built from graph.copy() minus excluded nodes.
        excluded_node_ids is a sorted list of removed node IDs.
    """
    islands = identify_islands(graph)

    excluded: list[Any] = []
    for component in islands:
        total_pop = sum(
            graph.nodes[n].get("pop_total", 0) for n in component
        )
        if total_pop < min_pop:
            excluded.extend(component)

    filtered = graph.copy()
    filtered.remove_nodes_from(excluded)

    return filtered, sorted(excluded)
