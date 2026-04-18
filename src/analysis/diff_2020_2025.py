"""Compare actual 2020 and 2025 electoral plans against MCMC ensemble metrics.

Functions
---------
load_actual_assignments      -- read year-specific assignments parquet
load_actual_metrics          -- read year-specific pre-computed metrics JSON
load_ensemble_metrics        -- read metrics parquet for a given run_id
compute_percentile           -- strict less-than percentile rank
compute_actual_plan_metrics  -- compute redistricting metrics for an actual plan
build_diff_report            -- assemble per-(year, metric) comparison records
save_diff_report             -- persist report as JSON
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

import networkx as nx
import pandas as pd
from shapely.geometry.base import BaseGeometry

from src.analysis.config import PathsConfig
from src.analysis.metrics.registry import compute_all

# Metrics compared across years
_COMPARED_METRICS: tuple[str, ...] = (
    "max_abs_pop_dev",
    "towns_split",
    "pln_area_splits",
    "mean_pp",
)


def load_actual_assignments(year: int, paths: PathsConfig) -> pd.DataFrame:
    """Load assignments parquet for *year* from ``output/actual_assignments/<year>.parquet``.

    Raises
    ------
    FileNotFoundError
        If the parquet file does not exist.
    """
    path = paths.output_dir / "actual_assignments" / f"{year}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Actual assignments not found: {path}")
    return pd.read_parquet(path)


def load_actual_metrics(year: int, paths: PathsConfig) -> dict[str, float]:
    """Load pre-computed metrics JSON for *year*.

    Written by the ``assign-actual`` subcommand alongside the assignments parquet.

    Raises
    ------
    FileNotFoundError
        If the metrics file does not exist.
    """
    path = paths.output_dir / "actual_assignments" / f"{year}_metrics.json"
    if not path.exists():
        raise FileNotFoundError(f"Actual metrics not found: {path}")
    return json.loads(path.read_text())


def load_ensemble_metrics(run_id: str, paths: PathsConfig) -> pd.DataFrame:
    """Load ``metrics.parquet`` for the given *run_id*.

    Raises
    ------
    FileNotFoundError
        If the parquet file does not exist.
    """
    path = paths.ensemble_dir(run_id) / "metrics.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Ensemble metrics not found: {path}")
    return pd.read_parquet(path)


def compute_percentile(actual_val: float, ensemble_vals: Sequence[float]) -> float:
    """Return the strict less-than percentile rank of *actual_val* in *ensemble_vals*.

    ``percentile = 100 * (number of ensemble values strictly less than actual_val)
                       / len(ensemble_vals)``

    Raises
    ------
    ValueError
        If *ensemble_vals* is empty.
    """
    vals = list(ensemble_vals)
    if not vals:
        raise ValueError("ensemble_vals must not be empty")
    n_less = sum(1 for v in vals if v < actual_val)
    return 100.0 * n_less / len(vals)


def compute_actual_plan_metrics(
    assignment_str: dict[int, str | None],
    graph: nx.Graph,
    subzone_geoms: dict[Any, BaseGeometry],
) -> dict[str, float]:
    """Compute redistricting metrics for an actual electoral plan.

    Parameters
    ----------
    assignment_str:
        Mapping of graph node_id → electoral district name (or None for unassigned).
    graph:
        Subzone graph with ``pop_total``, ``hdb_town``, ``pln_area`` node attrs.
    subzone_geoms:
        Mapping of node_id → Shapely geometry.

    Returns
    -------
    dict[str, float]
        Same keys as ``compute_all``: ``max_abs_pop_dev``, ``pop_range``,
        ``ideal_pop``, ``mean_pp``, ``min_pp``, ``cut_edges``,
        ``towns_split``, ``pln_area_splits``, ``town_split_entropy``.
    """
    # Drop nodes with no electoral assignment
    assigned = {node: ed for node, ed in assignment_str.items() if ed is not None}

    # Map string district names to stable integer IDs (sorted for determinism)
    unique_eds = sorted(set(assigned.values()))
    ed_to_int: dict[str, int] = {ed: i for i, ed in enumerate(unique_eds)}

    assignment_int: dict[int, int] = {node: ed_to_int[ed] for node, ed in assigned.items()}

    partition_parts: dict[int, list[int]] = {}
    for node, dist in assignment_int.items():
        partition_parts.setdefault(dist, []).append(node)

    # Restrict graph to assigned nodes only (drop unassigned islands)
    subgraph = graph.subgraph(assignment_int.keys())

    return compute_all(partition_parts, subzone_geoms, subgraph, assignment_int)


def build_diff_report(
    actual_metrics_2020: dict[str, float],
    actual_metrics_2025: dict[str, float],
    ensemble_metrics: pd.DataFrame,
) -> list[dict]:
    """Build a comparison report for the 2020 and 2025 plans vs the ensemble.

    Parameters
    ----------
    actual_metrics_2020:
        Pre-computed metric values for the 2020 electoral plan.
    actual_metrics_2025:
        Pre-computed metric values for the 2025 electoral plan.
    ensemble_metrics:
        MCMC ensemble metrics DataFrame (all steps, all runs combined).

    Returns
    -------
    list[dict]
        One dict per (year, metric) with keys:
        ``plan_year``, ``metric``, ``actual_value``, ``percentile``, ``n_ensemble``.
    """
    plan_pairs = [(2020, actual_metrics_2020), (2025, actual_metrics_2025)]
    report: list[dict] = []

    for year, actual_metrics in plan_pairs:
        for metric in _COMPARED_METRICS:
            actual_val = float(actual_metrics[metric])
            ensemble_col = ensemble_metrics[metric].tolist()
            pct = compute_percentile(actual_val, ensemble_col)
            report.append(
                {
                    "plan_year": year,
                    "metric": metric,
                    "actual_value": actual_val,
                    "percentile": pct,
                    "n_ensemble": len(ensemble_col),
                }
            )

    return report


def save_diff_report(report: list[dict], output_dir: Path) -> Path:
    """Write *report* as JSON to ``output_dir/diff_report.json``.

    Creates *output_dir* (and parents) if needed.

    Returns
    -------
    Path
        The path to the written file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "diff_report.json"
    out_path.write_text(json.dumps(report, indent=2) + "\n")
    return out_path
