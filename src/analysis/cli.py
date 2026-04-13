"""Command-line interface for the Singapore redistricting MCMC analysis pipeline.

Three subcommands:
  run-ensemble   -- run MCMC ensemble and write outputs
  assign-actual  -- assign subzones to actual electoral districts for a given year
  diff           -- compare 2020 and 2025 actual plans against an ensemble

Entry point::

    python -m src.analysis.cli <subcommand> [options]
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any

import networkx as nx
import pandas as pd

from src.analysis.assign_actual import assign_actual_plan
from src.analysis.config import EnsembleConfig, PathsConfig
from src.analysis.diff_2020_2025 import (
    build_diff_report,
    load_actual_assignments,
    load_ensemble_metrics,
    save_diff_report,
)
from src.analysis.ensemble import run_ensemble
from src.analysis.reporting.plots import save_all_plots
from src.utils import OUTPUT, PROCESSED, RAW

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers (thin wrappers; easy to mock in tests)
# ---------------------------------------------------------------------------


def _load_graph_for_actual(paths: PathsConfig) -> nx.Graph:
    """Load the subzone graph used for actual plan assignment."""
    from src.analysis.ensemble import build_pipeline_inputs

    graph, _gdf, _geoms = build_pipeline_inputs(paths)
    return graph


def _save_actual_assignment(assignment: dict[int, str | None], out_path: Path) -> None:
    """Persist *assignment* to *out_path* as Parquet."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {"node_id": node_id, "ed_name": ed_name}
        for node_id, ed_name in assignment.items()
    ]
    df = pd.DataFrame(rows)
    df.to_parquet(out_path, index=False)


def _make_paths_config() -> PathsConfig:
    return PathsConfig(processed_dir=PROCESSED, raw_dir=RAW, output_dir=OUTPUT)


# ---------------------------------------------------------------------------
# Subcommand handlers (each < 50 lines)
# ---------------------------------------------------------------------------


def _cmd_run_ensemble(args: argparse.Namespace) -> None:
    """Handler for the ``run-ensemble`` subcommand."""
    config = EnsembleConfig(
        run_id=args.run_id or "",
        n_steps=args.n_steps,
        burn_in=args.burn_in,
        k_districts=args.k,
        seed=args.seed,
    )
    paths = _make_paths_config()
    output_dir = run_ensemble(config, paths)
    print(str(output_dir))


def _cmd_assign_actual(args: argparse.Namespace) -> None:
    """Handler for the ``assign-actual`` subcommand."""
    year: int = args.year
    paths = _make_paths_config()

    graph = _load_graph_for_actual(paths)
    assignment = assign_actual_plan(year, graph, paths)

    out_path = OUTPUT / "actual_assignments" / f"{year}.parquet"
    _save_actual_assignment(assignment, out_path)
    print(str(out_path))


def _cmd_diff(args: argparse.Namespace) -> None:
    """Handler for the ``diff`` subcommand."""
    paths = _make_paths_config()

    ensemble_metrics = load_ensemble_metrics(args.run_id, paths)
    assignments_2020 = load_actual_assignments(2020, paths)
    assignments_2025 = load_actual_assignments(2025, paths)

    report = build_diff_report(assignments_2020, assignments_2025, ensemble_metrics)

    diff_out_dir = OUTPUT / "diff" / args.run_id
    report_path = save_diff_report(report, diff_out_dir)
    plot_paths = save_all_plots(report, ensemble_metrics, diff_out_dir / "plots")

    print(str(report_path))
    for p in plot_paths:
        print(str(p))


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.analysis.cli",
        description="Singapore redistricting MCMC analysis pipeline CLI.",
    )
    sub = parser.add_subparsers(dest="subcommand")
    sub.required = True

    # -- run-ensemble ---------------------------------------------------------
    re_parser = sub.add_parser(
        "run-ensemble",
        help="Run MCMC ensemble and write outputs.",
    )
    re_parser.add_argument("--run-id", default="", help="Unique run identifier.")
    re_parser.add_argument(
        "--n-steps", type=int, default=EnsembleConfig.n_steps, help="Number of MCMC steps."
    )
    re_parser.add_argument(
        "--burn-in", type=int, default=EnsembleConfig.burn_in, help="Burn-in steps."
    )
    re_parser.add_argument(
        "--k", type=int, default=EnsembleConfig.k_districts, help="Number of districts."
    )
    re_parser.add_argument(
        "--seed", type=int, default=EnsembleConfig.seed, help="Random seed."
    )
    re_parser.set_defaults(func=_cmd_run_ensemble)

    # -- assign-actual --------------------------------------------------------
    aa_parser = sub.add_parser(
        "assign-actual",
        help="Assign subzones to actual electoral districts.",
    )
    aa_parser.add_argument(
        "--year", type=int, required=True, choices=[2020, 2025],
        help="Election year (2020 or 2025).",
    )
    aa_parser.set_defaults(func=_cmd_assign_actual)

    # -- diff -----------------------------------------------------------------
    diff_parser = sub.add_parser(
        "diff",
        help="Compare actual plans against ensemble metrics.",
    )
    diff_parser.add_argument("--run-id", required=True, help="Ensemble run ID to compare against.")
    diff_parser.add_argument("--year-2020-run-id", required=True, help="Run ID for 2020 actual plan.")
    diff_parser.add_argument("--year-2025-run-id", required=True, help="Run ID for 2025 actual plan.")
    diff_parser.set_defaults(func=_cmd_diff)

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse arguments and dispatch to the appropriate subcommand handler."""
    parser = _build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":  # pragma: no cover
    main()
