"""Reporting plots for the MCMC ensemble analysis."""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib
import matplotlib.axes
import matplotlib.pyplot as plt
import pandas as pd

_METRICS = ["max_abs_pop_dev", "towns_split", "pln_area_splits", "mean_pp"]

_YEAR_COLORS: dict[int, str] = {
    2020: "blue",
    2025: "red",
}


def plot_metric_distribution(
    ensemble_vals: Sequence[float],
    actual_vals_by_year: dict[int, float],
    metric_name: str,
    ax: matplotlib.axes.Axes,
) -> None:
    """Draw histogram of ensemble_vals on ax; add vertical lines for each year's actual value.

    Line colors: 2020=blue, 2025=red. Adds a legend.
    """
    ax.hist(list(ensemble_vals), bins="auto", alpha=0.7, label="ensemble")

    for year, val in actual_vals_by_year.items():
        color = _YEAR_COLORS.get(year, "black")
        ax.axvline(x=val, color=color, linestyle="--", linewidth=1.5, label=str(year))

    ax.set_title(metric_name)
    ax.set_xlabel(metric_name)
    ax.set_ylabel("count")
    ax.legend()


def save_all_plots(
    diff_report: list[dict],
    ensemble_metrics: pd.DataFrame,
    output_dir: Path,
) -> list[Path]:
    """For each metric in diff_report, create a figure and save to output_dir/<metric>.png.

    Returns list of saved Paths. Creates output_dir if needed.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect actual values per metric per year from diff_report
    actual_by_metric: dict[str, dict[int, float]] = {}
    for entry in diff_report:
        metric = entry["metric"]
        year = entry["plan_year"]
        val = entry["actual_value"]
        actual_by_metric.setdefault(metric, {})[year] = val

    # Determine unique metrics (preserve order, deduplicate)
    seen: set[str] = set()
    metrics: list[str] = []
    for entry in diff_report:
        m = entry["metric"]
        if m not in seen:
            metrics.append(m)
            seen.add(m)

    saved: list[Path] = []
    for metric in metrics:
        if metric not in ensemble_metrics.columns:
            continue

        ensemble_vals = ensemble_metrics[metric].dropna().tolist()
        actual_vals = actual_by_metric.get(metric, {})

        fig, ax = plt.subplots()
        plot_metric_distribution(
            ensemble_vals=ensemble_vals,
            actual_vals_by_year=actual_vals,
            metric_name=metric,
            ax=ax,
        )
        out_path = output_dir / f"{metric}.png"
        fig.savefig(out_path)
        plt.close(fig)
        saved.append(out_path)

    return saved
