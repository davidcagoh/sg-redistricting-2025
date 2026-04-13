"""Assign subzones to electoral districts by areal overlap majority.

Algorithm
---------
1. Reproject both GeoDataFrames to a common projected CRS (EPSG:3414 SVY21)
   if they are not already in that CRS.
2. Use geopandas.overlay(how="intersection") to clip each subzone against
   every electoral district it touches.  Each row in the overlay result is one
   (subzone, ED) intersection piece with its own geometry.
3. Compute the area of each piece.
4. Group by subzone (_feature_id) and select the ED that contributes the
   largest area.
5. Left-join back to the full subzone list so subzones with zero overlap
   receive ed_name=None.

Both public functions are pure (no mutation of inputs, no disk I/O).
"""
from __future__ import annotations

import logging
from typing import Any

import geopandas as gpd
import networkx as nx
import pandas as pd

logger = logging.getLogger(__name__)

# Canonical projected CRS for Singapore spatial operations
_SVY21_EPSG = 3414

# Name of the electoral district name column we expect (primary) or fall back to
_ED_NAME_COL_PRIMARY = "ED_DESC"
_ED_NAME_COL_FALLBACK = "Name"

# Column name used internally to tag the winning ED
_INTERNAL_ED_COL = "_ed_name_internal"


def _resolve_ed_name_col(electoral: gpd.GeoDataFrame) -> str:
    """Return the name of the ED label column present in *electoral*.

    Raises
    ------
    ValueError
        If neither expected column is present.
    """
    if _ED_NAME_COL_PRIMARY in electoral.columns:
        return _ED_NAME_COL_PRIMARY
    if _ED_NAME_COL_FALLBACK in electoral.columns:
        return _ED_NAME_COL_FALLBACK
    raise ValueError(
        f"Electoral GeoDataFrame has neither '{_ED_NAME_COL_PRIMARY}' nor "
        f"'{_ED_NAME_COL_FALLBACK}' column. Available columns: {list(electoral.columns)}"
    )


def _ensure_projected(gdf: gpd.GeoDataFrame, *, label: str) -> gpd.GeoDataFrame:
    """Return *gdf* reprojected to EPSG:3414 if not already there.

    Never mutates the input.
    """
    if gdf.crs is None:
        raise ValueError(f"{label} GeoDataFrame has no CRS set.")
    if gdf.crs.to_epsg() != _SVY21_EPSG:
        logger.debug("Reprojecting %s from %s to EPSG:%d", label, gdf.crs, _SVY21_EPSG)
        return gdf.to_crs(epsg=_SVY21_EPSG)
    return gdf.copy()


def assign_subzones_to_eds(
    subzones: gpd.GeoDataFrame,
    electoral: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """Assign each subzone to an electoral district by areal overlap majority.

    For each subzone, the electoral district with the greatest intersection area
    is selected.  Subzones with no intersection with any electoral district
    receive ``ed_name=None``.

    Parameters
    ----------
    subzones:
        GeoDataFrame of subzone polygons.  Required columns:
        ``_feature_id``, ``subzone_name_norm``.
        Must be in a projected CRS (preferably EPSG:3414); reprojected if not.
    electoral:
        GeoDataFrame of electoral district polygons.
        Must contain ``ED_DESC`` or ``Name`` column.
        Must be in a projected CRS; reprojected if not.

    Returns
    -------
    pd.DataFrame
        One row per subzone with columns:
        ``_feature_id``, ``subzone_name_norm``, ``ed_name``,
        ``overlap_area_m2``, ``assignment_method``.
        ``assignment_method`` is ``"areal_majority"`` for all matched rows.

    Notes
    -----
    Both inputs must be in the same projected CRS (EPSG:3414 is recommended).
    The function never mutates the caller's GeoDataFrames.
    """
    # -- Guard: empty input --------------------------------------------------
    required_cols = {"_feature_id", "subzone_name_norm"}
    missing = required_cols - set(subzones.columns)
    if missing:
        raise ValueError(f"subzones GeoDataFrame missing required columns: {missing}")

    ed_col = _resolve_ed_name_col(electoral)

    # Return early if no subzones to process
    if len(subzones) == 0:
        return pd.DataFrame(
            columns=["_feature_id", "subzone_name_norm", "ed_name", "overlap_area_m2", "assignment_method"]
        )

    # -- Ensure consistent projected CRS ------------------------------------
    sz = _ensure_projected(subzones, label="subzones")
    el = _ensure_projected(electoral, label="electoral")

    # -- Intersection overlay ------------------------------------------------
    # overlay returns one row per (subzone, ED) intersection piece.
    # Column suffixes: subzone columns keep their names; ED columns get "_2"
    # if they clash.  We rename the ED name column before overlaying to avoid
    # ambiguity.
    el_renamed = el[[ed_col, "geometry"]].rename(columns={ed_col: _INTERNAL_ED_COL})

    # Preserve only the columns we need from sz to keep the overlay result lean
    sz_slim = sz[["_feature_id", "subzone_name_norm", "geometry"]].copy()

    if len(el_renamed) == 0:
        # No electoral districts → every subzone gets None
        base = sz_slim[["_feature_id", "subzone_name_norm"]].copy()
        base["ed_name"] = None
        base["overlap_area_m2"] = float("nan")
        base["assignment_method"] = "areal_majority"
        return pd.DataFrame(base)

    try:
        overlay = gpd.overlay(sz_slim, el_renamed, how="intersection", keep_geom_type=False)
    except Exception as exc:  # pragma: no cover — defensive
        logger.error("gpd.overlay failed: %s", exc)
        raise

    if len(overlay) == 0:
        # Geometries present but no intersections at all
        base = sz_slim[["_feature_id", "subzone_name_norm"]].copy()
        base["ed_name"] = None
        base["overlap_area_m2"] = float("nan")
        base["assignment_method"] = "areal_majority"
        return pd.DataFrame(base)

    # -- Compute intersection areas ------------------------------------------
    overlay = overlay.copy()
    overlay["_piece_area"] = overlay.geometry.area

    # -- Find dominant ED per subzone ----------------------------------------
    # For each _feature_id pick the row with the maximum piece area.
    idx_max = overlay.groupby("_feature_id")["_piece_area"].idxmax()
    dominant = overlay.loc[idx_max, ["_feature_id", "_piece_area", _INTERNAL_ED_COL]].copy()
    dominant = dominant.rename(
        columns={"_piece_area": "overlap_area_m2", _INTERNAL_ED_COL: "ed_name"}
    )

    # -- Left-join back to all subzones so orphans appear with None ----------
    sz_meta = sz_slim[["_feature_id", "subzone_name_norm"]].copy()
    merged = sz_meta.merge(dominant, on="_feature_id", how="left")

    # Fill assignment_method column
    merged["assignment_method"] = "areal_majority"

    # Ensure ed_name column contains Python None (not NaN) for missing rows
    # so callers can use `is None` checks.
    merged["ed_name"] = merged["ed_name"].where(merged["ed_name"].notna(), other=None)

    # Return as plain DataFrame (drop any geometry if somehow present)
    result = pd.DataFrame(
        merged[["_feature_id", "subzone_name_norm", "ed_name", "overlap_area_m2", "assignment_method"]]
    )
    return result


def assign_actual_plan(
    year: int,
    graph: nx.Graph,
    subzones_svy21: gpd.GeoDataFrame,
    electoral: gpd.GeoDataFrame,
) -> dict[int, str | None]:
    """Assign each graph node to an electoral district name.

    Uses :func:`assign_subzones_to_eds` internally.  Graph node IDs are
    integer row indices of *subzones_svy21*, matching the convention from
    :func:`~src.analysis.graph_build.build_subzone_graph`.

    Parameters
    ----------
    year:
        Election year (2020 or 2025) — used for logging only.
    graph:
        NetworkX graph whose node IDs are integer row indices of *subzones_svy21*.
    subzones_svy21:
        GeoDataFrame of subzone polygons in EPSG:3414.
        Required columns: ``_feature_id``, ``subzone_name_norm``.
    electoral:
        GeoDataFrame of electoral district polygons.

    Returns
    -------
    dict[int, str | None]
        Mapping of graph node ID → electoral district name.
        Nodes with no electoral overlap receive ``None``.
    """
    logger.info(
        "assign_actual_plan: year=%d, nodes=%d, electoral=%d",
        year,
        graph.number_of_nodes(),
        len(electoral),
    )

    if graph.number_of_nodes() == 0:
        return {}

    # Run areal-majority assignment
    assignment_df = assign_subzones_to_eds(subzones_svy21, electoral)

    # Build a mapping from _feature_id → ed_name
    fid_to_ed: dict[Any, str | None] = dict(
        zip(assignment_df["_feature_id"], assignment_df["ed_name"])
    )

    # Build node_id → ed_name using graph node attributes
    # Each graph node stores _feature_id as an attribute (set by build_subzone_graph).
    result: dict[int, str | None] = {}
    for node_id, attrs in graph.nodes(data=True):
        fid = attrs.get("_feature_id")
        ed_name = fid_to_ed.get(fid)  # Returns None if fid not in mapping
        result[node_id] = ed_name

    n_matched = sum(1 for v in result.values() if v is not None)
    n_unmatched = len(result) - n_matched
    logger.info(
        "assign_actual_plan year=%d: %d/%d nodes matched, %d unmatched",
        year,
        n_matched,
        len(result),
        n_unmatched,
    )

    return result
