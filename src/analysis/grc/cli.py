"""CLI entry point for the GRC/SMC variable-size ensemble (paper 2).

Usage:
    python -m src.analysis.grc.cli run-ensemble [options]

The GRC CLI is separate from the paper-1 CLI (src/analysis/cli.py) so
that the two pipelines cannot accidentally be mixed.
"""
from __future__ import annotations

import argparse
import sys

from src.analysis.config import PathsConfig
from src.analysis.grc.config import GRCConfig, SG2025_DISTRICT_TYPES, DistrictType
from src.analysis.grc.ensemble import run_grc_ensemble
from src.utils import OUTPUT, PROCESSED, RAW


def _build_paths() -> PathsConfig:
    return PathsConfig(processed_dir=PROCESSED, raw_dir=RAW, output_dir=OUTPUT)


def _cmd_run_ensemble(args: argparse.Namespace) -> None:
    config = GRCConfig(
        district_types=SG2025_DISTRICT_TYPES,
        pop_tolerance=args.pop_tolerance,
        n_steps=args.n_steps,
        burn_in=args.burn_in,
        seed=args.seed,
        run_id=args.run_id or "",
    )
    paths = _build_paths()
    print(
        f"Running GRC ensemble: k={config.k_districts}, seats={config.total_seats}, "
        f"seed={config.seed}, n_steps={config.n_steps}"
    )
    run_dir = run_grc_ensemble(config, paths)
    print(f"Done. Outputs in {run_dir}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m src.analysis.grc.cli",
        description="GRC/SMC variable-size ensemble pipeline (paper 2).",
    )
    sub = parser.add_subparsers(dest="command")

    p_run = sub.add_parser("run-ensemble", help="Run GRC MCMC ensemble.")
    p_run.add_argument("--run-id", default="", help="Unique run identifier.")
    p_run.add_argument("--n-steps", type=int, default=10_000)
    p_run.add_argument("--burn-in", type=int, default=1_000)
    p_run.add_argument("--seed", type=int, default=42)
    p_run.add_argument("--pop-tolerance", type=float, default=0.10)

    args = parser.parse_args(argv)
    if args.command == "run-ensemble":
        _cmd_run_ensemble(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
