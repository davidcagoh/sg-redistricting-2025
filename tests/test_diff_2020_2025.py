"""Tests for src/analysis/diff_2020_2025.py.

TDD RED phase: tests written BEFORE implementation.
All tests use tmp_path and in-memory DataFrames written to fake Parquet files.
No real data is required.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.analysis.config import PathsConfig


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_paths(tmp_path: Path) -> PathsConfig:
    processed = tmp_path / "processed"
    raw = tmp_path / "raw"
    output = tmp_path / "output"
    for d in (processed, raw, output):
        d.mkdir(parents=True, exist_ok=True)
    return PathsConfig(processed_dir=processed, raw_dir=raw, output_dir=output)


def _write_actual_assignments(paths: PathsConfig, year: int, run_id: str) -> None:
    """Write a minimal assignments parquet for the given year."""
    dst = paths.output_dir / "actual_assignments"
    dst.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(
        {
            "run_id": [run_id] * 3,
            "step_index": [0, 0, 0],
            "node_id": [1, 2, 3],
            "district_id": [0, 0, 1],
        }
    )
    df.to_parquet(dst / f"{year}.parquet", index=False)


def _write_ensemble_metrics(paths: PathsConfig, run_id: str, rows: list[dict]) -> None:
    """Write a metrics.parquet under the ensemble dir for run_id."""
    edir = paths.ensemble_dir(run_id)
    edir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(edir / "metrics.parquet", index=False)


# ---------------------------------------------------------------------------
# load_actual_assignments
# ---------------------------------------------------------------------------


def test_load_actual_assignments_returns_dataframe(tmp_path: Path) -> None:
    from src.analysis.diff_2020_2025 import load_actual_assignments

    paths = _make_paths(tmp_path)
    _write_actual_assignments(paths, 2020, "run-abc")
    df = load_actual_assignments(2020, paths)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3


def test_load_actual_assignments_columns(tmp_path: Path) -> None:
    from src.analysis.diff_2020_2025 import load_actual_assignments

    paths = _make_paths(tmp_path)
    _write_actual_assignments(paths, 2020, "run-abc")
    df = load_actual_assignments(2020, paths)
    assert "run_id" in df.columns
    assert "node_id" in df.columns


def test_load_actual_assignments_missing_raises(tmp_path: Path) -> None:
    from src.analysis.diff_2020_2025 import load_actual_assignments

    paths = _make_paths(tmp_path)
    with pytest.raises(FileNotFoundError):
        load_actual_assignments(2020, paths)


def test_load_actual_assignments_year_2025(tmp_path: Path) -> None:
    from src.analysis.diff_2020_2025 import load_actual_assignments

    paths = _make_paths(tmp_path)
    _write_actual_assignments(paths, 2025, "run-xyz")
    df = load_actual_assignments(2025, paths)
    assert df["run_id"].iloc[0] == "run-xyz"


# ---------------------------------------------------------------------------
# load_ensemble_metrics
# ---------------------------------------------------------------------------


def test_load_ensemble_metrics_returns_dataframe(tmp_path: Path) -> None:
    from src.analysis.diff_2020_2025 import load_ensemble_metrics

    paths = _make_paths(tmp_path)
    rows = [
        {"run_id": "run-abc", "step_index": i, "max_abs_pop_dev": 0.05}
        for i in range(5)
    ]
    _write_ensemble_metrics(paths, "run-abc", rows)
    df = load_ensemble_metrics("run-abc", paths)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 5


def test_load_ensemble_metrics_missing_raises(tmp_path: Path) -> None:
    from src.analysis.diff_2020_2025 import load_ensemble_metrics

    paths = _make_paths(tmp_path)
    with pytest.raises(FileNotFoundError):
        load_ensemble_metrics("nonexistent-run", paths)


# ---------------------------------------------------------------------------
# compute_percentile
# ---------------------------------------------------------------------------


def test_compute_percentile_median(tmp_path: Path) -> None:
    from src.analysis.diff_2020_2025 import compute_percentile

    # actual_val = 5, ensemble = [1..10] → 4 values < 5 → 40th percentile
    result = compute_percentile(5.0, [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
    assert result == pytest.approx(40.0)


def test_compute_percentile_min(tmp_path: Path) -> None:
    from src.analysis.diff_2020_2025 import compute_percentile

    result = compute_percentile(0.0, [1.0, 2.0, 3.0])
    assert result == pytest.approx(0.0)


def test_compute_percentile_max(tmp_path: Path) -> None:
    from src.analysis.diff_2020_2025 import compute_percentile

    result = compute_percentile(10.0, [1.0, 2.0, 3.0])
    assert result == pytest.approx(100.0)


def test_compute_percentile_empty_raises(tmp_path: Path) -> None:
    from src.analysis.diff_2020_2025 import compute_percentile

    with pytest.raises(ValueError):
        compute_percentile(1.0, [])


def test_compute_percentile_returns_float(tmp_path: Path) -> None:
    from src.analysis.diff_2020_2025 import compute_percentile

    result = compute_percentile(2.0, [1.0, 3.0])
    assert isinstance(result, float)


# ---------------------------------------------------------------------------
# build_diff_report
# ---------------------------------------------------------------------------

_METRICS = ["max_abs_pop_dev", "towns_split", "pln_area_splits", "mean_pp"]


def _make_assignments_df(run_id: str) -> pd.DataFrame:
    return pd.DataFrame(
        {"run_id": [run_id] * 2, "step_index": [0, 0], "node_id": [1, 2], "district_id": [0, 1]}
    )


def _make_ensemble_df(run_id: str, n: int = 10) -> pd.DataFrame:
    rows = []
    for i in range(n):
        row = {"run_id": run_id, "step_index": i}
        for m in _METRICS:
            row[m] = float(i)
        rows.append(row)
    return pd.DataFrame(rows)


def test_build_diff_report_structure(tmp_path: Path) -> None:
    from src.analysis.diff_2020_2025 import build_diff_report

    a2020 = _make_assignments_df("run-2020")
    a2025 = _make_assignments_df("run-2025")
    ens = pd.concat([_make_ensemble_df("run-2020"), _make_ensemble_df("run-2025")])

    report = build_diff_report(a2020, a2025, ens)

    assert isinstance(report, list)
    # 2 years × 4 metrics = 8 entries
    assert len(report) == 8


def test_build_diff_report_keys(tmp_path: Path) -> None:
    from src.analysis.diff_2020_2025 import build_diff_report

    a2020 = _make_assignments_df("run-2020")
    a2025 = _make_assignments_df("run-2025")
    ens = pd.concat([_make_ensemble_df("run-2020"), _make_ensemble_df("run-2025")])

    report = build_diff_report(a2020, a2025, ens)
    entry = report[0]

    for key in ("plan_year", "metric", "actual_value", "percentile", "n_ensemble"):
        assert key in entry, f"Missing key: {key}"


def test_build_diff_report_years(tmp_path: Path) -> None:
    from src.analysis.diff_2020_2025 import build_diff_report

    a2020 = _make_assignments_df("run-2020")
    a2025 = _make_assignments_df("run-2025")
    ens = pd.concat([_make_ensemble_df("run-2020"), _make_ensemble_df("run-2025")])

    report = build_diff_report(a2020, a2025, ens)
    years = {e["plan_year"] for e in report}
    assert years == {2020, 2025}


def test_build_diff_report_metrics_covered(tmp_path: Path) -> None:
    from src.analysis.diff_2020_2025 import build_diff_report

    a2020 = _make_assignments_df("run-2020")
    a2025 = _make_assignments_df("run-2025")
    ens = pd.concat([_make_ensemble_df("run-2020"), _make_ensemble_df("run-2025")])

    report = build_diff_report(a2020, a2025, ens)
    metrics = {e["metric"] for e in report}
    assert metrics == set(_METRICS)


def test_build_diff_report_n_ensemble(tmp_path: Path) -> None:
    from src.analysis.diff_2020_2025 import build_diff_report

    a2020 = _make_assignments_df("run-2020")
    a2025 = _make_assignments_df("run-2025")
    ens = pd.concat([_make_ensemble_df("run-2020", n=7), _make_ensemble_df("run-2025", n=7)])

    report = build_diff_report(a2020, a2025, ens)
    for entry in report:
        assert entry["n_ensemble"] == 7


def test_build_diff_report_unknown_run_id_raises(tmp_path: Path) -> None:
    from src.analysis.diff_2020_2025 import build_diff_report

    a2020 = _make_assignments_df("run-missing")
    a2025 = _make_assignments_df("run-2025")
    ens = _make_ensemble_df("run-2025")  # run-missing NOT in ensemble

    with pytest.raises(ValueError):
        build_diff_report(a2020, a2025, ens)


def test_build_diff_report_actual_value_is_first_step(tmp_path: Path) -> None:
    """Actual value for the plan year comes from step 0 of that run_id in ensemble."""
    from src.analysis.diff_2020_2025 import build_diff_report

    a2020 = _make_assignments_df("run-2020")
    a2025 = _make_assignments_df("run-2025")

    # step 0 has max_abs_pop_dev=0.0 for run-2020
    ens = pd.concat([_make_ensemble_df("run-2020"), _make_ensemble_df("run-2025")])
    report = build_diff_report(a2020, a2025, ens)

    entry = next(e for e in report if e["plan_year"] == 2020 and e["metric"] == "max_abs_pop_dev")
    assert entry["actual_value"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# save_diff_report
# ---------------------------------------------------------------------------


def test_save_diff_report_creates_file(tmp_path: Path) -> None:
    from src.analysis.diff_2020_2025 import save_diff_report

    report = [{"plan_year": 2020, "metric": "towns_split", "actual_value": 3.0, "percentile": 55.0, "n_ensemble": 10}]
    out = save_diff_report(report, tmp_path)
    assert out.exists()
    assert out.name == "diff_report.json"


def test_save_diff_report_returns_path(tmp_path: Path) -> None:
    from src.analysis.diff_2020_2025 import save_diff_report

    report: list[dict] = []
    out = save_diff_report(report, tmp_path)
    assert isinstance(out, Path)


def test_save_diff_report_valid_json(tmp_path: Path) -> None:
    from src.analysis.diff_2020_2025 import save_diff_report

    report = [{"plan_year": 2025, "metric": "mean_pp", "actual_value": 1.5, "percentile": 80.0, "n_ensemble": 5}]
    out = save_diff_report(report, tmp_path)
    data = json.loads(out.read_text())
    assert isinstance(data, list)
    assert data[0]["plan_year"] == 2025


def test_save_diff_report_creates_output_dir(tmp_path: Path) -> None:
    from src.analysis.diff_2020_2025 import save_diff_report

    nested = tmp_path / "a" / "b" / "c"
    report: list[dict] = []
    out = save_diff_report(report, nested)
    assert out.exists()
