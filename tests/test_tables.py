"""Tests for src/analysis/reporting/tables.py.

TDD RED phase: tests written BEFORE implementation.
All tests use fake in-memory data — no real files needed.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_METRICS = ["max_abs_pop_dev", "towns_split", "pln_area_splits", "mean_pp"]


def _make_full_report() -> list[dict]:
    return [
        {"plan_year": 2020, "metric": m, "actual_value": float(i + 1), "percentile": 30.0, "n_ensemble": 10}
        for i, m in enumerate(_METRICS)
    ] + [
        {"plan_year": 2025, "metric": m, "actual_value": float(i + 2), "percentile": 70.0, "n_ensemble": 10}
        for i, m in enumerate(_METRICS)
    ]


def _make_single_year_report(year: int = 2020) -> list[dict]:
    return [
        {"plan_year": year, "metric": m, "actual_value": float(i), "percentile": 50.0, "n_ensemble": 5}
        for i, m in enumerate(_METRICS)
    ]


# ---------------------------------------------------------------------------
# build_summary_table
# ---------------------------------------------------------------------------


def test_build_summary_table_returns_dataframe() -> None:
    from src.analysis.reporting.tables import build_summary_table

    report = _make_full_report()
    df = build_summary_table(report)
    assert isinstance(df, pd.DataFrame)


def test_build_summary_table_has_required_columns() -> None:
    from src.analysis.reporting.tables import build_summary_table

    report = _make_full_report()
    df = build_summary_table(report)
    expected_cols = {"metric", "value_2020", "percentile_2020", "value_2025", "percentile_2025"}
    assert expected_cols.issubset(set(df.columns)), f"Missing columns: {expected_cols - set(df.columns)}"


def test_build_summary_table_one_row_per_metric() -> None:
    from src.analysis.reporting.tables import build_summary_table

    report = _make_full_report()
    df = build_summary_table(report)
    assert len(df) == len(_METRICS)
    assert set(df["metric"]) == set(_METRICS)


def test_build_summary_table_values_correct() -> None:
    from src.analysis.reporting.tables import build_summary_table

    report = [
        {"plan_year": 2020, "metric": "towns_split", "actual_value": 3.0, "percentile": 45.0, "n_ensemble": 10},
        {"plan_year": 2025, "metric": "towns_split", "actual_value": 5.0, "percentile": 75.0, "n_ensemble": 10},
    ]
    df = build_summary_table(report)
    row = df[df["metric"] == "towns_split"].iloc[0]
    assert row["value_2020"] == pytest.approx(3.0)
    assert row["percentile_2020"] == pytest.approx(45.0)
    assert row["value_2025"] == pytest.approx(5.0)
    assert row["percentile_2025"] == pytest.approx(75.0)


def test_build_summary_table_missing_year_fills_nan() -> None:
    from src.analysis.reporting.tables import build_summary_table
    import math

    # Only 2020 present — 2025 columns should be NaN
    report = _make_single_year_report(year=2020)
    df = build_summary_table(report)
    row = df[df["metric"] == "max_abs_pop_dev"].iloc[0]
    assert math.isnan(row["value_2025"])
    assert math.isnan(row["percentile_2025"])


def test_build_summary_table_missing_2020_fills_nan() -> None:
    from src.analysis.reporting.tables import build_summary_table
    import math

    report = _make_single_year_report(year=2025)
    df = build_summary_table(report)
    row = df[df["metric"] == "towns_split"].iloc[0]
    assert math.isnan(row["value_2020"])
    assert math.isnan(row["percentile_2020"])


def test_build_summary_table_empty_report() -> None:
    from src.analysis.reporting.tables import build_summary_table

    df = build_summary_table([])
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0


def test_build_summary_table_metric_column_dtype() -> None:
    from src.analysis.reporting.tables import build_summary_table

    report = _make_full_report()
    df = build_summary_table(report)
    assert df["metric"].dtype == object  # string column


# ---------------------------------------------------------------------------
# save_summary_table
# ---------------------------------------------------------------------------


def test_save_summary_table_returns_tuple(tmp_path: Path) -> None:
    from src.analysis.reporting.tables import build_summary_table, save_summary_table

    df = build_summary_table(_make_full_report())
    result = save_summary_table(df, tmp_path)
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_save_summary_table_csv_exists(tmp_path: Path) -> None:
    from src.analysis.reporting.tables import build_summary_table, save_summary_table

    df = build_summary_table(_make_full_report())
    csv_path, _ = save_summary_table(df, tmp_path)
    assert csv_path.exists()
    assert csv_path.name == "summary.csv"


def test_save_summary_table_md_exists(tmp_path: Path) -> None:
    from src.analysis.reporting.tables import build_summary_table, save_summary_table

    df = build_summary_table(_make_full_report())
    _, md_path = save_summary_table(df, tmp_path)
    assert md_path.exists()
    assert md_path.name == "summary.md"


def test_save_summary_table_csv_is_valid(tmp_path: Path) -> None:
    from src.analysis.reporting.tables import build_summary_table, save_summary_table

    df = build_summary_table(_make_full_report())
    csv_path, _ = save_summary_table(df, tmp_path)
    loaded = pd.read_csv(csv_path)
    assert set(loaded["metric"]) == set(_METRICS)


def test_save_summary_table_md_is_markdown_table(tmp_path: Path) -> None:
    from src.analysis.reporting.tables import build_summary_table, save_summary_table

    df = build_summary_table(_make_full_report())
    _, md_path = save_summary_table(df, tmp_path)
    content = md_path.read_text()
    # Markdown tables contain | characters
    assert "|" in content


def test_save_summary_table_creates_output_dir(tmp_path: Path) -> None:
    from src.analysis.reporting.tables import build_summary_table, save_summary_table

    nested = tmp_path / "deep" / "nested" / "output"
    df = build_summary_table(_make_full_report())
    save_summary_table(df, nested)
    assert nested.exists()


def test_save_summary_table_returns_path_objects(tmp_path: Path) -> None:
    from src.analysis.reporting.tables import build_summary_table, save_summary_table

    df = build_summary_table(_make_full_report())
    csv_path, md_path = save_summary_table(df, tmp_path)
    assert isinstance(csv_path, Path)
    assert isinstance(md_path, Path)


def test_save_summary_table_md_contains_metric_names(tmp_path: Path) -> None:
    from src.analysis.reporting.tables import build_summary_table, save_summary_table

    df = build_summary_table(_make_full_report())
    _, md_path = save_summary_table(df, tmp_path)
    content = md_path.read_text()
    for m in _METRICS:
        assert m in content, f"Metric '{m}' not found in markdown output"
