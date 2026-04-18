"""Tests for src/analysis/diff_2020_2025.py."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import networkx as nx
import pandas as pd
import pytest
from shapely.geometry import box

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


def _write_actual_assignments(paths: PathsConfig, year: int) -> None:
    dst = paths.output_dir / "actual_assignments"
    dst.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame({"node_id": [1, 2, 3], "ed_name": ["A", "A", "B"]})
    df.to_parquet(dst / f"{year}.parquet", index=False)


def _write_actual_metrics(paths: PathsConfig, year: int, metrics: dict) -> None:
    dst = paths.output_dir / "actual_assignments"
    dst.mkdir(parents=True, exist_ok=True)
    (dst / f"{year}_metrics.json").write_text(json.dumps(metrics))


def _write_ensemble_metrics(paths: PathsConfig, run_id: str, rows: list[dict]) -> None:
    edir = paths.ensemble_dir(run_id)
    edir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(edir / "metrics.parquet", index=False)


_SAMPLE_METRICS = {
    "max_abs_pop_dev": 0.05,
    "towns_split": 3.0,
    "pln_area_splits": 2.0,
    "mean_pp": 0.4,
    "pop_range": 5000.0,
    "ideal_pop": 100000.0,
    "min_pp": 0.2,
    "cut_edges": 10,
    "town_split_entropy": 1.5,
}


# ---------------------------------------------------------------------------
# load_actual_assignments
# ---------------------------------------------------------------------------


def test_load_actual_assignments_returns_dataframe(tmp_path: Path) -> None:
    from src.analysis.diff_2020_2025 import load_actual_assignments

    paths = _make_paths(tmp_path)
    _write_actual_assignments(paths, 2020)
    df = load_actual_assignments(2020, paths)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3


def test_load_actual_assignments_columns(tmp_path: Path) -> None:
    from src.analysis.diff_2020_2025 import load_actual_assignments

    paths = _make_paths(tmp_path)
    _write_actual_assignments(paths, 2020)
    df = load_actual_assignments(2020, paths)
    assert "node_id" in df.columns
    assert "ed_name" in df.columns


def test_load_actual_assignments_missing_raises(tmp_path: Path) -> None:
    from src.analysis.diff_2020_2025 import load_actual_assignments

    paths = _make_paths(tmp_path)
    with pytest.raises(FileNotFoundError):
        load_actual_assignments(2020, paths)


def test_load_actual_assignments_year_2025(tmp_path: Path) -> None:
    from src.analysis.diff_2020_2025 import load_actual_assignments

    paths = _make_paths(tmp_path)
    _write_actual_assignments(paths, 2025)
    df = load_actual_assignments(2025, paths)
    assert set(df["ed_name"]) == {"A", "B"}


# ---------------------------------------------------------------------------
# load_actual_metrics
# ---------------------------------------------------------------------------


def test_load_actual_metrics_returns_dict(tmp_path: Path) -> None:
    from src.analysis.diff_2020_2025 import load_actual_metrics

    paths = _make_paths(tmp_path)
    _write_actual_metrics(paths, 2020, _SAMPLE_METRICS)
    result = load_actual_metrics(2020, paths)
    assert isinstance(result, dict)


def test_load_actual_metrics_values(tmp_path: Path) -> None:
    from src.analysis.diff_2020_2025 import load_actual_metrics

    paths = _make_paths(tmp_path)
    _write_actual_metrics(paths, 2020, _SAMPLE_METRICS)
    result = load_actual_metrics(2020, paths)
    assert result["max_abs_pop_dev"] == pytest.approx(0.05)
    assert result["towns_split"] == pytest.approx(3.0)


def test_load_actual_metrics_missing_raises(tmp_path: Path) -> None:
    from src.analysis.diff_2020_2025 import load_actual_metrics

    paths = _make_paths(tmp_path)
    with pytest.raises(FileNotFoundError):
        load_actual_metrics(2020, paths)


def test_load_actual_metrics_year_2025(tmp_path: Path) -> None:
    from src.analysis.diff_2020_2025 import load_actual_metrics

    paths = _make_paths(tmp_path)
    metrics_25 = dict(_SAMPLE_METRICS)
    metrics_25["towns_split"] = 7.0
    _write_actual_metrics(paths, 2025, metrics_25)
    result = load_actual_metrics(2025, paths)
    assert result["towns_split"] == pytest.approx(7.0)


# ---------------------------------------------------------------------------
# load_ensemble_metrics
# ---------------------------------------------------------------------------


def test_load_ensemble_metrics_returns_dataframe(tmp_path: Path) -> None:
    from src.analysis.diff_2020_2025 import load_ensemble_metrics

    paths = _make_paths(tmp_path)
    rows = [{"run_id": "run-abc", "step_index": i, "max_abs_pop_dev": 0.05} for i in range(5)]
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
# compute_actual_plan_metrics
# ---------------------------------------------------------------------------


def _make_tiny_graph() -> tuple[nx.Graph, dict]:
    """Two-node graph with pop, hdb_town, pln_area attrs and square geometries."""
    g = nx.Graph()
    g.add_node(0, pop_total=1000, hdb_town="TownA", pln_area="Area1")
    g.add_node(1, pop_total=1000, hdb_town="TownA", pln_area="Area1")
    g.add_edge(0, 1)
    geoms = {0: box(0, 0, 1, 1), 1: box(1, 0, 2, 1)}
    return g, geoms


def test_compute_actual_plan_metrics_returns_dict() -> None:
    from src.analysis.diff_2020_2025 import compute_actual_plan_metrics

    graph, geoms = _make_tiny_graph()
    assignment_str = {0: "DistA", 1: "DistB"}
    result = compute_actual_plan_metrics(assignment_str, graph, geoms)
    assert isinstance(result, dict)


def test_compute_actual_plan_metrics_required_keys() -> None:
    from src.analysis.diff_2020_2025 import compute_actual_plan_metrics

    graph, geoms = _make_tiny_graph()
    assignment_str = {0: "DistA", 1: "DistB"}
    result = compute_actual_plan_metrics(assignment_str, graph, geoms)
    for key in ("max_abs_pop_dev", "towns_split", "pln_area_splits", "mean_pp"):
        assert key in result, f"Missing key: {key}"


def test_compute_actual_plan_metrics_drops_unassigned() -> None:
    from src.analysis.diff_2020_2025 import compute_actual_plan_metrics

    graph, geoms = _make_tiny_graph()
    # node 1 has no assignment
    assignment_str = {0: "DistA", 1: None}
    result = compute_actual_plan_metrics(assignment_str, graph, geoms)
    assert isinstance(result, dict)


def test_compute_actual_plan_metrics_single_district() -> None:
    from src.analysis.diff_2020_2025 import compute_actual_plan_metrics

    graph, geoms = _make_tiny_graph()
    assignment_str = {0: "DistA", 1: "DistA"}
    result = compute_actual_plan_metrics(assignment_str, graph, geoms)
    # Both nodes in one district → pop_dev = 0
    assert result["max_abs_pop_dev"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# build_diff_report
# ---------------------------------------------------------------------------

_METRICS = ["max_abs_pop_dev", "towns_split", "pln_area_splits", "mean_pp"]


def _make_actual_metrics(base: float = 0.5) -> dict[str, float]:
    return {m: base for m in _METRICS}


def _make_ensemble_df(n: int = 10) -> pd.DataFrame:
    rows = []
    for i in range(n):
        row = {"run_id": "sg2025", "step_index": 1000 + i}
        for m in _METRICS:
            row[m] = float(i) / n
        rows.append(row)
    return pd.DataFrame(rows)


def test_build_diff_report_structure() -> None:
    from src.analysis.diff_2020_2025 import build_diff_report

    report = build_diff_report(_make_actual_metrics(), _make_actual_metrics(), _make_ensemble_df())
    assert isinstance(report, list)
    assert len(report) == 8  # 2 years × 4 metrics


def test_build_diff_report_keys() -> None:
    from src.analysis.diff_2020_2025 import build_diff_report

    report = build_diff_report(_make_actual_metrics(), _make_actual_metrics(), _make_ensemble_df())
    entry = report[0]
    for key in ("plan_year", "metric", "actual_value", "percentile", "n_ensemble"):
        assert key in entry, f"Missing key: {key}"


def test_build_diff_report_years() -> None:
    from src.analysis.diff_2020_2025 import build_diff_report

    report = build_diff_report(_make_actual_metrics(), _make_actual_metrics(), _make_ensemble_df())
    years = {e["plan_year"] for e in report}
    assert years == {2020, 2025}


def test_build_diff_report_metrics_covered() -> None:
    from src.analysis.diff_2020_2025 import build_diff_report

    report = build_diff_report(_make_actual_metrics(), _make_actual_metrics(), _make_ensemble_df())
    metrics = {e["metric"] for e in report}
    assert metrics == set(_METRICS)


def test_build_diff_report_n_ensemble() -> None:
    from src.analysis.diff_2020_2025 import build_diff_report

    report = build_diff_report(_make_actual_metrics(), _make_actual_metrics(), _make_ensemble_df(n=7))
    for entry in report:
        assert entry["n_ensemble"] == 7


def test_build_diff_report_actual_value_from_dict() -> None:
    from src.analysis.diff_2020_2025 import build_diff_report

    metrics_2020 = _make_actual_metrics(0.99)
    metrics_2025 = _make_actual_metrics(0.01)
    report = build_diff_report(metrics_2020, metrics_2025, _make_ensemble_df())

    entry_2020 = next(e for e in report if e["plan_year"] == 2020 and e["metric"] == "max_abs_pop_dev")
    assert entry_2020["actual_value"] == pytest.approx(0.99)

    entry_2025 = next(e for e in report if e["plan_year"] == 2025 and e["metric"] == "max_abs_pop_dev")
    assert entry_2025["actual_value"] == pytest.approx(0.01)


def test_build_diff_report_percentile_extreme_high() -> None:
    from src.analysis.diff_2020_2025 import build_diff_report

    # actual_value above all ensemble values → 100th percentile
    metrics = _make_actual_metrics(999.0)
    report = build_diff_report(metrics, metrics, _make_ensemble_df())
    for entry in report:
        assert entry["percentile"] == pytest.approx(100.0)


def test_build_diff_report_percentile_extreme_low() -> None:
    from src.analysis.diff_2020_2025 import build_diff_report

    # actual_value below all ensemble values → 0th percentile
    metrics = _make_actual_metrics(-1.0)
    report = build_diff_report(metrics, metrics, _make_ensemble_df())
    for entry in report:
        assert entry["percentile"] == pytest.approx(0.0)


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

    out = save_diff_report([], tmp_path)
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
    out = save_diff_report([], nested)
    assert out.exists()
