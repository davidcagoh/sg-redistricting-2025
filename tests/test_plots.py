"""Tests for src/analysis/reporting/plots.py.

TDD RED phase: tests written BEFORE implementation.
All tests use fake in-memory data — no real files needed.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_METRICS = ["max_abs_pop_dev", "towns_split", "pln_area_splits", "mean_pp"]

def _make_diff_report() -> list[dict]:
    return [
        {"plan_year": 2020, "metric": m, "actual_value": float(i + 1), "percentile": 40.0, "n_ensemble": 10}
        for i, m in enumerate(_METRICS)
    ] + [
        {"plan_year": 2025, "metric": m, "actual_value": float(i + 2), "percentile": 60.0, "n_ensemble": 10}
        for i, m in enumerate(_METRICS)
    ]


def _make_ensemble_metrics() -> pd.DataFrame:
    rows = []
    for i in range(10):
        row = {"run_id": "run-2020", "step_index": i}
        for m in _METRICS:
            row[m] = float(i) * 0.1
        rows.append(row)
    for i in range(10):
        row = {"run_id": "run-2025", "step_index": i}
        for m in _METRICS:
            row[m] = float(i) * 0.15
        rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# plot_metric_distribution
# ---------------------------------------------------------------------------


def test_plot_metric_distribution_runs_without_error() -> None:
    from src.analysis.reporting.plots import plot_metric_distribution

    fig, ax = plt.subplots()
    plot_metric_distribution(
        ensemble_vals=[1.0, 2.0, 3.0, 4.0, 5.0],
        actual_vals_by_year={2020: 2.5, 2025: 4.0},
        metric_name="max_abs_pop_dev",
        ax=ax,
    )
    plt.close(fig)


def test_plot_metric_distribution_adds_vertical_lines() -> None:
    from src.analysis.reporting.plots import plot_metric_distribution

    fig, ax = plt.subplots()
    plot_metric_distribution(
        ensemble_vals=[1.0, 2.0, 3.0],
        actual_vals_by_year={2020: 1.5, 2025: 2.5},
        metric_name="towns_split",
        ax=ax,
    )
    # Vertical lines appear as Axvline (Line2D with xdata == [x, x])
    vlines = [line for line in ax.get_lines() if len(set(line.get_xdata())) == 1]
    assert len(vlines) == 2, f"Expected 2 vertical lines, got {len(vlines)}"
    plt.close(fig)


def test_plot_metric_distribution_line_colors() -> None:
    from src.analysis.reporting.plots import plot_metric_distribution

    fig, ax = plt.subplots()
    plot_metric_distribution(
        ensemble_vals=[1.0, 2.0, 3.0],
        actual_vals_by_year={2020: 1.0, 2025: 3.0},
        metric_name="mean_pp",
        ax=ax,
    )
    vlines = [line for line in ax.get_lines() if len(set(line.get_xdata())) == 1]
    colors = {matplotlib.colors.to_hex(line.get_color()) for line in vlines}
    assert matplotlib.colors.to_hex("blue") in colors
    assert matplotlib.colors.to_hex("red") in colors
    plt.close(fig)


def test_plot_metric_distribution_has_legend() -> None:
    from src.analysis.reporting.plots import plot_metric_distribution

    fig, ax = plt.subplots()
    plot_metric_distribution(
        ensemble_vals=[1.0, 2.0, 3.0],
        actual_vals_by_year={2020: 1.0, 2025: 3.0},
        metric_name="pln_area_splits",
        ax=ax,
    )
    assert ax.get_legend() is not None
    plt.close(fig)


def test_plot_metric_distribution_single_year() -> None:
    """Works with only one year in actual_vals_by_year."""
    from src.analysis.reporting.plots import plot_metric_distribution

    fig, ax = plt.subplots()
    plot_metric_distribution(
        ensemble_vals=[0.1, 0.2, 0.3],
        actual_vals_by_year={2025: 0.25},
        metric_name="max_abs_pop_dev",
        ax=ax,
    )
    vlines = [line for line in ax.get_lines() if len(set(line.get_xdata())) == 1]
    assert len(vlines) == 1
    plt.close(fig)


def test_plot_metric_distribution_histogram_drawn() -> None:
    from src.analysis.reporting.plots import plot_metric_distribution

    fig, ax = plt.subplots()
    plot_metric_distribution(
        ensemble_vals=[1.0, 2.0, 3.0, 4.0, 5.0],
        actual_vals_by_year={2020: 3.0},
        metric_name="mean_pp",
        ax=ax,
    )
    # Histogram produces patches (bars)
    assert len(ax.patches) > 0
    plt.close(fig)


# ---------------------------------------------------------------------------
# save_all_plots
# ---------------------------------------------------------------------------


def test_save_all_plots_returns_list_of_paths(tmp_path: Path) -> None:
    from src.analysis.reporting.plots import save_all_plots

    diff_report = _make_diff_report()
    ensemble_metrics = _make_ensemble_metrics()
    paths = save_all_plots(diff_report, ensemble_metrics, tmp_path)
    assert isinstance(paths, list)
    assert len(paths) == len(_METRICS)


def test_save_all_plots_files_exist(tmp_path: Path) -> None:
    from src.analysis.reporting.plots import save_all_plots

    diff_report = _make_diff_report()
    ensemble_metrics = _make_ensemble_metrics()
    paths = save_all_plots(diff_report, ensemble_metrics, tmp_path)
    for p in paths:
        assert p.exists(), f"Expected file {p} to exist"


def test_save_all_plots_png_extension(tmp_path: Path) -> None:
    from src.analysis.reporting.plots import save_all_plots

    diff_report = _make_diff_report()
    ensemble_metrics = _make_ensemble_metrics()
    paths = save_all_plots(diff_report, ensemble_metrics, tmp_path)
    for p in paths:
        assert p.suffix == ".png", f"Expected .png, got {p.suffix}"


def test_save_all_plots_metric_names_in_filenames(tmp_path: Path) -> None:
    from src.analysis.reporting.plots import save_all_plots

    diff_report = _make_diff_report()
    ensemble_metrics = _make_ensemble_metrics()
    paths = save_all_plots(diff_report, ensemble_metrics, tmp_path)
    stems = {p.stem for p in paths}
    assert stems == set(_METRICS)


def test_save_all_plots_creates_output_dir(tmp_path: Path) -> None:
    from src.analysis.reporting.plots import save_all_plots

    out = tmp_path / "nested" / "plots"
    diff_report = _make_diff_report()
    ensemble_metrics = _make_ensemble_metrics()
    save_all_plots(diff_report, ensemble_metrics, out)
    assert out.exists()


def test_save_all_plots_returns_path_objects(tmp_path: Path) -> None:
    from src.analysis.reporting.plots import save_all_plots

    diff_report = _make_diff_report()
    ensemble_metrics = _make_ensemble_metrics()
    paths = save_all_plots(diff_report, ensemble_metrics, tmp_path)
    for p in paths:
        assert isinstance(p, Path)
