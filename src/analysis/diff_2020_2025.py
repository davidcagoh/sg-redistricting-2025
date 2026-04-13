"""Compare actual 2020 and 2025 electoral plans against MCMC ensemble metrics.

Functions
---------
load_actual_assignments  -- read year-specific assignments parquet
load_ensemble_metrics    -- read metrics parquet for a given run_id
compute_percentile       -- strict less-than percentile rank
build_diff_report        -- assemble per-(year, metric) comparison records
save_diff_report         -- persist report as JSON
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

import pandas as pd

from src.analysis.config import PathsConfig

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


def build_diff_report(
    assignments_2020: pd.DataFrame,
    assignments_2025: pd.DataFrame,
    ensemble_metrics: pd.DataFrame,
) -> list[dict]:
    """Build a comparison report for the 2020 and 2025 plans vs the ensemble.

    For each (year, metric) pair the actual value is taken from the first row
    of *ensemble_metrics* whose ``run_id`` matches the plan's run_id and whose
    ``step_index`` is 0.

    Parameters
    ----------
    assignments_2020:
        DataFrame with at least a ``run_id`` column for the 2020 plan.
    assignments_2025:
        DataFrame with at least a ``run_id`` column for the 2025 plan.
    ensemble_metrics:
        Combined metrics DataFrame containing rows for both run IDs.

    Returns
    -------
    list[dict]
        One dict per (year, metric) with keys:
        ``plan_year``, ``metric``, ``actual_value``, ``percentile``, ``n_ensemble``.

    Raises
    ------
    ValueError
        If a plan's run_id is not found in *ensemble_metrics*.
    """
    plan_pairs = [(2020, assignments_2020), (2025, assignments_2025)]
    report: list[dict] = []

    for year, assignments in plan_pairs:
        run_id = assignments["run_id"].iloc[0]

        run_rows = ensemble_metrics[ensemble_metrics["run_id"] == run_id]
        if run_rows.empty:
            raise ValueError(
                f"run_id '{run_id}' (year={year}) not found in ensemble_metrics"
            )

        # Actual value: step_index == 0 for this run, first match
        step0_rows = run_rows[run_rows["step_index"] == 0]
        actual_row = step0_rows.iloc[0] if not step0_rows.empty else run_rows.iloc[0]

        ensemble_vals_all = run_rows

        for metric in _COMPARED_METRICS:
            actual_val = float(actual_row[metric])
            ensemble_col = ensemble_vals_all[metric].tolist()
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
