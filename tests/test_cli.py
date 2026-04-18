"""Tests for src/analysis/cli.py.

TDD RED phase: tests written BEFORE implementation.
Tests verify arg parsing and that the right functions are called with right args.
Uses unittest.mock.patch to avoid real I/O.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_main(*args: str) -> None:
    """Import and call cli.main() with sys.argv patched to args."""
    from src.analysis import cli

    with patch.object(sys, "argv", ["src.analysis.cli", *args]):
        cli.main()


# ---------------------------------------------------------------------------
# run-ensemble subcommand
# ---------------------------------------------------------------------------


class TestRunEnsemble:
    def test_run_ensemble_calls_run_ensemble_function(self, tmp_path: Path) -> None:
        fake_output_dir = tmp_path / "ensemble" / "run-test"
        fake_output_dir.mkdir(parents=True)

        with patch("src.analysis.cli.run_ensemble", return_value=fake_output_dir) as mock_re:
            _run_main("run-ensemble", "--run-id", "run-test")

        mock_re.assert_called_once()

    def test_run_ensemble_passes_run_id(self, tmp_path: Path) -> None:
        fake_output_dir = tmp_path / "ensemble" / "my-run"
        fake_output_dir.mkdir(parents=True)

        with patch("src.analysis.cli.run_ensemble", return_value=fake_output_dir) as mock_re:
            _run_main("run-ensemble", "--run-id", "my-run")

        config_arg = mock_re.call_args[0][0]
        assert config_arg.run_id == "my-run"

    def test_run_ensemble_passes_n_steps(self, tmp_path: Path) -> None:
        fake_dir = tmp_path / "e" / "r"
        fake_dir.mkdir(parents=True)

        with patch("src.analysis.cli.run_ensemble", return_value=fake_dir) as mock_re:
            _run_main("run-ensemble", "--n-steps", "500")

        config_arg = mock_re.call_args[0][0]
        assert config_arg.n_steps == 500

    def test_run_ensemble_passes_burn_in(self, tmp_path: Path) -> None:
        fake_dir = tmp_path / "e" / "r"
        fake_dir.mkdir(parents=True)

        with patch("src.analysis.cli.run_ensemble", return_value=fake_dir) as mock_re:
            _run_main("run-ensemble", "--burn-in", "200")

        config_arg = mock_re.call_args[0][0]
        assert config_arg.burn_in == 200

    def test_run_ensemble_passes_k(self, tmp_path: Path) -> None:
        fake_dir = tmp_path / "e" / "r"
        fake_dir.mkdir(parents=True)

        with patch("src.analysis.cli.run_ensemble", return_value=fake_dir) as mock_re:
            _run_main("run-ensemble", "--k", "30")

        config_arg = mock_re.call_args[0][0]
        assert config_arg.k_districts == 30

    def test_run_ensemble_passes_seed(self, tmp_path: Path) -> None:
        fake_dir = tmp_path / "e" / "r"
        fake_dir.mkdir(parents=True)

        with patch("src.analysis.cli.run_ensemble", return_value=fake_dir) as mock_re:
            _run_main("run-ensemble", "--seed", "99")

        config_arg = mock_re.call_args[0][0]
        assert config_arg.seed == 99

    def test_run_ensemble_passes_paths_config(self, tmp_path: Path) -> None:
        fake_dir = tmp_path / "e" / "r"
        fake_dir.mkdir(parents=True)

        with patch("src.analysis.cli.run_ensemble", return_value=fake_dir) as mock_re:
            _run_main("run-ensemble")

        from src.analysis.config import PathsConfig
        paths_arg = mock_re.call_args[0][1]
        assert isinstance(paths_arg, PathsConfig)

    def test_run_ensemble_uses_path_constants(self, tmp_path: Path) -> None:
        fake_dir = tmp_path / "e" / "r"
        fake_dir.mkdir(parents=True)

        with patch("src.analysis.cli.run_ensemble", return_value=fake_dir) as mock_re:
            _run_main("run-ensemble")

        from src import utils
        paths_arg = mock_re.call_args[0][1]
        assert paths_arg.processed_dir == utils.PROCESSED
        assert paths_arg.raw_dir == utils.RAW
        assert paths_arg.output_dir == utils.OUTPUT

    def test_run_ensemble_defaults(self, tmp_path: Path) -> None:
        """Default values match EnsembleConfig defaults."""
        fake_dir = tmp_path / "e" / "r"
        fake_dir.mkdir(parents=True)

        with patch("src.analysis.cli.run_ensemble", return_value=fake_dir) as mock_re:
            _run_main("run-ensemble")

        from src.analysis.config import EnsembleConfig
        config_arg = mock_re.call_args[0][0]
        default = EnsembleConfig()
        assert config_arg.n_steps == default.n_steps
        assert config_arg.burn_in == default.burn_in
        assert config_arg.seed == default.seed
        assert config_arg.k_districts == default.k_districts

    def test_run_ensemble_prints_output_dir(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        fake_dir = tmp_path / "ensemble" / "run-test"
        fake_dir.mkdir(parents=True)

        with patch("src.analysis.cli.run_ensemble", return_value=fake_dir):
            _run_main("run-ensemble", "--run-id", "run-test")

        captured = capsys.readouterr()
        assert str(fake_dir) in captured.out


# ---------------------------------------------------------------------------
# assign-actual subcommand
# ---------------------------------------------------------------------------


_SAMPLE_METRICS = {"max_abs_pop_dev": 0.05, "towns_split": 3.0, "pln_area_splits": 2.0, "mean_pp": 0.4}


class TestAssignActual:
    def _patch_and_run(self, *args: str) -> MagicMock:
        """Run assign-actual with mocked assign_actual_plan and file I/O."""
        mock_assign = MagicMock(return_value={0: "Toa Payoh", 1: "Bishan"})

        with (
            patch("src.analysis.cli.assign_actual_plan", mock_assign),
            patch("src.analysis.cli._load_graph_for_actual",
                  return_value=(MagicMock(), MagicMock(), MagicMock())),
            patch("src.analysis.cli.load_electoral_boundaries", return_value=MagicMock()),
            patch("src.analysis.cli._save_actual_assignment"),
            patch("src.analysis.cli.compute_actual_plan_metrics", return_value=_SAMPLE_METRICS),
            patch("pathlib.Path.write_text"),
        ):
            _run_main(*args)

        return mock_assign

    def test_assign_actual_calls_assign_actual_plan(self) -> None:
        mock_assign = self._patch_and_run("assign-actual", "--year", "2020")
        mock_assign.assert_called_once()

    def test_assign_actual_passes_year_2020(self) -> None:
        mock_assign = self._patch_and_run("assign-actual", "--year", "2020")
        year_arg = mock_assign.call_args[0][0]
        assert year_arg == 2020

    def test_assign_actual_passes_year_2025(self) -> None:
        mock_assign = self._patch_and_run("assign-actual", "--year", "2025")
        year_arg = mock_assign.call_args[0][0]
        assert year_arg == 2025

    def test_assign_actual_requires_year(self) -> None:
        with pytest.raises(SystemExit):
            _run_main("assign-actual")

    def test_assign_actual_calls_save(self) -> None:
        mock_save = MagicMock()

        with (
            patch("src.analysis.cli.assign_actual_plan", return_value={0: "ED"}),
            patch("src.analysis.cli._load_graph_for_actual",
                  return_value=(MagicMock(), MagicMock(), MagicMock())),
            patch("src.analysis.cli.load_electoral_boundaries", return_value=MagicMock()),
            patch("src.analysis.cli._save_actual_assignment", mock_save),
            patch("src.analysis.cli.compute_actual_plan_metrics", return_value=_SAMPLE_METRICS),
            patch("pathlib.Path.write_text"),
        ):
            _run_main("assign-actual", "--year", "2020")

        mock_save.assert_called_once()

    def test_assign_actual_save_uses_year_in_path(self) -> None:
        mock_save = MagicMock()

        with (
            patch("src.analysis.cli.assign_actual_plan", return_value={0: "ED"}),
            patch("src.analysis.cli._load_graph_for_actual",
                  return_value=(MagicMock(), MagicMock(), MagicMock())),
            patch("src.analysis.cli.load_electoral_boundaries", return_value=MagicMock()),
            patch("src.analysis.cli._save_actual_assignment", mock_save),
            patch("src.analysis.cli.compute_actual_plan_metrics", return_value=_SAMPLE_METRICS),
            patch("pathlib.Path.write_text"),
        ):
            _run_main("assign-actual", "--year", "2020")

        save_path_arg = mock_save.call_args[0][1]
        assert "2020" in str(save_path_arg)

    def test_assign_actual_save_path_is_parquet(self) -> None:
        mock_save = MagicMock()

        with (
            patch("src.analysis.cli.assign_actual_plan", return_value={0: "ED"}),
            patch("src.analysis.cli._load_graph_for_actual",
                  return_value=(MagicMock(), MagicMock(), MagicMock())),
            patch("src.analysis.cli.load_electoral_boundaries", return_value=MagicMock()),
            patch("src.analysis.cli._save_actual_assignment", mock_save),
            patch("src.analysis.cli.compute_actual_plan_metrics", return_value=_SAMPLE_METRICS),
            patch("pathlib.Path.write_text"),
        ):
            _run_main("assign-actual", "--year", "2025")

        save_path_arg = mock_save.call_args[0][1]
        assert str(save_path_arg).endswith(".parquet")


# ---------------------------------------------------------------------------
# diff subcommand
# ---------------------------------------------------------------------------


class TestDiff:
    def _patch_and_run(self, *args: str) -> dict[str, MagicMock]:
        import pandas as pd

        _sample = {"max_abs_pop_dev": 0.05, "towns_split": 3.0, "pln_area_splits": 2.0, "mean_pp": 0.4}
        mock_load_metrics = MagicMock(return_value=pd.DataFrame({"run_id": ["r1"], "step_index": [0]}))
        mock_load_actual = MagicMock(return_value=pd.DataFrame({"node_id": [1], "ed_name": ["A"]}))
        mock_load_actual_metrics = MagicMock(return_value=_sample)
        mock_build_diff = MagicMock(return_value=[{"plan_year": 2020}])
        mock_save_diff = MagicMock(return_value=Path("/tmp/diff_report.json"))
        mock_save_plots = MagicMock(return_value=[Path("/tmp/plot.png")])

        with (
            patch("src.analysis.cli.load_ensemble_metrics", mock_load_metrics),
            patch("src.analysis.cli.load_actual_assignments", mock_load_actual),
            patch("src.analysis.cli.load_actual_metrics", mock_load_actual_metrics),
            patch("src.analysis.cli.build_diff_report", mock_build_diff),
            patch("src.analysis.cli.save_diff_report", mock_save_diff),
            patch("src.analysis.cli.save_all_plots", mock_save_plots),
        ):
            _run_main(*args)

        return {
            "load_metrics": mock_load_metrics,
            "load_actual": mock_load_actual,
            "load_actual_metrics": mock_load_actual_metrics,
            "build_diff": mock_build_diff,
            "save_diff": mock_save_diff,
            "save_plots": mock_save_plots,
        }

    def test_diff_calls_load_ensemble_metrics(self) -> None:
        mocks = self._patch_and_run(
            "diff", "--run-id", "run-001",
            "--year-2020-run-id", "run-2020",
            "--year-2025-run-id", "run-2025",
        )
        mocks["load_metrics"].assert_called_once()

    def test_diff_passes_run_id_to_load_metrics(self) -> None:
        mocks = self._patch_and_run(
            "diff", "--run-id", "run-001",
            "--year-2020-run-id", "run-2020",
            "--year-2025-run-id", "run-2025",
        )
        call_args = mocks["load_metrics"].call_args[0]
        assert "run-001" in call_args

    def test_diff_calls_load_actual_for_2020(self) -> None:
        mocks = self._patch_and_run(
            "diff", "--run-id", "run-001",
            "--year-2020-run-id", "run-2020",
            "--year-2025-run-id", "run-2025",
        )
        assert mocks["load_actual"].call_count >= 1

    def test_diff_calls_load_actual_for_2025(self) -> None:
        mocks = self._patch_and_run(
            "diff", "--run-id", "run-001",
            "--year-2020-run-id", "run-2020",
            "--year-2025-run-id", "run-2025",
        )
        # Called at least twice: once for 2020, once for 2025
        assert mocks["load_actual"].call_count == 2

    def test_diff_calls_build_diff_report(self) -> None:
        mocks = self._patch_and_run(
            "diff", "--run-id", "run-001",
            "--year-2020-run-id", "run-2020",
            "--year-2025-run-id", "run-2025",
        )
        mocks["build_diff"].assert_called_once()

    def test_diff_calls_save_diff_report(self) -> None:
        mocks = self._patch_and_run(
            "diff", "--run-id", "run-001",
            "--year-2020-run-id", "run-2020",
            "--year-2025-run-id", "run-2025",
        )
        mocks["save_diff"].assert_called_once()

    def test_diff_calls_save_all_plots(self) -> None:
        mocks = self._patch_and_run(
            "diff", "--run-id", "run-001",
            "--year-2020-run-id", "run-2020",
            "--year-2025-run-id", "run-2025",
        )
        mocks["save_plots"].assert_called_once()

    def test_diff_requires_run_id(self) -> None:
        with pytest.raises(SystemExit):
            _run_main("diff", "--year-2020-run-id", "r20", "--year-2025-run-id", "r25")

    def test_diff_requires_year_2020_run_id(self) -> None:
        with pytest.raises(SystemExit):
            _run_main("diff", "--run-id", "r", "--year-2025-run-id", "r25")

    def test_diff_requires_year_2025_run_id(self) -> None:
        with pytest.raises(SystemExit):
            _run_main("diff", "--run-id", "r", "--year-2020-run-id", "r20")

    def test_diff_prints_saved_paths(self, capsys: pytest.CaptureFixture) -> None:
        import pandas as pd

        _sample = {"max_abs_pop_dev": 0.05, "towns_split": 3.0, "pln_area_splits": 2.0, "mean_pp": 0.4}
        mock_report_path = Path("/tmp/diff_report.json")
        mock_plot_paths = [Path("/tmp/max_abs_pop_dev.png")]

        with (
            patch("src.analysis.cli.load_ensemble_metrics", return_value=pd.DataFrame()),
            patch("src.analysis.cli.load_actual_assignments", return_value=pd.DataFrame({"node_id": [1], "ed_name": ["A"]})),
            patch("src.analysis.cli.load_actual_metrics", return_value=_sample),
            patch("src.analysis.cli.build_diff_report", return_value=[]),
            patch("src.analysis.cli.save_diff_report", return_value=mock_report_path),
            patch("src.analysis.cli.save_all_plots", return_value=mock_plot_paths),
        ):
            _run_main(
                "diff", "--run-id", "run-001",
                "--year-2020-run-id", "run-2020",
                "--year-2025-run-id", "run-2025",
            )

        captured = capsys.readouterr()
        assert str(mock_report_path) in captured.out

    def test_diff_passes_year_2020_run_id_to_load_actual(self) -> None:
        import pandas as pd

        _sample = {"max_abs_pop_dev": 0.05, "towns_split": 3.0, "pln_area_splits": 2.0, "mean_pp": 0.4}
        captured_calls: list = []

        def fake_load_actual(year: int, paths):
            captured_calls.append(year)
            return pd.DataFrame({"node_id": [1], "ed_name": ["A"]})

        with (
            patch("src.analysis.cli.load_ensemble_metrics", return_value=pd.DataFrame()),
            patch("src.analysis.cli.load_actual_assignments", side_effect=fake_load_actual),
            patch("src.analysis.cli.load_actual_metrics", return_value=_sample),
            patch("src.analysis.cli.build_diff_report", return_value=[]),
            patch("src.analysis.cli.save_diff_report", return_value=Path("/tmp/r.json")),
            patch("src.analysis.cli.save_all_plots", return_value=[]),
        ):
            _run_main(
                "diff", "--run-id", "run-001",
                "--year-2020-run-id", "run-2020",
                "--year-2025-run-id", "run-2025",
            )

        assert 2020 in captured_calls
        assert 2025 in captured_calls


# ---------------------------------------------------------------------------
# No subcommand → shows help (exits with 0 or 2)
# ---------------------------------------------------------------------------


def test_no_subcommand_exits() -> None:
    with pytest.raises(SystemExit):
        _run_main()
