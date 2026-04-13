"""communities.py — attach HDB town labels to subzone graph nodes.

Pipeline step: after building the subzone adjacency graph, enrich each
node with the majority HDB contract town derived from building-level data.
"""
from __future__ import annotations

import logging

import geopandas as gpd
import networkx as nx
import pandas as pd

logger = logging.getLogger(__name__)

_JOIN_RATE_THRESHOLD = 0.80
_PURITY_THRESHOLD = 0.70


# ---------------------------------------------------------------------------
# Internal helpers (each < 50 lines)
# ---------------------------------------------------------------------------


def _normalize_join_key(blk: pd.Series, street: pd.Series) -> pd.Series:
    """Produce a single join key from block number and street, uppercased."""
    return blk.str.strip().str.upper() + "|" + street.str.strip().str.upper()


def _join_buildings_to_properties(
    buildings: gpd.GeoDataFrame,
    properties: pd.DataFrame,
) -> gpd.GeoDataFrame:
    """Merge buildings with property rows to attach ``bldg_contract_town``.

    Prefers a compound ``blk_no + street`` join when buildings have a ``street``
    column.  Falls back to ``blk_no``-only matching (taking the modal town per
    block) when the buildings source lacks a street name field — this covers the
    ``HDBExistingBuilding.geojson`` dataset which stores a street code rather than
    a human-readable street name.

    Warns via logging if the join rate falls below 80 %.
    Returns a GeoDataFrame that carries ``bldg_contract_town``.
    """
    bld = buildings.copy()

    if "street" in bld.columns:
        # Compound join on blk_no + street (exact match)
        bld["_join_key"] = _normalize_join_key(bld["blk_no"], bld["street"])
        prop = properties.copy()
        prop["_join_key"] = _normalize_join_key(prop["blk_no"], prop["street"])
        prop_slim = prop[["_join_key", "bldg_contract_town"]].drop_duplicates("_join_key")
        merged = bld.merge(prop_slim, on="_join_key", how="left")
    else:
        # Fallback: join on blk_no only; aggregate by taking modal town
        bld["_blk_key"] = bld["blk_no"].astype(str).str.strip().str.upper()
        prop = properties.copy()
        prop["_blk_key"] = prop["blk_no"].astype(str).str.strip().str.upper()
        modal_town = (
            prop.groupby("_blk_key")["bldg_contract_town"]
            .agg(lambda s: s.mode().iloc[0] if len(s) > 0 else None)
            .reset_index()
            .rename(columns={"bldg_contract_town": "bldg_contract_town"})
        )
        merged = bld.merge(modal_town, on="_blk_key", how="left")

    matched = merged["bldg_contract_town"].notna().sum()
    total = len(merged)
    rate = matched / total if total > 0 else 1.0

    if rate < _JOIN_RATE_THRESHOLD:
        logger.warning(
            "HDB building-property join rate is %.1f%% (threshold %.0f%%). "
            "Check blk_no / street normalisation.",
            rate * 100,
            _JOIN_RATE_THRESHOLD * 100,
        )

    return gpd.GeoDataFrame(merged, geometry="geometry", crs=buildings.crs)


def _reproject_buildings(
    buildings: gpd.GeoDataFrame,
    target_crs: str = "EPSG:3414",
) -> gpd.GeoDataFrame:
    """Return buildings in *target_crs*, reprojecting only when necessary."""
    if buildings.crs is None or buildings.crs.to_epsg() != 3414:
        return buildings.to_crs(target_crs)
    return buildings


def _spatial_join_to_subzones(
    buildings: gpd.GeoDataFrame,
    subzones: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """Spatial-join building centroids into subzone polygons (within predicate).

    Returns the joined frame with an ``index_right`` column holding the
    integer subzone row index.
    """
    centroids = buildings.copy()
    centroids["geometry"] = centroids.geometry.centroid

    joined = gpd.sjoin(centroids, subzones[["geometry"]], predicate="within", how="left")
    return joined


def _compute_town_per_node(
    joined: gpd.GeoDataFrame,
    node_ids: list[int],
) -> dict[int, tuple[str | None, float]]:
    """Return {node_id: (majority_town, purity)} for every node.

    Nodes absent from the spatial join get (None, 0.0).
    Warns when any purity < 0.7.
    """
    results: dict[int, tuple[str | None, float]] = {n: (None, 0.0) for n in node_ids}

    valid = joined.dropna(subset=["bldg_contract_town", "index_right"])
    valid = valid.copy()
    valid["index_right"] = valid["index_right"].astype(int)

    for node_id, group in valid.groupby("index_right"):
        if node_id not in results:
            continue
        counts = group["bldg_contract_town"].value_counts()
        majority_town = counts.index[0]
        majority_count = counts.iloc[0]
        purity = majority_count / len(group)
        results[node_id] = (majority_town, purity)

        if purity < _PURITY_THRESHOLD:
            logger.warning(
                "Subzone node %d has HDB town purity %.2f (< %.2f). "
                "Majority town: %s.",
                node_id,
                purity,
                _PURITY_THRESHOLD,
                majority_town,
            )

    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def attach_hdb_towns(
    graph: nx.Graph,
    subzones_svy21: gpd.GeoDataFrame,
    hdb_buildings: gpd.GeoDataFrame,
    hdb_properties: pd.DataFrame,
) -> nx.Graph:
    """Attach majority HDB contract town labels to every node in *graph*.

    Parameters
    ----------
    graph:
        Subzone adjacency graph.  Node IDs are integer row indices into
        *subzones_svy21*.  Never mutated.
    subzones_svy21:
        GeoDataFrame in EPSG:3414 with columns subzone_name_norm,
        PLN_AREA_N, pop_total, _feature_id, geometry.
    hdb_buildings:
        Point GeoDataFrame with columns blk_no, street.  May be in any CRS.
    hdb_properties:
        DataFrame with columns blk_no, street, bldg_contract_town.

    Returns
    -------
    nx.Graph
        A copy of *graph* where every node gains two attributes:
        ``hdb_town`` (str | None) and ``hdb_town_purity`` (float 0–1).
    """
    result = graph.copy()

    buildings = _reproject_buildings(hdb_buildings)
    enriched = _join_buildings_to_properties(buildings, hdb_properties)
    joined = _spatial_join_to_subzones(enriched, subzones_svy21)

    node_ids = list(result.nodes())
    town_map = _compute_town_per_node(joined, node_ids)

    for node_id, (town, purity) in town_map.items():
        result.nodes[node_id]["hdb_town"] = town
        result.nodes[node_id]["hdb_town_purity"] = purity

    return result
