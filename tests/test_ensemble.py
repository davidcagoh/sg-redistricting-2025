"""Tests for src/analysis/ensemble.py.

TDD RED phase: tests written BEFORE implementation.
All tests mock the MCMC chain and heavy I/O — no real chain iteration,
no disk reads beyond the tmp directory created by the function under test.

Fixture: 6-node graph split into 2 districts of 3 nodes each.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import geopandas as gpd
import networkx as nx
import pyarrow.parquet as pq
import pytest
from shapely.geometry import box

from src.analysis.config import EnsembleConfig, PathsConfig

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

METRICS_COLUMNS = {
    "run_id",
    "step_index",
    "accepted",
    "max_abs_pop_dev",
    "pop_range",
    "ideal_pop",
    "mean_pp",
    "min_pp",
    "cut_edges",
    "towns_split",
    "pln_area_splits",
    "town_split_entropy",
}

ASSIGNMENT_COLUMNS = {"run_id", "step_index", "node_id", "district_id"}

N_NODES = 6
N_STEPS_IN_MOCK_CHAIN = 3  # chain yields 3 partitions


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _make_graph() -> nx.Graph:
    """6-node fully-connected-in-two-components graph."""
    G = nx.Graph()
    for i in range(N_NODES):
        G.add_node(
            i,
            pop_total=1000,
            hdb_town="Tampines",
            pln_area="TAMPINES",
            subzone_name_norm=f"ZONE_{i}",
            _feature_id=i,
        )
    # Two contiguous groups: 0-1-2 and 3-4-5
    G.add_edges_from([(0, 1), (1, 2), (3, 4), (4, 5), (2, 3)])
    return G


def _make_gdf() -> gpd.GeoDataFrame:
    """Minimal GeoDataFrame with 6 box geometries in EPSG:3414."""
    rows = []
    for i in range(N_NODES):
        x0 = i * 100
        rows.append(
            {
                "geometry": box(x0, 0, x0 + 100, 100),
                "SUBZONE_N": f"ZONE_{i}",
                "PLN_AREA_N": "TAMPINES",
                "pop_total": 1000,
                "subzone_name_norm": f"ZONE_{i}",
                "_feature_id": i,
            }
        )
    gdf = gpd.GeoDataFrame(rows, crs="EPSG:3414")
    return gdf


def _make_geoms(gdf: gpd.GeoDataFrame) -> dict[int, object]:
    return {idx: row.geometry for idx, row in gdf.iterrows()}


def _make_assignment() -> dict[int, int]:
    """Nodes 0-2 → district 0; nodes 3-5 → district 1."""
    return {0: 0, 1: 0, 2: 0, 3: 1, 4: 1, 5: 1}


def _make_mock_partition(assignment: dict[int, int]) -> MagicMock:
    """Create a mock GerryChain Partition-like object."""
    parts = {0: frozenset([0, 1, 2]), 1: frozenset([3, 4, 5])}
    p = MagicMock()
    p.parts = parts
    p.assignment = assignment
    return p


def _make_fixed_metrics() -> dict[str, float]:
    return {
        "max_abs_pop_dev": 0.0,
        "pop_range": 0.0,
        "ideal_pop": 3000.0,
        "mean_pp": 0.8,
        "min_pp": 0.7,
        "cut_edges": 1,
        "towns_split": 0,
        "pln_area_splits": 0,
        "town_split_entropy": 0.0,
    }


def _make_paths_config(tmp_path: Path) -> PathsConfig:
    return PathsConfig(
        processed_dir=tmp_path / "processed",
        raw_dir=tmp_path / "raw",
        output_dir=tmp_path / "output",
    )


def _make_ensemble_config(run_id: str = "test-run-001") -> EnsembleConfig:
    return EnsembleConfig(
        k_districts=2,
        pop_tolerance=0.10,
        n_steps=N_STEPS_IN_MOCK_CHAIN,
        burn_in=0,
        seed=42,
        run_id=run_id,
    )


# ---------------------------------------------------------------------------
# Helpers to build mock chain
# ---------------------------------------------------------------------------


def _make_mock_chain(assignment: dict[int, int]) -> list[MagicMock]:
    """Return a list of N_STEPS mock partitions."""
    return [_make_mock_partition(assignment) for _ in range(N_STEPS_IN_MOCK_CHAIN)]


# ---------------------------------------------------------------------------
# Context manager to patch all heavy dependencies for run_ensemble
# ---------------------------------------------------------------------------

_ENSEMBLE_MODULE = "src.analysis.ensemble"


def _patch_all(tmp_path: Path):
    """Return a context manager that patches everything for run_ensemble."""
    graph = _make_graph()
    gdf = _make_gdf()
    geoms = _make_geoms(gdf)
    assignment = _make_assignment()
    mock_chain = _make_mock_chain(assignment)
    fixed_metrics = _make_fixed_metrics()

    class _Ctx:
        def __enter__(self):
            self._patches = []

            def _start(p):
                m = p.start()
                self._patches.append(p)
                return m

            self.mock_build_pipeline = _start(
                patch(
                    f"{_ENSEMBLE_MODULE}.build_pipeline_inputs",
                    return_value=(graph, gdf, geoms),
                )
            )
            self.mock_seed = _start(
                patch(
                    f"{_ENSEMBLE_MODULE}.make_seed_partition",
                    return_value=assignment,
                )
            )
            self.mock_initial = _start(
                patch(
                    f"{_ENSEMBLE_MODULE}.build_initial_partition",
                    return_value=MagicMock(),
                )
            )
            self.mock_constraints = _start(
                patch(
                    f"{_ENSEMBLE_MODULE}.build_constraints",
                    return_value=[MagicMock(), MagicMock(return_value=MagicMock())],
                )
            )
            self.mock_acceptance = _start(
                patch(
                    f"{_ENSEMBLE_MODULE}.make_acceptance",
                    return_value=MagicMock(),
                )
            )
            self.mock_chain = _start(
                patch(
                    f"{_ENSEMBLE_MODULE}.build_chain",
                    return_value=iter(mock_chain),
                )
            )
            self.mock_compute = _start(
                patch(
                    f"{_ENSEMBLE_MODULE}.compute_all",
                    return_value=fixed_metrics,
                )
            )
            self.mock_git_sha = _start(
                patch(
                    f"{_ENSEMBLE_MODULE}.get_git_sha",
                    return_value="abc1234",
                )
            )
            return self

        def __exit__(self, *args):
            for p in self._patches:
                p.stop()

    return _Ctx()


# ---------------------------------------------------------------------------
# Tests: run_ensemble returns a Path that exists
# ---------------------------------------------------------------------------


class TestRunEnsembleReturnValue:
    def test_returns_path(self, tmp_path: Path) -> None:
        paths = _make_paths_config(tmp_path)
        config = _make_ensemble_config()

        with _patch_all(tmp_path):
            from src.analysis.ensemble import run_ensemble

            result = run_ensemble(config, paths)

        assert isinstance(result, Path)

    def test_returned_path_exists(self, tmp_path: Path) -> None:
        paths = _make_paths_config(tmp_path)
        config = _make_ensemble_config()

        with _patch_all(tmp_path):
            from src.analysis.ensemble import run_ensemble

            result = run_ensemble(config, paths)

        assert result.exists()

    def test_returned_path_is_directory(self, tmp_path: Path) -> None:
        paths = _make_paths_config(tmp_path)
        config = _make_ensemble_config()

        with _patch_all(tmp_path):
            from src.analysis.ensemble import run_ensemble

            result = run_ensemble(config, paths)

        assert result.is_dir()


# ---------------------------------------------------------------------------
# Tests: output directory contains required files
# ---------------------------------------------------------------------------


class TestRunEnsembleOutputFiles:
    def test_metrics_parquet_exists(self, tmp_path: Path) -> None:
        paths = _make_paths_config(tmp_path)
        config = _make_ensemble_config()

        with _patch_all(tmp_path):
            from src.analysis.ensemble import run_ensemble

            run_dir = run_ensemble(config, paths)

        assert (run_dir / "metrics.parquet").exists()

    def test_assignments_parquet_exists(self, tmp_path: Path) -> None:
        paths = _make_paths_config(tmp_path)
        config = _make_ensemble_config()

        with _patch_all(tmp_path):
            from src.analysis.ensemble import run_ensemble

            run_dir = run_ensemble(config, paths)

        assert (run_dir / "assignments.parquet").exists()

    def test_manifest_json_exists(self, tmp_path: Path) -> None:
        paths = _make_paths_config(tmp_path)
        config = _make_ensemble_config()

        with _patch_all(tmp_path):
            from src.analysis.ensemble import run_ensemble

            run_dir = run_ensemble(config, paths)

        assert (run_dir / "manifest.json").exists()


# ---------------------------------------------------------------------------
# Tests: metrics.parquet schema
# ---------------------------------------------------------------------------


class TestMetricsParquetSchema:
    def test_metrics_parquet_has_correct_columns(self, tmp_path: Path) -> None:
        paths = _make_paths_config(tmp_path)
        config = _make_ensemble_config()

        with _patch_all(tmp_path):
            from src.analysis.ensemble import run_ensemble

            run_dir = run_ensemble(config, paths)

        table = pq.read_table(run_dir / "metrics.parquet")
        assert set(table.schema.names) == METRICS_COLUMNS

    def test_metrics_parquet_has_one_row_per_chain_step(self, tmp_path: Path) -> None:
        """After burn_in=0, every step is recorded — expect N_STEPS rows."""
        paths = _make_paths_config(tmp_path)
        config = _make_ensemble_config()

        with _patch_all(tmp_path):
            from src.analysis.ensemble import run_ensemble

            run_dir = run_ensemble(config, paths)

        table = pq.read_table(run_dir / "metrics.parquet")
        assert table.num_rows == N_STEPS_IN_MOCK_CHAIN

    def test_metrics_parquet_run_id_column_correct(self, tmp_path: Path) -> None:
        paths = _make_paths_config(tmp_path)
        config = _make_ensemble_config(run_id="test-run-001")

        with _patch_all(tmp_path):
            from src.analysis.ensemble import run_ensemble

            run_dir = run_ensemble(config, paths)

        table = pq.read_table(run_dir / "metrics.parquet")
        run_ids = table.column("run_id").to_pylist()
        assert all(r == "test-run-001" for r in run_ids)

    def test_metrics_parquet_step_index_sequential(self, tmp_path: Path) -> None:
        paths = _make_paths_config(tmp_path)
        config = _make_ensemble_config()

        with _patch_all(tmp_path):
            from src.analysis.ensemble import run_ensemble

            run_dir = run_ensemble(config, paths)

        table = pq.read_table(run_dir / "metrics.parquet")
        step_indices = table.column("step_index").to_pylist()
        assert step_indices == list(range(N_STEPS_IN_MOCK_CHAIN))

    def test_metrics_accepted_column_all_true(self, tmp_path: Path) -> None:
        """We log only accepted steps; accepted column should always be True."""
        paths = _make_paths_config(tmp_path)
        config = _make_ensemble_config()

        with _patch_all(tmp_path):
            from src.analysis.ensemble import run_ensemble

            run_dir = run_ensemble(config, paths)

        table = pq.read_table(run_dir / "metrics.parquet")
        accepted_vals = table.column("accepted").to_pylist()
        assert all(v is True for v in accepted_vals)


# ---------------------------------------------------------------------------
# Tests: assignments.parquet schema
# ---------------------------------------------------------------------------


class TestAssignmentsParquetSchema:
    def test_assignments_parquet_has_correct_columns(self, tmp_path: Path) -> None:
        paths = _make_paths_config(tmp_path)
        config = _make_ensemble_config()

        with _patch_all(tmp_path):
            from src.analysis.ensemble import run_ensemble

            run_dir = run_ensemble(config, paths)

        table = pq.read_table(run_dir / "assignments.parquet")
        assert set(table.schema.names) == ASSIGNMENT_COLUMNS

    def test_assignments_parquet_row_count(self, tmp_path: Path) -> None:
        """Long format: one row per (step, node). Expect n_steps * n_nodes rows."""
        paths = _make_paths_config(tmp_path)
        config = _make_ensemble_config()

        with _patch_all(tmp_path):
            from src.analysis.ensemble import run_ensemble

            run_dir = run_ensemble(config, paths)

        table = pq.read_table(run_dir / "assignments.parquet")
        expected_rows = N_STEPS_IN_MOCK_CHAIN * N_NODES
        assert table.num_rows == expected_rows

    def test_assignments_parquet_node_ids_complete(self, tmp_path: Path) -> None:
        """For each step, all N_NODES node IDs must appear exactly once."""
        paths = _make_paths_config(tmp_path)
        config = _make_ensemble_config()

        with _patch_all(tmp_path):
            from src.analysis.ensemble import run_ensemble

            run_dir = run_ensemble(config, paths)

        table = pq.read_table(run_dir / "assignments.parquet")
        df = table.to_pandas()
        for step in range(N_STEPS_IN_MOCK_CHAIN):
            step_df = df[df["step_index"] == step]
            assert set(step_df["node_id"].tolist()) == set(range(N_NODES))


# ---------------------------------------------------------------------------
# Tests: manifest.json
# ---------------------------------------------------------------------------


class TestManifestJson:
    def test_manifest_is_valid_json(self, tmp_path: Path) -> None:
        paths = _make_paths_config(tmp_path)
        config = _make_ensemble_config()

        with _patch_all(tmp_path):
            from src.analysis.ensemble import run_ensemble

            run_dir = run_ensemble(config, paths)

        manifest_text = (run_dir / "manifest.json").read_text()
        manifest = json.loads(manifest_text)
        assert isinstance(manifest, dict)

    def test_manifest_has_run_id(self, tmp_path: Path) -> None:
        paths = _make_paths_config(tmp_path)
        config = _make_ensemble_config(run_id="test-run-001")

        with _patch_all(tmp_path):
            from src.analysis.ensemble import run_ensemble

            run_dir = run_ensemble(config, paths)

        manifest = json.loads((run_dir / "manifest.json").read_text())
        assert manifest["run_id"] == "test-run-001"

    def test_manifest_has_config(self, tmp_path: Path) -> None:
        paths = _make_paths_config(tmp_path)
        config = _make_ensemble_config()

        with _patch_all(tmp_path):
            from src.analysis.ensemble import run_ensemble

            run_dir = run_ensemble(config, paths)

        manifest = json.loads((run_dir / "manifest.json").read_text())
        assert "config" in manifest

    def test_manifest_config_has_k_districts(self, tmp_path: Path) -> None:
        paths = _make_paths_config(tmp_path)
        config = _make_ensemble_config()

        with _patch_all(tmp_path):
            from src.analysis.ensemble import run_ensemble

            run_dir = run_ensemble(config, paths)

        manifest = json.loads((run_dir / "manifest.json").read_text())
        assert manifest["config"]["k_districts"] == 2

    def test_manifest_has_git_sha(self, tmp_path: Path) -> None:
        paths = _make_paths_config(tmp_path)
        config = _make_ensemble_config()

        with _patch_all(tmp_path):
            from src.analysis.ensemble import run_ensemble

            run_dir = run_ensemble(config, paths)

        manifest = json.loads((run_dir / "manifest.json").read_text())
        assert "git_sha" in manifest

    def test_manifest_has_n_accepted(self, tmp_path: Path) -> None:
        paths = _make_paths_config(tmp_path)
        config = _make_ensemble_config()

        with _patch_all(tmp_path):
            from src.analysis.ensemble import run_ensemble

            run_dir = run_ensemble(config, paths)

        manifest = json.loads((run_dir / "manifest.json").read_text())
        assert "n_accepted" in manifest

    def test_manifest_n_accepted_equals_chain_length(self, tmp_path: Path) -> None:
        """With burn_in=0 and all steps accepted, n_accepted == chain length."""
        paths = _make_paths_config(tmp_path)
        config = _make_ensemble_config()

        with _patch_all(tmp_path):
            from src.analysis.ensemble import run_ensemble

            run_dir = run_ensemble(config, paths)

        manifest = json.loads((run_dir / "manifest.json").read_text())
        assert manifest["n_accepted"] == N_STEPS_IN_MOCK_CHAIN

    def test_manifest_has_started_at(self, tmp_path: Path) -> None:
        paths = _make_paths_config(tmp_path)
        config = _make_ensemble_config()

        with _patch_all(tmp_path):
            from src.analysis.ensemble import run_ensemble

            run_dir = run_ensemble(config, paths)

        manifest = json.loads((run_dir / "manifest.json").read_text())
        assert "started_at" in manifest

    def test_manifest_has_completed_at(self, tmp_path: Path) -> None:
        paths = _make_paths_config(tmp_path)
        config = _make_ensemble_config()

        with _patch_all(tmp_path):
            from src.analysis.ensemble import run_ensemble

            run_dir = run_ensemble(config, paths)

        manifest = json.loads((run_dir / "manifest.json").read_text())
        assert "completed_at" in manifest


# ---------------------------------------------------------------------------
# Tests: FileExistsError when output dir already exists
# ---------------------------------------------------------------------------


class TestRunEnsembleFileExistsError:
    def test_raises_file_exists_error_when_dir_exists(self, tmp_path: Path) -> None:
        paths = _make_paths_config(tmp_path)
        config = _make_ensemble_config(run_id="duplicate-run")

        # Pre-create the final (non-tmp) directory
        final_dir = paths.ensemble_dir("duplicate-run")
        final_dir.mkdir(parents=True, exist_ok=True)

        with _patch_all(tmp_path):
            from src.analysis.ensemble import run_ensemble

            with pytest.raises(FileExistsError):
                run_ensemble(config, paths)

    def test_no_error_when_only_tmp_dir_exists(self, tmp_path: Path) -> None:
        """A stale .tmp dir from a crashed prior run should not block a new run."""
        paths = _make_paths_config(tmp_path)
        config = _make_ensemble_config(run_id="stale-tmp-run")

        # Pre-create the TMP directory (simulating a crashed prior run)
        tmp_dir = Path(str(paths.ensemble_dir("stale-tmp-run")) + ".tmp")
        tmp_dir.mkdir(parents=True, exist_ok=True)

        with _patch_all(tmp_path):
            from src.analysis.ensemble import run_ensemble

            # Should succeed — stale .tmp does NOT block a new run
            result = run_ensemble(config, paths)

        assert result.exists()


# ---------------------------------------------------------------------------
# Tests: build_pipeline_inputs call order
# ---------------------------------------------------------------------------


class TestBuildPipelineInputsCallOrder:
    """filter_for_mcmc MUST be called BEFORE attach_hdb_towns."""

    def test_filter_called_before_attach_hdb_towns(self, tmp_path: Path) -> None:
        """Verify the ordering: build_subzone_graph → filter_for_mcmc → attach_hdb_towns."""
        call_order: list[str] = []

        graph = _make_graph()
        gdf = _make_gdf()

        mock_subzone_layer = MagicMock()
        mock_subzone_layer.svy21 = gdf

        def record(name):
            def _inner(*args, **kwargs):
                call_order.append(name)
                return MagicMock()

            return _inner

        # We need filter_for_mcmc to return a tuple (graph, excluded)
        filtered_graph = graph.copy()
        filter_return = (filtered_graph, [])

        with (
            patch(
                "src.analysis.ensemble.load_subzones_with_population",
                return_value=mock_subzone_layer,
            ),
            patch(
                "src.analysis.ensemble.load_hdb_buildings",
                return_value=MagicMock(),
            ),
            patch(
                "src.analysis.ensemble.load_hdb_property_table",
                return_value=MagicMock(),
            ),
            patch(
                "src.analysis.ensemble.build_subzone_graph",
                side_effect=lambda *a, **kw: (call_order.append("build_subzone_graph"), graph)[1],
            ),
            patch(
                "src.analysis.ensemble.filter_for_mcmc",
                side_effect=lambda *a, **kw: (call_order.append("filter_for_mcmc"), filter_return)[1],
            ),
            patch(
                "src.analysis.ensemble.attach_hdb_towns",
                side_effect=lambda *a, **kw: (call_order.append("attach_hdb_towns"), filtered_graph)[1],
            ),
        ):
            from src.analysis.ensemble import build_pipeline_inputs

            paths = _make_paths_config(tmp_path)
            build_pipeline_inputs(paths)

        assert "filter_for_mcmc" in call_order
        assert "attach_hdb_towns" in call_order
        filter_idx = call_order.index("filter_for_mcmc")
        attach_idx = call_order.index("attach_hdb_towns")
        assert filter_idx < attach_idx, (
            f"filter_for_mcmc (pos {filter_idx}) must be called "
            f"before attach_hdb_towns (pos {attach_idx}); got order: {call_order}"
        )

    def test_build_subzone_graph_called_before_filter(self, tmp_path: Path) -> None:
        call_order: list[str] = []
        graph = _make_graph()
        gdf = _make_gdf()

        mock_subzone_layer = MagicMock()
        mock_subzone_layer.svy21 = gdf
        filter_return = (graph.copy(), [])

        with (
            patch("src.analysis.ensemble.load_subzones_with_population", return_value=mock_subzone_layer),
            patch("src.analysis.ensemble.load_hdb_buildings", return_value=MagicMock()),
            patch("src.analysis.ensemble.load_hdb_property_table", return_value=MagicMock()),
            patch(
                "src.analysis.ensemble.build_subzone_graph",
                side_effect=lambda *a, **kw: (call_order.append("build_subzone_graph"), graph)[1],
            ),
            patch(
                "src.analysis.ensemble.filter_for_mcmc",
                side_effect=lambda *a, **kw: (call_order.append("filter_for_mcmc"), filter_return)[1],
            ),
            patch(
                "src.analysis.ensemble.attach_hdb_towns",
                side_effect=lambda *a, **kw: (call_order.append("attach_hdb_towns"), graph)[1],
            ),
        ):
            from src.analysis.ensemble import build_pipeline_inputs

            paths = _make_paths_config(tmp_path)
            build_pipeline_inputs(paths)

        build_idx = call_order.index("build_subzone_graph")
        filter_idx = call_order.index("filter_for_mcmc")
        assert build_idx < filter_idx


# ---------------------------------------------------------------------------
# Tests: build_pipeline_inputs return value
# ---------------------------------------------------------------------------


class TestBuildPipelineInputsReturnValue:
    def test_returns_three_tuple(self, tmp_path: Path) -> None:
        graph = _make_graph()
        gdf = _make_gdf()

        mock_subzone_layer = MagicMock()
        mock_subzone_layer.svy21 = gdf
        filtered = graph.copy()

        with (
            patch("src.analysis.ensemble.load_subzones_with_population", return_value=mock_subzone_layer),
            patch("src.analysis.ensemble.load_hdb_buildings", return_value=MagicMock()),
            patch("src.analysis.ensemble.load_hdb_property_table", return_value=MagicMock()),
            patch("src.analysis.ensemble.build_subzone_graph", return_value=graph),
            patch("src.analysis.ensemble.filter_for_mcmc", return_value=(filtered, [])),
            patch("src.analysis.ensemble.attach_hdb_towns", return_value=filtered),
        ):
            from src.analysis.ensemble import build_pipeline_inputs

            paths = _make_paths_config(tmp_path)
            result = build_pipeline_inputs(paths)

        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_first_element_is_graph(self, tmp_path: Path) -> None:
        graph = _make_graph()
        gdf = _make_gdf()

        mock_subzone_layer = MagicMock()
        mock_subzone_layer.svy21 = gdf
        filtered = graph.copy()

        with (
            patch("src.analysis.ensemble.load_subzones_with_population", return_value=mock_subzone_layer),
            patch("src.analysis.ensemble.load_hdb_buildings", return_value=MagicMock()),
            patch("src.analysis.ensemble.load_hdb_property_table", return_value=MagicMock()),
            patch("src.analysis.ensemble.build_subzone_graph", return_value=graph),
            patch("src.analysis.ensemble.filter_for_mcmc", return_value=(filtered, [])),
            patch("src.analysis.ensemble.attach_hdb_towns", return_value=filtered),
        ):
            from src.analysis.ensemble import build_pipeline_inputs

            paths = _make_paths_config(tmp_path)
            result_graph, _, _ = build_pipeline_inputs(paths)

        assert isinstance(result_graph, nx.Graph)

    def test_third_element_is_dict_of_geoms(self, tmp_path: Path) -> None:
        """subzone_geoms must be {node_id: geometry} for filtered nodes only."""
        graph = _make_graph()
        gdf = _make_gdf()

        mock_subzone_layer = MagicMock()
        mock_subzone_layer.svy21 = gdf
        filtered = graph.copy()

        with (
            patch("src.analysis.ensemble.load_subzones_with_population", return_value=mock_subzone_layer),
            patch("src.analysis.ensemble.load_hdb_buildings", return_value=MagicMock()),
            patch("src.analysis.ensemble.load_hdb_property_table", return_value=MagicMock()),
            patch("src.analysis.ensemble.build_subzone_graph", return_value=graph),
            patch("src.analysis.ensemble.filter_for_mcmc", return_value=(filtered, [])),
            patch("src.analysis.ensemble.attach_hdb_towns", return_value=filtered),
        ):
            from src.analysis.ensemble import build_pipeline_inputs

            paths = _make_paths_config(tmp_path)
            _, filtered_gdf, subzone_geoms = build_pipeline_inputs(paths)

        assert isinstance(subzone_geoms, dict)
        # All keys are in the filtered gdf index
        for key in subzone_geoms:
            assert key in filtered_gdf.index


# ---------------------------------------------------------------------------
# Tests: burn_in respected
# ---------------------------------------------------------------------------


class TestBurnIn:
    def test_burn_in_steps_not_written_to_metrics(self, tmp_path: Path) -> None:
        """With burn_in=2 and a 3-step chain, only 1 row should be written."""
        paths = _make_paths_config(tmp_path)
        config = EnsembleConfig(
            k_districts=2,
            pop_tolerance=0.10,
            n_steps=N_STEPS_IN_MOCK_CHAIN,
            burn_in=2,  # skip first 2 of 3 steps
            seed=42,
            run_id="burn-in-test",
        )

        graph = _make_graph()
        gdf = _make_gdf()
        geoms = _make_geoms(gdf)
        assignment = _make_assignment()
        mock_chain = _make_mock_chain(assignment)
        fixed_metrics = _make_fixed_metrics()

        with (
            patch(f"{_ENSEMBLE_MODULE}.build_pipeline_inputs", return_value=(graph, gdf, geoms)),
            patch(f"{_ENSEMBLE_MODULE}.make_seed_partition", return_value=assignment),
            patch(f"{_ENSEMBLE_MODULE}.build_initial_partition", return_value=MagicMock()),
            patch(
                f"{_ENSEMBLE_MODULE}.build_constraints",
                return_value=[MagicMock(), MagicMock(return_value=MagicMock())],
            ),
            patch(f"{_ENSEMBLE_MODULE}.make_acceptance", return_value=MagicMock()),
            patch(f"{_ENSEMBLE_MODULE}.build_chain", return_value=iter(mock_chain)),
            patch(f"{_ENSEMBLE_MODULE}.compute_all", return_value=fixed_metrics),
            patch(f"{_ENSEMBLE_MODULE}.get_git_sha", return_value="abc1234"),
        ):
            from src.analysis.ensemble import run_ensemble

            run_dir = run_ensemble(config, paths)

        table = pq.read_table(run_dir / "metrics.parquet")
        # 3 steps total - 2 burn_in = 1 step written
        assert table.num_rows == 1

    def test_burn_in_steps_not_written_to_assignments(self, tmp_path: Path) -> None:
        """With burn_in=2 and 3 steps, assignments should have 1 * N_NODES rows."""
        paths = _make_paths_config(tmp_path)
        config = EnsembleConfig(
            k_districts=2,
            pop_tolerance=0.10,
            n_steps=N_STEPS_IN_MOCK_CHAIN,
            burn_in=2,
            seed=42,
            run_id="burn-in-assign-test",
        )

        graph = _make_graph()
        gdf = _make_gdf()
        geoms = _make_geoms(gdf)
        assignment = _make_assignment()
        mock_chain = _make_mock_chain(assignment)
        fixed_metrics = _make_fixed_metrics()

        with (
            patch(f"{_ENSEMBLE_MODULE}.build_pipeline_inputs", return_value=(graph, gdf, geoms)),
            patch(f"{_ENSEMBLE_MODULE}.make_seed_partition", return_value=assignment),
            patch(f"{_ENSEMBLE_MODULE}.build_initial_partition", return_value=MagicMock()),
            patch(
                f"{_ENSEMBLE_MODULE}.build_constraints",
                return_value=[MagicMock(), MagicMock(return_value=MagicMock())],
            ),
            patch(f"{_ENSEMBLE_MODULE}.make_acceptance", return_value=MagicMock()),
            patch(f"{_ENSEMBLE_MODULE}.build_chain", return_value=iter(mock_chain)),
            patch(f"{_ENSEMBLE_MODULE}.compute_all", return_value=fixed_metrics),
            patch(f"{_ENSEMBLE_MODULE}.get_git_sha", return_value="abc1234"),
        ):
            from src.analysis.ensemble import run_ensemble

            run_dir = run_ensemble(config, paths)

        table = pq.read_table(run_dir / "assignments.parquet")
        assert table.num_rows == 1 * N_NODES


# ---------------------------------------------------------------------------
# Tests: _build_run_outputs
# ---------------------------------------------------------------------------


class TestBuildRunOutputs:
    def test_creates_three_output_files(self, tmp_path: Path) -> None:
        from src.analysis.config import RunManifest
        from src.analysis.ensemble import _build_run_outputs

        run_dir = tmp_path / "run001"
        run_dir.mkdir(parents=True)

        metrics_rows = [
            {
                "run_id": "run001",
                "step_index": 0,
                "accepted": True,
                "max_abs_pop_dev": 0.0,
                "pop_range": 0.0,
                "ideal_pop": 3000.0,
                "mean_pp": 0.8,
                "min_pp": 0.7,
                "cut_edges": 1,
                "towns_split": 0,
                "pln_area_splits": 0,
                "town_split_entropy": 0.0,
            }
        ]
        assignment_rows = [
            {"run_id": "run001", "step_index": 0, "node_id": i, "district_id": 0}
            for i in range(3)
        ]
        manifest = RunManifest(
            run_id="run001",
            git_sha="abc1234",
            config=_make_ensemble_config(run_id="run001"),
            input_hashes={},
            started_at="2025-01-01T00:00:00",
            completed_at="2025-01-01T00:01:00",
            n_accepted=1,
            n_rejected=0,
        )

        _build_run_outputs(run_dir, metrics_rows, assignment_rows, manifest)

        assert (run_dir / "metrics.parquet").exists()
        assert (run_dir / "assignments.parquet").exists()
        assert (run_dir / "manifest.json").exists()

    def test_metrics_parquet_readable(self, tmp_path: Path) -> None:
        from src.analysis.config import RunManifest
        from src.analysis.ensemble import _build_run_outputs

        run_dir = tmp_path / "run002"
        run_dir.mkdir(parents=True)

        metrics_rows = [
            {
                "run_id": "run002",
                "step_index": i,
                "accepted": True,
                "max_abs_pop_dev": 0.0,
                "pop_range": 0.0,
                "ideal_pop": 3000.0,
                "mean_pp": 0.8,
                "min_pp": 0.7,
                "cut_edges": 1,
                "towns_split": 0,
                "pln_area_splits": 0,
                "town_split_entropy": 0.0,
            }
            for i in range(3)
        ]
        assignment_rows = []
        manifest = RunManifest(
            run_id="run002",
            git_sha="abc1234",
            config=_make_ensemble_config(run_id="run002"),
            input_hashes={},
            started_at="2025-01-01T00:00:00",
            completed_at="2025-01-01T00:01:00",
            n_accepted=3,
            n_rejected=0,
        )

        _build_run_outputs(run_dir, metrics_rows, assignment_rows, manifest)

        table = pq.read_table(run_dir / "metrics.parquet")
        assert table.num_rows == 3

    def test_manifest_json_content(self, tmp_path: Path) -> None:
        from src.analysis.config import RunManifest
        from src.analysis.ensemble import _build_run_outputs

        run_dir = tmp_path / "run003"
        run_dir.mkdir(parents=True)

        manifest = RunManifest(
            run_id="run003",
            git_sha="deadbeef",
            config=_make_ensemble_config(run_id="run003"),
            input_hashes={"foo": "bar"},
            started_at="2025-01-01T00:00:00",
            completed_at="2025-01-01T00:01:00",
            n_accepted=5,
            n_rejected=2,
        )

        _build_run_outputs(run_dir, [], [], manifest)

        data = json.loads((run_dir / "manifest.json").read_text())
        assert data["run_id"] == "run003"
        assert data["git_sha"] == "deadbeef"
        assert data["n_accepted"] == 5
        assert data["n_rejected"] == 2
        assert data["input_hashes"] == {"foo": "bar"}


# ---------------------------------------------------------------------------
# Tests: tmp-then-rename atomicity
# ---------------------------------------------------------------------------


class TestAtomicWrite:
    def test_tmp_dir_cleaned_up_after_success(self, tmp_path: Path) -> None:
        """The .tmp directory should not exist after a successful run."""
        paths = _make_paths_config(tmp_path)
        config = _make_ensemble_config(run_id="atomic-test")

        with _patch_all(tmp_path):
            from src.analysis.ensemble import run_ensemble

            run_dir = run_ensemble(config, paths)

        tmp_dir = Path(str(run_dir) + ".tmp")
        assert not tmp_dir.exists()

    def test_final_dir_is_run_id_dir(self, tmp_path: Path) -> None:
        """The returned path should be paths.ensemble_dir(run_id)."""
        paths = _make_paths_config(tmp_path)
        config = _make_ensemble_config(run_id="path-check-test")

        with _patch_all(tmp_path):
            from src.analysis.ensemble import run_ensemble

            run_dir = run_ensemble(config, paths)

        assert run_dir == paths.ensemble_dir("path-check-test")
